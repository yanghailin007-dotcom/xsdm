# -*- coding: utf-8 -*-
"""
BatchSummarizer 存根模块
为 HierarchicalPlanner 提供兼容性支持
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class BatchSummarizer:
    """批次总结器（存根实现）"""
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def summarize_batch(
        self,
        chapters: List[Dict],
        stage_goal: Dict = None,
        previous_summary: Dict = None
    ) -> Dict:
        """总结批次内容（存根：返回最小可用结构）"""
        goal_id = stage_goal.get('goal_id', 'G1') if stage_goal else 'G1'
        return {
            "summarized_chapters": len(chapters),
            "goal_progress": {goal_id: "10%"},
            "key_events": [],
            "character_state": {},
            "notes": "使用存根总结器"
        }
    
    def merge_summaries(self, old_summary: Dict, new_summary: Dict) -> Dict:
        """合并两个总结（存根：简单合并）"""
        merged = old_summary.copy()
        merged["summarized_chapters"] = merged.get("summarized_chapters", 0) + new_summary.get("summarized_chapters", 0)
        
        # 合并进度（取最大值）
        old_progress = merged.get("goal_progress", {})
        new_progress = new_summary.get("goal_progress", {})
        for k, v in new_progress.items():
            try:
                old_val = int(str(old_progress.get(k, "0%")).replace("%", ""))
                new_val = int(str(v).replace("%", ""))
                merged["goal_progress"][k] = f"{max(old_val, new_val)}%"
            except:
                merged["goal_progress"][k] = v
        
        return merged
