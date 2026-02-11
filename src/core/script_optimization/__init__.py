"""
短剧剧本多轮AI优化框架

使用示例:
    from src.core.script_optimization import ScriptOptimizationPipeline, OptimizationConfig
    
    pipeline = ScriptOptimizationPipeline()
    
    # 优化节拍表
    optimized_beats = pipeline.optimize_beats(beats_json, config={
        "check_emotional_arc": True,
        "check_turning_points": True
    })
    
    # 优化分镜剧本
    optimized_shots = pipeline.optimize_shots(shots_v2_json, config={
        "rounds": ["dialogue", "visual", "validation"]
    })
"""

from .pipeline import ScriptOptimizationPipeline
from .optimizers import (
    BeatStructureOptimizer,
    DialogueOptimizer,
    VisualOptimizer,
    InfoLayerOptimizer,
    PlatformValidator
)
from .config import OptimizationConfig

__all__ = [
    'ScriptOptimizationPipeline',
    'BeatStructureOptimizer',
    'DialogueOptimizer',
    'VisualOptimizer',
    'InfoLayerOptimizer',
    'PlatformValidator',
    'OptimizationConfig'
]
