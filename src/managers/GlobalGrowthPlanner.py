# GlobalGrowthPlanner.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
from typing import Dict, List, Optional, TYPE_CHECKING
from src.managers.StagePlanUtils import parse_chapter_range, is_chapter_in_range
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.NovelGenerator import NovelGenerator

class GlobalGrowthPlanner:
    """全局血肉内容规划器 - 负责全书和阶段内的内容规划（写什么）"""
    
    def __init__(self, novel_generator: "NovelGenerator"):
        self.logger = get_logger("GlobalGrowthPlanner")
        self.novel_generator = novel_generator  # 确保正确设置这个属性
        self.config = novel_generator.config
        self.Prompts = novel_generator.Prompts
        self.stage_content_cache = {}  # 缓存各阶段的内容规划
        self.global_growth_plan = None  # 全书成长规划
        
        # -------------------------------------------------------------
        # ▼▼▼ 修改开始：同步修改阶段特性为“起承转合”四段式 ▼▼▼
        # -------------------------------------------------------------
        self.stage_characteristics = {
            "opening_stage": {
                "name": "起 (开局阶段)",
                "focus": "建立基础，引入核心元素",
                "character_growth": "主角初始性格和能力建立",
                "faction_intro": "主要势力格局引入",
                "ability_foundation": "基础能力和装备获得"
            },
            "development_stage": {
                "name": "承 (发展阶段)",
                "focus": "深化发展，推进冲突",
                "character_growth": "能力提升和性格深化", 
                "faction_development": "势力关系变化和冲突升级",
                "ability_advancement": "掌握关键技能和突破"
            },
            "climax_stage": {
                "name": "转 (高潮阶段)",
                "focus": "冲突爆发，重大转折",
                "character_growth": "性格重大转变和成长",
                "faction_climax": "势力冲突达到高潮",
                "ability_peak": "能力质的飞跃和巅峰表现"
            },
            "ending_stage": {
                "name": "合 (结局阶段)",
                "focus": "解决矛盾，收束线索，完整收尾", 
                "character_growth": "完成角色弧光，展现最终成长状态",
                "faction_resolution": "势力格局最终确定与后续发展",
                "ability_mastery": "能力完全掌握与传承"
            }
        }
        # -------------------------------------------------------------
        # ▲▲▲ 修改结束 ▲▲▲
        # -------------------------------------------------------------

    def get_chapter_specific_context(self, chapter_number: int) -> Dict:
        """获取章节特定的成长规划上下文，不重新生成全局计划"""
        if not hasattr(self, 'global_growth_plan') or not self.global_growth_plan:
            return {}
        
        # 基于现有全局计划，计算当前章节的特定上下文
        chapter_context = {
            "current_stage": self._get_current_stage(chapter_number),
            "character_development": self._get_character_development_at_chapter(chapter_number),
            "faction_development": self._get_faction_development_at_chapter(chapter_number),
            "ability_progression": self._get_ability_progression_at_chapter(chapter_number),
            "current_objectives": self._get_current_objectives(chapter_number)
        }
        
        return chapter_context

    def _get_current_stage(self, chapter_number: int) -> Dict:
        """获取当前章节所属的阶段"""
        if not self.global_growth_plan or "stage_framework" not in self.global_growth_plan:
            return {"stage_name": "未知阶段", "chapter_range": "1-100"}
        
        # [终极修复] stage_framework 是一个字典, 我们需要遍历它的值(values)
        # 而不是它的键(keys)。
        for stage in self.global_growth_plan["stage_framework"].values():
            # 经过 .values() 处理后, 'stage' 现在就是我们需要的字典了，
            # 例如: {"stage_name": "起 (开局阶段)", "chapter_range": "1-30章", ...}
            # 因此，不再需要之前的 isinstance 和 json.loads 检查。

            chapter_range = stage.get("chapter_range", "")
            # 假设您有一个名为 parse_chapter_range 的辅助函数
            start, end = parse_chapter_range(chapter_range)
            if start <= chapter_number <= end:
                return stage  # 返回完整的阶段字典
        
        return {"stage_name": "未知阶段", "chapter_range": "1-100"}

    def _get_character_development_at_chapter(self, chapter_number: int) -> Dict:
        """获取当前章节的角色发展状态"""
        # 基于全局计划计算当前章节的发展状态
        # 简化实现
        return {
            "main_character": {
                "current_level": min(10, chapter_number // 3 + 1),
                "key_abilities": ["基础能力"],
                "relationships": {}
            }
        }

    def _get_faction_development_at_chapter(self, chapter_number: int) -> Dict:
        """获取当前章节的势力发展状态"""
        return {
            "major_factions": [],
            "current_balance": "稳定",
            "recent_changes": []
        }

    def _get_ability_progression_at_chapter(self, chapter_number: int) -> Dict:
        """获取当前章节的能力进度"""
        return {
            "unlocked_abilities": ["基础操控"],
            "current_focus": "掌握基础",
            "next_milestone": "第{}章".format(chapter_number + 5)
        }

    def _get_current_objectives(self, chapter_number: int) -> List[str]:
        """获取当前章节的目标"""
        return [
            "推进主角成长",
            "发展故事情节"
        ]

    def get_stage_content_plan(self, stage_name: str, chapter_range: str) -> Dict:
        """获取阶段的详细内容规划"""
        cache_key = f"{stage_name}_{chapter_range}"
        
        if cache_key in self.stage_content_cache:
            return self.stage_content_cache[cache_key]
        
        self.logger.info(f"  📝 生成{stage_name}的内容规划...")
        
        # 准备基础数据
        novel_data = self.novel_generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 直接构建 user_prompt，避免使用 format()
        user_prompt = f"""
    你是一位资深的网络小说策划编辑。请根据以下信息为{stage_name}阶段（章节范围：{chapter_range}）制定详细的内容规划。

    **小说基本信息**：
    - 小说标题：{novel_data["novel_title"]}
    - 小说简介：{novel_data["novel_synopsis"]}
    - 总章节数：{total_chapters}

    **阶段信息**：
    - 阶段名称：{stage_name}
    - 章节范围：{chapter_range}
    - 阶段特性：{self._get_stage_characteristics_text(stage_name)}

    **世界观概述**：
    {json.dumps(novel_data.get("core_worldview", {}), ensure_ascii=False)}

    **规划要求**：
    请制定包含以下方面的详细内容规划：

    ## 1. 人物成长计划
    - 主角性格发展轨迹
    - 能力进阶路径
    - 关键成长节点
    - 配角发展重点

    ## 2. 势力发展计划
    - 势力格局变化
    - 新势力引入
    - 冲突升级路径
    - 世界背景扩展

    ## 3. 能力装备计划
    - 新技能获得
    - 装备升级路线
    - 能力突破点
    - 系统规则揭示

    ## 4. 情感发展计划
    - 主要情感线发展
    - 情感冲突设计
    - 关系变化节点

    ## 5. 关键里程碑
    - 阶段重要事件
    - 转折点设计
    - 伏笔设置与回收

    **输出格式要求**：
    请以JSON格式输出，包含以下结构：
    {{
        "stage_name": "{stage_name}",
        "chapter_range": "{chapter_range}",
        "character_growth_plan": {{
            "protagonist_development": {{
                "personality_evolution": "主角性格发展",
                "ability_advancement": ["能力1", "能力2"],
                "key_growth_moments": [
                    {{
                        "moment": "成长节点描述",
                        "impact": "影响说明"
                    }}
                ]
            }}
        }},
        "faction_development_plan": {{
            "power_structure_changes": {{
                "rising_powers": ["新势力1"],
                "new_alliances": ["新联盟"]
            }}
        }},
        "ability_equipment_plan": {{
            "skill_progression": {{
                "new_skills": ["新技能"],
                "skill_upgrades": ["技能升级"]
            }}
        }},
        "emotional_development_plan": {{
            "main_emotional_arc": "主要情感发展线"
        }},
        "key_milestones": [
            {{
                "milestone": "里程碑事件",
                "significance": "重要性说明"
            }}
        ]
    }}

    请确保规划具体、可行，符合该阶段的特点和发展需求。
    """
        
        # 生成内容规划
        content_plan = self.novel_generator.api_client.generate_content_with_retry(
            "stage_content_planning",
            user_prompt,
            purpose=f"生成{stage_name}内容规划"
        )
        
        if content_plan:
            self.stage_content_cache[cache_key] = content_plan
            self.logger.info(f"  ✅ {stage_name}内容规划生成完成")
            self._print_content_plan_summary(content_plan)
            return content_plan
        else:
            self.logger.info(f"  ⚠️ {stage_name}内容规划生成失败，使用默认规划")
            return self._create_default_content_plan(stage_name, chapter_range)

    def get_chapter_content_context(self, chapter_number: int) -> Dict:
        """获取指定章节的内容规划上下文"""
        if not self.global_growth_plan:
            # 如果没有全局规划，先生成一个
            self.generate_global_growth_plan()
        
        # 获取当前阶段信息
        current_stage = self._get_current_stage(chapter_number)
        
        if not current_stage or not isinstance(current_stage, dict):
            return {}
        
        # 获取阶段内容规划
        content_plan = self.get_stage_content_plan(
            current_stage.get("stage_name", "未知阶段"),
            current_stage.get("chapter_range", "1-100")
        )
        
        # 生成章节特定的内容指导
        chapter_context = self._generate_chapter_content_context(
            chapter_number, current_stage, content_plan
        )
                # 新增：添加情绪指导
        emotional_context = self._get_emotional_context_for_chapter(chapter_number)
        chapter_context["emotional_guidance"] = emotional_context
        
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
        """获取成长规划上下文 - 支持分层上下文压缩"""
        # 首先检查是否已经有全局计划
        if (hasattr(self.novel_generator, 'novel_data') and
            self.novel_generator.novel_data and
            "global_growth_plan" in self.novel_generator.novel_data):

            self.global_growth_plan = self.novel_generator.novel_data["global_growth_plan"]
            self.logger.info("  ✅ 使用已存在的全局成长计划")
        elif not self.global_growth_plan:
            self.logger.info("  📚 生成全书全局成长规划...123")
            self.generate_global_growth_plan()

        # 然后获取章节特定上下文
        chapter_context = self.get_chapter_specific_context(chapter_number)

        # 🆕 应用分层上下文压缩
        from src.utils.LayeredContextManager import LayeredContextManager
        context_manager = LayeredContextManager()

        # 对全局成长规划进行基于章节距离的压缩
        compressed_global_plan = context_manager.compress_context(
            self.global_growth_plan or {}, chapter_number, 1, "plot"  # 全局计划被视为第1章的内容
        )

        # 对章节特定上下文进行压缩
        compressed_chapter_context = context_manager.compress_context(
            chapter_context, chapter_number, chapter_number, "character"
        )

        context = {
            "global_growth_plan": compressed_global_plan,
            "chapter_specific": compressed_chapter_context
        }

        # 添加上下文大小信息用于调试
        context_size_info = context_manager.get_context_size_info(context)
        if context_size_info.get("is_large", False):
            self.logger.info(f"⚠️ 第{chapter_number}章成长规划上下文较大: {context_size_info['estimated_tokens']} tokens")

        return context

    def _print_global_plan_summary(self, global_plan: Dict):
        """打印全局规划摘要"""
        self.logger.info("    📊 全书全局成长规划摘要:")
        
        # 阶段框架 - 修复：确保返回的是列表，不是None
        stages = global_plan.get("stage_framework") or []
        # 如果是字典，转换为列表
        if isinstance(stages, dict):
            stages = list(stages.values())
        self.logger.info(f"      阶段划分: {len(stages)}个主要阶段")
        
        # 人物成长
        character_arcs = global_plan.get("character_growth_arcs", {})
        protagonist = character_arcs.get("protagonist", {})
        self.logger.info(f"      主角成长弧线: {protagonist.get('overall_arc', '完整发展')}")
        
        # 势力发展
        faction_trajectory = global_plan.get("faction_development_trajectory", {})
        self.logger.info(f"      势力发展: {len(faction_trajectory)}个主要势力")
        
        # 能力系统
        ability_evolution = global_plan.get("ability_system_evolution", {})
        # 确保 ability_evolution 是字典类型
        if not isinstance(ability_evolution, dict):
            ability_evolution = {}
        breakthroughs = ability_evolution.get("breakthrough_milestones", [])
        # 确保 breakthroughs 是列表类型
        if not isinstance(breakthroughs, list):
            breakthroughs = []
        self.logger.info(f"      能力突破点: {len(breakthroughs)}个关键里程碑")

    def _print_content_plan_summary(self, content_plan: Dict):
        """打印内容规划摘要"""
        stage_name = content_plan.get("stage_name", "未知阶段")
        self.logger.info(f"    📊 {stage_name}内容规划摘要:")
        
        # 人物成长
        char_plan = content_plan.get("character_growth_plan", {})
        protagonist = char_plan.get("protagonist_development", {})
        abilities = protagonist.get("ability_advancement", [])
        self.logger.info(f"      人物成长: {len(abilities)}个新能力")
        
        # 势力发展
        faction_plan = content_plan.get("faction_development_plan", {})
        power_changes = faction_plan.get("power_structure_changes", {})
        new_powers = power_changes.get("rising_powers", [])
        self.logger.info(f"      势力变化: {len(new_powers)}个新势力")
        
        # 里程碑
        milestones = content_plan.get("key_milestones", [])
        self.logger.info(f"      关键里程碑: {len(milestones)}个")

    # -------------------------------------------------------------
    # ▼▼▼ 修改开始：修改默认全局规划为四阶段模型 ▼▼▼
    # -------------------------------------------------------------
    def _create_default_global_plan(self, total_chapters: int) -> Dict:
        """创建默认的“起承转合”四阶段全局成长规划"""
        # 定义四阶段的边界
        b = {
            "opening_end": int(total_chapters * 0.15),
            "development_start": int(total_chapters * 0.15) + 1,
            "development_end": int(total_chapters * 0.50), # 0.15 + 0.35
            "climax_start": int(total_chapters * 0.50) + 1,
            "climax_end": int(total_chapters * 0.80), # 0.50 + 0.30
            "ending_start": int(total_chapters * 0.80) + 1,
        }

        return {
            "overview": f"全书{total_chapters}章的“起承转合”四阶段完整成长规划",
            "stage_framework": [
                {
                    "stage_name": "起 (开局阶段)",
                    "chapter_range": f"1-{b['opening_end']}",
                    "core_objectives": ["建立故事基础", "引入核心冲突"],
                    "key_growth_themes": ["初始成长", "能力觉醒"],
                    "milestone_events": ["主角觉醒", "初次冲突"]
                },
                {
                    "stage_name": "承 (发展阶段)",
                    "chapter_range": f"{b['development_start']}-{b['development_end']}",
                    "core_objectives": ["深化矛盾", "角色成长", "扩展世界"],
                    "key_growth_themes": ["能力提升", "关系建立", "探索新地图"],
                    "milestone_events": ["关键突破", "重要联盟", "遭遇强敌"]
                },
                {
                    "stage_name": "转 (高潮阶段)", 
                    "chapter_range": f"{b['climax_start']}-{b['climax_end']}",
                    "core_objectives": ["冲突总爆发", "重大转折"],
                    "key_growth_themes": ["巅峰对决", "真相揭露", "角色蜕变"],
                    "milestone_events": ["最终对决", "关键反转", "揭露最大秘密"]
                },
                {
                    "stage_name": "合 (结局阶段)",
                    "chapter_range": f"{b['ending_start']}-{total_chapters}", 
                    "core_objectives": ["解决所有矛盾", "收束全部线索", "升华主题"],
                    "key_growth_themes": ["圆满收尾", "情感升华", "角色归宿"],
                    "milestone_events": ["核心矛盾解决", "所有伏笔回收", "大结局"]
                }
            ],
            "character_growth_arcs": {
                "protagonist": {
                    "overall_arc": "从平凡到非凡的完整成长历程",
                    "stage_specific_growth": {
                        "起 (开局阶段)": {},
                        "承 (发展阶段)": {},
                        "转 (高潮阶段)": {},
                        "合 (结局阶段)": {},
                    }
                }
            },
        }
    # -------------------------------------------------------------
    # ▲▲▲ 修改结束 ▲▲▲
    # -------------------------------------------------------------

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

    def generate_global_growth_plan(self) -> Dict:
        """生成全书的全局成长规划 - 增强版本，包含情绪规划"""
        self.logger.info("  📚 生成全书全局成长规划...1")
        self.logger.info("  📚 生成全书全局成长规划...2")
        
        # 通知进度更新：开始全局成长规划
        self._notify_progress("全局成长规划", 68, "正在制定全书成长规划框架...")
        
        # 准备基础数据
        novel_data = self.novel_generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        # ◀︎◀︎ 修改开始：强制使用 creative_seed 作为最高指令 ◀︎◀︎
        creative_seed = novel_data.get("novel_info", {}).get("creative_seed", {})

        # 如果 creative_seed 被错误地保存为字符串，则尝试解析为JSON
        if isinstance(creative_seed, str):
            try:
                creative_seed = json.loads(creative_seed)
            except Exception:
                # 解析失败时，降级为一个安全的空结构
                creative_seed = {"coreSellingPoints": "", "completeStoryline": {}}

        # 从 creative_seed 中提取您定义的原始卖点和故事线（现在 creative_seed 至少是 dict）
        original_selling_points = creative_seed.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_seed.get("completeStoryline", {})
        
        # 将故事线概要转化为“推荐策略”
        recommended_strategies = []
        if storyline:
            for stage_key, stage_data in storyline.items():
                stage_name = stage_data.get("stageName", stage_key)
                summary = stage_data.get("summary", "无概要")
                recommended_strategies.append(f"【{stage_name}阶段策略】: {summary}")
        
        # 构建一个忠于您原始设想的“最高优先级信息”
        author_vision_prompt_section = f"""
# 最高指令：以“作者愿景”为唯一准则进行规划

你是一名顶级的小说策划专家。你的唯一目标是严格遵循下方提供的“作者愿景”，为小说量身打造一个符合其独特内核的全书成长规划。如果其他商业分析与“作者愿景”冲突，必须以“作者愿景”为准。

## 作者愿景（本书成功的唯一关键）
*   **核心内核与卖点**: {original_selling_points}
*   **故事策略与脉络**: {json.dumps(recommended_strategies, ensure_ascii=False)}
"""
        # ◀︎◀︎ 修改结束 ◀︎◀︎

        # -------------------------------------------------------------
        # ▼▼▼ 修改开始：重构Prompt以强制使用“起承转合”框架 ▼▼▼
        # -------------------------------------------------------------
        # 2. 构建一个更智能、更通用的Prompt
        user_prompt = f"""
{author_vision_prompt_section}

## 小说基础信息
*   **小说标题**: {novel_data["novel_title"]}
*   **小说简介**: {novel_data["novel_synopsis"]}
*   **总章节数**: {total_chapters}

# 核心任务：将“作者愿景”重构为“起承转合”的专业大纲

你是一位顶级小说策划。你的任务是，在完全忠于上方【作者愿景】的核心卖点与情节内核的前提下，将其提供的较为随意的【故事策略与脉络】（例如：“乱星启程·天南潜龙”、“元婴双星”等阶段）进行专业化的重构，映射到一个标准的“起承转合”四阶段结构中。

## “起承转合”框架定义 (你必须遵守的输出结构)
*   **起 (开局阶段)**: 章节占比约15%。建立基础，引入核心元素。
*   **承 (发展阶段)**: 章节占比约35%。深化发展，推进冲突，扩展世界。
*   **转 (高潮阶段)**: 章节占比约30%。冲突爆发，重大转折，角色蜕变。
*   **合 (结局阶段)**: 章节占比约20%。解决矛盾，收束线索，完整收尾。

## 规划要求
1.  **结构映射**: 分析【作者愿景】中的故事线，将其内容合理地分配到“起”、“承”、“转”、“合”四个阶段中。
2.  **内容忠实**: 阶段名称必须使用“起承转合”，但各阶段的【核心目标】和【里程碑事件】必须提炼自作者的原始创意。例如，“起 (开局阶段)”可能就对应了作者原始创意中的“乱星启程·天南潜龙”阶段的核心内容。
3.  **统一规划**: 基于重构后的“起承转合”框架，统一规划**人物成长弧线**、**势力发展**和**能力体系**的演进，使其节奏与四段式结构保持一致。
4.  **动态章节**: 根据总章节数 ({total_chapters}章)，为每个阶段分配合理的章节范围。
5.  **输出格式**: 最终输出的JSON中，`stage_framework`部分必须是包含“起”、“承”、“转”、“合”四个阶段的列表或字典。

请基于此要求，输出一份将作者原始创意与专业“起承转合”结构完美结合的JSON格式全局成长规划。
"""    
        # -------------------------------------------------------------
        # ▲▲▲ 修改结束 ▲▲▲
        # -------------------------------------------------------------
        
        # 通知进度更新：开始API调用
        self._notify_progress("全局成长规划", 70, "正在调用AI生成成长规划...")
        
        # 添加调试信息
        self.logger.info(f"  🔍 调试信息 - total_chapters: {total_chapters}")
        self.logger.info(f"  🔍 调试信息 - novel_data 类型: {type(novel_data)}")
        
        # 原有的成长规划生成代码...
        try:
            global_plan = self.novel_generator.api_client.generate_content_with_retry(
                "global_growth_planning",
                user_prompt,
                purpose="生成全书全局成长规划"
            )
            
            if global_plan:
                self.global_growth_plan = global_plan
                self.novel_generator.novel_data["global_growth_plan"] = global_plan
                
                self.logger.info("  ✅ 全书全局成长规划生成完成")
                self._print_global_plan_summary(global_plan)
                
                # 通知进度更新：完成
                self._notify_progress("全局成长规划", 75, "全书成长规划生成完成")
                return global_plan
            else:
                self.logger.info("  ⚠️ 全书全局成长规划生成失败，使用默认规划")
                # 通知进度更新：使用默认规划
                self._notify_progress("全局成长规划", 72, "使用默认成长规划")
                return self._create_default_global_plan(total_chapters)
                
        except Exception as e:
            self.logger.error(f"  ❌ 生成全局成长规划时发生异常: {e}")
            # 通知进度更新：处理异常
            self._notify_progress("全局成长规划", 72, f"生成失败，使用默认规划: {str(e)}")
            return self._create_default_global_plan(total_chapters)

    def _get_emotional_context_for_chapter(self, chapter_number: int) -> Dict:
        """获取章节的情绪上下文 - 修复版本"""
        emotional_plan = self.novel_generator.novel_data.get("emotional_development_plan", {})
        
        # 调试信息
        self.logger.info(f"  🔍 获取情绪上下文 - 章节 {chapter_number}")
        self.logger.info(f"  🔍 emotional_plan 类型: {type(emotional_plan)}")
        
        # 修复：确保emotional_plan是字典
        if not emotional_plan:
            self.logger.info("  ⚠️ 情绪计划为空")
            return {}
        
        if isinstance(emotional_plan, str):
            self.logger.info(f"  ⚠️ 情绪计划是字符串，尝试解析")
            try:
                emotional_plan = json.loads(emotional_plan)
            except Exception as e:
                self.logger.info(f"  ❌ 解析情绪计划字符串失败: {e}")
                return {}
        
        if not isinstance(emotional_plan, dict):
            self.logger.info(f"  ❌ 情绪计划类型错误: {type(emotional_plan)}")
            return {}
        
        # 获取当前阶段
        current_stage = self._get_current_stage(chapter_number)
        current_stage_name = current_stage.get("stage_name", "未知阶段") if isinstance(current_stage, dict) else "未知阶段"
        self.logger.info(f"  🔍 当前阶段: {current_stage_name}")
        
        # 修复：安全地访问嵌套字典
        stage_emotional_planning = emotional_plan.get("stage_emotional_planning", {})
        if not isinstance(stage_emotional_planning, dict):
            self.logger.info(f"  ⚠️ stage_emotional_planning 不是字典: {type(stage_emotional_planning)}")
            stage_emotional_planning = {}
        
        stage_emotional_plan = stage_emotional_planning.get(current_stage_name, {})
        if not isinstance(stage_emotional_plan, dict):
            self.logger.info(f"  ⚠️ stage_emotional_plan 不是字典: {type(stage_emotional_plan)}")
            stage_emotional_plan = {}
        
        # 计算章节在阶段中的位置
        stage_range = self._get_stage_range(current_stage_name)
        if not stage_range:
            self.logger.info(f"  ⚠️ 无法获取阶段范围")
            return {}
            
        start_chap, end_chap = parse_chapter_range(stage_range)
        
        # 避免除零错误
        if end_chap - start_chap == 0:
            progress_in_stage = 0
        else:
            progress_in_stage = (chapter_number - start_chap + 1) / (end_chap - start_chap + 1)
        
        # 基于进度确定情绪重点
        if progress_in_stage < 0.3:
            emotional_focus = "建立阶段情感基础"
            intensity = "中等"
        elif progress_in_stage < 0.7:
            emotional_focus = "深化情感冲突和发展"
            intensity = "中高" 
        else:
            emotional_focus = "情感高潮或转折准备"
            intensity = "高"
        
        result = {
            "current_emotional_tone": stage_emotional_plan.get("emotional_tone", ""),
            "emotional_focus": emotional_focus,
            "target_intensity": intensity,
            "key_emotional_moments": stage_emotional_plan.get("key_emotional_moments", []),
            "reader_experience_goal": stage_emotional_plan.get("reader_experience_goal", "")
        }
        
        self.logger.info(f"  ✅ 第{chapter_number}章情绪上下文生成完成")
        return result

    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围 - 新增方法"""
        if not hasattr(self, 'global_growth_plan') or not self.global_growth_plan:
            return "1-100"
        
        for stage in self.global_growth_plan.get("stage_framework", []):
            if stage.get("stage_name") == stage_name:
                return stage.get("chapter_range", "1-100")
        
        return "1-100"
    
    def _notify_progress(self, stage_name: str, progress: int, message: Optional[str] = None):
        """通知进度更新"""
        try:
            # 如果novel_generator有进度回调，使用它
            if hasattr(self.novel_generator, '_update_task_status_callback'):
                callback = getattr(self.novel_generator, '_update_task_status_callback')
                task_id = getattr(self.novel_generator, '_current_task_id', None)
                
                if callback and callable(callback) and task_id:
                    callback(task_id, 'generating', progress, message)
                    self.logger.info(f"  📊 进度更新: {progress}% - {message or ''}")
            
            # 如果novel_generator有event_bus，也发布事件
            if hasattr(self.novel_generator, 'event_bus'):
                event_bus = getattr(self.novel_generator, 'event_bus')
                event_bus.publish('global_growth_planner.progress', {
                    'stage': stage_name,
                    'progress': progress,
                    'message': message or f"执行{stage_name}"
                })
                
        except Exception as e:
            # 不让进度通知失败影响主要功能
            self.logger.debug(f"  ⚠️ 进度通知失败: {e}")
