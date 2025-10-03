# GlobalGrowthPlanner.py
import json
from typing import Dict, List


class GlobalGrowthPlanner:
    """全局成长规划管理器 - 分层设计，避免token超限"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.stage_details_cache = {}  # 缓存各阶段的详细规划
    
    def create_comprehensive_growth_plan(self, creative_seed: str, novel_title: str, 
                                       novel_synopsis: str, total_chapters: int) -> Dict:
        """创建全书综合成长计划 - 精简版本"""
        print("=== 制定全书成长规划（精简版） ===")
        
        # 收集所有必要的基础数据
        worldview = self.generator.novel_data["core_worldview"]
        character_design = self.generator.novel_data["character_design"]
        
        # 提取关键信息，避免传递过多数据
        simplified_worldview = {
            "era": worldview.get("era", ""),
            "core_conflict": worldview.get("core_conflict", ""),
            "power_system": worldview.get("power_system", "")
        }
        
        simplified_chars = {
            "main_character": character_design.get("main_character", {}).get("name", ""),
            "important_characters": [char.get("name", "") for char in character_design.get("important_characters", [])[:3]]
        }
        
        user_prompt = f"""
# 小说基础信息
**创意种子**: {creative_seed}
**小说标题**: {novel_title}
**小说简介**: {novel_synopsis}
**总章节数**: {total_chapters}

# 世界观核心设定
{json.dumps(simplified_worldview, ensure_ascii=False)}

# 主要角色
{json.dumps(simplified_chars, ensure_ascii=False)}

# 制定全书成长规划（精简版）
请为这部小说制定一个精简的成长规划框架，只包含各阶段的核心重点：

## 全书阶段划分
请根据{total_chapters}章的总长度，划分为4-6个主要阶段，每个阶段包含：

### 阶段核心目标
- **主线推进**: 该阶段要解决的主要矛盾
- **人物成长**: 主角在该阶段的关键成长
- **势力变化**: 世界格局的主要变化
- **能力突破**: 重要的能力或装备提升

## 输出要求
请返回极其精简的JSON格式，只包含阶段划分和核心目标，不要展开细节。
每个阶段的描述控制在50字以内。

{{
    "stage_framework": [
        {{
            "stage_name": "阶段名称",
            "chapter_range": "1-10",
            "main_plot_focus": "核心剧情重点（20字内）",
            "character_growth_focus": "角色成长重点（15字内）", 
            "faction_development_focus": "势力发展重点（15字内）",
            "ability_breakthrough_focus": "能力突破重点（15字内）"
        }}
    ],
    "growth_milestones": {{
        "key_character_developments": [
            "里程碑1（10字内）",
            "里程碑2（10字内）"
        ],
        "key_faction_changes": [
            "势力变化1（10字内）",
            "势力变化2（10字内）"
        ],
        "key_ability_unlocks": [
            "能力解锁1（10字内）",
            "能力解锁2（10字内）"
        ]
    }}
}}
"""
        
        result = self.generator.api_client.generate_content_with_retry(
            "global_growth_planning",
            user_prompt,
            purpose="制定精简版全书成长规划"
        )
        
        if result:
            print("✅ 全书成长规划框架制定完成")
            self._print_growth_framework_summary(result)
            return result
        else:
            print("❌ 全书成长规划制定失败")
            return self._create_minimal_growth_framework(total_chapters)
    
    def get_stage_detailed_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """获取阶段的详细规划（按需生成，避免token超限）"""
        if stage_name in self.stage_details_cache:
            return self.stage_details_cache[stage_name]
        
        # 从全局框架中获取该阶段的基础信息
        framework = self.generator.novel_data.get("global_growth_plan", {})
        stage_info = None
        for stage in framework.get("stage_framework", []):
            if stage["stage_name"] == stage_name:
                stage_info = stage
                break
        
        if not stage_info:
            return self._create_default_stage_plan(stage_name, chapter_range)
        
        user_prompt = f"""
# 阶段详细规划生成
**阶段名称**: {stage_name}
**章节范围**: {chapter_range}

# 阶段核心目标
- **主线重点**: {stage_info.get('main_plot_focus', '')}
- **角色成长**: {stage_info.get('character_growth_focus', '')}
- **势力发展**: {stage_info.get('faction_development_focus', '')}
- **能力突破**: {stage_info.get('ability_breakthrough_focus', '')}

# 小说基础信息
**标题**: {self.generator.novel_data["novel_title"]}
**简介**: {self.generator.novel_data["novel_synopsis"]}

# 生成要求
请为该阶段生成详细的成长规划，包含：
1. 具体的情节发展点（3-5个）
2. 角色成长的具体表现
3. 势力关系的具体变化
4. 能力装备的具体提升

返回JSON格式：
{{
    "stage_name": "{stage_name}",
    "chapter_range": "{chapter_range}",
    "detailed_plot_points": [
        "具体情节发展点1",
        "具体情节发展点2",
        "具体情节发展点3"
    ],
    "character_development_details": {{
        "main_character_growth": "主角具体成长描述",
        "relationship_changes": ["关系变化1", "关系变化2"],
        "personality_evolution": "性格演变描述"
    }},
    "faction_development_details": {{
        "power_shifts": ["权力转移1", "权力转移2"],
        "new_alliances": ["新联盟1", "新联盟2"],
        "conflict_escalation": "冲突升级描述"
    }},
    "ability_equipment_details": {{
        "new_skills": ["新技能1", "新技能2"],
        "equipment_upgrades": ["装备升级1", "装备升级2"],
        "breakthrough_moments": ["突破时刻1", "突破时刻2"]
    }}
}}
"""
        
        detailed_plan = self.generator.api_client.generate_content_with_retry(
            "stage_detailed_planning",
            user_prompt,
            purpose=f"生成{stage_name}详细规划"
        )
        
        if detailed_plan:
            self.stage_details_cache[stage_name] = detailed_plan
            print(f"✅ 已生成{stage_name}的详细规划")
            return detailed_plan
        else:
            return self._create_default_stage_plan(stage_name, chapter_range)
    
    def _print_growth_framework_summary(self, growth_plan: Dict):
        """打印成长规划框架摘要"""
        print("\n📈 全书成长规划框架:")
        
        stages = growth_plan["stage_framework"]
        print(f"  阶段划分: {len(stages)}个主要阶段")
        for stage in stages:
            print(f"  - {stage['stage_name']} ({stage['chapter_range']}章)")
            print(f"    主线: {stage['main_plot_focus']}")
    
    def _create_minimal_growth_framework(self, total_chapters: int) -> Dict:
        """创建最小化的成长框架"""
        print("⚠️ 使用最小化成长框架")
        
        # 简单的四阶段划分
        quarter = total_chapters // 4
        stages = [
            {
                "stage_name": "开局阶段",
                "chapter_range": f"1-{quarter}",
                "main_plot_focus": "引入世界观和核心冲突",
                "character_growth_focus": "建立主角基础",
                "faction_development_focus": "介绍主要势力",
                "ability_breakthrough_focus": "获得基础能力"
            },
            {
                "stage_name": "发展阶段", 
                "chapter_range": f"{quarter+1}-{quarter*2}",
                "main_plot_focus": "推进主线任务",
                "character_growth_focus": "能力快速提升",
                "faction_development_focus": "势力关系变化",
                "ability_breakthrough_focus": "掌握关键技能"
            },
            {
                "stage_name": "转折阶段",
                "chapter_range": f"{quarter*2+1}-{quarter*3}",
                "main_plot_focus": "重大冲突爆发",
                "character_growth_focus": "性格重大转变",
                "faction_development_focus": "格局重新洗牌",
                "ability_breakthrough_focus": "能力质的飞跃"
            },
            {
                "stage_name": "结局阶段",
                "chapter_range": f"{quarter*3+1}-{total_chapters}",
                "main_plot_focus": "解决核心矛盾",
                "character_growth_focus": "完成最终成长",
                "faction_development_focus": "确立最终格局",
                "ability_breakthrough_focus": "达到能力巅峰"
            }
        ]
        
        return {
            "stage_framework": stages,
            "growth_milestones": {
                "key_character_developments": ["主角成长轨迹"],
                "key_faction_changes": ["势力演变过程"],
                "key_ability_unlocks": ["能力提升路径"]
            }
        }
    
    def _create_default_stage_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """创建默认的阶段详细规划"""
        return {
            "stage_name": stage_name,
            "chapter_range": chapter_range,
            "detailed_plot_points": [
                "推进主线情节发展",
                "深化角色关系互动",
                "引入新的冲突元素"
            ],
            "character_development_details": {
                "main_character_growth": "主角在该阶段获得成长",
                "relationship_changes": ["人际关系发展"],
                "personality_evolution": "性格有所演变"
            },
            "faction_development_details": {
                "power_shifts": ["势力平衡变化"],
                "new_alliances": ["新的联盟形成"],
                "conflict_escalation": "冲突进一步升级"
            },
            "ability_equipment_details": {
                "new_skills": ["掌握新技能"],
                "equipment_upgrades": ["装备得到提升"],
                "breakthrough_moments": ["能力获得突破"]
            }
        }
    
    def get_growth_context_for_chapter(self, chapter_number: int) -> Dict:
        """获取指定章节的成长上下文（智能分层）"""
        if "global_growth_plan" not in self.generator.novel_data:
            return {}
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        
        # 1. 首先从框架中确定当前阶段
        current_stage = self._get_current_stage(growth_plan, chapter_number)
        if not current_stage:
            return {}
        
        # 2. 按需获取该阶段的详细规划
        detailed_plan = self.get_stage_detailed_plan(
            current_stage["stage_name"], 
            current_stage["chapter_range"]
        )
        
        # 3. 返回精简的上下文信息
        return {
            "current_stage": current_stage["stage_name"],
            "stage_focus": {
                "main_plot": current_stage["main_plot_focus"],
                "character_growth": current_stage["character_growth_focus"],
                "faction_development": current_stage["faction_development_focus"],
                "ability_breakthrough": current_stage["ability_breakthrough_focus"]
            },
            "current_development": self._get_chapter_specific_development(
                chapter_number, current_stage, detailed_plan
            )
        }
    
    def _get_current_stage(self, growth_plan: Dict, chapter: int) -> Dict:
        """获取当前章节所属的阶段"""
        for stage in growth_plan.get("stage_framework", []):
            chapter_range = stage["chapter_range"]
            if self._is_chapter_in_range(chapter, chapter_range):
                return stage
        return None
    
    def _get_chapter_specific_development(self, chapter: int, stage: Dict, detailed_plan: Dict) -> Dict:
        """获取章节特定的发展信息"""
        # 基于章节在阶段中的位置，提供具体的发展指导
        start_chapter, end_chapter = self._parse_chapter_range(stage["chapter_range"])
        progress_in_stage = (chapter - start_chapter) / (end_chapter - start_chapter)
        
        if progress_in_stage < 0.3:
            phase = "阶段初期"
        elif progress_in_stage < 0.7:
            phase = "阶段中期" 
        else:
            phase = "阶段后期"
        
        return {
            "phase": phase,
            "suggested_focus": self._get_phase_focus(phase, detailed_plan),
            "key_plot_points": detailed_plan.get("detailed_plot_points", [])[:2]
        }
    
    def _get_phase_focus(self, phase: str, detailed_plan: Dict) -> str:
        """根据阶段位置获取重点"""
        focus_map = {
            "阶段初期": "建立基础，引入冲突",
            "阶段中期": "深化发展，推进情节", 
            "阶段后期": "准备转折，铺垫后续"
        }
        return focus_map.get(phase, "推进情节发展")
    
    def _parse_chapter_range(self, range_str: str) -> tuple:
        """解析章节范围字符串"""
        try:
            start, end = map(int, range_str.split("-"))
            return start, end
        except:
            return 1, 100
    
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