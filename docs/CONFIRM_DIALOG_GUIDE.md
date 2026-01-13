# 美观的确认对话框使用指南

## 概述

我们已经创建了一个美观的自定义确认对话框组件，用于替代简陋的浏览器原生 `confirm()` 对话框。这个组件提供了更好的用户体验和视觉效果。

## 功能特点

- ✨ 现代化设计，带有渐变背景和动画效果
- 🎨 支持多种类型：问题、警告、危险、成功
- 📱 完全响应式，支持移动端
- 🌓 支持暗色主题
- ⌨️ 键盘快捷键支持（ESC关闭，Enter确认）
- ♿ 无障碍功能支持
- 🔧 灵活的配置选项

## 文件结构

```
web/
├── static/
│   ├── css/
│   │   └── confirm-dialog.css          # 对话框样式
│   └── js/
│       └── confirm-dialog.js           # 对话框逻辑
└── templates/
    └── components/
        └── navbar-with-logout.html     # 可复用组件
```

## 快速开始

### 1. 在新页面中使用

在需要使用确认对话框的页面中，按照以下步骤操作：

#### 步骤1：引入CSS和JS

在HTML的 `<head>` 中引入CSS：

```html
<link rel="stylesheet" href="/static/css/confirm-dialog.css">
```

在 `</body>` 前引入JS：

```html
<script src="/static/js/confirm-dialog.js"></script>
```

#### 步骤2：替换logout函数

将原有的 `logout()` 函数替换为：

```html
<script>
function logout() {
    confirmLogout().then(confirmed => {
        if (confirmed) {
            window.location.href = '/logout';
        }
    });
}
</script>
```

### 2. 预设的便捷函数

组件提供了几个预设的便捷函数：

#### `confirmLogout()` - 退出登录确认

```javascript
confirmLogout().then(confirmed => {
    if (confirmed) {
        // 执行退出操作
        window.location.href = '/logout';
    }
});
```

效果：
- 🚪 图标
- 橙色警告样式
- 标题："退出登录"
- 消息："您确定要退出登录吗？"

#### `confirmDelete(itemName)` - 删除确认

```javascript
confirmDelete('这个项目').then(confirmed => {
    if (confirmed) {
        // 执行删除操作
        deleteProject();
    }
});
```

效果：
- 🗑️ 图标
- 红色危险样式
- 标题："确认删除"
- 消息："您确定要删除这个项目吗？"

#### `confirmAction(actionName, options)` - 通用操作确认

```javascript
confirmAction('保存更改', {
    title: '保存确认',
    type: 'question'
}).then(confirmed => {
    if (confirmed) {
        // 执行操作
        saveChanges();
    }
});
```

### 3. 自定义对话框

使用 `showConfirm()` 或 `confirmDialog.show()` 创建完全自定义的对话框：

```javascript
showConfirm('您确定要继续吗？', {
    title: '继续操作',
    subMessage: '此操作将保存您的所有更改',
    confirmText: '继续',
    cancelText: '返回',
    type: 'warning',
    icon: '⚠️'
}).then(confirmed => {
    if (confirmed) {
        // 用户点击了确认
    } else {
        // 用户点击了取消或关闭对话框
    }
});
```

## 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | string | '确认操作' | 对话框标题 |
| `message` | string | '您确定要执行此操作吗？' | 主要消息 |
| `subMessage` | string | '' | 次要消息（可选） |
| `confirmText` | string | '确认' | 确认按钮文本 |
| `cancelText` | string | '取消' | 取消按钮文本 |
| `type` | string | 'question' | 对话框类型：'question', 'warning', 'danger', 'success' |
| `icon` | string | 自动 | 自定义图标（emoji或文本） |

## 对话框类型

### question（问题）
- 默认类型
- 蓝紫色渐变
- 图标：❓
- 用于一般性确认

### warning（警告）
- 橙色渐变
- 图标：⚠️
- 用于警告性操作（如退出登录）

### danger（危险）
- 红色渐变
- 图标：🗑️
- 用于危险操作（如删除）

### success（成功）
- 绿色渐变
- 图标：✅
- 用于成功确认

## 示例：更新现有页面

### 示例1：video-studio.html

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频工作室</title>
    <link rel="stylesheet" href="/static/css/video-studio.css">
    <link rel="stylesheet" href="/static/css/confirm-dialog.css">
</head>
<body>
    <!-- 页面内容 -->
    
    <script src="/static/js/confirm-dialog.js"></script>
    <script src="/static/js/video-studio.js"></script>
    <script>
        function logout() {
            confirmLogout().then(confirmed => {
                if (confirmed) {
                    window.location.href = '/logout';
                }
            });
        }
    </script>
</body>
</html>
```

### 示例2：在其他页面使用

对于任何有退出登录按钮的页面（如 `index.html`, `novels.html`, `project-management.html` 等），只需：

1. 在 `<head>` 添加：
```html
<link rel="stylesheet" href="/static/css/confirm-dialog.css">
```

2. 在 `</body>` 前添加：
```html
<script src="/static/js/confirm-dialog.js"></script>
<script>
function logout() {
    confirmLogout().then(confirmed => {
        if (confirmed) {
            window.location.href = '/logout';
        }
    });
}
</script>
```

## 高级用法

### 链式调用

```javascript
// 先确认，再执行
confirmDelete('文件')
    .then(confirmed => {
        if (confirmed) {
            return showConfirm('是否同时删除相关联的记录？');
        }
        return Promise.resolve(false);
    })
    .then(confirmed => {
        if (confirmed) {
            deleteFileWithRecords();
        } else {
            deleteFileOnly();
        }
    });
```

### 异步操作

```javascript
confirmAction('提交审核').then(async confirmed => {
    if (confirmed) {
        try {
            await submitForReview();
            showSuccessToast('提交成功！');
        } catch (error) {
            showErrorToast('提交失败：' + error.message);
        }
    }
});
```

### 条件确认

```javascript
function handleDelete(item) {
    if (item.isImportant) {
        // 重要项目需要双重确认
        confirmDelete(item.name).then(firstConfirmed => {
            if (firstConfirmed) {
                showConfirm('此项目非常重要，真的要删除吗？', {
                    type: 'danger',
                    icon: '⚠️'
                }).then(secondConfirmed => {
                    if (secondConfirmed) {
                        deleteItem(item.id);
                    }
                });
            }
        });
    } else {
        // 普通项目一次确认即可
        confirmDelete(item.name).then(confirmed => {
            if (confirmed) {
                deleteItem(item.id);
            }
        });
    }
}
```

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 键盘快捷键

- **Enter** - 确认操作
- **Escape** - 取消操作
- **Tab** - 在按钮间切换

## 无障碍功能

- 完整的键盘导航支持
- ARIA标签支持
- 高对比度模式支持
- 屏幕阅读器友好

## 故障排除

### 对话框不显示

确保已正确引入CSS和JS文件：

```html
<link rel="stylesheet" href="/static/css/confirm-dialog.css">
<script src="/static/js/confirm-dialog.js"></script>
```

### 样式混乱

检查CSS文件加载顺序，确保 `confirm-dialog.css` 在其他样式之后引入。

### 函数未定义

确保在使用函数前已加载 `confirm-dialog.js`，或者将代码放在 `DOMContentLoaded` 事件中：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // 在这里使用 confirmDialog
});
```

## 总结

新的确认对话框组件提供了：

1. **更好的用户体验** - 美观的界面和流畅的动画
2. **更灵活的配置** - 支持自定义文本、图标和样式
3. **更强大的功能** - Promise支持、键盘快捷键、响应式设计
4. **更简单的集成** - 只需几行代码即可使用

替换所有页面的 `confirm()` 为新的确认对话框，将大大提升应用的视觉质量和用户体验！