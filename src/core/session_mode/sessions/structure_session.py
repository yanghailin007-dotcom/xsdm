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
        emotional_blueprint = self.novel_data.get("emotional_blueprint", {})
        global_growth = self.novel_data.get("global_growth_plan", {})

        prompt = f"""
请执行【步骤1：全书阶段划分】

基于情绪蓝图和成长规划，将全书 {total_chapters} 章划分为若干阶段。

## 情绪蓝图要点
- 情绪曲线: {len(emotional_blueprint.get('emotional_curves', []))} 个阶段
- 情绪钩子: {emotional_blueprint.get('emotional_hooks', [])}

## 成长规划要点
- 主角成长阶段: {len(global_growth.get('protagonist_growth', []))}
- 关键里程碑: {len(global_growth.get('milestone_events', []))}

## 输出要求
返回合法 JSON，顶层字段 "overall_stage_plan"，包含：
- stages: 阶段列表，每个阶段包含:
  - stage_number: 阶段序号
  - stage_name: 阶段名称
  - chapter_range: 章节范围（如 "1-30"）
  - chapter_count: 本章节点数
  - core_conflict: 核心冲突
  - emotional_focus: 情绪重点
  - growth_goals: 成长目标
  - key_events: 关键事件列表（3-5条）

建议划分 5-8 个阶段，每阶段 20-50 章。
"""
        return self.send_structured_message(prompt, purpose="stage_overview")

    def _execute_stage_details(self) -> Optional[Dict]:
        """执行步骤2: 阶段详细计划"""
        stage_overview = self.results.get("stage_overview", {})
        stages = stage_overview.get("stages", [])
        stage_count = len(stages)

        if stage_count == 0:
            self.session_logger.error("缺少阶段概览，无法生成详细计划")
            return None

        prompt = f"""
请执行【步骤2：阶段详细写作计划】

为全部 {stage_count} 个阶段生成详细的写作计划。

## 阶段概览
{json.dumps([{"num": s.get("stage_number"), "name": s.get("stage_name"), "chapters": s.get("chapter_range")} for s in stages], ensure_ascii=False, indent=2)}

## 输出要求
返回合法 JSON，顶层字段 "stage_writing_plans"，为对象格式（键为阶段名称）：
{{
  "阶段1名称": {{
    "opening_hook": "开局钩子设计",
    "chapter_breakdown": [
      {{
        "chapter_num": 1,
        "title": "章节标题",
        "key_events": "关键事件",
        "emotional_beats": "情绪节奏",
        "plot_progression": "剧情推进点",
        "suspense_setup": "悬念设置"
      }}
    ],
    "cliffhanger": "阶段结尾悬念",
    "transition_to_next": "与下阶段衔接"
  }}
}}

注意：
- 前 2 个阶段（约前 60 章）的 chapter_breakdown 需要详细，每章都要列出
- 后续阶段可以只列关键章节的细纲，其余章节用概览描述
- 总输出长度尽量精简，突出重点
"""
        return self.send_structured_message(prompt, purpose="stage_details")

    def _execute_supplementary_chars(self) -> Optional[Dict]:
        """执行步骤3: 补充角色生成"""
        stage_plans = self.results.get("stage_details", {})
        stage_writing_plans = stage_plans.get("stage_writing_plans", {})
        stage_count = len(stage_writing_plans)

        prompt = f"""
请执行【步骤3：全书补充角色生成】

基于已生成的 {stage_count} 个阶段详细计划，生成全书需要的补充角色。

## 输出要求
返回合法 JSON，顶层字段 "supplementary_characters"，为列表格式：
[
  {{
    "character_name": "角色名",
    "character_type": "角色类型（盟友/反派/中立/NPC）",
    "importance": "重要程度（主要/次要/龙套）",
    "introduce_stage": "登场阶段名称",
    "introduce_chapter": "登场章节号",
    "role_in_story": "在故事中的作用",
    "relationship_to_protagonist": "与主角关系",
    "key_traits": "关键特征",
    "plot_function": "剧情功能说明"
  }}
]

要求：
- 覆盖所有主要阶段的关键角色
- 与已有核心角色形成互补
- 每个角色有明确的剧情功能
- 预计生成 10-20 个补充角色
"""
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
