# 新UI迁移指南

## 📋 快速开始

### 1. 访问新UI

直接通过 URL 参数访问：
```
http://localhost:5000/landing?ui=v2
```

### 2. 切换回旧UI
```
http://localhost:5000/landing?ui=v1
```

---

## 🏗️ 创建新页面（使用V2框架）

### 步骤1: 继承基础模板

```html
<!-- templates/pages/v2/my-page-v2.html -->
{% extends "layouts/base-v2.html" %}

{% block title %}我的页面 - 大文娱系统{% endblock %}

{% block content %}
    <!-- 页面内容 -->
{% endblock %}
```

### 步骤2: 使用组件

```html
{% block content %}
    <!-- 使用内置组件 -->
    {% include 'components/v2/section-header.html' with 
        label="Section" 
        title="区块标题" 
    %}
    
    <!-- 使用卡片 -->
    <div class="v2-card v2-card--gradient">
        <div class="v2-card__icon v2-card__icon--purple">🎨</div>
        <h3 class="v2-card__title">卡片标题</h3>
        <p class="v2-card__desc">卡片描述文字...</p>
    </div>
{% endblock %}
```

### 步骤3: 注册路由

```python
# src/web/routes.py

@app.route('/my-page')
def my_page():
    # 自动根据用户设置选择 V1/V2
    return render_page('my-page', title="我的页面")
```

### 步骤4: 更新配置

```python
# config/ui_version.py

V2_PAGES = {
    "landing": ("landing_v2", True),      # 已完成
    "my-page": ("my_page_v2", True),      # 新页面
    "dashboard": ("dashboard_v2", False),  # 进行中
}
```

---

## 🧩 可用组件

### 导航相关
- `components/v2/navbar.html` - 导航栏（自动包含）
- `components/v2/user-menu.html` - 用户下拉菜单
- `components/v2/footer.html` - 页脚（自动包含）

### 内容组件
- `v2-card` - 卡片
- `v2-card--gradient` - 渐变边框卡片
- `v2-section-header` - 区块标题
- `v2-hero` - Hero区域
- `v2-features__grid` - 功能网格

### 表单组件
- `v2-input` - 输入框
- `v2-textarea` - 文本域
- `v2-label` - 标签
- `v2-form-group` - 表单组
- `v2-btn` - 按钮

---

## 🎨 自定义样式

### 使用CSS变量

```css
.my-custom-component {
    background: var(--v2-bg-secondary);
    color: var(--v2-text-primary);
    padding: var(--v2-space-4);
    border-radius: var(--v2-radius-lg);
}
```

### 渐变文字

```html
<h1 class="v2-gradient-text">渐变标题</h1>
```

### 玻璃拟态

```html
<div class="v2-glass">
    毛玻璃效果内容
</div>
```

---

## 🔄 从V1迁移到V2

### 对照表

| V1 元素 | V2 替代 |
|---------|---------|
| `.container` | `.v2-container` |
| `.btn.btn-primary` | `.v2-btn.v2-btn--primary` |
| `.card` | `.v2-card` |
| `.navbar` | `.v2-navbar` (自动包含) |
| `style.css` | `css/v2/design-system.css` |

### 迁移检查清单

- [ ] 继承 `base-v2.html`
- [ ] 替换按钮类名
- [ ] 替换卡片类名
- [ ] 替换表单类名
- [ ] 更新颜色变量
- [ ] 测试响应式
- [ ] 添加到 `V2_PAGES` 配置

---

## 🐛 调试技巧

### 查看当前UI版本

在页面中添加：
```html
<!-- 调试信息 -->
<p>当前UI版本: {{ ui_version }}</p>
<p>V2启用: {{ v2_enabled }}</p>
```

### 强制刷新缓存

```
Ctrl + Shift + R
```

---

## 📚 参考资源

- 设计文档: `docs/NEW_UI_FRAMEWORK.md`
- 样式文件: `web/static/css/v2/`
- 组件模板: `web/templates/components/v2/`
- 示例页面: `web/templates/pages/v2/landing-v2.html`
