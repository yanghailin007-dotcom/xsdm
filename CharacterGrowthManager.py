from typing import Dict, List


class CharacterGrowthManager:
    """人物成长管理器 - 负责主角和配角的成长路线设计"""
    
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
        print("  🎯 设计主角成长路线...")
        
        growth_plan = {
            "power_milestones": self._generate_power_milestones(character_design, total_chapters),
            "personality_evolution": self._generate_personality_evolution(character_design, total_chapters),
            "relationship_development": self._generate_relationship_development(character_design, total_chapters),
            "key_transformation_events": self._generate_transformation_events(character_design, total_chapters)
        }
        
        print(f"  ✅ 主角成长路线设计完成，包含{len(growth_plan['power_milestones'])}个力量里程碑")
        return growth_plan
    
    def _generate_power_milestones(self, character: Dict, total_chapters: int) -> List[Dict]:
        """生成力量成长里程碑"""
        power_system = self.generator.novel_data.get("core_worldview", {}).get("power_system", "")
        milestones = []
        
        # 根据力量体系设计成长节点
        if "修真" in power_system:
            cultivation_stages = ["炼气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫"]
            stage_count = min(len(cultivation_stages), 5)  # 最多5个主要阶段
            
            for i in range(stage_count):
                chapter = int(total_chapters * (i + 1) / (stage_count + 1))
                milestones.append({
                    "stage": cultivation_stages[i],
                    "chapter": chapter,
                    "abilities": self._generate_stage_abilities(cultivation_stages[i], character),
                    "breakthrough_conditions": self._generate_breakthrough_conditions(cultivation_stages[i])
                })
        else:
            # 默认成长阶段
            stages = ["入门", "熟练", "精通", "大成", "巅峰"]
            for i, stage in enumerate(stages):
                chapter = int(total_chapters * (i + 1) / (len(stages) + 1))
                milestones.append({
                    "stage": stage,
                    "chapter": chapter,
                    "abilities": [f"{stage}级技能"],
                    "breakthrough_conditions": [f"达到{stage}境界要求"]
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

    def _get_stage_chapter_range(self, stage_index: int, total_stages: int, total_chapters: int) -> str:
        """计算阶段的章节范围"""
        # 将总章节数按阶段数分配
        chapters_per_stage = total_chapters // total_stages
        start_chapter = stage_index * chapters_per_stage + 1
        end_chapter = (stage_index + 1) * chapters_per_stage
        
        # 处理余数，将多余的章节分配给最后一个阶段
        if stage_index == total_stages - 1:
            end_chapter = total_chapters
        
        return f"{start_chapter}-{end_chapter}"
    
    def _get_stage_personality(self, base_personality: str, stage_index: int, total_stages: int) -> str:
        """获取阶段性格特点"""
        personality_evolution = {
            0: f"{base_personality}，略显青涩",  # 初期
            1: f"{base_personality}，开始成熟",  # 发展期
            2: f"经历转变的{base_personality}",  # 转折期
            3: f"成熟的{base_personality}",      # 成熟期
            4: f"巅峰的{base_personality}"       # 巅峰期
        }
        return personality_evolution.get(stage_index, base_personality)
    
    def _get_overcome_flaws(self, flaws: List[str], stage_index: int, total_stages: int) -> List[str]:
        """获取已克服的性格缺陷"""
        if not flaws:
            return []
        
        # 假设缺陷按阶段逐步克服
        flaws_per_stage = max(1, len(flaws) // total_stages)
        start_index = stage_index * flaws_per_stage
        end_index = min((stage_index + 1) * flaws_per_stage, len(flaws))
        
        return flaws[start_index:end_index]
    
    def _generate_life_lessons(self, character: Dict, stage_index: int) -> List[str]:
        """生成人生教训"""
        base_lessons = [
            "认识到力量的重要性",
            "明白友情的珍贵", 
            "学会承担责任",
            "理解牺牲的意义",
            "领悟生命的真谛"
        ]
        
        lessons_per_stage = 1
        start_index = stage_index * lessons_per_stage
        end_index = start_index + lessons_per_stage
        
        return base_lessons[start_index:end_index]
    
    def _generate_stage_abilities(self, stage: str, character: Dict) -> List[str]:
        """生成阶段能力"""
        ability_templates = {
            "炼气": ["基础吐纳", "简单法术", "体质强化"],
            "筑基": ["御物飞行", "基础阵法", "神识外放"],
            "金丹": ["金丹领域", "高级法术", "法宝操控"],
            "元婴": ["元婴出窍", "空间感知", "大道感悟"],
            "化神": ["神通觉醒", "规则理解", "创造法术"]
        }
        
        return ability_templates.get(stage, [f"{stage}阶段能力"])
    
    def _generate_breakthrough_conditions(self, stage: str) -> List[str]:
        """生成突破条件"""
        condition_templates = {
            "炼气": ["灵气积累", "心境平和", "基础扎实"],
            "筑基": ["筑基丹", "闭关修炼", "机缘感悟"],
            "金丹": ["金丹材料", "天雷淬炼", "大道认可"],
            "元婴": ["元婴功法", "心境突破", "生死考验"],
            "化神": ["神念强大", "规则领悟", "天地认可"]
        }
        
        return condition_templates.get(stage, [f"达到{stage}突破条件"])
    
    def _generate_relationship_development(self, character: Dict, total_chapters: int) -> List[Dict]:
        """生成关系发展轨迹"""
        relationships = []
        stages = ["初识", "发展", "深化", "考验", "稳固"]
        
        for i, stage in enumerate(stages):
            chapter_range = self._get_stage_chapter_range(i, len(stages), total_chapters)
            relationships.append({
                "stage": stage,
                "chapter_range": chapter_range,
                "relationship_focus": f"关系{stage}阶段",
                "key_interactions": [f"{stage}关键互动"],
                "conflict_resolutions": [f"{stage}冲突解决"]
            })
        
        return relationships
    
    def _generate_transformation_events(self, character: Dict, total_chapters: int) -> List[Dict]:
        """生成转变事件"""
        events = []
        milestone_chapters = [
            int(total_chapters * 0.2),  # 20%
            int(total_chapters * 0.4),  # 40%
            int(total_chapters * 0.6),  # 60%
            int(total_chapters * 0.8)   # 80%
        ]
        
        event_types = ["觉醒", "挫折", "蜕变", "升华"]
        
        for i, chapter in enumerate(milestone_chapters):
            if i < len(event_types):
                events.append({
                    "event_type": event_types[i],
                    "chapter": chapter,
                    "description": f"主角经历{event_types[i]}事件",
                    "impact": f"导致{event_types[i]}性转变"
                })
        
        return events
    # 添加其他必要的方法
    def generate_supporting_characters_growth(self, character_design: Dict, total_chapters: int) -> List[Dict]:
        """生成配角成长轨迹"""
        print("  🎯 设计配角成长轨迹...")
        
        supporting_chars = character_design.get("important_characters", [])
        growth_plans = []
        
        for char in supporting_chars[:3]:  # 只处理前3个重要配角
            growth_plan = {
                "character_name": char.get("name", ""),
                "growth_arc": self._generate_supporting_character_arc(char, total_chapters),
                "key_moments": self._generate_supporting_key_moments(char, total_chapters),
                "final_destiny": self._generate_final_destiny(char)
            }
            growth_plans.append(growth_plan)
        
        print(f"  ✅ 配角成长轨迹设计完成，包含{len(growth_plans)}个配角")
        return growth_plans
    
    def _generate_supporting_character_arc(self, character: Dict, total_chapters: int) -> str:
        """生成配角成长轨迹描述"""
        role = character.get("role", "")
        personality = character.get("personality", "")
        
        arc_templates = {
            "盟友": f"{personality}的{role}，随着剧情逐渐成为主角的坚实后盾",
            "敌人": f"{personality}的{role}，与主角从对立到最终和解或被击败",
            "导师": f"{personality}的{role}，指导主角成长后功成身退",
            "恋人": f"{personality}的{role}，与主角共同经历风雨的情感发展"
        }
        
        return arc_templates.get(role, f"{personality}的{role}的成长轨迹")
    
    def _generate_supporting_key_moments(self, character: Dict, total_chapters: int) -> List[str]:
        """生成配角关键时刻"""
        role = character.get("role", "")
        
        moment_templates = {
            "盟友": ["初次相遇", "共同战斗", "生死考验", "最终并肩"],
            "敌人": ["初次交锋", "激烈对抗", "关键对决", "最终结局"],
            "导师": ["初次指导", "关键传授", "离别时刻", "后续影响"],
            "恋人": ["初次心动", "情感发展", "关系考验", "最终相守"]
        }
        
        return moment_templates.get(role, ["重要时刻1", "重要时刻2"])
    
    def _generate_final_destiny(self, character: Dict) -> str:
        """生成配角最终命运"""
        role = character.get("role", "")
        
        destiny_templates = {
            "盟友": "成为主角的终身挚友",
            "敌人": "被主角击败后改邪归正",
            "导师": "完成使命后隐退",
            "恋人": "与主角终成眷属"
        }
        
        return destiny_templates.get(role, "完成角色使命")    