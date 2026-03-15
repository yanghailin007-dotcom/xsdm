# 番茄爆款叙事优化方案

## 一、当前系统与番茄套路的映射分析

### 1.1 已实现的对应功能

| 番茄套路要素 | 当前系统实现 | 匹配度 |
|-------------|-------------|--------|
| **情绪蓝图** | `emotional_blueprint` - 全书情绪曲线规划 | ✅ 85% |
| **期待感映射** | `expectation_mapping` - 事件期待感标签系统 | ✅ 80% |
| **阶段规划** | `stage_plan` - 起承转合四段式 | ✅ 75% |
| **黄金开局** | `golden_opening` - 1-3章整体生成 | ✅ 70% |
| **事件系统** | `major_events` + `medium_events` 层级结构 | ✅ 65% |

### 1.2 核心差距识别

```
番茄爆款核心公式：[快-爽-期]三位一体
                    ↓
当前系统薄弱点：
├── 快：章节级节奏控制不足（只有阶段级）
├── 爽：打脸/反转的精细化设计缺失
└── 期：钩子密度和留存策略不够系统
```

---

## 二、关键改进模块

### 2.1 新增：「五章循环」节奏引擎

**现状问题**：
- 当前只有 `major_events`（重大事件）和 `medium_events`（中型事件）两级
- 缺少章节级的微节奏控制

**改进方案**：

```python
# 新增：ChapterRhythmEngine 章节节奏引擎
class ChapterRhythmEngine:
    """
    五章循环节奏控制器
    每5章必须完成一个情绪过山车周期
    """
    
    RHYTHM_PATTERN = {
        1: {"beat": "trigger", "emotion": "curiosity"},      # 触发事件
        2: {"beat": "engagement", "emotion": "tension"},     # 参与但不露底
        3: {"beat": "escalation", "emotion": "suppression"}, # 矛盾加深/嘲讽
        4: {"beat": "payoff", "emotion": "catharsis"},       # 打脸/碾压
        5: {"beat": "hook", "emotion": "anticipation"}       # 震惊+新钩子
    }
    
    def design_chapter_cluster(self, start_chapter: int, context: Dict) -> List[Dict]:
        """
        设计5章节奏单元
        返回：5个章节的设计概要
        """
        cluster = []
        for offset, pattern in self.RHYTHM_PATTERN.items():
            chapter_num = start_chapter + offset - 1
            chapter_design = {
                "chapter_number": chapter_num,
                "beat_type": pattern["beat"],
                "target_emotion": pattern["emotion"],
                "must_include": self._get_beat_requirements(pattern["beat"]),
                "scene_focus": self._get_scene_suggestions(pattern["beat"])
            }
            cluster.append(chapter_design)
        return cluster
```

**数据结构调整**：
```json
{
  "stage_writing_plan": {
    "chapter_clusters": [
      {
        "cluster_id": "opening_cluster_1",
        "chapters": "1-5",
        "rhythm_pattern": "五章循环",
        "beat_sequence": ["trigger", "engagement", "escalation", "payoff", "hook"],
        "expectation_management": {
          "chapter_3_end": "悬念钩子 - 反派放狠话",
          "chapter_4_peak": "打脸反转 - 底牌亮出",
          "chapter_5_end": "新钩子 - 更大的危机浮现"
        }
      }
    ]
  }
}
```

---

### 2.2 增强：「期待感」量化系统

**现状问题**：
- 期待感映射只有类型标签（SHOWCASE, CRISIS_RESCUE等）
- 缺少期待感的量化指标和密度控制

**改进方案**：

```python
class ExpectationMetrics:
    """
    期待感量化指标系统
    """
    
    # 番茄爆款期待感密度标准
    DENSITY_STANDARD = {
        "golden_3_chapters": {  # 黄金3章
            "min_hooks": 3,      # 至少3个钩子
            "urgency_score": 8,   # 紧迫感≥8分
            "cliffhanger": True   # 章章断 cliffhanger
        },
        "opening_stage": {      # 开局阶段(1-30章)
            "hook_interval": 3,   # 每3章一个钩子
            "payoff_ratio": 0.3,  # 兑现/铺垫比例 3:7
            "anticipation_score": 7.5
        },
        "climax_stage": {       # 高潮阶段
            "hook_interval": 1,   # 章章有钩子
            "payoff_ratio": 0.5,  # 兑现/铺垫比例 5:5
            "anticipation_score": 9.0
        }
    }
    
    def calculate_anticipation_score(self, chapter_plan: Dict) -> Dict:
        """
        计算单章期待感评分
        """
        metrics = {
            "hook_count": self._count_hooks(chapter_plan),
            "unresolved_tension": self._measure_tension(chapter_plan),
            "desire_gap": self._calculate_desire_gap(chapter_plan),
            "cliffhanger_strength": self._evaluate_cliffhanger(chapter_plan)
        }
        
        total_score = (
            metrics["hook_count"] * 2 +
            metrics["unresolved_tension"] * 1.5 +
            metrics["desire_gap"] * 2.5 +
            metrics["cliffhanger_strength"] * 2
        ) / 8
        
        return {
            "total_score": round(total_score, 1),
            "metrics": metrics,
            "suggestions": self._generate_optimization_suggestions(metrics)
        }
```

**期待感类型扩展**：
```python
# 新增番茄爆款专用期待感类型
TOMATO_EXPECTATION_TYPES = {
    "FACE_SLAP_SETUP": {        # 打脸铺垫
        "description": "反派嚣张嘲讽，主角隐忍不发",
        "delay_chapters": "2-3",  # 延迟兑现章节数
        "emotion_peak": "catharsis"
    },
    "IDENTITY_CONCEALMENT": {   # 身份隐藏
        "description": "真实身份差一步暴露",
        "delay_chapters": "5-10",
        "emotion_peak": "shock"
    },
    "WEALTH_TEASE": {          # 财力展示
        "description": "神豪财力永远差一步展示",
        "delay_chapters": "3-5",
        "emotion_peak": "awe"
    },
    "RELATIONSHIP_AMBIGUITY": { # 暧昧不推
        "description": "差一步确认关系",
        "delay_chapters": "10-20",
        "emotion_peak": "yearning"
    },
    "CRISIS_ESCALATION": {     # 危机升级
        "description": "解决一个又来一个更大的",
        "delay_chapters": "1-2",
        "emotion_peak": "tension"
    }
}
```

---

### 2.3 新增：「可视化冲突」场景设计器

**现状问题**：
- 场景描述偏重于"发生了什么"
- 缺少"画面感"和"切片镜头"设计

**改进方案**：

```python
class VisualConflictDesigner:
    """
    可视化冲突场景设计器
    每个关键场景必须设计3个「切片镜头」
    """
    
    CONFLICT_TEMPLATES = {
        "PUBLIC_HUMILIATION": {  # 当众打脸
            "visual_beats": [
                "反派居高临下的姿态特写",
                "众人嘲讽的群像反应",
                "主角不动声色的小动作"
            ],
            "reversal_moment": "底牌亮出的视觉冲击",
            "crowd_reaction": "从嘲讽到震惊的连续特写"
        },
        "IDENTITY_REVEAL": {    # 身份揭露
            "visual_beats": [
                "信物/标志物的特写",
                "反派从傲慢到惊恐的表情变化",
                "全场寂静的凝固画面"
            ],
            "reversal_moment": "身份确认的仪式感",
            "crowd_reaction": "跪拜/颤抖的夸张反应"
        },
        "SYSTEM_ACTIVATION": {  # 系统觉醒
            "visual_beats": [
                "濒死状态的绝望画面",
                "系统界面浮现的视觉特效",
                "身体变化的外在表现"
            ],
            "reversal_moment": "第一次使用能力的碾压效果",
            "crowd_reaction": "难以置信的眼神"
        }
    }
    
    def design_conflict_scene(self, conflict_type: str, context: Dict) -> Dict:
        """
        设计冲突场景的可视化分镜
        """
        template = self.CONFLICT_TEMPLATES.get(conflict_type)
        
        scene_design = {
            "conflict_type": conflict_type,
            "visual_beats": template["visual_beats"],
            "reversal_moment": {
                "description": template["reversal_moment"],
                "dialogue_requirements": "简短有力，不超过15字",
                "action_requirements": "压倒性的视觉冲击"
            },
            "crowd_reaction": template["crowd_reaction"],
            "douyin_slice": self._generate_short_video_slices(template)
        }
        
        return scene_design
```

---

### 2.4 新增：「情绪代餐」检测系统

**现状问题**：
- 有情绪蓝图，但缺少对读者情绪需求的精准匹配
- 缺少对现实情绪痛点的映射

**改进方案**：

```python
class EmotionalSubstituteMapper:
    """
    情绪代餐映射系统
    将读者现实痛点映射为小说情绪供给
    """
    
    # 情绪代餐映射表
    PAIN_POINT_MENU = {
        "work_frustration": {           # 职场憋屈
            "novel_substitute": "主角永远不受气，当场打脸",
            "scene_frequency": "每3章至少1次",
            "intensity_requirement": "打脸必须干脆利落，不拖泥带水"
        },
        "growth_anxiety": {             # 成长焦虑
            "novel_substitute": "系统/金手指=确定性成长",
            "scene_frequency": "每章都有能力提升的爽点",
            "intensity_requirement": "数值化展示，清晰可见"
        },
        "emotional_lack": {             # 情感匮乏
            "novel_substitute": "多女主暧昧+被倒追",
            "scene_frequency": "每5章至少1次暧昧互动",
            "intensity_requirement": "被追求，而非主动追求"
        },
        "powerlessness": {              # 无力感
            "novel_substitute": "无敌文=掌控一切的权力幻想",
            "scene_frequency": "核心冲突中主角永远掌控全局",
            "intensity_requirement": "俯视视角，降维打击"
        },
        "social_status": {              # 地位焦虑
            "novel_substitute": "身份反转，从底层到顶层",
            "scene_frequency": "每10章一次身份升级",
            "intensity_requirement": "周围人态度180度转变"
        }
    }
    
    def map_target_audience_pain(self, novel_data: Dict) -> Dict:
        """
        根据小说类型和目标读者，生成情绪代餐方案
        """
        novel_category = novel_data.get("category", "general")
        
        # 不同品类的情绪代餐重点
        CATEGORY_FOCUS = {
            "urban_fantasy": ["work_frustration", "powerlessness"],
            "system_cultivation": ["growth_anxiety", "powerlessness"],
            "romance": ["emotional_lack", "social_status"],
            "face_slap": ["work_frustration", "social_status"],
            "survival_horror": ["powerlessness", "growth_anxiety"]
        }
        
        focus_pains = CATEGORY_FOCUS.get(novel_category, ["work_frustration"])
        
        emotional_menu = {}
        for pain in focus_pains:
            emotional_menu[pain] = self.PAIN_POINT_MENU[pain]
        
        return {
            "target_pain_points": focus_pains,
            "emotional_substitute_plan": emotional_menu,
            "validation_checklist": self._generate_validation_checklist(emotional_menu)
        }
```

---

## 三、Prompt系统优化

### 3.1 新增番茄风格专用Prompt模板

```python
# 新增 Prompt 模板
TOMATO_WRITING_PROMPTS = {
    "golden_3_chapters": """
    【番茄黄金开局 - 前3章硬性要求】
    
    第1章：触发+钩子
    - 300字内必须出现主角
    - 800字内必须出现冲突（挑衅/危机/系统觉醒）
    - 结尾必须留 cliffhanger（悬念/新发现）
    
    第2章：参与+压抑
    - 主角入局但不露底牌
    - 反派/路人嘲讽（为后续打脸铺垫）
    - 主角内心有明确目标（读者知道主角有把握）
    
    第3章：反转+打脸+新钩子
    - 2000字左右必须出现打脸/反转
    - 反转必须干脆利落，不解释太多
    - 结尾必须开启更大的悬念/新副本
    
    【番茄风格禁忌】
    ❌ 不要大段心理描写
    ❌ 不要环境渲染超过200字
    ❌ 不要让主角受委屈超过一章
    ❌ 不要解释设定超过3句话
    
    【番茄风格必须】
    ✅ 对话要短、快、有梗
    ✅ 每500字一个小转折
    ✅ 章章断在 cliffhanger
    ✅ 让读者"骂着真香"（想推剧情又停不下来）
    """,
    
    "face_slap_scene": """
    【打脸场景设计模板】
    
    阶段1：嘲讽铺垫（占20%）
    - 反派居高临下的姿态
    - 路人附和嘲讽
    - 主角沉默/微笑/小动作
    
    阶段2：矛盾激化（占30%）
    - 反派得寸进尺
    - 众人开始同情主角（但不敢帮）
    - 主角准备动作（读者能看到底牌即将亮出）
    
    阶段3：反转打脸（占30%）
    - 底牌亮出，一句话秒杀
    - 反派表情从傲慢→震惊→恐惧的快速变化
    - 全场寂静3秒，然后哗然
    
    阶段4：余波钩子（占20%）
    - 反派跪地/逃窜/求饶
    - 路人态度180度转变
    - 新人物登场/新危机浮现
    
    【关键技巧】
    - 打脸前要让读者"憋屈"够，但不要太久（最多2章）
    - 打脸后不要解释，直接开启新事件
    - 用动作代替心理描写
    """,
    
    "cliffhanger_design": """
    【章末钩子设计指南】
    
    好的 cliffhanger = 让读者必须点下一章
    
    类型1：悬念型
    "就在这时，他看到了一个不可能出现在这里的人——"
    
    类型2：危机型
    "枪声响起，子弹穿透了她的胸口..."
    
    类型3：反转型
    "他恭敬地跪在地上，喊道：'参见少主！'全场哗然。"
    
    类型4：欲望型
    "她红着脸说：'今晚，我一个人在家...'"
    
    【设计要求】
    - 每章结尾必须有 cliffhanger
    - 黄金3章的 cliffhanger 必须是「危机型」或「反转型」
    - 不要在章末解释任何事情
    """
}
```

---

## 四、实施路线图

### Phase 1: 核心引擎（1-2周）

```
优先级：高
├── 实现 ChapterRhythmEngine（五章循环）
├── 扩展 ExpectationManager（期待感量化）
└── 更新 Prompt 模板（番茄风格专用）
```

### Phase 2: 场景系统（2-3周）

```
优先级：高
├── 实现 VisualConflictDesigner
├── 集成到 medium_event 生成流程
└── 添加「切片镜头」输出格式
```

### Phase 3: 情绪系统（3-4周）

```
优先级：中
├── 实现 EmotionalSubstituteMapper
├── 在创意输入阶段增加「目标读者痛点」选项
└── 添加情绪代餐验证检查点
```

### Phase 4: 质量评估（4-5周）

```
优先级：中
├── 新增番茄风格质量检测指标
│   ├── 节奏密度检测（3章打脸率）
│   ├── 期待感密度检测（钩子间隔）
│   └── 可视化冲突检测（场景画面感评分）
└── 质量评估报告增加「番茄爆款潜力分」
```

---

## 五、关键成功指标（KPI）

| 指标 | 当前水平 | 目标水平 | 检测方式 |
|------|---------|---------|---------|
| 3章打脸率 | 未统计 | ≥80% | 自动检测前3章是否出现打脸场景 |
| 章均钩子数 | 未统计 | ≥1.2 | 统计每章结尾悬念/钩子数量 |
| 情绪曲线陡峭度 | 中等 | 高 | 情绪转换间隔≤3章 |
| 场景画面感评分 | 中等 | ≥8/10 | AI评估场景可视化程度 |
| 番茄爆款潜力分 | 无 | ≥75分 | 综合以上指标的计算分数 |

---

## 六、风险与注意事项

1. **避免过度套路化**：
   - 五章循环是框架，不是枷锁
   - 允许20%的章节打破节奏（制造惊喜）

2. **保持类型差异化**：
   - 不同品类（玄幻/都市/悬疑）的五章循环内容不同
   - 不要所有类型都套用"打脸"模板

3. **质量与速度的 balance**：
   - 不要为了"快"牺牲基本的逻辑合理性
   - 番茄风格≠小白文，是"专业的小白文"

---

**文档版本**: v1.0  
**最后更新**: 2026-03-15  
**负责人**: AI Assistant
