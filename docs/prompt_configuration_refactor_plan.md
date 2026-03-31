# 提示词配置化改造计划

## 📊 当前状态分析

### 1. 已JSON化的配置

#### ✅ 市场导向模式 (market_driven)
| 配置项 | 文件路径 | 状态 |
|--------|---------|------|
| 步骤配置 | `steps/step_1_plan.json` ~ `step_6_chapter.json` | ✅ 已配置化 (6步) |
| 章节生成提示词 | `chapter_generation_prompts.json` | ✅ 已配置化 |
| 黄金三章提示词 | `golden_chapter_prompts.json` | ✅ 已配置化 |
| 战术规划提示词 | `tactical_planning_prompts.json` | ✅ 已配置化 |
| 写作风格 | `styles/*.json` | ✅ 已配置化 |

#### ✅ 传统模式 (traditional)
| 配置项 | 文件路径 | 状态 |
|--------|---------|------|
| 一阶段产物配置 | `phase_one/*.json` (10个) | ✅ 已配置化 |
| 二阶段章节配置 | `phase_two/*.json` (2个) | ✅ 已配置化 |
| 模式流程配置 | `mode_config.json` | ✅ 已配置化 |

### 2. 硬编码提示词统计

#### 🔴 高优先级（需要立即改造）
| 文件 | 硬编码数量 | 主要问题 |
|------|-----------|---------|
| `chapter_prompt_optimizer_v3.py` | **15+** | System Prompt组件全部硬编码，第1章详细指令1500+行 |
| `trope_prompt_builder.py` | **9** | 4阶段System Prompt全部硬编码 |
| `prompt_templates.py` | **7** | 5步骤Prompt模板生成器 |

#### 🟡 中优先级
| 文件 | 硬编码数量 | 主要问题 |
|------|-----------|---------|
| `market_driven_conversation.py` | **12** | 备用/默认提示词硬编码，主流程已支持JSON |
| `stage_chapter_generator.py` | **2** | 阶段System Prompt和单章Prompt硬编码 |

#### 🟢 低优先级（可延迟改造）
| 文件 | 硬编码数量 | 主要问题 |
|------|-----------|---------|
| `batch_chapter_generator.py` | **2** | Prompt构建硬编码 |
| `strategic_planner.py` | **2** | 战略规划Prompt硬编码 |
| `emotion_curve_generator.py` | **1** | 情绪曲线Prompt硬编码 |
| `plan_generator.py` | **1** | 标题生成Prompt硬编码 |
| `chapter_quality_checker.py` | **3** | 优化片段硬编码 |
| `tactical_planner.py` | **2** | 战术规划核心Prompt硬编码 |

---

## 🎯 改造目标

### 目标1: 100% 步骤配置化
- 所有一阶段步骤提示词支持JSON配置
- 所有二阶段章节生成提示词支持JSON配置
- 支持前端界面修改配置

### 目标2: System Prompt 组件化
- 将System Prompt拆分为可复用组件
- 支持动态组合
- 支持题材特定的组件

### 目标3: 模板引擎升级
- 支持条件渲染
- 支持变量继承
- 支持多层级配置覆盖

---

## 🏗️ 统一配置架构设计

### 配置目录结构
```
prompt_packages/
├── _base/                          # 基础可复用组件
│   ├── system_components/          # System Prompt组件
│   │   ├── header.json             # 头部身份定义
│   │   ├── core_rules.json         # 核心规则
│   │   ├── output_format.json      # 输出格式
│   │   ├── genre_specific/         # 题材特定组件
│   │   │   ├── guoyun.json
│   │   │   ├── shenhao.json
│   │   │   └── xianxia.json
│   │   └── algorithm_guides/       # 番茄算法指南
│   │       ├── emotion_density.json
│   │       ├── appeal_density.json
│   │       └── hook_design.json
│   └── writing_styles/             # 写作风格（已有）
│
├── default/
│   ├── market_driven/              # 市场导向模式
│   │   ├── package_info.json       # 包信息
│   │   ├── mode_config.json        # 模式配置（新增）
│   │   ├── steps/                  # 一阶段步骤（已有）
│   │   ├── phase_two/              # 二阶段配置（新增）
│   │   │   ├── system_prompt.json  # 章节生成System Prompt
│   │   │   ├── chapter_prompt.json # 单章Prompt模板
│   │   │   └── quality_check.json  # 质量检查Prompt
│   │   └── components/             # 组件库（新增）
│   │       ├── golden_chapter_1.json
│   │       ├── golden_chapter_2.json
│   │       ├── golden_chapter_3.json
│   │       └── standard_chapter.json
│   │
│   └── traditional/                # 传统模式（已有）
│       └── ...
│
└── user_custom/                    # 用户自定义
    └── {user_id}/
        └── {custom_mode}/
```

### 配置文件格式规范

#### 1. System Prompt 组件格式
```json
{
  "component_id": "header",
  "name": "头部身份定义",
  "description": "定义AI助手的身份和专业性",
  "content": "你是顶级网文策划专家...",
  "variables": ["genre", "style"],
  "conditional": {
    "genre": {
      "国运文": "你精通国运文的弹幕套路...",
      "神豪文": "你精通神豪文的数字爽点..."
    }
  },
  "editable": true,
  "ui_config": {
    "type": "textarea",
    "rows": 10,
    "label": "身份定义"
  }
}
```

#### 2. 步骤配置格式（扩展）
```json
{
  "step_id": "step_1_plan",
  "step_name": "生成完整方案",
  "step_order": 1,
  "system_prompt_components": [
    "header",
    "core_rules",
    "output_format"
  ],
  "prompt_template": {
    "type": "composite",
    "components": [
      {"ref": "genre_analysis"},
      {"ref": "user_choices"},
      {"ref": "output_requirements"}
    ]
  },
  "editable_components": ["core_rules", "output_requirements"],
  "ui_sections": [
    {
      "name": "核心规则",
      "component": "core_rules",
      "editable": true
    }
  ]
}
```

---

## 📝 详细改造任务清单

### Phase 1: 基础架构 (优先级: 🔴 高)

- [ ] **1.1 创建基础组件库**
  - [ ] 创建 `_base/system_components/` 目录
  - [ ] 迁移 `header` 组件 (从 `chapter_prompt_optimizer_v3.py`)
  - [ ] 迁移 `core_rules` 组件
  - [ ] 迁移 `output_format` 组件
  - [ ] 创建 `algorithm_guides` 子目录

- [ ] **1.2 升级 PromptLoader**
  - [ ] 支持组件加载和组合
  - [ ] 支持条件渲染
  - [ ] 支持变量继承

- [ ] **1.3 创建 Phase Two 配置目录**
  - [ ] 创建 `market_driven/phase_two/` 目录
  - [ ] 创建 `system_prompt.json`
  - [ ] 创建 `chapter_prompt.json`
  - [ ] 创建 `quality_check.json`

### Phase 2: 一阶段提示词配置化 (优先级: 🔴 高)

- [ ] **2.1 改造 `trope_prompt_builder.py`**
  - [ ] 将 `build_setting_system_prompt` → `_base/system_components/setting_stage.json`
  - [ ] 将 `build_character_system_prompt` → `_base/system_components/character_stage.json`
  - [ ] 将 `build_plot_system_prompt` → `_base/system_components/plot_stage.json`
  - [ ] 将 `build_chapter_system_prompt` → `_base/system_components/chapter_stage.json`
  - [ ] 修改代码从JSON加载

- [ ] **2.2 改造 `prompt_templates.py`**
  - [ ] 将6个步骤Prompt迁移到对应 `steps/step_X_xxx.json`
  - [ ] 修改代码从JSON加载

- [ ] **2.3 改造 `market_driven_conversation.py` 默认提示词**
  - [ ] 将默认角色设定迁移到JSON
  - [ ] 将默认情绪曲线迁移到JSON
  - [ ] 将默认阶段目标迁移到JSON

### Phase 3: 二阶段提示词配置化 (优先级: 🔴 高)

- [ ] **3.1 改造 `chapter_prompt_optimizer_v3.py`**
  - [ ] 将 `_build_header()` 迁移到组件
  - [ ] 将 `_build_core_setting()` 迁移到组件
  - [ ] 将 `_build_worldview_section()` 迁移到组件
  - [ ] 将 `_build_protagonist_section()` 迁移到组件
  - [ ] 将 `_build_tomato_algorithm_guide()` 迁移到组件
  - [ ] 将 `_build_micro_innovation_guide()` 迁移到组件
  - [ ] 将 `_build_genre_specific_guide()` 迁移到组件
  - [ ] 将 `_build_shock_techniques()` 迁移到组件
  - [ ] 将 `_build_emotion_control()` 迁移到组件
  - [ ] 将 `_build_format_rules()` 迁移到组件
  - [ ] 将 `_build_ai_self_check_guide()` 迁移到组件
  - [ ] 将黄金三章详细指令迁移到JSON

- [ ] **3.2 改造 `stage_chapter_generator.py`**
  - [ ] 将 `_build_stage_system_prompt()` 迁移到JSON
  - [ ] 将 `_build_chapter_prompt()` 迁移到JSON

### Phase 4: 质量检查和规划类 (优先级: 🟡 中)

- [ ] **4.1 改造质量检查相关**
  - [ ] `chapter_quality_checker.py` 优化片段JSON化
  - [ ] `chapter_two_stage_optimizer.py`

- [ ] **4.2 改造规划类**
  - [ ] `strategic_planner.py`
  - [ ] `tactical_planner.py`
  - [ ] `emotion_curve_generator.py`

### Phase 5: UI支持 (优先级: 🟡 中)

- [ ] **5.1 前端配置界面**
  - [ ] 支持步骤配置编辑
  - [ ] 支持组件编辑
  - [ ] 支持实时预览

- [ ] **5.2 配置验证**
  - [ ] JSON Schema验证
  - [ ] 变量引用检查
  - [ ] 循环依赖检查

---

## 🎨 前端配置界面设计

### 1. 步骤配置编辑页
```
┌─────────────────────────────────────────────┐
│ 步骤配置: 生成完整方案 (step_1_plan)         │
├─────────────────────────────────────────────┤
│                                             │
│ System Prompt组件:                          │
│ ☑️ 头部身份定义  [编辑]                      │
│ ☑️ 核心规则      [编辑]                      │
│ ☑️ 输出格式      [编辑]                      │
│                                             │
│ Prompt模板:                                 │
│ ┌───────────────────────────────────────┐   │
│ │ {{genre_analysis}}                    │   │
│ │ {{user_choices}}                      │   │
│ │ {{output_requirements}}               │   │
│ └───────────────────────────────────────┘   │
│                                             │
│ [保存] [重置为默认] [预览]                   │
└─────────────────────────────────────────────┘
```

### 2. 组件库管理页
```
┌─────────────────────────────────────────────┐
│ 组件库管理                                   │
├─────────────────────────────────────────────┤
│ 分类: [全部] [System] [模板] [题材特定]     │
│                                             │
│ ┌─────────────────────────────────────┐     │
│ │ 📄 头部身份定义 (header)            │     │
│ │     定义AI助手的身份和专业性        │     │
│ │     [编辑] [复制] [删除]            │     │
│ └─────────────────────────────────────┘     │
│                                             │
│ ┌─────────────────────────────────────┐     │
│ │ 📄 番茄算法-情绪密度指南            │     │
│ │     情绪词密度≥2.0个/千字要求       │     │
│ │     [编辑] [复制] [删除]            │     │
│ └─────────────────────────────────────┘     │
│                                             │
│ [+ 新建组件]                                │
└─────────────────────────────────────────────┘
```

---

## 📅 实施建议

### 时间估算
| Phase | 任务数 | 预估工时 | 优先级 |
|-------|-------|---------|--------|
| Phase 1 | 10 | 2天 | 🔴 高 |
| Phase 2 | 15 | 3天 | 🔴 高 |
| Phase 3 | 13 | 4天 | 🔴 高 |
| Phase 4 | 6 | 2天 | 🟡 中 |
| Phase 5 | 5 | 3天 | 🟡 中 |
| **总计** | **49** | **14天** | - |

### 推荐实施顺序
1. **第一周**: Phase 1 + Phase 2 (基础 + 一阶段)
2. **第二周**: Phase 3 (二阶段，最重要)
3. **第三周**: Phase 4 + Phase 5 (质量检查 + UI)

### 风险控制
- **向后兼容**: 改造期间保持旧代码作为fallback
- **渐进发布**: 每个Phase完成后单独测试
- **配置版本控制**: JSON配置增加version字段

---

## ✅ 验收标准

1. **功能验收**
   - [ ] 所有硬编码提示词已迁移到JSON
   - [ ] 前端可以编辑所有步骤配置
   - [ ] 配置修改后实时生效

2. **性能验收**
   - [ ] JSON加载时间 < 100ms
   - [ ] 配置切换时间 < 50ms

3. **兼容性验收**
   - [ ] 旧项目可以正常加载
   - [ ] 新配置可以降级使用默认
