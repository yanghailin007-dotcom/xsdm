# 动态情绪曲线管理方案

## 核心问题

### 现状问题
1. 只规划前30章，后面70章怎么办？
2. 实际生成偏离规划（比如第5章应该爽但没爽起来），后续怎么调整？
3. 不同批次（1-10章, 11-20章...）之间情绪如何衔接？

### 解决思路
**不是一次性规划，而是动态规划+滚动调整**

```
初始化：规划全书100章大框架（粗粒度）
    ↓
每批次开始前：基于实际生成情况，细化下10章规划
    ↓
每章生成后：对比预期vs实际，调整后续规划
```

---

## 一、三层规划体系

### Layer 1: 全书大框架（粗粒度，不变）
```python
MASTER_FRAMEWORK = {
    "total_chapters": 100,
    "arcs": [
        {
            "arc_name": "起-系统觉醒",
            "chapters": "1-10",
            "emotion_target": "压抑→希望→小爽",
            "major_slap": [3, 8],  # 大爽点位置
            "arc_goal": "建立系统，初步打脸"
        },
        {
            "arc_name": "承-快速升级", 
            "chapters": "11-30",
            "emotion_target": "持续爽快+期待",
            "major_slap": [15, 20, 28],
            "arc_goal": "实力提升，建立势力"
        },
        {
            "arc_name": "转-大高潮",
            "chapters": "31-60", 
            "emotion_target": "震惊+满足",
            "major_slap": [35, 45, 55],
            "arc_goal": "全国直播，身份登顶"
        },
        {
            "arc_name": "合-终极之战",
            "chapters": "61-100",
            "emotion_target": "终极爽快+圆满",
            "major_slap": [70, 85, 95],
            "arc_goal": "终极BOSS，完美结局"
        }
    ]
}
```

### Layer 2: 批次细规划（10章为单位，每批次前调整）
```python
BATCH_PLAN = {
    "batch_id": 3,  # 第3批次（21-30章）
    "chapters": "21-30",
    "based_on_framework": "承-快速升级",
    
    # 基于实际生成调整的细规划
    "chapter_plans": [
        {"ch": 21, "type": "铺垫", "target": "期待", "intensity": 5, 
         "adjustment_reason": "前一批次第20章大高潮后需要冷却"},
        {"ch": 22, "type": "推进", "target": "好奇", "intensity": 6},
        {"ch": 23, "type": "打脸", "target": "爽快", "intensity": 7, 
         "scene": "商场冲突", "target_npc": "富二代A"},
        # ...
        {"ch": 28, "type": "大高潮", "target": "震惊", "intensity": 9,
         "scene": "拍卖会", "target_npc": "首富", "shock_range": "全市"}
    ],
    
    # 与下一批次的衔接规划
    "transition_to_next": "第30章结尾埋下全国大赛的伏笔"
}
```

### Layer 3: 单章微调（实时调整）
```python
# 第23章生成后，发现实际情绪强度只有5（预期7）
ACTUAL_CH23 = {
    "expected": {"emotion": "爽快", "intensity": 7},
    "actual": {"emotion": "爽快", "intensity": 5},
    "deviation": -2
}

# 自动调整后续规划
ADJUSTED_PLAN = {
    "ch24": {"original_intensity": 6, "adjusted_intensity": 7, 
             "reason": "弥补23章强度不足"},
    "ch25": {"original_type": "铺垫", "adjusted_type": "打脸",
             "reason": "需要提前释放爽点"}
}
```

---

## 二、动态规划流程

### 流程图
```
初始化全书框架
    ↓
生成批次1 (1-10章)
    ├─ 每章生成 → 记录实际情绪
    ├─ 对比预期vs实际
    └─ 实时调整后续1-2章
    ↓
批次1完成 → 分析偏差
    ├─ 如果整体偏离：调整批次2规划
    └─ 生成批次2细规划 (11-20章)
    ↓
生成批次2 (11-20章)
    ├─ 同样流程...
    ↓
批次2完成 → 分析偏差 → 调整批次3...
```

### 代码实现
```python
class DynamicEmotionPlanner:
    """动态情绪规划器"""
    
    def __init__(self, state_manager: BurstStateManager):
        self.state_manager = state_manager
        self.master_framework = None
        self.current_batch_plan = None
        
    def init_master_framework(self, total_chapters: int, tropes: Dict):
        """初始化全书大框架"""
        # 基于套路和总章节数，生成粗粒度框架
        self.master_framework = self._generate_framework(total_chapters, tropes)
        self.state_manager.save_master_framework(self.master_framework)
    
    def plan_next_batch(self, batch_start: int, batch_size: int = 10) -> Dict:
        """规划下一批次（在批次开始前调用）"""
        batch_end = min(batch_start + batch_size - 1, 
                       self.master_framework['total_chapters'])
        
        # 1. 获取大框架中本批次的定位
        arc_info = self._get_arc_for_chapter(batch_start)
        
        # 2. 分析前一批次的偏差（如果有）
        previous_deviation = self._analyze_previous_batch(batch_start - 1)
        
        # 3. 基于框架+偏差，生成细规划
        batch_plan = self._generate_batch_plan(
            start=batch_start,
            end=batch_end,
            arc_target=arc_info['emotion_target'],
            major_slap_positions=arc_info['major_slap'],
            deviation_adjustment=previous_deviation
        )
        
        self.current_batch_plan = batch_plan
        return batch_plan
    
    def adjust_after_chapter(self, chapter_num: int, actual_emotion: Dict):
        """每章生成后调整后续规划"""
        # 找到本章的规划
        planned = self._get_planned_emotion(chapter_num)
        
        # 计算偏差
        deviation = self._calculate_deviation(planned, actual_emotion)
        
        if abs(deviation['intensity_diff']) >= 2:
            # 强度偏差大，调整后续1-2章
            self._adjust_next_chapters(chapter_num + 1, deviation)
        
        if deviation['emotion_mismatch']:
            # 情绪类型不匹配，调整后续3章
            self._adjust_emotion_trajectory(chapter_num + 1, actual_emotion)
        
        # 保存调整记录
        self.state_manager.record_adjustment(chapter_num, deviation)
    
    def _adjust_next_chapters(self, next_ch: int, deviation: Dict):
        """调整后续章节"""
        adjustment = deviation['intensity_diff']
        
        # 如果本章偏弱，下章加强
        if adjustment < 0:
            for i in range(3):  # 调整下3章
                ch = next_ch + i
                if ch in self.current_batch_plan['chapter_plans']:
                    plan = self.current_batch_plan['chapter_plans'][ch]
                    plan['intensity'] = min(10, plan.get('intensity', 5) + abs(adjustment) // 2)
                    plan['adjustment_note'] = f"补偿{next_ch-1}章强度不足"
        
        # 如果本章偏强，下章适当降低（避免疲劳）
        else:
            for i in range(2):
                ch = next_ch + i
                if ch in self.current_batch_plan['chapter_plans']:
                    plan = self.current_batch_plan['chapter_plans'][ch]
                    plan['intensity'] = max(3, plan.get('intensity', 5) - 1)
                    plan['adjustment_note'] = f"承接{next_ch-1}章高强度后的缓冲"
```

---

## 三、仿写情绪曲线（基于爆款书）

### 核心思路
**不只是自己规划，还要学习爆款书的情绪曲线**

```python
class EmotionImitationEngine:
    """情绪曲线仿写引擎"""
    
    def analyze_burst_novel(self, novel_text: str) -> Dict:
        """
        分析爆款小说的情绪曲线
        输入：爆款书的分章节文本
        输出：情绪曲线模板
        """
        chapters = self._split_chapters(novel_text)
        
        emotion_curve = []
        for i, ch_text in enumerate(chapters):
            emotion = self._analyze_chapter_emotion(ch_text)
            emotion_curve.append({
                "ch": i + 1,
                "emotion": emotion['type'],  # 压抑/爽/震惊/期待...
                "intensity": emotion['intensity'],  # 1-10
                "hook_type": emotion['hook_type'],  # 悬念/期待/震惊
                "key_event": emotion['key_event']  # 关键事件
            })
        
        # 提取模式
        pattern = self._extract_emotion_pattern(emotion_curve)
        
        return {
            "raw_curve": emotion_curve,
            "pattern": pattern,
            "applicable_genres": self._detect_genres(novel_text)
        }
    
    def apply_pattern(self, pattern: Dict, target_chapters: int) -> Dict:
        """
        将爆款书的情绪模式应用到新书
        """
        # 按比例缩放
        scale_factor = target_chapters / len(pattern['raw_curve'])
        
        adapted_curve = []
        for point in pattern['raw_curve']:
            adapted_ch = int(point['ch'] * scale_factor)
            adapted_curve.append({
                "ch": adapted_ch,
                "emotion": point['emotion'],
                "intensity": point['intensity'],
                "hook_type": point['hook_type'],
                "adapted_from": point['ch']  # 记录来源
            })
        
        return adapted_curve


# 使用示例
imitation = EmotionImitationEngine()

# 分析《开局物价贬值百万倍》前50章的情绪曲线
burst_pattern = imitation.analyze_burst_novel(
    novel_text=load_novel("开局物价贬值百万倍.txt"),
    chapters=50
)

# 应用到新书（100章）
new_curve = imitation.apply_pattern(burst_pattern, target_chapters=100)

# 保存为模板
save_template("神豪文情绪曲线模板_v1.json", new_curve)
```

### 情绪曲线模板库
```python
EMOTION_TEMPLATES = {
    "神豪文-花钱返利类": {
        "source": "开局物价贬值百万倍",
        "curve": [
            {"ch": 1, "emotion": "压抑→震惊", "intensity": 8, "event": "系统觉醒"},
            {"ch": 3, "emotion": "爽快", "intensity": 6, "event": "第一次花钱"},
            {"ch": 5, "emotion": "爽快", "intensity": 7, "event": "第一次打脸"},
            {"ch": 10, "emotion": "震惊", "intensity": 8, "event": "身份小曝光"},
            {"ch": 15, "emotion": "大爽快", "intensity": 9, "event": "拍卖会打脸"},
            # ...
        ],
        "pattern_rules": [
            "每3章一个小爽点",
            "每10章一个身份升级",
            "第1章必须压抑到极点",
            "第3章必须第一次打脸"
        ]
    },
    
    "国运文-直播类": {
        "source": "国运：开局扮演酒剑仙",
        "curve": [
            {"ch": 1, "emotion": "紧张→希望", "intensity": 8, "event": "被选召"},
            {"ch": 2, "emotion": "期待→爽快", "intensity": 7, "event": "首次扮演"},
            {"ch": 3, "emotion": "震惊", "intensity": 8, "event": "全国震惊"},
            # ...
        ],
        "pattern_rules": [
            "直播元素每章都要有",
            "弹幕反应分层描写",
            "国运具现要震撼"
        ]
    }
}
```

---

## 四、实际使用流程

### 初始化阶段
```python
# 1. 选择情绪曲线模板
template = EMOTION_TEMPLATES["神豪文-花钱返利类"]

# 2. 应用到本书（100章）
planner = DynamicEmotionPlanner(state_manager)
planner.init_from_template(template, total_chapters=100)

# 3. 生成全书大框架
planner.init_master_framework(total_chapters=100, tropes=tropes)
```

### 批次生成阶段
```python
for batch_start in range(1, 101, 10):  # 1, 11, 21, ...
    # 1. 批次开始前：规划下10章
    batch_plan = planner.plan_next_batch(batch_start, batch_size=10)
    
    # 2. 生成这10章
    for ch in range(batch_start, batch_start + 10):
        # 获取本章情绪目标
        emotion_target = batch_plan['chapter_plans'][ch]
        
        # 生成章节（把情绪目标传入Prompt）
        chapter_data = generator.generate_with_emotion_target(ch, emotion_target)
        
        # 记录实际情绪
        actual_emotion = chapter_data['emotion_result']
        
        # 调整后续规划
        planner.adjust_after_chapter(ch, actual_emotion)
    
    # 3. 批次完成后：分析并调整下一批次
    planner.analyze_batch_completion(batch_start)
```

---

## 五、关键改进点

| 方面 | 旧方案 | 新方案（动态+仿写） |
|------|--------|-------------------|
| 规划范围 | 只前30章 | 全书100章大框架 |
| 调整频率 | 不调整 | 每章实时调整 |
| 规划精度 | 固定 | 粗框架→细规划→单章微调 |
| 情绪来源 | 自己编 | 学习爆款书情绪曲线 |
| 偏差处理 | 无视 | 实时检测并补偿 |
| 批次衔接 | 可能断裂 | 基于实际生成调整下批次 |

这个方案的核心：**不是一次性完美规划，而是动态学习、实时调整、基于爆款**。
