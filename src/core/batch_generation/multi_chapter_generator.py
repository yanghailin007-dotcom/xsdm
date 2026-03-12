# -*- coding: utf-8 -*-
"""
多章批量内容生成器
基于中型事件一次性生成多章正文
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .writing_style_loader import WritingStyleGuideLoader, FormattedStyleGuide

logger = logging.getLogger(__name__)


@dataclass
class ChapterContent:
    """章节内容数据类"""
    chapter_number: int
    title: str
    content: str
    key_events: List[str]
    character_states: Dict[str, str]
    items_delta: Dict[str, str]
    time_progression: str


class MultiChapterContentGenerator:
    """
    多章批量内容生成器
    
    核心功能：
    1. 一次性为中型事件生成多章正文
    2. 自动加载写作风格指南
    3. 保持跨章连贯性
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
    
    def generate(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Dict[int, List[Dict]],
        consistency_guidance: str,
        novel_title: str,
        previous_state: Optional[Dict] = None,
        username: str = None
    ) -> Dict[int, ChapterContent]:
        """
        批量生成多章正文
        
        Args:
            medium_event: 中型事件数据
            chapter_range: (start_ch, end_ch) 章节范围
            scenes_by_chapter: {chapter_num: [scenes]} 每章场景列表
            consistency_guidance: 一致性指导
            novel_title: 小说标题（用于加载风格指南）
            previous_state: 前一中型事件的最终状态
            username: 用户名
            
        Returns:
            {chapter_num: ChapterContent} 生成的章节内容
        """
        start_ch, end_ch = chapter_range
        span = end_ch - start_ch + 1
        
        self.logger.info(f"[MultiChapterGen] 开始批量生成: {novel_title} 第{start_ch}-{end_ch}章, 跨度={span}")
        
        # 1. 加载写作风格指南
        style_guide = WritingStyleGuideLoader.load_and_format(novel_title, username)
        self.logger.info(f"[MultiChapterGen] 已加载风格指南: {style_guide.core_style[:50]}...")
        
        # 2. 构建Prompt
        prompt = self._build_prompt(
            medium_event=medium_event,
            chapter_range=chapter_range,
            scenes_by_chapter=scenes_by_chapter,
            consistency_guidance=consistency_guidance,
            style_guide=style_guide,
            previous_state=previous_state,
            novel_title=novel_title
        )
        
        # 3. 调用API生成（1次API调用=1创造点，无论生成多少章）
        self.logger.info(
            f"[MultiChapterGen] 调用API批量生成{span}章内容... "
            f"(预计消耗1创造点，节省{span - 1}点)"
        )
        
        # 获取API调用前的计数
        api_calls_before = getattr(self.api_client, 'api_call_counter', 0)
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="multi_chapter_content",
                user_prompt=prompt,
                purpose=f"批量生成{novel_title}第{start_ch}-{end_ch}章"
            )
            
            # 计算实际消耗的API调用次数
            api_calls_after = getattr(self.api_client, 'api_call_counter', api_calls_before + 1)
            api_calls_consumed = api_calls_after - api_calls_before
            points_saved = span - api_calls_consumed  # 相比逐章生成节省的点数
            
            if not result:
                raise ValueError("API返回为空")
            
            # 4. 解析结果
            chapters_data = self._parse_result(result, chapter_range)
            
            self.logger.info(
                f"[MultiChapterGen] 批量生成成功: {len(chapters_data)}章, "
                f"消耗{api_calls_consumed}创造点, 节省{points_saved}点"
            )
            return chapters_data
            
        except Exception as e:
            self.logger.error(f"[MultiChapterGen] 批量生成失败: {e}")
            raise
    
    def _build_prompt(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Dict[int, List[Dict]],
        consistency_guidance: str,
        style_guide: FormattedStyleGuide,
        previous_state: Optional[Dict],
        novel_title: str
    ) -> str:
        """构建多章生成Prompt"""
        start_ch, end_ch = chapter_range
        
        # 格式化场景规划
        scenes_formatted = self._format_scenes(scenes_by_chapter)
        
        # 构建跨章连贯指导
        cross_chapter_guide = self._build_cross_chapter_guide(scenes_by_chapter)
        
        # 前一事件状态
        previous_state_str = json.dumps(previous_state, ensure_ascii=False, indent=2) if previous_state else "无"
        
        prompt = f"""# 角色: {style_guide.core_style}

你正在创作小说《{novel_title}》。请基于提供的场景规划，一次性为连续的多章创作正文。

{style_guide.key_principles}

## 语言与叙事规范
{style_guide.language_characteristics}

{style_guide.narration_techniques}

## 章节写作技巧
{style_guide.chapter_techniques}

{style_guide.dialogue_style}

{style_guide.interaction_design}

## 一致性铁律（必须严格遵守）
{consistency_guidance}

## 中型事件信息
- **事件名称**: {medium_event.get('name', 'Unknown')}
- **事件目标**: {medium_event.get('main_goal', '')}
- **章节范围**: 第{start_ch}-{end_ch}章
- **情感重点**: {medium_event.get('emotional_focus', '')}

## 场景规划
{scenes_formatted}

## 跨章连贯指导
{cross_chapter_guide}

## 前一事件状态（本章起点）
{previous_state_str}

## 写作要求
1. **自由创作**: 基于场景自由发挥，不强制固定行文格式
2. **连贯优先**: 跨章节的角色状态、时间线必须一致
3. **节奏自然**: 根据场景的情绪强度自然调整叙事节奏
4. **细节丰富**: 感官描写、心理活动、对话都要有
5. **番茄风格**: 短段落、快节奏、强卡点

## 输出格式
请严格按照以下JSON格式返回：

```json
{{
  "chapters": [
    {{
      "chapter_number": {start_ch},
      "title": "章节标题（10-15字，有吸引力）",
      "content": "正文内容（2000-3000字）。注意：段落要短，适合手机阅读。情绪外显，通过动作对话体现。每章结尾要有强力卡点。",
      "key_events": ["本章关键事件1", "事件2"],
      "character_states": {{"角色名": "本章结束时的状态"}},
      "items_delta": {{"物品名": "变化描述（如'获得'/'使用'/'损坏'）"}},
      "time_progression": "时间推进（如'1天'/'3小时'）"
    }}
    {self._build_chapter_placeholders(start_ch + 1, end_ch)}
  ],
  "cross_chapter_notes": "跨章连贯性说明，如时间线、角色发展等"
}}
```

重要提示：
- 总共生成{end_ch - start_ch + 1}章，必须完整返回
- 每章2000-3000字
- 章节之间必须连贯，前一章结尾状态 = 后一章起始状态
- 每章结尾必须有卡点（悬念/情绪/冲突/期待）
- 严格遵循一致性铁律，不得出现矛盾
"""
        return prompt
    
    def _format_scenes(self, scenes_by_chapter: Dict[int, List[Dict]]) -> str:
        """格式化场景为Prompt友好形式"""
        lines = []
        
        for ch_num in sorted(scenes_by_chapter.keys()):
            scenes = scenes_by_chapter[ch_num]
            lines.append(f"\n### 第{ch_num}章场景")
            
            for i, scene in enumerate(scenes, 1):
                name = scene.get('name', f'场景{i}')
                position = scene.get('position', 'unknown')
                purpose = scene.get('purpose', '')
                intensity = scene.get('emotional_intensity', 'medium')
                actions = scene.get('key_actions', [])
                
                lines.append(f"""
{i}. **{name}** ({position})
   - 目标: {purpose}
   - 情绪强度: {intensity}
   - 关键动作: {', '.join(actions) if actions else '详见场景描述'}
""")
        
        return "\n".join(lines)
    
    def _build_cross_chapter_guide(self, scenes_by_chapter: Dict[int, List[Dict]]) -> str:
        """构建跨章连贯指导"""
        lines = []
        chapters = sorted(scenes_by_chapter.keys())
        
        for i in range(len(chapters) - 1):
            curr_ch = chapters[i]
            next_ch = chapters[i + 1]
            
            curr_scenes = scenes_by_chapter[curr_ch]
            next_scenes = scenes_by_chapter[next_ch]
            
            if curr_scenes and next_scenes:
                curr_ending = curr_scenes[-1].get('name', '结尾')
                next_opening = next_scenes[0].get('name', '开头')
                
                lines.append(f"""
【第{curr_ch}章 → 第{next_ch}章】
- 第{curr_ch}章结尾: {curr_ending}
- 第{next_ch}章开头: {next_opening}
- 衔接要求: 确保角色状态、地点、时间连贯
""")
        
        return "\n".join(lines) if lines else "无明显跨章衔接要求"
    
    def _build_chapter_placeholders(self, start: int, end: int) -> str:
        """构建后续章节的占位符示例"""
        if start > end:
            return ""
        
        placeholders = []
        for ch in range(start, min(end + 1, start + 2)):  # 最多显示2个示例
            placeholders.append(f"""
    ,{{
      "chapter_number": {ch},
      "title": "...",
      "content": "...",
      "key_events": ["..."],
      "character_states": {{}},
      "items_delta": {{}},
      "time_progression": "..."
    }}""")
        
        if end > start + 1:
            placeholders.append(f"\n    // ... 第{start + 2}-{end}章类似格式")
        
        return "\n".join(placeholders)
    
    def _parse_result(
        self,
        result: Dict,
        chapter_range: Tuple[int, int]
    ) -> Dict[int, ChapterContent]:
        """解析API返回结果为ChapterContent对象"""
        chapters_data = {}
        
        chapters_list = result.get("chapters", [])
        
        for ch_data in chapters_list:
            ch_num = ch_data.get("chapter_number")
            if not ch_num:
                continue
            
            content = ChapterContent(
                chapter_number=ch_num,
                title=ch_data.get("title", f"第{ch_num}章"),
                content=ch_data.get("content", ""),
                key_events=ch_data.get("key_events", []),
                character_states=ch_data.get("character_states", {}),
                items_delta=ch_data.get("items_delta", {}),
                time_progression=ch_data.get("time_progression", "0天")
            )
            
            chapters_data[ch_num] = content
        
        # 验证是否所有章节都生成了
        start_ch, end_ch = chapter_range
        for ch in range(start_ch, end_ch + 1):
            if ch not in chapters_data:
                self.logger.warning(f"[MultiChapterGen] 第{ch}章缺失于生成结果中")
        
        return chapters_data


# 便捷函数
def generate_multi_chapter_content(
    api_client,
    medium_event: Dict,
    chapter_range: Tuple[int, int],
    scenes_by_chapter: Dict[int, List[Dict]],
    consistency_guidance: str,
    novel_title: str,
    **kwargs
) -> Dict[int, ChapterContent]:
    """
    便捷函数：批量生成多章内容
    
    使用示例:
    result = generate_multi_chapter_content(
        api_client=api_client,
        medium_event=medium_event,
        chapter_range=(5, 7),
        scenes_by_chapter=scenes,
        consistency_guidance=guidance,
        novel_title="凡人修仙传",
        username="user1"
    )
    
    for ch_num, content in result.items():
        print(f"第{ch_num}章: {content.title}")
        print(f"字数: {len(content.content)}")
    """
    generator = MultiChapterContentGenerator(api_client)
    return generator.generate(
        medium_event=medium_event,
        chapter_range=chapter_range,
        scenes_by_chapter=scenes_by_chapter,
        consistency_guidance=consistency_guidance,
        novel_title=novel_title,
        **kwargs
    )
