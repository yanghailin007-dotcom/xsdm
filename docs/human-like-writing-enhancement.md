# 市场导向创作人味增强计划

## 一、问题诊断

### 1.1 当前市场导向创作的问题

**为什么容易被判定为AI文？**

| 问题类型 | 具体表现 | 检测特征 |
|---------|---------|---------|
| 句式同质化 | 段落长度均匀，句式结构单一 | 句子长度方差过小 |
| 过渡生硬 | 场景切换、情绪转折过于"标准" | 缺少自然的跳跃和留白 |
| 词汇选择 | 高频使用AI偏好的"安全词" | 词汇多样性不足 |
| 情感平面 | 情绪递进过于线性 | 缺少真人写作的波动感 |
| 细节缺失 | 五感描写不足，画面感弱 | 感官词汇密度低 |
| 口语感弱 | 对话过于书面化 | 缺少口语化表达和停顿 |

### 1.2 番茄头部作品的"人味"特征

**需要分析的目标作品类型：**
- 赘婿/战神类：如《上门龙婿》《绝世强龙》
- 玄幻修仙类：如《道诡异仙》《斩神》
- 都市脑洞类：如《开局地摊卖大力》《全球高武》
- 年代文/种田类：如《重生八零》《农家小福女》

**预期发现的"人味"特征：**
1. **句式节奏变化**：长短句交错，破碎句与完整句并存
2. **口语化表达**：适当的方言、口头禅、语气词
3. **感官细节**：视觉、听觉、嗅觉、触觉、味觉的具体描写
4. **心理留白**：不直接说情绪，通过动作和环境暗示
5. **意外转折**：不按套路出牌的小细节
6. **个体声音**：独特的叙述腔调（幽默、冷峻、吐槽等）

## 二、整体架构

```
人味增强系统
├── 生成阶段优化 (第一层)
│   ├── 人味写作风格指南
│   ├── 头部作品风格注入
│   └── 句式多样化策略
│
└── 润笔改写阶段 (第二层)
    ├── 句式重构模块
    ├── 感官增强模块
    ├── 口语化注入模块
    └── 个体腔调塑造模块
```

## 三、实施阶段

### Phase 1: 头部作品分析（第1-2周）

#### 任务1.1: 建立分析框架
**位置**: `src/core/human_touch/analyzer.py`

**分析维度：**
```python
class HumanTouchAnalyzer:
    """人味特征分析器"""
    
    def analyze_text(self, text: str) -> Dict:
        return {
            "sentence_patterns": {
                "avg_length": float,        # 平均句长
                "length_variance": float,   # 句长方差（人味指标）
                "short_sentence_ratio": float,  # 短句比例
                "fragment_ratio": float,    # 破碎句比例
            },
            "sensory_details": {
                "visual_density": float,    # 视觉描写密度
                "auditory_density": float,  # 听觉描写密度
                "tactile_density": float,   # 触觉描写密度
                "olfactory_density": float, # 嗅觉描写密度
                "gustatory_density": float, # 味觉描写密度
            },
            "dialogue_features": {
                "colloquialism_ratio": float,   # 口语化比例
                "dialect_markers": List[str],   # 方言标记
                "filler_words": List[str],      # 语气词使用
                "interruption_ratio": float,    # 对话打断比例
            },
            "narrative_voice": {
                "humor_markers": List[str],     # 幽默标记
                "sarcasm_indicators": List[str], #  sarcasm标记
                "self_awareness": float,        # 自我指涉程度（吐槽、meta）
                "emotional_variance": float,    # 情绪波动幅度
            },
            "transition_patterns": {
                "hard_cut_ratio": float,        # 硬切比例（人味指标）
                "fade_out_ratio": float,        # 淡出比例
                "unexpected_twist_ratio": float, # 意外转折比例
            }
        }
```

#### 任务1.2: 收集并分析样本
- 选择5-10本番茄头部作品
- 每本提取10-20个代表性章节
- 运行分析器建立"人味基准线"
- 生成对比报告（头部作品 vs 当前AI生成）

**产出**: `docs/human_touch_baseline_report.md`

### Phase 2: 生成阶段优化（第3-4周）

#### 任务2.1: 人味写作风格指南
**位置**: `src/core/human_touch/style_guide.py`

**核心提示词模块：**

```python
HUMAN_TOUCH_WRITING_GUIDE = """
【人味写作核心原则】

1. **句式节奏多样化**
   - 短句与长句交替使用，避免连续3句以上同长度
   - 适当使用破碎句（"他愣住了。"）制造停顿
   - 对话中穿插动作和环境描写，打破"他说-他说"的单调

2. **感官细节注入**
   - 每个重要场景必须包含至少2种感官描写
   - 视觉：不仅是"看到"，而是"怎么看到"（余光、扫视、定睛）
   - 听觉：环境音、内心声音的交织
   - 触觉：温度、质地、疼痛的具体感受

3. **口语化表达**
   - 对话使用日常口语，避免书面化长句
   - 适当加入方言词汇和语气词（但不过度）
   - 允许语法不完美的自然表达

4. **心理留白**
   - 不要直接陈述情绪，通过动作和生理反应暗示
   - "他的手在抖" 而非 "他很紧张"
   - 适当的省略，让读者自己填补

5. **个体腔调**
   - 根据角色性格选择叙述腔调：
     * 冷幽默型：自嘲、吐槽、黑色幽默
     * 热血型：短促有力、感叹号、内心呐喊
     * 沉稳型：长句、内敛、克制
   - 保持腔调一致性，但允许情绪波动

6. **意外细节**
   - 在套路情节中加入1-2个意外小细节
   - 反派的怪癖、环境的反常、主角的失误
   - 让情节不完全按"标准答案"发展
"""
```

#### 任务2.2: 头部作品风格注入
**位置**: `src/core/human_touch/style_injector.py`

**功能：**
- 从Phase 1分析结果中提取风格特征
- 生成"风格DNA"注入提示词
- 支持按题材选择对应头部风格

```python
class StyleInjector:
    """风格注入器"""
    
    def extract_style_dna(self, sample_chapters: List[str]) -> StyleDNA:
        """从样本中提取风格DNA"""
        
    def inject_to_prompt(self, base_prompt: str, style_dna: StyleDNA) -> str:
        """将风格DNA注入基础提示词"""
```

#### 任务2.3: 句式多样化策略
**位置**: `src/core/human_touch/sentence_diversity.py`

**策略：**
1. **句长控制**：强制长短交替
2. **句式模板库**：提供多样化句式选择
3. **破碎句插入**：在情绪高潮处自动插入破碎句
4. **倒装与省略**：适当使用倒装句和省略句

### Phase 3: 润笔改写系统（第5-8周）

#### 任务3.1: 句式重构模块
**位置**: `src/core/human_touch/rewriting/sentence_rewriter.py`

**改写策略：**
```python
class SentenceRewriter:
    """句式重构器"""
    
    REWRITE_PATTERNS = {
        "split_long": "将长句拆分为短句组合",
        "insert_fragment": "在情绪点插入破碎句",
        "vary_length": "调整句子长度分布",
        "add_pauses": "通过标点和省略制造停顿",
        "reorder_clauses": "调整从句顺序制造变化",
    }
    
    def rewrite_paragraph(self, paragraph: str) -> str:
        """重写段落，增加句式多样性"""
```

#### 任务3.2: 感官增强模块
**位置**: `src/core/human_touch/rewriting/sensory_enhancer.py`

**功能：**
- 识别缺少感官描写的场景
- 自动注入五感细节
- 保持与情节的协调性

```python
class SensoryEnhancer:
    """感官增强器"""
    
    def enhance_scene(self, scene_text: str) -> str:
        """
        增强场景的感官描写
        - 识别当前感官覆盖
        - 补充缺失的感官维度
        - 用具体细节替代抽象描述
        """
```

#### 任务3.3: 口语化注入模块
**位置**: `src/core/human_touch/rewriting/colloquial_injector.py`

**改写策略：**
1. **对话口语化**：将书面化对话改为自然口语
2. **内心独白口语化**：内心活动更像自言自语
3. **叙述口语化**：叙述者声音更贴近日常讲述

#### 任务3.4: 个体腔调塑造模块
**位置**: `src/core/human_touch/rewriting/voice_shaper.py`

**功能：**
- 根据角色/题材确定腔调类型
- 统一全文的叙述声音
- 在保持一致性的同时注入个性

### Phase 4: 整体集成（第9-10周）

#### 任务4.1: 人味增强管道
**位置**: `src/core/human_touch/enhancement_pipeline.py`

**流程：**
```
原始章节
    ↓
[生成阶段注入]
- 人味风格指南
- 头部作品风格DNA
- 句式多样化指令
    ↓
初稿生成
    ↓
[润笔改写阶段]
- 句式重构
- 感官增强
- 口语化注入
- 腔调统一
    ↓
人味增强稿
    ↓
[质量检查]
- 人味指标评分
- AI检测概率预估
- 人工抽检
    ↓
终稿输出
```

#### 任务4.2: 配置系统
**位置**: `config/human_touch_config.yaml`

```yaml
human_touch:
  # 总开关
  enabled: true
  
  # 生成阶段配置
  generation:
    style_guide_injection: true
    sentence_diversity: true
    style_dna_source: "top_tier_samples"  # 头部作品样本
  
  # 润笔阶段配置
  rewriting:
    enabled: true
    modules:
      sentence_rewriter: true
      sensory_enhancer: true
      colloquial_injector: true
      voice_shaper: true
    
    # 改写强度
    intensity: "medium"  # light/medium/aggressive
    
  # 质量检查
  quality_check:
    human_touch_threshold: 0.7  # 人味分数阈值
    ai_detection_simulation: true  # 模拟AI检测
```

#### 任务4.3: UI集成
**位置**: `web/templates/human_touch_panel.html`

**功能：**
- 人味增强开关
- 风格选择（热血/冷幽默/沉稳等）
- 改写强度调节
- 人味分数预览
- 前后对比查看

### Phase 5: 验证与迭代（第11-12周）

#### 任务5.1: 对比测试
- 同一创意，生成三组：
  1. 原始市场导向模式
  2. 生成阶段优化版
  3. 完整人味增强版
- 邀请读者盲测
- 记录AI检测通过率

#### 任务5.2: 迭代优化
- 根据测试结果调整策略
- 优化提示词和改写规则
- 建立持续学习机制（新样本→风格更新）

## 四、技术细节

### 4.1 模型选择

| 阶段 | 推荐模型 | 理由 |
|-----|---------|------|
| 生成阶段 | Gemini 2.5 Flash / DeepSeek | 成本低，适合长文本 |
| 润笔改写 | GPT-4o / Claude 3.5 Sonnet | 改写质量高，理解细微差别 |
| 质量检查 | 本地小模型 / 规则引擎 | 成本低，实时反馈 |

### 4.2 成本控制策略

```python
# 分级处理
def process_chapter(chapter: Chapter) -> Chapter:
    # 1. 快速预检：本地模型评估人味分数
    score = quick_human_touch_score(chapter.content)
    
    if score >= 0.8:
        # 人味充足，仅做轻量优化
        return light_touch_up(chapter)
    elif score >= 0.5:
        # 中等优化
        return medium_enhancement(chapter)
    else:
        # 深度改写
        return deep_rewrite(chapter)
```

### 4.3 文件结构

```
src/core/human_touch/
├── __init__.py
├── analyzer.py                  # 人味特征分析器
├── style_guide.py               # 风格指南
├── style_injector.py            # 风格注入器
├── sentence_diversity.py        # 句式多样化
├── enhancement_pipeline.py      # 增强管道
├── quality_checker.py           # 质量检查器
├── config.py                    # 配置管理
└── rewriting/
    ├── __init__.py
    ├── base_rewriter.py         # 改写基类
    ├── sentence_rewriter.py     # 句式重构
    ├── sensory_enhancer.py      # 感官增强
    ├── colloquial_injector.py   # 口语化注入
    └── voice_shaper.py          # 腔调塑造

config/human_touch_config.yaml   # 配置文件
docs/human_touch_samples/        # 头部作品样本
└── [genre]/
    ├── samples.json            # 样本章节
    ├── style_dna.json          # 提取的风格DNA
    └── analysis_report.md      # 分析报告
```

## 五、预期效果

### 5.1 量化指标

| 指标 | 当前AI文 | 目标 | 头部作品参考 |
|-----|---------|------|-------------|
| 句长方差 | < 5 | > 15 | 20-30 |
| 感官密度 | < 0.1 | > 0.3 | 0.4-0.6 |
| 口语化比例 | < 0.2 | > 0.4 | 0.5-0.7 |
| 破碎句比例 | < 0.05 | > 0.15 | 0.2-0.3 |
| AI检测概率 | > 0.8 | < 0.3 | < 0.2 |

### 5.2 质性指标

- 读者盲测：人味增强版 vs 头部作品，区分率<30%
- 编辑评价：通过人工审核率提升50%
- 平台表现：推荐量和阅读量提升

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 改写过度，失去原有风格 | 高 | 可配置改写强度，保留原始版本 |
| 成本超预算 | 中 | 分级处理，低分章节才深度改写 |
| 效果不达预期 | 中 | 持续迭代，建立反馈循环 |
| 与现有系统冲突 | 低 | 模块化设计，可独立开关 |

## 七、下一步行动

1. **确认计划**：用户审核此计划
2. **收集样本**：用户提供3-5本认为"人味足"的番茄头部作品
3. **开始Phase 1**：建立分析框架，分析样本
4. **建立baseline**：分析当前AI生成文本，量化差距
