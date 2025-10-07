# ForeshadowingManager.py
from typing import Any, Dict, List, Set
import json
from utils import parse_chapter_range, is_chapter_in_range

class ForeshadowingManager:
    """时机控制器 - 专注元素引入时机和铺垫计划（何时写）"""
    def __init__(self, novel_generator):
        self.novel_generator = novel_generator
        # 初始化所有必要的列表和属性
        self.elements_to_introduce = []  # 待引入的元素
        self.elements_to_develop = []    # 待发展的元素
        self.current_chapter = 0         # 当前章节
        self.registered_elements = {}    # 已注册的元素记录
        
        print("✅ 伏笔管理器初始化完成")

    def set_current_chapter(self, chapter_number: int):
        """设置当前章节号"""
        self.current_chapter = chapter_number

    def register_element(self, element_type: str, element_name: str, importance: str, 
                        target_chapter: int, purpose: str = "", stage_specific: bool = True):
        """注册伏笔元素 - 增强版本"""
        # 确保所有必要的列表都已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
        if not hasattr(self, 'current_chapter'):
            self.current_chapter = 0
        
        # 创建完整的元素对象
        element = {
            "type": element_type,
            "name": element_name,
            "importance": importance,
            "target_chapter": target_chapter,
            "purpose": purpose,
            "stage_specific": stage_specific,
            "introduced": False,
            "development_progress": 0,
            "registered_at": self.current_chapter,
            "element_id": f"{element_type}_{element_name}_{target_chapter}"
        }
        
        # 根据目标章节决定是引入还是发展
        if target_chapter <= self.current_chapter:
            self.elements_to_develop.append(element)
            print(f"  ✅ 注册待发展元素: {element_name} (类型: {element_type}, 目标: 第{target_chapter}章)")
        else:
            self.elements_to_introduce.append(element)
            print(f"  ✅ 注册待引入元素: {element_name} (类型: {element_type}, 目标: 第{target_chapter}章)")
    
    def clear_stage_elements(self):
        """清除阶段相关的伏笔元素"""
        # 确保列表已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
            
        # 保留全局伏笔元素（从世界观、角色设计等初始化的）
        # 只清除阶段特定的伏笔元素
        self.elements_to_introduce = [elem for elem in self.elements_to_introduce 
                                     if not elem.get('stage_specific', False)]
        self.elements_to_develop = [elem for elem in self.elements_to_develop 
                                   if not elem.get('stage_specific', False)]
        print("  ✅ 已清除阶段特定的伏笔元素")
    
    def get_context(self, chapter_number: int) -> Dict:
        """获取伏笔上下文 - 增强版本"""
        # 确保所有必要的属性都已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
        
        # 更新当前章节
        self.current_chapter = chapter_number
        print(f"  🎭 更新伏笔管理器当前章节: {chapter_number}")
        
        # 动态筛选当前章节相关的元素
        current_intro_elements = []
        current_develop_elements = []
        
        # 筛选需要引入的元素（目标章节等于当前章节）
        for element in self.elements_to_introduce:
            if element.get("target_chapter") == chapter_number:
                current_intro_elements.append(element)
                print(f"    ✅ 筛选到引入元素: {element.get('name')}")
        
        # 筛选需要发展的元素（目标章节小于等于当前章节且未引入）
        for element in self.elements_to_develop:
            if (element.get("target_chapter") <= chapter_number and 
                not element.get("introduced", False)):
                current_develop_elements.append(element)
                print(f"    ✅ 筛选到发展元素: {element.get('name')}")
        
        # 构建详细的上下文
        context = {
            "elements_to_introduce": current_intro_elements,
            "elements_to_develop": current_develop_elements,
            "foreshadowing_focus": f"第{chapter_number}章伏笔与铺垫",
            "total_elements_count": len(current_intro_elements) + len(current_develop_elements),
            "chapter_number": chapter_number
        }
        
        print(f"  📊 伏笔上下文构建完成: {len(current_intro_elements)}个引入, {len(current_develop_elements)}个发展")
        
        return context

    def _generate_event_guidance(self, event_context: Dict, chapter_number: int) -> str:
        """生成事件指导 - 新增方法"""
        if not event_context:
            return ""
        
        guidance_parts = []
        
        # 处理活跃事件
        active_events = event_context.get('active_events', [])
        if active_events:
            guidance_parts.append("## 🎯 活跃事件指导:")
            for event in active_events:
                if isinstance(event, dict):
                    event_name = event.get('name', '未知事件')
                    event_type = event.get('type', '普通')
                    guidance_parts.append(f"- **{event_name}** ({event_type}事件): 需要推进发展")
        
        # 处理即将发生的事件
        upcoming_events = event_context.get('upcoming_events', [])
        if upcoming_events:
            guidance_parts.append("## ⏰ 即将发生事件:")
            for event in upcoming_events:
                if isinstance(event, dict):
                    event_name = event.get('name', '未知事件')
                    trigger_chapter = event.get('trigger_chapter', chapter_number + 1)
                    guidance_parts.append(f"- **{event_name}**: 预计第{trigger_chapter}章触发")
        
        return "\n".join(guidance_parts) if guidance_parts else ""
    
    def generate_foreshadowing_prompt(self, chapter_number: int, event_context: Dict = None) -> str:
        """生成伏笔提示 - 修复版本，整合事件指导"""
        # 确保列表已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
            
        # 更新当前章节
        self.current_chapter = chapter_number
        
        # 检查是否是事件空窗期
        is_event_gap = event_context and (not event_context.get("active_events") and 
                                        not event_context.get("trigger_checkpoints"))
        
        # 构建提示
        prompt_parts = ["# 🎭 伏笔铺垫指导"]
        
        # 添加事件指导
        event_guidance = self._generate_event_guidance(event_context, chapter_number)
        if event_guidance:
            prompt_parts.append(event_guidance)
        
        # 事件空窗期的特殊伏笔机会
        if is_event_gap:
            prompt_parts.extend([
                "",
                "## 💫 事件空窗期伏笔机会",
                "当前没有活跃事件，是铺设长期伏笔的绝佳时机：",
                "- 可引入重要性较低但有趣的设定元素",
                "- 发展角色间的微妙关系和互动",
                "- 展示世界观的有趣细节和背景故事",
                "- 为后续重大事件埋下更隐蔽的线索",
                ""
            ])
        
        # 添加待引入元素
        intro_elements = [elem for elem in self.elements_to_introduce 
                        if elem["target_chapter"] == chapter_number]
        if intro_elements:
            prompt_parts.append("## 🆕 需要引入的元素:")
            for element in intro_elements:
                purpose = element['purpose'] if element['purpose'] else "推进情节发展"
                prompt_parts.append(f"- **{element['name']}** ({element['type']}): {purpose}")
        
        # 添加待发展元素  
        develop_elements = [elem for elem in self.elements_to_develop
                        if elem["target_chapter"] <= chapter_number and not elem["introduced"]]
        if develop_elements:
            prompt_parts.append("## 📈 需要发展的元素:")
            for element in develop_elements:
                prompt_parts.append(f"- **{element['name']}** ({element['type']}): 需要进一步发展")
        
        return "\n".join(prompt_parts) if len(prompt_parts) > 1 else "# 🎭 伏笔铺垫指导\n\n本章暂无特定的伏笔任务。"

    def get_stage_foreshadowing_plan(self, stage_name: str, start_chapter: int, 
                                   end_chapter: int, content_plan: Dict = None) -> Dict:
        """生成阶段的伏笔铺垫计划"""
        cache_key = f"{stage_name}_{start_chapter}_{end_chapter}"
        
        if cache_key in self.stage_foreshadowing_cache:
            return self.stage_foreshadowing_cache[cache_key]
        
        print(f"  ⏰ 生成{stage_name}的伏笔计划...")
        
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 计算章节分段
        stage_length = end_chapter - start_chapter + 1
        early_end = start_chapter + max(1, stage_length // 3) - 1
        middle_start = early_end + 1
        middle_end = start_chapter + (2 * stage_length // 3) - 1
        late_start = middle_end + 1
        
        user_prompt = self.Prompts["prompts"]["stage_foreshadowing_planning"].format(
            stage_name=stage_name,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            total_chapters=total_chapters,
            novel_title=novel_data["novel_title"],
            novel_synopsis=novel_data["novel_synopsis"],
            worldview_overview=json.dumps(novel_data.get("core_worldview", {}), ensure_ascii=False),
            content_plan_summary=self._get_content_plan_summary(content_plan),
            early_start=start_chapter,
            early_end=early_end,
            middle_start=middle_start,
            middle_end=middle_end,
            late_start=late_start,
            late_end=end_chapter
        )
        
        # 生成伏笔计划
        foreshadowing_plan = self.generator.api_client.generate_content_with_retry(
            "stage_foreshadowing_planning",
            user_prompt,
            purpose=f"生成{stage_name}伏笔计划"
        )
        
        if foreshadowing_plan:
            self.stage_foreshadowing_cache[cache_key] = foreshadowing_plan
            print(f"  ✅ {stage_name}伏笔计划生成完成")
            self._print_foreshadowing_plan_summary(foreshadowing_plan)
            return foreshadowing_plan
        else:
            print(f"  ⚠️ {stage_name}伏笔计划生成失败，使用默认计划")
            return self._create_default_foreshadowing_plan(stage_name, start_chapter, end_chapter)


    def _get_content_plan_summary(self, content_plan: Dict) -> str:
        """从内容规划中提取摘要信息"""
        if not content_plan:
            return "暂无详细内容规划参考"
        
        summary_parts = []
        
        # 提取人物成长信息
        char_plan = content_plan.get("character_growth_plan", {})
        if char_plan:
            protagonist = char_plan.get("protagonist_development", {})
            new_abilities = protagonist.get("ability_advancement", [])
            new_chars = char_plan.get("supporting_characters_development", {}).get("new_characters", [])
            
            if new_abilities:
                summary_parts.append(f"- 主角新能力: {', '.join(new_abilities[:3])}")
            if new_chars:
                summary_parts.append(f"- 新角色引入: {', '.join(new_chars[:3])}")
        
        # 提取势力发展信息
        faction_plan = content_plan.get("faction_development_plan", {})
        if faction_plan:
            power_changes = faction_plan.get("power_structure_changes", {})
            new_powers = power_changes.get("rising_powers", [])
            new_conflicts = faction_plan.get("conflict_escalation", {}).get("new_conflicts", [])
            
            if new_powers:
                summary_parts.append(f"- 新兴势力: {', '.join(new_powers[:3])}")
            if new_conflicts:
                summary_parts.append(f"- 新冲突: {', '.join(new_conflicts[:2])}")
        
        # 提取物品功法信息
        ability_plan = content_plan.get("ability_equipment_plan", {})
        if ability_plan:
            new_skills = ability_plan.get("skill_progression", {}).get("new_skills", [])
            new_equipment = ability_plan.get("equipment_advancement", {}).get("new_equipment", [])
            
            if new_skills:
                summary_parts.append(f"- 新技能: {', '.join(new_skills[:3])}")
            if new_equipment:
                summary_parts.append(f"- 新装备: {', '.join(new_equipment[:3])}")
        
        return "\n".join(summary_parts) if summary_parts else "内容规划较为常规，无特殊新元素"

    def _get_current_stage_from_plan(self, chapter_number: int, stage_plan: Dict) -> Dict:
        """从阶段计划中获取当前阶段信息"""
        if not stage_plan or "global_growth_plan" not in self.generator.novel_data:
            return None
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        for stage in growth_plan.get("stage_framework", []):
            chapter_range = stage["chapter_range"]
            if is_chapter_in_range(chapter_number, chapter_range):
                return stage
        return None

    def _generate_chapter_foreshadowing_context(self, chapter_number: int, 
                                              foreshadowing_plan: Dict) -> Dict:
        """生成章节特定的伏笔上下文"""
        chapter_plan = None
        chapter_by_chapter = foreshadowing_plan.get("chapter_by_chapter_plan", [])
        
        for plan in chapter_by_chapter:
            if plan.get("chapter_number") == chapter_number:
                chapter_plan = plan
                break
        
        if not chapter_plan:
            return {
                "foreshadowing_focus": "常规情节推进，无特殊伏笔任务",
                "foreshadowing_intensity": "normal",
                "specific_tasks": ["保持故事连贯性"]
            }
        
        # 构建详细的元素信息
        elements_to_introduce = []
        for element_name in chapter_plan.get("elements_to_introduce", []):
            element_info = self._get_element_detail(element_name, foreshadowing_plan)
            if element_info:
                elements_to_introduce.append(element_info)
        
        elements_to_develop = []
        for element_name in chapter_plan.get("elements_to_develop", []):
            element_info = self._get_development_detail(element_name, foreshadowing_plan)
            if element_info:
                elements_to_develop.append(element_info)
        
        return {
            "foreshadowing_focus": chapter_plan.get("foreshadowing_focus", "推进故事发展"),
            "elements_to_introduce": elements_to_introduce,
            "elements_to_develop": elements_to_develop,
            "foreshadowing_intensity": chapter_plan.get("foreshadowing_intensity", "normal"),
            "specific_tasks": chapter_plan.get("specific_tasks", [])
        }

    def _get_element_detail(self, element_name: str, foreshadowing_plan: Dict) -> Dict:
        """获取元素的详细信息"""
        new_elements = foreshadowing_plan.get("new_elements_introduction", [])
        for element in new_elements:
            if element.get("name") == element_name:
                return {
                    "name": element_name,
                    "type": element.get("element_type", "unknown"),
                    "purpose": element.get("purpose", ""),
                    "methods": element.get("foreshadowing_methods", []),
                    "formal_intro_chapter": element.get("formal_intro_chapter")
                }
        return None

    def _get_development_detail(self, element_name: str, foreshadowing_plan: Dict) -> Dict:
        """获取元素发展的详细信息"""
        existing_elements = foreshadowing_plan.get("existing_elements_development", [])
        for element in existing_elements:
            if element.get("name") == element_name:
                return {
                    "name": element_name,
                    "type": element.get("element_type", "unknown"),
                    "development_arc": element.get("development_arc", ""),
                    "methods": element.get("development_methods", []),
                    "key_turning_chapter": element.get("key_turning_chapter")
                }
        return None


    def get_chapter_foreshadowing_context(self, chapter_number: int, stage_plan: Dict = None) -> Dict:
        """获取指定章节的伏笔上下文 - 具体实现"""
        # 获取当前阶段信息
        current_stage = self._get_current_stage_from_plan(chapter_number, stage_plan)
        if not current_stage:
            return {
                "foreshadowing_focus": "常规情节推进，无特殊伏笔任务",
                "foreshadowing_intensity": "normal",
                "specific_tasks": ["保持故事连贯性"]
            }
        
        # 获取阶段伏笔计划
        stage_range = parse_chapter_range(current_stage["chapter_range"])
        foreshadowing_plan = self.get_stage_foreshadowing_plan(
            current_stage["stage_name"], stage_range[0], stage_range[1]
        )
        
        # 生成章节特定的伏笔指导
        chapter_context = self._generate_chapter_foreshadowing_context(
            chapter_number, foreshadowing_plan
        )
        
        return chapter_context

    def _print_foreshadowing_plan_summary(self, foreshadowing_plan: Dict):
        """打印伏笔计划摘要"""
        stage_name = foreshadowing_plan.get("stage_name", "未知阶段")
        print(f"    ⏰ {stage_name}伏笔计划摘要:")
        
        # 新元素引入
        new_elements = foreshadowing_plan.get("new_elements_introduction", [])
        print(f"      新元素引入: {len(new_elements)}个")
        
        # 现有元素发展
        existing_elements = foreshadowing_plan.get("existing_elements_development", [])
        print(f"      元素发展: {len(existing_elements)}个")
        
        # 章节分布
        chapter_plan = foreshadowing_plan.get("chapter_by_chapter_plan", [])
        light_chapters = len([p for p in chapter_plan if p.get("foreshadowing_intensity") == "light"])
        medium_chapters = len([p for p in chapter_plan if p.get("foreshadowing_intensity") == "medium"])
        strong_chapters = len([p for p in chapter_plan if p.get("foreshadowing_intensity") == "strong"])
        print(f"      伏笔强度分布: 轻度{light_chapters}章, 中度{medium_chapters}章, 重度{strong_chapters}章")

    def _create_default_foreshadowing_plan(self, stage_name: str, start_chapter: int, end_chapter: int) -> Dict:
        """创建默认的伏笔计划"""
        chapter_plan = []
        for chapter in range(start_chapter, end_chapter + 1):
            intensity = "light" if chapter < start_chapter + 3 else "medium" if chapter < end_chapter - 2 else "strong"
            chapter_plan.append({
                "chapter_number": chapter,
                "foreshadowing_focus": "推进故事发展",
                "elements_to_introduce": [],
                "elements_to_develop": [],
                "foreshadowing_intensity": intensity,
                "specific_tasks": ["保持情节连贯性"]
            })
        
        return {
            "stage_name": stage_name,
            "chapter_range": f"第{start_chapter}章-第{end_chapter}章",
            "new_elements_introduction": [],
            "existing_elements_development": [],
            "foreshadowing_intensity_schedule": {
                "light_foreshadowing_chapters": list(range(start_chapter, start_chapter + 3)),
                "medium_foreshadowing_chapters": list(range(start_chapter + 3, end_chapter - 2)),
                "strong_foreshadowing_chapters": list(range(end_chapter - 2, end_chapter + 1))
            },
            "chapter_by_chapter_plan": chapter_plan,
            "cross_stage_coordination": {
                "previous_stage_tie_ins": [],
                "next_stage_setups": []
            },
            "foreshadowing_synopsis": f"{stage_name}的常规伏笔安排"
        }
    
    # 在ForeshadowingManager类中添加
    def set_element_timing_planner(self, planner):
        """设置元素时机规划器"""
        self.timing_planner = planner

    def generate_comprehensive_foreshadowing_prompt(self, chapter_number: int, event_context: Dict = None) -> str:
        """生成综合的伏笔提示，包含元素登场时机"""
        base_prompt = self.generate_foreshadowing_prompt(chapter_number, event_context)
        
        # 添加元素登场时机信息
        if hasattr(self, 'timing_planner') and self.timing_planner.element_timing_plan:
            timing_info = self._get_chapter_timing_info(chapter_number)
            if timing_info:
                return base_prompt + "\n\n" + timing_info
        
        return base_prompt

    def _get_chapter_timing_info(self, chapter_number: int) -> str:
        """获取本章的元素登场时机信息"""
        timing_plan = self.timing_planner.element_timing_plan
        if not timing_plan:
            return ""
        
        elements_introducing = []
        
        # 检查所有类别中本章需要引入的元素
        for category in ["character_timing", "faction_timing", "ability_timing", "item_timing", "concept_timing"]:
            elements = timing_plan.get(category, [])
            for element in elements:
                if element.get("first_appearance_chapter") == chapter_number:
                    elements_introducing.append({
                        "type": category.replace("_timing", ""),
                        "name": element["name"],
                        "importance": element.get("importance", "普通")
                    })
        
        if not elements_introducing:
            return ""
        
        # 构建时机提示
        prompt_parts = ["## 🎯 本章需要引入的元素:"]
        for elem in elements_introducing:
            prompt_parts.append(f"- **{elem['name']}** ({elem['type']}): 重要性-{elem['importance']}")
        
        return "\n".join(prompt_parts)    

    def get_emotional_buffer_content(self, chapter_number: int) -> Dict[str, Any]:
        """获取情绪缓冲期的内容建议"""
        buffer_suggestions = {
            "available_elements": [],
            "side_plots": [],
            "character_moments": [],
            "world_building": []
        }
        
        # 1. 获取可用的伏笔元素（重要性较低的元素优先）
        for element in self.elements_to_introduce:
            if element.get("importance") in ["low", "medium"]:
                buffer_suggestions["available_elements"].append({
                    "name": element["name"],
                    "type": element["type"],
                    "suggested_approach": f"轻松引入{element['type']}「{element['name']}」",
                    "purpose": element.get("purpose", "丰富世界观")
                })
        
        # 2. 生成支线剧情建议
        buffer_suggestions["side_plots"] = self._generate_side_plot_suggestions(chapter_number)
        
        # 3. 角色日常时刻
        buffer_suggestions["character_moments"] = self._generate_character_moments(chapter_number)
        
        # 4. 世界观展示机会
        buffer_suggestions["world_building"] = self._generate_world_building_suggestions(chapter_number)
        
        return buffer_suggestions

    def _generate_side_plot_suggestions(self, chapter_number: int, novel_data: Dict = None) -> List[Dict]:
        """生成支线剧情建议 - 通用方法，基于小说数据结构"""
        if not novel_data:
            return self._get_default_side_plots()
        
        side_plots = []
        
        # 1. 基于角色关系生成支线
        character_design = novel_data.get("character_design", {})
        if character_design:
            main_char = character_design.get("main_character", {})
            supporting_chars = character_design.get("important_characters", [])
            
            # 主角与重要配角的互动支线
            for char in supporting_chars[:3]:  # 取前3个重要配角
                char_name = char.get("name", "")
                char_role = char.get("role", "")
                relationship = char.get("relationship", "")
                
                if char_name and relationship:
                    side_plots.append({
                        "type": "角色关系发展",
                        "description": f"{main_char.get('name', '主角')}与{char_name}的{relationship}互动",
                        "purpose": f"深化{char_name}的角色塑造，推进{relationship}线",
                        "emotional_tone": self._get_emotional_tone_by_relationship(relationship),
                        "related_characters": [main_char.get('name', '主角'), char_name],
                        "suggested_content": [
                            f"{char_name}的背景故事分享",
                            f"共同面对的小型挑战",
                            f"{relationship}相关的深度对话"
                        ]
                    })
        
        # 2. 基于世界观元素生成支线
        worldview = novel_data.get("core_worldview", {})
        if worldview:
            # 从世界观中提取可用的支线元素
            hot_elements = worldview.get("hot_elements", [])
            social_structure = worldview.get("social_structure", "")
            
            for element in hot_elements[:2]:  # 取前2个热门元素
                side_plots.append({
                    "type": "世界观探索",
                    "description": f"探索{element}相关的背景设定",
                    "purpose": f"丰富{element}的世界观细节",
                    "emotional_tone": "神秘、探索",
                    "related_elements": [element],
                    "suggested_content": self._get_world_element_content(element)
                })
        
        # 3. 基于当前情节阶段生成支线
        current_stage = self._get_current_stage_by_progress(chapter_number, novel_data)
        if current_stage:
            side_plots.append({
                "type": "阶段特色支线",
                "description": f"体现{current_stage}特色的辅助情节",
                "purpose": "强化当前阶段的主题氛围",
                "emotional_tone": self._get_stage_emotional_tone(current_stage),
                "stage_specific": True,
                "suggested_content": self._get_stage_specific_content(current_stage)
            })
        
        # 4. 基于系统设定生成支线（如果有系统元素）
        if self._has_system_elements(novel_data):
            side_plots.append({
                "type": "系统相关支线",
                "description": "探索系统功能或完成系统小任务",
                "purpose": "展示系统特色，提供成长展示机会",
                "emotional_tone": "惊奇、成长",
                "system_related": True,
                "suggested_content": [
                    "新技能或装备的测试场景",
                    "系统任务的轻松完成过程",
                    "系统功能的意外发现"
                ]
            })
        
        return side_plots if side_plots else self._get_default_side_plots()

    def _generate_character_moments(self, chapter_number: int, novel_data: Dict = None) -> List[Dict]:
        """生成角色日常时刻建议 - 通用方法"""
        if not novel_data:
            return self._get_default_character_moments()
        
        character_moments = []
        character_design = novel_data.get("character_design", {})
        
        if not character_design:
            return self._get_default_character_moments()
        
        main_char = character_design.get("main_character", {})
        supporting_chars = character_design.get("important_characters", [])
        
        # 主角的个人时刻
        if main_char:
            char_name = main_char.get("name", "主角")
            personality = main_char.get("personality", "")
            background = main_char.get("background", "")
            
            character_moments.append({
                "type": "主角内心世界",
                "description": f"展现{char_name}的内心思考和性格特点",
                "emotional_tone": "深沉、真实",
                "related_character": char_name,
                "suggested_scenes": [
                    f"{char_name}对当前处境的思考",
                    f"展现{personality}性格的具体行为",
                    f"{background}背景带来的独特视角"
                ]
            })
        
        # 配角的特色时刻
        for char in supporting_chars[:4]:  # 取前4个配角
            char_name = char.get("name", "")
            char_role = char.get("role", "")
            personality = char.get("personality", "")
            
            if char_name and char_role:
                character_moments.append({
                    "type": f"{char_role}特色时刻",
                    "description": f"展现{char_name}作为{char_role}的独特一面",
                    "emotional_tone": self._get_character_emotional_tone(char_role),
                    "related_character": char_name,
                    "suggested_scenes": [
                        f"{char_name}展现{personality}的日常行为",
                        f"{char_name}在团队中的独特作用",
                        f"{char_name}的个人小目标或烦恼"
                    ]
                })
        
        # 团队互动时刻
        if len(supporting_chars) >= 2:
            character_moments.append({
                "type": "团队互动",
                "description": "主要角色间的轻松互动",
                "emotional_tone": "温馨、幽默",
                "related_characters": [main_char.get("name", "主角")] + 
                                    [char.get("name") for char in supporting_chars[:3]],
                "suggested_scenes": [
                    "战斗或任务间隙的轻松对话",
                    "分享各自的故事或经历",
                    "团队协作中的小插曲"
                ]
            })
        
        return character_moments

    def _generate_world_building_suggestions(self, chapter_number: int, novel_data: Dict = None) -> List[Dict]:
        """生成世界观展示建议 - 通用方法"""
        if not novel_data:
            return self._get_default_world_building()
        
        world_building = []
        worldview = novel_data.get("core_worldview", {})
        
        if not worldview:
            return self._get_default_world_building()
        
        # 从世界观中提取关键信息
        era = worldview.get("era", "")
        core_conflict = worldview.get("core_conflict", "")
        overview = worldview.get("overview", "")
        power_system = worldview.get("power_system", "")
        social_structure = worldview.get("social_structure", "")
        
        # 时代背景展示
        if era:
            world_building.append({
                "type": "时代风貌",
                "description": f"展现{era}的时代特色和社会背景",
                "purpose": "增强故事的历史真实感和时代氛围",
                "emotional_tone": "怀旧、真实",
                "key_elements": [
                    "当时的日常生活场景",
                    "时代特有的社会现象",
                    "历史背景下的普通人生活"
                ]
            })
        
        # 核心冲突相关展示
        if core_conflict:
            world_building.append({
                "type": "冲突背景",
                "description": "展现故事核心冲突的深层背景",
                "purpose": "帮助读者理解故事矛盾的根源",
                "emotional_tone": "深沉、复杂",
                "key_elements": [
                    "冲突各方的立场和动机",
                    "冲突对普通人的影响",
                    "解决冲突的潜在可能性"
                ]
            })
        
        # 力量体系展示（如果有）
        if power_system:
            world_building.append({
                "type": "力量体系",
                "description": "展现故事中的特殊能力或技术体系",
                "purpose": "丰富世界观，展示独特设定",
                "emotional_tone": "惊奇、探索",
                "key_elements": [
                    "力量或技术的日常应用",
                    "掌握力量的过程和代价",
                    "力量体系对社会的影响"
                ]
            })
        
        # 社会结构展示
        if social_structure:
            world_building.append({
                "type": "社会百态",
                "description": "展现故事世界中的社会层次和人际关系",
                "purpose": "丰富故事的社会深度",
                "emotional_tone": "复杂、真实",
                "key_elements": [
                    "不同社会阶层的日常生活",
                    "社会规则和潜规则",
                    "人物在社会中的位置和挣扎"
                ]
            })
        
        return world_building

    # 辅助方法
    def _get_emotional_tone_by_relationship(self, relationship: str) -> str:
        """根据角色关系返回合适的情感基调"""
        tone_map = {
            "战友": "热血、信任",
            "爱人": "深情、温馨", 
            "师徒": "尊敬、成长",
            "对手": "紧张、敬佩",
            "朋友": "轻松、真诚",
            "兄弟": "豪迈、义气"
        }
        return tone_map.get(relationship, "温馨、真实")

    def _get_world_element_content(self, element: str) -> List[str]:
        """根据世界观元素返回相关内容建议"""
        content_map = {
            "魔法": ["魔法原理的简单展示", "魔法在日常生活中的应用", "学习魔法的趣事"],
            "修真": ["修炼心得的分享", "灵药或法宝的发现", "修真界的小常识"],
            "科技": ["科技产品的演示", "技术原理的通俗解释", "科技带来的生活变化"],
            "谍战": ["情报工作的细节", "伪装技巧的展示", "敌我双方的智力博弈"],
            "军事": ["武器装备的介绍", "战术策略的讨论", "军旅生活的描写"]
        }
        return content_map.get(element, ["相关背景的探索", "设定细节的展现"])

    def _get_current_stage_by_progress(self, chapter_number: int, novel_data: Dict) -> str:
        """根据章节进度推断当前阶段"""
        progress = novel_data.get("current_progress", {})
        total_chapters = progress.get("total_chapters", 100)
        current_stage = progress.get("current_stage", "")
        
        if current_stage:
            return current_stage
        
        # 如果没有明确阶段，根据章节比例推断
        progress_ratio = chapter_number / total_chapters if total_chapters > 0 else 0
        
        if progress_ratio <= 0.3:
            return "开局阶段"
        elif progress_ratio <= 0.7:
            return "发展阶段" 
        else:
            return "高潮阶段"

    def _get_stage_emotional_tone(self, stage: str) -> str:
        """根据阶段返回情感基调"""
        tone_map = {
            "开局阶段": "探索、新奇",
            "发展阶段": "成长、挑战", 
            "高潮阶段": "紧张、激烈",
            "结局阶段": "圆满、感慨"
        }
        return tone_map.get(stage, "适中、平稳")

    def _get_stage_specific_content(self, stage: str) -> List[str]:
        """根据阶段返回特色内容"""
        content_map = {
            "开局阶段": ["世界观的基础介绍", "主角的初始状态展示", "故事基调的确立"],
            "发展阶段": ["角色关系的深化", "次要目标的推进", "能力或势力的成长"],
            "高潮阶段": ["主要矛盾的激化", "关键能力的展示", "情感关系的考验"]
        }
        return content_map.get(stage, ["符合当前进度的辅助情节"])

    def _get_character_emotional_tone(self, role: str) -> str:
        """根据角色类型返回情感基调"""
        tone_map = {
            "忠诚的副手": "信赖、坚定",
            "智谋担当": "智慧、冷静",
            "宿命的敌人": "复杂、深刻", 
            "红颜知己": "温柔、理解",
            "导师": "威严、关怀"
        }
        return tone_map.get(role, "真实、立体")

    def _has_system_elements(self, novel_data: Dict) -> bool:
        """检测小说是否包含系统元素"""
        # 检查主角是否有特殊能力描述
        main_char = novel_data.get("character_design", {}).get("main_character", {})
        if "system" in str(main_char.get("special_ability", "")).lower():
            return True
        
        # 检查世界观中是否有系统相关描述
        worldview = novel_data.get("core_worldview", {})
        if "system" in str(worldview.get("power_system", "")).lower():
            return True
        
        # 检查阶段计划中是否有系统相关事件
        stage_plans = novel_data.get("stage_writing_plans", {})
        for stage in stage_plans.values():
            if "system" in str(stage).lower():
                return True
        
        return False

    # 默认方法保持不变
    def _get_default_side_plots(self) -> List[Dict]:
        """获取默认支线剧情（备用）"""
        return [
            {
                "type": "角色互动",
                "description": "主要角色间的轻松对话或日常互动",
                "purpose": "展现角色关系，增加人情味",
                "emotional_tone": "温馨、幽默"
            }
        ]

    def _get_default_character_moments(self) -> List[Dict]:
        """获取默认角色时刻（备用）"""
        return [
            {
                "type": "生活场景", 
                "description": "展示角色在日常生活中的一面",
                "examples": ["用餐时刻", "训练间隙", "休息时的思考"],
                "emotional_tone": "平静、真实"
            }
        ]

    def _get_default_world_building(self) -> List[Dict]:
        """获取默认世界观展示（备用）"""
        return [
            {
                "type": "环境描写",
                "description": "对特殊地点或景观的细致描写", 
                "purpose": "营造氛围，展示世界特色",
                "emotional_tone": "优美、宁静"
            }
        ]