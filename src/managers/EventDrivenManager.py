# EventDrivenManager.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from typing import Any, Dict, List, Optional
import re
from src.utils.logger import get_logger
class EventDrivenManager:
    """事件执行器 - 专注重大事件和中型事件的状态跟踪和执行"""
    def __init__(self, novel_generator):
        self.logger = get_logger("EventDrivenManager")
        self.generator = novel_generator
        self.active_events = {}  # 活跃的重大事件和中型事件
        self.event_history = []  # 已完成的事件历史
        self.event_triggers = {}  # 事件触发条件
    def update_from_stage_plan(self, stage_writing_plan: Dict):
        """从阶段写作计划中加载事件系统 - 简化版本，只处理重大事件和中型事件"""
        if not stage_writing_plan:
            return
        # 只处理重大事件和大事件
        event_system = stage_writing_plan.get("event_system", {})
        # 初始化活跃事件
        self._initialize_active_events(event_system)
        # 设置事件触发条件
        self._setup_event_triggers(event_system)
        self.logger.info(f"✓ 事件执行器已从阶段计划更新: {len(self.active_events)}个活跃事件")
    def get_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文 - 统一入口方法（支持分层上下文）"""
        original_context = self.get_chapter_event_context(chapter_number)
        # 🆕 应用分层上下文压缩
        from src.utils.LayeredContextManager import LayeredContextManager
        context_manager = LayeredContextManager()
        # 获取当前章节的事件历史，用于分层压缩
        compressed_context = {}
        # 对历史事件进行分层压缩
        if "active_events" in original_context:
            compressed_active_events = []
            for event in original_context["active_events"]:
                event_chapter = event.get("chapter", 1)
                compressed_event = context_manager.compress_context(
                    event, chapter_number, event_chapter, "event"
                )
                compressed_active_events.append(compressed_event)
            compressed_context["active_events"] = compressed_active_events
        # 对其他上下文进行基于时间的压缩
        for key, value in original_context.items():
            if key == "active_events":
                continue  # 已处理
            elif key in ["event_timeline", "previous_events", "upcoming_events"]:
                # 这些需要特殊处理的时间相关上下文
                compressed_context[key] = context_manager.compress_context(
                    value, chapter_number, None, "event"
                )
            else:
                # 其他上下文使用精要压缩
                compressed_context[key] = context_manager.compress_context(
                    value, chapter_number, None, "general"
                )
        # 添加上下文大小信息用于调试
        context_size_info = context_manager.get_context_size_info(compressed_context)
        if context_size_info.get("is_large", False):
            self.logger.info(f"⚠️ 第{chapter_number}章事件上下文较大: {context_size_info['estimated_tokens']} tokens")
        return compressed_context
    def generate_event_execution_prompt(self, chapter_number: int) -> str:
        """生成事件执行指导提示词 - 增强版本，包含前后事件信息"""
        event_context = self.get_chapter_event_context(chapter_number)
        # 🆕 获取事件时间线信息
        event_timeline = event_context.get("event_timeline", {})
        timeline_summary = event_timeline.get("timeline_summary", "")
        buffer_info = event_context.get("buffer_period", {})
        prompt_parts = ["# 🎯 事件执行指导"]
        # 🆕 添加事件时间线概览
        if timeline_summary:
            prompt_parts.extend([
                "## ⏰ 事件时间线概览",
                timeline_summary,
                ""
            ])
        # 🆕 添加上下文衔接指导
        previous_event = event_timeline.get("previous_event")
        next_event = event_timeline.get("next_event")
        if previous_event or next_event:
            prompt_parts.append("## 🔗 情节衔接指导")
            if previous_event:
                prompt_parts.extend([
                    f"### 📖 承接前情 (第{previous_event['chapter']}章)",
                    f"- **事件**: {previous_event['name']}",
                    f"- **类型**: {previous_event['type']}事件",
                    f"- **衔接重点**: 自然承接上一章的{previous_event.get('significance', '情节发展')}",
                    f"- **情感延续**: 保持{previous_event.get('emotional_impact', '情感基调')}的连贯性",
                    ""
                ])
            if next_event:
                prompt_parts.extend([
                    f"### 🔮 铺垫后续 (第{next_event['chapter']}章)",
                    f"- **即将发生**: {next_event['name']}",
                    f"- **事件类型**: {next_event['type']}事件",
                    f"- **铺垫重点**: 为下一章的{next_event.get('significance', '重要事件')}做好情感和情节准备",
                    f"- **伏笔设置**: 适当埋下与下一章事件相关的线索",
                    ""
                ])
        # 缓冲期特殊指导
        if buffer_info.get("is_buffer_period"):
            prompt_parts.append(self._generate_buffer_guidance(chapter_number, buffer_info))
        # 原有的事件指导逻辑
        if not buffer_info.get("is_buffer_period") or buffer_info.get("pre_major_event"):        
            # 按事件类型分组
            major_events = [e for e in event_context["active_events"] if e["type"] == "major_event"]
            medium_events = [e for e in event_context["active_events"] if e["type"] == "medium_event"]
            # 重大事件指导
            if major_events:
                prompt_parts.append("## 🚨 重大事件")
                for event in major_events:
                    event_name = event.get("name", "未知事件")
                    progress = event_context["event_progress"].get(event_name, {})
                    prompt_parts.extend([
                        f"### {event_name}",
                        f"**目标**: {event.get('main_goal', '推进故事发展')}",
                        f"**当前重点**: {event.get('current_stage_focus', '推进事件发展')}",
                        f"**进度**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                        f"**关键时刻**:"
                    ])
                    # 处理关键时刻显示
                    key_moments = event.get('key_moments', [])
                    if key_moments:
                        for moment in key_moments:
                            if isinstance(moment, dict):
                                desc = moment.get('description', '未描述')
                                chap = moment.get('chapter', '?')
                                prompt_parts.append(f"- 第{chap}章: {desc}")
                            else:
                                prompt_parts.append(f"- {moment}")
                    else:
                        prompt_parts.append("- 暂无关键时刻")
                    prompt_parts.append("")  # 空行分隔
            # 中型事件指导
            if medium_events:
                prompt_parts.append("## 🔥 中型事件")
                for event in medium_events:
                    event_name = event.get("name", "未知事件")
                    progress = event_context["event_progress"].get(event_name, {})
                    prompt_parts.extend([
                        f"### {event_name}",
                        f"**目标**: {event.get('main_goal', '推进故事发展')}",
                        f"**当前重点**: {event.get('current_stage_focus', '推进事件发展')}",
                        f"**进度**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                        f"**关联重大事件**: {event.get('connection_to_major', '独立事件')}"
                    ])
                    prompt_parts.append("")  # 空行分隔
            # 🆕 事件连贯性检查
            prompt_parts.extend([
                "## 🔍 事件连贯性检查",
                "写作时请确保：",
                "✅ 与上一章事件自然衔接，不出现逻辑断层",
                "✅ 为下一章事件做好适当铺垫，保持情节流畅", 
                "✅ 事件发展与角色情感变化协调一致",
                "✅ 保持主线情节的连贯性和推进感",
                ""
            ])
            # 触发检查点
            if event_context["trigger_checkpoints"]:
                prompt_parts.append("## ⏰ 事件触发检查点")
                for checkpoint in event_context["trigger_checkpoints"]:
                    prompt_parts.append(f"- **{checkpoint.get('trigger', '未知触发')}**: {checkpoint.get('description', '未指定描述')}")
            # 事件链影响
            if event_context["event_chain_effects"]:
                prompt_parts.append("## 🔗 事件链影响")
                for effect in event_context["event_chain_effects"]:
                    prompt_parts.append(f"- {effect.get('description', '未指定影响')} (源于: {effect.get('source_event', '未知事件')})")
            # 事件任务
            if event_context["event_tasks"]:
                prompt_parts.append("## ✅ 本章事件任务")
                for task in event_context["event_tasks"]:
                    priority_icon = "🔴" if task.get('priority') == 'critical' else "🟡" if task.get('priority') == 'high' else "🟢"
                    prompt_parts.append(f"- {priority_icon} **{task.get('priority', '普通')}优先级**: {task.get('description', '未指定任务')}")
        return "\n".join(prompt_parts)
    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文 - 增强版本，包含事件时间线"""
        context = {
            "active_events": [],
            "event_progress": {},
            "event_tasks": [],
            "trigger_checkpoints": [],
            "event_chain_effects": [],
            "buffer_period": {},
            "event_timeline": {}  # 🆕 新增事件时间线
        }
        # 如果没有活跃事件，尝试初始化
        if not self.active_events:
            self.initialize_event_system()
        if not self.active_events:
            gap_length = self._calculate_event_gap_length(chapter_number)
            if gap_length >= 3:  # 空窗期超过3章就创建支线
                self.create_side_quest_events(chapter_number, gap_length)
            else:
                self._create_fallback_events(chapter_number)
        # 🆕 获取事件时间线信息
        event_timeline = self._get_chapter_event_timeline(chapter_number)
        context["event_timeline"] = event_timeline
        # 计算精准缓冲期信息
        buffer_info = self._calculate_precise_buffer_periods(chapter_number)
        context["buffer_period"] = buffer_info
        # 获取当前活跃的事件
        active_count = 0
        for event_name, event_data in self.active_events.items():
            if self._is_event_active(chapter_number, event_data):
                active_count += 1
                event_context = self._build_event_context(chapter_number, event_data)
                context["active_events"].append(event_context)
                # 计算事件进度
                progress = self._calculate_event_progress(chapter_number, event_data)
                context["event_progress"][event_name] = progress
                # 生成事件任务
                tasks = self._generate_event_tasks(chapter_number, event_data, progress, buffer_info)
                context["event_tasks"].extend(tasks)
        # 检查触发条件
        trigger_checkpoints = self._check_event_triggers(chapter_number)
        context["trigger_checkpoints"] = trigger_checkpoints
        # 计算事件链影响
        chain_effects = self._calculate_chain_effects(chapter_number)
        context["event_chain_effects"] = chain_effects
        self.logger.info(f"📊 第{chapter_number}章事件上下文: {active_count}个活跃事件, {len(context['event_tasks'])}个任务")
        return context
    def _get_chapter_event_timeline(self, chapter_number: int) -> Dict:
        """获取章节的事件时间线信息 - 修正版本，准确区分事件状态"""
        # 构建完整的事件列表
        all_events = []
        # 添加重大事件
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "major_event":
                all_events.append({
                    "type": "major_event",
                    "name": event_data.get("name", "未命名重大事件"),
                    "start_chapter": event_data.get("start_chapter", 0),
                    "end_chapter": event_data.get("end_chapter", event_data.get("start_chapter", 0)),
                    "description": event_data.get("description", ""),
                    "significance": event_data.get("significance", "重大事件"),
                    "status": "active" if self._is_event_active(chapter_number, event_data) else "completed"
                })
        # 添加中型事件
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "medium_event":
                all_events.append({
                    "type": "medium_event",
                    "name": event_data.get("name", "未命名中型事件"),
                    "start_chapter": event_data.get("start_chapter", 0),
                    "end_chapter": event_data.get("end_chapter", event_data.get("start_chapter", 0)),
                    "description": event_data.get("description", ""),
                    "significance": event_data.get("connection_to_major", "中型事件"),
                    "status": "active" if self._is_event_active(chapter_number, event_data) else "completed"
                })
        # 按开始章节排序
        all_events.sort(key=lambda x: x["start_chapter"])
        # 🆕 准确区分事件状态
        previous_events = []
        current_events = []
        next_events = []
        for event in all_events:
            start_chapter = event["start_chapter"]
            end_chapter = event["end_chapter"]
            if end_chapter < chapter_number:
                # 已完成的事件
                previous_events.append(event)
            elif start_chapter <= chapter_number <= end_chapter:
                # 当前活跃的事件
                current_events.append(event)
            elif start_chapter > chapter_number:
                # 即将发生的事件
                next_events.append(event)
        # 找到最近的前一个事件（已完成的事件中最近结束的）
        previous_event = previous_events[-1] if previous_events else None
        # 找到下一个即将发生的事件
        next_event = next_events[0] if next_events else None
        return {
            "previous_event": previous_event,
            "current_events": current_events,
            "next_event": next_event,
            "all_events": all_events,
            "timeline_summary": self._generate_accurate_timeline_summary(previous_event, current_events, next_event, chapter_number)
        }
    def _generate_accurate_timeline_summary(self, previous_event: Optional[Dict], current_events: List[Dict], next_event: Optional[Dict], chapter_number: int) -> str:
        """生成准确的时间线摘要 - 修正版本"""
        summary_parts = []
        if previous_event:
            # 🆕 明确标识已完成的事件
            summary_parts.append(f"📖 已完结: 第{previous_event['start_chapter']}章《{previous_event['name']}》")
        if current_events:
            event_names = []
            for event in current_events:
                # 🆕 显示事件进度状态
                progress = self._calculate_event_progress(chapter_number, event)
                status_icon = "🟡" if progress.get("ratio", 0) < 0.7 else "🔴"
                event_names.append(f"《{event['name']}》{status_icon}")
            summary_parts.append(f"🎯 进行中: {', '.join(event_names)}")
        else:
            summary_parts.append("📝 本章: 日常推进或情感发展")
        if next_event:
            # 🆕 明确标识即将发生的事件
            summary_parts.append(f"🔮 即将开始: 第{next_event['start_chapter']}章《{next_event['name']}》")
        return " | ".join(summary_parts)
    def generate_event_execution_prompt(self, chapter_number: int) -> str:
        """生成事件执行指导提示词 - 修正版本，准确的事件状态"""
        event_context = self.get_chapter_event_context(chapter_number)
        # 🆕 获取准确的事件时间线信息
        event_timeline = event_context.get("event_timeline", {})
        timeline_summary = event_timeline.get("timeline_summary", "")
        buffer_info = event_context.get("buffer_period", {})
        prompt_parts = ["# 🎯 事件执行指导"]
        # 🆕 添加准确的事件时间线概览
        if timeline_summary:
            prompt_parts.extend([
                "## ⏰ 事件时间线概览",
                timeline_summary,
                ""
            ])
        # 🆕 修正情节衔接指导逻辑
        previous_event = event_timeline.get("previous_event")
        next_event = event_timeline.get("next_event")
        if previous_event or next_event:
            prompt_parts.append("## 🔗 情节衔接指导")
            if previous_event:
                # 🆕 对已完成事件的正确衔接指导
                prompt_parts.extend([
                    f"### 📖 承接已完结事件",
                    f"- **事件**: {previous_event['name']} (第{previous_event['start_chapter']}章)",
                    f"- **状态**: 已完结",
                    f"- **衔接重点**: 处理事件余波，展示角色情感消化和成长变化",
                    f"- **伏笔延续**: 确保已完结事件的重要影响在本章得到体现",
                    ""
                ])
            if next_event:
                # 🆕 对即将发生事件的正确衔接指导
                prompt_parts.extend([
                    f"### 🔮 铺垫即将开始事件",
                    f"- **事件**: {next_event['name']} (第{next_event['start_chapter']}章)",
                    f"- **状态**: 即将开始",
                    f"- **铺垫重点**: 为下一章的重大事件营造氛围，埋设必要伏笔",
                    f"- **情感准备**: 让读者对即将到来的事件产生期待",
                    ""
                ])
        # 缓冲期特殊指导
        if buffer_info.get("is_buffer_period"):
            prompt_parts.append(self._generate_buffer_guidance(chapter_number, buffer_info))
        # 🆕 修正活跃事件显示逻辑
        current_events = event_timeline.get("current_events", [])
        if current_events and (not buffer_info.get("is_buffer_period") or buffer_info.get("pre_major_event")):
            # 按事件类型分组
            major_events = [e for e in current_events if e["type"] == "major_event"]
            medium_events = [e for e in current_events if e["type"] == "medium_event"]
            # 🆕 重大事件指导 - 只显示真正活跃的事件
            if major_events:
                prompt_parts.append("## 🚨 进行中重大事件")
                for event in major_events:
                    event_name = event.get("name", "未知事件")
                    progress = event_context["event_progress"].get(event_name, {})
                    prompt_parts.extend([
                        f"### {event_name}",
                        f"**目标**: {event.get('main_goal', '推进故事发展')}",
                        f"**当前阶段**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                        f"**本章重点**: {self._get_chapter_specific_focus(chapter_number, event, progress)}",
                        f"**关键时刻**:"
                    ])
                    # 🆕 只显示本章相关的关键时刻
                    chapter_moments = self._get_chapter_key_moments(chapter_number, event)
                    if chapter_moments:
                        for moment in chapter_moments:
                            prompt_parts.append(f"- {moment}")
                    else:
                        prompt_parts.append("- 按计划推进事件发展")
                    prompt_parts.append("")  # 空行分隔
            # 🆕 中型事件指导 - 只显示真正活跃的事件
            if medium_events:
                prompt_parts.append("## 🔥 进行中型事件")
                for event in medium_events:
                    event_name = event.get("name", "未知事件")
                    progress = event_context["event_progress"].get(event_name, {})
                    prompt_parts.extend([
                        f"### {event_name}",
                        f"**目标**: {event.get('main_goal', '推进故事发展')}",
                        f"**当前阶段**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                        f"**关联**: {event.get('connection_to_major', '独立事件')}",
                        f"**本章任务**: {self._get_chapter_specific_focus(chapter_number, event, progress)}"
                    ])
                    prompt_parts.append("")  # 空行分隔
            # 🆕 修正事件连贯性检查
            prompt_parts.extend([
                "## 🔍 事件连贯性检查",
                "写作时请确保：",
                "✅ 已完结事件的影响得到合理体现",
                "✅ 进行中事件按计划推进，不出现逻辑跳跃",
                "✅ 为即将开始事件做好自然铺垫",
                "✅ 不同事件间的过渡平滑自然",
                "✅ 角色情感发展与事件进度协调一致",
                ""
            ])
            # 触发检查点
            if event_context["trigger_checkpoints"]:
                prompt_parts.append("## ⏰ 事件触发检查点")
                for checkpoint in event_context["trigger_checkpoints"]:
                    prompt_parts.append(f"- **{checkpoint.get('trigger', '未知触发')}**: {checkpoint.get('description', '未指定描述')}")
            # 事件链影响
            if event_context["event_chain_effects"]:
                prompt_parts.append("## 🔗 事件链影响")
                for effect in event_context["event_chain_effects"]:
                    prompt_parts.append(f"- {effect.get('description', '未指定影响')} (源于: {effect.get('source_event', '未知事件')})")
            # 事件任务
            if event_context["event_tasks"]:
                prompt_parts.append("## ✅ 本章事件任务")
                for task in event_context["event_tasks"]:
                    priority_icon = "🔴" if task.get('priority') == 'critical' else "🟡" if task.get('priority') == 'high' else "🟢"
                    prompt_parts.append(f"- {priority_icon} **{task.get('priority', '普通')}优先级**: {task.get('description', '未指定任务')}")
        return "\n".join(prompt_parts)
    def _get_chapter_specific_focus(self, chapter_number: int, event: Dict, progress: Dict) -> str:
        """获取本章特定的事件执行重点"""
        current_stage = progress.get("stage", "开局阶段")
        event_name = event.get("name", "")
        # 基于事件阶段和章节位置生成具体指导
        if current_stage == "开局阶段":
            return "建立事件基础，引入核心冲突和关键角色"
        elif current_stage == "发展阶段":
            return "深化矛盾，推进事件目标，发展角色关系"
        elif current_stage == "高潮阶段":
            return "处理关键转折和情感爆发点"
        else:  # 收尾阶段
            return "解决冲突，处理后续影响，展示角色成长"
    def _get_chapter_key_moments(self, chapter_number: int, event: Dict) -> List[str]:
        """获取本章相关的关键时刻"""
        key_moments = event.get("key_moments", [])
        chapter_moments = []
        for moment in key_moments:
            if isinstance(moment, dict):
                moment_chapter = moment.get("chapter", 0)
                if moment_chapter == chapter_number:
                    chapter_moments.append(moment.get("description", "未描述关键时刻"))
            elif isinstance(moment, str):
                # 从字符串中提取章节号
                chapter_match = re.search(r'第(\d+)章', moment)
                if chapter_match and int(chapter_match.group(1)) == chapter_number:
                    chapter_moments.append(moment)
        return chapter_moments
    def _generate_timeline_summary(self, previous_event: Optional[Dict], current_events: List[Dict], next_event: Optional[Dict]) -> str:
        """生成时间线摘要 - 新增方法"""
        summary_parts = []
        if previous_event:
            summary_parts.append(f"📖 前情: 第{previous_event['chapter']}章《{previous_event['name']}》")
        if current_events:
            event_names = [f"《{event['name']}》" for event in current_events]
            summary_parts.append(f"🎯 本章: {', '.join(event_names)}")
        else:
            summary_parts.append("📝 本章: 日常推进或情感发展")
        if next_event:
            summary_parts.append(f"🔮 后续: 第{next_event['chapter']}章《{next_event['name']}》")
        return " | ".join(summary_parts)
    def _generate_buffer_guidance(self, chapter_number: int, buffer_info: Dict) -> str:
        """生成缓冲期特定指导"""
        guidance_parts = []
        if buffer_info["post_medium_event"]:
            guidance_parts.extend([
                "## 🌊 中型事件后情绪缓冲期",
                "**重点任务**: 处理事件余波，展示角色情感消化",
                "**写作建议**:",
                "- 描写角色对刚结束事件的反思和感受",
                "- 通过日常场景展示世界观细节",
                "- 为下一个事件做自然过渡",
                "- 控制节奏，让读者情绪得到释放"
            ])
        elif buffer_info["pre_major_event"]:
            guidance_parts.extend([
                "## ⚡ 重大事件前准备期", 
                "**重点任务**: 营造氛围，铺设伏笔",
                "**写作建议**:",
                "- 通过环境描写暗示即将到来的风暴",
                "- 展现角色的预感或不安情绪",
                "- 埋设关键伏笔但不直接揭示",
                "- 逐步提升紧张感，为高潮做铺垫"
            ])
        elif buffer_info["between_medium_events"]:
            guidance_parts.extend([
                "## 🔄 中型事件间节奏调整期",
                "**重点任务**: 发展支线，丰富角色",
                "**写作建议**:",
                "- 推进次要情节和配角发展",
                "- 展示角色间的日常互动",
                "- 补充世界观和文化细节",
                "- 为主线事件提供背景支撑"
            ])
        return "\n".join(guidance_parts)    
    def _generate_event_gap_prompt(self, chapter_number: int, event_context: Dict) -> str:
        """生成事件空窗期的专门指导"""
        prompt_parts = [
            "# 🎯 事件执行指导 - 事件空窗期",
            "",
            "## 📊 当前状态分析",
            f"第{chapter_number}章处于**事件空窗期**，没有活跃的重大事件或中型事件。",
            "这是安排情绪缓冲、角色发展和世界观展示的绝佳时机。",
            ""
        ]
        # 检查是否有即将发生的事件需要铺垫
        upcoming_events = self._get_upcoming_events(chapter_number)
        if upcoming_events:
            prompt_parts.extend([
                "## 🔮 即将发生事件铺垫",
                "利用空窗期为后续事件做铺垫:"
            ])
            for event in upcoming_events[:3]:  # 只显示最近3个
                event_name = event.get('name', '未知事件')
                start_chapter = event.get('start_chapter', chapter_number + 1)
                prompt_parts.append(f"- **{event_name}** (预计第{start_chapter}章): 可埋下伏笔或相关线索")
            prompt_parts.append("")
        # 空窗期的核心任务建议
        prompt_parts.extend([
            "## 🎯 空窗期核心任务",
            "1. **角色深度发展**: 展现角色的内心世界、人际关系变化",
            "2. **世界观丰富**: 展示世界观细节，增强读者沉浸感", 
            "3. **伏笔铺设**: 为后续事件埋下巧妙线索",
            "4. **节奏调整**: 让读者从高强度事件中恢复，准备下一波高潮",
            "5. **支线推进**: 推进次要情节，丰富故事层次",
            "",
            "## 💡 创作提示",
            "- 保持与主线的关联性，避免完全脱离",
            "- 利用日常场景展现角色性格",
            "- 通过对话和互动深化人物关系",
            "- 适当加入幽默或温馨元素调节情绪",
            "- 确保空窗期内容推动故事整体发展"
        ])
        return "\n".join(prompt_parts)
    def _get_upcoming_events(self, chapter_number: int) -> List[Dict]:
        """获取即将发生的事件"""
        upcoming_events = []
        # 从事件触发器中查找
        for event_name, trigger_data in self.event_triggers.items():
            condition = trigger_data.get("condition", {})
            event_data = trigger_data.get("event_data", {})
            # 检查章节触发
            if condition.get("type") == "chapter":
                trigger_chapter = condition.get("chapter", 0)
                if trigger_chapter > chapter_number and trigger_chapter <= chapter_number + 10:  # 未来10章内
                    upcoming_events.append({
                        "name": event_name,
                        "start_chapter": trigger_chapter,
                        "type": event_data.get("type", "未知类型")
                    })
        return sorted(upcoming_events, key=lambda x: x.get("start_chapter", 999))
    def _parse_chapter_range(self, chapter_range: str) -> tuple:
        """从章节范围字符串中解析start和end章节"""
        if not chapter_range:
            return 1, 1
        
        # 使用正则表达式提取数字
        numbers = re.findall(r'\d+', chapter_range)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            chapter = int(numbers[0])
            return chapter, chapter
        else:
            return 1, 1
    
    def _initialize_active_events(self, event_system: Dict):
        """初始化活跃事件 - 只处理重大事件和中型事件"""
        self.active_events.clear()
        # 从重大事件的composition中提取中型事件
        for major_event in event_system.get("major_events", []):
            major_event_name = major_event.get("name")
            if major_event_name:
                # 解析章节范围
                chapter_range = major_event.get("chapter_range", "")
                start_chapter, end_chapter = self._parse_chapter_range(chapter_range)
                
                # 添加重大事件本身
                self.active_events[major_event_name] = {
                    "name": major_event_name,
                    "type": "major_event",
                    "main_goal": major_event.get("main_goal", "推进故事发展"),
                    "start_chapter": start_chapter,
                    "end_chapter": end_chapter,
                    "key_moments": major_event.get("key_moments", []),
                    "character_roles": major_event.get("character_roles", {}),
                    "stage_focus": major_event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": start_chapter,
                    "current_progress": 0,
                    "significance": major_event.get("significance", "重大转折点")
                }
             
            # 从composition中提取中型事件
            composition = major_event.get("composition", {})
            for phase_name, phase_events in composition.items():
                if isinstance(phase_events, list):
                    for medium_event in phase_events:
                        medium_event_name = medium_event.get("name")
                        if medium_event_name:
                            # 解析章节范围
                            chapter_range = medium_event.get("chapter_range", "")
                            start_chapter, end_chapter = self._parse_chapter_range(chapter_range)
                            
                            self.active_events[medium_event_name] = {
                                "name": medium_event_name,
                                "type": "medium_event",
                                "main_goal": medium_event.get("main_goal", "推进故事发展"),
                                "start_chapter": start_chapter,
                                "end_chapter": end_chapter,
                                "key_moments": medium_event.get("key_moments", []),
                                "character_roles": medium_event.get("character_roles", {}),
                                "stage_focus": medium_event.get("stage_focus", {}),
                                "status": "active",
                                "started_chapter": start_chapter,
                                "current_progress": 0,
                                "connection_to_major": major_event_name
                            }
        
        # 统计事件数量
        major_count = len([e for e in self.active_events.values() if e['type'] == 'major_event'])
        medium_count = len([e for e in self.active_events.values() if e['type'] == 'medium_event'])
        self.logger.info(f"✅ 初始化活跃事件: {major_count}个重大事件, {medium_count}个中型事件")
    def _build_event_context(self, chapter_number: int, event_data: Dict) -> Dict:
        """构建事件上下文 - 专注重大事件和中型事件"""
        progress = self._calculate_event_progress(chapter_number, event_data)
        # 处理关键时刻
        key_moments = []
        raw_moments = event_data.get("key_moments", [])
        for moment in raw_moments:
            if isinstance(moment, str):
                # 转换字符串格式为字典格式
                chapter_match = re.search(r'第(\d+)章', moment)
                moment_chapter = int(chapter_match.group(1)) if chapter_match else chapter_number
                key_moments.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            elif isinstance(moment, dict):
                key_moments.append({
                    "chapter": moment.get("chapter", chapter_number),
                    "description": moment.get("description", "未描述关键时刻"),
                    "preparation": moment.get("preparation", "正常推进")
                })
        # 构建事件上下文
        event_context = {
            "name": event_data.get("name", "未知事件"),
            "type": event_data.get("type", "medium_event"),
            "main_goal": event_data.get("main_goal", "推进故事发展"),
            "current_stage_focus": self._get_current_stage_focus(progress.get("stage", "开局阶段"), event_data),
            "key_moments": key_moments,
            "character_roles": event_data.get("character_roles", {}),
            "progress": progress
        }
        # 添加特定字段
        if event_data["type"] == "major_event":
            event_context["significance"] = event_data.get("significance", "重大转折点")
        elif event_data["type"] == "medium_event":
            event_context["connection_to_major"] = event_data.get("connection_to_major", "独立事件")
        return event_context
    def _calculate_event_progress(self, chapter_number: int, event_data: Dict) -> Dict:
        """计算事件进度 - 专注多章事件"""
        start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 1))
        end_chapter = event_data.get("end_chapter", chapter_number + 10)
        total_chapters = max(end_chapter - start_chapter + 1, 1)
        current_progress = max(min(chapter_number - start_chapter + 1, total_chapters), 0)
        progress_ratio = current_progress / total_chapters if total_chapters > 0 else 0
        # 确定阶段
        if progress_ratio <= 0.3:
            stage = "开局阶段"
        elif progress_ratio <= 0.6:
            stage = "发展阶段"
        elif progress_ratio <= 0.9:
            stage = "高潮阶段"
        else:
            stage = "收尾阶段"
        return {
            "current": current_progress,
            "total": total_chapters,
            "ratio": progress_ratio,
            "stage": stage
        }
    def _get_current_stage_focus(self, stage: str, event_data: Dict) -> str:
        """获取当前阶段的执行重点"""
        # 优先使用事件自定义的重点
        stage_focus = event_data.get("stage_focus", {})
        if isinstance(stage_focus, dict):
            custom_focus = stage_focus.get(stage)
            if custom_focus:
                return custom_focus
        # 默认阶段重点映射
        focus_map = {
            "开局阶段": "建立事件基础，引入核心冲突",
            "发展阶段": "深化矛盾，推进事件目标", 
            "高潮阶段": "冲突激化，关键转折",
            "收尾阶段": "解决冲突，展示后果"
        }
        return focus_map.get(stage, "推进事件发展")
    def _setup_event_triggers(self, event_system: Dict):
        """设置事件触发条件 - 只处理重大事件和中型事件"""
        self.event_triggers.clear()
        # 为重大事件和中型事件设置触发条件
        all_events = []
        all_events.extend(event_system.get("major_events", []))
        # 从重大事件的composition中提取中型事件
        for major_event in event_system.get("major_events", []):
            composition = major_event.get("composition", {})
            for phase_events in composition.values():
                if isinstance(phase_events, list):
                    all_events.extend(phase_events)
        for event in all_events:
            event_name = event.get("name")
            if not event_name:
                continue
            # 检查是否有自定义触发条件
            trigger_condition = event.get("trigger_condition")
            if trigger_condition:
                self.event_triggers[event_name] = {
                    "condition": trigger_condition,
                    "event_data": event
                }
            # 如果没有明确触发条件，使用章节触发
            elif "start_chapter" in event:
                trigger_chapter = event.get("start_chapter")
                if trigger_chapter:
                    self.event_triggers[event_name] = {
                        "condition": {
                            "type": "chapter",
                            "chapter": trigger_chapter
                        },
                        "event_data": event
                    }
    def _is_event_active(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否活跃"""
        if event_data.get("status") != "active":
            return False
        # 重大事件和中型事件都是多章事件
        start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 0))
        end_chapter = event_data.get("end_chapter", chapter_number + 100)
        return start_chapter <= chapter_number <= end_chapter
    def initialize_event_system(self):
        """初始化事件系统 - 从StagePlanManager统一接口加载重大事件和中型事件"""
        self.logger.info("🎯 初始化事件系统...")
        
        # 获取当前章节
        current_chapter = len(self.generator.novel_data["generated_chapters"]) + 1
        
        # 🔥 改进：通过StagePlanManager的统一接口获取阶段计划
        stage_plan_manager = self.generator.stage_plan_manager
        if not stage_plan_manager:
            self.logger.error("❌ StagePlanManager未初始化")
            self._create_fallback_events(current_chapter)
            return
        
        # 获取当前阶段名称
        current_stage = self._get_current_stage_from_plans(current_chapter)
        
        if current_stage:
            self.logger.info(f"✅ 当前阶段: {current_stage}")
            # 🆕 通过StagePlanManager的统一接口获取计划
            stage_plan = stage_plan_manager.get_stage_writing_plan_by_name(current_stage)
            
            if stage_plan:
                # 从stage_plan中提取event_system
                event_system = stage_plan.get("stage_writing_plan", {}).get("event_system", {})
                if event_system:
                    self.logger.info(f"✅ 从StagePlanManager加载 {current_stage} 的事件系统")
                    # 计算中型事件数量
                    major_events = event_system.get('major_events', [])
                    medium_count = 0
                    for major_event in major_events:
                        composition = major_event.get("composition", {})
                        for phase_events in composition.values():
                            if isinstance(phase_events, list):
                                medium_count += len(phase_events)
                    self.logger.info(f"   重大事件: {len(major_events)}个")
                    self.logger.info(f"   中型事件: {medium_count}个")
                    # 更新到事件执行器
                    self.update_from_stage_plan({"event_system": event_system})
                    return
                else:
                    self.logger.warn(f"⚠️ 阶段 {current_stage} 的事件系统为空")
            else:
                self.logger.warn(f"⚠️ 无法从StagePlanManager获取 {current_stage} 的计划")
        
        # 如果找不到当前阶段，尝试从所有阶段中查找
        self.logger.info("🔍 尝试从所有阶段查找适合当前章节的事件...")
        
        # 获取所有可用的阶段计划
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if "overall_stage_plan" in overall_plans:
            stage_plan_dict = overall_plans["overall_stage_plan"]
        else:
            stage_plan_dict = overall_plans
        
        for stage_name in stage_plan_dict.keys():
            stage_plan = stage_plan_manager.get_stage_writing_plan_by_name(stage_name)
            if stage_plan:
                # 检查该阶段是否包含当前章节
                chapter_range = stage_plan.get("stage_writing_plan", {}).get("chapter_range", "")
                if self._is_chapter_in_range(current_chapter, chapter_range):
                    self.logger.info(f"✅ 发现阶段 {stage_name} 包含第{current_chapter}章")
                    event_system = stage_plan.get("stage_writing_plan", {}).get("event_system", {})
                    if event_system:
                        self.logger.info(f"✅ 从StagePlanManager加载 {stage_name} 的事件系统")
                        self.update_from_stage_plan({"event_system": event_system})
                        return
        
        # 如果还是找不到，使用第一个可用的阶段
        if stage_plan_dict:
            first_stage = list(stage_plan_dict.keys())[0]
            stage_plan = stage_plan_manager.get_stage_writing_plan_by_name(first_stage)
            if stage_plan:
                event_system = stage_plan.get("stage_writing_plan", {}).get("event_system", {})
                if event_system:
                    self.logger.info(f"⚠️ 使用第一个可用阶段 {first_stage} 的事件系统")
                    self.update_from_stage_plan({"event_system": event_system})
                    return
        
        self.logger.warn("⚠️ 没有可用的阶段写作计划或事件系统")
        # 创建回退事件确保系统能工作
        self._create_fallback_events(current_chapter)
    def _get_current_stage_from_plans(self, chapter_number: int) -> str:
        """从阶段计划中获取当前章节所属的阶段"""
        novel_data = self.generator.novel_data
        # 从 overall_stage_plans 中查找
        if "overall_stage_plans" in novel_data and "overall_stage_plan" in novel_data["overall_stage_plans"]:
            overall_plan = novel_data["overall_stage_plans"]["overall_stage_plan"]
            for stage_name, stage_info in overall_plan.items():
                chapter_range = stage_info.get("chapter_range", "")
                if self._is_chapter_in_range(chapter_number, chapter_range):
                    return stage_name
        # 从 stage_writing_plans 中推断
        if "stage_writing_plans" in novel_data:
            for stage_name, stage_data in novel_data["stage_writing_plans"].items():
                if self._is_chapter_in_stage(chapter_number, stage_data):
                    return stage_name
        return "未知阶段"
    def _is_chapter_in_stage(self, chapter_number: int, stage_data: Dict) -> bool:
        """检查章节是否在阶段范围内"""
        chapter_range = ""
        if "stage_writing_plan" in stage_data:
            writing_plan = stage_data["stage_writing_plan"]
            chapter_range = writing_plan.get("chapter_range", "")
        else:
            chapter_range = stage_data.get("chapter_range", "")
        return self._is_chapter_in_range(chapter_number, chapter_range)
    def _is_chapter_in_range(self, chapter_number: int, chapter_range: str) -> bool:
        """检查章节是否在范围内"""
        if not chapter_range:
            return False
        try:
            numbers = re.findall(r'\d+', chapter_range)
            if len(numbers) >= 2:
                start_chapter = int(numbers[0])
                end_chapter = int(numbers[1])
                return start_chapter <= chapter_number <= end_chapter
            elif len(numbers) == 1:
                single_chapter = int(numbers[0])
                return chapter_number == single_chapter
        except Exception as e:
            self.logger.info(f"❌ 解析章节范围失败: {chapter_range}, 错误: {e}")
        return False
    def _generate_event_tasks(self, chapter_number: int, event_data: Dict, 
                         progress: Dict, buffer_info: Dict) -> List[Dict]:
        """生成事件执行任务"""
        tasks = []
        event_name = event_data.get("name", "未知事件")
        event_type = event_data.get("type", "medium_event")
        # 基于事件阶段生成任务
        current_stage = progress.get("stage", "开局阶段")
        # 如果在缓冲期，生成缓冲期特定任务
        if buffer_info["is_buffer_period"]:
            buffer_tasks = self._generate_buffer_specific_tasks(chapter_number, buffer_info)
            tasks.extend(buffer_tasks)
            # 缓冲期内的事件任务优先级降低
            if buffer_info["post_medium_event"]:
                tasks.append({
                    "event": event_name,
                    "description": f"处理{event_type}的后续影响和余波",
                    "priority": "low",
                    "type": "aftermath",
                    "buffer_context": "中型事件结束后的情绪缓冲"
                })
            elif buffer_info["pre_major_event"]:
                tasks.append({
                    "event": event_name, 
                    "description": f"为即将到来的重大事件做铺垫",
                    "priority": "medium", 
                    "type": "preparation",
                    "buffer_context": "重大事件前的氛围营造"
                })
            elif buffer_info["between_medium_events"]:
                tasks.append({
                    "event": event_name,
                    "description": f"在连续中型事件间隙推进支线发展",
                    "priority": "low",
                    "type": "side_development",
                    "buffer_context": "中型事件间的节奏调整"
                })
        else:
            if current_stage == "开局阶段":
                tasks.append({
                    "event": event_name,
                    "description": f"建立{event_type}基础设定和初始冲突",
                    "priority": "high",
                    "type": "setup"
                })
            elif current_stage == "发展阶段":
                tasks.append({
                    "event": event_name,
                    "description": f"深化{event_type}矛盾，推进核心目标",
                    "priority": "high",
                    "type": "development"
                })
            elif current_stage == "高潮阶段":
                tasks.append({
                    "event": event_name,
                    "description": f"处理{event_type}高潮和关键转折",
                    "priority": "critical",
                    "type": "climax"
                })
            else:  # 收尾阶段
                tasks.append({
                    "event": event_name,
                    "description": f"解决{event_type}冲突，处理后续影响",
                    "priority": "medium",
                    "type": "resolution"
                })
        # 添加特定关键时刻的任务
        upcoming_moments = self._get_upcoming_key_moments(chapter_number, event_data)
        for moment in upcoming_moments:
            if moment.get("chapter") == chapter_number:
                tasks.append({
                    "event": event_name,
                    "description": f"处理关键时刻: {moment.get('description', '未描述')}",
                    "priority": "critical",
                    "type": "key_moment"
                })
        return tasks
    def _get_upcoming_key_moments(self, chapter_number: int, event_data: Dict) -> List[Dict]:
        """获取即将到来的关键时刻"""
        key_moments = event_data.get("key_moments", [])
        upcoming = []
        for moment in key_moments:
            if isinstance(moment, str):
                chapter_match = re.search(r'第(\d+)章', moment)
                if chapter_match:
                    moment_chapter = int(chapter_match.group(1))
                else:
                    moment_chapter = chapter_number + 1
                upcoming.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            elif isinstance(moment, dict):
                moment_chapter = moment.get("chapter", 0)
                if moment_chapter >= chapter_number and moment_chapter <= chapter_number + 3:
                    upcoming.append({
                        "chapter": moment_chapter,
                        "description": moment.get("description", ""),
                        "preparation": moment.get("preparation", "正常推进")
                    })
        return upcoming
    def _check_event_triggers(self, chapter_number: int) -> List[Dict]:
        """检查事件触发条件"""
        checkpoints = []
        for event_name, trigger_data in self.event_triggers.items():
            condition = trigger_data.get("condition", {})
            event_data = trigger_data.get("event_data", {})
            # 简单的章节触发检查
            if condition.get("type") == "chapter":
                trigger_chapter = condition.get("chapter", 0)
                if chapter_number == trigger_chapter:
                    checkpoints.append({
                        "trigger": f"章节触发: 第{chapter_number}章",
                        "description": f"可能触发事件: {event_name}",
                        "event": event_name,
                        "condition": condition
                    })
            # 前置事件完成触发
            elif condition.get("type") == "event_completion":
                prerequisite = condition.get("prerequisite_event")
                if self._is_prerequisite_met(prerequisite):
                    checkpoints.append({
                        "trigger": f"事件完成触发: {prerequisite}",
                        "description": f"可能触发事件: {event_name}",
                        "event": event_name,
                        "condition": condition
                    })
        return checkpoints
    def _is_prerequisite_met(self, prerequisite_event: str) -> bool:
        """检查前置事件条件是否满足"""
        for history_event in self.event_history:
            if history_event.get("name") == prerequisite_event and history_event.get("status") == "completed":
                return True
        return False
    def _calculate_chain_effects(self, chapter_number: int) -> List[Dict]:
        """计算事件链影响"""
        effects = []
        # 检查已完成事件对当前的影响
        for history_event in self.event_history[-5:]:  # 最近5个事件
            if history_event.get("aftermath_effects"):
                for effect in history_event["aftermath_effects"]:
                    if effect.get("duration", chapter_number) >= chapter_number:
                        effects.append({
                            "source_event": history_event.get("name", "未知事件"),
                            "description": effect.get("description", "未描述影响"),
                            "impact_level": effect.get("impact", "medium")
                        })
        return effects
    def _create_fallback_events(self, chapter_number: int):
        """创建回退事件 - 只创建重大事件和中型事件"""
        self.logger.info("🔄 创建回退事件...")
        # 创建一个重大事件
        major_event = {
            "name": "核心剧情推进",
            "type": "major_event",
            "main_goal": "推进主线故事发展",
            "start_chapter": max(1, chapter_number - 2),
            "end_chapter": chapter_number + 8,
            "key_moments": [
                f"第{chapter_number + 2}章: 关键发展点",
                f"第{chapter_number + 5}章: 重要转折"
            ],
            "status": "active",
            "started_chapter": max(1, chapter_number - 2),
            "current_progress": 0,
            "significance": "推动故事核心发展"
        }
        # 创建一个中型事件
        medium_event = {
            "name": "重要支线发展",
            "type": "medium_event",
            "main_goal": "发展支线情节",
            "start_chapter": chapter_number,
            "end_chapter": chapter_number + 5,
            "key_moments": [
                f"第{chapter_number + 1}章: 支线起始",
                f"第{chapter_number + 3}章: 支线发展"
            ],
            "status": "active",
            "started_chapter": chapter_number,
            "current_progress": 0,
            "connection_to_major": "补充主线情节"
        }
        self.active_events[major_event["name"]] = major_event
        self.active_events[medium_event["name"]] = medium_event
        self.logger.info(f"✅ 创建回退事件完成: 1个重大事件, 1个中型事件")
    def update_event_system(self):
        """更新事件系统 - 由NovelGenerator调用"""
        self.logger.info("🔄 EventDrivenManager: 更新事件系统")
        self.active_events.clear()
        self.logger.info("  ✅ 已清除所有旧事件")
    def add_event(self, name: str, event_type: str, start_chapter: int, description: str = "", impact_level: str = "medium"):
        """添加新事件 - 只支持重大事件和中型事件"""
        if event_type not in ["major_event", "medium_event"]:
            self.logger.info(f"❌ 不支持的事件类型: {event_type} {name} {description}，只支持 major_event 和 medium_event")
            return
        event = {
            "name": name,
            "type": event_type,
            "start_chapter": start_chapter,
            "started_chapter": start_chapter,
            "description": description,
            "impact_level": impact_level,
            "status": "active",
            "current_progress": 0,
            "key_moments": [],
            "main_goal": description or "推进故事发展"
        }
        # 设置默认结束章节
        if event_type == "major_event":
            event["end_chapter"] = start_chapter + 10
            event["significance"] = "重大转折点"
        else:  # medium_event
            event["end_chapter"] = start_chapter + 5
            event["connection_to_major"] = "关联主线情节"
        self.active_events[name] = event
        self.logger.info(f"  ✅ 添加{event_type}: {name} (起始章节: {start_chapter})")
    def _check_consecutive_high_intensity(self, chapter_number: int, threshold: int = 4) -> bool:
        """检查是否连续高强度章节过多"""
        consecutive_high = 0
        for i in range(max(1, chapter_number - threshold), chapter_number):
            consecutive_high = 0
        return consecutive_high >= threshold
    def _calculate_precise_buffer_periods(self, chapter_number: int) -> Dict[str, bool]:
        """精准计算各种缓冲期类型"""
        buffer_info = {
            "post_medium_event": False,      # 中型事件结束后
            "pre_major_event": False,     # 重大事件开始前
            "between_medium_events": False,  # 连续中型事件之间
            "is_buffer_period": False     # 总体是否缓冲期
        }
        self.logger.info(f"\n=== 第{chapter_number}章缓冲期计算开始 ===")
        # 获取当前活跃事件，按类型分组显示层级关系
        active_major_events = []
        active_medium_events = []
        for event_name, event_data in self.active_events.items():
            if self._is_event_active(chapter_number, event_data):
                if event_data.get("type") == "major_event":
                    active_major_events.append(event_data)
                elif event_data.get("type") == "medium_event":
                    active_medium_events.append(event_data)
        
        self.logger.info(f"当前活跃事件数量: {len(active_major_events) + len(active_medium_events)}")
        
        # 先显示重大事件
        for i, event in enumerate(active_major_events):
            self.logger.info(f"  🎯 重大事件{i+1}: {event.get('name', '未知事件')}")
            
            # 显示属于该重大事件的中型事件
            major_name = event.get('name')
            related_medium = [e for e in active_medium_events
                           if e.get('connection_to_major') == major_name]
            if related_medium:
                self.logger.info(f"     ├─ 包含 {len(related_medium)} 个中型事件:")
                for j, medium in enumerate(related_medium):
                    # 从medium_events中移除已显示的
                    if medium in active_medium_events:
                        active_medium_events.remove(medium)
                    self.logger.info(f"     │  {j+1}. {medium.get('name', '未知事件')}")
        
        # 显示独立的中型事件
        if active_medium_events:
            self.logger.info(f"  🔥 独立中型事件: {len(active_medium_events)}个")
            for i, event in enumerate(active_medium_events):
                self.logger.info(f"     {i+1}. {event.get('name', '未知事件')}")
        # 检查中型事件结束后的缓冲
        post_medium_event = self._is_post_medium_event_buffer(chapter_number)
        buffer_info["post_medium_event"] = post_medium_event
        self.logger.info(f"中型事件结束后缓冲: {post_medium_event}")
        # 检查重大事件开始前的缓冲
        pre_major_event = self._is_pre_major_event_buffer(chapter_number)
        buffer_info["pre_major_event"] = pre_major_event
        self.logger.info(f"重大事件开始前缓冲: {pre_major_event}")
        # 检查连续中型事件之间的缓冲
        between_medium_events = self._is_between_medium_events_buffer(chapter_number)
        buffer_info["between_medium_events"] = between_medium_events
        self.logger.info(f"连续中型事件之间缓冲: {between_medium_events}")
        # 总体缓冲期判断
        is_buffer_period = (
            post_medium_event or
            pre_major_event or
            between_medium_events
        )
        buffer_info["is_buffer_period"] = is_buffer_period
        self.logger.info(f"总体是否缓冲期: {is_buffer_period}")
        self.logger.info(f"=== 第{chapter_number}章缓冲期计算结束 ===\n")
        return buffer_info
    def _is_post_medium_event_buffer(self, chapter_number: int) -> bool:
        """检查是否在中型事件结束后的缓冲期"""
        # 检查前1章是否有中型事件结束
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "medium_event":
                end_chapter = event_data.get("end_chapter", 0)
                if chapter_number == end_chapter + 1 or chapter_number == end_chapter + 2:
                    return True
        return False
    def _is_pre_major_event_buffer(self, chapter_number: int) -> bool:
        """检查是否在重大事件开始前的缓冲期"""
        # 检查后1章是否有重大事件开始
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "major_event":
                start_chapter = event_data.get("start_chapter", 0)
                if chapter_number == start_chapter - 1 or chapter_number == start_chapter - 2:
                    return True
        return False
    def _is_between_medium_events_buffer(self, chapter_number: int) -> bool:
        """检查是否在连续中型事件之间的缓冲期"""
        # 检查是否在两个中型事件之间的第一章
        prev_medium_event_end = None
        next_medium_event_start = None
        # 查找前一个中型事件的结束章节
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "medium_event":
                end_chapter = event_data.get("end_chapter", 0)
                if end_chapter < chapter_number and (prev_medium_event_end is None or end_chapter > prev_medium_event_end):
                    prev_medium_event_end = end_chapter
        # 查找下一个中型事件的开始章节
        for event_name, event_data in self.active_events.items():
            if event_data.get("type") == "medium_event":
                start_chapter = event_data.get("start_chapter", 0)
                if start_chapter > chapter_number and (next_medium_event_start is None or start_chapter < next_medium_event_start):
                    next_medium_event_start = start_chapter
        # 如果当前章节正好是前一个中型事件结束后、下一个中型事件开始前的第一章
        if prev_medium_event_end and next_medium_event_start:
            if chapter_number == prev_medium_event_end + 1:
                return True
        return False
    def _generate_buffer_specific_tasks(self, chapter_number: int, buffer_info: Dict) -> List[Dict]:
        """生成缓冲期特定任务"""
        tasks = []
        if buffer_info["post_medium_event"]:
            tasks.extend([
                {
                    "event": "情绪缓冲",
                    "description": "展示角色对中型事件的反应和情感消化",
                    "priority": "high",
                    "type": "emotional_processing"
                },
                {
                    "event": "世界观展示",
                    "description": "通过日常场景丰富世界观细节",
                    "priority": "medium",
                    "type": "world_building"
                }
            ])
        elif buffer_info["pre_major_event"]:
            tasks.extend([
                {
                    "event": "氛围营造", 
                    "description": "通过环境描写和角色预感营造紧张氛围",
                    "priority": "high",
                    "type": "atmosphere_building"
                },
                {
                    "event": "伏笔铺设",
                    "description": "为即将到来的重大事件埋设关键伏笔", 
                    "priority": "high",
                    "type": "foreshadowing"
                }
            ])
        elif buffer_info["between_medium_events"]:
            tasks.extend([
                {
                    "event": "支线发展",
                    "description": "推进次要情节和配角发展",
                    "priority": "medium",
                    "type": "side_plot_development"
                },
                {
                    "event": "角色互动",
                    "description": "展示角色间的日常关系和互动",
                    "priority": "medium",
                    "type": "character_interaction"
                }
            ])
        return tasks
    def _get_extended_event_gap_prompt(self, chapter_number: int, event_context: Dict) -> str:
        """生成长时间空窗期的专门指导"""
        # 计算空窗期长度
        gap_length = self._calculate_event_gap_length(chapter_number)
        prompt_parts = [
            "# 🎯 事件执行指导 - 长时间事件空窗期",
            "",
            "## 📊 当前状态分析",
            f"第{chapter_number}章处于**长时间事件空窗期**，已经持续{gap_length}章没有活跃的重大事件或中型事件。",
            "这是安排系统性支线发展和世界观建设的绝佳时机。",
            ""
        ]
        # 长时间空窗期的系统性支线安排
        prompt_parts.extend([
            "## 🎪 系统性支线安排策略",
            f"由于空窗期较长({gap_length}章)，需要系统性安排支线内容："
        ])
        # 根据空窗期长度提供不同策略
        if gap_length >= 10:
            prompt_parts.extend(self._get_extended_gap_strategy(gap_length, chapter_number))
        elif gap_length >= 5:
            prompt_parts.extend(self._get_medium_gap_strategy(gap_length, chapter_number))
        else:
            prompt_parts.extend(self._get_short_gap_strategy(gap_length, chapter_number))
        # 检查是否有即将发生的事件需要铺垫
        upcoming_events = self._get_upcoming_events(chapter_number)
        if upcoming_events:
            prompt_parts.extend([
                "",
                "## 🔮 即将发生事件铺垫",
                "利用空窗期为后续事件做系统性铺垫:"
            ])
            for event in upcoming_events[:5]:  # 显示更多即将事件
                event_name = event.get('name', '未知事件')
                start_chapter = event.get('start_chapter', chapter_number + 1)
                event_type = "重大事件" if event.get('type') == 'major_event' else "中型事件"
                prompt_parts.append(f"- **{event_name}** ({event_type}, 预计第{start_chapter}章):")
                prompt_parts.append(f"  - 可埋下伏笔线索")
                prompt_parts.append(f"  - 引入相关角色")
                prompt_parts.append(f"  - 建立事件背景")
            prompt_parts.append("")
        # 长时间空窗期的核心任务建议
        prompt_parts.extend([
            "## 🎯 长时间空窗期核心任务",
            "1. **支线剧情推进**: 安排2-3条并行支线，交替推进",
            "2. **角色深度发展**: 为主角和配角安排个人成长弧线", 
            "3. **世界观扩展**: 系统性展示世界观的不同方面",
            "4. **伏笔网络建设**: 为后续事件建立复杂的伏笔网络",
            "5. **节奏控制**: 保持适当的紧张度，避免读者失去兴趣",
            "",
            "## 💡 长时间空窗期创作提示",
            "- **支线交替**: 不同支线交替出现，保持新鲜感",
            "- **渐进紧张**: 空窗期后期逐渐提升紧张度",
            "- **主线关联**: 所有支线都应与主线有明确关联",
            "- **伏笔回收**: 适当回收前期伏笔，建立闭环",
            "- **角色成长**: 确保角色在空窗期有明显成长",
            "- **读者期待**: 在空窗期结束时建立对后续事件的强烈期待"
        ])
        return "\n".join(prompt_parts)
    def _calculate_event_gap_length(self, chapter_number: int) -> int:
        """计算当前事件空窗期的长度"""
        gap_length = 0
        # 从当前章节向前检查，直到找到活跃事件
        for check_chapter in range(chapter_number, max(1, chapter_number - 20), -1):
            has_active_events = False
            for event_name, event_data in self.active_events.items():
                if self._is_event_active(check_chapter, event_data):
                    has_active_events = True
                    break
            if has_active_events:
                break
            else:
                gap_length += 1
        return gap_length
    def _get_extended_gap_strategy(self, gap_length: int, chapter_number: int) -> List[str]:
        """获取长时间空窗期(10+章)的策略"""
        return [
            "### 10+章空窗期策略 - 系统性支线建设",
            "",
            "**支线架构建议**:",
            "- 安排3条主要支线，每条支线持续3-4章",
            "- 支线之间建立关联，形成支线网络", 
            "- 每条支线都应有明确的目标和结局",
            "",
            "**具体安排**:",
            f"- **第{chapter_number}-{chapter_number+3}章**: 启动第一条支线，侧重角色发展",
            f"- **第{chapter_number+2}-{chapter_number+5}章**: 启动第二条支线，侧重世界观扩展",
            f"- **第{chapter_number+4}-{chapter_number+7}章**: 启动第三条支线，侧重技能/能力成长",
            f"- **第{chapter_number+6}-{chapter_number+9}章**: 支线交汇，为回归主线铺垫",
            f"- **第{chapter_number+8}-{chapter_number+10}章**: 逐步提升紧张度，准备回归主线",
            "",
            "**注意事项**:",
            "- 避免支线过于分散，保持整体连贯性",
            "- 定期提醒主线存在，保持读者对主线的记忆",
            "- 在空窗期结束前2-3章开始为主线回归做铺垫"
        ]
    def _get_medium_gap_strategy(self, gap_length: int, chapter_number: int) -> List[str]:
        """获取中等长度空窗期(5-9章)的策略"""
        return [
            "### 5-9章空窗期策略 - 重点支线发展",
            "",
            "**支线架构建议**:",
            "- 安排2条主要支线，交替推进",
            "- 每条支线应有明确的开始、发展、结束",
            "",
            "**具体安排**:",
            f"- **第{chapter_number}-{chapter_number+2}章**: 发展第一条支线",
            f"- **第{chapter_number+1}-{chapter_number+4}章**: 发展第二条支线", 
            f"- **第{chapter_number+3}-{chapter_number+5}章**: 支线收尾，为主线回归准备",
            "",
            "**重点任务**:",
            "- 深化配角发展",
            "- 补充世界观细节",
            "- 建立新的角色关系"
        ]
    def _get_short_gap_strategy(self, gap_length: int, chapter_number: int) -> List[str]:
        """获取短空窗期(1-4章)的策略"""
        return [
            "### 1-4章空窗期策略 - 紧凑支线安排",
            "",
            "**安排建议**:",
            "- 安排1-2条紧凑支线",
            "- 侧重情绪缓冲和伏笔铺设",
            "",
            "**可用内容**:",
            "- 角色反思和成长时刻",
            "- 世界观细节展示",
            "- 幽默或温馨的插曲",
            "- 为后续事件的直接铺垫"
        ]
    def create_side_quest_events(self, chapter_number: int, gap_length: int):
        """为空窗期创建支线事件"""
        if gap_length >= 5:
            self.logger.info(f"🎯 检测到{gap_length}章空窗期，自动创建支线事件...")
            # 根据空窗期长度创建不同数量的支线事件
            if gap_length >= 10:
                self._create_extended_side_quests(chapter_number)
            elif gap_length >= 5:
                self._create_medium_side_quests(chapter_number)
            self.logger.info(f"✅ 已为第{chapter_number}章创建支线事件")
    def _create_extended_side_quests(self, chapter_number: int):
        """创建长时间空窗期的支线事件"""
        # 角色发展支线
        self.add_event(
            name="角色深度发展支线",
            event_type="medium_event",
            start_chapter=chapter_number,
            description="深入探索主要角色的背景故事和个人成长"
        )
        # 世界观扩展支线
        self.add_event(
            name="世界观探索支线",
            event_type="medium_event",
            start_chapter=chapter_number + 2,
            description="系统性展示世界观的不同方面和文化细节"
        )
        # 技能成长支线
        self.add_event(
            name="能力成长支线",
            event_type="medium_event",
            start_chapter=chapter_number + 4,
            description="主角或配角获得新技能或能力的成长过程"
        )
    def _create_medium_side_quests(self, chapter_number: int):
        """创建中等长度空窗期的支线事件"""
        # 主要支线
        self.add_event(
            name="重要支线发展",
            event_type="medium_event",
            start_chapter=chapter_number,
            description="推进与主线相关的次要情节发展"
        )
        # 配角发展支线
        self.add_event(
            name="配角成长支线",
            event_type="medium_event",
            start_chapter=chapter_number + 1,
            description="深化配角角色弧线和人际关系"
        )          