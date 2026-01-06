# 基于JSON结构的角色编辑器设计方案

## 设计思路

根据JSON数据结构动态生成UI表单，实现：
1. **自动字段识别**：根据JSON字段类型自动选择合适的UI组件
2. **智能布局**：根据字段关系自动组织表单布局
3. **嵌套结构支持**：支持处理嵌套对象和数组
4. **可扩展性**：易于添加新的字段类型和UI组件

## JSON数据结构分析

### 主角字段结构
```json
{
  "name": "诛仙",
  "role": "主角",
  "icon": "👤",
  "color": "#667eea",
  
  // 核心性格
  "core_personality": "极致利己、冷血、掌控欲极强",
  
  // 生活特征（嵌套对象）
  "living_characteristics": {
    "physical_presence": "...",
    "daily_habits": ["习惯1", "习惯2"],
    "speech_patterns": "...",
    "personal_quirks": "...",
    "emotional_triggers": "..."
  },
  
  // 灵魂矩阵（数组）
  "soul_matrix": [
    {
      "core_trait": "非人神性",
      "behavioral_manifestations": ["行为1", "行为2"]
    }
  ],
  
  // 动机（嵌套对象）
  "motivation": {
    "inner_drive": "...",
    "external_goals": "...",
    "secret_desires": "..."
  },
  
  // 势力关系（嵌套对象）
  "faction_affiliation": {
    "current_faction": "...",
    "position": "...",
    "loyalty_level": "...",
    "status_in_faction": "..."
  }
}
```

## 字段类型映射

### 1. 简单文本字段
- **组件**: `<input type="text">`
- **字段**: name, role, cultivation_level等

### 2. 长文本字段
- **组件**: `<textarea>`
- **字段**: background, motivation, description等

### 3. 嵌套对象
- **组件**: 分组表单（fieldset）
- **字段**: living_characteristics, motivation, faction_affiliation

### 4. 数组字段
- **组件**: 可重复表单项
- **字段**: soul_matrix, daily_habits, character_states

### 5. 选择字段
- **组件**: `<select>` 或颜色/图标选择器
- **字段**: role, icon, color, loyalty_level

## UI组织结构

### 第一层：基本信息
```
┌─────────────────────────────────────┐
│ 角色名称 | 角色类型                 │
│ 角色图标 | 代表颜色                 │
└─────────────────────────────────────┘
```

### 第二层：核心特征
```
┌─────────────────────────────────────┐
│ 核心性格（长文本）                  │
│ 对话风格示例（长文本）              │
└─────────────────────────────────────┘
```

### 第三层：嵌套对象分组
```
┌─────────────────────────────────────┐
│ 生活特征 ▼（可折叠）                │
│  ├─ 外貌特征（文本）                │
│  ├─ 日常习惯（数组，可添加）        │
│  ├─ 言语模式（文本）                │
│  └─ 情感触发点（文本）              │
└─────────────────────────────────────┘
```

### 第四层：数组字段
```
┌─────────────────────────────────────┐
│ 灵魂矩阵 [+ 添加]                   │
│  ┌─────────────────────────────┐   │
│  │ 核心特质：非人神性           │   │
│  │ 行为表现：                   │   │
│  │  - 行为1（可删除）           │   │
│  │  - 行为2（可删除）           │   │
│  │  [+ 添加行为] [删除项目]    │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 实现步骤

### Step 1: 字段类型检测
```javascript
function detectFieldType(key, value) {
  // 根据字段名和值类型推断UI组件
}
```

### Step 2: 动态表单生成器
```javascript
function generateFormFromSchema(schema) {
  // 根据JSON Schema生成表单
}
```

### Step 3: 嵌套结构处理器
```javascript
function processNestedObject(obj, parentKey) {
  // 处理嵌套对象，创建分组
}
```

### Step 4: 数组字段处理器
```javascript
function processArrayField(arr, parentKey) {
  // 处理数组，创建可重复项
}
```

## 优势

1. **自动化**：无需手动维护表单字段
2. **灵活性**：支持任意JSON结构
3. **一致性**：UI与数据结构完全对应
4. **可维护**：修改JSON结构自动更新UI

## 后续优化

1. 添加字段验证规则
2. 支持字段依赖关系
3. 添加字段提示和帮助文本
4. 支持自定义UI组件