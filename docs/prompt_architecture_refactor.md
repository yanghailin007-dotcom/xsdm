# 提示词架构梳理与重构方案

## 一、当前架构现状

### 1.1 文件分布

```
prompt_packages/default/market_driven/          (30KB, 7个JSON文件)
├── step_1_plan.json           # 生成完整方案
├── step_2_worldview.json      # 世界观设计
├── step_3_characters.json     # 角色设计
├── step_4_growth.json         # 成长路线
├── step_5_emotion.json        # 情绪曲线
├── step_6_alignment.json      # 对齐检查
└── step_7_chapter.json        # 章节生成

web/services/market_driven/                     (155KB, Python代码)
├── chapter_prompt_optimizer.py      (27KB)    # v1版本章节提示词
├── chapter_prompt_optimizer_v3.py   (95KB)    # v3版本章节提示词 ⭐主要问题
├── prompt_templates.py              (16KB)    # 基础模板
└── trope_prompt_builder.py          (15KB)    # 题材特定模板
```

### 1.2 问题诊断

| 问题 | 描述 | 影响 |
|------|------|------|
| **职责混杂** | 同样功能的提示词分散在 JSON 和 Python 中 | 维护困难，修改需要同时改多处 |
| **Python 膨胀** | 95KB 的 chapter_prompt_optimizer_v3.py 中 80% 是 Prompt 字符串 | 无法热更新，每次修改需重启服务 |
| **版本混乱** | v1/v3 两个版本同时存在，职责不清 | 开发者不知道用哪个 |
| **重复定义** | "震惊流写法"在多个文件中重复定义 | 不一致，容易遗漏修改 |

---

## 二、理想架构设计

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 运行时动态层 (Python)                               │
│  - 用户输入处理                                               │
│  - 上下文数据组装 (blueprint → variables)                     │
│  - 运行时参数调整 (temperature, max_tokens)                   │
│  - 响应解析和校验                                             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 调用
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 提示词引擎层 (Python)                               │
│  - 加载 JSON 提示词包                                        │
│  - 模板渲染 (Jinja2/变量替换)                                 │
│  - 条件分支处理 (if/else 逻辑)                                │
│  - 版本选择和回退                                             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 加载
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 提示词包层 (JSON)                                   │
│  - 系统角色定义                                               │
│  - 上下文区块配置                                             │
│  - 输出格式规范                                               │
│  - 写作风格指南 (震惊流/打脸流等)                             │
│  - 质量检查清单                                               │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 继承/覆盖
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 基础模板层 (JSON)                                   │
│  - 通用写作准则 (番茄风格/短段落等)                           │
│  - 通用禁忌清单                                              │
│  - 通用输出格式                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 职责边界

| 层级 | 应该做的 | 不应该做的 |
|------|----------|-----------|
| **JSON 提示词包** | 定义写什么、怎么写、风格要求 | 不写获取数据的逻辑 |
| **Python 引擎** | 组装数据、选择模板、渲染输出 | 不硬编码具体写作指令 |
| **运行时** | 调用 API、解析响应、异常处理 | 不生成 Prompt |

---

## 三、当前修改的归属梳理

### 3.1 已做的修改清单

| 修改内容 | 当前位置 | 应该归属 | 优先级 |
|----------|----------|----------|--------|
| max_tokens: 6000→8000 | step_7_chapter.json | ✅ JSON (已正确) | - |
| 震惊流写法指导 | chapter_prompt_optimizer_v3.py | 🔴 应该迁移到 JSON | 高 |
| "不要写第X层"标签 | chapter_prompt_optimizer_v3.py | 🔴 应该迁移到 JSON | 高 |
| "不要写章节标题" | step_7_chapter.json | ✅ JSON (已正确) | - |
| 字数分配指导 | chapter_prompt_optimizer_v3.py | 🟡 可以保留在 Python | 中 |
| 完整性检查逻辑 | chapter_conversation_generator.py | ✅ Python (运行时) | - |
| 黄金三章特殊结构 | chapter_prompt_optimizer_v3.py | 🟡 部分可配置化 | 中 |
| 质量评分关键词 | stage_review_optimizer.py | ✅ Python (运行时) | - |

---

## 四、迁移方案

### 4.1 第一步：创建"写作风格库" JSON 文件

新建 `prompt_packages/default/market_driven/styles/` 目录：

```
styles/
├── _base.json              # 基础写作风格 (番茄/起点)
├── shock_flow.json         # 震惊流写法 ⭐当前缺失
├── face_slap.json          # 打脸流写法
├── reveal.json             # 揭秘流写法
└── crisis.json             # 危机流写法
```

**shock_flow.json 示例：**
```json
{
  "style_id": "shock_flow",
  "style_name": "震惊流写法",
  "description": "多层次震惊铺展，引发读者强烈情绪共鸣",
  "rules": [
    "用自然叙事展现震惊，不要写'第一层、第二层'这种标签",
    "先写现场围观者反应，再写直播传播，最后写权威反应",
    "每个层级要有具体的人物反应、对话、动作"
  ],
  "examples": {
    "correct": "华夏直播间弹幕瞬间爆炸。\"负债47.6万？还是个无业游民？！\"",
    "incorrect": "第一层（现场）：华夏直播间弹幕瞬间爆炸..."
  },
  "techniques": {
    "expression": ["瞳孔骤然收缩", "嘴巴张成O型", "双腿发软"],
    "dialogue": ["这不可能！", "我眼花了？", "这还是人吗？"],
    "action": ["手机从手中滑落", "揉眼睛、掐大腿", "手指颤抖说不出话"]
  }
}
```

### 4.2 第二步：重构章节生成器

修改 `chapter_prompt_optimizer_v3.py`：

**重构前 (95KB)：**
```python
def _build_shock_techniques(self) -> str:
    return """## 😱 震惊流写作技法
    ### 第1层：现场围观者
    ... 大量硬编码文本 ...
    """
```

**重构后：**
```python
def _load_style_guide(self, style_id: str) -> str:
    """从 JSON 加载写作风格指南"""
    style_file = f"prompt_packages/default/market_driven/styles/{style_id}.json"
    with open(style_file, 'r', encoding='utf-8') as f:
        style = json.load(f)
    return self._render_style_template(style)
```

### 4.3 第三步：统一章节模板配置

在 `step_7_chapter.json` 中增加模板引用：

```json
{
  "step_id": "step_7_chapter",
  "templates": {
    "SETUP": {
      "style": "setup",
      "word_distribution": {
        "hook": 300,
        "development": 800,
        "climax": 1000,
        "reaction": 400
      }
    },
    "FACE_SLAP": {
      "style": "face_slap",
      "word_distribution": {
        "oppression": 500,
        "burst": 1000,
        "reward": 800,
        "hook": 100
      }
    }
  }
}
```

---

## 五、实施优先级

### Phase 1: 立即修复 (本周)
- [x] 增加 max_tokens 到 8000
- [x] 添加完整性检查逻辑
- [ ] 创建 `styles/shock_flow.json` 并迁移震惊流写法
- [ ] 修改 `chapter_prompt_optimizer_v3.py` 加载 JSON 风格

### Phase 2: 架构优化 (下周)
- [ ] 统一 v1/v3 两个版本的章节生成器
- [ ] 创建 `styles/` 目录并迁移所有写作风格
- [ ] 将字数分配指导迁移到 JSON 配置

### Phase 3: 长期完善 (本月)
- [ ] 支持运行时热加载提示词包
- [ ] 添加提示词版本管理
- [ ] 建立提示词 A/B 测试机制

---

## 六、代码层面的最小化修改

如果暂时无法大重构，至少需要保证：

1. **所有写作风格指导统一来源** - 不要在多个文件中重复定义
2. **关键参数（max_tokens）只在 JSON 中配置**
3. **添加注释标记**哪些 Prompt 未来要迁移到 JSON

示例标记：
```python
# TODO: 迁移到 JSON - styles/shock_flow.json
# 当前硬编码是为了快速修复，后续需重构
shock_guide = """..."""
```
