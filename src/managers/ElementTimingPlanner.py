# ElementTimingPlanner.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from typing import Dict, List
from src.utils.logger import get_logger
from src.managers.StagePlanUtils import parse_chapter_range
class ElementTimingPlanner:
    """元素登场时机规划器 - 专门负责各种元素的首次登场和铺垫时机"""
    def __init__(self, novel_generator):
        self.logger = get_logger("ElementTimingPlanner")
        self.novel_generator = novel_generator
        self.element_timing_plan = {}
        self.foreshadowing_manager = None
        self.project_manager = None  # 将注入ProjectManager实例
    def set_project_manager(self, manager):
        """设置项目管理器引用"""
        self.project_manager = manager
    def generate_element_timing_plan(self, global_growth_plan: Dict, overall_stage_plans: Dict) -> Dict:
        """生成元素登场时机规划 - 带持久化"""
        self.logger.info("  ⏰ 生成元素登场时机规划...")
        novel_data = self.novel_generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        # 首先尝试从文件加载现有规划
        if self.project_manager:
            existing_plan = self.project_manager.load_element_timing_plan(novel_data["novel_title"])
            if existing_plan:
                self.logger.info("  ✅ 从文件加载现有元素登场时机规划")
                self.element_timing_plan = existing_plan
                novel_data["element_timing_plan"] = existing_plan
                # 重新注册到伏笔管理器
                self._register_elements_to_foreshadowing(existing_plan)
                return existing_plan
        # 如果没有现有规划，生成新的
        all_elements = self._collect_all_elements(novel_data, global_growth_plan)
        timing_plan = self._plan_element_timing(all_elements, total_chapters, global_growth_plan, overall_stage_plans)
        if timing_plan:
            self.element_timing_plan = timing_plan
            novel_data["element_timing_plan"] = timing_plan
            # 保存到文件
            if self.project_manager:
                self.project_manager.save_element_timing_plan(novel_data["novel_title"], timing_plan)
            self.logger.info("  ✅ 元素登场时机规划完成并已保存")
            self._print_timing_plan_summary(timing_plan)
            # 自动注册到伏笔管理器
            self._register_elements_to_foreshadowing(timing_plan)
            # 生成并保存章节引入计划
            self._generate_chapter_introduction_schedules(timing_plan, total_chapters)
            return timing_plan
        else:
            self.logger.info("  ❌ 元素登场时机规划生成失败")
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
            self.logger.info("  ✅ 从文件加载元素登场时机规划成功")
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
    def _collect_all_elements(self, novel_data: Dict, global_plan: Dict) -> Dict:
        """收集所有需要规划时机的元素 - 修复版"""
        self.logger.info("  🔍 开始收集所有元素...")
        elements = {
            "characters": [],
            "factions": [], 
            "items": [],
            "abilities": [],
            "locations": [],
            "concepts": []
        }
        # 1. 收集角色 - 修复角色收集逻辑
        character_design = novel_data.get("character_design", {})
        # 收集主角
        main_char = character_design.get("main_character", {})
        if main_char and isinstance(main_char, dict):
            elements["characters"].append({
                "name": main_char.get("name", "主角"),
                "type": "主角",
                "importance": "核心",
                "description": f"{main_char.get('personality', '')} - {main_char.get('background', '')}"
            })
        # 收集重要角色
        important_chars = character_design.get("important_characters", [])
        for char in important_chars:
            if isinstance(char, dict):
                elements["characters"].append({
                    "name": char.get("name", "未知角色"),
                    "type": char.get("role", "配角"),
                    "importance": "重要",
                    "description": f"{char.get('personality', '')} - {char.get('purpose', '')}"
                })
        # 2. 收集世界观元素
        worldview = novel_data.get("core_worldview", {})
        self.logger.info(f"  🔍 世界观数据: {type(worldview)}, 内容: {worldview.keys() if isinstance(worldview, dict) else '非字典类型'}")
        # 收集势力 - 修复：从世界观中收集
        if "major_factions" in worldview:
            for faction in worldview["major_factions"]:
                if isinstance(faction, dict):
                    elements["factions"].append({
                        "name": faction.get("name", "未知势力"),
                        "description": faction.get("description", faction.get("purpose", ""))
                    })
                else:
                    elements["factions"].append({
                        "name": str(faction),
                        "description": "世界观中的主要势力"
                    })
        # 收集核心概念
        if "core_concepts" in worldview:
            for concept in worldview["core_concepts"]:
                if isinstance(concept, dict):
                    elements["concepts"].append({
                        "name": concept.get("name", "未知概念"),
                        "description": concept.get("description", "")
                    })
                else:
                    elements["concepts"].append({
                        "name": str(concept),
                        "description": "世界观核心概念"
                    })
        # 收集时代背景
        if "era" in worldview:
            elements["concepts"].append({
                "name": "时代背景",
                "description": worldview["era"]
            })
        # 收集核心冲突
        if "core_conflict" in worldview:
            elements["concepts"].append({
                "name": "核心冲突",
                "description": worldview["core_conflict"]
            })
        # 3. 收集能力系统 - 修复系统名称提取
        ability_system = novel_data.get("ability_system", {})
        # 动态提取能力系统名称
        if "power_system" in worldview:
            power_desc = worldview["power_system"]
            self.logger.info(f"  🔍 能力系统描述类型: {type(power_desc)}, 内容: {power_desc}")
            # 尝试从描述中提取系统名称
            system_name = self._extract_system_name(power_desc)
            elements["abilities"].append({
                "name": system_name,
                "description": power_desc
            })
        # 收集技能分类
        if "skill_categories" in ability_system:
            for category in ability_system["skill_categories"]:
                if "skills" in category:
                    for skill in category["skills"]:
                        if isinstance(skill, dict):
                            elements["abilities"].append({
                                "name": skill.get("name", "未知技能"),
                                "description": skill.get("description", "")
                            })
                        else:
                            elements["abilities"].append({
                                "name": str(skill),
                                "description": "系统能力"
                            })
        # 4. 从全局成长计划中收集额外元素 - 修复：正确处理列表类型
        if global_plan:
            self.logger.info(f"  🔍 全局成长计划类型: {type(global_plan)}, 内容: {global_plan.keys()}")
            # 收集成长阶段
            stages = global_plan.get("stage_framework", [])
            for stage in stages:
                elements["concepts"].append({
                    "name": f"{stage.get('stage_name', '阶段')}规划",
                    "description": f"目标: {', '.join(stage.get('core_objectives', []))}"
                })
            # 修复：正确处理 faction_development_trajectory 列表
            faction_trajectory = global_plan.get("faction_development_trajectory", [])
            for faction_info in faction_trajectory:
                if isinstance(faction_info, dict):
                    faction_name = faction_info.get("name", "未知势力")
                    if faction_name not in [f["name"] for f in elements["factions"]]:
                        elements["factions"].append({
                            "name": faction_name,
                            "description": f"发展路径: {faction_info.get('development_path', '')}"
                        })
        # 5. 从阶段写作计划中收集事件元素
        stage_plans = novel_data.get("stage_writing_plans", {})
        for stage_name, stage_data in stage_plans.items():
            writing_plan = stage_data.get("stage_writing_plan", {})
            # 收集重大事件
            event_system = writing_plan.get("event_system", {})
            major_events = event_system.get("major_events", [])
            for event in major_events:
                elements["concepts"].append({
                    "name": event.get("name", "重大事件"),
                    "description": f"重大事件: {event.get('main_goal', '')}"
                })
            # 收集大事件
            big_events = event_system.get("big_events", [])
            for event in big_events:
                elements["concepts"].append({
                    "name": event.get("name", "大事件"),
                    "description": f"大事件: {event.get('main_goal', '')}"
                })
        # 6. 从市场分析中收集热门元素
        market_analysis = novel_data.get("market_analysis", {})
        if "hot_elements" in worldview:
            for element in worldview["hot_elements"]:
                elements["concepts"].append({
                    "name": f"热门元素: {element}",
                    "description": "吸引读者的热门设定"
                })
        # 7. 收集核心卖点作为概念
        selling_points = market_analysis.get("core_selling_points", [])
        for i, point in enumerate(selling_points):
            elements["concepts"].append({
                "name": f"核心卖点{i+1}",
                "description": point
            })
        self.logger.info(f"  📊 元素收集统计: 角色{len(elements['characters'])}个, 势力{len(elements['factions'])}个, "
            f"能力{len(elements['abilities'])}个, 概念{len(elements['concepts'])}个")
        return elements
    def _extract_system_name(self, power_system_description: str) -> str:
        """从能力系统描述中提取系统名称"""
        import re
        self.logger.info(f"  🔍 _extract_system_name 输入类型: {type(power_system_description)}, 内容: {power_system_description}")
        # 如果输入不是字符串，尝试转换为字符串
        if not isinstance(power_system_description, str):
            self.logger.info(f"  ⚠️  power_system_description 不是字符串，进行转换")
            try:
                if isinstance(power_system_description, dict):
                    # 如果是字典，尝试提取描述字段
                    power_system_description = power_system_description.get('description', str(power_system_description))
                else:
                    power_system_description = str(power_system_description)
                self.logger.info(f"  🔍 转换后内容: {power_system_description}")
            except Exception as e:
                self.logger.info(f"  ❌ 转换失败: {e}")
                return "核心能力系统"
        # 常见系统名称模式
        patterns = [
            r'(.+?)系统',  # 匹配"XXX系统"
            r'(.+?)能力',  # 匹配"XXX能力"  
            r'(.+?)功法',  # 匹配"XXX功法"
            r'(.+?)技能',  # 匹配"XXX技能"
            r'(.+?)金手指',  # 匹配"XXX金手指"
        ]
        for pattern in patterns:
            match = re.search(pattern, power_system_description)
            if match:
                result = match.group(1).strip() + pattern[2:]  # 返回匹配到的名称+后缀
                self.logger.info(f"  🔍 正则匹配成功: {result}")
                return result
        # 如果没匹配到特定模式，尝试提取前几个词作为名称
        words = power_system_description.split()
        if len(words) > 0:
            # 取前2-3个词作为系统名称
            name_words = words[:min(3, len(words))]
            result = "".join(name_words) + "系统"
            self.logger.info(f"  🔍 使用单词提取: {result}")
            return result
        # 默认名称
        self.logger.info(f"  🔍 使用默认名称")
        return "核心能力系统"
    def _plan_element_timing(self, all_elements: Dict, total_chapters: int, global_growth_plan: Dict, overall_stage_plans: Dict) -> Dict:
        """为所有元素规划登场时机"""
        self.logger.info(f"  🔍 _plan_element_timing 开始规划，总章节: {total_chapters}")
        self.logger.info(f"  🔍 全局成长计划类型: {type(global_growth_plan)}")
        self.logger.info(f"  🔍 整体阶段计划类型: {type(overall_stage_plans)}")
        user_prompt = f"""
内容:
请根据以下小说设定、大纲和元素列表，为各元素规划登场时机。
## 小说核心设定与大纲
**小说信息**：
- 总章节：{total_chapters}
- 全局成长计划：{global_growth_plan}
- 全局写作计划：{overall_stage_plans}
---
## 待规划元素列表
请为以下清单中的所有元素规划登场时机：
### 1. 角色 (Characters)
{self._format_elements_for_prompt(all_elements['characters'])}
### 2. 势力 (Factions)
{self._format_elements_for_prompt(all_elements['factions'])}
### 3. 核心能力与造物 (Abilities & Creations)
{self._format_elements_for_prompt(all_elements['abilities'])}
{self._format_elements_for_prompt(all_elements['items'])}
### 4. 核心概念 (Concepts)
{self._format_elements_for_prompt(all_elements['concepts'])}
"""
        try:
            timing_plan = self.novel_generator.api_client.generate_content_with_retry(
                "element_timing_planning",
                user_prompt,
                purpose="生成元素登场时机规划"
            )
            self.logger.info(f"  🔍 API返回结果类型: {type(timing_plan)}")
            return timing_plan or self._create_default_timing_plan(all_elements, total_chapters)
        except Exception as e:
            self.logger.info(f"  ❌ _plan_element_timing 出错: {e}")
            import traceback
            traceback.print_exc()
            return self._create_default_timing_plan(all_elements, total_chapters)
    def _register_elements_to_foreshadowing(self, timing_plan: Dict):
        """将元素时机规划注册到伏笔管理器"""
        if not self.foreshadowing_manager:
            self.logger.info("  ⚠️ 伏笔管理器未设置，无法注册元素")
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
            foreshadowing_chapter = char.get("foreshadowing_chapter")
            if foreshadowing_chapter is not None and foreshadowing_chapter > 0:
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
        self.logger.info("  ✅ 已将所有元素注册到伏笔管理器")
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
        self.logger.info("  🔍 创建默认时机规划")
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
        self.logger.info(f"  🔍 默认规划完成: {len(plan['character_timing'])} 个角色")
        return plan
    def _print_timing_plan_summary(self, timing_plan: Dict):
        """打印时机规划摘要"""
        self.logger.info("    ⏰ 元素登场时机规划摘要:")
        for category, elements in timing_plan.items():
            if elements:
                early = len([e for e in elements if e.get("first_appearance_chapter", 999) <= 30])
                mid = len([e for e in elements if 31 <= e.get("first_appearance_chapter", 0) <= 70])
                late = len([e for e in elements if e.get("first_appearance_chapter", 0) >= 71])
                category_name = category.replace("_timing", "").title()
                self.logger.info(f"      {category_name}: 早期{early}个, 中期{mid}个, 后期{late}个")