import json
from pathlib import Path

path = Path('prompt_packages/_base/system_components/session_mode_prompts.json')
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['prompts']['stage_detail_single'] = """请执行【步骤：单个阶段详细写作计划】

当前阶段：{stage_name}（{chapter_range}，共 {chapter_count} 章）

## 阶段核心设定
- 核心冲突: {core_conflict}
- 情绪重点: {emotional_focus}
- 成长目标: {growth_goals}
- 关键事件: {key_events}

## 详细程度要求
{detail_level}

## 输出要求
返回合法 JSON，顶层字段为阶段名称 \"{stage_name}\"，值为对象，必须包含：
- \"opening_hook\": 开局钩子设计（字符串，50字以内）
- \"chapter_breakdown\": 章节细纲列表（对象列表），每个元素包含:
  - chapter_num: 章节号（整数或范围字符串，如 \"21-30\")
  - title: 章节标题（字符串）
  - key_events: 关键事件（字符串，30字以内）
  - emotional_beats: 情绪节奏（字符串，10字以内，如\"压抑→爆发\")
  - plot_progression: 剧情推进点（字符串，30字以内）
  - suspense_setup: 悬念设置（字符串，20字以内）
- \"cliffhanger\": 阶段结尾悬念（字符串，30字以内）
- \"transition_to_next\": 与下阶段衔接（字符串，30字以内）

【重要】总输出必须精简，避免冗长描述。禁止添加任何非规定字段。"""

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Updated {path}, total prompts: {len(data["prompts"])}')
