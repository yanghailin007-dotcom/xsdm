# EmotionalBlueprintManager.py
import json
from typing import Dict, Optional

import NovelGenerator

class EmotionalBlueprintManager:
    """
    情绪蓝图管理器
    负责在小说创作初期，定义全书的情感基调、情绪光谱和分阶段的情绪发展弧线。
    这是整个“情绪引导艺术”的最高战略规划。
    """
    # BUG 修复：将构造函数的参数名从 'generator' 修改为 'novel_generator'
    def __init__(self, novel_generator: NovelGenerator):
        self.generator = novel_generator
        self.api_client = novel_generator.api_client

    def generate_emotional_blueprint(self, novel_title: str, novel_synopsis: str, creative_seed: str) -> Optional[Dict]:
        """
        生成全书的情绪蓝图 (Emotional Blueprint)。

        Args:
            novel_title: 小说标题
            novel_synopsis: 小说简介
            creative_seed: 创意种子

        Returns:
            一个包含情绪蓝图的字典，或在失败时返回 None。
        """
        print("🎭 正在绘制全书情绪蓝图...")
        prompt = self._build_blueprint_prompt(novel_title, novel_synopsis, creative_seed)

        blueprint = self.generator.api_client.generate_content_with_retry(
            "emotional_blueprint_generation",
            prompt,
            purpose="生成全书情绪蓝图"
        )

        if blueprint and "emotional_spectrum" in blueprint and "stage_emotional_arcs" in blueprint:
            print("✅ 全书情绪蓝图绘制完成。")
            print(f"   - 核心情感光谱: {', '.join(blueprint.get('emotional_spectrum', []))}")
            self.generator.novel_data["emotional_blueprint"] = blueprint
            return blueprint
        else:
            print("❌ 全书情绪蓝图生成失败。")
            return None

    def _build_blueprint_prompt(self, novel_title: str, novel_synopsis: str, creative_seed: str) -> str:
        """构建情绪蓝图生成的提示词"""
        return f"""
# 角色：顶级的网文主编与读者心理分析师

# 核心任务
你的任务是基于小说的核心设定，设计一个引人入胜、让读者欲罢不能的【全书情绪发展蓝图】。你要规划的不是具体情节，而是读者在阅读不同阶段应该体验到的核心情绪流。

# 小说核心信息
- **书名**: {novel_title}
- **简介**: {novel_synopsis}
- **创意种子**: {creative_seed}

# 工作流程
1.  **定义情感光谱 (Emotional Spectrum)**: 这本小说除了常见的“爽”，核心情感驱动力是什么？是复仇的宣泄感？是兄弟情的热血？是对抗命运的悲壮？是探索未知的敬畏？还是守护温情的感动？请提炼出3-5个最核心的情绪关键词。
2.  **规划分阶段情绪弧线 (Stage Emotional Arcs)**: 将小说分为开局、发展、高潮、结局四个阶段，为每个阶段设定一个清晰的情绪递进目标。

# 输出规则
你必须返回一个严格的JSON对象。

## JSON结构定义：
{{
    "overall_emotional_tone": "string (用一句话概括全书的情感基调，例如：在绝望中寻找希望的悲壮史诗、热血豪迈的兄弟情谊与成长、轻松诙谐下的暗流涌动)",
    "emotional_spectrum": [
        "string (核心情绪1，例如：复仇宣泄感)",
        "string (核心情绪2，例如：守护温情)",
        "string (核心情绪3，例如：兄弟情谊)",
        "string (核心情绪4，例如：探索神秘)"
    ],
    "stage_emotional_arcs": {{
        "opening_stage": {{
            "description": "string (开局阶段的情绪目标，例如：从极度压抑和屈辱，到获得一线希望的期待感)",
            "start_emotion": "string (起始情绪，如：压抑/迷茫)",
            "end_emotion": "string (结束情绪，如：期待/决心)"
        }},
        "development_stage": {{
            "description": "string (发展阶段的情绪目标，例如：在不断成长中体验友情与信任，但因背叛而陷入低谷，最终重新振作)",
            "start_emotion": "string (起始情绪，如：成长喜悦)",
            "end_emotion": "string (结束情绪，如：悲愤后的坚定)"
        }},
        "climax_stage": {{
            "description": "string (高潮阶段的情绪目标，例如：将所有矛盾推向顶点，带来一场酣畅淋漓的情感大爆发与宣泄)",
            "start_emotion": "string (起始情绪，如：决绝/紧张)",
            "end_emotion": "string (结束情绪，如：宣泄/震撼)"
        }},
        "ending_stage": {{
            "description": "string (结局阶段的情绪目标，例如：解决所有遗憾，带来圆满的满足感和对角色未来的无限遐想)",
            "start_emotion": "string (起始情绪，如：释然)",
            "end_emotion": "string (结束情绪，如：圆满/感动)"
        }}
    }},
    "key_emotional_turning_points": [
        {{
            "approx_chapter_percent": "number (大约在全书百分之几的位置，如 25)",
            "description": "string (关键情绪转折点描述，例如：主角被最信任的兄弟背叛，情感基调由信任转为怀疑与痛苦)"
        }},
        {{
            "approx_chapter_percent": "number (例如：70)",
            "description": "string (例如：主角放下仇恨，为守护更重要的东西而战，情感基调由复仇升华为守护)"
        }}
    ]
}}
"""
