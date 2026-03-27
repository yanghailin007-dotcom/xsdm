# 阶段性复盘优化系统 (Stage Review & Optimization System)

## 核心理念

不再追求单章生成时100%完美，而是：
1. **快速生成**第一阶段（如30章）的初稿
2. **全局分析**识别所有问题（连续性问题、角色跳变、设定矛盾）
3. **多轮优化**批量修复所有问题
4. **更新设定**同步修正所有资料文件
5. **迭代逼近**同题材爆款标准

---

## 触发时机

| 阶段 | 章节范围 | 触发条件 | 优化重点 |
|------|---------|---------|---------|
| **开篇验证** | 1-3章 | 黄金三章完成后 | 开篇钩子、角色引入、世界观建立 |
| **第一幕复盘** | 1-30章 | 完成第一幕（ setup完成） | 主线铺垫、配角塑造、情绪曲线 |
| **中点复盘** | 1-60章 | 剧情中点（转折完成） | 剧情连贯性、反派层级、伏笔回收 |
| **高潮前复盘** | 1-100章 | 高潮铺垫完成 | 所有伏笔回收、角色成长线、世界观完整 |
| **完本复盘** | 1-200章 | 全书完成 | 整体节奏、爽点分布、结局满意度 |

---

## 评价维度（AI分析 prompt）

### 维度1：剧情连续性 (Plot Continuity)

```markdown
## 剧情连续性分析

请检查以下问题：

### 1.1 时间线一致性
- [ ] 章节间的时间跳跃是否有明确标注
- [ ] 倒计时/时间限制是否准确推进（如"72小时"是否在各章正确递减）
- [ ] 事件顺序是否符合因果逻辑

### 1.2 场景连贯性
- [ ] 章节结尾与下章开头是否在同一地点/状态
- [ ] 场景切换是否有过渡
- [ ] 战斗场景的胜负结果是否延续正确

### 1.3 剧情线索追踪
- [ ] 每条 subplot 是否有始有终
- [ ] 章尾悬念是否在3章内有回应
- [ ] 重要道具/信息是否被遗忘
```

### 维度2：角色一致性 (Character Consistency)

```markdown
## 角色一致性分析

### 2.1 主角一致性
检查主角在以下方面是否一致：
- [ ] **姓名**：是否出现错别字或别名混乱
- [ ] **能力**：已解锁的能力是否正确使用，未解锁的是否被提前使用
- [ ] **性格**：核心性格标签是否贯彻（如"护短"是否始终如一）
- [ ] **成长线**：实力/地位的成长是否符合逻辑递进

### 2.2 配角一致性
- [ ] 重要配角的立场是否稳定（无无理由跳反）
- [ ] 配角的能力等级是否稳定（无突然变强/变弱）
- [ ] 配角与主角的关系变化是否有铺垫

### 2.3 反派层级合理性
- [ ] 反派登场是否符合"由弱到强"的层级
- [ ] 上级反派的登场是否有下级反派的铺垫
- [ ] 已击败的反派的后续处理（死亡/监禁/逃跑）是否明确
```

### 维度3：世界设定一致性 (World Building Consistency)

```markdown
## 世界设定一致性分析

### 3.1 力量体系一致性
- [ ] 等级划分是否统一（如SS级始终强于S级）
- [ ] 升级条件是否前后一致
- [ ] 特殊能力/系统的规则是否稳定

### 3.2 组织势力一致性
- [ ] 各势力的层级结构是否清晰且稳定
- [ ] 势力间的关系（敌对/同盟/中立）是否有变化记录
- [ ] 势力实力评估是否前后一致

### 3.3 道具/资源设定
- [ ] 重要道具的功能描述是否一致
- [ ] 资源获取难度是否稳定
- [ ] 货币/数值系统是否统一
```

### 维度4：爆款标准对标 (Bestseller Benchmark)

```markdown
## 番茄爆款标准对标

### 4.1 开篇质量（1-3章）
评分标准（每项0-10分）：
- [ ] 第1章300字内是否有强冲突/钩子
- [ ] 系统/金手指的引入是否清晰有趣
- [ ] 主角的困境是否让读者共情
- [ ] 章尾悬念是否强烈

### 4.2 爽点密度（全文）
统计：
- [ ] 平均每章爽点数量（目标：≥1.5个/章）
- [ ] 爽点类型分布（装逼/收获/打脸/震惊）
- [ ] 压抑→爆发的节奏是否符合"3章一小爽，10章一大爽"

### 4.3 情绪曲线
- [ ] 情绪转折次数（目标：每章≥3次）
- [ ] 高潮章节分布是否均匀
- [ ] 压抑章节是否有明确的释放预期

### 4.4 节奏控制
- [ ] 水字数检测（无意义对话/环境描写占比<10%）
- [ ] 信息密度（每章推进的剧情点≥2个）
- [ ] 战斗/日常比例（建议 6:4 或 7:3）
```

---

## 优化流程

### Stage 1: 问题识别（第1轮AI调用）

```python
def stage1_identify_issues(chapters: List[Dict], stage: str) -> Dict:
    """
    识别所有问题
    """
    prompt = f"""
    你是一名专业的小说编辑，请对以下{stage}章节的初稿进行全面分析。
    
    章节内容：
    {format_chapters_for_analysis(chapters)}
    
    请按以下维度输出问题报告：
    
    ## 1. 剧情连续性问题
    列出所有时间/场景/线索断裂问题：
    - 第X章结尾 vs 第X+1章开头的矛盾点
    - 未回收的悬念（超过3章未提）
    - 逻辑矛盾
    
    ## 2. 角色一致性问题
    - 主角能力/性格的异常波动
    - 配角立场/能力的异常变化  
    - 反派层级的跳变（无铺垫升级）
    
    ## 3. 设定一致性问题
    - 力量体系的前后矛盾
    - 道具/能力的设定冲突
    - 组织势力的实力评估变化
    
    ## 4. 爆款标准差距
    - 爽点不足的章节列表
    - 情绪曲线平淡的章节
    - 节奏拖沓的章节
    
    输出格式：JSON
    {{
        "plot_issues": [...],
        "character_issues": [...], 
        "world_issues": [...],
        "bestseller_gaps": [...],
        "priority": "high/medium/low"
    }}
    """
    return call_ai(prompt)
```

### Stage 2: 批量修复规划（第2轮AI调用）

```python
def stage2_plan_fixes(issues: Dict, chapters: List[Dict]) -> List[FixPlan]:
    """
    规划修复方案（合并同类问题，批量处理）
    """
    prompt = f"""
    基于以下问题列表，制定批量修复方案：
    
    问题列表：
    {json.dumps(issues, ensure_ascii=False)}
    
    请输出修复计划：
    1. **全局修复**（影响多章的问题）
       - 设定统一化方案
       - 角色能力标准化
    
    2. **批量修复**（同类问题合并）
       - 章节X-Y：补充反派铺垫
       - 章节A-B：强化爽点
    
    3. **单章修复**（特殊问题）
       - 第N章：重写结尾以承接下文
    
    输出修复顺序（依赖关系）：
    先修复设定 → 再修复角色 → 最后修复剧情
    """
    return call_ai(prompt)
```

### Stage 3: 执行修复（多轮并行调用）

```python
def stage3_execute_fixes(fix_plans: List[FixPlan], chapters: List[Dict]) -> List[Dict]:
    """
    执行修复（可以并行处理无关的章节）
    """
    fixed_chapters = []
    
    for plan in fix_plans:
        if plan.type == "global":
            # 全局修复：更新设定文档
            update_world_state(plan.changes)
            
        elif plan.type == "batch":
            # 批量修复：相似章节一起处理
            batch_chapters = [chapters[i] for i in plan.chapter_indices]
            fixed = fix_batch_chapters(batch_chapters, plan.instructions)
            fixed_chapters.extend(fixed)
            
        elif plan.type == "single":
            # 单章修复
            chapter = chapters[plan.chapter_index]
            fixed = fix_single_chapter(chapter, plan.instructions)
            fixed_chapters.append(fixed)
    
    return fixed_chapters
```

### Stage 4: 验证修复（第3轮AI调用）

```python
def stage4_verify_fixes(original_issues: Dict, fixed_chapters: List[Dict]) -> bool:
    """
    验证修复效果
    """
    prompt = f"""
    对比修复前后的章节，验证以下问题是否已解决：
    
    原问题：
    {json.dumps(original_issues, ensure_ascii=False)}
    
    修复后章节：
    {format_chapters_for_analysis(fixed_chapters)}
    
    请输出：
    - 已解决的问题（打勾）
    - 仍存在的问题（列出）
    - 修复引入的新问题（如有）
    
    如果仍有问题，返回需要第2轮修复的清单。
    """
    result = call_ai(prompt)
    return result.all_resolved
```

### Stage 5: 同步更新设定文件

```python
def stage5_sync_settings(fixed_chapters: List[Dict], project_path: str):
    """
    同步更新所有设定文件
    """
    # 1. 更新 .world_state.json
    world_state = extract_world_state_from_chapters(fixed_chapters)
    save_json(f"{project_path}/.world_state.json", world_state)
    
    # 2. 更新 character_state.json
    character_state = extract_character_states(fixed_chapters)
    save_json(f"{project_path}/.character_state.json", character_state)
    
    # 3. 更新 plot_timeline.json（剧情时间线）
    timeline = extract_timeline(fixed_chapters)
    save_json(f"{project_path}/.plot_timeline.json", timeline)
    
    # 4. 更新 hooks_resolved.json（已解决的钩子）
    hooks = extract_resolved_hooks(fixed_chapters)
    save_json(f"{project_path}/.hooks_resolved.json", hooks)
    
    # 5. 生成优化报告
    report = generate_optimization_report(fixed_chapters)
    save_markdown(f"{project_path}/optimization_report_stage_X.md", report)
```

---

## 多轮迭代机制

```
第1轮生成 → 初稿（30章）
    ↓
第1轮优化 → 修复主要问题（连续性问题、角色跳变）
    ↓
第2轮优化 → 提升爆款质量（爽点强化、情绪优化）
    ↓
第3轮优化 → 细节润色（文笔、节奏微调）
    ↓
进入下一阶段（31-60章）
```

**停止条件**：
- 问题数量 < 阈值（如少于5个低级问题）
- 爆款评分 > 阈值（如>8.5分）
- 达到最大迭代次数（如3轮）

---

## 输出产物

每次复盘优化后生成：

1. **optimization_report_stage_X.md** - 优化报告
   - 发现的问题清单
   - 修复措施
   - 质量评分对比

2. **.world_state.json** - 更新后的世界状态
3. **.character_state.json** - 更新后的角色状态
4. **.plot_timeline.json** - 剧情时间线
5. **.hooks_resolved.json** - 已解决/待解决的钩子

---

## 与现有系统集成

```python
# 在 batch_chapter_generator.py 中添加触发点

def generate_batch(self, novel_title, start_chapter, end_chapter, ...):
    # 正常生成流程
    chapters = self._generate_chapters(...)
    
    # 检查是否达到阶段节点
    if end_chapter in [30, 60, 100, 150, 200]:
        logger.info(f"触发阶段性复盘：第{start_chapter}-{end_chapter}章")
        
        # 调用复盘优化系统
        from .stage_review_optimizer import StageReviewOptimizer
        optimizer = StageReviewOptimizer(self.project_path)
        
        optimized_chapters = optimizer.optimize_stage(
            chapters=chapters,
            stage_end=end_chapter,
            max_rounds=3
        )
        
        # 使用优化后的章节
        chapters = optimized_chapters
    
    return chapters
```

---

## 总结

这个方案的核心优势：

1. **化整为零**：不再追求单章完美，允许初稿有缺陷
2. **全局视角**：AI能看到全文，发现人眼难察的连续性问题
3. **批量修复**：同类问题一次性解决，效率更高
4. **迭代逼近**：多轮优化逐步逼近爆款标准
5. **资料同步**：所有设定文件自动更新，保持一致
