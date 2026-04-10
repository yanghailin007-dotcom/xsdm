# -*- coding: utf-8 -*-
"""
V2 六层架构数据模型
定义所有数据结构和类型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


# ==================== 枚举类型 ====================

class ChapterType(Enum):
    """章节类型"""
    FACE_SLAP = "打脸章"
    REWARD = "收获章"
    CRISIS = "危机章"
    REVELATION = "揭秘章"
    TRANSITION = "过渡章"


class EmotionType(Enum):
    """情绪类型"""
    SHUANG = "爽"      # 打脸、收获
    RAN = "燃"         # 战斗、国战
    TIAN = "甜"        # 感情线
    XUAN = "悬"        # 悬念、危机
    NUE = "虐"         # 压抑（需快速反转）
    JI = "急"          # 倒计时
    JING = "惊"        # 震惊
    PA = "怕"          # 恐怖


class Severity(Enum):
    """严重程度"""
    CRITICAL = "critical"    # 严重
    WARNING = "warning"      # 警告
    RECOMMENDED = "recommended"  # 建议


# ==================== Layer 1: 核心设定 ====================

@dataclass
class WorldRule:
    """世界观规则"""
    rule: str
    description: str


@dataclass
class PowerLevel:
    """力量等级"""
    level: str
    description: str
    requirements: str


@dataclass
class PowerSystem:
    """力量体系"""
    name: str
    levels: List[str]
    upgrade_method: str
    current_level: str


@dataclass
class WorldView:
    """世界观"""
    overview: str
    core_rules: List[WorldRule]
    power_system: PowerSystem
    world_rules: List[str]


@dataclass
class GoldenFinger:
    """金手指"""
    name: str
    type: str
    core_mechanism: str
    current_level: str
    current_ability: str
    limitations: List[str]
    growth_path: List[Dict[str, Any]]
    reward_sound: str


@dataclass
class Protagonist:
    """主角设定"""
    name: str
    age: int
    background: str
    surface_identity: str
    true_identity: str
    personality_tags: List[str]
    core_motivation: str
    catchphrases: List[str]
    signature_actions: List[str]
    forbidden_behaviors: List[str]


@dataclass
class BurstFormula:
    """爽点公式"""
    pattern: str
    shock_hierarchy: List[Dict[str, str]]
    reward_types: List[str]


@dataclass
class CoreSetting:
    """Layer 1: 核心设定"""
    version: str = "1.0"
    worldview: WorldView = field(default_factory=lambda: WorldView("", [], PowerSystem("", [], "", ""), []))
    golden_finger: GoldenFinger = field(default_factory=lambda: GoldenFinger("", "", "", "", "", [], [], ""))
    protagonist: Protagonist = field(default_factory=lambda: Protagonist("", 0, "", "", "", [], "", [], [], []))
    core_selling_point: str = ""
    burst_formula: BurstFormula = field(default_factory=lambda: BurstFormula("", [], []))
    core_taboos: List[Dict[str, str]] = field(default_factory=list)


# ==================== Layer 2: 战术规划 ====================

@dataclass
class StageInfo:
    """阶段信息"""
    stage_name: str
    chapter_range: str
    word_range: str
    core_mission: str
    stage_climax: Dict[str, Any]
    key_milestones: List[Dict[str, Any]]


@dataclass
class EmotionPhase:
    """情绪阶段"""
    range: str
    emotion: str
    intensity: str
    description: str
    key_hook: str


@dataclass
class BurstDesign:
    """爽点设计"""
    target: str
    method: str
    shock_levels: List[Dict[str, str]]
    rewards: List[Dict[str, str]]


@dataclass
class HookDesign:
    """钩子设计"""
    type: str
    content: str
    tease: str


@dataclass
class CurrentChapter:
    """本章规划"""
    chapter_num: int
    chapter_type: str
    tactical_intent: Dict[str, Any]
    burst_design: BurstDesign
    hook_design: HookDesign
    must_include: Dict[str, List[str]]


@dataclass
class ChapterSection:
    """章节结构段落"""
    name: str
    word_count: str
    requirement: str
    emotion: str
    intensity: str


@dataclass
class ChapterStructure:
    """章节结构"""
    sections: List[ChapterSection]


@dataclass
class TacticalPlanning:
    """Layer 2: 战术规划"""
    version: str = "1.0"
    current_stage: StageInfo = field(default_factory=lambda: StageInfo("", "", "", "", {}, []))
    stage_emotion_curve: List[EmotionPhase] = field(default_factory=list)
    current_chapter: CurrentChapter = field(default_factory=lambda: CurrentChapter(0, "", {}, BurstDesign("", "", [], []), HookDesign("", "", ""), {}))
    chapter_structure: ChapterStructure = field(default_factory=lambda: ChapterStructure([]))
    continuity: Dict[str, str] = field(default_factory=dict)
    foreshadowing: List[Dict[str, Any]] = field(default_factory=list)


# ==================== Layer 3: 题材技法 ====================

@dataclass
class ShockStep:
    """震惊铺展步骤"""
    order: int
    name: str
    content: str
    format: str
    examples: List[str] = field(default_factory=list)


@dataclass
class BarrageTemplate:
    """弹幕模板"""
    type: str
    emotion: str
    examples: List[str]


@dataclass
class BarrageRules:
    """弹幕规则"""
    required: bool
    min_count: int
    max_count: int
    format: str
    templates: List[BarrageTemplate]


@dataclass
class MoneyRules:
    """金钱规则（神豪文）"""
    precision: str
    forbidden_words: List[str]
    required_format: str
    examples: Dict[str, List[str]]


@dataclass
class SystemPrompt:
    """系统提示音"""
    type: str
    template: str
    usage: str


@dataclass
class BystanderTemplate:
    """路人模板"""
    type: str
    examples: List[str]


@dataclass
class ForbiddenElement:
    """禁用元素"""
    element: str
    examples: List[str]
    reason: str


@dataclass
class RequiredElement:
    """必须元素"""
    element: str
    check: str
    severity: str = "warning"


@dataclass
class DialogueMethod:
    """对话达成方法"""
    method: str
    description: str
    weight: str


@dataclass
class GenreTechniques:
    """Layer 3: 题材技法"""
    genre: str
    version: str
    description: str
    shock_progression: Dict[str, Any] = field(default_factory=dict)
    barrage_rules: Optional[BarrageRules] = None
    money_rules: Optional[MoneyRules] = None
    system_prompts: List[SystemPrompt] = field(default_factory=list)
    bystander_templates: Optional[List[BystanderTemplate]] = None
    consumption_scenes: Optional[Dict[str, Any]] = None
    data_visualization: Optional[Dict[str, Any]] = None
    forbidden_elements: List[ForbiddenElement] = field(default_factory=list)
    required_elements: List[RequiredElement] = field(default_factory=list)
    dialogue_achievement: List[DialogueMethod] = field(default_factory=list)
    pacing: Dict[str, Any] = field(default_factory=dict)
    quality_checkpoints: List[Dict[str, Any]] = field(default_factory=list)


# ==================== Layer 4: 文风技法 ====================

@dataclass
class ParagraphRule:
    """段落规范"""
    max_lines: int
    avg_length: str
    mobile_first: bool


@dataclass
class SentenceRule:
    """句子规范"""
    short_ratio: float
    max_length: int
    colloquial: bool


@dataclass
class DialogueRule:
    """对话规范"""
    ratio: float
    format: str
    one_per_paragraph: bool
    tags: List[str]


@dataclass
class PacingRule:
    """节奏规范"""
    conflict_first_300: bool
    mini_burst_every_1000: bool
    hook_last_50: bool
    no_dialogue_limit: int


@dataclass
class ShockFlowRule:
    """震惊流技法"""
    principles: List[str]
    forbidden: List[str]


@dataclass
class EmotionControlRule:
    """情绪控制"""
    transitions_per_chapter: int
    climax_intensity: int
    no_regression: bool


@dataclass
class ForbiddenItem:
    """禁止事项"""
    item: str
    description: str
    example: str


@dataclass
class WritingStyle:
    """Layer 4: 文风技法"""
    version: str = "1.0"
    paragraph: ParagraphRule = field(default_factory=lambda: ParagraphRule(3, "30-50字", True))
    sentence: SentenceRule = field(default_factory=lambda: SentenceRule(0.6, 15, True))
    dialogue: DialogueRule = field(default_factory=lambda: DialogueRule(0.5, '""', True, []))
    pacing: PacingRule = field(default_factory=lambda: PacingRule(True, True, True, 200))
    shock_flow: ShockFlowRule = field(default_factory=lambda: ShockFlowRule([], []))
    emotion_control: EmotionControlRule = field(default_factory=lambda: EmotionControlRule(3, 8, True))
    forbidden: List[ForbiddenItem] = field(default_factory=list)


# ==================== Layer 5: AI约束 ====================

@dataclass
class WordCountConstraint:
    """字数约束"""
    target: int
    min: int
    max: int
    tolerance: float


@dataclass
class FormatConstraint:
    """格式约束"""
    type: str
    structure: Dict[str, Any]
    separator: str


@dataclass
class FormatRule:
    """格式规则"""
    dialogue_wrapper: str
    system_wrapper: str
    paragraph_max_lines: int
    paragraph_max_chars: int


@dataclass
class SafetyConstraint:
    """安全约束"""
    sensitive_words_filter: bool
    political_correctness: bool
    violence_level: str


@dataclass
class AIConstraints:
    """Layer 5: AI约束"""
    version: str = "1.0"
    word_count: WordCountConstraint = field(default_factory=lambda: WordCountConstraint(2200, 2000, 2500, 0.1))
    output_format: FormatConstraint = field(default_factory=dict)
    format_rules: FormatRule = field(default_factory=lambda: FormatRule('""', "【】", 3, 80))
    forbidden: List[Dict[str, Any]] = field(default_factory=list)
    safety: SafetyConstraint = field(default_factory=lambda: SafetyConstraint(True, True, "轻度"))


# ==================== Layer 6: 自检清单 ====================

@dataclass
class CheckItem:
    """检查项"""
    item: str
    check: Optional[str] = None
    validator: Optional[str] = None
    severity: str = "warning"
    critical: bool = False


@dataclass
class PreWritingCheck:
    """写前自检"""
    items: List[CheckItem]


@dataclass
class DuringWritingCheckpoint:
    """写中检查点"""
    position: str
    checks: List[str]


@dataclass
class FormatCheck:
    """格式检查"""
    items: List[CheckItem]


@dataclass
class ContentCheck:
    """内容检查"""
    items: List[CheckItem]


@dataclass
class GenreSpecificCheck:
    """题材特定检查"""
    genre: str
    items: List[CheckItem]


@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    weight: float
    min_score: int
    factors: List[str]


@dataclass
class QualityScore:
    """质量评分"""
    metrics: List[QualityMetric]
    pass_threshold: int
    rewrite_if_below: int


@dataclass
class SelfCheck:
    """Layer 6: 自检清单"""
    version: str = "1.0"
    pre_writing: List[CheckItem] = field(default_factory=list)
    during_writing: List[DuringWritingCheckpoint] = field(default_factory=list)
    post_writing_format: List[CheckItem] = field(default_factory=list)
    post_writing_content: List[CheckItem] = field(default_factory=list)
    post_writing_genre: List[CheckItem] = field(default_factory=list)
    quality_score: QualityScore = field(default_factory=lambda: QualityScore([], 70, 70))
    execution_rules: Dict[str, Any] = field(default_factory=dict)


# ==================== 组装上下文 ====================

@dataclass
class EmotionPlan:
    """情绪规划"""
    chapter_type: str
    curve: str
    breakdown: List[Dict[str, Any]]


@dataclass
class AssemblyContext:
    """组装上下文"""
    novel_title: str = "未命名"
    chapter_num: int = 0
    protagonist_name: str = "主角"
    chapter_type: str = "打脸章"
    core_setting: Optional[CoreSetting] = None
    tactical_planning: Optional[TacticalPlanning] = None
    emotion_plan: Optional[EmotionPlan] = None
