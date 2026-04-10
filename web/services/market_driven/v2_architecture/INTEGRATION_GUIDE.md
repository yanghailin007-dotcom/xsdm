# V2 六层架构集成指南

## 概述

V2 六层架构已成功集成到章节生成系统中，实现了 System Prompt 和 User Prompt 的分离。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      System Prompt                          │
│                   (高频约束，长期保持)                        │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: 核心设定    - 世界观、金手指、人设                   │
│ Layer 2: 战术规划    - 阶段目标、章节目标                     │
│ Layer 3: 题材技法    - 国运文/神豪文特定规则 ★优先集成        │
│ Layer 4: 文风技法    - 快节奏、震惊流                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      User Prompt                            │
│                   (低频变化，每章更新)                        │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: AI约束      - 字数、格式、情绪曲线                   │
│ Layer 6: 自检清单    - 输出前检查项                          │
│ 任务指令             - 具体章节要求                          │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. LayeredSystemPrompt

分层 System Prompt 数据类，支持 Layer 1-4 的灵活组合。

```python
from web.services.market_driven.v2_architecture import LayeredSystemPrompt

system = LayeredSystemPrompt(
    layer1_core_setting="主角绑定酒剑仙模板...",
    layer2_tactical_planning="第一阶段：初入禁地...",
    layer3_genre_techniques="国运文技法：弹幕...",
    layer4_writing_style="快节奏、震惊流..."
)

# 组合全部
full = system.combine()

# 只组合 Layer 3-4 (作为 System Prompt 发送)
system_only = system.combine([3, 4])
```

### 2. LayeredUserPrompt

分层 User Prompt 数据类，支持 Layer 5-6 + 任务指令的动态组合。

```python
from web.services.market_driven.v2_architecture import LayeredUserPrompt

user = LayeredUserPrompt(
    layer5_ai_constraints="字数2000-2500...",
    layer6_self_check="□ 弹幕≥8条...",
    task_instruction="生成第7章..."
)

user_prompt = user.combine()
```

### 3. LayeredConversationSession

V2 分层对话会话类，支持 System Prompt 分层管理和动态更新。

```python
from web.services.market_driven.v2_architecture import LayeredConversationSession

session = LayeredConversationSession(
    api_client=api_client,
    system_prompt=system,
    max_history=10
)

# 发送消息
response = session.send_message(user_prompt)

# 更新特定层
session.update_system_layer(3, "新的题材技法...")
```

### 4. ChapterConversationV2

V2 章节对话生成器，整合六层架构的完整生成流程。

```python
from web.services.market_driven.v2_architecture import ChapterConversationV2

conversation = ChapterConversationV2(
    api_client=api_client,
    genre="国运文-直播类",
    core_setting="主角绑定酒剑仙模板...",
    tactical_planning="第一阶段..."
)

# 生成章节
content = conversation.generate_chapter(
    chapter_number=1,
    chapter_title="初入禁地",
    outline_summary="主角觉醒酒剑仙模板，进入国运禁地",
    chapter_type="爆发章"  # 打脸章/收获章/危机章/铺垫章/爆发章
)
```

## 情绪曲线模板

内置五种章节类型的情绪曲线：

| 类型 | 曲线 | 适用场景 |
|------|------|----------|
| 打脸章 | 虐(4)→急(7)→爽(9)→悬(7) | 反派挑衅→主角反击 |
| 爆发章 | 蓄(3)→爆(10)→收(5) | 实力全开的高潮 |
| 收获章 | 争(6)→得(8)→惊(7) | 获得宝物/奖励 |
| 危机章 | 安(3)→危(8)→逃(6) | 遭遇危险逃脱 |
| 铺垫章 | 平(4)→伏(5)→引(6) | 埋线铺垫过渡 |

## Prompt 分离优势

### 传统方式
```
每章请求 = System Prompt(2000字) + User Prompt(500字)
10章 = 2500 × 10 = 25000字
```

### V2 分离方式
```
首次请求 = System Prompt(800字, Layer 3-4) + User Prompt(500字)
后续请求 = User Prompt(300字, 仅任务变化)
10章 = 1300 + 300 × 9 = 15100字 (节省 40%)
```

## 集成优先级

### ✅ 已完成
1. **Layer 3 (题材技法)** - 国运文/神豪文 YAML 模板
2. **Layer 4 (文风技法)** - 快节奏、震惊流
3. **Layer 5 (AI约束)** - 字数、格式、情绪曲线
4. **Layer 6 (自检清单)** - 输出前检查

### 🔄 待集成
1. **与现有生成器集成** - 替换 `ChapterConversationGenerator`
2. **题材自动检测** - 从大纲自动识别题材类型
3. **情绪曲线动态规划** - 基于大纲自动选择章节类型
4. **缓存优化** - System Prompt 持久化

## 文件位置

```
web/services/market_driven/v2_architecture/
├── __init__.py                    # 导出 V2 组件
├── conversation_session_v2.py     # 分层对话会话
├── chapter_conversation_v2.py     # 章节对话生成器
├── prompt_assembler_v2.py         # 提示词组装器
├── layer_loaders.py               # 各层加载器
├── renderers.py                   # 各层渲染器
├── models.py                      # 数据模型
├── test_integration_v2.py         # 集成测试
└── INTEGRATION_GUIDE.md           # 本指南

prompt_packages/v2_architecture/
├── genre_techniques/
│   ├── 国运文.yaml               # 国运文题材技法
│   ├── 神豪文.yaml               # 神豪文题材技法
│   └── 通用.yaml                 # 通用题材技法
└── ...                           # 其他 YAML 模板
```

## 使用示例

### 快速开始

```python
# 1. 导入
from web.services.market_driven.v2_architecture import (
    ChapterConversationV2,
    create_chapter_conversation_v2
)

# 2. 从小说状态创建
novel_state = {
    "genre": "国运文-直播类",
    "core_setting": "主角绑定酒剑仙模板...",
    "tactical_planning": "第一阶段：初入禁地..."
}

conversation = create_chapter_conversation_v2(api_client, novel_state)

# 3. 生成章节
content = conversation.generate_chapter(
    chapter_number=7,
    chapter_title="一剑斩妖王",
    outline_summary="主角在禁地遭遇妖王，使用酒剑仙模板技能将其斩杀",
    chapter_type="爆发章"
)
```

### 高级用法

```python
# 自定义 System Prompt
from web.services.market_driven.v2_architecture import LayeredSystemPrompt

system = LayeredSystemPrompt(
    layer3_genre_techniques="自定义题材规则...",
    layer4_writing_style="自定义文风..."
)

session = LayeredConversationSession(
    api_client=api_client,
    system_prompt=system
)

# 动态更新题材规则
session.update_system_layer(3, "新的国运文规则...")
```

## 测试结果

```
✅ LayeredSystemPrompt 测试通过
✅ LayeredUserPrompt 测试通过
✅ LayeredConversationSession 测试通过
✅ ChapterConversationV2 测试通过
✅ System/User Prompt 分离测试通过
```

## 下一步

1. 在 `ChapterConversationGenerator` 中集成 V2 架构
2. 添加题材自动检测逻辑
3. 实现情绪曲线动态规划
4. 优化 Token 使用和缓存策略
