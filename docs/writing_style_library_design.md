# 庞大文风库系统设计方案

## 一、核心概念

### 1.1 什么是文风？

文风不仅仅是"人味"，而是更细粒度的写作特征：

```
文风 = 题材类型 + 叙事腔调 + 句式节奏 + 词汇偏好 + 情感表达 + 节奏控制
```

**示例：**
- 《上门龙婿》：赘婿题材 + 快节奏 + 口语化 + 强冲突 + 短句为主
- 《道诡异仙》：玄幻题材 + 诡异氛围 + 细腻描写 + 长句交错 + 心理刻画
- 《开局地摊卖大力》：都市脑洞 + 轻松幽默 + 吐槽风 + 网络化语言

### 1.2 系统目标

用户上传截图 → OCR识别 → 提取文风特征 → 入库 → 生成时自动匹配 → 风格注入

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       文风库系统                              │
├─────────────────────────────────────────────────────────────┤
│  输入层                                                        │
│  ├── 截图OCR模块 (tools/ocr_collector.py)                     │
│  │   └── 支持批量图片 → 文字识别 → 自动清洗                    │
│  ├── 手动录入模块 (tools/style_collector.py)                  │
│  │   └── 复制粘贴 → 结构化录入                                │
│  └── 网络采集模块 (可选)                                       │
│                                                                │
├─────────────────────────────────────────────────────────────┤
│  分析层                                                        │
│  ├── 文风特征提取器 (src/core/style_library/extractor.py)      │
│  │   ├── 句式指纹提取 (长短句分布、破碎句模式)                  │
│  │   ├── 词汇指纹提取 (高频词、独特用语、语气词)                │
│  │   ├── 节奏指纹提取 (段落长度、换行模式、标点运用)            │
│  │   └── 情感指纹提取 (情绪词汇密度、修辞手法偏好)              │
│  │                                                            │
│  └── 文风DNA生成器                                             │
│      └── 将多维度特征压缩为"风格向量"                          │
│                                                                │
├─────────────────────────────────────────────────────────────┤
│  存储层                                                        │
│  ├── 文风数据库 (data/style_library/style_db.sqlite)           │
│  │   ├── novels: 小说基本信息 + 风格标签                        │
│  │   ├── chapters: 章节原文 + 分析指标                          │
│  │   ├── style_profiles: 文风特征向量                           │
│  │   └── style_clusters: 聚类后的风格组                         │
│  │                                                            │
│  └── 文风模板库                                                │
│      └── 预定义的写作风格模板 (热血/幽默/悬疑/甜宠...)           │
│                                                                │
├─────────────────────────────────────────────────────────────┤
│  匹配层                                                        │
│  ├── 需求解析器 (src/core/style_library/matcher.py)            │
│  │   └── 将用户描述解析为风格需求向量                           │
│  │       例："快节奏赘婿打脸爽文" → [赘婿,快节奏,强冲突,口语化]  │
│  │                                                            │
│  ├── 风格匹配引擎                                              │
│  │   ├── 精确匹配：标签完全匹配                                 │
│  │   ├── 相似度匹配：向量余弦相似度                             │
│  │   └── 混合匹配：标签 + 向量 + 人工权重                       │
│  │                                                            │
│  └── 风格推荐器                                                │
│      └── 推荐Top-N相似风格，支持混合风格                        │
│                                                                │
├─────────────────────────────────────────────────────────────┤
│  应用层                                                        │
│  ├── 风格注入器 (src/core/style_library/injector.py)           │
│  │   └── 将选定的文风特征转换为Prompt指令                       │
│  │                                                            │
│  ├── 章节生成器集成                                            │
│  │   └── 在生成阶段自动加载匹配的风格                           │
│  │                                                            │
│  └── 风格混合器 (可选)                                         │
│      └── 支持两种风格混合 (如：热血70% + 幽默30%)               │
│                                                                │
└─────────────────────────────────────────────────────────────┘
```

## 三、核心模块设计

### 3.1 截图OCR模块

**技术选型：**
- 本地OCR：PaddleOCR（准确率高，免费）
- 云端OCR：百度OCR/腾讯OCR（识别率更高，但有成本）

**功能流程：**
```python
class OCRStyleCollector:
    """截图文风收集器"""
    
    def process_images(self, image_folder: str) -> List[ChapterSample]:
        """
        批量处理截图
        1. OCR识别文字
        2. 自动清洗（去除页眉页脚、章节导航）
        3. 分段处理
        4. 提取文风特征
        5. 入库
        """
```

**输入：** 文件夹内多张截图（支持jpg/png）
**输出：** 自动录入数据库，显示分析结果

### 3.2 文风特征向量

将文风量化为可计算的向量：

```python
@dataclass
class StyleFingerprint:
    """文风指纹"""
    
    # 1. 句式维度 (10维)
    sentence_pattern: List[float]  # 短句比、长句比、破碎句比、问句比、感叹句比...
    
    # 2. 词汇维度 (20维)
    vocabulary_profile: List[float]  # 高频词分布、成语密度、口语词密度、专业术语密度...
    
    # 3. 节奏维度 (10维)
    rhythm_pattern: List[float]  # 段长均值、段长方差、对话占比、动作描写密度...
    
    # 4. 情感维度 (10维)
    emotional_profile: List[float]  # 情绪词汇密度、修辞手法分布、氛围指标...
    
    # 5. 题材标签 (5维one-hot)
    genre_tags: List[int]  # [赘婿,玄幻,都市,年代,悬疑]
    
    # 6. 腔调标签 (5维one-hot)
    tone_tags: List[int]  # [热血,幽默,悬疑,甜宠,严肃]
    
    def to_vector(self) -> np.ndarray:
        """合并为完整风格向量 (60维)"""
        return np.concatenate([
            self.sentence_pattern,
            self.vocabulary_profile,
            self.rhythm_pattern,
            self.emotional_profile,
            self.genre_tags,
            self.tone_tags
        ])
```

### 3.3 风格匹配算法

```python
class StyleMatcher:
    """风格匹配器"""
    
    def match(self, requirements: StyleRequirements) -> List[StyleMatch]:
        """
        根据需求匹配最合适的文风
        
        匹配策略：
        1. 标签过滤：先按题材+腔调筛选候选集
        2. 向量相似度：计算余弦相似度
        3. 加权排序：结合人工权重（如句式权重>词汇权重）
        """
        
    def mix_styles(self, style1: StyleProfile, style2: StyleProfile, 
                   ratio: float = 0.5) -> StyleProfile:
        """
        混合两种风格
        例：热血风格70% + 幽默风格30%
        """
```

### 3.4 风格注入器

将风格特征转换为Prompt指令：

```python
class StyleInjector:
    """风格注入器"""
    
    def generate_style_prompt(self, style_profile: StyleProfile) -> str:
        """
        将风格档案转换为写作指令
        
        示例输出：
        【句式要求】
        - 短句占比60%，每章至少10个破碎句（"他愣住了。"）
        - 对话占比40%，使用口语化表达（"卧槽""啥情况"）
        - 避免连续3个长句（>40字）
        
        【节奏要求】
        - 每500字必须有一个小冲突
        - 每章结尾必须是悬念或反转
        - 情绪曲线：压抑→愤怒→爆发→爽感
        
        【词汇偏好】
        - 高频使用词汇：[打脸, 废物, 震惊, 不可能]
        - 语气词密度：每对话10%使用（啊/呢/吧/嘛）
        
        【腔调设定】
        - 叙述视角：第三人称，带轻微吐槽感
        - 主角内心OS：简短、直接、带情绪
        """
```

## 四、数据库设计

### 4.1 表结构

```sql
-- 小说表
CREATE TABLE novels (
    id INTEGER PRIMARY KEY,
    title TEXT,                    -- 书名
    author TEXT,                   -- 作者
    genre TEXT,                    -- 题材
    platform TEXT,                 -- 平台
    
    -- 风格标签（人工标注）
    tone_tags TEXT,                -- JSON ["热血", "快节奏"]
    style_description TEXT,        -- 风格描述
    
    -- 统计信息
    chapter_count INTEGER,
    total_words INTEGER,
    
    -- 风格向量（JSON）
    style_vector TEXT,
    
    created_at TEXT
);

-- 章节表
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    novel_id INTEGER,
    chapter_number INTEGER,
    title TEXT,
    content TEXT,                  -- 原文
    word_count INTEGER,
    
    -- 分析指标
    metrics TEXT,                  -- JSON
    style_vector TEXT,             -- 该章的风格向量
    
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 风格聚类表（自动维护）
CREATE TABLE style_clusters (
    id INTEGER PRIMARY KEY,
    cluster_name TEXT,             -- 聚类名称（如：热血赘婿型）
    center_vector TEXT,            -- 中心向量
    member_count INTEGER,          -- 成员数量
    keywords TEXT,                 -- 关键词
    sample_novel_ids TEXT          -- 示例小说ID列表
);

-- 用户偏好表（可选）
CREATE TABLE user_style_preferences (
    id INTEGER PRIMARY KEY,
    username TEXT,
    preferred_styles TEXT,         -- 偏好的风格ID列表
    custom_weights TEXT            -- 自定义权重
);
```

### 4.2 预定义风格模板

```python
# 系统内置的风格模板
PREDEFINED_STYLES = {
    "热血赘婿": {
        "genre": ["赘婿"],
        "tone": ["热血", "快节奏"],
        "sentence_variance": 20.0,
        "fragment_ratio": 0.15,
        "dialogue_ratio": 0.40,
        "colloquialism_density": 0.08,
    },
    "诡异修仙": {
        "genre": ["玄幻", "悬疑"],
        "tone": ["诡异", "压抑"],
        "sentence_variance": 35.0,
        "fragment_ratio": 0.20,
        "sensory_density": 0.06,
        "psychological_depth": 0.70,
    },
    "轻松脑洞": {
        "genre": ["都市", "脑洞"],
        "tone": ["幽默", "轻松"],
        "sentence_variance": 25.0,
        "colloquialism_density": 0.10,
        "self_awareness": 0.60,  # 吐槽/meta程度
    },
    "年代种田": {
        "genre": ["年代", "种田"],
        "tone": ["温馨", "慢节奏"],
        "sentence_variance": 30.0,
        "detail_density": 0.50,  # 细节描写密度
        "life_vibe": 0.80,       # 生活气息
    }
}
```

## 五、使用流程

### 5.1 建立文风库（一次性工作）

```bash
# 步骤1：收集样本（用户上传截图）
python tools/ocr_collector.py --input ~/screenshots/ --genre 赘婿

# 步骤2：自动分析并入库
# 系统会：OCR识别 → 提取特征 → 生成风格向量 → 存入数据库

# 步骤3：查看已建立的风格
python tools/style_viewer.py --list

# 输出：
# ID  | 书名           | 题材 | 风格标签         | 样本数
# ----|----------------|------|------------------|--------
# 1   | 上门龙婿       | 赘婿 | 热血,快节奏      | 5
# 2   | 绝世强龙       | 赘婿 | 热血,强冲突      | 3
# 3   | 道诡异仙       | 玄幻 | 诡异,悬疑        | 4
# ...
```

### 5.2 生成时自动匹配

在创作界面增加风格选择：

```yaml
# 创作配置
novel_config:
  title: "我的赘婿小说"
  genre: "赘婿"
  
  # 风格选择（多种方式）
  style_selection:
    # 方式1：精确匹配已有风格
    use_existing: "上门龙婿风格"
    
    # 方式2：描述需求，自动匹配
    description: "快节奏，强冲突，口语化，打脸爽文"
    
    # 方式3：混合风格
    mix:
      - style: "上门龙婿"
        weight: 0.7
      - style: "绝世强龙"
        weight: 0.3
    
    # 方式4：自定义微调
    customize:
      base: "上门龙婿"
      adjustments:
        dialogue_ratio: +0.1      # 增加对话
        sentence_variance: -5     # 降低句长变化
```

### 5.3 风格注入到生成流程

```python
# 在章节生成器中集成
class ChapterGenerator:
    def generate(self, chapter_num, style_config):
        # 1. 匹配风格
        style_profile = self.style_matcher.match(style_config)
        
        # 2. 生成风格提示词
        style_prompt = self.style_injector.generate(style_profile)
        
        # 3. 组合完整提示词
        full_prompt = f"""
        {base_prompt}
        
        {style_prompt}  # <-- 注入的风格指令
        
        请按以上要求生成第{chapter_num}章。
        """
        
        # 4. 生成
        return self.llm.generate(full_prompt)
```

## 六、关键技术点

### 6.1 OCR清洗

截图通常包含页眉页脚、章节导航、广告等噪音，需要自动清洗：

```python
def clean_ocr_text(raw_text: str) -> str:
    """清洗OCR识别结果"""
    # 去除常见噪音
    noise_patterns = [
        r'上一章.*?下一章',      # 章节导航
        r'\d+ / \d+',            # 页码
        r'番茄小说',             # 平台标识
        r'推荐阅读.*',           # 推荐
        r'本章完',               # 结尾标记
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    return text.strip()
```

### 6.2 风格向量降维

60维向量可能过于稀疏，使用PCA降维到10-20维，便于快速匹配。

### 6.3 增量学习

当新样本加入时，自动更新：
1. 该风格的中心向量
2. 聚类结果
3. 推荐权重

## 七、预期效果

### 7.1 精准匹配

用户描述："想要《上门龙婿》那种快节奏打脸的感觉"
→ 系统匹配：上门龙婿风格（相似度95%）
→ 生成文本：句式、节奏、词汇都接近目标作品

### 7.2 混合创新

用户描述："想要赘婿的热血 + 修仙的想象力"
→ 系统混合：热血赘婿70% + 诡异修仙30%
→ 生成文本：既有打脸爽感，又有奇幻设定

### 7.3 风格迁移

同一剧情，不同风格：
- 赘婿版：口语化，快节奏，强冲突
- 玄幻版：宏大叙事，细腻描写，慢热
- 轻松版：吐槽风，幽默梗，轻松愉快

## 八、实施建议

### 阶段1：基础建设（2周）
- [ ] OCR模块开发
- [ ] 数据库设计
- [ ] 基础特征提取

### 阶段2：样本积累（持续）
- [ ] 每种题材收集5-10本头部作品
- [ ] 每本5-10个章节样本
- [ ] 建立初始风格库（约50-100种风格）

### 阶段3：匹配算法（2周）
- [ ] 风格向量计算
- [ ] 相似度算法
- [ ] 推荐系统

### 阶段4：集成应用（2周）
- [ ] 风格注入器
- [ ] 生成器集成
- [ ] UI界面

### 阶段5：优化迭代（持续）
- [ ] 根据生成效果调整特征权重
- [ ] 增加更多维度（如：角色口吻、场景描写偏好）
- [ ] 用户反馈闭环

## 九、优势分析

| 优势 | 说明 |
|-----|------|
| **精准匹配** | 不是泛泛的"人味"，而是具体作品的"DNA" |
| **可复用** | 一次录入，永久使用，可跨项目复用 |
| **可混合** | 支持风格融合，创造新的写作风格 |
| **可量化** | 用数据说话，知道为什么像某个风格 |
| **可扩展** | 不断积累样本，风格库越来越丰富 |

这个设计将让系统从"模仿真人"进化到"模仿特定头部作品的风格"。
