# 短篇创作流程重设计

## 核心思路

从**一次性生成**改为**分步迭代式生成**，参考竞品的交互逻辑：

```
创意输入 → 大纲生成 → [可编辑] → 正文生成 → [可编辑] → 封面设置 → 完成
        └─不满意重生成─┘    └─单章重生成─┘
```

## 三阶段流程

### 第一阶段：大纲生成

**左栏（配置）**：
- AI模型选择
- 题材类型
- 目标字数/章节数
- 创意描述（必须）
- 补充信息（可选）
- 【开始生成大纲】按钮

**中栏（生成结果）**：
- 显示大纲生成中动画
- 生成完成显示：书名、简介、章节列表（标题+简介）
- 每个章节可展开看详细简介

**右栏（大纲编辑）**：
- 文本编辑框，可修改大纲
- 【应用到生成】按钮
- 【重新生成大纲】按钮

**确认后进入第二阶段**

### 第二阶段：正文生成

**左栏（配置）**：
- 显示当前大纲概要
- 【开始生成正文】按钮
- 【逐章生成】开关

**中栏（生成结果）**：
- 逐章显示生成进度
- 每章可展开看完整内容
- 【重新生成本章】按钮

**右栏（正文编辑）**：
- 文本编辑框，可修改正文
- 支持富文本编辑（可选）
- 【保存修改】按钮

**确认后进入第三阶段**

### 第三阶段：封面设置

**左栏**：无

**中栏**：
- 封面上传区域
- 或AI生成封面选项

**右栏**：
- 封面预览
- 调整选项

## API设计

### 现有API
- `POST /api/short-story/create` - 一次性生成（需要改造）

### 新API

```python
# 第一阶段：大纲生成
POST /api/short-story/outline
{
  "creative_seed": "创意描述",
  "genre": "题材",
  "chapter_count": 10,
  "word_count": 15000,
  "extra_info": "补充信息"
}
→ 返回 outline（书名、简介、章节列表）

# 第二阶段：正文生成
POST /api/short-story/content
{
  "outline": {...},  # 确认后的大纲
  "generate_mode": "all" | "chapter_by_chapter",
  "start_chapter": 1  # 从第几章开始生成
}
→ 返回 chapters（章节内容数组）

# 单章重新生成
POST /api/short-story/regenerate-chapter
{
  "outline": {...},
  "chapters": [...],  # 已生成的章节
  "chapter_number": 3  # 要重生的章节
}
→ 返回新生成的章节

# 第三阶段：保存完成
POST /api/short-story/finalize
{
  "title": "书名",
  "outline": {...},
  "chapters": [...],
  "cover_image": "..."  # 可选
}
→ 保存到项目
```

## 状态管理

前端维护一个状态对象：

```javascript
{
  currentPhase: 'outline' | 'content' | 'cover',  // 当前阶段
  config: {  // 配置（左栏）
    model: 'gemini',
    genre: 'revenge_romance',
    chapterCount: 12,
    wordCount: 15000,
    creativeSeed: '',
    extraInfo: ''
  },
  outline: {  // 大纲数据
    title: '',
    synopsis: '',
    chapters: [
      { number: 1, title: '', synopsis: '' }
    ]
  },
  outlineEditor: '',  // 右栏大纲编辑内容
  chapters: [  // 正文数据
    { number: 1, title: '', content: '', wordCount: 0 }
  ],
  contentEditor: '',  // 右栏正文编辑内容
  currentChapter: 1,  // 当前编辑的章节
  coverImage: null,   // 封面
  taskId: null,       // 当前任务ID
  isGenerating: false // 是否生成中
}
```

## 界面状态切换

```
[大纲生成] 标签激活时：
- 左栏：显示大纲配置
- 中栏：显示大纲生成结果或空状态
- 右栏：大纲编辑

[正文生成] 标签激活时：
- 左栏：显示当前大纲概要 + 生成按钮
- 中栏：章节列表（可展开）
- 右栏：正文编辑

[封面设置] 标签激活时：
- 左栏：隐藏或显示完成信息
- 中栏：封面上传/生成
- 右栏：封面预览
```

## 关键交互

1. **大纲不满意** → 修改创意描述 → 重新生成
2. **大纲满意但需微调** → 右栏编辑 → 应用到生成
3. **正文某章不满意** → 点击该章【重新生成】→ 保留上下文重新生成该章
4. **正文满意但需润色** → 右栏编辑 → 保存

## 技术实现

1. 后端需要拆分现有的一次性生成为三个阶段
2. 每个阶段独立API，支持断点续传
3. 保持ConversationSession，实现多轮对话
4. 前端使用状态管理维护当前进度

## 与现有系统对接

- 复用现有的 `ShortStoryConversationGenerator`
- 只是将 `generate()` 方法拆分为 `generateOutline()` 和 `generateChapters()`
- 数据库保存格式不变
