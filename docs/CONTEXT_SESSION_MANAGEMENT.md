# 会话管理与上下文延续实用方案

## 核心问题

### 当前痛点
1. 生成第20章后，会话满了，切换新会话后不知道第20章发生了啥
2. 主角明明已经"炼气期三层"了，新会话还以为他是"炼气期一层"
3. 伏笔埋了没回收，剧情不连贯

### 解决思路
**不是重新生成一阶段产物，而是更新"动态状态"**

```
一阶段产物（静态） + 动态状态快照（每章更新） = 完整上下文
```

---

## 一、数据分层

### Layer 1: 静态产物（一阶段生成，不变）
```python
STATIC_PRODUCTS = {
    "writing_style_guide": {...},      # 写作风格
    "core_worldview": {...},           # 世界观设定
    "character_design": {...},         # 角色初始设定
    "faction_system": {...},           # 势力系统
    "global_growth_plan": {...},       # 升级路线
    "stage_writing_plans": [...],      # 阶段规划
}
```

### Layer 2: 动态状态（每章更新）
```python
DYNAMIC_STATE = {
    "current_chapter": 25,              # 当前章节
    "current_stage": "第一阶段",        # 当前阶段
    
    "protagonist_state": {              # 主角当前状态（关键！）
        "name": "李明",
        "cultivation_level": "炼气期三层",  # 会变化
        "current_wealth": 5000000,      # 当前财富（会变化）
        "inventory": ["神秘戒指", "功法A"],  # 持有物品
        "relationships": {              # 人际关系（会变化）
            "张三": "敌对",
            "王五": "盟友"
        },
        "current_location": "东海市",   # 当前位置
        "emotional_state": "愤怒"       # 当前情绪
    },
    
    "important_npcs_state": {           # 重要NPC状态
        "张三": {"status": "被击败", "location": "医院"},
        "女主": {"status": "好感度60", "location": "学校"}
    },
    
    "world_events": [                   # 已发生的世界事件
        {"chapter": 5, "event": "拍卖会结束", "impact": "主角获得第一桶金"},
        {"chapter": 12, "event": "身份暴露", "impact": "全城震惊"},
        {"chapter": 20, "event": "击败张三", "impact": "获得张三的所有资产"}
    ],
    
    "active_quests": [                  # 进行中的任务
        {"name": "全国大赛", "progress": "30%", "deadline_chapter": 50},
        {"name": "寻找神秘老者", "progress": "10%", "hint": "老者最后出现在京城"}
    ],
    
    "pending_hints": [                  # 待回收伏笔
        {"hint": "玉佩的秘密", "planted_chapter": 3, "expected_resolve": 30},
        {"hint": "神秘老者身份", "planted_chapter": 15, "expected_resolve": 40}
    ],
    
    "recent_summaries": [               # 最近N章摘要（用于快速回忆）
        {"chapter": 23, "summary": "主角突破到炼气期三层..."},
        {"chapter": 24, "summary": "主角在拍卖会获得神秘功法..."},
        {"chapter": 25, "summary": "主角击败张三，获得其资产..."}
    ]
}
```

---

## 二、状态存储方案

### 存储位置
```
小说项目/
└── {novel_title}/
    ├── phase_one_products.json       # 静态产物
    ├── dynamic_state.json            # 动态状态（每章更新）
    ├── chapters/
    │   ├── chapter_001.json          # 章节内容+该章状态快照
    │   ├── chapter_002.json
    │   └── ...
    └── session_contexts/             # 会话上下文历史
        ├── session_001_summary.json
        └── session_002_summary.json
```

### 每章保存的内容
```json
{
  "chapter_number": 25,
  "title": "第25章 击败张三",
  "content": "正文...",
  "word_count": 2500,
  
  // 该章结束后的状态快照
  "state_snapshot": {
    "protagonist_state": {...},
    "world_events": [...],
    "active_quests": [...]
  },
  
  // 该章摘要
  "summary": "主角突破后实力大增，在商会冲突中击败张三...",
  
  // 该章关键变化
  "key_changes": [
    "主角突破到炼气期三层",
    "张三被击败，资产被主角接收",
    "主角与李家的关系恶化"
  ]
}
```

---

## 三、会话切换机制

### 触发条件
```python
def should_switch_session(current_session) -> bool:
    """判断是否需要切换会话"""
    # 1. Token数超过阈值
    if current_session.token_count > 120000:
        return True
    
    # 2. 对话轮数过多
    if current_session.message_count > 20:
        return True
    
    # 3. 上下文质量下降（通过评估响应质量）
    if current_session.quality_score < 6.0:
        return True
    
    return False
```

### 切换流程
```python
async def switch_session(novel_title: str, next_chapter: int):
    """执行会话切换"""
    
    # 1. 加载静态产物
    static_products = load_json(f"{novel_title}/phase_one_products.json")
    
    # 2. 加载最新动态状态
    dynamic_state = load_json(f"{novel_title}/dynamic_state.json")
    
    # 3. 构建新会话的System Prompt
    system_prompt = build_system_prompt(static_products, dynamic_state)
    
    # 4. 创建新会话
    new_session = api_client.create_conversation(
        system_prompt=system_prompt,
        provider="kimi"
    )
    
    # 5. 可选：添加最近2-3章的完整内容作为示例
    recent_chapters = load_recent_chapters(novel_title, count=3)
    for chapter in recent_chapters:
        new_session.messages.append({
            "role": "user", 
            "content": f"请按同样风格生成第{chapter['chapter_number']}章"
        })
        new_session.messages.append({
            "role": "assistant", 
            "content": chapter['content']
        })
    
    return new_session
```

### System Prompt 构建
```python
def build_system_prompt(static_products, dynamic_state) -> str:
    """构建包含完整上下文的System Prompt"""
    
    prompt = f"""【你是一个专业小说作家，正在创作长篇小说】

=== 静态设定（始终遵循）===
【写作风格】
{format_style_guide(static_products['writing_style_guide'])}

【世界观】
{format_worldview(static_products['core_worldview'])}

【势力系统】
{format_factions(static_products['faction_system'])}

【角色初始设定】
{format_characters(static_products['character_design'])}

=== 动态状态（当前情况）===
【当前章节】第{dynamic_state['current_chapter']}章
【当前阶段】{dynamic_state['current_stage']}

【主角当前状态】
- 姓名：{dynamic_state['protagonist_state']['name']}
- 实力：{dynamic_state['protagonist_state']['cultivation_level']}
- 财富：{dynamic_state['protagonist_state']['current_wealth']}
- 位置：{dynamic_state['protagonist_state']['current_location']}
- 情绪：{dynamic_state['protagonist_state']['emotional_state']}
- 持有物品：{', '.join(dynamic_state['protagonist_state']['inventory'])}

【重要NPC状态】
{format_npc_states(dynamic_state['important_npcs_state'])}

【已发生的重要事件】（按时间顺序）
{format_world_events(dynamic_state['world_events'])}

【进行中的任务】
{format_quests(dynamic_state['active_quests'])}

【待回收伏笔】
{format_hints(dynamic_state['pending_hints'])}

【最近3章摘要】
{format_recent_summaries(dynamic_state['recent_summaries'])}

=== 生成规则 ===
1. 严格遵循静态设定中的写作风格
2. 主角状态必须从"当前状态"开始，不能倒退
3. 必须推进"进行中的任务"
4. 适时回收"待回收伏笔"（如果到预期章节了）
5. 每章结束后更新主角状态

=== 输出格式 ===
请以JSON格式返回：
{{
  "chapter_title": "第X章 标题",
  "content": "正文内容（2500字左右）",
  "state_changes": {{
    "protagonist_updates": {{...}},  // 主角状态变化
    "new_events": [...],             // 新增事件
    "quest_progress": [...],         // 任务进度更新
    "hints_resolved": [...],         // 已回收伏笔
    "new_hints": [...]               // 新埋伏笔
  }},
  "summary": "本章摘要（200字）"
}}"""
    
    return prompt
```

---

## 四、状态更新机制

### 每章生成后更新
```python
async def update_dynamic_state(chapter_data: Dict, dynamic_state: Dict) -> Dict:
    """根据新生成的章节更新动态状态"""
    
    state_changes = chapter_data.get('state_changes', {})
    
    # 1. 更新主角状态
    if 'protagonist_updates' in state_changes:
        dynamic_state['protagonist_state'].update(state_changes['protagonist_updates'])
    
    # 2. 添加新事件
    if 'new_events' in state_changes:
        for event in state_changes['new_events']:
            dynamic_state['world_events'].append({
                "chapter": chapter_data['chapter_number'],
                "event": event['name'],
                "impact": event['impact']
            })
    
    # 3. 更新任务进度
    if 'quest_progress' in state_changes:
        for quest_update in state_changes['quest_progress']:
            for quest in dynamic_state['active_quests']:
                if quest['name'] == quest_update['name']:
                    quest['progress'] = quest_update['progress']
                    if quest_update.get('completed'):
                        quest['status'] = 'completed'
    
    # 4. 回收伏笔
    if 'hints_resolved' in state_changes:
        for resolved in state_changes['hints_resolved']:
            dynamic_state['pending_hints'] = [
                h for h in dynamic_state['pending_hints'] 
                if h['hint'] != resolved
            ]
    
    # 5. 添加新伏笔
    if 'new_hints' in state_changes:
        for new_hint in state_changes['new_hints']:
            dynamic_state['pending_hints'].append({
                "hint": new_hint['name'],
                "planted_chapter": chapter_data['chapter_number'],
                "expected_resolve": chapter_data['chapter_number'] + new_hint.get('delay', 20)
            })
    
    # 6. 更新最近摘要
    dynamic_state['recent_summaries'].append({
        "chapter": chapter_data['chapter_number'],
        "summary": chapter_data['summary']
    })
    # 只保留最近10章
    dynamic_state['recent_summaries'] = dynamic_state['recent_summaries'][-10:]
    
    # 7. 更新当前章节
    dynamic_state['current_chapter'] = chapter_data['chapter_number']
    
    return dynamic_state
```

---

## 五、具体实施步骤

### Step 1: 修改章节生成返回格式
要求AI返回结构化JSON，包含 `state_changes` 字段

### Step 2: 实现状态管理器
```python
class NovelStateManager:
    def __init__(self, novel_title: str):
        self.novel_title = novel_title
        self.static_products = None
        self.dynamic_state = None
        self.current_session = None
    
    def load_products(self):
        """加载一阶段产物"""
        pass
    
    def load_or_init_state(self):
        """加载或初始化动态状态"""
        pass
    
    def update_state(self, chapter_data):
        """更新状态"""
        pass
    
    def build_system_prompt(self) -> str:
        """构建System Prompt"""
        pass
    
    def should_switch_session(self) -> bool:
        """判断是否需要切换会话"""
        pass
    
    def switch_session(self):
        """执行会话切换"""
        pass
```

### Step 3: 修改批量章节生成器
集成 `NovelStateManager`，在每章生成后更新状态

### Step 4: 添加状态持久化
确保状态实时保存到文件，防止程序崩溃丢失

---

## 六、关键改进点

| 方面 | 旧方案 | 新方案 |
|------|--------|--------|
| 会话切换 | 丢失上下文，从头开始 | 携带完整状态，无缝衔接 |
| 主角状态 | 靠AI回忆，容易出错 | 结构化记录，精确更新 |
| 伏笔回收 | 容易遗漏 | 系统追踪，到期提醒 |
| 任务进度 | 散落在正文中 | 结构化记录，随时查看 |
| NPC关系 | 靠AI记忆 | 状态化记录，不会矛盾 |

这个方案的核心是：**把AI应该记住的东西，变成结构化数据来管理**。

需要我先实现 `NovelStateManager` 类吗？
