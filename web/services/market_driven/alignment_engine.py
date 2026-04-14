# -*- coding: utf-8 -*-
"""
Alignment Engine - 生成前数据校验引擎（瘦身版）

职责大幅收缩：仅保留 P0 硬规则扫描，检查产物文件是否存在、
格式合法、关键字段非空、题材防火墙、跨产物数值一致性。

不再执行 P1 自动修复和 P2 AI 优化（这些职责已上移至
核心设定圣经 + AI 编辑审稿流程）。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from web.services.market_driven.alignment_scanners import AlignmentScannerSet, AlignmentIssue

logger = logging.getLogger(__name__)


class AlignmentEngine:
    """
    生成前数据校验引擎（Data Validation Engine）

    设计：
    - P0: 硬规则扫描（机器执行，发现 Critical 问题即拦截）
    - 无 P1/P2：修复与优化已上移至 Bible Review 流程
    """

    def __init__(self, genre: str, project_path: str, api_client=None):
        self.genre = genre
        self.project_path = Path(project_path)
        self.scanner_set = AlignmentScannerSet(genre, self.project_path)
        # api_client 参数保留以兼容旧调用，但本引擎不再使用
        self.api_client = api_client

    def run(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据校验流程

        Returns:
            {
                "success": bool,
                "phase": str,
                "p0_issues": List[Dict],
                "message": str,
            }
        """
        logger.info(
            f"[AlignmentEngine] 启动数据校验 | 题材: {self.genre} | 项目: {self.project_path}"
        )

        # ========== P0 轮：硬规则扫描 ==========
        logger.info("[AlignmentEngine] ===== P0 轮：硬规则扫描 =====")
        p0_issues = self.scanner_set.scan_all()

        critical_count = sum(1 for i in p0_issues if i.severity == "critical")
        high_count = sum(1 for i in p0_issues if i.severity == "high")

        logger.info(
            f"[AlignmentEngine] P0扫描完成 | Critical: {critical_count} | High: {high_count} | Total: {len(p0_issues)}"
        )

        # Critical 未清零 → 任务失败
        if critical_count > 0:
            logger.error(
                f"[AlignmentEngine] 熔断！发现 {critical_count} 个 Critical 问题，禁止进入生成阶段"
            )
            return {
                "success": False,
                "phase": "P0_failed",
                "p0_issues": [i.to_dict() for i in p0_issues],
                "message": f"数据校验未通过：发现 {critical_count} 个 Critical 问题",
            }

        # High 未清零 → 警告但通过
        if high_count > 0:
            logger.warning(
                f"[AlignmentEngine] 发现 {high_count} 个 High 问题，但 Critical 已清零，允许继续"
            )

        return {
            "success": True,
            "phase": "P0",
            "p0_issues": [i.to_dict() for i in p0_issues],
            "message": "P0 数据校验通过"
            if high_count == 0
            else f"P0 数据校验通过（遗留 {high_count} 个 High 问题）",
        }
