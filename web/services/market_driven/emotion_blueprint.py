"""
情绪蓝图系统
只给AI情绪约束，不给具体情节，让AI自由创作
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PhaseRequirements:
    """阶段要求"""
    chapters: str
    emotion_arc: str
    must_have: List[str]
    intensity_range: tuple
    climax_type: str
    creative_hints: Dict[str, str] = field(default_factory=dict)


class EmotionBlueprint:
    """情绪蓝图 - 定义情绪轨迹但不限制具体情节"""
    
    DEFAULT_GUOYUN = {
        "phase_1": PhaseRequirements(
            chapters="1-3",
            emotion_arc="压抑→震惊→希望",
            must_have=["极端困境", "系统觉醒", "第一个小爽点"],
            intensity_range=(8, 10),
            climax_type="钩子章",
            creative_hints={"opening": "任意困境", "system": "任意系统类型"}
        ),
        "phase_2": PhaseRequirements(
            chapters="4-10",
            emotion_arc="积累→爆发→满足",
            must_have=["连续打脸", "能力成长", "首次震惊全场"],
            intensity_range=(7, 9),
            climax_type="小高潮密集",
            creative_hints={"enemies": "任意敌人组合", "progression": "能力进度10%-30%"}
        ),
        "phase_3": PhaseRequirements(
            chapters="11-20",
            emotion_arc="平静→危机→突破",
            must_have=["新地图", "新敌人", "队友成长", "2-3次中爽点"],
            intensity_range=(6, 8),
            climax_type="铺垫+中爽点",
            creative_hints={"map": "任意地形", "forces": "任意组织"}
        ),
        "phase_4": PhaseRequirements(
            chapters="21-30",
            emotion_arc="绝望→逆转→炸裂→余波",
            must_have=["绝境<10%生存率", "国际联盟3国+", "濒死突破", "国运级奖励"],
            intensity_range=(9, 10),
            climax_type="大高潮",
            creative_hints={
                "boss_type": "任意类型（神话/机械/外星等）",
                "enemy_alliance": "任意国家组合",
                "breakthrough": "任意突破方式",
                "reward": "能源/科技/军事/民生等任意类型"
            }
        )
    }
    
    def __init__(self):
        self.phases = self.DEFAULT_GUOYUN
    
    def get_phase_for_chapter(self, chapter_num: int) -> Optional[PhaseRequirements]:
        """获取章节所属阶段"""
        for phase in self.phases.values():
            if '-' in phase.chapters:
                start, end = map(int, phase.chapters.split('-'))
                if start <= chapter_num <= end:
                    return phase
        return None
    
    def build_constraint_prompt(self, chapter_num: int) -> str:
        """构建约束提示词"""
        phase = self.get_phase_for_chapter(chapter_num)
        if not phase:
            return ""
        
        lines = [
            "\n【情绪蓝图约束 - 必须遵循】",
            f"阶段：第{phase.chapters}章 | 类型：{phase.climax_type}",
            f"情绪弧：{phase.emotion_arc}",
            f"强度：{phase.intensity_range[0]}-{phase.intensity_range[1]}/10",
            "",
            "【必须完成的爽点清单】",
        ]
        for i, item in enumerate(phase.must_have, 1):
            lines.append(f"{i}. {item}")
        
        if phase.creative_hints:
            lines.extend(["", "【创作自由 - AI自由发挥】"])
            for key, hint in phase.creative_hints.items():
                lines.append(f"  • {key}: {hint}")
        
        lines.extend([
            "",
            "【约束规则】",
            "✅ 必须完成所有爽点清单",
            "✅ 情绪强度符合要求",
            "❌ 不要套路化（避免读者猜到结局）",
            "🎯 目标：让读者猜不到下一章！",
            ""
        ])
        return "\n".join(lines)


def get_default_blueprint():
    return EmotionBlueprint()
