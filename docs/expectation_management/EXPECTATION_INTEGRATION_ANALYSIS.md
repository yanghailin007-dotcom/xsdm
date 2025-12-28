# 期待感系统集成分析文档

## 概述

本文档详细分析了期待感管理系统如何检查重复和衔接，以及期待感与事件的融合机制。

---

## 一、期待感重复检查机制

### 1.1 唯一ID生成

**位置**: [`ExpectationManager.py:294`](src/managers/ExpectationManager.py:294)

```python
expectation_id = f"exp_{event_id}_{planting_chapter}"
```

**机制**：
- 每个期待通过 `事件ID_章节号` 生成唯一标识
- 同一事件在同一章多次标记会被覆盖，避免重复

### 1.2 事件映射表

**位置**: [`ExpectationManager.py:312`](src/managers/ExpectationManager.py:312)

```python
self.event_expectation_map[event_id] = expectation_id
```

**机制**：
- 一个事件只能对应一个期待ID
- 防止为同一事件创建重复的期待

---

## 二、期待感衔接检查机制

### 2.1 生成前检查 (pre_generation_check)

**位置**: [`ExpectationManager.py:330-397`](src/managers/ExpectationManager.py:330)

#### 检查1: 待释放期待

```python
pending_expectations = self._get_pending_expectations_for_chapter(chapter_num)
for exp_id in pending_expectations:
    constraints.append(ExpectationConstraint(
        type="must_release",
        urgency="critical",
        message=f"本章必须释放期待：{exp_record.planting_description}",
        suggestions=[...],
        expectation_id=exp_id
    ))
```

**检查逻辑**：
- 找出所有 `target_chapter <= 当前章节` 的未释放期待
- **衔接保障**：确保种植的期待不会被遗忘

#### 检查2: 期待空缺

```python
if len(pending_expectations) == 0:
    constraints.append(ExpectationConstraint(
        type="must_plant",
        urgency="high",
        message=f"本章没有待释放的期待，建议种植新的期待",
        suggestions=[
            "展示橱窗：展示强大的能力或宝物",
            "情绪钩子：制造误解或轻视",
            "伏笔埋设：暗示重大秘密",
            "套娃式：在满足旧期待的同时开启新期待"
        ]
    ))
```

**检查逻辑**：
- 如果本章没有待释放期待，提示种植新期待
- **衔接保障**：避免章节"平淡无奇"，保持追读动力

#### 检查3: 超时期待

```python
if (exp_record.status == ExpectationStatus.PLANTED and 
    exp_record.target_chapter and 
    chapter_num >= exp_record.target_chapter + 2):
    constraints.append(ExpectationConstraint(
        type="must_release",
        urgency="critical",
        message=f"期待已超时{chapter_num - exp_record.target_chapter}章！",
        suggestions=["立即在本章释放该期待", "或者提供明确的延期理由"]
    ))
```

**检查逻辑**：
- 超过目标章节2章还未释放的期待
- **衔接保障**：防止期待"烂尾"

### 2.2 生成后验证 (post_generation_validate)

**位置**: [`ExpectationManager.py:481-529`](src/managers/ExpectationManager.py:481)

```python
def _validate_expectation_satisfaction(self, exp_record, content_analysis):
    rule = EXPECTATION_RULES.get(exp_record.expectation_type)
    score = 0.0
    
    # 1. 检查满足指标（5分）
    for indicator in rule.satisfaction_indicators:
        if indicator.lower() in content.lower():
            score += 5.0
    
    # 2. 检查释放要求（3分，需满足60%）
    release_requirements_met = 0
    for requirement in rule.release_requirements:
        if requirement.lower() in content.lower():
            release_requirements_met += 1
    
    if release_requirements_met >= len(rule.release_requirements) * 0.6:
        score += 3.0
    
    # 3. 基础分（2分）
    score += 2.0
    
    return min(10.0, score), notes
```

**验证标准**：
- **满足指标检查**：内容是否包含期待类型的满足关键词（如"实力提升"、"震惊"等）
- **释放要求检查**：是否满足至少60%的释放要求
- **评分标准**：≥7.0分才算满足，否则标记为违规

---

## 三、期待感与事件的融合机制

### 3.1 融合时机：事件规划完成后自动添加

**关键点**：期待感不是在拆分中级事件时拆解，而是在事件规划完成后自动分析并添加。

#### 自动分析流程

**位置**: [`ExpectationIntegrator.analyze_and_tag_events`](src/managers/ExpectationManager.py:675)

```python
# 在 StagePlanManager 生成阶段计划后
expectation_result = self.expectation_integrator.analyze_and_tag_events(
    major_events=final_writing_plan["event_system"]["major_events"],
    stage_name=stage_name
)
```

#### 分析策略：决策树

**位置**: [`ExpectationIntegrator._analyze_and_tag_major_event`](src/managers/ExpectationManager.py:710)

```python
# 根据事件特征自动选择期待类型
if "击败" in main_goal or "战胜" in main_goal or "复仇" in main_goal:
    return ExpectationType.SUPPRESSION_RELEASE  # 压抑释放
elif "获得" in main_goal or "得到" in main_goal or "炼成" in main_goal:
    return ExpectationType.SHOWCASE  # 展示橱窗
elif "误解" in emotional_focus or "轻视" in emotional_focus:
    return ExpectationType.EMOTIONAL_HOOK  # 情绪钩子
elif "展示" in main_goal or "学习" in main_goal:
    return ExpectationType.POWER_GAP  # 实力差距
elif "揭秘" in main_goal or "真相" in main_goal:
    return ExpectationType.MYSTERY_FORESHADOW  # 伏笔揭秘
else:
    return ExpectationType.NESTED_DOLL  # 套娃式期待（默认）
```

#### 为重大和中型事件分别添加期待

**重大事件示例**：
```python
# 示例：重大事件"击败温天仁"（第10-25章）
exp_id = manager.tag_event_with_expectation(
    event_id="击败温天仁",
    expectation_type=ExpectationType.SUPPRESSION_RELEASE,
    planting_chapter=10,
    description="主角击败温天仁的期待",
    target_chapter=25
)
```

**中型事件示例**：
```python
# 示例：中型事件"宗门长老轻视主角"（第8-10章）
exp_id = manager.tag_event_with_expectation(
    event_id="宗门长老轻视主角",
    expectation_type=ExpectationType.EMOTIONAL_HOOK,
    planting_chapter=8,
    description="制造打脸期待",
    target_chapter=12
)
```

### 3.2 生成章节内容时：构建期待感提示词

#### 生成前检查期待约束

**建议集成位置**: [`ChapterGenerator.generate_chapter_content_for_novel`](src/core/content_generation/chapter_generator.py:22)

```python
# 1. 生成前检查期待约束
expectation_constraints = expectation_manager.pre_generation_check(
    chapter_num=chapter_number
)

# 2. 将期待约束添加到章节参数
chapter_params["expectation_constraints"] = expectation_constraints
```

#### 构建期待感指导文本

```python
def _build_expectation_guidance(self, constraints: List) -> str:
    """构建期待感指导文本"""
    if not constraints:
        return ""
    
    guidance_parts = ["## 🎯 本章期待感要求\n"]
    
    for constraint in constraints:
        if constraint.type == "must_release":
            guidance_parts.append(f"""
### 【必须释放】{constraint.message}

**实现建议**:
{chr(10).join([f"  - {s}" for s in constraint.suggestions])}

**关键要素**:
- 展示期待被满足的具体过程
- 描写角色/读者的情感反应
- 给足篇幅和细节,不要草草了事
""")
        
        elif constraint.type == "must_plant":
            guidance_parts.append(f"""
### 【建议种植新期待】

{constraint.message}

**推荐方案**:
{chr(10).join([f"  - {s}" for s in constraint.suggestions])}

**实现要点**:
- 选择1-2种期待类型
- 确保期待足够具体和明确
- 为后续释放埋下合理的基础
""")
    
    return "\n".join(guidance_parts)
```

#### 注入章节生成Prompt

```python
# 在章节生成提示词中添加
expectation_guidance = self._build_expectation_guidance(
    chapter_params.get("expectation_constraints", [])
)

chapter_generation_prompt = f"""
## 章节创作指令 ##
为《{novel_title}》创作第{chapter_number}章。

{expectation_guidance}  # 🎯 期待感要求

{intensity_guidance}    # 🌊 情绪强度指南
{scenes_input_str}       # 📋 场景结构

## 2. 背景与衔接
...
"""
```

### 3.3 生成章节内容后：验证期待满足度

```python
# 3. 生成后验证期待满足度
validation_result = expectation_manager.post_generation_validate(
    chapter_num=chapter_number,
    content_analysis={"content": chapter_data.get("content", "")},
    released_expectation_ids=released_expectations
)

# 4. 处理验证结果
if not validation_result["passed"]:
    self.logger.warning(f"⚠️ 第{chapter_number}章期待感验证未完全通过")
```

---

## 四、套娃式期待的衔接检查

### 关联关系维护

**位置**: [`ExpectationManager.py:308`](src/managers/ExpectationManager.py:308)

```python
record = ExpectationRecord(
    related_expectations=[main_exp_id, sub_exp1_id]
)
```

### 测试案例

**位置**: [`test_expectation_manager.py:42-79`](tests/test_expectation_manager.py:42)

```python
# 大期待：击败温天仁 (第10-25章)
main_exp = manager.tag_event_with_expectation(
    event_id="main_arc_001",
    expectation_type=ExpectationType.SUPPRESSION_RELEASE,
    planting_chapter=10,
    description="击败温天仁,为师门报仇",
    target_chapter=25
)

# 小期待1：获得六极真魔体 (第12-18章)
sub_exp1 = manager.tag_event_with_expectation(
    event_id="sub_arc_001",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=12,
    description="获得六极真魔体",
    target_chapter=18,
    related_expectations=[main_exp]  # 关联到大期待
)

# 小期待2：掌握万剑归宗 (第15-20章)
sub_exp2 = manager.tag_event_with_expectation(
    event_id="sub_arc_002",
    expectation_type=ExpectationType.SHOWCASE,
    planting_chapter=15,
    description="掌握万剑归宗",
    target_chapter=20,
    related_expectations=[main_exp, sub_exp1]  # 关联到前序期待
)
```

**衔接逻辑**：
- 小期待必须在大期待释放之前完成
- 形成环环相扣的期待链
- 通过 `related_expectations` 字段追踪关系

---

## 五、关键检查点总结

| 检查类型 | 检查时机 | 检查内容 | 失败处理 |
|---------|---------|---------|---------|
| **重复检查** | 种植时 | 事件ID + 章节号唯一性 | 覆盖旧期待 |
| **衔接检查** | 生成前 | 是否有待释放期待 | 提示must_release |
| **空缺检查** | 生成前 | 是否没有待释放期待 | 提示must_plant |
| **超时检查** | 生成前 | 是否超过目标章节2章 | 紧急释放提示 |
| **满足度检查** | 生成后 | 评分≥7.0，满足60%要求 | 标记为FAILED |

---

## 六、完整融合流程图

```
┌─────────────────────────────────────────────────────────────┐
│              期待感与事件的完整融合流程                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  阶段1: 事件规划阶段                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. 生成重大事件骨架                                      ││
│  │    └─> major_event_skeletons                            ││
│  │                                                         ││
│  │ 2. 解析重大事件为中型事件                                ││
│  │    └─> composition = {"起": [中型事件1, ...], ...}      ││
│  │                                                         ││
│  │ 3. 【自动添加期待标签】                                  ││
│  │    └─> ExpectationIntegrator.analyze_and_tag_events()  ││
│  │        ├─ 分析重大事件 → 添加主期待                      ││
│  │        └─ 分析中型事件 → 添加子期待                      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  阶段2: 章节生成阶段                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. 生成前检查                                           ││
│  │    └─> pre_generation_check(chapter_num)                ││
│  │        ├─ 查找待释放期待 (must_release)                  ││
│  │        ├─ 检查期待空缺 (must_plant)                     ││
│  │        └─ 检查超时期待                                   ││
│  │                                                         ││
│  │ 2. 构建期待感提示词                                      ││
│  │    └─> _build_expectation_guidance(constraints)          ││
│  │                                                         ││
│  │ 3. 注入章节生成 Prompt                                   ││
│  │    └─> chapter_generation_prompt += expectation_guidance ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  阶段3: 生成后验证阶段                                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. 提取释放的期待ID                                     ││
│  │    └─> _extract_released_expectations()                 ││
│  │                                                         ││
│  │ 2. 验证期待满足度                                       ││
│  │    └─> post_generation_validate()                       ││
│  │        ├─ 检查满足指标 (5分)                            ││
│  │        ├─ 检查释放要求 (3分，需满足60%)                 ││
│  │        └─ 基础分 (2分)                                  ││
│  │                                                         ││
│  │ 3. 更新期待状态                                         ││
│  │    ├─ 评分 ≥ 7.0 → RELEASED                            ││
│  │    └─ 评分 < 7.0 → FAILED                              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、关键特点

1. **自动化分析**：期待感标签不是手动添加，而是根据事件特征自动分析生成
2. **非拆解模式**：期待感不是在事件分解时拆解，而是在完整的事件体系上叠加
3. **双阶段约束**：
   - **规划阶段**：通过 `ExpectationIntegrator` 自动添加期待标签
   - **生成阶段**：通过 `pre_generation_check` 获取约束并构建提示词
4. **事后验证**：通过 `post_generation_validate` 验证期待是否被满足

---

## 八、集成建议

### 在 StagePlanManager 中集成

```python
def generate_stage_writing_plan(self, stage_name: str, ...):
    # ... 现有的 fase 1-4 代码 ...
    
    # fase 4.5: 添加期待感标签 (新增)
    self.logger.info("   fase 4.5: 添加期待感标签...")
    
    # 分析并标记事件
    expectation_result = self.expectation_integrator.analyze_and_tag_events(
        major_events=final_writing_plan["event_system"]["major_events"],
        stage_name=stage_name
    )
    
    # 将期待感信息添加到计划中
    final_writing_plan["stage_writing_plan"]["expectation_map"] = \
        self.expectation_manager.export_expectation_map()
    
    self.logger.info(f"  ✅ 已为 {expectation_result['tagged_count']} 个事件添加期待标签")
    
    # ... 继续现有的 fase 5-6 代码 ...
    
    return final_writing_plan
```

### 在 ChapterGenerator 中集成

```python
def generate_chapter_content_for_novel(self, chapter_number: int, ...):
    # ========== 新增：期待感管理开始 ==========
    # 1. 生成前检查期待约束
    expectation_constraints = expectation_manager.pre_generation_check(
        chapter_num=chapter_number
    )
    
    # 2. 将期待约束添加到章节参数
    chapter_params["expectation_constraints"] = expectation_constraints
    
    # ... 现有的章节内容生成代码 ...
    
    # ========== 新增：期待感验证开始 ==========
    # 3. 生成后验证期待满足度
    validation_result = expectation_manager.post_generation_validate(
        chapter_num=chapter_number,
        content_analysis=content_analysis,
        released_expectation_ids=released_expectations
    )
    
    # 4. 将验证结果添加到章节数据
    chapter_data["expectation_validation"] = validation_result
    # ========== 新增：期待感验证结束 ==========
    
    return chapter_data
```

---

## 结论

期待感系统通过**前后双重检查**机制，确保期待的种植和释放能够顺畅衔接，避免重复和遗漏。这种设计确保了期待感与事件的自然融合，通过自动化分析、生成时约束和事后验证三个阶段，构建了完整的期待感管理闭环。