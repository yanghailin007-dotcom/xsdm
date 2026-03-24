# 第一阶段产品智能优化系统

## 概述

第一阶段产品智能优化系统是一个**嵌套在第15步质量评估**中的三轮多轮对话优化工具。它对小说世界观、角色、势力、升级路线、写作风格、故事线等核心设定进行深度分析，在质量评估之前自动执行。

## 三轮优化流程 (嵌套在第15步)

### 第一轮:平台风格适配

**目标**:检查核心设定是否符合目标平台读者偏好

**检查维度**:
- 核心设定吸引力 (0-100分)
- 卖点突出程度 (0-100分)
- 角色人设适配 (0-100分)
- 开篇张力 (0-100分)

### 第二轮:数据匹配

**目标**:验证写作计划是否符合当下市场趋势,同时确保创意性

**检查维度**:
- 市场契合度 (0-100分)
- 创新性评估 (0-100分)
- 差异化优势 (0-100分)
- 商业潜力 (0-100分)

### 第三轮:内容连贯性检查

**目标**:检查小说内容是否存在严重的断档、脱节问题

**检查维度**:
- 世界观一致性
- 角色逻辑性
- 势力关系合理性
- 升级体系连贯性
- 剧情冲突检测

## 执行流程 (第15步)

```
第15步: 智能优化 + 质量评估
├── 阶段1: 三轮智能优化 (95%-97%)
│   ├── 第1轮: 平台风格适配
│   ├── 第2轮: 数据匹配
│   └── 第3轮: 内容连贯性检查
├── 阶段2: 质量评估 (98%-100%)
│   └── 对优化后的设定进行质量评估
└── 完成: 生成综合报告
```

## 平台配置

- **番茄小说 (fanqie)**: 快节奏、爽点密集、创新设定接受度高
- **起点中文网 (qidian)**: 注重完整性、接受慢热、人物刻画深度
- **通用 (general)**: 平衡方案

## 独立优化功能 (可选)

除了嵌套在第15步的自动优化外，系统还保留了独立的优化功能：

### API 端点

```http
# 启动独立优化任务
POST /api/phase-one/optimize

# 启动优化+评估组合任务
POST /api/phase-one/optimize-then-assess

# 获取任务状态
GET /api/phase-one/optimize-then-assess/<task_id>

# 获取质量评估报告
GET /api/quality-assessment/<novel_title>
```

### 在项目可视化页面使用

1. 打开项目可视化页面 `/project-viewer?title=小说标题`
2. 点击顶部工具栏的 "智能优化" 按钮
3. 选择目标平台
4. 查看三轮优化进度
5. 查看优化结果并应用建议

## 后端代码修改

### PhaseGenerator.py 修改

在第15步质量评估之前，添加了 `_run_phase_one_optimization` 方法调用：

```python
# 🔥 新增：先执行三轮智能优化，再进行质量评估
def _run_phase_one_optimization(self) -> Optional[Dict]:
    """执行第一阶段三轮智能优化"""
    # 1. 加载第一阶段产品
    # 2. 执行三轮优化
    # 3. 保存优化结果
    pass
```

### 修改位置

1. **正常流程** (约第347行)：在 `generate_phase_one_complete_v2` 方法中
2. **恢复流程** (约第624行)：在恢复模式的质量评估步骤中

## 输出文件

优化完成后，会生成以下文件：

```
小说项目/
└── {小说标题}/
    ├── phase_one_optimization.json     # 三轮优化详细结果
    ├── quality_assessment.json         # 质量评估报告
    └── ...
```

### phase_one_optimization.json 结构

```json
{
    "overall_score": 82,
    "platform": "fanqie",
    "platform_name": "番茄小说",
    "rounds": {
        "platform_adaptation": {
            "score": 78,
            "dimensions": {...},
            "issues": [...],
            "suggestions": [...]
        },
        "data_matching": {...},
        "coherence_check": {...}
    },
    "priority_actions": {
        "high": [...],
        "medium": [...],
        "low": [...]
    },
    "optimization_time": "..."
}
```

## 优化结果解读

### 总体评分

- **90-100分**: 优秀作品,只需微调
- **80-89分**: 良好作品,有改进空间
- **70-79分**: 一般作品,需要较大调整
- **60-69分**: 较差作品,建议重新规划
- **<60分**: 需要大幅修改或重新开始

### 优先级行动

- **高优先级**: 必须修复的严重问题
- **中优先级**: 建议改进的优化项
- **低优先级**: 可选的微调建议

## 接入真实AI服务

当前版本使用模拟数据进行演示。要接入真实AI服务:

1. 修改 `PhaseOneOptimizer` 类中的三个 `_roundX_xxx` 方法
2. 使用多轮对话获取更精准的优化建议

示例:

```python
def _round1_platform_adaptation(self) -> Dict[str, Any]:
    # 构建提示词
    system_prompt = "..."
    user_prompt = "..."
    
    # 调用AI API
    response = self.api_client.chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # 解析结果
    result = json.loads(response)
    return result
```

## 测试

运行测试:

```bash
python tests/test_phase_one_optimizer.py
```

测试覆盖:
- 优化器核心逻辑
- 任务管理器
- 平台配置
- 结果生成

## 文件清单

| 文件 | 说明 |
|------|------|
| `web/services/phase_one_optimizer.py` | 三轮优化核心逻辑 |
| `web/services/phase_one_optimize_then_assess.py` | 优化+评估组合服务 |
| `web/api/phase_one_optimization_api.py` | 独立优化API |
| `web/api/phase_one_optimize_assess_api.py` | 组合优化API |
| `src/core/PhaseGenerator.py` | 修改第15步流程 |
| `web/templates/components/progress-section.html` | 步骤UI描述 |
| `web/templates/phase-one-setup-new.html` | 步骤UI描述 |
