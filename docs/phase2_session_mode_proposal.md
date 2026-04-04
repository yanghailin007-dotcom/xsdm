# 自由创意模式 Phase 2 会话化改造方案

> 状态：待实施（建议待 Phase 1 会话化效果验证后再启动）  
> 版本：v1.0  
> 背景：当前市场导向模式已成熟使用 `ConversationSession` 进行多轮对话批量生成，而自由创意模式 Phase 2 仍停留在单轮 one-shot 批量生成（`MediumEventBatchProcessor`，每批最多 3 章）。本方案旨在将自由创意模式 Phase 2 升级为会话化生成，以提升跨章连贯性、质量一致性和可恢复性。

---

## 一、现状与问题

### 1.1 两条 Phase 2 链路对比

| 维度 | 市场导向模式 | 自由创意模式（传统 Phase 2） |
|------|-------------|---------------------------|
| **生成入口** | `BatchChapterGenerator.generate_batch()` | `NovelGenerator.generate_chapters_batch()` |
| **会话机制** | ✅ `ConversationSession` 拼接 message history | ❌ `MultiChapterContentGenerator.generate()` 单轮 one-shot JSON |
| **批量大小** | 固定 **6 章/批** | `chapters_per_batch=3`，`MediumEventBatchProcessor` 2-3 章/次 |
| **上下文继承** | 同一 session 内逐章对话，自然继承前文 | 靠 prompt 里显式拼接 `consistency_guidance` + `previous_state` |
| **断点恢复** | 按 batch 恢复 | 按 batch 恢复，但 batch 内无法细粒度恢复 |
| **质量评估** | `ChapterQualityChecker` + 滑动窗口复盘 | `LayeredQualityAssessor` 单轮评估 |

### 1.2 核心问题

1. **无原生多轮上下文**：自由创意模式写第 3 章时，AI 并不“记得”第 1-2 章的对话细节，只能依赖人工压缩的 `consistency_guidance`，长 stage 越往后一致性越差。
2. **批量上限低**：`MediumEventBatchProcessor` 一次 API 调用最多塞 3 章正文进 JSON 返回，对于 200 章小说 API 调用次数较多。
3. **`StageWritingSession` 空置**：`src/core/session_mode/sessions/stage_writing_session.py` 已存在且 `SessionOrchestrator.run_phase_two_stage()` 有调用入口，但**未接入主流程**，目前的实现也只是 for 循环逐章独立调用，没有使用 `ConversationSession`。
4. **事件边界与 token 的矛盾**：若纯按重大事件拆分，可能遇到 8-10 章的跨度过长事件，导致对话上下文爆炸、注意力稀释；若纯固定 6 章，又可能在高潮处切断上下文。

---

## 二、方案目标

1. **会话化**：将自由创意 Phase 2 从 one-shot batch 升级为 `ConversationSession` 多轮对话生成。
2. **可控性**：单一会话的上下文长度必须有硬上限，避免 token 爆炸和质量衰减。
3. **剧情对齐**：批次拆分尽量落在重大事件边界或转折点，减少高潮处断章。
4. **最小侵入**：不删除原有传统链路，通过配置开关 `session_mode.phase2_enabled` 做双轨运行。
5. **复用现有资产**：复用 `SessionOrchestrator` 的检查点机制、`ConversationSession` 基础设施、以及市场导向模式的 prompt 构建经验。

---

## 三、推荐方案：固定 6 章硬上限 + 软对齐重大事件边界

### 3.1 拆分策略

```
规则：
1. 硬上限：1 个 ConversationSession 最多连续生成 6 章。
2. 软对齐：批次边界优先落在 medium event 的结束章（或 stage 内部转折点）。
3. 动态调整：
   - 当前事件剩 1-2 章     → 单独 1 个小 session
   - 当前事件跨 3-6 章     → 正好 1 个完整 session
   - 当前事件跨 7-12 章    → 拆成 6 + 剩余（或对齐内部转折点拆分）
   - 当前事件跨 >12 章     → 按 6 章等分，必要时强制截断
```

**示例**：

| Stage 内章节 | 事件分布 | 拆分结果 | 说明 |
|-------------|---------|---------|------|
| 1-6 | 事件A(1-3), 事件B(4-6) | **1-6** 一个 session | 正好 6 章，边界自然对齐 |
| 7-14 | 事件C(7-10), 事件D(11-14) | **7-10**, **11-14** | 按事件边界拆成 4+4 |
| 15-26 | 事件E(15-22), 事件F(23-26) | **15-20**, **21-26** | 事件E跨8章，拆6+2，20章处截断 |
| 27-30 | 事件G(27-30) | **27-30** 一个 session | 4 章，小于上限 |

### 3.2 为什么选 6 章？

- **市场导向模式已验证**：当前 `web/services/market_driven/config.py` 中 `chapters_per_batch = 6`，且运行稳定。
- **Kimi 256K 上下文甜蜜点**：`system_prompt (~2K)` + `6 章 × (prompt ~500字 + 正文 ~2500字)` ≈ 18-20K 输入，到第 6 轮时总上下文约 20-25K，仍在舒适区。
- **注意力与成本平衡**：超过 6 章后，模型对早期章节的细节记忆开始衰减，且每轮输入 token 线性增长，成本上升。

---

## 四、架构设计

### 4.1 模块职责

```
┌─────────────────────────────────────────────────────────────┐
│  NovelGenerator.phase_two_generation()                      │
│  （路由层：检测 session_mode.phase2_enabled 开关）           │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │ 开关关闭                    │ 开关打开
         ▼                           ▼
┌─────────────────┐    ┌──────────────────────────────────────┐
│ 传统链路         │    │ SessionOrchestrator                  │
│ generate_chapters_batch() │    │ .run_phase_two_stage(stage_num)     │
└─────────────────┘    └──────────────────────────────────────┘
                                    │
                                    ▼
                       ┌──────────────────────────────┐
                       │ StageWritingSession          │
                       │ （stage 级协调器）            │
                       └──────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
   │ _split_stage_   │  │ _execute_sub_   │  │ _execute_sub_   │
   │ into_batches()  │  │ batch_conversa- │  │ batch_conversa- │
   │                 │  │ tion(batch_2)   │  │ tion(batch_n)   │
   │ 返回:           │  │                 │  │                 │
   │ [(1,6),(7,12)]  │  │ 创建 Conver-    │  │ 创建 Conver-    │
   │                 │  │ sationSession   │  │ sationSession   │
   └─────────────────┘  │ for ch in batch:│  │ for ch in batch:│
                        │   session.send  │  │   session.send  │
                        │   _message(...) │  │   _message(...) │
                        └─────────────────┘  └─────────────────┘
                                    │
                                    ▼
                       ┌──────────────────────────────┐
                       │ _execute_stage_summary()     │
                       │ 生成 stage summary，写入     │
                       │ context_briefs 供下游使用    │
                       └──────────────────────────────┘
```

### 4.2 新增/改造模块清单

| 模块 | 动作 | 说明 |
|------|------|------|
| `StageWritingSession` | **改造** | 新增 `_split_stage_into_batches()` 和 `_execute_sub_batch_conversation()` |
| `SessionOrchestrator.run_phase_two_stage()` | **改造** | 补齐桥接逻辑：把 session 产物同步回 `novel_data`、触发进度回调、保存单章文件 |
| `NovelGenerator.phase_two_generation()` | **新增分支** | 检测 `session_mode.phase2_enabled`，为 true 时走 session 链路 |
| `Phase2WritingPromptBuilder`（新建） | **新建** | 从自由创意的 `stage_writing_plans` + `medium_event` + `writing_style_guide` 组装 system_prompt 和 chapter_prompt |
| `config.py` | **新增配置项** | `session_mode.phase2_enabled`、可选 `phase2_batch_size`（默认 6） |

---

## 五、关键改造点详细说明

### 5.1 路由入口：`NovelGenerator.phase_two_generation()`

```python
# 伪代码，供后续参考

def phase_two_generation(self, novel_title, from_chapter, chapters_to_generate, ...):
    end_chapter = from_chapter + chapters_to_generate - 1
    
    # 新增：Session Mode 开关
    session_mode_cfg = self.config.get("session_mode", {})
    if session_mode_cfg.get("phase2_enabled", False):
        return self._phase_two_generation_session_mode(
            novel_title, from_chapter, end_chapter
        )
    
    # 原有传统逻辑
    return self.generate_chapters_batch(from_chapter, end_chapter)
```

### 5.2 `StageWritingSession` 核心改造

```python
class StageWritingSession(NovelGenerationSession):
    STEPS = ["stage_outline", "chapter_writing", "stage_summary"]
    BATCH_SIZE = 6  # 硬上限

    def __init__(self, *args, stage_number=1, medium_events=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_number = stage_number
        self.medium_events = medium_events or []
        self.generated_chapters = {}
        self.stage_summary_text = ""
        self.prompt_builder = Phase2WritingPromptBuilder(
            self.novel_data, self.stage_number
        )

    def _split_stage_into_batches(self) -> List[Tuple[int, int]]:
        """
        按 medium event 边界 + BATCH_SIZE 硬上限拆分。
        算法思路（可用贪心实现）：
        1. 获取本 stage 的所有章节范围 [stage_start, stage_end]。
        2. 按 medium event 的结束章排序，得到候选断点。
        3. 从左到右，每次尽量取到下一个 event 边界；
           若到边界会超过 BATCH_SIZE，则提前在 BATCH_SIZE 处截断。
        """
        # 具体实现参考下方伪代码
        ...

    def _execute_chapter_writing(self, outline: Dict) -> bool:
        """改造为 sub-batch 级 conversation 生成"""
        batches = self._split_stage_into_batches()
        
        for start_ch, end_ch in batches:
            if not self._execute_sub_batch_conversation(start_ch, end_ch, outline):
                return False
        return True

    def _execute_sub_batch_conversation(
        self, start_ch: int, end_ch: int, outline: Dict
    ) -> bool:
        from src.core.APIClient import ConversationSession
        
        system_prompt = self.prompt_builder.build_system_prompt(start_ch)
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=self.api_client.default_provider,
            purpose_prefix=f"StageWriting-{self.stage_number}"
        )
        session.max_history = 50  # 保留足够历史
        
        prev_summary = self._get_prev_summary(start_ch)
        
        for ch_num in range(start_ch, end_ch + 1):
            chapter_plan = self._get_chapter_plan(ch_num, outline)
            emotion_beat = self._get_emotion_beat(ch_num)
            
            prompt = self.prompt_builder.build_chapter_prompt(
                chapter_num=ch_num,
                chapter_plan=chapter_plan,
                emotion_beat=emotion_beat,
                prev_summary=prev_summary
            )
            
            content = session.send_message(prompt, purpose=f"chapter_{ch_num}")
            if not content:
                return False
            
            # 解析 content（正文 + 标题）
            parsed = self._parse_chapter_response(content, ch_num)
            self.generated_chapters[ch_num] = parsed
            
            # 更新 prev_summary 供下一章使用
            prev_summary = self._summarize_chapter(parsed)
            
            # 🔥 关键：每章落盘，防止 batch 中间失败全部丢失
            self._save_chapter_to_disk(parsed)
        
        return True
```

### 5.3 `SessionOrchestrator.run_phase_two_stage()` 桥接层

```python
def run_phase_two_stage(self, stage_number: int) -> bool:
    from src.core.session_mode.sessions.stage_writing_session import StageWritingSession
    
    briefs = [
        self.context_briefs.get('foundation', ''),
        self.context_briefs.get('character', ''),
        self.context_briefs.get('structure', ''),
    ]
    prev_summary = self.context_briefs.get(f'stage_{stage_number - 1}_summary', "")
    if prev_summary:
        briefs.append(prev_summary)
    
    # 提取本 stage 的 medium_events
    medium_events = self._get_stage_medium_events(stage_number)
    
    session = StageWritingSession(
        api_client=self.generator.api_client,
        domain="writing",
        context_briefs=briefs,
        novel_data=self.generator.novel_data,
        stage_number=stage_number,
        medium_events=medium_events,
    )
    
    success = session.execute_all_steps()
    if not success:
        return False
    
    # ===== 桥接：同步回传统数据结构 =====
    for ch_num, ch_data in session.get_generated_chapters().items():
        # 1. 写入 novel_data
        self.generator.novel_data["generated_chapters"][str(ch_num)] = ch_data
        
        # 2. 触发事件总线（现有 UI/保存监听）
        self.generator.event_bus.publish('chapter.generated', {
            'chapter_number': ch_num,
            'result': ch_data,
            'context': {}  # 可扩展
        })
        
        # 3. 进度回调（Web UI 实时进度）
        if hasattr(self.generator, '_phase_two_progress_callback') and callable(...):
            self.generator._phase_two_progress_callback(
                ch_num, "completed",
                {"status": "completed", "chapter_title": ch_data.get('chapter_title'), "word_count": ch_data.get('word_count')}
            )
        
        # 4. 持久化单章文件
        self._persist_chapter(ch_num, ch_data)
    
    # 保存 stage summary 到 context_briefs
    self.context_briefs[f'stage_{stage_number}_summary'] = session.get_stage_summary()
    self._save_checkpoint()
    return True
```

### 5.4 Prompt Builder 设计思路

`Phase2WritingPromptBuilder` 需要把自由创意模式现有的数据源映射到对话 prompt：

| Prompt 部分 | 数据源 |
|------------|--------|
| **System Prompt** | `writing_style_guide`（核心风格、核心原则） + `core_worldview`（世界观约束） + `character_design`（角色设定，尤其是主角名锁定） |
| **Chapter Prompt** | `stage_writing_plans`（本章细纲） + `medium_event`（当前事件信息） + `EventDrivenManager.get_context(chapter_num)`（事件上下文） + `ExpectationManager.pre_generation_check()`（期待感约束） + `GlobalGrowthPlanner.get_context()`（成长上下文） + `prev_summary`（上一章摘要） |

可借鉴 `web/services/market_driven/chapter_conversation_generator.py` 中的 `_build_system_prompt()` 和 `_build_chapter_prompt()` 逻辑，但数据源换成自由创意的结构。

---

## 六、检查点与恢复策略

### 6.1 分层检查点

| 层级 | 粒度 | 保存内容 | 恢复动作 |
|------|------|---------|---------|
| **Orchestrator 层** | Stage 级 | `context_briefs` + `stage_{N}_summary` | 跳过已完成的 stage |
| **Session 层** | Sub-batch 级 | batch 结束后的 `generated_chapters` + `prev_summary` | 从本 stage 未完成的 batch 开始 |
| **Disk 层** | 单章级 | 每章生成后立即写 `.json` 文件 | 加载已存在的章节，跳过生成 |

### 6.2 恢复流程

```
1. 启动时检查 checkpoint
2. 若 stage_{k}_summary 存在 → stage k 已完成，从 stage k+1 开始
3. 若 stage_{k} 部分完成 → 加载已生成的单章文件，定位到第一个缺失的章节号
4. 以该章节号作为新 batch 的起点，创建新的 ConversationSession 继续生成
```

**注意**：由于 `ConversationSession` 的 message history 无法跨运行持久化，恢复时必须**新建 session**，并用 `prev_summary` + 最近 1-2 章的完整内容作为 `system_prompt` 或首条 user message 注入，以快速重建上下文。

---

## 七、风险评估与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| **Token 超限** | 单 session 生成 6 章时，若某章正文过长（>3500字），上下文膨胀导致 API 报错 | 增加输入 token 预估算；超长时自动拆小 batch（从 6 降 4 或 3） |
| **上下文丢失** | 按 batch 拆分时，batch 2 对 batch 1 的细节记忆减弱 | 在 system_prompt 中显式注入「前 batch 摘要 + 关键状态」；使用 `StageWritingSession` 的 `stage_summary` 作为跨 batch 桥梁 |
| **质量评估不兼容** | 现有 `LayeredQualityAssessor` 评估的是一次性 JSON 多章输出，对对话生成的单章可能需要调整评估 prompt | 复用市场导向的 `ChapterQualityChecker` 做逐章质检；或保持现有 assessor 但改为对 batch 内所有章一起评估 |
| **配置开关遗漏** | 某些入口（如命令行、续写）未走 `phase_two_generation()` 路由，导致 session 模式未生效 | 统一所有 Phase 2 入口到 `NovelGenerator.phase_two_generation()` 或 `PhaseGenerator.generate_phase_two()` |
| **Prompt Builder 覆盖不全** | 自由创意的 `stage_writing_plans` 结构与市场的 `blueprint` 差异大，prompt 可能遗漏关键约束 | 先用 1 本完整小说走通全流程，对比传统输出与会话输出，补齐缺失字段 |

---

## 八、验收标准

1. **功能**：开启 `session_mode.phase2_enabled` 后，自由创意模式 Phase 2 能正常生成完整小说，章节文件正常落盘。
2. **连贯性**：同 batch 内章节无明显人设/剧情/时间线断裂；跨 batch 的主角姓名、修为、关键物品保持一致。
3. **性能**：单 session 内生成 6 章时，API 无 413/414 token 超限错误；单章平均生成时间与传统模式持平或更优。
4. **恢复**：在 batch 中间中断（如第 3/6 章后 kill 进程），重启后能从第 4 章继续，不重复生成 1-3 章。
5. **回退**：关闭 `session_mode.phase2_enabled` 后，系统能 100% 回到现有传统链路运行。

---

## 九、实施建议（优先级排序）

1. **P0 - 等待前置条件**
   - Phase 1 会话化（`FoundationSession`、`CharacterSession`、`StructureSession`）稳定运行至少 2-3 本完整小说。
   - 确认 `SessionOrchestrator` 的检查点/恢复机制无 bug。

2. **P1 - 基础设施**
   - 新建 `Phase2WritingPromptBuilder`，先让 prompt 输出与市场导向模式的质量对齐。
   - 改造 `StageWritingSession` 的 `_split_stage_into_batches()` 和 `_execute_sub_batch_conversation()`。

3. **P2 - 接入主流程**
   - 在 `NovelGenerator.phase_two_generation()` 增加 `session_mode.phase2_enabled` 分支。
   - 补齐 `SessionOrchestrator.run_phase_two_stage()` 的桥接层。

4. **P3 - 验收与打磨**
   - 用 1 本 50 章 + 1 本 200 章小说做端到端测试，重点观察跨 batch 一致性和断点恢复。
   - 根据测试结果调整 `BATCH_SIZE`（6 章为初始值，可据模型表现上调或下调）。

---

## 十、参考文件索引

| 文件 | 作用 |
|------|------|
| `src/core/session_mode/sessions/stage_writing_session.py` | 主要改造对象 |
| `src/core/session_mode/session_orchestrator.py` | `run_phase_two_stage()` 桥接层 |
| `src/core/NovelGenerator.py` | Phase 2 路由入口 `phase_two_generation()` |
| `src/core/PhaseGenerator.py` | 备用路由入口 `generate_phase_two()` |
| `src/core/APIClient.py` | `ConversationSession` 基础设施 |
| `web/services/market_driven/chapter_conversation_generator.py` | 市场导向会话生成参考实现 |
| `web/services/market_driven/config.py` | `chapters_per_batch = 6` 参考配置 |
| `src/core/batch_generation/processor.py` | 现有传统 batch 链路（用于对比） |
