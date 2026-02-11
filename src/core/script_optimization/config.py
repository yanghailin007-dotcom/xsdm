"""
优化配置类
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class BeatStructureConfig:
    """节拍结构优化配置"""
    check_emotional_arc: bool = True
    check_turning_points: bool = True
    check_duration_distribution: bool = True
    target_beats_range: tuple = (10, 14)  # 46秒短剧建议的beats数量
    climax_duration_ratio: float = 0.3  # 高潮部分时长占比


@dataclass
class DialogueConfig:
    """对白优化配置"""
    remove_preaching: bool = True
    remove_explicit_exposition: bool = True
    max_dialogue_length: int = 20  # 单句台词最大单词数


@dataclass
class VisualConfig:
    """视觉优化配置"""
    enhance_veo_prompt: bool = True
    add_shot_spec: bool = True
    vertical_frame_check: bool = True


@dataclass
class InfoLayerConfig:
    """信息层次优化配置"""
    progressive_revelation: bool = True
    add_foreshadowing: bool = True
    max_foreshadowing_distance: float = 0.5


@dataclass
class ValidationConfig:
    """平台质检配置"""
    check_hook: bool = True
    check_pacing: bool = True
    check_cliffhanger: bool = True
    max_avg_shot_duration: float = 4.0
    min_avg_shot_duration: float = 2.0


@dataclass
class OptimizationConfig:
    """完整优化配置"""
    platform: str = "douyin"  # douyin | kuaishou | general
    target_duration: int = 46
    
    # 轮次开关
    beat_structure: bool = True
    dialogue: bool = True
    visual: bool = True
    info_layer: bool = True
    validation: bool = True
    
    # 质量阈值
    quality_threshold: float = 7.5
    max_iterations: int = 2
    
    # 详细配置
    beat_structure_config: BeatStructureConfig = field(default_factory=BeatStructureConfig)
    dialogue_config: DialogueConfig = field(default_factory=DialogueConfig)
    visual_config: VisualConfig = field(default_factory=VisualConfig)
    info_layer_config: InfoLayerConfig = field(default_factory=InfoLayerConfig)
    validation_config: ValidationConfig = field(default_factory=ValidationConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationConfig':
        """从字典创建配置"""
        config = cls()
        
        if 'platform' in data:
            config.platform = data['platform']
        if 'target_duration' in data:
            config.target_duration = data['target_duration']
        if 'beat_structure' in data:
            config.beat_structure = data['beat_structure']
        if 'dialogue' in data:
            config.dialogue = data['dialogue']
        if 'visual' in data:
            config.visual = data['visual']
        if 'info_layer' in data:
            config.info_layer = data['info_layer']
        if 'validation' in data:
            config.validation = data['validation']
        if 'quality_threshold' in data:
            config.quality_threshold = data['quality_threshold']
        if 'max_iterations' in data:
            config.max_iterations = data['max_iterations']
            
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'platform': self.platform,
            'target_duration': self.target_duration,
            'beat_structure': self.beat_structure,
            'dialogue': self.dialogue,
            'visual': self.visual,
            'info_layer': self.info_layer,
            'validation': self.validation,
            'quality_threshold': self.quality_threshold,
            'max_iterations': self.max_iterations
        }
