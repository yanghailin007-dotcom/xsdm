import re
from typing import List, Optional
from .types import ChapterContext, ChapterSpec, GeneratedChapter
from .prompt_builder import PromptBuilder


class ChapterContentGenerator:
    def __init__(self, api_client):
        self.api_client = api_client
        self.prompt_builder = PromptBuilder()

    def generate_batch(
        self,
        context: ChapterContext,
        chapters: List[ChapterSpec],
        previous_ending: str = ""
    ) -> List[GeneratedChapter]:
        prompt = self.prompt_builder.build_batch_prompt(context, chapters, previous_ending)
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_content_generation",
            user_prompt=prompt,
            purpose=f"批量生成{context.novel_title}第{chapters[0].chapter_number}-{chapters[-1].chapter_number}章"
        )
        if not result:
            return []
        raw_text = result if isinstance(result, str) else str(result)
        return self._parse_chapters(raw_text, chapters)

    def generate_single(
        self,
        context: ChapterContext,
        chapter: ChapterSpec,
        previous_ending: str = ""
    ) -> Optional[GeneratedChapter]:
        prompt = self.prompt_builder.build_single_prompt(context, chapter, previous_ending)
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_content_generation",
            user_prompt=prompt,
            purpose=f"生成{context.novel_title}第{chapter.chapter_number}章"
        )
        if not result:
            return None
        raw_text = result if isinstance(result, str) else str(result)
        parsed = self._parse_chapters(raw_text, [chapter])
        return parsed[0] if parsed else None

    def _parse_chapters(self, text: str, expected: List[ChapterSpec]) -> List[GeneratedChapter]:
        chapters = []
        # 优先匹配 --- 第N章 标题 --- 格式
        pattern = re.compile(
            r'---\s*第(\d+)章\s+(.*?)\s*---\n(.*?)'
            r'(?=(?:---\s*第\d+章\s+)|\Z)',
            re.DOTALL
        )
        matches = pattern.findall(text)
        if matches:
            for num_str, title, content in matches:
                num = int(num_str)
                content = content.strip()
                # 🔥 清理正文内部可能残留的标题行
                content = re.sub(r'^---\s*第\s*\d+\s*章\s+.*?---\s*\n?', '', content, flags=re.MULTILINE)
                content = re.sub(r'^第\s*\d+\s*章[：:\s]+.*?\n', '', content, flags=re.MULTILINE)
                chapters.append(GeneratedChapter(
                    chapter_number=num,
                    title=title.strip(),
                    content=content,
                    word_count=len(content)
                ))
        else:
            # fallback: 按 "第N章" 拆分段落
            parts = re.split(r'\n?\s*第\s*(\d+)\s*章[：:\s]', text)
            # parts[0] 是前文，parts[1]=num, parts[2]=content...
            idx_map = {spec.chapter_number: spec for spec in expected}
            for i in range(1, len(parts), 2):
                try:
                    num = int(parts[i])
                except ValueError:
                    continue
                content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                lines = content.split('\n', 1)
                title = lines[0].strip() if lines else ""
                body = lines[1].strip() if len(lines) > 1 else content
                # 如果没有提取到标题，用预期 spec 的标题
                spec = idx_map.get(num)
                if spec and not body:
                    body = content
                if spec and not title:
                    title = spec.title
                # 🔥 清理正文内部可能残留的标题行
                body = re.sub(r'^---\s*第\s*\d+\s*章\s+.*?---\s*\n?', '', body, flags=re.MULTILINE)
                body = re.sub(r'^第\s*\d+\s*章[：:\s]+.*?\n', '', body, flags=re.MULTILINE)
                chapters.append(GeneratedChapter(
                    chapter_number=num,
                    title=title,
                    content=body,
                    word_count=len(body)
                ))
        return chapters
