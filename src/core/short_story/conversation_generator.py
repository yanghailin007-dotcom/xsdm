"""
短篇对话生成器
使用 ConversationSession 逐章生成短篇正文
"""

import re
import logging
from typing import Dict, Optional, List

from src.core.APIClient import ConversationSession
from .prompt_builder import ShortStoryPromptBuilder

logger = logging.getLogger(__name__)


class ShortStoryConversationGenerator:
    """短篇对话生成器"""
    
    # 每多少章强制重建 session，防止 token 过长
    SESSION_REBUILD_INTERVAL = 6
    
    def __init__(self, api_client, genre: str, session: ConversationSession = None):
        self.api_client = api_client
        self.genre = genre
        self.prompt_builder = ShortStoryPromptBuilder()
        self.session = session
        self.session_chapter_count = 0
        self.total_chapters_generated = 0
        self._own_session = session is None  # 标记是否由本类自行管理 session
        
    def generate_chapter(self, chapter_number: int, total_chapters: int,
                        blueprint: Dict, prev_summary: str = "",
                        character_states: Optional[Dict] = None) -> Dict:
        """
        生成单章内容
        """
        logger.info(f"[ShortStoryConvGen] 生成第 {chapter_number} 章")
        
        # 检查是否需要重建 session（仅当自行管理 session 时）
        if self._own_session and (self.session is None or self.session_chapter_count >= self.SESSION_REBUILD_INTERVAL):
            self._rebuild_session(prev_summary, character_states)
        
        prompt = self.prompt_builder.get_chapter_prompt(
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            blueprint=blueprint,
            prev_summary=prev_summary,
            character_states=character_states
        )
        
        purpose = f"short_story_chapter_{chapter_number}"
        response = self.session.send_message(prompt, purpose=purpose)
        
        if not response:
            raise ValueError(f"第 {chapter_number} 章生成失败：API 返回空")
        
        parsed = self._parse_chapter_response(response, chapter_number)
        self.session_chapter_count += 1
        self.total_chapters_generated += 1
        
        return parsed
    
    def _rebuild_session(self, prev_summary: str = "",
                        character_states: Optional[Dict] = None):
        """重建对话 session（仅在自行管理 session 时调用）"""
        if not self._own_session:
            logger.info("[ShortStoryConvGen] 外部传入 session，跳过内部重建")
            return
        
        system_prompt = self.prompt_builder.get_system_prompt(self.genre)
        
        # 如果已有生成历史，在 system prompt 中注入上下文摘要
        if prev_summary and self.total_chapters_generated > 0:
            context_injection = f"\n\n【前文摘要】\n{prev_summary}\n"
            if character_states:
                context_injection += "\n【当前人物状态】\n"
                for k, v in character_states.items():
                    context_injection += f"- {k}: {v}\n"
            system_prompt += context_injection
        
        self.session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=self.api_client.default_provider,
            purpose_prefix="ShortStory"
        )
        self.session.max_history = self.prompt_builder.get_max_history()
        self.session_chapter_count = 0
        
        logger.info(f"[ShortStoryConvGen] 重建 ConversationSession | genre={self.genre}")
    
    def _parse_chapter_response(self, response: str, chapter_number: int) -> Dict:
        """解析章节响应，提取标题、正文、摘要"""
        title = self._extract_section(response, "标题")
        content = self._extract_section(response, "正文")
        summary = self._extract_section(response, "摘要")
        
        # 如果没有找到明确的 section，尝试用正则提取第一行作为标题
        if not title:
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            if lines:
                title = lines[0]
                content = '\n'.join(lines[1:])
        
        word_count = len(content)
        
        return {
            "chapter_number": chapter_number,
            "title": title or f"第{chapter_number}章",
            "content": content,
            "summary": summary,
            "word_count": word_count
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取 ---章节名--- 和下一个 --- 之间的内容"""
        pattern = rf'---{section_name}---\s*(.*?)\s*(?=---|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def get_session_stats(self) -> Dict:
        """获取会话统计"""
        if self.session:
            return self.session.get_stats()
        return {"turn_count": 0}
