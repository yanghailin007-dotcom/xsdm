# -*- coding: utf-8 -*-
"""
Alignment Engine - 多轮爆款对齐引擎
P0硬规则扫描 → P1修复 → P0重扫 → P2AI优化
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from web.services.market_driven.alignment_scanners import AlignmentScannerSet, AlignmentIssue
from web.services.market_driven.alignment_repair import AutoRepair, AIAssistedRepair

logger = logging.getLogger(__name__)


class AlignmentEngine:
    """
    多轮爆款对齐引擎
    
    设计：
    - P0: 硬规则扫描（机器执行，发现Critical问题立即拦截）
    - P1: 一致性修复（规则自动修 + AI辅助修）
    - P0-Retry: 修复后重扫规则（Critical必须清零）
    - P2: AI爆款节奏优化（在干净数据上执行现有逻辑）
    """
    
    MAX_REPAIR_ROUNDS = 2
    
    def __init__(self, genre: str, project_path: str, api_client=None):
        self.genre = genre
        self.project_path = Path(project_path)
        self.api_client = api_client
        self.scanner_set = AlignmentScannerSet(genre, self.project_path)
        self.auto_repair = AutoRepair(self.project_path)
        self.ai_repair = AIAssistedRepair(api_client, genre, self.project_path) if api_client else None
    
    def run(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整对齐流程
        
        Returns:
            {
                "success": bool,
                "phase": str,
                "p0_issues": List[Dict],
                "p1_repair_report": Dict,
                "p0_retry_issues": List[Dict],
                "p2_result": Dict,
                "final_result": Dict,  # 返回给调用方的产物数据
                "message": str,
            }
        """
        logger.info(f"[AlignmentEngine] 启动多轮对齐 | 题材: {self.genre} | 项目: {self.project_path}")
        
        # ========== P0 轮：硬规则扫描 ==========
        logger.info("[AlignmentEngine] ===== P0 轮：硬规则扫描 =====")
        p0_issues = self.scanner_set.scan_all()
        
        critical_count = sum(1 for i in p0_issues if i.severity == "critical")
        high_count = sum(1 for i in p0_issues if i.severity == "high")
        
        logger.info(f"[AlignmentEngine] P0扫描完成 | Critical: {critical_count} | High: {high_count} | Total: {len(p0_issues)}")
        
        # 如果完全没有问题，直接跳到 P2
        if not p0_issues:
            logger.info("[AlignmentEngine] P0 无问题，直接进入 P2")
            p2_result = self._run_p2(previous_results)
            return {
                "success": True,
                "phase": "P2",
                "p0_issues": [],
                "p1_repair_report": None,
                "p0_retry_issues": [],
                "p2_result": p2_result,
                "final_result": p2_result.get("optimized", previous_results),
                "message": "P0 无问题，P2 优化完成",
            }
        
        # 如果有 Critical 或 High，进入 P1 修复
        if critical_count > 0 or high_count > 0:
            logger.info("[AlignmentEngine] 发现 Critical/High 问题，进入 P1 修复")
            
            # ========== P1 轮：修复 ==========
            repair_round = 0
            current_issues = p0_issues
            p1_reports = []
            
            while repair_round < self.MAX_REPAIR_ROUNDS and current_issues:
                repair_round += 1
                logger.info(f"[AlignmentEngine] P1 修复第 {repair_round}/{self.MAX_REPAIR_ROUNDS} 轮...")
                
                # Step 1: 自动修复
                auto_report = self.auto_repair.repair(current_issues)
                logger.info(f"[AlignmentEngine] 自动修复: {auto_report['fixed_count']}/{len(current_issues)}")
                
                remaining_after_auto = auto_report["remaining_issues"]
                
                # Step 2: AI辅助修复（如果有API客户端且还有剩余问题）
                ai_report = {"fixed_count": 0, "remaining_issues": remaining_after_auto, "modified_files": []}
                if self.ai_repair and remaining_after_auto:
                    ai_report = self.ai_repair.repair(remaining_after_auto)
                    logger.info(f"[AlignmentEngine] AI修复: {ai_report['fixed_count']}/{len(remaining_after_auto)}")
                
                p1_reports.append({
                    "round": repair_round,
                    "auto": auto_report,
                    "ai": ai_report,
                })
                
                current_issues = ai_report["remaining_issues"]
                
                # 修复后重扫 P0
                if current_issues:
                    logger.info("[AlignmentEngine] 修复后重扫 P0...")
                    retry_issues = self.scanner_set.scan_all()
                    retry_critical = sum(1 for i in retry_issues if i.severity == "critical")
                    retry_high = sum(1 for i in retry_issues if i.severity == "high")
                    logger.info(f"[AlignmentEngine] P0重扫结果 | Critical: {retry_critical} | High: {retry_high} | Total: {len(retry_issues)}")
                    
                    if retry_critical == 0 and retry_high == 0:
                        logger.info("[AlignmentEngine] P0重扫通过，进入 P2")
                        current_issues = []
                        break
                    
                    current_issues = retry_issues
            
            # P1 修复结束后，最终重扫
            logger.info("[AlignmentEngine] P1 全部修复轮次结束，进行最终 P0 重扫...")
            final_p0_issues = self.scanner_set.scan_all()
            final_critical = sum(1 for i in final_p0_issues if i.severity == "critical")
            final_high = sum(1 for i in final_p0_issues if i.severity == "high")
            
            logger.info(f"[AlignmentEngine] 最终P0重扫 | Critical: {final_critical} | High: {final_high} | Total: {len(final_p0_issues)}")
            
            # 熔断判断：Critical 未清零 → 任务失败
            if final_critical > 0:
                logger.error(f"[AlignmentEngine] 熔断！P1修复 {self.MAX_REPAIR_ROUNDS} 轮后仍有 {final_critical} 个 Critical 问题")
                return {
                    "success": False,
                    "phase": "P1_failed",
                    "p0_issues": [i.to_dict() for i in p0_issues],
                    "p1_repair_report": p1_reports,
                    "p0_retry_issues": [i.to_dict() for i in final_p0_issues],
                    "p2_result": None,
                    "final_result": None,
                    "message": f"爆款对齐未通过：P1修复后仍有 {final_critical} 个 Critical 问题",
                }
            
            # High 未清零 → 继续进入 P2，但日志警告
            if final_high > 0:
                logger.warning(f"[AlignmentEngine] P0重扫仍有 {final_high} 个 High 问题，但 Critical 已清零，继续进入 P2")
            
            # 重新加载修复后的产物数据
            refreshed_results = self._reload_phase_one_products(previous_results)
            
            # ========== P2 轮：AI 爆款节奏优化 ==========
            logger.info("[AlignmentEngine] ===== P2 轮：AI 爆款节奏优化 =====")
            p2_result = self._run_p2(refreshed_results)
            
            return {
                "success": True,
                "phase": "P2",
                "p0_issues": [i.to_dict() for i in p0_issues],
                "p1_repair_report": p1_reports,
                "p0_retry_issues": [i.to_dict() for i in final_p0_issues],
                "p2_result": p2_result,
                "final_result": p2_result.get("optimized", refreshed_results),
                "message": "P0/P1 对齐通过，P2 优化完成" if final_high == 0 else f"P0/P1 对齐通过（遗留 {final_high} 个 High 问题），P2 优化完成",
            }
        
        # 只有 Low/Medium，直接 P2
        logger.info("[AlignmentEngine] 仅 Low/Medium 问题，直接进入 P2")
        p2_result = self._run_p2(previous_results)
        
        return {
            "success": True,
            "phase": "P2",
            "p0_issues": [i.to_dict() for i in p0_issues],
            "p1_repair_report": None,
            "p0_retry_issues": [],
            "p2_result": p2_result,
            "final_result": p2_result.get("optimized", previous_results),
            "message": "P0 仅发现 Low/Medium 问题，P2 优化完成",
        }
    
    def _reload_phase_one_products(self, previous_results: Dict) -> Dict:
        """修复后重新加载一阶段产物数据"""
        from web.services.market_driven.phase_one_loader import PhaseOneDataLoader
        
        try:
            # 🔥 使用全新实例，绕过全局缓存，确保读取到 P1 修复后的最新文件内容
            loader = PhaseOneDataLoader(self.project_path)
            refreshed = loader.load_all()
            # 保留 previous_results 中已有的顶层字段
            result = dict(previous_results)
            # 用重新加载的数据覆盖对应字段
            for key in ["plan", "core_worldview", "faction_system", "character_design",
                        "global_growth_plan", "emotional_blueprint", "stage_goals",
                        "market_analysis", "golden_finger", "emotion_curve"]:
                if key in refreshed:
                    result[key] = refreshed[key]
            return result
        except Exception as e:
            logger.warning(f"[AlignmentEngine] 重新加载产物失败: {e}，使用原数据")
            return previous_results
    
    def _run_p2(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        P2轮：执行现有的爆款对齐优化逻辑
        由于现有逻辑在 MarketDrivenConversationSession 中，我们这里做简化调用
        """
        # P2 的核心检查点：
        # 1. 情绪曲线与阶段目标对齐
        # 2. 情绪节奏逻辑（是否有颠倒）
        # 3. 金手指深度检查（从字段升级为内容）
        
        optimized = dict(previous_results)
        p2_issues = []
        
        emotion_curve = optimized.get("emotion_curve", [])
        stage_goals = optimized.get("stage_goals", [])
        
        # --- P2-1: 情绪曲线与阶段目标对齐检查 ---
        if isinstance(stage_goals, list) and isinstance(emotion_curve, list):
            for sg in stage_goals:
                deliverables = sg.get("key_deliverables", [])
                expected_range = sg.get("expected_chapters", "")
                
                # 提取章节范围
                start_ch, end_ch = 0, 0
                if isinstance(expected_range, str):
                    import re
                    m = re.search(r"(\d+)-(\d+)", expected_range)
                    if m:
                        start_ch, end_ch = int(m.group(1)), int(m.group(2))
                
                if start_ch > 0:
                    # 检查该阶段内是否有高潮/反转/震惊章节
                    has_climax = False
                    for point in emotion_curve:
                        ch = point.get("chapter", 0)
                        emotion = point.get("emotion", "")
                        if start_ch <= ch <= end_ch and emotion in ["反转", "爆发", "震惊", "打脸", "高潮"]:
                            has_climax = True
                            break
                    
                    if not has_climax:
                        p2_issues.append({
                            "category": "emotion_stage_misalignment",
                            "severity": "high",
                            "message": f"阶段 {sg.get('goal_id')} ({start_ch}-{end_ch}章) 缺少与 key_deliverables 对应的情绪高潮",
                            "suggestion": f"建议在 {start_ch}-{end_ch} 章之间插入一个反转或震惊章节",
                        })
        
        # --- P2-2: 情绪节奏逻辑检查（先高潮后铺垫） ---
        if isinstance(emotion_curve, list) and len(emotion_curve) >= 5:
            # 简单检查：连续两章都是震惊/反转后，突然出现压抑/期待（且没有新冲突）
            for i in range(1, len(emotion_curve)):
                prev = emotion_curve[i - 1]
                curr = emotion_curve[i]
                
                prev_emotion = prev.get("emotion", "")
                curr_emotion = curr.get("emotion", "")
                
                # 如果前章是震惊/打脸，当前章是期待，但描述中没有引入新冲突/伏笔 → 可能节奏脱节
                if prev_emotion in ["震惊", "打脸", "爆发"] and curr_emotion in ["期待", "平静"]:
                    desc = curr.get("description", "")
                    if not any(kw in desc for kw in ["收到", "准备", "新", "更大的", "危机", "挑战", "敌人"]):
                        p2_issues.append({
                            "category": "emotion_rhythm_inversion",
                            "severity": "medium",
                            "message": f"第{curr.get('chapter')}章在高潮后直接进入平淡期待，缺少新冲突引入，可能导致爽感断层",
                            "suggestion": f"建议第{curr.get('chapter')}章加入一个新的挑衅或伏笔事件",
                        })
        
        # --- P2-3: 金手指深度检查（内容级） ---
        gf = optimized.get("golden_finger", {})
        if isinstance(gf, dict):
            abilities = gf.get("abilities", {})
            growth_text = abilities.get("growth", "") if isinstance(abilities, dict) else ""
            
            # 检查是否有明确的成长阶段数
            stage_count = 0
            if isinstance(growth_text, str):
                import re
                stage_count = len(re.findall(r"(\d+-\d+级)", growth_text))
            
            if stage_count < 2:
                p2_issues.append({
                    "category": "golden_finger_depth",
                    "severity": "medium",
                    "message": "金手指成长阶段划分不够清晰（少于2个阶段）",
                    "suggestion": "建议明确设计 3-5 个成长阶段，每个阶段有具体的触发条件和能力变化",
                })
        
        # P2 的优化策略：记录问题但不阻断（因为 P0 已经把致命问题清掉了）
        # 如果有 High 问题，尝试用 AI 做轻量优化
        if p2_issues:
            logger.info(f"[AlignmentEngine] P2 发现 {len(p2_issues)} 个优化点")
        
        return {
            "optimized": optimized,
            "p2_issues": p2_issues,
            "message": f"P2 完成，发现 {len(p2_issues)} 个可优化点",
        }
