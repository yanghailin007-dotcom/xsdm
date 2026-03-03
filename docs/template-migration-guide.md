# 模板架构迁移指南

## 现状
当前有31个模板文件，都是独立的HTML，没有使用模板继承。导航栏在每个页面重复定义。

## 目标架构
使用Jinja2模板继承，实现：
- 一处修改，全站生效
- 减少重复代码
- 更容易维护

## 目录结构

```
web/templates/
├── layouts/                    # 布局模板
│   ├── base.html              # 基础布局
│   └── base-simple.html       # 简化布局（无导航栏）
├── components/                 # 可复用组件
│   ├── navbar.html            # 导航栏
│   ├── user-menu.html         # 用户菜单
│   ├── footer.html            # 页脚
│   └── flash-messages.html    # 消息提示
├── macros/                     # Jinja2宏
│   └── forms.html             # 表单组件
└── pages/                      # 页面模板（可选）
    ├── index.html
    ├── novels.html
    └── ...
```

## 迁移策略

### 方案1：新建页面使用新架构（推荐用于新页面）

新创建的页面直接继承基础模板：

```html
{% extends "layouts/base.html" %}

{% block title %}页面标题 - 大文娱系统{% endblock %}

{% block extra_css %}
    <!-- 页面特有CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/page-specific.css') }}">
{% endblock %}

{% block content %}
    <!-- 页面内容 -->
    <div class="page-wrapper">
        <h1>页面标题</h1>
        <!-- ... -->
    </div>
{% endblock %}

{% block extra_js %}
    <!-- 页面特有JS -->
    <script src="{{ url_for('static', filename='js/page-specific.js') }}"></script>
{% endblock %}
```

### 方案2：渐进式重构现有页面

1. **选择试点页面**（建议从简单页面开始）
   - 推荐顺序：`account.html` → `dashboard.html` → `novels.html` → ...

2. **备份原文件**
   ```bash
   cp web/templates/account.html web/templates/account.html.backup
   ```

3. **提取页面特有内容**
   - 删除 `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` 等标签
   - 删除重复的导航栏代码
   - 保留页面主体内容

4. **添加模板继承标记**
   在文件开头添加：
   ```html
   {% extends "layouts/base.html" %}
   ```

5. **测试验证**
   - 检查页面渲染是否正常
   - 检查导航栏、用户菜单是否工作
   - 检查所有交互功能

### 方案3：使用页面模板快速创建（推荐）

复制 `web/templates/_template-example.html` 作为起点：

```bash
cp web/templates/_template-example.html web/templates/new-page.html
```

## 模板块说明

### base.html 提供的块

| 块名 | 用途 | 是否必填 |
|------|------|----------|
| `title` | 页面标题 | 否 |
| `extra_css` | 额外CSS | 否 |
| `content` | 页面主内容 | 是 |
| `footer` | 页脚（可覆盖） | 否 |
| `extra_js` | 额外JS | 否 |
| `main_class` | 主容器CSS类 | 否 |

## 常见问题

### Q: 某个页面不需要导航栏怎么办？
使用 `base-simple.html`：
```html
{% extends "layouts/base-simple.html" %}
```

### Q: 需要在特定位置插入内容怎么办？
可以在基础模板中添加更多块：
```html
{% block before_content %}{% endblock %}
{% block content %}{% endblock %}
{% block after_content %}{% endblock %}
```

### Q: 如何在页面中使用组件？
```html
{% include 'components/user-menu.html' %}
```

### Q: 迁移后样式不对怎么办？
1. 检查是否有遗漏的CSS链接
2. 检查是否有样式冲突
3. 使用浏览器的开发者工具检查元素

## 迁移检查清单

- [ ] 页面继承基础模板
- [ ] 标题设置正确
- [ ] 导航栏显示正常
- [ ] 用户菜单可以展开/收起
- [ ] 所有原有功能正常工作
- [ ] 响应式布局正常
- [ ] 没有重复的CSS/JS引入

## 迁移优先级

按以下优先级逐步迁移：

1. **高优先级**（用户高频访问）
   - `index.html`
   - `phase-one-setup-new.html`
   - `phase-two-generation.html`
   - `project-management.html`

2. **中优先级**
   - `novels.html`
   - `novel_view.html`
   - `cover_maker.html`
   - `fanqie_upload.html`

3. **低优先级**（工具页面）
   - `contract_management.html`
   - `dashboard.html`
   - 其他工具页面

## 工具支持

使用迁移助手脚本预览变更：

```bash
python tools/migrate_to_base_template.py web/templates/account.html --dry-run
```

## 最佳实践

1. **保持组件独立性**
   - 每个组件应该可以独立使用
   - 组件不应该依赖特定页面结构

2. **CSS命名规范**
   - 使用 BEM 命名法：`block__element--modifier`
   - 避免全局样式冲突

3. **JavaScript模块化**
   - 将JS功能封装为独立函数
   - 使用 `window.xxx = xxx` 导出全局函数供HTML事件使用

4. **测试覆盖**
   - 每个迁移的页面都应该进行完整测试
   - 特别关注用户认证相关页面
