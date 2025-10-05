# ElementTimingPlanner.py
from typing import Dict, List


class ElementTimingPlanner:
    """元素登场时机规划器 - 专门负责各种元素的首次登场和铺垫时机"""
    def __init__(self, novel_generator):
        self.novel_generator = novel_generator
        self.element_timing_plan = {}
        self.foreshadowing_manager = None
        self.project_manager = None  # 将注入ProjectManager实例
        
    def set_project_manager(self, manager):
        """设置项目管理器引用"""
        self.project_manager = manager

    def generate_element_timing_plan(self, global_plan: Dict) -> Dict:
        """生成元素登场时机规划 - 带持久化"""
        print("  ⏰ 生成元素登场时机规划...")
        
        novel_data = self.novel_generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 首先尝试从文件加载现有规划
        if self.project_manager:
            existing_plan = self.project_manager.load_element_timing_plan(novel_data["novel_title"])
            if existing_plan:
                print("  ✅ 从文件加载现有元素登场时机规划")
                self.element_timing_plan = existing_plan
                novel_data["element_timing_plan"] = existing_plan
                
                # 重新注册到伏笔管理器
                self._register_elements_to_foreshadowing(existing_plan)
                return existing_plan
        
        # 如果没有现有规划，生成新的
        all_elements = self._collect_all_elements(novel_data, global_plan)
        timing_plan = self._plan_element_timing(all_elements, total_chapters, global_plan)
        
        if timing_plan:
            self.element_timing_plan = timing_plan
            novel_data["element_timing_plan"] = timing_plan
            
            # 保存到文件
            if self.project_manager:
                self.project_manager.save_element_timing_plan(novel_data["novel_title"], timing_plan)
            
            print("  ✅ 元素登场时机规划完成并已保存")
            self._print_timing_plan_summary(timing_plan)
            
            # 自动注册到伏笔管理器
            self._register_elements_to_foreshadowing(timing_plan)
            
            # 生成并保存章节引入计划
            self._generate_chapter_introduction_schedules(timing_plan, total_chapters)
            
            return timing_plan
        else:
            print("  ❌ 元素登场时机规划生成失败")
            return {}

    def _generate_chapter_introduction_schedules(self, timing_plan: Dict, total_chapters: int):
        """生成并保存各章节的元素引入计划"""
        if not self.project_manager:
            return
        
        novel_title = self.novel_generator.novel_data["novel_title"]
        
        # 按每10章一个区间生成计划
        for start_chapter in range(1, total_chapters + 1, 10):
            end_chapter = min(start_chapter + 9, total_chapters)
            chapter_range = f"{start_chapter}-{end_chapter}"
            
            schedule = self.get_element_introduction_schedule(chapter_range)
            if schedule:
                self.project_manager.save_element_introduction_schedule(novel_title, schedule, chapter_range)

    def load_timing_plan_from_file(self) -> bool:
        """从文件加载时机规划"""
        if not self.project_manager:
            return False
        
        novel_title = self.novel_generator.novel_data["novel_title"]
        timing_plan = self.project_manager.load_element_timing_plan(novel_title)
        
        if timing_plan:
            self.element_timing_plan = timing_plan
            self.novel_generator.novel_data["element_timing_plan"] = timing_plan
            print("  ✅ 从文件加载元素登场时机规划成功")
            
            # 重新注册到伏笔管理器
            self._register_elements_to_foreshadowing(timing_plan)
            return True
        
        return False

    def get_chapter_introduction_plan(self, chapter_number: int) -> Dict:
        """获取指定章节的元素引入计划 - 带缓存"""
        # 首先检查内存中是否有计划
        if self.element_timing_plan:
            return self._get_chapter_introduction_from_plan(chapter_number)
        
        # 如果没有，尝试从文件加载
        if self.load_timing_plan_from_file():
            return self._get_chapter_introduction_from_plan(chapter_number)
        
        return {}

    def _get_chapter_introduction_from_plan(self, chapter_number: int) -> Dict:
        """从时机规划中获取章节引入计划"""
        plan = {
            "characters": [],
            "factions": [],
            "abilities": [],
            "items": [],
            "concepts": []
        }
        
        # 检查角色引入
        for char in self.element_timing_plan.get("character_timing", []):
            if char.get("first_appearance_chapter") == chapter_number:
                plan["characters"].append({
                    "name": char["name"],
                    "type": char.get("type", "角色"),
                    "importance": char.get("importance", "普通"),
                    "foreshadowing_chapter": char.get("foreshadowing_chapter"),
                    "reasoning": char.get("reasoning", "")
                })
        
        # 类似处理其他类别...
        for faction in self.element_timing_plan.get("faction_timing", []):
            if faction.get("first_appearance_chapter") == chapter_number:
                plan["factions"].append({
                    "name": faction["name"],
                    "importance": faction.get("importance", "普通"),
                    "introduction_method": faction.get("introduction_method", "")
                })
        
        for ability in self.element_timing_plan.get("ability_timing", []):
            if ability.get("first_appearance_chapter") == chapter_number:
                plan["abilities"].append({
                    "name": ability["name"],
                    "acquisition_method": ability.get("acquisition_method", "")
                })
        
        return plan
        
    def set_foreshadowing_manager(self, manager):
        """设置伏笔管理器引用"""
        self.foreshadowing_manager = manager
    
    def generate_element_timing_plan(self, global_plan: Dict) -> Dict:
        """基于全局成长规划生成元素登场时机计划"""
        print("  ⏰ 生成元素登场时机规划...")
        
        novel_data = self.novel_generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 准备所有需要规划时机的元素
        all_elements = self._collect_all_elements(novel_data, global_plan)
        
        # 生成时机规划
        timing_plan = self._plan_element_timing(all_elements, total_chapters, global_plan)
        
        self.element_timing_plan = timing_plan
        novel_data["element_timing_plan"] = timing_plan
        
        print("  ✅ 元素登场时机规划完成")
        self._print_timing_plan_summary(timing_plan)
        
        # 自动注册到伏笔管理器
        self._register_elements_to_foreshadowing(timing_plan)
        
        return timing_plan
    
    def _collect_all_elements(self, novel_data: Dict, global_plan: Dict) -> Dict:
        """收集所有需要规划时机的元素"""
        elements = {
            "characters": [],
            "factions": [], 
            "items": [],
            "abilities": [],
            "locations": [],
            "concepts": []
        }
        
        # 从角色设计中收集
        character_design = novel_data.get("character_design", {})
        for char_type, chars in character_design.items():
            if isinstance(chars, list):
                for char in chars:
                    if isinstance(char, dict):
                        elements["characters"].append({
                            "name": char.get("name", "未知角色"),
                            "type": char_type,
                            "importance": char.get("importance", "普通"),
                            "description": char.get("description", "")
                        })
        
        # 从世界观中收集势力和概念
        worldview = novel_data.get("core_worldview", {})
        if "major_factions" in worldview:
            elements["factions"].extend(worldview["major_factions"])
        
        if "core_concepts" in worldview:
            elements["concepts"].extend(worldview["core_concepts"])
        
        # 从能力系统中收集
        ability_system = novel_data.get("ability_system", {})
        if "skill_categories" in ability_system:
            for category in ability_system["skill_categories"]:
                if "skills" in category:
                    elements["abilities"].extend(category["skills"])
        
        return elements
    
    def _plan_element_timing(self, all_elements: Dict, total_chapters: int, global_plan: Dict) -> Dict:
        """为所有元素规划登场时机"""
        
        user_prompt = f"""
请为以下小说的各种元素规划首次登场和铺垫时机：

**小说信息**：
- 总章节：{total_chapters}
- 全局规划阶段：{self._get_stages_summary(global_plan)}

**需要规划时机的元素**：

## 主要角色：
{self._format_elements_for_prompt(all_elements['characters'])}

## 势力组织：
{self._format_elements_for_prompt(all_elements['factions'])}

## 能力功法：
{self._format_elements_for_prompt(all_elements['abilities'])}

## 重要物品：
{self._format_elements_for_prompt(all_elements['items'])}

## 核心概念：
{self._format_elements_for_prompt(all_elements['concepts'])}

**规划要求**：
1. 为每个元素指定首次正式登场的具体章节
2. 如果需要铺垫，指定铺垫章节（比正式登场早3-10章）
3. 根据元素重要性分配不同章节：
   - 核心元素：早期登场（1-30章）
   - 重要元素：中期登场（31-70章） 
   - 次要元素：后期登场（71章以后）
4. 考虑元素间的关联性，相关元素在相近章节登场

请输出JSON格式的时机规划：
{{
    "character_timing": [
        {{
            "name": "角色名",
            "type": "主角/配角/反派",
            "first_appearance_chapter": 具体章节,
            "foreshadowing_chapter": 铺垫章节,
            "importance": "核心/重要/次要",
            "reasoning": "登场时机理由"
        }}
    ],
    "faction_timing": [
        {{
            "name": "势力名", 
            "first_appearance_chapter": 具体章节,
            "foreshadowing_chapter": 铺垫章节,
            "importance": "核心/重要/次要",
            "introduction_method": "直接登场/间接提及"
        }}
    ],
    "ability_timing": [
        {{
            "name": "功法名",
            "first_appearance_chapter": 具体章节,
            "foreshadowing_chapter": 铺垫章节, 
            "acquisition_method": "修炼获得/奇遇/传承"
        }}
    ],
    "item_timing": [
        {{
            "name": "物品名",
            "first_appearance_chapter": 具体章节,
            "foreshadowing_chapter": 铺垫章节,
            "purpose": "战斗/辅助/剧情"
        }}
    ],
    "concept_timing": [
        {{
            "name": "概念名",
            "first_appearance_chapter": 具体章节,
            "explanation_method": "直接说明/通过事件展现"
        }}
    ]
}}
"""
        
        timing_plan = self.novel_generator.api_client.generate_content_with_retry(
            "element_timing_planning",
            user_prompt,
            purpose="生成元素登场时机规划"
        )
        
        return timing_plan or self._create_default_timing_plan(all_elements, total_chapters)
    
    def _register_elements_to_foreshadowing(self, timing_plan: Dict):
        """将元素时机规划注册到伏笔管理器"""
        if not self.foreshadowing_manager:
            print("  ⚠️ 伏笔管理器未设置，无法注册元素")
            return
            
        current_chapter = self.foreshadowing_manager.current_chapter
        
        # 注册角色
        for char in timing_plan.get("character_timing", []):
            self.foreshadowing_manager.register_element(
                element_type="角色",
                element_name=char["name"],
                importance=char.get("importance", "普通"),
                target_chapter=char["first_appearance_chapter"],
                purpose=f"角色登场：{char.get('reasoning', '')}",
                stage_specific=False  # 全局元素
            )
            
            # 如果有铺垫章节，也注册铺垫
            if "foreshadowing_chapter" in char and char["foreshadowing_chapter"] > 0:
                self.foreshadowing_manager.register_element(
                    element_type="角色铺垫",
                    element_name=f"{char['name']}的铺垫",
                    importance="中等",
                    target_chapter=char["foreshadowing_chapter"],
                    purpose=f"为{char['name']}的登场做铺垫",
                    stage_specific=False
                )
        
        # 注册势力（类似逻辑）
        for faction in timing_plan.get("faction_timing", []):
            self.foreshadowing_manager.register_element(
                element_type="势力",
                element_name=faction["name"],
                importance=faction.get("importance", "普通"),
                target_chapter=faction["first_appearance_chapter"],
                purpose=f"势力引入：{faction.get('introduction_method', '')}",
                stage_specific=False
            )
        
        # 注册功法和物品（类似逻辑）
        print("  ✅ 已将所有元素注册到伏笔管理器")
    
    def get_element_introduction_schedule(self, chapter_range: str) -> Dict:
        """获取指定章节范围内需要引入的元素"""
        start_chapter, end_chapter = parse_chapter_range(chapter_range)
        
        schedule = {
            "characters_to_introduce": [],
            "factions_to_introduce": [],
            "abilities_to_introduce": [], 
            "items_to_introduce": [],
            "concepts_to_introduce": []
        }
        
        for category in ["character_timing", "faction_timing", "ability_timing", "item_timing", "concept_timing"]:
            elements = self.element_timing_plan.get(category, [])
            for element in elements:
                if start_chapter <= element["first_appearance_chapter"] <= end_chapter:
                    key = f"{category.split('_')[0]}s_to_introduce"
                    if key in schedule:
                        schedule[key].append(element)
        
        return schedule
    
    def _format_elements_for_prompt(self, elements: List) -> str:
        """格式化元素列表用于提示词"""
        if not elements:
            return "无"
        
        formatted = []
        for elem in elements[:10]:  # 限制数量避免过长
            if isinstance(elem, dict):
                name = elem.get('name', '未知')
                desc = elem.get('description', elem.get('purpose', ''))
                formatted.append(f"- {name}: {desc}")
            else:
                formatted.append(f"- {elem}")
        
        return "\n".join(formatted)
    
    def _get_stages_summary(self, global_plan: Dict) -> str:
        """获取阶段摘要"""
        if not global_plan or "stage_framework" not in global_plan:
            return "未知阶段划分"
        
        stages = []
        for stage in global_plan["stage_framework"]:
            stages.append(f"{stage['stage_name']}({stage['chapter_range']})")
        
        return " | ".join(stages)
    
    def _create_default_timing_plan(self, all_elements: Dict, total_chapters: int) -> Dict:
        """创建默认的时机规划"""
        plan = {
            "character_timing": [],
            "faction_timing": [],
            "ability_timing": [],
            "item_timing": [],
            "concept_timing": []
        }
        
        # 简单分配：核心元素在前1/3，重要元素在中间1/3，次要元素在后1/3
        core_end = total_chapters // 3
        important_end = 2 * total_chapters // 3
        
        # 分配角色
        for i, char in enumerate(all_elements["characters"][:10]):  # 限制数量
            if i < 3:  # 核心角色
                chapter = max(1, i + 1)
            elif i < 7:  # 重要角色
                chapter = core_end + i - 2
            else:  # 次要角色
                chapter = important_end + i - 6
                
            plan["character_timing"].append({
                "name": char.get("name", f"角色{i+1}"),
                "type": char.get("type", "配角"),
                "first_appearance_chapter": min(chapter, total_chapters),
                "foreshadowing_chapter": max(1, chapter - 3),
                "importance": "核心" if i < 3 else "重要" if i < 7 else "次要",
                "reasoning": "默认分配"
            })
        
        return plan
    
    def _print_timing_plan_summary(self, timing_plan: Dict):
        """打印时机规划摘要"""
        print("    ⏰ 元素登场时机规划摘要:")
        
        for category, elements in timing_plan.items():
            if elements:
                early = len([e for e in elements if e.get("first_appearance_chapter", 999) <= 30])
                mid = len([e for e in elements if 31 <= e.get("first_appearance_chapter", 0) <= 70])
                late = len([e for e in elements if e.get("first_appearance_chapter", 0) >= 71])
                
                category_name = category.replace("_timing", "").title()
                print(f"      {category_name}: 早期{early}个, 中期{mid}个, 后期{late}个")