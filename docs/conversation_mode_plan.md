# 对话模式设定生成规划（DeepSeek 优化版）

> 分支：`feature/conversation-mode`  
> 目标：将小说创作流程从"表单配置+多轮串行生成"优化为"DeepSeek 式对话+单轮全设定生成"

---

## 一、当前流程的问题

```
用户填表单 → Phase One（5-10轮API）→ 世界观 → 角色 → 大纲 → 细纲
                ↓
            Phase Two（50-100轮API）→ 逐章生成
```

**痛点**：
- 用户需要填大量表单，门槛高
- Phase One 需要 5-10 轮 API 调用，耗时 10-30 分钟
- 每轮都有状态维护、上下文同步的复杂度
- 设定在不同轮次间可能出现不一致
- API 成本高（Kimi/Gemini 每轮 ¥0.5-2）

---

## 二、新流程设计

```
┌─────────────────────────────────────────────────────────────┐
│  第一步：对话式创意开发（DeepSeek Chat 模式）                  │
│  ─────────────────────────────────────────                   │
│  用户：我想写一个神豪文，主角靠打赏女配刷经验值                 │
│  AI：这个创意不错！我分析一下市场定位...                       │
│  用户：女主能不能加几个？                                      │
│  AI：可以，建议配置为...                                       │
│  ...多轮对话，直到用户满意...                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓ 用户点击"生成设定"
┌─────────────────────────────────────────────────────────────┐
│  第二步：单轮全设定生成（DeepSeek Flash，成本 ¥0.3）          │
│  ─────────────────────────────────────────                   │
│  一轮API调用，输出完整JSON：                                    │
│  ├── 世界观（5000字）                                         │
│  ├── 角色设定×10（15000字）                                   │
│  ├── 全书大纲 200章（30000字）                                │
│  ├── 分卷细纲（50000字）                                      │
│  └── 总计约 10万字 / 150K tokens                              │
│  耗时：30-60秒                                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  第三步：正文批量生成（DeepSeek Flash/Pro）                   │
│  ─────────────────────────────────────────                   │
│  按批次并行生成，每批 8-16 章                                   │
│  200章 × 2000字 ≈ 60万 tokens                                │
│  Flash 成本：¥1.2 / Pro 成本：¥15                            │
└─────────────────────────────────────────────────────────────┘
```

**总成本**：Flash 全本约 ¥1.5，Pro 全本约 ¥15。  
**总时间**：设定 30-60 秒 + 正文 10-20 分钟（并行）。

---

## 三、核心改进点

| 维度 | 旧流程 | 新流程 | 收益 |
|------|--------|--------|------|
| 用户输入 | 填表单 | 聊天对话 | 门槛大幅降低 |
| 设定生成 | 5-10 轮串行 | 1 轮输出 | 速度提升 10 倍 |
| 一致性 | 多轮可能矛盾 | 单轮全局可见 | 一致性 100% |
| 成本 | ¥5-20 | ¥0.3（设定） | 成本降低 90% |
| 可控性 | 中途难改 | 对话中随时调整 | 用户体验提升 |
| 代码复杂度 | 高（状态机+多轮会话） | 低（两轮调用） | 维护成本降低 |

---

## 四、架构设计

### 4.1 新增模块

```
feature/conversation-mode
├── src/core/conversation_mode/
│   ├── __init__.py
│   ├── creative_chat_session.py      # 对话式创意开发会话
│   ├── one_shot_setting_generator.py # 单轮全设定生成器
│   └── setting_validator.py          # 设定一致性校验器
├── src/prompts/ConversationPrompts.py # 对话模式专用提示词
├── web/api/conversation_api.py        # 对话模式API端点
└── web/templates/pages/v2/
    └── conversation-planning.html     # 对话式设定页面
```

### 4.2 核心类设计

#### `CreativeChatSession`
```python
class CreativeChatSession(ConversationSession):
    """对话式创意开发会话
    
    职责：
    1. 接收用户的原始创意输入
    2. 以对话形式引导用户完善创意（市场分析、题材定位、角色建议等）
    3. 维护对话历史，支持多轮追问
    4. 对话结束后，输出结构化的"创意简报"
    """
    
    def __init__(self, api_client):
        super().__init__(api_client)
        self.creative_brief = {}  # 创意简报
        
    def start_creative_chat(self, user_idea: str) -> str:
        """用户输入核心创意，AI 返回初步分析"""
        ...
        
    def continue_chat(self, user_message: str) -> str:
        """继续对话，用户可追问、修改、确认"""
        ...
        
    def finalize_brief(self) -> Dict:
        """对话结束，输出结构化创意简报"""
        ...
```

#### `OneShotSettingGenerator`
```python
class OneShotSettingGenerator:
    """单轮全设定生成器
    
    职责：
    1. 接收 CreativeChatSession 输出的创意简报
    2. 构建超大提示词（包含番茄小说平台规范、爽文写作公式等）
    3. 调用 DeepSeek API（1M 上下文，384K 输出）
    4. 一轮输出完整的项目设定 JSON
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        
    def generate_all_settings(self, creative_brief: Dict) -> Dict:
        """单轮生成所有设定"""
        prompt = self._build_mega_prompt(creative_brief)
        response = self.api_client.send_message(prompt, max_tokens=200000)
        return self._parse_settings(response)
        
    def _build_mega_prompt(self, brief: Dict) -> str:
        """构建超大提示词
        
        包含：
        - 平台规范（番茄小说黄金三章、爽点密度等）
        - 创意简报
        - 输出格式要求（JSON Schema）
        - 示例（few-shot）
        """
        ...
```

### 4.3 数据流

```
用户输入
  ↓
[Frontend] conversation-planning.html (聊天界面)
  ↓ POST /api/conversation/chat
[Backend] conversation_api.py
  ↓
[Core] CreativeChatSession (维护对话状态)
  ↓ 多轮对话...
用户点击"生成设定"
  ↓ POST /api/conversation/generate-settings
[Core] OneShotSettingGenerator
  ↓ 单轮 DeepSeek API 调用
完整设定 JSON
  ↓
保存为 project_info.json + chapters/ + 各设定文件
  ↓
进入正文生成
```

---

## 五、前端设计

### 5.1 页面布局

```
┌────────────────────────────────────────────────────┐
│  对话式设定生成                                      │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │ 🤖 AI                                        │  │
│  │ 这个创意很有潜力！让我分析一下市场定位...      │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │ 用户：女主能不能加几个？                       │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │ 🤖 AI                                        │  │
│  │ 建议配置 5 个女主，分别对应...                 │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ─────────────────────────────────────────────    │
│  [输入创意或追问...                    ] [发送]    │
│  [✨ 生成设定]  ← 用户满意后点击                    │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 5.2 复用已有组件

- **聊天 UI**：复用 `novelcraft.html` 的 `.ai-chat` 组件
- **流式输出**：复用 `/api/novelcraft/chat/stream` SSE 接口
- **模型选择**：复用已有模型选择器，默认 DeepSeek Flash

---

## 六、提示词设计

### 6.1 对话阶段提示词（`ConversationPrompts`）

```python
CREATIVE_CHAT_SYSTEM_PROMPT = """
你是一位资深网文编辑+市场分析师，专精于番茄小说平台。

你的任务：通过对话帮助用户将一个粗糙的创意，打磨成一个有市场潜力的网文方案。

对话原则：
1. 先肯定用户的创意，建立信心
2. 用提问引导用户补充关键信息（题材、主角、金手指、爽点）
3. 提供市场数据和同类爆款案例作为参考
4. 每轮对话结束时，给出 2-3 个明确的选项让用户选择
5. 不要一次性输出太多信息，保持对话节奏

你需要收集的信息清单：
- 核心创意（一句话概括）
- 题材类型（都市/玄幻/科幻等）
- 主角人设（年龄、身份、性格）
- 金手指/核心爽点机制
- 目标读者群体
- 预计篇幅（100章/200章/500章）
- 风格偏好（轻松搞笑/黑暗复仇/热血升级）
"""
```

### 6.2 单轮设定生成提示词（核心）

```python
ONE_SHOT_SETTING_PROMPT = """
你是一位顶级网文策划，专精于番茄小说平台的爽文设计。

【平台规范】（必须遵守）
- 黄金三章：第1章必须出系统/金手指，第2章必须有首次打脸/收获，第3章必须有升级/反转
- 爽点密度：每3-5章必须有一个小爽点，每15-20章必须有一个大爽点
- 压抑-爆发配对：每个爽点前必须有足够的压抑铺垫（被看不起、被欺负、困境）
- 收获具象化：每次爽点后主角必须有具体收获（钱/地位/能力/人脉/女人）

【用户创意简报】
{creative_brief}

【输出要求】
请输出一个完整的 JSON，包含以下字段：

{{
    "novel_title": "书名（15字以内，有吸引力）",
    "novel_synopsis": "简介（300字以内，包含核心卖点+主角+金手指+爽点）",
    "genre": "题材",
    "target_platform": "番茄小说",
    
    "worldview": {{
        "background": "世界背景",
        "rules": "核心规则",
        "power_system": "力量/财富体系"
    }},
    
    "characters": [
        {{
            "name": "角色名",
            "role": "主角/女主/反派/配角",
            "personality": "性格",
            "background": "背景",
            "motivation": "动机",
            "growth_arc": "成长弧线"
        }}
    ],
    
    "outline": {{
        "total_chapters": 200,
        "volumes": [
            {{
                "volume_name": "卷名",
                "chapters": "1-20",
                "core_conflict": "核心冲突",
                "climax_chapter": "高潮章节",
                "chapters_detail": [
                    {{
                        "chapter_number": 1,
                        "title": "章节标题",
                        "word_count_target": 2000,
                        "key_events": ["事件1", "事件2"],
                        "emotional_arc": "压抑→震惊→期待",
                        "payoff_type": "系统觉醒/首次打脸/收获奖励",
                        "suppression_setup": "压抑设计",
                        "payoff_design": "爽点设计",
                        "concrete_reward": "具体收获"
                    }}
                ]
            }}
        ]
    }}
}}

【重要】
- 大纲必须覆盖全部 {total_chapters} 章
- 每章必须有明确的 "payoff_type"（爽点类型）
- 压抑和爽点必须成对出现
- 主角不能有圣母行为，必须有仇必报
- 女性角色必须有独立动机，不能是工具人
"""
```

---

## 七、实现计划

### Phase 1：核心后端（2-3天）

- [ ] 新建 `src/core/conversation_mode/` 模块
- [ ] 实现 `CreativeChatSession`
- [ ] 实现 `OneShotSettingGenerator`
- [ ] 编写 `ConversationPrompts`
- [ ] 实现设定 JSON 解析和校验
- [ ] 编写单元测试

### Phase 2：API 层（1-2天）

- [ ] 新建 `web/api/conversation_api.py`
- [ ] 实现 `/api/conversation/chat`（流式）
- [ ] 实现 `/api/conversation/generate-settings`（单轮大输出）
- [ ] 实现 `/api/conversation/status`
- [ ] 集成到 Flask app

### Phase 3：前端页面（2-3天）

- [ ] 新建 `conversation-planning.html`
- [ ] 复用 NovelCraft 聊天组件
- [ ] 实现"生成设定"按钮和进度显示
- [ ] 设定结果预览和编辑
- [ ] 一键保存为项目

### Phase 4：集成与优化（2-3天）

- [ ] 对接现有 `NovelGenerator` 的正文生成流程
- [ ] 优化 DeepSeek 调用（缓存命中、重试策略）
- [ ] 错误处理和降级（输出超长时的分页策略）
- [ ] 性能测试（200章大纲生成耗时）

---

## 八、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| DeepSeek 输出被截断（>384K） | 设定不完整 | 分两层生成：先生成世界观+角色+卷级大纲，再逐卷生成细纲 |
| JSON 解析失败 | 系统崩溃 | 多层解析 fallback + 正则提取 |
| 大纲质量不如多轮生成 | 可读性差 | 增加 few-shot 示例 + 输出后人工校验 |
| 长上下文注意力衰减 | 后面章节质量差 | 使用 "卷级生成"：每卷单独调用，保持上下文聚焦 |
| DeepSeek API 不稳定 | 生成失败 | 本地缓存 + 自动重试 + 降级到 Kimi/Gemini |

---

## 九、关键决策

### 决策 1：单轮 vs 两轮设定生成？

**建议：两轮**
- 第 1 轮（Flash）：生成世界观 + 角色 + 4卷 × 20章的卷级大纲（约 5万字）
- 第 2 轮（4次并行 Flash）：每卷生成 50 章细纲（每次约 3万字）

原因：384K 输出上限虽然够，但质量上"聚焦 narrower 的上下文"效果更好。

### 决策 2：对话阶段用 Flash 还是 Pro？

**建议：对话用 Flash，生成设定用 Pro**
- 对话阶段：成本低，速度快，Flash 足够
- 设定生成：Pro 质量更高，但成本 ¥24/百万 vs Flash ¥2/百万
- 如果设定生成 150K tokens，Pro 成本 ¥3.6，Flash 成本 ¥0.3
- **折中方案**：先用 Flash 生成，不满意再用 Pro 重试

### 决策 3：是否保留旧流程？

**建议：保留**
- 旧流程（市场导向模式）作为"高级模式"
- 新流程（对话模式）作为"快速模式"
- 用户在首页选择："快速创作（对话模式）" vs "专业创作（市场导向）"

---

## 十、下一步行动

1. **确认本规划** → 开始 Phase 1 实现
2. **先写一个最小可行版本（MVP）**：
   - 一个命令行脚本，输入创意 → 调用 DeepSeek → 输出设定 JSON
   - 验证单轮生成的质量和可行性
3. **再集成到 Web 界面**

要我立即开始写 MVP 命令行脚本吗？
