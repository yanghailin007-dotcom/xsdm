"""
会话模式生成骨架 - 分域会话 + Context Brief 传递

提供:
- NovelGenerationSession: 小说生成专用会话基类
- SessionOrchestrator: 会话编排器，负责按顺序执行各域会话
- PhaseOneConversationOrchestrator: 第一阶段对话编排器（新）
- FallbackManager: 回退管理器（新）
- validators: 产物格式验证器（新）
"""

from .novel_generation_session import NovelGenerationSession
from .session_orchestrator import SessionOrchestrator

# 新增模块（第一阶段对话化改造）
from .validators import (
    FoundationPlanningValidator,
    CharacterNarrativeValidator,
    StructurePlanningValidator,
    ExpectationSystemValidator,
    ValidatorFactory,
    compare_session_outputs,
    quick_validate,
)
from .fallback_manager import (
    FallbackManager,
    ExecutionMode,
    FallbackReason,
    create_fallback_manager_from_config,
    get_default_fallback_manager,
)
from .phase_one_orchestrator import (
    PhaseOneConversationOrchestrator,
    PhaseOneContext,
    create_phase_one_orchestrator,
)

__all__ = [
    # 现有模块
    "NovelGenerationSession",
    "SessionOrchestrator",
    # 新增模块
    "FoundationPlanningValidator",
    "CharacterNarrativeValidator",
    "StructurePlanningValidator",
    "ExpectationSystemValidator",
    "ValidatorFactory",
    "compare_session_outputs",
    "quick_validate",
    "FallbackManager",
    "ExecutionMode",
    "FallbackReason",
    "create_fallback_manager_from_config",
    "get_default_fallback_manager",
    "PhaseOneConversationOrchestrator",
    "PhaseOneContext",
    "create_phase_one_orchestrator",
]
