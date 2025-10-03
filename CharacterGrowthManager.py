from typing import Dict, List


class CharacterGrowthManager:
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.growth_templates = {
            "power_progression": {
                "慢热型": [0.1, 0.3, 0.6, 0.8, 1.0],
                "爆发型": [0.05, 0.2, 0.5, 0.9, 1.0],
                "平稳型": [0.15, 0.35, 0.55, 0.75, 1.0]
            },
            "personality_arcs": {
                "英雄成长": ["天真", "挫折", "觉醒", "成熟", "升华"],
                "反派转变": ["正直", "诱惑", "堕落", "疯狂", "毁灭"],
                "智者启蒙": ["迷茫", "学习", "领悟", "教导", "超脱"]
            }
        }
    
    def design_main_character_growth(self, character_design: Dict, total_chapters: int) -> Dict:
        """设计主角完整成长路线"""
        growth_plan = {
            "power_milestones": self._generate_power_milestones(character_design, total_chapters),
            "personality_evolution": self._generate_personality_evolution(character_design, total_chapters),
            "relationship_development": self._generate_relationship_development(character_design, total_chapters),
            "key_transformation_events": self._generate_transformation_events(character_design, total_chapters)
        }
        return growth_plan
    
    def _generate_power_milestones(self, character: Dict, total_chapters: int) -> List[Dict]:
        """生成力量成长里程碑"""
        power_system = self.generator.novel_data["core_worldview"].get("power_system", "")
        milestones = []
        
        # 根据力量体系设计成长节点
        if "修真" in power_system:
            cultivation_stages = ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫"]
            for i, stage in enumerate(cultivation_stages):
                chapter = int(total_chapters * (i + 1) / (len(cultivation_stages) + 1))
                milestones.append({
                    "stage": stage,
                    "chapter": chapter,
                    "abilities": self._generate_stage_abilities(stage, character),
                    "breakthrough_conditions": self._generate_breakthrough_conditions(stage)
                })
        
        return milestones
    
    def _generate_personality_evolution(self, character: Dict, total_chapters: int) -> List[Dict]:
        """生成性格演变轨迹"""
        personality = character.get("personality", "")
        initial_flaws = character.get("character_flaws", [])
        
        evolution = []
        stages = ["初期", "发展期", "转折期", "成熟期", "巅峰期"]
        
        for i, stage in enumerate(stages):
            chapter_range = self._get_stage_chapter_range(i, len(stages), total_chapters)
            evolution.append({
                "stage": stage,
                "chapter_range": chapter_range,
                "personality_traits": self._get_stage_personality(personality, i, len(stages)),
                "flaws_overcome": self._get_overcome_flaws(initial_flaws, i, len(stages)),
                "key_lessons": self._generate_life_lessons(character, i)
            })
        
        return evolution