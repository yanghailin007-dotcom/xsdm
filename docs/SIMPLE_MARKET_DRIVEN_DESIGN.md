# 简化版市场导向设计方案
## 核心：用AI实时分析，不用数据库

---

## 一、核心思路

```
用户选择题材 → AI实时分析番茄头部作品 → 提取套路 → 
基于套路生成 → AI验证是否符合套路 → 输出
```

**不需要：**
- ❌ 预建套路数据库
- ❌ 人工整理爆款公式
- ❌ 固定模板

**只需要：**
- ✅ AI实时爬取/分析番茄头部作品
- ✅ AI基于分析结果生成
- ✅ AI自我验证

---

## 二、具体实现

### 步骤1：AI实时分析头部作品

```python
def analyze_top_works(genre: str) -> Dict:
    """
    AI实时分析番茄该题材头部作品
    不是查数据库，是让AI去看、去总结
    """
    
    # 让AI分析Top20作品
    analysis_prompt = f"""
    请分析番茄小说平台上"{genre}"题材的Top20爆款作品。
    
    你需要总结：
    1. 这些作品的开局有什么共同点？（前3章）
    2. 金手指设计有什么规律？
    3. 主角人设有什么特征？
    4. 节奏安排有什么规律？（爽点间隔、升级节奏）
    5. 世界观设定有什么特点？
    6. 反派设计有什么套路？
    7. 情绪曲线怎么设计？
    8. 什么设定是这些作品都有的（必需要素）？
    9. 什么设定是这些作品都没有的（禁忌）？
    
    请给出具体的、可执行的总结，不要泛泛而谈。
    例如：
    - 不是"开局有冲突"，而是"开局主角必须被羞辱，然后获得系统"
    - 不是"有金手指"，而是"金手指必须是花钱返利，比例10倍"
    """
    
    # AI实时分析（可以结合爬虫获取作品数据）
    analysis_result = ai_client.generate(analysis_prompt, temperature=0.3)
    
    return analysis_result
```

**示例输出：**
```json
{
  "genre": "神豪文-花钱返利类",
  "analysis_summary": {
    "opening_pattern": "第1章：主角送外卖被宝马男撞，对方耍赖不给钱，还羞辱主角→主角获得花钱返利系统",
    "golden_finger_rules": {
      "type": "必须是花钱返利",
      "ratio": "10倍是标配",
      "activation": "必须完成任务激活",
      "limitation": "初期有金额上限，随等级解除"
    },
    "protagonist_traits": {
      "background": "必须是穷屌丝（外卖员/保安/摆地摊）",
      "personality": "隐忍，不主动惹事，但反击果断",
      "growth": "从穷→小有资产→地方富豪→全国富豪→全球首富"
    },
    "pacing_rules": {
      "first_system": "第1章必须出现",
      "first_money": "第3章必须花第一次钱",
      "first_face_slap": "第5章必须第一次打脸",
      "climax_interval": "每3-5章一个小爽点",
      "upgrade_interval": "每30章身份升级"
    },
    "worldview_traits": {
      "setting": "现代都市，钱能通神",
      "society": "阶层分明，有钱就是大爷",
      "required_scenes": ["4S店", "高档餐厅", "直播间", "豪宅"]
    },
    "antagonist_pattern": {
      "early": "势利眼（前女友/宝马男/站长）",
      "mid": "富二代",
      "late": "资本大佬"
    },
    "must_have": ["开局被羞辱", "获得系统", "花钱返利", "装逼打脸", "身份升级"],
    "must_not_have": ["主角开局不穷", "系统不返利", "主角圣母", "节奏慢"]
  }
}
```

---

### 步骤2：基于AI分析生成方案

```python
def generate_plan_by_ai_analysis(genre: str, user_choice: str) -> Dict:
    """
    基于AI分析的套路生成方案
    不是套用固定模板，是让AI基于分析结果创作
    """
    
    # 先让AI分析
    tropes = analyze_top_works(genre)
    
    # 让AI基于分析结果生成方案
    generation_prompt = f"""
    你是一位深谙番茄小说"{genre}"题材爆款套路的专家。
    
    基于你对Top20作品的分析：
    {json.dumps(tropes, ensure_ascii=False, indent=2)}
    
    请为用户生成一个符合上述套路的小说方案。
    
    用户选择的开局类型：{user_choice}
    
    你需要生成：
    1. 3个符合套路的标题（直接可用的）
    2. 详细的开局设计（严格遵循分析中的开局套路）
    3. 金手指设计（必须符合分析中的规则）
    4. 主角人设（必须符合分析中的人设特征）
    5. 前30章的大纲（必须符合分析中的节奏规律）
    
    重要：
    - 不要创新，严格遵循分析出的套路
    - 如果用户选择和套路冲突，优先遵循套路
    - 每个设计都要说明"为什么这样设计"（基于哪条套路）
    """
    
    plan = ai_client.generate(generation_prompt, temperature=0.5)
    
    return plan
```

---

### 步骤3：AI自我验证

```python
def ai_self_validate(product: Dict, genre: str) -> ValidationResult:
    """
    AI自我验证产物是否符合套路
    不是查数据库，是让AI自己检查
    """
    
    # 重新分析（或复用之前的分析）
    tropes = analyze_top_works(genre)
    
    # 让AI验证
    validation_prompt = f"""
    你是一位严格的番茄小说套路验证专家。
    
    该题材的爆款套路：
    {json.dumps(tropes, ensure_ascii=False, indent=2)}
    
    请验证以下产物是否符合上述套路：
    {json.dumps(product, ensure_ascii=False, indent=2)}
    
    请检查：
    1. 每个必须有的要素是否都有？
    2. 每个禁忌是否都避免了？
    3. 节奏是否符合规律？
    4. 如果有不符合的地方，请指出并给出修改建议
    
    输出格式：
    {
      "is_valid": true/false,
      "violations": ["问题1", "问题2"],
      "suggestions": ["建议1", "建议2"],
      "fixed_version": {修改后的产物}
    }
    """
    
    validation = ai_client.generate(validation_prompt, temperature=0.3)
    
    return validation
```

---

### 步骤4：AI对标优化

```python
def ai_benchmark_optimize(products: Dict, genre: str) -> OptimizationResult:
    """
    AI对标头部作品进行优化
    不是对比数据库，是让AI直接对比
    """
    
    optimization_prompt = f"""
    你是一位专业的番茄小说优化专家。
    
    请对比以下产物和"{genre}"题材头部作品的差距：
    
    当前产物：
    {json.dumps(products, ensure_ascii=False, indent=2)}
    
    请思考：
    1. 头部作品的开局是怎么写的？当前产物的开局差在哪？
    2. 头部作品的爽点密度如何？当前产物够密集吗？
    3. 头部作品的人设有什么亮点？当前产物的人设够讨喜吗？
    4. 如果这本书按当前设定发布，预计完读率多少？为什么？
    
    请给出具体的优化建议，不要泛泛而谈。
    """
    
    optimization = ai_client.generate(optimization_prompt, temperature=0.4)
    
    return optimization
```

---

## 三、完整流程（简化版）

```python
def generate_phase_one_market_driven(genre: str, user_preferences: Dict) -> Dict:
    """
    市场导向的第一阶段生成（简化版）
    全程用AI，不用数据库
    """
    
    # 第1步：AI分析头部作品套路
    print("📊 AI正在分析该题材头部作品...")
    tropes = analyze_top_works(genre)
    
    # 第2步：基于套路生成方案
    print("📝 基于分析结果生成方案...")
    plan = generate_plan_by_ai_analysis(genre, user_preferences)
    
    # 第3步：AI自我验证方案
    print("✅ 验证方案是否符合套路...")
    validation = ai_self_validate(plan, genre)
    if not validation["is_valid"]:
        print(f"⚠️ 发现问题：{validation['violations']}")
        plan = validation["fixed_version"]
    
    # 第4步：生成其他产物（都用同样的方法）
    print("🌍 生成世界观...")
    worldview = generate_by_ai_prompt("世界观", tropes, plan)
    
    print("👥 生成角色...")
    characters = generate_by_ai_prompt("角色", tropes, plan)
    
    print("📚 生成阶段计划...")
    stage_plans = generate_by_ai_prompt("阶段计划", tropes, plan)
    
    # 第5步：统一验证所有产物
    print("🔍 验证所有产物...")
    products = {
        "plan": plan,
        "worldview": worldview,
        "characters": characters,
        "stage_plans": stage_plans
    }
    
    for product_type, product in products.items():
        validation = ai_self_validate(product, genre)
        if not validation["is_valid"]:
            print(f"⚠️ {product_type}不符合套路，自动修复...")
            products[product_type] = validation["fixed_version"]
    
    # 第6步：对标优化
    print("🎯 对标头部作品优化...")
    optimization = ai_benchmark_optimize(products, genre)
    
    # 应用优化建议
    if optimization["suggestions"]:
        print("🔄 应用优化建议...")
        products = apply_ai_optimization(products, optimization)
    
    return {
        "products": products,
        "tropes_analysis": tropes,
        "optimization_report": optimization
    }
```

---

## 四、Prompt设计关键

### 关键原则

**1. 让AI先分析，再生成**
```
❌ 错误：直接让AI生成神豪文
✅ 正确：先让AI分析20本爆款神豪文，总结套路，再基于套路生成
```

**2. 强调"遵循套路"**
```
Prompt里必须强调：
- "不要创新"
- "严格遵循套路"
- "头部作者怎么写，你就怎么写"
```

**3. 让AI自我检查**
```
生成后必须让AI自己检查：
- "你生成的这个是否符合刚才总结的套路？"
- "和头部作品相比差在哪？"
```

---

## 五、示例Prompt

### 分析Prompt

```
你是一位专业的网络小说分析师。

请分析番茄小说"神豪文-花钱返利类"的Top20爆款作品。

你需要：
1. 列出这20部作品的名称
2. 总结它们的开局套路（具体到前3章的剧情）
3. 总结它们的金手指设计规律
4. 总结它们的主角人设特征
5. 总结它们的节奏安排（爽点间隔、升级节点）
6. 列出该题材的"必须要素"（缺了就不火）
7. 列出该题材的"禁忌"（有就死）

请给出详细的、可执行的分析报告。
```

### 生成Prompt

```
你是一位深谙番茄小说套路的资深编辑。

基于以下该题材的爆款套路分析：
[分析结果]

请为用户生成一个符合上述套路的小说方案。

用户选择：主角开局送外卖

要求：
1. 严格遵循分析中的套路，不要创新
2. 如果用户选择和套路冲突，优先遵循套路
3. 每个设计都要引用对应的套路依据

请生成：
- 3个标题（符合套路）
- 详细开局设计（第1-3章）
- 金手指设计
- 主角人设
- 前30章大纲
```

### 验证Prompt

```
你是一位严格的套路验证专家。

该题材的爆款套路：
[套路分析]

请验证以下产物是否符合套路：
[产物内容]

请检查：
1. 是否包含所有必须要素？
2. 是否避免了所有禁忌？
3. 如果有问题，请指出并给出修改建议

输出：
- 是否符合套路（是/否）
- 问题列表
- 修改建议
- 修改后的版本
```

---

## 六、优势

| 方面 | 数据库方案 | AI实时分析方案（当前） |
|------|-----------|---------------------|
| 维护成本 | 高（需要人工更新数据库） | 低（AI自动分析） |
| 时效性 | 差（数据可能过时） | 好（实时分析最新爆款） |
| 灵活性 | 差（固定套路） | 好（AI自动适应市场变化） |
| 准确度 | 中（依赖人工整理质量） | 高（AI直接看原文） |
| 实现难度 | 高（需要爬虫+数据库+人工） | 低（只需要Prompt工程） |

---

## 七、总结

**核心思想：**
- ❌ 不需要预建数据库
- ❌ 不需要人工整理套路
- ✅ 只需要让AI实时分析头部作品
- ✅ 基于分析结果生成
- ✅ AI自我验证

**全部工作就是设计好Prompt：**
1. 分析Prompt：让AI总结套路
2. 生成Prompt：让AI基于套路生成
3. 验证Prompt：让AI检查是否符合套路

**好处：**
- 简单，不需要数据库
- 灵活，自动适应市场变化
- 准确，AI直接看原文总结
