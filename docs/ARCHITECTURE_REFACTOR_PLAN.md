# 架构重构计划：外挂式场景拆分器

**状态**: 设计完成，待实施  
**最后更新**: 2026-03-14

---

## 1. 核心理念：WHAT-HOW 分离 + 外挂式拆分器

```
┌─────────────────────────────────────────────────────────────────┐
│                      阶段一：骨架规划 (WHAT)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  重大事件骨架 (Major Event Skeleton)                      │   │
│  │  • 事件名称、范围、核心冲突、目标、角色槽位建议              │   │
│  │  • 可选：调用场景拆分器进行预拆分（默认不拆分）              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 生成骨架
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ★ 外挂式场景拆分器 (Scene Splitter) ★          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 拆分策略配置 │  │ 节奏模板选择 │  │ 批量生成策略 │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                    ┌─────▼─────┐                                │
│                    │ 拆分执行器 │  ← 可被阶段一或阶段二调用        │
│                    └─────┬─────┘                                │
│                          │                                      │
│                    输出：场景列表（带节奏标记+批量批次）            │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  番茄节奏模板    │  │  起点节奏模板    │  │  自定义模板      │
│  (脉冲式)       │  │  (传统渐进)      │  │  (感情线/悬疑)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      阶段二：内容生成 (HOW)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  默认行为：调用场景拆分器 → 批量生成 → 组装章节            │   │
│  │  灵活模式：可直接使用阶段一预拆分结果                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 为什么采用外挂式设计？

### 2.1 解决的核心问题

| 问题 | 原架构 | 新架构 |
|------|--------|--------|
| 节奏控制不精细 | 阶段一预拆分时固定节奏 | 阶段二根据平台动态选择节奏模板 |
| 平台适配困难 | 阶段一写死番茄风格 | 拆分器支持多模板，按需切换 |
| 错误无法修正 | 阶段一错误传导到阶段二 | 阶段二可重新拆分，隔离错误 |
| 策略僵化 | 绑定在阶段一 | 外挂组件，可被任意阶段调用 |

### 2.2 架构优势

```
灵活性维度：
├─ 调用时机灵活：阶段一(可选) / 阶段二(默认) / 实时重拆分
├─ 策略组合灵活：番茄/起点/自定义 × 粗粒度/细粒度 × 批量/逐一生成
├─ 扩展性灵活：新增平台只需添加模板，无需改核心逻辑
└─ 降级灵活：拆分器故障可回退到简单映射模式
```

---

## 3. 场景拆分器详细设计

### 3.1 模块结构

```python
src/core/scene_splitter/
├── __init__.py              # 主入口：SceneSplitter
├── models.py                # 数据模型：Scene, RhythmPattern, BatchConfig
├── strategies/              # 拆分策略
│   ├── __init__.py
│   ├── base.py             # 抽象基类：SplitStrategy
│   ├── fanqie_strategy.py  # 番茄脉冲式
│   ├── qidian_strategy.py  # 起点传统式
│   └── custom_strategy.py  # 自定义模板
├── templates/               # 节奏模板库
│   ├── fanqie_pulse.json   # 番茄：强钩子+快节奏
│   ├── qidian_classic.json # 起点：渐进式+伏笔
│   └── romance_arc.json    # 感情线：心动节奏
├── batch_optimizer.py       # 批量生成优化器
└── config.py               # 配置管理
```

### 3.2 核心接口设计

```python
# src/core/scene_splitter/__init__.py

from typing import List, Optional, Dict, Literal
from dataclasses import dataclass

@dataclass
class Scene:
    """拆分后的场景"""
    scene_id: str              # 唯一标识
    event_ref: str             # 关联的重大事件
    scene_type: str            # 场景类型：hook/conflict/develop/resolve/cliff
    rhythm_pattern: str        # 节奏模板名称
    word_count_target: int     # 目标字数
    suspense_level: int        # 悬念等级 1-5
    emotion_direction: str     # 情绪走向
    batch_group: int           # 批量生成批次号
    
@dataclass  
class SplitConfig:
    """拆分配置"""
    platform: Literal["fanqie", "qidian", "custom"]  # 目标平台
    granularity: Literal["coarse", "fine", "auto"]   # 拆分粒度
    batch_size: int                                    # 每批场景数
    rhythm_template: Optional[str] = None              # 指定节奏模板
    golden_arc_mode: bool = False                      # 黄金三章模式

class SceneSplitter:
    """
    外挂式场景拆分器
    
    可被以下场景调用：
    1. 阶段一：用户选择"详细规划"模式时预拆分
    2. 阶段二：默认调用进行动态拆分
    3. 重生成：章节质量不达标时重新拆分
    """
    
    def __init__(self, config: SplitConfig):
        self.config = config
        self.strategy = self._load_strategy()
    
    def split(
        self, 
        major_events: List[Dict],
        stage_context: Dict,
        chapter_position: int
    ) -> List[Scene]:
        """
        拆分重大事件为场景列表
        
        Args:
            major_events: 重大事件骨架列表
            stage_context: 阶段上下文（世界观、角色、已生成内容）
            chapter_position: 当前章节位置（用于黄金三章判断）
            
        Returns:
            场景列表（已按批量批次分组）
        """
        # 1. 选择节奏模板
        rhythm = self._select_rhythm_template(chapter_position)
        
        # 2. 按策略拆分每个重大事件
        scenes = []
        for event in major_events:
            event_scenes = self.strategy.split_event(event, rhythm)
            scenes.extend(event_scenes)
        
        # 3. 应用黄金三章特殊处理
        if self.config.golden_arc_mode and chapter_position <= 3:
            scenes = self._apply_golden_arc_rules(scenes)
        
        # 4. 批量批次优化
        batches = self._optimize_batches(scenes)
        
        return batches
    
    def resplit(
        self,
        original_scenes: List[Scene],
        feedback: Dict,
        adjustment_type: Literal["granularity", "rhythm", "batch_size"]
    ) -> List[Scene]:
        """
        基于反馈重新拆分（用于质量不达标时）
        """
        # 动态调整配置并重新拆分
        pass
```

### 3.3 节奏模板设计

```json
// templates/fanqie_pulse.json
{
  "name": "番茄脉冲式",
  "description": "快节奏强钩子，适合番茄免费模式",
  "platform": "fanqie",
  "rhythm_pattern": [
    {"position": 0.0, "type": "hook", "weight": 1.5, "min_words": 200},
    {"position": 0.2, "type": "conflict", "weight": 1.2, "min_words": 300},
    {"position": 0.5, "type": "develop", "weight": 1.0, "min_words": 400},
    {"position": 0.8, "type": "escalate", "weight": 1.3, "min_words": 300},
    {"position": 1.0, "type": "cliff", "weight": 1.5, "min_words": 200}
  ],
  "batch_rules": {
    "max_scenes_per_chapter": 5,
    "preferred_batch_size": 3,
    "min_scenes_for_batch": 2
  }
}

// templates/qidian_classic.json
{
  "name": "起点传统式", 
  "description": "渐进式节奏，注重伏笔和世界构建",
  "platform": "qidian",
  "rhythm_pattern": [
    {"position": 0.0, "type": "setup", "weight": 1.0, "min_words": 300},
    {"position": 0.3, "type": "develop", "weight": 1.0, "min_words": 400},
    {"position": 0.6, "type": "conflict", "weight": 1.2, "min_words": 400},
    {"position": 0.9, "type": "resolve", "weight": 1.0, "min_words": 300},
    {"position": 1.0, "type": "transition", "weight": 0.8, "min_words": 200}
  ],
  "batch_rules": {
    "max_scenes_per_chapter": 4,
    "preferred_batch_size": 2,
    "min_scenes_for_batch": 2
  }
}
```

---

## 4. 与现有系统集成

### 4.1 阶段一集成（可选预拆分）

```python
# src/managers/stage_plan/planning_manager.py

class PlanningManager:
    async def generate_detailed_plan(
        self, 
        plan_id: str,
        split_scenes: bool = False,  # 新增参数：是否预拆分
        split_config: Optional[SplitConfig] = None
    ):
        """
        生成详细规划
        
        Args:
            split_scenes: 是否调用场景拆分器预拆分（默认False）
            split_config: 拆分配置（split_scenes=True时需要）
        """
        # 1. 生成重大事件骨架
        major_events = await self._generate_major_events(plan_id)
        
        if split_scenes:
            # 2. 可选：调用场景拆分器
            splitter = SceneSplitter(split_config)
            scenes = splitter.split(
                major_events=major_events,
                stage_context=await self._get_stage_context(plan_id),
                chapter_position=0  # 阶段一不确定具体章节位置
            )
            # 3. 存储预拆分结果
            await self._save_pre_split_scenes(plan_id, scenes)
        
        return {"major_events": major_events, "pre_split": split_scenes}
```

### 4.2 阶段二集成（默认调用）

```python
# src/core/content_generation/stage_generator.py

class StageGenerator:
    async def generate_chapter(
        self,
        task: GenerationTask,
        platform: str = "fanqie"
    ) -> Chapter:
        """生成章节 - 重构后版本"""
        
        # 1. 获取重大事件骨架
        major_events = await self._get_major_events(task.plan_id, task.chapter_num)
        
        # 2. ★ 调用场景拆分器（默认行为）
        splitter = SceneSplitter(SplitConfig(
            platform=platform,
            granularity="auto",
            batch_size=self._get_optimal_batch_size(task),
            golden_arc_mode=task.chapter_num <= 3
        ))
        
        scenes = splitter.split(
            major_events=major_events,
            stage_context=await self._build_context(task),
            chapter_position=task.chapter_num
        )
        
        # 3. 按批次生成场景内容
        chapter_content = []
        for batch_num in range(1, max(s.batch_group for s in scenes) + 1):
            batch_scenes = [s for s in scenes if s.batch_group == batch_num]
            batch_content = await self._generate_scene_batch(
                batch_scenes, 
                task,
                rhythm_template=scenes[0].rhythm_pattern
            )
            chapter_content.extend(batch_content)
        
        # 4. 组装章节
        return self._assemble_chapter(chapter_content, scenes)
```

---

## 5. 实施路线图

### Phase 1: 场景拆分器核心（3周）

**Week 1: 基础架构**
```
- [ ] 创建 scene_splitter/ 模块结构
- [ ] 实现核心数据模型 (Scene, SplitConfig)
- [ ] 实现策略基类和策略加载器
- [ ] 编写单元测试框架
```

**Week 2: 节奏模板**
```
- [ ] 设计番茄脉冲模板 (fanqie_pulse.json)
- [ ] 设计起点传统模板 (qidian_classic.json)
- [ ] 实现模板加载和验证
- [ ] 实现节奏应用逻辑
```

**Week 3: 批量优化**
```
- [ ] 实现批量批次优化器
- [ ] 集成到阶段二生成流程
- [ ] 端到端测试
- [ ] 性能基准测试
```

### Phase 2: 阶段一简化（2周）

**Week 4-5: 重构阶段一**
```
- [ ] 修改规划生成器，只输出骨架
- [ ] 添加可选预拆分开关
- [ ] 迁移存量数据格式
- [ ] 回归测试
```

### Phase 3: 高级功能（3周）

**Week 6-8: 增强功能**
```
- [ ] 黄金三章特殊处理
- [ ] 基于质量反馈的动态重拆分
- [ ] 自定义模板编辑器
- [ ] A/B测试框架
```

### Phase 4: 稳定化（2周）

**Week 9-10: 生产就绪**
```
- [ ] 灰度发布策略
- [ ] 监控和告警
- [ ] 文档完善
- [ ] 全量上线
```

**总工期：10周**

---

## 6. 关键决策点

### 决策1：阶段一默认行为
- **选项A**: 阶段一不拆分（纯骨架），所有拆分在阶段二（推荐）
- **选项B**: 阶段一提供"详细模式"可选预拆分
- **选项C**: 保持现状，阶段一粗拆分 + 阶段二精拆分

**建议**：选项A，保持架构简洁，阶段二全权负责HOW

### 决策2：拆分器部署方式
- **选项A**: 进程内库（当前设计）
- **选项B**: 独立服务（未来可扩展为微服务）
- **选项C**: 混合模式（默认进程内，可配置为服务）

**建议**：选项A起步，预留选项C的接口

### 决策3：存量数据处理
- **选项A**: 自动迁移（读取时转换格式）
- **选项B**: 冻结存量，新计划使用新架构
- **选项C**: 批量脚本迁移

**建议**：选项A，向后兼容

---

## 7. 文件变更清单

### 新增文件
```
src/core/scene_splitter/
├── __init__.py
├── models.py
├── base.py
├── strategies/
│   ├── __init__.py
│   ├── base.py
│   ├── fanqie_strategy.py
│   ├── qidian_strategy.py
│   └── custom_strategy.py
├── templates/
│   ├── fanqie_pulse.json
│   ├── qidian_classic.json
│   └── romance_arc.json
├── batch_optimizer.py
└── config.py
tests/core/scene_splitter/
├── test_splitter.py
├── test_strategies.py
└── test_templates.py
```

### 修改文件
```
src/managers/stage_plan/planning_manager.py      # 添加可选预拆分
src/core/content_generation/stage_generator.py   # 集成场景拆分器
src/core/content_generation/chapter_generator.py # 使用拆分结果
config/scene_splitter.yaml                       # 拆分器配置
```

### 删除/废弃
```
# 原阶段一预拆分逻辑（迁移到场景拆分器）
# 原节奏控制代码（被模板替代）
```

---

## 8. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 拆分质量不稳定 | 中 | 高 | 功能开关 + 快速回退机制 |
| 性能下降 | 低 | 中 | 缓存拆分结果 + 异步预加载 |
| 模板不适用 | 中 | 中 | 多模板备选 + 自定义模板 |
| 学习成本 | 低 | 低 | 完善文档 + 示例代码 |

---

## 9. 成功指标

1. **质量指标**
   - 章节质量评分 > 8.0 的比例提升 10%
   - 字数达标率 > 95%

2. **效率指标**
   - 阶段二 API 调用次数减少 20-30%
   - 单章生成时间减少 15%

3. **灵活性指标**
   - 新增平台适配时间 < 1周
   - 切换节奏模板时间 < 1天

---

**下一步**: 确认决策点后，开始 Phase 1 实施
