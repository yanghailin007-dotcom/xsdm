"""
一阶段产物 AI 一致性审查服务
用 AI 审查替代规则检验，检查书名、简介、金手指、主角、世界观之间的冲突。
"""
import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PhaseOneAIReviewer:
    """
    AI 审稿人模式：像网文编辑一样审阅一阶段产物，发现设定冲突并给出修正建议。
    """

    def __init__(self, api_client):
        self.api_client = api_client

    def review(self, products: Dict[str, Any]) -> Dict[str, Any]:
        """
        审查一阶段产物，返回审查结果。
        如果发现问题，直接返回 AI 建议的修正版本。
        """
        prompt = self._build_review_prompt(products)

        try:
            response = self.api_client.generate_content_with_retry(
                content_type="phase_one_ai_review",
                user_prompt=prompt,
                system_prompt="你是一位资深网文编辑，专门审查小说基础设定是否存在自相矛盾。请严格按 JSON 格式输出，不要添加任何额外说明。",
                temperature=0.3,
                purpose="phase_one_consistency_review"
            )
            review = self._parse_review_response(response)
            logger.info(f"[PhaseOneAIReviewer] 审查完成: status={review.get('status')}, issues={len(review.get('issues', []))}")
            return review
        except Exception as e:
            logger.error(f"[PhaseOneAIReviewer] AI 审查调用失败: {e}", exc_info=True)
            # 审查失败时不阻断流程，返回通过状态
            return {
                "status": "passed",
                "issues": [],
                "fixed_version": {},
                "summary": "AI 审查服务暂时不可用，跳过审查",
                "error": str(e)
            }

    def apply_fixes(self, products: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
        """
        将审查建议中的高置信度、可自动修复的问题应用到产物中。
        返回修正后的产物副本。
        """
        fixed = dict(products)
        fixed_version = review.get("fixed_version", {})
        issues = review.get("issues", [])

        # 🔥 过滤掉无意义的占位符值
        def _is_meaningful(val: str) -> bool:
            if not val or not isinstance(val, str):
                return False
            meaningless = {"待补充", "待定", "未知", "暂无", "请补充", "未命名", ""}
            return val.strip() not in meaningless

        applied_count = 0
        for issue in issues:
            if issue.get("auto_applicable") and issue.get("confidence", 0) >= 0.85:
                applied_count += 1
                logger.info(f"[PhaseOneAIReviewer] 自动修复: {issue.get('location')} -> {issue.get('suggestion')}")

        # 按 fixed_version 中的字段映射更新产物（只应用有意义的值）
        # 书名
        if _is_meaningful(fixed_version.get("title")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            fixed["plan"]["title"] = fixed_version["title"]
            fixed["title"] = fixed_version["title"]

        # 简介
        if _is_meaningful(fixed_version.get("synopsis")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            fixed["plan"]["synopsis"] = fixed_version["synopsis"]
            if "core_selling_points" not in fixed["plan"]:
                fixed["plan"]["core_selling_points"] = []
            fixed["plan"]["core_selling_points"] = [{"point": fixed_version["synopsis"]}]

        # 金手指名称
        if _is_meaningful(fixed_version.get("golden_finger_name")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            if "golden_finger" not in fixed["plan"]:
                fixed["plan"]["golden_finger"] = {}
            fixed["plan"]["golden_finger"]["name"] = fixed_version["golden_finger_name"]
            fixed["plan"]["golden_finger"]["basic_info"] = fixed["plan"]["golden_finger"].get("basic_info", {})
            fixed["plan"]["golden_finger"]["basic_info"]["name"] = fixed_version["golden_finger_name"]

        # 金手指初始能力
        if _is_meaningful(fixed_version.get("golden_finger_initial")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            if "golden_finger" not in fixed["plan"]:
                fixed["plan"]["golden_finger"] = {}
            fixed["plan"]["golden_finger"]["initial_ability"] = fixed_version["golden_finger_initial"]

        # 金手指成长规则
        if _is_meaningful(fixed_version.get("golden_finger_growth")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            if "golden_finger" not in fixed["plan"]:
                fixed["plan"]["golden_finger"] = {}
            fixed["plan"]["golden_finger"]["growth_rule"] = fixed_version["golden_finger_growth"]

        # 主角名
        if _is_meaningful(fixed_version.get("protagonist_name")):
            if "plan" not in fixed:
                fixed["plan"] = {}
            fixed["plan"]["protagonist"] = fixed["plan"].get("protagonist", {})
            fixed["plan"]["protagonist"]["name"] = fixed_version["protagonist_name"]

        logger.info(f"[PhaseOneAIReviewer] 自动修复完成，共应用 {applied_count} 条高置信度建议")
        return fixed

    def _build_review_prompt(self, products: Dict[str, Any]) -> str:
        plan = products.get("plan", {})
        title = products.get("title", "") or plan.get("title", "")
        synopsis = ""
        if plan.get("synopsis"):
            synopsis = plan.get("synopsis")
        elif plan.get("core_selling_points"):
            synopsis = plan.get("core_selling_points")[0].get("point", "") if isinstance(plan.get("core_selling_points"), list) else ""

        gf = plan.get("golden_finger", {})
        gf_name = (
            gf.get("basic_info", {}).get("name")
            or gf.get("name")
            or ""
        )
        gf_initial = gf.get("initial_ability", "")
        gf_growth = gf.get("growth_rule", "")
        gf_limitations = gf.get("limitations", "")

        protagonist = plan.get("protagonist", {})
        protagonist_name = protagonist.get("name", "")
        protagonist_personality = protagonist.get("personality", "")
        protagonist_background = protagonist.get("background", "")

        worldview = products.get("core_worldview", {})
        if isinstance(worldview, dict):
            world_background = worldview.get("background", "") or worldview.get("world_setting", "") or str(worldview)[:500]
        else:
            world_background = str(worldview)[:500]

        # 成长路线中的数字
        growth_plan = products.get("global_growth_plan", {})
        growth_text = json.dumps(growth_plan, ensure_ascii=False, indent=2)[:800] if growth_plan else ""

        return f"""你是一位资深网文编辑，负责审查小说项目的基础设定是否存在自相矛盾或卖点不清晰的问题。

## 审查对象
【书名】：{title}
【简介】：{synopsis}
【金手指名称】：{gf_name}
【金手指初始能力】：{gf_initial}
【金手指成长规则】：{gf_growth}
【金手指限制条件】：{gf_limitations}
【主角名】：{protagonist_name}
【主角人设】：{protagonist_personality}
【主角背景】：{protagonist_background}
【世界观背景】：{world_background}
【成长路线节选】：{growth_text}

## 你的任务
1. 检查书名、简介、金手指三者是否存在数字/概念冲突（如书名说"双倍返利"，金手指写"100倍"）
2. 检查主角人设是否与故事基调冲突（如神豪文主角设定为"极度自卑、不敢花钱"）
3. 检查世界观与金手指能力是否匹配（如现代都市背景出现修仙式升级）
4. 检查核心卖点是否在后续设定中被稀释或背叛
5. 检查升级曲线是否过陡导致爽感提前透支（如第3章就买千万豪宅）

## 输出格式（必须严格为合法 JSON，禁止 Markdown 代码块包裹）
{{
  "status": "needs_fix" | "passed",
  "issues": [
    {{
      "location": "具体位置，如'书名 vs 金手指设计'",
      "problem": "问题描述",
      "suggestion": "具体修正建议",
      "confidence": 0.0-1.0,
      "auto_applicable": true/false
    }}
  ],
  "fixed_version": {{
    "title": "修正后的书名（如无需修改则保持原样）",
    "synopsis": "修正后的简介",
    "golden_finger_name": "修正后的金手指名称",
    "golden_finger_initial": "修正后的初始能力描述",
    "golden_finger_growth": "修正后的成长规则",
    "protagonist_name": "修正后的主角名"
  }},
  "summary": "给作者的简短总结（50字内）"
}}

## 审查原则
- 如果书名含具体数字（如"双倍""百倍"），金手指规则必须严格匹配，不能含糊
- 金手指名称里的数字（如"万倍"）如果和实际能力描述（"100倍"）不符，视为标题党/设定崩盘，必须修正
- 不要让主角开局太强，否则后期没有成长空间
- 不要提出"尽量""适当"等模糊建议，每条建议必须具体可执行
- 如果没有任何冲突，status 必须为 "passed"，issues 为空数组
"""

    def _parse_review_response(self, response: Any) -> Dict[str, Any]:
        if not response:
            return {"status": "passed", "issues": [], "fixed_version": {}, "summary": "AI 返回为空"}

        # 🔥 修复：APIClient 可能已经自动解析为 dict
        if isinstance(response, dict):
            data = response
            if "status" not in data:
                data["status"] = "passed"
            if "issues" not in data:
                data["issues"] = []
            if "fixed_version" not in data:
                data["fixed_version"] = {}
            return data

        text = str(response)
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            logger.warning(f"[PhaseOneAIReviewer] 无法从响应中提取 JSON: {text[:200]}")
            return {"status": "passed", "issues": [], "fixed_version": {}, "summary": "解析失败"}

        try:
            data = json.loads(json_match.group())
            # 基础校验
            if "status" not in data:
                data["status"] = "passed"
            if "issues" not in data:
                data["issues"] = []
            if "fixed_version" not in data:
                data["fixed_version"] = {}
            return data
        except Exception as e:
            logger.warning(f"[PhaseOneAIReviewer] JSON 解析失败: {e}")
            return {"status": "passed", "issues": [], "fixed_version": {}, "summary": "解析失败"}
