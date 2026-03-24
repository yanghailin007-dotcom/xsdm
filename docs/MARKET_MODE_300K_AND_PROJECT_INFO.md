# 市场导向模式：30万字生成 + 统一项目信息设计

## 一、市场导向模式生成30万字

### 核心差异（vs 自由创作模式）

| 环节 | 自由创作模式 | 市场导向模式 |
|------|-------------|-------------|
| 章节规划 | 基于创意自由发挥 | 严格遵循套路节奏公式 |
| 爽点设计 | AI自由安排 | 按套路固定间隔插入 |
| 冲突设计 | 自然发展 | 按套路模板执行 |
| 质量检查 | 通用标准 | 是否符合爆款套路 |

### 30万字生成流程

```python
def generate_300k_market_driven(novel_title: str, genre: str) -> Dict:
    """
    市场导向模式生成30万字（100-120章）
    """
    
    # 第0步：AI分析套路（一次性）
    tropes = ai_analyze_genre_tropes(genre)
    
    # 第1步：基于套路生成全书规划
    blueprint = generate_blueprint_by_tropes(tropes, target_words=300000)
    # blueprint包含每章的：字数、爽点类型、冲突强度、情绪曲线
    
    # 第2步：批量生成
    results = []
    for batch in range(1, 13):  # 12批，每批10章
        start = (batch-1) * 10 + 1
        end = batch * 10
        
        print(f"生成第{batch}/12批：第{start}-{end}章")
        
        batch_result = generate_batch_market_driven(
            novel_title=novel_title,
            start_chapter=start,
            end_chapter=end,
            blueprint=blueprint,
            tropes=tropes
        )
        
        results.append(batch_result)
        
        # 每批后保存检查点
        save_checkpoint(novel_title, batch, blueprint)
    
    return {
        "total_chapters": 120,
        "total_words": sum(r['total_words'] for r in results),
        "avg_quality": sum(r['avg_quality'] for r in results) / len(results),
        "blueprint": blueprint
    }
```

### 基于套路的章节规划（BluePrint）

```python
def generate_blueprint_by_tropes(tropes: Dict, target_words: int) -> Dict:
    """
    基于套路生成全书章节规划
    确保每章都符合爆款节奏
    """
    
    chapters = target_words // 2500  # 平均每章2500字
    
    blueprint = {
        "total_chapters": chapters,
        "total_words_target": target_words,
        "chapters": []
    }
    
    for ch_num in range(1, chapters + 1):
        chapter_plan = {
            "chapter_number": ch_num,
            "target_words": 2500,
            
            # 基于套路的节奏设计
            "climax_type": determine_climax_type(ch_num, tropes),
            # 例：第1章"转折", 第3章"小爽点", 第5章"爽点", 第10章"大爽点"
            
            "conflict_type": determine_conflict_type(ch_num, tropes),
            # 例：初期"势利眼羞辱", 中期"富二代打压", 后期"资本对抗"
            
            "emotional_curve": determine_emotion(ch_num, tropes),
            # 例：压抑→愤怒→反击→爽快
            
            "required_elements": get_required_elements(ch_num, tropes),
            # 例：第1章必须有["系统出现"], 第3章必须有["第一次花钱"]
            
            "face_slap_target": determine_face_slap_target(ch_num, tropes),
            # 例：第5章打脸"前女友", 第15章打脸"富二代"
            
            "power_level": calculate_power_level(ch_num, tropes),
            # 例：第1章"穷屌丝", 第30章"地方富豪"
            
            "expectation_hooks": get_expectation_hooks(ch_num, tropes),
            # 例：本章结尾埋下什么钩子，让读者想看下章
        }
        
        blueprint["chapters"].append(chapter_plan)
    
    return blueprint
```

### 单章生成（严格按套路）

```python
def generate_single_chapter_market_driven(
    chapter_num: int,
    novel_data: Dict,
    blueprint: Dict,
    tropes: Dict
) -> Dict:
    """
    市场导向模式生成单章
    严格按套路模板执行
    """
    
    plan = blueprint["chapters"][chapter_num - 1]
    
    # 构建Prompt（强调套路）
    prompt = f"""
    你是一位深谙番茄"{tropes['genre']}"爆款套路的资深写手。
    
    【必须遵循的套路】
    {json.dumps(tropes['core_formula'], ensure_ascii=False)}
    
    【本章规划】
    - 第{chapter_num}章
    - 爽点类型：{plan['climax_type']}
    - 冲突类型：{plan['conflict_type']}
    - 情绪曲线：{plan['emotional_curve']}
    - 必须包含：{', '.join(plan['required_elements'])}
    - 打脸对象：{plan['face_slap_target']}
    - 主角当前身份：{plan['power_level']}
    
    【前文摘要】（最近3章）
    {get_recent_summary(chapter_num, novel_data, count=3)}
    
    【世界观】
    {novel_data['core_worldview']['summary']}
    
    【角色设定】
    主角：{novel_data['character_design']['main_character']}
    当前反派：{get_current_antagonist(chapter_num, novel_data)}
    
    【写作要求】
    1. 严格按本章规划写，不要偏离
    2. 必须包含规划中的所有要素
    3. 结尾必须有钩子：{plan['expectation_hooks']}
    4. 字数2500字左右
    5. 语言直白，段落短小，适合手机阅读
    
    请直接创作本章内容。
    """
    
    content = ai_client.generate(prompt, temperature=0.7)
    
    # 套路符合性验证
    validation = validate_chapter_follows_tropes(content, plan, tropes)
    if not validation['is_valid']:
        print(f"⚠️ 第{chapter_num}章偏离套路，自动修正...")
        content = fix_chapter_by_tropes(content, validation['issues'], tropes)
    
    return {
        "chapter_number": chapter_num,
        "title": extract_title(content),
        "content": content,
        "word_count": len(content),
        "blueprint": plan,
        "validation": validation
    }
```

### 批量生成（带监控）

```python
def generate_batch_market_driven(
    novel_title: str,
    start_chapter: int,
    end_chapter: int,
    blueprint: Dict,
    tropes: Dict
) -> Dict:
    """
    批量生成一批章节（市场导向）
    """
    
    novel_data = load_novel_data(novel_title)
    generated = []
    failed = []
    
    for ch_num in range(start_chapter, end_chapter + 1):
        try:
            print(f"  生成第{ch_num}章...", end="")
            
            chapter = generate_single_chapter_market_driven(
                ch_num, novel_data, blueprint, tropes
            )
            
            # 保存
            save_chapter(novel_title, chapter)
            
            # 更新novel_data（用于后续章节）
            update_novel_data_progress(novel_data, chapter)
            
            generated.append(chapter)
            print(f" ✅ ({chapter['word_count']}字)")
            
        except Exception as e:
            print(f" ❌ ({str(e)})")
            failed.append({"chapter": ch_num, "error": str(e)})
            continue
    
    return {
        "batch_start": start_chapter,
        "batch_end": end_chapter,
        "generated": len(generated),
        "failed": len(failed),
        "total_words": sum(c['word_count'] for c in generated),
        "avg_quality": sum(c['validation']['score'] for c in generated) / len(generated) if generated else 0
    }
```

---

## 二、统一项目信息设计

### 核心原则

两种模式使用**完全相同**的项目信息结构，只是`generation_mode`字段区分：

```python
project_info = {
    # 基础信息（两种模式都有）
    "novel_title": "书名",
    "novel_synopsis": "简介",
    "genre": "神豪文",
    "sub_genre": "花钱返利类",
    "target_platform": "番茄小说",
    "generation_mode": "market_driven",  # 或 "creative"
    
    # 作者信息（上传用）
    "author_name": "作者名",
    "author_id": "作者ID",
    
    # 分类标签（上传用）
    "category_tags": {
        "main_category": "都市",           # 主分类（番茄要求）
        "sub_category": "都市生活",        # 子分类（番茄要求）
        "tags": ["神豪", "系统", "爽文"],   # 标签（番茄要求）
        "target_audience": "男频",         # 受众
        "content_rating": "全年龄"         # 分级
    },
    
    # 生成元数据
    "generation_metadata": {
        "generated_at": "2024-01-01",
        "total_chapters": 120,
        "total_words": 300000,
        "ai_model": "gpt-4",
        
        # 模式特定信息
        "mode_specific": {
            # 市场导向模式特有
            "tropes_analysis": {...},        # 套路分析结果
            "blueprint": {...},               # 章节规划
            "benchmark_works": [...],         # 对标作品
            
            # 或自由创作模式特有
            "creative_seed": {...},           # 原始创意
            "user_intentions": [...]          # 用户意图
        }
    },
    
    # 产物映射（第一阶段）
    "products_mapping": {
        "selected_plan": "selected_plan.json",
        "writing_style_guide": "writing_style_guide.json",
        "core_worldview": "core_worldview.json",
        "faction_system": "faction_system.json",
        "character_design": "character_design.json",
        "stage_writing_plans": "stage_writing_plans.json",
        "global_growth_plan": "global_growth_plan.json",
        "emotional_blueprint": "emotional_blueprint.json",
        "expectation_mapping": "expectation_mapping.json",
        "market_analysis": "market_analysis.json"
    },
    
    # 章节索引（第二阶段）
    "chapters_index": [
        {"chapter_number": 1, "title": "第1章标题", "word_count": 2500, "file": "chapter_001.txt"},
        {"chapter_number": 2, "title": "第2章标题", "word_count": 2600, "file": "chapter_002.txt"},
        # ...
    ],
    
    # 质量评估
    "quality_assessment": {
        "overall_score": 85,
        "commercial_score": 82,            # 市场导向模式特有
        "readiness": "ready",
        "generated_at": "2024-01-01"
    },
    
    # 上传相关信息（番茄要求）
    "upload_info": {
        "fanqie_book_id": None,            # 上传后填充
        "upload_status": "not_uploaded",   # not_uploaded / uploaded / published
        "upload_time": None,
        "published_chapters": 0,           # 已发布章节数
        "contract_status": "none"          # none / signed
    }
}
```

### 文件结构（两种模式统一）

```
小说项目/{书名}/
├── project_info.json              # 统一的项目信息（两种模式相同格式）
├── phase_one_products/            # 第一阶段产物
│   ├── selected_plan.json
│   ├── writing_style_guide.json
│   ├── core_worldview.json
│   ├── faction_system.json
│   ├── character_design.json
│   ├── stage_writing_plans.json
│   └── ...
├── chapters/                      # 章节文件（两种模式相同格式）
│   ├── chapter_001.txt
│   ├── chapter_002.txt
│   └── ...
├── chapters_index.json            # 章节索引
├── quality_assessment.json        # 质量评估
└── uploads/                       # 上传相关
    ├── fanqie_config.json         # 番茄上传配置
    └── upload_logs.json           # 上传记录
```

### 章节文件格式（统一）

```python
# chapter_001.txt 格式（两种模式完全一致）
chapter_data = {
    "metadata": {
        "chapter_number": 1,
        "title": "开局被甩，获得神豪系统",
        "word_count": 2580,
        "generated_at": "2024-01-01 10:00:00",
        "generation_mode": "market_driven",  # 标记生成模式
        
        # 质量评估（统一格式）
        "quality_score": 8.5,
        "assessment": {
            "coherence": 9,
            "climax": 8,
            "character": 9,
            "writing": 8
        },
        
        # 市场导向模式特有（自由创作模式为空或默认值）
        "market_driven_metadata": {
            "blueprint_climax_type": "转折",
            "required_elements": ["系统出现", "被羞辱"],
            "tropes_compliance": 0.95  # 套路符合度
        }
    },
    
    "content": """
    第1章 开局被甩，获得神豪系统
    
    夏天骑着电动车，在烈日下穿行...
    （正文内容）
    """
}
```

### 上传相关字段详解

```python
# 番茄上传需要的项目信息
upload_fields = {
    # 必填字段
    "novel_title": "书名（15字以内）",
    "novel_synopsis": "简介（50-500字）",
    "cover_image": "封面图路径",
    
    # 分类标签（番茄后台选择）
    "category_tags": {
        "main_category": "主分类",        # 都市/玄幻/科幻...
        "sub_category": "子分类",         # 都市生活/异术超能...
        "tags": ["标签1", "标签2"],        # 最多5个标签
    },
    
    # 作者信息
    "author_name": "作者笔名",
    "author_statement": "作者的话（可选）",
    
    # 连载设置
    "serial_settings": {
        "initial_chapters": 3,            # 首次发布章节数
        "daily_update": 2,                # 日更多少章
        "update_time": "18:00"            # 更新时间
    },
    
    # 版权信息
    "copyright": {
        "is_original": True,              # 是否原创
        "is_exclusive": True,             # 是否独家
        "has_agreement": False            # 是否签约
    }
}
```

---

## 三、两种模式的数据转换

如果用户想从自由创作转为市场导向（或反之）：

```python
def convert_project_mode(project_path: str, target_mode: str) -> bool:
    """
    转换项目生成模式
    只改metadata，不动章节内容
    """
    
    project_info = load_project_info(project_path)
    
    if target_mode == "market_driven"::
        # 补充市场导向特有字段
        project_info["generation_metadata"]["mode_specific"] = {
            "tropes_analysis": ai_analyze_from_existing(project_path),
            "blueprint": generate_blueprint_from_chapters(project_path),
            "conversion_notice": "从自由创作模式转换，部分字段为事后分析"
        }
    
    elif target_mode == "creative":
        # 补充自由创作特有字段
        project_info["generation_metadata"]["mode_specific"] = {
            "creative_seed": extract_creative_seed(project_path),
            "user_intentions": extract_user_intentions(project_path),
            "conversion_notice": "从市场导向模式转换"
        }
    
    project_info["generation_mode"] = target_mode
    save_project_info(project_path, project_info)
    
    return True
```

---

## 四、关键实现要点

### 1. 市场导向模式的核心

```python
# 每章生成前，检查是否符合套路
def pre_generate_check(chapter_num: int, blueprint: Dict, tropes: Dict):
    """
    生成前检查：确保本章符合套路要求
    """
    plan = blueprint["chapters"][chapter_num - 1]
    
    checks = {
        "climax_type": f"本章必须是{plan['climax_type']}",
        "required_elements": f"必须包含：{', '.join(plan['required_elements'])}",
        "emotion": f"情绪曲线：{plan['emotional_curve']}",
        "hook": f"结尾钩子：{plan['expectation_hooks']}"
    }
    
    return checks
```

### 2. 统一保存接口

```python
def save_chapter_unified(novel_title: str, chapter: Dict, mode: str):
    """
    统一章节保存接口
    两种模式调用相同的保存逻辑
    """
    
    # 统一数据结构
    chapter_data = {
        "metadata": {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "word_count": chapter["word_count"],
            "generation_mode": mode,
            "generated_at": datetime.now().isoformat(),
            "quality_score": chapter.get("quality_score", 0)
        },
        "content": chapter["content"]
    }
    
    # 模式特有字段（如果有）
    if mode == "market_driven" and "blueprint" in chapter:
        chapter_data["metadata"]["market_driven_metadata"] = {
            "blueprint_climax_type": chapter["blueprint"]["climax_type"],
            "tropes_compliance": chapter["validation"]["score"]
        }
    
    # 保存到统一位置
    save_path = f"小说项目/{novel_title}/chapters/chapter_{chapter['chapter_number']:03d}.json"
    save_json(save_path, chapter_data)
    
    # 更新章节索引
    update_chapters_index(novel_title, chapter_data["metadata"])
```

### 3. 上传接口统一

```python
def prepare_upload_data(novel_title: str) -> Dict:
    """
    准备上传数据（两种模式统一入口）
    """
    
    project_info = load_project_info(novel_title)
    
    # 提取上传所需字段（与生成模式无关）
    upload_data = {
        "title": project_info["novel_title"],
        "synopsis": project_info["novel_synopsis"],
        "category": project_info["category_tags"]["main_category"],
        "sub_category": project_info["category_tags"]["sub_category"],
        "tags": project_info["category_tags"]["tags"],
        "author_name": project_info["author_name"],
        "chapters": []
    }
    
    # 加载章节内容
    for ch_meta in project_info["chapters_index"]:
        chapter_data = load_chapter(novel_title, ch_meta["chapter_number"])
        upload_data["chapters"].append({
            "number": ch_meta["chapter_number"],
            "title": chapter_data["metadata"]["title"],
            "content": chapter_data["content"]
        })
    
    return upload_data
```

---

## 五、总结

### 30万字生成（市场导向）

1. **AI分析套路**（一次性）
2. **生成BluePrint**（全书章节规划）
3. **分批生成**（12批，每批10章）
4. **每章严格按套路**（climax_type, required_elements）
5. **套路符合性验证**（偏离则自动修正）

### 项目信息统一

| 层级 | 统一字段 | 模式特有字段 |
|------|---------|-------------|
| 基础信息 | title, synopsis, genre | generation_mode |
| 分类标签 | 完全相同（上传用） | - |
| 章节格式 | metadata + content | mode_specific（子字段） |
| 文件结构 | 完全相同 | - |

### 关键原则

1. **数据结构统一**：只有`generation_mode`和`mode_specific`不同
2. **上传接口统一**：不关心生成模式，只读取统一格式
3. **章节保存统一**：相同文件格式，相同索引方式
4. **可转换**：两种模式可以互相转换（保留原有内容）
