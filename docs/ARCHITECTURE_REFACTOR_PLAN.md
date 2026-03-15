# 小说生成系统架构重构计划

## 文档信息
- **版本**: v1.0
- **日期**: 2026-03-15
- **状态**: 设计阶段
- **负责人**: AI Assistant

---

## 一、现状分析

### 1.1 当前架构流程

```
┌─────────────────────────────────────────────────────────────┐
│                     第一阶段：设定生成                         │
├─────────────────────────────────────────────────────────────┤
│  1. 创意精炼                                                │
│  2. 同人检测                                                │
│  3. 方案生成与选择                                           │
│  4. 世界观构建                                               │
│  5. 角色设计                                                 │
│  6. 全书阶段计划                                             │
│  7. 阶段详细计划 ← 问题所在                                   │
│     └── Major Events（重大事件）                              │
│         └── Medium Events（中级事件）← 预生成，过度细化         │
│             └── Scenes（场景）← 预生成，限制灵活性              │
│  8. 补充角色生成                                             │
│  9. 期待感映射                                               │
│  10. 质量评估                                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     第二阶段：内容生成                         │
├─────────────────────────────────────────────────────────────┤
│  基于阶段一预设计的 Medium Events 批量生成章节                   │
│  └── 问题：只能机械执行，无法根据实际效果调整                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心问题

| 问题 | 描述 | 影响 |
|------|------|------|
| **过度预设** | 阶段一就把 Medium Events 和 Scenes 都定死了 | 阶段二失去灵活性，无法动态调整 |
| **平台适配差** | 一套模板通用，无法针对番茄/起点选择不同节奏 | 番茄留存率低，起点节奏过快 |
| **批量生成受限** | 预设计的场景结构限制了批量生成的发挥 | 章间节奏控制困难 |
| **错误传导** | 阶段一的规划错误会一直传导到最终输出 | 质量难以在阶段二修正 |

### 1.3 具体表现

- **黄金开局**：预设计的场景可能不符合番茄快节奏要求
- **批量生成**：2-3章批量时，章间节奏难以控制
- **节奏模板**：起承转合结构不适合脉冲式网文
- **字数控制**：预设计场景字数分配不合理

---

## 二、新架构设计

### 2.1 核心思想

**"规划-细化分离"**：阶段一只做顶层设计，阶段二根据平台、位置、目标动态细化。

```
阶段一：WHAT（做什么）
  └── 重大事件骨架：目标、冲突、情绪方向

阶段二：HOW（怎么做）
  └── 动态拆分：根据平台选择拆分策略
  └── 节奏模板：脉冲/传统/感情线
  └── 批量生成：基于动态设计生成内容
```

### 2.2 新架构流程

```
┌─────────────────────────────────────────────────────────────┐
│                     第一阶段：顶层设计                         │
├─────────────────────────────────────────────────────────────┤
│  【保留不变】                                                │
│  1-6. 创意、检测、方案、世界观、角色、阶段计划                 │
│                                                             │
│  【修改：简化】                                              │
│  7. 重大事件规划（新增）                                      │
│     └── Major Event Skeleton（骨架）                         │
│         ├── name: 事件名称                                   │
│         ├── chapter_range: 章节范围（如1-30）                  │
│         ├── core_conflict: 核心冲突                          │
│         ├── emotional_goal: 情绪目标                         │
│         ├── plot_goal: 剧情目标                              │
│         ├── estimated_events: 预计中级事件数（建议，非固定）     │
│         └── slot_templates: 事件槽位模板（类型建议）           │
│                                                             │
│  【保留不变】                                                │
│  8-10. 补充角色、期待感映射、质量评估                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     第二阶段：动态细化                         │
├─────────────────────────────────────────────────────────────┤
│  【新增：动态拆分器】                                         │
│  1. 根据平台选择拆分策略                                       │
│     ├── 番茄：高频爽点，短事件（1-2章）                        │
│     ├── 起点：可长铺垫（2-5章）                               │
│     └── 晋江：感情线为主（2-3章）                             │
│                                                             │
│  2. 根据章节位置调整粒度                                       │
│     ├── 黄金三章：1章1事件，高密度                             │
│     ├── 开局阶段：2章1事件                                     │
│     ├── 发展阶段：3章1事件                                     │
│     └── 高潮阶段：2章1事件，高强度                             │
│                                                             │
│  3. 选择节奏模板                                              │
│     ├── 脉冲式（番茄）：危机→应对→爆发→收获+钩子              │
│     ├── 传统式（起点）：起→承→转→合                           │
│     └── 感情线（晋江）：偶遇→互动→升温→悬念                   │
│                                                             │
│  【修改：批量生成】                                           │
│  4. 基于动态设计的 Medium Events 批量生成章节                   │
│     └── 批量Prompt根据 rhythm_template 选择不同模板            │
│                                                             │
│  【保留不变】                                                │
│  5. 质量评估与优化                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据结构变更

#### 2.3.1 阶段一输出：Major Event Skeleton（新）

```json
{
  "stage_name": "opening_stage",
  "major_events": [
    {
      "name": "黄泉医院：模拟器初显威",
      "chapter_range": "1-30",
      "core_conflict": "主角被困诡异医院，必须用模拟器能力破解规则生存",
      "emotional_goal": "从恐惧到掌控，建立主角智力 superiority",
      "plot_goal": "获得首个诡异道具，建立医院内的小势力",
      "estimated_medium_events": 4,
      "slot_templates": [
        {
          "type": "trigger_burst",
          "description": "入院即触发死亡规则，用模拟器首次脱险",
          "suggested_chapters": "1-3",
          "emotional_arc": "恐惧→惊险→释放"
        },
        {
          "type": "suppression_reversal", 
          "description": "护士打压，主角反杀立威",
          "suggested_chapters": "4-12",
          "emotional_arc": "憋屈→爆发→震惊"
        },
        {
          "type": "harvest_upgrade",
          "description": "获得诡异道具，能力升级",
          "suggested_chapters": "13-20",
          "emotional_arc": "期待→满足→新目标"
        },
        {
          "type": "exploration_discovery",
          "description": "发现医院隐藏楼层，预告大BOSS",
          "suggested_chapters": "21-30",
          "emotional_arc": "好奇→紧张→更大的危机"
        }
      ],
      "key_elements": ["模拟器", "医院规则", "诡异道具"],
      "ending_hook": "医院只是诡异世界的冰山一角"
    }
  ]
}
```

**与旧版对比**：
- ❌ 旧版：直接包含 `medium_events` 和 `scenes`
- ✅ 新版：只包含 `slot_templates`（建议性），实际拆分延迟到阶段二

#### 2.3.2 阶段二生成：Medium Event（动态）

```json
{
  "name": "入院即危机：模拟器首次激活",
  "chapter_range": "1-3",
  "parent_major_event": "黄泉医院：模拟器初显威",
  "rhythm_template": "pulse",
  "scenes": [
    {
      "sequence": 1,
      "beat": "危机触发",
      "description": "刚入院就触发死亡规则，10分钟倒计时",
      "emotion_target": "恐惧",
      "estimated_words": 600
    },
    {
      "sequence": 2,
      "beat": "能力觉醒",
      "description": "绑定诡异人生模拟器，首次使用试错",
      "emotion_target": "期待",
      "estimated_words": 700
    },
    {
      "sequence": 3,
      "beat": "惊险脱险",
      "description": "利用模拟器找到生路，成功存活",
      "emotion_target": "释放",
      "estimated_words": 700
    }
  ],
  "chapter_hooks": {
    "1": "规则比想象中更危险",
    "2": "院长在监控中注意到了主角",
    "3": "更大的危机正在酝酿"
  }
}
```

**关键变化**：
- `rhythm_template`：明确指定节奏类型
- `chapter_hooks`：每章钩子强度不同
- `scenes`：阶段二根据模板动态生成，非阶段一预设

---

## 三、详细实施计划

### 3.1 Phase 1：简化阶段一（预计1-2周）

#### 3.1.1 修改文件列表

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `src/managers/StagePlanManager.py` | 移除 Medium Events 预生成逻辑 | 3天 |
| `src/core/generation/PlanGenerator.py` | 修改 Major Events 生成Prompt | 2天 |
| `src/prompts/PlanningPrompts.py` | 新增 Skeleton 生成模板 | 2天 |
| `src/managers/stage_plan/plan_persistence.py` | 修改保存格式 | 1天 |

#### 3.1.2 关键修改点

**PlanGenerator.py 修改**：

```python
# 修改前：生成详细的 Medium Events
def generate_stage_writing_plan(...):
    # ... 生成 major_events
    for major in major_events:
        major["medium_events"] = self._generate_medium_events(major)  # ❌ 移除
        for medium in major["medium_events"]:
            medium["scenes"] = self._generate_scenes(medium)  # ❌ 移除

# 修改后：只生成 Skeleton
def generate_stage_writing_plan(...):
    # ... 生成 major_events
    for major in major_events:
        major["slot_templates"] = self._generate_slot_templates(major)  # ✅ 只生成模板建议
        # medium_events 和 scenes 不再预生成
```

**PlanningPrompts.py 新增**：

```python
MAJOR_EVENT_SKELETON_PROMPT = """
你正在为小说规划重大事件。请设计事件骨架，但不要细化到具体场景。

【输出要求】
只输出以下信息：
1. 事件名称
2. 章节范围（如1-30）
3. 核心冲突
4. 情绪目标
5. 剧情目标
6. 预计拆分成几个中级事件（建议数字）
7. 每个中级事件的类型建议（trigger/suppression/harvest/exploration）

【禁止输出】
- 不要输出具体场景设计
- 不要输出详细对话
- 不要输出每章具体内容
"""
```

### 3.2 Phase 2：新增动态拆分器（预计2-3周）

#### 3.2.1 新增文件

| 文件 | 功能 | 工作量 |
|------|------|--------|
| `src/core/generation/dynamic_splitter.py` | 动态拆分器主类 | 5天 |
| `src/core/generation/rhythm_templates.py` | 节奏模板定义 | 2天 |
| `src/core/generation/platform_strategies.py` | 平台策略配置 | 2天 |

#### 3.2.2 核心类设计

**DynamicEventSplitter 类**：

```python
class DynamicEventSplitter:
    """
    阶段二：动态拆分重大事件为中级事件
    """
    
    def __init__(self, platform: str = "fanqie"):
        self.platform = platform
        self.strategy = PLATFORM_STRATEGIES[platform]
        self.template_manager = RhythmTemplateManager()
    
    def split(self, major_event: Dict) -> List[Dict]:
        """
        主入口：拆分重大事件
        """
        chapter_range = major_event["chapter_range"]
        start, end = self._parse_range(chapter_range)
        total = end - start + 1
        
        medium_events = []
        current = start
        slot_idx = 0
        slots = major_event.get("slot_templates", [])
        
        while current <= end:
            # 1. 决定这个中级事件的跨度
            span = self._decide_span(current, total, slots[slot_idx] if slot_idx < len(slots) else None)
            
            # 2. 选择节奏模板
            rhythm = self._select_rhythm_template(current, total, slots[slot_idx] if slot_idx < len(slots) else None)
            
            # 3. 生成场景
            scenes = self._generate_scenes(span, rhythm)
            
            medium_event = {
                "name": f"{major_event['name']}_Part{len(medium_events)+1}",
                "chapter_range": f"{current}-{min(current+span-1, end)}",
                "parent_major_event": major_event["name"],
                "rhythm_template": rhythm["name"],
                "scenes": scenes,
                "chapter_hooks": self._generate_hooks(span, rhythm)
            }
            
            medium_events.append(medium_event)
            current += span
            slot_idx += 1
        
        return medium_events
    
    def _decide_span(self, current_ch: int, total: int, slot_template: Dict) -> int:
        """决定中级事件覆盖几章"""
        # 黄金三章：1章1事件
        if current_ch <= 3:
            return 1
        
        # 根据平台策略
        max_span = self.strategy["max_chapters_per_medium"]
        
        # 根据模板类型微调
        if slot_template:
            template_type = slot_template.get("type", "")
            if template_type == "trigger_burst":
                return min(3, max_span)  # 触发事件可稍长
            elif template_type == "suppression_reversal":
                return min(2, max_span)  # 打脸事件要短
        
        return min(max_span, total - current_ch + 1)
    
    def _select_rhythm_template(self, current_ch: int, total: int, slot_template: Dict) -> Dict:
        """选择节奏模板"""
        base_template = self.strategy["rhythm_template"]
        
        # 可根据 slot_template 的类型微调
        if slot_template:
            slot_type = slot_template.get("type", "")
            if slot_type in ["trigger_burst", "suppression_reversal"]:
                return self.template_manager.get_template("pulse_intense")
            elif slot_type == "harvest_upgrade":
                return self.template_manager.get_template("pulse_satisfaction")
        
        return self.template_manager.get_template(base_template)
```

**RhythmTemplateManager 类**：

```python
class RhythmTemplateManager:
    """节奏模板管理器"""
    
    TEMPLATES = {
        "pulse": {
            "name": "pulse",
            "description": "脉冲式（番茄风格）",
            "scene_sequence": ["危机", "应对", "爆发", "收获+钩子"],
            "emotion_arc": "紧张→释放→紧张→释放",
            "chapter_hooks": ["强", "强", "极强"],
            "prompt_addition": PULSE_PROMPT_ADDITION
        },
        "pulse_intense": {
            "name": "pulse_intense",
            "description": "强脉冲（高潮/打脸）",
            "scene_sequence": ["压抑", "积累", "全面爆发", "震撼收获"],
            "emotion_arc": "憋屈→紧张→极致释放→爽",
            "chapter_hooks": ["中", "强", "极强"],
            "prompt_addition": PULSE_INTENSE_PROMPT_ADDITION
        },
        "classic": {
            "name": "classic",
            "description": "传统起承转合（起点风格）",
            "scene_sequence": ["起", "承", "转", "合"],
            "emotion_arc": "平→起→高→收",
            "chapter_hooks": ["弱", "中", "强"],
            "prompt_addition": CLASSIC_PROMPT_ADDITION
        },
        "romance": {
            "name": "romance",
            "description": "感情线模板",
            "scene_sequence": ["偶遇", "互动", "升温", "悬念"],
            "emotion_arc": "甜→酸→甜→悬念",
            "chapter_hooks": ["中", "强", "中"],
            "prompt_addition": ROMANCE_PROMPT_ADDITION
        }
    }
    
    def get_template(self, name: str) -> Dict:
        return self.TEMPLATES.get(name, self.TEMPLATES["pulse"])
```

### 3.3 Phase 3：集成批量生成（预计2-3周）

#### 3.3.1 修改文件

| 文件 | 修改内容 | 工作量 |
|------|---------|--------|
| `src/core/batch_generation/multi_chapter_generator.py` | 修改Prompt构建，支持节奏模板 | 4天 |
| `src/core/batch_generation/processor.py` | 集成动态拆分器 | 3天 |
| `src/core/NovelGenerator.py` | 修改阶段二入口 | 2天 |

#### 3.3.2 关键修改

**MultiChapterGenerator 修改**：

```python
def _build_prompt(self, medium_event: Dict, ...):
    # 获取节奏模板
    rhythm_template = medium_event.get("rhythm_template", "pulse")
    template = self.template_manager.get_template(rhythm_template)
    
    prompt = f"""
【批量生成任务】
生成小说《{novel_title}》第{start_ch}-{end_ch}章，共{span}章。

【节奏模板：{template['description']}】
本章遵循"{template['name']}"节奏模板：
- 场景序列：{' → '.join(template['scene_sequence'])}
- 情绪曲线：{template['emotion_arc']}
- 章节钩子强度：{' → '.join(template['chapter_hooks'])}

{template['prompt_addition']}

【章间衔接要求】
1. 第N章结尾必须和第N+1章开头有因果关系
2. 情绪必须波动：{template['emotion_arc']}
3. 每章字数均衡：各章字数差异不超过20%
4. 钩子强度递增：{' < '.join(template['chapter_hooks'])}

【场景设计】
{self._format_scenes(medium_event['scenes'])}

【输出格式】
请返回以下JSON格式：
{{
    "chapters": [
        {{
            "chapter_number": {start_ch},
            "chapter_title": "标题（不超过14字）",
            "content": "正文内容（约2000字）",
            "word_count": 字数统计
        }},
        ...
    ]
}}
"""
    return prompt
```

### 3.4 Phase 4：测试与优化（预计1-2周）

#### 3.4.1 测试计划

| 测试项 | 方法 | 通过标准 |
|--------|------|---------|
| 功能测试 | 单元测试 | 各模块接口正常 |
| 集成测试 | 端到端生成 | 全流程无报错 |
| A/B测试 | 新旧架构对比 | 新架构3章留存率提升>20% |
| 平台适配测试 | 番茄/起点各生成一本 | 节奏符合平台特点 |

---

## 四、接口变更清单

### 4.1 新增接口

```python
# src/core/generation/dynamic_splitter.py

class DynamicEventSplitter:
    def __init__(self, platform: str)
    def split(self, major_event: Dict) -> List[Dict]
    
class RhythmTemplateManager:
    def get_template(self, name: str) -> Dict
    def list_templates(self) -> List[str]

# src/core/generation/platform_strategies.py

PLATFORM_STRATEGIES = {
    "fanqie": PlatformStrategy,
    "qidian": PlatformStrategy,
    "jjwxc": PlatformStrategy
}
```

### 4.2 修改接口

```python
# src/managers/StagePlanManager.py

# 修改前
def generate_stage_writing_plan(...) -> Dict:
    # 返回包含 medium_events 的详细计划
    
# 修改后
def generate_stage_writing_plan(...) -> Dict:
    # 返回只包含 major_events（skeleton）的简化计划
    
# 新增
def get_skeleton_plan(self, stage_name: str) -> Optional[Dict]:
    """获取阶段一生成的骨架计划"""
```

### 4.3 废弃接口

```python
# 以下接口将标记为废弃，保留兼容性但不再推荐

def _generate_medium_events(self, major_event: Dict) -> List[Dict]:
    """❌ 废弃：阶段一不再预生成 Medium Events"""
    
def _generate_scenes(self, medium_event: Dict) -> List[Dict]:
    """❌ 废弃：阶段一不再预生成 Scenes"""
```

---

## 五、风险与回退方案

### 5.1 风险分析

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|---------|
| **动态拆分质量不稳定** | 中 | 高 | 保留人工调整接口，允许编辑拆分结果 |
| **批量生成与节奏模板不匹配** | 中 | 中 | 准备多套Prompt模板，根据效果切换 |
| **阶段二耗时增加** | 高 | 中 | 拆分器结果可缓存，避免重复计算 |
| **兼容性问题** | 低 | 高 | 保留旧版API，新旧架构可切换 |

### 5.2 回退方案

**方案A：功能开关（推荐）**

```python
# config.py
GENERATION_MODE = "new"  # "new" | "legacy"

# 代码中
if GENERATION_MODE == "new":
    result = new_architecture_generate()
else:
    result = legacy_generate()  # 保留旧代码
```

**方案B：蓝绿部署**
- 新架构部署在独立分支
- 用户可选择使用新版或旧版
- 数据完全兼容，可随时切换

**方案C：数据迁移**
- 旧项目使用旧架构继续完成
- 新项目使用新架构
- 不提供自动迁移，避免数据损坏

---

## 六、时间规划

```
第1-2周：Phase 1 - 简化阶段一
  ├── 修改 PlanGenerator
  ├── 修改 PlanningPrompts
  ├── 修改 StagePlanManager
  └── 单元测试

第3-5周：Phase 2 - 新增动态拆分器
  ├── 实现 DynamicEventSplitter
  ├── 实现 RhythmTemplateManager
  ├── 实现 PlatformStrategies
  └── 单元测试

第6-8周：Phase 3 - 集成批量生成
  ├── 修改 MultiChapterGenerator
  ├── 修改 BatchProcessor
  ├── 修改 NovelGenerator
  └── 集成测试

第9-10周：Phase 4 - 测试与优化
  ├── A/B测试
  ├── Bug修复
  ├── 性能优化
  └── 文档更新

第11周：上线准备
  ├── 灰度发布
  ├── 监控部署
  └── 应急预案
```

---

## 七、决策确认

在正式启动前，需要确认以下决策：

1. **是否接受阶段一输出简化？**
   - [ ] 是，接受更抽象的骨架输出
   - [ ] 否，需要保留详细预设计

2. **平台策略优先级？**
   - [ ] 优先番茄（脉冲式）
   - [ ] 优先起点（传统式）
   - [ ] 同时支持，用户选择

3. **回退方案选择？**
   - [ ] 功能开关（推荐）
   - [ ] 蓝绿部署
   - [ ] 数据迁移

4. **资源投入？**
   - [ ] 全力投入（2-3人，10周）
   - [ ] 兼职投入（1人，20周）
   - [ ] 暂缓，先做其他优化

---

## 八、附录

### 8.1 节奏模板详细设计

见文档：`docs/RHYTHM_TEMPLATES.md`（待创建）

### 8.2 平台策略详细配置

见文档：`docs/PLATFORM_STRATEGIES.md`（待创建）

### 8.3 API接口详细定义

见文档：`docs/API_SPEC_REFACTOR.md`（待创建）

---

**文档结束**

如需进一步细化某个部分，请告知，我可以继续扩展。
