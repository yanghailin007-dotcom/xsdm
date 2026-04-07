"""
CharacterNarrativeSession - 角色与叙事会话（Session B）
=========================================================

职责：
- 设计核心角色（主角、关键配角、反派）
- 制定情绪蓝图
- 规划全局成长路线

对话轮次：4-5轮
1. 分析 FoundationPlanning 的 Context Brief，确定角色方向
2. 主角深度设计
3. 关键配角和反派设计
4. 情绪蓝图规划
5. 成长里程碑设计

产物格式（必须与传统模式一致）：
{
    "character_design": {
        "protagonist": {
            "basic_info": {"name": str, ...},
            "goals": str/list,
            "abilities": str/list
        },
        "supporting_characters": [...],  # 可选
        "antagonist": {...}  # 可选
    },
    "emotional_blueprint": {
        "emotional_arcs": [...],
        "key_emotional_beats": [...],  # 可选
        "emotional_themes": [...]  # 可选
    },
    "global_growth_plan": {
        "protagonist_growth": [...],
        "milestone_events": [...],
        "power_progression": [...],  # 可选
        "relationship_development": [...]  # 可选
    }
}
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.utils.logger import get_logger

logger = get_logger("CharacterNarrativeSession")


class CharacterNarrativeSession(NovelGenerationSession):
    """
    角色与叙事会话
    
    合并原步骤7-8（character_design + emotional_growth_planning）
    """
    
    STEPS = ["character_design", "emotional_growth_planning"]
    
    def __init__(
        self,
        api_client,
        novel_data: Optional[Dict] = None,
        context_briefs: Optional[List[str]] = None,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # Session B 接收 FoundationPlanning 的 Context Brief
        super().__init__(
            api_client=api_client,
            domain="character_narrative",
            context_briefs=context_briefs or [],
            novel_data=novel_data,
            provider=provider,
            model_name=model_name,
            temperature=temperature,
        )
        
        # 存储每轮结果
        self.results: Dict[str, Any] = {}
        
        # 进度回调
        self._progress_callback: Optional[Callable[[int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """设置进度回调"""
        self._progress_callback = callback
    
    def _update_progress(self, progress: int, message: str):
        """更新进度"""
        if self._progress_callback:
            self._progress_callback(progress, message)
        logger.info(f"[CharacterNarrative] 进度 {progress}%: {message}")
    
    # =====================================================================
    # 主执行流程
    # =====================================================================
    
    def execute_all_steps(self) -> Dict[str, Any]:
        """
        执行全部4-5轮对话
        
        🔥 基于 FoundationPlanningSession 的 Context Brief 和 final_plan
        
        Returns:
            完整产物字典
        """
        logger.info("=" * 60)
        logger.info("CharacterNarrativeSession 开始执行")
        logger.info("基于 FoundationPlanning 的 Context Brief 生成角色与叙事...")
        logger.info("=" * 60)
        
        # 🔥 验证输入：必须有 final_plan 或 selected_plan
        final_plan = self.novel_data.get("final_plan") or self.novel_data.get("selected_plan", {})
        if not final_plan:
            raise ValueError("novel_data 中缺少 final_plan 或 selected_plan")
        
        # 🔥 获取 FoundationPlanning 的 Context Brief
        foundation_brief = {}
        if self.context_briefs:
            try:
                # 尝试解析第一个 brief（应该是 FoundationPlanning 的）
                foundation_brief = json.loads(self.context_briefs[0]) if isinstance(self.context_briefs[0], str) else self.context_briefs[0]
            except:
                logger.warning("无法解析 FoundationPlanning 的 Context Brief")
        
        logger.info(f"输入验证通过，开始生成角色与叙事...")
        
        try:
            # 第1轮：分析 Context Brief，确定角色方向
            self._update_progress(10, "分析基础规划，确定角色方向...")
            step1_result = self._round1_analyze_brief(foundation_brief, final_plan)
            self.results["direction_analysis"] = step1_result
            
            # 第2轮：主角深度设计
            self._update_progress(30, "设计主角...")
            step2_result = self._round2_protagonist_design(foundation_brief, final_plan, step1_result)
            self.results["protagonist"] = step2_result
            
            # 第3轮：关键配角和反派设计
            self._update_progress(50, "设计配角和反派...")
            step3_result = self._round3_supporting_characters(foundation_brief, final_plan, step2_result)
            self.results["supporting"] = step3_result
            
            # 第4轮：情绪蓝图规划
            self._update_progress(70, "规划情绪蓝图...")
            step4_result = self._round4_emotional_blueprint(foundation_brief, final_plan, step2_result)
            self.results["emotional_blueprint"] = step4_result
            
            # 第5轮：成长里程碑设计
            self._update_progress(85, "设计成长里程碑...")
            step5_result = self._round5_growth_plan(foundation_brief, final_plan, step2_result, step4_result)
            self.results["growth_plan"] = step5_result
            
            # 第6轮：整合输出
            self._update_progress(95, "整合角色与叙事...")
            final_result = self._round6_integrate(
                step2_result, step3_result, step4_result, step5_result
            )
            
            # 验证产物格式
            self._update_progress(98, "验证产物格式...")
            if not self._validate_output(final_result):
                logger.error("产物格式验证失败")
                raise ValueError("产物格式不符合要求")
            
            self._update_progress(100, "角色与叙事生成完成")
            
            logger.info("✅ CharacterNarrativeSession 执行完成")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ CharacterNarrativeSession 执行失败: {e}", exc_info=True)
            raise
    
    # =====================================================================
    # 各轮对话实现
    # =====================================================================
    
    def _round1_analyze_brief(self, foundation_brief: Dict, final_plan: Dict) -> Dict:
        """
        第1轮：分析 Context Brief 和 final_plan，确定角色设计方向
        """
        # 提取关键信息
        world_overview = foundation_brief.get("world_overview", "")
        power_system = foundation_brief.get("power_system", "")
        main_conflict = foundation_brief.get("main_conflict", "")
        
        # 从 final_plan 获取主角设定
        core_setting = final_plan.get("core_setting", {})
        protagonist_seed = core_setting.get("protagonist", {})
        golden_finger = core_setting.get("golden_finger", {})
        
        user_prompt = f"""基于基础规划的输出，分析角色设计方向。

**世界观信息**
- 世界概述：{world_overview}
- 力量体系：{power_system}
- 核心冲突：{main_conflict}

**Final Plan 中的主角设定**
- 身份：{protagonist_seed.get("identity", "未指定")}
- 性格：{protagonist_seed.get("personality", "未指定")}
- 目标：{protagonist_seed.get("goal", "未指定")}
- 成长线：{protagonist_seed.get("growth_arc", "未指定")}

**金手指设定**
- 能力：{golden_finger.get("ability", "未指定")}
- 限制：{golden_finger.get("limitations", "未指定")}

**分析任务**
1. 确定主角的核心人设定位（性格标签、行为模式）
2. 确定配角阵容需求（需要哪些类型的配角）
3. 确定反派定位（主要威胁来源）
4. 确定角色关系网络的核心矛盾

**输出格式（JSON）**
{{
    "protagonist_positioning": {{
        "personality_tags": ["标签1", "标签2", "标签3"],
        "behavior_pattern": "行为模式描述",
        "core_motivation": "核心动机"
    }},
    "supporting_cast_needs": [
        {{"role_type": "盟友类型", "purpose": "在故事中的作用"}},
        {{"role_type": "女主/男主类型", "purpose": "与主角的关系定位"}}
    ],
    "antagonist_positioning": {{
        "type": "反派类型",
        "threat_level": "威胁等级",
        "conflict_nature": "与主角的冲突本质"
    }},
    "relationship_core_conflict": "角色关系网络的核心矛盾描述"
}}"""
        
        logger.info("[Round 1] 分析角色设计方向")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round1_analyze_brief"
        )
        
        if not result:
            raise RuntimeError("第1轮对话失败：无法分析角色方向")
        
        return result
    
    def _round2_protagonist_design(self, foundation_brief: Dict, final_plan: Dict, 
                                   direction: Dict) -> Dict:
        """
        第2轮：主角深度设计
        """
        # 提取世界观信息
        world_overview = foundation_brief.get("world_overview", "")
        power_system = foundation_brief.get("power_system", "")
        
        # 从 final_plan 获取主角设定
        core_setting = final_plan.get("core_setting", {})
        protagonist_seed = core_setting.get("protagonist", {})
        golden_finger = core_setting.get("golden_finger", {})
        
        user_prompt = f"""基于角色方向分析，深度设计主角。

**世界观背景**
- 世界概述：{world_overview}
- 力量体系：{power_system}

**Final Plan 主角设定**
- 身份：{protagonist_seed.get("identity", "未指定")}
- 性格：{protagonist_seed.get("personality", "未指定")}
- 目标：{protagonist_seed.get("goal", "未指定")}

**金手指**
- 能力：{golden_finger.get("ability", "未指定")}
- 限制：{golden_finger.get("limitations", "未指定")}
- 升级路线：{golden_finger.get("upgrade_path", "未指定")}

**角色方向**
{json.dumps(direction.get("protagonist_positioning", {}), ensure_ascii=False, indent=2)}

**设计任务**
设计完整的主角人设，包含：

1. **基础信息**
   - 姓名（符合题材风格）
   - 年龄、性别、外貌特征
   - 背景故事（与末世/世界观相关的经历）

2. **性格特征**
   - 核心性格（3-5个关键词）
   - 行为模式
   - 价值观和信念
   - 缺陷和成长空间

3. **目标与动机**
   - 短期目标（第一阶段）
   - 长期目标（全书）
   - 深层心理动机

4. **能力设定**
   - 初始能力（金手指）
   - 能力限制和代价
   - 成长潜力

5. **人际关系定位**
   - 在势力中的位置
   - 与关键角色的初始关系

**输出格式（JSON）**
{{
    "basic_info": {{
        "name": "主角姓名",
        "age": "年龄",
        "gender": "性别",
        "appearance": "外貌描述（100字内）",
        "background": "背景故事（150字内）"
    }},
    "personality": {{
        "core_traits": ["性格标签1", "性格标签2", "性格标签3"],
        "behavior_pattern": "典型行为模式描述",
        "values": "核心价值观",
        "flaws": "性格缺陷和成长空间"
    }},
    "goals": {{
        "short_term": "短期目标",
        "long_term": "长期目标",
        "motivation": "深层动机"
    }},
    "abilities": {{
        "initial": "初始能力描述",
        "limitations": "能力限制",
        "growth_potential": "成长潜力"
    }},
    "relationship_position": "人际关系定位描述"
}}"""
        
        logger.info("[Round 2] 设计主角")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round2_protagonist_design"
        )
        
        if not result:
            raise RuntimeError("第2轮对话失败：无法设计主角")
        
        return result
    
    def _round3_supporting_characters(self, foundation_brief: Dict, final_plan: Dict,
                                     protagonist: Dict) -> Dict:
        """
        第3轮：关键配角和反派设计
        """
        # 提取势力信息
        factions = foundation_brief.get("factions", [])
        main_conflict = foundation_brief.get("main_conflict", "")
        
        protagonist_name = protagonist.get("basic_info", {}).get("name", "主角")
        
        user_prompt = f"""基于主角设定，设计关键配角和反派。

**主角信息**
- 姓名：{protagonist_name}
- 性格：{protagonist.get("personality", {}).get("core_traits", [])}
- 能力：{protagonist.get("abilities", {}).get("initial", "")}

**势力格局**
{factions}

**核心冲突**
{main_conflict}

**设计任务**
1. **核心盟友（2-3人）**
   - 每个人：姓名、定位、与主角的关系、在故事中的作用

2. **女主/男主（1人，如适用）**
   - 姓名、定位、与主角的感情线发展

3. **主要反派（1-2人）**
   - 姓名、定位、与主角的冲突、动机

4. **势力代表（根据势力数量）**
   - 各势力的关键人物

**设计原则**
- 配角要有鲜明的记忆点
- 反派要有合理的动机，不是单纯为恶
- 角色间关系要有张力和发展空间

**输出格式（JSON）**
{{
    "supporting_characters": [
        {{
            "role": "盟友1",
            "name": "姓名",
            "positioning": "定位描述",
            "relationship_with_protagonist": "与主角关系",
            "story_function": "在故事中的作用"
        }},
        {{
            "role": "女主/男主",
            "name": "姓名",
            "positioning": "定位描述",
            "relationship_arc": "感情线发展"
        }}
    ],
    "antagonist": {{
        "name": "反派姓名",
        "positioning": "定位描述",
        "motivation": "动机（要有合理性）",
        "conflict_with_protagonist": "与主角的冲突",
        "threat_level": "威胁等级"
    }},
    "faction_representatives": [
        {{"faction": "势力名称", "representative": "代表人物", "role": "角色定位"}}
    ]
}}"""
        
        logger.info("[Round 3] 设计配角和反派")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round3_supporting_characters"
        )
        
        if not result:
            raise RuntimeError("第3轮对话失败：无法设计配角和反派")
        
        return result
    
    def _round4_emotional_blueprint(self, foundation_brief: Dict, final_plan: Dict,
                                   protagonist: Dict) -> Dict:
        """
        第4轮：情绪蓝图规划
        """
        # 提取全书结构
        book_structure = final_plan.get("book_structure", {})
        stages = book_structure.get("stages", [])
        
        protagonist_name = protagonist.get("basic_info", {}).get("name", "主角")
        
        user_prompt = f"""基于全书结构和主角设定，规划情绪蓝图。

**主角**
- 姓名：{protagonist_name}
- 目标：{protagonist.get("goals", {}).get("long_term", "")}
- 性格：{protagonist.get("personality", {}).get("core_traits", [])}

**全书阶段结构**
{json.dumps(stages, ensure_ascii=False, indent=2)}

**设计任务**
1. **全书情绪弧线**
   - 整体情绪走向（如：压抑→希望→危机→爆发→登顶）
   - 每个阶段的情绪基调

2. **关键情绪转折点**
   - 全书3-5个关键情绪转折
   - 每个转折点的：位置（章节）、情绪变化、触发事件

3. **情绪主题**
   - 全书要传递的核心情感体验
   - 读者应该获得的情感共鸣

**设计原则**
- 情绪要有起伏，不能一成不变
- 高潮前要铺垫，高潮后要有缓冲
- 情绪转折要与剧情发展匹配

**输出格式（JSON）**
{{
    "emotional_arcs": [
        {{
            "stage": "阶段名称",
            "emotional_tone": "情绪基调",
            "reader_feeling": "读者应该感受到的情绪"
        }}
    ],
    "key_emotional_beats": [
        {{
            "chapter_percent": 10,
            "description": "第一个情绪转折点",
            "emotional_shift": "从什么情绪转到什么情绪"
        }}
    ],
    "emotional_themes": [
        "核心情感主题1",
        "核心情感主题2"
    ]
}}"""
        
        logger.info("[Round 4] 规划情绪蓝图")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round4_emotional_blueprint"
        )
        
        if not result:
            raise RuntimeError("第4轮对话失败：无法规划情绪蓝图")
        
        return result
    
    def _round5_growth_plan(self, foundation_brief: Dict, final_plan: Dict,
                           protagonist: Dict, emotional_blueprint: Dict) -> Dict:
        """
        第5轮：成长里程碑设计
        """
        # 提取全书结构
        book_structure = final_plan.get("book_structure", {})
        stages = book_structure.get("stages", [])
        
        # 提取能力设定
        abilities = protagonist.get("abilities", {})
        golden_finger = final_plan.get("core_setting", {}).get("golden_finger", {})
        
        user_prompt = f"""基于全书结构和情绪蓝图，设计主角成长路线。

**主角能力**
- 初始：{abilities.get("initial", "")}
- 限制：{abilities.get("limitations", "")}
- 成长潜力：{abilities.get("growth_potential", "")}

**全书阶段**
{json.dumps([{"name": s.get("name"), "goal": s.get("goal")} for s in stages], ensure_ascii=False, indent=2)}

**情绪弧线**
{json.dumps(emotional_blueprint.get("emotional_arcs", []), ensure_ascii=False, indent=2)}

**设计任务**
1. **主角成长阶段**
   - 每个阶段的成长目标
   - 能力提升的时间点
   - 性格/心智的成长

2. **里程碑事件**
   - 全书5-8个关键里程碑
   - 每个里程碑：章节位置、事件、成长意义

3. **能力进阶路线**
   - 金手指的升级节点
   - 每次升级带来的变化

4. **人际关系发展**
   - 与关键角色的关系变化节点

**输出格式（JSON）**
{{
    "protagonist_growth": [
        {{
            "stage": "阶段名称",
            "growth_goal": "成长目标",
            "ability_progression": "能力提升",
            "mental_growth": "心智成长"
        }}
    ],
    "milestone_events": [
        {{
            "chapter_range": "章节范围",
            "event": "里程碑事件",
            "significance": "成长意义"
        }}
    ],
    "power_progression": [
        {{
            "chapter": "章节",
            "upgrade": "能力提升",
            "impact": "带来的影响"
        }}
    ],
    "relationship_development": [
        {{
            "character": "角色",
            "relationship_change": "关系变化",
            "chapter": "发生章节"
        }}
    ]
}}"""
        
        logger.info("[Round 5] 设计成长里程碑")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round5_growth_plan"
        )
        
        if not result:
            raise RuntimeError("第5轮对话失败：无法设计成长里程碑")
        
        return result
    
    def _round6_integrate(self, protagonist: Dict, supporting: Dict,
                         emotional_blueprint: Dict, growth_plan: Dict) -> Dict:
        """
        第6轮：整合所有输出，生成标准格式
        """
        user_prompt = f"""整合所有角色与叙事设计，生成标准输出格式。

**主角设计**
{json.dumps(protagonist, ensure_ascii=False, indent=2)}

**配角和反派设计**
{json.dumps(supporting, ensure_ascii=False, indent=2)}

**情绪蓝图**
{json.dumps(emotional_blueprint, ensure_ascii=False, indent=2)}

**成长规划**
{json.dumps(growth_plan, ensure_ascii=False, indent=2)}

**整合任务**
1. 将主角、配角、反派整合为 character_design 格式
2. 整理 emotional_blueprint 格式
3. 整理 global_growth_plan 格式
4. 确保所有必需字段都存在

**输出格式（JSON）**
{{
    "character_design": {{
        "protagonist": {{
            "basic_info": {{
                "name": "主角姓名",
                "age": "年龄",
                "gender": "性别",
                "appearance": "外貌",
                "background": "背景"
            }},
            "goals": {{
                "short_term": "短期目标",
                "long_term": "长期目标",
                "motivation": "动机"
            }},
            "abilities": {{
                "initial": "初始能力",
                "limitations": "限制",
                "growth_potential": "成长潜力"
            }},
            "personality": {{
                "core_traits": ["性格标签"],
                "behavior_pattern": "行为模式",
                "values": "价值观",
                "flaws": "缺陷"
            }},
            "relationship_position": "人际定位"
        }},
        "supporting_characters": [
            {{"role": "角色定位", "name": "姓名", "description": "描述"}}
        ],
        "antagonist": {{
            "name": "反派姓名",
            "positioning": "定位",
            "motivation": "动机"
        }}
    }},
    "emotional_blueprint": {{
        "emotional_arcs": [
            {{"stage": "阶段", "emotional_tone": "情绪基调", "reader_feeling": "读者感受"}}
        ],
        "key_emotional_beats": [
            {{"chapter_percent": 10, "description": "转折点", "emotional_shift": "情绪变化"}}
        ],
        "emotional_themes": ["主题1", "主题2"]
    }},
    "global_growth_plan": {{
        "protagonist_growth": [
            {{"stage": "阶段", "growth_goal": "成长目标", "ability_progression": "能力提升", "mental_growth": "心智成长"}}
        ],
        "milestone_events": [
            {{"chapter_range": "章节", "event": "事件", "significance": "意义"}}
        ],
        "power_progression": [
            {{"chapter": "章节", "upgrade": "升级", "impact": "影响"}}
        ],
        "relationship_development": [
            {{"character": "角色", "relationship_change": "关系变化", "chapter": "章节"}}
        ]
    }}
}}"""
        
        logger.info("[Round 6] 整合输出")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round6_integrate"
        )
        
        if not result:
            raise RuntimeError("第6轮对话失败：无法整合输出")
        
        return result
    
    # =====================================================================
    # 验证与导出
    # =====================================================================
    
    def _validate_output(self, output: Dict) -> bool:
        """验证产物格式"""
        from src.core.session_mode.validators import CharacterNarrativeValidator
        
        validator = CharacterNarrativeValidator()
        result = validator.validate(output)
        
        if not result.is_valid:
            logger.error(f"产物验证失败:\n{result.get_error_report()}")
        
        return result.is_valid
    
    def export_results(self) -> Dict[str, Any]:
        """
        导出结果（兼容传统格式）
        """
        return self.results.get("final_integrated", {})
    
    def export_context_brief(self) -> Dict[str, Any]:
        """
        导出 Context Brief 传递给 StructurePlanningSession
        """
        character_design = self.results.get("final_integrated", {}).get("character_design", {})
        emotional_blueprint = self.results.get("final_integrated", {}).get("emotional_blueprint", {})
        growth_plan = self.results.get("final_integrated", {}).get("global_growth_plan", {})
        
        protagonist = character_design.get("protagonist", {})
        
        return {
            "protagonist_profile": {
                "name": protagonist.get("basic_info", {}).get("name", ""),
                "core_traits": protagonist.get("personality", {}).get("core_traits", []),
                "goals": protagonist.get("goals", {}).get("long_term", ""),
                "abilities": protagonist.get("abilities", {}).get("initial", "")
            },
            "key_supporting_chars": [
                {"role": sc.get("role", ""), "name": sc.get("name", "")}
                for sc in character_design.get("supporting_characters", [])
            ],
            "antagonist": {
                "name": character_design.get("antagonist", {}).get("name", ""),
                "motivation": character_design.get("antagonist", {}).get("motivation", "")
            },
            "emotional_arc": emotional_blueprint.get("emotional_arcs", []),
            "key_emotional_turning_points": [
                beat.get("description", "")
                for beat in emotional_blueprint.get("key_emotional_beats", [])
            ],
            "growth_milestones": [
                event.get("event", "")
                for event in growth_plan.get("milestone_events", [])
            ],
            "generation_timestamp": datetime.now().isoformat(),
            "session_type": "CharacterNarrativeSession"
        }
