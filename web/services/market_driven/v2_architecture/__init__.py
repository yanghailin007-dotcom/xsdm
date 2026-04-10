# -*- coding: utf-8 -*-
"""
V2 六层架构提示词系统

六层架构:
- Layer 1: 核心设定 (CoreSetting)
- Layer 2: 战术规划 (TacticalPlanning)
- Layer 3: 题材技法 (GenreTechniques)
- Layer 4: 文风技法 (WritingStyle)
- Layer 5: AI约束 (AIConstraints)
- Layer 6: 自检清单 (SelfCheck)
"""

from .prompt_assembler_v2 import PromptAssemblerV2, AssemblyContext
from .layer_loaders import (
    CoreSettingLoader,
    TacticalPlanningLoader,
    GenreTechniquesLoader,
    WritingStyleLoader,
    AIConstraintsLoader,
    SelfCheckLoader
)
from .renderers import (
    CoreSettingRenderer,
    TacticalPlanningRenderer,
    GenreTechniquesRenderer,
    WritingStyleRenderer,
    AIConstraintsRenderer,
    SelfCheckRenderer
)
from .conversation_session_v2 import (
    LayeredConversationSession,
    LayeredSystemPrompt,
    LayeredUserPrompt
)
from .chapter_conversation_v2 import (
    ChapterConversationV2,
    create_chapter_conversation_v2
)

__all__ = [
    'PromptAssemblerV2',
    'AssemblyContext',
    # Loaders
    'CoreSettingLoader',
    'TacticalPlanningLoader',
    'GenreTechniquesLoader',
    'WritingStyleLoader',
    'AIConstraintsLoader',
    'SelfCheckLoader',
    # Renderers
    'CoreSettingRenderer',
    'TacticalPlanningRenderer',
    'GenreTechniquesRenderer',
    'WritingStyleRenderer',
    'AIConstraintsRenderer',
    'SelfCheckRenderer',
    # V2 对话会话
    'LayeredConversationSession',
    'LayeredSystemPrompt',
    'LayeredUserPrompt',
    'ChapterConversationV2',
    'create_chapter_conversation_v2'
]
