# 动态情绪规划器使用示例

## 完整使用流程

```python
from web.services.market_driven.burst_state_manager import BurstStateManager
from web.services.market_driven.emotion_planner import DynamicEmotionPlanner, create_emotion_planner
from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
from src.core.APIClient import APIClient
from config.config import CONFIG

# 1. 初始化API客户端
api_client = APIClient(CONFIG)

# 2. 准备plan和tropes
novel_title = "我的神豪人生"
total_chapters = 100

plan = {
    "protagonist_name": "李明",
    "protagonist_age": 28,
    "protagonist_identity": "外卖员",
    "protagonist_personality": "隐忍,护短,不圣母",
    "protagonist_appearance": "平凡,坚毅眼神,外卖服",
    "main_city": "东海市",
    "total_chapters": total_chapters,
    "genre": "神豪文-花钱返利类",
    "important_npcs": [
        {"name": "林雪", "role": "女主", "identity": "校花", "traits": "高冷,善良", "relation": "陌生"},
        {"name": "张少", "role": "初期反派", "identity": "富二代", "traits": "嚣张,愚蠢", "relation": "敌对", "fate": "被反复打脸"},
        {"name": "王管家", "role": "管家", "identity": "首富家忠仆", "traits": "忠诚,精明", "relation": "未来效忠"}
    ]
}

tropes = {
    "power_system": "花钱返利系统",
    "pacing": {
        "first_face_slap": "第3章",
        "first_major_climax": "第15章"
    },
    "core_formula": "穷屌丝→花钱返利系统→被迫高消费→装逼打脸→身份升级→更大场面"
}

# 3. 初始化状态管理器
state_manager = BurstStateManager(novel_title)
state_manager.init_from_plan(plan, tropes)

# 4. 初始化情绪规划器（使用爆款模板）
emotion_planner = create_emotion_planner(
    novel_title=novel_title,
    total_chapters=total_chapters,
    genre=plan['genre'],
    tropes=tropes
)

# 5. 初始化批量生成器
generator = BatchChapterGenerator(
    api_client=api_client,
    state_manager=state_manager,
    emotion_planner=emotion_planner
)

# 6. 批量生成（使用新接口）
results = generator.generate_with_state_manager(
    novel_title=novel_title,
    start_chapter=1,
    end_chapter=30,  # 先生成前30章
    blueprint={"chapters": []},
    tropes=tropes,
    plan=plan
)

print(f"生成完成：")
print(f"- 成功：{len(results['generated'])}章")
print(f"- 失败：{len(results['failed'])}章")
print(f"- 平均质量：{results['avg_quality']:.1f}")
if 'emotion_summary' in results:
    print(f"- 情绪摘要：{results['emotion_summary']}")
```

## 情绪规划器单独使用

```python
from web.services.market_driven.emotion_planner import DynamicEmotionPlanner

# 1. 创建规划器
planner = DynamicEmotionPlanner("我的神豪人生")

# 2. 初始化全书框架（使用爆款模板）
planner.init_master_framework(
    total_chapters=100,
    tropes=tropes,
    template_key="神豪文-花钱返利类"  # 使用神豪文爆款模板
)

# 3. 规划第一批次（1-10章）
batch1_plan = planner.plan_next_batch(start_chapter=1, batch_size=10)

print(f"批次{batch1_plan.batch_id}规划：")
for ch, plan in batch1_plan.chapter_plans.items():
    print(f"  第{ch}章: {plan.type}(目标{plan.target_emotion}, 强度{plan.intensity})")

# 4. 生成第1章后记录实际情绪
planner.record_actual_emotion(ch=1, actual={
    "emotion": "压抑→震惊",
    "intensity": 8,
    "event_type": "系统觉醒"
})

# 5. 如果实际偏离规划，自动调整后续
# 例如：第1章预期强度8，实际只有6，系统会自动加强第2-3章

# 6. 获取下一章情绪目标
next_plan = planner.get_chapter_emotion_target(ch=2)
print(f"第2章情绪目标: {next_plan.target_emotion}(强度{next_plan.intensity})")

# 7. 获取生成摘要
summary = planner.get_emotion_summary()
print(f"生成摘要: {summary}")
```

## 情绪曲线模板

系统内置了爆款书情绪模板：

### 神豪文-花钱返利类
```python
{
    "pattern_name": "神豪文经典节奏",
    "curve": [
        {"ch": 1, "emotion": "压抑→震惊", "intensity": 8, "event": "系统觉醒"},
        {"ch": 2, "emotion": "好奇→期待", "intensity": 6, "event": "初试系统"},
        {"ch": 3, "emotion": "爽快", "intensity": 6, "event": "第一次花钱打脸"},
        {"ch": 5, "emotion": "爽快", "intensity": 7, "event": "第一次大打脸"},
        {"ch": 8, "emotion": "震惊", "intensity": 8, "event": "身份小曝光"},
        {"ch": 10, "emotion": "大爽快", "intensity": 8, "event": "阶段性总结"},
        {"ch": 15, "emotion": "震惊", "intensity": 9, "event": "拍卖会大场面"},
        {"ch": 20, "emotion": "大爽快", "intensity": 9, "event": "身份中曝光"},
        {"ch": 28, "emotion": "震惊", "intensity": 9, "event": "第一阶段高潮"},
        {"ch": 30, "emotion": "满足→期待", "intensity": 8, "event": "总结+新目标"},
    ],
    "rules": [
        "第1章必须压抑到极点然后系统觉醒",
        "第3章必须第一次打脸（小）",
        "第5章必须第一次大打脸",
        "每10章一个身份升级",
        "每3-5章一个小爽点"
    ]
}
```

### 国运文-直播类
```python
{
    "pattern_name": "国运文经典节奏",
    "curve": [
        {"ch": 1, "emotion": "紧张→希望", "intensity": 8, "event": "被选召"},
        {"ch": 2, "emotion": "期待→爽快", "intensity": 7, "event": "首次扮演"},
        {"ch": 3, "emotion": "震惊", "intensity": 8, "event": "全国震惊"},
        {"ch": 5, "emotion": "爽快", "intensity": 7, "event": "首次击杀"},
        {"ch": 10, "emotion": "大爽快", "intensity": 9, "event": "第一层BOSS"},
    ]
}
```

## 自动调整机制

### 场景1：强度偏差补偿
```
第5章规划: 爽快(强度7)
第5章实际: 爽快(强度5) ← 偏弱

自动调整:
  第6章: 强度 6→7 (+1补偿)
  第7章: 强度 7→8 (+1补偿)
  
日志: "前一批次情绪偏弱(-2.0)，加强本批次"
```

### 场景2：情绪类型不匹配
```
第10章规划: 大高潮(震惊)
第10章实际: 平淡(无聊) ← 类型不匹配

自动调整:
  第11章: 类型 铺垫→爽点
  第12章: 类型 推进→打脸
  
日志: "情绪类型偏离规划，加快爽点节奏"
```

### 场景3：高强度后缓冲
```
第15章规划: 大高潮(强度9)
第15章实际: 大高潮(强度10) ← 超预期

自动调整:
  第16章: 类型 打脸→铺垫 (缓冲)
  
日志: "承接15章高强度后的缓冲"
```

## 生成的数据文件

```
小说项目/
└── 我的神豪人生/
    ├── emotion_framework.json      # 全书情绪框架
    │   {
    │       "total_chapters": 100,
    │       "template_source": "神豪文经典节奏",
    │       "arcs": [
    │           {"arc_name": "起-系统觉醒", "start_ch": 1, "end_ch": 10, ...},
    │           {"arc_name": "承-快速升级", "start_ch": 11, "end_ch": 30, ...},
    │           ...
    │       ],
    │       "scaled_curve": [...]  # 按比例缩放后的曲线
    │   }
    │
    ├── chapters/
    │   ├── chapter_001.json
    │   │   {
    │   │       "chapter_number": 1,
    │   │       "title": "第1章 系统觉醒",
    │   │       "content": "...",
    │   │       "emotion_target": {         # 规划的情绪
    │   │           "type": "转折",
    │   │           "target_emotion": "压抑→震惊",
    │   │           "intensity": 8
    │   │       },
    │   │       "emotion_actual": {         # 实际达成的情绪
    │   │           "actual_emotion": "压抑→震惊",
    │   │           "intensity": 8,
    │   │           "hook": "系统即将激活"
    │   │       }
    │   │   }
    │   └── ...
    │
    └── emotion_history.json        # 情绪历史记录（可选）
```

## 与状态管理器的关系

```
状态管理器(BurstStateManager)
    ├─ 管理：主角状态、NPC关系、世界事件（基础一致性）
    └─ 提供给：System Prompt的基础设定

情绪规划器(DynamicEmotionPlanner)
    ├─ 管理：情绪节奏、爽点规划、偏差调整（爆款节奏）
    └─ 提供给：每章的情绪目标

批量生成器(BatchChapterGenerator)
    ├─ 整合：状态 + 情绪
    └─ 输出：符合设定的、节奏正确的章节
```

## 关键优势

| 问题 | 旧方案 | 新方案（动态情绪规划） |
|------|--------|----------------------|
| 只规划前30章 | ✗ 后面没规划 | ✓ 全书100章框架 |
| 情绪偏离 | ✗ 无视 | ✓ 自动检测并补偿 |
| 批次衔接 | ✗ 可能断裂 | ✓ 基于实际生成调整 |
| 节奏来源 | ✗ 自己编 | ✓ 爆款书模板 |
| 爽点强度 | ✗ 随机 | ✓ 递增规划+偏差补偿 |

现在系统可以：**学习爆款书的情绪曲线，动态规划全书，实时调整偏差**。
