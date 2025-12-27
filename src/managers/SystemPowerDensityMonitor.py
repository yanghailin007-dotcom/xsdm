"""
系统功率密度监控器 - 通用框架
适用于所有"系统流"小说（掠夺、签到、抽卡、升级等）

功能：
1. 生成前检查：判断当前章节是否必须触发系统
2. 生成后验证：检查是否符合密度要求
3. 自动修正：为下一章生成补偿性建议
"""

from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SystemType(Enum):
    """系统类型枚举"""
    LOOT_SYSTEM = "loot_system"  # 掠夺/掉落系统
    SIGN_IN_SYSTEM = "sign_in_system"  # 签到系统
    GACHA_SYSTEM = "gacha_system"  # 抽卡系统
    UPGRADE_SYSTEM = "upgrade_system"  # 升级系统
    COLLECTION_SYSTEM = "collection_system"  # 收集系统


@dataclass
class DensityRule:
    """密度规则配置"""
    system_type: SystemType
    name: str
    description: str
    target_frequency_per_10_chapters: float  # 每10章期望触发次数
    max_consecutive_chapters_without_trigger: int  # 最多连续不触发章节数
    must_show_result: bool  # 是否必须展示结果
    
    # 验证指标
    validation_metrics: List[str] = field(default_factory=list)


# 预定义的系统密度规则
SYSTEM_DENSITY_RULES = {
    SystemType.LOOT_SYSTEM: DensityRule(
        system_type=SystemType.LOOT_SYSTEM,
        name="掠夺/掉落系统",
        description="主角通过击杀敌人获得能力的系统",
        target_frequency_per_10_chapters=3.5,  # 每10章3-4次
        max_consecutive_chapters_without_trigger=3,  # 最多3章不掠夺
        must_show_result=True,
        validation_metrics=["loot_count", "loot_quality_score", "loot_variety"]
    ),
    SystemType.SIGN_IN_SYSTEM: DensityRule(
        system_type=SystemType.SIGN_IN_SYSTEM,
        name="签到系统",
        description="主角定期获得奖励的系统",
        target_frequency_per_10_chapters=2.0,  # 每10章2次
        max_consecutive_chapters_without_trigger=7,  # 最多7章不签到
        must_show_result=True,
        validation_metrics=["sign_in_count", "reward_value_score"]
    ),
    SystemType.GACHA_SYSTEM: DensityRule(
        system_type=SystemType.GACHA_SYSTEM,
        name="抽卡系统",
        description="主角通过抽卡获得能力的系统",
        target_frequency_per_10_chapters=1.0,  # 每10章1次
        max_consecutive_chapters_without_trigger=15,  # 最多15章不抽卡
        must_show_result=True,
        validation_metrics=["gacha_count", "rarity_distribution"]
    ),
    SystemType.UPGRADE_SYSTEM: DensityRule(
        system_type=SystemType.UPGRADE_SYSTEM,
        name="升级系统",
        description="主角通过升级变强的系统",
        target_frequency_per_10_chapters=2.5,  # 每10章2-3次
        max_consecutive_chapters_without_trigger=5,  # 最多5章不升级
        must_show_result=True,
        validation_metrics=["upgrade_count", "power_growth_rate"]
    ),
    SystemType.COLLECTION_SYSTEM: DensityRule(
        system_type=SystemType.COLLECTION_SYSTEM,
        name="收集系统",
        description="主角收集特定物品的系统",
        target_frequency_per_10_chapters=2.0,  # 每10章2次
        max_consecutive_chapters_without_trigger=6,  # 最多6章不收集
        must_show_result=True,
        validation_metrics=["collection_count", "collection_progress"]
    )
}


@dataclass
class TriggerRecord:
    """系统触发记录"""
    chapter: int
    triggered: bool
    target_name: Optional[str] = None
    reward_name: Optional[str] = None
    reward_quality: Optional[str] = None  # 金/紫/蓝/白
    reward_type: Optional[str] = None  # 体质类/技能类/物品类


@dataclass
class DensityConstraint:
    """密度约束"""
    type: str  # must_trigger, must_change_pace, must_meet_density
    urgency: str  # critical, high, medium, low
    message: str
    suggestions: List[str] = field(default_factory=list)


class SystemPowerDensityMonitor:
    """
    系统功率密度监控器
    
    使用示例：
    ```python
    monitor = SystemPowerDensityMonitor(
        system_type=SystemType.LOOT_SYSTEM,
        rule=SYSTEM_DENSITY_RULES[SystemType.LOOT_SYSTEM]
    )
    
    # 生成前检查
    constraints = monitor.pre_generation_check(chapter_num=21)
    if constraints:
        print("必须满足的约束：", constraints)
    
    # 生成后验证
    result = monitor.post_generation_validate(
        chapter_num=21,
        triggered=True,
        target_name="温天仁",
        reward_name="六极真魔体",
        reward_quality="紫"
    )
    ```
    """
    
    def __init__(self, system_type: SystemType, rule: Optional[DensityRule] = None):
        """
        初始化监控器
        
        Args:
            system_type: 系统类型
            rule: 密度规则，如果不提供则使用预定义规则
        """
        self.system_type = system_type
        self.rule = rule or SYSTEM_DENSITY_RULES.get(system_type)
        if not self.rule:
            raise ValueError(f"未找到系统类型 {system_type} 的密度规则")
        
        self.trigger_history: List[TriggerRecord] = []
        self.chapter_types: Dict[int, str] = {}  # 章节类型：combat, plot, dialogue等
    
    def pre_generation_check(self, chapter_num: int) -> List[DensityConstraint]:
        """
        生成前检查：返回必须执行的约束
        
        Args:
            chapter_num: 当前章节号
            
        Returns:
            约束列表
        """
        # 类型断言：self.rule在__init__中已确保非空
        assert self.rule is not None, "密度规则未初始化"
        
        constraints = []
        
        # 检查1：触发间隔
        chapters_since_trigger = self.get_chapters_since_last_trigger(chapter_num)
        if chapters_since_trigger >= self.rule.max_consecutive_chapters_without_trigger:
            target_hint = self.get_available_targets_hint()
            if isinstance(target_hint, list):
                target_hint = target_hint[0] if target_hint else "相关目标"
            
            constraints.append(DensityConstraint(
                type="must_trigger",
                urgency="critical",
                message=f"已{chapters_since_trigger}章未触发{self.rule.name}，本章必须触发！",
                suggestions=[
                    f"设计一个{self.rule.description}的情节",
                    f"目标选项：{target_hint}",
                    "触发方式：遭遇→击杀→触发→展示效果"
                ]
            ))
        
        # 检查2：最近10章密度
        trigger_count_10 = self.get_trigger_count_in_range(chapter_num - 10, chapter_num)
        expected = self.rule.target_frequency_per_10_chapters
        if trigger_count_10 < expected * 0.6:  # 低于期望的60%
            constraints.append(DensityConstraint(
                type="must_meet_density",
                urgency="high",
                message=f"最近10章仅触发{trigger_count_10}次{self.rule.name}（期望{expected}次），密度不足！",
                suggestions=[
                    "本章必须触发高价值目标",
                    "如果无法触发，必须在下一章开头补上"
                ]
            ))
        
        # 检查3：连续相同类型章节
        if self.system_type == SystemType.LOOT_SYSTEM:
            consecutive_combat = self.get_consecutive_chapter_type(chapter_num, "combat")
            if consecutive_combat >= 3:
                constraints.append(DensityConstraint(
                    type="must_change_pace",
                    urgency="high",
                    message=f"已连续{consecutive_combat}章战斗场景，必须切换节奏！",
                    suggestions=[
                        "选项A：触发后进入剧情推进（对话/布局/规划）",
                        "选项B：设计非战斗的触发（探险/发现/交易）",
                        "选项C：本章专注于展示触发后的效果和影响"
                    ]
                ))
        
        return constraints
    
    def post_generation_validate(  # type: ignore
        self,
        chapter_num: int,
        triggered: bool,
        target_name: Optional[str] = None,
        reward_name: Optional[str] = None,
        reward_quality: Optional[str] = None,
        reward_type: Optional[str] = None,
        chapter_type: Optional[str] = None
    ) -> Dict:
        """
        生成后验证：检查是否符合约束
        
        Args:
            chapter_num: 章节号
            triggered: 是否触发系统
            target_name: 目标名称
            reward_name: 奖励名称
            reward_quality: 奖励品质（金/紫/蓝/白）
            reward_type: 奖励类型（体质类/技能类/物品类）
            chapter_type: 章节类型
            
        Returns:
            验证结果
        """
        result = {
            "passed": True,
            "violations": [],
            "warnings": [],
            "recommendations": []
        }
        
        # 记录触发历史
        record = TriggerRecord(
            chapter=chapter_num,
            triggered=triggered,
            target_name=target_name,
            reward_name=reward_name,
            reward_quality=reward_quality,
            reward_type=reward_type
        )
        self.trigger_history.append(record)
        if chapter_type:
            self.chapter_types[chapter_num] = chapter_type
        
        # 获取生成前的约束
        constraints = self.pre_generation_check(chapter_num)
        
        # 类型断言：self.rule在__init__中已确保非空
        assert self.rule is not None, "密度规则未初始化"
        
        # 验证1：是否满足必须触发的要求
        for constraint in constraints:
            if constraint.type == "must_trigger" and not triggered:
                result["passed"] = False
                result["violations"].append({
                    "severity": "critical",
                    "message": f"违反约束：{constraint.message}",
                    "suggestions": constraint.suggestions
                })
                result["recommendations"].append(
                    "建议：立即重写本章，添加触发情节；或在下一章开头立即补上"
                )
        
        # 验证2：是否展示结果
        if triggered and self.rule.must_show_result and not reward_name:
            result["warnings"].append({
                "severity": "medium",
                "message": f"触发了{self.rule.name}但未展示具体奖励效果"
            })
            result["recommendations"].append(
                "建议：补充奖励的名称、品质和具体效果展示"
            )
        
        # 验证3：奖励质量
        if triggered and reward_quality:
            if reward_quality not in ["金", "紫", "蓝", "白", "橙", "红"]:
                result["warnings"].append({
                    "severity": "low",
                    "message": f"奖励品质'{reward_quality}'不在标准范围内"
                })
        
        return result
    
    def get_chapters_since_last_trigger(self, current_chapter: int) -> int:
        """获取距离上次触发的章节数"""
        for record in reversed(self.trigger_history):
            if record.triggered:
                return current_chapter - record.chapter
        return current_chapter  # 如果从未触发，返回当前章节数
    
    def get_trigger_count_in_range(self, start_chapter: int, end_chapter: int) -> int:
        """获取指定章节范围内的触发次数"""
        count = 0
        for record in self.trigger_history:
            if start_chapter <= record.chapter <= end_chapter and record.triggered:
                count += 1
        return count
    
    def get_consecutive_chapter_type(self, current_chapter: int, chapter_type: str) -> int:
        """获取连续相同类型章节的数量"""
        count = 0
        for i in range(current_chapter - 1, 0, -1):
            if self.chapter_types.get(i) == chapter_type:
                count += 1
            else:
                break
        return count
    
    def get_available_targets_hint(self) -> Union[str, List[str]]:
        """获取可用目标的提示（子类可重写）"""
        if self.system_type == SystemType.LOOT_SYSTEM:
            return ["原著反派/精英怪/BOSS", "携带高级词条的修士"]
        elif self.system_type == SystemType.SIGN_IN_SYSTEM:
            return "特殊地点/时间节点"
        elif self.system_type == SystemType.GACHA_SYSTEM:
            return "卡池/特殊抽卡机会"
        else:
            return "相关目标"
    
    def generate_density_report(self, start_chapter: int = 1, end_chapter: Optional[int] = None) -> Dict:  # type: ignore
        """
        生成密度报告
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节（默认为最新章节）
            
        Returns:
            密度报告
        """
        if not end_chapter:
            end_chapter = max([r.chapter for r in self.trigger_history], default=1)
        
        # 类型断言：self.rule在__init__中已确保非空
        assert self.rule is not None, "密度规则未初始化"
        
        total_chapters = end_chapter - start_chapter + 1
        trigger_records = [r for r in self.trigger_history if start_chapter <= r.chapter <= end_chapter]
        trigger_count = sum(1 for r in trigger_records if r.triggered)
        
        # 计算密度
        density_per_10_chapters = (trigger_count / total_chapters) * 10 if total_chapters > 0 else 0
        expected_density = self.rule.target_frequency_per_10_chapters
        density_score = min(100, int((density_per_10_chapters / expected_density) * 100))
        
        # 查找最大间隔
        max_gap = 0
        current_gap = 0
        for i in range(start_chapter, end_chapter + 1):
            record = next((r for r in trigger_records if r.chapter == i), None)
            if record and record.triggered:
                max_gap = max(max_gap, current_gap)
                current_gap = 0
            else:
                current_gap += 1
        max_gap = max(max_gap, current_gap)
        
        return {
            "system_type": self.system_type.value,
            "system_name": self.rule.name,
            "chapter_range": f"{start_chapter}-{end_chapter}",
            "total_chapters": total_chapters,
            "trigger_count": trigger_count,
            "density_per_10_chapters": round(density_per_10_chapters, 2),
            "expected_density": expected_density,
            "density_score": density_score,
            "max_gap_without_trigger": max_gap,
            "acceptable_gap": self.rule.max_consecutive_chapters_without_trigger,
            "issues": self._identify_issues(density_per_10_chapters, max_gap),
            "recommendations": self._generate_recommendations(density_per_10_chapters, max_gap)
        }
    
    def _identify_issues(self, density: float, max_gap: int) -> List[Dict]:  # type: ignore
        """识别问题"""
        issues = []
        
        # 类型断言：self.rule在__init__中已确保非空
        assert self.rule is not None, "密度规则未初始化"
        
        if density < self.rule.target_frequency_per_10_chapters * 0.6:
            issues.append({
                "severity": "high",
                "type": "low_density",
                "message": f"密度不足：实际{density:.1f}/10章，期望{self.rule.target_frequency_per_10_chapters}/10章"
            })
        
        if max_gap > self.rule.max_consecutive_chapters_without_trigger:
            issues.append({
                "severity": "critical",
                "type": "excessive_gap",
                "message": f"存在{max_gap}章连续未触发的区间（允许最大{self.rule.max_consecutive_chapters_without_trigger}章）"
            })
        
        return issues
    
    def _generate_recommendations(self, density: float, max_gap: int) -> List[str]:  # type: ignore
        """生成改进建议"""
        recommendations = []
        
        if density < self.rule.target_frequency_per_10_chapters * 0.6:
            recommendations.append(
                f"建议：提高{self.rule.name}的触发频率，目标为每{10/self.rule.target_frequency_per_10_chapters:.1f}章触发1次"
            )
        
        if max_gap > self.rule.max_consecutive_chapters_without_trigger:
            recommendations.append(
                f"建议：在超过{self.rule.max_consecutive_chapters_without_trigger}章未触发的区间中插入触发情节"
            )
        
        return recommendations


class LootSystemMonitor(SystemPowerDensityMonitor):
    """掠夺系统专用监控器"""
    
    def __init__(self):
        super().__init__(
            system_type=SystemType.LOOT_SYSTEM,
            rule=SYSTEM_DENSITY_RULES[SystemType.LOOT_SYSTEM]
        )
    
    def get_available_targets_hint(self) -> str:
        """获取可掠夺目标的提示"""
        return "原著反派（温天仁、慕兰神师、古魔等）、精英怪（阴冥兽王、变异鬼王等）、特殊NPC（携带高级词条的修士）"


# 使用示例
if __name__ == "__main__":
    # 创建掠夺系统监控器
    monitor = LootSystemMonitor()
    
    # 模拟前20章的触发记录
    monitor.post_generation_validate(
        chapter_num=2,
        triggered=True,
        target_name="温天仁",
        reward_name="六极真魔体",
        reward_quality="紫",
        reward_type="体质类",
        chapter_type="combat"
    )
    
    monitor.post_generation_validate(
        chapter_num=20,
        triggered=True,
        target_name="罗刹鬼王",
        reward_name="万魂统御",
        reward_quality="紫",
        reward_type="技能类",
        chapter_type="combat"
    )
    
    # 生成第21章前的检查
    print("=== 第21章生成前检查 ===")
    constraints = monitor.pre_generation_check(21)
    for constraint in constraints:
        print(f"[{constraint.urgency.upper()}] {constraint.message}")
        for suggestion in constraint.suggestions:
            print(f"  - {suggestion}")
    
    # 生成密度报告
    print("\n=== 密度报告（1-20章） ===")
    report = monitor.generate_density_report(1, 20)
    print(f"触发次数：{report['trigger_count']}/20章")
    print(f"密度：{report['density_per_10_chapters']}/10章（期望{report['expected_density']}/10章）")
    print(f"密度得分：{report['density_score']}/100")
    print(f"最大间隔：{report['max_gap_without_trigger']}章（允许{report['acceptable_gap']}章）")
    
    if report['issues']:
        print("\n发现问题：")
        for issue in report['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['message']}")
    
    if report['recommendations']:
        print("\n改进建议：")
        for rec in report['recommendations']:
            print(f"  - {rec}")