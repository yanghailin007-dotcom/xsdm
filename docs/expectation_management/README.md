# 期待感管理系统 - 核心文档

## 📚 文档导航

- **[系统指南](./EXPECTATION_SYSTEM_GUIDE.md)** - 完整的系统使用指南，包含所有期待类型详解
- **[集成示例](./INTEGRATION_EXAMPLE.md)** - 详细的集成步骤和代码示例
- **本文档** - 快速开始和系统概览

## 🎯 系统概述

期待感管理系统是一个贯穿小说生成全流程的框架，用于确保小说始终能维持读者的追读动力。系统基于以下核心原理：

### 核心原理

1. **展示橱窗效应** - 提前展示奖励或能力的强大
2. **压抑与释放** - 制造阻碍，积累势能，最后释放
3. **套娃式期待** - 大期待包着小期待，环环相扣
4. **情绪钩子** - 利用打脸、认同、身份揭秘
5. **实力差距** - 展示主角与目标的差距
6. **伏笔揭秘** - 埋下伏笔，期待真相揭晓

## 🚀 快速开始

### 1. 基础使用

```python
from src.managers.ExpectationManager import ExpectationManager, ExpectationType

# 初始化管理器
manager = ExpectationManager()

# 种植一个期待
exp_id = manager.tag_event_with_expectation(
    event_id="showcase_power_001",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=10,
    description="温天仁展示六极真魔体威力",
    target_chapter=15
)

# 生成前检查
constraints = manager.pre_generation_check(chapter_num=15)

# 生成后验证
result = manager.post_generation_validate(
    chapter_num=15,
    content_analysis={"content": "主角获得六极真魔体，实力大增"},
    released_expectation_ids=[exp_id]
)

# 生成报告
report = manager.generate_expectation_report(1, 20)
```

### 2. 自动集成

```python
from src.managers.ExpectationManager import ExpectationIntegrator

# 初始化集成器
integrator = ExpectationIntegrator(manager)

# 自动分析并标记事件
result = integrator.analyze_and_tag_events(
    major_events=stage_plan["event_system"]["major_events"],
    stage_name="opening_stage"
)

print(f"已为 {result['tagged_count']} 个事件添加期待标签")
```

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    期待感管理系统                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  事件规划阶段                    章节生成阶段                  │
│  ┌──────────────┐              ┌──────────────┐              │
│  │ 分析事件     │  ────────>   │ 生成前检查   │              │
│  │ 添加期待标签 │              │ 获取约束     │              │
│  └──────────────┘              └──────────────┘              │
│         │                            │                       │
│         │                            │                       │
│         ▼                            ▼                       │
│  ┌──────────────┐              ┌──────────────┐              │
│  │ 期待记录     │              │ 生成后验证   │              │
│  │ 映射存储     │ <────────   │ 检查满足度   │              │
│  └──────────────┘              └──────────────┘              │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                          │
│  │ 报告生成     │                                          │
│  │ 改进建议     │                                          │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 期待感类型

| 类型 | 说明 | 最少积累章节 | 典型应用 |
|------|------|-------------|---------|
| 展示橱窗 | 提前展示奖励/能力的强大 | 3章 | 反派展示、传说描述 |
| 压抑释放 | 制造阻碍，积累势能 | 5章 | 击败BOSS、获得宝物 |
| 套娃期待 | 大期待包着小期待 | 2章 | 长期主线分解 |
| 情绪钩子 | 打脸、认同、身份揭秘 | 2章 | 被轻视、隐藏身份 |
| 实力差距 | 展示主角与目标的差距 | 5章 | 遭遇碾压、实力提升 |
| 伏笔揭秘 | 埋下伏笔，期待揭晓 | 7章 | 神秘身世、隐藏秘密 |

## 🔧 关键API

### ExpectationManager

```python
# 种植期待
tag_event_with_expectation(
    event_id: str,
    expectation_type: ExpectationType,
    planting_chapter: int,
    description: str,
    target_chapter: Optional[int] = None,
    related_expectations: Optional[List[str]] = None
) -> str

# 生成前检查
pre_generation_check(chapter_num: int) -> List[ExpectationConstraint]

# 生成后验证
post_generation_validate(
    chapter_num: int,
    content_analysis: Dict,
    released_expectation_ids: Optional[List[str]] = None
) -> Dict

# 生成报告
generate_expectation_report(
    start_chapter: int = 1,
    end_chapter: Optional[int] = None
) -> Dict

# 导出/导入映射
export_expectation_map() -> Dict
import_expectation_map(data: Dict)
```

### ExpectationIntegrator

```python
# 自动分析并标记事件
analyze_and_tag_events(
    major_events: List[Dict],
    stage_name: str
) -> Dict
```

## 📈 质量指标

### 自动验证指标

- **期待种植率**: 每10章至少种植5个期待
- **期待满足率**: 已释放期待中，满足度≥7分的占80%以上
- **期待密度**: 同一时刻活跃的期待数在3-8个之间

### 期待感评分标准

| 分数 | 等级 | 说明 |
|------|------|------|
| 9-10 | 优秀 | 完美满足期待，情感冲击强烈 |
| 7-8 | 良好 | 满足期待，有足够的情感释放 |
| 5-6 | 一般 | 基本满足，但情感冲击不足 |
| 0-4 | 失败 | 未能满足期待，读者失望 |

## 🎓 最佳实践

### 1. 期待感密度控制

```python
# 短期期待：每3-5章释放一次
expectation_manager.tag_event_with_expectation(
    event_id="short_term",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=5,
    target_chapter=10  # 5章后释放
)

# 中期期待：每10-15章释放一次
expectation_manager.tag_event_with_expectation(
    event_id="medium_term",
    expectation_type=ExpectationType.SUPPRESSION_RELEASE,
    planting_chapter=10,
    target_chapter=25  # 15章后释放
)

# 长期期待：贯穿整个阶段
expectation_manager.tag_event_with_expectation(
    event_id="long_term",
    expectation_type=ExpectationType.MYSTERY_FORESHADOW,
    planting_chapter=1,
    target_chapter=50  # 50章后释放
)
```

### 2. 套娃式期待设计

```python
# 大期待：击败温天仁 (第10-25章)
main_exp = expectation_manager.tag_event_with_expectation(
    event_id="defeat_wentianren",
    expectation_type=ExpectationType.SUPPRESSION_RELEASE,
    planting_chapter=10,
    description="击败温天仁，为师门报仇",
    target_chapter=25
)

# 小期待1：获得六极真魔体 (第12-18章)
sub_exp1 = expectation_manager.tag_event_with_expectation(
    event_id="get_body",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=12,
    description="获得六极真魔体，提升实力",
    target_chapter=18,
    related_expectations=[main_exp]
)

# 小期待2：掌握万剑归宗 (第15-20章)
sub_exp2 = expectation_manager.tag_event_with_expectation(
    event_id="learn_skill",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=15,
    description="掌握万剑归宗，增强战斗力",
    target_chapter=20,
    related_expectations=[main_exp, sub_exp1]
)
```

### 3. 接力式期待

```python
# 在满足一个期待的同时，开启下一个期待
# 第15章：满足期待A，同时开启期待B
expectation_manager.post_generation_validate(
    chapter_num=15,
    content_analysis={"content": "主角获得六极真魔体，同时发现新的秘境"},
    released_expectation_ids=["exp_a"]
)

# 立即种植新期待
expectation_manager.tag_event_with_expectation(
    event_id="exp_b",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=15,
    description="探索新发现的秘境",
    target_chapter=22
)
```

## 🧪 测试

运行单元测试：

```bash
python tests/test_expectation_manager.py
```

预期输出：
```
======================================================================
开始运行期待感管理系统测试
======================================================================
...
======================================================================
测试总结
======================================================================
运行测试: 9
成功: 9
失败: 0
错误: 0
======================================================================
```

## 📚 相关文档

- [系统指南](./EXPECTATION_SYSTEM_GUIDE.md) - 详细的期待类型说明和使用方法
- [集成示例](./INTEGRATION_EXAMPLE.md) - 完整的集成步骤和代码示例
- [单元测试](../../tests/test_expectation_manager.py) - 完整的测试用例

## 🎯 核心价值

通过期待感管理系统，你可以：

1. **结构化期待管理** - 将模糊的"追读动力"转化为可操作的系统
2. **全流程集成** - 从规划到生成到验证的完整闭环
3. **自动化验证** - 减少人工检查成本
4. **数据驱动** - 通过报告持续优化期待感质量
5. **避免平淡** - 确保每章都有明确的期待点
6. **防止落空** - 验证期待是否被满足，避免读者失望

## 💡 核心原则

记住这个核心原则：

> **永远不要给读者一个"清静"的时刻**
>
> 每章都要么释放旧期待，要么种植新期待，让读者始终有追读的动力。

---

**开始使用**：请参考 [集成示例](./INTEGRATION_EXAMPLE.md) 了解如何将系统集成到你的项目中。