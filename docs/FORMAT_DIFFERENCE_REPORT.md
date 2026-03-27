# 新旧版本格式差异报告 - 影响番茄自动上传

## 🔴 核心问题

新版的 `plan` 和产物格式与旧版不兼容，导致番茄自动上传时无法正确读取标签信息。

---

## 一、标签信息格式差异

### 旧版格式（支持自动上传）

```python
# 旧版方案结构
{
    "selected_plan": {
        "title": "小说标题",
        "synopsis": "简介",
        "tags": {
            "main_category": "玄幻",           # 主分类（番茄界面：主分类标签页）
            "themes": ["东方玄幻", "异世大陆"], # 主题（番茄界面：主题标签页）
            "roles": ["孤儿", "老师"],          # 角色（番茄界面：角色标签页）
            "plots": ["废柴流", "奇遇"],        # 情节（番茄界面：情节标签页）
            "target_audience": "男频"           # 受众（番茄界面：男频/女频选择）
        },
        "suggestions": {
            "name": "主角名",
            "genre": "题材"
        }
    }
}
```

**番茄上传代码期望的格式**（`novel_publisher.py` 第290-294行）：
```python
tags_info = novel_data.get("selected_plan", {}).get("tags", {})
main_category = tags_info.get("main_category", "")
themes = tags_info.get("themes", [])
roles = tags_info.get("roles", [])
plots = tags_info.get("plots", [])
gender = tags_info.get("target_audience", "男频")
```

### 新版格式（缺少关键标签字段）

```python
# 新版方案结构（plan_generator.py 生成）
{
    "plan": {
        "genre": "神豪文-花钱返利类",
        "title_options": [...],
        "recommended_title": "...",
        "opening_design": {...},
        "golden_finger": {...},
        "protagonist": {...},
        "outline_first_30": [...],
        "core_selling_points": [...],
        # ❌ 缺少 "tags" 字段！
    }
}

# 新版 project_info 结构（project_manager.py）
{
    "category_tags": {
        "main_category": "都市",      # 有主分类
        "sub_category": "都市生活",   # 有子分类
        "tags": ["神豪", "系统", "爽文"],  # 有标签列表
        "target_audience": "男频",
        "content_rating": "全年龄"
    }
    # ❌ 但缺少 themes、roles、plots 字段！
}
```

---

## 二、产物字段差异

### 旧版产物字段

```python
{
    "worldview": {...},           # 世界观
    "characters": {...},          # 角色设计
    "factions": {...},            # 势力设定
    "growth": {...},              # 升级路线
    "writing": {...},             # 写作风格
    "storyline": {...},           # 故事线规划
    "market_analysis": {...}      # 市场分析
}
```

### 新版产物字段

```python
{
    "writing_style_guide": {...},     # 写作风格指南（对应旧版 writing）
    "market_analysis": {...},          # 市场分析
    "core_worldview": {...},           # 世界观（对应旧版 worldview）
    "faction_system": {...},           # 势力系统（对应旧版 factions）
    "character_design": {...},         # 角色设计（对应旧版 characters）
    "global_growth_plan": {...},       # 升级路线（对应旧版 growth）
    "stage_writing_plans": {...},      # 阶段写作计划
    "emotional_blueprint": {...},      # 情绪蓝图
    "expectation_mapping": {...},      # 期待感映射
    "emotion_curve": [...]             # 情绪曲线（新增）
}
```

**问题**：字段名不一致，如果上传代码期望的是旧版字段名，会找不到数据。

---

## 三、保存路径差异

### 旧版保存结构

```
小说项目/
├── 项目信息/
│   └── {timestamp}_项目信息.json    # 包含 selected_plan 和 tags
├── 一阶段产物/
│   ├── 世界观与修炼体系.json
│   ├── 核心角色设计.json
│   ├── 势力设定.json
│   └── ...
└── 章节/
    └── ...
```

### 新版保存结构

```
小说项目/
├── project_info.json              # 项目信息（包含 category_tags，但没有 themes/roles/plots）
├── 一阶段产物/
│   ├── core_worldview.json        # 世界观
│   ├── character_design.json      # 角色设计
│   ├── faction_system.json        # 势力系统
│   └── ...
└── 章节/
    └── ...
```

---

## 四、具体问题列表

### 1. ✅ 已发现问题：Plan 中缺少 `tags` 字段

**影响程度**：🔴 严重 - 导致无法自动选择番茄标签

**详细说明**：
- 新版 `plan_generator.py` 生成的方案中没有 `tags` 字段
- 番茄上传代码 `novel_publisher.py` 期望从 `selected_plan.tags` 读取：
  - `main_category` - 主分类
  - `themes` - 主题标签
  - `roles` - 角色标签
  - `plots` - 情节标签
  - `target_audience` - 男频/女频

**代码位置**：
- 问题代码：`web/services/market_driven/plan_generator.py` 第58-91行，生成的 plan 字典缺少 tags
- 使用代码：`web/fanqie_uploader/novel_publisher.py` 第290-510行，期望读取 selected_plan.tags

### 2. ⚠️ 潜在问题：字段名映射

**影响程度**：🟡 中等 - 可能导致数据读取失败

**详细说明**：
- 新版产物字段名与旧版不同
- 如果上传代码或其他地方硬编码了旧版字段名，会找不到数据

**字段映射表**：
| 旧版字段 | 新版字段 | 状态 |
|---------|---------|------|
| `worldview` | `core_worldview` | ⚠️ 不同 |
| `characters` | `character_design` | ⚠️ 不同 |
| `factions` | `faction_system` | ⚠️ 不同 |
| `growth` | `global_growth_plan` | ⚠️ 不同 |
| `writing` | `writing_style_guide` | ⚠️ 不同 |
| `market_analysis` | `market_analysis` | ✅ 相同 |

### 3. ⚠️ 潜在问题：产物结构差异

**影响程度**：🟡 中等

**详细说明**：
- 新版 `character_design` 结构：
  ```python
  {
      "main_character": {...},      # 主角
      "antagonists": [...],         # 反派列表
      "core_allies": [...]          # 核心盟友
  }
  ```
- 旧版可能是扁平结构或不同的嵌套方式

---

## 五、修复建议

### 方案1：在 Plan 中添加 tags 字段（推荐）

修改 `plan_generator.py`，在生成的 plan 中添加符合上传要求的 tags：

```python
# 在 plan 字典中添加
def generate_plan(self, genre: str, tropes: Dict, user_choices: Dict) -> Dict:
    plan = {
        # ... 现有字段 ...
        
        # 添加标签信息（供番茄上传使用）
        "tags": {
            "main_category": self._get_main_category(genre),  # 根据题材映射
            "themes": self._get_themes(genre),                 # 根据题材获取主题
            "roles": self._get_roles(genre),                   # 根据题材获取角色
            "plots": self._get_plots(genre),                   # 根据题材获取情节
            "target_audience": "男频"                           # 默认男频
        }
    }
```

### 方案2：在上传代码中适配新版格式

修改 `novel_publisher.py`，支持从新版结构中读取标签：

```python
# 优先读取旧版格式，如果不存在则读取新版格式
tags_info = novel_data.get("selected_plan", {}).get("tags", {})
if not tags_info:
    # 尝试从新版 category_tags 读取
    category_tags = novel_data.get("category_tags", {})
    tags_info = {
        "main_category": category_tags.get("main_category", ""),
        "themes": category_tags.get("tags", []),  # 用 tags 代替 themes
        "roles": [],  # 默认值
        "plots": [],  # 默认值
        "target_audience": category_tags.get("target_audience", "男频")
    }
```

### 方案3：创建格式转换器

创建一个转换函数，将新版格式转换为旧版格式：

```python
def convert_new_format_to_old(new_format: Dict) -> Dict:
    """将新版产物格式转换为旧版格式"""
    return {
        "selected_plan": {
            "title": new_format.get("plan", {}).get("recommended_title", ""),
            "tags": convert_category_to_tags(new_format.get("category_tags", {}))
        },
        "worldview": new_format.get("core_worldview", {}),
        "characters": new_format.get("character_design", {}),
        # ... 其他字段映射
    }
```

---

## 六、验证检查清单

修复后需要验证以下功能：

- [ ] 生成的 plan 包含完整的 tags 字段
- [ ] tags 中包含 main_category、themes、roles、plots、target_audience
- [ ] 番茄上传代码能正确读取 tags
- [ ] 能正确选择主分类标签
- [ ] 能正确选择主题标签
- [ ] 能正确选择角色标签
- [ ] 能正确选择情节标签
- [ ] 能正确选择男频/女频
- [ ] 整本书创建流程正常

---

## 七、相关代码文件

| 文件 | 说明 |
|-----|------|
| `web/services/market_driven/plan_generator.py` | 新版方案生成器，缺少 tags |
| `web/services/market_driven/project_manager.py` | 项目管理，有 category_tags 但格式不同 |
| `web/fanqie_uploader/novel_publisher.py` | 番茄上传代码，期望旧版格式 |
| `web/api/market_driven_api.py` | API 层，调用方案生成和保存 |

---

*报告生成时间：2026-03-26*
