# 基于JSON结构的角色编辑器集成指南

## 概述

本指南说明如何将新的基于JSON结构的动态表单系统集成到现有的角色编辑器中。

## 核心优势

### 1. 自动化表单生成
- 根据JSON数据结构自动生成UI
- 无需手动维护表单字段
- 支持动态添加新字段

### 2. 智能字段分类
- 自动将字段分组到合适的分类中
- 每个分类有清晰的图标和标签
- 支持折叠/展开，提升用户体验

### 3. 灵活的UI组件
- 文本输入框
- 长文本域
- 下拉选择
- 图标选择器
- 颜色选择器

## 文件结构

```
web/static/js/
├── character-editor.js              # 原有编辑器（保持兼容）
├── character-editor-json-based.js   # 新的JSON驱动系统
└── ...

web/static/css/
├── character-editor.css             # 原有样式
├── character-editor-json-based.css  # 新的动态表单样式
└── ...
```

## 快速开始

### 步骤1: 引入新文件

在HTML模板中添加新的CSS和JS文件：

```html
<!-- 在 head 中添加 -->
<link rel="stylesheet" href="/static/css/character-editor-json-based.css">

<!-- 在 body 底部添加 -->
<script src="/static/js/character-editor-json-based.js"></script>
```

### 步骤2: 修改表单填充函数

在 [`character-editor.js`](web/static/js/character-editor.js:677) 中更新 `populateCharacterForm` 函数：

```javascript
function populateCharacterForm(character) {
    const container = document.getElementById('dynamic-form-sections');
    if (!container) {
        console.error('❌ 找不到dynamic-form-sections容器');
        return;
    }
    
    // 使用新的JSON驱动表单生成器
    const form = generateFormFromJSON(character);
    container.innerHTML = '';
    container.appendChild(form);
    
    console.log('✅ 动态表单生成完成');
}
```

### 步骤3: 修改数据收集函数

在 [`character-editor.js`](web/static/js/character-editor.js:534) 中更新 `saveCharacter` 函数：

```javascript
async function saveCharacter() {
    // 使用新的数据收集函数
    const charData = collectDataFromForm();
    
    // 验证必填字段
    if (!charData.name || !charData.name.trim()) {
        alert('请输入角色名称');
        return;
    }
    
    // 更新或添加角色
    if (currentEditingCharacter !== null) {
        characterData[currentEditingCharacter] = charData;
    } else {
        characterData.push(charData);
        currentEditingCharacter = characterData.length - 1;
    }
    
    // 刷新列表
    renderCharacterList();
    showStatusMessage('✅ 角色保存成功', 'success');
}
```

## 字段定义系统

### 添加新字段

在 [`character-editor-json-based.js`](web/static/js/character-editor-json-based.js:8) 中的 `FIELD_DEFINITIONS` 对象中添加新字段：

```javascript
const FIELD_DEFINITIONS = {
    // 现有字段...
    
    // 添加新字段
    'new_field_name': {
        label: '字段显示名称',
        type: 'text',           // text | textarea | select | icon-selector | color-selector
        required: false,
        category: 'basic',      // 分类：basic | personality | appearance | background | faction | abilities | narrative | other
        priority: 10,           // 在分类中的显示顺序（数字越小越靠前）
        placeholder: '提示文本...'
    },
    
    // 嵌套对象字段
    'parent_field.child_field': {
        label: '子字段名称',
        type: 'textarea',
        category: 'background',
        priority: 1
    }
};
```

### 添加新分类

在 [`character-editor-json-based.js`](web/static/js/character-editor-json-based.js:155) 中的 `CATEGORY_CONFIG` 对象中添加新分类：

```javascript
const CATEGORY_CONFIG = {
    // 现有分类...
    
    // 添加新分类
    new_category: {
        label: '新分类名称',
        icon: '📁',           // Emoji图标
        layout: 'vertical',   // vertical | grid
        priority: 9           // 显示顺序
    }
};
```

## 使用示例

### 示例1: 添加"战斗能力"分类

```javascript
// 1. 添加分类
const CATEGORY_CONFIG = {
    // ...现有分类
    combat: {
        label: '战斗能力',
        icon: '⚔️',
        layout: 'vertical',
        priority: 6
    }
};

// 2. 添加字段
const FIELD_DEFINITIONS = {
    'combat_style': {
        label: '战斗风格',
        type: 'textarea',
        category: 'combat',
        priority: 1,
        placeholder: '描述角色的战斗风格...'
    },
    'signature_move': {
        label: '招牌招式',
        type: 'textarea',
        category: 'combat',
        priority: 2
    },
    'weakness': {
        label: '弱点',
        type: 'textarea',
        category: 'combat',
        priority: 3
    }
};
```

### 示例2: 添加嵌套对象字段

```javascript
// JSON数据结构
{
    "social_status": {
        "reputation": "声望卓著",
        "influence_area": "整个修仙界",
        "allies_count": 50
    }
}

// 字段定义
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
},
'social_status.allies_count': {
    label: '盟友数量',
    type: 'text',
    category: 'narrative',
    priority: 6
}
```

## 高级功能

### 1. 字段验证

```javascript
// 在字段定义中添加验证规则
'cultivation_level': {
    label: '修炼等级',
    type: 'text',
    category: 'abilities',
    priority: 1,
    validate: (value) => {
        // 自定义验证逻辑
        if (!value) return true;
        const validLevels = ['练气', '筑基', '金丹', '元婴', '化神'];
        return validLevels.some(level => value.includes(level));
    },
    errorMessage: '请输入有效的修炼等级'
}
```

### 2. 字段依赖

```javascript
// 实现字段间的依赖关系
'faction_affiliation.current_faction': {
    label: '当前势力',
    type: 'select',
    options: ['无', '正道盟', '魔庭', '散修'],
    category: 'faction',
    priority: 1,
    onChange: (value) => {
        // 当势力改变时，动态更新其他字段
        updateFactionRelatedFields(value);
    }
}
```

### 3. 自定义UI组件

```javascript
// 扩展新的UI组件类型
'custom_field': {
    label: '自定义字段',
    type: 'custom-component',
    category: 'other',
    priority: 1,
    render: (value) => {
        // 返回自定义的DOM元素
        return createCustomComponent(value);
    }
}
```

## 数据结构映射

### 简单字段
```javascript
// JSON: { "name": "诛仙" }
// 定义: name -> 文本输入框
```

### 嵌套对象
```javascript
// JSON: { "motivation": { "inner_drive": "进化" } }
// 定义: motivation.inner_drive -> 文本域
```

### 数组字段（待实现）
```javascript
// JSON: { "character_states": [...] }
// 定义: character_states -> 可重复表单项
```

## 兼容性说明

### 向后兼容
- 保留原有的 [`character-editor.js`](web/static/js/character-editor.js:1) 文件
- 新系统作为可选增强功能
- 可以逐步迁移，不影响现有功能

### 数据格式
- 完全兼容现有的JSON数据结构
- 支持新旧数据格式的混合使用
- 自动适配不同的字段命名

## 故障排除

### 问题1: 表单字段没有显示
**原因**: 字段没有在 `FIELD_DEFINITIONS` 中定义
**解决**: 在字段定义中添加对应的配置

### 问题2: 嵌套对象字段显示不正确
**原因**: 使用了错误的字段路径格式
**解决**: 使用 `parent.child` 格式定义嵌套字段

### 问题3: 分类折叠后无法展开
**原因**: CSS或JavaScript冲突
**解决**: 检查是否有样式冲突，确保 `toggleSection` 函数可用

## 性能优化

### 1. 懒加载
对于大量字段，可以实现懒加载：
```javascript
// 只在展开分类时生成表单
section.addEventListener('expand', () => {
    generateFieldsForCategory(category);
});
```

### 2. 虚拟滚动
对于超长的表单，使用虚拟滚动提升性能

### 3. 防抖保存
在用户输入时使用防抖技术，减少频繁的数据更新

## 未来扩展

### 计划中的功能
1. **数组字段支持**: 处理 `soul_matrix` 等数组字段
2. **字段验证**: 完整的表单验证系统
3. **字段依赖**: 实现字段间的动态关联
4. **模板系统**: 预设的角色模板
5. **批量编辑**: 支持批量修改多个角色
6. **导入导出**: JSON格式的导入导出功能

## 总结

基于JSON结构的动态表单系统提供了：
- ✅ 自动化的表单生成
- ✅ 灵活的字段定义
- ✅ 清晰的分类组织
- ✅ 良好的扩展性
- ✅ 完全的向后兼容

通过这个系统，您可以快速添加新字段和分类，而无需修改HTML模板或编写复杂的表单逻辑。