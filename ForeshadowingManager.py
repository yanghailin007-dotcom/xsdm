# ForeshadowingManager.py
from typing import Dict, List, Set
import json
from utils import parse_chapter_range, is_chapter_in_range

class ForeshadowingManager:
    """时机控制器 - 专注元素引入时机和铺垫计划（何时写）"""
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.foreshadowing_elements = {
            "factions": {},
            "characters": {},
            "items": {},
            "locations": {},
            "concepts": {}
        }
        self.introduced_elements = set()
        self.stage_foreshadowing_cache = {}  # 缓存各阶段的伏笔计划
        
        # 伏笔方法库
        self.foreshadowing_methods = {
            "factions": {
                "light": ["路人对话提及", "背景新闻暗示", "相关物品出现", "历史文献记载"],
                "medium": ["角色讨论其影响", "相关事件发生", "历史背景介绍", "势力标志出现"],
                "strong": ["直接冲突预兆", "关键人物关联", "重大事件关联", "势力代表登场"]
            },
            "characters": {
                "light": ["他人提及名字", "相关物品出现", "背景故事暗示", "传闻描述"],
                "medium": ["详细背景介绍", "与他人的关系铺垫", "能力/特点传闻", "间接影响展现"],
                "strong": ["直接影响力展现", "关键事件关联", "主角目标关联", "直接互动铺垫"]
            },
            "items": {
                "light": ["传说/神话提及", "相关描述出现", "功能暗示", "历史记载"],
                "medium": ["具体信息介绍", "获取线索出现", "重要性强调", "使用效果描述"],
                "strong": ["直接线索出现", "获取方法明确", "关键作用展示", "实际使用演示"]
            },
            "locations": {
                "light": ["地图标记", "旅行者描述", "历史记载", "相关物品产地"],
                "medium": ["详细地理描述", "文化特色介绍", "战略重要性说明", "相关事件发生地"],
                "strong": ["主角亲自前往", "关键场景设置", "地形影响剧情", "直接描述重要性"]
            },
            "concepts": {
                "light": ["术语提及", "简单解释", "相关现象描述", "背景设定说明"],
                "medium": ["详细定义", "规则解释", "应用示例", "重要性说明"],
                "strong": ["实际应用展示", "关键作用体现", "系统化阐述", "直接影响剧情"]
            }
        }

    def register_element(self, element_type: str, name: str, importance: str, 
                        planned_intro_chapter: int, description: str = ""):
        """注册需要铺垫的元素"""
        self.foreshadowing_elements[element_type][name] = {
            "importance": importance,
            "planned_intro_chapter": planned_intro_chapter,
            "description": description,
            "foreshadowing_chapters": [],
            "foreshadowing_methods": [],
            "is_introduced": False
        }

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
        
        user_prompt = self.config["prompts"]["stage_foreshadowing_planning"].format(
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

    def get_chapter_foreshadowing_context(self, chapter_number: int, 
                                        stage_plan: Dict = None) -> Dict:
        """获取指定章节的伏笔上下文"""
        # 获取当前阶段信息
        current_stage = self._get_current_stage_from_plan(chapter_number, stage_plan)
        if not current_stage:
            return {}
        
        # 获取阶段伏笔计划
        stage_range = self._parse_chapter_range(current_stage["chapter_range"])
        foreshadowing_plan = self.get_stage_foreshadowing_plan(
            current_stage["stage_name"], stage_range[0], stage_range[1]
        )
        
        # 生成章节特定的伏笔指导
        chapter_context = self._generate_chapter_foreshadowing_context(
            chapter_number, foreshadowing_plan
        )
        
        return chapter_context

    def generate_foreshadowing_prompt(self, chapter_number: int, 
                                    content_context: Dict = None) -> str:
        """生成章节的伏笔提示词"""
        chapter_context = self.get_chapter_foreshadowing_context(chapter_number)
        
        if not chapter_context or not chapter_context.get("foreshadowing_tasks"):
            return "# 🎭 伏笔铺垫指导\n\n本章暂无特定的伏笔任务。"
        
        prompt_parts = ["\n\n# 🎭 伏笔铺垫指导"]
        
        # 添加本章伏笔重点
        prompt_parts.append(f"## 本章伏笔重点")
        prompt_parts.append(f"{chapter_context['foreshadowing_focus']}")
        
        # 添加具体任务
        if chapter_context.get("elements_to_introduce"):
            prompt_parts.append(f"\n## 需要引入的元素:")
            for element in chapter_context["elements_to_introduce"]:
                prompt_parts.append(f"- **{element['name']}** ({element['type']}): {element['purpose']}")
                prompt_parts.append(f"  建议方式: {', '.join(element['methods'][:2])}")
        
        if chapter_context.get("elements_to_develop"):
            prompt_parts.append(f"\n## 需要发展的元素:")
            for element in chapter_context["elements_to_develop"]:
                prompt_parts.append(f"- **{element['name']}** ({element['type']}): {element['development_arc']}")
                prompt_parts.append(f"  发展方式: {', '.join(element['methods'][:2])}")
        
        # 添加伏笔强度指导
        intensity = chapter_context.get("foreshadowing_intensity", "normal")
        intensity_guide = {
            "light": "轻度伏笔: 自然提及，不过度强调",
            "medium": "中度伏笔: 适当强调，建立预期", 
            "strong": "重度伏笔: 明确暗示，制造悬念"
        }
        prompt_parts.append(f"\n## 伏笔强度: {intensity_guide.get(intensity, '正常铺垫')}")
        
        # 添加具体任务指导
        if chapter_context.get("specific_tasks"):
            prompt_parts.append(f"\n## 具体伏笔任务:")
            for task in chapter_context["specific_tasks"]:
                prompt_parts.append(f"- {task}")
        
        return "\n".join(prompt_parts)

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
            if self._is_chapter_in_range(chapter_number, chapter_range):
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

    def _is_chapter_in_range(self, chapter: int, range_str: str) -> bool:
        """检查章节是否在指定范围内"""
        try:
            if "-" in range_str:
                start, end = map(int, range_str.split("-"))
                return start <= chapter <= end
            else:
                return chapter == int(range_str)
        except:
            return False

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

    def get_foreshadowing_opportunities(self, current_chapter: int) -> Dict:
        """获取当前章节的铺垫机会（兼容旧接口）"""
        opportunities = {}
        
        for element_type, elements in self.foreshadowing_elements.items():
            for name, data in elements.items():
                intro_chapter = data["planned_intro_chapter"]
                
                # 如果计划在后续章节出场，且距离出场还有3-10章，开始铺垫
                if current_chapter < intro_chapter and intro_chapter - current_chapter <= 10:
                    # 计算铺垫强度
                    if intro_chapter - current_chapter <= 3:
                        intensity = "strong"
                    elif intro_chapter - current_chapter <= 6:
                        intensity = "medium"
                    else:
                        intensity = "light"
                    
                    if element_type not in opportunities:
                        opportunities[element_type] = []
                    
                    opportunities[element_type].append({
                        "name": name,
                        "intensity": intensity,
                        "planned_intro_chapter": intro_chapter,
                        "chapters_until_intro": intro_chapter - current_chapter
                    })
        
        return opportunities

    def _get_element_type_name(self, element_type: str) -> str:
        """获取元素类型名称"""
        names = {
            "factions": "势力",
            "characters": "角色", 
            "items": "物品",
            "locations": "地点",
            "concepts": "概念"
        }
        return names.get(element_type, element_type)