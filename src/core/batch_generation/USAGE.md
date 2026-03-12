# 中型事件批量生成功能使用指南

## 概述

本模块实现了按中型事件批量生成章节内容的优化方案，可将API调用次数减少50-60%。

## 核心特性

- **批量生成**: 2-3章中型事件一次性生成
- **黄金三章整体生成**: 第1-3章作为整体一次性生成，保证开篇连贯性
- **风格指南自动加载**: 从文件动态加载番茄向写作风格
- **分层质量评估**: Level 1轻量评估 + Level 2深度检查
- **智能回退**: 批量失败时自动降级到逐章生成

## 快速开始

### 方法1: 完整处理器（推荐）

```python
from src.core.batch_generation import MediumEventBatchProcessor

# 初始化处理器
processor = MediumEventBatchProcessor(
    api_client=api_client,
    novel_generator=novel_generator  # 可选，用于世界状态管理
)

# 处理中型事件
result = processor.process_medium_event(
    medium_event={
        "name": "韩立得掌天瓶",
        "main_goal": "主角获得金手指",
        "chapter_range": "5-7"
    },
    chapter_range=(5, 7),  # 第5-7章
    novel_data={
        "novel_title": "凡人修仙传",
        "username": "user1"
    },
    scenes_by_chapter={
        5: [scene1, scene2, ...],
        6: [scene3, scene4, ...],
        7: [scene5, scene6, ...]
    }
)

# 检查结果
if result.success:
    print(f"生成成功！")
    print(f"API调用次数: {result.api_calls_used}")
    print(f"创造点消耗: {result.points_consumed}点")
    print(f"创造点节省: {result.points_saved}点")
    print(f"评估级别: {result.assessment.level.value}")
    print(f"总体评分: {result.assessment.overall_score}")
    
    for ch_num, content in result.chapters.items():
        print(f"第{ch_num}章: {content.title}")
        print(f"  字数: {len(content.content)}")
        print(f"  关键事件: {content.key_events}")
else:
    print(f"生成失败: {result.error}")
```

### 方法2: 集成到ContentGenerator

```python
from src.core.batch_generation import patch_content_generator

# 在ContentGenerator初始化后打补丁
content_generator = ContentGenerator(api_client, novel_generator)
patch_content_generator(content_generator)

# 然后可以直接使用
chapters = content_generator.batch_adapter.generate_medium_event(
    medium_event=event,
    chapter_range=(5, 7),
    novel_data=novel_data
)
```

### 方法3: 便捷函数

```python
from src.core.batch_generation import (
    process_medium_event_batch,
    generate_multi_chapter_content,
    quick_assess_batch
)

# 完整处理
result = process_medium_event_batch(
    api_client=api_client,
    medium_event=event,
    chapter_range=(5, 7),
    novel_data=novel_data
)

# 仅生成内容（跳过评估）
chapters = generate_multi_chapter_content(
    api_client=api_client,
    medium_event=event,
    chapter_range=(5, 7),
    scenes_by_chapter=scenes,
    consistency_guidance=guidance,
    novel_title="凡人修仙传"
)

# 快速评估
assessment = quick_assess_batch(
    api_client=api_client,
    chapters_content=chapters,
    medium_event=event,
    world_state_before=world_state,
    style_guide=style_guide,
    novel_title="凡人修仙传"
)
```

## 黄金三章整体生成

黄金三章（第1-3章）是小说的开篇，必须作为一个整体一次性生成，以保证：
- **开篇钩子连贯延续**
- **角色状态自然过渡**
- **情绪弧线完整**：压抑→好奇→兴奋→满足→期待

### 自动检测

当传入的章节范围包含第1章且至少到第2章时，处理器会自动使用黄金三章整体生成模式：

```python
# 这会触发黄金三章整体生成
result = processor.process_medium_event(
    medium_event=event,
    chapter_range=(1, 3),  # 黄金三章
    novel_data=novel_data
)
```

### 专用生成器

如果需要单独控制黄金三章生成：

```python
from src.core.batch_generation import GoldenChaptersGenerator, generate_golden_chapters

# 方法1: 使用类
generator = GoldenChaptersGenerator(api_client)
chapters = generator.generate(
    novel_data=novel_data,
    creative_seed=creative_seed,
    selected_plan=selected_plan
)

# 方法2: 便捷函数
chapters = generate_golden_chapters(
    api_client=api_client,
    novel_data=novel_data,
    creative_seed=creative_seed,
    selected_plan=selected_plan
)

# 检查三章完整性
for ch_num in [1, 2, 3]:
    if ch_num in chapters:
        content = chapters[ch_num]
        print(f"第{ch_num}章: {content.title}")
        print(f"  字数: {len(content.content)}")
        print(f"  关键事件: {content.key_events}")
```

### 黄金三章结构要求

整体生成时会强制要求：

| 章节 | 核心任务 | 情绪目标 | 卡点类型 |
|-----|---------|---------|---------|
| 第1章 | 建立情境，激活金手指 | 压抑→好奇 | 悬念型 |
| 第2章 | 测试金手指，周围反应 | 好奇→兴奋 | 期待型 |
| 第3章 | 第一次成功，打脸/反转 | 兴奋→满足 | 悬念型 |

### 黄金三章点数消耗

黄金三章整体生成 vs 逐章生成：

| 方案 | 消耗点数 | 节省点数 | 节省比例 |
|-----|---------|---------|---------|
| 逐章生成 | 9点 | - | - |
| 整体生成 | 3-4点 | 5-6点 | **55-66%** |

### 黄金三章专用评估

黄金三章使用**独立于普通章节**的评估体系，重点评估：

```python
from src.core.batch_generation import assess_golden_chapters

# 评估黄金三章
assessment = assess_golden_chapters(
    api_client=api_client,
    chapters_content={1: ch1, 2: ch2, 3: ch3},
    novel_data=novel_data,
    creative_seed=creative_seed,
    selected_plan=selected_plan
)

# 查看评估结果
print(f"总体评分：{assessment.overall_score}/10")
print(f"开篇钩子：{assessment.opening_hook}/10")
print(f"类型契合：{assessment.type_match}/10")
print(f"读者吸引：{assessment.reader_attraction}/10")
print(f"三章流畅：{assessment.chapter_flow}/10")
print(f"爽点质量：{assessment.payoff_quality}/10")

# 读者反馈模拟
print("读者反馈：")
for ch, reaction in assessment.reader_reactions.items():
    print(f"  {ch}：{reaction}")

# 改进建议
if assessment.overall_score < 7.0:
    print("改进建议：")
    for suggestion in assessment.improvement_suggestions:
        print(f"  - {suggestion}")
```

#### 评估维度说明

| 维度 | 权重 | 评估重点 |
|-----|------|---------|
| **开篇钩子** | 20% | 15秒内抓住读者，强烈冲突/悬念 |
| **类型契合** | 20% | 是否符合该类型核心卖点 |
| **读者吸引** | 20% | 目标读者是否产生共鸣 |
| **三章流畅** | 20% | 情绪弧线是否完整递进 |
| **爽点质量** | 20% | 第3章是否给出足够回报 |

#### 类型特定评估

评估器会根据小说类型自动调整评估标准：

**神豪文评估重点**：
- 金钱装逼场景是否到位
- 身份反差是否清晰
- 打脸反转是否有力
- 周围人震惊反应是否充分

**修仙文评估重点**：
- 金手指激活是否自然
- 修炼升级是否爽
- 他人轻视→震惊的反差
- 修仙世界观是否吸引人

**赘婿文评估重点**：
- 屈辱铺垫是否到位
- 隐忍是否有张力
- 反转是否够爽
- 家人态度转变是否合理

#### 评分标准

| 分数 | 等级 | 说明 |
|-----|------|------|
| 9-10 | 优秀 | 开篇强力，类型纯正，读者必追 |
| 7-8.9 | 良好 | 整体合格， minor tweaks needed |
| 5-6.9 | 合格 | 基本可读，但有明显改进空间 |
| <5 | 需修改 | 吸引力不足，建议重写 |

#### 生成改进报告

```python
from src.core.batch_generation import GoldenChaptersAssessor

assessor = GoldenChaptersAssessor(api_client)
report = assessor.generate_improvement_guide(assessment, chapters_content)

# 保存报告
with open("golden_chapters_improvement.md", "w", encoding="utf-8") as f:
    f.write(report)
```
```

## 配置选项

### 跳过质量评估

如果不需要质量评估（节省1次API调用）：

```python
result = processor.process_medium_event(
    ...,
    skip_assessment=True  # 跳过评估
)
```

### 强制使用批量/逐章

```python
# 强制使用批量（即使单章）
chapters = adapter.generate_medium_event(
    ...,
    force_batch=True
)

# 手动判断是否使用批量
if processor.should_use_batch((5, 7)):
    # 使用批量
    result = processor.process_medium_event(...)
else:
    # 使用逐章
    chapters = adapter._generate_chapter_by_chapter(...)
```

### 拆分大型事件

对于跨度>3章的中型事件，自动拆分：

```python
# 手动拆分
batches = processor.split_large_event((1, 10), batch_size=3)
# 返回: [(1, 3), (4, 6), (7, 9), (10, 10)]

# 批量处理所有批次
all_chapters = {}
for batch_range in batches:
    result = processor.process_medium_event(
        medium_event=event,
        chapter_range=batch_range,
        ...
    )
    all_chapters.update(result.chapters)
```

## 点数统计与监控

### 实时点数消耗

批量生成会自动扣除创造点，1次API调用 = 1创造点：

```python
result = processor.process_medium_event(...)

if result.success:
    print(f"本次消耗: {result.points_consumed}创造点")
    print(f"本次节省: {result.points_saved}创造点")
    print(f"节省比例: {result.points_saved / (result.points_consumed + result.points_saved):.1%}")
```

### 累计统计

```python
# 获取处理统计（包含点数信息）
stats = processor.get_stats()
print(f"""
总事件数: {stats['total_events']}
批量成功: {stats['batch_success']}
回退次数: {stats['fallback_count']}
节省调用: {stats['api_calls_saved']}点  # 累计节省的创造点
成功率: {stats['success_rate']:.1%}
""")

# 重置统计
processor.reset_stats()
```

### 点数不足处理

如果创造点不足，API调用会失败，批量生成会自动回退：

```python
result = processor.process_medium_event(...)

if result.fallback_used and "点数" in str(result.warnings):
    print("警告: 创造点不足，已回退到逐章生成")
    # 提示用户充值
```

## API调用与创造点消耗

### 点数规则
- **1次API调用 = 1创造点**
- 批量生成无论生成多少章，**正文生成只消耗1创造点**
- 质量评估根据级别消耗：Level 1 = 1点，Level 2 = 1-2点

### 消耗对比

| 中型事件 | 原逐章方案 | 批量方案 | 节省创造点 | 节省比例 |
|---------|-----------|---------|-----------|---------|
| 1章 | 3点 | 3点 | 0点 | 0% |
| 2章 | 6点 | 3点 | 3点 | **50%** |
| 3章 | 9点 | 3-4点 | 5-6点 | **55%** |
| 5章(2+3) | 15点 | 7点 | 8点 | **53%** |

*注：包含场景生成、正文生成、质量评估*

## 错误处理

批量生成失败时自动回退：

```python
result = processor.process_medium_event(...)

if result.fallback_used:
    print(f"警告: 已回退到{result.fallback_level}模式")
    for warning in result.warnings:
        print(f"  - {warning}")
```

回退层级：
1. `retry_N` - 指数退避重试
2. `split_batches` - 拆分为小批次
3. `chapter_by_chapter` - 逐章生成（最终保障）

## 风格指南

自动从文件加载：`{novel_title}_writing_style_guide.json`

如文件不存在，使用番茄小说默认风格。

手动加载风格指南：

```python
from src.core.batch_generation import get_writing_style_for_prompt

style = get_writing_style_for_prompt("凡人修仙传", "user1")

# 使用风格片段构建Prompt
prompt = f"""
# 角色: {style.core_style}
{style.key_principles}
{style.language_characteristics}
...
"""
```

## 最佳实践

1. **2-3章事件最优**: 批量生成在2-3章时效果最好
2. **保留场景复用**: 传入scenes_by_chapter避免重复生成场景
3. **合理跳过评估**: 开发调试时可skip_assessment，生产环境建议开启
4. **监控回退率**: 回退率过高时检查API稳定性或调整质量阈值

## 集成到现有流程

修改 `ContentGenerator.generate_single_chapter` 的调用处：

```python
# 原代码（逐章）
for ch_num in range(start, end + 1):
    content = self.generate_chapter_content(...)

# 新代码（批量优化）
from src.core.batch_generation import MediumEventBatchProcessor

processor = MediumEventBatchProcessor(self.api_client, self.novel_generator)

# 按中型事件分组处理
for medium_event in medium_events:
    ch_range = parse_chapter_range(medium_event['chapter_range'])
    
    result = processor.process_medium_event(
        medium_event=medium_event,
        chapter_range=ch_range,
        novel_data=self.novel_data
    )
    
    if result.success:
        # 保存生成的章节
        for ch_num, content in result.chapters.items():
            self._save_chapter(ch_num, content)
```
