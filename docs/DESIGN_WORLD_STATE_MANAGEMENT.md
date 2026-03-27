# 剧情连贯性与设定合理性保障方案

## 问题分析

### 1. 剧情连贯性问题（4/10分）

| 问题 | 现象 | 根因 |
|------|------|------|
| **线索断裂** | 神启会第2、4、5章出现，然后消失 | AI忘记之前的线索 |
| **反派混乱** | 马克/杰克/卡特随意切换 | 每批生成时重新编造名字 |
| **伤势反复** | 白月魁第5章中毒，第8章没治疗就好了 | 状态没有跟踪 |
| **伏笔丢失** | 高维观察者第21章突然出现 | 没有"待激活线索"机制 |

### 2. 设定合理性问题（5/10分）

| 问题 | 现象 | 根因 |
|------|------|------|
| **扮演度混乱** | 0%比85%还强 | 没有强制规则约束 |
| **能力突兀** | 雷神领域突然领悟 | 没有解锁记录 |
| **规则不清** | 扮演度回落逻辑混乱 | 没有当前状态追踪 |

### 根因总结

**AI在多轮对话中丢失了剧情状态和设定规则**

```
第1批会话: 神启会出现 → 需要标记为"活跃线索"
第2批会话: 神启会是什么？ → 线索断裂

第10章: 扮演度0%→50%（突破）→ 需要记录"当前扮演度:50%"
第11章: 扮演度？随便写个80% → 设定混乱
```

---

## 解决方案：三层防护架构

### 第一层：WorldStateManager（世界状态管理器）

**功能**：集中式剧情状态管理

```python
class WorldState:
    protagonist: CharacterStatus      # 主角状态（伤势、能力）
    allies: Dict[str, CharacterStatus]  # 盟友状态
    enemies: Dict[str, CharacterStatus] # 敌人状态
    plot_threads: Dict[str, PlotThread] # 剧情线索
    system_rules: SystemRule          # 系统规则（扮演度）
```

**持久化**：状态保存在 `.world_state.json`，跨批次保持

### 第二层：Constraint Prompt Injection（约束提示词注入）

**每章生成前，自动注入当前状态**：

```
【世界状态约束 - 必须遵循】
主角(陆离)当前状态:
  - 健康: 健康
  - 已解锁能力: 雷神领域, 九霄神雷, 雷神之锤

盟友状态:
  - 白月魁: 健康

系统规则(扮演度):
  - 当前扮演度: 50%
  - 历史最高: 100%
  - 已解锁技能: 雷神领域, 九霄神雷
  - 特殊状态: 透支

活跃剧情线索(本章需要提及或推进):
  - 神启会: 神秘组织，对主角感兴趣
    提示: 第25-30章之间正式接触
  - 反龙联盟: 漂亮国牵头的反龙国联盟

【约束规则】
1. 必须保持上述角色状态一致
2. 不能突然解锁未获得的能力
3. 活跃的剧情线索需要在文中体现
4. 扮演度变化需要有合理过渡
```

### 第三层：Validation & Auto-fix（校验与自动修复）

**生成后自动校验**：

```python
def validate_chapter(content: str) -> List[str]:
    issues = []
    
    # 1. 校验线索连续性
    for thread in active_threads:
        if thread.last_mentioned < current_chapter - 3:
            issues.append(f"线索'{thread.name}'已{current_chapter - thread.last_mentioned}章未提及")
    
    # 2. 校验扮演度合理性
    if 扮演度变化 > 50% and 没有合理解释:
        issues.append("扮演度变化过大，需要更合理过渡")
    
    # 3. 校验伤势连续性
    if 盟友上一章中毒 and 本章没有治疗就健康:
        issues.append("伤势恢复缺少治疗过程")
    
    return issues
```

---

## 核心组件

### 1. WorldStateManager

```python
class WorldStateManager:
    def initialize_from_novel_data(novel_data)  # 初始化
    def update_after_chapter(chapter_num, content)  # 更新状态
    def build_constraint_prompt(chapter_num) -> str  # 生成约束提示词
    def validate_chapter(chapter_num, content) -> List[str]  # 校验
```

### 2. 状态跟踪机制

**角色状态**：
```python
@dataclass
class CharacterStatus:
    name: str
    health: str  # 健康/轻伤/重伤/中毒/濒死
    injuries: List[str]  # 具体伤势
    abilities_unlocked: List[str]  # 已解锁能力
```

**剧情线索**：
```python
@dataclass
class PlotThread:
    name: str
    status: str  # active/paused/resolved
    introduced_chapter: int
    last_mentioned: int  # 最后提及章节
    priority: int  # 优先级
    next_trigger: str  # 下次触发条件
```

**系统规则**：
```python
@dataclass
class SystemRule:
    current_playing_degree: float  # 当前扮演度
    max_playing_degree: float  # 历史最高
    special_states: List[str]  # 透支/虚弱等
    unlocked_skills: List[str]  # 已解锁技能
```

---

## 工作流程

```
批次生成开始
    │
    ▼
初始化 WorldStateManager
从 novel_data 提取初始状态
    │
    ▼
循环生成每章
    │
    ├─ 注入约束提示词（当前状态）
    │
    ├─ AI生成章节
    │
    ├─ 自动修复（主角名等）
    │
    ├─ 校验剧情连贯性
    │   └─ 发现问题 → 记录警告
    │
    └─ 更新世界状态
        ├─ 检测伤势变化
        ├─ 检测能力解锁
        ├─ 检测扮演度变化
        └─ 更新线索提及时间
    │
    ▼
保存状态到文件
    │
    ▼
下一批次
读取状态文件
继续生成...
```

---

## 预期效果

### 剧情连贯性（4/10 → 8/10）

| 修复前 | 修复后 |
|--------|--------|
| 神启会消失 | 每5章至少提及一次活跃线索 |
| 反派名混乱 | 使用 enemies 字典中的名字 |
| 伤势反复 | 跟踪 health 状态，治疗前保持健康受损 |
| 伏笔突兀 | 待激活线索在指定章节前不会强制引入 |

### 设定合理性（5/10 → 8/10）

| 修复前 | 修复后 |
|--------|--------|
| 0%比85%强 | 约束提示词明确当前扮演度，AI必须遵循 |
| 能力突兀 | unlocked_skills 列表控制，只能使用已解锁 |
| 扮演度混乱 | 自动检测变化幅度，过大时警告 |

---

## 已实施文件

1. ✅ `world_state_manager.py` - 核心状态管理
2. ✅ `chapter_conversation_generator.py` - 集成约束提示词
3. ✅ `batch_chapter_generator.py` - 传递 WorldStateManager
4. ✅ `character_state_manager.py` - 角色名一致性

---

## 重启后生效

新配置将在服务器重启后生效：
- 每章生成前自动注入状态约束
- 生成后自动更新世界状态
- 跨批次保持一致性
