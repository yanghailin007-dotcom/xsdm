# 批量章节生成方案（30万字+）

## 目标
连续生成100-150章（30万-50万字），全程自动，人工只需监控

---

## 核心问题

### 1. 上下文管理（最核心）

生成到第100章时，AI需要知道：
- 前99章发生了什么？
- 主角现在什么实力？
- 开了哪些伏笔？
- 世界观有什么变化？

**解决方案：动态上下文压缩**

```python
def build_chapter_context(chapter_number: int, novel_data: Dict) -> str:
    """
    构建章节生成所需的上下文
    不是把所有章节都丢给AI，而是智能压缩
    """
    
    context_parts = []
    
    # 1. 基础设定（始终保留）
    context_parts.append(f"""
    小说基础设定：
    - 标题：{novel_data['novel_title']}
    - 世界观：{novel_data['core_worldview']['summary']}
    - 主角：{novel_data['character_design']['main_character']['name']}
    - 当前实力：{get_current_power_level(chapter_number, novel_data)}
    """)
    
    # 2. 近期剧情（最近5章详细摘要）
    recent_chapters = get_recent_chapters(chapter_number, count=5)
    context_parts.append("最近5章剧情：")
    for ch in recent_chapters:
        context_parts.append(f"- 第{ch['number']}章：{ch['summary']}")
    
    # 3. 关键伏笔状态（只保留未回收的）
    active_foreshadowing = get_active_foreshadowing(novel_data, chapter_number)
    if active_foreshadowing:
        context_parts.append("待回收伏笔：")
        for fs in active_foreshadowing:
            context_parts.append(f"- {fs['description']}（预计第{fs['expected_chapter']}章回收）")
    
    # 4. 长期剧情线（每10章更新一次）
    if chapter_number % 10 == 1:
        long_term_arc = get_long_term_arc(novel_data, chapter_number)
        context_parts.append(f"长期剧情线：{long_term_arc}")
    
    # 5. 第1章永远保留（基础设定）
    if chapter_number > 1:
        chapter1_summary = get_chapter_summary(1, novel_data)
        context_parts.append(f"第1章开局：{chapter1_summary}")
    
    return "\n".join(context_parts)
```

### 2. 批量生成流水线

```python
class BatchChapterGenerator:
    """批量章节生成器"""
    
    def __init__(self, novel_data: Dict, config: Dict):
        self.novel_data = novel_data
        self.config = config
        self.generated_chapters = []
        self.failed_chapters = []
        
    def generate_batch(self, start_chapter: int, end_chapter: int) -> Dict:
        """
        批量生成章节
        支持断点续传、失败重试
        """
        
        results = {
            "generated": [],
            "failed": [],
            "total_words": 0,
            "avg_quality_score": 0
        }
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            print(f"\n{'='*60}")
            print(f"正在生成第{chapter_num}章...")
            print(f"{'='*60}")
            
            try:
                # 1. 构建上下文
                context = build_chapter_context(chapter_num, self.novel_data)
                
                # 2. 获取该章写作计划
                chapter_plan = self._get_chapter_plan(chapter_num)
                
                # 3. 生成章节
                chapter_content = self._generate_single_chapter(
                    chapter_num=chapter_num,
                    context=context,
                    plan=chapter_plan
                )
                
                # 4. 质量评估
                quality_score = self._assess_chapter_quality(
                    chapter_num, 
                    chapter_content
                )
                
                # 5. 如果质量不达标，自动优化
                if quality_score < self.config['min_quality_score']:
                    print(f"⚠️ 质量评分{quality_score}偏低，自动优化...")
                    chapter_content = self._optimize_chapter(
                        chapter_num,
                        chapter_content,
                        quality_score
                    )
                    quality_score = self._assess_chapter_quality(
                        chapter_num, 
                        chapter_content
                    )
                
                # 6. 保存
                self._save_chapter(chapter_num, chapter_content, quality_score)
                
                # 7. 更新小说数据（用于后续章节）
                self._update_novel_data(chapter_num, chapter_content)
                
                results["generated"].append({
                    "chapter": chapter_num,
                    "word_count": chapter_content['word_count'],
                    "quality_score": quality_score
                })
                results["total_words"] += chapter_content['word_count']
                
                print(f"✅ 第{chapter_num}章生成完成")
                print(f"   字数：{chapter_content['word_count']}")
                print(f"   质量：{quality_score}/10")
                
            except Exception as e:
                print(f"❌ 第{chapter_num}章生成失败: {e}")
                results["failed"].append({
                    "chapter": chapter_num,
                    "error": str(e)
                })
                self.failed_chapters.append(chapter_num)
                
                # 记录失败，继续下一章
                continue
        
        # 计算平均质量
        if results["generated"]:
            results["avg_quality_score"] = sum(
                c["quality_score"] for c in results["generated"]
            ) / len(results["generated"])
        
        return results
    
    def resume_generation(self) -> Dict:
        """
        断点续传
        从上次失败的地方继续
        """
        last_generated = self._get_last_generated_chapter()
        start = last_generated + 1
        end = self.config['total_chapters']
        
        print(f"🔄 断点续传：从第{start}章开始")
        return self.generate_batch(start, end)
```

### 3. 质量保障机制

```python
def ensure_chapter_quality(chapter_num: int, content: str, context: str) -> str:
    """
    确保章节质量的完整流程
    """
    
    # 1. 基础质量检查
    issues = []
    
    # 字数检查
    word_count = len(content)
    if word_count < 2000:
        issues.append(f"字数不足：{word_count}字，需要>2000字")
    
    # 2. AI质量评估
    assessment_prompt = f"""
    请评估以下章节的质量（1-10分）：
    
    章节上下文：
    {context}
    
    章节内容：
    {content[:3000]}...
    
    评估维度：
    - 剧情连贯性（是否承接上文）
    - 爽点密度（是否有足够爽点）
    - 角色一致性（角色行为是否符合人设）
    - 文笔质量（是否流畅易读）
    - 期待感（结尾是否有钩子）
    
    输出格式：
    {{
        "overall_score": 8.5,
        "dimension_scores": {{
            "coherence": 9,
            "climax": 8,
            "character": 9,
            "writing": 8,
            "hook": 8
        }},
        "issues": ["问题1", "问题2"],
        "suggestions": ["建议1", "建议2"]
    }}
    """
    
    assessment = ai_client.generate(assessment_prompt, temperature=0.3)
    
    # 3. 如果评分低，自动优化
    if assessment["overall_score"] < 7:
        print(f"⚠️ 质量偏低({assessment['overall_score']})，自动优化...")
        content = optimize_chapter(content, assessment["suggestions"])
    
    return content
```

### 4. 智能分批次生成

30万字不能一次生成，需要分批：

```python
def generate_300k_words(novel_data: Dict) -> None:
    """
    生成30万字（约100-120章）
    """
    
    batch_generator = BatchChapterGenerator(novel_data, config={
        "total_chapters": 120,
        "batch_size": 10,  # 每批10章
        "min_quality_score": 7.0,
        "auto_optimize": True
    })
    
    # 分批生成，每批之间有检查点
    total_batches = 12  # 120章 / 10章每批
    
    for batch_num in range(1, total_batches + 1):
        start_chapter = (batch_num - 1) * 10 + 1
        end_chapter = batch_num * 10
        
        print(f"\n{'='*60}")
        print(f"开始生成第{batch_num}/{total_batches}批")
        print(f"章节：{start_chapter}-{end_chapter}")
        print(f"{'='*60}")
        
        results = batch_generator.generate_batch(start_chapter, end_chapter)
        
        # 批次检查
        if results["avg_quality_score"] < 6.5:
            print("⚠️ 本批质量偏低，暂停生成，请检查")
            input("按回车继续，或Ctrl+C退出...")
        
        # 保存检查点
        save_checkpoint(batch_num, novel_data)
        
        print(f"\n✅ 第{batch_num}批完成")
        print(f"   生成：{len(results['generated'])}章")
        print(f"   失败：{len(results['failed'])}章")
        print(f"   平均质量：{results['avg_quality_score']:.1f}")
        print(f"   累计字数：{results['total_words']}")
```

### 5. 监控面板

```python
class GenerationMonitor:
    """生成监控面板"""
    
    def display_progress(self, current: int, total: int, stats: Dict):
        """显示生成进度"""
        
        progress = current / total * 100
        
        print(f"""
        ╔════════════════════════════════════════════════╗
        ║           批量章节生成进度                      ║
        ╠════════════════════════════════════════════════╣
        ║  总进度: {current}/{total} ({progress:.1f}%)            ║
        ║  预计剩余时间: {stats['estimated_remaining']}              ║
        ╠════════════════════════════════════════════════╣
        ║  本批统计:                                     ║
        ║    - 已生成: {stats['generated']}章                    ║
        ║    - 失败: {stats['failed']}章                      ║
        ║    - 平均质量: {stats['avg_quality']:.1f}/10             ║
        ║    - 总字数: {stats['total_words']:,}                ║
        ╠════════════════════════════════════════════════╣
        ║  最近5章质量: {', '.join([str(s) for s in stats['recent_scores']])}    ║
        ╚════════════════════════════════════════════════╝
        """)
```

---

## 执行建议

### 对于30万字+作品

1. **分阶段生成**
   - 第1阶段：1-30章（测试市场反应）
   - 第2阶段：31-60章
   - 第3阶段：61-100章
   - 第4阶段：101-150章

2. **每阶段后人工审核**
   - 不是审核文字，是审核**套路是否走偏**
   - 检查：节奏、爽点、人设是否还符合套路

3. **数据反馈调优**
   - 如果前30章数据好，继续按原套路生成
   - 如果数据差，暂停，用AI分析原因，调整后再继续

---

## 技术要点

1. **上下文压缩**：只给AI最必要的信息
2. **断点续传**：随时可暂停、恢复
3. **质量监控**：自动检查，低质量自动优化
4. **分批生成**：每批后有检查点
5. **失败重试**：单章失败不影响整体
