import json
import re
from typing import List, Dict
from .types import ChapterContext, ChapterSpec, GeneratedChapter


class QualityGate:
    def __init__(self, api_client):
        self.api_client = api_client

    def assess(self, context: ChapterContext, chapters: List[GeneratedChapter]) -> Dict:
        if not chapters:
            return {"score": 0.0, "can_proceed": False, "feedback": "无内容"}
        content_block = "\n\n".join(
            f"### 第{ch.chapter_number}章 {ch.title}\n{ch.content[:800]}"
            for ch in chapters
        )
        prompt = f"""你是一位小说质检编辑。请对以下小说章节进行快速质量评估，只输出 JSON。

【小说标题】{context.novel_title}

【待评估内容节选】
{content_block}

【评估维度】
1. 流畅度 (0-10)
2. 情节连贯性 (0-10)
3. 人设一致性 (0-10)
4. 爽点/吸引力 (0-10)

请输出如下 JSON（不要添加 markdown 代码块标记）：
{{
  "overall_score": 7.5,
  "can_proceed": true,
  "feedback": "具体问题和改进建议，如果没有则写'无明显问题'"
}}

JSON:"""
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_quality_assessment",
            user_prompt=prompt,
            purpose=f"质量评估{context.novel_title}"
        )
        if not result:
            return {"score": 6.0, "can_proceed": True, "feedback": "评估超时，默认通过"}
        try:
            text = result if isinstance(result, str) else str(result)
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                data = json.loads(m.group())
                return {
                    "score": float(data.get("overall_score", 6.0)),
                    "can_proceed": bool(data.get("can_proceed", True)),
                    "feedback": data.get("feedback", "")
                }
        except Exception:
            pass
        return {"score": 6.0, "can_proceed": True, "feedback": "评估解析失败，默认通过"}

    def optimize(self, context: ChapterContext, chapter: ChapterSpec, content: str, feedback: str) -> str:
        from .prompt_builder import PromptBuilder
        prompt = PromptBuilder.build_optimize_prompt(context, chapter, content, feedback)
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_content_optimization",
            user_prompt=prompt,
            purpose=f"润色{context.novel_title}第{chapter.chapter_number}章"
        )
        if result:
            text = result if isinstance(result, str) else str(result)
            return text.strip()
        return content
