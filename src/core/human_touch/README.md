# 人味增强系统

让AI写作更像真人的完整解决方案。

## 系统架构

```
人味增强系统
├── database.py          # 头部作品样本数据库
├── analyzer.py          # 人味特征分析器
├── style_guide.py       # 风格指南（待实现）
├── style_injector.py    # 风格注入器（待实现）
└── rewriting/           # 润笔改写模块（待实现）
    ├── sentence_rewriter.py
    ├── sensory_enhancer.py
    ├── colloquial_injector.py
    └── voice_shaper.py
```

## 快速开始

### 1. 收集头部作品样本

```bash
# 交互式录入
python tools/sample_collector.py

# 或批量导入
python tools/sample_collector.py --import samples.json
```

### 2. 分析AI生成文本

```bash
# 分析单个章节
python tools/analyze_ai_text.py --file chapter_001.txt --compare

# 分析整个项目
python tools/analyze_ai_text.py --project "小说项目/我的小说"
```

### 3. 在代码中使用

```python
from src.core.human_touch import HumanTouchAnalyzer, SampleDatabase

# 分析文本
analyzer = HumanTouchAnalyzer()
metrics = analyzer.analyze("你的文本内容...")

print(f"人味分数: {metrics.overall_score}")
print(f"句长方差: {metrics.sentence_variance}")

# 查询样本数据库
db = SampleDatabase()
novels = db.get_all_novels(genre="赘婿")
```

## 核心指标

### 人味分数计算维度

| 维度 | 权重 | 说明 |
|-----|------|------|
| 句长方差 | 25% | 句式变化程度，头部作品通常15-40 |
| 破碎句比例 | 15% | 短句占比，头部作品通常10-20% |
| 感官密度 | 20% | 五感描写丰富度 |
| 口语化程度 | 15% | 对话自然度 |
| 词汇多样性 | 15% | 词汇丰富度 |
| 展示比例 | 10% | 展示vs讲述 |

### 头部作品基准线

```python
# 赘婿类
{
    'sentence_variance': 20.0,
    'fragment_ratio': 0.12,
    'sensory_density': 0.03,
    'overall_score': 65.0,
}

# 玄幻类
{
    'sentence_variance': 30.0,
    'fragment_ratio': 0.18,
    'sensory_density': 0.05,
    'overall_score': 75.0,
}
```

## 数据表结构

### novels 表（小说样本）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| title | TEXT | 书名 |
| author | TEXT | 作者 |
| genre | TEXT | 题材 |
| rating | REAL | 评分 |
| sample_reason | TEXT | 选择理由 |
| style_tags | TEXT | 风格标签(JSON) |
| overall_metrics | TEXT | 整体指标(JSON) |

### chapters 表（章节样本）

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| novel_id | INTEGER | 外键 |
| chapter_number | INTEGER | 章节号 |
| content | TEXT | 正文内容 |
| word_count | INTEGER | 字数 |
| metrics | TEXT | 分析指标(JSON) |
| sentence_variance | REAL | 句长方差 |

## 开发计划

### Phase 1: 基础设施 ✅
- [x] 样本数据库
- [x] 特征分析器
- [x] 数据收集工具

### Phase 2: 样本收集
- [ ] 收集各题材头部作品样本
- [ ] 建立基准线数据

### Phase 3: 生成优化（待开发）
- [ ] 人味写作风格指南
- [ ] 头部作品风格注入
- [ ] 句式多样化策略

### Phase 4: 润笔改写（待开发）
- [ ] 句式重构模块
- [ ] 感官增强模块
- [ ] 口语化注入模块
- [ ] 个体腔调塑造模块

## 相关文档

- [样本收集指南](../../docs/human_touch_sample_guide.md)
- [完整计划](../../docs/human-like-writing-enhancement.md)
