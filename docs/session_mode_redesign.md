# 小说生成系统：会话模式改造设计方案

## 一、问题分析

### 1.1 当前现状
- **传统模式**：每个子步骤（世界观、角色、阶段计划等）都是独立的单次 API 调用，LLM 没有上下文记忆，导致：
  - 前后设定不一致（角色能力与世界观冲突）
  - 重复解释背景，Token 浪费
  - 质量低、需要大量后校验

- **现有会话模式**：`PhaseOneConversationSession` 已将一阶段 7 个步骤塞进**同一个 Kimi 会话**：
  1. foundation_planning（写作风格+市场分析）
  2. worldview_factions（世界观+势力）
  3. character_design（核心角色）
  4. emotional_growth（情绪蓝图+成长规划）
  5. stage_overview（全书阶段划分）
  6. stage_details（各阶段详细计划）
  7. supplementary_chars（补充角色）

### 1.2 "内容偏多"的痛点
把一阶段所有内容塞进**一个会话**，产生以下问题：

| 问题 | 表现 |
|------|------|
| **上下文稀释** | 到第 5、6 轮时，LLM 对早期设定（如世界观细节）的记忆衰减，导致阶段计划与世界观偏离 |
| **输出 token 爆炸** | `stage_details` 要求输出所有阶段的每章细纲，单次 JSON 可达 15K+ token，解析压力大 |
| **错误回滚成本高** | 如果第 6 步失败，前面 5 步全部作废，无法复用 |
| **角色漂移** | LLM 在一个会话中同时扮演"设定专家+角色专家+结构专家+市场分析师"，容易角色混乱 |
| **二阶段无法承接** | 如果把章节生成也接入同一个会话，上下文会彻底失控 |

---

## 二、设计目标

1. **全链路会话化**：不仅是第一阶段，第二阶段（章节正文生成）也要引入会话模式
2. **解决内容过载**：通过"分域会话 + 摘要传递"，控制单个会话的上下文量
3. **保持设定一致性**：会话之间不是传递原始 JSON，而是传递**结构化摘要（Context Brief）**
4. **失败可恢复**：每个会话结束即为一个坚固检查点，失败时从上一个会话恢复
5. **对外兼容**：仍然暴露 15 个标准步骤的进度和检查点，前端无感

---

## 三、核心设计原则：Domain-Specific Session（分域会话）

### 3.1 原则
> **一个会话 = 一个创作域 = 一个专家角色 = 5~8 轮对话**

把原来"一阶段一个大会话"拆成 **3 个独立会话**，第二阶段拆成 **N 个阶段会话**。

### 3.2 会话拆分架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          创意种子 + 方案选择                              │
│                    （仍为单次调用，快速确定方向）                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  会话 A：创作基线会话 (Foundation Session)                                │
│  角色：世界观与风格专家                                                   │
│  轮次：3~4 轮                                                            │
│  内容：                                                                 │
│    1. 生成写作风格指南                                                     │
│    2. 生成市场分析                                                         │
│    3. 生成世界观框架                                                       │
│    4. 生成势力/阵营系统                                                    │
│  输出：创作基线文档 (Foundation Brief, ~1500 字)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ Foundation Brief
┌─────────────────────────────────────────────────────────────────────────┐
│  会话 B：角色与叙事会话 (Character Session)                                │
│  角色：角色与叙事专家                                                     │
│  轮次：3~4 轮                                                            │
│  内容：                                                                 │
│    1. 核心角色设计（主角、盟友、反派）                                      │
│    2. 情绪蓝图设计                                                         │
│    3. 主角成长规划                                                         │
│  输入：会话 A 的 Foundation Brief（摘要，非完整 JSON）                     │
│  输出：角色叙事文档 (Character Brief, ~2000 字)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ Foundation Brief + Character Brief
┌─────────────────────────────────────────────────────────────────────────┐
│  会话 C：结构规划会话 (Structure Session)                                  │
│  角色：结构规划专家                                                       │
│  轮次：3~4 轮                                                            │
│  内容：                                                                 │
│    1. 全书阶段划分（5~8 个阶段）                                           │
│    2. 阶段详细写作计划（重点阶段详细，其余概述）                            │
│    3. 全书补充角色生成                                                     │
│  输入：A 的 Foundation Brief + B 的 Character Brief                       │
│  输出：完整的大纲数据结构 (novel_data 一阶段全部字段)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ 一阶段完成
┌─────────────────────────────────────────────────────────────────────────┐
│  阶段会话 D~N：阶段写作会话 (Stage Writing Session)                        │
│  角色：执笔作家                                                           │
│  轮次：每阶段 5~10 轮（细纲 2 轮 + 正文 3~8 轮）                            │
│  内容：                                                                 │
│    1. 生成该阶段的章节细纲（3~5 章一细纲）                                  │
│    2. 逐章生成正文                                                         │
│    3. 章节内回溯修正（可选）                                                │
│  输入：该阶段所需的 Foundation Brief + Character Brief + 当前阶段计划摘要    │
│  输出：该阶段全部章节正文                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 四、关键机制设计

### 4.1 Context Brief（会话间摘要传递）

**这是解决"内容偏多"的核心机制。**

会话之间不传递完整的 JSON 原始数据，而是在每个会话结束时，由 LLM 自动生成一份**精炼的上下文摘要（Context Brief）**，供下一个会话使用。

#### Foundation Brief 示例格式
```markdown
# 创作基线摘要

## 世界观核心
- 力量体系：灵气复苏，修为分九境...
- 世界规则：天道残缺，强者可撕裂虚空...
- 关键地点：青云宗（主角起点）、魔渊（最终战场）...

## 风格定位
- 核心风格：热血升级+权谋智斗
- 语言特点：短句为主、打斗场景快节奏、对话带机锋
- 禁止事项：禁止现代网络用语、禁止战力崩坏

## 市场定位
- 目标平台：番茄小说
- 核心卖点：废柴逆袭、宗门争霸、秘境探险
- 目标读者：18-30 岁男性，偏好传统玄幻
```

#### Character Brief 示例格式
```markdown
# 角色与叙事摘要

## 核心角色
- 林凡（主角）：18岁，青云宗外门弟子，性格隐忍但睚眦必报...
- 苏婉儿（盟友）：医仙传人，与主角有救命之恩...
- 血魔老祖（反派）：魔渊领袖，曾与主角师父有旧...

## 情绪主线
- 开局：压抑→爆发（第1-10章）
- 中段：顺境→背叛→谷底（第11-50章）
- 高潮：复仇→登顶（第51-200章）

## 成长里程碑
- 第1阶段：觉醒金手指（灵气亲和度MAX）
- 第3阶段：获得上古传承
- 第5阶段：突破至圣人境
```

#### 为什么不用原始 JSON？
| 对比项 | 原始 JSON | Context Brief |
|--------|-----------|---------------|
| Token 长度 | 8000~15000 | 1500~2500 |
| 信息密度 | 低（大量结构化字段） | 高（自然语言，保留关键约束） |
| LLM 理解度 | 一般（机器格式） | 高（人话，带强调） |
| 一致性 | 容易遗漏字段 | 重点突出，不易遗忘 |

### 4.2 会话内的"自约束机制"

在每个会话的系统提示词中，加入**约束声明**：

```
## 当前会话规则
1. 你只能修改当前会话负责的创作域内容
2. 对于输入的 Context Brief，你只能引用，不能修改
3. 如果你发现当前域的设定与 Context Brief 冲突，请在输出中标注冲突点，而不是擅自修改
4. 每轮输出后，请用 1-2 句话总结本轮对设定的关键变更
```

### 4.3 二阶段：Stage Writing Session（阶段写作会话）

这是质量提升最大的地方。当前章节生成是"单章单次调用"，没有上下文，导致：
- 章与章之间衔接生硬
- 伏笔回收困难
- 角色语气不连贯

#### Stage Writing Session 流程
```
第 1 轮：生成阶段细纲
  系统：你正在写《XX》的第 X 阶段（第 30-60 章）
  用户：请根据以下阶段计划，生成第 30-35 章的详细细纲...
  AI：输出 6 章的细纲

第 2 轮：确认/调整细纲
  用户：第 33 章的转折太突兀，请调整为...
  AI：修改后的细纲

第 3 轮：生成第 30 章正文
  用户：请根据细纲，生成第 30 章正文，约 3000 字...
  AI：第 30 章正文

第 4 轮：生成第 31 章正文
  用户：继续生成第 31 章...
  AI：第 31 章正文（携带第 30 章结尾上下文）

...（中间章节）...

第 N 轮：阶段总结
  用户：请总结本阶段已写内容，并列出留给下阶段的悬念和伏笔
  AI：阶段总结摘要
```

**每阶段一个独立会话**，会话结束时产出的"阶段总结"可以作为下一个阶段会话的输入之一。

### 4.4 进度映射与检查点兼容性

对外仍然保持现有的 15 步骤进度体系：

| 实际执行 | 对外步骤 |
|---------|---------|
| 会话 A：foundation_planning | writing_style (8%) → market_analysis (15%) → worldview (23%) → faction_system (31%) |
| 会话 B：character_design | character_design (38%) → emotional_growth_planning (46%) |
| 会话 C：stage_overview → stage_details → supplementary | stage_plan (62%) → detailed_stage_plans (69%) → supplementary_characters (74%) → expectation_mapping (77%) → system_init (85%) |
| 二阶段：Stage Writing Session 1 | phase_two_progress (按章节进度映射) |

每个会话完成时保存一个**坚固检查点（Durable Checkpoint）**：
- 会话 A 完成 → 保存 `foundation_brief` + `novel_data` 基线字段
- 会话 B 完成 → 保存 `character_brief` + `novel_data` 角色字段
- 会话 C 完成 → 保存完整 `novel_data`（一阶段结束）
- 阶段会话 N 完成 → 保存该阶段所有章节 + `stage_summary`

---

## 五、架构改造方案

### 5.1 类结构改造

```python
# 新增：通用会话基类
class NovelGenerationSession(ConversationSession):
    """小说生成专用会话基类，支持 Context Brief 输入和自约束"""
    
    def __init__(self, api_client, domain: str, context_briefs: List[str], ...):
        # domain: "foundation" | "character" | "structure" | "writing"
        # context_briefs: 上游会话的摘要列表
        ...
    
    def generate_brief(self) -> str:
        """会话结束时，自动生成本域的 Context Brief"""
        ...

# 新增：分域会话实现
class FoundationSession(NovelGenerationSession):
    """会话 A：创作基线"""
    STEPS = ["writing_style", "market_analysis", "worldview", "faction_system"]

class CharacterSession(NovelGenerationSession):
    """会话 B：角色与叙事"""
    STEPS = ["character_design", "emotional_blueprint", "global_growth_plan"]

class StructureSession(NovelGenerationSession):
    """会话 C：结构规划"""
    STEPS = ["stage_overview", "stage_details", "supplementary_chars"]

class StageWritingSession(NovelGenerationSession):
    """会话 D~N：阶段写作"""
    def generate_stage_outline(self, stage_plan): ...
    def generate_chapter(self, chapter_num): ...
    def generate_stage_summary(self) -> str: ...

# 新增：会话编排器
class SessionOrchestrator:
    """
    负责：
    1. 按顺序启动各个 Domain Session
    2. 传递 Context Brief
    3. 保存中间检查点
    4. 对外映射进度到 15 步骤体系
    """
    def run_phase_one(self) -> bool:
        # 1. 启动 FoundationSession
        # 2. 获取 FoundationBrief，启动 CharacterSession
        # 3. 获取 CharacterBrief，启动 StructureSession
        # 4. 输出完整 novel_data
        ...
    
    def run_phase_two_stage(self, stage_number: int) -> bool:
        # 1. 提取当前阶段需要的所有 Brief
        # 2. 启动 StageWritingSession
        # 3. 保存章节 + StageSummary
        ...
```

### 5.2 PhaseGenerator 改造点

当前 `PhaseGenerator.generate_phase_one_preparations()` 的逻辑：

```python
# 旧逻辑
if 用多轮对话模式:
    调用 PhaseOneConversationSession（7 步一个会话）
else:
    分步调用（单次 API）
```

**新逻辑**：
```python
# 新逻辑
if 用分域会话模式:
    orchestrator = SessionOrchestrator(self.generator)
    return orchestrator.run_phase_one()
elif 用旧的多轮对话模式:
    保留原有兼容路径
else:
    分步调用（单次 API）
```

### 5.3 NovelGenerator 改造点

- `phase_one_generation()` 不变，调用 `PhaseGenerator.generate_phase_one_preparations()`
- 新增 `phase_two_stage_generation(stage_number)` 方法，用于按阶段生成章节
- 新增配置项 `use_domain_session_mode = True`

### 5.4 检查点系统改造

在 `GenerationCheckpoint` 中新增支持保存 `context_briefs`：

```json
{
  "phase": "phase_one",
  "step": "character_design",
  "step_status": "completed",
  "data": {
    "novel_data_snapshot": {...},
    "context_briefs": {
      "foundation_brief": "...",
      "character_brief": "..."
    }
  }
}
```

恢复时，从检查点读取 `context_briefs`，直接传入下一个会话，无需重新生成。

---

## 六、数据流图

```
                    ┌─────────────────┐
                    │   创意种子 + 方案  │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │    FoundationSession (A)     │
              │  输出: foundation_brief      │
              │  检查点: foundation_done     │
              └──────────────┬───────────────┘
                             │ foundation_brief
                             ▼
              ┌──────────────────────────────┐
              │    CharacterSession (B)      │
              │  输出: character_brief       │
              │  检查点: character_done      │
              └──────────────┬───────────────┘
                             │ foundation_brief + character_brief
                             ▼
              ┌──────────────────────────────┐
              │    StructureSession (C)      │
              │  输出: 完整 novel_data       │
              │  检查点: phase_one_completed │
              └──────────────┬───────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │          StageWritingSession 1             │
        │  输入: briefs + stage_1_plan               │
        │  输出: chapters 1-30 + stage_1_summary     │
        │  检查点: stage_1_completed                 │
        └────────────────────┬───────────────────────┘
                             │ stage_1_summary
                             ▼
        ┌────────────────────────────────────────────┐
        │          StageWritingSession 2             │
        │  输入: briefs + stage_2_plan + s1_summary  │
        │  输出: chapters 31-60 + stage_2_summary    │
        │  检查点: stage_2_completed                 │
        └────────────────────┬───────────────────────┘
                             │ ...
                             ▼
```

---

## 七、实施建议（优先级排序）

### Phase 1：搭建基础设施（1-2 天）
1. 实现 `NovelGenerationSession` 基类
2. 实现 `SessionOrchestrator` 骨架
3. 修改 `GenerationCheckpoint` 支持保存 `context_briefs`

### Phase 2：改造一阶段（2-3 天）
1. 实现 `FoundationSession`、`CharacterSession`、`StructureSession`
2. 在 `PhaseGenerator` 中接入 `SessionOrchestrator`
3. 保留旧模式作为配置回退（`use_domain_session_mode = False`）
4. 跑通一阶段全流程，对比质量

### Phase 3：改造二阶段（3-5 天）
1. 实现 `StageWritingSession`
2. 修改章节生成入口，支持"按阶段生成"
3. 前端增加"按阶段生成"的进度显示
4. 重点测试：
   - 章与章衔接是否自然
   - 伏笔回收率是否提高
   - 角色语气是否一致

### Phase 4：优化与固化（2-3 天）
1. 根据测试结果调整各 session 的系统提示词
2. 优化 Context Brief 的生成 prompt，确保信息密度
3. 完善检查点恢复逻辑
4. 废弃旧的多轮对话模式，全面切换到分域会话模式

---

## 八、风险与应对

| 风险 | 应对 |
|------|------|
| Context Brief 丢失关键信息 | 在生成 Brief 的 prompt 中强制要求列出"不可修改的硬性约束"清单 |
| 会话 A 和 B 之间设定冲突 | 在 B 的系统提示中加入"冲突检测"指令，要求 LLM 标注而非覆盖 |
| Stage Writing Session 上下文超限 | 当单阶段超过 30 章时，拆成 2 个子会话；定期总结并裁剪历史 |
| Token 成本反而上升 | Kimi 缓存命中后 Context Brief 成本极低；若成本敏感，可回退到旧模式 |
| 前端进度显示断层 | `SessionOrchestrator` 负责把内部步骤实时映射到 15 步骤体系 |

---

## 九、总结

**核心结论**：不要把"一阶段"甚至"全书"塞进一个大会话。应该采用 **Domain-Specific Session（分域会话）+ Context Brief（摘要传递）** 的架构：

- **3 个会话完成一阶段**：Foundation → Character → Structure
- **N 个会话完成二阶段**：每个阶段一个 Stage Writing Session
- **会话之间传递精炼摘要**，而不是原始 JSON
- **每个会话结束即为一个坚固检查点**

这样既能享受会话模式带来的**上下文连贯、设定一致、质量提升**，又能避免"内容偏多"导致的**上下文稀释、输出爆炸、失败成本高**的问题。
