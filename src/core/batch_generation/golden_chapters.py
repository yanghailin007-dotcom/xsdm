# -*- coding: utf-8 -*-
"""
黄金三章整体生成器

黄金三章（第1-3章）必须作为一个整体一次性生成，确保：
1. 开篇钩子连贯延续
2. 角色状态自然过渡
3. 故事节奏流畅
4. 情绪弧线完整
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .writing_style_loader import WritingStyleGuideLoader
from .multi_chapter_generator import ChapterContent

logger = logging.getLogger(__name__)


class GoldenChaptersGenerator:
    """
    黄金三章整体生成器
    
    第1-3章一次性生成，保证开篇的连贯性和吸引力
    """
    
    # 黄金三章固定范围
    GOLDEN_RANGE = (1, 3)
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
    
    def is_golden_chapters(self, chapter_range: Tuple[int, int]) -> bool:
        """判断是否为黄金三章"""
        start, end = chapter_range
        return start == 1 and end >= 2  # 包含第1章且至少到第2章
    
    def generate(
        self,
        novel_data: Dict,
        creative_seed: Dict,
        selected_plan: Dict,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None,
        username: str = None
    ) -> Dict[int, ChapterContent]:
        """
        整体生成黄金三章
        
        Args:
            novel_data: 小说数据
            creative_seed: 创意种子
            selected_plan: 选定方案
            scenes_by_chapter: 预生成的场景
            username: 用户名
            
        Returns:
            {1: ch1, 2: ch2, 3: ch3} 三章内容
        """
        novel_title = novel_data.get("novel_title", "Unknown")
        
        self.logger.info(
            f"[GoldenChapters] 开始整体生成黄金三章: {novel_title}"
        )
        
        # 1. 加载风格指南
        style_guide = WritingStyleGuideLoader.load_and_format(novel_title, username)
        
        # 2. 构建黄金三章专用Prompt
        prompt = self._build_golden_prompt(
            novel_title=novel_title,
            creative_seed=creative_seed,
            selected_plan=selected_plan,
            style_guide=style_guide,
            scenes_by_chapter=scenes_by_chapter
        )
        
        # 3. 调用API一次性生成三章
        self.logger.info(f"[GoldenChapters] 调用API整体生成黄金三章...")
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="chapter_content_generation",
                user_prompt=prompt,
                purpose=f"整体生成《{novel_title}》黄金三章",
                chapter_number=1
            )
            
            if not result:
                raise ValueError("API返回为空")
            
            # 4. 解析结果
            chapters_data = self._parse_golden_result(result)
            
            self.logger.info(
                f"[GoldenChapters] 黄金三章生成成功: "
                f"{len(chapters_data)}章"
            )
            
            return chapters_data
            
        except Exception as e:
            self.logger.error(f"[GoldenChapters] 生成失败: {e}")
            raise
    
    def _build_golden_prompt(
        self,
        novel_title: str,
        creative_seed: Dict,
        selected_plan: Dict,
        style_guide: Any,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]]
    ) -> str:
        """构建黄金三章专用Prompt"""
        
        # 🔥 修复：确保 selected_plan 是字典而不是列表
        if isinstance(selected_plan, list):
            self.logger.warning(f"[GoldenChapters] selected_plan 是列表而非字典，使用空字典替代")
            selected_plan = {}
        elif not isinstance(selected_plan, dict):
            self.logger.warning(f"[GoldenChapters] selected_plan 类型错误: {type(selected_plan)}，使用空字典替代")
            selected_plan = {}
        
        # 提取核心设定
        core_settings = selected_plan.get("core_settings", {}) if isinstance(selected_plan, dict) else {}
        story_development = selected_plan.get("story_development", {}) if isinstance(selected_plan, dict) else {}
        
        world_background = core_settings.get("world_background", "")
        golden_finger = core_settings.get("golden_finger", "")
        core_selling_points = core_settings.get("core_selling_points", [])
        protagonist_position = story_development.get("protagonist_position", "")
        
        # 格式化场景
        scenes_formatted = self._format_scenes(scenes_by_chapter)
        
        prompt = f"""# 角色: {style_guide.core_style}

你正在创作小说《{novel_title}》的开篇黄金三章。这是小说最重要的部分，必须一次性整体生成，确保三章连贯、节奏紧凑、吸引力强。

{style_guide.key_principles}

## 黄金三章核心要求

### 整体目标
黄金三章必须完成以下目标：
1. **第1章**: 快速建立情境，引入核心冲突，激活金手指/系统
2. **第2章**: 展示金手指效果，小试牛刀，建立期待感
3. **第3章**: 第一次小高潮/打脸，释放爽感，留下强钩子

### 连贯性要求
- 三章必须有清晰的情绪弧线：压抑→好奇→兴奋→满足→期待
- 角色状态自然过渡：普通人→发现金手指→初步掌握→第一次成功
- 伏笔与呼应：第1章埋下的伏笔，第3章必须有回应

## 写作规范
{style_guide.language_characteristics}

{style_guide.narration_techniques}

{style_guide.chapter_techniques}

## 小说核心设定

**世界观背景**:
{world_background}

**金手指/系统**:
{golden_finger}

**核心爽点**:
{chr(10).join(f"- {point}" for point in core_selling_points)}

**主角定位**:
{protagonist_position}

## 场景规划（参考）
{scenes_formatted}

## 黄金三章具体设计

### 第1章设计要点
- **开篇**: 3句话内抓住读者，强烈冲突或悬念
- **主角登场**: 清晰展示处境和困境
- **金手指激活**: 自然、有戏剧性
- **结尾卡点**: 金手指刚刚激活，读者期待效果

### 第2章设计要点
- **承接**: 主角意识到金手指的作用
- **初次尝试**: 小范围测试金手指效果
- **周围反应**: 他人对主角变化的反应（惊讶/怀疑）
- **结尾卡点**: 即将面临第一个挑战/冲突

### 第3章设计要点
- **冲突爆发**: 利用金手指应对第一个挑战
- **打脸/反转**: 从被轻视到震惊他人
- **爽点释放**: 读者期待得到满足
- **强钩子**: 为第4章埋下更大的期待

## 输出格式

请严格按照以下JSON格式返回黄金三章的完整内容：

```json
{{
  "golden_chapters": {{
    "overall_arc": "三章整体情绪弧线描述",
    "foreshadowing": ["伏笔1", "伏笔2"],
    "payoff": "第3章如何回应第1章的设定"
  }},
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "第1章标题（10-15字，强吸引力）",
      "content": "第1章正文（2500-3000字）。注意：开篇强力，快速进入冲突，激活金手指，结尾卡点。",
      "key_events": ["事件1", "事件2"],
      "character_states": {{"主角名": "获得金手指"}},
      "items_delta": {{"金手指名": "激活"}},
      "time_progression": "时间推进",
      "hook_type": "悬念型/情绪型/冲突型/期待型",
      "hook_description": "卡点具体内容"
    }},
    {{
      "chapter_number": 2,
      "title": "第2章标题",
      "content": "第2章正文（2500-3000字）。承接第1章，测试金手指，周围反应，结尾卡点。",
      "key_events": ["事件1", "事件2"],
      "character_states": {{"主角名": "初步掌握金手指"}},
      "items_delta": {{}},
      "time_progression": "时间推进",
      "hook_type": "期待型",
      "hook_description": "即将面对挑战"
    }},
    {{
      "chapter_number": 3,
      "title": "第3章标题",
      "content": "第3章正文（2500-3000字）。冲突爆发，打脸/反转，爽点释放，强钩子结尾。",
      "key_events": ["事件1", "事件2", "事件3"],
      "character_states": {{"主角名": "第一次成功"}},
      "items_delta": {{}},
      "time_progression": "时间推进",
      "hook_type": "悬念型",
      "hook_description": "更大的挑战/秘密即将揭晓"
    }}
  ]
}}
```

## 重要提醒

1. **必须一次性生成三章**，保持连贯性
2. **每章字数2500-3000字**，不能太少
3. **卡点必须强**，每章结尾都要有让读者点击下一章的冲动
4. **情绪递进**：第1章压抑→第2章好奇→第3章爽快
5. **消除AI痕迹**：语言自然，避免"首先、其次"等词汇
"""
        return prompt
    
    def _format_scenes(self, scenes_by_chapter: Optional[Dict[int, List[Dict]]]) -> str:
        """格式化场景"""
        if not scenes_by_chapter:
            return "无预设计场景，请自由发挥"
        
        lines = []
        for ch_num in sorted(scenes_by_chapter.keys()):
            if ch_num > 3:
                continue
            scenes = scenes_by_chapter[ch_num]
            lines.append(f"\n第{ch_num}章场景:")
            for i, scene in enumerate(scenes, 1):
                lines.append(f"  {i}. {scene.get('name', f'场景{i}')} - {scene.get('purpose', '')}")
        
        return "\n".join(lines)
    
    def _parse_golden_result(self, result: Any) -> Dict[int, ChapterContent]:
        """解析黄金三章结果"""
        chapters_data = {}
        
        # 🔥 修复：处理API返回可能是列表或字典的情况
        if isinstance(result, list):
            # 如果直接返回列表，直接使用
            chapters_list = result
        elif isinstance(result, dict):
            # 如果返回字典，提取 chapters 字段
            chapters_list = result.get("chapters", [])
            # 也可能直接是 {"1": {...}, "2": {...}} 格式
            if not chapters_list and any(str(i) in result for i in [1, 2, 3]):
                chapters_list = [result.get(str(i)) for i in [1, 2, 3] if result.get(str(i))]
        else:
            self.logger.error(f"[GoldenChapters] 未知的结果格式: {type(result)}")
            return chapters_data
        
        if not chapters_list:
            self.logger.error("[GoldenChapters] 无法提取章节数据")
            return chapters_data
        
        for ch_data in chapters_list:
            # 🔥 修复：确保 ch_data 是字典
            if not isinstance(ch_data, dict):
                self.logger.warning(f"[GoldenChapters] 跳过非字典章节数据: {type(ch_data)}")
                continue
            
            ch_num = ch_data.get("chapter_number")
            if not ch_num or ch_num not in [1, 2, 3]:
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
            
            # 记录卡点信息
            hook_type = ch_data.get("hook_type", "")
            hook_desc = ch_data.get("hook_description", "")
            self.logger.info(f"[GoldenChapters] 第{ch_num}章卡点: [{hook_type}] {hook_desc}")
        
        # 验证三章完整性
        for ch in [1, 2, 3]:
            if ch not in chapters_data:
                self.logger.warning(f"[GoldenChapters] 第{ch}章缺失于生成结果中")
        
        return chapters_data


def generate_golden_chapters(
    api_client,
    novel_data: Dict,
    creative_seed: Dict,
    selected_plan: Dict,
    **kwargs
) -> Dict[int, ChapterContent]:
    """
    便捷函数：生成黄金三章
    
    使用示例:
    chapters = generate_golden_chapters(
        api_client=api_client,
        novel_data=novel_data,
        creative_seed=creative_seed,
        selected_plan=selected_plan
    )
    
    for ch_num in [1, 2, 3]:
        content = chapters[ch_num]
        print(f"第{ch_num}章: {content.title}")
    """
    generator = GoldenChaptersGenerator(api_client)
    return generator.generate(
        novel_data=novel_data,
        creative_seed=creative_seed,
        selected_plan=selected_plan,
        **kwargs
    )
