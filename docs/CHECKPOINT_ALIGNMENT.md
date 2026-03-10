# 检查点与UI步骤对齐说明

## 修改概述

将恢复模式的检查点与UI的14步生成流程严格对齐，确保用户能够清晰了解当前恢复位置。

## 架构设计

### 后端检查点步骤（13个）

```python
# generation_checkpoint.py 中定义的 PHASES['phase_one']['steps']
1.  initialization              (0%)   - 初始化
2.  writing_style              (8%)   - 写作风格
3.  market_analysis            (15%)  - 市场分析
4.  worldview                  (23%)  - 世界观构建
5.  faction_system             (31%)  - 势力系统
6.  character_design           (38%)  - 角色设计
7.  emotional_growth_planning  (46%)  - 情感蓝图与成长规划（合并）
8.  stage_plan                 (62%)  - 分阶段大纲
9.  detailed_stage_plans       (69%)  - 详细阶段计划
10. expectation_mapping        (77%)  - 期待感地图
11. system_init                (85%)  - 系统初始化
12. saving                     (92%)  - 保存结果
13. quality_assessment         (100%) - 质量评估
```

### 前端UI显示步骤（14个）

```javascript
// phase-one-setup-v2.html 中定义的 allSteps
1.  creative_refinement       - 创意精炼
2.  fanfiction_detection      - 同人检测
3.  multiple_plans            - 多计划生成
4.  plan_selection            - 计划选择
5.  foundation_planning       - 基础规划
6.  worldview_with_factions   - 世界观与势力
7.  character_design          - 角色设计
8.  emotional_growth_planning - 情感与成长规划
9.  stage_plan                - 分阶段大纲
10. detailed_stage_plans      - 详细阶段计划
11. expectation_mapping       - 期待感地图
12. system_init               - 系统初始化
13. saving                    - 保存结果
14. quality_assessment        - 质量评估
```

## 步骤映射关系

| 后端检查点步骤 | 前端UI步骤 |
|----------------|-----------|
| initialization | creative_refinement, fanfiction_detection, multiple_plans, plan_selection |
| writing_style | foundation_planning |
| market_analysis | foundation_planning |
| worldview | worldview_with_factions |
| faction_system | worldview_with_factions |
| character_design | character_design |
| emotional_growth_planning | emotional_growth_planning |
| stage_plan | stage_plan |
| detailed_stage_plans | detailed_stage_plans |
| expectation_mapping | expectation_mapping |
| system_init | system_init |
| saving | saving |
| quality_assessment | quality_assessment |

## 关键修改

### 1. generation_checkpoint.py
- 将 `emotional_blueprint` 和 `growth_plan` 合并为 `emotional_growth_planning`
- 更新子步骤定义，将两个原步骤作为合并后步骤的子步骤
- 更新 API 调用估算

### 2. PhaseGenerator.py
- `step_progress_map` 使用13个步骤（已与检查点对齐）
- 在 `update_progress_callback` 中添加检查点自动保存逻辑

### 3. novel_manager.py
- 更新 `_update_checkpoint` 调用，使用与检查点定义一致的步骤名称

### 4. phase-one-setup-v2.html
- `STEP_NAME_MAPPING` 已支持前后端步骤名称映射
- 前端会自动将后端步骤名称映射到显示步骤

## 恢复行为

当用户恢复生成时：

1. 后端从最后一个保存的检查点步骤继续
2. 前端根据 `current_step` 正确显示当前进度
3. 合并步骤（如 emotional_growth_planning）会显示为单个UI步骤
4. 用户可以看到清晰的恢复位置和剩余步骤

## 测试验证

运行测试脚本验证对齐：

```bash
python tests/test_checkpoint_alignment.py
```

验证内容包括：
- 后端检查点步骤数量（13个）
- 前端UI步骤数量（14个）
- 前后端映射完整性
- 子步骤定义正确性
