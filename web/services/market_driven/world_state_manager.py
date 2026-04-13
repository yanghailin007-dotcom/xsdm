"""
世界状态管理器 (WorldStateManager)

解决剧情连贯性和设定合理性问题：
1. 跟踪所有剧情线索（神启会、高维观察者等）
2. 管理角色状态（伤势、能力、关系）
3. 强制执行设定规则（扮演度系统）
4. 生成"剧情约束提示词"注入每章
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class CharacterStatus:
    """角色状态"""
    name: str
    health: str = "健康"  # 健康/轻伤/重伤/濒死
    injuries: List[str] = field(default_factory=list)  # 具体伤势列表
    abilities_unlocked: List[str] = field(default_factory=list)  # 已解锁能力
    current_location: str = ""  # 当前位置
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他角色关系
    description: str = ""  # 描述（兼容旧数据）


@dataclass
class PlotThread:
    """剧情线索"""
    name: str
    status: str = "active"  # active/paused/resolved
    introduced_chapter: int = 0  # 引入章节
    last_mentioned: int = 0  # 最后提及章节
    priority: int = 5  # 优先级 1-10
    description: str = ""  # 描述
    next_trigger: str = ""  # 下次触发条件


@dataclass
class SystemRule:
    """系统规则状态 - 通用模型，支持不同书的系统类型"""
    # 通用字段（推荐新代码使用）
    system_name: str = ""  # 系统名称（如"弹幕干涉系统"、"扮演度系统"）
    system_type: str = ""  # 系统类型（如"金手指"、"扮演系统"、"直播系统"）
    current_level: str = "初始"  # 当前等级/阶段
    current_power: float = 0.0  # 当前能力值（通用）
    max_power: float = 0.0  # 历史最高能力值
    unlocked_abilities: List[str] = field(default_factory=list)  # 已解锁能力
    
    # 兼容字段（保留旧数据兼容）
    current_playing_degree: float = 0.0  # 当前扮演度（兼容旧数据）
    max_playing_degree: float = 0.0  # 历史最高扮演度（兼容旧数据）
    cooldown_end_chapter: int = 0  # 冷却结束章节
    special_states: List[str] = field(default_factory=list)  # 特殊状态
    unlocked_skills: List[str] = field(default_factory=list)  # 已解锁技能（兼容旧数据）


@dataclass
class WorldState:
    """完整世界状态"""
    protagonist: CharacterStatus = field(default_factory=lambda: CharacterStatus(name="主角"))
    allies: Dict[str, CharacterStatus] = field(default_factory=dict)  # 盟友
    enemies: Dict[str, CharacterStatus] = field(default_factory=dict)  # 敌人
    plot_threads: Dict[str, PlotThread] = field(default_factory=dict)  # 剧情线索
    system_rules: SystemRule = field(default_factory=SystemRule)  # 系统规则
    important_items: List[str] = field(default_factory=list)  # 重要物品
    global_events: List[str] = field(default_factory=list)  # 全局事件
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WorldState':
        # 🔥 修复：只获取类定义中存在的字段，忽略多余字段
        from dataclasses import fields
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # 🔥 辅助函数：过滤字典字段
        def filter_fields(data_dict: dict, dataclass_type) -> dict:
            """只保留dataclass定义的字段"""
            valid = {f.name for f in fields(dataclass_type)}
            return {k: v for k, v in data_dict.items() if k in valid}
        
        # 🔥 关键修复：递归转换嵌套字典为对象，同时过滤字段
        # protagonist: dict -> CharacterStatus
        if 'protagonist' in filtered_data and isinstance(filtered_data['protagonist'], dict):
            filtered_protagonist = filter_fields(filtered_data['protagonist'], CharacterStatus)
            filtered_data['protagonist'] = CharacterStatus(**filtered_protagonist)
        
        # allies: dict[str, dict] -> dict[str, CharacterStatus]
        if 'allies' in filtered_data and isinstance(filtered_data['allies'], dict):
            filtered_data['allies'] = {
                k: CharacterStatus(**filter_fields(v, CharacterStatus)) if isinstance(v, dict) else v
                for k, v in filtered_data['allies'].items()
            }
        
        # enemies: dict[str, dict] -> dict[str, CharacterStatus]
        if 'enemies' in filtered_data and isinstance(filtered_data['enemies'], dict):
            filtered_data['enemies'] = {
                k: CharacterStatus(**filter_fields(v, CharacterStatus)) if isinstance(v, dict) else v
                for k, v in filtered_data['enemies'].items()
            }
        
        # plot_threads: dict[str, dict] -> dict[str, PlotThread]
        if 'plot_threads' in filtered_data and isinstance(filtered_data['plot_threads'], dict):
            filtered_data['plot_threads'] = {
                k: PlotThread(**filter_fields(v, PlotThread)) if isinstance(v, dict) else v
                for k, v in filtered_data['plot_threads'].items()
            }
        
        # system_rules: dict -> SystemRule
        if 'system_rules' in filtered_data and isinstance(filtered_data['system_rules'], dict):
            filtered_rules = filter_fields(filtered_data['system_rules'], SystemRule)
            filtered_data['system_rules'] = SystemRule(**filtered_rules)
        
        return cls(**filtered_data)


class WorldStateManager:
    """
    世界状态管理器
    
    核心功能：
    1. 持久化剧情状态（跨批次保持连贯）
    2. 生成"剧情约束提示词"
    3. 校验生成内容是否符合设定
    4. 自动修复剧情bug
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.state_file = self.project_path / ".world_state.json"
        self.state = self._load_state()
        logger.info(f"[WorldState] 初始化完成 | 项目: {project_path}")
    
    def _load_state(self) -> WorldState:
        """加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"[WorldState] 已加载状态: {self.state_file}")
                return WorldState.from_dict(data)
            except Exception as e:
                logger.error(f"[WorldState] 加载状态失败: {e}")
        
        # 创建默认状态
        logger.info("[WorldState] 创建默认状态")
        return WorldState()
    
    def save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"[WorldState] 状态已保存")
        except Exception as e:
            logger.error(f"[WorldState] 保存状态失败: {e}")
    
    def _load_genre_config(self, genre: str) -> dict:
        """
        加载题材配置文件
        优先级: 用户配置 > 系统默认
        """
        # 获取配置路径（优先用户配置）
        base_path = self._get_config_base_path()
        config_path = base_path / "genre_techniques" / f"{genre}.yaml"
        
        if not config_path.exists():
            logger.warning(f"[WorldState] 题材配置不存在: {config_path}")
            return {}
        
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('world_state_initialization', {})
        except Exception as e:
            logger.error(f"[WorldState] 加载题材配置失败: {e}")
            return {}
    
    def _get_config_base_path(self) -> Path:
        """
        获取配置基础路径
        优先级: 
        1. prompt_packages/default/market_driven/v2_config/ (用户配置)
        2. prompt_packages/v2_architecture/ (系统默认)
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # 优先使用用户配置
        user_config = project_root / "prompt_packages" / "default" / "market_driven" / "v2_config"
        if user_config.exists():
            return user_config
        
        # 回退到系统默认
        return project_root / "prompt_packages" / "v2_architecture"
    
    def _load_golden_finger_config(self) -> dict:
        """
        加载金手指设计配置文件
        优先顺序：
        1. phase_one_products/金手指设计.json
        2. phase_one_products/金手指设定.json
        3. phase_one_products/golden_finger.json
        """
        possible_files = [
            self.project_path / "phase_one_products" / "金手指设计.json",
            self.project_path / "phase_one_products" / "金手指设定.json",
            self.project_path / "phase_one_products" / "golden_finger.json",
        ]
        
        for file_path in possible_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"[WorldState] 从 {file_path.name} 加载金手指配置成功")
                    return data
                except Exception as e:
                    logger.warning(f"[WorldState] 加载金手指配置失败 {file_path}: {e}")
        
        return {}
    
    def initialize_from_novel_data(self, novel_data: dict, chapter: int = 1):
        """从 novel_data 初始化状态（根据题材类型从配置读取）"""
        # 检测题材类型
        genre = self._detect_genre(novel_data)
        
        # 加载题材配置
        genre_config = self._load_genre_config(genre)
        
        # 主角
        char_design = novel_data.get('character_design', {})
        protagonist = char_design.get('protagonist', {})
        protag_name = protagonist.get('name', '主角')
        
        # 从配置获取主角初始化数据
        protagonist_config = genre_config.get('protagonist', {})
        self.state.protagonist = CharacterStatus(
            name=protag_name,
            health=protagonist_config.get('health', '健康'),
            abilities_unlocked=protagonist_config.get('abilities_unlocked', [])
        )
        
        # 盟友（根据配置和条件）
        allies = {}
        allies_config = genre_config.get('allies', [])
        for ally_config in allies_config:
            condition = ally_config.get('condition', '')
            # 检查条件
            if condition:
                condition_met = False
                if 'novel_data中包含' in condition:
                    # 提取关键词
                    import re
                    match = re.search(r"'([^']+)'", condition)
                    if match:
                        keyword = match.group(1)
                        condition_met = keyword in str(novel_data)
                
                if not condition_met:
                    continue
            
            # 创建盟友
            ally_name = ally_config.get('name', '盟友')
            allies[ally_name] = CharacterStatus(
                name=ally_name,
                health=ally_config.get('health', '健康'),
                abilities_unlocked=ally_config.get('abilities_unlocked', []),
                relationships={protag_name: ally_config.get('relationships', '盟友')}
            )
        self.state.allies = allies
        
        # 剧情线索（根据配置和条件）
        plot_threads = {}
        plots_config = genre_config.get('plot_threads', [])
        for plot_config in plots_config:
            condition = plot_config.get('condition', '')
            # 检查条件
            if condition:
                condition_met = False
                if 'novel_data中包含' in condition:
                    import re
                    match = re.search(r"'([^']+)'", condition)
                    if match:
                        keyword = match.group(1)
                        condition_met = keyword in str(novel_data)
                
                if not condition_met:
                    continue
            
            # 创建剧情线索
            plot_name = plot_config.get('name', '未命名')
            plot_threads[plot_name] = PlotThread(
                name=plot_name,
                status=plot_config.get('status', 'active'),
                introduced_chapter=plot_config.get('introduced_chapter', 1),
                priority=plot_config.get('priority', 5),
                description=plot_config.get('description', ''),
                next_trigger=plot_config.get('next_trigger', '')
            )
        self.state.plot_threads = plot_threads
        
        # 🔥 系统规则（优先从金手指设计文件加载，其次题材配置）
        gf_config = self._load_golden_finger_config()
        system_config = genre_config.get('system_rules', {})
        
        if gf_config:
            # 从金手指设计文件构建系统规则
            abilities = gf_config.get('abilities', [])
            initial_abilities = []
            if isinstance(abilities, dict):
                # 兼容 abilities 为字典的格式 (e.g. {"initial": "...", "growth": "..."})
                for key, value in abilities.items():
                    if key == 'initial' or '初始' in str(value):
                        initial_abilities.append(str(value))
            elif isinstance(abilities, list):
                for ab in abilities:
                    if isinstance(ab, dict) and ab.get('stage') == '初始':
                        initial_abilities.append(ab.get('ability', ''))
                    elif isinstance(ab, str):
                        initial_abilities.append(ab)
            
            # 安全获取 current_level
            current_level = '初始'
            if isinstance(abilities, list) and abilities and isinstance(abilities[0], dict):
                current_level = abilities[0].get('stage', '初始')
            elif isinstance(abilities, dict):
                current_level = abilities.get('stage', '初始') or '初始'
            
            self.state.system_rules = SystemRule(
                system_name=gf_config.get('name', '系统'),
                system_type=gf_config.get('type', '金手指'),
                current_level=current_level,
                current_power=1.0,
                unlocked_abilities=initial_abilities[:2]  # 只取前2个初始能力
            )
            logger.info(f"[WorldState] 从金手指设计文件初始化系统规则: {gf_config.get('name')}")
        elif system_config:
            # 从题材配置构建系统规则
            self.state.system_rules = SystemRule(
                system_name=system_config.get('system_name', '系统'),
                system_type=system_config.get('system_type', '金手指'),
                current_level=system_config.get('current_level', '初始'),
                current_power=float(system_config.get('current_power', 0.0)),
                current_playing_degree=float(system_config.get('current_playing_degree', 0.0)),
                max_playing_degree=float(system_config.get('max_playing_degree', 0.0)),
                unlocked_abilities=system_config.get('unlocked_abilities', []),
                unlocked_skills=system_config.get('unlocked_skills', [])
            )
        else:
            self.state.system_rules = SystemRule()
        
        self.save_state()
        logger.info(f"[WorldState] 从配置初始化完成 | 题材: {genre} | 主角: {protag_name}")
    
    def _detect_genre(self, novel_data: dict) -> str:
        """检测小说题材类型"""
        # 1. 从 suggestions.genre 获取
        suggestions = novel_data.get('suggestions', {})
        if isinstance(suggestions, dict) and suggestions.get('genre'):
            return suggestions.get('genre')
        
        # 2. 从 tags 分析
        tags = novel_data.get('tags', [])
        if isinstance(tags, list):
            tags_str = ' '.join(str(t) for t in tags)
        else:
            tags_str = str(tags)
        
        # 3. 从标题分析
        title = novel_data.get('title', '')
        
        combined_text = tags_str + ' ' + title
        
        # 关键词匹配
        if any(kw in combined_text for kw in ['国运', '扮演', '禁地', '求生', '龙国', '灯塔国']):
            return '国运文'
        elif any(kw in combined_text for kw in ['神豪', '返利', '暴击', '消费', '壕']):
            return '神豪文'
        elif any(kw in combined_text for kw in ['赘婿', '龙王', '修罗', '战神', '丈母娘']):
            return '赘婿文'
        
        # 从大纲内容判断
        outline = novel_data.get('outline', '')
        if '国运' in outline or '扮演' in outline or '禁地' in outline:
            return '国运文'
        elif '神豪' in outline or '返利' in outline:
            return '神豪文'
        
        return '未知'  # 默认未知题材
    
    def update_after_chapter(self, chapter_num: int, chapter_content: str, chapter_title: str = ""):
        """
        根据生成的章节内容更新状态
        
        Args:
            chapter_num: 章节号
            chapter_content: 章节内容
            chapter_title: 章节标题
        """
        content = chapter_content
        
        # 1. 检测主角伤势变化
        if '中毒' in content or '毒伤' in content:
            if '白月魁' in content and ('中毒' in content.split('白月魁')[1][:500] if '白月魁' in content else False):
                ally = self.state.allies.get('白月魁')
                if ally:
                    ally.health = "中毒"
                    ally.injuries.append(f"第{chapter_num}章中毒")
                    logger.info(f"[WorldState] 白月魁状态更新: 中毒 (第{chapter_num}章)")
        
        if '治愈' in content or '痊愈' in content or '伤势好转' in content:
            for name, char in self.state.allies.items():
                if name in content and char.health != "健康":
                    char.health = "健康"
                    char.injuries = []
                    logger.info(f"[WorldState] {name}状态更新: 恢复健康")
        
        # 2. 检测能力解锁
        skill_keywords = {
            '雷神领域': '雷神领域',
            '九霄神雷': '九霄神雷',
            '雷霆万钧': '雷霆万钧',
            '雷神之锤': '雷神之锤(完整)',
            '雷神之翼': '雷神之翼(飞行)',
            '电磁感知': '电磁感知',
        }
        
        for keyword, skill_name in skill_keywords.items():
            if keyword in content and skill_name not in self.state.system_rules.unlocked_skills:
                self.state.system_rules.unlocked_skills.append(skill_name)
                logger.info(f"[WorldState] 新技能解锁: {skill_name} (第{chapter_num}章)")
        
        # 3. 检测扮演度变化
        import re
        playing_degree_patterns = [
            r'扮演度[：:]\s*(\d+)%',
            r'相似度[：:]\s*(\d+)%',
            r'当前扮演度[：:]\s*(\d+)',
        ]
        for pattern in playing_degree_patterns:
            matches = re.findall(pattern, content)
            if matches:
                try:
                    degree = float(matches[-1])  # 取最后一个
                    self.state.system_rules.current_playing_degree = degree
                    if degree > self.state.system_rules.max_playing_degree:
                        self.state.system_rules.max_playing_degree = degree
                    logger.info(f"[WorldState] 扮演度更新: {degree}% (第{chapter_num}章)")
                except:
                    pass
                break
        
        # 4. 更新剧情线索提及时间
        for name, thread in self.state.plot_threads.items():
            if name in content:
                thread.last_mentioned = chapter_num
                if thread.status == 'paused':
                    thread.status = 'active'
                    logger.info(f"[WorldState] 剧情线索激活: {name} (第{chapter_num}章)")
        
        # 5. 检测特殊状态
        if '透支' in content or '虚弱期' in content:
            if '透支' not in self.state.system_rules.special_states:
                self.state.system_rules.special_states.append('透支')
                logger.info(f"[WorldState] 特殊状态添加: 透支 (第{chapter_num}章)")
        
        if '虚弱期结束' in content or '恢复' in content:
            if '透支' in self.state.system_rules.special_states:
                self.state.system_rules.special_states.remove('透支')
                logger.info(f"[WorldState] 特殊状态移除: 透支 (第{chapter_num}章)")
        
        self.save_state()
    
    def build_constraint_prompt(self, chapter_num: int) -> str:
        """
        构建剧情约束提示词
        
        这个提示词会被注入到每章的生成指令中，强制AI遵循当前状态
        使用通用字段，支持不同书的系统类型（弹幕系统、扮演度系统等）
        """
        lines = ["\n【世界状态约束 - 必须遵循】\n"]
        
        # 1. 主角状态
        protag = self.state.protagonist
        lines.append(f"主角({protag.name})当前状态:")
        lines.append(f"  - 健康: {protag.health}")
        if protag.current_location:
            lines.append(f"  - 当前位置: {protag.current_location}")
        if protag.abilities_unlocked:
            lines.append(f"  - 已解锁能力: {', '.join(protag.abilities_unlocked[-3:])}")
        
        # 2. 盟友状态
        if self.state.allies:
            lines.append("\n盟友状态:")
            for name, ally in self.state.allies.items():
                if ally.health != "健康":
                    lines.append(f"  - {name}: {ally.health}")
                    if ally.injuries:
                        lines.append(f"    伤势: {ally.injuries[-1]}")
                else:
                    lines.append(f"  - {name}: 健康")
        
        # 3. 系统规则（使用实际的系统名称，不再硬编码"扮演度"）
        rules = self.state.system_rules
        
        # 优先使用新的通用字段，兼容旧字段
        system_name = rules.system_name or "系统"
        current_level = rules.current_level or "初始"
        current_power = rules.current_power if rules.current_power > 0 else rules.current_playing_degree
        max_power = rules.max_power if rules.max_power > 0 else rules.max_playing_degree
        
        # 合并已解锁能力（新旧字段兼容）
        all_abilities = list(rules.unlocked_abilities)
        if not all_abilities and rules.unlocked_skills:
            all_abilities = list(rules.unlocked_skills)
        
        lines.append(f"\n{system_name}状态:")
        lines.append(f"  - 当前等级/阶段: {current_level}")
        
        # 只有在有具体数值时才显示
        if current_power > 0:
            lines.append(f"  - 当前能力值: {current_power:.1f}")
        if max_power > 0:
            lines.append(f"  - 历史最高: {max_power:.1f}")
        if all_abilities:
            lines.append(f"  - 已解锁能力: {', '.join(all_abilities[-3:])}")
        if rules.special_states:
            lines.append(f"  - 特殊状态: {', '.join(rules.special_states)}")
        
        # 4. 活跃的剧情线索
        active_threads = [
            t for t in self.state.plot_threads.values()
            if t.status == 'active' and t.last_mentioned is not None and chapter_num - t.last_mentioned <= 5  # 5章内提及过
        ]
        if active_threads:
            lines.append(f"\n活跃剧情线索(本章需要提及或推进):")
            for thread in sorted(active_threads, key=lambda x: x.priority, reverse=True)[:3]:
                lines.append(f"  - {thread.name}: {thread.description}")
                if thread.next_trigger and chapter_num >= thread.introduced_chapter:
                    lines.append(f"    提示: {thread.next_trigger}")
        
        # 5. 即将激活的线索
        pending_threads = [
            t for t in self.state.plot_threads.values()
            if t.status == 'paused' and t.introduced_chapter <= chapter_num
        ]
        if pending_threads:
            lines.append(f"\n待激活线索(本章可引入):")
            for thread in pending_threads[:2]:
                lines.append(f"  - {thread.name}: 预计第{thread.introduced_chapter}章引入")
        
        lines.append("\n【约束规则】")
        lines.append(f"1. 必须保持上述角色状态与{system_name}状态一致")
        lines.append("2. 不能突然解锁未获得的能力")
        lines.append("3. 活跃的剧情线索需要在文中体现（至少提及）")
        lines.append("4. 能力/等级变化需要有合理过渡，不能突变")
        lines.append("")
        
        return "\n".join(lines)
    
    def validate_chapter(self, chapter_num: int, content: str) -> List[str]:
        """
        校验章节内容是否符合设定
        
        Returns:
            问题列表，空列表表示通过
        """
        issues = []
        
        # 1. 校验主角名一致性
        protag_name = self.state.protagonist.name
        wrong_names = ['林枫', '林霄', '林雷']
        for wrong in wrong_names:
            if wrong in content:
                issues.append(f"使用了错误的主角名'{wrong}'，应为'{protag_name}'")
        
        # 2. 校验扮演度合理性
        # 如果扮演度从很低突然变很高，需要检查是否有合理解释
        import re
        degree_matches = re.findall(r'扮演度[：:]\s*(\d+)%', content)
        if degree_matches:
            degrees = [int(d) for d in degree_matches]
            if len(degrees) >= 2:
                max_change = max(degrees) - min(degrees)
                if max_change > 50:
                    issues.append(f"扮演度变化过大({min(degrees)}%→{max(degrees)}%)，需要更合理的过渡")
        
        # 3. 校验伤势连续性
        for name, ally in self.state.allies.items():
            if ally.health == "中毒" and name in content:
                # 如果上一章中毒，本章没有治疗过程却健康了
                if '治愈' not in content and '解毒' not in content and '恢复' not in content:
                    if '健康' in content or '无碍' in content:
                        issues.append(f"{name}上一章中毒，本章没有治疗过程就恢复健康")
        
        # 4. 校验剧情线索
        for name, thread in self.state.plot_threads.items():
            if thread.status == 'active' and thread.last_mentioned is not None and thread.last_mentioned < chapter_num - 3:
                # 活跃线索超过3章没提及
                if name not in content:
                    issues.append(f"活跃剧情线索'{name}'已连续{chapter_num - thread.last_mentioned}章未提及")
        
        return issues
    
    def get_summary(self) -> str:
        """获取状态摘要"""
        return (
            f"[WorldState] 主角:{self.state.protagonist.name}({self.state.protagonist.health}) | "
            f"扮演度:{self.state.system_rules.current_playing_degree:.0f}% | "
            f"活跃线索:{len([t for t in self.state.plot_threads.values() if t.status=='active'])} | "
            f"解锁技能:{len(self.state.system_rules.unlocked_skills)}"
        )
