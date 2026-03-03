# 模板组件架构设计

## 设计目标

1. **DRY原则** (Don't Repeat Yourself)
   - 导航栏、用户菜单等公共组件只定义一次
   - 修改一处，全站生效

2. **关注点分离**
   - 布局 (Layout) 与内容 (Content) 分离
   - 结构与样式分离

3. **易于维护**
   - 清晰的目录结构
   - 统一的命名规范
   - 完善的文档

4. **渐进式迁移**
   - 支持新旧页面共存
   - 不需要一次性重构所有页面

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      页面 (Page)                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  {% extends "layouts/base.html" %}                     │  │
│  │                                                        │  │
│  │  {% block content %}                                   │  │
│  │    ┌─────────────────────────────────────────────┐     │  │
│  │    │           页面特有内容                        │     │  │
│  │    └─────────────────────────────────────────────┘     │  │
│  │  {% endblock %}                                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   布局模板 (Layout)                          │
│              layouts/base.html                               │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐            │
│  │   Navbar    │  │ Content  │  │   Footer    │            │
│  │  Component  │  │  Block   │  │  (optional) │            │
│  └─────────────┘  └──────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  组件 (Components)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   navbar     │  │  user-menu   │  │    footer    │       │
│  │   .html      │  │   .html      │  │    .html     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构设计

```
web/templates/
│
├── _template-example.html      # 示例页面模板（复制起点）
│
├── layouts/                    # 布局模板目录
│   ├── base.html              # 标准布局（带导航栏）
│   └── base-simple.html       # 简化布局（无导航栏，用于登录页等）
│
├── components/                 # 可复用组件目录
│   ├── navbar.html            # 统一导航栏
│   ├── user-menu.html         # 用户菜单（已含积分系统）
│   ├── footer.html            # 页脚组件
│   ├── flash-messages.html    # Flash消息提示
│   └── head-inject.html       # 快速注入导航栏（过渡方案）
│
├── macros/                     # Jinja2宏（可选）
│   └── forms.html             # 表单组件宏
│
└── [各页面.html]               # 继承基础模板的页面
```

---

## 组件设计原则

### 1. 独立性原则

每个组件应该可以独立使用，不依赖特定的页面结构：

```html
<!-- ✅ 好的设计：组件自包含 -->
<div class="user-menu-component">
    <style> /* 组件样式 */ </style>
    <div class="user-menu">...</div>
    <script> // 组件逻辑 </script>
</div>
```

### 2. 可配置性原则

组件应该支持通过参数进行配置：

```html
<!-- 通过 with 语句传递参数 -->
{% with show_back_btn=false, title="自定义标题" %}
    {% include 'components/navbar.html' %}
{% endwith %}
```

### 3. 样式隔离原则

使用特定的CSS类名前缀，避免全局污染：

```css
/* ✅ 好的设计：使用组件前缀 */
.navbar-component { ... }
.navbar-component .nav-btn { ... }

/* ❌ 避免：全局样式 */
.nav-btn { ... }  /* 可能影响其他组件 */
```

---

## 模板继承设计

### 基础模板结构

```html
<!DOCTYPE html>
<html>
<head>
    <!-- 公共头部 -->
    <title>{% block title %}默认标题{% endblock %}</title>
    
    <!-- 公共CSS -->
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- 公共组件：导航栏 -->
    {% include 'components/navbar.html' %}
    
    <!-- 内容区 -->
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <!-- 公共组件：页脚 -->
    {% block footer %}{% endblock %}
    
    <!-- 公共JS -->
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 块设计规范

| 块名 | 用途 | 是否必须实现 | 说明 |
|------|------|-------------|------|
| `title` | 页面标题 | 否 | 默认"大文娱系统" |
| `extra_css` | 额外CSS | 否 | 页面特有样式 |
| `content` | 主内容 | **是** | 页面主体 |
| `footer` | 页脚 | 否 | 默认有页脚，可覆盖 |
| `extra_js` | 额外JS | 否 | 页面特有脚本 |
| `main_class` | 主容器类 | 否 | 用于特殊布局 |

---

## 迁移策略设计

### 阶段1：基础准备（已完成）

- [x] 创建基础模板
- [x] 创建导航栏组件
- [x] 创建用户菜单组件
- [x] 编写迁移文档

### 阶段2：试点验证（建议立即开始）

选择1-2个页面进行试点迁移，验证方案可行性：
- 选择简单的页面（如 account.html）
- 按照迁移指南操作
- 记录问题和解决方案

### 阶段3：分批迁移（按优先级）

| 批次 | 页面 | 预计时间 |
|------|------|----------|
| 第1批 | 4个高优先级页面 | 2小时 |
| 第2批 | 7个中优先级页面 | 2.5小时 |
| 第3批 | 14个低优先级页面 | 3.5小时 |
| 第4批 | 5个特殊页面 | 1小时 |

### 阶段4：全面切换

- 更新开发规范，要求新页面使用模板继承
- 逐步清理遗留的重复代码
- 归档备份文件

---

## 扩展设计

### 未来可添加的组件

1. **面包屑导航** (`breadcrumb.html`)
   ```html
   {% include 'components/breadcrumb.html' with items=[...] %}
   ```

2. **分页组件** (`pagination.html`)
   ```html
   {% include 'components/pagination.html' with page=current_page total=total_pages %}
   ```

3. **数据表格** (`data-table.html`)
   ```html
   {% include 'components/data-table.html' with columns=[...] data=[...] %}
   ```

4. **模态框** (`modal.html`)
   ```html
   {% include 'components/modal.html' with id="my-modal" title="标题" %}
   ```

### 宏(Macro)设计

对于需要重复使用的UI元素，使用Jinja2宏：

```html
<!-- macros/buttons.html -->
{% macro primary_button(text, href="#", icon=None) %}
    <a href="{{ href }}" class="btn btn-primary">
        {% if icon %}<span class="icon">{{ icon }}</span>{% endif %}
        {{ text }}
    </a>
{% endmacro %}
```

使用：
```html
{% from 'macros/buttons.html' import primary_button %}

{{ primary_button("保存", "/save", icon="💾") }}
```

---

## 性能考虑

### 1. 组件缓存

Jinja2会自动缓存模板片段，组件被多次包含时不会重复解析。

### 2. CSS优化

- 组件样式使用内联 `<style>`，减少HTTP请求
- 或者使用构建工具将组件CSS合并

### 3. 按需加载

对于大型组件，考虑使用AJAX懒加载：

```html
<div id="user-menu-container" data-load-url="/api/user-menu">
    <!-- 内容通过JS动态加载 -->
</div>
```

---

## 维护指南

### 修改组件

1. 编辑对应的组件文件
2. 测试所有使用该组件的页面
3. 更新组件文档

### 添加新组件

1. 在 `components/` 目录创建新文件
2. 确保组件自包含（HTML + CSS + JS）
3. 在本文档中添加组件说明
4. 创建使用示例

### 废弃组件

1. 标记组件为废弃（在文件顶部添加注释）
2. 保留文件但不再维护
3. 逐步替换使用处
4. 确认无使用后删除

---

## 总结

这套架构提供了：

- ✅ **清晰的层次结构** - Layout → Page → Component
- ✅ **灵活的扩展能力** - 易于添加新组件
- ✅ **渐进式迁移路径** - 不需要一次性重构
- ✅ **完善的文档支持** - 多个维度的文档覆盖

通过这套架构，可以实现一处修改、全站生效的目标，大大提高开发效率和维护便利性。
