# 情绪规划逻辑纠正

## 核心问题发现

用户的质疑揭示了一个根本性的逻辑错误：

### 错误的设计逻辑
```
情绪计划（先规划） → 导致 → 事件（后发生）
```
❌ **这是反直觉的！**

### 正确的逻辑
```
事件（发生了什么） → 导致 → 情绪（主角/读者感受到什么）
```
✅ **这才是自然的因果关系！**

## 当前系统的问题

### 1. EmotionalPlanManager 的设计问题

**当前做法**：
```python
# EmotionalPlanManager 独立生成情绪计划
stage_emotional_plan = {
    "emotional_segments": [
        {
            "segment_name": "压抑与铺垫期",
            "chapter_range": "31-45",
            "target_emotion_keyword": "压抑/屈辱",
            "core_emotional_task": "累积读者负面情绪"
        }
    ]
}
```

**问题**：
- 这个情绪计划是"独立于事件"生成的
- 它规定了"第31-45章应该让读者感到压抑"
- 但没有考虑**具体发生了什么事件**
- 情绪和事件是**割裂的**

### 2. 数据流问题

**当前流程**：
```
1. EmotionalPlanManager 生成阶段情绪分段（第31-45章要压抑）
2. EventDecomposer 分解重大事件（第31-40章发生什么）
3. 两者之间没有强关联！
```

**问题**：
- 如果第31-40章发生的事件是"主角获得金手指、大杀四方"
- 那情绪应该是"爽快、扬眉吐气"
- 但情绪计划要求的是"压抑、屈辱"
- **矛盾！**

## 正确的设计逻辑

### 核心原则

> **情绪是从事件中自然产生的，不应该预先规定情绪再去找事件。**

### 正确的数据流

```
1. EmotionalBlueprintManager - 顶层情绪蓝图（战略级）
   ├─ 定义情感光谱（核心情感驱动力）
   ├─ 定义分阶段情绪目标（起承转合）
   └─ 定义关键情绪转折点
   
2. StagePlanManager - 生成重大事件骨架
   └─ 基于阶段目标，规划重大事件
   
3. EventDecomposer - 分解重大事件为中型事件
   ├─ 输入：重大事件骨架 + 阶段情绪目标
   ├─ 推导：每个中型事件的情绪目标
   └─ 输出：中型事件 + 从事件推导出的情绪目标
```

### 关键变化

**删除**：
- ❌ `EmotionalPlanManager.generate_stage_emotional_plan()` - 不再独立生成阶段情绪分段

**增强**：
- ✅ `EventDecomposer.decompose_major_event()` - 在分解时推导情绪目标

## 重新设计

### Step 1: 保留顶层情绪蓝图（不变）

**EmotionalBlueprintManager** 继续工作：
```python
emotional_blueprint = {
    "emotional_spectrum": ["复仇宣泄感", "守护温情", "兄弟情谊"],
    "stage_emotional_arcs": {
        "opening_stage": {
            "description": "从极度压抑和屈辱，到获得一线希望的期待感",
            "start_emotion": "压抑/迷茫",
            "end_emotion": "期待/决心"
        },
        "development_stage": {
            "description": "在不断成长中体验友情与信任，但因背叛而陷入低谷，最终重新振作",
            "start_emotion": "成长喜悦",
            "end_emotion": "悲愤后的坚定"
        }
    }
}
```

**作用**：
- 这是**战略级的指导**
- 定义了整个阶段的情绪起点和终点
- 不规定具体细节，只规定方向

### Step 2: 在事件分解时推导情绪

**EventDecomposer** 的新职责：

```python
def decompose_major_event(self, 
                        major_event_skeleton: Dict,
                        stage_emotional_arc: Dict,  # 新增：阶段情绪弧线
                        overall_emotional_blueprint: Dict):  # 新增：整体情绪蓝图
    
    # 构建提示词
    prompt = f"""
    # 任务：分解重大事件并推导情绪目标
    
    ## 重大事件信息
    - 名称：{major_event_skeleton['name']}
    - 章节范围：{major_event_skeleton['chapter_range']}
    - 核心目标：{major_event_skeleton['main_goal']}
    
    ## 阶段情绪弧线指导
    - 阶段起点情绪：{stage_emotional_arc['start_emotion']}
    - 阶段终点情绪：{stage_emotional_arc['end_emotion']}
    - 阶段情绪描述：{stage_emotional_arc['description']}
    
    ## 核心要求
    1. **事件优先**：首先规划"起承转合"应该发生什么事件
    2. **情绪推导**：基于发生的事件，推导主角/读者会感受到什么情绪
    3. **情绪连贯**：确保情绪发展符合阶段情绪弧线的方向
    
    ## 输出格式
    {{
        "name": "重大事件名称",
        "composition": {{
            "起": [
                {{
                    "name": "中型事件名称",
                    "main_goal": "事件目标",
                    "description": "事件描述",
                    
                    # === 情绪推导（从事件推导出来） ===
                    "emotional_derivation": {{
                        "trigger_event": "触发这个情绪的具体事件",
                        "emotional_response": "主角/读者自然的情绪反应",
                        "emotional_intensity": "low/medium/high",
                        "emotional_beats": ["情绪节拍1", "情绪节拍2"]
                    }},
                    
                    # === 与阶段情绪弧线的对齐 ===
                    "alignment_with_stage_arc": {{
                        "position_in_arc": "起/承/转/合",
                        "contribution_to_stage_emotion": "这个事件如何推动阶段情绪发展"
                    }}
                }}
            ]
        }}
    }}
    """
```

### Step 3: 数据示例

**输入**：
```python
# 阶段情绪弧线
stage_emotional_arc = {
    "description": "从极度压抑和屈辱，到获得一线希望的期待感",
    "start_emotion": "压抑/迷茫",
    "end_emotion": "期待/决心"
}

# 重大事件骨架
major_event = {
    "name": "首次历练任务",
    "chapter_range": "31-40",
    "main_goal": "通过历练任务展示主角成长"
}
```

**输出（从事件推导情绪）**：
```python
{
    "name": "首次历练任务",
    "composition": {
        "起": [{
            "name": "接受任务",
            "main_goal": "主角报名参加历练任务",
            "description": "主角在任务榜前犹豫，最终下定决心报名",
            
            # 从事件推导情绪
            "emotional_derivation": {
                "trigger_event": "主角看到任务要求，担心实力不足，但咬牙报名",
                "emotional_response": "忐忑不安中带着一丝决心",
                "emotional_intensity": "medium",
                "emotional_beats": [
                    "看到高要求时的自我怀疑",
                    "回忆过往失败的不甘",
                    "咬牙报名的决绝"
                ]
            },
            
            # 与阶段情绪弧线对齐
            "alignment_with_stage_arc": {
                "position_in_arc": "起",
                "contribution_to_stage_emotion": "在压抑的基础上，埋下希望的种子"
            }
        }],
        
        "承": [{
            "name": "遭遇挫折",
            "main_goal": "任务中遭遇困难，被队友轻视",
            "description": "主角在战斗中表现不佳，被队友嘲讽",
            
            "emotional_derivation": {
                "trigger_event": "主角实力不足，战斗失利，被嘲笑",
                "emotional_response": "屈辱、愤怒、不甘",
                "emotional_intensity": "high",
                "emotional_beats": [
                    "战斗无力的尴尬",
                    "被嘲讽的屈辱",
                    "内心强烈的愤怒与不甘"
                ]
            },
            
            "alignment_with_stage_arc": {
                "position_in_arc": "承",
                "contribution_to_stage_emotion": "将压抑情绪推向顶点，为爆发做铺垫"
            }
        }]
    }
}
```

## 修改清单

### 删除（1处）
- ❌ `EmotionalPlanManager.generate_stage_emotional_plan()` - 不再需要

### 修改（2处）

#### 1. EventDecomposer.decompose_major_event()
**文件**: `src/managers/stage_plan/event_decomposer.py`

**修改**：
```python
def decompose_major_event(self, 
                        major_event_skeleton: Dict, 
                        stage_name: str, 
                        stage_range: str, 
                        novel_title: str, 
                        novel_synopsis: str, 
                        creative_seed: Dict, 
                        overall_stage_plan: Dict,
                        global_novel_data: Dict,
                        stage_emotional_arc: Dict = None,        # 改名：从 plan 改为 arc
                        overall_emotional_blueprint: Dict = None
                        ) -> Optional[Dict]:
```

#### 2. EventDecomposer._build_decomposition_prompt()
**文件**: `src/managers/stage_plan/event_decomposer.py`

**核心改动**：
- 不再引用"阶段情绪分段"
- 改为引用"阶段情绪弧线"（起点情绪、终点情绪）
- 提示词改为"从事件推导情绪"，而不是"按情绪规划事件"

#### 3. StagePlanManager._decompose_major_events_to_medium_only()
**文件**: `src/managers/StagePlanManager.py`

**修改**：
```python
def _decompose_major_events_to_medium_only(self, ...):
    # 不再调用 EmotionalPlanManager
    
    # 从 emotional_blueprint 中提取阶段情绪弧线
    emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
    stage_emotional_arc = emotional_blueprint.get("stage_emotional_arcs", {}).get(stage_name)
    
    # 传递给 EventDecomposer
    fleshed_out_event = self.event_decomposer.decompose_major_event(
        ...
        stage_emotional_arc=stage_emotional_arc,  # 传递弧线，不是计划
        overall_emotional_blueprint=emotional_blueprint
    )
```

## 总结

### 核心原则修正

**错误**：情绪 → 导致 → 事件
**正确**：事件 → 导致 → 情绪

### 设计修正

1. **保留顶层情绪蓝图** - 战略级指导，定义方向
2. **删除阶段情绪分段** - 不再预先规定细节
3. **增强事件分解** - 从事件推导情绪，而不是按情绪规划事件

### 好处

- ✅ 逻辑自然：情绪从事件中产生
- ✅ 因果一致：事件和情绪对齐
- ✅ 灵活性：事件决定情绪，而不是情绪限制事件
- ✅ 减少API：不再单独生成阶段情绪计划