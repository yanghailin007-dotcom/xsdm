# 文风库使用文档

## 快速开始

### 1. 录入头部作品风格

用户提供截图 → 大模型识别文字 → 录入系统

```bash
python tools/style_collector.py
```

交互流程：
1. 输入书名、作者、题材
2. 输入风格标签（如：热血、快节奏、口语化）
3. 粘贴章节内容（可多章）
4. 系统自动分析并入库

### 2. 在代码中使用

```python
from src.core.style_library import (
    StyleDatabase, StyleMatcher, 
    StyleRequirements, StyleInjector
)

# 初始化
db = StyleDatabase()
matcher = StyleMatcher(db)
injector = StyleInjector()

# 匹配风格
requirements = StyleRequirements(
    genre="赘婿",
    tone_tags=["热血", "快节奏"],
    description="像上门龙婿那种打脸爽文"
)

matches = matcher.match(requirements, top_k=3)

# 获取最佳匹配
best_style = matches[0].profile
print(f"匹配到风格: {best_style.title} (相似度{matches[0].match_score:.1f}%)")

# 生成风格Prompt
style_prompt = injector.generate_prompt(best_style)

# 用于生成
full_prompt = f"""
{base_writing_prompt}

{style_prompt}

请按以上风格要求生成章节。
"""
```

## 系统架构

```
src/core/style_library/
├── database.py      # 数据库存储
├── extractor.py     # 特征提取
├── matcher.py       # 风格匹配
└── injector.py      # 风格注入
```

### 风格指纹 (StyleFingerprint)

18维特征向量：
- **句式维度**: 平均句长、句长方差、短句比例、破碎句比例、问句比、感叹句比
- **词汇维度**: 口语化密度、语气词密度、重复率、词汇丰富度
- **节奏维度**: 对话占比、段长、过渡词比例、硬切比例
- **情感维度**: 感官密度、情绪词密度、展示比例

### 匹配算法

1. **标签过滤**: 先按题材+腔调筛选候选集
2. **向量相似度**: 计算18维向量的余弦相似度
3. **加权排序**: 综合标签匹配度和指纹相似度

## 典型使用场景

### 场景1：精确复刻某本书的风格

```python
# 直接获取已有风格
profile = db.get_profile_by_title("上门龙婿")
prompt = injector.generate_prompt(profile)
```

### 场景2：描述需求，自动匹配

```python
# 自然语言描述
matches = matcher.match_by_description(
    "快节奏打脸爽文，口语化强，短句多",
    genre="赘婿"
)

# 使用最佳匹配
best = matches[0]
```

### 场景3：混合两种风格

```python
# 70%上门龙婿 + 30%绝世强龙
mixed_fp = matcher.mix_styles([
    (profile1.id, 0.7),
    (profile2.id, 0.3)
])

# 生成混合风格Prompt
prompt = injector.generate_mixed_prompt(
    [profile1, profile2], 
    [0.7, 0.3]
)
```

## 数据结构

### style_profiles 表

| 字段 | 说明 |
|-----|------|
| id | 风格ID |
| title | 书名 |
| author | 作者 |
| genre | 题材 |
| tone_tags | 腔调标签 ["热血","快节奏"] |
| pace | 节奏 |
| fingerprint | 18维风格向量（JSON） |
| chapter_count | 样本章节数 |

### chapter_samples 表

| 字段 | 说明 |
|-----|------|
| id | 章节ID |
| profile_id | 所属风格 |
| chapter_number | 章节号 |
| content | 原文（可选） |
| fingerprint | 该章的指纹 |

## 录入建议

### 选书标准
- 番茄头部作品（阅读100万+）
- 评分9.0+
- 风格鲜明

### 样本选择
每本书建议录入：
- 开头1-2章（学习抓人技巧）
- 中期1-2章（学习节奏控制）
- 高潮1章（学习爽点营造）

### 风格标签建议
```
题材: 赘婿, 玄幻, 都市, 年代, 悬疑
腔调: 热血, 幽默, 压抑, 甜宠, 严肃
节奏: 快节奏, 慢节奏, 张弛有度
特色: 口语化, 细腻, 脑洞大, 反转多
```

## 数据库位置

```
data/style_library/styles.db
```

可直接用SQLite工具查看。

## 扩展计划

- [ ] 接入LLM自动解析风格描述
- [ ] 风格聚类自动分组
- [ ] 生成效果反馈闭环
