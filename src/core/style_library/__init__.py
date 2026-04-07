"""
文风库系统 - 精准匹配头部作品风格
"""

from .database import StyleDatabase, StyleProfile, ChapterSample
from .extractor import StyleExtractor, StyleFingerprint
from .matcher import StyleMatcher, StyleRequirements
from .injector import StyleInjector

__all__ = [
    'StyleDatabase', 'StyleProfile', 'ChapterSample',
    'StyleExtractor', 'StyleFingerprint',
    'StyleMatcher', 'StyleRequirements', 'StyleInjector',
]
