# 创意系统改进说明

## 概述

本次改进包含两个主要优化：

1. **同人小说检测优化**：解决将原创创意误判为同人小说的问题
2. **多文件创意存储**：支持将创意拆分为多个独立文件，便于管理

---

## 问题1：同人小说检测误判修复

### 问题描述

之前的系统会将包含任何引号内容的文本都识别为同人小说。例如，您的原创创意《修仙：我是一柄魔剑》中提到功法"《吞天魔功》"，系统就误判为《吞天魔功》的同人小说。

### 解决方案

#### 1. 严格的同人标记检测

现在只有当创意中**明确包含同人相关表述**时，才会判定为同人小说：

```python
# 明确的同人标记（必须出现以下模式才判定为同人）
- "同人文"
- "同人小说" 
- "同人作品"
- "基于《作品名》"
- "改编自《作品名》"
- "穿越到《作品名》"
- "重生在《作品名》"
- "《作品名》同人"
- "《作品名》衍生"
- "《作品名》AU"
```

#### 2. 功法/技能名称排除

系统现在会自动识别并排除常见的修仙功法、技能、法宝名称：

```python
# 排除列表（示例）
功法、武技、法术、神通、秘术、绝学、技法、战技
魔功、神功、天功、玄功、宝典、真经、秘籍、心法
剑诀、刀法、拳法、掌法、指法、身法、步法、遁术
吞天魔功、九转金身、龙象般若、北冥神功等
```

#### 3. 上下文检查

即使文本中包含《作品名》，也会检查上下文：

- 必须有明确的同人相关表述（如"基于"、"改编"、"同人"等）
- 如果是已知作品名，但没有同人标记，仍会被排除

### 使用示例

#### ✅ 会被识别为同人小说

```json
{
  "coreSetting": "基于《凡人修仙传》的同人小说，主角穿越到修仙界..."
}
```

#### ❌ 不会被识别为同人小说（原创）

```json
{
  "coreSetting": "主角修练《吞天魔功》，成为修仙界最强..."
}
```

#### ❌ 不会被识别为同人小说（原创）

```json
{
  "coreSetting": "重生成一把魔剑，拥有剑主调教系统...",
  "completeStoryline": {
    "opening": {
      "summary": "主角传授《吞天魔功》给宿主..."
    }
  }
}
```

---

## 问题2：多文件创意存储

### 问题描述

之前所有创意都存储在一个 `novel_ideas.txt` 文件中，随着创意增多，文件会越来越大，不便管理。

### 解决方案

#### 新的文件结构

```
data/creative_ideas/
├── novel_ideas.txt               # 旧版单文件（向后兼容）
├── 001_修仙我是一柄魔剑.json     # 创意1（独立文件）
├── 002_都市重生系统.json         # 创意2（独立文件）
├── 003_科幻星际时代.json         # 创意3（独立文件）
└── ...
```

**说明**：无需索引文件，系统会自动扫描目录中的所有 `.json` 文件（按文件名排序），ID对应文件序号。

#### 单个创意文件格式

```json
{
  "coreSetting": "核心设定内容...",
  "coreSellingPoints": "核心卖点...",
  "completeStoryline": {
    "opening": {...},
    "development": {...},
    "conflict": {...},
    "ending": {...}
  },
  "novelTitle": "小说标题",
  "synopsis": "简介...",
  "totalChapters": 200,
  "lastUpdated": "2025-12-28T16:00:00.000000"
}
```

---

## 迁移指南

### 从单文件迁移到多文件

#### 步骤1：运行迁移工具

```bash
# 在项目根目录执行
python tools/migrate_creative_to_multi_files.py
```

迁移工具会：

1. ✅ 自动备份原文件到 `novel_ideas_backup_YYYYMMDD_HHMMSS.txt`
2. ✅ 为每个创意创建独立的 JSON 文件
3. ✅ 保留原文件作为备份
4. ✅ 无需索引文件，系统自动扫描

#### 步骤2：验证迁移结果

检查 `data/creative_ideas/` 目录：

```bash
# 列出所有创意文件
ls -la data/creative_ideas/*.json
```

#### 步骤3：测试加载

系统会自动检测使用哪种模式：

- 如果存在 `index.json` → 使用多文件模式
- 否则 → 使用单文件模式（向后兼容）

### API 使用说明

#### 获取创意列表

```bash
GET /api/creative-ideas
```

响应示例：

```json
{
  "success": true,
  "count": 3,
  "storage_info": {
    "format": "multi_file",
    "total_count": 3,
    "directory": "data/creative_ideas",
    "files": ["001_修仙我是一柄魔剑.json", "002_都市重生系统.json"]
  },
  "creative_ideas": [...]
}
```

#### 获取单个创意

```bash
GET /api/creative-ideas/1
```

#### 更新创意

```bash
PUT /api/creative-ideas/1
Content-Type: application/json

{
  "coreSetting": "更新后的核心设定",
  "novelTitle": "更新后的标题",
  ...
}
```

#### 删除创意

```bash
DELETE /api/creative-ideas/1
```

---

## 向后兼容性

系统完全向后兼容：

1. **自动检测模式**：系统会自动检测使用单文件还是多文件模式
2. **保留旧文件**：迁移工具不会删除原 `novel_ideas.txt`
3. **API 不变**：前端代码无需修改，API 接口保持一致

---

## 技术实现

### 核心类：CreativeIdeasManager

```python
from src.managers.CreativeIdeasManager import CreativeIdeasManager

# 初始化管理器
manager = CreativeIdeasManager()

# 加载所有创意
data = manager.load_creative_ideas()
print(f"模式: {data['format']}")
print(f"创意数量: {len(data['creativeWorks'])}")

# 获取单个创意
idea = manager.get_creative_idea(1)

# 添加新创意
new_id = manager.add_creative_idea(creative_data)

# 更新创意
manager.update_creative_idea(1, updated_data)

# 删除创意
manager.delete_creative_idea(1)

# 获取存储信息
info = manager.get_storage_info()
```

### 同人检测：ImprovedFanfictionDetector

```python
from src.core.ImprovedFanfictionDetector import ImprovedFanfictionDetector

detector = ImprovedFanfictionDetector()

# 检测是否为同人小说
is_fanfiction, original_work = detector.detect_fanfiction(creative_work)

if is_fanfiction:
    print(f"检测为同人小说，原著: {original_work}")
else:
    print("原创作品")
```

---

## 常见问题

### Q1: 迁移后原文件会删除吗？

**A:** 不会。迁移工具会创建备份文件，原 `novel_ideas.txt` 会被保留。您可以确认无误后再手动删除。

### Q2: 可以混合使用两种模式吗？

**A:** 不建议。系统会优先使用多文件模式（如果 `index.json` 存在）。建议统一使用多文件模式。

### Q3: 如何回退到单文件模式？

**A:** 删除 `index.json` 和所有独立的创意文件，保留原来的 `novel_ideas.txt` 即可。

### Q4: 我的创意包含《作品名》但不是同人，怎么办？

**A:** 新的检测逻辑已经很严格了。只要不包含明确的同人标记（如"基于"、"改编"、"同人"等），就不会被识别为同人小说。

### Q5: 可以手动添加创意文件吗？

**A:** 可以。按照以下步骤：

1. 创建 JSON 文件，格式如上所示
2. 文件命名：`{序号:03d}_{标题}.json`
3. 更新 `index.json`，添加新创意的元信息

---

## 总结

### 改进效果

1. **同人检测更准确**
   - ✅ 不再将功法名误判为原著名
   - ✅ 只有明确的同人标记才会触发检测
   - ✅ 原创创意不再被误判

2. **创意管理更便捷**
   - ✅ 每个创意独立文件，易于管理
   - ✅ 支持增量添加，不需要加载所有创意
   - ✅ 向后兼容，平滑迁移

### 下一步

- [ ] 运行迁移工具
- [ ] 测试同人检测准确性
- [ ] 验证多文件加载功能
- [ ] 根据需要调整检测规则

---

## 更新日志

### 2025-12-28

- ✅ 修复同人小说检测误判问题
- ✅ 实现多文件创意存储
- ✅ 创建 CreativeIdeasManager 管理类
- ✅ 更新 API 支持两种模式
- ✅ 提供迁移工具和文档