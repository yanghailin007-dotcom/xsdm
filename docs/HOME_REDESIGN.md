# 大文娱系统首页 - 大厂级设计重构

## 设计系统

### 色彩方案（参考 Linear + Vercel）

```css
/* 主色调 - 紫蓝渐变 */
--primary-500: #6366f1;    /* Indigo */
--primary-600: #4f46e5;    /* Deep Indigo */
--accent-purple: #8b5cf6;  /* Purple */

/* 背景色 - 深色模式 */
--bg-primary: #0a0a0a;     /* 纯黑背景 */
--bg-secondary: #111111;   /* 卡片背景 */
--bg-tertiary: #1a1a1a;    /* 悬停背景 */
--bg-elevated: #161616;    /* 提升层级 */

/* 边框色 */
--border-subtle: rgba(255, 255, 255, 0.06);
--border-default: rgba(255, 255, 255, 0.1);
--border-hover: rgba(255, 255, 255, 0.15);
--border-glow: rgba(99, 102, 241, 0.3);    /* 发光边框 */

/* 文字色 */
--text-primary: #fafafa;
--text-secondary: #a1a1aa;
--text-tertiary: #71717a;
--text-muted: #52525b;

/* 状态色 */
--success: #22c55e;
--warning: #f59e0b;
--error: #ef4444;
```

---

## 布局结构

### 1. Hero 区域（全新设计）

```
┌─────────────────────────────────────────────────────────────┐
│  [微光背景 - 动态渐变网格]                                    │
│                                                              │
│           🎨 AI 小说创作平台                                  │
│           标签：创新工作台                                    │
│                                                              │
│     用 AI 将创意变成畅销小说                                  │
│     两阶段生成 · 智能世界观 · 自动化发布                      │
│                                                              │
│     ┌─────────────────────────────────────────┐             │
│     │  📊  1      📄  14      🔄  0          │             │
│     │  项目      章节      进行中            │             │
│     └─────────────────────────────────────────┘             │
│                                                              │
│     [🚀 开始创作]  [📖 查看教程]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**设计要点：**
- 背景使用动态渐变网格（类似 Linear）
- 标题使用渐变色文字
- 统计数字使用大号字体 + 细字重
- 按钮使用渐变背景 + 发光效果

---

### 2. 快捷入口卡片（玻璃拟态风格）

```
┌─────────────────────────────────────────────────────────────┐
│  快速开始                                                    │
│  选择一个方式开始创作                                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  🎨          │  │  📁          │  │  ✨          │      │
│  │  两阶段生成  │  │  项目管理    │  │  创意库      │      │
│  │  从设定开始  │  │  3个项目     │  │  12个创意    │      │
│  │              │  │              │  │              │      │
│  │  [开始 →]    │  │  [管理 →]    │  │  [浏览 →]    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  📚          │  │  🎨          │  │  🍅          │      │
│  │  查看作品    │  │  封面制作    │  │  番茄上传    │      │
│  │  14章节      │  │  AI设计      │  │  一键发布    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**设计要点：**
- 卡片使用玻璃拟态效果（backdrop-blur）
- 1px 渐变边框（hover 时发光）
- 图标使用渐变背景圆形
- 底部添加数据统计

---

### 3. 创意输入区域（分步表单）

```
┌─────────────────────────────────────────────────────────────┐
│  开始新的创作                                                │
│                                                              │
│  [📝 从空白开始]  [💡 从创意库]  [📋 从模板]               │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  小说标题                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 凡人修仙传同人：观战者                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  小说简介                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 穿越者李尘身具观战悟道体质...                       │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  总章节数              本次生成章节                        │
│  ┌──────────┐          ┌──────────┐                       │
│  │ 200 章 ▼ │          │ 5 章   ▼ │                       │
│  └──────────┘          └──────────┘                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  💰 预计消耗: 10 创造点    当前余额: 88 点         │   │
│  │                                                     │   │
│  │              [ 开始生成 → ]                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**设计要点：**
- 输入框使用 subtle 边框，focus 时渐变边框
- 标签页切换使用 pill 样式
- 底部成本估算使用独立卡片
- 主按钮使用渐变 + 阴影

---

## CSS 实现核心代码

### 1. 渐变边框卡片（参考 Linear）

```css
.feature-card {
  position: relative;
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 24px;
  
  /* 渐变边框 */
  border: 1px solid transparent;
  background-clip: padding-box;
  
  /* 发光效果 */
  box-shadow: 
    0 0 0 1px var(--border-subtle),
    0 4px 24px rgba(0, 0, 0, 0.3);
  
  transition: all 0.3s ease;
}

.feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.3),
    transparent 50%,
    rgba(139, 92, 246, 0.2)
  );
  -webkit-mask: 
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask: 
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.feature-card:hover::before {
  opacity: 1;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 0 0 1px var(--border-hover),
    0 8px 32px rgba(99, 102, 241, 0.15);
}
```

### 2. 渐变文字标题

```css
.gradient-text {
  background: linear-gradient(
    135deg,
    #fafafa 0%,
    #a1a1aa 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.gradient-text-accent {
  background: linear-gradient(
    135deg,
    #6366f1 0%,
    #8b5cf6 50%,
    #a78bfa 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

### 3. 微光背景动画

```css
.hero-background {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(
      ellipse 80% 50% at 50% -20%,
      rgba(99, 102, 241, 0.15),
      transparent
    ),
    radial-gradient(
      ellipse 60% 40% at 80% 50%,
      rgba(139, 92, 246, 0.1),
      transparent
    );
  animation: pulse-glow 8s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
```

### 4. 主按钮样式

```css
.btn-primary {
  position: relative;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: white;
  padding: 12px 32px;
  border-radius: 10px;
  border: none;
  font-weight: 500;
  
  box-shadow: 
    0 1px 2px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 4px 16px rgba(99, 102, 241, 0.4);
  
  transition: all 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 
    0 1px 2px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.15) inset,
    0 8px 24px rgba(99, 102, 241, 0.5);
}
```

---

## 字体系统

```css
/* 标题 */
--font-h1: 600 48px/1.1 system-ui, -apple-system, sans-serif;
--font-h2: 600 32px/1.2 system-ui, -apple-system, sans-serif;
--font-h3: 600 24px/1.3 system-ui, -apple-system, sans-serif;

/* 正文 */
--font-body: 400 16px/1.6 system-ui, -apple-system, sans-serif;
--font-small: 400 14px/1.5 system-ui, -apple-system, sans-serif;
--font-caption: 400 12px/1.4 system-ui, -apple-system, sans-serif;

/* 数字统计 */
--font-stat: 300 64px/1 system-ui, -apple-system, sans-serif;
```

---

## 间距系统

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

/* 页面内边距 */
--page-padding: 24px;
--max-width: 1200px;
```

---

## 实施步骤

1. **更新 CSS 变量** - 替换新的色彩系统
2. **重构 Hero 区域** - 添加微光背景和渐变文字
3. **重新设计卡片** - 使用渐变边框和悬停效果
4. **优化表单** - 使用新的输入框样式
5. **添加微交互** - 悬停动画、加载状态

---

## 参考网站

- **Linear**: https://linear.app（深色模式 + 渐变边框）
- **Vercel**: https://vercel.com（渐变文字 + 卡片设计）
- **Notion**: https://notion.so（简洁布局 + 留白）
- **Stripe**: https://stripe.com（精美渐变 + 动画）
