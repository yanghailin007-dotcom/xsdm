# 文风库系统

精准匹配头部作品风格的完整解决方案。

## 核心功能

1. **风格录入** - 分析头部作品，提取18维风格特征
2. **风格匹配** - 根据需求自动匹配最相似的风格
3. **风格混合** - 支持多种风格按比例混合
4. **风格注入** - 将风格特征转换为Prompt指令

## 快速使用

### 录入风格

```bash
python tools/style_collector.py
```

用户只需：
1. 提供截图（大模型识别文字）
2. 输入书名、题材、风格标签
3. 粘贴章节内容
4. 系统自动分析入库

### 使用风格

```python
from src.core.style_library import StyleDatabase, StyleMatcher, StyleInjector

db = StyleDatabase()
matcher = StyleMatcher(db)
injector = StyleInjector()

# 匹配风格
matches = matcher.match_by_description("快节奏打脸爽文", genre="赘婿")
best = matches[0].profile

# 生成风格Prompt
prompt = injector.generate_prompt(best)
```

## 文件结构

```
src/core/style_library/
├── __init__.py
├── database.py      # StyleDatabase, StyleProfile, StyleFingerprint
├── extractor.py     # StyleExtractor - 特征提取
├── matcher.py       # StyleMatcher - 风格匹配
├── injector.py      # StyleInjector - Prompt生成
└── README.md

tools/
└── style_collector.py   # 交互式录入工具

docs/
└── style_library_usage.md   # 详细使用文档
```

## 18维风格特征

| 维度 | 特征 | 说明 |
|-----|------|------|
| 句式 | 句长方差 | 最重要指标，头部作品通常15-40 |
| 句式 | 短句比例 | <10字的句子占比 |
| 句式 | 破碎句比例 | <5字的极短句 |
| 词汇 | 口语化密度 | 口语词汇的频率 |
| 词汇 | 词汇丰富度 | 不同词占比 |
| 节奏 | 对话占比 | 引号内内容比例 |
| 节奏 | 硬切比例 | 无过渡的段落切换 |
| 情感 | 感官密度 | 五感描写的频率 |
| 情感 | 展示比例 | 展示vs讲述 |

## 匹配算法

```
1. 标签过滤（题材+腔调）
2. 18维向量余弦相似度
3. 加权综合排序
```

## 数据库

位置：`data/style_library/styles.db`

表：
- `style_profiles` - 风格档案
- `chapter_samples` - 章节样本
- `style_mixes` - 混合风格（预留）

## 使用文档

详细文档：`docs/style_library_usage.md`
