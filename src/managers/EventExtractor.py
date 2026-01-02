"""
通用事件提取器 - 从小说数据中提取重大事件和中级事件

支持多种数据格式和路径：
- quality_data.writing_plans (新格式)
- stage_writing_plans (旧格式)
- 产物文件格式
"""

from typing import Dict, List, Optional, Any
import json
from src.utils.logger import get_logger


class EventExtractor:
    """通用事件提取器"""
    
    def __init__(self, logger_instance=None):
        self.logger = logger_instance or get_logger("EventExtractor")
    
    def extract_all_major_events(self, novel_data: Dict) -> List[Dict]:
        """
        提取所有重大事件
        
        支持多种数据格式：
        1. quality_data.writing_plans (新格式)
        2. stage_writing_plans (中间格式)
        3. 直接从项目文件读取 (旧格式: _stage_writing_plan.json)
        
        Args:
            novel_data: 小说数据字典
            
        Returns:
            重大事件列表（已按章节排序）
        """
        all_events = []
        
        # 1. 首先尝试从 quality_data.writing_plans 获取
        quality_data = novel_data.get("quality_data", {})
        writing_plans = quality_data.get("writing_plans", {})
        
        self.logger.info(f"📊 [EventExtractor] quality_data 存在: {bool(quality_data)}")
        self.logger.info(f"📊 [EventExtractor] writing_plans 键: {list(writing_plans.keys()) if writing_plans else '无'}")
        
        if writing_plans:
            # 遍历所有写作计划
            for stage_name, plan_data in writing_plans.items():
                if not isinstance(plan_data, dict):
                    continue
                
                self.logger.info(f"📊 [EventExtractor] 处理阶段: {stage_name}")
                self.logger.info(f"📊 [EventExtractor] plan_data 键: {list(plan_data.keys())}")
                
                # 尝试从多个可能的位置提取事件
                events = (
                    plan_data.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []) or
                    plan_data.get('event_system', {}).get('major_events', []) or
                    plan_data.get('major_events', [])
                )
                
                self.logger.info(f"📊 [EventExtractor] 从 {stage_name} 提取到 {len(events)} 个重大事件")
                
                # 为每个事件添加元数据
                for event in events:
                    self._enrich_event_metadata(event, stage_name)
                    all_events.append(event)
        else:
            # 2. 🔥 新增：尝试从 stage_writing_plans 获取（中间格式）
            stage_writing_plans = novel_data.get("stage_writing_plans", {})
            
            if stage_writing_plans:
                self.logger.info(f"📊 [EventExtractor] 从 stage_writing_plans 提取")
                self.logger.info(f"📊 [EventExtractor] stage_writing_plans 键: {list(stage_writing_plans.keys())}")
                
                for stage_name, stage_data in stage_writing_plans.items():
                    if not isinstance(stage_data, dict):
                        continue
                    
                    # 尝试从多个可能的位置提取事件
                    events = (
                        stage_data.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []) or
                        stage_data.get('event_system', {}).get('major_events', []) or
                        stage_data.get('major_events', [])
                    )
                    
                    self.logger.info(f"📊 [EventExtractor] 从 {stage_name} 提取到 {len(events)} 个重大事件")
                    
                    # 为每个事件添加元数据
                    for event in events:
                        self._enrich_event_metadata(event, stage_name)
                        all_events.append(event)
            else:
                # 3. 🔥 最后尝试：直接从项目文件读取旧格式的 writing_plan
                title = novel_data.get("novel_title", "") or novel_data.get("title", "")
                if not title:
                    self.logger.warn("⚠️ 无法确定项目标题，跳过直接文件读取")
                else:
                    all_events = self._extract_from_project_files(title, novel_data)
        
        # 按章节排序
        all_events.sort(key=lambda x: x.get("_start_chapter", 0))
        
        self.logger.info(f"✅ [EventExtractor] 总共提取到 {len(all_events)} 个重大事件")
        return all_events
    
    def _extract_from_project_files(self, title: str, novel_data: Dict) -> List[Dict]:
        """
        直接从项目文件读取旧格式的写作计划
        
        旧格式：吞噬万界：从一把生锈铁剑开始_开局_stage_writing_plan.json
        
        Args:
            title: 小说标题
            novel_data: 小说数据
            
        Returns:
            重大事件列表
        """
        import re
        from pathlib import Path
        
        all_events = []
        
        # 清理标题中的特殊字符
        safe_title = re.sub(r'[\\/*?"<>|]', "_", title)
        
        # 检查多个可能的路径
        project_paths = [
            Path("小说项目") / safe_title / "planning",
            Path("小说项目") / title / "planning",
        ]
        
        for project_path in project_paths:
            if not project_path.exists():
                continue
            
            self.logger.info(f"🔍 [EventExtractor] 检查路径: {project_path}")
            
            # 查找所有 stage_writing_plan 文件
            plan_files = list(project_path.glob("*_stage_writing_plan.json"))
            
            if plan_files:
                self.logger.info(f"✅ [EventExtractor] 找到 {len(plan_files)} 个写作计划文件")
                
                # 按阶段顺序排序文件
                def get_stage_order(filename):
                    match = re.search(r'_(.+?)_stage_writing_plan\.json$', filename)
                    if match:
                        stage = match.group(1)
                        stage_order_map = {
                            "opening_stage": 0,
                            "development_stage": 1,
                            "climax_stage": 2,
                            "ending_stage": 3
                        }
                        return stage_order_map.get(stage, 99)
                    return 99
                
                plan_files.sort(key=get_stage_order)
                
                # 读取每个阶段的文件
                for plan_file in plan_files:
                    try:
                        with open(plan_file, 'r', encoding='utf-8') as f:
                            plan_data = json.load(f)
                        
                        # 提取阶段名称
                        match = re.search(r'_(.+?)_stage_writing_plan\.json$', plan_file.name)
                        stage_name = match.group(1) if match else "unknown"
                        
                        # 提取事件
                        events = plan_data.get("event_system", {}).get("major_events", [])
                        
                        self.logger.info(f"📊 [EventExtractor] 从 {stage_name} 提取到 {len(events)} 个重大事件")
                        
                        for event in events:
                            self._enrich_event_metadata(event, stage_name)
                            all_events.append(event)
                            
                    except Exception as e:
                        self.logger.error(f"❌ [EventExtractor] 读取文件失败 {plan_file.name}: {e}")
                
                break
        
        return all_events
    
    def _enrich_event_metadata(self, event: Dict, stage_name: str):
        """
        为事件添加元数据
        
        Args:
            event: 事件字典
            stage_name: 阶段名称
        """
        event["_stage"] = stage_name
        chapter_range = event.get("chapter_range", "1-10")
        
        try:
            from src.managers.StagePlanUtils import parse_chapter_range
            start_ch, end_ch = parse_chapter_range(chapter_range)
            event["_start_chapter"] = start_ch
            event["_end_chapter"] = end_ch
        except Exception as e:
            self.logger.warn(f"解析章节范围失败: {chapter_range}, {e}")
            event["_start_chapter"] = 1
            event["_end_chapter"] = 10
    
    def extract_medium_events(self, major_event: Dict) -> List[Dict]:
        """
        从重大事件的 composition 中提取中级事件
        
        支持两种格式:
        - 新格式: 起因、发展、高潮、结局
        - 旧格式: 起、承、转、合
        
        Args:
            major_event: 重大事件字典
            
        Returns:
            中级事件列表
        """
        medium_events = []
        
        composition = major_event.get("composition", {})
        
        if not composition:
            # 如果没有 composition，检查是否有 _medium_events
            return major_event.get("_medium_events", [])
        
        # 🔥 支持两种格式：先尝试新格式，如果为空则尝试旧格式
        new_stage_order = ["起因", "发展", "高潮", "结局"]
        old_stage_order = ["起", "承", "转", "合"]
        
        # 检测使用哪种格式
        has_new_format = any(composition.get(stage) for stage in new_stage_order)
        has_old_format = any(composition.get(stage) for stage in old_stage_order)
        
        if has_new_format:
            stage_order = new_stage_order
        elif has_old_format:
            stage_order = old_stage_order
        else:
            # 如果都没有，尝试提取所有非空键
            stage_order = list(composition.keys())
        
        # 按叙事顺序提取
        for stage in stage_order:
            events = composition.get(stage, [])
            if isinstance(events, list):
                for event in events:
                    event_copy = dict(event)
                    event_copy["stage"] = stage
                    event_copy["parent_major_event"] = major_event.get("name")
                    medium_events.append(event_copy)
        
        return medium_events
    
    def extract_character_designs(self, novel_data: Dict) -> List[Dict]:
        """
        提取角色设计数据
        
        Args:
            novel_data: 小说数据字典
            
        Returns:
            角色列表
        """
        characters = []
        
        # 从多个可能的路径提取角色数据
        # 1. 从 quality_data.character_development
        quality_data = novel_data.get("quality_data", {})
        character_development = quality_data.get("character_development", {})
        
        if character_development:
            for char_name, char_data in character_development.items():
                if isinstance(char_data, dict):
                    characters.append({
                        "name": char_name,
                        **char_data
                    })
        
        # 2. 从 character_design 字段
        if not characters:
            character_design = novel_data.get("character_design", {})
            if isinstance(character_design, dict):
                for char_name, char_data in character_design.items():
                    if isinstance(char_data, dict):
                        characters.append({
                            "name": char_name,
                            **char_data
                        })
        
        # 3. 🔥 新增：直接从项目文件读取角色设计
        if not characters:
            characters = self._extract_character_designs_from_files(novel_data)
        
        self.logger.info(f"✅ [EventExtractor] 提取到 {len(characters)} 个角色设计")
        return characters
    
    def _extract_character_designs_from_files(self, novel_data: Dict) -> List[Dict]:
        """
        直接从项目文件读取角色设计
        
        Args:
            novel_data: 小说数据字典
            
        Returns:
            角色列表
        """
        import json
        import re
        from pathlib import Path
        
        characters = []
        title = novel_data.get("novel_title", "") or novel_data.get("title", "")
        
        if not title:
            self.logger.warn("⚠️ 无法确定项目标题，跳过角色文件读取")
            return characters
        
        # 清理标题中的特殊字符
        safe_title = re.sub(r'[\\/*?"<>|]', "_", title)
        
        # 检查多个可能的路径
        project_paths = [
            Path("小说项目") / safe_title / "characters",
            Path("小说项目") / title / "characters",
        ]
        
        for project_path in project_paths:
            if not project_path.exists():
                continue
            
            self.logger.info(f"🔍 [EventExtractor] 检查角色路径: {project_path}")
            
            # 查找角色设计文件
            character_files = list(project_path.glob("*_角色设计.json"))
            
            if character_files:
                self.logger.info(f"✅ [EventExtractor] 找到 {len(character_files)} 个角色设计文件")
                
                for char_file in character_files:
                    try:
                        with open(char_file, 'r', encoding='utf-8') as f:
                            char_data = json.load(f)
                        
                        # 处理主角
                        main_character = char_data.get("main_character", {})
                        if main_character and isinstance(main_character, dict):
                            characters.append({
                                "name": main_character.get("name", "未命名主角"),
                                "role": main_character.get("role_type", "主角"),
                                "appearance": main_character.get("living_characteristics", {}).get("physical_presence", ""),
                                "personality": main_character.get("core_personality", ""),
                                "background": main_character.get("background", ""),
                                "dialogue_style": main_character.get("dialogue_style_example", ""),
                                **main_character
                            })
                            self.logger.info(f"  ✅ 提取主角: {main_character.get('name', '未命名')}")
                        
                        # 处理重要角色
                        important_chars = char_data.get("important_characters", [])
                        if isinstance(important_chars, list):
                            for char in important_chars:
                                if isinstance(char, dict):
                                    characters.append({
                                        "name": char.get("name", "未命名角色"),
                                        "role": char.get("role", "配角"),
                                        "appearance": char.get("living_characteristics", {}).get("physical_presence", ""),
                                        "personality": char.get("soul_matrix", [{}])[0].get("core_trait", "") if char.get("soul_matrix") else "",
                                        "background": char.get("initial_state", {}).get("description", ""),
                                        "dialogue_style": char.get("dialogue_style_example", ""),
                                        **char
                                    })
                                    self.logger.info(f"  ✅ 提取配角: {char.get('name', '未命名')}")
                        
                        # 如果找到了角色，就不再继续查找其他路径
                        if characters:
                            break
                            
                    except Exception as e:
                        self.logger.error(f"❌ [EventExtractor] 读取角色文件失败 {char_file.name}: {e}")
                
                break
        
        return characters
    
    def generate_character_prompts(self, characters: List[Dict]) -> List[Dict]:
        """
        为角色生成剧照生成提示词
        
        Args:
            characters: 角色列表
            
        Returns:
            包含生成提示词的角色列表
        """
        character_prompts = []
        
        for char in characters:
            name = char.get("name", "未命名角色")
            role = char.get("role", "主角")
            appearance = char.get("appearance", "")
            personality = char.get("personality", "")
            background = char.get("background", "")
            
            # 🔥 根据角色类型生成不同的提示词
            # 检查是否为特殊角色（如物品、武器等）
            is_object_character = self._is_object_character(char, appearance)
            
            if is_object_character:
                # 对于物品角色（如剑），生成物品展示提示词
                prompt = self._generate_object_portrait_prompt(name, role, appearance, background)
            else:
                # 对于普通角色，生成人物肖像提示词
                prompt = self._generate_human_portrait_prompt(name, role, appearance, personality, background)
            
            character_prompts.append({
                "character_name": name,
                "character_data": char,
                "generation_prompt": prompt,
                "prompt_type": "object_portrait" if is_object_character else "character_still"
            })
        
        return character_prompts
    
    def _is_object_character(self, char: Dict, appearance: str) -> bool:
        """
        判断是否为物品角色（非人类角色）
        
        Args:
            char: 角色数据
            appearance: 外貌描述
            
        Returns:
            是否为物品角色
        """
        # 检查外貌描述中的关键词
        object_keywords = [
            "剑", "刀", "枪", "武器", "法宝", "神器",
            "sword", "blade", "weapon", "artifact", "object",
            "形态", "铁", "金属", "锈", "剑身"
        ]
        
        appearance_lower = appearance.lower()
        for keyword in object_keywords:
            if keyword in appearance_lower:
                return True
        
        # 检查角色定位
        role = char.get("role", "")
        if "武器" in role or "物品" in role or "法宝" in role:
            return True
        
        return False
    
    def _generate_object_portrait_prompt(self, name: str, role: str, appearance: str, background: str) -> str:
        """
        生成物品角色的剧照提示词
        
        Args:
            name: 角色名称
            role: 角色定位
            appearance: 外貌特征
            background: 背景故事
            
        Returns:
            物品剧照生成提示词
        """
        prompt = f"""【物品角色剧照生成请求】

【物品信息】
物品名称：{name}
物品类型：{role}
外观描述：{appearance}

【画面要求】
- 中心构图，物品占据画面主要位置
- 清晰展示物品的所有细节和特征
- 背景简洁深色，突出物品主体
- 光影效果体现物品材质和质感
- 整体风格神秘、强大、古老

【构图建议】
- 使用特写或大特写镜头
- 物品正面展示，突出关键特征
- 可以添加光晕或能量效果，体现物品的特殊性

【禁止元素】
- ⚠️ 不要生成任何人形角色或人物
- ⚠️ 不要添加手、脸等人身体部位
- ⚠️ 只展示物品本身

请生成高质量的物品剧照，用于视频制作。"""
        return prompt
    
    def _generate_human_portrait_prompt(self, name: str, role: str, appearance: str, personality: str, background: str) -> str:
        """
        生成普通角色的人物肖像提示词
        
        Args:
            name: 角色名称
            role: 角色定位
            appearance: 外貌特征
            personality: 性格特点
            background: 背景故事
            
        Returns:
            人物肖像生成提示词
        """
        prompt = f"""【人物角色剧照生成请求】

【角色信息】
姓名：{name}
角色定位：{role}
外貌特征：{appearance}
性格特点：{personality}

【画面要求】
- 半身或全身像，展示角色完整形象
- 背景简洁，符合角色气质
- 光影效果体现角色性格和情绪
- 服装道具与角色身份匹配
- 表情生动，体现角色内在特质

【艺术风格】
- 亚洲动漫风格或写实风格
- 线条清晰，色彩鲜明
- 注重细节，突出角色个性

【禁止元素】
- ⚠️ 只生成一个角色，不要添加其他人物
- ⚠️ 不要生成群体场景

请生成高质量的人物剧照，用于视频制作。"""
        return prompt
    
    def count_medium_events(self, novel_data: Dict) -> int:
        """
        统计小说中的中级事件总数
        
        Args:
            novel_data: 小说数据字典
            
        Returns:
            中级事件总数
        """
        major_events = self.extract_all_major_events(novel_data)
        total_count = 0
        
        for event in major_events:
            composition = event.get("composition", {})
            for stage_events in composition.values():
                if isinstance(stage_events, list):
                    total_count += len(stage_events)
        
        return total_count


# 创建全局实例
_event_extractor_instance = None

def get_event_extractor(logger_instance=None) -> EventExtractor:
    """获取事件提取器实例（单例模式）"""
    global _event_extractor_instance
    if _event_extractor_instance is None:
        _event_extractor_instance = EventExtractor(logger_instance)
    return _event_extractor_instance