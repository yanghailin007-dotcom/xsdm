# 视频制作入口UI风格分析与统一设计方案

## 📋 文档信息

- **创建时间**: 2026-01-20
- **版本**: v1.0
- **状态**: 技术分析与规划阶段

---

## 一、现有UI风格分析

### 1.1 涉及的CSS文件

| 文件名 | 行数 | 用途 | 风格特征 |
|--------|------|------|----------|
| `video-task-manager.css` | 950 | 视频任务管理系统 | 深色主题，蓝色系主色调 |
| `video-generation.css` | 2781 | 视频生成系统 | 深色主题，蓝紫渐变，复杂交互 |
| `video-studio.css` | 1214 | 视频工作室 | 深色主题，紫青渐变，现代感 |
| `video-generation-character-portrait.css` | 313 | 角色剧照生成面板 | 浅色主题，白色背景 |
| `portrait-studio.css` | 1058 | 人物剧照工作室 | 浅色主题，现代简洁 |

### 1.2 色彩系统分析

#### 1.2.1 深色主题（3个文件）

**主色调差异：**

| 文件 | 主色调 | 渐变方案 |
|------|--------|----------|
| video-task-manager.css | `#2563eb` (蓝) | 单色 |
| video-generation.css | `#2563eb` (蓝) | 蓝紫渐变 `#667eea → #764ba2` |
| video-studio.css | `#8b5cf6` (紫) | 紫青渐变 `#8b5cf6 → #06b6d4` |

**背景色：**
- 所有深色主题使用相同的背景层次：
  - `--bg-primary: #0f172a` (最深)
  - `--bg-secondary: #1e293b` (次深)
  - `--bg-tertiary: #334155` (较浅)

**文字色：**
- `--text-primary: #f1f5f9`
- `--text-secondary: #cbd5e1`

#### 1.2.2 浅色主题（2个文件）

| 文件 | 主色调 | 背景系统 |
|------|--------|----------|
| video-generation-character-portrait.css | `#667eea` (蓝紫) | 纯白 `#ffffff` |
| portrait-studio.css | `#667eea` (蓝紫) | 灰白系 `#f8fafc → #ffffff` |

### 1.3 组件风格对比

#### 1.3.1 按钮样式

| 组件 | video-task-manager | video-generation | video-studio | portrait-studio |
|------|-------------------|------------------|--------------|-----------------|
| 主按钮 | 实心蓝色 | 渐变蓝紫 | 渐变紫青 | 渐变蓝紫 |
| 次按钮 | 灰色背景 | 灰色背景 | 灰色背景 | 灰色背景 |
| 返回按钮 | 渐变蓝紫 | 渐变蓝紫 | 渐变紫青 | 半透明白 |
| 圆角 | 0.5rem (8px) | 0.5rem (8px) | 0.5rem (8px) | 10-12px |
| 阴影 | 中等 | 较重 | 较重 | 轻微 |

#### 1.3.2 卡片样式

| 属性 | 深色主题 | 浅色主题 |
|------|----------|----------|
| 背景 | `var(--bg-secondary)` | `#ffffff` |
| 边框 | `1px solid var(--border-color)` | `1px solid #e2e8f0` |
| 圆角 | 1rem (16px) | 10-16px |
| 阴影 | 无或轻微 | 明显分层阴影 |
| 内边距 | 1.5-2rem | 1.5rem |

#### 1.3.3 输入框样式

| 属性 | 深色主题 | 浅色主题 |
|------|----------|----------|
| 背景 | `var(--bg-tertiary)` | `#ffffff` |
| 边框 | 2px solid, hover/focus变蓝 | 2px solid, hover/focus变蓝 |
| 圆角 | 0.375-0.75rem | 8-12px |
| 内边距 | 0.625-1rem | 0.875-1rem |

### 1.4 布局系统分析

#### 1.4.1 网格布局

**三栏布局**（video-task-manager）：
```css
grid-template-columns: 400px 1fr 320px;
```

**两栏布局**（video-generation, video-studio）：
```css
grid-template-columns: 380px 1fr 320px;  /* 带右侧边栏 */
grid-template-columns: 1fr 400px;       /* 不带右侧边栏 */
```

#### 1.4.2 间距系统

| 用途 | 深色主题 | 浅色主题 |
|------|----------|----------|
| 组件外边距 | 2rem | 1.5-2rem |
| 卡片内边距 | 1.5-2rem | 1.5rem |
| 元素间距 | 0.5-1rem | 0.5-0.75rem |
| 容器边距 | 0 2rem | 0 2rem |

---

## 二、UI不一致性问题识别

### 2.1 严重问题

#### 🔴 问题1：主题混乱
- **现象**：5个文件中3个深色、2个浅色
- **影响**：用户在不同页面间切换时体验割裂
- **位置**：
  - `video-generation-character-portrait.css` 使用纯白背景
  - `portrait-studio.css` 使用浅灰背景

#### 🔴 问题2：主色调不统一
- **现象**：蓝色 vs 紫色，无明确主题色
- **影响**：品牌识别度低，视觉不一致
- **详情**：
  - video-task-manager: `#2563eb` (蓝)
  - video-studio: `#8b5cf6` (紫)
  - 其他: 渐变蓝紫 `#667eea → #764ba2`

#### 🔴 问题3：圆角半径不统一
- **现象**：8px、10px、12px、16px混用
- **影响**：视觉细节不统一
- **分布**：
  - 按钮：8-12px
  - 卡片：16px
  - 输入框：6-12px

#### 🔴 问题4：阴影系统缺失
- **现象**：有的文件用阴影，有的不用
- **影响**：层次感不统一
- **详情**：
  - video-task-manager: 几乎无阴影
  - portrait-studio: 完整的阴影系统 `--shadow-sm` 到 `--shadow-xl`

### 2.2 中等问题

#### 🟡 问题5：动画时长不一致
- **现象**：0.2s、0.3s混用
- **影响**：交互节奏不统一

#### 🟡 问题6：渐变方向不统一
- **现象**：135deg、90deg混用
- **影响**：视觉效果不统一

#### 🟡 问题7：字体大小层级不清晰
- **现象**：标题大小跳跃式变化
- **影响**：视觉层次不清晰

### 2.3 轻微问题

#### 🟢 问题8：CSS变量命名不完全一致
- **现象**：有的用 `--bg-card`，有的不用
- **影响**：维护难度增加

---

## 三、统一设计方案

### 3.1 设计原则

1. **一致性优先**：所有页面必须使用相同的主题、色彩、组件样式
2. **渐进增强**：保留现有功能，逐步统一样式
3. **性能优先**：使用CSS变量减少重复代码
4. **可维护性**：建立清晰的设计系统文档
5. **用户体验**：确保暗色模式护眼，同时保持现代感

### 3.2 推荐主题选择

**方案A：深色主题（推荐）**
- ✅ 现有3/5文件已使用
- ✅ 适合长时间使用，护眼
- ✅ 专业感强，符合创作工具定位
- ✅ 内容突出，减少视觉干扰

**方案B：浅色主题**
- ⚠️ 需要大规模改动
- ✅ 更加明亮、现代
- ⚠️ 长时间使用易疲劳

**最终选择：方案A（深色主题）**

### 3.3 统一色彩系统

#### 3.3.1 主色调（推荐：蓝紫渐变）

```css
:root {
    /* ===== 核心品牌色 ===== */
    --primary-color: #667eea;           /* 主色：蓝紫 */
    --primary-hover: #764ba2;           /* 主色悬停：深紫 */
    --primary-light: #8b9cf5;           /* 浅主色 */
    --primary-dark: #5a67d8;            /* 深主色 */
    
    /* ===== 辅助色 ===== */
    --secondary-color: #06b6d4;         /* 辅助色：青色 */
    --accent-color: #8b5cf6;            /* 强调色：紫色 */
    
    /* ===== 功能色 ===== */
    --success-color: #10b981;           /* 成功：绿色 */
    --warning-color: #f59e0b;           /* 警告：橙色 */
    --danger-color: #ef4444;            /* 危险：红色 */
    --info-color: #3b82f6;              /* 信息：蓝色 */
    
    /* ===== 背景色（深色主题）===== */
    --bg-primary: #0f172a;              /* 主背景：最深的蓝黑 */
    --bg-secondary: #1e293b;            /* 次背景：卡片背景 */
    --bg-tertiary: #334155;             /* 第三级背景：输入框等 */
    --bg-elevated: #475569;             /* 悬浮层背景 */
    
    /* ===== 文字色 ===== */
    --text-primary: #f1f5f9;            /* 主文字：接近白色 */
    --text-secondary: #cbd5e1;          /* 次文字：浅灰 */
    --text-tertiary: #94a3b8;           /* 第三级文字：中灰 */
    --text-disabled: #64748b;           /* 禁用文字：深灰 */
    
    /* ===== 边框色 ===== */
    --border-color: #475569;            /* 主边框 */
    --border-light: #64748b;            /* 浅边框 */
    --border-focus: var(--primary-color); /* 聚焦边框 */
    
    /* ===== 阴影系统 ===== */
    --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.15);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.2);
    --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.25);
    --shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.3);
    
    /* ===== 渐变色 ===== */
    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --gradient-secondary: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%);
    --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
    --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    
    /* ===== 圆角系统 ===== */
    --radius-sm: 0.375rem;    /* 6px */
    --radius-md: 0.5rem;      /* 8px */
    --radius-lg: 0.75rem;     /* 12px */
    --radius-xl: 1rem;        /* 16px */
    --radius-2xl: 1.25rem;    /* 20px */
    --radius-full: 9999px;    /* 完全圆角 */
    
    /* ===== 间距系统 ===== */
    --space-xs: 0.25rem;      /* 4px */
    --space-sm: 0.5rem;       /* 8px */
    --space-md: 0.75rem;      /* 12px */
    --space-lg: 1rem;         /* 16px */
    --space-xl: 1.5rem;       /* 24px */
    --space-2xl: 2rem;        /* 32px */
    --space-3xl: 3rem;        /* 48px */
    
    /* ===== 动画时长 ===== */
    --duration-fast: 150ms;
    --duration-normal: 250ms;
    --duration-slow: 350ms;
    
    /* ===== 字体大小 ===== */
    --text-xs: 0.75rem;       /* 12px */
    --text-sm: 0.875rem;      /* 14px */
    --text-base: 1rem;        /* 16px */
    --text-lg: 1.125rem;      /* 18px */
    --text-xl: 1.25rem;       /* 20px */
    --text-2xl: 1.5rem;       /* 24px */
    --text-3xl: 1.875rem;     /* 30px */
    --text-4xl: 2.25rem;      /* 36px */
}
```

### 3.4 统一组件样式规范

#### 3.4.1 按钮组件

**主按钮（Primary Button）**
```css
.btn-primary {
    background: var(--gradient-primary);
    color: white;
    border: none;
    padding: var(--space-lg) var(--space-xl);
    border-radius: var(--radius-lg);
    font-weight: 600;
    font-size: var(--text-base);
    cursor: pointer;
    transition: all var(--duration-normal) ease;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:active {
    transform: translateY(0);
}

.btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}
```

**次要按钮（Secondary Button）**
```css
.btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 2px solid var(--border-color);
    padding: var(--space-lg) var(--space-xl);
    border-radius: var(--radius-lg);
    font-weight: 600;
    font-size: var(--text-base);
    cursor: pointer;
    transition: all var(--duration-normal) ease;
}

.btn-secondary:hover {
    background: var(--bg-elevated);
    border-color: var(--primary-color);
    transform: translateY(-1px);
}
```

**图标按钮（Icon Button）**
```css
.btn-icon {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    width: 2.5rem;
    height: 2.5rem;
    border-radius: var(--radius-md);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--duration-fast) ease;
}

.btn-icon:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}
```

#### 3.4.2 卡片组件

**基础卡片**
```css
.card {
    background: var(--bg-secondary);
    border-radius: var(--radius-xl);
    padding: var(--space-xl);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
    transition: all var(--duration-normal) ease;
}

.card:hover {
    box-shadow: var(--shadow-lg);
    border-color: var(--border-light);
}

.card-clickable {
    cursor: pointer;
}

.card-clickable:hover {
    transform: translateY(-2px);
    border-color: var(--primary-color);
}
```

#### 3.4.3 输入框组件

**文本输入框**
```css
.input {
    width: 100%;
    padding: var(--space-md) var(--space-lg);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-color);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: var(--text-base);
    transition: all var(--duration-fast) ease;
}

.input:hover {
    border-color: var(--border-light);
}

.input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input::placeholder {
    color: var(--text-tertiary);
}

.input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
```

**文本域**
```css
.textarea {
    min-height: 120px;
    resize: vertical;
    font-family: 'Courier New', monospace;
    line-height: 1.6;
}
```

#### 3.4.4 模态框组件

```css
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: fadeIn var(--duration-normal) ease;
}

.modal-content {
    background: var(--bg-secondary);
    border-radius: var(--radius-xl);
    width: 90%;
    max-width: 800px;
    max-height: 80vh;
    overflow: hidden;
    box-shadow: var(--shadow-2xl);
    animation: slideUp var(--duration-normal) ease;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-xl);
    border-bottom: 1px solid var(--border-color);
}

.modal-body {
    padding: var(--space-xl);
    overflow-y: auto;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-lg);
    padding: var(--space-xl);
    border-top: 1px solid var(--border-color);
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

#### 3.4.5 进度条组件

```css
.progress-bar {
    width: 100%;
    height: 12px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    overflow: hidden;
    position: relative;
}

.progress-fill {
    height: 100%;
    background: var(--gradient-primary);
    border-radius: var(--radius-full);
    transition: width var(--duration-normal) ease;
    position: relative;
}

.progress-fill.animate {
    animation: progressShimmer 2s infinite;
}

.progress-fill.animate::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.3),
        transparent
    );
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
```

#### 3.4.6 Toast通知组件

```css
.toast {
    position: fixed;
    bottom: var(--space-2xl);
    right: var(--space-2xl);
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: var(--space-lg) var(--space-xl);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-xl);
    transform: translateY(150%);
    transition: transform var(--duration-normal) ease;
    z-index: 2000;
    min-width: 300px;
}

.toast.show {
    transform: translateY(0);
}

.toast.success {
    border-left: 4px solid var(--success-color);
}

.toast.error {
    border-left: 4px solid var(--danger-color);
}

.toast.warning {
    border-left: 4px solid var(--warning-color);
}

.toast.info {
    border-left: 4px solid var(--info-color);
}
```

### 3.5 统一布局规范

#### 3.5.1 页面容器

```css
.page-container {
    min-height: 100vh;
    background: var(--bg-primary);
}

.navbar {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: var(--space-lg) 0;
    position: sticky;
    top: 0;
    z-index: 100;
}

.nav-container {
    max-width: 1800px;
    margin: 0 auto;
    padding: 0 var(--space-2xl);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--space-lg);
}

.main-content {
    max-width: 1800px;
    margin: 0 auto;
    padding: var(--space-2xl);
}
```

#### 3.5.2 网格布局

**三栏布局（带侧边栏）**
```css
.layout-three-column {
    display: grid;
    grid-template-columns: 380px 1fr 320px;
    gap: var(--space-2xl);
    min-height: calc(100vh - 120px);
}

@media (max-width: 1400px) {
    .layout-three-column {
        grid-template-columns: 350px 1fr;
    }
    .layout-three-column .right-sidebar {
        display: none;
    }
}

@media (max-width: 768px) {
    .layout-three-column {
        grid-template-columns: 1fr;
    }
}
```

**两栏布局**
```css
.layout-two-column {
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: var(--space-2xl);
}

@media (max-width: 1200px) {
    .layout-two-column {
        grid-template-columns: 1fr;
    }
}
```

#### 3.5.3 响应式断点

```css
/* 手机 */
@media (max-width: 640px) {
    :root {
        --space-xs: 0.125rem;
        --space-sm: 0.375rem;
        --space-md: 0.5rem;
        --space-lg: 0.75rem;
        --space-xl: 1rem;
        --space-2xl: 1.5rem;
    }
}

/* 平板 */
@media (min-width: 641px) and (max-width: 1024px) {
    /* 中等屏幕优化 */
}

/* 桌面 */
@media (min-width: 1025px) {
    /* 大屏幕优化 */
}
```

### 3.6 统一动画规范

```css
/* 淡入动画 */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 滑入动画（侧边栏） */
@keyframes slideInRight {
    from {
        transform: translateX(100%);
    }
    to {
        transform: translateX(0);
    }
}

/* 缩放动画（模态框） */
@keyframes scaleIn {
    from {
        opacity: 0;
        transform: scale(0.9);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

/* 旋转动画（加载） */
@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

/* 脉冲动画（提醒） */
@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}
```

---

## 四、实施建议

### 4.1 迁移策略

#### 阶段1：创建基础样式文件（1-2天）
1. 创建 `web/static/css/video-ui-base.css`
2. 定义所有CSS变量
3. 实现通用组件样式
4. 编写使用文档

#### 阶段2：逐步迁移（3-5天）
**优先级排序：**
1. **高优先级**：`portrait-studio.css`（浅色转深色，改动最大）
2. **中优先级**：`video-generation-character-portrait.css`
3. **低优先级**：`video-task-manager.css`、`video-generation.css`、`video-studio.css`（已基本符合）

#### 阶段3：测试与优化（2-3天）
1. 视觉回归测试
2. 交互测试
3. 性能优化
4. 浏览器兼容性测试

### 4.2 文件结构建议

```
web/static/css/
├── video-ui-base.css          # 基础样式（新增）
├── video-ui-components.css    # 组件样式（新增）
├── video-ui-utilities.css     # 工具类（新增）
├── video-task-manager.css     # 页面特定样式
├── video-generation.css
├── video-studio.css
├── video-generation-character-portrait.css
└── portrait-studio.css
```

### 4.3 HTML引入顺序

```html
<!-- 1. 基础样式 -->
<link rel="stylesheet" href="/static/css/video-ui-base.css">

<!-- 2. 组件样式 -->
<link rel="stylesheet" href="/static/css/video-ui-components.css">

<!-- 3. 工具类 -->
<link rel="stylesheet" href="/static/css/video-ui-utilities.css">

<!-- 4. 页面特定样式 -->
<link rel="stylesheet" href="/static/css/video-[page-name].css">
```

### 4.4 向后兼容方案

为避免破坏现有功能，采用**叠加式迁移**：

```css
/* 旧样式保留 */
.old-button {
    /* ... */
}

/* 新样式使用新的类名 */
.btn-primary {
    /* ... */
}

/* 或使用数据属性选择器 */
[data-ui-version="new"] .button {
    /* 新样式 */
}
```

### 4.5 CSS变量覆盖机制

如果某个页面需要特殊样式：

```css
/* 在页面特定CSS中 */
.special-page {
    --primary-color: #8b5cf6;  /* 覆盖主色 */
    --radius-lg: 0.5rem;       /* 覆盖圆角 */
}
```

---

## 五、质量保障

### 5.1 视觉检查清单

- [ ] 所有页面使用相同的主题（深色）
- [ ] 所有按钮使用统一的样式规范
- [ ] 所有卡片使用统一的圆角和阴影
- [ ] 所有输入框使用统一的边框和焦点样式
- [ ] 所有渐变使用统一的颜色和方向
- [ ] 所有动画使用统一的时长和缓动函数

### 5.2 代码检查清单

- [ ] 所有CSS变量在 `video-ui-base.css` 中定义
- [ ] 所有组件在 `video-ui-components.css` 中实现
- [ ] 所有工具类在 `video-ui-utilities.css` 中定义
- [ ] 页面特定CSS只包含页面特定的样式
- [ ] 没有重复的样式定义
- [ ] 使用CSS变量而不是硬编码颜色

### 5.3 测试清单

- [ ] 浏览器兼容性测试（Chrome、Firefox、Safari、Edge）
- [ ] 响应式测试（手机、平板、桌面）
- [ ] 暗色模式测试
- [ ] 交互状态测试（hover、active、focus、disabled）
- [ ] 性能测试（加载时间、渲染性能）

---

## 六、总结

### 6.1 关键发现

1. **主题不统一**：5个文件中3个深色、2个浅色，需要统一为深色主题
2. **色彩混乱**：主色调在蓝色和紫色之间摇摆，需要明确品牌色
3. **组件不一致**：按钮、卡片、输入框等组件样式差异较大
4. **缺失设计系统**：没有统一的设计规范和CSS变量体系

### 6.2 推荐方案

- **主题**：统一使用深色主题（护眼、专业）
- **主色**：蓝紫渐变 `#667eea → #764ba2`（现代、科技感）
- **圆角**：建立统一系统（6px、8px、12px、16px）
- **阴影**：建立分层阴影系统（xs到2xl）
- **布局**：统一间距和网格系统

### 6.3 实施优先级

1. **立即执行**：创建基础样式文件和设计文档
2. **短期（1周内）**：迁移浅色主题页面
3. **中期（2-3周）**：统一所有组件样式
4. **长期（1个月）**：完善设计系统和文档

### 6.4 预期收益

- ✅ **用户体验提升**：统一的视觉风格减少认知负担
- ✅ **开发效率提升**：统一的设计系统减少重复工作
- ✅ **维护成本降低**：清晰的代码结构便于后期维护
- ✅ **品牌一致性**：统一的色彩和组件强化品牌识别

---

## 附录

### A. 参考资料

- [Material Design 3](https://m3.material.io/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Design Systems](https://www.designsystems.com/)

### B. 工具推荐

- **颜色工具**：[Coolors](https://coolors.co/)、[Adobe Color](https://color.adobe.com/)
- **对比度检查**：[WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- **渐变生成**：[CSS Gradient](https://cssgradient.io/)

### C. 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

**文档版本**: v1.0  
**最后更新**: 2026-01-20  
**维护者**: UI设计团队
