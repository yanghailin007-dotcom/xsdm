"""
扩充版期待感管理系统 - 覆盖20种网文套路
核心功能：
1. 定义20种期待感类型，覆盖主流网文的所有常见套路
2. 事件驱动的期待绑定机制，根据事件进度灵活判断释放时机
3. 在章节生成前检查期待设置
4. 在章节生成后验证期待是否被满足
5. 提供期待感的验证和修正建议
6. 期待感密度监控和质量保障
"""

from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from src.utils.logger import get_logger


class ExpectationType(Enum):
    """期待感类型枚举 - 扩充到20种"""
    # 原有6种
    SHOWCASE = "showcase"  # 展示橱窗：提前展示奖励或能力
    SUPPRESSION_RELEASE = "suppression_release"  # 压抑释放：制造阻碍后释放
    NESTED_DOLL = "nested_doll"  # 套娃期待：大期待包着小期待
    EMOTIONAL_HOOK = "emotional_hook"  # 情绪钩子：打脸、认同、身份揭秘
    POWER_GAP = "power_gap"  # 实力差距：期待变强
    MYSTERY_FORESHADOW = "mystery_foreshadow"  # 伏笔揭秘

    # 新增14种
    PIG_EATS_TIGER = "pig_eats_tiger"  # 扮猪吃虎：隐藏实力后打脸
    SHOW_OFF_FACE_SLAP = "show_off_face_slap"  # 装逼打脸：展示实力打脸
    IDENTITY_REVEAL = "identity_reveal"  # 身份反转：隐藏身份揭晓
    BEAUTY_FAVOR = "beauty_favor"  # 美人恩：女主好感
    FORTUITOUS_ENCOUNTER = "fortuitous_encounter"  # 机缘巧合：意外获得奇遇
    COMPETITION = "competition"  # 比试切磋：宗门大比等
    AUCTION_TREASURE = "auction_treasure"  # 拍卖会争宝
    SECRET_REALM_EXPLORATION = "secret_realm_exploration"  # 秘境探险
    ALCHEMY_CRAFTING = "alchemy_crafting"  # 炼丹炼器
    FORMATION_BREAKING = "formation_breaking"  # 阵法破解
    SECT_MISSION = "sect_mission"  # 宗门任务
    CROSS_WORLD_TELEPORT = "cross_world_teleport"  # 跨界传送
    CRISIS_RESCUE = "crisis_rescue"  # 危机救援
    MASTER_INHERITANCE = "master_inheritance"  # 师恩传承


class ExpectationStatus(Enum):
    """期待感状态"""
    PLANTED = "planted"  # 已种植
    FERMENTING = "fermenting"  # 发酵中（正在积累势能）
    READY_TO_RELEASE = "ready_to_release"  # 即将释放
    RELEASED = "released"  # 已释放
    FAILED = "failed"  # 释放失败


@dataclass
class FlexibleRange:
    """灵活范围配置"""
    min_chapters: int  # 最少章节数
    max_chapters: int  # 最多章节数
    optimal_chapters: int  # 最佳章节数


@dataclass
class ExpectationRule:
    """期待感规则"""
    expectation_type: ExpectationType
    name: str
    description: str

    # 种植规则
    planting_methods: List[str] = field(default_factory=list)
    min_chapters_before_release: int = 3  # 最少需要多少章积累

    # 释放规则
    release_requirements: List[str] = field(default_factory=list)
    satisfaction_indicators: List[str] = field(default_factory=list)

    # 验证指标
    validation_metrics: List[str] = field(default_factory=list)


# 预定义的期待感规则 - 扩充到20种
EXPECTATION_RULES = {
    # 原有6种
    ExpectationType.SHOWCASE: ExpectationRule(
        expectation_type=ExpectationType.SHOWCASE,
        name="展示橱窗效应",
        description="提前展示奖励或能力的强大，让读者明确知道有一个'好东西'在那里，但主角暂时还得不到",
        planting_methods=[
            "让反派或配角展示强大能力",
            "通过传说或古籍描述宝物威力",
            "让主角亲眼目睹高阶修士施展法术"
        ],
        min_chapters_before_release=3,
        release_requirements=[
            "主角需要具备获取该奖励/能力的基础条件",
            "需要克服明确的阻碍",
            "过程要有波折，不能太顺利"
        ],
        satisfaction_indicators=[
            "主角成功获得奖励/学会能力",
            "展示了奖励/能力的具体效果",
            "有明确的成长或实力提升描述"
        ],
        validation_metrics=["showcase_clear", "obstacle_clear", "satisfaction_visible"]
    ),

    ExpectationType.SUPPRESSION_RELEASE: ExpectationRule(
        expectation_type=ExpectationType.SUPPRESSION_RELEASE,
        name="压抑与释放",
        description="制造阻碍，积累势能，在最后释放带来爽感",
        planting_methods=[
            "立靶子：设立必须要打倒的敌人或必须要得到的道具",
            "给限制：告诉读者为什么现在还做不到",
            "攒怒气/资源：用章节描写主角为了目标做的准备"
        ],
        min_chapters_before_release=5,
        release_requirements=[
            "有明确的至暗时刻或关键危机",
            "主角在最后时刻逆转局面",
            "释放过程要有足够的篇幅"
        ],
        satisfaction_indicators=[
            "问题得到解决",
            "有强烈的情感宣泄",
            "读者能感受到主角的成长"
        ],
        validation_metrics=["suppression_depth", "crisis_clear", "release_intensity"]
    ),

    ExpectationType.NESTED_DOLL: ExpectationRule(
        expectation_type=ExpectationType.NESTED_DOLL,
        name="套娃式期待",
        description="大期待包着小期待，环环相扣",
        planting_methods=[
            "在满足一个期待的同时，开启新的期待",
            "设置多层次的伏笔",
            "让不同层级的期待交织进行"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "每个期待都要有独立的满足点",
            "期待之间要有逻辑关联",
            "不能同时满足所有期待，要保持节奏"
        ],
        satisfaction_indicators=[
            "至少有一层期待被满足",
            "新的期待被合理引入",
            "整体推进了主线"
        ],
        validation_metrics=["layer_count", "transition_smooth", "main_thread_advance"]
    ),

    ExpectationType.EMOTIONAL_HOOK: ExpectationRule(
        expectation_type=ExpectationType.EMOTIONAL_HOOK,
        name="情绪钩子",
        description="利用情绪期待制造追读动力，如打脸、认同、身份揭秘",
        planting_methods=[
            "描写周围人对主角的误解、轻视",
            "埋下身份线索但暂不揭晓",
            "制造'想看他后悔'的期待"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "关键时刻的到来",
            "真相被揭晓或展示",
            "他人的反应被重点描写"
        ],
        satisfaction_indicators=[
            "他人的震惊、后悔",
            "主角得到认同或证明自己",
            "情感得到宣泄"
        ],
        validation_metrics=["emotion_strength", "reaction_clear", "satisfaction_degree"]
    ),

    ExpectationType.POWER_GAP: ExpectationRule(
        expectation_type=ExpectationType.POWER_GAP,
        name="实力差距期待",
        description="展示主角与目标的实力差距，让读者期待变强",
        planting_methods=[
            "让主角遭遇实力碾压",
            "展示高阶修士的强大",
            "明确实力差距的具体表现"
        ],
        min_chapters_before_release=5,
        release_requirements=[
            "主角有明确的修炼/成长路径",
            "有阶段性突破",
            "最终能够缩小或逆转差距"
        ],
        satisfaction_indicators=[
            "实力提升的具体表现",
            "能够战胜曾经的对手",
            "有量化的成长指标"
        ],
        validation_metrics=["gap_clear", "path_clear", "growth_visible"]
    ),

    ExpectationType.MYSTERY_FORESHADOW: ExpectationRule(
        expectation_type=ExpectationType.MYSTERY_FORESHADOW,
        name="伏笔揭秘期待",
        description="埋下伏笔，让读者期待真相揭晓",
        planting_methods=[
            "在剧情中埋下线索",
            "提出谜题或疑问",
            "暗示重大秘密的存在"
        ],
        min_chapters_before_release=7,
        release_requirements=[
            "谜题的答案要合理",
            "不能与之前的线索矛盾",
            "揭晓时机要恰当"
        ],
        satisfaction_indicators=[
            "谜题得到解答",
            "答案符合逻辑",
            "有恍然大悟的感觉"
        ],
        validation_metrics=["clue_clear", "answer_logical", "timing_appropriate"]
    ),

    # 新增14种
    ExpectationType.PIG_EATS_TIGER: ExpectationRule(
        expectation_type=ExpectationType.PIG_EATS_TIGER,
        name="扮猪吃虎",
        description="主角隐藏实力，被轻视后打脸",
        planting_methods=[
            "主角故意示弱",
            "他人轻视嘲讽",
            "营造废柴形象"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "关键时刻到来",
            "主角展露真实实力",
            "众人震惊后悔"
        ],
        satisfaction_indicators=[
            "实力展示震撼全场",
            "轻视者后悔莫及",
            "地位迅速提升"
        ],
        validation_metrics=["hiding_clear", "reversal_shocking", "face_slap_complete"]
    ),

    ExpectationType.SHOW_OFF_FACE_SLAP: ExpectationRule(
        expectation_type=ExpectationType.SHOW_OFF_FACE_SLAP,
        name="装逼打脸",
        description="主角展示实力/财富/人脉，让轻视者打脸",
        planting_methods=[
            "主角准备展示",
            "有人质疑",
            "立下赌约"
        ],
        min_chapters_before_release=1,
        release_requirements=[
            "展示成果",
            "事实说话",
            "众人震惊"
        ],
        satisfaction_indicators=[
            "质疑者被打脸",
            "展示内容超预期",
            "获得认可和尊重"
        ],
        validation_metrics=["challenge_clear", "showcase_impressive", "slap_effective"]
    ),

    ExpectationType.IDENTITY_REVEAL: ExpectationRule(
        expectation_type=ExpectationType.IDENTITY_REVEAL,
        name="身份反转",
        description="主角隐藏真实身份，揭晓时带来震撼",
        planting_methods=[
            "埋下身份线索",
            "暗示特殊背景",
            "偶尔展示异常能力"
        ],
        min_chapters_before_release=10,
        release_requirements=[
            "剧情发展到关键时刻",
            "身份揭晓合理",
            "众人震惊"
        ],
        satisfaction_indicators=[
            "身份揭晓震撼",
            "之前的线索得到解释",
            "地位发生改变"
        ],
        validation_metrics=["clues_consistent", "reveal_shocking", "impact_significant"]
    ),

    ExpectationType.BEAUTY_FAVOR: ExpectationRule(
        expectation_type=ExpectationType.BEAUTY_FAVOR,
        name="美人恩",
        description="女主对主角有好感，制造感情期待",
        planting_methods=[
            "女主出现",
            "初次互动",
            "埋下好感种子"
        ],
        min_chapters_before_release=3,
        release_requirements=[
            "主角展现魅力",
            "拯救女主",
            "感情升温"
        ],
        satisfaction_indicators=[
            "女主主动帮助",
            "暗示心意",
            "感情线推进"
        ],
        validation_metrics=["romance_clear", "favor_returned", "relationship_advances"]
    ),

    ExpectationType.FORTUITOUS_ENCOUNTER: ExpectationRule(
        expectation_type=ExpectationType.FORTUITOUS_ENCOUNTER,
        name="机缘巧合",
        description="意外获得奇遇/宝物/传承",
        planting_methods=[
            "发现线索",
            "误入秘境",
            "偶然机会"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "主角探索或冒险",
            "获得机缘",
            "实力提升"
        ],
        satisfaction_indicators=[
            "获得宝物或传承",
            "实力明显提升",
            "命运发生改变"
        ],
        validation_metrics=["encounter_reasonable", "gain_valuable", "growth_visible"]
    ),

    ExpectationType.COMPETITION: ExpectationRule(
        expectation_type=ExpectationType.COMPETITION,
        name="比试切磋",
        description="宗门大比/擂台赛/武会切磋",
        planting_methods=[
            "宣布比赛",
            "立下赌约",
            "众人质疑"
        ],
        min_chapters_before_release=5,
        release_requirements=[
            "比赛进行",
            "主角获胜",
            "打脸质疑者"
        ],
        satisfaction_indicators=[
            "一路过关斩将",
            "最终夺冠",
            "获得奖励和认可"
        ],
        validation_metrics=["preparation_adequate", "victory_earned", "rewards_gained"]
    ),

    ExpectationType.AUCTION_TREASURE: ExpectationRule(
        expectation_type=ExpectationType.AUCTION_TREASURE,
        name="拍卖会争宝",
        description="拍卖会上看中宝物，与竞拍者争夺",
        planting_methods=[
            "发现宝物",
            "准备资金",
            "遇到竞拍对手"
        ],
        min_chapters_before_release=3,
        release_requirements=[
            "拍卖开始",
            "激烈竞价",
            "最终获得"
        ],
        satisfaction_indicators=[
            "成功拍得宝物",
            "击败竞争对手",
            "物超所值"
        ],
        validation_metrics=["treasure_desirable", "competition_fierce", "acquisition_successful"]
    ),

    ExpectationType.SECRET_REALM_EXPLORATION: ExpectationRule(
        expectation_type=ExpectationType.SECRET_REALM_EXPLORATION,
        name="秘境探险",
        description="进入秘境/遗迹/副本探险",
        planting_methods=[
            "发现秘境入口",
            "组建队伍",
            "准备物资"
        ],
        min_chapters_before_release=8,
        release_requirements=[
            "探险过程",
            "获得宝物",
            "遭遇危险"
        ],
        satisfaction_indicators=[
            "历经凶险",
            "获得重宝",
            "实力提升"
        ],
        validation_metrics=["preparation_thorough", "exploration_exciting", "rewards_significant"]
    ),

    ExpectationType.ALCHEMY_CRAFTING: ExpectationRule(
        expectation_type=ExpectationType.ALCHEMY_CRAFTING,
        name="炼丹炼器",
        description="炼制丹药/炼制法器，展示能力",
        planting_methods=[
            "获得配方",
            "准备材料",
            "开始炼制"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "炼制过程",
            "克服困难",
            "炼制成功"
        ],
        satisfaction_indicators=[
            "炼制成功",
            "品质超预期",
            "众人震惊"
        ],
        validation_metrics=["materials_ready", "process_difficult", "quality_excellent"]
    ),

    ExpectationType.FORMATION_BREAKING: ExpectationRule(
        expectation_type=ExpectationType.FORMATION_BREAKING,
        name="阵法破解",
        description="破解阵法/解谜/过关",
        planting_methods=[
            "遇到阵法",
            "分析阵法",
            "尝试破解"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "分析原理",
            "寻找方法",
            "成功破解"
        ],
        satisfaction_indicators=[
            "成功破解",
            "获得奖励",
            "展现智慧"
        ],
        validation_metrics=["analysis_clever", "method_effective", "solution_elegant"]
    ),

    ExpectationType.SECT_MISSION: ExpectationRule(
        expectation_type=ExpectationType.SECT_MISSION,
        name="宗门任务",
        description="完成宗门任务获得奖励",
        planting_methods=[
            "接取任务",
            "了解要求",
            "开始执行"
        ],
        min_chapters_before_release=3,
        release_requirements=[
            "执行任务",
            "克服困难",
            "完成任务"
        ],
        satisfaction_indicators=[
            "任务完成",
            "获得奖励",
            "提升地位"
        ],
        validation_metrics=["mission_clear", "execution_smooth", "rewards_satisfactory"]
    ),

    ExpectationType.CROSS_WORLD_TELEPORT: ExpectationRule(
        expectation_type=ExpectationType.CROSS_WORLD_TELEPORT,
        name="跨界传送",
        description="跨越位面/世界/传送",
        planting_methods=[
            "发现传送阵",
            "获得传送符",
            "偶然触发"
        ],
        min_chapters_before_release=10,
        release_requirements=[
            "修复传送阵",
            "准备穿越",
            "成功传送"
        ],
        satisfaction_indicators=[
            "成功传送",
            "探索新环境",
            "开启新篇章"
        ],
        validation_metrics=["preparation_adequate", "transition_smooth", "new_world_exciting"]
    ),

    ExpectationType.CRISIS_RESCUE: ExpectationRule(
        expectation_type=ExpectationType.CRISIS_RESCUE,
        name="危机救援",
        description="他人陷入危机，主角出手相救",
        planting_methods=[
            "发现危机",
            "决定救援",
            "制定计划"
        ],
        min_chapters_before_release=2,
        release_requirements=[
            "追踪线索",
            "实施救援",
            "化险为夷"
        ],
        satisfaction_indicators=[
            "成功救出",
            "击败敌人",
            "获得感激"
        ],
        validation_metrics=["crisis_urgent", "rescue_timely", "gratitude_sincere"]
    ),

    ExpectationType.MASTER_INHERITANCE: ExpectationRule(
        expectation_type=ExpectationType.MASTER_INHERITANCE,
        name="师恩传承",
        description="获得师父指点/传承功法",
        planting_methods=[
            "遇到良师",
            "展现天赋",
            "获得认可"
        ],
        min_chapters_before_release=5,
        release_requirements=[
            "考验心性",
            "师父传授",
            "功法升级"
        ],
        satisfaction_indicators=[
            "被收为徒",
            "获得传承",
            "实力大增"
        ],
        validation_metrics=["talent_shown", "master_impressed", "inheritance_valuable"]
    )
}


@dataclass
class ExpectationRecord:
    """期待感记录 - 增强版"""
    id: str  # 唯一标识
    expectation_type: ExpectationType
    status: ExpectationStatus

    # 种植信息
    planted_chapter: int
    planting_description: str  # 如何种植的
    target_chapter: Optional[int] = None  # 计划在哪章释放

    # 事件绑定
    bound_event_id: Optional[str] = None  # 绑定的事件ID
    trigger_condition: Optional[str] = None  # 触发条件
    flexible_range: Optional[FlexibleRange] = None  # 灵活范围

    # 释放信息
    released_chapter: Optional[int] = None
    release_description: Optional[str] = None

    # 验证信息
    satisfaction_score: Optional[float] = None  # 满足度评分 0-10
    validation_notes: List[str] = field(default_factory=list)

    # 关联信息
    related_expectations: List[str] = field(default_factory=list)  # 套娃式期待的关联ID


@dataclass
class ExpectationConstraint:
    """期待感约束"""
    type: str  # must_plant, must_release, must_advance
    urgency: str  # critical, high, medium, low
    message: str
    suggestions: List[str] = field(default_factory=list)
    expectation_id: Optional[str] = None


class ExpectationManager:
    """
    扩充版期待感管理器 - 支持20种期待类型和事件驱动

    使用示例：
    ```python
    manager = ExpectationManager()

    # 规划阶段：为事件添加期待标签
    manager.tag_event_with_expectation(
        event_id="event_001",
        expectation_type=ExpectationType.SHOWCASE,
        planting_chapter=10,
        target_chapter=15,
        description="展示温天仁的六极真魔体威力"
    )

    # 生成前检查：本章需要处理哪些期待
    constraints = manager.pre_generation_check(chapter_num=15)

    # 生成后验证：期待是否被满足
    result = manager.post_generation_validate(
        chapter_num=15,
        content_analysis=analysis_result
    )
    ```
    """

    def __init__(self):
        self.logger = get_logger("ExpectationManager")
        self.expectations: Dict[str, ExpectationRecord] = {}  # id -> record
        self.event_expectation_map: Dict[str, str] = {}  # event_id -> expectation_id
        self.chapter_hooks: Dict[int, List[str]] = {}  # chapter -> [expectation_ids]

        # 统计信息
        self.planted_count = 0
        self.released_count = 0
        self.failed_count = 0

    def tag_event_with_expectation(
        self,
        event_id: str,
        expectation_type: ExpectationType,
        planting_chapter: int,
        description: str,
        target_chapter: Optional[int] = None,
        bound_event_id: Optional[str] = None,
        trigger_condition: Optional[str] = None,
        flexible_range: Optional[Dict] = None,
        related_expectations: Optional[List[str]] = None
    ) -> str:
        """
        为事件添加期待标签 - 增强版，支持事件绑定

        Args:
            event_id: 事件ID
            expectation_type: 期待类型
            planting_chapter: 种植章节
            description: 期待描述
            target_chapter: 目标释放章节（可选）
            bound_event_id: 绑定的事件ID（可选）
            trigger_condition: 触发条件（可选）
            flexible_range: 灵活范围配置（可选）
            related_expectations: 关联的期待ID（用于套娃式期待）

        Returns:
            期待ID
        """
        expectation_id = f"exp_{event_id}_{planting_chapter}"

        # 计算目标章节（如果未指定）
        rule = EXPECTATION_RULES.get(expectation_type)
        if not target_chapter and rule:
            target_chapter = planting_chapter + rule.min_chapters_before_release

        # 处理灵活范围
        flexible_range_obj = None
        if flexible_range:
            flexible_range_obj = FlexibleRange(
                min_chapters=flexible_range.get("min_chapters", 1),
                max_chapters=flexible_range.get("max_chapters", 10),
                optimal_chapters=flexible_range.get("optimal_chapters", 5)
            )

        record = ExpectationRecord(
            id=expectation_id,
            expectation_type=expectation_type,
            status=ExpectationStatus.PLANTED,
            planted_chapter=planting_chapter,
            planting_description=description,
            target_chapter=target_chapter,
            bound_event_id=bound_event_id or event_id,
            trigger_condition=trigger_condition,
            flexible_range=flexible_range_obj,
            related_expectations=related_expectations or []
        )

        self.expectations[expectation_id] = record
        self.event_expectation_map[event_id] = expectation_id

        # 记录章节钩子
        if planting_chapter not in self.chapter_hooks:
            self.chapter_hooks[planting_chapter] = []
        self.chapter_hooks[planting_chapter].append(expectation_id)

        if target_chapter and target_chapter not in self.chapter_hooks:
            self.chapter_hooks[target_chapter] = []
        if target_chapter:
            self.chapter_hooks[target_chapter].append(expectation_id)

        self.planted_count += 1

        self.logger.info(
            f"✅ 为事件 '{event_id}' 添加期待标签: {expectation_type.value} "
            f"(第{planting_chapter}章种植, 计划第{target_chapter}章释放)"
        )

        return expectation_id

    def pre_generation_check(
        self,
        chapter_num: int,
        event_context: Optional[Dict] = None
    ) -> List[ExpectationConstraint]:
        """
        生成前检查：返回本章必须处理的期待

        Args:
            chapter_num: 当前章节号
            event_context: 事件上下文（可选）

        Returns:
            约束列表
        """
        constraints = []

        # 检查1：本章是否有期待需要释放
        pending_expectations = self._get_pending_expectations_for_chapter(
            chapter_num, event_context
        )
        for exp_id in pending_expectations:
            exp_record = self.expectations.get(exp_id)
            if not exp_record:
                continue

            rule = EXPECTATION_RULES.get(exp_record.expectation_type)
            if not rule:
                continue

            constraints.append(ExpectationConstraint(
                type="must_release",
                urgency="critical",
                message=f"本章必须释放期待：{exp_record.planting_description}",
                suggestions=[
                    f"释放方法：{', '.join(rule.release_requirements)}",
                    f"满足指标：{', '.join(rule.satisfaction_indicators)}",
                    "确保有足够的篇幅和情感冲击"
                ],
                expectation_id=exp_id
            ))

        # 检查2：是否需要种植新的期待
        if len(pending_expectations) == 0:
            constraints.append(ExpectationConstraint(
                type="must_plant",
                urgency="high",
                message=f"本章没有待释放的期待，建议种植新的期待",
                suggestions=[
                    "展示橱窗：展示强大的能力或宝物",
                    "情绪钩子：制造误解或轻视",
                    "伏笔埋设：暗示重大秘密",
                    "套娃式：在满足旧期待的同时开启新期待",
                    "扮猪吃虎：主角隐藏实力",
                    "装逼打脸：展示实力打脸质疑者"
                ]
            ))

        # 检查3：是否有期待即将超时
        for exp_id, exp_record in self.expectations.items():
            if (exp_record.status == ExpectationStatus.PLANTED and
                exp_record.target_chapter and
                chapter_num >= exp_record.target_chapter + 2):

                constraints.append(ExpectationConstraint(
                    type="must_release",
                    urgency="critical",
                    message=f"期待 '{exp_record.planting_description}' 已超时{chapter_num - exp_record.target_chapter}章！",
                    suggestions=[
                        "立即在本章释放该期待",
                        "或者提供明确的延期理由"
                    ],
                    expectation_id=exp_id
                ))

        return constraints

    def post_generation_validate(
        self,
        chapter_num: int,
        content_analysis: Dict,
        released_expectation_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        生成后验证：检查期待是否被满足

        Args:
            chapter_num: 章节号
            content_analysis: 内容分析结果
            released_expectation_ids: 本章释放的期待ID列表

        Returns:
            验证结果
        """
        result = {
            "passed": True,
            "violations": [],
            "warnings": [],
            "recommendations": [],
            "satisfied_expectations": [],
            "pending_expectations": []
        }

        # 处理释放的期待
        if released_expectation_ids:
            for exp_id in released_expectation_ids:
                exp_record = self.expectations.get(exp_id)
                if not exp_record:
                    continue

                # 验证期待是否被满足
                satisfaction_score, notes = self._validate_expectation_satisfaction(
                    exp_record, content_analysis
                )

                exp_record.released_chapter = chapter_num
                exp_record.status = ExpectationStatus.RELEASED
                exp_record.satisfaction_score = satisfaction_score
                exp_record.validation_notes = notes

                if satisfaction_score >= 7.0:
                    result["satisfied_expectations"].append({
                        "id": exp_id,
                        "description": exp_record.planting_description,
                        "score": satisfaction_score
                    })
                    self.released_count += 1
                else:
                    result["violations"].append({
                        "severity": "high",
                        "message": f"期待 '{exp_record.planting_description}' 满足度不足 ({satisfaction_score:.1f}/10)",
                        "notes": notes
                    })
                    self.failed_count += 1

        # 检查未处理的期待
        pending = self._get_pending_expectations_for_chapter(chapter_num, {})
        if pending:
            for exp_id in pending:
                exp_record = self.expectations.get(exp_id)
                if exp_record:
                    result["pending_expectations"].append({
                        "id": exp_id,
                        "description": exp_record.planting_description,
                        "target_chapter": exp_record.target_chapter
                    })

        return result

    def _get_pending_expectations_for_chapter(
        self,
        chapter_num: int,
        event_context: Dict
    ) -> List[str]:
        """获取本章待释放的期待 - 支持事件驱动"""
        pending = []

        for exp_id, exp_record in self.expectations.items():
            if exp_record.status != ExpectationStatus.PLANTED:
                continue

            # 检查是否绑定了事件
            if exp_record.bound_event_id and event_context:
                # 获取事件进度
                event_progress = self._get_event_progress(
                    exp_record.bound_event_id, event_context
                )

                # 根据事件进度判断
                if self._should_release_expectation(exp_record, event_progress):
                    pending.append(exp_id)
            elif exp_record.target_chapter and exp_record.target_chapter <= chapter_num:
                # 传统章节判断
                pending.append(exp_id)

        return pending

    def _get_event_progress(self, event_id: str, event_context: Dict) -> Dict:
        """获取事件的进度信息"""
        active_events = event_context.get("active_events", [])
        for event in active_events:
            if event.get("id") == event_id:
                return {
                    "current_chapter": event.get("current_chapter", 0),
                    "total_chapters": event.get("total_chapters", 0),
                    "phase": event.get("current_phase", "unknown"),
                    "progress_percentage": event.get("progress_percentage", 0)
                }
        return {}

    def _should_release_expectation(
        self,
        exp_record: ExpectationRecord,
        event_progress: Dict
    ) -> bool:
        """判断是否应该释放期待"""
        if not event_progress:
            return False

        flexible_range = exp_record.flexible_range
        if not flexible_range:
            return False

        progress_percentage = event_progress.get("progress_percentage", 0)

        # 事件进度达到60-90%时是最佳释放时机
        if 60 <= progress_percentage <= 90:
            return True

        # 如果超过最大等待范围，强制释放
        if progress_percentage > 90:
            return True

        return False

    def _validate_expectation_satisfaction(
        self,
        exp_record: ExpectationRecord,
        content_analysis: Dict
    ) -> Tuple[float, List[str]]:
        """
        验证期待的满足度

        Returns:
            (评分, 备注)
        """
        rule = EXPECTATION_RULES.get(exp_record.expectation_type)
        if not rule:
            return 5.0, ["未找到期待规则"]

        score = 0.0
        notes = []

        # 检查满足指标
        content = content_analysis.get("content", "")
        has_satisfaction = False

        for indicator in rule.satisfaction_indicators:
            if indicator.lower() in content.lower():
                has_satisfaction = True
                break

        if has_satisfaction:
            score += 5.0
            notes.append("✅ 包含满足指标")
        else:
            notes.append(f"❌ 缺少满足指标: {', '.join(rule.satisfaction_indicators)}")

        # 检查释放要求
        release_requirements_met = 0
        for requirement in rule.release_requirements:
            if requirement.lower() in content.lower():
                release_requirements_met += 1

        if release_requirements_met >= len(rule.release_requirements) * 0.6:
            score += 3.0
            notes.append(f"✅ 满足{release_requirements_met}/{len(rule.release_requirements)}个释放要求")
        else:
            notes.append(f"⚠️ 仅满足{release_requirements_met}/{len(rule.release_requirements)}个释放要求")

        # 基础分
        score += 2.0

        return min(10.0, score), notes

    def generate_expectation_report(
        self,
        start_chapter: int = 1,
        end_chapter: Optional[int] = None
    ) -> Dict:
        """
        生成期待感报告

        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节

        Returns:
            期待感报告
        """
        if not end_chapter:
            end_chapter = max(
                [exp.planted_chapter for exp in self.expectations.values()], default=1
            )

        # 统计期待
        total_expectations = 0
        released_expectations = 0
        failed_expectations = 0
        pending_expectations = 0

        expectation_type_stats = {}

        for exp_record in self.expectations.values():
            if start_chapter <= exp_record.planted_chapter <= end_chapter:
                total_expectations += 1

                # 统计类型
                exp_type = exp_record.expectation_type.value
                if exp_type not in expectation_type_stats:
                    expectation_type_stats[exp_type] = {"total": 0, "released": 0, "failed": 0}
                expectation_type_stats[exp_type]["total"] += 1

                if exp_record.status == ExpectationStatus.RELEASED:
                    released_expectations += 1
                    expectation_type_stats[exp_type]["released"] += 1

                    if exp_record.satisfaction_score and exp_record.satisfaction_score < 7.0:
                        failed_expectations += 1
                        expectation_type_stats[exp_type]["failed"] += 1
                elif exp_record.status == ExpectationStatus.PLANTED:
                    pending_expectations += 1

        # 计算满足率
        satisfaction_rate = (
            (released_expectations - failed_expectations) / released_expectations
            if released_expectations > 0 else 0
        )

        return {
            "chapter_range": f"{start_chapter}-{end_chapter}",
            "total_expectations": total_expectations,
            "released_expectations": released_expectations,
            "failed_expectations": failed_expectations,
            "pending_expectations": pending_expectations,
            "satisfaction_rate": round(satisfaction_rate * 100, 2),
            "expectation_type_stats": expectation_type_stats,
            "issues": self._identify_expectation_issues(),
            "recommendations": self._generate_expectation_recommendations()
        }

    def _identify_expectation_issues(self) -> List[Dict]:
        """识别期待感问题"""
        issues = []

        # 检查超时的期待
        for exp_id, exp_record in self.expectations.items():
            if (exp_record.status == ExpectationStatus.PLANTED and
                exp_record.target_chapter):

                # 这里简化处理，实际应该传入当前章节
                if exp_record.planted_chapter > exp_record.target_chapter + 10:
                    issues.append({
                        "severity": "critical",
                        "type": "overdue_expectation",
                        "message": f"期待 '{exp_record.planting_description}' 已严重超时"
                    })

        return issues

    def _generate_expectation_recommendations(self) -> List[str]:
        """生成期待感改进建议"""
        recommendations = []

        # 检查期待类型分布
        type_counts = {}
        for exp_record in self.expectations.values():
            exp_type = exp_record.expectation_type.value
            type_counts[exp_type] = type_counts.get(exp_type, 0) + 1

        # 检查核心套路
        if not type_counts.get("showcase"):
            recommendations.append("建议：增加'展示橱窗'类型的期待，提前展示奖励或能力的强大")

        if not type_counts.get("emotional_hook"):
            recommendations.append("建议：增加'情绪钩子'类型的期待，制造打脸或认同的期待")

        # 检查新增套路
        if not type_counts.get("pig_eats_tiger"):
            recommendations.append("建议：增加'扮猪吃虎'类型的期待，这是网文经典套路")

        if not type_counts.get("show_off_face_slap"):
            recommendations.append("建议：增加'装逼打脸'类型的期待，提升爽感")

        return recommendations

    def export_expectation_map(self) -> Dict:
        """导出期待感映射"""
        return {
            "expectations": {
                exp_id: {
                    "type": exp_record.expectation_type.value,
                    "status": exp_record.status.value,
                    "planted_chapter": exp_record.planted_chapter,
                    "target_chapter": exp_record.target_chapter,
                    "released_chapter": exp_record.released_chapter,
                    "description": exp_record.planting_description,
                    "satisfaction_score": exp_record.satisfaction_score,
                    "bound_event_id": exp_record.bound_event_id,
                    "trigger_condition": exp_record.trigger_condition,
                    "flexible_range": {
                        "min_chapters": exp_record.flexible_range.min_chapters,
                        "max_chapters": exp_record.flexible_range.max_chapters,
                        "optimal_chapters": exp_record.flexible_range.optimal_chapters
                    } if exp_record.flexible_range else None
                }
                for exp_id, exp_record in self.expectations.items()
            },
            "event_expectation_map": self.event_expectation_map,
            "chapter_hooks": self.chapter_hooks
        }

    def import_expectation_map(self, data: Dict):
        """导入期待感映射"""
        if "expectations" in data:
            for exp_id, exp_data in data["expectations"].items():
                flexible_range_obj = None
                if exp_data.get("flexible_range"):
                    fr = exp_data["flexible_range"]
                    flexible_range_obj = FlexibleRange(
                        min_chapters=fr["min_chapters"],
                        max_chapters=fr["max_chapters"],
                        optimal_chapters=fr["optimal_chapters"]
                    )

                exp_record = ExpectationRecord(
                    id=exp_id,
                    expectation_type=ExpectationType(exp_data["type"]),
                    status=ExpectationStatus(exp_data["status"]),
                    planted_chapter=exp_data["planted_chapter"],
                    planting_description=exp_data["description"],
                    target_chapter=exp_data.get("target_chapter"),
                    released_chapter=exp_data.get("released_chapter"),
                    satisfaction_score=exp_data.get("satisfaction_score"),
                    bound_event_id=exp_data.get("bound_event_id"),
                    trigger_condition=exp_data.get("trigger_condition"),
                    flexible_range=flexible_range_obj
                )
                self.expectations[exp_id] = exp_record

        if "event_expectation_map" in data:
            self.event_expectation_map = data["event_expectation_map"]

        if "chapter_hooks" in data:
            self.chapter_hooks = data["chapter_hooks"]


def auto_bind_expectation_to_event(event: Dict) -> ExpectationType:
    """
    根据事件类型自动匹配最合适的期待类型

    Args:
        event: 事件字典，包含main_goal等信息

    Returns:
        匹配的期待类型
    """
    event_goal = event.get("main_goal", "").lower()
    event_type = event.get("type", "")
    event_name = event.get("name", "").lower()

    # 决策树 - 按优先级匹配
    if "比试" in event_goal or "大比" in event_goal or "比赛" in event_goal or "擂台" in event_goal:
        return ExpectationType.COMPETITION

    if "炼丹" in event_goal or "炼器" in event_goal:
        return ExpectationType.ALCHEMY_CRAFTING

    if "拍卖" in event_goal or "竞拍" in event_goal:
        return ExpectationType.AUCTION_TREASURE

    if "秘境" in event_goal or "遗迹" in event_goal or "副本" in event_goal or "探险" in event_goal:
        return ExpectationType.SECRET_REALM_EXPLORATION

    if "救援" in event_goal or "救" in event_goal or "拯救" in event_goal:
        return ExpectationType.CRISIS_RESCUE

    if "师父" in event_goal or "传承" in event_goal or "指点" in event_goal:
        return ExpectationType.MASTER_INHERITANCE

    if "传送" in event_goal or "穿越" in event_goal or "跨界" in event_goal:
        return ExpectationType.CROSS_WORLD_TELEPORT

    if "任务" in event_goal or "完成" in event_goal:
        return ExpectationType.SECT_MISSION

    if "阵法" in event_goal or "破解" in event_goal or "解谜" in event_goal:
        return ExpectationType.FORMATION_BREAKING

    if "机缘" in event_goal or "奇遇" in event_goal or "意外" in event_goal:
        return ExpectationType.FORTUITOUS_ENCOUNTER

    if "身份" in event_goal or "揭秘" in event_goal or "身世" in event_goal:
        return ExpectationType.IDENTITY_REVEAL

    if "美人" in event_goal or "女主" in event_goal or "感情" in event_goal or "好感" in event_goal:
        return ExpectationType.BEAUTY_FAVOR

    if "打脸" in event_goal or "展示" in event_goal or "证明" in event_goal:
        return ExpectationType.SHOW_OFF_FACE_SLAP

    if "隐藏" in event_goal or "示弱" in event_goal or "废柴" in event_goal:
        return ExpectationType.PIG_EATS_TIGER

    # 检查事件名称
    if "比试" in event_name or "大比" in event_name:
        return ExpectationType.COMPETITION

    if "拍卖" in event_name:
        return ExpectationType.AUCTION_TREASURE

    if "秘境" in event_name or "遗迹" in event_name:
        return ExpectationType.SECRET_REALM_EXPLORATION

    # 默认使用套娃期待
    return ExpectationType.NESTED_DOLL


class ExpectationDensityMonitor:
    """期待感密度监控器"""

    def __init__(self, expectation_manager: ExpectationManager):
        self.em = expectation_manager
        self.logger = get_logger("ExpectationDensityMonitor")

    def calculate_density(
        self,
        start_chapter: int,
        end_chapter: int
    ) -> Dict:
        """计算期待感密度"""
        total_chapters = end_chapter - start_chapter + 1

        # 统计各类期待数量
        expectation_counts = {}
        for exp_record in self.em.expectations.values():
            if start_chapter <= exp_record.planted_chapter <= end_chapter:
                exp_type = exp_record.expectation_type.value
                expectation_counts[exp_type] = expectation_counts.get(exp_type, 0) + 1

        # 计算密度
        density = {
            "total_expectations": sum(expectation_counts.values()),
            "expectations_per_chapter": sum(expectation_counts.values()) / total_chapters,
            "type_distribution": expectation_counts,
            "density_rating": self._rate_density(
                sum(expectation_counts.values()), total_chapters
            )
        }

        return density

    def _rate_density(
        self,
        total_expectations: int,
        total_chapters: int
    ) -> str:
        """评估密度等级"""
        density = total_expectations / total_chapters

        if density >= 1.5:
            return "过高"
        elif density >= 1.0:
            return "优秀"
        elif density >= 0.7:
            return "良好"
        elif density >= 0.5:
            return "一般"
        else:
            return "不足"

    def generate_recommendations(self, density: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        rating = density.get("density_rating", "")

        if rating == "不足":
            recommendations.append(
                "期待感密度不足，建议增加期待种植。每10章应至少有5-8个期待。"
            )
        elif rating == "过高":
            recommendations.append(
                "期待感密度过高，可能导致读者疲劳。建议适当减少，或延长期待发酵时间。"
            )

        # 检查类型分布
        type_dist = density.get("type_distribution", {})
        if not type_dist.get("pig_eats_tiger"):
            recommendations.append("建议增加'扮猪吃虎'类型的期待，这是网文经典套路。")

        if not type_dist.get("show_off_face_slap"):
            recommendations.append("建议增加'装逼打脸'类型的期待，提升爽感。")

        if not type_dist.get("beauty_favor"):
            recommendations.append("建议增加'美人恩'类型的期待，丰富感情线。")

        return recommendations
