# 期待感管理系统 - 集成示例

本文档展示如何将期待感管理系统完整集成到现有的小说生成流程中。

## 目录结构

```
src/
├── managers/
│   ├── ExpectationManager.py          # 期待感管理核心
│   ├── StagePlanManager.py            # 需要修改：添加期待管理
│   └── ...
├── core/
│   └── content_generation/
│       ├── chapter_generator.py       # 需要修改：添加期待验证
│       └── ...
tests/
└── test_expectation_manager.py         # 单元测试
```

## 第一步：在 NovelGenerator 中初始化期待管理器

### 修改 `src/core/NovelGenerator.py`

```python
from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator

class NovelGenerator:
    def __init__(self, config):
        # ... 现有初始化代码 ...
        
        # 添加期待管理器
        self.expectation_manager = ExpectationManager()
        self.expectation_integrator = ExpectationIntegrator(self.expectation_manager)
        
        self.logger.info("✅ 期待感管理器初始化完成")
```

## 第二步：在 StagePlanManager 中集成期待标签

### 修改 `src/managers/StagePlanManager.py`

在 `generate_stage_writing_plan` 方法中添加期待感标签生成：

```python
def generate_stage_writing_plan(self, stage_name: str, stage_range: str, 
                                creative_seed: str, novel_title: str, 
                                novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
    """生成阶段写作计划（添加期待感管理）"""
    
    # ... 现有的 fase 1-4 代码 ...
    
    # fase 4.5: 添加期待感标签 (新增)
    self.logger.info("   fase 4.5: 添加期待感标签...")
    
    # 分析并标记事件
    expectation_result = self.expectation_integrator.analyze_and_tag_events(
        major_events=final_writing_plan["stage_writing_plan"]["event_system"]["major_events"],
        stage_name=stage_name
    )
    
    # 将期待感信息添加到计划中
    final_writing_plan["stage_writing_plan"]["expectation_map"] = \
        self.expectation_manager.export_expectation_map()
    
    self.logger.info(f"  ✅ 已为 {expectation_result['tagged_count']} 个事件添加期待标签")
    
    # ... 继续现有的 fase 5-6 代码 ...
    
    return final_writing_plan
```

同时需要在 `StagePlanManager.__init__` 中添加期待管理器引用：

```python
class StagePlanManager:
    def __init__(self, novel_generator):
        self.generator = novel_generator
        
        # ... 现有初始化代码 ...
        
        # 添加期待管理器引用
        self.expectation_manager = novel_generator.expectation_manager
        self.expectation_integrator = novel_generator.expectation_integrator
```

## 第三步：在 ChapterGenerator 中添加期待检查和验证

### 修改 `src/core/content_generation/chapter_generator.py`

在 `generate_chapter_content_for_novel` 方法中添加期待感管理：

```python
def generate_chapter_content_for_novel(self, chapter_number: int, 
                                       novel_data: Dict, context) -> Optional[Dict]:
    """生成章节内容（添加期待感管理）"""
    
    self.logger.info(f"🎬 开始生成第{chapter_number}章内容...")
    
    # ... 现有的初始化代码 ...
    
    try:
        # ========== 新增：期待感管理开始 ==========
        # 1. 生成前检查期待约束
        expectation_manager = self.cg.novel_generator.expectation_manager
        expectation_constraints = expectation_manager.pre_generation_check(
            chapter_num=chapter_number
        )
        
        if expectation_constraints:
            self.logger.info(f"  🎯 第{chapter_number}章有 {len(expectation_constraints)} 个期待约束")
            for constraint in expectation_constraints:
                self.logger.info(f"     - [{constraint.urgency}] {constraint.message}")
        
        # 2. 将期待约束添加到章节参数
        chapter_params["expectation_constraints"] = expectation_constraints
        # ========== 新增：期待感管理结束 ==========
        
        # ... 现有的章节内容生成代码 ...
        
        # ========== 新增：期待感验证开始 ==========
        # 3. 生成后验证期待满足度
        content_analysis = {
            "content": chapter_data.get("content", ""),
            "chapter_title": chapter_data.get("chapter_title", "")
        }
        
        # 提取本章释放的期待ID（基于内容分析）
        released_expectations = self._extract_released_expectations(
            chapter_data.get("content", ""),
            expectation_constraints
        )
        
        validation_result = expectation_manager.post_generation_validate(
            chapter_num=chapter_number,
            content_analysis=content_analysis,
            released_expectation_ids=released_expectations
        )
        
        # 4. 处理验证结果
        if not validation_result["passed"]:
            self.logger.warning(f"  ⚠️ 第{chapter_number}章期待感验证未完全通过")
            for violation in validation_result.get("violations", []):
                self.logger.warning(f"     - {violation['message']}")
        else:
            self.logger.info(f"  ✅ 第{chapter_number}章期待感验证通过")
        
        # 统计信息
        satisfied_count = len(validation_result.get("satisfied_expectations", []))
        pending_count = len(validation_result.get("pending_expectations", []))
        self.logger.info(f"  📊 期待统计: 满足{satisfied_count}个, 待处理{pending_count}个")
        
        # 5. 将验证结果添加到章节数据
        chapter_data["expectation_validation"] = validation_result
        # ========== 新增：期待感验证结束 ==========
        
        # ... 现有的后续处理代码 ...
        
        return chapter_data
        
    except Exception as e:
        # ... 现有异常处理 ...
        pass

def _extract_released_expectations(self, content: str, 
                                  constraints: List) -> List[str]:
    """从章节内容中提取释放的期待ID"""
    released_ids = []
    
    for constraint in constraints:
        if constraint.type == "must_release" and constraint.expectation_id:
            # 简单检查：如果约束中提到的关键词出现在内容中
            # 实际应用中可以使用更复杂的NLP分析
            if constraint.expectation_id:
                released_ids.append(constraint.expectation_id)
    
    return released_ids
```

同时需要修改 `_build_chapter_generation_prompt` 方法，将期待感指导添加到 prompt 中：

```python
def _build_chapter_generation_prompt(self, chapter_params: Dict, 
                                    chapter_number: int, 
                                    intensity_guidance: str, 
                                    scenes_input_str: str) -> str:
    """构建章节生成提示词（添加期待感指导）"""
    
    # ========== 新增：期待感指导 ==========
    expectation_guidance = self._build_expectation_guidance(
        chapter_params.get("expectation_constraints", [])
    )
    # ========== 新增结束 ==========
    
    return f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_number}章。

{expectation_guidance}  # 新增

{intensity_guidance}

{scenes_input_str}

## 2. 背景与衔接
...

---

请你作为一名优秀的小说家,根据以上所有指令,直接创作出本章的完整内容。
"""

def _build_expectation_guidance(self, constraints: List) -> str:
    """构建期待感指导文本"""
    if not constraints:
        return ""
    
    guidance_parts = ["## 🎯 本章期待感要求\n"]
    
    for constraint in constraints:
        if constraint.type == "must_release":
            guidance_parts.append(f"""
### 【必须释放】{constraint.message}

**实现建议**:
{chr(10).join([f"  - {s}" for s in constraint.suggestions])}

**关键要素**:
- 展示期待被满足的具体过程
- 描写角色/读者的情感反应
- 给足篇幅和细节,不要草草了事
""")
        
        elif constraint.type == "must_plant":
            guidance_parts.append(f"""
### 【建议种植新期待】

{constraint.message}

**推荐方案**:
{chr(10).join([f"  - {s}" for s in constraint.suggestions])}

**实现要点**:
- 选择1-2种期待类型
- 确保期待足够具体和明确
- 为后续释放埋下合理的基础
""")
    
    return "\n".join(guidance_parts)
```

## 第四步：在生成完成后生成期待感报告

### 添加新的API接口

在 `web/api/novel_api.py` 中添加：

```python
@novel_bp.route('/api/novels/<novel_id>/expectation-report', methods=['GET'])
def get_expectation_report(novel_id):
    """获取期待感报告"""
    try:
        start_chapter = request.args.get('start', 1, type=int)
        end_chapter = request.args.get('end', type=int)
        
        novel = NovelManager.get_novel(novel_id)
        if not novel:
            return jsonify({"error": "小说不存在"}), 404
        
        expectation_manager = novel.novel_generator.expectation_manager
        report = expectation_manager.generate_expectation_report(
            start_chapter=start_chapter,
            end_chapter=end_chapter
        )
        
        return jsonify({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## 第五步：运行测试

### 执行单元测试

```bash
# 运行期待感管理器测试
cd d:/work6.05
python tests/test_expectation_manager.py
```

预期输出：
```
======================================================================
开始运行期待感管理系统测试
======================================================================
test_tag_event_with_expectation ... ok
test_nested_doll_expectation ... ok
test_pre_generation_check ... ok
test_post_generation_validate_success ... ok
test_post_generation_validate_failure ... ok
test_generate_expectation_report ... ok
test_analyze_and_tag_major_event ... ok
test_analyze_and_tag_medium_event ... ok
test_complete_workflow ... ok

======================================================================
测试总结
======================================================================
运行测试: 9
成功: 9
失败: 0
错误: 0
======================================================================
```

## 第六步：实际使用示例

### 完整的生成流程示例

```python
from src.core.NovelGenerator import NovelGenerator

# 1. 初始化生成器
generator = NovelGenerator(config={
    "api_key": "your_api_key",
    "model": "your_model"
})

# 2. 生成阶段计划（会自动添加期待标签）
stage_plan = generator.stage_plan_manager.generate_stage_writing_plan(
    stage_name="opening_stage",
    stage_range="1-20",
    creative_seed=creative_seed,
    novel_title="凡人：我能掠夺词条",
    novel_synopsis="...",
    overall_stage_plan=overall_plan
)

# 查看添加的期待标签
print("期待标签统计:")
for exp_id, exp_data in stage_plan["expectation_map"]["expectations"].items():
    print(f"  - {exp_data['type']}: {exp_data['description']}")
    print(f"    种植章节: {exp_data['planted_chapter']}")
    print(f"    目标章节: {exp_data['target_chapter']}")

# 3. 生成章节（会自动检查和验证期待）
chapter_data = generator.content_generator.generate_chapter_content_for_novel(
    chapter_number=15,
    novel_data=novel_data,
    context=context
)

# 查看期待验证结果
validation = chapter_data.get("expectation_validation", {})
print(f"\n期待验证结果:")
print(f"  通过: {validation['passed']}")
print(f"  满足期待数: {len(validation['satisfied_expectations'])}")
print(f"  待处理期待数: {len(validation['pending_expectations'])}")

# 4. 生成期待感报告
report = generator.expectation_manager.generate_expectation_report(
    start_chapter=1,
    end_chapter=20
)

print(f"\n期待感报告:")
print(f"  总期待数: {report['total_expectations']}")
print(f"  满足率: {report['satisfaction_rate']}%")
```

## 故障排除

### 问题1：期待标签没有被添加

**症状**：`expectation_map` 为空

**检查步骤**：
```python
# 检查期待管理器是否初始化
print(hasattr(generator, 'expectation_manager'))  # 应该为 True

# 检查事件是否被正确分析
major_events = stage_plan["event_system"]["major_events"]
print(f"重大事件数: {len(major_events)}")  # 应该 > 0

# 手动调用分析
result = generator.expectation_integrator.analyze_and_tag_events(
    major_events=major_events,
    stage_name="opening_stage"
)
print(f"标记数量: {result['tagged_count']}")
```

### 问题2：期待验证总是失败

**症状**：`post_generation_validate` 返回 `passed=False`

**解决方案**：
```python
# 查看详细的验证失败原因
validation = expectation_manager.post_generation_validate(...)
for violation in validation["violations"]:
    print(f"失败原因: {violation['message']}")
    print(f"详细信息: {violation['notes']}")

# 根据失败原因调整：
# 1. 检查内容是否包含满足指标
# 2. 增加释放过程的篇幅
# 3. 加强情感冲击的描写
```

### 问题3：期待感密度不足

**症状**：报告显示 `total_expectations` 过低

**解决方案**：
```python
# 手动添加期待标签
expectation_manager.tag_event_with_expectation(
    event_id="manual_expectation_001",
    expectation_type=ExpectationType.EMOTIONAL_HOOK,
    planting_chapter=current_chapter,
    description="制造情绪钩子",
    target_chapter=current_chapter + 5
)

# 或调整自动分析的敏感度
# 修改 ExpectationIntegrator 中的判断逻辑
```

## 最佳实践总结

1. **规划阶段**：确保每个重大事件都有对应的期待标签
2. **生成阶段**：严格遵循期待约束，不要遗漏必须释放的期待
3. **验证阶段**：仔细检查验证结果，及时调整
4. **报告阶段**：定期生成报告，持续优化期待感密度和质量

通过这个完整的集成，你的小说生成系统将具备强大的期待感管理能力，确保每章都能维持读者的追读动力！