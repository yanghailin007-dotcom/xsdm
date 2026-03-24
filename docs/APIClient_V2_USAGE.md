# APIClient V2 使用指南

## 概述

APIClient 现在支持两种调用模式：

1. **单次模式 (Single Call)** - 无状态调用，适用于独立任务
2. **会话模式 (Session)** - 维护上下文，适用于多轮对话

## 快速开始

### 初始化

```python
from src.core.APIClient import APIClient
from config.config import CONFIG

client = APIClient(CONFIG)
```

---

## 单次模式

适用于：单章生成、独立分析、批量处理等无需上下文的场景

### 基本用法

```python
# 简单调用
result = client.single_call(
    system_prompt="你是一位专业的小说作家",
    user_prompt="请写一个关于废土求生的开头",
    purpose="chapter_generation"
)

print(result)
```

### 完整参数

```python
result = client.single_call(
    system_prompt="你是作家",      # 系统提示词
    user_prompt="写第一章",         # 用户提示词
    temperature=0.8,                # 温度（创造性）
    max_tokens=4000,                # 最大输出长度
    purpose="novel_ch1",            # 用途标识（日志用）
    provider="gemini",              # 指定提供商（可选）
    model_name="gemini-pro"         # 指定模型（可选）
)
```

### 批量处理示例

```python
chapters = ["第一章大纲", "第二章大纲", "第三章大纲"]
results = []

for i, outline in enumerate(chapters):
    result = client.single_call(
        system_prompt="你是小说家",
        user_prompt=f"根据大纲写作: {outline}",
        purpose=f"batch_chapter_{i+1}"
    )
    results.append(result)
```

---

## 会话模式

适用于：连贯创作、多轮优化、需要保持上下文的场景

### 基本用法

```python
# 创建会话
session = client.create_session(
    session_id="novel_001",                    # 会话ID
    system_prompt="你是一位擅长神豪文的作家",    # 系统设定
    provider="kimi",                           # 使用Kimi（原生支持会话）
    temperature=0.7,
    max_history=10                             # 保留最近10轮
)

# 第一轮
chapter1 = session.send_message("写第1章：主角获得系统")
print(chapter1)

# 第二轮（自动带上下文）
chapter2 = session.send_message("继续写第2章：主角第一次花钱")
print(chapter2)

# 第三轮（上下文继续累积）
chapter3 = session.send_message("写第3章：主角打脸富二代")
print(chapter3)
```

### 不同提供商的会话实现

#### Kimi（原生支持）

```python
session = client.create_session(
    session_id="kimi_session",
    system_prompt="你是作家",
    provider="kimi"  # 原生多轮对话
)

# 内部使用 messages 数组格式
# [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]
```

#### Gemini/Deepseek（拼接模拟）

```python
session = client.create_session(
    session_id="gemini_session",
    system_prompt="你是作家",
    provider="gemini"  # 通过拼接模拟会话
)

# 内部自动将历史拼接到 prompt 中
# 用户：写第一章
# 助手：第一章内容...
# 用户：继续写第二章
```

### 流式输出

```python
session = client.create_session(
    session_id="stream_test",
    system_prompt="你是作家",
    provider="kimi"
)

# 流式接收
for chunk in session.send_message_stream("写一段动作戏"):
    print(chunk, end="", flush=True)
```

### 会话管理

```python
# 清空历史（保留system prompt）
session.clear_history(keep_system=True)

# 完全清空
session.clear_history(keep_system=False)

# 导出历史
history = session.export_history()
# [{"role": "system", "content": "..."}, ...]

# 查看统计
print(f"对话轮数: {session.turn_count}")
print(f"历史消息数: {len(session.messages)}")
```

---

## 模式选择指南

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 单章独立生成 | 单次 | 无需上下文，更快 |
| 批量生成章节 | 单次 | 可并行处理 |
| 连贯小说创作 | 会话 | 保持人物设定和剧情一致 |
| 多轮优化修改 | 会话 | 基于前文改进 |
| 复杂角色设计 | 会话 | 多轮讨论完善 |
| 简单问答 | 单次 | 一次性即可 |

---

## 高级用法

### 会话持久化

```python
import json

# 保存会话状态
session_data = {
    "id": session_id,
    "history": session.export_history(),
    "turn_count": session.turn_count
}
with open("session.json", "w") as f:
    json.dump(session_data, f)

# 恢复会话（待实现）
```

### 多会话并行

```python
# 同时处理多个小说
novel_a = client.create_session("novel_a", "你是A作家", provider="kimi")
novel_b = client.create_session("novel_b", "你是B作家", provider="gemini")

# 交替生成
ch_a1 = novel_a.send_message("写第一章")
ch_b1 = novel_b.send_message("写第一章")
ch_a2 = novel_a.send_message("写第二章")
ch_b2 = novel_b.send_message("写第二章")
```

---

## 注意事项

1. **Token 消耗**：会话模式由于携带历史，Token 消耗会逐渐增加
2. **历史裁剪**：超过 max_history 后，旧消息会被自动移除
3. **Provider 切换**：不同提供商的会话不能混用
4. **错误处理**：调用失败时，用户消息不会加入历史

---

## 迁移指南

### 从旧版迁移

旧版代码：
```python
# 旧版单次调用
result = client.generate_content_with_retry(
    content_type="chapter",
    user_prompt="写第一章"
)

# 旧版会话
session = client.create_conversation(
    system_prompt="你是作家"
)
chapter1 = session.send_message("写第一章")
```

新版代码：
```python
# 新版单次调用
result = client.single_call(
    system_prompt=client.Prompts["chapter"],
    user_prompt="写第一章",
    purpose="chapter_gen"
)

# 新版会话
session = client.create_session(
    session_id="novel_001",
    system_prompt="你是作家",
    provider="kimi"
)
chapter1 = session.send_message("写第一章")
```

---

## 待实现功能

- [ ] SimulatedSession 完整实现（Gemini拼接模式优化）
- [ ] 会话持久化和恢复
- [ ] 多会话管理器
- [ ] Token 使用统计
- [ ] 自动历史摘要（长会话优化）
