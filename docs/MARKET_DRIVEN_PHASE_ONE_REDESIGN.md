# 第一阶段彻底市场导向整改方案
## 核心思想：不是"我想写什么"，而是"市场需要什么"

---

## 一、当前问题诊断

### 现有流程的问题

```
现有流程（作者中心）：
用户创意 → AI生成方案 → AI写设定 → 优化 → 生成章节
     ↑
问题：用户创意可能不符合市场，AI自由发挥可能偏离套路
```

**问题1：创意驱动而非市场驱动**
- 用户输入一个创意，AI基于这个创意展开
- 如果创意本身不符合市场，后面全错
- 例：用户想写"主角养花的日常"，但这在番茄不火

**问题2：自由生成而非套路生成**
- AI自由发挥写世界观、角色
- 可能写出"有创意但没市场"的设定
- 例：AI设计了一个复杂的政治斗争世界观，但读者爱看的是简单直白的升级

**问题3：缺乏市场验证环节**
- 生成过程中没有对照同类爆款
- 不知道"神豪文的标准套路是什么"
- 生成后才发现和市场脱节

---

## 二、整改核心思想

### 新的流程（市场中心）

```
新流程：
用户选择题材（如神豪文）→ 系统提取该题材套路 → 基于套路生成方案 → 
基于套路写设定 → 对标爆款优化 → 生成章节
     ↑                                              ↑
用户只选择大方向                              全程套入已验证套路
```

### 核心原则

1. **题材决定套路**
   - 每种题材都有已验证的爆款公式
   - 不是创新，而是**复用成功公式**
   - 例：神豪文 = 穷→获得系统→花钱返利→打脸→升级身份→更大打脸

2. **套路决定设定**
   - 世界观、角色、剧情都要**服务套路**
   - 不是"我想设计一个什么样的世界"，而是"神豪文需要什么样的世界"
   - 例：神豪文的世界不需要复杂政治，需要"有钱就能解决一切"的简单逻辑

3. **对标而非创造**
   - 每个环节都要**对标同类爆款**
   - 不是"我觉得这样写挺好"，而是"头部作者都这么写"
   - 例：神豪文主角必须开局穷，这是套路，不要创新

---

## 三、整改后的第一阶段流程

### 步骤0：题材选择（新增）

**用户不再输入创意，而是选择题材**

```
请选择您要写的题材（已验证市场）：
├── 神豪文（花钱返利类）
├── 神豪文（签到奖励类）
├── 国运文（直播类）
├── 国运文（禁地探险类）
├── 签到文（日常签到类）
├── 签到文（异界签到类）
├── 奶爸文（萌宝类）
├── 奶爸文（修炼类）
├── 神选文（神明选拔类）
├── 模拟器文（人生模拟类）
└── ...（其他已验证题材）
```

**每个题材附带：**
- 该题材在番茄的平均数据（完读率、稿费区间）
- 该题材当前是否热门（上升/平稳/下降）
- 该题材的竞争程度（红海/蓝海）

---

### 步骤1：套路提取（新增）

**系统从番茄头部作品中提取该题材的爆款套路**

```python
def extract_genre_tropes(genre: str) -> Dict:
    """
    提取题材的爆款套路
    基于番茄该题材Top100作品分析
    """
    return {
        "神豪文-花钱返利类": {
            # 核心套路公式
            "core_formula": "穷屌丝→获得花钱返利系统→被迫花钱→装逼打脸→身份升级→更大场面",
            
            # 开局套路（必须这样写）
            "opening_tropes": {
                "chapter_1": {
                    "must_have": ["主角穷到极点", "被前女友/亲戚羞辱", "获得系统"],
                    "must_not_have": ["主角本来就富", "慢慢介绍背景", "没有冲突"],
                    "example": "开局送外卖被宝马男撞，对方耍赖，主角激活系统"
                },
                "chapter_2_3": {
                    "must_have": ["第一次花钱", "第一次返利", "第一次打脸"],
                    "pattern": "系统任务→被迫高消费→周围人震惊→获得返利→实力提升"
                }
            },
            
            # 金手指套路
            "golden_finger_tropes": {
                "type": "花钱返利",
                "ratio": "10倍返利是标配",
                "trigger": "必须在正常消费场景触发",
                "limitation": "初期有金额限制，后期解除"
            },
            
            # 爽点套路
            "climax_tropes": [
                "初期：打外卖站长、打宝马男",
                "中期：打富二代、打家族",
                "后期：打资本、打国外势力"
            ],
            
            # 角色套路
            "character_tropes": {
                "protagonist": "开局必须是穷屌丝，性格隐忍但爆发力强",
                "antagonist": "初期：势利眼；中期：富二代；后期：资本大佬",
                "female_lead": "初期看不起主角，后期跪舔；或一开始就看中主角潜力"
            },
            
            # 世界观套路
            "worldview_tropes": {
                "setting": "现代都市，钱能通神",
                "society": "阶层分明，有钱就是大爷",
                "power_system": "系统提供资金，资金带来权力"
            },
            
            # 节奏套路
            "pacing_tropes": {
                "climax_frequency": "每3章一个小爽点，每10章一个大爽点",
                "upgrade_frequency": "每30章身份升级一次",
                "face_slap_frequency": "不能断，保持连续打脸"
            },
            
            # 对标作品
            "benchmark_works": [
                {"title": "开局物价贬值百万倍", "why": "开局长度控制得好，系统出现时机完美"},
                {"title": "我有九千万亿舔狗金", "why": "打脸节奏把握精准"},
                {"title": "神豪：从被校花拒绝开始", "why": "情绪调动到位"}
            ]
        }
    }
```

---

### 步骤2：基于套路的方案生成（修改）

**不是生成方案，而是套用套路模板**

```python
def generate_plan_based_on_tropes(tropes: Dict, user_preferences: Dict) -> Dict:
    """
    基于套路模板生成方案
    用户只能做选择题，不能自由发挥
    """
    
    plan = {
        # 标题必须从套路模板中选择
        "title_options": tropes["title_templates"],
        # 例：神豪文标题模板
        # ["开局物价贬值百万倍", "我有九千万亿舔狗金", "神豪：从被校花拒绝开始"]
        
        # 金手指必须是该题材标准金手指
        "golden_finger": tropes["golden_finger_tropes"],
        
        # 主角人设必须遵循套路
        "protagonist": tropes["character_tropes"]["protagonist"],
        
        # 核心冲突必须遵循套路
        "core_conflict": tropes["core_formula"],
        
        # 用户可选择的微调（在套路框架内）
        "user_choices": {
            "antagonist_type": ["势利眼前女友", "势利眼亲戚", "势利眼上司"],  # 必须选
            "initial_scenario": ["送外卖", "当保安", "摆地摊"],  # 必须选
            "first_big_face_slap": ["买车", "买房", "打赏主播"],  # 必须选
        }
    }
    
    return plan
```

**用户界面示例：**
```
已为您匹配神豪文-花钱返利类的爆款套路

✅ 标题建议（任选其一）：
  ○ 开局物价贬值百万倍，我成了神豪
  ○ 我有九千万亿舔狗金，却只爱一人
  ○ 神豪：从被校花拒绝开始

✅ 金手指设定（已固定）：
  花钱10倍返利系统
  - 必须完成任务才能激活
  - 返利金额随等级提升
  【不可修改，这是该题材标配】

✅ 主角设定（已固定）：
  开局：穷外卖员/保安/摆地摊
  性格：隐忍，不主动惹事，但不怕事
  【不可修改，这是读者代入的基础】

⚙️ 您可以选择的细节：
  - 羞辱主角的人是谁？ [前女友/亲戚/上司]
  - 第一次打脸场景？ [4S店买房/直播间打赏]
  - 第一个身份升级节点？ [30章成为豪车车主/50章成为商场股东]

❌ 以下选择会导致作品不火：
  × 主角开局不穷
  × 系统没有返利机制
  × 主角性格过于温和不反击
```

---

### 步骤3：基于套路的产物生成（修改）

**每个产物都必须符合套路模板**

#### 世界观生成（套路化）

```python
def generate_worldview_by_tropes(tropes: Dict) -> Dict:
    """
    基于套路生成世界观
    不是创造，而是套用已验证的框架
    """
    
    worldview_template = tropes["worldview_tropes"]
    
    return {
        "world_overview": worldview_template["setting"],
        "power_system": {
            # 神豪文的力量体系就是资金等级
            "levels": [
                {"name": "穷屌丝", "threshold": 0, "description": "开局必须这样"},
                {"name": "小有资产", "threshold": 1000000, "description": "第10章左右"},
                {"name": "地方富豪", "threshold": 100000000, "description": "第50章左右"},
                {"name": "全国富豪", "threshold": 10000000000, "description": "第200章左右"},
                {"name": "全球首富", "threshold": 1000000000000, "description": "后期"}
            ]
        },
        "social_structure": worldview_template["society"],
        "key_locations": [
            # 神豪文的标准场景
            "4S店（装逼打脸高发地）",
            "高档餐厅（身份揭示地）",
            "直播间（打赏装逼地）",
            "豪宅/别墅（身份象征）",
            "高档商场（消费打脸地）"
        ]
    }
```

#### 角色设计（套路化）

```python
def generate_characters_by_tropes(tropes: Dict) -> Dict:
    """
    基于套路生成角色
    每个角色都有固定的套路功能
    """
    
    character_tropes = tropes["character_tropes"]
    
    return {
        "main_character": {
            "name": "由用户选择",
            "background": tropes["opening_tropes"]["chapter_1"]["must_have"][0],  # 必须穷
            "personality": character_tropes["protagonist"],
            "growth_arc": tropes["core_formula"],
            "must_do": ["隐忍", "反击", "升级", "打脸"],
            "must_not_do": ["主动惹事", "圣母", "优柔寡断"]
        },
        
        "antagonist_tier_1": {
            # 初期反派：势利眼
            "function": "制造开局冲突",
            "examples": ["势利眼前女友", "势利眼宝马男", "势利眼站长"],
            "defeat_chapter": "第5-10章必须被打脸",
            "pattern": "看不起→羞辱→主角反击→震惊→后悔"
        },
        
        "antagonist_tier_2": {
            # 中期反派：富二代
            "function": "提供中期爽点",
            "examples": ["地方富二代", "家族子弟"],
            "defeat_chapter": "第50-100章",
            "pattern": "炫富→压主角→主角更有钱→碾压"
        },
        
        "female_lead": {
            "function": "情感线和侧面装逼",
            "options": [
                "势利眼型：初期看不起主角，后期跪舔",
                "慧眼识珠型：初期就看好主角，投资潜力股",
                "冰山女神型：被主角慢慢融化"
            ],
            "note": "必须让读者觉得主角配得上最好的"
        }
    }
```

#### 阶段计划（套路化）

```python
def generate_stage_plans_by_tropes(tropes: Dict) -> Dict:
    """
    基于套路生成阶段计划
    严格遵循该题材的节奏公式
    """
    
    pacing = tropes["pacing_tropes"]
    
    return {
        "stage_1": {
            "chapters": "1-30",
            "theme": "激活系统，第一次打脸",
            "must_have_events": [
                {"chapter": 1, "event": "获得系统", "climax_type": "转折"},
                {"chapter": 3, "event": "第一次花钱", "climax_type": "小爽点"},
                {"chapter": 5, "event": "第一次打脸", "climax_type": "爽点"},
                {"chapter": 10, "event": "身份首次升级", "climax_type": "中爽点"},
                {"chapter": 30, "event": "第一阶段高潮", "climax_type": "大爽点"}
            ],
            "climax_frequency": pacing["climax_frequency"]
        },
        
        "stage_2": {
            "chapters": "31-100",
            "theme": "身份升级，更大的打脸",
            "must_have_events": [
                {"chapter": 50, "event": "成为地方富豪", "climax_type": "身份升级"},
                {"chapter": 80, "event": "打脸地方势力", "climax_type": "大爽点"},
                {"chapter": 100, "event": "进入更高圈子", "climax_type": "转折"}
            ]
        },
        
        # 后续阶段...
    }
```

---

### 步骤4：套路验证（新增）

**生成每个产物后，都要验证是否符合套路**

```python
def validate_against_tropes(product: Dict, tropes: Dict, product_type: str) -> ValidationResult:
    """
    验证产物是否符合套路
    不符合则强制修改
    """
    
    violations = []
    
    if product_type == "worldview":
        # 验证世界观是否符合题材套路
        if "power_system" in product:
            levels = product["power_system"].get("levels", [])
            if len(levels) < 5:
                violations.append("力量体系层级太少，神豪文需要5个资金等级")
        
        # 神豪文必须有消费场景
        locations = product.get("key_locations", [])
        required_locations = ["4S店", "高档餐厅", "直播间"]
        for loc in required_locations:
            if not any(loc in l for l in locations):
                violations.append(f"缺少必要场景：{loc}，神豪文装逼需要这个场景")
    
    elif product_type == "character_design":
        # 验证主角是否符合套路
        protagonist = product.get("main_character", {})
        if protagonist.get("background") != "穷":
            violations.append("主角开局必须穷，这是神豪文套路")
        
        if protagonist.get("personality") == "圣母":
            violations.append("主角性格不能圣母，神豪文需要杀伐果断")
    
    elif product_type == "stage_writing_plans":
        # 验证节奏是否符合套路
        events = product.get("events", [])
        if not any(e.get("chapter") == 1 and "系统" in str(e) for e in events):
            violations.append("第1章必须出现系统，延迟出现会导致流失")
    
    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        auto_fixes=generate_fixes(violations, tropes)  # 自动修复建议
    )
```

---

### 步骤5：对标优化（修改）

**不是优化"写得好不好"，而是优化"和爆款差多少"**

```python
def optimize_against_benchmarks(products: Dict, tropes: Dict) -> OptimizationResult:
    """
    对标爆款进行优化
    找出和头部作品的差距
    """
    
    benchmarks = tropes["benchmark_works"]
    
    comparison = {
        "opening": compare_opening(products, benchmarks),
        "pacing": compare_pacing(products, benchmarks),
        "climax_design": compare_climax(products, benchmarks),
        "character_depth": compare_characters(products, benchmarks)
    }
    
    # 生成对齐建议
    optimizations = []
    for aspect, result in comparison.items():
        if result["gap"] > 0.3:  # 差距超过30%
            optimizations.append({
                "aspect": aspect,
                "current": result["current"],
                "benchmark": result["benchmark"],
                "gap": result["gap"],
                "suggestion": result["suggestion"]
            })
    
    return OptimizationResult(
        overall_alignment=1 - sum(r["gap"] for r in comparison.values()) / len(comparison),
        optimizations=optimizations
    )
```

---

## 四、整改后的用户界面

### 新界面（市场导向）

```
╔════════════════════════════════════════════════════════════╗
║         欢迎使用番茄小说爆款生成器                          ║
║     基于市场数据，生成符合套路的作品                        ║
╚════════════════════════════════════════════════════════════╝

步骤1：选择题材（已验证市场）
────────────────────────────────────
请选择您要写的题材：

[热门题材]
  🔥 神豪文 → 花钱返利类（完读率15%，月入过万概率高）
  🔥 神豪文 → 签到奖励类（完读率12%，竞争激烈）
  🔥 国运文 → 直播类（完读率18%，当前上升期）
  🔥 奶爸文 → 萌宝类（完读率20%，蓝海市场）

[您选择的题材：神豪文-花钱返利类]

该题材的爆款公式：
穷屌丝 → 获得花钱返利系统 → 被迫花钱 → 装逼打脸 → 身份升级 → 更大场面

✅ 优势：市场大，读者多，套路成熟
⚠️ 风险：竞争激烈，需要执行力
────────────────────────────────────

步骤2：选择套路细节（基于头部作品分析）
────────────────────────────────────

[开局设定]（必须从以下选择，这些已验证能火）
  ○ 送外卖被宝马男撞，对方耍赖（参考：《开局物价贬值百万倍》）
  ○ 当保安被富二代羞辱（参考：《我有九千万亿舔狗金》）
  ○ 摆地摊被前女友看不起（参考：《神豪：从被校花拒绝开始》）

[金手指设定]（已固定，这是标配）
  ✅ 花钱10倍返利系统
  ✅ 完成任务激活返利
  ✅ 返利金额随等级提升
  [不可修改]

[第一次打脸场景]（选择最火的）
  ○ 4S店买车，销售员狗眼看人低（热度：⭐⭐⭐⭐⭐）
  ○ 高档餐厅吃饭，被服务员看不起（热度：⭐⭐⭐⭐）
  ○ 直播间打赏，被主播嘲讽（热度：⭐⭐⭐⭐⭐）

[反派类型]（多选，按顺序出现）
  □ 势利眼前女友（必选项，90%爆款都有）
  □ 势利眼亲戚（可选，增加代入感）
  □ 势利眼上司（可选，职场共鸣）
────────────────────────────────────

步骤3：生成基于套路的设定
────────────────────────────────────

正在基于您选择的套路生成设定...

✅ 世界观生成完成
   基于神豪文套路：现代都市，钱能通神
   包含必要场景：4S店、高档餐厅、直播间

✅ 角色设计完成
   主角：穷外卖员，隐忍型，符合套路
   初期反派：势利眼前女友（已验证有效）
   中期反派：地方富二代（套路标配）

✅ 阶段计划生成完成
   第1章：获得系统（套路要求）
   第3章：第一次花钱（节奏要求）
   第5章：第一次打脸（爽点要求）
   第30章：身份首次升级（节奏要求）

⚠️ 套路验证通过
────────────────────────────────────

步骤4：对标爆款优化
────────────────────────────────────

正在对比同类爆款作品...

vs 《开局物价贬值百万倍》：
  ✅ 开节奏相似（95%匹配）
  ⚠️ 爽点密度略低（建议增加2个中期爽点）

vs 《我有九千万亿舔狗金》：
  ✅ 金手指设计符合套路
  ✅ 打脸节奏匹配

优化建议：
  1. 第15章增加一个"买车打脸"爽点（对标爆款第12章）
  2. 女主角提前到第8章出场（爆款平均第7章）
────────────────────────────────────

步骤5：生成完成
────────────────────────────────────

✅ 您的作品已基于市场套路生成完成！

预估数据：
  - 完读率：12-18%（基于同类作品平均）
  - 稿费潜力：3000-8000元/月（基于执行力）
  - 火的可能性：中高（符合套路）

⚠️ 重要提示：
  生成后不要大幅修改设定，这会偏离套路！
  如果必须修改，请先查看该题材的"修改禁区"。

下一步：开始生成章节（将严格遵循套路节奏）
────────────────────────────────────
```

---

## 五、关键修改点汇总

### 1. 新增：套路数据库

```python
# 建立题材-套路数据库
genre_tropes_db = {
    "神豪文-花钱返利类": {
        # 完整的套路模板（见上文）
    },
    "国运文-直播类": {
        # 完整的套路模板
    },
    # ... 其他题材
}

# 套路数据来源：
# 1. 番茄该题材Top100作品分析
# 2. 编辑推荐的爆款公式
# 3. 数据分析团队提供的套路报告
```

### 2. 修改：方案生成逻辑

```python
# 旧逻辑（创意驱动）
def generate_plan(creative_seed):
    # 基于用户创意自由生成
    return ai_generate(creative_seed)

# 新逻辑（套路驱动）
def generate_plan(genre, user_choices):
    tropes = genre_tropes_db[genre]
    # 基于套路模板填充用户选择
    return fill_trope_template(tropes, user_choices)
```

### 3. 新增：套路验证层

```python
# 在产物生成后插入验证
def generate_and_validate(product_type, genre):
    tropes = genre_tropes_db[genre]
    product = generate_by_tropes(tropes, product_type)
    
    # 验证是否符合套路
    validation = validate_against_tropes(product, tropes, product_type)
    if not validation.is_valid:
        # 强制修复
        product = auto_fix(product, validation.violations, tropes)
    
    return product
```

### 4. 修改：优化逻辑

```python
# 旧逻辑（通用优化）
def optimize(products):
    return general_optimize(products)

# 新逻辑（对标优化）
def optimize(products, genre):
    tropes = genre_tropes_db[genre]
    benchmarks = tropes["benchmark_works"]
    # 对标爆款找出差距
    return benchmark_optimize(products, benchmarks)
```

---

## 六、预期效果

### 整改前
- 用户输入创意 → AI自由发挥 → 可能偏离市场 → 数据差

### 整改后
- 用户选择题材 → 套用已验证套路 → 符合市场 → 数据好

### 关键指标预期提升

| 指标 | 整改前 | 整改后（预期） | 提升原因 |
|------|--------|---------------|---------|
| 首章流失率 | 50-60% | 30-40% | 开局严格遵循爆款套路 |
| 10章留存 | 20-30% | 35-45% | 节奏符合市场验证 |
| 完读率 | 5-10% | 12-18% | 爽点设计对标爆款 |
| 月入过万比例 | <5% | 15-25% | 全程市场导向 |

---

## 七、实施建议

### 阶段1：建立套路数据库（2-4周）
1. 分析番茄各题材Top100作品
2. 提取爆款套路公式
3. 建立套路数据库

### 阶段2：修改生成逻辑（2-3周）
1. 修改方案生成，套用套路模板
2. 修改产物生成，符合套路要求
3. 新增套路验证层

### 阶段3：对标优化系统（1-2周）
1. 建立爆款对标系统
2. 实现差距分析和自动修复
3. 集成到生成流程

### 阶段4：界面改造（1周）
1. 重新设计用户界面
2. 从创意输入改为题材选择
3. 增加套路说明和数据展示

---

## 总结

**核心转变：**
- ❌ 从"我想写什么"（创意驱动）
- ✅ 到"市场需要什么"（套路驱动）

**核心理念：**
- 网络文学的成功不是创造新套路，而是**复用已验证的爆款套路**
- 用户的创意可能不符合市场，但**套路数据库里的公式一定符合市场**
- 不是"写得好不好"，而是"套用得对不对"

**最终目标：**
让每一本生成的书都**严格遵循番茄平台的爆款套路**，最大程度提高成功概率。
