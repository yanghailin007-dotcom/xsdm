"""
Tomato Bestseller Tactical Session
番茄爆款细纲会话 - 三轮对话生成30章规划

三轮流程：
1. 第1轮：核心设定对齐（世界观+金手指+主角人设）
2. 第2轮：情绪爽点规划（情绪曲线+钩子+爽点）
3. 第3轮：角色出场规划（已有角色+新增角色）

作者: AI Assistant
版本: 3.0
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from .phase_one_loader import PhaseOneDataLoader, load_phase_one_data

logger = logging.getLogger(__name__)


class TomatoBestsellerTacticalSession:
    """
    番茄爆款细纲会话
    
    专为番茄小说爆款公式设计的三轮细纲规划：
    - 确保核心设定不丢失
    - 章章有钩子，情绪过山车
    - 角色受控，避免乱创
    """
    
    # 番茄爆款常量
    CHAPTERS_PER_BATCH = 30      # 每批次规划30章
    MAX_NEW_CHARACTERS = 2       # 每批次最多新增2个角色
    HOOK_TYPES = ["悬念", "危机", "反转", "震惊", "期待", "疑问"]
    EMOTION_TYPES = ["压抑", "紧张", "愤怒", "嘲讽", "反转", "小爽快", "大爽快", "震惊", "期待", "满足"]
    BEAT_TYPES = ["铺垫", "冲突", "反转", "渲染", "爽点", "伏笔", "过渡"]
    
    def __init__(
        self,
        session_id: str,
        start_chapter: int,
        end_chapter: int,
        project_path: Path,
        api_client=None,
        novel_title: str = "",
        emotion_curve: List[Dict] = None,
        sub_theme: str = None
    ):
        self.session_id = session_id
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        self.project_path = Path(project_path)
        self.api_client = api_client
        self.novel_title = novel_title
        self.emotion_curve = emotion_curve or []
        self.sub_theme = sub_theme or self._detect_sub_theme()
        
        # 加载一阶段数据
        self.phase_one_data = load_phase_one_data(self.project_path)
        
        # 🔥 加载核心设定圣经（layer_1_4_core_settings.md）
        self.core_settings_bible = self._load_core_settings_bible()
        
        # 三轮输出缓存
        self.round1_result = None    # 核心设定对齐
        self.round2_result = None    # 情绪爽点规划
        self.round3_result = None    # 角色出场规划
        
        # 最终蓝图
        self.final_blueprint = None
        
        logger.info(f"[TomatoTacticalSession] 初始化: {session_id}, 第{start_chapter}-{end_chapter}章")
    
    def generate_blueprint(self) -> Dict:
        """
        执行三轮对话，生成完整战术蓝图
        
        Returns:
            Dict: 包含设定框架、情绪规划、角色规划的完整蓝图
        """
        logger.info(f"[TomatoTacticalSession] 开始三轮细纲规划")
        
        # 第1轮：核心设定对齐
        logger.info(f"[TomatoTacticalSession] 第1轮：核心设定对齐")
        self.round1_result = self._round_1_core_setting()
        
        # 第2轮：情绪爽点规划
        logger.info(f"[TomatoTacticalSession] 第2轮：情绪爽点规划")
        self.round2_result = self._round_2_emotion_planning()
        
        # 第3轮：角色出场规划
        logger.info(f"[TomatoTacticalSession] 第3轮：角色出场规划")
        self.round3_result = self._round_3_character_planning()
        
        # 合并输出
        self.final_blueprint = self._merge_blueprint()
        
        logger.info(f"[TomatoTacticalSession] 三轮规划完成，生成蓝图")
        return self.final_blueprint
    
    def _round_1_core_setting(self) -> Dict:
        """
        第1轮：核心设定对齐
        
        输入：世界观、金手指、主角人设、阶段目标
        输出：30章设定落地框架
        """
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认框架")
            return self._get_default_core_framework()
        
        # 构建第1轮提示词
        prompt = self._build_round1_prompt()
        system_prompt = self._get_round1_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round1_core_setting",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                purpose="战术规划-核心设定对齐",
                provider='kimi'
            )
            
            result = self._parse_json_response(response)
            
            # 验证关键字段
            if not result.get('core_framework'):
                logger.warning("[TomatoTacticalSession] 第1轮输出缺少core_framework，使用默认")
                return self._get_default_core_framework()
            
            logger.info(f"[TomatoTacticalSession] 第1轮完成，获得设定框架")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第1轮失败: {e}")
            return self._get_default_core_framework()
    
    def _load_core_settings_bible(self) -> str:
        """读取 layer_1_4_core_settings.md 作为核心设定圣经"""
        bible_path = self.project_path / "layer_1_4_core_settings.md"
        if bible_path.exists():
            try:
                content = bible_path.read_text(encoding='utf-8')
                # 截断过长内容，避免 system prompt 爆炸（保留前 8000 字）
                if len(content) > 8000:
                    content = content[:8000] + "\n\n[核心设定圣经过长，已截断前8000字]"
                logger.info(f"[TomatoTacticalSession] 已加载核心设定圣经: {bible_path} ({len(content)} 字)")
                return content
            except Exception as e:
                logger.warning(f"[TomatoTacticalSession] 读取核心设定圣经失败: {e}")
        else:
            logger.warning(f"[TomatoTacticalSession] 核心设定圣经不存在: {bible_path}，将回退到一阶段数据摘要")
        return ""
    
    def _safe_dict(self, obj, path=""):
        """安全获取字典，非字典时返回空字典并记录警告"""
        if isinstance(obj, dict):
            return obj
        logger.warning(f"[TomatoTacticalSession] 期望dict但得到{type(obj).__name__} (路径: {path})，使用空字典")
        return {}
    
    def _detect_sub_theme(self) -> Optional[str]:
        """基于 project_info.json 中的 genre 推断子主题"""
        try:
            project_info_path = self.project_path / "project_info.json"
            if project_info_path.exists():
                with open(project_info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                genre = info.get("genre", "")
                mapping = {
                    "god-tier-spending": "spending_rebate",
                    "god-tier-investment": "investment_guru",
                    "god-tier-livestream": "livestream_tycoon",
                    "god-tier-checkin": "daily_checkin",
                    "sign-in-daily": "daily_checkin",
                }
                sub_theme = mapping.get(genre)
                if sub_theme:
                    logger.info(f"[TomatoTacticalSession] 自动推断子主题: {genre} -> {sub_theme}")
                    return sub_theme
        except Exception as e:
            logger.warning(f"[TomatoTacticalSession] 推断子主题失败: {e}")
        return None
    
    def _load_prompt_template(self, round_name: str, prompt_type: str, sub_theme=None) -> Optional[str]:
        """从配置包加载prompt模板（支持按题材覆写和子主题场景库注入）"""
        try:
            # 定位配置文件：从当前文件向上回溯到项目根
            config_path = (
                Path(__file__).parent.parent.parent.parent
                / "prompt_packages"
                / "default"
                / "market_driven"
                / "components"
                / "planning"
                / "tactical_session_prompts.json"
            )
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 优先检查题材覆写
            genre = getattr(self, '_genre', '') or ''
            if genre:
                override = (
                    data.get("genre_overrides", {})
                    .get(genre, {})
                    .get(round_name, {})
                    .get(prompt_type)
                )
                if override:
                    logger.info(f"[TomatoTacticalSession] 使用题材覆写prompt: {genre}/{round_name}/{prompt_type}")
                    return override
            
            template = data.get("prompts", {}).get(round_name, {}).get(prompt_type)
            
            # 注入子主题场景库
            if template and round_name == "round2" and prompt_type == "user_prompt_template" and sub_theme:
                scenarios = (
                    data.get("prompts", {})
                    .get("round2", {})
                    .get("sub_themes", {})
                    .get(sub_theme, {})
                    .get("scenarios", "")
                )
                if scenarios:
                    template = template.replace("{sub_theme_scenarios}", scenarios)
                    logger.info(f"[TomatoTacticalSession] 注入子主题场景库: {sub_theme}")
                else:
                    template = template.replace("{sub_theme_scenarios}", "")
                    logger.warning(f"[TomatoTacticalSession] 未找到子主题场景库: {sub_theme}")
            
            return template
        except Exception as e:
            logger.warning(f"[TomatoTacticalSession] 加载prompt配置失败({round_name}/{prompt_type}): {e}")
            return None
    
    def _build_round1_prompt(self) -> str:
        """构建第1轮提示词（精简版：核心设定已由圣经承载）"""
        # 只需要提取用于模板和自检的关键信息
        world = self._safe_dict(self.phase_one_data.get('world_setting', {}), 'world_setting')
        power_system = self._safe_dict(world.get('power_system', {}), 'world_setting.power_system')
        char_design = self._safe_dict(self.phase_one_data.get('character_design', {}), 'character_design')
        protagonist = self._safe_dict(char_design.get('protagonist', {}), 'character_design.protagonist')
        progression = self.phase_one_data.get('progression_path', {})
        
        # 防御性处理：protagonist_growth 可能是 dict 或 list
        protagonist_growth = progression.get('protagonist_growth', {})
        if isinstance(protagonist_growth, dict):
            milestones = protagonist_growth.get('milestones', [])
        elif isinstance(protagonist_growth, list):
            milestones = protagonist_growth
        else:
            milestones = []
        
        # 从配置包加载模板
        prompt_template = self._load_prompt_template("round1", "user_prompt_template")
        if not prompt_template:
            logger.warning("[TomatoTacticalSession] Round1 用户prompt配置缺失，使用极简fallback")
            prompt_template = """# 番茄爆款细纲规划 - 第1轮：核心设定对齐\n\n为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章设定落地框架。\n\n系统：{system_name}\n主角：{protagonist_name}\n\n升级里程碑：\n{milestones}\n\n请输出包含 core_framework 的JSON。"""
        
        # 🔥 动态提取系统/金手指名称和主角名，用于自检清单
        system_name = (
            self.phase_one_data.get('golden_finger', {}).get('basic_info', {}).get('name')
            or self.phase_one_data.get('golden_finger', {}).get('name')
            or power_system.get('name')
            or '核心金手指系统'
        )
        
        format_params = {
            'novel_title': self.novel_title,
            'start_chapter': self.start_chapter,
            'end_chapter': self.end_chapter,
            'system_name': system_name,
            'protagonist_name': protagonist.get('name', '主角'),
            'milestones': self._format_milestones(milestones)
        }
        
        return prompt_template.format(**format_params)
    
    def _get_round1_system_prompt(self) -> str:
        """第1轮系统提示词（注入核心设定圣经）"""
        sp = self._load_prompt_template("round1", "system_prompt")
        if not sp:
            sp = "你是专业的番茄小说细纲规划师，负责核心设定对齐。输出必须是JSON格式。"
        if self.core_settings_bible:
            sp += f"\n\n---\n\n# 核心设定圣经（必须严格遵守）\n\n{self.core_settings_bible}"
        return sp
    
    def _round_2_emotion_planning(self) -> Dict:
        """
        第2轮：情绪爽点规划（核心层）
        
        输入：第1轮输出 + 情绪曲线 + 爆款公式
        输出：30章详细情绪设计
        """
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认情绪规划")
            return self._get_default_emotion_plan()
        
        prompt = self._build_round2_prompt()
        system_prompt = self._get_round2_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round2_emotion_planning",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.75,
                purpose="战术规划-情绪爽点",
                provider='kimi'
            )
            
            result = self._parse_json_response(response)
            
            if not result.get('chapters'):
                logger.warning("[TomatoTacticalSession] 第2轮输出缺少chapters，使用默认")
                return self._get_default_emotion_plan()
            
            # 验证每章都有钩子
            self._validate_hooks(result.get('chapters', []))
            
            logger.info(f"[TomatoTacticalSession] 第2轮完成，规划{len(result.get('chapters', []))}章")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第2轮失败: {e}")
            return self._get_default_emotion_plan()
    
    def _build_round2_prompt(self) -> str:
        """构建第2轮提示词 - 使用format方法避免f-string解析问题"""
        round1 = self.round1_result.get('core_framework', {}) if self.round1_result else {}
        
        emotion_blueprint = self._safe_dict(self.phase_one_data.get('emotional_blueprint', {}), 'emotional_blueprint')
        climax_moments = emotion_blueprint.get('climax_moments', [])
        
        if not climax_moments and self.emotion_curve:
            climax_moments = [
                f"第{e.get('chapter')}章-{e.get('emotion', '高潮')}"
                for e in self.emotion_curve
                if e.get('intensity', 0) >= 9
            ]
        
        batch_climax = [c for c in climax_moments 
                       if self.start_chapter <= self._parse_chapter_num(c) <= self.end_chapter]
        
        emotion_curve_text = ""
        if self.emotion_curve:
            relevant = [e for e in self.emotion_curve 
                       if self.start_chapter <= e.get('chapter', 0) <= self.end_chapter]
            emotion_curve_text = "\n".join([
                f"第{e.get('chapter')}章: {e.get('emotion', '')} (强度{e.get('intensity', 5)})"
                for e in relevant[:10]
            ])
        
        world_building = self._format_simple_list(round1.get('world_building_chapters', []))
        golden_finger = self._format_simple_list(round1.get('golden_finger_progression', []))
        protagonist_moments = self._format_simple_list(round1.get('protagonist_moments', []))
        goal_milestones = self._format_goal_milestones(round1.get('goal_milestones', {}))
        key_constraints = self._format_list(round1.get('key_constraints', []))
        batch_climax_str = self._format_list(batch_climax)
        batch_climax_raw = ', '.join(str(c) for c in batch_climax) if batch_climax else '无'
        emotion_text = emotion_curve_text or '未提供详细曲线'
        
        prompt_template = self._load_prompt_template("round2", "user_prompt_template", sub_theme=self.sub_theme)
        if not prompt_template:
            logger.warning("[TomatoTacticalSession] Round2 用户prompt配置缺失，使用极简fallback")
            prompt_template = """# 番茄爆款细纲规划 - 第2轮：情绪爽点规划\n\n为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章详细情绪设计。\n\n设定约束：\n{key_constraints}\n\n高潮节点：{batch_climax_raw}\n\n请输出包含 chapters 和 emotion_analysis 的JSON。"""
        
        return prompt_template.format(
            novel_title=self.novel_title,
            start_chapter=self.start_chapter,
            end_chapter=self.end_chapter,
            world_building=world_building,
            golden_finger=golden_finger,
            protagonist_moments=protagonist_moments,
            goal_milestones=goal_milestones,
            key_constraints=key_constraints,
            batch_climax_str=batch_climax_str,
            batch_climax_raw=batch_climax_raw,
            emotion_text=emotion_text
        )
    
    def _get_round2_system_prompt(self) -> str:
        """第2轮系统提示词（注入核心设定圣经）"""
        sp = self._load_prompt_template("round2", "system_prompt")
        if not sp:
            sp = "你是番茄小说爆款情绪设计专家。输出必须是JSON格式，每章必须有hook_content。"
        if self.core_settings_bible:
            sp += f"\n\n---\n\n# 核心设定圣经（必须严格遵守）\n\n{self.core_settings_bible}"
        return sp
    
    def _round_3_character_planning(self) -> Dict:
        """
        第3轮：角色出场规划
        
        输入：前两轮输出 + 角色设计.json
        输出：角色出场表 + 新增角色规划
        """
        # 加载已有角色
        loader = PhaseOneDataLoader(self.project_path)
        existing_chars = loader.get_character_list()
        
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认角色规划")
            return self._get_default_character_plan(existing_chars)
        
        prompt = self._build_round3_prompt(existing_chars)
        system_prompt = self._get_round3_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round3_character_planning",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                purpose="战术规划-角色出场",
                provider='kimi'
            )
            
            result = self._parse_json_response(response)
            
            if not result.get('character_plan'):
                logger.warning("[TomatoTacticalSession] 第3轮输出缺少character_plan，使用默认")
                return self._get_default_character_plan(existing_chars)
            
            # 验证新角色数量
            new_chars = result.get('character_plan', {}).get('new_characters', [])
            if len(new_chars) > self.MAX_NEW_CHARACTERS:
                logger.warning(f"[TomatoTacticalSession] 新角色过多({len(new_chars)})，限制为{self.MAX_NEW_CHARACTERS}")
                result['character_plan']['new_characters'] = new_chars[:self.MAX_NEW_CHARACTERS]
            
            logger.info(f"[TomatoTacticalSession] 第3轮完成，规划{len(existing_chars)}个已有角色+{len(new_chars)}个新角色")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第3轮失败: {e}")
            return self._get_default_character_plan(existing_chars)
    
    def _build_round3_prompt(self, existing_chars: List[Dict]) -> str:
        """构建第3轮提示词"""
        # 格式化已有角色
        chars_text = "\n".join([
            f"- {c.get('name')} ({c.get('type')}): {c.get('role')} - 特质: {', '.join(c.get('traits', [])[:3])}"
            for c in existing_chars[:20]
        ])
        
        # 获取第2轮章节规划
        chapters = self.round2_result.get('chapters', []) if self.round2_result else []
        chapters_summary = "\n".join([
            f"第{c.get('chapter_number')}章: {c.get('event', '')[:50]}... 情绪:{c.get('emotion')}{c.get('intensity')}"
            for c in chapters[:15]
        ])
        
        prompt_template = self._load_prompt_template("round3", "user_prompt_template")
        if not prompt_template:
            logger.warning("[TomatoTacticalSession] Round3 用户prompt配置缺失，使用极简fallback")
            prompt_template = """# 番茄爆款细纲规划 - 第3轮：角色出场规划

已有角色：
{chars_text}

前15章情节：
{chapters_summary}

请输出包含 character_plan 的JSON，新角色不超过2个。"""
        return prompt_template.format(
            chars_text=chars_text,
            chapters_summary=chapters_summary,
            start_chapter=self.start_chapter
        )
    
    def _get_round3_system_prompt(self) -> str:
        """第3轮系统提示词（注入核心设定圣经）"""
        sp = self._load_prompt_template("round3", "system_prompt")
        if not sp:
            sp = "你是角色规划专家。输出必须是JSON格式，new_characters不能超过2个。"
        if self.core_settings_bible:
            sp += f"\n\n---\n\n# 核心设定圣经（必须严格遵守）\n\n{self.core_settings_bible}"
        return sp
    
    def _merge_blueprint(self) -> Dict:
        """合并三轮输出为最终蓝图"""
        # 获取各轮数据
        round1 = self.round1_result or {}
        round2 = self.round2_result or {}
        round3 = self.round3_result or {}
        
        # 获取章节列表
        chapters = round2.get('chapters', [])
        character_plan = round3.get('character_plan', {})
        
        # 为每章添加角色分配
        chapter_assignments = character_plan.get('chapter_assignments', [])
        assignments_map = {a.get('chapter'): a for a in chapter_assignments}
        
        for chapter in chapters:
            ch_num = chapter.get('chapter_number')
            if ch_num in assignments_map:
                chapter['assigned_characters'] = {
                    'core': assignments_map[ch_num].get('core', []),
                    'major': assignments_map[ch_num].get('major', []),
                    'minor': assignments_map[ch_num].get('minor', [])
                }
            else:
                # 默认分配：从已有角色中提取核心角色，不硬编码
                existing_chars = character_plan.get('existing_characters', [])
                protagonist = next((c for c in existing_chars if c.get('type') == 'protagonist'), None)
                core_chars = [protagonist.get('name')] if protagonist else []
                
                # 添加重要盟友（最多1个）
                allies = [c.get('name') for c in existing_chars if c.get('type') == 'ally'][:1]
                core_chars.extend(allies)
                
                chapter['assigned_characters'] = {
                    'core': core_chars,
                    'major': [],
                    'minor': []
                }
        
        # 构建最终蓝图
        blueprint = {
            'metadata': {
                'session_id': self.session_id,
                'range': f'{self.start_chapter}-{self.end_chapter}',
                'generated_at': datetime.now().isoformat(),
                'rounds_completed': 3,
                'novel_title': self.novel_title
            },
            'core_setting': round1.get('core_framework', {}),
            'chapters': chapters,
            'character_plan': character_plan,
            'emotion_analysis': round2.get('emotion_analysis', {}),
            'summary': {
                'total_chapters': len(chapters),
                'total_satisfaction_points': len([c for c in chapters if c.get('satisfaction_point')]),
                'total_face_slapping': len([c for c in chapters if c.get('face_slapping')]),
                'new_characters_introduced': len(character_plan.get('new_characters', [])),
                'goal_milestones_achieved': len(round1.get('core_framework', {}).get('goal_milestones', {}))
            }
        }
        
        # 🔥 保存新角色到角色设计文件
        self._save_new_characters_to_design(character_plan.get('new_characters', []))
        
        return blueprint
    
    def _save_new_characters_to_design(self, new_characters: List[Dict]) -> None:
        """
        将新角色保存到角色设计.json文件
        
        Args:
            new_characters: 新角色列表
        """
        if not new_characters or not self.project_path:
            return
        
        try:
            import json
            from pathlib import Path
            
            # 角色设计文件路径
            char_design_path = Path(self.project_path) / "phase_one_products" / "角色设计.json"
            
            if not char_design_path.exists():
                logger.warning(f"[TomatoTacticalSession] 角色设计文件不存在: {char_design_path}")
                return
            
            # 读取现有角色设计
            with open(char_design_path, 'r', encoding='utf-8') as f:
                char_design = json.load(f)
            
            # 确保有 supporting_roles 字段
            if 'supporting_roles' not in char_design:
                char_design['supporting_roles'] = []
            
            if not isinstance(char_design['supporting_roles'], list):
                char_design['supporting_roles'] = []
            
            # 获取现有角色名（避免重复）
            existing_names = set()
            for key in ['protagonist', 'core_allies', 'main_antagonists', 'supporting_roles']:
                if key in char_design:
                    if key == 'protagonist' and isinstance(char_design[key], dict):
                        existing_names.add(char_design[key].get('name', ''))
                    elif isinstance(char_design[key], list):
                        for item in char_design[key]:
                            if isinstance(item, dict):
                                existing_names.add(item.get('name', ''))
                    elif isinstance(char_design[key], dict):
                        for stage, villains in char_design[key].items():
                            if isinstance(villains, list):
                                for v in villains:
                                    if isinstance(v, dict):
                                        existing_names.add(v.get('name', ''))
            
            # 添加新角色到 supporting_roles
            added_count = 0
            for char in new_characters:
                if not isinstance(char, dict):
                    continue
                
                char_name = char.get('name', '')
                if not char_name or char_name in existing_names:
                    continue
                
                # 构建角色数据
                char_data = {
                    'name': char_name,
                    'role': char.get('role', '配角'),
                    'identity': char.get('description', ''),
                    'traits': char.get('traits', []),
                    'first_appearance': char.get('first_chapter', char.get('intro_chapter', 0)),
                    'source': 'tactical_planning',
                    'created_at': datetime.now().isoformat(),
                    'notes': f'由战术规划生成，第{char.get("first_chapter", char.get("intro_chapter", 0))}章出场'
                }
                
                char_design['supporting_roles'].append(char_data)
                existing_names.add(char_name)
                added_count += 1
                logger.info(f"[TomatoTacticalSession] 新角色添加到角色设计: {char_name}")
            
            # 保存回文件
            if added_count > 0:
                with open(char_design_path, 'w', encoding='utf-8') as f:
                    json.dump(char_design, f, ensure_ascii=False, indent=2)
                logger.info(f"[TomatoTacticalSession] 角色设计文件已更新: 新增{added_count}个角色")
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 保存新角色失败: {e}")
    
    # ========== 辅助方法 ==========
    
    def _parse_json_response(self, response) -> Dict:
        """解析API返回的JSON"""
        try:
            if isinstance(response, dict):
                return response
            
            text = str(response)
            # 尝试提取JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            
            logger.warning("[TomatoTacticalSession] 无法从响应中提取JSON")
            return {}
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] JSON解析失败: {e}")
            return {}
    
    def _get_current_stage_goal(self) -> Dict:
        """获取当前阶段目标"""
        loader = PhaseOneDataLoader(self.project_path)
        return loader.get_current_stage_goal(self.start_chapter) or {}
    
    def _get_current_power_stage(self) -> str:
        """获取当前能力阶段描述"""
        try:
            progression = self.phase_one_data.get('progression_path', {})
            ability = progression.get('ability_system_progression', {})
            
            # 🔥 防御性处理：确保是字典类型
            early = ability.get('early_stage', {}) if isinstance(ability, dict) else {}
            if isinstance(early, str):
                early = {'mechanics': early, 'description': early}
            
            if self.start_chapter <= 30:
                mechanics = early.get('mechanics', '基础阶段') if isinstance(early, dict) else str(early) or '基础阶段'
                return f"1-30级（早期）: {mechanics}"
            
            mid = ability.get('mid_stage', {}) if isinstance(ability, dict) else {}
            if isinstance(mid, str):
                mid = {'mechanics': mid, 'description': mid}
            
            if self.start_chapter <= 80:
                mechanics = mid.get('mechanics', '成长阶段') if isinstance(mid, dict) else str(mid) or '成长阶段'
                return f"31-80级（中期）: {mechanics}"
            
            return "81级+（后期）: 巅峰阶段"
        except Exception as e:
            logger.warning(f"[_get_current_power_stage] 获取能力阶段失败: {e}")
            return "能力成长阶段"
    
    def _format_list(self, items: List) -> str:
        """格式化列表为字符串"""
        if not items:
            return "- 无"
        return "\n".join([f"- {item}" for item in items])
    
    def _format_simple_list(self, items: List) -> str:
        """格式化简单列表（对dict自动展开为Markdown列表项）"""
        if not items:
            return "无"
        lines = []
        for item in items[:10]:
            if isinstance(item, dict):
                # 将dict展开为可读的行内键值对
                pairs = [f"{k}={v}" for k, v in item.items()]
                lines.append("- " + " | ".join(pairs))
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)
    
    def _format_goal_milestones(self, milestones: dict) -> str:
        """格式化阶段目标里程碑（从嵌套dict转为Markdown列表）"""
        if not milestones:
            return "无"
        lines = []
        for k, v in milestones.items():
            if isinstance(v, dict):
                ch = v.get('chapter', '?')
                deliverable = v.get('deliverable', '')
                emotion = v.get('emotion', '')
                lines.append(f"- 第{ch}章: {deliverable} (情绪:{emotion})")
            else:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    
    def _format_milestones(self, milestones: List[Dict]) -> str:
        """格式化里程碑"""
        if not milestones:
            return "- 无"
        return "\n".join([
            f"- 第{m.get('chapter', '?')}: {m.get('event', '')[:50]}"
            for m in milestones
        ])
    
    def _parse_chapter_num(self, chapter_str) -> int:
        """解析章节号"""
        try:
            if isinstance(chapter_str, int):
                return chapter_str
            if isinstance(chapter_str, str):
                # 提取数字
                nums = re.findall(r'\d+', chapter_str)
                return int(nums[0]) if nums else 0
            return 0
        except:
            return 0
    
    def _validate_hooks(self, chapters: List[Dict]):
        """验证每章都有钩子"""
        for ch in chapters:
            ch_num = ch.get('chapter_number', '?')
            if not ch.get('hook_content'):
                logger.warning(f"[TomatoTacticalSession] 第{ch_num}章缺少钩子！")
    
    # ========== 默认输出 ==========
    
    def _get_default_core_framework(self) -> Dict:
        """获取默认核心框架"""
        return {
            'core_framework': {
                'world_building_chapters': [],
                'golden_finger_progression': [],
                'protagonist_moments': [],
                'goal_milestones': {},
                'key_constraints': ['使用默认框架，约束较少']
            }
        }
    
    def _get_default_emotion_plan(self) -> Dict:
        """获取默认情绪规划"""
        chapters = []
        for i in range(self.start_chapter, self.end_chapter + 1):
            chapters.append({
                'chapter_number': i,
                'emotion': '期待',
                'intensity': 7,
                'event': f'第{i}章事件（默认规划）',
                'hook_content': '章尾钩子（默认规划）',
                'assigned_characters': {'core': ['主角', '同伴'], 'major': [], 'minor': []}
            })
        return {'chapters': chapters}
    
    def _get_default_character_plan(self, existing_chars: List[Dict]) -> Dict:
        """获取默认角色规划（基于已有角色，无硬编码）"""
        # 从已有角色中提取主角作为核心
        protagonist = next((c for c in existing_chars if c.get('type') == 'protagonist'), None)
        core = [protagonist.get('name')] if protagonist else []
        
        # 提取盟友和反派作为主要角色
        major = [c.get('name') for c in existing_chars if c.get('type') in ['ally', 'villain']][:5]
        
        chapter_assignments = []
        for i in range(self.start_chapter, self.end_chapter + 1):
            chapter_assignments.append({
                'chapter': i,
                'core': core,
                'major': major if i % 5 == 0 else [],  # 每5章出一次重要配角
                'minor': []
            })
        
        return {
            'character_plan': {
                'core_characters': [{'name': '主角'}, {'name': '同伴'}],
                'major_characters': [],
                'minor_characters': [],
                'new_characters': [],
                'chapter_assignments': chapter_assignments,
                'constraints': ['使用默认规划']
            }
        }


# ========== 全局会话管理 ==========

_sessions: Dict[str, TomatoBestsellerTacticalSession] = {}

def create_tactical_session(
    project_path: Path,
    api_client=None,
    start_chapter: int = 1,
    end_chapter: int = 30,
    novel_title: str = "",
    emotion_curve: List[Dict] = None,
    sub_theme: str = None
) -> TomatoBestsellerTacticalSession:
    """
    创建新的番茄爆款细纲会话
    
    Args:
        project_path: 项目路径
        api_client: API客户端
        start_chapter: 开始章节
        end_chapter: 结束章节
        novel_title: 小说标题
        emotion_curve: 情绪曲线数据
        sub_theme: 子主题（如 investment_guru / livestream_tycoon / daily_checkin）
    
    Returns:
        TomatoBestsellerTacticalSession: 细纲会话实例
    """
    session_id = f"TAC-{start_chapter}-{end_chapter}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    session = TomatoBestsellerTacticalSession(
        session_id=session_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        project_path=project_path,
        api_client=api_client,
        novel_title=novel_title,
        emotion_curve=emotion_curve,
        sub_theme=sub_theme
    )
    
    _sessions[session_id] = session
    logger.info(f"[TomatoTacticalSession] 创建会话: {session_id} | 子主题: {sub_theme or 'auto-detect'}")
    
    return session

def get_tactical_session(session_id: str) -> Optional[TomatoBestsellerTacticalSession]:
    """获取已创建的会话"""
    return _sessions.get(session_id)
