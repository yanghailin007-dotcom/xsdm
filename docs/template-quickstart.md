# 模板组件快速开始指南

## 你已经拥有的

✅ **user-menu.html** - 用户下拉菜单组件（已修复）  
✅ **navbar.html** - 统一导航栏组件  
✅ **layouts/base.html** - 基础模板  
✅ **layouts/base-simple.html** - 简化模板  

---

## 三种集成方案（选一个适合你的）

### 方案A：模板继承（推荐用于新页面）

**适用场景**: 创建新页面，或重构旧页面

**步骤**:
1. 复制示例模板:
   ```bash
   cp web/templates/_template-example.html web/templates/my-page.html
   ```

2. 修改内容块:
   ```html
   {% extends "layouts/base.html" %}
   
   {% block title %}我的页面{% endblock %}
   
   {% block content %}
       <h1>页面内容</h1>
   {% endblock %}
   ```

3. 访问 `/my-page` 测试

---

### 方案B：组件包含（快速给现有页面加导航栏）

**适用场景**: 现有页面只想添加统一导航栏，不想大改

**步骤**:

1. 在现有页面的 `<body>` 开始处添加:
   ```html
   <body>
       {% include 'components/navbar.html' %}
       <!-- 原有内容 -->
   </body>
   ```

2. 给 body 添加顶部间距样式:
   ```html
   <style>
       body { padding-top: 64px; } /* 给固定导航栏留出空间 */
   </style>
   ```

3. 测试导航栏和用户菜单是否正常工作

---

### 方案C：手动复制（临时方案）

**适用场景**: 页面结构特殊，无法使用上述方案

**步骤**:
1. 复制 `navbar.html` 中的样式到页面 `<head>`
2. 复制 `navbar.html` 中的 HTML 结构到页面 `<body>` 开始处
3. 复制 `user-menu.html` 到导航栏的适当位置
4. 测试并调整样式冲突

---

## 立即可用的页面

### 高优先级（建议立即迁移）

复制下面的代码快速迁移核心页面：

#### 1. phase-one-setup-new.html

```html
{% extends "layouts/base.html" %}

{% block title %}第一阶段设定 - 小说生成系统{% endblock %}

{% block extra_css %}
    <!-- 保留原有CSS链接 -->
{% endblock %}

{% block content %}
    <!-- 保留原页面body内的内容（除去原有的导航栏代码） -->
{% endblock %}

{% block extra_js %}
    <!-- 保留原有JS链接 -->
{% endblock %}
```

#### 2. phase-two-generation.html

同上，只修改 `title`

#### 3. project-management.html

同上

---

## 一键迁移脚本

使用提供的脚本预览迁移效果:

```bash
# 预览变更（不实际修改）
python tools/migrate_to_base_template.py web/templates/account.html --dry-run

# 实际执行迁移（会创建备份）
python tools/migrate_to_base_template.py web/templates/account.html
```

---

## 常见问题

### Q: 迁移后样式乱了怎么办？
检查:
1. 是否删除了原页面的 `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` 标签
2. 是否保留了页面特有的CSS
3. 是否有CSS类名冲突

### Q: 用户菜单不展开怎么办？
确保:
1. `user-info.js` 已正确加载
2. 页面已登录（有session）
3. 检查控制台是否有JS错误

### Q: 可以在导航栏添加自定义按钮吗？
可以，编辑 `components/navbar.html`，在适当位置添加按钮。

---

## 下一步建议

1. **立即**: 选择1-2个页面试用方案A或B
2. **本周**: 迁移高优先级的4个核心页面
3. **本月**: 逐步迁移其他页面
4. **长期**: 所有新页面都使用模板继承

---

## 需要帮助？

查看详细文档:
- [完整迁移指南](./template-migration-guide.md)
- [迁移状态追踪](./template-migration-status.md)
- 示例模板: `web/templates/_template-example.html`
