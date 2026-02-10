# 短剧工作台 - JSON导入格式规范

## 概述

JSON导入功能支持两种模式：
1. **简洁模式** - 只填写基础信息，系统自动AI生成分镜
2. **完整模式** - 填写完整的分镜数据，直接使用你的分镜

## 标准JSON格式

```json
{
  "title": "剧集名称 [必填]",
  "episode": 1,
  "description": "本集创意描述 [必填]",
  "world_setting": "世界观设定 [可选]",
  "style": "风格: 通用/玄幻/都市/废土...",
  "shot_duration": 5,
  "protagonist": {
    "name": "主角姓名 [必填]",
    "age": "年龄 [可选]",
    "appearance": "外观描述 [必填]",
    "role": "身份/性格 [可选]"
  },
  "shots": [
    {
      "shot_number": 1,
      "scene_title": "场景标题",
      "content": "镜头内容描述",
      "duration": 5,
      "camera_angle": "视角: 广角/中景/特写...",
      "camera_movement": "运镜: 推/拉/摇/移...",
      "scene_type": "场景类型: environment/dialogue/action",
      "dialogues": [
        {"speaker": "角色名", "text": "对话内容"}
      ]
    }
  ]
}
```

## 字段详解

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✓ | 剧集名称 |
| episode | number | | 集数，默认1 |
| description | string | ✓ | 本集创意描述 |
| world_setting | string | | 世界观设定 |
| style | string | | 风格类型，默认"通用" |
| shot_duration | number | | 每镜头时长(秒)，默认5 |
| protagonist | object | | 主角信息 |
| shots | array | | 分镜列表（如果有则直接使用，否则AI生成） |

### 主角字段 (protagonist)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✓ | 主角姓名 |
| age | string | | 年龄 |
| appearance | string | ✓ | 外观描述（用于角色一致性） |
| role | string | | 身份/性格描述 |

### 分镜字段 (shots[n])

| 字段 | 类型 | 说明 |
|------|------|------|
| shot_number | number | 镜头序号 |
| scene_title | string | 场景标题 |
| content | string | 镜头内容描述 |
| duration | number | 时长(秒) |
| camera_angle | string | 摄影角度 |
| camera_movement | string | 运镜方式 |
| scene_type | string | 场景类型 |
| dialogues | array | 对话列表 |

### 对话字段 (dialogues[n])

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| speaker | string | ✓ | 说话角色 |
| text | string | ✓ | 对话内容 |

## 使用示例

### 示例1: 简洁模式（推荐）

只需要基础信息，分镜由AI自动生成：

```json
{
  "title": "废土：开局徒手掹高达",
  "episode": 1,
  "description": "主角在废土垃圾场发现神秘机甲残骸，凭借机械改造能力修复机甲，遭遇掠夺者袭击，驾驶机甲反杀。",
  "protagonist": {
    "name": "林小满",
    "appearance": "黄色战术外卖服（改装），黑色低马尾，戴黑框眼镜，左臂有红色山海经图腾胎记"
  }
}
```

### 示例2: 完整模式（自带分镜）

提供完整的分镜数据，系统直接使用：

```json
{
  "title": "废土：开局徒手掹高达",
  "episode": 1,
  "description": "主角在废土垃圾场发现神秘机甲残骸...",
  "world_setting": "2145年，核战后的末世废土，灵气复苏导致生物变异...",
  "style": "废土",
  "shot_duration": 5,
  "protagonist": {
    "name": "林小满",
    "age": "22岁",
    "appearance": "黄色战术外卖服（改装），黑色低马尾，戴黑框眼镜，左臂有红色山海经图腾胎记，机械工具腰带",
    "role": "底层外卖骑手，性格贪媚但勇敢，擅长机械改造"
  },
  "shots": [
    {
      "shot_number": 1,
      "scene_title": "开场-废土场景",
      "content": "广角：荒芜的废土垃圾场，天空呈现诡异的紫红色",
      "duration": 6,
      "camera_angle": "广角",
      "camera_movement": "慢推进",
      "scene_type": "environment"
    },
    {
      "shot_number": 2,
      "scene_title": "发现机甲",
      "content": "中景：林小满蹲在机甲残骸旁，眼镜反射着金属光泽",
      "duration": 5,
      "camera_angle": "中景",
      "camera_movement": "固定",
      "scene_type": "dialogue",
      "dialogues": [
        {
          "speaker": "林小满",
          "text": "这玩意儿...至少值三百信用点！"
        }
      ]
    }
  ]
}
```

## 支持的兼容格式

系统支持智能解析多种常见格式：

### 格式1: 小说/故事结构
```json
{
  "story": "故事内容...",
  "chapters": [
    {"title": "第一章", "scenes": [...]}
  ]
}
```

### 格式2: 分镜表结构
```json
{
  "script": {"title": "...", "scenes": [...]},
  "shots": [...]
}
```

### 格式3: 简化结构
```json
{
  "name": "剧名",
  "idea": "创意...",
  "character": "角色..."
}
```

### 格式4: 纯文本数组
```json
[
  "第一个镜头描述...",
  "第二个镜头描述..."
]
```

## 快速使用指南

1. 点击"创建新项目" -> "从创意导入"
2. 切换到"JSON导入"模式
3. 粘贴AI生成的JSON
4. 点击"智能解析"自动识别格式
5. 点击"开始创作"

## 提示

- 如果没有提供`shots`字段，系统会自动调用AI生成分镜
- 如果提供了`shots`字段，系统会直接使用你的分镜数据
- 对话中的`speaker`建议使用主角姓名，而不是"主角"这样的通称
- `外观描述`越详细，AI生成的角色一致性越好
