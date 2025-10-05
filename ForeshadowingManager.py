# ForeshadowingManager.py
from typing import Dict, List, Set
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
        """注册伏笔元素 - 修复版本"""
        # 确保所有必要的列表都已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
        if not hasattr(self, 'current_chapter'):
            self.current_chapter = 0
        
        # 创建元素对象
        element = {
            "type": element_type,
            "name": element_name,
            "importance": importance,
            "target_chapter": target_chapter,
            "purpose": purpose,
            "stage_specific": stage_specific,
            "introduced": False,
            "development_progress": 0
        }
        
        # 根据目标章节决定是引入还是发展
        if target_chapter <= self.current_chapter:
            self.elements_to_develop.append(element)
            print(f"  ✅ 注册待发展元素: {element_name} (类型: {element_type}, 目标章节: {target_chapter})")
        else:
            self.elements_to_introduce.append(element)
            print(f"  ✅ 注册待引入元素: {element_name} (类型: {element_type}, 目标章节: {target_chapter})")
    
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
        """获取伏笔上下文 - 修复版本"""
        # 确保所有必要的属性都已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
        
        # 更新当前章节
        self.current_chapter = chapter_number
        
        # 构建上下文
        context = {
            "elements_to_introduce": self.elements_to_introduce.copy(),
            "elements_to_develop": self.elements_to_develop.copy(),
            "foreshadowing_focus": f"第{chapter_number}章伏笔管理"
        }
        
        return context
    
    def generate_foreshadowing_prompt(self, chapter_number: int, event_context: Dict = None) -> str:
        """生成伏笔提示 - 修复版本，整合事件指导"""
        # 确保列表已初始化
        if not hasattr(self, 'elements_to_introduce'):
            self.elements_to_introduce = []
        if not hasattr(self, 'elements_to_develop'):
            self.elements_to_develop = []
            
        # 更新当前章节
        self.current_chapter = chapter_number
        
        # 生成事件指导
        event_guidance = self._generate_event_guidance(event_context, chapter_number)
        
        # 构建提示
        prompt_parts = ["# 🎭 伏笔铺垫指导"]
        
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
                        if elem["target_chapter"] <= chapter_number and not element["introduced"]]
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