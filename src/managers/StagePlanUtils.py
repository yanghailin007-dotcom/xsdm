"""StagePlanManager 的工具函数模块
包含所有辅助函数和工具方法
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import re
from typing import Dict, List, Tuple
from src.utils.logger import get_logger
def parse_chapter_range(chapter_range: str) -> Tuple[int, int]:
    """解析章节范围字符串，返回(start, end)元组"""
    if not chapter_range:
        return 1, 1
    # 提取所有数字
    numbers = re.findall(r'\d+', chapter_range)
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        return int(numbers[0]), int(numbers[0])
    else:
        return 1, 1
def is_chapter_in_range(chapter_number: int, chapter_range: str) -> bool:
    """检查章节是否在指定范围内"""
    start_chap, end_chap = parse_chapter_range(chapter_range)
    return start_chap <= chapter_number <= end_chap
def calculate_stage_boundaries(total_chapters: int) -> Dict:
    """计算阶段边界 - 独立工具函数"""
    ratios = [0.16, 0.26, 0.28, 0.18, 0.12]  # 确保总和为1.0
    # 计算累积章节数，确保不重叠
    chapters = [0]
    for ratio in ratios:
        chapters.append(chapters[-1] + int(total_chapters * ratio))
    # 确保最后一个章节等于总章节数
    chapters[-1] = total_chapters
    return {
        "opening_end": chapters[1],
        "development_start": chapters[1] + 1,
        "development_end": chapters[2], 
        "climax_start": chapters[2] + 1,
        "climax_end": chapters[3],
        "ending_start": chapters[3] + 1,
        "ending_end": chapters[4],
        "final_start": chapters[4] + 1
    }
def validate_event_structure(events: Dict) -> bool:
    """验证事件结构完整性"""
    required_keys = {
        "major_events": ["name", "start_chapter", "end_chapter"],
        "medium_events": ["name", "chapter"],
        "minor_events": ["name", "chapter"]
    }
    for event_type, required in required_keys.items():
        if event_type in events:
            for event in events[event_type]:
                for key in required:
                    if key not in event:
                        return False
    return True
def sort_events_by_chapter(events: Dict) -> Dict:
    """按章节排序事件"""
    for event_type in ["major_events", "medium_events", "minor_events"]:
        if event_type in events:
            if event_type == "major_events":
                events[event_type] = sorted(events[event_type], key=lambda x: x.get('start_chapter', 0))
            else:
                events[event_type] = sorted(events[event_type], key=lambda x: x.get('chapter', 0))
    return events
def calculate_optimal_event_density(stage_length: int) -> Dict:
    """根据阶段长度智能计算最优事件密度"""
    if stage_length <= 20:
        # 短阶段：减少事件数量
        return {
            "major_events": max(1, stage_length // 20),
            "medium_events": max(2, stage_length // 10),
            "minor_events": max(3, stage_length // 6)
        }
    elif stage_length <= 40:
        # 中等阶段：适中密度
        return {
            "major_events": max(1, stage_length // 15),
            "medium_events": max(2, stage_length // 8),
            "minor_events": max(3, stage_length // 5)
        }
    else:
        # 长阶段：控制最大数量，避免过度复杂
        return {
            "major_events": min(5, stage_length // 15),  # 最多5个重大事件
            "medium_events": min(8, stage_length // 8),  # 最多8个中型事件
            "minor_events": min(12, stage_length // 5)   # 最多12个小型事件
        }
def build_event_chains(events: List) -> List:
    """构建事件链条，确保逻辑连贯"""
    if not events:
        return []
    chains = []
    current_chain = []
    for event in sorted(events, key=lambda x: x.get('start_chapter', 0)):
        if not current_chain:
            current_chain.append(event)
        else:
            last_event = current_chain[-1]
            # 检查事件是否连贯
            last_event_end = last_event.get('end_chapter', last_event.get('start_chapter', 0))
            current_event_start = event.get('start_chapter', 0)
            if current_event_start - last_event_end <= 5:
                current_chain.append(event)
            else:
                chains.append(current_chain)
                current_chain = [event]
    if current_chain:
        chains.append(current_chain)
    return chains
def calculate_max_event_gap(events: List) -> int:
    """计算最大事件间隔"""
    if not events:
        return 999  # 没有事件，间隔极大
    # 按开始章节排序
    sorted_events = sorted(events, key=lambda x: x.get('start_chapter', 0))
    max_gap = 0
    # 检查第一个事件之前的间隔（假设阶段从第1章开始）
    first_event_start = sorted_events[0].get('start_chapter', 1)
    if first_event_start > 1:
        max_gap = max(max_gap, first_event_start - 1)
    # 检查事件之间的间隔
    for i in range(1, len(sorted_events)):
        prev_event = sorted_events[i-1]
        current_event = sorted_events[i]
        prev_event_end = prev_event.get('end_chapter', prev_event.get('start_chapter', 0))
        current_event_start = current_event.get('start_chapter', 0)
        gap = current_event_start - prev_event_end - 1
        max_gap = max(max_gap, gap)
    return max_gap
def extract_plot_advice(guidance: Dict) -> Dict:
    """从指导中提取情节建议"""
    writing_focus = guidance.get("writing_focus", "")
    key_tasks = guidance.get("key_tasks", [])
    plot_advice = {}
    # 基于写作重点生成情节建议
    if "冲突" in writing_focus:
        plot_advice["conflict_design"] = "重点设计或推进冲突"
    if "高潮" in writing_focus:
        plot_advice["climax_point"] = "设置情感或情节高潮"
    if "悬念" in writing_focus:
        plot_advice["ending_approach"] = "设置悬念吸引继续阅读"
    return plot_advice
def extract_character_advice(guidance: Dict) -> Dict:
    """从指导中提取角色建议"""
    writing_focus = guidance.get("writing_focus", "")
    key_tasks = guidance.get("key_tasks", [])
    character_advice = {}
    # 基于写作重点生成角色建议
    if any(task in writing_focus for task in ["角色", "人物", "主角"]):
        character_advice["protagonist_development"] = "重点展现主角成长"
    if any(task in writing_focus for task in ["配角", "关系", "互动"]):
        character_advice["supporting_characters_focus"] = "发展配角关系"
    # 从关键任务中提取
    for task in key_tasks:
        if "角色" in task or "人物" in task:
            character_advice["protagonist_development"] = task
        if "关系" in task or "互动" in task:
            character_advice["supporting_characters_focus"] = task
    return character_advice
def create_default_emotional_profile(stage_name: str) -> Dict:
    """创建默认的情绪特征配置"""
    stage_emotional_profiles = {
        "opening_stage": {
            "goal": "建立情感连接和读者认同",
            "pace": "逐步加强情感投入",
            "intensity": "低到中"
        },
        "development_stage": {
            "goal": "深化情感冲突和发展关系",
            "pace": "起伏变化，快慢结合", 
            "intensity": "中"
        },
        "climax_stage": {
            "goal": "情感爆发和高潮体验",
            "pace": "紧张加速，高潮集中",
            "intensity": "高"
        },
        "ending_stage": {
            "goal": "情感解决和成长体现",
            "pace": "逐渐放缓，情感升华",
            "intensity": "中到高"
        },
        "final_stage": {
            "goal": "情感圆满和主题共鸣",
            "pace": "平稳深沉，余韵绵长",
            "intensity": "中"
        }
    }
    return stage_emotional_profiles.get(stage_name, {
        "goal": "情感发展和角色成长",
        "pace": "自然流畅",
        "intensity": "中"
    })
def format_writing_plan_summary(writing_plan: Dict) -> str:
    """格式化写作计划摘要"""
    if not writing_plan:
        return "无写作计划数据"
    # 检查嵌套结构
    if "stage_writing_plan" in writing_plan:
        actual_plan = writing_plan["stage_writing_plan"]
    else:
        actual_plan = writing_plan
    stage_name = actual_plan.get("stage_name", "未知阶段")
    event_system = actual_plan.get("event_system", {})
    major_events = event_system.get("major_events", [])
    summary = f"🎬 {stage_name}写作计划摘要:\n"
    summary += f"   重大事件: {len(major_events)}个\n"
    # 添加事件详情
    if major_events:
        for i, event in enumerate(major_events):
            summary += f"   📌 {event.get('name', '无名事件')}: 第{event.get('start_chapter', '?')}-{event.get('end_chapter', '?')}章\n"
    return summary
def validate_emotional_range(chapter: int, chapter_range: str) -> bool:
    """验证章节是否在情绪范围内"""
    if not chapter_range or "-" not in chapter_range:
        return False
    try:
        # 处理 "4-6章" 这样的格式 - 只提取数字部分
        range_str = chapter_range.replace("章", "").strip()
        # 使用正则表达式只提取数字部分，忽略括号注释等
        numbers = re.findall(r'\d+', range_str)
        if len(numbers) < 2:
            return False
        start_chap = int(numbers[0])
        end_chap = int(numbers[1])
        return start_chap <= chapter <= end_chap
    except Exception:
        return False
def is_near_turning_point(chapter: int, approx_chapter: str) -> bool:
    """检查章节是否接近转折点"""
    if not approx_chapter:
        return False
    try:
        # 使用正则表达式提取所有数字
        numbers = re.findall(r'\d+', approx_chapter)
        # 检查是否有匹配的章节号
        for num_str in numbers:
            chap_num = int(num_str)
            if abs(chapter - chap_num) <= 2:  # 前后2章内视为接近
                return True
        return False
    except Exception:
        return False