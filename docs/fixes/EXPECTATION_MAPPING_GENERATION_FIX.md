# 期待感映射生成修复（AI智能分析版）

## 问题描述

在第一阶段生成过程中，**期待感映射（expectation_map）没有被生成**，导致：

1. 用户访问故事线页面时看到警告：
   ```
   ⚠️ 故事线数据存在但没有期待感映射，前端将不会显示期待感标签
   ```

2. 虽然API层有后备生成逻辑，但这只在用户访问时才触发，不应该依赖这种后备方案

3. 期待感标签应该在**第一阶段生成时**就自动创建并保存

## 根本原因

查看代码流程：
1. [`PhaseGenerator._generate_stage_writing_plans()`](src/core/PhaseGenerator.py:388-444) 调用 `StagePlanManager.generate_stage_writing_plan()`
2. [`StagePlanManager.generate_stage_writing_plan()`](src/managers/StagePlanManager.py:200-320) 生成重大事件和中型事件
3. **但是**，在整个过程中**没有调用期待感管理器**来为事件添加期待感标签！
4. 期待感映射只在API层（[`phase_generation_api.py:1441-1486`](web/api/phase_generation_api.py:1441-1486)）有一个**后备生成逻辑**，但这只在用户访问故事线页面时才触发

## 修复方案

### 核心设计原则

**期待感映射必须由AI智能分析生成，而不是简单的关键词匹配规则！**

- ✅ **AI智能分析**：让AI理解事件内容，选择最合适的期待类型
- ✅ **智能推理**：AI会分析事件的目标、情感焦点、在剧情中的作用
- ✅ **后备方案**：如果AI分析失败，降级到规则匹配（但不应该依赖）

### 实现方案

在 [`StagePlanManager.generate_stage_writing_plan()`](src/managers/StagePlanManager.py:200-320) 中添加了 **Phase 5.5** 来生成期待感映射：

### 1. 在 `generate_stage_writing_plan()` 中调用期待感映射生成

```python
# Phase 5: 验证和保存
self.logger.info("   Phase 5: 进行最终整体验证和保存...")
final_writing_plan = self._validate_and_optimize_writing_plan(
    final_writing_plan, stage_name, stage_range
)

# 🆕 Phase 5.5: 生成期待感映射
self.logger.info("   Phase 5.5: 为事件生成期待感标签...")
final_writing_plan = self._generate_expectation_mapping(
    final_writing_plan, stage_name
)
```

### 2. 新增 `_generate_expectation_mapping()` 方法

位置：[`src/managers/StagePlanManager.py:1065-1179`](src/managers/StagePlanManager.py:1065-1179)

**功能**：
- ✅ 初始化 `ExpectationManager` 和 `ExpectationIntegrator`
- ✅ 使用AI智能分析每个事件，选择最合适的期待类型
- ✅ AI会分析事件的目标、情感焦点、在剧情中的作用
- ✅ AI返回期待类型、种植章节、目标章节和理由
- ✅ 如果AI分析失败，降级到规则匹配（但不应该依赖）
- ✅ 导出期待感映射并保存到项目目录

**AI智能分析工作流程**：
```python
# 1. 初始化期待感管理器
expectation_manager = ExpectationManager()
expectation_integrator = ExpectationIntegrator(expectation_manager)

# 2. 构建AI分析prompt
events_summary = [
    {
        "name": "主角初入江湖",
        "chapter_range": "1-10",
        "main_goal": "建立主角形象和世界观",
        "role_in_stage_arc": "起",
        "emotional_focus": "好奇、探索"
    },
    ...
]

# 3. 调用AI分析
analysis_prompt = f"""你是网文期待感策划专家。请分析以下事件...

# 期待感类型说明：
1. showcase（展示橱窗）: 提前展示奖励或能力的强大
2. suppression_release（压抑释放）: 制造阻碍，积累势能
3. nested_doll（套娃期待）: 大期待包着小期待
4. emotional_hook（情绪钩子）: 打脸、认同、身份揭秘
5. power_gap（实力差距）: 展示实力差距
6. mystery_foreshadow（伏笔揭秘）: 埋下伏笔

# 事件列表：
{json.dumps(events_summary)}

请为每个事件返回：
{{
  "index": 1,
  "expectation_type": "showcase",
  "reasoning": "该事件涉及宝物发现，适合使用展示橱窗...",
  "planting_chapter": 10,
  "target_chapter": 15,
  "description": "主角获得神秘宝物的期待"
}}
"""

# 4. 解析AI返回的结果并种植期待
for ai_event in ai_events:
    exp_id = expectation_manager.tag_event_with_expectation(
        event_id=event_name,
        expectation_type=ai_event["expectation_type"],
        planting_chapter=ai_event["planting_chapter"],
        description=ai_event["description"],
        target_chapter=ai_event["target_chapter"]
    )

# 5. 导出并保存期待感映射
expectation_map = expectation_manager.export_expectation_map()
```

## AI智能分析 vs 规则匹配

### AI智能分析（主要方式）

**优势**：
- ✅ 理解事件上下文和深层含义
- ✅ 能够分析复杂的情感和剧情关系
- ✅ 选择更精准的期待类型
- ✅ 提供选择理由（reasoning）

**AI Prompt示例**：
```
你是网文期待感策划专家。请分析以下重大事件...

事件：主角初入江湖
- 章节：1-10
- 目标：建立主角形象和世界观
- 情感焦点：好奇、探索

分析结果：
- 期待类型：showcase（展示橱窗）
- 理由：该事件用于展示世界观的宏大和主角的潜力，适合使用展示橱窗效应
- 种植章节：1
- 目标章节：5
```

### 规则匹配（后备方式）

**用途**：仅当AI分析失败时使用

| 期待类型 | 关键词匹配 | 适用场景 |
|---------|-----------|---------|
| `SUPPRESSION_RELEASE` | 击败、战胜、复仇、逆袭 | 主角需要反击的场景 |
| `SHOWCASE` | 获得、得到、炼成、宝物 | 获得奖励或能力 |
| `MYSTERY_FORESHADOW` | 揭秘、真相、秘密、身世 | 悬疑或谜题 |
| `EMOTIONAL_HOOK` | 误解、轻视、震惊、打脸 | 情绪冲突 |
| `POWER_GAP` | 展示、学习、提升、突破 | 实力成长 |
| `NESTED_DOLL` | 挑战、任务、试炼 | 多层次期待（默认） |

**注意**：规则匹配只是后备方案，不应该依赖它！

## 数据结构

### 期待感映射结构
```json
{
  "expectations": {
    "exp_事件名_章节": {
      "type": "suppression_release",
      "status": "planted",
      "planted_chapter": 10,
      "target_chapter": 15,
      "released_chapter": null,
      "description": "事件名: 目标描述...",
      "satisfaction_score": null
    }
  },
  "event_expectation_map": {
    "事件名": "exp_事件名_章节"
  },
  "chapter_hooks": {
    "10": ["exp_事件名_章节"],
    "15": ["exp_事件名_章节"]
  }
}
```

### 写作计划中的存储
```json
{
  "stage_writing_plan": {
    "stage_name": "opening_stage",
    "chapter_range": "1-30",
    "event_system": {
      "major_events": [...]
    },
    "expectation_map": {
      // 期待感映射数据
    }
  }
}
```

## 文件存储

期待感映射会保存在：
```
小说项目/
  {小说标题}/
    expectation_map.json  ← 期待感映射文件
```

这个文件会被API层的加载逻辑读取：
```python
# web/api/phase_generation_api.py:1406-1414
expectation_map_file = loader.project_dir / "expectation_map.json"
if expectation_map_file.exists():
    with open(expectation_map_file, 'r', encoding='utf-8') as f:
        expectation_data = json.load(f)
        expectation_map = expectation_data.get('expectation_map', expectation_data)
```

## 测试验证

1. **生成新项目**时，检查第一阶段生成日志：
   ```
   Phase 5.5: 为事件生成期待感标签...
     -> 开始为【opening_stage】生成期待感映射（AI智能分析）...
     🤖 AI正在分析【opening_stage】的 5 个重大事件...
       ✓ AI为事件 '主角初入江湖' 选择期待类型: showcase
         理由: 该事件用于展示世界观的宏大和主角的潜力
       ✓ AI为事件 '初遇宿敌' 选择期待类型: suppression_release
         理由: 该事件涉及主角与宿敌的首次冲突，适合使用压抑释放
     ✅ AI成功为【opening_stage】的 5 个事件生成期待感标签
       ✅ 期待感映射已保存: 小说项目/标题/expectation_map.json
   ```

2. **访问故事线页面**，确认：
   - ✅ 没有警告信息
   - ✅ 每个事件显示对应的期待感标签
   - ✅ 期待感类型合理

3. **检查文件**，确认：
   - ✅ `expectation_map.json` 文件存在
   - ✅ 包含所有重大事件的期待感映射
   - ✅ 数据结构正确

## 相关文件

- **核心修复**：
  - [`src/managers/StagePlanManager.py`](src/managers/StagePlanManager.py:298-302) - 添加 Phase 5.5 调用
  - [`src/managers/StagePlanManager.py`](src/managers/StagePlanManager.py:1065-1179) - `_generate_expectation_mapping()` 方法
  - [`src/managers/ExpectationManager.py`](src/managers/ExpectationManager.py:675-838) - `analyze_and_tag_events()` AI智能分析
  
- **后备方案**：
  - [`src/managers/ExpectationManager.py`](src/managers/ExpectationManager.py:840-933) - 规则匹配分析
  - [`web/api/phase_generation_api.py:47-147`](web/api/phase_generation_api.py:47-147) - `select_expectation_type()` 函数
  
- **其他相关**：
  - [`src/core/PhaseGenerator.py`](src/core/PhaseGenerator.py:388-444) - 调用阶段计划生成

- **文档**：
  - [`docs/expectation_management/EXPECTATION_SYSTEM_GUIDE.md`](docs/expectation_management/EXPECTATION_SYSTEM_GUIDE.md) - 期待感系统指南
  - [`docs/expectation_management/INTEGRATION_EXAMPLE.md`](docs/expectation_management/INTEGRATION_EXAMPLE.md) - 集成示例

## 影响范围

- ✅ **向后兼容**：旧项目没有期待感映射时，API层的后备逻辑仍然有效
- ✅ **性能影响**：每个阶段生成时额外调用期待感管理器，影响可忽略
- ✅ **数据一致性**：新项目生成的写作计划会自动包含期待感映射

## 总结

这次修复确保了**期待感映射在第一阶段生成时就自动创建，并使用AI智能分析**，而不是依赖简单的关键词匹配规则或API层的后备逻辑。这样：
1. ✅ 用户体验更好，不会看到警告信息
2. ✅ 数据一致性更好，生成时就有期待感标签
3. ✅ 期待感类型更精准，AI理解事件上下文
4. ✅ 代码结构更合理，核心生成逻辑完整
5. ✅ 有智能后备方案，即使AI失败也能继续

**关键改进**：
- 🤖 **AI智能分析**：不再是简单的关键词匹配，而是AI理解事件内容
- 📝 **智能推理**：AI会提供选择理由，便于调试和优化
- 🔄 **优雅降级**：AI失败时自动降级到规则匹配，不会中断流程
- 💾 **持久化**：期待感映射保存到文件，API可以加载使用

修复日期：2026-01-04