# 情绪规划增强设计方案

## 一、设计目标

采用**方案B的三层情绪规划**，但通过**增强提示词**实现，避免增加API调用次数。

## 二、当前状态分析

### 已有的情绪字段
```python
# 中型事件已有字段
medium_event = {
    "name": "中型事件名称",
    "emotional_focus": "屈辱/不甘",           # ✅ 已有
    "emotional_intensity": "high",            # ✅ 已有
    "key_emotional_beats": ["被人嘲笑"],      # ✅ 已有
}
```

### 缺失的关联性
- ❌ 中型事件没有映射到阶段情绪分段
- ❌ 重大事件没有整体情绪弧线
- ❌ 重大事件的"起承转合"缺乏情绪发展指导

## 三、设计方案

### Step 1: 阶段情绪计划（已有，无需修改）
- EmotionalPlanManager 生成
- 输出：3-5个情绪分段，每个分段包含：
  - segment_name
  - chapter_range
  - target_emotion_keyword
  - core_emotional_task

### Step 2: 重大事件情绪细分（新增，通过提示词增强）

#### 2.1 在现有API调用中增加上下文
在 `EventDecomposer.decompose_major_event()` 调用时：
- 传入 `stage_emotional_plan`
- 传入 `overall_emotional_blueprint`

#### 2.2 提示词增强策略

**当前提示词结构**：
```python
prompt = f"""
# 任务：重大事件"分形解剖"与"情绪融合"
## 当前待分解的重大事件信息
- 重大事件名称：{name}
- 事件章节范围：{range}
- 事件情绪目标：{goal}
"""
```

**增强后的提示词结构**：
```python
prompt = f"""
# 任务：重大事件"分形解剖"与"情绪融合"

## 【新增】阶段情绪蓝图参考
{stage_emotional_plan_formatted}

## 当前待分解的重大事件信息
- 重大事件名称：{name}
- 事件章节范围：{range}
- 事件情绪目标：{goal}

## 【新增】重大事件情绪细分要求
你需要为重大事件的"起承转合"设计情绪发展弧线：
1. **起**：承接上一阶段情绪，引入本事件情绪基调
2. **承**：情绪深化，矛盾激化
3. **转**：情绪转折，达到高潮或低谷
4. **合**：情绪释放，为下一阶段铺垫

## 【新增】中型事件情绪映射要求
每个中型事件必须：
1. 明确映射到某个阶段情绪分段
2. 说明对阶段情绪目标的贡献
3. 设计具体的情绪节拍
"""
```

### Step 3: 中型事件情绪细化（增强现有字段）

#### 3.1 新增关联性字段（在现有API返回中要求）
```python
medium_event = {
    # === 现有字段（保留） ===
    "name": "中型事件名称",
    "type": "medium_event",
    "chapter_range": "10-15",
    "main_goal": "目标描述",
    "emotional_focus": "屈辱/不甘",
    "emotional_intensity": "high",
    "key_emotional_beats": ["被人嘲笑", "实力不济", "决心变强"],
    "description": "事件描述",
    "contribution_to_major": "对重大事件的贡献",
    
    # === 新增字段（通过提示词要求） ===
    # 映射到阶段情绪分段
    "stage_emotional_mapping": {
        "segment_name": "压抑与铺垫期",           # 所属的阶段情绪分段
        "segment_emotion_keyword": "压抑/屈辱",    # 阶段情绪关键词
        "contribution_to_stage_emotion": "通过描述主角被家族抛弃、受人欺凌、实力低微的困境，累积读者的负面情绪，为后续爆发做铺垫。"
    },
    
    # 重大事件情绪细分中的定位
    "major_event_emotional_arc": "起",           # 在重大事件情绪弧线中的位置（起/承/转/合）
    "emotional_transition_from": "",             # 从什么情绪过渡（如果是"承"及以后）
    "emotional_transition_to": "",               # 过渡到什么情绪（如果不是"合"）
    
    # 增强的情绪节拍
    "emotional_beat_sequence": [                 # 有序的情绪节拍序列
        {
            "beat_type": "trigger",              # 触发/积累/爆发/释放
            "emotion": "屈辱",
            "intensity": "medium",
            "scene_hint": "被人嘲笑实力低微"
        },
        {
            "beat_type": "accumulation",
            "emotion": "愤怒",
            "intensity": "high",
            "scene_hint": "意识到差距，内心不甘"
        }
    ]
}
```

## 四、实施细节

### 4.1 修改 EventDecomposer.decompose_major_event() 方法签名

```python
def decompose_major_event(self, 
                        major_event_skeleton: Dict, 
                        stage_name: str, 
                        stage_range: str, 
                        novel_title: str, 
                        novel_synopsis: str, 
                        creative_seed: Dict, 
                        overall_stage_plan: Dict,
                        global_novel_data: Dict,
                        stage_emotional_plan: Dict = None,        # 新增
                        overall_emotional_blueprint: Dict = None  # 新增
                        ) -> Optional[Dict]:
```

### 4.2 增强 _build_decomposition_prompt() 方法

#### 4.2.1 格式化阶段情绪计划
```python
def _format_stage_emotional_plan(self, stage_emotional_plan: Dict, 
                                 major_event_chapter_range: str) -> str:
    """
    格式化阶段情绪计划，只提取与当前重大事件相关的部分
    
    Returns:
        格式化的情绪分段文本
    """
    if not stage_emotional_plan or "emotional_segments" not in stage_emotional_plan:
        return "（无阶段情绪计划）"
    
    # 解析重大事件的章节范围
    major_start, major_end = parse_chapter_range(major_event_chapter_range)
    
    # 找出与重大事件范围重叠的情绪分段
    relevant_segments = []
    for segment in stage_emotional_plan["emotional_segments"]:
        seg_start, seg_end = parse_chapter_range(segment["chapter_range"])
        # 检查是否有重叠
        if not (seg_end < major_start or seg_start > major_end):
            relevant_segments.append(segment)
    
    if not relevant_segments:
        return "（重大事件范围与阶段情绪分段无重叠）"
    
    formatted = "## 相关的阶段情绪分段\n\n"
    for i, segment in enumerate(relevant_segments, 1):
        formatted += f"""
### {i}. {segment['segment_name']} ({segment['chapter_range']})
- **核心情绪关键词**：{segment['target_emotion_keyword']}
- **核心情绪任务**：{segment['core_emotional_task']}

"""
    
    return formatted
```

#### 4.2.2 构建增强的提示词
```python
def _build_decomposition_prompt(self, major_event_skeleton: Dict,
                               stage_name: str, 
                               top_level_context: str,
                               stage_emotional_plan: Dict = None,  # 新增
                               overall_emotional_blueprint: Dict = None) -> str:  # 新增
    """构建事件分解prompt（增强版）"""
    
    # 格式化阶段情绪计划
    stage_emotional_guidance = ""
    if stage_emotional_plan:
        stage_emotional_guidance = self._format_stage_emotional_plan(
            stage_emotional_plan, 
            major_event_skeleton.get('chapter_range', '1-1')
        )
    
    # 提取重大事件的情绪目标
    major_emotional_goal = major_event_skeleton.get('emotional_goal', 
                                  major_event_skeleton.get('emotional_arc', '未指定'))
    
    prompt = f"""
# 任务：重大事件"分形解剖"与"情绪融合"

{top_level_context}

{stage_emotional_guidance}

## 当前待分解的重大事件信息
- **所属阶段**: {stage_name}
- **重大事件名称**: {major_event_skeleton.get('name')}
- **事件章节范围**: {major_event_skeleton.get('chapter_range')}
- **事件情绪目标**: {major_emotional_goal}

## 分解原则与规则 (必须严格遵守)
1. **目标继承与服务**: 每一个中型事件都必须为实现【当前重大事件核心目标】和【顶层战略背景】服务。
2. **结构完整**: 所有中型事件必须构成服务于重大事件目标的、逻辑连贯的"起、承、转、合"结构。
3. **绝对覆盖指令**: 所有中型事件的 chapter_range 必须完整覆盖重大事件的整个章节范围。

## 【核心】重大事件情绪细分要求

你需要为重大事件设计一个完整的情绪发展弧线：

### 情绪弧线设计（起承转合）

**起（引入期）**
- **情绪起点**：承接上一事件的情绪状态
- **情绪目标**：引入本事件的基调情绪
- **设计要点**：通过情境展示，让读者进入情绪氛围

**承（发展期）**
- **情绪深化**：在"起"的基础上，情绪逐渐加强
- **矛盾激化**：通过冲突，让情绪更加复杂
- **设计要点**：增加情绪层次，让读者感受到张力

**转（转折期）**
- **情绪转折**：达到情绪的高峰或低谷
- **意外元素**：通过意外，打破读者预期
- **设计要点**：形成强烈冲击，留下深刻印象

**合（收束期）**
- **情绪释放**：对前面的情绪积累做出回应
- **过渡铺垫**：为下一个重大事件做好情绪准备
- **设计要点**：给予读者满足感，同时引发新的期待

### 中型事件情绪映射要求

每个中型事件必须包含以下情绪信息：

1. **阶段情绪映射**（stage_emotional_mapping）：
   - 明确所属的阶段情绪分段
   - 说明对阶段情绪目标的具体贡献
   - 确保与阶段整体情绪发展方向一致

2. **重大事件情绪定位**（major_event_emotional_arc）：
   - 标注在重大事件情绪弧线中的位置（起/承/转/合）
   - 如果是"承"及以后，说明从什么情绪过渡
   - 如果不是"合"，说明过渡到什么情绪

3. **情绪节拍序列**（emotional_beat_sequence）：
   - 按顺序列出情绪变化节拍
   - 每个节拍包含：类型、情绪、强度、场景提示
   - 确保情绪变化有逻辑性

## 【重要】特殊情感事件设计原则

特殊情感事件不是独立的章节事件，而是**附着在中型事件上的情感元素**：

1. **附着到中型事件**：每个特殊情感事件必须明确附着到某个具体的中型事件
2. **指定目标章节**：如果中型事件跨越多章，必须明确特殊情感事件发生在哪一章
3. **不要分配chapter_range**：特殊情感事件不占用独立章节，只需要指定目标章节号
4. **提供融合线索**：给出情感基调、关键元素，让场景生成自然融合

## 输出格式（严格遵守）

{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
    "main_goal": "{major_event_skeleton.get('main_goal')}",
    "emotional_goal": "{major_event_skeleton.get('emotional_goal', major_emotional_goal)}",
    "chapter_range": "{major_event_skeleton.get('chapter_range')}",
    
    // 重大事件整体情绪弧线（新增）
    "emotional_arc_overview": {{
        "起": "引入期的情绪发展描述",
        "承": "发展期的情绪深化描述",
        "转": "转折期的情绪冲击描述",
        "合": "收束期的情绪释放描述"
    }},
    
    "composition": {{
        "起": [
            {{
                "name": "中型事件名",
                "type": "medium_event",
                "chapter_range": "string",
                "main_goal": "目标",
                "description": "描述",
                "contribution_to_major": "对重大事件的贡献",
                
                // === 现有情绪字段（保留） ===
                "emotional_focus": "string",
                "emotional_intensity": "low/medium/high",
                "key_emotional_beats": ["情感节拍1"],
                
                // === 新增：阶段情绪映射 ===
                "stage_emotional_mapping": {{
                    "segment_name": "所属的阶段情绪分段名称",
                    "segment_emotion_keyword": "阶段情绪关键词",
                    "contribution_to_stage_emotion": "具体如何贡献于阶段情绪目标"
                }},
                
                // === 新增：重大事件情绪定位 ===
                "major_event_emotional_arc": "起/承/转/合",
                "emotional_transition_from": "从什么情绪过渡（如果是'承'及以后）",
                "emotional_transition_to": "过渡到什么情绪（如果不是'合'）",
                
                // === 新增：有序的情绪节拍序列 ===
                "emotional_beat_sequence": [
                    {{
                        "beat_type": "trigger/accumulation/climax/release",
                        "emotion": "具体情绪",
                        "intensity": "low/medium/high",
                        "scene_hint": "场景提示"
                    }}
                ],
                
                // 特殊情感事件（附着在中型事件上）
                "special_emotional_events": [
                    {{
                        "name": "情感互动名称",
                        "target_chapter": 10,
                        "purpose": "深化角色关系",
                        "emotional_tone": "温馨/紧张/忧郁等",
                        "key_elements": ["对话", "眼神交流", "肢体语言"],
                        "context_hint": "在中型事件的转折点"
                    }}
                ]
            }}
        ],
        "承": [],
        "转": [],
        "合": []
    }},
    "emotional_arc_summary": "string",
    "aftermath": "string"
}}

**重要提醒**：
- stage_emotional_mapping、major_event_emotional_arc、emotional_beat_sequence 是新增的必需字段
- special_emotional_events 是中型事件的子字段，不是重大事件的顶级字段
- 确保所有中型事件的 chapter_range 完整覆盖重大事件的章节范围
"""
    return prompt
```

### 4.3 修改 StagePlanManager 调用

在 `StagePlanManager._decompose_major_events_to_medium_only()` 中：

```python
def _decompose_major_events_to_medium_only(self, major_event_skeletons: List[Dict],
                                         stage_name: str, stage_range: str,
                                         creative_seed: Dict, novel_title: str,
                                         novel_synopsis: str, overall_stage_plan: Dict) -> List[Dict]:
    """分解重大事件为中型事件（第一阶段专用 - 不进行场景分解）"""
    self.logger.info("    [第一阶段] 只分解到中型事件，不进行场景分解...")
    fleshed_out_major_events = []
    
    # === 新增：获取阶段情绪计划 ===
    emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
    stage_emotional_plan = self.emotional_manager.generate_stage_emotional_plan(
        stage_name, stage_range, emotional_blueprint
    )
    
    for skeleton in major_event_skeletons:
        self.logger.info(f"    -> 正在解剖重大事件: '{skeleton['name']}' ({skeleton['chapter_range']})")
        
        fleshed_out_event = None
        for attempt in range(3):
            try:
                # === 修改：传入阶段情绪计划 ===
                fleshed_out_event = self.event_decomposer.decompose_major_event(
                    major_event_skeleton=skeleton,
                    stage_name=stage_name,
                    stage_range=stage_range,
                    novel_title=novel_title,
                    novel_synopsis=novel_synopsis,
                    creative_seed=creative_seed,
                    overall_stage_plan=overall_stage_plan,
                    global_novel_data=self.generator.novel_data,
                    stage_emotional_plan=stage_emotional_plan,              # 新增
                    overall_emotional_blueprint=emotional_blueprint          # 新增
                )
                
                if fleshed_out_event:
                    self.logger.info(f"      ✅ 成功分解为中型事件（第一阶段到此为止）")
                    break
                else:
                    self.logger.warn(f"      ⚠️ 第{attempt+1}次解剖失败")
            except Exception as e:
                self.logger.error(f"      ❌ 第{attempt+1}次解剖出错: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
        
        # ... 后续处理
```

## 五、数据流示例

### 输入数据
```python
# 阶段情绪计划
stage_emotional_plan = {
    "stage_name": "development_stage",
    "main_emotional_arc": "主角在挫折中成长，逐步积累力量",
    "emotional_segments": [
        {
            "segment_name": "压抑与铺垫期",
            "chapter_range": "31-45",
            "target_emotion_keyword": "压抑/屈辱",
            "core_emotional_task": "通过描述主角被欺凌、实力低微，累积读者负面情绪"
        },
        {
            "segment_name": "初获奇遇期",
            "chapter_range": "46-60",
            "target_emotion_keyword": "惊喜/期待",
            "core_emotional_task": "主角获得金手指，展示成长潜力"
        }
    ]
}

# 重大事件骨架
major_event_skeleton = {
    "name": "首次历练任务",
    "chapter_range": "31-40",
    "main_goal": "通过历练任务展示主角成长",
    "role_in_stage_arc": "承",
    "emotional_goal": "从屈辱到初展锋芒"
}
```

### 输出数据
```python
# 分解后的重大事件
decomposed_major_event = {
    "name": "首次历练任务",
    "chapter_range": "31-40",
    "emotional_goal": "从屈辱到初展锋芒",
    
    # 重大事件整体情绪弧线
    "emotional_arc_overview": {
        "起": "主角接受任务时的忐忑不安，对实力不足的担忧",
        "承": "任务过程中的挫折，被队友轻视，遭遇困难",
        "转": "关键时刻发挥奇遇能力，挽救局面",
        "合": "完成任务获得认可，内心建立自信"
    },
    
    "composition": {
        "起": [{
            "name": "接受任务",
            "chapter_range": "31-32",
            "main_goal": "主角报名参加历练任务",
            
            # 现有字段
            "emotional_focus": "忐忑/不安",
            "emotional_intensity": "medium",
            "key_emotional_beats": ["担心实力不足", "下定决心"],
            
            # 新增：阶段情绪映射
            "stage_emotional_mapping": {
                "segment_name": "压抑与铺垫期",
                "segment_emotion_keyword": "压抑/屈辱",
                "contribution_to_stage_emotion": "通过主角对实力的自我怀疑，强化读者对主角弱势地位的认知，为后续爆发积累情绪。"
            },
            
            # 新增：重大事件情绪定位
            "major_event_emotional_arc": "起",
            "emotional_transition_from": "无（事件起点）",
            "emotional_transition_to": "挫折与屈辱",
            
            # 新增：有序的情绪节拍序列
            "emotional_beat_sequence": [
                {
                    "beat_type": "trigger",
                    "emotion": "犹豫",
                    "intensity": "low",
                    "scene_hint": "看着任务榜犹豫不决"
                },
                {
                    "beat_type": "accumulation",
                    "emotion": "不安",
                    "intensity": "medium",
                    "scene_hint": "回忆过往失败经历"
                },
                {
                    "beat_type": "climax",
                    "emotion": "决心",
                    "intensity": "high",
                    "scene_hint": "咬牙报名，眼神坚定"
                }
            ]
        }],
        "承": [{
            "name": "遭遇挫折",
            "chapter_range": "33-36",
            "main_goal": "任务中遭遇困难，被队友轻视",
            "emotional_focus": "屈辱/不甘",
            "emotional_intensity": "high",
            
            "stage_emotional_mapping": {
                "segment_name": "压抑与铺垫期",
                "segment_emotion_keyword": "压抑/屈辱",
                "contribution_to_stage_emotion": "通过被队友嘲讽、遭遇强敌无力应对，将读者压抑情绪推向顶点。"
            },
            
            "major_event_emotional_arc": "承",
            "emotional_transition_from": "不安",
            "emotional_transition_to": "爆发",
            
            "emotional_beat_sequence": [
                {
                    "beat_type": "trigger",
                    "emotion": "期待",
                    "intensity": "medium",
                    "scene_hint": "队伍集合，主角满怀希望"
                },
                {
                    "beat_type": "accumulation",
                    "emotion": "尴尬",
                    "intensity": "medium",
                    "scene_hint": "被队友质疑实力"
                },
                {
                    "beat_type": "accumulation",
                    "emotion": "屈辱",
                    "intensity": "high",
                    "scene_hint": "战斗中无力应对，被嘲讽"
                },
                {
                    "beat_type": "climax",
                    "emotion": "愤怒",
                    "intensity": "high",
                    "scene_hint": "内心极度不甘，咬牙切齿"
                }
            ]
        }],
        # ... "转"和"合"的中型事件
    }
}
```

## 六、优势总结

### 1. 不增加API调用
- 所有情绪规划都在一次 `decompose_major_event` API调用中完成
- 通过增强提示词，让AI一次性返回完整的情绪细分结果

### 2. 层级关系清晰
```
阶段情绪分段
    ↓ 映射到
重大事件情绪弧线（起承转合）
    ↓ 细化为
中型事件情绪目标
    ↓ 具体化为
情绪节拍序列
```

### 3. 保持向后兼容
- 保留现有的 `emotional_focus`、`emotional_intensity` 字段
- 新增字段都是可选的，不影响现有逻辑

### 4. 可验证性强
- 每个层级都有明确的映射关系
- 可以通过代码验证情绪发展的连贯性

## 七、后续优化方向

### 短期（当前实施）
- ✅ 增强提示词，实现三层情绪规划
- ✅ 在 `decompose_major_event` 一次调用中完成

### 中期（未来优化）
- 添加情绪连贯性验证逻辑
- 在 `SceneAssembler` 中参考情绪节拍生成场景
- 在 `ContentGenerator` 中使用情绪指导写作

### 长期（高级功能）
- 情绪效果追踪：分析生成内容是否达到预期情绪
- 动态情绪调整：根据读者反馈调整情绪规划
- 情绪模板库：积累常见情绪模式，提高生成效率