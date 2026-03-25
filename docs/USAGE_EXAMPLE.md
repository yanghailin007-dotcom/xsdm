# 使用示例 - 集成状态管理的章节生成

## 快速开始

```python
from web.services.market_driven.burst_state_manager import BurstStateManager
from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
from src.core.APIClient import APIClient
from config.config import CONFIG

# 1. 初始化API客户端
api_client = APIClient(CONFIG)

# 2. 初始化状态管理器
novel_title = "我的神豪人生"
state_manager = BurstStateManager(novel_title)

# 3. 从plan初始化核心设定
plan = {
    "protagonist_name": "李明",
    "protagonist_age": 28,
    "protagonist_identity": "外卖员",
    "protagonist_personality": "隐忍,护短,不圣母",
    "protagonist_appearance": "平凡,坚毅眼神,外卖服",
    "main_city": "东海市",
    "important_npcs": [
        {"name": "林雪", "role": "女主", "identity": "校花", "traits": "高冷,善良", "relation": "陌生"},
        {"name": "张少", "role": "初期反派", "identity": "富二代", "traits": "嚣张,愚蠢", "relation": "敌对", "fate": "被反复打脸"}
    ]
}

tropes = {
    "power_system": "花钱返利系统",
    "pacing": {
        "first_face_slap": "第3章",
        "first_major_climax": "第15章"
    }
}

state_manager.init_from_plan(plan, tropes)

# 4. 初始化批量生成器（传入state_manager）
generator = BatchChapterGenerator(api_client=api_client, state_manager=state_manager)

# 5. 批量生成章节
results = generator.generate_with_state_manager(
    novel_title=novel_title,
    start_chapter=1,
    end_chapter=10,
    blueprint={"chapters": []},  # 可以传入详细的章节规划
    tropes=tropes,
    plan=plan
)

print(f"生成完成：成功{len(results['generated'])}章，失败{len(results['failed'])}章")
```

## 状态管理器数据文件

运行后会自动创建以下文件：

```
小说项目/
└── 我的神豪人生/
    ├── core_identity.json           # 核心设定（主角、NPC、世界观）
    ├── dynamic_state.json           # 动态状态（当前章节、主角状态、NPC状态）
    ├── emotion_rhythm.json          # 情绪节奏（情绪历史、下章规划）
    └── chapters/
        ├── chapter_001.json         # 章节内容 + 状态快照
        ├── chapter_002.json
        └── ...
```

## 会话切换示例

当会话满载时，状态管理器可以重建完整的上下文：

```python
# 假设已经生成了20章，需要切换会话继续生成第21章

# 1. 重新加载状态管理器（自动加载所有状态）
state_manager = BurstStateManager("我的神豪人生")

# 2. 为第21章构建System Prompt
system_prompt = state_manager.build_system_prompt(chapter_num=21)

# 3. 使用新的System Prompt创建会话并生成
response = api_client.generate_content_with_retry(
    content_type="chapter_content_structured",
    system_prompt=system_prompt,
    user_prompt="请生成第21章内容",
    temperature=0.7
)

# 4. 解析响应并更新状态
chapter_data = json.loads(response)
state_manager.update_after_chapter(21, chapter_data)
```

## 关键特性

### 1. 主角一致性保证
- 主角姓名、年龄、核心性格从`core_identity.json`读取，永远不会变
- 当前状态（实力、资产、位置）从`dynamic_state.json`读取，每章更新
- AI生成时必须从当前状态开始，不能倒退

### 2. NPC状态追踪
- NPC的核心设定（身份、性格）不变
- NPC的动态状态（关系、位置、是否知道秘密）每章更新
- 已死亡的NPC不会复活

### 3. 情绪节奏管理
- 自动规划前30章的情绪曲线
- 记录每章实际达成的情绪
- 指导下章写作的情绪目标

### 4. 状态验证
每章更新前自动验证：
- 系统等级只能升不能降
- 资产只能增不能减（除非特殊剧情）
- 主角姓名不能变
- 已死NPC不能复活

## 与旧模式对比

| 特性 | 旧模式 | 新模式（状态管理） |
|------|--------|-------------------|
| 主角姓名 | 可能变 | 100%一致 |
| 主角实力 | 可能倒退 | 只能前进 |
| NPC关系 | 容易混乱 | 精确追踪 |
| 会话切换 | 上下文丢失 | 状态恢复 |
| 情绪节奏 | 无管理 | 自动规划 |
| 伏笔回收 | 容易遗漏 | 系统追踪 |

## 故障排查

### 问题1：核心设定未初始化
```
Error: 核心设定未初始化
```
**解决**：确保先调用 `state_manager.init_from_plan(plan, tropes)`

### 问题2：状态更新非法
```
Error: 状态更新非法: ['系统等级不能下降']
```
**解决**：检查AI返回的`state_updates`，确保数值不倒退

### 问题3：生成内容不是JSON
```
Error: JSON解析失败
```
**解决**：System Prompt中已包含严格的JSON格式要求，如仍失败，会回退到文本模式
