"""上下文管理器 - 防止Claude上下文长度超限"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class ContextManager:
    """管理生成过程中的上下文，防止无限累积导致Claude上下文超限"""

    def __init__(self, max_context_size: int = 50000):
        """
        初始化上下文管理器

        Args:
            max_context_size: 最大上下文大小（字符数），默认50000
        """
        self.max_context_size = max_context_size
        self.logger = None  # 会被外部设置

    def set_logger(self, logger):
        """设置logger"""
        self.logger = logger

    def cleanup_novel_data_context(self, novel_data: Dict, current_chapter: int) -> Dict:
        """
        清理novel_data中的累积数据，防止上下文超限

        Args:
            novel_data: 当前的novel_data字典
            current_chapter: 当前章节号

        Returns:
            清理后的novel_data
        """
        if self.logger:
            self.logger.info(f"🧹 开始清理第{current_chapter}章的上下文...")

        original_size = len(str(novel_data))

        # 1. 清理generated_chapters - 只保留最近几章的完整内容
        novel_data = self._cleanup_generated_chapters(novel_data, current_chapter)

        # 2. 清理事件上下文
        novel_data = self._cleanup_event_context(novel_data)

        # 3. 清理伏笔上下文
        novel_data = self._cleanup_foreshadowing_context(novel_data)

        # 4. 清理角色管理数据
        novel_data = self._cleanup_character_data(novel_data, current_chapter)

        # 5. 清理其他累积数据
        novel_data = self._cleanup_misc_data(novel_data)

        cleaned_size = len(str(novel_data))
        reduction = original_size - cleaned_size

        if self.logger:
            self.logger.info(f"  ✅ 上下文清理完成: {original_size:,} -> {cleaned_size:,} 字符")
            self.logger.info(f"  📉 减少了 {reduction:,} 字符 ({reduction/original_size*100:.1f}%)")

        return novel_data

    def _cleanup_generated_chapters(self, novel_data: Dict, current_chapter: int) -> Dict:
        """清理generated_chapters，只保留最近章节的完整内容"""
        if "generated_chapters" not in novel_data:
            return novel_data

        generated_chapters = novel_data["generated_chapters"]
        if not isinstance(generated_chapters, dict):
            return novel_data

        # 保留最近3章的完整内容，其他章节只保留摘要
        recent_chapters_to_keep = 3
        chapters_to_process = list(generated_chapters.keys())
        chapters_to_process.sort()

        cleaned_chapters = {}
        current_chapters_count = 0

        # 从后往前处理，优先保留最新章节
        for chapter_num in reversed(chapters_to_process):
            chapter_data = generated_chapters[chapter_num]

            if current_chapters_count < recent_chapters_to_keep:
                # 保留完整数据
                cleaned_chapters[chapter_num] = chapter_data
                current_chapters_count += 1
            else:
                # 只保留摘要信息
                cleaned_chapters[chapter_num] = {
                    "chapter_title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                    "word_count": chapter_data.get("word_count", 0),
                    "quality_score": chapter_data.get("quality_score", 0),
                    "next_chapter_hook": chapter_data.get("next_chapter_hook", ""),
                    "connection_to_previous": chapter_data.get("connection_to_previous", ""),
                    # 保留第一段内容作为基本参考
                    "content_preview": self._get_content_preview(chapter_data.get("content", "")),
                    # 标记为已清理
                    "_context_cleaned": True
                }

        novel_data["generated_chapters"] = cleaned_chapters
        return novel_data

    def _cleanup_event_context(self, novel_data: Dict) -> Dict:
        """清理事件上下文，只保留活跃事件"""
        # 清理事件驱动管理器的数据
        if hasattr(self, '_cleanup_event_manager'):
            novel_data = self._cleanup_event_manager(novel_data)
        return novel_data

    def _cleanup_foreshadowing_context(self, novel_data: Dict) -> Dict:
        """清理伏笔上下文，只保留未完成的伏笔"""
        # 清理伏笔管理器的数据
        if hasattr(self, '_cleanup_foreshadowing_manager'):
            novel_data = self._cleanup_foreshadowing_manager(novel_data)
        return novel_data

    def _cleanup_character_data(self, novel_data: Dict, current_chapter: int) -> Dict:
        """清理角色数据，移除不活跃的次要角色"""
        if "character_design" not in novel_data:
            return novel_data

        character_design = novel_data["character_design"]
        if not isinstance(character_design, dict):
            return novel_data

        # 保留主要角色和近期出现的角色
        main_characters = character_design.get("main_character", {})
        core_characters = character_design.get("core_characters", {})

        # 清理次要角色列表，只保留基本信息
        if "minor_characters" in character_design:
            minor_characters = character_design["minor_characters"]
            if isinstance(minor_characters, dict):
                cleaned_minor = {}
                for char_id, char_data in minor_characters.items():
                    if isinstance(char_data, dict):
                        # 只保留基本信息
                        cleaned_minor[char_id] = {
                            "name": char_data.get("name", char_id),
                            "role": char_data.get("role", "次要角色"),
                            "last_appearance": char_data.get("last_appearance", current_chapter),
                            "_minimal_info": True
                        }
                character_design["minor_characters"] = cleaned_minor

        novel_data["character_design"] = character_design
        return novel_data

    def _cleanup_misc_data(self, novel_data: Dict) -> Dict:
        """清理其他累积数据"""
        # 清理优化历史
        if "optimization_history" in novel_data:
            optimization_history = novel_data["optimization_history"]
            if isinstance(optimization_history, dict):
                # 每个章节只保留最近2次优化记录
                cleaned_history = {}
                for chapter_num, records in optimization_history.items():
                    if isinstance(records, list):
                        cleaned_history[chapter_num] = records[-2:]  # 只保留最近2条
                novel_data["optimization_history"] = cleaned_history

        # 清理临时缓存数据
        keys_to_remove = ["_temp_cache", "_generation_context", "_debug_info"]
        for key in keys_to_remove:
            if key in novel_data:
                del novel_data[key]

        return novel_data

    def _get_content_preview(self, content: str, max_length: int = 300) -> str:
        """获取内容预览"""
        if not content:
            return ""

        # 获取前300字符作为预览
        preview = content[:max_length]
        if len(content) > max_length:
            preview += "...[内容已清理，仅保留预览]"

        return preview

    def check_context_size(self, novel_data: Dict) -> bool:
        """
        检查上下文大小是否超过限制

        Args:
            novel_data: 要检查的数据

        Returns:
            True如果需要清理，False如果不需要
        """
        current_size = len(str(novel_data))
        return current_size > self.max_context_size

    def get_context_size_info(self, novel_data: Dict) -> Dict:
        """
        获取上下文大小信息

        Args:
            novel_data: 要分析的数据

        Returns:
            包含大小信息的字典
        """
        total_size = len(str(novel_data))

        # 分析各部分大小
        size_breakdown = {}
        for key, value in novel_data.items():
            if key != "generated_chapters":  # 这个单独处理
                size_breakdown[key] = len(str(value))

        # 特别处理generated_chapters
        if "generated_chapters" in novel_data:
            gc_size = len(str(novel_data["generated_chapters"]))
            size_breakdown["generated_chapters"] = gc_size

            # 统计章节数量
            chapter_count = len(novel_data["generated_chapters"])
            size_breakdown["chapter_count"] = chapter_count

        return {
            "total_size": total_size,
            "size_breakdown": size_breakdown,
            "needs_cleanup": total_size > self.max_context_size,
            "max_size": self.max_context_size,
            "usage_percentage": (total_size / self.max_context_size) * 100
        }


# 全局上下文管理器实例
context_manager = ContextManager()