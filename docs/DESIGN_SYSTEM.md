# 大文娱系统 - 全站设计统一方案

## 设计理念

### 设计原则
1. **一致性** - 全站使用统一的色彩、字体、间距
2. **简洁性** - 去除多余装饰，聚焦内容
3. **反馈性** - 每个操作都有视觉反馈
4. **层次性** - 清晰的信息层级

### 参考大厂
- **Linear** - 边框发光、深色主题
- **Vercel** - 渐变文字、精致阴影
- **Notion** - 留白、字体层级

---

## 1. 色彩系统

### 主色调
```css
:root {
    /* 品牌色 - 紫蓝渐变 */
    --primary-400: #818cf8;
    --primary-500: #6366f1;  /* 主色 */
    --primary-600: #4f46e5;
    --accent-purple: #8b5cf6;
    --accent-pink: #ec4899;
    
    /* 背景色 */
    --bg-primary: #0a0a0a;      /* 页面背景 */
    --bg-secondary: #111111;    /* 卡片背景 */
    --bg-tertiary: #1a1a1a;     /* 悬停背景 */
    --bg-elevated: #161616;     /* 提升层级 */
    
    /* 边框 */
    --border-subtle: rgba(255, 255, 255, 0.06);
    --border-default: rgba(255, 255, 255, 0.1);
    --border-hover: rgba(255, 255, 255, 0.15);
    --border-glow: rgba(99, 102, 241, 0.4);
    
    /* 文字 */
    --text-primary: #fafafa;
    --text-secondary: #a1a1aa;
    --text-tertiary: #71717a;
    --text-muted: #52525b;
    
    /* 状态 */
    --success: #22c55e;
    --warning: #f59e0b;
    --error: #ef4444;
    --info: #3b82f6;
}
```

### 渐变预设
```css
/* 主渐变 */
--gradient-primary: linear-gradient(135deg, #6366f1, #4f46e5);
--gradient-accent: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899);

/* 文字渐变 */
--gradient-text: linear-gradient(135deg, #fafafa 0%, #a78bfa 100%);

/* 边框渐变 */
--gradient-border: linear-gradient(135deg, rgba(99, 102, 241, 0.5), transparent 50%);

/* 背景渐变 */
--gradient-glow: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent);
```

---

## 2. 字体系统

### 字体家族
```css
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
--font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', monospace;
```

### 字体层级
```css
/* 标题 */
--text-h1: 600 48px/1.1 var(--font-sans);      /* Hero 标题 */
--text-h2: 600 32px/1.2 var(--font-sans);      /* 页面标题 */
--text-h3: 600 24px/1.3 var(--font-sans);      /* 区块标题 */
--text-h4: 600 18px/1.4 var(--font-sans);      /* 卡片标题 */

/* 正文 */
--text-body: 400 16px/1.6 var(--font-sans);    /* 正文 */
--text-small: 400 14px/1.5 var(--font-sans);   /* 小字 */
--text-caption: 400 12px/1.4 var(--font-sans); /* 辅助文字 */

/* 数字 */
--text-stat: 300 64px/1 var(--font-sans);      /* 统计数字 */
```

---

## 3. 间距系统

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;

/* 页面 */
--page-padding: 24px;
--page-max-width: 1200px;
--navbar-height: 64px;
```

---

## 4. 组件规范

### 4.1 按钮

#### 主按钮
```css
.btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 
        0 0 0 1px rgba(255, 255, 255, 0.1) inset,
        0 4px 16px rgba(99, 102, 241, 0.4);
}

.btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 
        0 0 0 1px rgba(255, 255, 255, 0.15) inset,
        0 8px 24px rgba(99, 102, 241, 0.5);
}
```

#### 次按钮
```css
.btn-secondary {
    padding: 12px 24px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-secondary:hover {
    background: var(--bg-elevated);
    border-color: var(--border-hover);
}
```

#### 幽灵按钮
```css
.btn-ghost {
    padding: 8px 16px;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-ghost:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
}
```

### 4.2 卡片

#### 标准卡片
```css
.card {
    position: relative;
    background: var(--bg-secondary);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid var(--border-subtle);
    transition: all 0.3s ease;
}

.card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}
```

#### 渐变边框卡片
```css
.card-gradient-border {
    position: relative;
    background: var(--bg-secondary);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 0 0 1px var(--border-subtle);
}

.card-gradient-border::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 16px;
    padding: 1px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), transparent 50%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 0.3s;
}

.card-gradient-border:hover::before {
    opacity: 1;
}
```

### 4.3 输入框

```css
.input {
    width: 100%;
    padding: 12px 16px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    font-size: 15px;
    color: var(--text-primary);
    transition: all 0.2s;
}

.input:focus {
    outline: none;
    border-color: var(--primary-500);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.input::placeholder {
    color: var(--text-muted);
}
```

### 4.4 标签页

```css
.tabs {
    display: flex;
    gap: 4px;
    padding: 4px;
    background: var(--bg-tertiary);
    border-radius: 10px;
    width: fit-content;
}

.tab {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
}

.tab:hover {
    color: var(--text-primary);
}

.tab.active {
    background: var(--bg-elevated);
    color: var(--text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
```

---

## 5. 布局规范

### 5.1 页面结构
```
┌─────────────────────────────────────┐
│              Navbar                 │  64px
├─────────────────────────────────────┤
│                                     │
│              Hero                   │  根据内容
│                                     │
├─────────────────────────────────────┤
│                                     │
│           Main Content              │  自适应
│                                     │
├─────────────────────────────────────┤
│              Footer                 │
└─────────────────────────────────────┘
```

### 5.2 内容区域
```css
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
}

.section {
    padding: 64px 0;
}
```

### 5.3 网格系统
```css
/* 2列网格 */
.grid-2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

/* 3列网格 */
.grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}

/* 4列网格 */
.grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}

/* 响应式 */
@media (max-width: 1024px) {
    .grid-4 { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
    .grid-2, .grid-3, .grid-4 {
        grid-template-columns: 1fr;
    }
}
```

---

## 6. 动画规范

### 6.1 过渡动画
```css
/* 标准过渡 */
--transition-fast: 0.15s ease;
--transition-normal: 0.2s ease;
--transition-slow: 0.3s ease;

/* 弹性过渡 */
--transition-bounce: 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
```

### 6.2 关键帧
```css
/* 淡入 */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* 上浮 */
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

/* 脉冲发光 */
@keyframes pulse-glow {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}

/* 呼吸效果 */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
```

---

## 7. 各页面统一改造清单

### 7.1 首页 (index.html) ✅ 已完成原型
- [x] Hero 区域微光背景
- [x] 渐变边框卡片
- [x] 渐变色标题
- [ ] 实际代码实现

### 7.2 项目管理页 (project-management.html)
- [ ] 统一导航栏样式
- [ ] 项目卡片改为渐变边框
- [ ] 统计数字使用新字体
- [ ] 按钮使用新样式

### 7.3 第一阶段设置 (phase-one-setup.html)
- [ ] 步骤条样式统一
- [ ] 输入框使用新样式
- [ ] 表单卡片使用渐变边框

### 7.4 第二阶段生成 (phase-two-generation.html)
- [ ] 进度卡片样式统一
- [ ] 章节网格对齐
- [ ] 按钮样式统一

### 7.5 导航栏组件 (navbar.html)
- [ ] 毛玻璃效果
- [ ] 按钮样式统一
- [ ] 用户菜单样式

---

## 8. 实施计划

### 阶段一：基础样式
1. 创建 `design-system.css` 文件
2. 定义所有 CSS 变量
3. 创建基础组件样式

### 阶段二：组件改造
1. 更新按钮组件
2. 更新卡片组件
3. 更新输入框组件
4. 更新导航栏

### 阶段三：页面改造
1. 首页
2. 项目管理
3. 第一阶段
4. 第二阶段

### 阶段四：细节优化
1. 动画效果
2. 响应式适配
3. 交互反馈

---

## 9. 快速开始

### 步骤1：引入设计系统
```html
<link rel="stylesheet" href="/static/css/design-system.css">
```

### 步骤2：使用组件
```html
<!-- 主按钮 -->
<button class="btn btn-primary">🚀 开始创作</button>

<!-- 渐变边框卡片 -->
<div class="card card-gradient-border">
    <h3>卡片标题</h3>
    <p>卡片内容</p>
</div>

<!-- 输入框 -->
<input type="text" class="input" placeholder="请输入">
```

### 步骤3：自定义样式
```css
.my-custom-component {
    /* 使用设计系统变量 */
    background: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: 12px;
    padding: var(--space-4);
}
```

---

## 10. 检查清单

在改造每个页面时检查：

- [ ] 使用了正确的背景色
- [ ] 文字使用了正确的颜色层级
- [ ] 按钮使用了标准样式
- [ ] 卡片使用了渐变边框
- [ ] 间距符合设计系统
- [ ] 动画效果一致
- [ ] 响应式适配正确
