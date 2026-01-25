"""
章节状态管理器 - 负责章节间衔接状态的管理

用于解决章节之间的连贯性问题，通过结构化的结尾状态传递，
确保AI在生成新章节时能够准确衔接上一章的结尾状态。

新增：场景时间线追踪，防止相邻章节重复描写同一时间点的事件
"""
import json
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from src.utils.logger import get_logger
from datetime import datetime


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


# ==================== 场景时间线追踪系统 ====================

@dataclass
class SceneTimelineInfo:
    """
    场景时间线信息

    记录每个章节的时间覆盖范围，用于检测章节重复
    """
    chapter_number: int = 0

    # === 时间范围 ===
    start_time: str = ""           # 章节开始时间点（如：林家议事大厅，当日清晨）
    end_time: str = ""             # 章节结束时间点（如：林家议事大厅，紫气消散后）

    # === 关键事件序列 ===
    key_events: List[str] = field(default_factory=list)  # 本章发生的关键事件序列

    # === 场景摘要 ===
    scene_summary: str = ""        # 场景摘要，用于AI理解本章发生了什么

    # === 时间戳（用于排序）===
    time_index: int = 0            # 相对时间索引，数字越大表示越晚

    def to_prompt_context(self) -> str:
        """转换为提示词上下文"""
        lines = [f"### 第{self.chapter_number}章时间线信息"]
        if self.start_time:
            lines.append(f"- **开始时间**：{self.start_time}")
        if self.end_time:
            lines.append(f"- **结束时间**：{self.end_time}")
        if self.key_events:
            lines.append(f"- **关键事件序列**：")
            for i, event in enumerate(self.key_events, 1):
                lines.append(f"  {i}. {event}")
        if self.scene_summary:
            lines.append(f"- **场景摘要**：{self.scene_summary}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict) -> 'SceneTimelineInfo':
        """从字典创建 SceneTimelineInfo"""
        if 'key_events' not in data:
            data['key_events'] = []
        return cls(**data)

    def to_dict(self) -> Dict:
        """转为字典"""
        return asdict(self)


class SceneTimelineTracker:
    """
    场景时间线追踪器

    功能：
    1. 记录每章的时间覆盖范围
    2. 检测相邻章节是否有时间线重叠（重复描写）
    3. 生成时间连续性约束，传递给AI
    """

    def __init__(self, novel_title: str):
        self.logger = get_logger("SceneTimelineTracker")
        self.novel_title = novel_title
        # 存储每章的时间线信息：{chapter_number: SceneTimelineInfo}
        self._timeline: Dict[int, SceneTimelineInfo] = {}
        # 时间索引计数器
        self._next_time_index = 1

    def record_chapter_timeline(self, timeline_info: SceneTimelineInfo) -> None:
        """
        记录章节的时间线信息

        Args:
            timeline_info: 章节时间线信息
        """
        timeline_info.time_index = self._next_time_index
        self._next_time_index += 1
        self._timeline[timeline_info.chapter_number] = timeline_info
        self.logger.info(f"  📍 第{timeline_info.chapter_number}章时间线已记录: {timeline_info.start_time} → {timeline_info.end_time}")

    def get_timeline(self, chapter_number: int) -> Optional[SceneTimelineInfo]:
        """获取指定章节的时间线信息"""
        return self._timeline.get(chapter_number)

    def get_previous_timeline(self, current_chapter: int) -> Optional[SceneTimelineInfo]:
        """获取上一章的时间线信息"""
        if current_chapter <= 1:
            return None
        return self.get_timeline(current_chapter - 1)

    def check_timeline_continuity(self, current_chapter: int,
                                  current_start_time: str = "") -> Tuple[bool, str]:
        """
        检查当前章节与上一章的时间线是否连续

        Args:
            current_chapter: 当前章节号
            current_start_time: 当前章节计划开始的时间点

        Returns:
            (是否连续, 检查消息)
        """
        if current_chapter == 1:
            return True, "第一章，无需检查连续性"

        previous_timeline = self.get_previous_timeline(current_chapter)
        if not previous_timeline:
            return True, "上一章时间线未记录，跳过检查"

        # 如果没有提供当前开始时间，返回警告
        if not current_start_time:
            return True, "⚠️ 当前章节未提供开始时间，无法检测连续性"

        # 检查时间索引
        prev_index = previous_timeline.time_index
        curr_index = self._next_time_index

        # 简单检测：如果当前开始时间与上一章结束时间相同或更早，可能有重复
        has_overlap = (
            current_start_time == previous_timeline.end_time or
            current_start_time == previous_timeline.start_time or
            (current_start_time in previous_timeline.scene_summary and
             current_chapter - prev_index == 1)
        )

        if has_overlap:
            warning_msg = (
                f"⚠️ 检测到第{current_chapter}章可能与第{current_chapter-1}章存在时间线重叠！\n"
                f"   上一章范围: {previous_timeline.start_time} → {previous_timeline.end_time}\n"
                f"   本章开始: {current_start_time}\n"
                f"   建议：确保本章从 '{previous_timeline.end_time}' 之后的时间点开始"
            )
            self.logger.warn(warning_msg)
            return False, warning_msg

        info_msg = (
            f"✅ 时间线连续性检查通过\n"
            f"   上一章结束: {previous_timeline.end_time}\n"
            f"   本章开始: {current_start_time}"
        )
        return True, info_msg

    def build_timeline_constraint_for_generation(self, current_chapter: int) -> str:
        """
        为章节生成构建时间线约束提示词

        Args:
            current_chapter: 当前章节号

        Returns:
            时间线约束提示词
        """
        if current_chapter == 1:
            return "- **时间线要求**：这是第一章，建立故事的起始时间点。"

        previous_timeline = self.get_previous_timeline(current_chapter)
        if not previous_timeline:
            return "- **时间线要求**：未找到上一章时间线信息，请自然衔接。"

        constraint = f"""- **时间线铁律**：本章必须在上一章结束之后继续，严禁重复描写已写过的场景！
  - 上一章时间范围：{previous_timeline.start_time} → {previous_timeline.end_time}
  - 上一章关键事件：{'; '.join(previous_timeline.key_events[-3:])}  # 最近3个事件
  - **绝对禁止**：不要从 '{previous_timeline.start_time}' 或更早的时间点重新开始
  - **正确做法**：从 '{previous_timeline.end_time}' 之后的时间点继续故事，或进行时间跳跃"""

        return constraint

    def extract_timeline_from_chapter_content(self, chapter_number: int,
                                              chapter_content: str) -> Optional[SceneTimelineInfo]:
        """
        从生成的章节内容中提取时间线信息

        Args:
            chapter_number: 章节号
            chapter_content: 章节内容

        Returns:
            提取的时间线信息，如果提取失败返回None
        """
        import re

        # 尝试从内容中提取结尾状态（其中包含时间信息）
        # 查找 JSON 格式的结尾状态报告
        json_pattern = r'```json\s*(\{.*?"chapter_number"\s*:\s*' + str(chapter_number) + r'.*?\})\s*```'
        match = re.search(json_pattern, chapter_content, re.DOTALL)

        if not match:
            # 尝试查找不带代码块的JSON
            json_pattern2 = r'\{\s*"chapter_number"\s*:\s*' + str(chapter_number) + r'.*?"time_point".*?\}'
            match = re.search(json_pattern2, chapter_content, re.DOTALL)

        if match:
            try:
                import json
                # 扩展匹配范围以获取完整JSON
                start = match.start()
                brace_count = 0
                i = start
                while i < len(chapter_content):
                    if chapter_content[i] == '{':
                        brace_count += 1
                    elif chapter_content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_state = json.loads(chapter_content[start:i+1])
                            return self._convert_end_state_to_timeline(chapter_number, end_state)
                    i += 1
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warn(f"  ⚠️ 解析章节{chapter_number}的结尾状态失败: {e}")

        # 如果无法从JSON提取，使用简单的规则提取
        return self._simple_extract_timeline(chapter_number, chapter_content)

    def _convert_end_state_to_timeline(self, chapter_number: int,
                                       end_state: Dict) -> SceneTimelineInfo:
        """将结尾状态转换为时间线信息"""
        # 从上一章的时间线推断开始时间
        previous_timeline = self.get_previous_timeline(chapter_number)
        start_time = previous_timeline.end_time if previous_timeline else "故事开始"

        # 提取关键事件
        key_events = end_state.get("unresolved", [])  # 使用未解决的悬念作为关键事件
        current_event = end_state.get("current_event", "")
        if current_event:
            key_events.insert(0, current_event)

        return SceneTimelineInfo(
            chapter_number=chapter_number,
            start_time=start_time,
            end_time=end_state.get("time_point", "未知"),
            key_events=key_events[:5],  # 最多5个
            scene_summary=f"{end_state.get('location', '')} - {end_state.get('atmosphere', '')}"
        )

    def _simple_extract_timeline(self, chapter_number: int,
                                 content: str) -> SceneTimelineInfo:
        """简单的规则提取时间线信息"""
        # 提取前200字作为场景摘要
        summary = content[:200].replace('\n', ' ').strip() + "..."

        # 尝试从内容中找时间关键词
        time_keywords = ['清晨', '上午', '中午', '下午', '傍晚', '夜间', '子时', '次日',
                        '三天后', '半月后', '数日后', '片刻后', '片刻', '当即']
        found_time = "未知"
        for keyword in time_keywords:
            if keyword in content:
                found_time = keyword
                break

        previous_timeline = self.get_previous_timeline(chapter_number)
        start_time = previous_timeline.end_time if previous_timeline else found_time

        return SceneTimelineInfo(
            chapter_number=chapter_number,
            start_time=start_time,
            end_time=found_time,
            key_events=[f"本章结束于{found_time}"],
            scene_summary=summary[:100]
        )

    def validate_scene_time_progression(self, chapter_number: int, scenes: List[Dict]) -> Dict:
        """
        验证章节内场景的时间递进关系

        检测：
        1. 场景的 sequence 是否按顺序递增
        2. 场景的 role (起/承/转/合) 是否符合预期顺序
        3. 场景的 position 是否合理递进
        4. 是否有明显的时序问题（如高潮在开篇之后）

        Args:
            chapter_number: 章节号
            scenes: 场景列表

        Returns:
            {
                "is_valid": bool,
                "issues": List[Dict],
                "warnings": List[str],
                "scene_count": int
            }
        """
        issues = []
        warnings = []

        if not scenes:
            return {
                "is_valid": False,
                "issues": [{"type": "no_scenes", "message": "没有场景数据"}],
                "warnings": [],
                "scene_count": 0
            }

        # 检查 sequence 顺序
        expected_sequences = []
        actual_sequences = []
        role_order = {"起": 1, "承": 2, "转": 3, "合": 4}
        role_positions = {}

        for i, scene in enumerate(scenes):
            seq = scene.get("sequence", i + 1)
            actual_sequences.append(seq)
            expected_sequences.append(i + 1)

            # 检查 role 顺序
            role = scene.get("role", "")
            if role in role_order:
                if role in role_positions:
                    issues.append({
                        "type": "duplicate_role",
                        "scene": scene.get("name", "未命名"),
                        "role": role,
                        "message": f"场景 '{scene.get('name')}' 的 role '{role}' 与前面的场景重复"
                    })
                else:
                    role_positions[role] = i

            # 检查 position 的合理性
            position = scene.get("position", "")
            if position:
                # 检查是否有明显的时序问题
                if "ending" in position and i < len(scenes) - 1:
                    issues.append({
                        "type": "premature_ending",
                        "scene": scene.get("name", "未命名"),
                        "position": position,
                        "message": f"场景 '{scene.get('name')}' 的 position 是 'ending' 但不是最后一个场景"
                    })

        # 检查 sequence 是否连续
        if actual_sequences != expected_sequences:
            issues.append({
                "type": "sequence_mismatch",
                "expected": expected_sequences,
                "actual": actual_sequences,
                "message": f"场景 sequence 不连续: 期望 {expected_sequences}, 实际 {actual_sequences}"
            })

        # 检查 role 的递进关系
        sorted_roles = sorted(role_positions.items(), key=lambda x: x[1])
        role_values = [role_order[r] for r, _ in sorted_roles]

        # 检查 role 是否递增（允许部分缺失，但不能倒退）
        for i in range(len(role_values) - 1):
            if role_values[i] > role_values[i + 1]:
                issues.append({
                    "type": "role_regression",
                    "roles": [sorted_roles[i][0], sorted_roles[i + 1][0]],
                    "message": f"场景 role 倒退: '{sorted_roles[i][0]}' 在 '{sorted_roles[i + 1][0]}' 之后"
                })

        # 检查缺少的关键 role
        required_roles = {"起", "转"}  # 起和转是必须的
        missing_roles = required_roles - set(role_positions.keys())
        if missing_roles:
            warnings.append(f"缺少必要的 role: {missing_roles}")

        # 场景数量检查
        scene_count = len(scenes)
        if scene_count < 3:
            warnings.append(f"场景数量过少 ({scene_count}个)，建议4-6个")
        elif scene_count > 8:
            warnings.append(f"场景数量过多 ({scene_count}个)，可能导致节奏过快")

        is_valid = len(issues) == 0

        if not is_valid:
            self.logger.warn(f"  ⚠️ 第{chapter_number}章场景时间递进验证发现问题:")
            for issue in issues:
                self.logger.warn(f"     - {issue['message']}")
        else:
            self.logger.info(f"  ✅ 第{chapter_number}章场景时间递进验证通过")

        return {
            "is_valid": is_valid,
            "issues": issues,
            "warnings": warnings,
            "scene_count": scene_count
        }

    def get_all_timelines(self) -> Dict[int, SceneTimelineInfo]:
        """获取所有已记录的时间线"""
        return self._timeline.copy()

    def clear_all_timelines(self):
        """清空所有时间线记录"""
        self._timeline.clear()
        self._next_time_index = 1
        self.logger.info("  🧹 已清空所有场景时间线记录")
