# 自由创意模式一阶段对话化改造方案

## 一、现状分析

### 1.1 当前自由创意模式的问题

| 问题 | 说明 | 影响 |
|------|------|------|
| **分步独立调用** | 每个步骤(writing_style, market_analysis, worldview...)都是独立的 API 调用 | 上下文无法复用，每次都需要重新传递背景信息 |
| **串行执行** | 13+ 个步骤串行执行，每个步骤 1-2 次 API 调用 | 总调用次数 15-20 次，耗时极长 |
| **冷启动问题** | 每个新步骤都是冷启动，模型需要重新理解任务 | 生成质量不稳定 |
| **Token 浪费** | 重复传递相同的背景信息 | 成本增加 40-60% |

### 1.2 市场导向对话模式的优势

| 优势 | 说明 | 效果 |
|------|------|------|
| **单一会话复用** | 6 个步骤在同一个 ConversationSession 中完成 | 上下文连续继承 |
| **减少调用次数** | 仅需 6 次 API 调用完成一阶段 | 速度提升 60-70% |
| **热启动生成** | 后续步骤基于已有上下文，模型理解更深入 | 质量更稳定 |
| **Token 优化** | 利用上下文缓存机制（Kimi 仅 ¥0.7/1M tokens）| 成本降低 50%+ |

## 二、改造方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    FreeCreativeConversationSession           │
│                      (自由创意对话会话)                       │
├─────────────────────────────────────────────────────────────┤
│  步骤1: 基础规划 (Foundation Planning)                        │
│    ├── 写作风格指南                                          │
│    └── 市场分析                                              │
├─────────────────────────────────────────────────────────────┤
│  步骤2: 世界观与势力 (Worldview & Factions)                   │
│    ├── 世界观框架                                            │
│    └── 势力/阵营系统                                         │
├─────────────────────────────────────────────────────────────┤
│  步骤3: 角色设计 (Character Design)                          │
│    ├── 主角设计                                              │
│    ├── 盟友设计                                              │
│    └── 反派设计                                              │
├─────────────────────────────────────────────────────────────┤
│  步骤4: 情绪与成长 (Emotion & Growth)                        │
│    ├── 情绪蓝图                                              │
│    └── 角色成长路线                                          │
├─────────────────────────────────────────────────────────────┤
│  步骤5: 阶段规划 (Stage Planning)                            │
│    ├── 全书阶段划分                                          │
│    └── 阶段详细计划                                          │
├─────────────────────────────────────────────────────────────┤
│  步骤6: 补充与完善 (Supplementary)                           │
│    ├── 补充角色                                              │
│    └── 期待感映射                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计

#### 2.2.1 系统提示词设计

```python
SYSTEM_PROMPT = """# 角色：顶级网文策划专家

你正在为一部网络小说进行【第一阶段设定生成】。这是一个连续的多步骤创作过程，你将通过多轮对话逐步完成所有设定。

## 小说基础信息
- **书名**: {title}
- **类型**: {category}
- **简介**: {synopsis}
- **创意种子**: {creative_seed}

## 你的工作流程
你将按照以下顺序完成设定，每轮对话我会指示你进行下一步：

1. **基础规划** - 写作风格指南 + 市场分析
2. **世界观与势力** - 世界观框架 + 势力/阵营系统
3. **角色设计** - 主角、盟友、反派等核心角色
4. **情绪与成长规划** - 情绪蓝图 + 角色成长路线
5. **阶段规划** - 整体章节阶段规划 + 各阶段详细计划
6. **补充与完善** - 补充角色 + 期待感映射

## 输出规范
- 所有输出必须是合法的 JSON 格式
- 使用中文，符合中国网文市场特点
- 保持前后一致，后续步骤要参考前面的设定
- 每轮只输出当前步骤的内容，不要重复输出之前的内容
- 如果某步骤需要引用前面步骤的内容，请确保逻辑一致

## 当前进度
当前步骤: {current_step}
已完成: {completed_steps}
"""
```

#### 2.2.2 步骤提示词配置

创建 `prompt_packages/default/free_creative/conversation/conversation_steps.json`:

```json
{
  "steps": {
    "foundation_planning": {
      "name": "基础规划",
      "progress": 15,
      "ui_stage": "planning",
      "system_prompt_update": "现在你进入【基础规划】阶段。基于小说的创意种子，生成写作风格指南和市场分析。",
      "user_prompt_template": "请为这部小说生成基础规划：\n\n1. **写作风格指南**: 包括叙事视角、语言风格、节奏控制、爽点设计原则\n2. **市场分析**: 包括目标读者、竞品分析、差异化卖点\n\n输出格式必须是JSON：\n{{\n  \"writing_style_guide\": {{...}},\n  \"market_analysis\": {{...}}\n}}"
    },
    "worldview_factions": {
      "name": "世界观与势力",
      "progress": 30,
      "ui_stage": "worldview",
      "system_prompt_update": "现在你进入【世界观与势力】阶段。基于前面的基础规划，设计完整的世界观框架。",
      "user_prompt_template": "...",
      "depends_on": ["foundation_planning"]
    },
    "character_design": {
      "name": "角色设计",
      "progress": 45,
      "ui_stage": "worldview",
      "system_prompt_update": "现在你进入【角色设计】阶段。基于世界观，设计核心角色。",
      "user_prompt_template": "...",
      "depends_on": ["worldview_factions"]
    },
    "emotional_growth": {
      "name": "情绪与成长",
      "progress": 60,
      "ui_stage": "worldview",
      "system_prompt_update": "...",
      "depends_on": ["character_design"]
    },
    "stage_planning": {
      "name": "阶段规划",
      "progress": 80,
      "ui_stage": "chapters",
      "system_prompt_update": "...",
      "depends_on": ["emotional_growth"]
    },
    "supplementary": {
      "name": "补充与完善",
      "progress": 100,
      "ui_stage": "complete",
      "system_prompt_update": "...",
      "depends_on": ["stage_planning"]
    }
  }
}
```

### 2.3 代码实现方案

#### 2.3.1 核心类设计

```python
# src/core/free_creative_conversation.py

from src.core.APIClient import ConversationSession
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import json

@dataclass
class ConversationStep:
    """对话步骤定义"""
    step_id: str
    name: str
    progress: int
    ui_stage: str
    depends_on: List[str]
    system_prompt_update: str
    user_prompt_template: str

class FreeCreativeConversationSession(ConversationSession):
    """
    自由创意模式一阶段对话会话
    
    将一阶段所有步骤整合为单个连续对话，利用上下文缓存机制:
    - 减少 API 调用次数（从 15-20 次降至 6 次）
    - 利用上下文缓存节省 Token 成本
    - 提高生成质量和一致性
    """
    
    STEPS = [
        ConversationStep("foundation_planning", "基础规划", 15, "planning", [], ...),
        ConversationStep("worldview_factions", "世界观与势力", 30, "worldview", ["foundation_planning"], ...),
        ConversationStep("character_design", "角色设计", 45, "worldview", ["worldview_factions"], ...),
        ConversationStep("emotional_growth", "情绪与成长", 60, "worldview", ["character_design"], ...),
        ConversationStep("stage_planning", "阶段规划", 80, "chapters", ["emotional_growth"], ...),
        ConversationStep("supplementary", "补充与完善", 100, "complete", ["stage_planning"], ...),
    ]
    
    def __init__(self, api_client, novel_data: Dict, provider: str = "kimi", model_name: str = None):
        self.novel_data = novel_data
        self.current_step_index = 0
        self.results = {}
        self.step_callbacks = {}
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        super().__init__(api_client, system_prompt, provider=provider, model_name=model_name)
        
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        title = self.novel_data.get("novel_title", "")
        category = self.novel_data.get("category", "未分类")
        synopsis = self.novel_data.get("novel_synopsis", "")
        creative_seed = self.novel_data.get("creative_seed", {})
        
        return f"""# 角色：顶级网文策划专家
...
"""
    
    def execute_all_steps(self, 
                         progress_callback: Optional[Callable] = None,
                         project_path: Optional[str] = None) -> Dict:
        """执行所有步骤"""
        for step in self.STEPS:
            self._execute_step(step, progress_callback, project_path)
        return self.results
    
    def _execute_step(self, step: ConversationStep, 
                     progress_callback: Optional[Callable] = None,
                     project_path: Optional[str] = None):
        """执行单个步骤"""
        # 更新系统提示词（可选，用于让模型知道当前阶段）
        if step.system_prompt_update:
            self._update_system_prompt(step.system_prompt_update)
        
        # 构建用户提示词
        user_prompt = self._build_step_prompt(step)
        
        # 发送消息
        response = self.send_message(
            user_prompt=user_prompt,
            temperature=0.7,
            purpose=f"步骤{self.current_step_index+1}: {step.name}"
        )
        
        # 解析结果
        result = self._parse_step_result(step.step_id, response)
        self.results[step.step_id] = result
        
        # 更新进度
        if progress_callback:
            progress_callback(step.step_id, step.progress, f"{step.name}完成", 
                            {"stage": step.ui_stage})
        
        # 保存中间结果
        if project_path:
            self._save_step_result(step.step_id, result, project_path)
        
        self.current_step_index += 1
```

#### 2.3.2 PhaseGenerator 集成

```python
# src/core/PhaseGenerator.py 修改

def generate_phase_one_preparations(self) -> bool:
    """
    第一阶段准备工作 - 新增对话模式支持
    """
    # 🚀 优先级1: 对话模式（最快）
    if CONVERSATION_MODE_AVAILABLE and self._should_use_conversation_mode():
        print("\n" + "="*60)
        print("🚀 启用对话模式 - 6步完成一阶段")
        print("   单一会话复用，上下文连续继承")
        print("="*60)
        return self._generate_phase_one_with_conversation(
            update_progress_callback=update_progress_callback,
            update_step_status=update_step_status,
            notify_failure=notify_failure
        )
    
    # 优先级2: 分域会话模式（已有）
    if DOMAIN_SESSION_MODE_AVAILABLE and self._should_use_domain_session_mode():
        ...
    
    # 回退: 传统分步模式
    ...

def _generate_phase_one_with_conversation(self, ...):
    """使用对话模式执行一阶段"""
    from src.core.free_creative_conversation import FreeCreativeConversationSession
    
    session = FreeCreativeConversationSession(
        api_client=self.generator.api_client,
        novel_data=self.generator.novel_data,
        provider="kimi",
        model_name=self.generator.model_name
    )
    
    results = session.execute_all_steps(
        progress_callback=update_progress_callback,
        project_path=self.generator.project_path
    )
    
    # 同步结果到 novel_data
    self._sync_conversation_results_to_novel_data(results)
    return True
```

## 三、实施计划

### 阶段一：核心框架（2-3天）

1. **创建 `FreeCreativeConversationSession` 类**
   - 继承 `ConversationSession`
   - 实现 6 个步骤的执行逻辑
   - 添加结果解析和保存

2. **创建步骤提示词配置**
   - `conversation_steps.json` 配置文件
   - 每个步骤的 system_prompt 和 user_prompt

3. **PhaseGenerator 集成**
   - 添加对话模式检测方法
   - 实现 `_generate_phase_one_with_conversation`

### 阶段二：测试优化（2-3天）

1. **单元测试**
   - 每个步骤的提示词测试
   - 结果解析准确性测试

2. **集成测试**
   - 完整流程测试
   - 与市场导向模式对比测试

3. **性能测试**
   - API 调用次数统计
   - Token 消耗统计
   - 总耗时对比

### 阶段三：上线部署（1天）

1. **灰度发布**
   - 默认关闭，通过配置启用
   - 收集用户反馈

2. **监控告警**
   - 对话模式成功率监控
   - 异常自动回退

## 四、预期效果

| 指标 | 当前模式 | 对话模式 | 提升 |
|------|----------|----------|------|
| API 调用次数 | 15-20 次 | 6 次 | **65%↓** |
| 平均耗时 | 8-12 分钟 | 3-5 分钟 | **60%↓** |
| Token 成本 | 100% | 40-50% | **50%↓** |
| 生成质量 | 波动较大 | 更稳定 | **稳定性提升** |

## 五、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 对话模式生成质量下降 | 中 | 高 | 保留传统模式作为回退 |
| 长上下文导致超时 | 中 | 中 | 步骤6拆分为两个子步骤 |
| 提示词调优耗时 | 高 | 中 | 分阶段迭代优化 |
| 兼容性问题 | 低 | 高 | 充分测试，保留回退机制 |

---

**下一步行动**: 请确认此方案后，我将开始阶段一的实施。
