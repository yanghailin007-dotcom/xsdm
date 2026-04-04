"""
会话模式生成骨架 - 分域会话 + Context Brief 传递

提供:
- NovelGenerationSession: 小说生成专用会话基类
- SessionOrchestrator: 会话编排器，负责按顺序执行各域会话
"""

from .novel_generation_session import NovelGenerationSession
from .session_orchestrator import SessionOrchestrator

__all__ = [
    "NovelGenerationSession",
    "SessionOrchestrator",
]
