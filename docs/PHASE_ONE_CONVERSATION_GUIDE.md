# 第一阶段对话化改造 - 开发文档

## 概述

本项目将小说生成第一阶段的剩余步骤（步骤5-13）改造为多轮对话模式，以提高生成质量和一致性。

## 架构设计

### 整体流程

```
第一阶段（15步骤）
├── 步骤1-4: CreativeToPlanConversation（原有）
│   └── 产物: final_plan
├── 步骤5-6: FoundationPlanningSession（新增）
│   └── 产物: writing_style_guide, market_analysis, core_worldview, faction_system
├── 步骤7-8: CharacterNarrativeSession（新增）
│   └── 产物: character_design, emotional_blueprint, global_growth_plan
├── 步骤9-11: _generate_overall_planning（传统）
│   └── 产物: stage_plans, emotional_blueprint, global_growth_plan, supplementary_characters
├── 步骤12-13: ExpectationSystemSession（新增）
│   └── 产物: expectation_mapping, system_init
└── 步骤14-15: 传统方法（保存+质量评估）
```

### 会话架构

```
PhaseOneConversationOrchestrator
├── Session A: FoundationPlanningSession
│   ├── 输入: final_plan
│   ├── 对话: 6轮
│   └── 输出: foundation_brief
├── Session B: CharacterNarrativeSession
│   ├── 输入: final_plan + foundation_brief
│   ├── 对话: 6轮
│   └── 输出: character_brief
└── Session D: ExpectationSystemSession
    ├── 输入: novel_data + all_briefs
    ├── 对话: 3轮
    └── 输出: expectation_brief
```

## 核心组件

### 1. Session 基类

**位置**: `src/core/session_mode/novel_generation_session.py`

所有 Session 继承自 `NovelGenerationSession`，它提供：
- Context Brief 输入支持
- 结构化输出解析
- 自动 Brief 生成

### 2. 新开发的 Sessions

#### FoundationPlanningSession

**位置**: `src/core/session_mode/sessions/foundation_planning_session.py`

**职责**: 生成基础规划（写作风格、市场分析、世界观、势力系统）

**对话轮次**: 6轮
1. 分析 final_plan，提取关键要素
2. 生成写作风格指南
3. 进行市场分析
4. 构建世界观
5. 设计势力系统
6. 整合输出

**产物格式**:
```json
{
  "writing_style_guide": {
    "core_style": "str",
    "language_characteristics": ["str"],
    "key_principles": ["str"],
    "atmosphere": "str",
    "pacing": "str",
    "dialogue_style": "str"
  },
  "market_analysis": {
    "target_platform": "str",
    "genre_positioning": "str",
    "core_selling_points": ["str"],
    "target_audience": "str",
    "competitive_analysis": {},
    "market_potential": "str"
  },
  "core_worldview": {
    "world_overview": "str",
    "power_system": "str",
    "key_locations": [],
    "world_rules": ["str"],
    "historical_background": "str"
  },
  "faction_system": {
    "factions": [],
    "main_conflict": "str",
    "faction_power_balance": "str",
    "recommended_starting_faction": "str"
  }
}
```

#### CharacterNarrativeSession

**位置**: `src/core/session_mode/sessions/character_narrative_session.py`

**职责**: 设计角色与叙事（主角、配角、情绪蓝图、成长规划）

**对话轮次**: 6轮
1. 分析 FoundationPlanning 的 Context Brief
2. 主角深度设计
3. 配角和反派设计
4. 情绪蓝图规划
5. 成长里程碑设计
6. 整合输出

**产物格式**:
```json
{
  "character_design": {
    "protagonist": {
      "basic_info": {"name": "str", ...},
      "goals": {},
      "abilities": {},
      "personality": {}
    },
    "supporting_characters": [],
    "antagonist": {}
  },
  "emotional_blueprint": {
    "emotional_arcs": [],
    "key_emotional_beats": [],
    "emotional_themes": []
  },
  "global_growth_plan": {
    "protagonist_growth": [],
    "milestone_events": [],
    "power_progression": [],
    "relationship_development": []
  }
}
```

#### ExpectationSystemSession

**位置**: `src/core/session_mode/sessions/expectation_system_session.py`

**职责**: 设计期待感系统（元素提取、登场时机、系统集成）

**对话轮次**: 3轮
1. 分析前序产物，提取期待感元素
2. 设计元素登场时机
3. 整合与系统集成

**产物格式**:
```json
{
  "expectation_mapping": {
    "expectation_elements": [],
    "element_schedule": {},
    "reveal_timing": {}
  },
  "system_init": {
    "initialized_systems": [],
    "status": "completed"
  }
}
```

### 3. 验证器

**位置**: `src/core/session_mode/validators.py`

每个 Session 都有对应的验证器：
- `FoundationPlanningValidator`
- `CharacterNarrativeValidator`
- `ExpectationSystemValidator`

验证器检查产物格式是否与传统模式一致。

### 4. 回退管理器

**位置**: `src/core/session_mode/fallback_manager.py`

**功能**:
- 管理每个 Session 的执行模式（对话/传统/自动）
- 对话模式失败时自动降级到传统模式
- 记录执行统计和回退历史

**配置示例**:
```python
config = {
    "foundation_planning": {"mode": "auto"},  # 自动选择
    "character_narrative": {"mode": "conversation"},  # 强制对话
    "expectation_system": {"mode": "traditional"}  # 强制传统
}
```

### 5. 编排器

**位置**: `src/core/session_mode/phase_one_orchestrator.py`

**功能**:
- 管理多个 Session 的执行顺序
- 传递 Context Brief
- 映射进度到15步骤体系
- 集成检查点管理

## 使用方法

### 启用对话模式

在配置中设置：

```python
config = {
    "use_creative_conversation_mode": True,  # 步骤1-4
    "use_phase_one_conversation_mode": True,  # 步骤5-13
    "session_fallback": {
        "foundation_planning": {"mode": "auto"},
        "character_narrative": {"mode": "auto"},
        "expectation_system": {"mode": "auto"}
    }
}
```

### 强制使用传统模式

```python
config = {
    "use_phase_one_conversation_mode": False
}
```

### 单独测试 Session

```python
from src.core.session_mode.sessions.foundation_planning_session import (
    FoundationPlanningSession
)

session = FoundationPlanningSession(
    api_client=api_client,
    novel_data=novel_data,
    provider="gemini",
    temperature=0.7
)

result = session.execute_all_steps()
```

## 测试

### 运行集成测试

```bash
python -m tests.test_full_integration
```

### 运行单个 Session 测试

```bash
python -m tests.test_foundation_planning_session --all
python -m tests.test_character_narrative_session --all
```

## 注意事项

### 1. 产物格式兼容性

所有对话模式的产物必须与传统模式完全一致。使用验证器确保兼容性。

### 2. Context Brief 传递

Session B 接收 Session A 的 Brief，Session D 接收所有前面的 Brief。确保 Brief 格式正确。

### 3. 回退机制

默认启用自动回退。如果对话模式失败，会自动降级到传统模式。

### 4. 细纲生成

步骤9-11（细纲生成）保持传统实现，因为它已经稳定工作且经过多轮优化。

## 文件结构

```
src/core/session_mode/
├── __init__.py
├── phase_one_orchestrator.py      # 第一阶段编排器
├── validators.py                   # 产物格式验证器
├── fallback_manager.py             # 回退管理器
├── novel_generation_session.py     # Session 基类
└── sessions/
    ├── __init__.py
    ├── foundation_planning_session.py   # Session A
    ├── character_narrative_session.py    # Session B
    ├── expectation_system_session.py     # Session D
    └── structure_session.py              # 现有（未启用）

tests/
├── test_full_integration.py        # 完整集成测试
├── test_foundation_planning_session.py
├── test_character_narrative_session.py
└── test_expectation_system_session.py
```

## 总结

本次改造将第一阶段的 3 个关键步骤（基础规划、角色叙事、期待感系统）对话化，保留了细纲生成的传统实现。新架构支持：

1. **灵活的执行模式** - 每个 Session 可独立配置
2. **自动回退** - 确保稳定性
3. **Context Brief 传递** - 保持上下文连贯
4. **产物格式兼容** - 与传统模式100%兼容

所有测试通过，可以安全使用。
