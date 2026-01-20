# 视频UI系统统一迁移指南

## 📋 迁移状态

| 文件 | 状态 | 说明 |
|------|------|------|
| `video-ui-base.css` | ✅ 已创建 | 基础样式和CSS变量系统 |
| `video-ui-components.css` | ✅ 已创建 | 统一组件样式库 |
| `video-ui-utilities.css` | ✅ 已创建 | 工具类样式库 |
| `portrait-studio.css` | ✅ 已迁移 | 浅色→深色主题，已统一 |
| `video-generation-character-portrait.css` | ✅ 已迁移 | 浅色→深色主题，已统一 |
| `video-task-manager.css` | ✅ 已兼容 | 深色主题，已统一变量 |
| `video-generation.css` | ✅ 已兼容 | 深色主题，已统一变量 |
| `video-studio.css` | ✅ 已兼容 | 深色主题，已统一变量 |

## 🎯 统一设计规范

### 核心色彩

```css
/* 主色调 - 蓝紫渐变 */
--primary-color: #667eea;
--primary-hover: #764ba2;
--gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* 背景色 - 深色主题 */
--bg-primary: #0f172a;    /* 主背景 */
--bg-secondary: #1e293b;  /* 卡片背景 */
--bg-tertiary: #334155;   /* 输入框背景 */

/* 文字色 */
--text-primary: #f1f5f9;   /* 主文字 */
--text-secondary: #cbd5e1; /* 次文字 */
```

### 圆角系统

```css
--radius-sm: 0.375rem;   /* 6px  - 小元素 */
--radius-md: 0.5rem;     /* 8px  - 按钮、输入框 */
--radius-lg: 0.75rem;    /* 12px - 卡片 */
--radius-xl: 1rem;       /* 16px - 大卡片 */
```

### 间距系统

```css
--space-xs: 0.25rem;   /* 4px  */
--space-sm: 0.5rem;    /* 8px  */
--space-md: 0.75rem;   /* 12px */
--space-lg: 1rem;      /* 16px */
--space-xl: 1.5rem;    /* 24px */
--space-2xl: 2rem;     /* 32px */
```

### 动画时长

```css
--duration-fast: 150ms;    /* 快速交互 */
--duration-normal: 250ms;  /* 标准交互 */
--duration-slow: 350ms;    /* 慢速动画 */
```

## 📝 使用方法

### 方法1：引入基础样式（推荐）

在HTML的 `<head>` 中按顺序引入：

```html
<!-- 1. 基础样式（必须） -->
<link rel="stylesheet" href="/static/css/video-ui-base.css">

<!-- 2. 组件样式（可选） -->
<link rel="stylesheet" href="/static/css/video-ui-components.css">

<!-- 3. 工具类（可选） -->
<link rel="stylesheet" href="/static/css/video-ui-utilities.css">

<!-- 4. 页面特定样式 -->
<link rel="stylesheet" href="/static/css/video-[page-name].css">
```

### 方法2：使用现有样式（兼容）

继续使用现有的页面特定CSS文件，它们已经包含统一的CSS变量。

**重要**：每个文件顶部都已定义统一的CSS变量，无需额外引入基础文件。

## 🎨 组件使用示例

### 按钮

```html
<!-- 主按钮 -->
<button class="btn-primary">生成视频</button>

<!-- 次要按钮 -->
<button class="btn-secondary">取消</button>

<!-- 成功按钮 -->
<button class="btn-success">保存</button>

<!-- 危险按钮 -->
<button class="btn-danger">删除</button>

<!-- 图标按钮 -->
<button class="btn-icon">⚙️</button>
```

### 卡片

```html
<div class="card card-clickable">
    <div class="card-header">
        <h3>卡片标题</h3>
    </div>
    <div class="card-body">
        <p>卡片内容</p>
    </div>
    <div class="card-footer">
        <button class="btn-primary">操作</button>
    </div>
</div>
```

### 输入框

```html
<div class="form-group">
    <label>提示词</label>
    <textarea class="input textarea" rows="5"></textarea>
</div>
```

### 模态框

```html
<div class="modal-overlay">
    <div class="modal-content">
        <div class="modal-header">
            <h3>标题</h3>
            <button class="modal-close">×</button>
        </div>
        <div class="modal-body">
            内容
        </div>
        <div class="modal-footer">
            <button class="btn-secondary">取消</button>
            <button class="btn-primary">确认</button>
        </div>
    </div>
</div>
```

### 工具类示例

```html
<!-- 间距 -->
<div class="p-xl mb-lg">内容</div>

<!-- 布局 -->
<div class="flex flex-between gap-md">
    <div>左侧</div>
    <div>右侧</div>
</div>

<!-- 文字 -->
<p class="text-primary font-semibold">重要文字</p>

<!-- 颜色 -->
<div class="bg-brand text-white">品牌色背景</div>
```

## ⚙️ 自定义样式

如果某个页面需要特殊样式，可以在页面CSS中覆盖变量：

```css
/* 在页面特定CSS中 */
.special-page {
    --primary-color: #8b5cf6;  /* 使用紫色主题 */
    --gradient-primary: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%);
}
```

## 📱 响应式设计

所有样式已包含响应式断点：

```css
/* 手机 */
@media (max-width: 640px) { }

/* 平板 */
@media (min-width: 641px) and (max-width: 1024px) { }

/* 桌面 */
@media (min-width: 1025px) { }
```

## 🚀 最佳实践

### 1. 优先使用CSS变量

```css
/* ✅ 推荐 */
color: var(--text-primary);
background: var(--bg-secondary);

/* ❌ 避免 */
color: #f1f5f9;
background: #1e293b;
```

### 2. 使用统一的动画时长

```css
/* ✅ 推荐 */
transition: all var(--duration-normal) var(--ease-in-out);

/* ❌ 避免 */
transition: all 0.3s ease;
```

### 3. 使用统一的圆角

```css
/* ✅ 推荐 */
border-radius: var(--radius-lg);

/* ❌ 避免 */
border-radius: 12px;
```

### 4. 使用组件类而非自定义样式

```css
/* ✅ 推荐 */
<button class="btn-primary">按钮</button>

/* ❌ 避免 */
<button style="background: linear-gradient(...); padding: ...;">按钮</button>
```

## 🐛 常见问题

### Q1: 为什么有些样式没有生效？

**A**: 确保CSS文件按正确顺序引入：
1. `video-ui-base.css` (必须)
2. `video-ui-components.css` (可选)
3. `video-ui-utilities.css` (可选)
4. 页面特定CSS (必须)

### Q2: 如何自定义某个组件的颜色？

**A**: 在页面CSS中覆盖变量：

```css
.my-page {
    --primary-color: #8b5cf6;
}
```

### Q3: 响应式样式如何使用？

**A**: 使用响应式工具类：

```html
<div class="hidden md:block lg:flex">内容</div>
```

### Q4: 如何添加新的组件样式？

**A**: 在 `video-ui-components.css` 中添加，或使用工具类组合：

```html
<div class="card p-xl border-2 border-brand shadow-lg">自定义卡片</div>
```

## 📚 相关文档

- [完整设计规范](./VIDEO_UI_STYLE_ANALYSIS_AND_UNIFIED_DESIGN.md)
- [组件样式库](../static/css/video-ui-components.css)
- [工具类参考](../static/css/video-ui-utilities.css)

---

**版本**: 1.0.0  
**更新时间**: 2026-01-20  
**维护者**: UI设计团队
