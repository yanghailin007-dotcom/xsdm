"""
Structure Session - 结构规划会话
负责: 全书阶段划分 + 阶段详细计划 + 补充角色
"""

import json
from typing import Dict, Optional, Any, List

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class StructureSession(NovelGenerationSession):
    """结构规划会话"""

    STEPS = ["stage_overview", "stage_details", "supplementary_chars"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results: Dict[str, Any] = {}

    def execute_all_steps(self) -> bool:
        """执行 Structure 域的所有步骤"""
        self.session_logger.info("[StructureSession] 开始执行步骤...")

        # Step 1: 全书阶段划分
        step1_result = self._execute_stage_overview()
        if not step1_result:
            self.session_logger.error("[StructureSession] 阶段划分步骤失败")
            return False
        self.results["stage_overview"] = step1_result

        # Step 2: 阶段详细计划
        step2_result = self._execute_stage_details()
        if not step2_result:
            self.session_logger.error("[StructureSession] 阶段详细计划步骤失败")
            return False
        self.results["stage_details"] = step2_result

        # Step 3: 补充角色
        step3_result = self._execute_supplementary_chars()
        if not step3_result:
            self.session_logger.warning("[StructureSession] 补充角色步骤失败，继续使用已有角色")
            step3_result = {"supplementary_characters": []}
        self.results["supplementary_chars"] = step3_result

        self.session_logger.info("[StructureSession] 所有步骤执行完成")
        return True

    def _execute_stage_overview(self) -> Optional[Dict]:
        """执行步骤1: 全书阶段划分"""
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        global_growth = self.novel_data.get("global_growth_plan", {})
        
        # 提取主角成长阶段数量
        growth_stages = global_growth.get('protagonist_growth', [])
        milestones = global_growth.get('milestone_events', [])

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "stage_overview",
            default="",
            total_chapters=total_chapters,
            growth_stage_count=len(growth_stages),
            milestone_count=len(milestones),
            suggest_min=total_chapters // 6,
            suggest_max=total_chapters // 4
        )
        
        if not prompt:
            self.session_logger.error("[StructureSession] 未找到 stage_overview 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="stage_overview")

    def _execute_stage_details(self) -> Optional[Dict]:
        """执行步骤2: 阶段详细计划"""
        stage_overview = self.results.get("stage_overview", {})
        stages = stage_overview.get("stages", [])
        stage_count = len(stages)

        if stage_count == 0:
            self.session_logger.error("缺少阶段概览，无法生成详细计划")
            return None

        # 区分详细阶段和概览阶段
        detailed_stages = stages[:2] if len(stages) >= 2 else stages
        overview_stages = stages[2:] if len(stages) > 2 else []

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "stage_details",
            default="",
            stage_count=stage_count,
            stage_overview_summary=json.dumps([{"num": s.get("stage_number"), "name": s.get("stage_name"), "chapters": s.get("chapter_range"), "core_conflict": s.get("core_conflict")} for s in stages], ensure_ascii=False, indent=2),
            detailed_stage_count=len(detailed_stages),
            detailed_stage_names=", ".join([s.get('stage_name') for s in detailed_stages]),
            overview_stage_count=len(overview_stages),
            overview_stage_names=", ".join([s.get('stage_name') for s in overview_stages]) if overview_stages else "无"
        )
        
        if not prompt:
            self.session_logger.error("[StructureSession] 未找到 stage_details 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="stage_details")

    def _execute_supplementary_chars(self) -> Optional[Dict]:
        """执行步骤3: 补充角色生成"""
        stage_plans = self.results.get("stage_details", {})
        stage_writing_plans = stage_plans.get("stage_writing_plans", {})
        stage_count = len(stage_writing_plans)
        
        # 提取各阶段的关键事件作为参考
        stage_events = {}
        for stage_name, plan in stage_writing_plans.items():
            breakdown = plan.get("chapter_breakdown", [])
            events = [b.get("key_events", "") for b in breakdown if b.get("key_events")]
            stage_events[stage_name] = events[:3]  # 只取前3个关键事件

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "supplementary_chars",
            default="",
            stage_count=stage_count,
            stage_events=json.dumps(stage_events, ensure_ascii=False, indent=2)
        )
        
        if not prompt:
            self.session_logger.error("[StructureSession] 未找到 supplementary_chars 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="supplementary_chars")

    def export_results(self) -> Dict[str, Any]:
        """导出结果，映射到 novel_data 的字段名"""
        overview = self.results.get("stage_overview", {})
        details = self.results.get("stage_details", {})
        supplementary = self.results.get("supplementary_chars", {})

        return {
            "overall_stage_plans": overview,
            "stage_writing_plans": details.get("stage_writing_plans", {}),
            "supplementary_characters": supplementary.get("supplementary_characters", []),
            # expectation_mapping 和 system_init 在此模式下视为结构规划的自然产物
            "expectation_mapping": {"status": "integrated", "source": "structure_session"},
            "system_init": {"status": "completed", "source": "structure_session"},
        }
