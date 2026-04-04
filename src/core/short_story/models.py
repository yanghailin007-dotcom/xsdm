"""
短篇小说数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class StoryMode(str, Enum):
    """短篇创作模式"""
    CREATIVE = "creative"      # 创意模式
    IMITATE = "imitate"        # 仿写模式


class StoryGenre(str, Enum):
    """短篇题材类型"""
    REVENGE_ROMANCE = "revenge_romance"      # 虐恋追妻火葬场
    URBAN_BRAINSTORM = "urban_brainstorm"    # 都市脑洞
    ERA_STORY = "era_story"                  # 年代文
    REBIRTH_REVENGE = "rebirth_revenge"      # 重生复仇
    HIGH_CONCEPT = "high_concept"            # 高概念脑洞


@dataclass
class ShortStoryConfig:
    """短篇创作配置"""
    mode: StoryMode = StoryMode.CREATIVE
    title: str = ""
    genre: StoryGenre = StoryGenre.REVENGE_ROMANCE
    target_word_count: int = 15000           # 目标总字数
    chapter_count: int = 8                   # 目标章节数
    ending_type: str = "open"                # he / be / open
    
    # 创意模式专用
    creative_seed: str = ""                  # 创意种子
    
    # 仿写模式专用
    reference_text: str = ""                 # 参考文本
    protagonist_replacement: str = ""        # 主角身份替换
    era_replacement: str = ""                # 时代背景替换
    
    # 系统配置
    username: str = ""
    project_path: str = ""
    api_client: Any = None


@dataclass
class ChapterBlueprint:
    """单章蓝图"""
    chapter_number: int
    title: str = ""
    word_count: int = 2000
    
    # 三大钩子
    crisis_hook: str = ""        # 危机钩（开头）
    payoff_hook: str = ""        # 爽点钩（中间）
    cliffhanger: str = ""        # 悬念钩（章末）
    
    # 情绪设计
    emotion_start: str = ""      # 开头情绪
    emotion_peak: str = ""       # 高峰情绪
    emotion_end: str = ""        # 结尾情绪
    
    # 剧情推进
    key_events: List[str] = field(default_factory=list)
    character_states: Dict[str, str] = field(default_factory=dict)
    visual_scenes: List[str] = field(default_factory=list)  # 可视化场景（短剧改编用）


@dataclass
class TropeTemplate:
    """套路模板（仿写模式拆解结果 / 创意模式直接生成）"""
    genre: str = ""
    core_conflict: str = ""          # 核心冲突
    protagonist_tag: str = ""        # 主角人设标签
    antagonist_tag: str = ""         # 反派人设标签
    opening_formula: str = ""        # 开局公式（死亡开局）
    turning_points: List[str] = field(default_factory=list)  # 关键转折点
    payoff_scenes: List[str] = field(default_factory=list)   # 爽点/名场面列表
    ending_formula: str = ""         # 结局公式
    hot_keywords: List[str] = field(default_factory=list)    # 建议书名热词


@dataclass
class ShortStoryResult:
    """短篇生成结果"""
    success: bool = False
    title: str = ""
    synopsis: str = ""
    chapters: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    total_word_count: int = 0
    
    # 质检报告
    quality_score: float = 0.0
    chapter_scores: Dict[int, float] = field(default_factory=dict)
    
    # 改编友好度
    visual_scenes: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    api_calls_used: int = 0
    points_consumed: float = 0.0
    error_message: str = ""
