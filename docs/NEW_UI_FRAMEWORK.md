# 大文娱系统 - 新UI框架设计方案

## 🎯 设计目标

1. **框架化设计** - 使用组件化架构，复用导航栏、卡片、按钮等
2. **新旧并存** - 不修改旧页面，通过配置切换新旧UI
3. **渐进式迁移** - 新页面使用新框架，旧页面逐步迁移
4. **一键切换** - 用户可在设置中选择新旧界面风格

---

## 📁 目录结构

```
web/
├── templates/
│   ├── layouts/                    # 布局模板
│   │   ├── base.html              # 旧版基础模板
│   │   └── base-v2.html           # 新版基础模板（新设计系统）
│   │
│   ├── components/v2/             # 新版组件库
│   │   ├── navbar.html            # 导航栏（含用户菜单）
│   │   ├── user-menu.html         # 用户下拉菜单
│   │   ├── feature-card.html      # 功能卡片
│   │   ├── stat-card.html         # 统计卡片
│   │   ├── form-input.html        # 表单输入
│   │   ├── btn-primary.html       # 主按钮
│   │   ├── btn-secondary.html     # 次按钮
│   │   ├── section-header.html    # 区块标题
│   │   ├── hero-section.html      # Hero区域
│   │   └── footer.html            # 页脚
│   │
│   ├── pages/v2/                  # 新版页面（使用v2框架）
│   │   ├── landing-v2.html        # 新Landing页
│   │   ├── index-v2.html          # 新首页
│   │   ├── dashboard-v2.html      # 新仪表板
│   │   └── ...
│   │
│   └── pages/                     # 旧版页面（保持不变）
│       ├── landing.html
│       ├── index.html
│       └── ...
│
├── static/
│   ├── css/v2/                    # 新版样式系统
│   │   ├── design-system.css      # 设计系统变量+基础
│   │   ├── components.css         # 组件样式
│   │   ├── layouts.css            # 布局样式
│   │   └── utilities.css          # 工具类
│   │
│   ├── js/v2/                     # 新版脚本
│   │   ├── components.js          # 组件交互
│   │   └── theme.js               # 主题切换
│   │
│   └── css/                       # 旧版样式（保持不变）
│       └── style.css
│
└── config/
    └── ui_version.py              # UI版本配置

src/web/
├── middleware/
│   └── ui_version_middleware.py   # UI版本中间件
│
└── api/
    └── settings_api.py            # 用户设置API（含UI版本）
```

---

## 🎨 设计系统 (Design System)

### 色彩方案

```css
:root {
    /* 主色调 */
    --v2-primary-500: #6366f1;
    --v2-primary-600: #4f46e5;
    --v2-accent-purple: #8b5cf6;
    --v2-accent-pink: #ec4899;
    
    /* 背景色 */
    --v2-bg-primary: #0a0a0a;
    --v2-bg-secondary: #111111;
    --v2-bg-tertiary: #1a1a1a;
    --v2-bg-elevated: #161616;
    
    /* 边框 */
    --v2-border-subtle: rgba(255, 255, 255, 0.06);
    --v2-border-default: rgba(255, 255, 255, 0.1);
    --v2-border-hover: rgba(255, 255, 255, 0.15);
    
    /* 文字 */
    --v2-text-primary: #fafafa;
    --v2-text-secondary: #a1a1aa;
    --v2-text-tertiary: #71717a;
    --v2-text-muted: #52525b;
}
```

### 组件规范

| 组件 | 类名 | 说明 |
|------|------|------|
| 导航栏 | `.v2-navbar` | 固定顶部，毛玻璃效果 |
| 功能卡片 | `.v2-feature-card` | 渐变边框发光，悬停抬升 |
| 主按钮 | `.v2-btn-primary` | 渐变背景，阴影 |
| 次按钮 | `.v2-btn-secondary` | 描边，深色背景 |
| 输入框 | `.v2-input` | 深色背景，focus渐变边框 |

---

## 🔀 入口切换机制

### 1. 用户级切换（推荐）

用户在设置中选择UI版本，存储到数据库/LocalStorage：

```python
# 用户设置表
class UserSettings:
    user_id: int
    ui_version: str  # "v1" | "v2" | "auto"
    theme: str       # "dark" | "light" | "auto"
```

```javascript
// 前端存储
localStorage.setItem('ui_version', 'v2');
```

### 2. URL参数切换（开发测试）

```
/?ui=v2          # 强制使用v2
/?ui=v1          # 强制使用v1
```

### 3. 全局配置切换（管理员）

```python
# config/ui_version.py
DEFAULT_UI_VERSION = "v2"  # 全局默认
ENABLE_V2 = True           # 是否启用v2
V2_PAGES = [               # 已迁移到v2的页面
    "landing",
    "index", 
    "dashboard",
]
```

---

## 🚀 实现步骤

### Phase 1: 搭建框架（1-2天）

1. 创建 `base-v2.html` 基础模板
2. 创建设计系统 CSS (`design-system.css`)
3. 创建核心组件（navbar, cards, buttons）
4. 创建中间件处理版本切换

### Phase 2: 迁移核心页面（2-3天）

1. Landing 页 → `landing-v2.html`
2. 首页 → `index-v2.html`
3. 仪表板 → `dashboard-v2.html`

### Phase 3: 功能页面迁移（逐步）

按优先级逐个迁移：
- 项目管理
- 小说创作
- 视频制作
- ...

---

## 💡 使用示例

### 创建新页面

```html
<!-- templates/pages/v2/my-page-v2.html -->
{% extends "layouts/base-v2.html" %}

{% block title %}我的页面 - 大文娱系统{% endblock %}

{% block content %}
    <!-- 使用组件 -->
    {% include 'components/v2/hero-section.html' with title="页面标题" subtitle="副标题" %}
    
    <div class="v2-container">
        {% include 'components/v2/feature-card.html' with 
            icon="📖" 
            title="功能标题" 
            desc="功能描述" 
        %}
    </div>
{% endblock %}
```

### 组件复用

```html
<!-- 导航栏（所有v2页面自动包含） -->
<nav class="v2-navbar">
    <div class="v2-navbar-brand">...</div>
    <div class="v2-navbar-actions">
        {% include 'components/v2/user-menu.html' %}
    </div>
</nav>
```

---

## ⚙️ 切换逻辑

```python
# middleware/ui_version_middleware.py
class UIVersionMiddleware:
    def process_request(self, request):
        # 1. 检查URL参数
        ui_version = request.args.get('ui')
        
        # 2. 检查用户设置
        if not ui_version and current_user.is_authenticated:
            ui_version = current_user.settings.ui_version
        
        # 3. 使用全局默认
        if not ui_version:
            ui_version = config.DEFAULT_UI_VERSION
        
        # 4. 存储到请求上下文
        request.ui_version = ui_version
        
        # 5. 自动路由到对应模板
        if ui_version == 'v2' and request.endpoint in V2_PAGES:
            request.template_suffix = '-v2'
```

---

## 📊 迁移进度追踪

| 页面 | 状态 | 优先级 |
|------|------|--------|
| Landing | ✅ 已设计 | P0 |
| 首页 | 🔄 进行中 | P0 |
| 仪表板 | ⏳ 待开始 | P0 |
| 项目管理 | ⏳ 待开始 | P1 |
| 小说创作 | ⏳ 待开始 | P1 |
| 视频制作 | ⏳ 待开始 | P2 |

---

## ✅ 优势

1. **零风险** - 旧页面完全不动，随时可回退
2. **渐进式** - 按优先级逐个迁移，不影响业务
3. **一致性** - 所有v2页面使用统一组件，风格一致
4. **可测试** - URL参数随时切换，方便对比测试
5. **用户体验** - 用户可自主选择喜欢的版本
