"""
ExpectationSystemSession - 期待感系统会话（Session D）
=========================================================

职责：
- 提取和设计期待感元素
- 规划元素登场时机
- 系统初始化配置

对话轮次：3轮
1. 分析前序产物，提取期待感元素
2. 设计元素登场时机和节奏
3. 系统集成与验证

产物格式（必须与传统模式一致）：
{
    "expectation_mapping": {
        "expectation_elements": [...],
        "element_schedule": {...},  # 可选
        "reveal_timing": {...}      # 可选
    },
    "system_init": {
        "initialized_systems": [...],
        "status": "completed"
    }
}
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.utils.logger import get_logger

logger = get_logger("ExpectationSystemSession")


class ExpectationSystemSession(NovelGenerationSession):
    """
    期待感系统会话
    
    合并原步骤12-13（expectation_mapping + system_init）
    """
    
    STEPS = ["expectation_mapping", "system_init"]
    
    def __init__(
        self,
        api_client,
        novel_data: Optional[Dict] = None,
        context_briefs: Optional[List[str]] = None,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # Session D 接收前面所有 Session 的 Context Briefs
        super().__init__(
            api_client=api_client,
            domain="expectation_system",
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
        logger.info(f"[ExpectationSystem] 进度 {progress}%: {message}")
    
    # =====================================================================
    # 主执行流程
    # =====================================================================
    
    def execute_all_steps(self) -> Dict[str, Any]:
        """
        执行全部3轮对话
        
        🔥 基于前面所有 Session 的产物生成期待感系统
        
        Returns:
            完整产物字典
        """
        logger.info("=" * 60)
        logger.info("ExpectationSystemSession 开始执行")
        logger.info("基于前序产物生成期待感系统...")
        logger.info("=" * 60)
        
        # 🔥 验证输入：必须有必要的产物数据
        character_design = self.novel_data.get("character_design", {})
        stage_plans = self.novel_data.get("overall_stage_plans", {})
        
        if not character_design:
            logger.warning("novel_data 中缺少 character_design")
        
        if not stage_plans:
            logger.warning("novel_data 中缺少 overall_stage_plans")
        
        # 🔥 解析 Context Briefs
        foundation_brief = {}
        character_brief = {}
        structure_brief = {}
        
        if self.context_briefs:
            try:
                if len(self.context_briefs) > 0:
                    foundation_brief = json.loads(self.context_briefs[0]) if isinstance(self.context_briefs[0], str) else self.context_briefs[0]
                if len(self.context_briefs) > 1:
                    character_brief = json.loads(self.context_briefs[1]) if isinstance(self.context_briefs[1], str) else self.context_briefs[1]
                if len(self.context_briefs) > 2:
                    structure_brief = json.loads(self.context_briefs[2]) if isinstance(self.context_briefs[2], str) else self.context_briefs[2]
            except Exception as e:
                logger.warning(f"解析 Context Briefs 时出错: {e}")
        
        try:
            # 第1轮：分析前序产物，提取期待感元素
            self._update_progress(15, "分析前序产物，提取期待感元素...")
            step1_result = self._round1_analyze_expectation_elements(
                foundation_brief, character_brief, structure_brief
            )
            self.results["expectation_elements"] = step1_result
            
            # 第2轮：设计元素登场时机
            self._update_progress(50, "设计期待感元素登场时机...")
            step2_result = self._round2_design_reveal_timing(step1_result)
            self.results["reveal_timing"] = step2_result
            
            # 第3轮：整合与系统集成
            self._update_progress(85, "整合期待感系统，完成初始化...")
            final_result = self._round3_integrate(step1_result, step2_result)
            
            # 验证产物格式
            self._update_progress(95, "验证产物格式...")
            if not self._validate_output(final_result):
                logger.error("产物格式验证失败")
                raise ValueError("产物格式不符合要求")
            
            self._update_progress(100, "期待感系统完成")
            
            logger.info("✅ ExpectationSystemSession 执行完成")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ ExpectationSystemSession 执行失败: {e}", exc_info=True)
            raise
    
    # =====================================================================
    # 各轮对话实现
    # =====================================================================
    
    def _round1_analyze_expectation_elements(
        self,
        foundation_brief: Dict,
        character_brief: Dict,
        structure_brief: Dict
    ) -> Dict:
        """
        第1轮：分析前序产物，提取期待感元素
        """
        # 提取关键信息
        golden_finger = foundation_brief.get("power_system", "")
        main_conflict = foundation_brief.get("main_conflict", "")
        
        protagonist_name = character_brief.get("protagonist_profile", {}).get("name", "主角")
        growth_milestones = character_brief.get("growth_milestones", [])
        emotional_turning_points = character_brief.get("key_emotional_turning_points", [])
        
        # 从 novel_data 获取更详细的信息
        character_design = self.novel_data.get("character_design", {})
        antagonist = character_design.get("antagonist", {})
        
        final_plan = self.novel_data.get("final_plan") or self.novel_data.get("selected_plan", {})
        core_setting = final_plan.get("core_setting", {})
        golden_finger_detail = core_setting.get("golden_finger", {})
        
        user_prompt = f"""基于前序所有产物，提取和设计期待感元素。

**基础设定信息**
- 金手指：{golden_finger}
- 核心冲突：{main_conflict}

**主角信息**
- 姓名：{protagonist_name}
- 成长里程碑：{json.dumps(growth_milestones, ensure_ascii=False)}
- 情绪转折点：{json.dumps(emotional_turning_points, ensure_ascii=False)}

**反派信息**
- 姓名：{antagonist.get("name", "未命名")}
- 动机：{antagonist.get("motivation", "")}

**金手指详细设定**
- 能力：{golden_finger_detail.get("ability", "")}
- 限制：{golden_finger_detail.get("limitations", "")}
- 升级路线：{golden_finger_detail.get("upgrade_path", "")}

**设计任务**
识别全书所有期待感元素，包括：

1. **金手指相关期待**（3-5个）
   - 能力觉醒/升级的节点
   - 新功能的解锁
   - 能力极限的突破

2. **剧情悬念**（3-5个）
   - 核心伏笔（末世真相、势力秘密等）
   - 反派阴谋的揭示
   - 主角身世的秘密

3. **情感期待**（2-3个）
   - 主角与关键角色的关系发展
   - 情感高潮点

4. **势力发展期待**（2-3个）
   - 势力扩张的关键节点
   - 与其他势力的博弈结果

5. **情绪爆点**（3-5个）
   - 全书最重要的情绪高潮
   - 读者最期待的场景

**输出格式（JSON）**
{{
    "expectation_elements": [
        {{
            "element_id": "元素编号（如：GF_1表示金手指第1个）",
            "name": "元素名称",
            "type": "类型：golden_finger/plot/emotion/faction/emotion_peak",
            "description": "元素描述",
            "source": "来源：final_plan/character_design/stage_plan等",
            "importance": "重要程度：critical/high/medium",
            "expected_impact": "对读者的预期冲击力"
        }}
    ],
    "element_summary": {{
        "total_count": 15,
        "critical_elements": ["关键元素1", "关键元素2"],
        "reader_expectations": "读者对全书的主要期待总结"
    }}
}}"""
        
        logger.info("[Round 1] 分析期待感元素")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round1_expectation_elements"
        )
        
        if not result:
            raise RuntimeError("第1轮对话失败：无法分析期待感元素")
        
        return result
    
    def _round2_design_reveal_timing(self, elements: Dict) -> Dict:
        """
        第2轮：设计元素登场时机
        """
        expectation_elements = elements.get("expectation_elements", [])
        
        # 获取全书结构
        stage_plans = self.novel_data.get("overall_stage_plans", {})
        stages = stage_plans.get("overall_stage_plan", {}).get("stages", [])
        
        # 获取情绪蓝图
        emotional_blueprint = self.novel_data.get("emotional_blueprint", {})
        emotional_arcs = emotional_blueprint.get("emotional_arcs", [])
        
        user_prompt = f"""基于期待感元素，设计每个元素的最佳登场时机。

**期待感元素列表**
{json.dumps(expectation_elements, ensure_ascii=False, indent=2)}

**全书阶段结构**
{json.dumps([{"name": s.get("stage_name"), "range": s.get("chapter_range")} for s in stages], ensure_ascii=False, indent=2)}

**情绪弧线**
{json.dumps(emotional_arcs, ensure_ascii=False, indent=2)}

**设计任务**
为每个期待感元素设计最佳登场时机：

1. **时机规划原则**
   - 关键元素要分散，不要挤在一起
   - 每个阶段都要有期待点
   - 高潮前要层层铺垫
   - 考虑情绪曲线的配合

2. **每元素的规划**
   - 初现（第一次提及/暗示）
   - 铺垫（多次提及，增加期待）
   - 揭示（正式揭晓，满足期待）
   - 后续（持续影响）

3. **特别设计**
   - 前10章的"钩子"设计（吸引读者继续阅读）
   - 每50章的大高潮设计
   - 全书终极期待的铺垫节奏

**输出格式（JSON）**
{{
    "element_schedule": [
        {{
            "element_id": "元素编号",
            "element_name": "元素名称",
            "timeline": [
                {{
                    "phase": "初现/铺垫/揭示/后续",
                    "chapter_range": "章节范围（如：1-10）",
                    "method": "呈现方式（暗示/明示/侧面描写等）",
                    "intensity": "强度：subtle/building/climax/resolution"
                }}
            ],
            "key_chapters": ["关键章节1", "关键章节2"],
            "interaction_with_other_elements": ["相关元素编号"]
        }}
    ],
    "critical_moments": [
        {{
            "chapter": "章节号",
            "moment": "关键时刻描述",
            "elements_involved": ["涉及的元素"],
            "reader_expected_reaction": "预期读者反应"
        }}
    ],
    "expectation_curve": "全书期待值曲线描述（如：逐渐攀升-中段高峰-最终爆发）"
}}"""
        
        logger.info("[Round 2] 设计登场时机")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round2_reveal_timing"
        )
        
        if not result:
            raise RuntimeError("第2轮对话失败：无法设计登场时机")
        
        return result
    
    def _round3_integrate(self, elements: Dict, timing: Dict) -> Dict:
        """
        第3轮：整合输出
        """
        user_prompt = f"""整合所有期待感系统设计，生成标准输出格式。

**期待感元素**
{json.dumps(elements.get("expectation_elements", []), ensure_ascii=False, indent=2)}

**登场时机规划**
{json.dumps(timing.get("element_schedule", []), ensure_ascii=False, indent=2)}

**关键时刻**
{json.dumps(timing.get("critical_moments", []), ensure_ascii=False, indent=2)}

**整合任务**
1. 整理为标准的 expectation_mapping 格式
2. 生成 system_init 信息
3. 验证所有关键字段

**输出格式（JSON）**
{{
    "expectation_mapping": {{
        "expectation_elements": [
            {{
                "id": "元素ID",
                "name": "元素名称",
                "type": "元素类型",
                "timeline": {{
                    "first_mention": "首次提及章节",
                    "buildup": "铺垫章节",
                    "reveal": "揭示章节",
                    "resolution": "后续影响章节"
                }},
                "key_chapters": ["关键章节"],
                "importance": "重要程度"
            }}
        ],
        "element_schedule": {{
            "by_chapter": {{
                "章节号": ["该章节的期待感元素"]
            }},
            "by_stage": {{
                "阶段名": ["该阶段的期待感元素"]
            }}
        }},
        "reveal_timing": {{
            "critical_reveals": [
                {{"chapter": "章节", "element": "元素", "impact": "影响力"}}
            ],
            "expectation_curve": "期待值曲线描述"
        }}
    }},
    "system_init": {{
        "initialized_systems": [
            "expectation_management",
            "character_consistency",
            "plot_tracking"
        ],
        "status": "completed",
        "initialization_timestamp": "{datetime.now().isoformat()}",
        "version": "1.0"
    }}
}}"""
        
        logger.info("[Round 3] 整合输出")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round3_integrate"
        )
        
        if not result:
            raise RuntimeError("第3轮对话失败：无法整合输出")
        
        return result
    
    # =====================================================================
    # 验证与导出
    # =====================================================================
    
    def _validate_output(self, output: Dict) -> bool:
        """验证产物格式"""
        from src.core.session_mode.validators import ExpectationSystemValidator
        
        validator = ExpectationSystemValidator()
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
        导出 Context Brief（这是最后一个 Session，可以给第二阶段使用）
        """
        expectation_mapping = self.results.get("final_integrated", {}).get("expectation_mapping", {})
        
        return {
            "critical_expectations": [
                elem.get("name", "")
                for elem in expectation_mapping.get("expectation_elements", [])
                if elem.get("importance") == "critical"
            ],
            "key_reveal_chapters": [
                reveal.get("chapter", "")
                for reveal in expectation_mapping.get("reveal_timing", {}).get("critical_reveals", [])
            ],
            "expectation_curve": expectation_mapping.get("reveal_timing", {}).get("expectation_curve", ""),
            "system_ready": True,
            "generation_timestamp": datetime.now().isoformat(),
            "session_type": "ExpectationSystemSession"
        }
