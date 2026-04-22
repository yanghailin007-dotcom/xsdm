# 自由创意模式一阶段改造方案

## 一、改造目标

将自由创意模式的一阶段从"多步骤分会话"架构，改造为"单会话爽点驱动"架构，同时升级产物丰富度。

### 核心指标
- API调用次数：从 15+ 次独立调用 → 1-2 次对话调用
- 产物丰富度：从"抽象框架" → "具象素材库（角色参考库/爽点清单/逐章细纲）"
- 结构模型：从"起承转合四段式" → "爽点单元制"
- 状态追踪：从"无" → "主角实时状态（财富/位置/心情/已完成事件）"

---

## 二、产物格式定义（核心）

### 2.1 统一核心设定文件：`core_settings.json`

```json
{
  "book_title": "书名",
  "book_summary_short": "一句话简介（80字内）",
  "book_summary_long": "详细简介（200-300字）",
  "tomato_tags": {
    "main_category": "都市",
    "themes": ["神豪", "系统", "逆袭"],
    "roles": ["男主", "美女", "反派"],
    "plots": ["系统流", "打脸", "逆袭"],
    "target_audience": "男频"
  },
  "system_mechanism": {
    "name": "系统名称",
    "binding_rule": "绑定规则",
    "daily_requirement": "日常要求",
    "unlock_function": "解锁功能",
    "limitations": "限制条件"
  },
  "initial_state": {
    "protagonist_wealth": "0",
    "protagonist_location": "出租屋",
    "protagonist_mood": "沮丧",
    "system_daily_limit": "100万",
    "system_today_withdrawn": "0",
    "binding_days": "0",
    "completed_events": ""
  }
}
```

### 2.2 角色卡+参考库：`character_reference_library.json`

```json
{
  "protagonist": {
    "name": "江辰",
    "age": 27,
    "identity": "大厂程序员，刚被裁员",
    "appearance": "具体外貌描述（头发/穿着/体型）",
    "personality": "表面温和、内心吐槽、关键时刻硬气",
    "background": "被裁员、被劈腿、银行卡300元",
    "common_phrases": ["口头禅1", "口头禅2"],
    "typical_expressions": ["翻白眼", "嘴角抽搐"],
    "typical_actions": ["摸鼻子", "推眼镜"],
    "habits": "具体习惯"
  },
  "key_characters": [
    {
      "name": "关珊珊（红毛）",
      "role": "暴力搞笑担当",
      "appearance": "红色长发、花臂纹身、紧身皮裤",
      "common_phrases": ["cnm老娘弄死你！"],
      "typical_actions": ["一脚踹门", "摔手机"],
      "bond_with_protagonist": "从雇佣关系到生死之交"
    }
  ],
  "reference_library": {
    "daily_behavior": ["打游戏时全神贯注，赢了大喊大叫", "刷抖音时不停大笑"],
    "dialogue_library": ["哎呀，你这样子太土了吧！", "哥，带我去蹦迪呗！"],
    "expression_library": ["翻白眼", "吐舌头", "歪头笑"]
  }
}
```

### 2.3 爽点单元制阶段规划：`satisfaction_units.json`

```json
{
  "structural_model": "爽点单元制",
  "total_chapters": 200,
  "units": [
    {
      "unit_id": "U1",
      "unit_name": "【钩子单元】系统觉醒+首次猎奇",
      "chapter_range": "1-20",
      "core_satisfaction": "金手指激活+身份反差",
      "satisfaction_moments": [
        {"chapter": "1", "type": "低谷铺垫", "desc": "被裁员+被劈腿，银行卡300元"},
        {"chapter": "2", "type": "金手指", "desc": "网吧绑定精神小妹，系统激活"},
        {"chapter": "5", "type": "日常猎奇", "desc": "带精神小妹吃路边摊，路人震惊"},
        {"chapter": "10", "type": "小爽点", "desc": "首次提现，买苹果手机"},
        {"chapter": "20", "type": "单元高潮", "desc": "大巴上精神小妹初显威，红毛踹厕所门"}
      ],
      "key_antagonist": "无",
      "ending_hook": "到达村口，老妈审视，精神小妹惊艳亮相"
    },
    {
      "unit_id": "U2",
      "unit_name": "【怼人单元】极品亲戚连环打脸",
      "chapter_range": "21-50",
      "core_satisfaction": "怼亲戚+白切黑+打脸",
      "satisfaction_moments": [
        {"chapter": "23", "type": "怼人", "desc": "大姑催婚，指手画脚"},
        {"chapter": "26", "type": "白切黑", "desc": "瑶瑶装委屈，反手抖出大姑儿子高利贷"},
        {"chapter": "31", "type": "技术爽点", "desc": "二舅妈嫌贫爱富，麦麦查出出轨黑历史"},
        {"chapter": "46", "type": "暴力爽点", "desc": "村霸找茬，红毛单挑整个帮派"},
        {"chapter": "50", "type": "单元高潮", "desc": "极品亲戚全部闭嘴，主角地位初显"}
      ],
      "key_antagonist": "大姑/二舅妈/村霸",
      "ending_hook": "绿茶初恋带富二代回家炫耀"
    }
  ]
}
```

### 2.4 逐章细纲：`chapter_outline.md`

每章格式：
```markdown
## 第X章 [章节标题]
- **场景设定**：[地点、时间、氛围]
- **涉及角色**：[主要角色]
- **核心爽点**：[爽点类型+具体描述]
- **具体情节**：
  1. 开场：...
  2. 发展：...
  3. 碰撞：...
  4. 结尾：...
- **关键对话示例**：
  - 角色A："..."
  - 角色B："..."
- **角色细节**：[具体外貌/表情/动作描写]
- **状态更新**：
  - 主角财富：...
  - 主角位置：...
  - 主角心情：...
  - 已完成事件：...
```

---

## 三、单会话 Prompt 设计

### 3.1 System Prompt

```
你是番茄小说平台的顶级编辑+写手。你的任务是基于用户创意，一次性输出完整的一阶段设定。

## 输出规范（严格JSON格式）

你必须输出一个完整的JSON对象，包含以下7个顶级字段：

1. `book_info` — 书名、简介、番茄标签
2. `system_mechanism` — 系统机制（绑定规则/日常要求/解锁功能/限制条件）
3. `character_cards` — 角色卡（主角+关键配角，必须含外貌/口头禅/习惯性动作）
4. `character_reference_library` — 参考库（日常行为/对话/表情/动作模板）
5. `worldbuilding` — 世界观（现代都市背景+精神小妹文化圈层+融合场景）
6. `satisfaction_units` — 爽点单元规划（5-8个单元，每个单元含爽点事件清单）
7. `initial_state` — 初始状态（主角财富/位置/心情/系统额度/已完成事件）

## 核心规则

### 角色设计（必须具象化）
- 每个角色必须有：具体外貌（头发颜色/妆容/穿着/体型）、口头禅（3-5句）、习惯性动作（2-3个）、典型表情（2-3个）
- 禁止抽象描述如"美女""反派""性格隐忍"
- 配角必须有与主角的关系定位和互动模式

### 系统机制（必须融入剧情）
- 系统不是外挂，是故事引擎
- 必须设计限制条件（如"每天必须和精神小妹待8小时"）制造日常冲突
- 成长感来自系统解锁新功能，不是单纯数值增加

### 爽点单元制（禁止起承转合）
- 全书划分为5-8个爽点单元
- 每个单元有独立的爽点主题（如"怼极品亲戚""打脸前女友"）
- 单元名本身就是阅读钩子
- 单元内部节奏：小爽点密集（每2-3章）+ 单元末大爽点
- 单元之间用"身份升级"或"新地图"连接

### 参考库（必须可执行）
- `dialogue_library`：每个主要角色至少5句典型台词
- `expression_library`：至少6种微表情（翻白眼/吐舌头/歪头笑...）
- `daily_behavior_library`：至少6种日常行为（打游戏摔手机/蹦迪吐烟圈...）

### 番茄风格约束
- 快节奏：每章都有进展，开场3句话进入正题
- 爽点密集：每章至少1个小爽点
- 对话多：用对话推动情节，不要大段叙述
- 口语化：贴近网络用语
- 轻喜剧：轻松幽默，不要太沉重

## 禁止事项
- ❌ 起承转合四段式结构
- ❌ 前女友羞辱、穷小子逆袭等老套路开局
- ❌ 抽象概括的角色描述
- ❌ 与剧情无关的系统外挂
- ❌ 改造精神小妹（必须保持本色）
```

### 3.2 User Prompt

```
请基于以下创意，生成完整的一阶段设定：

## 用户创意
{creative_seed}

## 总章节数
{total_chapters}章

## 目标平台
番茄小说（男频/快节奏/爽点密集）

## 特别要求
{additional_requirements}

请严格按照System Prompt中定义的JSON格式输出全部7个字段。
如果输出过长被截断，优先保证前4个字段（book_info/system_mechanism/character_cards/reference_library）完整。
```

---

## 四、架构改造

### 4.1 新增文件

| 文件 | 职责 |
|------|------|
| `src/core/creative_phase_one_session.py` | 单会话一阶段生成器（核心） |
| `src/core/parsers/phase_one_parser.py` | 一阶段产物解析+验证+补全 |
| `src/core/parsers/state_tracker.py` | 状态追踪器（财富/位置/心情/事件） |
| `src/prompts/creative_phase_one_prompts.py` | 单会话Prompt模板 |

### 4.2 改造文件

| 文件 | 改造内容 |
|------|---------|
| `src/core/PhaseGenerator.py` | 删除 `_generate_phase_one_with_creative_conversation` + `_continue_phase_one_after_conversation` 嵌套，改为调用 `CreativePhaseOneSession` |
| `src/core/PhaseGenerator.py` | `_generate_overall_planning` 中的起承转合 → 爽点单元制 |
| `src/prompts/PlanningPrompts.py` | `overall_stage_plan` prompt 重写 |
| `src/prompts/PlanningPrompts.py` | `emotional_development_planning` 阶段命名改 unit_id |
| `src/prompts/PlanningPrompts.py` | `emotional_blueprint_generation` 按爽点单元划分情绪弧线 |
| `src/core/NovelGenerator.py` | `phase_one_generation` 中增加 `use_single_session_mode` 配置 |
| `web/managers/novel_manager.py` | 进度步骤从15个改为5个（初始化/方案生成/设定细化/细纲生成/保存） |

### 4.3 删除/废弃

| 文件/方法 | 原因 |
|-----------|------|
| `src/core/creative_to_plan_conversation.py` | 被单会话替代 |
| `src/core/session_mode/sessions/foundation_planning_session.py` | 被单会话替代 |
| `PhaseGenerator._generate_phase_one_with_creative_conversation()` | 被单会话替代 |
| `PhaseGenerator._continue_phase_one_after_conversation()` | 被单会话替代 |
| `PhaseGenerator._generate_foundation_setup_session()` | 被单会话替代 |

---

## 五、实施步骤（按优先级）

### Phase 1：产物格式+Prompt（1-2天）
1. 定义 `core_settings.json` / `character_reference_library.json` / `satisfaction_units.json` 格式
2. 编写 `creative_phase_one_prompts.py`（System Prompt + User Prompt）
3. 用测试创意跑通Prompt，验证输出质量

### Phase 2：单会话生成器（2-3天）
1. 实现 `CreativePhaseOneSession.generate()`
2. 实现 `PhaseOneParser`（JSON解析+字段验证+缺失补全）
3. 接入现有 `APIClient`，支持对话模式
4. 单测：验证单会话输出包含全部7个字段

### Phase 3：接入PhaseGenerator（1-2天）
1. 在 `PhaseGenerator.generate_phase_one_preparations()` 中新增分支
2. `use_single_session_mode=True` 时调用 `CreativePhaseOneSession`
3. `use_single_session_mode=False` 时保留传统模式（fallback）
4. 产物保存逻辑改造：保存统一 `core_settings.json` + 兼容旧格式

### Phase 4：起承转合→爽点单元制（1-2天）
1. 重写 `PlanningPrompts.overall_stage_plan`
2. 重写 `PhaseGenerator._generate_overall_planning` 中的阶段处理
3. 改造 `detailed_stage_plans` 子步骤（emotional_plan/event_decomposition... → 爽点事件清单）

### Phase 5：状态追踪（1天）
1. 实现 `StateTracker`
2. 细纲生成时注入当前状态
3. 每章生成后解析并更新状态

### Phase 6：联调+回退（1-2天）
1. 端到端测试：创意输入 → 一阶段产物 → 二阶段章节生成
2. 对比测试：单会话 vs 传统模式，产物丰富度对比
3. 如果单会话失败率>15%，回退到双会话模式（方案A→方案B）

---

## 六、关键设计决策

### Q1：单会话输出太长被截断怎么办？
A：分两次生成，但保持在同一个对话中：
- 第1轮：生成前4个字段（book_info + system + characters + reference_library）
- 第2轮：在同对话中继续生成后3个字段（worldbuilding + satisfaction_units + initial_state）
- 这样总调用次数=2，但上下文连贯

### Q2：如何确保产物质量？
A：三层校验：
1. **格式校验**：`PhaseOneParser` 检查必要字段，缺失则同对话补全
2. **内容校验**：检查角色是否有口头禅/外貌、单元是否有爽点清单
3. **一致性校验**：检查角色名在各字段中是否一致、状态是否冲突

### Q3：如何兼容现有项目？
A：双轨并行：
- 新增配置项 `use_single_session_mode: true/false`
- 默认对新项目启用单会话模式
- 现有项目继续用传统模式（通过检查点判断）
- 产物保存时同时输出新格式（`core_settings.json`）和兼容格式（旧的 `plan.json` + `worldview.json`...）

### Q4：模型选择？
A：单会话模式强制使用 **kimi**（256K上下文），因为：
- 输出量可能达到 12K-16K tokens
- 需要长上下文保持角色/设定一致性
- 豆包/其他模型作为 fallback

---

## 七、预期效果

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| 一阶段API调用 | 15+次 | 1-2次 |
| 一阶段耗时 | 15-20分钟 | 3-5分钟 |
| 产物丰富度 | 抽象框架 | 具象素材库 |
| 角色具象化 | name+traits | 外貌+口头禅+动作+表情 |
| 结构模型 | 起承转合 | 爽点单元制 |
| 状态追踪 | ❌ | ✅ |
| 参考库 | ❌ | ✅ |
| 细纲颗粒度 | 情绪标签 | 场景+对话+爽点+状态更新 |
