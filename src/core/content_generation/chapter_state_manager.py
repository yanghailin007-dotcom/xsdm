"""
章节状态管理器 - 负责章节间衔接状态的管理

用于解决章节之间的连贯性问题，通过结构化的结尾状态传递，
确保AI在生成新章节时能够准确衔接上一章的结尾状态。
"""
import json
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from src.utils.logger import get_logger


@dataclass
class ChapterEndState:
    """
    章节结尾状态 - 通用结构

    记录章节结束时的关键状态信息，用于下一章的开头衔接
    """
    chapter_number: int = 0

    # === 基础信息 ===
    time_point: str = ""          # 时间点（如：当晚子时、次日清晨、三日后）
    location: str = ""            # 地点
    atmosphere: str = ""           # 氛围基调（紧张/轻松/压抑/欢快/平静等）

    # === 角色状态 ===
    characters: List[Dict] = field(default_factory=list)
    # 每个角色包含：name, location, action, emotion, health

    # === 事件状态 ===
    current_event: str = ""       # 当前事件名称
    event_concluded: bool = False  # 事件是否完结

    # === 剧情状态 ===
    unresolved: List[str] = field(default_factory=list)  # 未解决的悬念/冲突
    hook: str = ""                # 结尾钩子/悬念

    # === 衔接提示 ===
    next_transition_hint: str = ""  # 给下一章的衔接建议（如：时间跳跃/直接继续/开启新事件）

    def to_prompt_context(self) -> str:
        """
        转换为提示词上下文格式
        用于下一章生成时的衔接场景要求
        """
        lines = [f"### 第{self.chapter_number}章结尾状态"]

        if self.time_point:
            lines.append(f"- **时间**：{self.time_point}")
        if self.location:
            lines.append(f"- **地点**：{self.location}")
        if self.atmosphere:
            lines.append(f"- **氛围**：{self.atmosphere}")

        if self.current_event:
            status = "已完结" if self.event_concluded else "进行中"
            lines.append(f"- **事件**：{self.current_event}（{status}）")

        if self.characters:
            lines.append("- **角色状态**：")
            for char in self.characters:
                char_info = f"  - {char.get('name', '')}"
                if char.get('location'):
                    char_info += f"在{char['location']}"
                if char.get('action'):
                    char_info += f"，{char['action']}"
                if char.get('emotion'):
                    char_info += f"，{char['emotion']}"
                lines.append(char_info)

        if self.unresolved:
            lines.append(f"- **未解决**：{', '.join(self.unresolved)}")

        if self.hook:
            lines.append(f"- **悬念**：{self.hook}")

        if self.next_transition_hint:
            lines.append(f"- **衔接建议**：{self.next_transition_hint}")

        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ChapterEndState':
        """从字典创建 ChapterEndState"""
        # 确保列表字段存在
        if 'characters' not in data:
            data['characters'] = []
        if 'unresolved' not in data:
            data['unresolved'] = []
        return cls(**data)

    def to_dict(self) -> Dict:
        """转为字典，用于序列化保存"""
        return asdict(self)

    def __str__(self) -> str:
        """字符串表示，用于日志"""
        return f"第{self.chapter_number}章结尾状态: {self.time_point} @ {self.location}"


class ChapterStateManager:
    """
    章节状态管理器

    负责存储和检索章节的结尾状态
    """

    def __init__(self, novel_title: str, api_client=None):
        self.logger = get_logger("ChapterStateManager")
        self.novel_title = novel_title
        self.api_client = api_client
        # 存储每章的结尾状态：{chapter_number: ChapterEndState}
        self._end_states: Dict[int, ChapterEndState] = {}

    def get_end_state(self, chapter_number: int) -> Optional[ChapterEndState]:
        """
        获取指定章节的结尾状态

        Args:
            chapter_number: 章节号

        Returns:
            章节结尾状态，如果不存在返回None
        """
        return self._end_states.get(chapter_number)

    def set_end_state(self, end_state: ChapterEndState):
        """
        保存章节的结尾状态

        Args:
            end_state: 章节结尾状态对象
        """
        self._end_states[end_state.chapter_number] = end_state
        self.logger.info(f"  📌 第{end_state.chapter_number}章结尾状态已保存: {end_state}")

    def get_previous_end_state(self, current_chapter: int) -> Optional[ChapterEndState]:
        """
        获取上一章的结尾状态

        Args:
            current_chapter: 当前章节号

        Returns:
            上一章的结尾状态，如果是第一章则返回None
        """
        if current_chapter <= 1:
            return None
        return self.get_end_state(current_chapter - 1)

    def build_default_end_state(self, chapter_number: int) -> ChapterEndState:
        """
        创建默认的结尾状态（当提取失败时使用）
        """
        return ChapterEndState(
            chapter_number=chapter_number,
            time_point="未知",
            location="未知",
            atmosphere="平静",
            characters=[],
            current_event="未知",
            event_concluded=True,
            unresolved=[],
            hook=""
        )

    def clear_all_states(self):
        """清空所有状态"""
        self._end_states.clear()
        self.logger.info("  🧹 已清空所有章节结尾状态")

    def get_all_states(self) -> Dict[int, ChapterEndState]:
        """获取所有已保存的结尾状态"""
        return self._end_states.copy()
