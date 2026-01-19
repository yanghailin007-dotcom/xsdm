# 扩充版期待感管理系统 - 快速开始指南

## 📖 概述

扩充版期待感管理系统提供了20种网文常见套路的期待感管理，支持事件驱动绑定机制，让每章都能牵动读者的追读动力。

### 核心特性

- ✅ **20种期待感类型**：覆盖主流网文的所有常见套路
- ✅ **事件驱动绑定**：根据事件进度灵活判断释放时机
- ✅ **自动事件匹配**：智能为事件匹配合适的期待类型
- ✅ **密度监控**：确保期待感质量可控可衡量
- ✅ **完整的工作流程**：从种植到验证的全生命周期管理

---

## 🚀 快速开始

### 1. 基本使用

```python
from src.managers.ExpectationManager import (
    ExpectationManager,
    ExpectationType,
    auto_bind_expectation_to_event
)

# 初始化管理器
manager = ExpectationManager()

# 为事件添加期待标签
exp_id = manager.tag_event_with_expectation(
    event_id="alchemy_competition_001",
    expectation_type=ExpectationType.ALCHEMY_CRAFTING,
    planting_chapter=10,
    description="赢得炼丹比赛，证明主角实力",
    target_chapter=15
)

print(f"期待ID: {exp_id}")
# 输出: 期待ID: exp_alchemy_competition_001_10
```

### 2. 自动事件匹配

```python
# 定义事件
event = {
    "id": "boss_fight_001",
    "name": "击败最终BOSS",
    "main_goal": "击败温天仁，为师门报仇"
}

# 自动匹配合适的期待类型
exp_type = auto_bind_expectation_to_event(event)
print(f"匹配类型: {exp_type.value}")
# 输出: 匹配类型: suppression_release
```

### 3. 生成前检查

```python
# 在生成章节前检查期待约束
constraints = manager.pre_generation_check(
    chapter_num=15,
    event_context={"active_events": []}
)

for constraint in constraints:
    print(f"[{constraint.urgency}] {constraint.message}")
    for suggestion in constraint.suggestions:
        print(f"  - {suggestion}")
```

### 4. 生成后验证

```python
# 生成章节后验证期待是否被满足
validation_result = manager.post_generation_validate(
    chapter_num=15,
    content_analysis={"content": chapter_content},
    released_expectation_ids=[exp_id]
)

print(f"验证通过: {validation_result['passed']}")
print(f"满足的期待: {len(validation_result['satisfied_expectations'])}个")
```

---

## 📚 20种期待感类型详解

### 原有6种

| 类型 | 说明 | 最小间隔 | 适用场景 |
|------|------|----------|----------|
| `showcase` | 展示橱窗：提前展示奖励或能力 | 3章 | 获得宝物、学习功法前 |
| `suppression_release` | 压抑释放：制造阻碍后释放 | 5章 | 复仇、击败强敌 |
| `nested_doll` | 套娃期待：大期待包小期待 | 2章 | 多层次情节推进 |
| `emotional_hook` | 情绪钩子：打脸、认同 | 2章 | 误解消除、身份揭秘 |
| `power_gap` | 实力差距：期待变强 | 5章 | 实力碾压后成长 |
| `mystery_foreshadow` | 伏笔揭秘：埋下线索 | 7章 | 长期伏笔、谜题解答 |

### 新增14种

| 类型 | 说明 | 最小间隔 | 适用场景 |
|------|------|----------|----------|
| `pig_eats_tiger` | 扮猪吃虎：隐藏实力后打脸 | 2-3章 | 主角被轻视后展现实力 |
| `show_off_face_slap` | 装逼打脸：展示实力打脸 | 1-2章 | 立下赌约后证明自己 |
| `identity_reveal` | 身份反转：隐藏身份揭晓 | 10-15章 | 长期身份伏笔 |
| `beauty_favor` | 美人恩：女主好感 | 3-5章 | 感情线推进 |
| `fortuitous_encounter` | 机缘巧合：意外获得奇遇 | 2-3章 | 发现宝物、传承 |
| `competition` | 比试切磋：宗门大比 | 5+3章 | 宗门大比、擂台赛 |
| `auction_treasure` | 拍卖会争宝 | 3-5章 | 拍卖会竞拍宝物 |
| `secret_realm_exploration` | 秘境探险 | 8-10章 | 探险遗迹、副本 |
| `alchemy_crafting` | 炼丹炼器 | 2-3章 | 炼制丹药、法器 |
| `formation_breaking` | 阵法破解 | 2-4章 | 破解阵法、解谜 |
| `sect_mission` | 宗门任务 | 3-5章 | 完成任务获得奖励 |
| `cross_world_teleport` | 跨界传送 | 10-15章 | 跨越位面、世界 |
| `crisis_rescue` | 危机救援 | 2-3章 | 拯救重要人物 |
| `master_inheritance` | 师恩传承 | 5-8章 | 获得师父指点 |

---

## 🔧 高级用法

### 1. 事件驱动绑定

```python
# 将期待绑定到事件，根据事件进度自动判断释放时机
exp_id = manager.tag_event_with_expectation(
    event_id="boss_fight_001",
    expectation_type=ExpectationType.SUPPRESSION_RELEASE,
    planting_chapter=10,
    description="击败最终BOSS温天仁",
    target_chapter=20,
    bound_event_id="boss_fight_001",  # 绑定到事件
    trigger_condition="event_reaches_climax",  # 触发条件
    flexible_range={  # 灵活范围
        "min_chapters": 8,
        "max_chapters": 15,
        "optimal_chapters": 10
    }
)
```

### 2. 密度监控

```python
from src.managers.ExpectationManager import ExpectationDensityMonitor

# 创建密度监控器
monitor = ExpectationDensityMonitor(manager)

# 计算期待感密度
density = monitor.calculate_density(start_chapter=1, end_chapter=20)

print(f"总期待数: {density['total_expectations']}")
print(f"每章期待: {density['expectations_per_chapter']:.2f}")
print(f"密度评级: {density['density_rating']}")

# 生成改进建议
recommendations = monitor.generate_recommendations(density)
for rec in recommendations:
    print(f"- {rec}")
```

### 3. 期待感报告

```python
# 生成期待感报告
report = manager.generate_expectation_report(
    start_chapter=1,
    end_chapter=20
)

print(f"总期待数: {report['total_expectations']}")
print(f"已释放: {report['released_expectations']}")
print(f"满足率: {report['satisfaction_rate']}%")
print(f"类型分布: {report['expectation_type_stats']}")
```

---

## 💡 最佳实践

### 1. 期待感密度控制

- **优秀密度**: 每10章5-8个期待
- **密度不足**: 每10章少于5个期待 → 增加期待种植
- **密度过高**: 每10章多于15个期待 → 减少或延长期待

### 2. 类型分布建议

- **核心套路**（必备）:
  - 扮猪吃虎 (`pig_eats_tiger`)
  - 装逼打脸 (`show_off_face_slap`)
  - 展示橱窗 (`showcase`)

- **辅助套路**（推荐）:
  - 美人恩 (`beauty_favor`) - 丰富感情线
  - 比试切磋 (`competition`) - 展现实力
  - 秘境探险 (`secret_realm_exploration`) - 获得宝物

### 3. 接力式期待

在满足一个期待的同时，开启下一个期待：

```python
# 第10章：释放"炼丹比赛"期待，同时开启"拍卖会"期待
manager.tag_event_with_expectation(
    event_id="auction_001",
    expectation_type=ExpectationType.AUCTION_TREASURE,
    planting_chapter=15,  # 在炼丹比赛结束后立即种植
    description="在拍卖会上竞拍稀世灵药",
    related_expectations=["exp_alchemy_competition_10"]  # 关联前一个期待
)
```

### 4. 可视化期待

让读者明确知道"好东西"在哪里：

```python
# 展示橱窗效应
manager.tag_event_with_expectation(
    event_id="treasure_001",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=5,
    description="主角在古籍中看到'九转金丹'的威力，但配方缺失",
    target_chapter=12
)
```

---

## 📋 完整工作流程示例

```python
from src.managers.ExpectationManager import (
    ExpectationManager,
    ExpectationType,
    ExpectationDensityMonitor
)

# 1. 初始化管理器
manager = ExpectationManager()
monitor = ExpectationDensityMonitor(manager)

# 2. 为多个事件添加期待
events = [
    {
        "id": "alchemy_competition",
        "type": ExpectationType.COMPETITION,
        "planting_chapter": 10,
        "target_chapter": 15,
        "description": "赢得宗门炼丹比赛"
    },
    {
        "id": "show_off_power",
        "type": ExpectationType.PIG_EATS_TIGER,
        "planting_chapter": 5,
        "target_chapter": 8,
        "description": "长老嘲讽主角，主角默默承受"
    },
    {
        "id": "auction_treasure",
        "type": ExpectationType.AUCTION_TREASURE,
        "planting_chapter": 16,
        "target_chapter": 20,
        "description": "在拍卖会上竞拍稀世灵药"
    }
]

for event in events:
    manager.tag_event_with_expectation(
        event_id=event["id"],
        expectation_type=event["type"],
        planting_chapter=event["planting_chapter"],
        description=event["description"],
        target_chapter=event["target_chapter"]
    )

# 3. 生成章节前检查
chapter_num = 8
constraints = manager.pre_generation_check(
    chapter_num=chapter_num,
    event_context={}
)

# 4. 根据约束生成章节内容
print(f"第{chapter_num}章期待约束: {len(constraints)}个")

# 5. 生成后验证
validation_result = manager.post_generation_validate(
    chapter_num=chapter_num,
    content_analysis={"content": "主角展露真实实力，全场震惊"},
    released_expectation_ids=["exp_show_off_power_5"]
)

# 6. 定期检查密度
density = monitor.calculate_density(1, 20)
print(f"期待感密度: {density['density_rating']}")
```

---

## 🔍 调试和监控

### 查看所有期待

```python
# 导出期待映射
export_data = manager.export_expectation_map()

# 查看所有期待
for exp_id, exp_data in export_data["expectations"].items():
    print(f"{exp_id}: {exp_data['description']}")
    print(f"  类型: {exp_data['type']}")
    print(f"  状态: {exp_data['status']}")
    print(f"  种植章节: {exp_data['planted_chapter']}")
    print(f"  目标章节: {exp_data['target_chapter']}")
```

### 查看期待问题

```python
# 生成报告
report = manager.generate_expectation_report(1, 50)

# 查看问题
for issue in report["issues"]:
    print(f"[{issue['severity']}] {issue['message']}")

# 查看建议
for rec in report["recommendations"]:
    print(f"- {rec}")
```

---

## ⚠️ 注意事项

1. **不要让读者"清静"**: 每章都要么释放旧期待，要么种植新期待
2. **接力式期待**: 在满足一个期待的同时，开启下一个期待
3. **可视化期待**: 让读者明确知道"好东西"在哪里
4. **自然融入情节**: 期待感的释放必须符合剧情发展
5. **控制密度**: 避免期待感过高导致读者疲劳

---

## 📚 相关文档

- [完整实施方案](./EXPANDED_IMPLEMENTATION_PLAN.md)
- [期待感系统指南](./EXPECTATION_SYSTEM_GUIDE.md)
- [集成示例](./INTEGRATION_EXAMPLE.md)

---

## 🎉 总结

扩充版期待感管理系统通过20种网文常见套路的覆盖，事件驱动的灵活绑定机制，以及密度监控的质量保障，真正实现了让每章都能牵动读者的追读动力！

**核心优势**:
- ✅ 覆盖更全面的网文套路
- ✅ 避免固定章节要求的僵化
- ✅ 与叙事节奏自然融合
- ✅ 自动化程度更高
- ✅ 质量可控可衡量
