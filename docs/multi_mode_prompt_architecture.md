# 多模式提示词包架构设计方案

## 一、现状分析

### 1.1 现有模式识别

| 模式ID | 模式名称 | 实现位置 | 提示词组织方式 |
|--------|----------|----------|----------------|
| `market_driven` | 市场驱动7步流 | `web/services/market_driven/` | ✅ JSON提示词包 |
| `traditional` | 传统分阶段 | `web/services/phase_one_optimizer.py` | ❌ 硬编码Python |
| `simple` | 简单生成 | `web/services/script_generator.py` | ❌ 硬编码Python |

### 1.2 架构问题

```
当前混乱状态：

prompt_packages/
└── default/
    └── market_driven/          ← 只有market_driven使用JSON
        ├── step_1_plan.json
        └── ...

web/services/
├── market_driven/              ← 使用JSON提示词包
│   ├── chapter_prompt_optimizer_v3.py
│   └── ...
├── phase_one_optimizer.py      ← 硬编码提示词
└── script_generator.py         ← 硬编码提示词
```

**问题**：
1. 只有 market_driven 使用了 JSON 提示词包架构
2. 传统模式的提示词散落在各个 Python 文件中
3. 没有统一的多模式管理机制
4. 新增模式需要大量重复开发

---

## 二、统一架构设计

### 2.1 目标架构

```
prompt_packages/
├── README.md                       # 提示词包说明文档
│
├── _base/                          # 基础模板（所有模式共享）
│   ├── writing_styles/             # 写作风格库
│   │   ├── shock_flow.json         # 震惊流
│   │   ├── face_slap.json          # 打脸流
│   │   └── ...
│   └── common_rules.json           # 通用规则
│
├── market_driven/                  # 模式：市场驱动7步流
│   ├── package_info.json           # 包信息
│   ├── mode_config.json            # 模式配置
│   │
│   ├── steps/                      # 步骤配置
│   │   ├── step_1_plan.json
│   │   ├── step_2_worldview.json
│   │   └── ...
│   │
│   └── templates/                  # 章节点模板
│       ├── chapter_setup.json
│       └── chapter_faceslap.json
│
├── traditional/                    # 模式：传统分阶段
│   ├── package_info.json
│   ├── mode_config.json
│   │
│   ├── steps/                      # 简化的步骤
│   │   ├── step_1_concept.json     # 创意设定
│   │   ├── step_2_outline.json     # 大纲生成
│   │   └── step_3_chapter.json     # 章节生成
│   │
│   └── templates/                  # 传统模板
│       └── standard_chapter.json
│
├── simple/                         # 模式：简单快速生成
│   ├── package_info.json
│   └── steps/
│       └── single_step.json        # 一步完成
│
└── user_custom/                    # 用户自定义包
    └── {user_id}/
        └── my_custom_mode/
```

### 2.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 模式引擎层 (Python)                                 │
│  - 各模式的特定实现逻辑                                       │
│  - 如：market_driven的7步对话流                             │
│  - 如：traditional的分阶段优化                               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 通用引擎层 (Python)                                 │
│  - PromptEngine: 统一渲染引擎                                │
│  - StyleLoader: 写作风格加载器                               │
│  - TemplateEngine: 模板渲染引擎                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 模式配置层 (JSON)                                   │
│  - package_info.json: 包元信息                               │
│  - mode_config.json: 模式流程配置                            │
│  - steps/*.json: 步骤配置                                    │
│  - templates/*.json: 模板配置                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 基础资源层 (JSON)                                   │
│  - _base/writing_styles/: 共享写作风格                       │
│  - _base/common_rules.json: 通用规则                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、关键文件规范

### 3.1 package_info.json

```json
{
  "id": "market_driven",
  "name": "市场驱动7步流",
  "version": "1.0.0",
  "description": "基于市场分析的7步对话式生成流程",
  "author": "System",
  "tags": ["advanced", "full_featured"],
  "min_app_version": "2.0.0",
  
  "compatibility": {
    "genres": ["国运文", "神豪文", "修仙文", "模拟器文", "all"],
    "platforms": ["fanqie", "qidian", "all"]
  },
  
  "entry_point": {
    "module": "web.services.market_driven.market_driven_conversation",
    "class": "MarketDrivenConversation"
  }
}
```

### 3.2 mode_config.json

```json
{
  "mode_id": "market_driven",
  
  "flow": {
    "type": "conversation",      // conversation | pipeline | single
    "steps": [
      {"step_id": "step_1", "name": "完整方案", "order": 1, "required": true},
      {"step_id": "step_2", "name": "世界观", "order": 2, "required": true},
      {"step_id": "step_3", "name": "角色", "order": 3, "required": true},
      {"step_id": "step_4", "name": "成长路线", "order": 4, "required": true},
      {"step_id": "step_5", "name": "情绪曲线", "order": 5, "required": true},
      {"step_id": "step_6", "name": "对齐检查", "order": 6, "required": false},
      {"step_id": "step_7", "name": "章节生成", "order": 7, "required": true}
    ]
  },
  
  "features": {
    "supports_resume": true,          // 支持断点续传
    "supports_edit": true,            // 支持中间结果编辑
    "supports_quality_check": true,   // 支持质量检查
    "auto_save": true                 // 自动保存
  },
  
  "templates": {
    "chapter_types": ["SETUP", "FACE_SLAP", "REWARD", "REVEAL", "CRISIS", "TRANSITION"]
  },
  
  "inherit_from": "_base"             // 继承基础资源
}
```

### 3.3 步骤文件结构

```json
{
  "step_id": "step_7_chapter",
  "step_name": "生成章节",
  "step_type": "conversation",      // conversation | generation | check
  "order": 7,
  
  "prompt_template": {
    "system_role": "...",
    "context_sections": [...],
    "variables": [...]
  },
  
  "response_format": {
    "type": "json",
    "schema": {...}
  },
  
  "ai_settings": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.9,
    "max_tokens": 8000
  },
  
  "inherits": {
    "writing_style": "shock_flow",   // 引用 _base/writing_styles/
    "template": "chapter_faceslap"   // 引用本模式的 templates/
  }
}
```

---

## 四、统一加载器设计

### 4.1 ModeLoader 类

```python
class ModeLoader:
    """模式统一加载器"""
    
    def __init__(self, base_path: str = "prompt_packages"):
        self.base_path = Path(base_path)
        self._cache = {}
    
    def list_modes(self) -> List[Dict]:
        """列出所有可用模式"""
        modes = []
        for mode_dir in self.base_path.iterdir():
            if mode_dir.is_dir() and not mode_dir.name.startswith('_'):
                info = self._load_package_info(mode_dir)
                if info:
                    modes.append(info)
        return modes
    
    def load_mode(self, mode_id: str) -> ModeConfig:
        """加载指定模式"""
        if mode_id in self._cache:
            return self._cache[mode_id]
        
        mode_path = self.base_path / mode_id
        config = ModeConfig.load(mode_path)
        self._cache[mode_id] = config
        return config
    
    def get_step_prompt(self, mode_id: str, step_id: str, variables: Dict) -> str:
        """获取步骤的渲染后提示词"""
        mode = self.load_mode(mode_id)
        step = mode.get_step(step_id)
        
        # 加载继承的写作风格
        if step.inherits and step.inherits.writing_style:
            style = self.load_writing_style(step.inherits.writing_style)
        
        # 渲染模板
        return self.render_prompt(step.prompt_template, variables, style)
```

### 4.2 使用示例

```python
# 1. 初始化加载器
loader = ModeLoader()

# 2. 列出可用模式
modes = loader.list_modes()
# [{"id": "market_driven", "name": "市场驱动7步流"}, ...]

# 3. 加载特定模式
mode = loader.load_mode("market_driven")

# 4. 获取步骤提示词
prompt = loader.get_step_prompt(
    mode_id="market_driven",
    step_id="step_7_chapter",
    variables={
        "chapter_number": 1,
        "beat_type": "FACE_SLAP",
        ...
    }
)

# 5. 切换模式（如切换到传统模式）
traditional_mode = loader.load_mode("traditional")
```

---

## 五、迁移计划

### Phase 1: 基础架构 (本周)

1. **创建 `_base` 目录**
   - 迁移写作风格库到 `_base/writing_styles/`
   - 创建 `common_rules.json`

2. **重构 `market_driven`**
   - 移动 `step_*.json` 到 `market_driven/steps/`
   - 创建 `mode_config.json`
   - 更新代码使用新路径

### Phase 2: 传统模式迁移 (下周)

1. **创建 `traditional` 模式包**
   - 从 `phase_one_optimizer.py` 提取提示词
   - 创建简化的3步配置
   - 创建 `package_info.json`

2. **实现 TraditionalModeEngine**
   - 适配传统分阶段流程
   - 支持 mode_config 驱动的执行

### Phase 3: 简单模式 (可选)

1. **创建 `simple` 模式包**
   - 一步到位的快速生成
   - 最小化配置

### Phase 4: 统一引擎 (长期)

1. **开发 ModeLoader**
   - 统一加载机制
   - 缓存和热更新支持

2. **UI 适配**
   - 模式选择界面
   - 动态加载步骤配置

---

## 六、传统模式提示词包设计

### 6.1 传统模式的特点

- 流程简单：创意 → 大纲 → 章节
- 中间产物可编辑
- 快速迭代
- 适合新手用户

### 6.2 传统模式目录结构

```
traditional/
├── package_info.json
├── mode_config.json
├── steps/
│   ├── step_1_concept.json       # 创意设定
│   ├── step_2_outline.json       # 大纲生成
│   └── step_3_chapter.json       # 章节生成
└── templates/
    └── standard_chapter.json     # 标准章节模板
```

### 6.3 传统模式流程对比

| 阶段 | Market Driven (7步) | Traditional (3步) |
|------|---------------------|-------------------|
| 初始 | Step 1: 完整方案 | Step 1: 创意设定 |
| 设定 | Step 2-4: 世界观/角色/成长 | (合并到Step1) |
| 情绪 | Step 5: 情绪曲线 | (简化处理) |
| 检查 | Step 6: 对齐检查 | (可选) |
| 生成 | Step 7: 章节生成 | Step 3: 章节生成 |

**优势**：
- Traditional 更快更简单
- Market Driven 更全面质量更高
- 用户根据需求选择

---

## 七、总结

### 核心价值

1. **统一架构**：所有模式使用相同的 JSON 配置架构
2. **代码复用**：共享基础资源（写作风格、通用规则）
3. **易于扩展**：新增模式只需创建 JSON 配置
4. **热更新**：修改配置无需重启服务
5. **用户体验**：清晰的模式选择，按需选择复杂度

### 下一步行动

建议立即实施 Phase 1，建立基础架构，然后逐步迁移其他模式。
