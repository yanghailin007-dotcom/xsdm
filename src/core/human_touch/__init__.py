"""
人味增强系统 - 让AI写作更像真人

主要模块:
- analyzer: 人味特征分析器
- database: 头部作品数据库
- style_guide: 风格指南
"""

from .analyzer import HumanTouchAnalyzer
from .database import SampleDatabase, NovelSample, ChapterSample

__all__ = [
    'HumanTouchAnalyzer',
    'SampleDatabase', 
    'NovelSample',
    'ChapterSample',
]
