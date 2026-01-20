# WorldStateManager 角色相关数据处理方案

## 📊 问题概述

在当前的WorldStateManager架构中，角色相关的数据分散存储在多个位置，导致：
1. **查询复杂**：需要从多个文件聚合数据
2. **同步困难**：更新时需要同时修改多处
3. **一致性风险**：可能出现数据不一致

---

## 🔍 当前数据存储结构

### 1. character_development.json（角色基础信息）

```json
{
  "林凡": {
    "name": "林凡",
    "status": "active",
    "role_type": "主角",
    "importance": "major",
    "first_appearance_chapter": 1,
    "last_updated_chapter": 10,
    "total_appearances": 10,

    // 角色属性（包含部分状态数据）
    "attributes": {
      "status": "active",
      "location": "青云宗",
      "cultivation_level": "筑基期",
      "cultivation_system": "修仙",
      "money": 100,                    // ← 金钱存储在这里
      "money_sources": [],
      "recent_transactions": []
    },

    // 角色发展相关
    "personality_traits": {...},
    "background_story": {...},
    "relationship_network": {...},
    "development_milestones": [...]
  }
}
```

**特点**：
- ✅ 存储角色的**身份信息**和**发展轨迹**
- ✅ 包含**基础状态**（修为、位置、金钱）
- ⚠️ 金钱信息可能与ledger不同步

### 2. world_state.json（物品/技能/地点）

```json
{
  "cultivation_skills": {
    "天罡剑诀": {
      "owner": "林凡",          // ← 通过owner字段关联角色
      "level": "圆满",
      "type": "功法",
      "quality": "地阶",
      "description": "..."
    }
  },

  "cultivation_items": {
    "青云剑": {
      "owner": "林凡",          // ← 通过owner字段关联角色
      "type": "法宝",
      "quality": "上品",
      "status": "完好"
    }
  },

  "relationships": {...},
  "locations": {...},
  "economy": [...]               // ← 经济事件记录
}
```

**特点**：
- ✅ 存储**游戏物品**（技能、法宝、丹药等）
- ✅ 通过`owner`字段关联角色
- ⚠️ 查询角色物品需要遍历整个数据集

### 3. {novel}_money_ledger.json（金钱账本）

```json
[
  {
    "tx_id": "uuid",
    "character": "林凡",
    "amount": -50,
    "counterparty": "王二牛",
    "reason": "购买丹药",
    "chapter": 10
  }
]
```

**特点**：
- ✅ 记录所有金钱交易历史
- ✅ 可以追溯任何时间的金钱变化
- ⚠️ 当前余额需要通过计算得到

---

## 🎯 解决方案

### 方案A：保持现状 + 优化查询接口（推荐）

**核心思想**：
- 不改变底层存储结构
- 提供统一的查询接口，内部处理多源数据聚合
- 添加数据一致性验证机制

**优点**：
- ✅ 改动最小，风险低
- ✅ 向后兼容
- ✅ 可以逐步优化

**实施步骤**：

#### 1. 创建角色状态聚合查询接口

在WorldStateManager中添加新方法：

```python
def get_character_complete_state(self, novel_title: str, character_name: str) -> Dict:
    """
    获取角色的完整状态信息（聚合多源数据）

    Returns:
        {
            "基础信息": {...},
            "状态属性": {
                "修为": "筑基期",
                "位置": "青云宗",
                "金钱": 100,  # 从ledger计算得出
            },
            "技能列表": [...],      # 从world_state聚合
            "物品列表": [...],      # 从world_state聚合
            "最近交易": [...]       # 从ledger获取
        }
    """
    # 1. 加载角色基础信息
    char_data = self._load_character_development_data(novel_title).get(character_name, {})

    # 2. 加载世界状态
    world_state = self.load_previous_assessments(novel_title)

    # 3. 聚合技能
    skills = self._aggregate_character_skills(world_state, character_name)

    # 4. 聚合物品
    items = self._aggregate_character_items(world_state, character_name)

    # 5. 计算当前金钱
    money = self._compute_money_balance(novel_title, character_name)

    # 6. 获取最近交易
    recent_txs = self._get_recent_transactions(novel_title, character_name, limit=10)

    return {
        "基础信息": {
            "姓名": character_name,
            "角色类型": char_data.get("role_type"),
            "重要性": char_data.get("importance"),
            "状态": char_data.get("status"),
            "首次出场": char_data.get("first_appearance_chapter"),
            "总出场": char_data.get("total_appearances")
        },
        "状态属性": {
            "修为": char_data.get("attributes", {}).get("cultivation_level"),
            "位置": char_data.get("attributes", {}).get("location"),
            "金钱": money,
            "门派": char_data.get("attributes", {}).get("faction")
        },
        "技能列表": skills,
        "物品列表": items,
        "最近交易": recent_txs
    }

def _aggregate_character_skills(self, world_state: Dict, character_name: str) -> List[Dict]:
    """聚合角色的所有技能"""
    skills = []
    cultivation_skills = world_state.get("cultivation_skills", {})
    for skill_name, skill_data in cultivation_skills.items():
        if skill_data.get("owner") == character_name:
            skills.append({
                "名称": skill_name,
                "类型": skill_data.get("type"),
                "等级": skill_data.get("level"),
                "品质": skill_data.get("quality"),
                "描述": skill_data.get("description")
            })
    return skills

def _aggregate_character_items(self, world_state: Dict, character_name: str) -> List[Dict]:
    """聚合角色的所有物品"""
    items = []
    cultivation_items = world_state.get("cultivation_items", {})
    for item_name, item_data in cultivation_items.items():
        if item_data.get("owner") == character_name:
            items.append({
                "名称": item_name,
                "类型": item_data.get("type"),
                "品质": item_data.get("quality"),
                "状态": item_data.get("status")
            })
    return items

def _get_recent_transactions(self, novel_title: str, character_name: str, limit: int = 10) -> List[Dict]:
    """获取角色最近的交易记录"""
    ledger_file = self._money_ledger_file(novel_title)
    if not os.path.exists(ledger_file):
        return []

    with open(ledger_file, 'r', encoding='utf-8') as f:
        ledger = json.load(f)

    # 筛选该角色的交易并按时间排序
    char_txs = [tx for tx in ledger if tx.get("character") == character_name]
    char_txs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return char_txs[:limit]
```

#### 2. 添加数据一致性验证

```python
def validate_character_data_consistency(self, novel_title: str, character_name: str) -> Dict:
    """
    验证角色数据的一致性

    检查项：
    1. attributes.money vs ledger计算值
    2. attributes.cultivation_level vs 技能等级
    3. 物品owner是否都指向有效角色
    """
    issues = []

    # 1. 加载数据
    char_data = self._load_character_development_data(novel_title).get(character_name, {})
    world_state = self.load_previous_assessments(novel_title)

    # 2. 验证金钱一致性
    recorded_money = char_data.get("attributes", {}).get("money", 0)
    calculated_money = self._compute_money_balance(novel_title, character_name)

    if abs(recorded_money - calculated_money) > 0.01:
        issues.append({
            "type": "MONEY_MISMATCH",
            "severity": "高",
            "description": f"角色{character_name}的attributes.money({recorded_money})与ledger计算值({calculated_money})不一致",
            "suggestion": "以ledger计算值为准，更新attributes.money"
        })

    # 3. 验证物品owner
    cultivation_items = world_state.get("cultivation_items", {})
    for item_name, item_data in cultivation_items.items():
        if item_data.get("owner") == character_name:
            # 检查角色是否存在
            if character_name not in char_data:
                issues.append({
                    "type": "ORPHANED_ITEM",
                    "severity": "中",
                    "description": f"物品{item_name}的owner指向不存在的角色{character_name}",
                    "suggestion": "更新物品的owner或删除该物品"
                })

    return {
        "character": character_name,
        "is_consistent": len(issues) == 0,
        "issues": issues
    }
```

#### 3. 统一的角色状态更新接口

```python
def update_character_state(self, novel_title: str, character_name: str,
                          state_updates: Dict, chapter_number: int) -> bool:
    """
    统一的角色状态更新接口

    自动处理多源数据的同步更新

    Args:
        state_updates: {
            "attributes": {
                "cultivation_level": "金丹期",
                "location": "天宗",
                "money": 150
            },
            "skills": {
                "add": ["天罡剑诀"],
                "remove": [],
                "update": {
                    "天罡剑诀": {"level": "大成"}
                }
            },
            "items": {
                "add": [
                    {"name": "青云剑", "type": "法宝", "quality": "上品"}
                ],
                "remove": []
            }
        }
    """
    # 1. 更新角色基础信息
    if "attributes" in state_updates:
        self.manage_character_development_table(
            novel_title,
            {
                "name": character_name,
                "attributes": state_updates["attributes"]
            },
            chapter_number,
            "update"
        )

    # 2. 更新技能
    if "skills" in state_updates:
        self._update_character_skills(novel_title, character_name,
                                     state_updates["skills"], chapter_number)

    # 3. 更新物品
    if "items" in state_updates:
        self._update_character_items(novel_title, character_name,
                                    state_updates["items"], chapter_number)

    return True

def _update_character_skills(self, novel_title: str, character_name: str,
                            skill_updates: Dict, chapter_number: int):
    """更新角色的技能"""
    world_state = self.load_previous_assessments(novel_title)
    cultivation_skills = world_state.setdefault("cultivation_skills", {})

    # 添加新技能
    for skill_name in skill_updates.get("add", []):
        cultivation_skills[skill_name] = {
            "owner": character_name,
            "level": "初学",
            "type": "功法",
            "first_appearance": chapter_number,
            "last_updated": chapter_number
        }

    # 更新技能
    for skill_name, updates in skill_updates.get("update", {}).items():
        if skill_name in cultivation_skills:
            cultivation_skills[skill_name].update(updates)
            cultivation_skills[skill_name]["last_updated"] = chapter_number

    # 删除技能
    for skill_name in skill_updates.get("remove", []):
        if skill_name in cultivation_skills:
            del cultivation_skills[skill_name]

    # 保存
    state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(world_state, f, ensure_ascii=False, indent=2)
```

---

### 方案B：完全重构为统一存储（长期方案）

**核心思想**：
- 创建独立的`CharacterManager`类
- 将所有角色相关数据迁移到character_development.json
- world_state只存储不归属角色的全局数据

**优点**：
- ✅ 数据高度内聚
- ✅ 查询性能更好
- ✅ 一致性更容易保证

**缺点**：
- ❌ 需要大规模重构
- ❌ 迁移风险高
- ❌ 可能影响现有功能

**建议**：暂时不采用，等待方案A实施稳定后再考虑

---

## ✅ 推荐实施计划

### 第一阶段：优化查询接口（1-2天）

1. ✅ 添加`get_character_complete_state()`聚合查询方法
2. ✅ 添加`validate_character_data_consistency()`一致性验证
3. ✅ 更新ContentGenerator使用新接口

### 第二阶段：统一更新接口（2-3天）

4. ✅ 添加`update_character_state()`统一更新接口
5. ✅ 实现技能/物品的自动同步更新
6. ✅ 添加单元测试

### 第三阶段：监控和优化（持续）

7. ✅ 添加数据一致性检查日志
8. ✅ 优化查询性能（添加缓存）
9. ✅ 编写使用文档

---

## 📝 使用示例

### 查询角色完整状态

```python
world_state_manager = WorldStateManager(novel_title="我的修仙小说")

# 获取角色完整状态
linfan_state = world_state_manager.get_character_complete_state(
    novel_title="我的修仙小说",
    character_name="林凡"
)

print(linfan_state)
# {
#     "基础信息": {...},
#     "状态属性": {
#         "修为": "筑基期",
#         "位置": "青云宗",
#         "金钱": 100
#     },
#     "技能列表": [
#         {"名称": "天罡剑诀", "等级": "圆满", "品质": "地阶"}
#     ],
#     "物品列表": [
#         {"名称": "青云剑", "类型": "法宝", "品质": "上品"}
#     ]
# }
```

### 更新角色状态

```python
# 统一更新接口
world_state_manager.update_character_state(
    novel_title="我的修仙小说",
    character_name="林凡",
    chapter_number=10,
    state_updates={
        "attributes": {
            "cultivation_level": "金丹期",
            "money": 150
        },
        "skills": {
            "add": ["金丹功法"],
            "update": {
                "天罡剑诀": {"level": "大成"}
            }
        },
        "items": {
            "add": [
                {"name": "飞剑", "type": "法宝", "quality": "极品"}
            ]
        }
    }
)
```

---

## 🔧 迁移指南

对于现有代码，建议按以下方式迁移：

### 旧代码（多源查询）

```python
# 旧方式：需要从多个地方获取数据
char_data = load_character_development(novel_title)
money = char_data["林凡"]["attributes"]["money"]

world_state = load_world_state(novel_title)
skills = [s for s in world_state["cultivation_skills"].values() if s["owner"] == "林凡"]
items = [i for i in world_state["cultivation_items"].values() if i["owner"] == "林凡"]
```

### 新代码（统一接口）

```python
# 新方式：使用统一接口
complete_state = world_state_manager.get_character_complete_state(
    novel_title="我的修仙小说",
    character_name="林凡"
)

money = complete_state["状态属性"]["金钱"]
skills = complete_state["技能列表"]
items = complete_state["物品列表"]
```

---

## 📊 总结

| 方案 | 改动量 | 风险 | 优点 | 缺点 | 推荐度 |
|------|--------|------|------|------|--------|
| **方案A** | 小 | 低 | 改动小、向后兼容、可逐步优化 | 查询仍需多源聚合 | ⭐⭐⭐⭐⭐ |
| **方案B** | 大 | 高 | 数据内聚、性能好 | 重构风险高、迁移成本大 | ⭐⭐ |

**建议**：采用**方案A**，保持当前存储结构，通过优化查询接口和添加一致性验证来解决实际问题。
