# 一阶段生成流程优化方案（兼顾质量与Token限制）

## 问题分析

### Token限制风险
- Gemini Pro 最大输出：8K tokens（约6000中文字）
- 4个阶段详细计划合并会远超限制
- 质量评估需要独立进行（无法合并）

### 质量保障需求
- 每个阶段的质量评估不能省略
- 中间检查点是防止AI"跑偏"的关键
- 复杂内容需要分步生成确保准确性

---

## 保守优化方案（推荐）

### 优化1：阶段详细计划 - 流式并行生成 ✅
**不改变API调用次数，但缩短等待时间**

```python
# 当前：串行生成（4个阶段，每个2-3次调用，共8-12次）
# 阶段1 → 阶段2 → 阶段3 → 阶段4（顺序执行，总时间累加）

# 优化：4个阶段并行生成（同时发起4个请求）
# 阶段1 + 阶段2 + 阶段3 + 阶段4（并行执行，时间取最长）
```

**实现方式**：
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_stage_parallel(self, stages):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for stage_name in stages:
            future = executor.submit(
                self.generate_stage_writing_plan, 
                stage_name, ...
            )
            futures[future] = stage_name
        
        for future in as_completed(futures):
            stage_name = futures[future]
            try:
                result = future.result()
                # 保存结果
            except Exception as e:
                # 单个阶段失败不影响其他
                logger.error(f"{stage_name} 生成失败: {e}")
```

**收益**：
- API调用次数：不变（8-12次）
- 时间：从40分钟→15分钟（并行）
- 质量：完全保持（每个阶段独立评估）
- Token：无压力（每个请求独立）

---

### 优化2：质量评估轻量化 ✅
**减少不必要的深度评估**

当前问题：
- 每个方案都要新鲜度+质量评估（2次）
- 每个阶段详细计划后也有评估

优化策略：
```python
# 方案选择阶段（已优化）
- 使用AI自评分数
- 只深度评估分数在临界值（7.5-8.5）的方案

# 阶段详细计划阶段
- 保持每个阶段的质量检查（这是必需的）
- 但使用轻量级评估（1次调用而非2次）
```

---

### 优化3：基础规划合并（低Token方案）✅

**写作风格 + 市场分析 合并**

```python
# 合并提示词设计（控制输出大小）
user_prompt = f"""
请为以下小说同时生成：

【输出1：写作风格指南】
- 核心风格定位（100字以内）
- 语言特点（3个关键词）
- 叙事技巧（2-3个要点）

【输出2：市场分析】  
- 目标读者画像（50字以内）
- 核心卖点提炼（3条）
- 对标作品（2-3个）

创意种子：{creative_seed}
"""
```

**Token控制**：
- 明确要求输出长度限制
- 预计输出：500-800 tokens（安全范围内）

**收益**：
- API调用：2次→1次（节省1次）
- 时间：-3分钟
- 质量：轻微影响（但可接受）

---

### 优化4：世界观+势力系统合并（可选）⚠️

**谨慎合并，保持质量**

```python
# 提示词设计：世界观为主体，势力为子模块
user_prompt = f"""
请构建完整的世界观框架，其中必须包含势力系统设计：

【世界观框架】
- 世界背景
- 力量体系
- 规则设定

【势力系统】（作为世界观的组成部分）
- 3-5个主要势力
- 势力关系网络
- 主角初始立场

要求：世界观和势力系统必须在逻辑上自洽统一
"""
```

**风险提示**：
- Token可能接近上限（建议先测试）
- 如果失败，自动降级为两次调用

---

## 优化前后对比

| 阶段 | 优化前 | 优化后 | 策略 | 时间 |
|------|--------|--------|------|------|
| 方案选择 | 7次 | 2次 | AI自评+深度兜底 | ✅ 已优化 |
| 基础规划 | 2次 | 1次 | 风格+市场合并 | -3分钟 |
| 世界观 | 2次 | 1-2次 | 世界观+势力尝试合并 | -2分钟 |
| 角色设计 | 1次 | 1次 | 保持 | - |
| 全书规划 | 3次 | 3次 | 保持（不宜合并） | - |
| 阶段详细计划 | 8-12次 | 8-12次 | **并行生成** | -25分钟 |
| 质量评估 | 1次 | 1次 | 保持 | - |
| **总计** | **24-28次** | **18-22次** | | **40min→15min** |

---

## 实施建议

### 优先级1（立即实施）：阶段并行生成
- 零风险，收益最大
- 代码改动小
- 质量完全保持

### 优先级2（测试后实施）：基础规划合并
- Token风险低
- 收益中等
- 需要测试输出质量

### 优先级3（可选）：世界观合并
- Token风险中等
- 需要失败回退机制

---

## Token安全检测机制

```python
def safe_merge_call(self, prompt_type, user_prompt, max_tokens=6000):
    """
    安全的合并调用，如果token超限自动降级
    """
    try:
        # 先尝试合并调用
        result = self.api_client.generate_content_with_retry(
            prompt_type,
            user_prompt,
            purpose="合并生成",
            max_tokens=max_tokens
        )
        
        # 检查结果完整性
        if self._check_result_complete(result):
            return result, "merged"
        else:
            raise Exception("结果不完整")
            
    except Exception as e:
        logger.warning(f"合并调用失败，降级为分步调用: {e}")
        # 降级为分步调用
        return self._fallback_to_separate_calls(), "separate"
```

这个方案是否更符合你的需求？优先实施**并行生成**，其他作为可选优化？
