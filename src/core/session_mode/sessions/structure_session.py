"""
Structure Session - 结构规划会话
负责: 全书阶段划分 + 阶段详细计划 + 补充角色

修复: stage_details 改为多轮对话逐阶段生成，避免单轮输出过长导致卡死
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

        # Step 2: 阶段详细计划（多轮对话逐阶段生成）
        step2_result = self._execute_stage_details_multiround()
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

        # 🔥 修复：大章数小说减少建议阶段数，降低后续多轮生成压力
        if total_chapters >= 400:
            suggest_min = total_chapters // 5
            suggest_max = total_chapters // 3
        elif total_chapters >= 300:
            suggest_min = total_chapters // 5
            suggest_max = total_chapters // 4
        else:
            suggest_min = total_chapters // 6
            suggest_max = total_chapters // 4

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "stage_overview",
            default="",
            total_chapters=total_chapters,
            growth_stage_count=len(growth_stages),
            milestone_count=len(milestones),
            suggest_min=suggest_min,
            suggest_max=suggest_max
        )
        
        if not prompt:
            self.session_logger.error("[StructureSession] 未找到 stage_overview 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="stage_overview")

    def _execute_stage_details_multiround(self) -> Optional[Dict]:
        """
        执行步骤2: 阶段详细计划（多轮对话逐阶段生成）
        
        在同一会话中，每次只生成 1 个阶段的详细计划，避免单轮输出过长导致卡死。
        """
        stage_overview = self.results.get("stage_overview", {})
        # 兼容 LLM 可能忽略顶层字段的情况：优先取顶层 stages，否则取 overall_stage_plan.stages
        stages = stage_overview.get("stages", []) or stage_overview.get("overall_stage_plan", {}).get("stages", [])
        stage_count = len(stages)

        if stage_count == 0:
            self.session_logger.error("缺少阶段概览，无法生成详细计划")
            return None

        self.session_logger.info(
            f"[StructureSession] 开始逐阶段生成详细计划，共 {stage_count} 个阶段"
        )

        stage_writing_plans = {}
        
        # 前 3 个阶段做详细生成，后面的做精简生成
        detailed_count = min(3, stage_count)
        
        for idx, stage in enumerate(stages):
            stage_name = stage.get("stage_name", f"阶段{idx+1}")
            is_detailed = idx < detailed_count
            
            self.session_logger.info(
                f"[StructureSession] 正在生成阶段 {idx+1}/{stage_count}: {stage_name} "
                f"({'详细' if is_detailed else '精简'})"
            )
            
            detail_level = self._build_detail_level_text(stage, is_detailed)
            
            from src.prompts.Prompts import Prompts
            prompts = Prompts()
            prompt = prompts.format(
                "stage_detail_single",
                default="",
                stage_name=stage_name,
                chapter_range=stage.get("chapter_range", ""),
                chapter_count=stage.get("chapter_count", 0),
                core_conflict=stage.get("core_conflict", ""),
                emotional_focus=stage.get("emotional_focus", ""),
                growth_goals=stage.get("growth_goals", ""),
                key_events=json.dumps(stage.get("key_events", []), ensure_ascii=False),
                detail_level=detail_level
            )
            
            if not prompt:
                self.session_logger.error("[StructureSession] 未找到 stage_detail_single 提示词模板")
                return None
            
            result = self.send_structured_message(prompt, purpose=f"stage_detail_{idx+1}")
            
            if result and stage_name in result:
                stage_writing_plans[stage_name] = result[stage_name]
                self.session_logger.info(f"[StructureSession] 阶段 {stage_name} 生成成功")
            elif result:
                # 有时 LLM 会忽略顶层字段要求，返回一个对象，我们尝试适配
                first_key = next(iter(result.keys())) if result else None
                if first_key and isinstance(result.get(first_key), dict):
                    stage_writing_plans[stage_name] = result[first_key]
                    self.session_logger.info(f"[StructureSession] 阶段 {stage_name} 生成成功（键名适配: {first_key}）")
                else:
                    self.session_logger.warning(
                        f"[StructureSession] 阶段 {stage_name} 返回格式异常，跳过"
                    )
            else:
                self.session_logger.error(f"[StructureSession] 阶段 {stage_name} 生成失败")
                return None

        return {"stage_writing_plans": stage_writing_plans}

    def _build_detail_level_text(self, stage: Dict, is_detailed: bool) -> str:
        """构建单个阶段的详细程度说明"""
        chapter_count = stage.get("chapter_count", 0)
        if is_detailed:
            if chapter_count > 50:
                return (
                    "本阶段需要详细规划。由于章节数较多（超过50章），"
                    "请将关键转折点章节单独列出，非关键的连续章节可合并为范围（如'31-40'）并简要概述。"
                    "确保每10章至少有一个明确的情绪起伏或剧情推进点被单独标注。"
                )
            return (
                "本阶段需要详细规划：chapter_breakdown 必须尽量覆盖该阶段的每一章，"
                "每章都要有标题、关键事件、情绪节奏、剧情推进点和悬念设置。"
            )
        else:
            return (
                "本阶段做精简规划：chapter_breakdown 只列出关键章节（至少5-8个转折点），"
                "其余连续章节可合并为范围并简要概述整体剧情走向。"
            )

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
