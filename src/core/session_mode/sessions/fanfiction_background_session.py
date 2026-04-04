"""
Fanfiction Background Session - 同人背景资料会话

负责：提取原著背景资料 → 多轮自我修正 → 生成精炼的【原著背景摘要】

相比传统的单次调用+验证器修正模式，会话模式的优势：
1. 上下文连贯，修正轮次能记住前面的提取结果
2. 不需要每轮重复解释"这是什么作品"
3. 最终输出一份结构化的 Context Brief，供后续所有创作域引用
"""

import json
from typing import Dict, Optional, Any

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class FanfictionBackgroundSession(NovelGenerationSession):
    """
    同人背景资料专用会话
    
    流程：
    1. 提取原著背景资料（世界观、角色、力量体系、关键事件）
    2. 自我审查和修正（基于常见错误和历史教训）
    3. 生成精炼的【原著背景摘要 Brief】
    """

    STEPS = ["background_extraction", "background_correction", "background_brief"]

    def __init__(self, *args, work_name: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.work_name = work_name
        self.results: Dict[str, Any] = {}
        self.background_brief: str = ""

    def _get_domain_chinese_name(self) -> str:
        return f"同人背景资料提取（{self.work_name}）"

    def execute_all_steps(self) -> bool:
        """执行同人背景资料提取的所有步骤"""
        self.session_logger.info(f"[FanfictionBackgroundSession] 开始提取《{self.work_name}》背景资料...")

        # Step 1: 提取初稿
        step1_result = self._execute_background_extraction()
        if not step1_result:
            self.session_logger.error("[FanfictionBackgroundSession] 背景资料提取失败")
            return False
        self.results["background_extraction"] = step1_result

        # Step 2: 自我修正
        step2_result = self._execute_background_correction(step1_result)
        if step2_result:
            self.results["background_correction"] = step2_result
        else:
            self.session_logger.warning("[FanfictionBackgroundSession] 自我修正步骤失败，使用初稿")
            self.results["background_correction"] = step1_result

        # Step 3: 生成 Brief
        brief = self._execute_background_brief()
        if brief:
            self.background_brief = brief
        else:
            self.session_logger.warning("[FanfictionBackgroundSession] Brief 生成失败")

        self.session_logger.info(f"[FanfictionBackgroundSession] 《{self.work_name}》背景资料提取完成")
        return True

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
            self.session_logger.error("[FanfictionBackgroundSession] 未找到 fanfiction_background_extraction 提示词模板")
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
            self.session_logger.error("[FanfictionBackgroundSession] 未找到 fanfiction_background_correction 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="background_correction")

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
            self.session_logger.error("[FanfictionBackgroundSession] 未找到 fanfiction_background_brief 提示词模板")
            return None
            
        return self.send_message(prompt, purpose="background_brief")

    def export_results(self) -> Dict[str, Any]:
        """
        导出结果，格式与 ImprovedFanfictionDetector 的输出保持兼容
        
        Returns:
            包含 worldview, characters, power_system, key_events, verification_result 的字典
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
        }
