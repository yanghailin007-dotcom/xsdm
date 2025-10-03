import json
from typing import Dict, List


class GlobalGrowthPlanner:
    """全局成长规划管理器 - 在全书层面设计所有成长系统"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
    
    def create_comprehensive_growth_plan(self, creative_seed: str, novel_title: str, 
                                       novel_synopsis: str, total_chapters: int) -> Dict:
        """创建全书综合成长计划"""
        print("=== 制定全书成长规划 ===")
        
        # 收集所有必要的基础数据
        worldview = self.generator.novel_data["core_worldview"]
        character_design = self.generator.novel_data["character_design"]
        market_analysis = self.generator.novel_data["market_analysis"]
        
        user_prompt = f"""
# 小说基础信息
**创意种子**: {creative_seed}
**小说标题**: {novel_title}
**小说简介**: {novel_synopsis}
**总章节数**: {total_chapters}

# 世界观设定
{json.dumps(worldview, ensure_ascii=False)}

# 角色设计
{json.dumps(character_design, ensure_ascii=False)}

# 市场分析
{json.dumps(market_analysis, ensure_ascii=False)}

# 制定全书成长规划
请为这部小说制定一个完整的成长规划，包含以下四个核心系统：

## 1. 人物成长体系
设计主角和重要配角的完整成长轨迹：

### 主角成长路线
- **能力成长**: 从弱到强的具体阶段和里程碑
- **性格演变**: 性格转变的关键节点和原因  
- **人际关系**: 与各角色的关系发展轨迹
- **价值观变化**: 世界观和价值观的演变过程

### 配角成长设计
- **重要配角**: 主要配角的独立成长线
- **关系网络**: 角色间关系的动态变化
- **命运轨迹**: 各角色的最终归宿

## 2. 势力发展体系  
设计世界中各势力的发展轨迹：

### 势力成长规划
- **势力兴衰**: 各势力的崛起、鼎盛、衰落时间线
- **权力平衡**: 不同阶段的世界格局变化
- **冲突演变**: 势力间冲突的升级和解决
- **外交关系**: 联盟、敌对关系的动态变化

## 3. 物品升级体系
设计功法、技能、装备的升级路径：

### 功法技能系统
- **修炼体系**: 完整的境界和等级划分
- **技能树**: 技能解锁和升级的条件
- **突破机制**: 关键突破的时机和条件

### 装备宝物系统  
- **装备等级**: 从凡器到神器的完整路径
- **强化机制**: 装备升级和强化的方式
- **获取途径**: 重要宝物的获得时机

## 4. 阶段性角色规划
设计各阶段需要的临时角色：

### 阶段角色分配
- **角色类型**: 各阶段需要的角色类型和数量
- **出场时机**: 角色出场和退场的合理时机
- **功能定位**: 每个角色在阶段中的具体作用

# 输出格式
{{
    "character_growth_plan": {{
        "main_character_timeline": [
            {{
                "stage": "阶段名称",
                "chapters": "章节范围",
                "ability_level": "能力水平",
                "key_breakthroughs": ["关键突破1", "关键突破2"],
                "personality_changes": "性格变化",
                "relationship_developments": ["关系发展1", "关系发展2"]
            }}
        ],
        "supporting_characters_growth": [
            {{
                "character_name": "角色姓名", 
                "growth_arc": "成长轨迹描述",
                "key_moments": ["关键时刻1", "关键时刻2"],
                "final_destiny": "最终命运"
            }}
        ]
    }},
    "faction_development_plan": {{
        "faction_timelines": [
            {{
                "faction_name": "势力名称",
                "development_stages": [
                    {{
                        "stage": "发展阶段",
                        "chapters": "章节范围",
                        "power_level": "势力强度", 
                        "key_events": ["关键事件1", "关键事件2"],
                        "territory_changes": "领土变化",
                        "relationship_changes": {{
                            "allies": ["盟友"],
                            "enemies": ["敌人"]
                        }}
                    }}
                ]
            }}
        ],
        "world_power_balance": [
            {{
                "chapters": "章节范围", 
                "dominant_powers": ["主导势力"],
                "rising_powers": ["新兴势力"],
                "declining_powers": ["衰落势力"]
            }}
        ]
    }},
    "item_upgrade_plan": {{
        "cultivation_system": {{
            "realm_progression": [
                {{
                    "realm": "境界名称",
                    "typical_chapters": "通常达到的章节范围",
                    "abilities_unlocked": ["解锁能力1", "解锁能力2"],
                    "breakthrough_requirements": ["突破要求1", "突破要求2"],
                    "significance": "境界意义"
                }}
            ]
        }},
        "equipment_upgrade_paths": [
            {{
                "item_type": "物品类型",
                "upgrade_stages": [
                    {{
                        "tier": "等级",
                        "chapters": "获得/升级章节", 
                        "special_effects": ["特殊效果"],
                        "upgrade_materials": ["升级材料"]
                    }}
                ]
            }}
        ]
    }},
    "phase_character_blueprint": {{
        "stage_character_requirements": [
            {{
                "stage_name": "阶段名称",
                "required_character_types": ["需要角色类型1", "需要角色类型2"],
                "estimated_character_count": 预计角色数量,
                "key_functions": ["关键功能1", "关键功能2"]
            }}
        ]
    }}
}}
"""
        
        result = self.generator.api_client.generate_content_with_retry(
            "global_growth_planning",
            user_prompt,
            purpose="制定全书成长规划"
        )
        
        if result:
            print("✅ 全书成长规划制定完成")
            self._print_growth_plan_summary(result)
            return result
        else:
            print("❌ 全书成长规划制定失败")
            return self._create_fallback_growth_plan(total_chapters)
    
    def _print_growth_plan_summary(self, growth_plan: Dict):
        """打印成长规划摘要"""
        print("\n📈 全书成长规划摘要:")
        
        # 主角成长
        main_timeline = growth_plan["character_growth_plan"]["main_character_timeline"]
        print(f"  👤 主角成长阶段: {len(main_timeline)}个关键阶段")
        
        # 势力发展
        faction_timelines = growth_plan["faction_development_plan"]["faction_timelines"]
        print(f"  🏰 势力发展轨迹: {len(faction_timelines)}个主要势力")
        
        # 修炼体系
        cultivation_realms = growth_plan["item_upgrade_plan"]["cultivation_system"]["realm_progression"]
        print(f"  🧘 修炼境界: {len(cultivation_realms)}个主要境界")
        
        # 阶段性角色
        stage_chars = growth_plan["phase_character_blueprint"]["stage_character_requirements"]
        print(f"  🎭 阶段角色规划: {len(stage_chars)}个阶段的角色需求")
    
    def _create_fallback_growth_plan(self, total_chapters: int) -> Dict:
        """创建备用的成长规划"""
        print("⚠️ 使用备用成长规划")
        
        return {
            "character_growth_plan": {
                "main_character_timeline": self._create_default_character_timeline(total_chapters),
                "supporting_characters_growth": []
            },
            "faction_development_plan": {
                "faction_timelines": [],
                "world_power_balance": []
            },
            "item_upgrade_plan": {
                "cultivation_system": {"realm_progression": []},
                "equipment_upgrade_paths": []
            },
            "phase_character_blueprint": {
                "stage_character_requirements": []
            }
        }
    
    def _create_default_character_timeline(self, total_chapters: int) -> List[Dict]:
        """创建默认的主角成长时间线"""
        stages = [
            {"stage": "初期成长", "chapters": f"1-{total_chapters//4}", "ability_level": "入门", "key_breakthroughs": ["基础能力掌握"]},
            {"stage": "快速发展", "chapters": f"{total_chapters//4+1}-{total_chapters//2}", "ability_level": "熟练", "key_breakthroughs": ["关键技能突破"]},
            {"stage": "成熟稳定", "chapters": f"{total_chapters//2+1}-{total_chapters*3//4}", "ability_level": "精通", "key_breakthroughs": ["核心能力大成"]},
            {"stage": "巅峰境界", "chapters": f"{total_chapters*3//4+1}-{total_chapters}", "ability_level": "巅峰", "key_breakthroughs": ["达到极限"]}
        ]
        return stages
    
    def get_growth_context_for_chapter(self, chapter_number: int) -> Dict:
        """获取指定章节的成长上下文"""
        if "global_growth_plan" not in self.generator.novel_data:
            return {}
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        context = {
            "character_growth": self._get_character_growth_at_chapter(growth_plan, chapter_number),
            "faction_development": self._get_faction_development_at_chapter(growth_plan, chapter_number),
            "item_upgrade_status": self._get_item_upgrade_at_chapter(growth_plan, chapter_number),
            "phase_characters_expected": self._get_expected_phase_characters(growth_plan, chapter_number)
        }
        
        return context
    
    def _get_character_growth_at_chapter(self, growth_plan: Dict, chapter: int) -> Dict:
        """获取指定章节时的人物成长状态"""
        timeline = growth_plan["character_growth_plan"]["main_character_timeline"]
        
        for stage in timeline:
            chapter_range = stage["chapters"]
            if self._is_chapter_in_range(chapter, chapter_range):
                return {
                    "current_stage": stage["stage"],
                    "ability_level": stage["ability_level"],
                    "recent_breakthroughs": stage.get("key_breakthroughs", []),
                    "personality_state": stage.get("personality_changes", "稳定")
                }
        
        return {"current_stage": "未知", "ability_level": "未知"}
    
    def _get_faction_development_at_chapter(self, growth_plan: Dict, chapter: int) -> Dict:
        """获取指定章节时的势力发展状态"""
        # 简化的实现 - 实际应该更复杂
        return {
            "power_balance": "稳定",
            "major_conflicts": [],
            "rising_powers": []
        }
    
    def _get_item_upgrade_at_chapter(self, growth_plan: Dict, chapter: int) -> Dict:
        """获取指定章节时的物品升级状态"""
        realms = growth_plan["item_upgrade_plan"]["cultivation_system"]["realm_progression"]
        
        current_realm = "未知境界"
        for realm in realms:
            if self._is_chapter_in_range(chapter, realm.get("typical_chapters", "1-100")):
                current_realm = realm["realm"]
                break
        
        return {
            "current_realm": current_realm,
            "next_breakthrough": "未知",
            "available_skills": []
        }
    
    def _get_expected_phase_characters(self, growth_plan: Dict, chapter: int) -> List[str]:
        """获取预期在本章节出现的阶段性角色类型"""
        stage_name = self.generator.stage_plan_manager.get_current_stage(chapter)
        blueprint = growth_plan["phase_character_blueprint"]["stage_character_requirements"]
        
        for stage_req in blueprint:
            if stage_req["stage_name"] == stage_name:
                return stage_req["required_character_types"]
        
        return []
    
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