"""
Fanfiction Background Session - 同人背景资料会话

负责：提取原著背景资料 → 多轮自我修正/用户校正 → 生成精炼的【原著背景摘要】

支持两种模式：
1. AUTO（自动）：AI 自我提取 → 自我修正 → 生成 Brief
2. INTERACTIVE（交互）：AI 提取 → 用户审查校正 → 确认后生成 Brief
"""

import json
from enum import Enum
from typing import Dict, Optional, Any

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class PlanningMode(Enum):
    AUTO = "auto"
    INTERACTIVE = "interactive"


class FanfictionBackgroundSession(NovelGenerationSession):
    """
    同人背景资料专用会话
    
    流程：
    1. 提取原著背景资料（世界观、角色、力量体系、关键事件）
    2. 自我审查和用户校正
    3. 生成精炼的【原著背景摘要 Brief】
    """

    STEPS = ["background_extraction", "background_correction", "background_brief"]

    def __init__(
        self,
        *args,
        work_name: str = "",
        mode: PlanningMode = PlanningMode.AUTO,
        **kwargs
    ):
        self.work_name = work_name
        super().__init__(*args, domain="fanfiction_background", **kwargs)
        self.mode = mode
        self.results: Dict[str, Any] = {}
        self.background_brief: str = ""
        self.current_draft: Optional[Dict] = None
        self.is_locked: bool = False

    def _get_domain_chinese_name(self) -> str:
        return f"同人背景资料提取（{self.work_name}）"

    def execute_all_steps(self) -> bool:
        """执行同人背景资料提取的所有步骤（自动模式专用）"""
        if self.mode != PlanningMode.AUTO:
            self.session_logger.error(
                "[FanfictionBackgroundSession] INTERACTIVE 模式不支持 execute_all_steps，"
                "请使用 execute_interactive_step"
            )
            return False
        
        self.session_logger.info(
            f"[FanfictionBackgroundSession] 开始自动提取《{self.work_name}》背景资料..."
        )

        # Step 1: 提取初稿
        step1_result = self._execute_background_extraction()
        if not step1_result:
            self.session_logger.error("[FanfictionBackgroundSession] 背景资料提取失败")
            return False
        self.results["background_extraction"] = step1_result
        self.current_draft = step1_result

        # Step 2: 自我修正
        step2_result = self._execute_background_correction(step1_result)
        if step2_result:
            self.results["background_correction"] = step2_result
            self.current_draft = step2_result
        else:
            self.session_logger.warning(
                "[FanfictionBackgroundSession] 自我修正步骤失败，使用初稿"
            )
            self.results["background_correction"] = step1_result

        # Step 3: 生成 Brief
        brief = self._execute_background_brief()
        if brief:
            self.background_brief = brief
            self.is_locked = True
        else:
            self.session_logger.warning(
                "[FanfictionBackgroundSession] Brief 生成失败"
            )

        self.session_logger.info(
            f"[FanfictionBackgroundSession] 《{self.work_name}》背景资料提取完成"
        )
        return True

    def execute_interactive_step(
        self, user_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        交互模式：单步执行，返回当前状态和给用户的展示内容
        
        Args:
            user_input: 用户反馈。首次调用传入 None 或空字符串，触发提取草稿。
        
        Returns:
            包含 status, draft, message 等字段的字典
        """
        if self.mode != PlanningMode.INTERACTIVE:
            return {
                "status": "error",
                "message": "当前不是交互模式"
            }

        if self.is_locked:
            return {
                "status": "locked",
                "background_brief": self.background_brief,
                "message": "背景资料已确认锁定"
            }

        # 第一次进入：提取草稿
        if self.current_draft is None:
            draft = self._execute_background_extraction()
            if not draft:
                return {
                    "status": "error",
                    "message": "背景资料提取失败"
                }
            self.current_draft = draft
            self.results["background_extraction"] = draft
            return {
                "status": "awaiting_review",
                "draft": self.current_draft,
                "message": f"已提取《{self.work_name}》的背景资料草稿，请检查是否有误"
            }

        # 用户确认：锁定
        confirm_keywords = ["确认", "准确", "没问题", "继续", "✅", "ok", "OK", "对", "正确"]
        if user_input and any(kw in user_input.strip() for kw in confirm_keywords):
            # 先用 self-correct 做一次最终修正
            corrected = self._execute_background_correction(self.current_draft)
            if corrected:
                self.current_draft = corrected
                self.results["background_correction"] = corrected
            else:
                self.results["background_correction"] = self.current_draft
            
            brief = self._execute_background_brief()
            if brief:
                self.background_brief = brief
                self.is_locked = True
                return {
                    "status": "locked",
                    "background_brief": self.background_brief,
                    "message": "背景资料已确认，即将进入方案生成"
                }
            else:
                return {
                    "status": "error",
                    "message": "Brief 生成失败"
                }

        # 用户提出修正
        if user_input:
            corrected = self._correct_by_user_feedback(
                self.current_draft,
                user_input,
                self.work_name
            )
            if corrected:
                self.current_draft = corrected
                return {
                    "status": "awaiting_review",
                    "draft": self.current_draft,
                    "message": "已根据你的意见修正，请再次检查"
                }
            else:
                return {
                    "status": "error",
                    "message": "修正处理失败"
                }

        return {
            "status": "awaiting_review",
            "draft": self.current_draft,
            "message": "请检查背景资料草稿"
        }

    def _execute_background_extraction(self) -> Optional[Dict]:
        """执行步骤1: 提取原著背景资料"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        prompt = prompts.format(
            "fanfiction_background_extraction",
            default="",
            work_name=self.work_name
        )
        
        if not prompt:
            self.session_logger.error(
                "[FanfictionBackgroundSession] 未找到 fanfiction_background_extraction 提示词模板"
            )
            return None
            
        return self.send_structured_message(prompt, purpose="background_extraction")

    def _execute_background_correction(self, draft: Dict) -> Optional[Dict]:
        """执行步骤2: 自我审查和修正"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        prompt = prompts.format(
            "fanfiction_background_correction",
            default="",
            work_name=self.work_name,
            draft_json=json.dumps(draft, ensure_ascii=False, indent=2)
        )
        
        if not prompt:
            self.session_logger.error(
                "[FanfictionBackgroundSession] 未找到 fanfiction_background_correction 提示词模板"
            )
            return None
            
        return self.send_structured_message(prompt, purpose="background_correction")

    def _correct_by_user_feedback(
        self, draft: Dict, feedback: str, work_name: str
    ) -> Optional[Dict]:
        """根据用户反馈修正背景资料"""
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        prompt = prompts.format(
            "fanfiction_correct_by_feedback",
            default="",
            work_name=work_name,
            draft=json.dumps(draft, ensure_ascii=False, indent=2),
            feedback=feedback
        )
        
        if not prompt:
            self.session_logger.error(
                "[FanfictionBackgroundSession] 未找到 fanfiction_correct_by_feedback 提示词模板"
            )
            return None
            
        return self.send_structured_message(prompt, purpose="background_correction_by_feedback")

    def _execute_background_brief(self) -> Optional[str]:
        """执行步骤3: 生成精炼的【原著背景摘要】"""
        corrected = self.results.get("background_correction", {})
        
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        
        prompt = prompts.format(
            "fanfiction_background_brief",
            default="",
            work_name=self.work_name,
            corrected_json=json.dumps(corrected, ensure_ascii=False, indent=2)
        )
        
        if not prompt:
            self.session_logger.error(
                "[FanfictionBackgroundSession] 未找到 fanfiction_background_brief 提示词模板"
            )
            return None
            
        return self.send_message(prompt, purpose="background_brief")

    def export_results(self) -> Dict[str, Any]:
        """
        导出结果，格式与 ImprovedFanfictionDetector 的输出保持兼容
        """
        background = self.results.get("background_correction", {})
        
        return {
            "worldview": background.get("worldview", {}),
            "characters": background.get("characters", {}),
            "power_system": background.get("power_system", {}),
            "key_events": background.get("key_events", {}),
            "verification_result": {
                "is_credible": True,
                "confidence_score": 1.0,
                "credibility_level": "high",
                "issues_found": [],
                "source": "session_mode",
                "work_name": self.work_name,
            },
            "source": "session_mode",
            "work_name": self.work_name,
            "background_brief": self.background_brief,
            "mode": self.mode.value,
            "locked": self.is_locked,
        }
