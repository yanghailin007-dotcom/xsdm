# GlobalGrowthPlanner.py
import json
from typing import Dict, List, Optional
from utils import parse_chapter_range, is_chapter_in_range

class GlobalGrowthPlanner:
    """全局血肉内容规划器 - 负责全书和阶段内的内容规划（写什么）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.config = novel_generator.config
        self.Prompts = novel_generator.Prompts
        self.stage_content_cache = {}  # 缓存各阶段的内容规划
        self.global_growth_plan = None  # 全书成长规划
        
        # 从config读取阶段特性
        self.stage_characteristics = self.Prompts.get("stage_characteristics", {
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
        })

    def generate_global_growth_plan(self) -> Dict:
        """生成全书的全局成长规划"""
        print("  📚 生成全书全局成长规划...")
        
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 添加小说基础信息
        user_prompt = f"""
你正在为以下小说制定全局成长规划：

**小说标题**: {novel_data["novel_title"]}
**小说简介**: {novel_data["novel_synopsis"]}
**总章节**: {total_chapters}
**核心世界观**: {json.dumps(novel_data.get('core_worldview', {}), ensure_ascii=False)}
**主要角色**: {json.dumps(novel_data.get('character_design', {}), ensure_ascii=False)}

请基于以上信息制定贯穿总章节: {total_chapters}章全书的完整成长规划。
"""
        
        # 生成全局成长规划
        global_plan = self.generator.api_client.generate_content_with_retry(
            "global_growth_planning",
            user_prompt,
            purpose="生成全书全局成长规划"
        )
        
        if global_plan:
            self.global_growth_plan = global_plan
            self.generator.novel_data["global_growth_plan"] = global_plan
            print("  ✅ 全书全局成长规划生成完成")
            self._print_global_plan_summary(global_plan)
            return global_plan
        else:
            print("  ⚠️ 全书全局成长规划生成失败，使用默认规划")
            return self._create_default_global_plan(total_chapters)

    def get_stage_content_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """获取阶段的详细内容规划"""
        cache_key = f"{stage_name}_{chapter_range}"
        
        if cache_key in self.stage_content_cache:
            return self.stage_content_cache[cache_key]
        
        print(f"  📝 生成{stage_name}的内容规划...")
        
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 从config获取提示词
        prompt_template = self.Prompts["prompts"]["stage_content_planning"]
        
        user_prompt = prompt_template.format(
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
        if not self.global_growth_plan:
            # 如果没有全局规划，先生成一个
            self.generate_global_growth_plan()
        
        # 获取当前阶段信息
        current_stage = self._get_current_stage(self.global_growth_plan, chapter_number)
        
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
        
        # 修复势力发展重点的获取逻辑
        faction_key = None
        for key in ['faction_intro', 'faction_development', 'faction_climax', 'faction_resolution', 'faction_legacy']:
            if key in chars:
                faction_key = key
                break
        
        # 修复能力发展重点的获取逻辑  
        ability_key = None
        for key in ['ability_foundation', 'ability_advancement', 'ability_peak', 'ability_mastery', 'ability_legacy']:
            if key in chars:
                ability_key = key
                break
        
        return f"""
    **阶段重点**: {chars.get('focus', '')}
    **人物成长重点**: {chars.get('character_growth', '')}
    **势力发展重点**: {chars.get(faction_key, '') if faction_key else ''}
    **能力发展重点**: {chars.get(ability_key, '') if ability_key else ''}
    """

    def _get_current_stage(self, growth_plan: Dict, chapter: int) -> Optional[Dict]:
        """获取当前章节所属的阶段"""
        for stage in growth_plan.get("stage_framework", []):
            chapter_range = stage["chapter_range"]
            if is_chapter_in_range(chapter, chapter_range):
                return stage
        return None

    def _generate_chapter_content_context(self, chapter: int, stage: Dict, content_plan: Dict) -> Dict:
        """生成章节特定的内容上下文"""
        start_chapter, end_chapter = parse_chapter_range(stage["chapter_range"])
        stage_length = end_chapter - start_chapter + 1
        
        if stage_length == 0:  # 避免除零错误
            progress_in_stage = 0
        else:
            progress_in_stage = (chapter - start_chapter + 1) / stage_length
        
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
            if abilities and len(abilities) > 0:
                return f"深化能力发展：{', '.join(abilities[:2])}"
            else:
                return "关键技能掌握"
        else:
            moments = protagonist.get("key_growth_moments", [])
            if moments and len(moments) > 0:
                return f"达成成长里程碑：{moments[-1].get('moment', '重要转变')}"
            else:
                return "重要转变"

    def _get_faction_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取势力发展重点"""
        plan = content_plan.get("faction_development_plan", {})
        power_changes = plan.get("power_structure_changes", {})
        conflicts = plan.get("conflict_escalation", {})
        
        if phase == "阶段初期":
            new_powers = power_changes.get("rising_powers", [])
            if new_powers and len(new_powers) > 0:
                return f"引入新势力：{', '.join(new_powers[:2])}"
            else:
                return "势力格局建立"
        elif phase == "阶段中期":
            ongoing = conflicts.get("ongoing_conflicts", [])
            if ongoing and len(ongoing) > 0:
                return f"冲突升级：{ongoing[0]}"
            else:
                return "势力矛盾深化"
        else:
            new_conflicts = conflicts.get("new_conflicts", [])
            if new_conflicts and len(new_conflicts) > 0:
                return f"新冲突出现：{new_conflicts[0]}"
            else:
                return "格局变化"

    def _get_ability_focus_for_phase(self, phase: str, content_plan: Dict) -> str:
        """根据阶段进度获取能力发展重点"""
        plan = content_plan.get("ability_equipment_plan", {})
        skills = plan.get("skill_progression", {})
        breakthroughs = plan.get("breakthrough_moments", [])
        
        if phase == "阶段初期":
            new_skills = skills.get("new_skills", [])
            if new_skills and len(new_skills) > 0:
                return f"获得新能力：{', '.join(new_skills[:2])}"
            else:
                return "基础能力建立"
        elif phase == "阶段中期":
            upgrades = skills.get("skill_upgrades", [])
            if upgrades and len(upgrades) > 0:
                return f"能力升级：{upgrades[0]}"
            else:
                return "技能强化"
        else:
            if breakthroughs and len(breakthroughs) > 0:
                return f"准备突破：{breakthroughs[-1].get('breakthrough', '重要突破')}"
            else:
                return "重要突破"


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

    def _is_chapter_near_range(self, chapter: int, chapter_range: str, window: int = 3) -> bool:
        """检查章节是否在指定范围的附近（前后window章）"""
        start_chapter, end_chapter = parse_chapter_range(chapter_range)
        
        # 检查章节是否在范围内
        if start_chapter <= chapter <= end_chapter:
            return True
        
        # 检查章节是否在范围附近（前后window章）
        if (start_chapter - window <= chapter <= start_chapter - 1) or \
        (end_chapter + 1 <= chapter <= end_chapter + window):
            return True
        
        return False



    def get_context(self, chapter_number: int) -> Dict:
        """获取章节的成长规划上下文"""
        return self.get_chapter_content_context(chapter_number)

    def get_chapter_content_context(self, chapter_number: int) -> Dict:
        """获取指定章节的内容规划上下文 - 具体实现"""
        if not self.global_growth_plan:
            # 如果没有全局规划，先生成一个
            self.generate_global_growth_plan()
        
        # 获取当前阶段信息
        current_stage = self._get_current_stage(self.global_growth_plan, chapter_number)
        
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

    def _print_global_plan_summary(self, global_plan: Dict):
        """打印全局规划摘要"""
        print("    📊 全书全局成长规划摘要:")
        
        # 阶段框架
        stages = global_plan.get("stage_framework", [])
        print(f"      阶段划分: {len(stages)}个主要阶段")
        
        # 人物成长
        character_arcs = global_plan.get("character_growth_arcs", {})
        protagonist = character_arcs.get("protagonist", {})
        print(f"      主角成长弧线: {protagonist.get('overall_arc', '完整发展')}")
        
        # 势力发展
        faction_trajectory = global_plan.get("faction_development_trajectory", {})
        print(f"      势力发展: {len(faction_trajectory)}个主要势力")
        
        # 能力系统
        ability_evolution = global_plan.get("ability_system_evolution", {})
        breakthroughs = ability_evolution.get("breakthrough_milestones", [])
        print(f"      能力突破点: {len(breakthroughs)}个关键里程碑")

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

    def _create_default_global_plan(self, total_chapters: int) -> Dict:
        """创建默认的全局成长规划"""
        return {
            "overview": f"全书{total_chapters}章的完整成长规划",
            "stage_framework": [
                {
                    "stage_name": "开局阶段",
                    "chapter_range": f"1-{int(total_chapters*0.15)}",
                    "core_objectives": ["建立故事基础", "引入核心冲突"],
                    "key_growth_themes": ["初始成长", "能力觉醒"],
                    "milestone_events": ["主角觉醒", "初次冲突"]
                },
                {
                    "stage_name": "发展阶段",
                    "chapter_range": f"{int(total_chapters*0.15)+1}-{int(total_chapters*0.45)}",
                    "core_objectives": ["深化矛盾", "角色成长"],
                    "key_growth_themes": ["能力提升", "关系建立"],
                    "milestone_events": ["关键突破", "重要联盟"]
                },
                {
                    "stage_name": "高潮阶段", 
                    "chapter_range": f"{int(total_chapters*0.45)+1}-{int(total_chapters*0.8)}",
                    "core_objectives": ["冲突爆发", "重大转折"],
                    "key_growth_themes": ["巅峰对决", "真相揭露"],
                    "milestone_events": ["最终对决", "真相大白"]
                },
                {
                    "stage_name": "收尾阶段",
                    "chapter_range": f"{int(total_chapters*0.8)+1}-{int(total_chapters*0.95)}", 
                    "core_objectives": ["解决矛盾", "收束线索"],
                    "key_growth_themes": ["圆满收尾", "情感升华"],
                    "milestone_events": ["矛盾解决", "伏笔回收"]
                },
                {
                    "stage_name": "结局阶段",
                    "chapter_range": f"{int(total_chapters*0.95)+1}-{total_chapters}",
                    "core_objectives": ["完整收尾", "交代后续"],
                    "key_growth_themes": ["最终归宿", "主题升华"],
                    "milestone_events": ["大结局", "后记"]
                }
            ],
            "character_growth_arcs": {
                "protagonist": {
                    "overall_arc": "从平凡到非凡的完整成长历程",
                    "stage_specific_growth": {
                        "开局阶段": {
                            "personality_development": "建立基础性格",
                            "ability_progression": "获得初始能力", 
                            "relationship_evolution": "建立初始关系"
                        }
                    }
                }
            },
            "faction_development_trajectory": {
                "主要势力": {
                    "development_path": "势力发展路径",
                    "key_expansion_points": ["关键扩张"],
                    "relationship_evolution": "关系演变"
                }
            },
            "ability_system_evolution": {
                "skill_progression_path": "技能成长路线",
                "equipment_upgrade_roadmap": "装备升级规划", 
                "breakthrough_milestones": ["重要突破"]
            },
            "emotional_development_journey": {
                "main_emotional_arc": "主要情感发展",
                "relationship_development_phases": ["关系建立阶段"],
                "emotional_climax_points": ["情感高潮"]
            }
        }

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