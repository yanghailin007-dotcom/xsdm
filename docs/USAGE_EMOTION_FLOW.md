# 情绪流使用示例

## 核心概念

**情绪流 = 心电图模式**
- 没有"起承转合"，只有情绪的起伏
- 每章都有用：要么爽、要么期待、要么钩子
- 情绪强度1-10，像心电图一样高低起伏

## 快速开始

```python
from web.services.market_driven.emotion_flow import create_emotion_flow
from web.services.market_driven.burst_state_manager import BurstStateManager
from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
from src.core.APIClient import APIClient

# 初始化
api_client = APIClient(CONFIG)
novel_title = "我的神豪人生"

# 创建情绪流（使用爆款模板）
emotion_flow = create_emotion_flow(
    novel_title=novel_title,
    genre="神豪文-花钱返利类",
    total_chapters=100
)

# 查看情绪心电图
print(emotion_flow.get_curve_visualization())
# 输出:
# 情绪心电图:
# 章数 | 情绪    | 强度 | 类型 | 作用
# --------------------------------------------------
#   1  | 压抑    |  9   | 钩子 | 绝望开局，让读者代入
#   2  | 希望    |  6   | 转折 | 系统出现，点燃希望
#   3  | 爽快    |  6   | 爽点 | 第一次花钱打脸
#   4  | 期待    |  5   | 钩子 | 新目标出现
#   5  | 爽快    |  7   | 爽点 | 第一次大打脸...

# 获取单章情绪节拍
beat = emotion_flow.get_beat(5)
print(f"第5章: {beat.emotion}(强度{beat.intensity}) - {beat.purpose}")
# 输出: 第5章: 爽快(强度7) - 第一次大打脸，身份小提升

# 获取接下来5章
next_beats = emotion_flow.get_next_n_beats(start_ch=6, n=5)
for b in next_beats:
    print(f"第{b.ch}章: {b.emotion}({b.intensity}) - {b.beat_type}")
# 输出:
# 第6章: 期待(5) - 铺垫
# 第7章: 好奇(4) - 钩子
# 第8章: 爽快(7) - 爽点
# 第9章: 震惊(8) - 震惊
# 第10章: 期待(6) - 钩子

# 检查是否有连续低强度
low_chapters = emotion_flow.check_continuous_low(window=3)
if low_chapters:
    print(f"警告：第{low_chapters}章开始连续低强度!")
```

## 完整生成流程

```python
# 准备plan和tropes
plan = {
    "protagonist_name": "李明",
    "protagonist_age": 28,
    "protagonist_identity": "外卖员",
    "protagonist_personality": "隐忍,护短,不圣母",
    "main_city": "东海市",
    "total_chapters": 100,
    "genre": "神豪文-花钱返利类",
    "important_npcs": [
        {"name": "林雪", "role": "女主", "identity": "校花", "traits": "高冷,善良"},
        {"name": "张少", "role": "初期反派", "identity": "富二代", "fate": "被反复打脸"}
    ]
}

tropes = {
    "power_system": "花钱返利系统",
    "core_formula": "穷屌丝→花钱返利系统→装逼打脸→身份升级"
}

# 初始化状态管理器
state_manager = BurstStateManager(novel_title)
state_manager.init_from_plan(plan, tropes)

# 初始化批量生成器
generator = BatchChapterGenerator(
    api_client=api_client,
    state_manager=state_manager,
    emotion_flow=emotion_flow  # 传入情绪流
)

# 批量生成前30章
results = generator.generate_with_state_manager(
    novel_title=novel_title,
    start_chapter=1,
    end_chapter=30,
    blueprint={},
    tropes=tropes,
    plan=plan
)

print(f"生成完成：成功{len(results['generated'])}章")
```

## 情绪节拍类型

```python
BEAT_TYPES = {
    "钩子": "章尾悬念，让读者必须看下一章",
    "爽点": "打脸/收获/升级，让读者爽",
    "震惊": "身份曝光/大场面，让读者震惊",
    "收获": "主角获得实质性好处",
    "铺垫": "为下一波爽点做准备（强度不能太低）",
    "转折": "剧情转折，如系统觉醒",
    "推进": "剧情推进，新场景/新人物"
}
```

## 情绪模板

### 神豪文经典节奏
```
章数 | 情绪    | 强度 | 节拍 | 作用
-----|---------|------|------|------
1    | 压抑    | 9    | 钩子 | 被羞辱，负债，绝望开局
2    | 希望    | 6    | 转折 | 系统觉醒，点燃希望
3    | 爽快    | 6    | 爽点 | 第一次花钱打脸
4    | 期待    | 5    | 钩子 | 新目标：豪车
5    | 爽快    | 7    | 爽点 | 4S店打脸，买豪车
6    | 期待    | 5    | 铺垫 | 遇到女主，新场景
7    | 好奇    | 4    | 钩子 | 神秘人物出现
8    | 爽快    | 7    | 爽点 | 餐厅打脸富二代
9    | 震惊    | 8    | 震惊 | 车主身份曝光
10   | 期待    | 6    | 钩子 | 拍卖会预告
11   | 紧张    | 7    | 铺垫 | 拍卖会开启
12   | 爽快    | 7    | 推进 | 一路竞价
13   | 爽快    | 8    | 爽点 | 连续打脸
14   | 震惊    | 8    | 震惊 | 全场震惊财力
15   | 大爽快  | 9    | 高潮 | 拍下天价宝物
...

规律：
- 情绪：压抑→希望→爽快→期待→更爽快→震惊→期待→高潮
- 强度：9→6→6→5→7→5→4→7→8→6→7→7→8→8→9
- 不能有连续3章低于6
- 章章有钩子或爽点
```

### 国运文经典节奏
```
章数 | 情绪    | 强度 | 节拍 | 作用
-----|---------|------|------|------
1    | 紧张    | 8    | 钩子 | 被选召，全国关注
2    | 期待    | 7    | 转折 | 绑定系统，获得能力
3    | 爽快    | 8    | 爽点 | 首次展示，全国震惊
4    | 期待    | 6    | 钩子 | 新禁地挑战
5    | 爽快    | 7    | 爽点 | 首杀，具现奖励
...

规律：
- 每章必须有直播弹幕（分层反应）
- 每章必须有国运具现的全国反应
- 每章必须有"震惊"元素
```

## 自动调整机制

```python
# 第5章规划：爽快(强度7)
# 实际生成：爽快(强度5) ← 偏弱

emotion_flow.record_actual(ch=5, emotion="爽快", intensity=5)

# 系统自动调整后续章节
# 第6章：强度 5→6 (+1补偿)
# 第7章：强度 4→5 (+1补偿)

print("调整后:")
for b in emotion_flow.get_next_n_beats(6, 3):
    print(f"第{b.ch}章: {b.emotion}({b.intensity})")
```

## 数据文件

```
小说项目/
└── 我的神豪人生/
    ├── emotion_flow.json           # 情绪流定义
    │   {
    │       "total_chapters": 100,
    │       "curve": [
    │           {"ch": 1, "emotion": "压抑", "intensity": 9, "beat_type": "钩子", ...},
    │           {"ch": 2, "emotion": "希望", "intensity": 6, "beat_type": "转折", ...},
    │           ...
    │       ],
    │       "actual_emotions": {     # 实际生成的情绪
    │           "5": {"emotion": "爽快", "intensity": 7, ...},
    │           ...
    │       }
    │   }
    │
    └── chapters/
        ├── chapter_001.json
        │   {
        │       "emotion_beat": {
        │           "planned": {"emotion": "压抑", "intensity": 9, ...},
        │           "actual": {"actual_emotion": "压抑", "intensity": 9, ...}
        │       }
        │   }
        └── ...
```

## 关键规则

```python
RULES = [
    "不能连续3章强度低于6（会流失读者）",
    "每5章必须有一个强度≥8的章节",
    "大高潮(强度9)后必须有1章冷却(强度5-6)",
    "章章有钩子，或爽点，或期待",
    "情绪只能跳跃1-2级，不能压抑直接大爽快"
]
```

## 对比：起承转合 vs 情绪流

| 传统（起承转合） | 情绪流（心电图） |
|-----------------|----------------|
| 起：10章铺垫 | 第1章压抑(9) → 直接钩住读者 |
| 承：20章平淡 | 没有"承"，每章都有用 |
| 转：40章高潮 | 每10章一个中高潮 |
| 合：30章收尾 | 情绪渐弱但章章有钩子 |
| 中间易流失 | 全程保持兴趣 |
| 过渡章可以水 | 没有真正的过渡章 |

**核心转变**：从"写故事"变成"操控读者情绪的心跳"。
