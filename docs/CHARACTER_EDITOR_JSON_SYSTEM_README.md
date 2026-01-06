# 基于JSON结构的动态角色编辑器系统

## 📋 项目概述

这是一个创新的、基于JSON数据结构自动生成UI表单的角色编辑器系统。它能够根据角色的JSON数据结构，智能地生成对应的表单界面，无需手动编写HTML表单代码。

## 🎯 核心设计理念

### 1. **数据驱动UI**
- 表单完全由JSON数据结构驱动
- 自动识别字段类型并匹配合适的UI组件
- 支持嵌套对象和复杂数据结构

### 2. **智能分类组织**
- 自动将字段按功能分类（基本信息、性格、背景等）
- 每个分类可折叠/展开，提升用户体验
- 支持自定义分类和字段映射

### 3. **高度可扩展**
- 通过配置文件轻松添加新字段
- 支持自定义UI组件
- 模块化设计，易于维护和扩展

## 📁 文件结构

```
docs/
├── CHARACTER_EDITOR_JSON_BASED_DESIGN.md      # 设计方案文档
├── CHARACTER_EDITOR_JSON_INTEGRATION_GUIDE.md  # 集成指南
└── CHARACTER_EDITOR_JSON_SYSTEM_README.md      # 本文档（系统总览）

web/static/js/
├── character-editor.js              # 原有编辑器（保持兼容）
└── character-editor-json-based.js   # 新的JSON驱动系统 ⭐

web/static/css/
├── character-editor.css             # 原有样式
└── character-editor-json-based.css  # 新的动态表单样式 ⭐
```

## 🚀 快速开始

### 1. 引入文件

在HTML模板中添加：

```html
<link rel="stylesheet" href="/static/css/character-editor-json-based.css">
<script src="/static/js/character-editor-json-based.js"></script>
```

### 2. 使用API

```javascript
// 生成表单
const form = generateFormFromJSON(characterData);
document.getElementById('form-container').appendChild(form);

// 收集数据
const collectedData = collectDataFromForm();
```

### 3. 定义字段

在 [`FIELD_DEFINITIONS`](web/static/js/character-editor-json-based.js:8) 中配置：

```javascript
const FIELD_DEFINITIONS = {
    'field_name': {
        label: '字段显示名称',
        type: 'text',           // text | textarea | select
        category: 'basic',      // 分类
        priority: 1             // 顺序
    }
};
```

## 🎨 支持的字段类型

### 1. **文本输入** (`text`)
```javascript
'name': {
    label: '角色名称',
    type: 'text',
    required: true
}
```

### 2. **长文本域** (`textarea`)
```javascript
'background': {
    label: '背景故事',
    type: 'textarea',
    placeholder: '详细描述...'
}
```

### 3. **下拉选择** (`select`)
```javascript
'role': {
    label: '角色类型',
    type: 'select',
    options: ['主角', '配角', '反派']
}
```

### 4. **图标选择器** (`icon-selector`)
```javascript
'icon': {
    label: '角色图标',
    type: 'icon-selector'
}
```

### 5. **颜色选择器** (`color-selector`)
```javascript
'color': {
    label: '代表颜色',
    type: 'color-selector'
}
```

## 📦 数据分类系统

系统内置8个预定义分类：

| 分类 | 图标 | 描述 |
|------|------|------|
| `basic` | 📋 | 基本信息（名称、类型、图标） |
| `personality` | 🧠 | 核心性格（性格、对话风格） |
| `appearance` | ✨ | 生活特征（外貌、习惯） |
| `background` | 📖 | 背景故事（背景、动机） |
| `faction` | ⚔️ | 势力关系（所属势力、地位） |
| `abilities` | 💪 | 能力状态（等级、技能） |
| `narrative` | 📝 | 叙事作用（角色功能、读者印象） |
| `other` | 📦 | 其他信息 |

## 🔧 高级功能

### 嵌套对象支持

自动处理嵌套的JSON结构：

```json
{
    "motivation": {
        "inner_drive": "进化",
        "external_goals": "吞噬",
        "secret_desires": "成神"
    }
}
```

字段定义：
```javascript
'motivation.inner_drive': {
    label: '内在驱动力',
    type: 'textarea',
    category: 'background'
}
```

### 字段优先级

使用 `priority` 控制字段显示顺序：

```javascript
{
    'field1': { priority: 1 },  // 先显示
    'field2': { priority: 2 },  // 后显示
    'field3': { priority: 3 }   // 最后显示
}
```

### 自定义分类

添加新的分类：

```javascript
const CATEGORY_CONFIG = {
    custom_category: {
        label: '自定义分类',
        icon: '🎯',
        layout: 'vertical',
        priority: 10
    }
};
```

## 💡 使用示例

### 示例1: 添加战斗能力字段

```javascript
// 在 FIELD_DEFINITIONS 中添加
'combat_style': {
    label: '战斗风格',
    type: 'textarea',
    category: 'abilities',
    priority: 4,
    placeholder: '描述角色的战斗风格...'
},
'signature_move': {
    label: '招牌招式',
    type: 'textarea',
    category: 'abilities',
    priority: 5
}
```

### 示例2: 添加社会关系字段

```javascript
// 处理嵌套对象
'social_status.reputation': {
    label: '声望',
    type: 'text',
    category: 'narrative',
    priority: 4
},
'social_status.influence_area': {
    label: '影响力范围',
    type: 'textarea',
    category: 'narrative',
    priority: 5
}
```

## 🔄 工作流程

### 1. 数据加载
```
JSON数据 → 字段识别 → 分类组织 → UI生成
```

### 2. 用户编辑
```
用户输入 → 表单验证 → 数据收集 → 更新JSON
```

### 3. 数据保存
```
收集数据 → 格式转换 → 保存到后端 → 刷新UI
```

## 🎯 核心优势

### ✅ 自动化
- 无需手写HTML表单
- 自动适配数据结构变化
- 减少维护成本

### ✅ 灵活性
- 支持任意JSON结构
- 可自定义字段类型和验证
- 易于扩展新功能

### ✅ 用户体验
- 清晰的字段分组
- 可折叠的分类区块
- 响应式设计，支持移动端

### ✅ 可维护性
- 配置驱动的字段定义
- 模块化的代码结构
- 完善的文档和示例

## 🛠️ 技术实现

### 核心算法

1. **字段类型检测**
   - 根据字段名和值类型推断UI组件
   - 支持自动类型映射

2. **动态表单生成**
   - 根据JSON Schema生成表单
   - 支持嵌套对象和数组

3. **数据收集与验证**
   - 自动收集表单数据
   - 重建嵌套对象结构

### 关键函数

```javascript
// 生成表单
generateFormFromJSON(character) → HTMLElement

// 收集数据
collectDataFromForm() → Object

// 创建字段
createFormFieldElement(field) → HTMLElement

// 切换区块
toggleSection(button) → void
```

## 📊 数据流程图

```
┌─────────────┐
│  JSON数据   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  字段识别与分类  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  动态表单生成    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  用户编辑输入    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  数据收集与保存  │
└─────────────────┘
```

## 🔮 未来扩展

### 计划中的功能

1. **数组字段支持**
   - 处理 `soul_matrix` 等数组字段
   - 支持动态添加/删除数组项

2. **字段验证系统**
   - 完整的表单验证
   - 自定义验证规则
   - 实时验证反馈

3. **字段依赖关系**
   - 实现字段间的动态关联
   - 条件显示字段
   - 级联选择

4. **模板系统**
   - 预设的角色模板
   - 快速创建角色
   - 批量应用模板

5. **导入导出**
   - JSON格式导入导出
   - 支持多种数据格式
   - 数据迁移工具

6. **高级UI组件**
   - 富文本编辑器
   - 图片上传
   - 标签系统
   - 时间轴组件

## 📖 相关文档

- [设计方案](CHARACTER_EDITOR_JSON_BASED_DESIGN.md) - 详细的系统设计文档
- [集成指南](CHARACTER_EDITOR_JSON_INTEGRATION_GUIDE.md) - 集成步骤和API说明
- [现有编辑器](../CHARACTER_EDITOR_README.md) - 原有编辑器文档

## 🤝 贡献指南

### 添加新字段类型

1. 在 `createFormFieldElement` 中添加新的case
2. 实现对应的UI组件
3. 在 `collectDataFromForm` 中添加数据收集逻辑
4. 更新文档和示例

### 添加新分类

1. 在 `CATEGORY_CONFIG` 中定义新分类
2. 设置合适的图标和布局
3. 更新文档

### 优化建议

- 性能优化：实现懒加载和虚拟滚动
- 用户体验：添加更多交互动画
- 可访问性：改进键盘导航和屏幕阅读器支持

## 📞 技术支持

如有问题或建议，请参考：
- 设计文档了解系统架构
- 集成指南查看API使用
- 示例代码学习最佳实践

## 📄 许可证

本项目是小说创作系统的一部分，遵循项目的整体许可证。

---

**版本**: 1.0.0  
**最后更新**: 2026-01-05  
**维护者**: Kilo Code