# GlobalGrowthPlanner.py
import json
from typing import Dict, List, Optional


class GlobalGrowthPlanner:
    """血肉内容规划器 - 专注阶段内的内容规划（写什么）"""
    
    # 类内部集成的提示词模板
    PROMPTS = {
        "stage_content_planning": """
你是一位资深的网络小说内容架构师。请为小说的特定阶段制定详细的内容规划。

# 阶段信息
**阶段名称**: {stage_name}
**章节范围**: {chapter_range}
**总章节数**: {total_chapters}

# 小说基础信息
**标题**: {novel_title}
**简介**: {novel_synopsis}
**核心世界观**: {worldview_overview}

# 当前阶段特性
{stage_characteristics}

# 内容规划要求
请为这个阶段制定详细的内容规划，专注于"写什么"，包含以下方面：

## 1. 人物成长规划
### 主角成长轨迹
- **性格演变**: 本阶段主角性格会发生什么变化？
- **能力提升**: 具体会掌握哪些新能力或技能？
- **动机深化**: 主角的目标和动机会如何深化？
- **关系发展**: 与重要角色的关系如何变化？

### 配角发展计划
- **重要配角**: 哪些配角需要重点发展？
- **新角色引入**: 需要引入哪些新角色？
- **关系网络**: 角色关系网络如何演变？

## 2. 势力发展规划
### 势力格局变化
- **权力转移**: 势力间的权力平衡如何变化？
- **新联盟**: 会形成哪些新的联盟关系？
- **冲突升级**: 现有冲突如何升级或转化？
- **新兴势力**: 是否有新势力登场？

### 世界观扩展
- **新地域**: 需要展现哪些新地点或场景？
- **文化揭示**: 可以揭示哪些世界观细节？
- **体系完善**: 力量体系或社会体系如何完善？

## 3. 物品功法规划
### 能力突破路线
- **技能解锁**: 主角会解锁哪些新技能？
- **装备升级**: 重要装备如何升级或获得？
- **境界突破**: 修行境界或能力等级如何突破？
- **特殊机缘**: 会获得哪些特殊机缘或物品？

### 系统完善
- **规则揭示**: 需要揭示哪些系统规则？
- **限制突破**: 现有的限制如何被突破？
- **新功能解锁**: 系统会解锁哪些新功能？

## 4. 情感发展计划
### 情感线索
- **主要情感**: 主角的主要情感线如何发展？
- **次要情感**: 配角的情感线如何安排？
- **情感冲突**: 会有什么情感冲突或转折？

## 5. 关键里程碑
列出本阶段必须达成的关键成长节点，每个节点应包含：
- 具体成就
- 发生的大致章节位置
- 对后续剧情的影响

# 输出格式
{{
    "stage_name": "{stage_name}",
    "chapter_range": "{chapter_range}",
    "character_growth_plan": {{
        "protagonist_development": {{
            "personality_evolution": "性格演变描述",
            "ability_advancement": ["新能力1", "新能力2"],
            "motivation_deepening": "动机深化描述",
            "key_growth_moments": [
                {{
                    "moment": "成长时刻描述",
                    "approximate_chapter": "大致章节",
                    "impact": "对后续的影响"
                }}
            ]
        }},
        "supporting_characters_development": {{
            "focus_characters": ["需要重点发展的配角"],
            "new_characters": ["需要引入的新角色"],
            "relationship_evolution": {{
                "character1_character2": "关系变化描述"
            }}
        }}
    }},
    "faction_development_plan": {{
        "power_structure_changes": {{
            "rising_powers": ["新兴势力"],
            "declining_powers": ["衰落势力"],
            "new_alliances": ["新联盟关系"]
        }},
        "conflict_escalation": {{
            "ongoing_conflicts": ["持续冲突及其升级"],
            "new_conflicts": ["新出现的冲突"]
        }},
        "world_building_expansion": {{
            "new_locations": ["新地点"],
            "cultural_revelations": ["文化揭示"],
            "system_refinements": ["体系完善"]
        }}
    }},
    "ability_equipment_plan": {{
        "skill_progression": {{
            "new_skills": ["新技能1", "新技能2"],
            "skill_upgrades": ["技能升级1", "技能升级2"]
        }},
        "equipment_advancement": {{
            "new_equipment": ["新装备"],
            "equipment_upgrades": ["装备升级"]
        }},
        "breakthrough_moments": [
            {{
                "breakthrough": "突破描述",
                "requirements": "突破条件",
                "consequences": "突破后果"
            }}
        ],
        "system_evolution": {{
            "rule_revelations": ["规则揭示"],
            "limitation_breakthroughs": ["限制突破"],
            "new_features": ["新功能解锁"]
        }}
    }},
    "emotional_development_plan": {{
        "main_emotional_arc": "主要情感线发展",
        "secondary_emotional_arcs": ["次要情感线"],
        "emotional_conflicts": ["情感冲突"]
    }},
    "key_milestones": [
        {{
            "milestone": "里程碑描述",
            "chapter_range": "发生章节范围",
            "significance": "重要性说明"
        }}
    ],
    "content_synopsis": "本阶段内容总体概述"
}}
请确保规划具体、可执行，并与前后阶段自然衔接。
"""
    }

    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.stage_content_cache = {}  # 缓存各阶段的内容规划
        self.stage_characteristics = {
            "opening_stage": {
                "focus": "建立基础，引入核心元素",
                "character_growth": "主角初始性格和能力建立",
                "faction_intro": "主要势力格局引入",
                "ability_foundation": "基础能力和装备获得"
            },
            "development_stage": {
                "focus": "深化发展，推进冲突",
                "character_growth": "能力提升和性格深化", 
                "faction_development": "势力关系变化和冲突升级",
                "ability_advancement": "掌握关键技能和突破"
            },
            "climax_stage": {
                "focus": "冲突爆发，重大转折",
                "character_growth": "性格重大转变和成长",
                "faction_climax": "势力冲突达到高潮",
                "ability_peak": "能力质的飞跃和巅峰表现"
            },
            "ending_stage": {
                "focus": "解决矛盾，收束线索", 
                "character_growth": "完成角色弧光",
                "faction_resolution": "势力格局最终确定",
                "ability_mastery": "能力完全掌握"
            },
            "final_stage": {
                "focus": "完整收尾，交代后续",
                "character_growth": "最终成长状态展现",
                "faction_legacy": "势力后续发展",
                "ability_legacy": "能力传承或影响"
            }
        }

    def get_stage_content_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """获取阶段的详细内容规划"""
        cache_key = f"{stage_name}_{chapter_range}"
        
        if cache_key in self.stage_content_cache:
            return self.stage_content_cache[cache_key]
        
        print(f"  📝 生成{stage_name}的内容规划...")
        
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        user_prompt = self.PROMPTS["stage_content_planning"].format(
            stage_name=stage_name,
            chapter_range=chapter_range,
            total_chapters=total_chapters,
            novel_title=novel_data["novel_title"],
            novel_synopsis=novel_data["novel_synopsis"],
            worldview_overview=json.dumps(novel_data.get("core_worldview", {}), ensure_ascii=False),
            stage_characteristics=self._get_stage_characteristics_text(stage_name)
        )
        
        # 生成内容规划
        content_plan = self.generator.api_client.generate_content_with_retry(
            "stage_content_planning",
            user_prompt,
            purpose=f"生成{stage_name}内容规划"
        )
        
        if content_plan:
            self.stage_content_cache[cache_key] = content_plan
            print(f"  ✅ {stage_name}内容规划生成完成")
            self._print_content_plan_summary(content_plan)
            return content_plan
        else:
            print(f"  ⚠️ {stage_name}内容规划生成失败，使用默认规划")
            return self._create_default_content_plan(stage_name, chapter_range)

    def get_chapter_content_context(self, chapter_number: int) -> Dict:
        """获取指定章节的内容规划上下文"""
        if "global_growth_plan" not in self.generator.novel_data:
            return {}
        
        # 获取当前阶段信息
        growth_plan = self.generator.novel_data["global_growth_plan"]
        current_stage = self._get_current_stage(growth_plan, chapter_number)
        
        if not current_stage:
            return {}
        
        # 获取阶段内容规划
        content_plan = self.get_stage_content_plan(
            current_stage["stage_name"], 
            current_stage["chapter_range"]
        )
        
        # 生成章节特定的内容指导
        chapter_context = self._generate_chapter_content_context(
            chapter_number, current_stage, content_plan
        )
        
        return chapter_context

    def _get_stage_characteristics_text(self, stage_name: str) -> str:
        """获取阶段特性的文本描述"""
        chars = self.stage_characteristics.get(stage_name, {})
        return f"""
**阶段重点**: {chars.get('focus', '')}
**人物成长重点**: {chars.get('character_growth', '')}
**势力发展重点**: {chars.get('faction_intro', chars.get('faction_development', chars.get('faction_climax', chars.get('faction_resolution', chars.get('faction_legacy', '')))))}
**能力发展重点**: {chars.get('ability_foundation', chars.get('ability_advancement', chars.get('ability_peak', chars.get('ability_mastery', chars.get('ability_legacy', '')))))}
"""

    def _get_current_stage(self, growth_plan: Dict, chapter: int) -> Optional[Dict]:
        """获取当前章节所属的阶段"""
        for stage in growth_plan.get("stage_framework", []):
            chapter_range = stage["chapter_range"]
            if self._is_chapter_in_range(chapter, chapter_range):
                return stage
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

    def _generate_chapter_content_context(self, chapter: int, stage: Dict, content_plan: Dict) -> Dict:
        """生成章节特定的内容上下文"""
        start_chapter, end_chapter = self._parse_chapter_range(stage["chapter_range"])
        progress_in_stage = (chapter - start_chapter + 1) / (end_chapter - start_chapter + 1)
        
        # 基于进度确定内容重点
        if progress_in_stage < 0.3:
            phase = "阶段初期"
            focus = "建立基础，引入新元素"
        elif progress_in_stage < 0.7:
            phase = "阶段中期"
            focus = "深化发展，推进冲突"
        else:
            phase = "阶段后期"
            focus = "准备转折，达成里程碑"
        
        return {
            "current_stage": stage["stage_name"],
            "stage_progress": phase,
            "content_focus": {
                "character_growth": self._get_character_focus_for_phase(phase, content_plan),
                "faction_development": self._get_faction_focus_for_phase(phase, content_plan),
                "ability_advancement": self._get_ability_focus_for_phase(phase, content_plan),
                "emotional_development": self._get_emotional_focus_for_phase(phase, content_plan)
            },
            "key_milestones_nearby": self._get_nearby_milestones(chapter, content_plan),
            "integration_guidance": f"本阶段{phase}，重点{focus}，应自然衔接前后内容"
        }

    def _get_character_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取人物成长重点"""
        plan = content_plan.get("character_growth_plan", {})
        protagonist = plan.get("protagonist_development", {})
        
        if phase == "阶段初期":
            return f"建立{protagonist.get('personality_evolution', '性格基础')}"
        elif phase == "阶段中期":
            abilities = protagonist.get("ability_advancement", [])
            return f"深化能力发展：{', '.join(abilities[:2]) if abilities else '关键技能掌握'}"
        else:
            moments = protagonist.get("key_growth_moments", [])
            return f"达成成长里程碑：{moments[-1]['moment'] if moments else '重要转变'}"

    def _get_faction_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取势力发展重点"""
        plan = content_plan.get("faction_development_plan", {})
        power_changes = plan.get("power_structure_changes", {})
        conflicts = plan.get("conflict_escalation", {})
        
        if phase == "阶段初期":
            new_powers = power_changes.get("rising_powers", [])
            return f"引入新势力：{', '.join(new_powers[:2]) if new_powers else '势力格局建立'}"
        elif phase == "阶段中期":
            ongoing = conflicts.get("ongoing_conflicts", [])
            return f"冲突升级：{ongoing[0] if ongoing else '势力矛盾深化'}"
        else:
            new_conflicts = conflicts.get("new_conflicts", [])
            return f"新冲突出现：{new_conflicts[0] if new_conflicts else '格局变化'}"

    def _get_ability_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取能力发展重点"""
        plan = content_plan.get("ability_equipment_plan", {})
        skills = plan.get("skill_progression", {})
        breakthroughs = plan.get("breakthrough_moments", [])
        
        if phase == "阶段初期":
            new_skills = skills.get("new_skills", [])
            return f"获得新能力：{', '.join(new_skills[:2]) if new_skills else '基础能力建立'}"
        elif phase == "阶段中期":
            upgrades = skills.get("skill_upgrades", [])
            return f"能力升级：{upgrades[0] if upgrades else '技能强化'}"
        else:
            return f"准备突破：{breakthroughs[-1]['breakthrough'] if breakthroughs else '重要突破'}"

    def _get_emotional_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取情感发展重点"""
        plan = content_plan.get("emotional_development_plan", {})
        main_arc = plan.get("main_emotional_arc", "")
        conflicts = plan.get("emotional_conflicts", [])
        
        if phase == "阶段初期":
            return f"情感线建立：{main_arc.split('。')[0] if main_arc else '关系发展'}"
        elif phase == "阶段中期":
            return f"情感深化：{conflicts[0] if conflicts else '情感冲突'}"
        else:
            return f"情感转折：{main_arc.split('。')[-1] if main_arc else '关系变化'}"

    def _get_nearby_milestones(self, chapter: int, content_plan: Dict) -> List[str]:
        """获取附近的关键里程碑"""
        milestones = content_plan.get("key_milestones", [])
        nearby = []
        
        for milestone in milestones:
            chapter_range = milestone.get("chapter_range", "")
            if self._is_chapter_near_range(chapter, chapter_range):
                nearby.append(milestone["milestone"])
        
        return nearby[:2]  # 返回最近的两个里程碑

    def _is_chapter_near_range(self, chapter: int, range_str: str) -> bool:
        """检查章节是否在里程碑附近"""
        try:
            if "-" in range_str:
                start, end = map(int, range_str.split("-"))
                return start - 3 <= chapter <= end + 3
            else:
                target = int(range_str)
                return target - 3 <= chapter <= target + 3
        except:
            return False

    def _parse_chapter_range(self, range_str: str) -> tuple:
        """解析章节范围字符串"""
        try:
            start, end = map(int, range_str.split("-"))
            return start, end
        except:
            return 1, 100

    def _print_content_plan_summary(self, content_plan: Dict):
        """打印内容规划摘要"""
        stage_name = content_plan.get("stage_name", "未知阶段")
        print(f"    📊 {stage_name}内容规划摘要:")
        
        # 人物成长
        char_plan = content_plan.get("character_growth_plan", {})
        protagonist = char_plan.get("protagonist_development", {})
        abilities = protagonist.get("ability_advancement", [])
        print(f"      人物成长: {len(abilities)}个新能力")
        
        # 势力发展
        faction_plan = content_plan.get("faction_development_plan", {})
        power_changes = faction_plan.get("power_structure_changes", {})
        new_powers = power_changes.get("rising_powers", [])
        print(f"      势力变化: {len(new_powers)}个新势力")
        
        # 里程碑
        milestones = content_plan.get("key_milestones", [])
        print(f"      关键里程碑: {len(milestones)}个")

    def _create_default_content_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """创建默认的内容规划"""
        return {
            "stage_name": stage_name,
            "chapter_range": chapter_range,
            "character_growth_plan": {
                "protagonist_development": {
                    "personality_evolution": "主角性格自然发展",
                    "ability_advancement": ["基础能力提升"],
                    "motivation_deepening": "目标逐步明确",
                    "key_growth_moments": [
                        {
                            "moment": "重要成长节点",
                            "approximate_chapter": "阶段中期",
                            "impact": "推动剧情发展"
                        }
                    ]
                },
                "supporting_characters_development": {
                    "focus_characters": ["重要配角"],
                    "new_characters": ["新角色"],
                    "relationship_evolution": {
                        "主角_配角": "关系自然发展"
                    }
                }
            },
            "faction_development_plan": {
                "power_structure_changes": {
                    "rising_powers": ["新兴势力"],
                    "declining_powers": ["衰落势力"],
                    "new_alliances": ["新联盟"]
                },
                "conflict_escalation": {
                    "ongoing_conflicts": ["持续冲突"],
                    "new_conflicts": ["新冲突"]
                },
                "world_building_expansion": {
                    "new_locations": ["新地点"],
                    "cultural_revelations": ["文化背景"],
                    "system_refinements": ["体系完善"]
                }
            },
            "ability_equipment_plan": {
                "skill_progression": {
                    "new_skills": ["新技能"],
                    "skill_upgrades": ["技能升级"]
                },
                "equipment_advancement": {
                    "new_equipment": ["新装备"],
                    "equipment_upgrades": ["装备升级"]
                },
                "breakthrough_moments": [
                    {
                        "breakthrough": "能力突破",
                        "requirements": "成长积累",
                        "consequences": "实力提升"
                    }
                ],
                "system_evolution": {
                    "rule_revelations": ["规则揭示"],
                    "limitation_breakthroughs": ["限制突破"],
                    "new_features": ["新功能"]
                }
            },
            "emotional_development_plan": {
                "main_emotional_arc": "情感线发展",
                "secondary_emotional_arcs": ["次要情感"],
                "emotional_conflicts": ["情感冲突"]
            },
            "key_milestones": [
                {
                    "milestone": "阶段目标达成",
                    "chapter_range": chapter_range,
                    "significance": "推进故事发展"
                }
            ],
            "content_synopsis": f"{stage_name}的内容发展规划"
        }