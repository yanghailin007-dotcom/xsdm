# 番茄爆款仿写系统 - 完整总结

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    批量章节生成器                            │
│              (BatchChapterGenerator)                        │
│                                                             │
│  整合三层数据，输出符合爆款标准的章节                         │
└────────────────────┬────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ 核心设定  │  │ 动态状态  │  │ 情绪流   │
│ 管理器   │  │ 管理器   │  │ 管理器   │
│          │  │          │  │          │
│ 主角姓名 │  │ 当前实力 │  │ 情绪心电图│
│ NPC设定  │  │ 资产等级 │  │ 每章节拍 │
│ 世界观锚点│  │ NPC关系  │  │ 强度规划 │
│ (不变)   │  │ (每章更新)│  │ (爆款模板)│
└──────────┘  └──────────┘  └──────────┘
```

## 三层数据管理

### 第一层：核心设定 (Core Identity) - 不变
```python
{
    "protagonist": {
        "name": "李明",  # 绝对不能变
        "age": 28,
        "core_personality": ["隐忍", "护短", "不圣母"]
    },
    "core_npcs": {
        "林雪": {"role": "女主", "initial_relation": "陌生"},
        "张少": {"role": "初期反派", "fate": "被反复打脸"}
    },
    "world_anchors": {
        "main_city": "东海市",
        "power_system": "花钱返利系统"
    }
}
```
**存储**: `core_identity.json`  
**更新**: 一次初始化，永不改变  
**作用**: 确保主角名字、NPC身份、世界观100%一致

### 第二层：动态状态 (Dynamic State) - 每章更新
```python
{
    "current_chapter": 25,
    "protagonist_current": {
        "cultivation_level": "炼气期三层",  # 只能升
        "current_wealth": 5000000,          # 只能增
        "current_location": "东海市→京城",
        "known_identity": "隐藏"
    },
    "npc_states": {
        "张少": {"status": "被击败住院", "shame_level": 100}
    },
    "key_numbers": {
        "system_level": 3,
        "revenge_count": 5
    }
}
```
**存储**: `dynamic_state.json`  
**更新**: 每章生成后更新  
**作用**: 确保状态不倒退（等级、资产），NPC关系准确

### 第三层：情绪流 (Emotion Flow) - 爆款节奏
```python
[
    {"ch": 1, "emotion": "压抑", "intensity": 9, "beat_type": "钩子", "purpose": "绝望开局"},
    {"ch": 2, "emotion": "希望", "intensity": 6, "beat_type": "转折", "purpose": "系统觉醒"},
    {"ch": 3, "emotion": "爽快", "intensity": 6, "beat_type": "爽点", "purpose": "第一次打脸"},
    {"ch": 4, "emotion": "期待", "intensity": 5, "beat_type": "钩子", "purpose": "新目标"},
    {"ch": 5, "emotion": "爽快", "intensity": 7, "beat_type": "爽点", "purpose": "大打脸"},
    # ... 像心电图一样起伏
]
```
**存储**: `emotion_flow.json`  
**更新**: 基于爆款模板初始化，实际生成后可调整  
**作用**: 确保章章有爽点/钩子，没有平淡章

---

## 核心特性

### 1. 基础一致性（人物不崩）
- ✅ 主角姓名、年龄、核心性格100%一致
- ✅ NPC姓名、身份、关系100%准确
- ✅ 世界时间、地点、力量体系不矛盾
- ✅ 已死NPC不会复活，已曝光身份不会失忆

### 2. 状态连续性（进度不倒退）
- ✅ 系统等级只能升不能降
- ✅ 资产只能增不能减
- ✅ 实力不会莫名其妙倒退
- ✅ 人际关系变化可追溯

### 3. 爆款节奏（情绪不断裂）
- ✅ 没有"起承转合"的平淡期
- ✅ 章章有钩子或爽点
- ✅ 每3-5章一个爽点
- ✅ 情绪强度递增
- ✅ 学习爆款书情绪曲线模板

### 4. 动态调整（偏差自动补偿）
- ✅ 本章偏弱 → 下1-2章加强
- ✅ 本章偏强 → 下章缓冲
- ✅ 连续低强度警告
- ✅ 批次衔接自动调整

---

## 文件结构

```
小说项目/
└── {novel_title}/
    ├── core_identity.json          # 核心设定（不变）
    ├── dynamic_state.json          # 动态状态（每章更新）
    ├── emotion_flow.json           # 情绪流（爆款节奏）
    ├── emotion_framework.json      # 全书情绪框架（旧版，可选）
    │
    └── chapters/
        ├── chapter_001.json
        │   {
        │       "chapter_number": 1,
        │       "title": "第1章 系统觉醒",
        │       "content": "正文...",
        │       "word_count": 2500,
        │       
        │       # 三层数据快照
        │       "state_snapshot": {
        │           "protagonist_state": {...},
        │           "emotion_beat": {
        │               "planned": {"emotion": "压抑", "intensity": 9},
        │               "actual": {"emotion": "压抑", "intensity": 9}
        │           }
        │       },
        │       "generated_at": "2024-01-01T12:00:00"
        │   }
        └── ...
```

---

## 使用示例

```python
from web.services.market_driven.burst_state_manager import BurstStateManager
from web.services.market_driven.emotion_flow import create_emotion_flow
from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator

# 1. 初始化状态管理器
state_manager = BurstStateManager("我的神豪人生")
state_manager.init_from_plan(plan, tropes)

# 2. 初始化情绪流
emotion_flow = create_emotion_flow(
    novel_title="我的神豪人生",
    genre="神豪文-花钱返利类",
    total_chapters=100
)

# 3. 查看情绪心电图
print(emotion_flow.get_curve_visualization())

# 4. 批量生成
generator = BatchChapterGenerator(
    api_client=api_client,
    state_manager=state_manager,
    emotion_flow=emotion_flow
)

results = generator.generate_with_state_manager(
    novel_title="我的神豪人生",
    start_chapter=1,
    end_chapter=30,
    blueprint={},
    tropes=tropes,
    plan=plan
)
```

---

## 关键改进

| 问题 | 旧方案 | 新方案 |
|------|--------|--------|
| 主角名字变来变去 | ❌ 无管理 | ✅ 核心设定锁定 |
| 实力/资产倒退 | ❌ 无验证 | ✅ 动态状态验证 |
| 中间有平淡章 | ❌ 起承转合 | ✅ 情绪心电图 |
| 情绪断裂 | ❌ 无视偏差 | ✅ 自动补偿调整 |
| 节奏靠感觉 | ❌ 随机生成 | ✅ 爆款模板 |
| 会话切换丢上下文 | ❌ 从头开始 | ✅ 状态快照恢复 |

---

## 后续优化方向

### P1（高优先级）
1. **爆款书情绪提取器**：自动分析爆款书，提取情绪曲线模板
2. **A/B测试框架**：对比不同情绪曲线的读完率
3. **实时质量评估**：生成时实时评估是否符合爆款标准

### P2（中优先级）
4. **多模态情绪**：不只是文字，还有直播弹幕、全国反应等
5. **个性化调整**：根据读者反馈调整情绪曲线
6. **跨书连贯**：系列小说之间的状态和情绪衔接

### P3（低优先级）
7. **可视化编辑器**：图形化编辑情绪曲线
8. **社区模板库**：用户共享情绪曲线模板
9. **AI辅助调整**：让AI分析偏差原因并给出调整建议

---

## 核心原则总结

```
仿写番茄爆款的三个支柱：

1. 基础一致性（设定不崩）
   └─ 核心设定100%准确，人物不倒退

2. 情绪流（节奏不断）
   └─ 章章有爽点/钩子，像心电图一样起伏

3. 动态调整（偏差补偿）
   └─ 实际偏离规划时，自动调整后续

最终目标：让读者停不下来，章章付费，疯狂追更。
```
