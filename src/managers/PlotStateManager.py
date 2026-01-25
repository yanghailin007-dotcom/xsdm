"""
情节状态管理器 - 跟踪已完成情节，防止内容重复
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum
import re

class PlotPointStatus(Enum):
    """情节点状态"""
    UNUSED = "unused"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@dataclass
class PlotPoint:
    """情节点 - 最小的不可分割情节单元"""
    id: str
    name: str
    keywords: List[str]
    status: PlotPointStatus = PlotPointStatus.UNUSED
    completed_in_chapter: Optional[int] = None
    completed_in_event: Optional[str] = None

@dataclass
class EventState:
    """事件状态 - 记录一个事件完成后的故事状态"""
    event_name: str
    event_id: str
    chapter_range: str
    completed_plot_points: List[str] = field(default_factory=list)
    established_facts: List[str] = field(default_factory=list)
    character_states: Dict[str, str] = field(default_factory=dict)
    forbidden_for_future: List[str] = field(default_factory=list)


class PlotStateManager:
    """情节状态管理器 - 跟踪已完成情节，防止内容重复"""
    
    CORE_PLOT_KEYWORDS = {
        "退婚", "系统觉醒", "系统开启", "金手指激活", 
        "初次突破", "第一次杀人", "初遇女主", "加入宗门",
        "第一次秘境", "第一次大比", "第一次复仇",
        "开局", "穿越", "重生", "绑定系统"
    }
    
    def __init__(self):
        self.tracked_plot_points = {}
        self.event_state_chain = []
        self.forbidden_plot_patterns = set()    
    def register_plot_points_from_events(self, major_events):
        """从重大事件中注册所有情节点"""
        for event in major_events:
            self._extract_plot_points_from_event(event)
    
    def _extract_plot_points_from_event(self, event):
        """从事件中提取情节点"""
        event_name = event.get("name", "")
        main_goal = event.get("main_goal", "")
        chapter_range = event.get("chapter_range", "")
        combined_text = f"{event_name} {main_goal}"
        for keyword in self.CORE_PLOT_KEYWORDS:
            if keyword in combined_text:
                plot_id = f"{keyword}_{chapter_range}"
                if plot_id not in self.tracked_plot_points:
                    self.tracked_plot_points[plot_id] = PlotPoint(
                        id=plot_id,
                        name=keyword,
                        keywords=[keyword],
                        status=PlotPointStatus.IN_PROGRESS
                    )
    
    def mark_event_completed(self, event, event_index):
        """标记一个事件已完成，记录状态"""
        event_name = event.get("name", "")
        chapter_range = event.get("chapter_range", "")
        completed_plots = []
        for plot_id, plot_point in self.tracked_plot_points.items():
            if plot_point.status == PlotPointStatus.IN_PROGRESS:
                if self._event_completes_plot(event, plot_point):
                    plot_point.status = PlotPointStatus.COMPLETED
                    plot_point.completed_in_event = event_name
                    completed_plots.append(plot_id)
        event_state = EventState(
            event_name=event_name,
            event_id=f"event_{event_index}",
            chapter_range=chapter_range,
            completed_plot_points=completed_plots,
            forbidden_for_future=self._extract_forbidden_plots(event)
        )
        self.event_state_chain.append(event_state)
        return event_state
    
    def _event_completes_plot(self, event, plot_point):
        """检查事件是否完成了指定情节"""
        event_text = " ".join([
            event.get("name", ""),
            event.get("main_goal", ""),
            event.get("emotional_arc_summary", "")
        ])
        for keyword in plot_point.keywords:
            if keyword in event_text:
                return True
        return False
    
    def _extract_forbidden_plots(self, event):
        """从事件中提取禁止未来重复的情节"""
        forbidden = []
        event_text = " ".join([
            event.get("name", ""),
            event.get("main_goal", "")
        ]).lower()
        for keyword in self.CORE_PLOT_KEYWORDS:
            if keyword in event_text:
                forbidden.append(keyword)
        return forbidden    
    def get_forbidden_plots_for_next_event(self):
        """获取下一个事件禁止使用的情节"""
        if not self.event_state_chain:
            return []
        forbidden = set()
        for state in self.event_state_chain:
            forbidden.update(state.forbidden_for_future)
        return list(forbidden)
    
    def get_context_for_next_event(self, previous_events):
        """为下一个事件生成上下文约束"""
        if not self.event_state_chain:
            return "这是第一个事件，可以自由设计情节。"
        forbidden_plots = self.get_forbidden_plots_for_next_event()
        completed_plots = []
        for state in self.event_state_chain:
            completed_plots.extend([
                self.tracked_plot_points[pid].name 
                for pid in state.completed_plot_points 
                if pid in self.tracked_plot_points
            ])
        context_parts = [
            "# 情节约束（必须严格遵守）",
            "",
            "## 已完成的核心情节（禁止重复）："
        ]
        if completed_plots:
            for plot in completed_plots:
                context_parts.append(f"- {plot}（已完成，不要再次设计）")
        else:
            context_parts.append("- （暂无）")
        context_parts.append("")
        context_parts.append("## 禁止使用的情节模式：")
        if forbidden_plots:
            for plot in forbidden_plots:
                context_parts.append(f"- {plot}（已在之前事件中使用，绝对禁止重复）")
        else:
            context_parts.append("- （暂无）")
        context_parts.append("")
        context_parts.append("**重要提示**：设计本事件时，必须避免与上述已完成情节产生任何形式的重复。")
        return "\n".join(context_parts)
    
    def check_plot_duplication(self, new_event):
        """检查新事件是否与已有情节重复"""
        issues = []
        new_event_text = " ".join([
            new_event.get("name", ""),
            new_event.get("main_goal", "")
        ]).lower()
        for keyword in self.get_forbidden_plots_for_next_event():
            if keyword in new_event_text:
                issues.append(f"事件包含已完成的情节：'{keyword}'")
        return issues
    def analyze_event_overlap(self, event1, event2):
        """分析两个事件之间的内容重叠度"""
        text1 = " ".join([
            event1.get("name", ""),
            event1.get("main_goal", ""),
            event1.get("emotional_arc_summary", "")
        ]).lower()
        text2 = " ".join([
            event2.get("name", ""),
            event2.get("main_goal", ""),
            event2.get("emotional_arc_summary", "")
        ]).lower()
        overlap_keywords = []
        for keyword in self.CORE_PLOT_KEYWORDS:
            if keyword in text1 and keyword in text2:
                overlap_keywords.append(keyword)
        overlap_score = len(overlap_keywords)
        return {
            "overlap_keywords": overlap_keywords,
            "overlap_score": overlap_score,
            "has_critical_overlap": overlap_score > 0,
            "event1_name": event1.get("name", ""),
            "event2_name": event2.get("name", "")
        }
    
    def get_state_summary(self):
        """获取状态摘要"""
        return {
            "total_tracked_plots": len(self.tracked_plot_points),
            "completed_plots": len([p for p in self.tracked_plot_points.values() if p.status == PlotPointStatus.COMPLETED]),
            "in_progress_plots": len([p for p in self.tracked_plot_points.values() if p.status == PlotPointStatus.IN_PROGRESS]),
            "events_processed": len(self.event_state_chain),
            "forbidden_patterns": list(self.forbidden_plot_patterns)
        }