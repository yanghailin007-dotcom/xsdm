# 模板组件系统 - 总览

## 这是什么？

这是一套为 Flask + Jinja2 项目设计的**模板组件架构**，解决多页面项目中导航栏、用户菜单等公共组件的复用问题。

## 解决了什么问题？

| 问题 | 解决方案 |
|------|----------|
| 31个页面各自维护导航栏 | 统一组件，一处修改全站生效 |
| 用户菜单代码重复 | 抽取为独立组件 |
| 新页面需要复制大量样板代码 | 使用模板继承，只写内容 |
| 样式不一致 | 统一样式定义在组件内 |

## 核心文件

```
web/templates/
├── layouts/
│   ├── base.html              # ⭐ 标准布局（带导航栏）
│   └── base-simple.html       # 简化布局（登录页等）
├── components/
│   ├── navbar.html            # ⭐ 统一导航栏
│   ├── user-menu.html         # ⭐ 用户菜单（含积分系统）
│   └── footer.html            # 页脚组件
└── _template-example.html     # ⭐ 页面模板示例
```

## 三种使用方式

### 方式1：模板继承（推荐）

适合：**新页面、重构旧页面**

```html
{% extends "layouts/base.html" %}

{% block title %}页面标题{% endblock %}

{% block content %}
    <h1>页面内容</h1>
{% endblock %}
```

✅ 优点：最规范，自动获得所有公共组件  
❌ 缺点：需要修改现有页面结构

### 方式2：组件包含

适合：**给现有页面快速添加导航栏**

```html
<body>
    {% include 'components/navbar.html' %}
    <!-- 原有内容 -->
</body>
```

✅ 优点：改动最小，快速生效  
❌ 缺点：页面仍需维护部分样板代码

### 方式3：手动复制

适合：**页面结构特殊，无法使用上述方案**

直接将组件代码复制到页面中。

✅ 优点：最灵活  
❌ 缺点：维护困难，不推荐

---

## 快速开始（5分钟上手）

### Step 1: 复制示例模板

```bash
cp web/templates/_template-example.html web/templates/test-page.html
```

### Step 2: 修改内容

编辑 `test-page.html`：

```html
{% block title %}测试页面{% endblock %}

{% block content %}
    <h1>Hello World</h1>
    <p>这是我的新页面</p>
{% endblock %}
```

### Step 3: 添加路由

在 `app.py` 或对应的路由文件中添加：

```python
@app.route('/test-page')
def test_page():
    return render_template('test-page.html')
```

### Step 4: 访问测试

打开浏览器访问 `/test-page`，应该能看到：
- 顶部统一导航栏
- 用户菜单（登录后）
- 页面内容

---

## 迁移现有页面

### 高优先级页面（建议立即迁移）

| 页面 | 状态 | 操作 |
|------|------|------|
| `phase-one-setup-new.html` | ⬜ 待迁移 | 使用方式1 |
| `phase-two-generation.html` | ⬜ 待迁移 | 使用方式1 |
| `project-management.html` | ⬜ 待迁移 | 使用方式1 |
| `novels.html` | ⬜ 待迁移 | 使用方式1或2 |

### 迁移步骤

1. **备份原文件**
   ```bash
   cp page.html page.html.backup
   ```

2. **选择方案**
   - 有时间重构 → 方案1（模板继承）
   - 快速修复 → 方案2（组件包含）

3. **测试验证**
   - 页面正常显示
   - 导航栏功能正常
   - 用户菜单可以展开

4. **更新状态**
   修改 `docs/template-migration-status.md`

---

## 文档导航

| 文档 | 内容 | 适合 |
|------|------|------|
| `template-quickstart.md` | 5分钟快速上手 | 立即开始 |
| `template-migration-guide.md` | 详细迁移指南 | 全面了解 |
| `template-migration-status.md` | 页面迁移进度表 | 跟踪进度 |
| `template-architecture.md` | 架构设计说明 | 深入理解 |
| 本文档 | 总览和入口 | 第一次阅读 |

---

## 常见问题 FAQ

### Q: 用户菜单点击不展开？

检查：
1. `user-info.js` 中的ID是否是 `user-dropdown`（不是 `userDropdown`）
2. 浏览器控制台是否有JS错误
3. 用户是否已登录

### Q: 样式和原有页面冲突？

解决方案：
1. 使用更具体的CSS选择器
2. 将组件样式放在页面样式之后加载
3. 使用 `!important` 覆盖（不推荐）

### Q: 可以在导航栏添加新按钮吗？

可以，编辑 `components/navbar.html`，在适当位置添加按钮代码。

### Q: 某些页面不需要导航栏？

使用简化布局：
```html
{% extends "layouts/base-simple.html" %}
```

### Q: 如何修改所有页面的页脚？

编辑 `layouts/base.html` 中的 `footer` 块。

---

## 最佳实践

### ✅ 应该做的

- 新页面都使用模板继承
- 组件保持独立性
- 定期同步迁移进度
- 保留备份直到确认无误

### ❌ 不应该做的

- 在页面中重复定义导航栏
- 直接修改组件生成的备份文件
- 一次性迁移所有页面（风险高）
- 忽略测试验证

---

## 技术支持

遇到问题？

1. 查看详细文档：`docs/template-*.md`
2. 参考示例：`web/templates/_template-example.html`
3. 检查浏览器控制台错误
4. 对比已迁移的页面（如 `index.html`）

---

## 路线图

- [x] 创建基础模板系统
- [x] 创建导航栏组件
- [x] 创建用户菜单组件
- [x] 编写完整文档
- [ ] 迁移高优先级页面（建议本周完成）
- [ ] 迁移中优先级页面（建议本月完成）
- [ ] 迁移低优先级页面
- [ ] 添加更多组件（面包屑、分页等）

---

**开始使用**: 查看 `template-quickstart.md`

**详细了解**: 查看 `template-architecture.md`

**跟踪进度**: 查看 `template-migration-status.md`
