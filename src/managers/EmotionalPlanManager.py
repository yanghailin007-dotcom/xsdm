# EmotionalPlanManager.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import re
from typing import Dict, Optional, List
from src.utils.logger import get_logger

class EmotionalPlanManager:
    """
    情绪计划管理器 - 负责将高阶的“情绪蓝图”战术性地分解到各个阶段和章节。
    """
    # BUG 修复：将构造函数的参数名从 'generator' 修改为 'novel_generator'
    def __init__(self, novel_generator):
        self.logger = get_logger("EmotionalPlanManager")
        self.generator = novel_generator

    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, emotional_blueprint: Dict) -> Dict:
        """
        根据情绪蓝图，为指定阶段生成详细的情绪执行计划。

        Args:
            stage_name: 阶段名称 (e.g., "opening_stage")
            stage_range: 章节范围 (e.g., "1-30")
            emotional_blueprint: 全书的情绪蓝图

        Returns:
            该阶段的详细情绪计划。
        """
        self.logger.info(f"   💖 正在为 {stage_name} 规划详细情绪节奏...")
        stage_arc = emotional_blueprint.get("stage_emotional_arcs", {}).get(stage_name)
        if not stage_arc:
            self.logger.info(f"      ⚠️ 在情绪蓝图中未找到 {stage_name} 的情绪弧线定义。")
            return {}

        emotional_spectrum = emotional_blueprint.get("emotional_spectrum", [])
        prompt = self._build_stage_plan_prompt(stage_name, stage_range, stage_arc, emotional_spectrum)

        plan = self.generator.api_client.generate_content_with_retry(
            "stage_emotional_planning",
            prompt,
            purpose=f"生成{stage_name}情绪计划"
        )
        
        if plan and "emotional_segments" in plan:
            self.logger.info(f"   ✅ {stage_name} 情绪节奏规划完成。")
            return plan
        return {}

    def _build_stage_plan_prompt(self, stage_name: str, stage_range: str, stage_arc: Dict, emotional_spectrum: List[str]) -> str:
        stage_arc_desc = stage_arc.get('description', '情绪发展')
        return f"""
# 角色：金牌网文编辑，情绪节奏大师

# 核心任务
为小说的一个大的阶段（{stage_range}），设计一个具体、可执行的【情绪节奏方案】。你需要将抽象的情绪目标，拆解成若干个情绪小节，并为每个小节分配章节范围和核心任务。

# 战略输入
- **当前阶段**: {stage_name}
- **章节范围**: {stage_range}
- **本阶段核心情绪目标**: {stage_arc_desc}
- **全书核心情感光谱**: {', '.join(emotional_spectrum)}

# 工作要求
1.  将本阶段 ({stage_range}) 分为3-5个【情绪分段】(Emotional Segments)。
2.  每个分段都要有一个明确的【情绪关键词】（从情感光谱中选取或创造更具体的，如'初露锋芒的爽感'、'失去挚友的悲痛'）。
3.  为每个分段规划【核心情绪任务】，即通过什么类型的事件来达成该情绪。

# 输出格式 (严格JSON)
{{
    "stage_name": "{stage_name}",
    "main_emotional_arc": "{stage_arc_desc}",
    "emotional_segments": [
        {{
            "segment_name": "string (情绪分段的名称，例如：压抑与铺垫期)",
            "chapter_range": "string (该分段的章节范围，例如：1-8章)",
            "target_emotion_keyword": "string (本分段的核心情绪关键词，例如：压抑/屈辱)",
            "core_emotional_task": "string (如何达成该情绪，例如：通过描述主角被家族抛弃、受人欺凌、实力低微的困境，累积读者的负面情绪，为后续爆发做铺垫。)"
        }},
        {{
            "segment_name": "string (例如：初获奇遇，希望萌生)",
            "chapter_range": "string (例如：9-15章)",
            "target_emotion_keyword": "string (例如：惊喜/期待)",
            "core_emotional_task": "string (例如：主角意外获得金手指，实力得到初步提升，解决了一个小危机，让读者看到翻盘的希望，产生追读的期待感。)"
        }},
        {{
            "segment_name": "string (例如：小试牛刀，扬眉吐气)",
            "chapter_range": "string (例如：16-30章)",
            "target_emotion_keyword": "string (例如：扬眉吐气/爽感)",
            "core_emotional_task": "string (例如：主角利用新能力在一次小型比试中打败了曾经欺辱他的人，完成了开篇的第一个小目标，释放了前期积累的压抑情绪，给予读者强烈的满足感。)"
        }}
    ]
}}
"""

    def get_emotional_guidance_for_chapter(self, chapter_number: int, stage_emotional_plan: Dict) -> Dict:
        """为单个章节获取精确的情绪指导"""
        if not stage_emotional_plan or "emotional_segments" not in stage_emotional_plan:
            return {"error": "阶段性情绪计划无效"}

        for segment in stage_emotional_plan.get("emotional_segments", []):
            try:
                start_chap, end_chap = map(int, re.findall(r'\d+', segment.get("chapter_range", "0-0")))
                if start_chap <= chapter_number <= end_chap:
                    return {
                        "target_emotion_keyword": segment.get("target_emotion_keyword", "无特定情绪"),
                        "core_emotional_task": segment.get("core_emotional_task", "常规情节推进"),
                        "segment_name": segment.get("segment_name", "未知分段"),
                        "source_plan": "EmotionalPlanManager"
                    }
            except Exception:
                continue
        
        return {"target_emotion_keyword": "过渡章节", "core_emotional_task": "承上启下，平稳过渡情绪。"}
