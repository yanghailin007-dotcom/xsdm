# 情绪规划增强 - 实施指南

## 核心策略

**通过增强提示词实现三层情绪规划，无需增加API调用**

## 实施步骤

### Step 1: 修改方法签名（1处）

**文件**: `src/managers/stage_plan/event_decomposer.py`

**方法**: [`EventDecomposer.decompose_major_event()`](src/managers/stage_plan/event_decomposer.py:17)

**修改**:
```python
# 新增两个可选参数
def decompose_major_event(self, 
                        major_event_skeleton: Dict, 
                        stage_name: str, 
                        stage_range: str, 
                        novel_title: str, 
                        novel_synopsis: str, 
                        creative_seed: Dict, 
                        overall_stage_plan: Dict,
                        global_novel_data: Dict,
                        stage_emotional_plan: Dict = None,        # 新增
                        overall_emotional_blueprint: Dict = None  # 新增
                        ) -> Optional[Dict]:
```

### Step 2: 增强提示词构建方法（1处）

**文件**: `src/managers/stage_plan/event_decomposer.py`

**方法**: [`EventDecomposer._build_decomposition_prompt()`](src/managers/stage_plan/event_decomposer.py:178)

**修改内容**:
1. 添加 `_format_stage_emotional_plan()` 辅助方法
2. 在 prompt 中增加阶段情绪计划引用
3. 在 prompt 中增加重大事件情绪细分要求
4. 在输出格式中增加新字段要求

**关键新增字段**:
```python
# 在每个中型事件中要求AI生成：
{
    "stage_emotional_mapping": {
        "segment_name": "所属的阶段情绪分段",
        "segment_emotion_keyword": "阶段情绪关键词",
        "contribution_to_stage_emotion": "对阶段情绪目标的贡献"
    },
    "major_event_emotional_arc": "起/承/转/合",
    "emotional_transition_from": "从什么情绪过渡",
    "emotional_transition_to": "过渡到什么情绪",
    "emotional_beat_sequence": [
        {
            "beat_type": "trigger/accumulation/climax/release",
            "emotion": "具体情绪",
            "intensity": "low/medium/high",
            "scene_hint": "场景提示"
        }
    ]
}
```

### Step 3: 更新调用处（1处）

**文件**: `src/managers/StagePlanManager.py`

**方法**: [`StagePlanManager._decompose_major_events_to_medium_only()`](src/managers/StagePlanManager.py:652)

**修改**:
```python
# 在分解前生成阶段情绪计划
emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
stage_emotional_plan = self.emotional_manager.generate_stage_emotional_plan(
    stage_name, stage_range, emotional_blueprint
)

# 调用时传入
fleshed_out_event = self.event_decomposer.decompose_major_event(
    major_event_skeleton=skeleton,
    stage_name=stage_name,
    stage_range=stage_range,
    novel_title=novel_title,
    novel_synopsis=novel_synopsis,
    creative_seed=creative_seed,
    overall_stage_plan=overall_stage_plan,
    global_novel_data=self.generator.novel_data,
    stage_emotional_plan=stage_emotional_plan,              # 新增
    overall_emotional_blueprint=emotional_blueprint          # 新增
)
```

## 修改总结

| 修改点 | 文件 | 方法 | 改动量 |
|--------|------|------|--------|
| 1 | event_decomposer.py | decompose_major_event() | 方法签名+2行 |
| 2 | event_decomposer.py | _build_decomposition_prompt() | 提示词增强（~100行） |
| 3 | event_decomposer.py | 新增 _format_stage_emotional_plan() | 新方法（~30行） |
| 4 | StagePlanManager.py | _decompose_major_events_to_medium_only() | +8行 |

**总计**: 约140行代码修改

## 不需要修改的地方

- ✅ `EmotionalPlanManager` - 保持不变，继续生成阶段情绪分段
- ✅ 中型事件的现有字段 - `emotional_focus`、`emotional_intensity` 等保留
- ✅ 其他调用处 - 参数是可选的，不影响现有逻辑

## 验证方法

修改后，检查生成的中型事件是否包含：
1. `stage_emotional_mapping` - 映射到阶段情绪分段
2. `major_event_emotional_arc` - 在重大事件中的情绪定位
3. `emotional_beat_sequence` - 有序的情绪节拍

## 数据流示例

**输入**:
```
阶段情绪分段: "压抑与铺垫期" (31-45章)
重大事件: "首次历练任务" (31-40章)
```

**输出**:
```
中型事件: "接受任务" (31-32章)
  └─ stage_emotional_mapping.segment_name: "压抑与铺垫期"
  └─ major_event_emotional_arc: "起"
  └─ emotional_beat_sequence: [犹豫→不安→决心]
```

## 风险评估

- **风险等级**: 低
- **原因**: 
  1. 只修改提示词和参数传递
  2. 新字段是可选的，不破坏现有逻辑
  3. 向后兼容，不影响其他功能