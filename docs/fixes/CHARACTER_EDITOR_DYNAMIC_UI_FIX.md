# 角色编辑器动态UI修复

## 问题

角色编辑器的HTML模板中包含大量硬编码的JSON示例数据，而不是根据实际的角色数据动态生成UI。这导致：

1. UI不能根据JSON数据结构自适应
2. 无法显示复杂角色数据结构的所有字段
3. 表单字段固定，无法扩展

## 解决方案

### 1. 清理HTML模板

**文件**: `web/templates/components/character-editor-modal.html`

- 移除所有硬编码的角色数据
- 保留基本的模态框结构
- 添加`dynamic-form-sections`容器用于动态生成表单

```html
<div id="dynamic-form-sections">
    <!-- 动态生成的表单区域 -->
</div>
```

### 2. 实现动态表单生成

**文件**: `web/static/js/character-editor.js`

#### 新增功能：

1. **`createFormSection(title, fields, layout)`**
   - 创建表单区块
   - 支持grid和vertical两种布局

2. **`createFormField(label, type, id, value, required)`**
   - 创建表单字段
   - 自动选择input或textarea
   - 支持必填验证

3. **`generateDynamicFields(character)`**
   - 根据角色数据动态生成字段
   - 智能字段映射（中文名称）
   - 自动过滤复杂对象和数组

4. **重新实现`populateCharacterForm(character)`**
   - 动态生成完整表单
   - 保留基本信息（名称、类型）
   - 自动添加图标和颜色选择器
   - 根据数据结构生成其他字段

#### 字段映射表：

```javascript
const fieldMappings = {
    'core_personality': '核心性格',
    'living_characteristics': '生活特征',
    'background': '背景故事',
    'motivation': '动机',
    'growth_arc': '成长弧线',
    'dialogue_style_example': '对话风格示例',
    'cultivation_level': '修炼等级',
    'abilities': '特殊能力',
    'skills': '主要技能',
    'physical_presence': '外貌特征',
    'speech_patterns': '言语模式',
    'inner_conflicts': '内心冲突',
    'description': '角色描述',
    'personality': '性格特点',
    'appearance': '外貌特征'
};
```

### 3. 增强数据加载

**文件**: `web/static/js/character-editor.js`

#### `loadCharacterData()`改进：

支持复杂的角色数据结构：

1. **`{main_character, important_characters}` 结构**
   - 自动提取主角和重要角色
   - 保留原始数据中的所有字段
   - 智能映射到标准格式

2. **简单数组结构**
   - 直接使用数组数据
   - 兼容旧格式

### 4. 更新保存功能

**文件**: `web/static/js/character-editor.js`

#### `saveCharacter()`改进：

- 从动态表单收集所有字段数据
- 使用`dataset.fieldId`标识字段
- 自动补充默认值
- 保持数据完整性

### 5. 添加CSS样式

**文件**: `web/static/css/character-editor.css`

```css
.form-vertical {
    display: flex;
    flex-direction: column;
    gap: 16px;
}
```

## 使用示例

### 基本用法

```javascript
// 打开角色编辑器
openCharacterEditor();
```

### 数据结构示例

```json
{
  "main_character": {
    "name": "诛仙",
    "core_personality": "极致利己、冷血",
    "living_characteristics": {
      "physical_presence": "暗红色长剑..."
    },
    "background": "前世是资本巨鳄...",
    "cultivation_level": "凡铁级"
  },
  "important_characters": [
    {
      "name": "叶红衣",
      "role": "核心盟友",
      "core_trait": "黑化/执着",
      "cultivation_level": "炼气三层"
    }
  ]
}
```

### 自动生成的表单字段

1. **基本信息**
   - 角色名称 *
   - 角色类型
   - 角色图标（选择器）
   - 代表颜色（选择器）

2. **详细信息**（动态生成）
   - 核心性格
   - 生活特征
   - 背景故事
   - 动机
   - 成长弧线
   - 对话风格示例
   - 修炼等级
   - 特殊能力
   - 主要技能
   - 外貌特征
   - 言语模式
   - 内心冲突

## 优势

1. **灵活性**: UI完全根据数据结构动态生成
2. **可扩展**: 新增字段无需修改代码
3. **智能**: 自动选择合适的输入控件
4. **兼容**: 支持多种数据格式
5. **用户友好**: 字段使用中文显示

## 测试

1. 打开角色编辑器
2. 检查是否正确加载角色数据
3. 选择角色查看表单是否正确生成
4. 编辑并保存角色
5. 验证数据完整性

## 未来改进

1. 支持嵌套对象的编辑（如living_characteristics）
2. 添加字段验证规则
3. 支持自定义字段类型
4. 添加字段分组功能
5. 支持字段排序

## 相关文件

- `web/templates/components/character-editor-modal.html` - 模态框模板
- `web/static/js/character-editor.js` - 核心逻辑
- `web/static/css/character-editor.css` - 样式
- `web/api/character_api.py` - API接口

## 创建时间

2026-01-05