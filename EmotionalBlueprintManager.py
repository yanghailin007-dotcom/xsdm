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
    # -------------------------------------------------------------
    # ▼▼▼ 修改开始：优化“四段式”模型的描述，明确“起承转合”的对应关系 ▼▼▼
    # -------------------------------------------------------------
    STRUCTURAL_MODELS = {
        "四段式": {
            "description": "将小说分为“起、承、转、合”四个经典阶段，为每个阶段设定一个清晰的情绪递进目标。",
            "stages": {
                "opening_stage": {
                    "name": "起 (开局阶段)",
                    "description_prompt": "string (开局阶段的情绪目标，例如：从极度压抑和屈辱，到获得一线希望的期待感)",
                    "start_emotion_prompt": "string (起始情绪，如：压抑/迷茫)",
                    "end_emotion_prompt": "string (结束情绪，如：期待/决心)"
                },
                "development_stage": {
                    "name": "承 (发展阶段)",
                    "description_prompt": "string (发展阶段的情绪目标，例如：在不断成长中体验友情与信任，但因背叛而陷入低谷，最终重新振作)",
                    "start_emotion_prompt": "string (起始情绪，如：成长喜悦)",
                    "end_emotion_prompt": "string (结束情绪，如：悲愤后的坚定)"
                },
                "climax_stage": {
                    "name": "转 (高潮阶段)",
                    "description_prompt": "string (高潮阶段的情绪目标，例如：将所有矛盾推向顶点，带来一场酣畅淋漓的情感大爆发与宣泄)",
                    "start_emotion_prompt": "string (起始情绪，如：决绝/紧张)",
                    "end_emotion_prompt": "string (结束情绪，如：宣泄/震撼)"
                },
                "ending_stage": {
                    "name": "合 (结局阶段)",
                    "description_prompt": "string (结局阶段的情绪目标，例如：解决所有遗憾，带来圆满的满足感和对角色未来的无限遐想)",
                    "start_emotion_prompt": "string (起始情绪，如：释然)",
                    "end_emotion_prompt": "string (结束情绪，如：圆满/感动)"
                }
            }
        },
    # -------------------------------------------------------------
    # ▲▲▲ 修改结束 ▲▲▲
    # -------------------------------------------------------------
        "三幕剧": {
            "description": "采用经典的三幕剧结构。第一幕用于建置，第二幕用于对抗，第三幕用于解决。这是一种强冲突、强节奏的结构。",
            "stages": {
                "act_one": {
                    "name": "第一幕：建置 (Setup)",
                    "description_prompt": "string (第一幕目标：建立主角的日常生活，引入核心冲突，并以一个无法回头的激励事件（Inciting Incident）结束)",
                    "start_emotion_prompt": "string (起始情绪，如：平静/不安)",
                    "end_emotion_prompt": "string (结束情绪，如：决心/被迫行动)"
                },
                "act_two": {
                    "name": "第二幕：对抗 (Confrontation)",
                    "description_prompt": "string (第二幕目标：主角在新环境中面对不断升级的障碍和冲突，经历一系列的尝试与失败，直到中点危机（Midpoint Crisis），最终在第二幕结尾达到最低谷)",
                    "start_emotion_prompt": "string (起始情绪，如：挣扎/希望)",
                    "end_emotion_prompt": "string (结束情绪，如：绝望/破釜沉舟)"
                },
                "act_three": {
                    "name": "第三幕：解决 (Resolution)",
                    "description_prompt": "string (第三幕目标：主角从最低谷奋起反击，迎来最终高潮（Climax），解决核心矛盾，并展示其蜕变后的新状态)",
                    "start_emotion_prompt": "string (起始情绪，如：决一死战)",
                    "end_emotion_prompt": "string (结束情绪，如：新生/释然)"
                }
            }
        }
    }


    # BUG 修复：将构造函数的参数名从 'generator' 修改为 'novel_generator'
    def __init__(self, novel_generator: NovelGenerator):
        self.generator = novel_generator
        self.api_client = novel_generator.api_client

    def generate_emotional_blueprint(self, novel_title: str, novel_synopsis: str, creative_seed: str, structural_model: str = "四段式") -> Optional[Dict]:
        """
        生成全书的情绪蓝图 (Emotional Blueprint)。

        Args:
            novel_title: 小说标题
            novel_synopsis: 小说简介
            creative_seed: 创意种子
            structural_model: 结构模型，可选 "四段式" 或 "三幕剧"

        Returns:
            一个包含情绪蓝图的字典，或在失败时返回 None。
        """
        print(f"🎭 正在绘制全书情绪蓝图 (结构模型: {structural_model})...")
        prompt = self._build_blueprint_prompt(novel_title, novel_synopsis, creative_seed, structural_model)

        blueprint = self.generator.api_client.generate_content_with_retry(
            "emotional_blueprint_generation",
            prompt,
            purpose="生成全书情绪蓝图"
        )

        if blueprint and "emotional_spectrum" in blueprint and "stage_emotional_arcs" in blueprint:
            print("✅ 全书情绪蓝图绘制完成。")
            print(f"   - 核心情感光谱: {', '.join(blueprint.get('emotional_spectrum', []))}")
            self.generator.novel_data["emotional_blueprint"] = blueprint
            # TODO: 在此可以增加对各阶段情绪逻辑连贯性的验证
            return blueprint
        else:
            print("❌ 全书情绪蓝图生成失败。")
            return None

    def _build_blueprint_prompt(self, novel_title: str, novel_synopsis: str, creative_seed: str, structural_model: str) -> str:
        """构建情绪蓝图生成的提示词"""
        # 选择结构模型，如果指定的模型不存在，则默认使用“四段式”
        model = self.STRUCTURAL_MODELS.get(structural_model, self.STRUCTURAL_MODELS["四段式"])
        model_description = model['description']
        stages = model['stages']

        # 动态构建 stage_emotional_arcs 的 JSON 字符串
        stage_arc_parts = []
        for stage_key, stage_info in stages.items():
            part = f"""
            "{stage_key}": {{
                "description": "{stage_info['description_prompt']}",
                "start_emotion": "{stage_info['start_emotion_prompt']}",
                "end_emotion": "{stage_info['end_emotion_prompt']}"
            }}"""
            stage_arc_parts.append(part)
        
        stage_arcs_json_string = ",\n".join(stage_arc_parts)

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
2.  **规划分阶段情绪弧线 (Stage Emotional Arcs)**: 你将采用 **【{structural_model}】** 结构。{model_description}

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
{stage_arcs_json_string}
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
