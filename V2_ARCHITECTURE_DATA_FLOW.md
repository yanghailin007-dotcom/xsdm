# V2 六层架构 - 数据来源说明

## 核心原则

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据来源分类                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【项目信息驱动】每个项目不同，从 novel_data/tactical_plan 提取   │
│    ├── Layer 1: 核心设定（主角/金手指/世界观）                    │
│    └── Layer 2: 战术规划（阶段/章节目标/结构设计）                │
│                                                                  │
│  【配置文件驱动】通用规则，从 YAML 文件加载                        │
│    ├── Layer 3: 题材技法（神豪文/国运文规则）                     │
│    ├── Layer 4: 文风技法（番茄快节奏规范）                        │
│    ├── Layer 5: AI约束（字数/格式/禁止事项）                      │
│    └── Layer 6: 自检清单（写作前/后检查）                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1-2: 项目信息驱动

### Layer 1 核心设定 - 从项目信息提取

**数据来源**: `novel_data` 参数

| 内容 | 来源字段 | 示例 |
|-----|---------|-----|
| 主角姓名 | `suggestions.name` | "苏泽" |
| 金手指类型 | `golden_finger.type` | "神豪盲盒系统" |
| 题材 | `suggestions.genre` | "神豪文-签到奖励类" |
| 世界观 | `core_worldview` | 从项目配置提取 |
| 角色设定 | `character_design` | 从项目配置提取 |

**构建方法**: `_build_layer1_core_setting()` 从 novel_data 动态构建

---

### Layer 2 战术规划 - 从章节规划提取

**数据来源**: `chapter_plan` 参数 (来自 tactical_plan.json)

| 内容 | 来源字段 | 示例 |
|-----|---------|-----|
| 章节类型 | `beat_type` | "打脸章" |
| 情绪目标 | `emotion` + `intensity` | "爽快", 9 |
| 爽点设计 | `satisfaction_point` | "消费5亿触发返利" |
| 打脸设计 | `face_slapping` | "前女友被社会性死亡" |
| 钩子内容 | `hook_content` | "高维观察者出现" |

**构建方法**: `_build_layer2_tactical_planning()` 从 chapter_plan 动态构建

---

## Layer 3-6: 配置文件驱动

### Layer 3 题材技法 - 从 YAML 加载

**文件位置**: `prompt_packages/default/market_driven/v2_config/genre_techniques/`

```yaml
# 神豪文.yaml
shock_progression:  # 震惊铺展5步
  - 消费行为
  - 周围人心算
  - 店员/经理反应
  - 反派打脸
  - 消息扩散

must_include:  # 必须元素
  - element: "精确金额"
    check: "至少3处具体金额，精确到分"
```

**修改方式**: 直接编辑 YAML 文件 → 重启 Flask

---

### Layer 4 文风技法 - 从 YAML 加载

**文件位置**: `prompt_packages/default/market_driven/v2_config/writing_style.yaml` (待添加)

```yaml
# 文风规范
paragraph:
  max_lines: 4
  avg_length: "50-80字"

sentence:
  short_ratio: 0.4  # 短句占比≥40%
  max_length: 25

dialogue:
  ratio: 0.5  # 对话占比≥50%
```

---

### Layer 5 AI约束 - 从 YAML 加载

**文件位置**: `prompt_packages/default/market_driven/v2_config/ai_constraints.yaml`

```yaml
word_count:
  target: 2200
  min: 2000
  max: 2500

format_rules:
  dialogue_wrapper: '""'
  system_wrapper: "【】"

forbidden:  # 禁止事项
  - description: "爽点回退"
  - description: "预告欺诈"
```

---

### Layer 6 自检清单 - 从 YAML 加载

**文件位置**: `prompt_packages/default/market_driven/v2_config/self_check.yaml`

```yaml
pre_writing:  # 写前检查
  - item: "确认本章题材正确"
    critical: true

post_writing_format:  # 格式检查
  - item: "字数是否在范围内"
    severity: "critical"
```

---

## 修改指南

### 场景 1: 修改主角人设

**不要**修改 YAML 文件 ❌
```bash
# 错误！修改这个文件无效
core_setting_example.yaml
```

**应该**在项目页面修改 ✅
```
项目页面 → 角色设定 → 修改主角姓名/性格
```

效果：Layer 1.1 主角人设自动更新

---

### 场景 2: 修改神豪文金额要求

**应该**修改 YAML 文件 ✅
```bash
# 正确！修改这个文件
prompt_packages/default/market_driven/v2_config/genre_techniques/神豪文.yaml

must_include:
  - element: "精确金额"
    check: "至少5处具体金额，精确到分"  # 从3处改为5处
```

然后重启 Flask

效果：所有神豪文项目的 Layer 3 都更新

---

### 场景 3: 修改字数要求

**应该**修改 YAML 文件 ✅
```bash
# 正确！修改这个文件
prompt_packages/default/market_driven/v2_config/ai_constraints.yaml

word_count:
  target: 2500  # 从2200改为2500
```

然后重启 Flask

效果：所有项目的 Layer 5 都更新

---

## 代码实现对照

```python
class V2IntegrationAdapter:
    
    # Layer 1: 从 novel_data 构建（项目信息）
    def _build_layer1_core_setting(self) -> str:
        # 从 self.novel_data 提取主角、金手指等信息
        # 动态生成 Layer 1 内容
        pass
    
    # Layer 2: 从 chapter_plan 构建（章节规划）
    def _build_layer2_tactical_planning(self, chapter_plan) -> str:
        # 从 chapter_plan 提取阶段、目标、情绪等
        # 动态生成 Layer 2 内容
        pass
    
    # Layer 3: 从 YAML 加载（配置文件）
    def build_system_prompt_v2(self):
        genre_data = self._genre_loader.load(self.genre)  # 加载 YAML
        layer3_content = self._genre_renderer.render(genre_data)
        pass
    
    # Layer 5: 从 YAML 加载（配置文件）
    def build_user_prompt_v2(self):
        constraints = self._constraints_loader.load()  # 加载 YAML
        layer5_content = self._format_constraints(constraints)
        pass
```

---

## 总结

| 层级 | 数据来源 | 修改方式 | 影响范围 |
|-----|---------|---------|---------|
| Layer 1 | 项目信息 | 项目页面修改角色/金手指 | 仅当前项目 |
| Layer 2 | 章节规划 | 修改 tactical_plan | 仅当前项目 |
| Layer 3 | YAML 配置 | 编辑 genre_techniques/*.yaml | 所有项目 |
| Layer 4 | YAML 配置 | 编辑 writing_style.yaml | 所有项目 |
| Layer 5 | YAML 配置 | 编辑 ai_constraints.yaml | 所有项目 |
| Layer 6 | YAML 配置 | 编辑 self_check.yaml | 所有项目 |
