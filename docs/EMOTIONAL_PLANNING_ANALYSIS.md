# 情绪规划流程分析与优化方案

## 一、当前流程现状

### 1. 现有的事件层级结构
```
阶段 (Stage: development_stage)
  └─ 重大事件
      └─ 中型事件
          └─ 场景事件
```

### 2. 现有的情绪规划层级
```
阶段情绪计划
  └─ 3-5个情绪分段
      └─ 章节范围
      └─ 情绪关键词
      └─ 核心情绪任务
```

### 3. 当前问题诊断

**问题1：情绪规划层级不匹配**
- 事件已经细化到**中型事件层级**
- 情绪规划只停留在**阶段分段层级**
- 导致：无法为具体的中型事件提供精确的情绪指导

**问题2：情绪与事件脱节**
- 中型事件有自己的 `emotional_focus`、`emotional_intensity`、`key_emotional_beats`
- 但这些情绪目标没有与阶段情绪计划建立明确的层级关系
- 导致：难以保证整个阶段的情绪发展连贯性

**问题3：重复的API调用**
- EmotionalPlanManager 为每个阶段生成情绪分段
- EventDecomposer 在分解重大事件时也会考虑情绪
- 两次调用可能产生不一致的情绪目标

## 二、优化方案设计

### 方案A：双层情绪规划（推荐）

#### 设计思路
保持阶段级情绪规划，但增加事件级情绪细化

```
阶段情绪计划
  ├─ 整体情绪弧线
  └─ 3-5个情绪分段
      └─ 情绪分段 → 映射到 → 重大事件
          └─ 重大事件情绪细化 → 映射到 → 中型事件
```

#### 实现步骤

**Step 1: 保留阶段情绪计划**
- EmotionalPlanManager 继续生成阶段级的情绪分段
- 目的：为整个阶段提供情绪发展的大方向

**Step 2: 为重大事件生成情绪细分**
- 在 EventDecomposer.decompose_major_event() 中
- 参考阶段情绪计划，为重大事件的每个阶段（起承转合）设计情绪目标
- 输出：每个中型事件的精确情绪目标

**Step 3: 建立映射关系**
```python
major_event = {
    "name": "重大事件名称",
    "emotional_mapping": {
        "起": {
            "stage_emotional_segment": "压抑与铺垫期",  # 映射到阶段情绪分段
            "medium_event_emotion": "屈辱/愤怒"          # 中型事件情绪
        },
        "承": {...},
        "转": {...},
        "合": {...}
    }
}
```

#### 优点
- 保留整体情绪发展框架
- 为具体事件提供精确情绪指导
- 避免重复API调用

---

### 方案B：三层情绪规划（完整版）

#### 设计思路
为每个层级都生成情绪规划

```
阶段情绪计划 → 重大事件情绪计划 → 中型事件情绪计划
```

#### 实现步骤

**Step 1: 阶段情绪计划（已有）**
- EmotionalPlanManager 生成
- 3-5个情绪分段

**Step 2: 重大事件情绪细分（新增）**
- 为每个重大事件生成情绪弧线
- 重大事件的起承转合对应不同的情绪发展阶段

**Step 3: 中型事件情绪细化（已有但需增强）**
- 每个中型事件已有 `emotional_focus`、`emotional_intensity`
- 增强与上级情绪目标的关联性

#### 优点
- 情绪规划最完整、最细致
- 层级关系清晰

#### 缺点
- API调用次数增加
- 可能过度设计

---

### 方案C：轻量级优化（快速方案）

#### 设计思路
不增加新的情绪规划层级，只是增强现有数据的关联性

#### 实现步骤

**Step 1: 修改 EventDecomposer**
- 在分解重大事件时，**必须传入** stage_emotional_plan
- 在 prompt 中明确要求参考阶段情绪计划

**Step 2: 增强中型事件的情绪字段**
```python
medium_event = {
    "name": "中型事件名称",
    "main_goal": "...",
    # 增加以下字段
    "parent_stage_emotional_segment": "压抑与铺垫期",  # 所属的阶段情绪分段
    "emotion_contribution_to_stage": "通过主角被欺凌，累积读者压抑情绪",  # 对阶段情绪目标的贡献
    # 保留现有字段
    "emotional_focus": "...",
    "emotional_intensity": "...",
    "key_emotional_beats": [...]
}
```

#### 优点
- 改动最小
- 不增加API调用
- 快速实现

#### 缺点
- 情绪规划仍然不够细致

---

## 三、推荐实施方案

### 短期方案（立即实施）：方案C - 轻量级优化

**理由：**
1. 改动小，风险低
2. 不增加API成本
3. 快速解决当前问题

**具体实施：**
1. 修改 `EventDecomposer._build_decomposition_prompt()`
2. 增加 stage_emotional_plan 参数
3. 在 prompt 中强调参考阶段情绪计划
4. 要求中型事件明确映射到阶段情绪分段

### 中期方案（未来优化）：方案A - 双层情绪规划

**理由：**
1. 平衡了完整性和成本
2. 为重大事件提供情绪指导
3. 保留阶段整体情绪框架

**具体实施：**
1. 为重大事件生成情绪细分（可以在分解时一起完成）
2. 建立情绪映射关系
3. 在验证阶段检查情绪连贯性

---

## 四、实施检查清单

### 轻量级优化实施清单

- [ ] 1. 修改 EventDecomposer.decompose_major_event() 方法签名
  - 增加 `stage_emotional_plan` 参数
  - 增加 `overall_emotional_blueprint` 参数
  
- [ ] 2. 更新 _build_decomposition_prompt()
  - 在 prompt 中增加阶段情绪计划的引用
  - 要求每个中型事件必须映射到某个阶段情绪分段
  
- [ ] 3. 更新中型事件的输出结构
  - 增加 `parent_stage_emotional_segment` 字段
  - 增加 `emotion_contribution_to_stage` 字段
  
- [ ] 4. 更新 StagePlanManager._generate_major_event_skeletons_with_retry()
  - 在调用 EventDecomposer 时传入 stage_emotional_plan
  
- [ ] 5. 测试验证
  - 检查生成的中型事件是否正确映射到阶段情绪分段
  - 验证情绪发展是否连贯

---

## 五、代码修改示例

### 修改点1: EventDecomposer.decompose_major_event()

```python
def decompose_major_event(self, major_event_skeleton: Dict, stage_name: str, 
                        stage_range: str, novel_title: str, novel_synopsis: str, 
                        creative_seed: Dict, overall_stage_plan: Dict,
                        global_novel_data: Dict,
                        stage_emotional_plan: Dict = None,  # 新增参数
                        overall_emotional_blueprint: Dict = None) -> Optional[Dict]:  # 新增参数
```

### 修改点2: 在 prompt 中增加情绪规划引用

```python
# 在 _build_decomposition_prompt() 中增加：
emotional_guidance = ""
if stage_emotional_plan and "emotional_segments" in stage_emotional_plan:
    emotional_guidance = "\n## 阶段情绪分段指导\n"
    for segment in stage_emotional_plan["emotional_segments"]:
        emotional_guidance += f"""
### {segment['segment_name']} ({segment['chapter_range']})
- 核心情绪：{segment['target_emotion_keyword']}
- 情绪任务：{segment['core_emotional_task']}
"""
```

### 修改点3: 中型事件输出格式

```python
medium_event = {
    "name": "中型事件名称",
    # 新增字段
    "parent_stage_emotional_segment": "压抑与铺垫期",
    "emotion_contribution_to_stage": "通过描述主角受欺凌，累积读者压抑情绪",
    # 保留现有字段
    "emotional_focus": "屈辱/不甘",
    "emotional_intensity": "high",
    "key_emotional_beats": ["被人嘲笑", "实力不济", "决心变强"]
}
```

---

## 六、总结

### 当前问题
- 事件已拆分到中型事件层级，但情绪规划只停留在阶段分段层级
- 两者不匹配，导致情绪指导不够精确

### 推荐方案
**短期**：轻量级优化（方案C）
- 在中型事件中增加与阶段情绪分段的映射关系
- 不增加API调用，快速实施

**长期**：双层情绪规划（方案A）
- 为重大事件增加情绪细分
- 建立完整的情绪层级体系

### 下一步行动
1. 确认采用哪个方案
2. 实施代码修改
3. 测试验证效果