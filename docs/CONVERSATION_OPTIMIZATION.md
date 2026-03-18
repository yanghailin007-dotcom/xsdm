# 多轮对话优化小说生成指南

## 问题背景

传统的小说生成方式每次调用 API 都重新传递 system_prompt，存在以下问题：

1. **Token 浪费** - 每次都要重复发送 system prompt（通常 500-2000 tokens）
2. **上下文断裂** - 模型无法"记住"之前生成的内容风格
3. **连贯性差** - 章节之间风格可能不一致

## 解决方案：ConversationSession

使用 `ConversationSession` 类实现多轮对话，只需在第一次调用时传递 system prompt。

## 核心优势

| 特性 | 传统方式 | 多轮对话方式 |
|------|---------|-------------|
| System Prompt | 每次重复发送 | 只发一次 |
| Token 消耗 | 高 | 低（节省 20-40%）|
| 上下文连贯 | 差 | 好 |
| 风格一致性 | 差 | 好 |

## 使用示例

### 基础用法

```python
from src.core.APIClient import APIClient
from src.core.Config import Config

# 初始化
config = Config()
api_client = APIClient(config)

# 创建对话会话
session = api_client.create_conversation(
    system_prompt="""你是一位专业网络小说作家，擅长创作玄幻修仙小说。
风格要求：热血、升级流、节奏快、每章3000字左右。
主角设定：林尘，废柴少年，获得神秘戒指后开始逆袭。""",
    provider="kimi",
    model_name="moonshot-v1-32k",
    purpose_prefix="小说生成"
)

# 生成大纲（第1轮 - 包含 system prompt）
outline = session.send_message(
    user_prompt="请生成一份详细的小说大纲，包含50章的标题和简要情节。",
    purpose="大纲生成"
)

# 生成第1章（第2轮 - 只发送 user prompt，利用上下文）
chapter1 = session.send_message(
    user_prompt="根据大纲，详细生成第1章内容。要求：开篇吸引人，3000字。",
    purpose="章节_1"
)

# 生成第2章（第3轮 - 继续利用上下文）
chapter2 = session.send_message(
    user_prompt="继续生成第2章，承接第1章结尾的剧情。",
    purpose="章节_2"
)

# ... 继续生成后续章节

# 查看统计信息
stats = session.get_stats()
print(f"对话轮次: {stats['turn_count']}")
print(f"累计消息: {stats['message_count']}")
print(f"Token估算: {stats['total_tokens_sent'] + stats['total_tokens_received']}")

# 清理历史（可选）
session.clear_history(keep_system=True)  # 保留 system prompt
```

### 高级用法：上下文管理器

```python
# 使用 with 语句自动管理会话
with api_client.create_conversation(
    system_prompt="你是一位专业作家...",
    provider="kimi"
) as session:
    
    # 批量生成多章
    for chapter_num in range(1, 11):
        content = session.send_message(
            user_prompt=f"生成第{chapter_num}章内容",
            purpose=f"章节_{chapter_num}"
        )
        # 保存章节...
        
    # 会话结束时自动记录统计信息
```

### 混合模式：多 Provider 切换

```python
# 创建 Kimi 会话用于主线剧情
main_session = api_client.create_conversation(
    system_prompt="主线剧情作家...",
    provider="kimi",
    model_name="moonshot-v1-32k"
)

# 创建 Gemini 会话用于支线/番外
side_session = api_client.create_conversation(
    system_prompt="支线剧情作家...",
    provider="gemini"
)

# 并行生成
chapter_main = main_session.send_message("生成主线第10章")
chapter_side = side_session.send_message("生成支线第3章")
```

### 实际项目集成示例

```python
class NovelGenerator:
    def __init__(self, api_client):
        self.api_client = api_client
        self.session = None
    
    def start_project(self, novel_config):
        """开始一个新小说项目"""
        # 根据小说类型构建 system prompt
        system_prompt = self._build_system_prompt(novel_config)
        
        # 创建长期会话
        self.session = self.api_client.create_conversation(
            system_prompt=system_prompt,
            provider=novel_config.get('provider', 'kimi'),
            purpose_prefix=novel_config['title']
        )
        
        self.logger.info(f"开始生成小说: {novel_config['title']}")
    
    def generate_outline(self):
        """生成大纲"""
        return self.session.send_message(
            "请生成详细的小说大纲，包含50章的标题、主要情节和关键冲突点。",
            purpose="大纲"
        )
    
    def generate_chapter(self, chapter_num, outline_hint):
        """生成单章"""
        # 利用会话上下文保持风格一致
        return self.session.send_message(
            f"生成第{chapter_num}章。\n"
            f"本章要点: {outline_hint}\n"
            f"要求: 3000字，保持与前文章节风格一致",
            purpose=f"第{chapter_num}章"
        )
    
    def generate_batch(self, start_chapter, count):
        """批量生成章节"""
        chapters = []
        for i in range(start_chapter, start_chapter + count):
            chapter = self.generate_chapter(i, f"第{i}章情节要点")
            chapters.append(chapter)
            
            # 可选：每生成5章保存一次上下文快照
            if i % 5 == 0:
                self._save_checkpoint()
        
        return chapters
    
    def get_project_stats(self):
        """获取项目统计"""
        return self.session.get_stats()


# 使用示例
generator = NovelGenerator(api_client)

# 配置小说
generator.start_project({
    'title': '逆天邪神',
    'genre': '玄幻修仙',
    'style': '热血升级流',
    'provider': 'kimi',
    'model': 'moonshot-v1-32k'
})

# 生成
outline = generator.generate_outline()
chapters = generator.generate_batch(start_chapter=1, count=10)

# 查看统计
stats = generator.get_project_stats()
print(f"项目统计: {stats}")
```

## Token 节省计算

假设一个典型的小说生成任务：

| 项目 | 传统方式 | 多轮对话 | 节省 |
|------|---------|---------|------|
| System Prompt | 1000 tokens/次 | 1000 tokens/次 | - |
| 50章 × 调用 | 50,000 tokens | 1,000 tokens | 98% |
| 每章 User Prompt | 200 tokens | 200 tokens | - |
| 50章 × User | 10,000 tokens | 10,000 tokens | - |
| **总计发送** | **60,000 tokens** | **11,000 tokens** | **81.7%** |

## 最佳实践

### 1. 何时使用多轮对话？

✅ **推荐使用**
- 同一小说的连续章节生成
- 需要保持风格一致性的任务
- 批量生成内容（如大纲→章节）

❌ **不建议使用**
- 完全独立的单章生成
- 不同类型/风格的内容切换
- 需要完全重置上下文的场景

### 2. System Prompt 设计

```python
# 好的 System Prompt - 具体、详细
system_prompt = """你是一位专业网络小说作家。

【风格设定】
- 类型：玄幻修仙
- 风格：热血升级流
- 节奏：快，每章要有爽点
- 字数：每章3000字左右

【主角设定】
- 姓名：林尘
- 性格：坚韧、聪明、护短
- 金手指：神秘戒指中的老者

【写作要求】
1. 开篇要有冲突或悬念
2. 章节结尾留钩子
3. 对话简洁有力
4. 场景描写要有画面感
"""

# 差的 System Prompt - 太简单
bad_prompt = "你是一个作家，写玄幻小说。"
```

### 3. 上下文管理

```python
# 每生成10章清理一次历史，防止上下文过长
if chapter_num % 10 == 0:
    session.clear_history(keep_system=True)
    # 重新发送关键设定
    session.send_message("提醒：主角是林尘，金手指是神秘戒指...")
```

### 4. 错误处理

```python
for attempt in range(3):
    result = session.send_message(f"生成第{chapter_num}章")
    if result:
        break
    else:
        # 失败时清理最后一次用户消息
        session.clear_history(keep_system=True)
        time.sleep(2)
```

## 故障排除

### 问题：上下文太长导致响应变慢

**解决：**
```python
# 定期清理历史
if len(session.messages) > 20:
    session.clear_history(keep_system=True)
```

### 问题：模型"忘记"早期设定

**解决：**
```python
# 定期提醒关键设定
if chapter_num % 5 == 0:
    session.send_message(
        "【设定提醒】主角：林尘，当前境界：筑基期...",
        purpose="提醒"
    )
```

### 问题：Token 消耗仍过高

**解决：**
- 使用更小上下文的模型（8k 代替 32k）
- 精简 system prompt
- 减少对话轮次

## 总结

多轮对话模式可以：
1. **节省 80%+ 的 Token 消耗**
2. **保持章节间的风格连贯性**
3. **减少 API 调用成本**
4. **提高生成质量**

特别适合长篇小说、系列内容的批量生成。
