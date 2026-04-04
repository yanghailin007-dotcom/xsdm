"""
番茄短篇小说创作核心包
提供短篇爆款生成、仿写拆解、完读率质检等能力
"""

from .models import ShortStoryConfig, ChapterBlueprint, ShortStoryResult, TropeTemplate
from .generator import ShortStoryGenerator

__all__ = [
    "ShortStoryConfig",
    "ChapterBlueprint", 
    "ShortStoryResult",
    "TropeTemplate",
    "ShortStoryGenerator",
]
