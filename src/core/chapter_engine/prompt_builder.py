from typing import List
from .types import ChapterContext, ChapterSpec


class PromptBuilder:
    @staticmethod
    def build_batch_prompt(
        context: ChapterContext,
        chapters: List[ChapterSpec],
        previous_ending: str = ""
    ) -> str:
        specs_text = []
        for ch in chapters:
            specs_text.append(
                f"### 第{ch.chapter_number}章 {ch.title}\n"
                f"{ch.outline}\n"
            )
        specs_block = "\n\n".join(specs_text)

        golden_hint = ""
        if any(ch.is_golden_chapter for ch in chapters):
            golden_hint = (
                "\n【特别注意】本批次包含小说开篇章节（前3章），请务必：\n"
                "- 第一章在300字内出现主角，1000字内出现第一个小冲突或爽点；\n"
                "- 三章内完成世界观初步展示 + 主角核心动机/金手指揭示；\n"
                "- 节奏要快，禁止大段环境描写和设定说明。\n"
            )

        prompt = f"""你是一位顶尖的网络小说作家。请根据以下信息，一次性生成 {len(chapters)} 章小说正文。

【小说标题】{context.novel_title}

【核心设定】
{context.core_setting}

【世界观】
{context.worldview}

【角色设定】
{context.characters}

【文风要求】
{context.writing_style}

【前文摘要/衔接】
{context.previous_summary or "无"}

{golden_hint}

【逐章细纲】
{specs_block}

【输出格式要求】
请严格按照以下格式输出，每一章必须包含明确的标题和正文：

--- 第N章 标题 ---
（本章正文，字数要求 {context.word_count_min}-{context.word_count_max} 字）

注意：
1. 禁止输出任何与正文无关的总结、分析、说明文字。
2. 每一章内容要情节连贯，人物行为符合设定。
3. 章节之间要有自然的起承转合。
"""
        if previous_ending:
            prompt += f"\n【上一批次结尾片段】\n{previous_ending}\n"
        return prompt

    @staticmethod
    def build_single_prompt(
        context: ChapterContext,
        chapter: ChapterSpec,
        previous_ending: str = ""
    ) -> str:
        return PromptBuilder.build_batch_prompt(context, [chapter], previous_ending)

    @staticmethod
    def build_optimize_prompt(
        context: ChapterContext,
        chapter: ChapterSpec,
        original_content: str,
        feedback: str
    ) -> str:
        return f"""你是一位小说润色专家。请根据以下反馈，对指定章节进行优化改写，保持原意但提升质量。

【小说标题】{context.novel_title}
【文风要求】{context.writing_style}

【章节信息】第{chapter.chapter_number}章 {chapter.title}
【细纲】{chapter.outline}

【待优化原文】
{original_content}

【优化反馈】
{feedback}

【输出要求】
直接输出优化后的完整章节正文，不要添加任何解释、总结或格式外的内容。字数保持在 {context.word_count_min}-{context.word_count_max} 字之间。
"""
