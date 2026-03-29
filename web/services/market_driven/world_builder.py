# -*- coding: utf-8 -*-
"""
WorldBuilder 存根模块
为 HierarchicalPlanner 提供兼容性支持
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class WorldBuilder:
    """世界观构建器（存根实现）"""
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def build_world_setting(
        self,
        genre: str,
        novel_title: str,
        protagonist_name: str,
        total_chapters: int = 100,
        target_words: int = None
    ) -> Dict:
        """构建世界观设定（存根：返回最小可用结构）"""
        logger.warning("[WorldBuilder] 使用存根实现生成世界观")
        return {
            "world_setting": {
                "overview": f"{novel_title}的世界观",
                "power_system": "待完善",
                "social_structure": "待完善"
            },
            "characters": {
                "protagonist": {"name": protagonist_name},
                "supporting": []
            },
            "stage_goals": [],
            "total_chapters": total_chapters
        }
