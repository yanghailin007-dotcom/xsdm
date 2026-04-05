"""
阶段式章节生成器
按题材特定的阶段性节奏批量生成
每个阶段创建一个独立对话会话

节奏参数从爆款分析中获取：
- stage_climax_interval: 阶段性高潮间隔（如：30章/50章/100章）
- small_climax_interval: 小高潮间隔（如：3章）
- medium_climax_interval: 中高潮间隔（如：10章）
- large_climax_interval: 大高潮间隔（如：20章）
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StageChapterGenerator:
    """
    阶段式章节生成器
    
    设计原则：
    1. 按题材特定的"阶段性节奏"划分（从爆款分析获取）
    2. 每个阶段创建独立对话会话
    3. 会话system_prompt包含完整一阶段设定+本阶段详细规划
    
    阶段划分基于爆款分析中的stage_rhythm：
    - stage_climax_chapters: 阶段性高潮章节列表
    - 如果没有提供，使用默认的30章周期
    
    示例（100章小说，默认30章周期）：
    - 阶段1：第1-30章 - 系统觉醒，第一次大高潮
    - 阶段2：第31-60章 - 快速发展，第二次大高潮  
    - 阶段3：第61-90章 - 终极对决，最大高潮
    - 阶段4：第91-100章 - 结局收尾
    """
    
    # JSON配置文件路径
    DEFAULT_PROMPT_PACKAGE = "default"
    PROMPT_BASE_DIR = "prompt_packages"
    
    def __init__(self, api_client, novel_data: Dict, tropes: Dict, prompt_package: Optional[str] = None):
        self.api_client = api_client
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            import logging
            logging.warning(f"[StageChapterGenerator] novel_data 是列表类型，转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            import logging
            logging.warning(f"[StageChapterGenerator] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.tropes = tropes
        
        # 使用的prompt包名称
        self.prompt_package = prompt_package or self.DEFAULT_PROMPT_PACKAGE
        
        # 加载prompt配置（支持从JSON加载，失败则使用内置模板）
        self._stage_system_prompt_config = self._load_prompt_config("stage_system_prompt.json")
        self._chapter_prompt_config = self._load_prompt_config("chapter_prompt_template.json")
        
        # 提取基本信息
        self.novel_title = novel_data.get('title', '未命名')
        self.total_chapters = novel_data.get('chapters', 100)
        
        # 生成器ID
        import uuid
        self.generator_id = f"STAGE-{uuid.uuid4().hex[:8].upper()}"
        
        # 当前会话
        self.current_session = None
        self.current_stage = None
    
    def _get_prompt_config_path(self, filename: str) -> str:
        """获取prompt配置文件路径"""
        return os.path.join(
            self.PROMPT_BASE_DIR,
            self.prompt_package,
            "market_driven",
            "phase_two",
            filename
        )
    
    def _load_prompt_config(self, filename: str) -> Optional[Dict]:
        """
        从JSON文件加载prompt配置
        
        Returns:
            配置字典，如果加载失败则返回None（使用内置模板）
        """
        config_path = self._get_prompt_config_path(filename)
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"[StageChapterGenerator] 成功加载prompt配置: {config_path}")
                return config
            else:
                logger.warning(f"[StageChapterGenerator] Prompt配置文件不存在: {config_path}，将使用内置模板")
                return None
        except Exception as e:
            logger.warning(f"[StageChapterGenerator] 加载prompt配置失败: {e}，将使用内置模板")
            return None
    
    def _render_template(self, template: str, variables: Dict, defaults: Optional[Dict] = None) -> str:
        """
        渲染模板字符串，替换变量
        
        Args:
            template: 模板字符串
            variables: 变量字典
            defaults: 默认值字典
        
        Returns:
            渲染后的字符串
        """
        result = template
        
        # 合并默认值和实际值
        merged = {}
        if defaults:
            merged.update(defaults)
        merged.update(variables)
        
        # 替换变量
        for key, value in merged.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                # 处理不同类型的值
                if isinstance(value, (dict, list)):
                    result = result.replace(placeholder, json.dumps(value, ensure_ascii=False, indent=2))
                else:
                    result = result.replace(placeholder, str(value))
        
        return result
        
    def calculate_stages(self) -> List[Dict]:
        """
        计算阶段划分 - 基于题材分析的阶段性节奏
        
        从爆款分析中获取该题材特定的阶段性节奏：
        - stage_climax_interval: 阶段性大高潮间隔（如：30章/50章/100章）
        - stage_climax_chapters: 具体的阶段性高潮章节列表
        - stage_climax_types: 每个阶段性高潮的类型描述
        
        如果爆款分析中没有节奏信息，则使用默认的30章周期。
        """
        stages = []
        
        # 从爆款分析中获取阶段性节奏
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        stage_climax_chapters = stage_rhythm.get('stage_climax_chapters', [])
        stage_climax_types = stage_rhythm.get('stage_climax_types', [])
        stage_interval = stage_rhythm.get('stage_climax_interval', 30)
        
        # 如果有具体的阶段性高潮章节列表，按此划分
        if stage_climax_chapters and len(stage_climax_chapters) > 0:
            prev_ch = 0
            for i, climax_ch in enumerate(stage_climax_chapters):
                if climax_ch > self.total_chapters:
                    break
                    
                start_ch = prev_ch + 1
                end_ch = min(climax_ch, self.total_chapters)
                
                # 获取该阶段的高潮类型描述
                climax_type = stage_climax_types[i] if i < len(stage_climax_types) else f"第{i+1}次阶段性高潮"
                
                stages.append({
                    "stage_number": i + 1,
                    "name": self._get_stage_name(i, stage_rhythm),
                    "start_chapter": start_ch,
                    "end_chapter": end_ch,
                    "theme": self._get_stage_theme(i, stage_rhythm),
                    "climax_chapter": end_ch,
                    "climax_type": climax_type,
                    "outline": self._generate_stage_outline(start_ch, end_ch, stage_rhythm)
                })
                
                prev_ch = end_ch
            
            # 如果还有剩余章节，添加最终阶段
            if prev_ch < self.total_chapters:
                stages.append({
                    "stage_number": len(stages) + 1,
                    "name": "最终阶段：圆满落幕",
                    "start_chapter": prev_ch + 1,
                    "end_chapter": self.total_chapters,
                    "theme": "结局收尾，最终高潮",
                    "climax_chapter": self.total_chapters,
                    "climax_type": "最终大高潮",
                    "outline": self._generate_stage_outline(prev_ch + 1, self.total_chapters, stage_rhythm, is_final=True)
                })
        else:
            # 使用默认的阶段性节奏（每30章一个阶段）
            stages = self._calculate_default_stages(stage_interval)
        
        return stages
    
    def _calculate_default_stages(self, interval: int = 30) -> List[Dict]:
        """使用默认节奏计算阶段（当爆款分析中没有节奏信息时）"""
        stages = []
        
        full_cycles = self.total_chapters // interval
        remainder = self.total_chapters % interval
        
        cycle_names = [
            "第一周期：崭露头角",
            "第二周期：快速发展", 
            "第三周期：声名鹊起",
            "第四周期：登顶巅峰"
        ]
        
        for i in range(full_cycles):
            start_ch = i * interval + 1
            end_ch = (i + 1) * interval
            
            stages.append({
                "stage_number": i + 1,
                "name": cycle_names[min(i, len(cycle_names) - 1)],
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "theme": self._get_cycle_theme(i),
                "climax_chapter": end_ch,
                "climax_type": f"第{i+1}次阶段性总结高潮",
                "outline": self._generate_stage_outline(start_ch, end_ch, {})
            })
        
        if remainder > 0:
            start_ch = full_cycles * interval + 1
            end_ch = self.total_chapters
            
            stages.append({
                "stage_number": full_cycles + 1,
                "name": "最终周期：圆满落幕",
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "theme": "结局收尾，最终高潮",
                "climax_chapter": end_ch,
                "climax_type": "最终大高潮",
                "outline": self._generate_stage_outline(start_ch, end_ch, {}, is_final=True)
            })
        
        return stages
    
    def _get_stage_name(self, stage_index: int, stage_rhythm: Dict) -> str:
        """获取阶段名称"""
        # 尝试从stage_rhythm中获取
        if 'stage_names' in stage_rhythm and stage_index < len(stage_rhythm['stage_names']):
            return stage_rhythm['stage_names'][stage_index]
        
        # 默认命名
        default_names = [
            "第一周期：崭露头角",
            "第二周期：快速发展", 
            "第三周期：声名鹊起",
            "第四周期：登顶巅峰"
        ]
        return default_names[min(stage_index, len(default_names) - 1)]
    
    def _get_stage_theme(self, stage_index: int, stage_rhythm: Dict) -> str:
        """获取阶段主题"""
        # 尝试从stage_rhythm中获取
        if 'stage_themes' in stage_rhythm and stage_index < len(stage_rhythm['stage_themes']):
            return stage_rhythm['stage_themes'][stage_index]
        
        # 根据早期/中期/后期返回不同主题
        early = stage_rhythm.get('early_stage', {})
        mid = stage_rhythm.get('mid_stage', {})
        late = stage_rhythm.get('late_stage', {})
        
        if stage_index == 0:
            return early.get('rhythm', '初入江湖，建立根基')
        elif stage_index == 1:
            return mid.get('rhythm', '快速发展，势力扩张')
        else:
            return late.get('rhythm', '登顶巅峰，制定规则')
    
    def _get_cycle_theme(self, cycle_index: int) -> str:
        """获取周期主题"""
        themes = [
            "初入江湖，建立根基",
            "快速发展，势力扩张",
            "名震一方，格局打开",
            "登顶巅峰，制定规则"
        ]
        return themes[min(cycle_index, len(themes) - 1)]
    
    def _generate_stage_outline(self, start: int, end: int, stage_rhythm: Dict, is_final: bool = False) -> List[Dict]:
        """
        生成阶段大纲 - 基于题材特定的阶段性节奏
        
        从stage_rhythm中获取该题材的节奏规律：
        - small_climax_interval: 小高潮间隔（默认3章）
        - medium_climax_interval: 中高潮间隔（默认10章）
        - large_climax_interval: 大高潮间隔（默认20章）
        """
        outline = []
        stage_length = end - start + 1
        
        # 获取节奏参数（带默认值）
        small_interval = stage_rhythm.get('small_climax_interval', 3)
        medium_interval = stage_rhythm.get('medium_climax_interval', 10)
        large_interval = stage_rhythm.get('large_climax_interval', 20)
        
        # 节奏标签映射
        rhythm_labels = stage_rhythm.get('rhythm_labels', {
            '3': '3章一小爽',
            '10': '10章一中爽',
            '20': '20章一大爽',
            '30': '阶段高潮'
        })
        
        for ch in range(start, end + 1):
            relative_ch = ch - start + 1  # 阶段内章节号
            
            # 章节1：开局
            if relative_ch == 1:
                outline.append({
                    "chapter": ch, 
                    "type": "开局", 
                    "emotion": "期待",
                    "event": "新阶段开始，设定目标",
                    "rhythm": "阶段开局"
                })
            # 大高潮（如第20章）
            elif relative_ch == large_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "大高潮", 
                    "emotion": "大爽快",
                    "event": "重大转折，实力飞跃",
                    "rhythm": rhythm_labels.get(str(large_interval), f"{large_interval}章一大爽")
                })
            # 中高潮（如第10章）
            elif relative_ch == medium_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "中高潮", 
                    "emotion": "爽快",
                    "event": "获得资源/身份升级",
                    "rhythm": rhythm_labels.get(str(medium_interval), f"{medium_interval}章一中爽")
                })
            # 小高潮（如第3章）
            elif relative_ch == small_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "小高潮", 
                    "emotion": "小爽快",
                    "event": "第一次打脸，立威",
                    "rhythm": rhythm_labels.get(str(small_interval), f"{small_interval}章一小爽")
                })
            # 阶段最终章
            elif ch == end:
                if is_final:
                    outline.append({
                        "chapter": ch, 
                        "type": "最终高潮", 
                        "emotion": "爆发+满足",
                        "event": "最终决战，圆满结局",
                        "rhythm": "最终高潮"
                    })
                else:
                    outline.append({
                        "chapter": ch, 
                        "type": "阶段高潮", 
                        "emotion": "爆发+期待",
                        "event": "阶段性总结，开启新周期",
                        "rhythm": "阶段高潮"
                    })
            # 其他节奏点（如其他3的倍数）
            elif relative_ch % small_interval == 0:
                outline.append({
                    "chapter": ch, 
                    "type": "小爽点", 
                    "emotion": "爽快",
                    "event": "日常打脸/收获",
                    "rhythm": f"{small_interval}章节奏"
                })
            else:
                outline.append({
                    "chapter": ch, 
                    "type": "推进", 
                    "emotion": "期待",
                    "event": "剧情推进，蓄势",
                    "rhythm": "铺垫"
                })
        
        return outline
    

    
    def _get_outline_first_30(self) -> List[Dict]:
        """获取前30章大纲"""
        plan = self.novel_data.get('plan', {})
        return plan.get('outline_first_30', [])
    
    def _infer_stage_outline(self, start: int, end: int, stage_type: str) -> List[Dict]:
        """
        推断阶段大纲（基于套路模板）
        """
        outline = []
        
        # 节奏模板
        if stage_type == "承":
            # 发展阶段：每10章一个小高潮
            for ch in range(start, end + 1):
                pos = (ch - start) % 10
                if pos == 0:
                    outline.append({"chapter": ch, "type": "小高潮", "emotion": "爽快"})
                elif pos == 5:
                    outline.append({"chapter": ch, "type": "中高潮", "emotion": "震惊"})
                else:
                    outline.append({"chapter": ch, "type": "推进", "emotion": "期待"})
        
        elif stage_type == "转":
            # 高潮阶段：紧张升级
            for ch in range(start, end + 1):
                pos = (ch - start) % 10
                if pos == 0:
                    outline.append({"chapter": ch, "type": "大高潮", "emotion": "爆发"})
                else:
                    outline.append({"chapter": ch, "type": "紧张", "emotion": "危机"})
        
        else:  # 合
            # 结局阶段：满足收尾
            for ch in range(start, end + 1):
                if ch == end:
                    outline.append({"chapter": ch, "type": "结局", "emotion": "满足"})
                else:
                    outline.append({"chapter": ch, "type": "收尾", "emotion": "温馨"})
        
        return outline
    
    def generate_stage(self, stage: Dict, progress_callback=None) -> List[Dict]:
        """
        生成单个阶段的章节
        
        Args:
            stage: 阶段信息（包含start_chapter, end_chapter等）
            progress_callback: 进度回调(chapter_num, total)
        
        Returns:
            生成的章节列表
        """
        stage_num = stage['stage_number']
        start_ch = stage['start_chapter']
        end_ch = stage['end_chapter']
        total = end_ch - start_ch + 1
        
        logger.info(f"[阶段生成 {self.generator_id}] 开始生成阶段{stage_num}: 第{start_ch}-{end_ch}章 | {stage['name']}")
        
        # 创建新会话（每个阶段独立会话）
        self.current_stage = stage
        self.current_session = self._create_stage_session(stage)
        
        chapters = []
        prev_summary = ""
        
        for i, ch_num in enumerate(range(start_ch, end_ch + 1)):
            logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage_num} 第{ch_num}章 ({i+1}/{total})")
            
            try:
                chapter = self._generate_chapter_in_session(
                    chapter_num=ch_num,
                    stage=stage,
                    prev_summary=prev_summary
                )
                
                chapters.append(chapter)
                prev_summary = self._summarize_chapter(chapter)
                
                if progress_callback:
                    progress_callback(ch_num, self.total_chapters)
                
            except Exception as e:
                logger.error(f"[阶段生成 {self.generator_id}] 第{ch_num}章失败: {e}")
                chapters.append(self._create_error_chapter(ch_num, e))
        
        logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage_num}完成 | 成功: {len([c for c in chapters if c.get('word_count', 0) > 0])}/{total}")
        return chapters
    
    def _create_stage_session(self, stage: Dict) -> 'ConversationSession':
        """
        创建阶段会话
        system_prompt包含完整一阶段设定+本阶段详细规划
        """
        from src.core.APIClient import ConversationSession
        
        system_prompt = self._build_stage_system_prompt(stage)
        
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=self.api_client.default_provider,
            purpose_prefix=f"STAGE-{self.generator_id}-{stage['stage_number']}"
        )
        session.max_history = 50
        
        logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage['stage_number']}会话创建 | 历史限制: 50")
        return session
    
    def _build_stage_system_prompt(self, stage: Dict) -> str:
        """
        构建阶段系统提示词
        包含：
        1. 完整一阶段设定（世界观、角色、成长路线）
        2. 本阶段详细规划（本阶段大纲、高潮设计）
        
        注意：使用从爆款分析中提取的题材特定节奏参数
        """
        # 如果成功加载了JSON配置，使用模板渲染
        if self._stage_system_prompt_config and self._stage_system_prompt_config.get('template'):
            return self._build_stage_system_prompt_from_template(stage)
        
        # 🔥 配置缺失时抛出错误，强制用户配置
        error_msg = """
❌ 错误：阶段系统提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/phase_two/stage_system_prompt.json

或使用API创建配置：
POST /api/v2/prompt-config/component/stage_system_prompt

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _build_stage_system_prompt_from_template(self, stage: Dict) -> str:
        """使用JSON模板构建阶段系统提示词"""
        config = self._stage_system_prompt_config
        template = config['template']
        defaults = config.get('defaults', {})
        
        # 一阶段完整设定
        worldview = self.novel_data.get('core_worldview', {})
        faction_system = self.novel_data.get('faction_system', {})
        char_design = self.novel_data.get('character_design', {})
        growth_plan = self.novel_data.get('global_growth_plan', {})
        emotion_curve = self.novel_data.get('emotion_curve', [])
        
        # 本阶段规划
        stage_outline = stage.get('outline', [])
        
        # 获取主角当前阶段能力
        protagonist_current = self._get_protagonist_stage_status(stage)
        
        # 从爆款分析中获取节奏参数
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        small_interval = stage_rhythm.get('small_climax_interval', defaults.get('small_interval', 3))
        medium_interval = stage_rhythm.get('medium_climax_interval', defaults.get('medium_interval', 10))
        large_interval = stage_rhythm.get('large_climax_interval', defaults.get('large_interval', 20))
        rhythm_description = stage_rhythm.get('description', defaults.get('rhythm_description', '每30章一个完整周期'))
        
        # 计算节奏节点
        small_climax = stage['start_chapter'] + small_interval - 1
        medium_climax = stage['start_chapter'] + medium_interval - 1
        large_climax = stage['start_chapter'] + large_interval - 1
        stage_climax = stage['end_chapter']
        
        # 构建变量字典
        variables = {
            'novel_title': self.novel_title,
            'stage_name': stage['name'],
            'stage_number': stage['stage_number'],
            'start_chapter': stage['start_chapter'],
            'end_chapter': stage['end_chapter'],
            'worldview': worldview,
            'faction_system': faction_system,
            'char_design': char_design,
            'growth_plan': growth_plan,
            'stage_theme': stage['theme'],
            'climax_chapter': stage['climax_chapter'],
            'climax_type': stage['climax_type'],
            'rhythm_description': rhythm_description,
            'small_interval': small_interval,
            'medium_interval': medium_interval,
            'large_interval': large_interval,
            'protagonist_status': protagonist_current,
            'stage_outline': stage_outline,
            'small_climax': small_climax,
            'medium_climax': medium_climax,
            'large_climax': large_climax,
            'stage_climax': stage_climax
        }
        
        return self._render_template(template, variables, defaults)
    
    def _get_protagonist_stage_status(self, stage: Dict) -> Dict:
        """获取主角当前阶段状态 - 基于周期升级"""
        stage_num = stage['stage_number']
        
        # 从爆款分析中获取节奏参数
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        small_interval = stage_rhythm.get('small_climax_interval', 3)
        medium_interval = stage_rhythm.get('medium_climax_interval', 10)
        large_interval = stage_rhythm.get('large_climax_interval', 20)
        
        # 根据周期返回对应能力状态
        ability_levels = [
            "初入江湖，小有所成",
            "一方豪杰，声名鹊起", 
            "名震一方，实力强横",
            "天下闻名，无敌之姿"
        ]
        
        growth_goals = [
            "完成第一阶段目标，建立根基",
            "完成第二阶段目标，势力扩张",
            "完成第三阶段目标，格局打开",
            "完成最终阶段，登顶巅峰"
        ]
        
        # 计算节奏节点
        small_climax = stage['start_chapter'] + small_interval - 1
        medium_climax = stage['start_chapter'] + medium_interval - 1
        large_climax = stage['start_chapter'] + large_interval - 1
        
        return {
            "current_stage": f"第{stage_num}阶段",
            "ability_level": ability_levels[min(stage_num - 1, 3)],
            "stage_goal": growth_goals[min(stage_num - 1, 3)],
            "milestones": [
                f"第{stage['start_chapter']}章：阶段开始，设定目标",
                f"第{small_climax}章：第一次小高潮（打脸）",
                f"第{medium_climax}章：第一次中高潮（资源）",
                f"第{large_climax}章：第一次大高潮（升级）",
                f"第{stage['end_chapter']}章：阶段性总结高潮"
            ]
        }
    
    def _parse_response(self, response) -> Dict:
        """
        解析响应，返回包含 title 和 content 的字典
        支持分隔符格式(---标题---/---正文---)和JSON格式
        """
        import re
        
        result = {'title': '', 'content': ''}
        
        if isinstance(response, dict):
            result['title'] = response.get('title', '')
            result['content'] = response.get('content', str(response))
        elif isinstance(response, str):
            cleaned_response = response.strip()
            
            # 策略1: 尝试解析分隔符格式 ---标题---/---正文---
            title_match = re.search(r'---\s*[标標][题題]\s*---\s*\n?(.*?)\n?---\s*[正正][文文]\s*---', cleaned_response, re.DOTALL | re.IGNORECASE)
            if title_match:
                result['title'] = title_match.group(1).strip()
                # 正文在 ---正文--- 之后
                content_start = cleaned_response.find('---正文---') + len('---正文---')
                if content_start < len('---正文---') + 10:
                    content_start = cleaned_response.find('---正文---') + len('---正文---')
                result['content'] = cleaned_response[content_start:].strip()
                logger.info(f"[StageGenerator] 使用分隔符格式解析,标题: '{result['title']}'")
                return self._clean_result(result)
            
            # 策略2: 移除 Markdown 代码块后尝试解析 JSON
            json_content = cleaned_response
            if json_content.startswith('```'):
                first_newline = json_content.find('\n')
                if first_newline != -1:
                    json_content = json_content[first_newline:].strip()
                if json_content.endswith('```'):
                    json_content = json_content[:-3].strip()
            
            try:
                parsed = json.loads(json_content)
                if isinstance(parsed, dict):
                    result['title'] = parsed.get('title', '')
                    result['content'] = parsed.get('content', cleaned_response)
                    logger.info(f"[StageGenerator] 使用JSON格式解析,标题: '{result['title']}'")
                else:
                    result['content'] = cleaned_response
            except:
                # JSON 解析失败，使用清理后的内容
                result['content'] = cleaned_response
                
                # 尝试从纯文本中提取标题
                lines = cleaned_response.split('\n')
                for line in lines[:5]:
                    line = line.strip()
                    if line and 4 <= len(line) <= 20:
                        if not line.startswith('第') and '章' not in line and not line.startswith('【'):
                            result['title'] = line
                            break
        else:
            result['content'] = str(response)
        
        return self._clean_result(result)
    
    def _clean_result(self, result: Dict) -> Dict:
        """清理结果中的标题行"""
        import re
        if result['content']:
            title_patterns = [
                r'^第[一二三四五六七八九十百千万零\d]+章[：:\s]*[^\n]*\n*',
                r'^Chapter\s*\d+[：:\s]*[^\n]*\n*',
            ]
            for pattern in title_patterns:
                result['content'] = re.sub(pattern, '', result['content'], flags=re.IGNORECASE)
            result['content'] = result['content'].lstrip('\n')
        return result
    
    def _generate_chapter_in_session(self, chapter_num: int, stage: Dict, prev_summary: str) -> Dict:
        """在会话中生成单章"""
        # 获取本章大纲
        chapter_outline = self._get_chapter_outline(chapter_num, stage)
        
        # 构建提示词
        prompt = self._build_chapter_prompt(chapter_num, stage, chapter_outline, prev_summary)
        
        # 添加分隔符格式要求
        prompt += """

## 【强制输出格式 - 使用分隔符】
必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：

---标题---
章节标题（8-14字，不要'第X章'前缀）
---正文---
章节正文内容（2000-2500字，直接从场景开始）

⚠️ **重要警告**：
- 必须严格按照上述分隔符格式返回
- 标题只放在---标题---后面，不要重复放在正文里
- 正文开头绝对禁止写"第X章：XXX"
"""
        
        # 发送消息
        logger.info(f"[阶段生成 {self.generator_id}] 发送第{chapter_num}章提示词 | 历史: {len(self.current_session.messages)}条")
        response = self.current_session.send_message(prompt, temperature=0.7)
        logger.info(f"[阶段生成 {self.generator_id}] 接收第{chapter_num}章响应 | 轮次: {self.current_session.turn_count}")
        
        # 🔥 解析JSON响应
        parsed = self._parse_response(response)
        title = parsed.get('title', '')
        content = parsed.get('content', '')
        
        return {
            "chapter_number": chapter_num,
            "title": title or self._extract_title(content, chapter_outline),
            "content": content,
            "word_count": len(content),
            "stage": stage['stage_number'],
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_chapter_outline(self, chapter_num: int, stage: Dict) -> Dict:
        """获取本章大纲"""
        for item in stage.get('outline', []):
            if item.get('chapter') == chapter_num:
                return item
        return {"chapter": chapter_num, "type": "推进", "emotion": "期待"}
    
    def _build_chapter_prompt(self, chapter_num: int, stage: Dict, outline: Dict, prev_summary: str) -> str:
        """构建章节提示词"""
        if not self._chapter_prompt_config or not self._chapter_prompt_config.get('template_parts'):
            raise ValueError("[StageGenerator] chapter_prompt_config 未加载，请检查配置文件")
        return self._build_chapter_prompt_from_template(chapter_num, stage, outline, prev_summary)
    
    def _build_chapter_prompt_from_template(self, chapter_num: int, stage: Dict, outline: Dict, prev_summary: str) -> str:
        """使用JSON模板构建章节提示词"""
        config = self._chapter_prompt_config
        parts = config['template_parts']
        defaults = config.get('defaults', {})
        climax_rules = config.get('climax_rules', {})
        
        relative_ch = chapter_num - stage['start_chapter'] + 1
        climax_ch = stage['end_chapter']
        chapters_to_climax = climax_ch - chapter_num
        
        # 获取本章类型和情绪（使用默认值）
        chapter_type = outline.get('type', defaults.get('chapter_type', '推进'))
        emotion = outline.get('emotion', defaults.get('emotion', '期待'))
        rhythm = outline.get('rhythm', defaults.get('rhythm', ''))
        event = outline.get('event', defaults.get('event', ''))
        
        # 构建基础变量
        variables = {
            'chapter_num': chapter_num,
            'stage_number': stage['stage_number'],
            'relative_ch': relative_ch,
            'stage_name': stage['name'],
            'chapter_type': chapter_type,
            'emotion': emotion,
            'rhythm': rhythm,
            'event': event,
            'climax_type': stage.get('climax_type', ''),
            'chapters_to_climax': chapters_to_climax,
            'prev_summary': (prev_summary[:300] + "...") if prev_summary else "",
            'climax_ch': climax_ch
        }
        
        # 渲染各部分
        result_parts = []
        
        # Header
        result_parts.append(self._render_template(parts['header'], variables, defaults))
        
        # 本章定位
        positioning_lines = parts['chapter_positioning']
        for line in positioning_lines:
            result_parts.append(self._render_template(line, variables, defaults))
        
        # 节奏节点（如果有）
        if rhythm:
            result_parts.append(self._render_template(parts['rhythm_info'], variables, defaults))
        
        # 核心事件（如果有）
        if event:
            result_parts.append(self._render_template(parts['event_info'], variables, defaults))
        
        # 高潮提示
        climax_indicators = parts['climax_indicators']
        
        # 根据条件添加高潮提示
        if chapter_num == climax_ch:
            # 周期高潮
            for line in climax_indicators['final_climax']:
                result_parts.append(self._render_template(line, variables, defaults))
        elif chapters_to_climax == 5:
            for line in climax_indicators['countdown_5']:
                result_parts.append(self._render_template(line, variables, defaults))
        elif chapters_to_climax == 10:
            for line in climax_indicators['countdown_10']:
                result_parts.append(self._render_template(line, variables, defaults))
        elif chapter_type == '小高潮':
            for line in climax_indicators['small_climax']:
                result_parts.append(self._render_template(line, variables, defaults))
        elif chapter_type == '中高潮':
            for line in climax_indicators['medium_climax']:
                result_parts.append(self._render_template(line, variables, defaults))
        elif chapter_type == '大高潮':
            for line in climax_indicators['large_climax']:
                result_parts.append(self._render_template(line, variables, defaults))
        
        # 前文摘要
        if prev_summary:
            for line in parts['previous_summary']:
                result_parts.append(self._render_template(line, variables, defaults))
        
        # 写作要求
        for line in parts['writing_requirements']:
            result_parts.append(self._render_template(line, variables, defaults))
        
        return "\n".join(result_parts)
    
    def _extract_title(self, content: str, outline: Dict) -> str:
        """
        提取或生成章节标题
        
        策略：
        1. 优先从outline获取（战术规划中定义的标题）
        2. 其次从outline的event/purpose字段生成
        """
        # 1. 优先从outline获取标题
        if outline:
            # 直接标题字段
            title = outline.get('title', '').strip()
            if title and title != '章节' and not title.startswith('第'):
                return title
            
            # 从event字段生成（事件描述通常是核心剧情）
            event = outline.get('event', '').strip()
            if event and len(event) <= 30:
                return event
            elif event:
                return event[:20] + ('...' if len(event) > 20 else '')
            
            # 从purpose字段生成（战术企图）
            purpose = outline.get('purpose', '').strip()
            if purpose and len(purpose) <= 30:
                return purpose
            elif purpose:
                return purpose[:20] + ('...' if len(purpose) > 20 else '')
        
        # 2. 默认标题
        chapter_num = outline.get('chapter', 0) if outline else 0
        return f"第{chapter_num}章"
    
    def _summarize_chapter(self, chapter: Dict) -> str:
        """章节摘要"""
        content = chapter.get('content', '')
        return content[:200] + "..." if len(content) > 200 else content
    
    def _create_error_chapter(self, chapter_num: int, error: Exception) -> Dict:
        """创建错误章节记录"""
        return {
            "chapter_number": chapter_num,
            "title": f"第{chapter_num}章（生成失败）",
            "content": f"生成失败: {str(error)}",
            "word_count": 0,
            "error": str(error)
        }


# 便捷函数
def generate_by_stages(api_client, novel_data: Dict, tropes: Dict, prompt_package: Optional[str] = None,
                       progress_callback=None) -> Dict[int, List[Dict]]:
    """
    按阶段生成所有章节
    
    Args:
        api_client: API客户端
        novel_data: 小说数据
        tropes: 爆款分析数据
        prompt_package: 使用的prompt包名称（默认"default"）
        progress_callback: 进度回调
    
    Returns:
        Dict[阶段号, 章节列表]
    """
    generator = StageChapterGenerator(api_client, novel_data, tropes, prompt_package)
    
    # 计算阶段
    stages = generator.calculate_stages()
    logger.info(f"[阶段生成] 共划分{len(stages)}个阶段")
    
    # 逐个阶段生成
    all_chapters = {}
    for stage in stages:
        chapters = generator.generate_stage(stage, progress_callback)
        all_chapters[stage['stage_number']] = chapters
    
    return all_chapters
