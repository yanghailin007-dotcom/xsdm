# -*- coding: utf-8 -*-
"""
Bible Reviewer - 核心设定圣经 AI 编辑审稿器

使用提示词工程驱动 AI 以"番茄编辑"人格审查设定圣经，
输出结构化报告，发现并拦截数值崩坏、题材漂移、预期欺诈等问题。
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BibleReviewBlockedError(Exception):
    """圣经审稿被 BLOCK 时抛出的异常，携带完整审稿报告"""

    def __init__(self, message: str, report: Dict[str, Any], report_path: Path):
        super().__init__(message)
        self.report = report
        self.report_path = report_path


class BibleReviewer:
    """核心设定圣经审稿器"""

    def __init__(self, api_client, project_path: str, genre: Optional[str] = None):
        self.api_client = api_client
        self.project_path = Path(project_path)
        self.genre = genre or "unknown"
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> Dict:
        prompt_path = (
            Path(__file__).parent.parent.parent.parent
            / "prompt_packages"
            / "default"
            / "market_driven"
            / "components"
            / "bible_review_prompts.json"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[BibleReviewer] 加载提示词配置失败: {e}，使用内联默认配置")
            return {}

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从 AI 返回文本中提取 JSON"""
        if not text:
            return None
        # 优先提取 markdown 代码块中的 json
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            candidate = m.group(1).strip()
        else:
            candidate = text.strip()
        # 寻找最外层的大括号
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception as e:
            logger.warning(f"[BibleReviewer] JSON 解析失败: {e} | 原始文本前500字: {text[:500]}")
            return None

    def review(self, bible_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        执行审稿，返回结构化报告字典。
        如果任意维度为 BLOCK，会抛出 BibleReviewBlockedError。
        """
        if bible_path is None:
            bible_path = self.project_path / "layer_1_4_core_settings.md"
        if not bible_path.exists():
            raise FileNotFoundError(f"核心设定圣经不存在: {bible_path}")

        with open(bible_path, "r", encoding="utf-8") as f:
            bible_content = f.read()

        # 组装 prompt
        templates = self._prompts.get("templates", {})
        sys_tpl = templates.get("editor_system_prompt", {}).get("template", "")
        user_tpl = templates.get("user_prompt", {}).get("template", "")

        system_prompt = sys_tpl
        user_prompt = user_tpl.replace("{bible_content}", bible_content)

        if not self.api_client:
            logger.warning("[BibleReviewer] 未提供 api_client，跳过 AI 审稿")
            return {
                "overall_pass": True,
                "skipped": True,
                "reason": "api_client 不可用",
            }

        logger.info(f"[BibleReviewer] 开始审稿 | 项目: {self.project_path}")
        raw_response = self.api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            purpose="bible_review",
        )

        parsed = self._extract_json(raw_response or "")
        if parsed is None:
            logger.error("[BibleReviewer] AI 返回内容无法解析为 JSON，视为审稿失败")
            # 返回一个安全回退：不阻断，但标记解析失败
            return {
                "overall_pass": True,
                "skipped": True,
                "reason": "AI 返回解析失败",
                "raw_response": raw_response,
            }

        # 标准化报告
        report = self._normalize_report(parsed)

        # 保存报告
        report_path = self.project_path / "bible_review_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"[BibleReviewer] 审稿报告已保存: {report_path}")

        # BLOCK 判定
        has_block = any(
            d.get("verdict") == "BLOCK" for d in report.get("dimensions", [])
        )
        if has_block:
            block_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "BLOCK"]
            bible_path_abs = str(bible_path.resolve())
            msg = f"核心设定圣经审稿未通过，BLOCK 维度: {', '.join(block_dims)}。请人工修改 {bible_path_abs} 后重试。"
            logger.error(f"[BibleReviewer] {msg}")
            raise BibleReviewBlockedError(msg, report, report_path)

        warn_dims = [d["name"] for d in report.get("dimensions", []) if d.get("verdict") == "WARN"]
        if warn_dims:
            logger.warning(f"[BibleReviewer] 审稿通过，但存在 WARN 维度: {', '.join(warn_dims)}")
        else:
            logger.info("[BibleReviewer] 审稿通过，无 BLOCK/WARN")

        return report

    def _normalize_report(self, parsed: Dict) -> Dict:
        """将 AI 返回的 JSON 标准化为内部格式"""
        dims = []
        expected_names = [
            "平台适配性",
            "数值可持续性",
            "题材一致性",
            "预期管理",
            "爽感折旧率",
        ]
        raw_dims = parsed.get("dimensions", [])
        name_to_raw = {d.get("name"): d for d in raw_dims if d.get("name")}

        for name in expected_names:
            d = name_to_raw.get(name, {})
            dims.append(
                {
                    "name": name,
                    "verdict": d.get("verdict", "PASS"),
                    "problem": d.get("problem", d.get("问题描述", "无")),
                    "fix_suggestion": d.get("fix_suggestion", d.get("修改建议", "无")),
                }
            )

        overall = parsed.get("overall_pass", True)
        # 如果有 BLOCK 但 overall_pass 为 true，强制修正
        has_block = any(dd.get("verdict") == "BLOCK" for dd in dims)
        if has_block:
            overall = False

        return {
            "overall_pass": overall,
            "dimensions": dims,
            "estimated_read_rate": parsed.get("estimated_read_rate", ""),
            "biggest_risk": parsed.get("biggest_risk", ""),
        }
