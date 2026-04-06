# 续写/重写功能修复报告

## 修复日期
2026-04-06

## 问题描述

### 现象
用户反馈作品续写功能无法正常使用，生成内容质量低下或与已有内容不连贯。

### 根本原因
在 `_run_continue_chapter_generation` 和 `_run_rewrite_generation` 函数中，传递给 `BatchChapterGenerator.generate_batch()` 的 `novel_data` 参数过于简单：

```python
# 修复前的代码（问题）
novel_data = {
    'title': title,
    'username': username,
    'project_path': str(project_path)
}
```

**关键缺失信息：**
- ❌ 世界观设定（worldview）
- ❌ 角色设计（protagonist, character_design）
- ❌ 金手指设定（golden_finger）
- ❌ 主线剧情（main_plot, storyline）
- ❌ 全书结构（book_structure, stage_goals）
- ❌ 情绪曲线（emotion_curve）
- ❌ 核心卖点（core_selling_point）

### 为什么会导致问题？

`BatchChapterGenerator` 使用 `ChapterConversationGenerator` 进行对话式章节生成，该生成器依赖 `novel_data` 构建提示词上下文。

当 `novel_data` 不完整时：
1. 系统提示词缺少关键设定信息
2. AI 无法准确理解故事背景和角色设定
3. 生成的章节与已有内容脱节
4. 角色行为不一致，世界观混乱

## 修复方案

### 修复内容

在 `_run_continue_chapter_generation` 和 `_run_rewrite_generation` 中，从 `blueprint` 提取完整信息构建 `novel_data`：

```python
# 修复后的代码
novel_data = {
    'title': title,
    'novel_title': title,
    'username': username,
    'project_path': str(project_path),
    # 核心设定
    'core_setting': {
        'worldview': blueprint.get('core_setting', {}).get('worldview', ''),
        'power_system': blueprint.get('core_setting', {}).get('power_system', ''),
    },
    'worldview': blueprint.get('worldview', ''),
    # 角色设计
    'character_design': {
        'protagonist': blueprint.get('core_setting', {}).get('protagonist', {}),
    },
    'protagonist': blueprint.get('protagonist', {}),
    # 金手指
    'golden_finger': blueprint.get('golden_finger', {}),
    # 主线剧情
    'storyline': blueprint.get('main_plot', ''),
    'main_plot': blueprint.get('main_plot', ''),
    # 全书结构
    'book_structure': blueprint.get('book_structure', {}),
    'stage_goals': blueprint.get('stage_goals', []),
    # 情绪曲线
    'emotion_curve': blueprint.get('emotion_curve', []),
    # 卖点
    'core_selling_point': blueprint.get('core_selling_point', ''),
    # 其他元数据
    'target_chapters': blueprint.get('target_chapters', 200),
    'genre': blueprint.get('genre', ''),
}
```

### 修复文件
- `web/api/market_driven_api.py`
  - `_run_continue_chapter_generation` 函数
  - `_run_rewrite_generation` 函数

## 影响分析

### 1. 续写功能 (Continue)

#### 修复前
- ✅ 保留已有章节（正确）
- ✅ 使用现有 blueprint（正确）
- ❌ **novel_data 不完整，导致生成质量低下**

#### 修复后
- ✅ 保留已有章节
- ✅ 使用现有 blueprint
- ✅ **完整的 novel_data 确保生成质量和连贯性**

**用户体验变化：**
- 续写生成的章节与已有内容风格一致
- 角色行为符合既定设定
- 世界观保持一致

### 2. 重写功能 (Rewrite)

#### 修复前
- ✅ 删除已有章节（正确）
- ✅ 基于新设定生成 blueprint（正确）
- ❌ **novel_data 不完整，影响新章节生成质量**

#### 修复后
- ✅ 删除已有章节
- ✅ 基于新设定生成 blueprint
- ✅ **完整的 novel_data 确保新章节质量**

**用户体验变化：**
- 重新生成的章节质量更高
- 新设定能够准确体现在生成内容中

### 3. 重新规划功能 (Replan)

**注意：** 重新规划功能主要更新 project_info 和 blueprint，不直接调用章节生成，因此不受此问题影响。

## 测试建议

### 续写功能测试
```bash
# 1. 创建一个已有前10章的项目
# 2. 调用续写 API 生成第11-15章
POST /api/market-driven/{title}/continue-chapters
{
    "start_chapter": 11,
    "end_chapter": 15
}

# 3. 验证生成的章节
# - 角色设定是否与前10章一致
# - 世界观是否连贯
# - 剧情是否合理延续
```

### 重写功能测试
```bash
# 1. 选择一个已有章节的项目
# 2. 调用重写 API
POST /api/market-driven/{title}/rewrite
{
    "new_settings": {
        "title": "新标题",
        "sellpoint": "新卖点",
        "chapters": 50,
        "protagonist_name": "新主角名",
        "protagonist_bg": "新背景",
        "golden_finger_type": "system",
        "golden_finger_desc": "新金手指",
        "main_plot": "新主线"
    }
}

# 3. 验证
# - 旧章节是否已删除
# - 新章节是否基于新设定生成
```

## 后续优化建议

### 1. 续写上下文增强（建议优先级：高）
当前续写只传递了 blueprint 中的静态设定，建议增加：
```python
# 读取前3章内容作为上下文
previous_chapters = _get_last_n_chapters(project_path, start_chapter - 1, n=3)
novel_data['previous_context'] = previous_chapters
```

**收益：**
- 生成的章节能够更准确地承接前文剧情
- 对话风格保持一致
- 避免剧情重复或跳跃

### 2. 批次间上下文传递（建议优先级：中）
大批量续写时（如51-100章），分多个批次生成：
```python
# 批次2生成前，读取批次1的最后几章
if batch_num > 1:
    last_batch_context = _get_last_batch_chapters(...)
    novel_data['previous_batch_context'] = last_batch_context
```

**收益：**
- 批次间的剧情衔接更自然
- 避免大跨度续写时的设定漂移

### 3. 自动备份机制（建议优先级：高）
重写功能会删除已有章节，建议添加：
```python
def _create_backup_before_rewrite(project_path):
    backup_dir = project_path / "backups" / f"rewrite_{timestamp}"
    # 备份 chapters 目录和 project_info.json
```

**收益：**
- 防止误操作导致数据丢失
- 用户可以恢复到重写前的状态

## 总结

| 功能 | 修复前状态 | 修复后状态 | 建议 |
|------|------------|------------|------|
| **续写** | ❌ 因 novel_data 不完整导致生成质量低 | ✅ 修复完成，生成质量提升 | 建议增加前文上下文 |
| **重写** | ❌ 因 novel_data 不完整影响生成质量 | ✅ 修复完成，生成质量提升 | 建议添加自动备份 |
| **重新规划** | ✅ 不受影响 | ✅ 正常 | - |

## 相关文档
- `docs/continue_vs_rewrite_analysis.md` - 三个功能的详细对比分析
