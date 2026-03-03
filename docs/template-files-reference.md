# 模板系统文件清单

## 目录结构

```
web/templates/
├── _template-example.html          # 示例页面模板
├── layouts/                        # 布局模板目录
│   ├── base.html                  # 标准基础模板 ⭐
│   ├── base-new.html              # 新版基础模板（可选）
│   └── base-simple.html           # 简化模板（无导航栏）
├── components/                     # 组件目录
│   ├── navbar.html                # 统一导航栏 ⭐
│   ├── user-menu.html             # 用户菜单（含积分系统）⭐
│   ├── footer.html                # 页脚组件
│   ├── head-inject.html           # 快速注入组件
│   └── ...                        # 其他业务组件
docs/
├── template-system-README.md      # 总览文档 ⭐
├── template-quickstart.md         # 快速开始 ⭐
├── template-migration-guide.md    # 迁移指南
├── template-migration-status.md   # 迁移状态
├── template-architecture.md       # 架构设计
└── template-files-reference.md    # 本文件
tools/
└── migrate_to_base_template.py    # 迁移辅助脚本
```

## 核心文件说明

### ⭐ 必须了解

| 文件 | 路径 | 作用 |
|------|------|------|
| `base.html` | `web/templates/layouts/` | 标准布局模板 |
| `navbar.html` | `web/templates/components/` | 统一导航栏组件 |
| `user-menu.html` | `web/templates/components/` | 用户菜单组件 |
| `_template-example.html` | `web/templates/` | 页面模板示例 |
| `template-system-README.md` | `docs/` | 系统总览文档 |
| `template-quickstart.md` | `docs/` | 快速开始指南 |

### 📄 布局模板

| 文件 | 用途 | 使用场景 |
|------|------|----------|
| `base.html` | 标准布局，含导航栏 | 大多数页面 |
| `base-new.html` | 新版布局（实验性） | 新页面可选 |
| `base-simple.html` | 简化布局，无导航栏 | 登录页、落地页 |

### 🧩 组件

| 文件 | 功能 | 状态 |
|------|------|------|
| `navbar.html` | 统一导航栏 | ✅ 已可用 |
| `user-menu.html` | 用户菜单+积分系统 | ✅ 已修复 |
| `footer.html` | 页脚 | ⬜ 待完善 |
| `head-inject.html` | 快速注入导航栏 | ✅ 过渡方案 |

### 📚 文档

| 文件 | 内容 | 适合读者 |
|------|------|----------|
| `template-system-README.md` | 系统总览 | 所有人 |
| `template-quickstart.md` | 5分钟上手 | 想立即开始的人 |
| `template-migration-guide.md` | 详细迁移指南 | 需要全面了解的人 |
| `template-migration-status.md` | 页面迁移进度 | 跟踪进度的人 |
| `template-architecture.md` | 架构设计说明 | 想深入理解的人 |
| `template-files-reference.md` | 文件清单 | 查找文件的人 |

### 🛠️ 工具

| 文件 | 功能 | 使用方式 |
|------|------|----------|
| `migrate_to_base_template.py` | 自动迁移脚本 | `python tools/migrate_to_base_template.py page.html` |

## 文件依赖关系

```
base.html
├── navbar.html
│   └── user-menu.html
├── footer.html (可选)
└── flash-messages (内联)

页面.html
└── extends base.html
    └── 填充 content 块
```

## 使用路径速查

### 在页面中使用

```html
<!-- 继承基础模板 -->
{% extends "layouts/base.html" %}

<!-- 包含组件 -->
{% include 'components/navbar.html' %}
{% include 'components/user-menu.html' %}
```

### 静态文件引用

```html
<!-- CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

<!-- JS -->
<script src="{{ url_for('static', filename='js/script.js') }}"></script>
```

## 快速访问

| 你想做什么 | 查看文件 |
|-----------|----------|
| 了解整个系统 | `docs/template-system-README.md` |
| 立即开始使用 | `docs/template-quickstart.md` |
| 创建新页面 | `web/templates/_template-example.html` |
| 给现有页面加导航栏 | `web/templates/components/head-inject.html` |
| 了解迁移步骤 | `docs/template-migration-guide.md` |
| 查看迁移进度 | `docs/template-migration-status.md` |
| 深入理解架构 | `docs/template-architecture.md` |

## 文件大小参考

```
# 文档
README.md                    ~5.7 KB
quickstart.md                ~3.7 KB
migration-guide.md           ~5.1 KB
migration-status.md          ~4.5 KB
architecture.md              ~10.4 KB

# 模板
base.html                    ~1.9 KB
base-simple.html             ~1.3 KB
navbar.html                  ~4.8 KB
user-menu.html               ~14.6 KB
template-example.html        ~1.9 KB

# 工具
migrate_to_base_template.py  ~4.6 KB
```

---

**总文件数**: 15个文件  
**总大小**: ~50 KB  
**核心文件**: 6个
