"""
章节生成对话模式的 Prompt Layers 通用模块

复用市场导向V2的六层架构，通过 re-export 避免重复代码。

V2原文件保留在 web/services/market_driven/v2_architecture/ 不变，
此处仅做 re-export 供 src/core/chapter_engine/ 使用。
"""

# V2 数据模型
try:
    from web.services.market_driven.v2_architecture.models import (
        ChapterType, EmotionType, Severity,
        CoreSetting, WorldView, WorldRule, PowerSystem, GoldenFinger, Protagonist,
        TacticalPlanning, StageInfo, EmotionPhase, BurstDesign, HookDesign,
        GenreTechniques, WritingStyle, AIConstraints, SelfCheck,
        EmotionPlan, AssemblyContext
    )
except ImportError:
    # 如果路径不同，尝试备用import
    import importlib
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    v2_models = importlib.import_module("web.services.market_driven.v2_architecture.models")
    ChapterType = v2_models.ChapterType
    EmotionType = v2_models.EmotionType
    Severity = v2_models.Severity
    CoreSetting = v2_models.CoreSetting
    WorldView = v2_models.WorldView
    WorldRule = v2_models.WorldRule
    PowerSystem = v2_models.PowerSystem
    GoldenFinger = v2_models.GoldenFinger
    Protagonist = v2_models.Protagonist
    TacticalPlanning = v2_models.TacticalPlanning
    StageInfo = v2_models.StageInfo
    EmotionPhase = v2_models.EmotionPhase
    BurstDesign = v2_models.BurstDesign
    HookDesign = v2_models.HookDesign
    GenreTechniques = v2_models.GenreTechniques
    WritingStyle = v2_models.WritingStyle
    AIConstraints = v2_models.AIConstraints
    SelfCheck = v2_models.SelfCheck
    EmotionPlan = v2_models.EmotionPlan
    AssemblyContext = v2_models.AssemblyContext

# V2 Loaders
try:
    from web.services.market_driven.v2_architecture.layer_loaders import (
        BaseLoader,
        CoreSettingLoader,
        TacticalPlanningLoader,
        GenreTechniquesLoader,
        WritingStyleLoader,
        AIConstraintsLoader,
        SelfCheckLoader
    )
except ImportError:
    import importlib
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    v2_loaders = importlib.import_module("web.services.market_driven.v2_architecture.layer_loaders")
    BaseLoader = v2_loaders.BaseLoader
    CoreSettingLoader = v2_loaders.CoreSettingLoader
    TacticalPlanningLoader = v2_loaders.TacticalPlanningLoader
    GenreTechniquesLoader = v2_loaders.GenreTechniquesLoader
    WritingStyleLoader = v2_loaders.WritingStyleLoader
    AIConstraintsLoader = v2_loaders.AIConstraintsLoader
    SelfCheckLoader = v2_loaders.SelfCheckLoader

# V2 Renderers
try:
    from web.services.market_driven.v2_architecture.renderers import (
        BaseRenderer,
        CoreSettingRenderer,
        TacticalPlanningRenderer,
        GenreTechniquesRenderer,
        WritingStyleRenderer,
        AIConstraintsRenderer,
        SelfCheckRenderer
    )
except ImportError:
    import importlib
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    v2_renderers = importlib.import_module("web.services.market_driven.v2_architecture.renderers")
    BaseRenderer = v2_renderers.BaseRenderer
    CoreSettingRenderer = v2_renderers.CoreSettingRenderer
    TacticalPlanningRenderer = v2_renderers.TacticalPlanningRenderer
    GenreTechniquesRenderer = v2_renderers.GenreTechniquesRenderer
    WritingStyleRenderer = v2_renderers.WritingStyleRenderer
    AIConstraintsRenderer = v2_renderers.AIConstraintsRenderer
    SelfCheckRenderer = v2_renderers.SelfCheckRenderer

# 本模块新增：情绪曲线模板
from .emotion_curves import (
    EMOTION_CURVE_TEMPLATES,
    get_emotion_curve_text,
    get_emotion_curve_for_role,
    infer_chapter_role,
    get_chapter_type_from_role,
    CHAPTER_ROLES
)

__all__ = [
    # 枚举
    'ChapterType', 'EmotionType', 'Severity',
    # 数据模型
    'CoreSetting', 'WorldView', 'WorldRule', 'PowerSystem', 'GoldenFinger', 'Protagonist',
    'TacticalPlanning', 'StageInfo', 'EmotionPhase', 'BurstDesign', 'HookDesign',
    'GenreTechniques', 'WritingStyle', 'AIConstraints', 'SelfCheck',
    'EmotionPlan', 'AssemblyContext',
    # Loaders
    'BaseLoader', 'CoreSettingLoader', 'TacticalPlanningLoader',
    'GenreTechniquesLoader', 'WritingStyleLoader', 'AIConstraintsLoader', 'SelfCheckLoader',
    # Renderers
    'BaseRenderer', 'CoreSettingRenderer', 'TacticalPlanningRenderer',
    'GenreTechniquesRenderer', 'WritingStyleRenderer', 'AIConstraintsRenderer', 'SelfCheckRenderer',
    # 情绪曲线
    'EMOTION_CURVE_TEMPLATES', 'get_emotion_curve_text', 'get_emotion_curve_for_role', 'CHAPTER_ROLES',
]
