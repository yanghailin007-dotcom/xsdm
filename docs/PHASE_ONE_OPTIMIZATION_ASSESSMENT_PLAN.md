# 第一阶段优化与评估方案设计

## 一、第一阶段产物清单

### 核心产物（第二阶段必须使用）
| 产物名称 | 数据结构 | 第二阶段使用场景 |
|---------|---------|----------------|
| `selected_plan` | 方案对象 | 获取标题、简介、核心方向 |
| `writing_style_guide` | 风格指南 | 章节生成的风格约束 |
| `core_worldview` | 世界观设定 | 章节生成的世界观一致性 |
| `character_design` | 角色设计 | 角色出场、对话、行为逻辑 |
| `stage_writing_plans` | 阶段写作计划 | **最重要**：包含事件系统，决定每章内容 |
| `emotional_blueprint` | 情绪蓝图 | 情绪曲线设计 |
| `global_growth_plan` | 成长计划 | 主角成长路线 |

### 辅助产物
| 产物名称 | 用途 |
|---------|------|
| `market_analysis` | 市场分析（参考性） |
| `faction_system` | 势力系统（世界观补充） |
| `expectation_mapping` | 期待感映射（参考性） |
| `supplementary_characters` | 补充角色（参考性） |

---

## 二、第二阶段（章节生成）实际依赖分析

### 章节生成核心方法: `_prepare_chapter_params`

```python
# 实际使用的 novel_data 字段：
- novel_title                    # 标题
- novel_synopsis                 # 简介  
- writing_style_guide            # 写作风格
- core_worldview                 # 世界观
- character_design               # 角色设计
- stage_writing_plans            # 阶段写作计划（含事件系统）
- emotional_blueprint            # 情绪蓝图
- global_growth_plan             # 成长计划
- current_progress.total_chapters # 总章节数
```

### 关键发现

**1. stage_writing_plans 是核心**
- 包含 `event_system.major_events` - 重大事件
- 包含 `event_system.medium_events` - 中型事件  
- 包含场景设计、章节范围、事件分解
- **每章内容都基于这个计划生成**

**2. character_design 是角色基础**
- 主角设定决定故事走向
- 配角设定影响剧情发展
- 关系网络影响互动逻辑

**3. core_worldview 是世界基础**
- 修炼体系、力量等级
- 世界规则、地理设定
- 背景设定的一致性

---

## 三、优化与评估对象重新设计

### 不应该做的事
❌ **不要把所有产物都丢给优化器**
- 数据量太大，AI难以处理
- 很多产物是参考性的，不需要优化
- 盲目优化可能破坏已有设计

### 应该做的事
✅ **针对第二阶段实际使用的核心数据进行优化**

---

## 四、三轮优化重新设计

### 第一轮: 写作计划优化
**目标**: 优化 `stage_writing_plans` 阶段写作计划

**检查维度**:
1. **事件系统完整性**
   - 重大事件是否有明确的目标和转折点
   - 事件之间的逻辑关系是否清晰
   - 事件与主角成长的关联是否紧密

2. **章节分配合理性**
   - 每个事件的章节数分配是否合理
   - 节奏是否张弛有度
   - 高潮点分布是否均匀

3. **场景设计可行性**
   - 场景是否能在字数限制内完成
   - 场景之间的衔接是否自然
   - 场景功能是否明确（起承转合）

**优化输出**:
- 修订后的 `stage_writing_plans`
- 问题列表和改进建议
- 结构调整建议

### 第二轮: 角色与世界观适配
**目标**: 优化 `character_design` + `core_worldview`

**检查维度**:
1. **角色与世界观一致性**
   - 角色能力是否符合世界规则
   - 角色背景是否融入世界设定
   - 角色动机是否基于世界逻辑

2. **角色关系网络合理性**
   - 主要角色之间的关系是否清晰
   - 冲突和联盟是否合理
   - 关系发展是否有空间

3. **成长体系可行性**
   - 升级路线是否清晰
   - 金手指设定是否有趣且不崩坏
   - 成长节奏是否适中

**优化输出**:
- 角色设计调整建议
- 世界观补充说明
- 一致性问题修复

### 第三轮: 写作风格与情绪匹配
**目标**: 优化 `writing_style_guide` + `emotional_blueprint`

**检查维度**:
1. **风格与题材匹配**
   - 写作风格是否符合目标平台
   - 语言风格是否统一
   - 叙事视角是否合适

2. **情绪曲线设计**
   - 情绪高低起伏是否合理
   - 高潮点位置是否合适
   - 读者情感引导是否有效

3. **开篇吸引力**
   - 前三章是否有足够吸引力
   - 悬念设置是否得当
   - 铺垫与爆发的平衡

**优化输出**:
- 风格指南调整
- 情绪曲线优化建议
- 开篇修改建议

---

## 五、质量评估对象

### 评估核心: 章节生成可行性

不是评估"写得有多好"，而是评估"能否顺利生成章节"

**评估维度**:

1. **事件可执行性** (40分)
   - 每个事件是否有清晰的执行路径
   - 场景是否可以转化为具体章节
   - 字数估算是否合理

2. **角色可用性** (30分)
   - 角色设定是否足够详细用于生成
   - 角色之间是否有明确的互动逻辑
   - 主角是否有清晰的行动动机

3. **世界一致性** (20分)
   - 世界观规则是否自洽
   - 设定是否有过多的漏洞
   - 背景是否支撑故事发展

4. **风格可执行性** (10分)
   - 风格指南是否具体可执行
   - 是否有明确的写作约束
   - 是否符合目标平台要求

---

## 六、执行流程（第15步）

```
第15步: 智能优化 + 质量评估
│
├── 阶段1: 加载核心数据 (0-5%)
│   ├── 加载 stage_writing_plans
│   ├── 加载 character_design
│   ├── 加载 core_worldview
│   ├── 加载 writing_style_guide
│   └── 加载 emotional_blueprint
│
├── 阶段2: 三轮优化 (5-75%)
│   ├── 第1轮: 写作计划优化 (5-30%)
│   │   └── 优化 stage_writing_plans
│   ├── 第2轮: 角色与世界观适配 (30-50%)
│   │   └── 优化 character_design + core_worldview
│   └── 第3轮: 风格与情绪匹配 (50-75%)
│       └── 优化 writing_style_guide + emotional_blueprint
│
├── 阶段3: 应用优化结果 (75-90%)
│   ├── 保存优化后的 stage_writing_plans
│   ├── 保存优化建议到 optimization_report.json
│   └── 更新 novel_data
│
└── 阶段4: 质量评估 (90-100%)
    ├── 评估章节生成可行性
    ├── 生成可行性报告
    └── 保存 quality_assessment.json
```

---

## 七、输出文件

```
小说项目/{标题}/
├── stage_writing_plan_optimized.json    # 优化后的阶段写作计划
├── optimization_report.json              # 三轮优化详细报告
│   ├── round1_plan_optimization          # 写作计划优化结果
│   ├── round2_character_worldview        # 角色与世界观优化
│   └── round3_style_emotion              # 风格与情绪优化
├── optimization_suggestions.md           # 人工审核建议
└── quality_assessment.json               # 质量评估报告
    ├── executability_score               # 可执行性评分
    ├── issues                            # 潜在问题
    └── recommendations                   # 执行建议
```

---

## 八、与第二阶段衔接

### 优化后直接可用的数据

第二阶段生成章节时，优先使用优化后的数据：

```python
# 在 _prepare_chapter_params 中
stage_writing_plan = (
    novel_data.get("stage_writing_plans_optimized")  # 优先使用优化后的
    or novel_data.get("stage_writing_plans")          # 回退到原始版本
)
```

### 质量评估指导第二阶段

如果质量评估发现问题，在章节生成时增加检查：
- 事件执行困难时，触发事件重组
- 角色设定模糊时，使用AI补充细节
- 世界观冲突时，进行一致性修复

---

## 九、实现优先级

1. **P0**: 修改 `_run_phase_one_optimization` 只加载核心数据
2. **P0**: 重新设计三轮优化逻辑（针对核心数据）
3. **P1**: 修改质量评估，评估章节生成可行性
4. **P1**: 实现优化结果保存和应用
5. **P2**: 在第二阶段使用优化后的数据
6. **P2**: 前端展示优化报告和建议

---

## 十、关键修改点

### 1. PhaseGenerator._run_phase_one_optimization
```python
def _run_phase_one_optimization(self):
    # 只加载核心数据
    core_data = {
        'stage_writing_plans': novel_data.get('stage_writing_plans'),
        'character_design': novel_data.get('character_design'),
        'core_worldview': novel_data.get('core_worldview'),
        'writing_style_guide': novel_data.get('writing_style_guide'),
        'emotional_blueprint': novel_data.get('emotional_blueprint'),
    }
    
    # 三轮优化...
    # 1. 优化写作计划
    # 2. 优化角色与世界观
    # 3. 优化风格与情绪
    
    # 保存优化结果
    novel_data['stage_writing_plans_optimized'] = optimized_plan
    novel_data['optimization_report'] = report
```

### 2. PhaseOneOptimizer 类重构
```python
class PhaseOneOptimizer:
    def optimize(self, core_data, platform):
        # 第1轮: 写作计划优化
        plan_result = self._optimize_writing_plan(
            core_data['stage_writing_plans']
        )
        
        # 第2轮: 角色与世界观适配
        char_world_result = self._optimize_character_worldview(
            core_data['character_design'],
            core_data['core_worldview']
        )
        
        # 第3轮: 风格与情绪匹配
        style_result = self._optimize_style_emotion(
            core_data['writing_style_guide'],
            core_data['emotional_blueprint']
        )
        
        return {
            'optimized_plan': plan_result['optimized_plan'],
            'report': {
                'round1': plan_result,
                'round2': char_world_result,
                'round3': style_result
            }
        }
```

### 3. 质量评估修改
```python
def _assess_writing_plan_quality(self):
    # 评估章节生成可行性
    # 不是评估"写得好不好"，而是"能不能生成"
    
    executability_checks = [
        check_event_executability(plan),
        check_character_usability(characters),
        check_worldview_consistency(worldview),
        check_style_feasibility(style_guide)
    ]
    
    return {
        'executability_score': calculate_score(executability_checks),
        'can_generate': all(checks),
        'issues': collect_issues(checks),
        'recommendations': generate_recommendations(checks)
    }
```

---

## 总结

**核心理念**: 优化和评估不是做"文学批评"，而是做"工程检查" - 确保第二阶段能顺利生成章节。

**优化对象**: 只优化第二阶段实际使用的核心数据，不碰参考性产物。

**三轮分工**:
1. 第1轮: 检查故事骨架（写作计划）
2. 第2轮: 检查角色和世界设定
3. 第3轮: 检查风格和情绪设计

**质量评估**: 评估"可执行性"，不是"文学性"。
