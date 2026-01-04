"""
期待感管理系统
核心功能：
1. 定义期待感的类型和规则
2. 在事件规划阶段引入期待标签
3. 在章节生成前检查期待设置
4. 在章节生成后验证期待是否被满足
5. 提供期待感的验证和修正建议
"""

from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from src.utils.logger import get_logger


class ExpectationType(Enum):
    """期待感类型枚举"""
    SHOWCASE = "showcase"  # 展示橱窗：提前展示奖励或能力
    SUPPRESSION_RELEASE = "suppression_release"  # 压抑释放：制造阻碍后释放
    NESTED_DOLL = "nested_doll"  # 套娃期待：大期待包着小期待
    EMOTIONAL_HOOK = "emotional_hook"  # 情绪钩子：打脸、认同、身份揭秘
    POWER_GAP = "power_gap"  # 实力差距：期待变强
    MYSTERY_FORESHADOW = "mystery_foreshadow"  # 伏笔揭秘


class ExpectationStatus(Enum):
    """期待感状态"""
    PLANTED = "planted"  # 已种植
    FERMENTING = "fermenting"  # 发酵中（正在积累势能）
    READY_TO_RELEASE = "ready_to_release"  # 即将释放
    RELEASED = "released"  # 已释放
    FAILED = "failed"  # 释放失败


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


# 预定义的期待感规则
EXPECTATION_RULES = {
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
    )
}


@dataclass
class ExpectationRecord:
    """期待感记录"""
    id: str  # 唯一标识
    expectation_type: ExpectationType
    status: ExpectationStatus
    
    # 种植信息
    planted_chapter: int
    planting_description: str  # 如何种植的
    target_chapter: Optional[int] = None  # 计划在哪章释放
    
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
    期待感管理器
    
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
        related_expectations: Optional[List[str]] = None
    ) -> str:
        """
        为事件添加期待标签
        
        Args:
            event_id: 事件ID
            expectation_type: 期待类型
            planting_chapter: 种植章节
            description: 期待描述
            target_chapter: 目标释放章节（可选）
            related_expectations: 关联的期待ID（用于套娃式期待）
            
        Returns:
            期待ID
        """
        expectation_id = f"exp_{event_id}_{planting_chapter}"
        
        # 计算目标章节（如果未指定）
        rule = EXPECTATION_RULES.get(expectation_type)
        if not target_chapter and rule:
            target_chapter = planting_chapter + rule.min_chapters_before_release
        
        record = ExpectationRecord(
            id=expectation_id,
            expectation_type=expectation_type,
            status=ExpectationStatus.PLANTED,
            planted_chapter=planting_chapter,
            planting_description=description,
            target_chapter=target_chapter,
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
        
        self.logger.info(f"✅ 为事件 '{event_id}' 添加期待标签: {expectation_type.value} (第{planting_chapter}章种植, 计划第{target_chapter}章释放)")
        
        return expectation_id
    
    def pre_generation_check(self, chapter_num: int, event_context: Optional[Dict] = None) -> List[ExpectationConstraint]:
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
        pending_expectations = self._get_pending_expectations_for_chapter(chapter_num)
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
                    "套娃式：在满足旧期待的同时开启新期待"
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
        pending = self._get_pending_expectations_for_chapter(chapter_num)
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
    
    def _get_pending_expectations_for_chapter(self, chapter_num: int) -> List[str]:
        """获取本章待释放的期待"""
        pending = []
        for exp_id, exp_record in self.expectations.items():
            if (exp_record.status == ExpectationStatus.PLANTED and
                exp_record.target_chapter and
                exp_record.target_chapter <= chapter_num):
                pending.append(exp_id)
        return pending
    
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
    
    def generate_expectation_report(self, start_chapter: int = 1, end_chapter: Optional[int] = None) -> Dict:
        """
        生成期待感报告
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            
        Returns:
            期待感报告
        """
        if not end_chapter:
            end_chapter = max([exp.planted_chapter for exp in self.expectations.values()], default=1)
        
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
        satisfaction_rate = (released_expectations - failed_expectations) / released_expectations if released_expectations > 0 else 0
        
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
        
        if not type_counts.get("showcase"):
            recommendations.append("建议：增加'展示橱窗'类型的期待，提前展示奖励或能力的强大")
        
        if not type_counts.get("emotional_hook"):
            recommendations.append("建议：增加'情绪钩子'类型的期待，制造打脸或认同的期待")
        
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
                    "satisfaction_score": exp_record.satisfaction_score
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
                exp_record = ExpectationRecord(
                    id=exp_id,
                    expectation_type=ExpectationType(exp_data["type"]),
                    status=ExpectationStatus(exp_data["status"]),
                    planted_chapter=exp_data["planted_chapter"],
                    planting_description=exp_data["description"],
                    target_chapter=exp_data.get("target_chapter"),
                    released_chapter=exp_data.get("released_chapter"),
                    satisfaction_score=exp_data.get("satisfaction_score")
                )
                self.expectations[exp_id] = exp_record
        
        if "event_expectation_map" in data:
            self.event_expectation_map = data["event_expectation_map"]
        
        if "chapter_hooks" in data:
            self.chapter_hooks = data["chapter_hooks"]


# 集成到StagePlanManager的辅助类
class ExpectationIntegrator:
    """期待感集成器 - 将期待感管理集成到事件规划流程"""
    
    def __init__(self, expectation_manager: ExpectationManager):
        self.em = expectation_manager
        self.logger = get_logger("ExpectationIntegrator")
    
    def analyze_and_tag_events(self, major_events: List[Dict], stage_name: str,
                             api_client=None, novel_title: str = "") -> Dict:
        """
        使用AI分析事件并添加期待标签
        
        Args:
            major_events: 重大事件列表
            stage_name: 阶段名称
            api_client: API客户端（用于AI分析）
            novel_title: 小说标题
            
        Returns:
            分析结果
        """
        self.logger.info(f"🎯 开始为 {stage_name} 阶段的事件添加期待标签（AI智能分析）...")
        
        if not api_client:
            self.logger.warn("⚠️ 未提供API客户端，使用规则匹配作为后备方案")
            return self._analyze_and_tag_events_with_rules(major_events, stage_name)
        
        tagged_count = 0
        
        # 构建AI分析的prompt
        events_summary = []
        for i, event in enumerate(major_events, 1):
            event_summary = {
                "index": i,
                "name": event.get("name", "未知事件"),
                "chapter_range": event.get("chapter_range", ""),
                "main_goal": event.get("main_goal", ""),
                "role_in_stage_arc": event.get("role_in_stage_arc", ""),
                "emotional_focus": event.get("emotional_focus", ""),
                "description": event.get("description", "")
            }
            events_summary.append(event_summary)
        
        # 构建AI分析prompt
        analysis_prompt = f"""你是网文期待感策划专家。请分析以下{len(major_events)}个重大事件，为每个事件选择最合适的期待感类型。

# 期待感类型说明：
1. **showcase（展示橱窗）**: 提前展示奖励或能力的强大，让读者期待获得
2. **suppression_release（压抑释放）**: 制造阻碍，积累势能，最后释放带来爽感
3. **nested_doll（套娃期待）**: 大期待包着小期待，环环相扣
4. **emotional_hook（情绪钩子）**: 利用情绪期待（打脸、认同、身份揭秘）
5. **power_gap（实力差距）**: 展示实力差距，让读者期待变强
6. **mystery_foreshadow（伏笔揭秘）**: 埋下伏笔，让读者期待真相揭晓

# 小说信息：
- 小说标题: {novel_title}
- 阶段: {stage_name}

# 事件列表：
{json.dumps(events_summary, ensure_ascii=False, indent=2)}

# 任务：
请为每个事件分析并返回以下JSON格式：
{{
  "events": [
    {{
      "index": 1,
      "expectation_type": "showcase",
      "reasoning": "该事件涉及宝物发现，适合使用展示橱窗效应...",
      "planting_chapter": 10,
      "target_chapter": 15,
      "description": "主角获得神秘宝物的期待"
    }}
  ]
}}

请确保：
1. 期待类型与事件内容高度契合
2. 种植章节和目标章节合理（至少间隔3章）
3. 描述简洁有力，突出核心期待
"""
        
        try:
            # 调用AI分析
            self.logger.info(f"🤖 正在调用AI分析 {len(major_events)} 个事件...")
            
            result = api_client.generate_content_with_retry(
                content_type="expectation_analysis",
                user_prompt=analysis_prompt,
                purpose=f"为{stage_name}阶段的事件分析期待感类型"
            )
            
            if result and isinstance(result, dict) and "events" in result:
                # 解析AI返回的结果
                ai_events = result["events"]
                
                for ai_event in ai_events:
                    index = ai_event.get("index") - 1  # 转换为0-based索引
                    if 0 <= index < len(major_events):
                        event = major_events[index]
                        event_name = event.get("name", "未知事件")
                        
                        # 获取期待类型
                        exp_type_str = ai_event.get("expectation_type", "nested_doll")
                        try:
                            exp_type = ExpectationType(exp_type_str)
                        except ValueError:
                            exp_type = ExpectationType.NESTED_DOLL
                            self.logger.warn(f"⚠️ 未知的期待类型 '{exp_type_str}'，使用默认类型")
                        
                        # 种植期待
                        exp_id = self.em.tag_event_with_expectation(
                            event_id=event_name,
                            expectation_type=exp_type,
                            planting_chapter=ai_event.get("planting_chapter", 1),
                            description=ai_event.get("description", f"{event_name}的期待"),
                            target_chapter=ai_event.get("target_chapter")
                        )
                        
                        tagged_count += 1
                        reasoning = ai_event.get("reasoning", "")
                        self.logger.info(f"  ✓ AI为事件 '{event_name}' 选择期待类型: {exp_type.value}")
                        self.logger.info(f"    理由: {reasoning}")
                
                self.logger.info(f"✅ AI成功为 {tagged_count} 个事件生成期待感标签")
                
                return {
                    "tagged_count": tagged_count,
                    "expectation_summary": self.em.export_expectation_map(),
                    "analysis_method": "AI"
                }
            else:
                self.logger.warn("⚠️ AI分析失败，使用规则匹配作为后备方案")
                return self._analyze_and_tag_events_with_rules(major_events, stage_name)
                
        except Exception as e:
            self.logger.error(f"❌ AI分析出错: {e}")
            self.logger.info("使用规则匹配作为后备方案")
            return self._analyze_and_tag_events_with_rules(major_events, stage_name)
    
    def _analyze_and_tag_events_with_rules(self, major_events: List[Dict], stage_name: str) -> Dict:
        """
        使用规则匹配分析事件（后备方案）
        
        Args:
            major_events: 重大事件列表
            stage_name: 阶段名称
            
        Returns:
            分析结果
        """
        self.logger.info(f"🎯 使用规则匹配为 {stage_name} 阶段的事件添加期待标签...")
        
        tagged_count = 0
        for major_event in major_events:
            # 分析重大事件
            exp_id = self._analyze_and_tag_major_event(major_event, stage_name)
            if exp_id:
                tagged_count += 1
            
            # 分析中型事件
            composition = major_event.get("composition", {})
            for phase_events in composition.values():
                for medium_event in phase_events:
                    exp_id = self._analyze_and_tag_medium_event(medium_event, major_event, stage_name)
                    if exp_id:
                        tagged_count += 1
        
        self.logger.info(f"✅ 规则匹配为 {tagged_count} 个事件添加了期待标签")
        
        return {
            "tagged_count": tagged_count,
            "expectation_summary": self.em.export_expectation_map(),
            "analysis_method": "rules"
        }
    
    def _analyze_and_tag_major_event(self, event: Dict, stage_name: str) -> Optional[str]:
        """分析并标记重大事件"""
        event_name = event.get("name", "未知事件")
        chapter_range = event.get("chapter_range", "")
        
        # 解析章节范围
        from src.managers.StagePlanUtils import parse_chapter_range
        start_chapter, end_chapter = parse_chapter_range(chapter_range)
        
        # 根据事件目标判断期待类型
        main_goal = event.get("main_goal", "").lower()
        
        # 决策树：根据事件特征选择期待类型
        exp_type = None
        description = ""
        
        if "击败" in main_goal or "战胜" in main_goal or "复仇" in main_goal:
            exp_type = ExpectationType.SUPPRESSION_RELEASE
            description = f"主角击败{event_name}的期待"
        elif "获得" in main_goal or "得到" in main_goal or "炼成" in main_goal:
            exp_type = ExpectationType.SHOWCASE
            description = f"主角获得{event_name}中提到的宝物/能力的期待"
        elif "揭秘" in main_goal or "真相" in main_goal:
            exp_type = ExpectationType.MYSTERY_FORESHADOW
            description = f"{event_name}中的真相揭秘期待"
        else:
            # 默认使用套娃式期待
            exp_type = ExpectationType.NESTED_DOLL
            description = f"{event_name}的情节发展期待"
        
        # 添加期待标签
        exp_id = self.em.tag_event_with_expectation(
            event_id=event_name,
            expectation_type=exp_type,
            planting_chapter=start_chapter,
            description=description,
            target_chapter=end_chapter
        )
        
        self.logger.info(f"  ✓ 为重大事件 '{event_name}' 添加期待: {exp_type.value}")
        
        return exp_id
    
    def _analyze_and_tag_medium_event(self, medium_event: Dict, major_event: Dict, stage_name: str) -> Optional[str]:
        """分析并标记中型事件"""
        event_name = medium_event.get("name", "未知事件")
        chapter_range = medium_event.get("chapter_range", "")
        
        # 解析章节范围
        from src.managers.StagePlanUtils import parse_chapter_range
        start_chapter, end_chapter = parse_chapter_range(chapter_range)
        
        # 根据事件特征判断期待类型
        main_goal = medium_event.get("main_goal", "").lower()
        emotional_focus = medium_event.get("emotional_focus", "").lower()
        
        exp_type = None
        description = ""
        
        if "误解" in emotional_focus or "轻视" in emotional_focus or "震惊" in main_goal:
            exp_type = ExpectationType.EMOTIONAL_HOOK
            description = f"'{event_name}'中的打脸/认同期待"
        elif "展示" in main_goal or "学习" in main_goal:
            exp_type = ExpectationType.POWER_GAP
            description = f"主角在'{event_name}'中展示能力的期待"
        elif "伏笔" in main_goal or "线索" in main_goal:
            exp_type = ExpectationType.MYSTERY_FORESHADOW
            description = f"'{event_name}'中的伏笔期待"
        
        # 如果判断出期待类型，则添加标签
        if exp_type:
            exp_id = self.em.tag_event_with_expectation(
                event_id=event_name,
                expectation_type=exp_type,
                planting_chapter=start_chapter,
                description=description,
                target_chapter=end_chapter
            )
            
            self.logger.info(f"    ✓ 为中型事件 '{event_name}' 添加期待: {exp_type.value}")
            
            return exp_id
        
        return None