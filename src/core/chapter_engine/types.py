from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any


@dataclass
class ChapterContext:
    novel_title: str
    core_setting: str = ""
    worldview: str = ""
    characters: str = ""
    previous_summary: str = ""
    writing_style: str = "番茄小说爽文风格，快节奏，情节紧凑"
    word_count_min: int = 1500
    word_count_max: int = 3500
    novel_data: Optional[Dict[str, Any]] = None  # 🔥 新增：对话模式需要的小说数据


@dataclass
class BatchContext:
    """批次上下文（从大阶段解析的爽点单元信息）"""
    stage_name: str = ""           # 大阶段名称（opening/development/climax/ending）
    stage_chapter_range: str = ""  # 大阶段章节范围（如 "1-100"）
    core_payoff: str = ""          # 核心爽点
    suppression_setup: str = ""    # 压抑铺垫
    key_events: List[str] = field(default_factory=list)  # 关键事件列表
    emotional_focus: str = ""      # 情绪焦点


@dataclass
class ChapterSpec:
    chapter_number: int
    title: str = ""
    outline: str = ""
    is_golden_chapter: bool = False
    expected_role: str = ""        # 🔥 新增：预期章节角色（setup/suppression/payoff/harvest/crisis）
    emotion_curve: str = ""        # 🔥 新增：情绪曲线类型（打脸章/爆发章/收获章/危机章/铺垫章）


@dataclass
class GeneratedChapter:
    chapter_number: int
    title: str
    content: str
    word_count: int = 0
    quality_score: float = 0.0
    issues: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    chapters: List[GeneratedChapter] = field(default_factory=list)
    overall_score: float = 0.0
    can_proceed: bool = True
    issues: List[str] = field(default_factory=list)


@dataclass
class Callbacks:
    on_chapter_done: Optional[Callable[[GeneratedChapter], None]] = None
    on_progress: Optional[Callable[[Dict], None]] = None
