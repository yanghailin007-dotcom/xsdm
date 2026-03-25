# 小说生成上下文管理设计方案

## 1. 问题分析

### 当前问题
- API返回纯文本，缺乏结构化（标题、内容、状态分离）
- 长文本生成容易超出上下文窗口（Kimi k2.5 支持 256K tokens，但生成质量会下降）
- 会话切换时上下文丢失，导致剧情不连贯

### 核心需求
1. **结构化返回**：章节标题、正文、关键状态快照
2. **上下文压缩**：会话满了后智能总结，保留关键信息
3. **状态连续性**：人物状态、剧情进度、伏笔回收等不丢失

---

## 2. 数据结构设计

### 2.1 章节生成返回格式

```json
{
  "chapter_title": "第X章 具体标题",
  "content": "章节正文内容...",
  "word_count": 2500,
  "character_states": {
    "主角": {
      "情绪": "愤怒/兴奋/冷静",
      "实力等级": "炼气期三层",
      "持有物品": ["神秘戒指", "100万现金"],
      "人际关系变化": {
        "反派A": "敌对→被击杀",
        "女主": "陌生→产生好感"
      }
    }
  },
  "world_states": {
    "当前地点": "东海市→京城",
    "时间线": "第3天晚上",
    "重大事件": ["拍卖会结束", "身份暴露"]
  },
  "plot_progress": {
    "本阶段进度": "30%",
    "已完成": ["获得系统", "第一次打脸"],
    "待完成": ["全国大赛", "终极BOSS战"],
    "已埋伏笔": ["神秘老者出现", "玉佩的秘密"]
  },
  "next_chapter_hook": "章尾悬念/期待点",
  "summary_for_context": "本章核心内容摘要（200字以内，用于上下文压缩）"
}
```

### 2.2 上下文状态快照（ContextSnapshot）

```python
@dataclass
class ContextSnapshot:
    """人生状态快照 - 用于会话切换时恢复上下文"""
    
    # 基础信息
    novel_id: str
    current_chapter: int
    total_chapters: int
    
    # 人物状态（核心）
    protagonist_state: Dict[str, Any]  # 主角当前状态
    important_characters: Dict[str, Dict]  # 重要配角状态
    
    # 世界状态
    current_location: str
    current_time: str
    world_events: List[str]  # 已发生的重大事件
    
    # 剧情状态
    current_arc: str  # 当前剧情阶段
    arc_progress: float  # 阶段进度 0-100
    active_quests: List[str]  # 进行中的任务/目标
    pending_hints: List[str]  # 待回收的伏笔
    
    # 历史摘要（压缩后）
    chapter_summaries: List[str]  # 每章摘要，最近N章
    key_moments: List[str]  # 关键时刻（跨章节的）
    
    # 会话信息
    created_at: str
    session_token_count: int  # 当前会话token数
```

---

## 3. 上下文压缩策略

### 3.1 三级压缩机制

```
Level 1: 完整历史（前10章）
  └─> 保留完整对话，用于近期上下文

Level 2: 摘要历史（11-30章）  
  └─> 每章压缩为200字摘要

Level 3: 关键时刻（31章以前）
  └─> 只保留关键节点（升级、身份变化、重大事件）
```

### 3.2 压缩触发条件

```python
class ContextCompressor:
    """上下文压缩器"""
    
    def should_compress(self, messages: List[Dict], token_count: int) -> bool:
        """判断是否需要压缩"""
        # 策略1: Token数超过阈值（如 100K）
        if token_count > 100000:
            return True
            
        # 策略2: 章节数超过阈值（如 15章）
        chapter_count = self._count_chapters(messages)
        if chapter_count > 15:
            return True
            
        # 策略3: 对话轮数过多
        if len(messages) > 30:
            return True
            
        return False
    
    def compress(self, messages: List[Dict], snapshot: ContextSnapshot) -> List[Dict]:
        """执行压缩"""
        # 1. 分离system prompt
        system_msg = messages[0]  # 保留
        
        # 2. 分离最近N章（完整保留）
        recent_messages = messages[-10:]  # 最近10条
        
        # 3. 中间部分生成摘要
        middle_messages = messages[1:-10]
        summary = self._generate_summary(middle_messages, snapshot)
        
        # 4. 构建新的消息列表
        return [
            system_msg,
            {"role": "user", "content": f"【前文摘要】{summary}"},
            {"role": "assistant", "content": "已了解前文内容。"},
            *recent_messages
        ]
```

### 3.3 摘要生成Prompt

```python
SUMMARY_PROMPT = """请对以下小说章节内容进行摘要，用于后续生成时恢复上下文：

【需要摘要的内容】
{chapter_contents}

【当前人物状态】
{character_states}

请输出结构化摘要：
1. 剧情进展：本阶段完成了哪些重要事件
2. 人物变化：主角和重要配角的状态变化
3. 待回收伏笔：哪些悬念还未解决
4. 下一章预期：基于当前状态，读者期待什么

限制在500字以内，确保关键信息不丢失。"""
```

---

## 4. 会话切换流程

### 4.1 检测与切换

```python
class ConversationManager:
    """对话管理器 - 管理多个会话的切换"""
    
    def __init__(self, api_client, max_tokens_per_session=150000):
        self.api_client = api_client
        self.max_tokens = max_tokens_per_session
        self.current_session = None
        self.snapshot = None
        self.session_count = 0
    
    async def generate_chapter(self, chapter_num: int, context: Dict) -> ChapterData:
        """生成单章 - 自动处理会话切换"""
        
        # 1. 检查当前会话是否需要切换
        if self.current_session and self._should_switch_session():
            await self._switch_session()
        
        # 2. 确保会话存在
        if not self.current_session:
            self.current_session = self._create_new_session()
        
        # 3. 生成章节
        response = await self._generate_with_context(chapter_num, context)
        
        # 4. 解析结构化数据
        chapter_data = self._parse_response(response)
        
        # 5. 更新状态快照
        self._update_snapshot(chapter_data)
        
        # 6. 保存章节
        await self._save_chapter(chapter_data)
        
        return chapter_data
    
    def _should_switch_session(self) -> bool:
        """判断是否需要切换会话"""
        # 检查token数
        token_count = self.current_session.estimate_token_count()
        return token_count > self.max_tokens
    
    async def _switch_session(self):
        """执行会话切换"""
        logger.info("【会话切换】上下文即将满载，生成摘要并创建新会话...")
        
        # 1. 生成当前会话的摘要
        session_summary = await self._generate_session_summary()
        
        # 2. 保存快照
        self.snapshot.session_summaries.append(session_summary)
        
        # 3. 创建新会话，携带压缩后的上下文
        self.current_session = self._create_new_session(
            compressed_context=self._build_compressed_context()
        )
        
        self.session_count += 1
        logger.info(f"【会话切换】新会话 #{self.session_count} 已创建")
```

---

## 5. 实施步骤

### Phase 1: 结构化返回（当前最紧急）

1. 修改章节生成Prompt，要求JSON格式返回
2. 更新 `_call_ai_generation` 解析JSON
3. 更新章节数据结构，包含 `character_states` 等字段

### Phase 2: 状态快照

1. 实现 `ContextSnapshot` 类
2. 在章节生成后自动提取状态
3. 保存状态到文件/数据库

### Phase 3: 上下文压缩

1. 实现 `ContextCompressor` 类
2. 集成到 `ConversationSession`
3. 添加摘要生成逻辑

### Phase 4: 会话管理

1. 实现 `ConversationManager` 类
2. 自动检测会话满载
3. 无缝切换会话

---

## 6. Prompt 模板

### 6.1 章节生成Prompt（结构化）

```python
CHAPTER_GENERATION_PROMPT = """【系统】
你是专业小说作家。请基于以下信息生成第{chapter_num}章。

【人物状态快照】
{character_states}

【世界状态】
{world_states}

【本章规划】
{chapter_plan}

【前文摘要】（最近3章）
{recent_summaries}

【输出要求】
请以JSON格式返回，包含以下字段：
{{
  "chapter_title": "第X章 具体标题",
  "content": "章节正文（2500字左右）",
  "character_states": {{
    "主角": {{"情绪": "...", "实力": "...", "物品": []}},
    "其他重要人物": {{...}}
  }},
  "world_states": {{"地点": "...", "时间": "...", "事件": []}},
  "plot_progress": {{"本阶段": "...", "进度": "...%"}},
  "next_chapter_hook": "章尾悬念",
  "summary_for_context": "本章摘要（200字）"
}}

注意：
1. content字段只包含正文，不要标题
2. 人物状态要详细记录变化
3. summary_for_context要简洁但信息完整"""
```

---

这个设计方案解决的核心问题：
1. **结构化数据**：不再返回纯文本，而是包含状态快照的JSON
2. **上下文连续性**：会话切换时通过摘要保持连贯
3. **状态可追踪**：随时知道主角在哪、有什么、剧情到哪了
4. **伏笔可管理**：记录已埋伏笔，确保后续回收

需要我先实现Phase 1的结构化返回吗？
