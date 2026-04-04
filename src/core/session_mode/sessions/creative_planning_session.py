"""
Creative Planning Session - 创意策划会话

从原始创意到选定爆款方案的完整对话过程。
支持两种模式：
- AUTO: AI 自我迭代优化，用户无感知
- INTERACTIVE: 用户参与多轮对话，共同打磨方案
"""

import json
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.core.session_mode.sessions.fanfiction_background_session import (
    FanfictionBackgroundSession,
    PlanningMode,
)


@dataclass
class CreativePlanningState:
    """创意策划会话状态（用于交互模式持久化）"""
    mode: str = "auto"
    current_phase: str = "diagnosis"  # diagnosis -> fanfiction -> initial_plans -> refinement -> finalization
    novel_seed: Dict[str, Any] = field(default_factory=dict)
    
    # 同人背景阶段
    fanfiction_detected: bool = False
    fanfiction_work_name: str = ""
    fanfiction_background_brief: str = ""
    fanfiction_background_locked: bool = False
    
    # 诊断与方案
    diagnosis: Dict[str, Any] = field(default_factory=dict)
    plan_candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_plan: Dict[str, Any] = field(default_factory=dict)
    refinement_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 最终产物
    final_plan_brief: Dict[str, Any] = field(default_factory=dict)


class CreativePlanningSession(NovelGenerationSession):
    """
    创意策划会话
    
    自动模式流程：
    1. 创意诊断
    2. 同人背景提取（如需要）
    3. 生成初版方案
    4. AI 编辑审查循环（自我优化 N 轮）
    5. 爆款化定型 -> final_plan_brief
    
    交互模式流程：
    1. 创意诊断
    2. 同人背景提取 -> 展示给用户 -> 用户校正 -> 确认
    3. 生成初版方案 -> 展示给用户
    4. 用户反馈循环（选择/修改）
    5. 爆款化定型 -> final_plan_brief
    """

    STEPS = [
        "creative_diagnosis",
        "fanfiction_background",
        "initial_planning",
        "plan_refinement",
        "explosive_finalization",
    ]

    def __init__(
        self,
        api_client,
        mode: PlanningMode = PlanningMode.AUTO,
        max_auto_iterations: int = 3,
        context_briefs: Optional[List[str]] = None,
        novel_data: Optional[Dict] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        super().__init__(
            api_client=api_client,
            domain="creative_planning",
            context_briefs=context_briefs or [],
            novel_data=novel_data or {},
            provider=provider,
            model_name=model_name,
            temperature=temperature,
        )
        self.mode = mode
        self.max_auto_iterations = max_auto_iterations
        self.state = CreativePlanningState(
            mode=mode.value,
            novel_seed=dict(novel_data or {}),
        )
        self._fanfiction_session: Optional[FanfictionBackgroundSession] = None

    def _get_domain_chinese_name(self) -> str:
        return "创意策划"

    # ==================================================================
    # 自动模式入口
    # ==================================================================
    def execute_all_steps(self) -> bool:
        """自动模式：一次性执行完整创意策划流程"""
        if self.mode != PlanningMode.AUTO:
            self.session_logger.error(
                "[CreativePlanningSession] INTERACTIVE 模式不支持 execute_all_steps"
            )
            return False

        self.session_logger.info(
            f"[CreativePlanningSession] 启动自动模式，最大迭代轮数: {self.max_auto_iterations}"
        )

        # Step 1: 创意诊断
        diagnosis = self._run_diagnosis()
        if not diagnosis:
            self.session_logger.error("[CreativePlanningSession] 创意诊断失败")
            return False
        self.state.diagnosis = diagnosis
        self.state.fanfiction_detected = diagnosis.get("is_fanfiction", False)
        self.state.fanfiction_work_name = diagnosis.get("fanfiction_work", "")

        # Step 2: 同人背景（如需要）
        if self.state.fanfiction_detected and self.state.fanfiction_work_name:
            fanfiction_result = self._run_fanfiction_background_auto()
            if fanfiction_result:
                self.state.fanfiction_background_brief = fanfiction_result.get(
                    "background_brief", ""
                )
                self.state.fanfiction_background_locked = True

        # Step 3: 初版方案
        plans = self._run_initial_plans()
        if not plans:
            self.session_logger.error("[CreativePlanningSession] 初版方案生成失败")
            return False
        self.state.plan_candidates = plans

        # Step 4: AI 自我优化循环
        selected_plan = self._run_editor_review_loop()
        if not selected_plan:
            # 如果没有通过审查，强行选择评分最高的
            selected_plan = max(plans, key=lambda p: p.get("market_fit_score", 0))
        self.state.selected_plan = selected_plan

        # Step 5: 爆款化定型
        final_brief = self._run_explosive_finalization()
        if not final_brief:
            self.session_logger.error("[CreativePlanningSession] 爆款化定型失败")
            return False
        self.state.final_plan_brief = final_brief

        self.session_logger.info(
            "[CreativePlanningSession] 自动模式执行完成，"
            f"最终对齐评分: {final_brief.get('market_alignment', {}).get('score', 'N/A')}"
        )
        return True

    # ==================================================================
    # 交互模式入口
    # ==================================================================
    def execute_interactive_step(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        交互模式：单步执行，根据当前状态和 user_input 推进流程
        
        Returns:
            包含 status, data, message, next_action 的字典
        """
        if self.mode != PlanningMode.INTERACTIVE:
            return {"status": "error", "message": "当前不是交互模式"}

        phase = self.state.current_phase

        # ------------------------------------------------------------------
        # Phase: diagnosis
        # ------------------------------------------------------------------
        if phase == "diagnosis":
            diagnosis = self._run_diagnosis()
            if not diagnosis:
                return {"status": "error", "message": "创意诊断失败"}
            self.state.diagnosis = diagnosis
            self.state.fanfiction_detected = diagnosis.get("is_fanfiction", False)
            self.state.fanfiction_work_name = diagnosis.get("fanfiction_work", "")

            if self.state.fanfiction_detected and self.state.fanfiction_work_name:
                self.state.current_phase = "fanfiction"
                # 自动启动同人背景提取，无需用户多等一轮空回复
                if self._fanfiction_session is None:
                    self._fanfiction_session = FanfictionBackgroundSession(
                        api_client=self.api_client,
                        work_name=self.state.fanfiction_work_name,
                        mode=PlanningMode.INTERACTIVE,
                        context_briefs=self.context_briefs,
                        novel_data=self.novel_data,
                        provider=self.provider,
                        model_name=self.model_name,
                        temperature=self.temperature,
                    )
                fanfiction_result = self._fanfiction_session.execute_interactive_step()
                return {
                    "status": "awaiting_fanfiction_review",
                    "data": {
                        "diagnosis": diagnosis,
                        "draft": fanfiction_result.get("draft", {}),
                    },
                    "message": fanfiction_result.get(
                        "message",
                        f"已提取《{self.state.fanfiction_work_name}》原作背景资料，请检查是否准确"
                    ),
                }
            else:
                self.state.current_phase = "initial_plans"
                plans = self._run_initial_plans()
                if not plans:
                    return {"status": "error", "message": "初版方案生成失败"}
                self.state.plan_candidates = plans
                return {
                    "status": "awaiting_plan_selection",
                    "data": {
                        "diagnosis": diagnosis,
                        "plans": plans,
                    },
                    "message": "已生成 3 个创作方向，请选择或提出修改意见"
                }

        # ------------------------------------------------------------------
        # Phase: fanfiction
        # ------------------------------------------------------------------
        if phase == "fanfiction":
            if self._fanfiction_session is None:
                self._fanfiction_session = FanfictionBackgroundSession(
                    api_client=self.api_client,
                    work_name=self.state.fanfiction_work_name,
                    mode=PlanningMode.INTERACTIVE,
                    context_briefs=self.context_briefs,
                    novel_data=self.novel_data,
                    provider=self.provider,
                    model_name=self.model_name,
                    temperature=self.temperature,
                )

            fanfiction_result = self._fanfiction_session.execute_interactive_step(
                user_input
            )

            if fanfiction_result["status"] == "locked":
                self.state.fanfiction_background_brief = fanfiction_result.get(
                    "background_brief", ""
                )
                self.state.fanfiction_background_locked = True
                self.state.current_phase = "initial_plans"
                
                # 同人背景确认后，继续生成方案
                plans = self._run_initial_plans()
                if not plans:
                    return {"status": "error", "message": "初版方案生成失败"}
                self.state.plan_candidates = plans
                return {
                    "status": "awaiting_plan_selection",
                    "data": {
                        "fanfiction_brief": self.state.fanfiction_background_brief,
                        "plans": plans,
                    },
                    "message": "背景资料已确认，已生成 3 个创作方向，请选择或提出修改意见"
                }

            elif fanfiction_result["status"] == "awaiting_review":
                return {
                    "status": "awaiting_fanfiction_review",
                    "data": {
                        "draft": fanfiction_result.get("draft", {}),
                    },
                    "message": fanfiction_result["message"]
                }
            else:
                return {
                    "status": "error",
                    "message": fanfiction_result.get("message", "同人背景处理失败")
                }

        # ------------------------------------------------------------------
        # Phase: initial_plans / refinement
        # ------------------------------------------------------------------
        if phase in ("initial_plans", "refinement"):
            if not user_input:
                return {
                    "status": "awaiting_plan_selection",
                    "data": {"plans": self.state.plan_candidates},
                    "message": "请选择一个方案或提出修改意见"
                }

            # 用户选择了一个方案（A/B/C 或方案名称）
            selected = self._try_parse_plan_selection(user_input)
            if selected:
                self.state.selected_plan = selected
                # 用户直接选择后，可以进入爆款化定型
                # 但也允许继续优化，所以这里返回 awaiting_confirmation
                self.state.current_phase = "refinement"
                return {
                    "status": "plan_selected",
                    "data": {"selected_plan": selected},
                    "message": f"已选择方案 {selected.get('plan_id', '')}，你可以继续优化或直接定型",
                    "next_actions": ["继续优化", "爆款化定型"]
                }

            # 用户提出定型/确认指令
            finalize_keywords = ["定型", "确认", "直接定型", "爆款化定型", "🎯", "ok", "OK", "进入生成", "保存方案"]
            if any(kw in user_input.strip() for kw in finalize_keywords):
                self.state.current_phase = "finalization"
                return self.execute_interactive_step(user_input)

            # 用户提出反馈，需要优化
            current_plan = self.state.selected_plan if self.state.selected_plan else self.state.plan_candidates[0]
            refined = self._run_refinement(current_plan, user_input)
            if not refined:
                return {"status": "error", "message": "方案优化失败"}

            self.state.selected_plan = refined
            self.state.refinement_history.append({
                "feedback": user_input,
                "result": refined,
            })
            self.state.current_phase = "refinement"

            return {
                "status": "awaiting_plan_selection",
                "data": {"refined_plan": refined},
                "message": "已根据你的意见优化，是否继续修改或进入爆款化定型？",
                "next_actions": ["继续优化", "爆款化定型"]
            }

        # ------------------------------------------------------------------
        # Phase: finalization
        # ------------------------------------------------------------------
        if phase == "finalization":
            plan_to_finalize = self.state.selected_plan
            if not plan_to_finalize:
                return {"status": "error", "message": "没有可定型的方案"}
            
            final_brief = self._run_explosive_finalization(plan_to_finalize)
            if not final_brief:
                return {"status": "error", "message": "爆款化定型失败"}
            
            self.state.final_plan_brief = final_brief
            return {
                "status": "completed",
                "data": {"final_plan_brief": final_brief},
                "message": "创意策划完成，方案已定型"
            }

        return {"status": "error", "message": f"未知阶段: {phase}"}

    def transition_to_finalization(self) -> Dict[str, Any]:
        """
        交互模式下，显式触发从 refinement 到 finalization 的过渡
        """
        self.state.current_phase = "finalization"
        return self.execute_interactive_step()

    # ==================================================================
    # 内部步骤实现
    # ==================================================================
    def _run_diagnosis(self) -> Optional[Dict[str, Any]]:
        """步骤1: 创意诊断"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        novel_seed = self.novel_data.get("creative_seed", "")
        if not novel_seed:
            # 尝试其他字段
            novel_seed = self.novel_data.get("novel_synopsis", "")
        
        prompt = prompts.format(
            "creative_planning_diagnosis",
            default="",
            novel_seed=novel_seed,
        )
        
        if not prompt:
            self.session_logger.error("未找到 creative_planning_diagnosis 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="creative_diagnosis")

    def _run_fanfiction_background_auto(self) -> Optional[Dict[str, Any]]:
        """自动模式：同人背景提取"""
        session = FanfictionBackgroundSession(
            api_client=self.api_client,
            work_name=self.state.fanfiction_work_name,
            mode=PlanningMode.AUTO,
            context_briefs=self.context_briefs,
            novel_data=self.novel_data,
            provider=self.provider,
            model_name=self.model_name,
            temperature=self.temperature,
        )
        success = session.execute_all_steps()
        if success:
            # 将 brief 注入 novel_data，供下游使用
            brief = session.background_brief
            self.novel_data["fanfiction_brief"] = brief
            return session.export_results()
        return None

    def _run_initial_plans(self) -> Optional[List[Dict[str, Any]]]:
        """步骤3: 生成初版方案"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        fanfiction_brief_text = ""
        if self.state.fanfiction_background_brief:
            fanfiction_brief_text = (
                "\n\n## 同人原作背景约束\n"
                + self.state.fanfiction_background_brief
            )
        
        prompt = prompts.format(
            "creative_planning_initial_plans",
            default="",
            diagnosis_json=json.dumps(self.state.diagnosis, ensure_ascii=False, indent=2),
            novel_title=self.novel_data.get("novel_title", "未命名"),
            category=self.novel_data.get("category", "未分类"),
            total_chapters=self.novel_data.get("current_progress", {}).get("total_chapters", 200),
            fanfiction_brief=fanfiction_brief_text,
        )
        
        if not prompt:
            self.session_logger.error("未找到 creative_planning_initial_plans 提示词模板")
            return None
            
        result = self.send_structured_message(prompt, purpose="initial_plans")
        if result and "plans" in result:
            return result["plans"]
        return None

    def _run_editor_review_loop(self) -> Optional[Dict[str, Any]]:
        """
        自动模式：AI 编辑审查 + 优化循环
        """
        current_plan = max(
            self.state.plan_candidates,
            key=lambda p: p.get("market_fit_score", 0)
        )
        
        for iteration in range(1, self.max_auto_iterations + 1):
            self.session_logger.info(
                f"[CreativePlanningSession] 自动优化第 {iteration}/{self.max_auto_iterations} 轮"
            )
            
            review = self._run_editor_review(current_plan)
            if not review:
                self.session_logger.warning("编辑审查失败，跳过本轮优化")
                continue
            
            score = review.get("overall_score", 0)
            verdict = review.get("verdict", "fail")
            
            self.session_logger.info(
                f"[CreativePlanningSession] 编辑评分: {score}/10,  verdict: {verdict}"
            )
            
            if verdict == "pass" and score >= 8.5:
                self.session_logger.info("方案已达到爆款标准，停止优化")
                return current_plan
            
            # 根据编辑反馈优化
            feedback = "\n".join(review.get("actionable_feedback", []))
            refined = self._run_refinement(current_plan, feedback)
            if refined:
                current_plan = refined
                self.state.refinement_history.append({
                    "iteration": iteration,
                    "review": review,
                    "result": refined,
                })
            else:
                self.session_logger.warning("自动优化失败，保留上一版方案")
        
        return current_plan

    def _run_editor_review(self, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """AI 编辑审查"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        prompt = prompts.format(
            "creative_planning_editor_review",
            default="",
            plan_json=json.dumps(plan, ensure_ascii=False, indent=2),
        )
        
        if not prompt:
            self.session_logger.error("未找到 creative_planning_editor_review 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="editor_review")

    def _run_refinement(self, plan: Dict[str, Any], feedback: str) -> Optional[Dict[str, Any]]:
        """根据反馈优化方案"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        fanfiction_brief_text = ""
        if self.state.fanfiction_background_brief:
            fanfiction_brief_text = self.state.fanfiction_background_brief
        
        prompt = prompts.format(
            "creative_planning_refine_by_feedback",
            default="",
            current_plan_json=json.dumps(plan, ensure_ascii=False, indent=2),
            feedback=feedback,
            fanfiction_brief=fanfiction_brief_text or "（无同人约束）",
        )
        
        if not prompt:
            self.session_logger.error("未找到 creative_planning_refine_by_feedback 提示词模板")
            return None
            
        result = self.send_structured_message(prompt, purpose="plan_refinement")
        if result and "refined_plan" in result:
            return result["refined_plan"]
        return None

    def _run_explosive_finalization(
        self, plan: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """步骤5: 爆款化定型"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        target_plan = plan or self.state.selected_plan
        if not target_plan:
            target_plan = max(
                self.state.plan_candidates,
                key=lambda p: p.get("market_fit_score", 0)
            )
        
        prompt = prompts.format(
            "creative_planning_explosive_finalization",
            default="",
            final_plan_json=json.dumps(target_plan, ensure_ascii=False, indent=2),
        )
        
        if not prompt:
            self.session_logger.error("未找到 creative_planning_explosive_finalization 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="explosive_finalization")

    # ==================================================================
    # 辅助方法
    # ==================================================================
    def _try_parse_plan_selection(self, user_input: str) -> Optional[Dict[str, Any]]:
        """尝试解析用户是否选择了一个方案"""
        text = user_input.strip()
        # 直接匹配 A/B/C
        if text in ("A", "B", "C"):
            for plan in self.state.plan_candidates:
                if plan.get("plan_id") == text:
                    return plan
        
        # 匹配 "方案A", "选A", "选方案A"
        import re
        match = re.search(r'[选要方案]*\s*([ABC])\b', text)
        if match:
            plan_id = match.group(1)
            for plan in self.state.plan_candidates:
                if plan.get("plan_id") == plan_id:
                    return plan
        
        # 按名称匹配
        for plan in self.state.plan_candidates:
            name = plan.get("plan_name", "")
            if name and name in text:
                return plan
        
        return None

    def export_results(self) -> Dict[str, Any]:
        """导出最终产物"""
        return {
            "creative_planning_brief": self.state.final_plan_brief,
            "final_plan_brief": self.state.final_plan_brief,
            "diagnosis": self.state.diagnosis,
            "plan_candidates": self.state.plan_candidates,
            "selected_plan": self.state.selected_plan,
            "fanfiction_brief": self.state.fanfiction_background_brief,
            "mode": self.mode.value,
            "refinement_history": self.state.refinement_history,
        }

    def generate_brief(self, session_results: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """生成 Context Brief，供下游 Foundation/Character/Structure 使用"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        final_plan = self.state.final_plan_brief
        if not final_plan:
            return None
        
        prompt = prompts.format(
            "creative_planning_brief_generation",
            default="",
            final_plan_json=json.dumps(final_plan, ensure_ascii=False, indent=2),
        )
        
        if not prompt:
            # 回退到基类实现
            return super().generate_brief(session_results)
        
        brief = self.send_message(
            user_prompt=prompt,
            temperature=0.5,
            purpose="generate_creative_planning_brief",
        )
        
        if brief:
            import re
            brief = re.sub(r'^```(?:markdown)?\s*|\s*```$', '', brief, flags=re.MULTILINE).strip()
        
        return brief
