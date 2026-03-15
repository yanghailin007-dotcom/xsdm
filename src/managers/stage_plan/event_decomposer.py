"""
事件分解器 - 负责将事件分解为不同层级
"""
import json
from typing import Dict, List, Optional
from src.utils.logger import get_logger
from src.managers.StagePlanUtils import parse_chapter_range


class EventDecomposer:
    """事件分解器 - 将重大事件分解为中型事件和场景"""
    
    def __init__(self, api_client, logger_name: str = "EventDecomposer"):
        self.api_client = api_client
        self.logger = get_logger(logger_name)
    
    def decompose_major_event(self, major_event_skeleton: Dict, stage_name: str,
                            stage_range: str, novel_title: str, novel_synopsis: str,
                            creative_seed: Dict, overall_stage_plan: Dict,
                            global_novel_data: Dict,
                            stage_emotional_arc: Optional[Dict] = None,
                            overall_emotional_blueprint: Optional[Dict] = None,
                            plot_constraint_context: Optional[str] = None) -> Optional[Dict]:
        """
        分解重大事件为中型事件和特殊情感事件
        
        Args:
            major_event_skeleton: 重大事件骨架
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            novel_title: 小说标题
            novel_synopsis: 小说简介
            creative_seed: 创意种子
            overall_stage_plan: 整体阶段计划
            global_novel_data: 全局小说数据
            plot_constraint_context: 情节连续性约束上下文，防止内容重复
            
        Returns:
            分解后的重大事件字典
        """
        try:
            # 构建顶层上下文
            top_level_context_block = self._build_top_level_context(
                creative_seed, global_novel_data, overall_stage_plan, stage_name
            )
            
            # 构建prompt
            prompt = self._build_decomposition_prompt(
                major_event_skeleton, stage_name, top_level_context_block,
                stage_emotional_arc, overall_emotional_blueprint,
                plot_constraint_context
            )
            
            # 调用API生成
            result = self.api_client.generate_content_with_retry(
                content_type="major_event_decomposition",
                user_prompt=prompt,
                purpose=f"解剖事件'{major_event_skeleton.get('name')}'"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"分解重大事件时出错: {e}")
            return None
    
    def smart_decompose_medium_events(self, major_event: Dict, stage_name: str,
                                     novel_title: str, novel_synopsis: str,
                                     creative_seed: Dict, overall_stage_plan: Dict,
                                     global_novel_data: Dict,
                                     consistency_guidance: Optional[str] = None) -> Dict:
        """
        智能分解中型事件 - AI自由决策最优结构
        
        ⚠️ 灵活策略：让AI根据中型事件的具体情况（章节数、目标复杂度、情感需求）
        自由决定：
        - 哪些场景可以合并到一章内
        - 哪些场景需要扩展成多个章节
        - 每章应该包含多少个场景
        - 场景之间如何衔接
        
        核心原则：
        1. **避免重复**：不要在不同章节使用相同或相似的场景
        2. **完整结构**：确保每个中型事件的章节范围内形成连贯的叙事流
        3. **灵活调整**：根据实际情况自由决定结构，不强制规定
        
        Args:
            major_event: 重大事件
            stage_name: 阶段名称
            其他参数同上
            
        Returns:
            更新后的重大事件
        """
        # 收集所有中型事件（支持两种格式）
        all_medium_events = []
        composition = major_event.get("composition", {})
        
        # 🔥 修复：支持黄金三章的数组格式和标准事件的字典格式
        if isinstance(composition, list):
            # 黄金三章格式：composition是数组
            all_medium_events = composition
        elif isinstance(composition, dict):
            # 标准事件格式：composition是起承转合字典
            for phase_events in composition.values():
                if isinstance(phase_events, list):
                    all_medium_events.extend(phase_events)
        
        self.logger.info(f"  📋 开始为 {len(all_medium_events)} 个中型事件进行智能分解（AI自由决策结构）...")
        
        # 为每个中型事件进行分解
        decomposed_medium_events = []
        for medium_event in all_medium_events:
            chapter_range = medium_event.get('chapter_range', '0-0')
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            
            self.logger.info(f"    -> 中型事件'{medium_event['name']}'({chapter_count}章) - AI自由决策最优结构")
            
            # 让AI自由决策如何分解
            decomposed_event = self._decompose_with_ai_free_choice(
                medium_event, major_event, stage_name, novel_title, novel_synopsis,
                creative_seed, overall_stage_plan, global_novel_data,
                consistency_guidance
            )
            
            if decomposed_event:
                # 保留中型事件的核心目标信息
                decomposed_event.update({
                    "main_goal": medium_event.get("main_goal", ""),
                    "emotional_focus": medium_event.get("emotional_focus", ""),
                    "emotional_intensity": medium_event.get("emotional_intensity", "medium"),
                    "key_emotional_beats": medium_event.get("key_emotional_beats", []),
                    "contribution_to_major": medium_event.get("contribution_to_major", "")
                })
                decomposed_medium_events.append(decomposed_event)
            else:
                self.logger.warning(f"      ⚠️ 中型事件'{medium_event['name']}'分解失败，保留原始结构")
                decomposed_medium_events.append(medium_event)
        
        # 更新重大事件的composition（支持两种格式）
        major_event_copy = major_event.copy()
        
        if isinstance(composition, list):
            # 🔥 黄金三章格式：composition保持为数组
            major_event_copy["composition"] = decomposed_medium_events
        else:
            # 🔥 标准事件格式：composition是起承转合字典
            major_event_copy["composition"] = {}
            for phase_name, phase_events in composition.items():
                major_event_copy["composition"][phase_name] = []
                for event in phase_events:
                    # 找到对应的分解后中型事件（添加安全检查）
                    event_name = event.get('name')
                    if event_name:
                        decomposed_event = next((de for de in decomposed_medium_events
                                               if de.get('name') == event_name), event)
                    else:
                        # 如果没有name字段，使用原事件
                        decomposed_event = event
                    major_event_copy["composition"][phase_name].append(decomposed_event)
        
        self.logger.info(f"  ✅ 中型事件分解完成：{len(decomposed_medium_events)}/{len(all_medium_events)} 成功")
        return major_event_copy
    
    def _build_top_level_context(self, creative_seed: Dict, global_novel_data: Dict,
                                overall_stage_plan: Dict, stage_name: str) -> str:
        """构建顶层设计上下文"""
        try:
            creative_seed_str = json.dumps(creative_seed, ensure_ascii=False, indent=2)
            global_growth_plan = global_novel_data.get("global_growth_plan", {})
            global_growth_plan_str = json.dumps(global_growth_plan, ensure_ascii=False, indent=2)
            current_stage_plan_str = json.dumps(
                overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}),
                ensure_ascii=False, indent=2
            )
            
            return f"""
# 1. 最高指令：核心创意种子 (Creative Seed)
你的一切创作都必须是这份文档的具象化，尤其是要参考`completeStoryline`中为当前阶段设计的剧情。

{creative_seed_str}

# 2. 战略蓝图：全书成长规划 (Global Growth Plan)
你设计的事件必须服务于这些主角成长目标。

{global_growth_plan_str}

# 3. 当前阶段任务 (Current Stage Plan)
你正在为这个阶段设计情节，必须完成其核心任务。

{current_stage_plan_str}
"""
        except Exception as e:
            self.logger.warning(f"构建顶层上下文时发生错误: {e}, 使用简化版上下文。")
            return "# 顶层战略背景\n简化版上下文"

    def _build_comprehensive_scene_context(self, global_novel_data: Dict, major_event: Dict,
                                          medium_event: Dict, stage_name: str) -> str:
        """
        构建场景生成的综合上下文（使用共享的 SceneContextBuilder）

        包含：
        1. 角色信息（主角、重要配角）
        2. 世界观设定（修炼体系、世界规则）
        3. 重大事件完整信息
        4. 阶段上下文

        Args:
            global_novel_data: 全局小说数据
            major_event: 所属重大事件
            medium_event: 当前中型事件
            stage_name: 阶段名称

        Returns:
            格式化的上下文字符串
        """
        from src.utils.SceneContextBuilder import get_scene_context_builder

        context_builder = get_scene_context_builder()
        return context_builder.build_comprehensive_context(
            medium_event, major_event, global_novel_data, stage_name
        )

    def _build_decomposition_prompt(self, major_event_skeleton: Dict,
                                   stage_name: str, top_level_context: str,
                                   stage_emotional_arc: Optional[Dict] = None,
                                   overall_emotional_blueprint: Optional[Dict] = None,
                                   plot_constraint_context: Optional[str] = None) -> str:
        """构建事件分解prompt（从事件推导情绪）"""
        
        # 构建情节约束部分
        plot_constraint_section = ""
        if plot_constraint_context:
            plot_constraint_section = f"""

## 【关键约束】情节连续性要求
{plot_constraint_context}

"""

        # 构建情绪弧线指导
        emotional_guidance = ""
        if stage_emotional_arc:
            emotional_guidance = f"""
## 阶段情绪弧线指导（战略级指导）
- **阶段起点情绪**: {stage_emotional_arc.get('start_emotion', '未定义')}
- **阶段终点情绪**: {stage_emotional_arc.get('end_emotion', '未定义')}
- **阶段情绪发展**: {stage_emotional_arc.get('description', '未定义')}

**核心原则**: 情绪是从事件中自然产生的，而不是预先规定的。
"""
        
        # 构建情感光谱指导
        emotional_spectrum_guidance = ""
        if overall_emotional_blueprint and "emotional_spectrum" in overall_emotional_blueprint:
            spectrum = overall_emotional_blueprint.get("emotional_spectrum", [])
            if spectrum:
                emotional_spectrum_guidance = f"""
## 全书情感光谱参考
核心情感驱动力: {', '.join(spectrum)}

这是本小说的情感底色，所有情绪发展都应该与之呼应。
"""
        
        return f"""
# 任务：重大事件"分形解剖"与"情绪推导"
你的任务是将一个宏观的"重大事件"，根据其在全书蓝图中的战略地位，分解为具体的、可执行的【中型事件】。

{top_level_context}
{plot_constraint_section}

{emotional_guidance}

{emotional_spectrum_guidance}

## 当前待分解的重大事件信息
- **所属阶段**: {stage_name}
- **重大事件名称**: {major_event_skeleton.get('name')}
- **事件章节范围**: {major_event_skeleton.get('chapter_range')}
- **事件核心目标**: {major_event_skeleton.get('main_goal', '推进主情节')}

## 核心原则：从事件推导情绪（不是从情绪规划事件）

**正确的逻辑**:
1. **事件优先**: 首先规划"起承转合"应该发生什么事件
2. **情绪推导**: 基于发生的事件，推导主角/读者会感受到什么情绪
3. **情绪连贯**: 确保情绪发展符合阶段情绪弧线的方向

**错误的做法**（严禁）:
- ❌ 先规定"第31-40章要压抑"，再去找压抑的事件
- ❌ 情绪和事件割裂，没有因果联系
- ❌ 为了符合情绪目标，强行编造不自然的事件

## 分解原则与规则 (必须严格遵守)
1.  **目标继承与服务**: 你设计的每一个【中型事件】都必须是为实现【当前重大事件核心目标】和【顶层战略背景】服务的。
2.  **结构完整**: 所有中型事件必须共同构成一个服务于重大事件目标的、逻辑连贯的"起、承、转、合"结构。
3.  【绝对覆盖指令】: 你生成的所有中型事件的chapter_range，必须完整且无缝地覆盖父级"重大事件"的整个章节范围。
4.  【🔥黄金三章特殊规则 - 整体式设计】:
    - **当重大事件是"黄金开局弧光"(is_golden_arc=true)且章节范围为1-3时**
    - **黄金三章是一个完整的整体，不需要内部分解为"起承转合"**
    - **必须只生成一个中型事件**，覆盖全部1-3章
    - **禁止将黄金三章拆分为多个中型事件**
    - **composition中只有"起"包含这一个事件，"承、转、合"必须为空数组[]**
    - 黄金三章本身就是一个完整的开局，不需要再用起承转合细分
    - 这12-18个情节点自然形成完整开局故事的内在节奏
    - 情节点数量要求：12-18个（3章 × 每章4-6个）
5.  【🔥绝对禁止时间重叠】:
    - 每个中型事件必须**紧接着上一个中型事件结束的地方开始**
    - **严禁重新描述**前一个中型事件已经完成的情节
    - 如果中型事件A在第1章结束时"老祖显圣"，那么中型事件B（第2章）必须从"显圣之后的反应"开始，不能重新描述"老祖显圣"的过程
    - 这是**时间线连续**，不是**同一事件的不同角度描述**

## 【🔥强制规则】情节点数量要求

每个中型事件的 plot_outline 必须严格遵循以下数量规则：

| 章节数 | 情节点数量 | 计算方式 |
|-------|----------|---------|
| 1章   | 4-6个    | 每章4-6个 |
| 2章   | 8-12个   | 每章4-6个 × 2 |
| 3章   | 12-18个  | 每章4-6个 × 3 |
| n章   | n×4 到 n×6个 | 每章4-6个 × n |

**⚠️ 这是硬性要求，不是建议！**
- 如果生成的情节点数量不足，将被判定为不合格
- 情节点数量宁多勿少（在范围内）
- 每个情节点必须是具体、可展开的内容，不能空洞

## 【重要】特殊情感事件设计原则

特殊情感事件不是独立的章节事件，而是**附着在中型事件上的情感元素**，用于深化角色关系、调整叙事节奏。

**关键要求**：
1. **附着到中型事件**：每个特殊情感事件必须明确附着到某个具体的中型事件
2. **指定目标章节**：如果中型事件跨越多章，必须明确特殊情感事件发生在哪一章
3. **不要分配chapter_range**：特殊情感事件不占用独立章节，只需要指定目标章节号
4. **提供融合线索**：给出情感基调、关键元素，让第二阶段的场景生成自然融合

## 输出格式: 严格遵守规则，返回包含'composition'字段的JSON对象

【🔥 黄金三章(1-3章)特殊输出格式 - 整体式设计】
当章节范围为1-3时，composition直接是一个包含单个完整事件的数组，**不需要"起承转合"结构**：
{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "起",
    "main_goal": "完整呈现开局：诡异降临→模拟器初现→初步破局",
    "chapter_range": "1-3",
    "composition": [
        {{
            "name": "黄金开局整体事件",
            "type": "medium_event",
            "chapter_range": "1-3",
            "main_goal": "完整呈现开局阶段全部内容",
            "plot_outline": [
                "第1章情节点1...",
                "第1章情节点2...",
                "第1章情节点3...",
                "第1章情节点4...",
                "第2章情节点1...",
                "第2章情节点2...",
                "第2章情节点3...",
                "第2章情节点4...",
                "第3章情节点1...",
                "第3章情节点2...",
                "第3章情节点3...",
                "第3章情节点4..."
            ],
            "description": "黄金三章是番茄小说开局特殊设计，不需要内部分解，直接包含12-18个情节点",
            "stage_context": {{...}},
            "emotional_derivation": {{...}},
            "alignment_with_stage_arc": {{"position_in_arc": "起", "contribution_to_stage_emotion": "高能开局，极速入戏"}},
            "contribution_to_major": "完成开局留存读者的目标",
            "special_emotional_events": [...]
        }}
    ],
    "emotional_arc_summary": "黄金开局：危机降临→冷静应对→破局反击"
}}

【标准事件(4章及以上)输出格式】
当章节范围大于3章时，composition是起承转合字典，分解为多个中型事件：
{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
    "main_goal": "{major_event_skeleton.get('main_goal')}",
    "chapter_range": "{major_event_skeleton.get('chapter_range')}",
    "composition": {{
        "起": [{{...中型事件1...}}],
        "承": [{{...中型事件2...}}],
        "转": [{{...中型事件3...}}],
        "合": [{{...中型事件4...}}]
    }},
    "emotional_arc_summary": "重大事件整体情绪弧线总结"
}}

【关键区分】
- **黄金三章(1-3章)**: composition = [单个完整事件] （数组，不是字典！）
- **标准事件(4章+)**: composition = {{"起": [...], "承": [...], "转": [...], "合": [...]}} （起承转合字典）

注意：
1. **🔥 黄金三章(1-3章)的composition是数组，不是起承转合字典**
2. **🔥 黄金三章是番茄小说特殊开局设计，不需要内部分解，就是一个整体**
3. **🔥 plot_outline 数量强制规则**：黄金三章必须12-18个情节点（3章 × 每章4-6个）
4. 每个情节点应该是可以展开为300-500字场景的具体内容
5. 情节点之间必须有因果关系和时间递进关系
6. emotional_derivation 和 alignment_with_stage_arc 是新增的必需字段
7. special_emotional_events 是中型事件的子字段，不是重大事件的顶级字段
8. 情绪必须从事件中自然推导，不能为了符合目标而强行编造
"""
    
    def _decompose_to_chapter_then_scene(self, medium_event: Dict, major_event: Dict,
                                       stage_name: str, novel_title: str, novel_synopsis: str,
                                       creative_seed: Dict, overall_stage_plan: Dict,
                                       global_novel_data: Dict,
                                       consistency_guidance: Optional[str] = None,
                                       enforce_chapter_independence: bool = False) -> Optional[Dict]:
        """
        分解中型事件为章节事件，然后分解为场景
        
        Args:
            enforce_chapter_independence: 是否强制每章独立（避免场景重复）
                - True: 为每章生成独立的起承转合场景，明确递进关系
                - False: 标准分解，章节之间自然衔接
        """
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
            一致性铁律 (必须遵守)
            你在进行事件分解时，必须严格遵守以下已确定的世界事实。
            {consistency_guidance}
            """
        
        # 第一步：分解为章节事件
        chapter_instruction = """
请将这个中型事件分解为各个章节事件，每个章节事件覆盖1章。"""
        
        if enforce_chapter_independence:
            chapter_instruction += """

## 【关键要求】章节独立性和递进性
为避免内容重复，每章必须具有：
1. **独立目标**：每章完成中型事件目标的不同阶段（起始/发展/高潮/收尾）
2. **独立场景**：每章形成完整的起承转合场景结构，不要与其他章重复
3. **递进关系**：章节之间要有明确的递进关系，前一章节为后一章铺垫
4. **避免重复**：严禁在不同章节使用相同或相似的场景内容"""
        
        # 🔥 新增：收集当前中型事件中的特殊情感事件
        special_emotional_context = ""
        special_events = medium_event.get("special_emotional_events", [])
        if special_events:
            # 按章节分组特殊情感事件
            events_by_chapter = {}
            for se in special_events:
                target_ch = se.get("target_chapter")
                if target_ch:
                    if target_ch not in events_by_chapter:
                        events_by_chapter[target_ch] = []
                    events_by_chapter[target_ch].append(se)

            if events_by_chapter:
                special_emotional_context = "\n## 【情感融合要求】特殊情感事件\n"
                for chapter_num, events in sorted(events_by_chapter.items()):
                    special_emotional_context += f"\n### 第{chapter_num}章需要融合的情感事件：\n"
                    for se in events:
                        special_emotional_context += f"- **{se.get('name')}**: {se.get('purpose', '')}\n"
                        special_emotional_context += f"  - 情感基调: {se.get('emotional_tone', '')}\n"
                        special_emotional_context += f"  - 关键元素: {', '.join(se.get('key_elements', []))}\n"
                        if se.get('context_hint'):
                            special_emotional_context += f"  - 上下文提示: {se.get('context_hint')}\n"

                special_emotional_context += "\n**重要**：请将这些情感元素自然地融入到对应章节的场景中，让情感发展与情节推进有机结合，不要生硬插入。\n"

        # 获取阶段上下文（如果有）
        stage_context_info = medium_event.get('stage_context', {})
        stage_context_section = ""
        if stage_context_info:
            stage_context_section = f"""
### 所属阶段目标（最高层级指导）
- **阶段名称**: {stage_context_info.get('stage_name', stage_name)}
- **阶段核心目标**: {stage_context_info.get('stage_goal', '推进主线发展')}
- **本事件对阶段的贡献**: {stage_context_info.get('contribution_to_stage', '服务于阶段目标')}
"""

        # 构建写作计划上下文
        writing_context = f"""
## 【写作计划上下文】本事件在整体故事中的作用

{stage_context_section}
### 所属重大事件
- **重大事件名称**: {major_event.get('name')}
- **重大事件目标**: {major_event.get('main_goal')}
- **在重大事件中的贡献**: {medium_event.get('contribution_to_major', '推进情节')}

### 关键情绪节拍（需要铺垫的情绪）
{chr(10).join(f'- {beat}' for beat in medium_event.get('key_emotional_beats', [])) if medium_event.get('key_emotional_beats') else '- 无特定情绪节拍要求'}
"""

        # 添加情绪推导信息（如果有）
        if 'emotional_derivation' in medium_event:
            ed = medium_event['emotional_derivation']
            writing_context += f"""
### 情绪推导信息
- **触发事件**: {ed.get('trigger_event', '未定义')}
- **情绪反应**: {ed.get('emotional_response', '未定义')}
- **情绪节拍**: {', '.join(ed.get('emotional_beats', []))}
"""

        # 添加阶段弧线对齐信息（如果有）
        if 'alignment_with_stage_arc' in medium_event:
            aln = medium_event['alignment_with_stage_arc']
            writing_context += f"""
### 在阶段情绪弧线中的位置
- **位置**: {aln.get('position_in_arc', '未定义')}
- **对阶段情绪的贡献**: {aln.get('contribution_to_stage_emotion', '未定义')}
"""

        # 🔥 新增：构建综合场景上下文（角色、世界观、重大事件）
        comprehensive_scene_context = self._build_comprehensive_scene_context(
            global_novel_data, major_event, medium_event, stage_name
        )

        chapter_events_prompt = f"""
# 任务：中型事件"章节分解" - 服务于中型事件目标
{consistency_block}
你需要将一个多章的中型事件分解为具体的章节事件。

{writing_context}

{comprehensive_scene_context}

## 当前中型事件信息
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event.get('name')}
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
{special_emotional_context}

## 分解要求
{chapter_instruction}
"""
        
        chapter_events_result = self.api_client.generate_content_with_retry(
            content_type="medium_event_decomposition",
            user_prompt=chapter_events_prompt,
            purpose=f"分解中型事件'{medium_event.get('name')}'为章节事件"
        )
        
        if not chapter_events_result:
            self.logger.error(f"  ❌ 生成章节事件失败，返回None")
            return None
        
        # 验证返回的数据结构
        if "chapter_events" not in chapter_events_result:
            self.logger.error(f"  ⚠️ API返回数据缺少'chapter_events'字段: {list(chapter_events_result.keys())}")
            self.logger.error(f"  完整数据: {chapter_events_result}")
            return None
        
        chapter_events = chapter_events_result.get("chapter_events", [])
        if not chapter_events:
            self.logger.error(f"  ⚠️ chapter_events列表为空")
            return None
        
        self.logger.info(f"  ✅ 成功生成{len(chapter_events)}个章节事件")
        
        # 第二步：为每个章节事件分解为场景事件
        scene_structured_chapters = []
        previous_chapter_scenes = None
        
        for idx, chapter_event in enumerate(chapter_events):
            # 验证章节事件数据结构
            if not isinstance(chapter_event, dict):
                self.logger.error(f"  ❌ 章节事件{idx+1}不是字典类型: {type(chapter_event)}")
                continue
            
            if 'name' not in chapter_event:
                self.logger.error(f"  ❌ 章节事件{idx+1}缺少'name'字段，包含的键: {list(chapter_event.keys())}")
                self.logger.error(f"  完整数据: {chapter_event}")
                continue
            
            # 确保chapter_event有必需的字段
            event_name = chapter_event.get('name') or f"章节事件_{idx+1}"
            chapter_range = chapter_event.get('chapter_range', '未知')
            main_goal = chapter_event.get('main_goal', '未指定目标')
            
            self.logger.info(f"    📋 处理章节事件: {event_name} ({chapter_range})")
            
            # 构建前一章场景的上下文
            previous_context = ""
            if previous_chapter_scenes:
                prev_scenes = previous_chapter_scenes.get("scene_structure", {}).get("scenes", [])
                previous_context = f"""
## ⚠️ 重要：前一章场景回顾 (避免重复)
这是前一章的第{idx}个章节事件。在为本章设计场景时，**严禁重复**以下场景。
"""

            # 🔥 新增：构建综合场景上下文（角色、世界观、重大事件）
            comprehensive_scene_context = self._build_comprehensive_scene_context(
                global_novel_data, major_event, medium_event
            )

            scene_structure_prompt = f"""
# 任务：章节事件"场景结构构建"
你需要为一个章节事件设计完整的场景结构。

## 当前章节事件信息
- **章节事件名称**: {event_name}
- **章节范围**: {chapter_range}
- **章节目标**: {main_goal}
{previous_context}

{comprehensive_scene_context}

## 场景构建要求
请为这个章节设计4-6个场景事件，形成完整的起承转合戏剧结构。

## 【强制要求】情绪强度分布
你**必须**为每个场景设置不同的情绪强度：low/medium/high
- **起**（开篇场景）: low
- **承**（发展场景）: medium
- **转**（高潮场景）: high
- **合**（收尾场景）: medium → low

## 输出格式
返回JSON格式，包含 scene_structure.scenes[]

每个场景必须包含以下完整字段：
- **name**（必填，4-12字，有画面感）
- sequence, role（起/承/转/合）, position, description, purpose
- key_actions[], emotional_intensity（low/medium/high）, emotional_impact
- dialogue_highlights[], conflict_point, sensory_details, transition_to_next, estimated_word_count, chapter_hook
"""
            
            scene_result = self.api_client.generate_content_with_retry(
                content_type="chapter_event_design",
                user_prompt=scene_structure_prompt,
                purpose=f"为章节事件'{event_name}'构建场景结构"
            )
            
            if scene_result:
                scene_structured_chapters.append(scene_result)
            else:
                scene_structured_chapters.append(chapter_event)
        
        if scene_structured_chapters:
            chapter_events_result["chapter_events"] = scene_structured_chapters
        
        return chapter_events_result
    
    def _decompose_direct_to_scene(self, medium_event: Dict, major_event: Dict,
                                  stage_name: str, novel_title: str, novel_synopsis: str,
                                  creative_seed: Dict, overall_stage_plan: Dict,
                                  global_novel_data: Dict,
                                  consistency_guidance: Optional[str] = None) -> Optional[Dict]:
        """直接将中型事件分解为场景序列"""
        chapter_range = medium_event.get('chapter_range', '0-0')
        start_ch, end_ch = parse_chapter_range(chapter_range)
        chapter_count = end_ch - start_ch + 1
        
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
## 已确定的事实 (一致性铁律 - 必须严格遵守)
{consistency_guidance}
"""
        
        # 构建详细的章节分配说明
        chapter_breakdown = ""
        for i in range(chapter_count):
            chapter_num = start_ch + i
            chapter_breakdown += f"- 第{chapter_num}章: 需要完成中型事件目标的{['起始','发展','高潮','收尾'][min(i, 3)]}部分\n"

        # 获取阶段上下文（如果有）
        stage_context_info = medium_event.get('stage_context', {})
        stage_context_section = ""
        if stage_context_info:
            stage_context_section = f"""
### 所属阶段目标（最高层级指导）
- **阶段名称**: {stage_context_info.get('stage_name', stage_name)}
- **阶段核心目标**: {stage_context_info.get('stage_goal', '推进主线发展')}
- **本事件对阶段的贡献**: {stage_context_info.get('contribution_to_stage', '服务于阶段目标')}
"""

        # 构建写作计划上下文
        writing_context = f"""
## 【写作计划上下文】本事件在整体故事中的作用

{stage_context_section}
### 所属重大事件
- **重大事件名称**: {major_event.get('name')}
- **重大事件目标**: {major_event.get('main_goal')}
- **在重大事件中的贡献**: {medium_event.get('contribution_to_major', '推进情节')}

### 关键情绪节拍（需要铺垫的情绪）
{chr(10).join(f'- {beat}' for beat in medium_event.get('key_emotional_beats', [])) if medium_event.get('key_emotional_beats') else '- 无特定情绪节拍要求'}
"""

        # 添加情绪推导信息（如果有）
        if 'emotional_derivation' in medium_event:
            ed = medium_event['emotional_derivation']
            writing_context += f"""
### 情绪推导信息
- **触发事件**: {ed.get('trigger_event', '未定义')}
- **情绪反应**: {ed.get('emotional_response', '未定义')}
- **情绪节拍**: {', '.join(ed.get('emotional_beats', []))}
"""

        # 添加阶段弧线对齐信息（如果有）
        if 'alignment_with_stage_arc' in medium_event:
            aln = medium_event['alignment_with_stage_arc']
            writing_context += f"""
### 在阶段情绪弧线中的位置
- **位置**: {aln.get('position_in_arc', '未定义')}
- **对阶段情绪的贡献**: {aln.get('contribution_to_stage_emotion', '未定义')}
"""

        # 🔥 新增：收集当前中型事件中的特殊情感事件
        special_emotional_context = ""
        special_events = medium_event.get("special_emotional_events", [])
        if special_events:
            # 按章节分组特殊情感事件
            events_by_chapter = {}
            for se in special_events:
                target_ch = se.get("target_chapter")
                if target_ch:
                    if target_ch not in events_by_chapter:
                        events_by_chapter[target_ch] = []
                    events_by_chapter[target_ch].append(se)

            if events_by_chapter:
                special_emotional_context = "\n## 【情感融合要求】特殊情感事件\n"
                for chapter_num, events in sorted(events_by_chapter.items()):
                    if start_ch <= chapter_num <= end_ch:  # 只包含在中型事件范围内的章节
                        special_emotional_context += f"\n### 第{chapter_num}章需要融合的情感事件：\n"
                        for se in events:
                            special_emotional_context += f"- **{se.get('name')}**: {se.get('purpose', '')}\n"
                            special_emotional_context += f"  - 情感基调: {se.get('emotional_tone', '')}\n"
                            special_emotional_context += f"  - 关键元素: {', '.join(se.get('key_elements', []))}\n"
                            if se.get('context_hint'):
                                special_emotional_context += f"  - 上下文提示: {se.get('context_hint')}\n"

                special_emotional_context += "\n**重要**：请将这些情感元素自然地融入到对应章节的场景中，让情感发展与情节推进有机结合。\n"

        # 🔥 新增：构建综合场景上下文（角色、世界观、重大事件）
        comprehensive_scene_context = self._build_comprehensive_scene_context(
            global_novel_data, major_event, medium_event, stage_name
        )

        prompt = f"""
# 任务：中型事件"多章场景构建"
{consistency_block}
你需要为一个跨{chapter_count}章的中型事件设计详细的场景事件序列。

{writing_context}

{comprehensive_scene_context}

## 当前中型事件信息
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
{special_emotional_context}

## 章节分配要求
{chapter_breakdown}

## 【强制要求】情绪强度分布
你**必须**为每个场景设置不同的情绪强度：low/medium/high

每章的结构要求：
1. **第1章** (起始章): low → medium → high → medium
2. **中间章节** (发展章): medium → medium → high → medium
3. **最后一章** (收尾章): medium → medium → high → low

## 输出格式
返回JSON格式，包含：name, chapter_range, decomposition_type: "direct_scene", chapter_breakdown.overall_arc, scene_sequences[]

每个场景必须包含name（4-12字）、sequence、role、position、description、purpose、key_actions[]、emotional_intensity、emotional_impact、dialogue_highlights[]、conflict_point、sensory_details、transition_to_next、estimated_word_count、chapter_hook
"""
        
        result = self.api_client.generate_content_with_retry(
            content_type="multi_chapter_scene_design",
            user_prompt=prompt,
            purpose=f"为中型事件'{medium_event.get('name')}'构建多章场景序列"
        )
        
        return result
    
    def _decompose_with_ai_free_choice(self, medium_event: Dict, major_event: Dict,
                                      stage_name: str, novel_title: str, novel_synopsis: str,
                                      creative_seed: Dict, overall_stage_plan: Dict,
                                      global_novel_data: Dict,
                                      consistency_guidance: Optional[str] = None) -> Optional[Dict]:
        """
        让AI自由决策中型事件的最优分解结构
        
        不强制规定章节数和场景数的对应关系，让AI根据具体情况灵活决定：
        - 哪些场景可以合并到一章内
        - 哪些场景需要扩展成多个章节
        - 每章应该包含多少个场景
        - 如何在{chapter_count}章内形成连贯的叙事流
        
        Args:
            medium_event: 中型事件
            major_event: 所属重大事件
            其他参数同上
            
        Returns:
            AI自由决策后的分解结果
        """
        chapter_range = medium_event.get('chapter_range', '1-1')
        start_ch, end_ch = parse_chapter_range(chapter_range)
        chapter_count = end_ch - start_ch + 1
        
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
## 已确定的事实 (一致性铁律)
{consistency_guidance}
"""

        # 获取阶段上下文（如果有）
        stage_context_info = medium_event.get('stage_context', {})
        stage_context_section = ""
        if stage_context_info:
            stage_context_section = f"""
### 所属阶段目标（最高层级指导）
- **阶段名称**: {stage_context_info.get('stage_name', stage_name)}
- **阶段核心目标**: {stage_context_info.get('stage_goal', '推进主线发展')}
- **本事件对阶段的贡献**: {stage_context_info.get('contribution_to_stage', '服务于阶段目标')}
"""

        # 构建写作计划上下文
        writing_context = f"""
## 【写作计划上下文】本事件在整体故事中的作用

{stage_context_section}
### 所属重大事件
- **重大事件名称**: {major_event.get('name')}
- **重大事件目标**: {major_event.get('main_goal')}
- **在重大事件中的贡献**: {medium_event.get('contribution_to_major', '推进情节')}

### 关键情绪节拍（需要铺垫的情绪）
{chr(10).join(f'- {beat}' for beat in medium_event.get('key_emotional_beats', [])) if medium_event.get('key_emotional_beats') else '- 无特定情绪节拍要求'}
"""

        # 添加情绪推导信息（如果有）
        if 'emotional_derivation' in medium_event:
            ed = medium_event['emotional_derivation']
            writing_context += f"""
### 情绪推导信息
- **触发事件**: {ed.get('trigger_event', '未定义')}
- **情绪反应**: {ed.get('emotional_response', '未定义')}
- **情绪节拍**: {', '.join(ed.get('emotional_beats', []))}
"""

        # 添加阶段弧线对齐信息（如果有）
        if 'alignment_with_stage_arc' in medium_event:
            aln = medium_event['alignment_with_stage_arc']
            writing_context += f"""
### 在阶段情绪弧线中的位置
- **位置**: {aln.get('position_in_arc', '未定义')}
- **对阶段情绪的贡献**: {aln.get('contribution_to_stage_emotion', '未定义')}
"""

        # 🔥 新增：构建综合场景上下文（角色、世界观、重大事件）
        comprehensive_scene_context = self._build_comprehensive_scene_context(
            global_novel_data, major_event, medium_event, stage_name
        )

        prompt = f"""
# 任务：中型事件"智能场景分解" - AI自由决策最优结构
{consistency_block}
你需要为一个中型事件设计最优的场景分解结构。

{writing_context}

{comprehensive_scene_context}

## 当前中型事件信息
- **中型事件名称**: {medium_event.get('name')}
- **章节范围**: {chapter_range} (共{chapter_count}章)
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **情绪强度**: {medium_event.get('emotional_intensity', 'medium')}

## 【核心原则】灵活决策，避免死板

你有完全的自由来决定如何在这个{chapter_count}章的范围内安排场景。请根据以下考虑做出最佳决策：

### 决策考虑因素：
1. **目标复杂度**：如果目标简单，可以一章完成；如果复杂，需要多章展开
2. **情感弧线**：情绪需要铺垫和发展，不要急躁
3. **节奏控制**：读者需要呼吸的空间，不要信息过载
4. **叙事连贯**：场景之间要有自然的过渡和递进

### 你需要决策：
- **是否需要分解为章节事件？**
  - 如果{chapter_count}章的内容相对独立，建议分解为章节事件
  - 如果{chapter_count}章讲述的是一个连续的情节，可以不分解，直接生成场景序列
  
- **每章包含多少个场景？**
  - 可以根据需要灵活调整（3-8个场景都是合理的）
  - 重要的转折章可以有更多场景
  - 过渡章可以有较少场景
  
- **哪些场景可以合并？哪些需要扩展？**
  - 相关的场景可以合并到一章内
  - 重要的场景可以扩展成多个章节
  - 根据叙事需要自由决定

### 【唯一约束】避免重复
- **严禁在不同章节使用相同或相似的场景内容**
- 每个场景都应该有独特的进展和意义
- 章节之间要有明确的递进关系

## 【强制要求】情绪强度分布

你**必须**为每个场景设置不同的情绪强度：low/medium/high

每章的结构要求：
1. **起始章**: low → medium → high → medium（起承转合）
2. **中间章节**: medium → medium → high → medium（持续发展）
3. **收尾章**: medium → medium → high → low（高潮收束）

场景之间要有流畅的过渡，形成完整的叙事流。最后一个场景必须包含吸引读者继续阅读的钩子。

## 输出格式（根据你的决策选择合适的格式）

### 【强制要求】每个场景必须包含以下完整字段：

**基础字段**：
- **name**（必填，4-12字，有画面感）: 如"林中分赃"、"师兄拦路"
- **sequence**: 场景序号
- **role**: 场景在起承转合中的角色（起/承/转/合）
- **position**: 场景位置描述
- **description**: 场景详细描述（100-200字）
- **purpose**: 场景在故事中的作用

**动作与情感**：
- **key_actions[]**: 关键动作列表（3-5个具体动作）
- **emotional_intensity**: 情绪强度（low/medium/high）
- **emotional_impact**: 情感冲击描述

**对话与冲突**：
- **dialogue_highlights[]**: 对话亮点（2-3句精彩对话）
- **conflict_point**: 场景中的冲突点

**细节与过渡**：
- **sensory_details**: 感官细节（视觉、听觉、触觉等）
- **transition_to_next**: 如何过渡到下一个场景
- **estimated_word_count**: 预计字数
- **chapter_hook**: 场景结尾钩子（吸引读者继续阅读的关键点，最后一章的最后一个场景必填）

### 方案A：直接生成场景序列（连续情节）
返回：name, chapter_range, decomposition_type: "ai_free_direct_scenes", ai_decision, chapter_breakdown.overall_arc, scene_sequences[].scene_events[]

### 方案B：分解为章节事件（章节相对独立）
返回：name, chapter_range, decomposition_type: "ai_free_chapter_events", ai_decision, chapter_events[].scene_structure.scenes[]

### 方案C：混合方案（自由设计）
确保包含：scene_events或scenes字段、每个场景包含上述所有强制字段、明确的章节范围对应关系

请根据你的专业判断，选择或创造最适合这个中型事件的结构。
"""
        
        result = self.api_client.generate_content_with_retry(
            content_type="medium_event_decomposition",  # 使用已支持的内容类型
            user_prompt=prompt,
            purpose=f"AI自由决策中型事件'{medium_event.get('name')}'的最优结构"
        )
        
        if result:
            self.logger.info(f"      ✅ AI成功自由决策并生成了场景结构")
            # 记录AI的决策原因（如果有）
            if "ai_decision" in result:
                self.logger.info(f"      📝 AI决策原因: {result['ai_decision']}")
        else:
            self.logger.error(f"      ❌ AI自由决策分解失败")
        
        return result
    
    def _decompose_single_chapter_with_complete_arc(self, medium_event: Dict, major_event: Dict,
                                                    stage_name: str, novel_title: str, novel_synopsis: str,
                                                    creative_seed: Dict, overall_stage_plan: Dict,
                                                    global_novel_data: Dict,
                                                    consistency_guidance: Optional[str] = None,
                                                    previous_chapters_scenes: Optional[Dict] = None) -> Optional[Dict]:
        """
        为单章中型事件生成完整的起承转合场景

        这个方法专门处理只有1章的中型事件，直接生成一个完整的起承转合场景序列，
        确保单章也能形成完整的戏剧结构。

        Args:
            medium_event: 单章中型事件
            major_event: 所属重大事件
            其他参数同上
            previous_chapters_scenes: 前几章已完成场景信息（用于避免重复）

        Returns:
            包含完整场景序列的单章事件
        """
        chapter_range = medium_event.get('chapter_range', '1-1')
        start_ch, _ = parse_chapter_range(chapter_range)
        
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
## 已确定的事实 (一致性铁律 - 必须严格遵守)
{consistency_guidance}
"""
        
        # 🔥 新增：收集当前中型事件中的特殊情感事件
        special_emotional_context = ""
        special_events = medium_event.get("special_emotional_events", [])
        if special_events:
            # 只包含目标章节为当前章节的事件
            current_chapter_events = [se for se in special_events if se.get("target_chapter") == start_ch]
            
            if current_chapter_events:
                special_emotional_context = "\n## 【情感融合要求】本章需要融合的情感事件：\n"
                for se in current_chapter_events:
                    special_emotional_context += f"\n### {se.get('name')}\n"
                    special_emotional_context += f"- **目的**: {se.get('purpose', '')}\n"
                    special_emotional_context += f"- **情感基调**: {se.get('emotional_tone', '')}\n"
                    special_emotional_context += f"- **关键元素**: {', '.join(se.get('key_elements', []))}\n"
                    if se.get('context_hint'):
                        special_emotional_context += f"- **上下文提示**: {se.get('context_hint')}\n"
                
                special_emotional_context += "\n**重要**：请将这些情感元素自然地融入到本章的场景中，让情感发展与情节推进有机结合。\n"
        
        # 获取阶段上下文（如果有）
        stage_context_info = medium_event.get('stage_context', {})
        stage_context_section = ""
        if stage_context_info:
            stage_context_section = f"""
### 所属阶段目标（最高层级指导）
- **阶段名称**: {stage_context_info.get('stage_name', stage_name)}
- **阶段核心目标**: {stage_context_info.get('stage_goal', '推进主线发展')}
- **本事件对阶段的贡献**: {stage_context_info.get('contribution_to_stage', '服务于阶段目标')}
"""

        # 构建写作计划上下文
        writing_context = f"""
## 【写作计划上下文】本事件在整体故事中的作用

{stage_context_section}
### 所属重大事件
- **重大事件名称**: {major_event.get('name')}
- **重大事件目标**: {major_event.get('main_goal')}
- **在重大事件中的贡献**: {medium_event.get('contribution_to_major', '推进情节')}

### 关键情绪节拍（需要铺垫的情绪）
{chr(10).join(f'- {beat}' for beat in medium_event.get('key_emotional_beats', [])) if medium_event.get('key_emotional_beats') else '- 无特定情绪节拍要求'}

### 情绪推导信息
"""
        # 添加情绪推导信息（如果有）
        if 'emotional_derivation' in medium_event:
            ed = medium_event['emotional_derivation']
            writing_context += f"""- **触发事件**: {ed.get('trigger_event', '未定义')}
- **情绪反应**: {ed.get('emotional_response', '未定义')}
- **情绪节拍**: {', '.join(ed.get('emotional_beats', []))}
"""

        # 添加阶段弧线对齐信息（如果有）
        if 'alignment_with_stage_arc' in medium_event:
            aln = medium_event['alignment_with_stage_arc']
            writing_context += f"""
### 在阶段情绪弧线中的位置
- **位置**: {aln.get('position_in_arc', '未定义')}
- **对阶段情绪的贡献**: {aln.get('contribution_to_stage_emotion', '未定义')}
"""

        # 🔥 新增：构建综合场景上下文（角色、世界观、重大事件）
        comprehensive_scene_context = self._build_comprehensive_scene_context(
            global_novel_data, major_event, medium_event, stage_name
        )

        # 🔥 新增：构建前几章场景概要（用于避免重复）
        previous_chapters_section = ""
        if previous_chapters_scenes:
            previous_chapters_section = self._format_previous_chapters_scenes_for_scene_generation(
                previous_chapters_scenes, start_ch
            )

        prompt = f"""
# 任务：单章中型事件"完整起承转合场景构建"
{consistency_block}
你需要为一个单章中型事件设计完整的起承转合场景结构。

{writing_context}

{comprehensive_scene_context}

## 当前中型事件信息
- **中型事件名称**: {medium_event.get('name')}
- **章节范围**: {chapter_range}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **情绪强度**: {medium_event.get('emotional_intensity', 'medium')}
{special_emotional_context}
{previous_chapters_section}

## 【关键要求】完整的起承转合结构
由于只有1章，**必须**在一个章节内形成完整的起承转合戏剧结构：
1. **起（开篇场景）**: 引入本章核心冲突或情境，吸引读者注意力
2. **承（发展场景）**: 深化冲突，展开情节，增加复杂性
3. **转（高潮场景）**: 达到本章的情感或冲突顶点，形成转折
4. **合（收尾场景）**: 解决本章冲突，为下一章埋下伏笔

## 场景设计要求
- 总共4-6个场景，每个场景对应起承转合的某个阶段
- 每个场景都要有明确的情绪强度：low/medium/high
- 情绪强度应该呈现：low → medium → high → medium 的波动曲线
- 场景之间要有流畅的过渡，形成完整的叙事流
- 最后一个场景必须包含吸引读者继续阅读的钩子

## 输出格式要求
返回JSON格式，包含以下结构：
- name, chapter_range, decomposition_type: "single_chapter_complete_arc"
- chapter_breakdown.overall_arc: 整体弧线描述
- scene_sequences[].scene_events[]: 场景数组（4-6个场景）

每个场景必须包含：
- **name**（必填，4-12字，有画面感）: 如"林中分赃"、"师兄拦路"
- sequence, role（起/承/转/合）, position, description, purpose
- key_actions[], emotional_intensity（low/medium/high）, emotional_impact
- dialogue_highlights[], conflict_point, sensory_details, transition_to_next, estimated_word_count, chapter_hook
"""
        
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_event_design",  # 使用已支持的内容类型
            user_prompt=prompt,
            purpose=f"为单章中型事件'{medium_event.get('name')}'生成完整起承转合场景"
        )

        if result:
            # 🆕 兼容多种返回格式
            # 格式1: scene_sequences[].scene_events[] (新格式)
            # 格式2: scene_structure.scenes[] (旧格式)
            scenes = []

            if 'scene_sequences' in result and result['scene_sequences']:
                scenes = result['scene_sequences'][0].get('scene_events', [])
                self.logger.info(f"      ✅ 成功为单章事件生成完整起承转合场景（{len(scenes)}个场景）")
            elif 'scene_structure' in result and result['scene_structure']:
                scenes = result['scene_structure'].get('scenes', [])
                # 转换为新格式
                result['scene_sequences'] = [{
                    'scene_events': scenes
                }]
                self.logger.info(f"      ✅ 成功为单章事件生成完整起承转合场景（旧格式，{len(scenes)}个场景）")
            else:
                self.logger.warning(f"      ⚠️ API返回数据格式不符合预期")
                self.logger.info(f"      📋 返回的键: {list(result.keys())}")
                self.logger.info(f"      📋 完整数据: {json.dumps(result, ensure_ascii=False)[:500]}")
        else:
            self.logger.error(f"      ❌ 生成单章完整场景失败，API返回为空")

        return result

    def _format_previous_chapters_scenes_for_scene_generation(self, previous_chapters_scenes: Dict,
                                                           current_chapter: int) -> str:
        """
        格式化前几章已完成场景概要（专门用于场景生成，避免重复）

        Args:
            previous_chapters_scenes: 前几章场景数据
            current_chapter: 当前章节号

        Returns:
            格式化后的前几章场景概要文本
        """
        if not previous_chapters_scenes:
            return ""

        lines = []
        lines.append("## ⚠️ 【禁止重复】前几章已完成场景概要")
        lines.append("")
        lines.append("以下是前几章已经发生的场景事件。**本章严禁重复这些场景内容**！")
        lines.append("")
        lines.append("请仔细阅读每个场景的【关键动作】和【核心目标】，确保新场景不与已有场景重叠。")
        lines.append("")

        # 按章节分组展示
        scenes_by_chapter = previous_chapters_scenes.get("scenes_by_chapter", {})
        previous_chapters = sorted([int(ch) for ch in scenes_by_chapter.keys() if int(ch) < current_chapter])

        for ch in previous_chapters:
            scenes = scenes_by_chapter.get(str(ch), [])
            if not scenes:
                continue

            lines.append(f"### 第{ch}章已完成场景（共{len(scenes)}个）:")
            lines.append("")

            for i, scene in enumerate(scenes, 1):
                lines.append(f"**场景{i}：{scene.get('name', '未命名')}**")
                lines.append(f"  - 位置：{scene.get('position', '未知')}")
                lines.append(f"  - 目标：{scene.get('purpose', '未指定')}")

                # 提取关键动作
                key_actions = scene.get("key_actions", [])
                if key_actions:
                    lines.append(f"  - 已完成动作：")
                    for action in key_actions[:3]:  # 最多显示3个动作
                        lines.append(f"    • {action}")
                    if len(key_actions) > 3:
                        lines.append(f"    • ...等共{len(key_actions)}个动作")

                lines.append("")

        if not previous_chapters:
            lines.append("（无前几章场景数据）")
            lines.append("")

        # 添加明确的禁止重复指令
        lines.append("## 【绝对要求】场景设计时必须遵循以下原则：")
        lines.append("1. **严禁重复**：不能设计与前几章相同或高度相似的场景")
        lines.append("2. **递进关系**：新场景应该是已有情节的延续和发展，而非重新开始")
        lines.append("3. **承接上一章**：如果上一章结尾是A状态，本章应该从A状态的延续开始")
        lines.append("")

        return "\n".join(lines)

    def decompose_multiple_major_events(self, major_event_skeletons: List[Dict],
                                       stage_name: str, stage_range: str,
                                       novel_title: str, novel_synopsis: str,
                                       creative_seed: Dict, overall_stage_plan: Dict,
                                       global_novel_data: Dict,
                                       stage_emotional_arc: Optional[Dict] = None,
                                       overall_emotional_blueprint: Optional[Dict] = None) -> List[Dict]:
        """
        批量分解多个重大事件为中型事件（优化版）
        
        与逐个分解相比的优势：
        1. 减少API调用次数（一次调用分解多个事件）
        2. AI能更好地把握多个事件之间的连贯性
        3. 更好的情节一致性，因为AI能看到全貌
        
        Args:
            major_event_skeletons: 重大事件骨架列表（2-4个事件）
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            novel_title: 小说标题
            novel_synopsis: 小说简介
            creative_seed: 创意种子
            overall_stage_plan: 整体阶段计划
            global_novel_data: 全局小说数据
            stage_emotional_arc: 阶段情绪弧线
            overall_emotional_blueprint: 全书情绪蓝图
            
        Returns:
            分解后的重大事件列表
        """
        if not major_event_skeletons:
            return []
        
        # 如果只有一个事件，回退到单个分解
        if len(major_event_skeletons) == 1:
            result = self.decompose_major_event(
                major_event_skeleton=major_event_skeletons[0],
                stage_name=stage_name,
                stage_range=stage_range,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                creative_seed=creative_seed,
                overall_stage_plan=overall_stage_plan,
                global_novel_data=global_novel_data,
                stage_emotional_arc=stage_emotional_arc,
                overall_emotional_blueprint=overall_emotional_blueprint
            )
            return [result] if result else []
        
        try:
            # 构建顶层上下文
            top_level_context_block = self._build_top_level_context(
                creative_seed, global_novel_data, overall_stage_plan, stage_name
            )
            
            # 构建批量分解的prompt
            prompt = self._build_batch_decomposition_prompt(
                major_event_skeletons, stage_name, stage_range, top_level_context_block,
                stage_emotional_arc, overall_emotional_blueprint
            )
            
            self.logger.info(f"  🚀 批量分解 {len(major_event_skeletons)} 个重大事件: " + 
                           ", ".join([s.get('name', '未命名') for s in major_event_skeletons]))
            
            # 调用API生成（使用更强的模型）
            result = self.api_client.generate_content_with_retry(
                content_type="batch_major_event_decomposition",
                user_prompt=prompt,
                purpose=f"批量解剖{len(major_event_skeletons)}个重大事件"
            )
            
            if not result:
                self.logger.warning("  ⚠️ 批量分解失败，回退到逐个分解")
                return self._fallback_to_individual_decomposition(
                    major_event_skeletons, stage_name, stage_range,
                    novel_title, novel_synopsis, creative_seed,
                    overall_stage_plan, global_novel_data,
                    stage_emotional_arc, overall_emotional_blueprint
                )
            
            # 解析返回结果
            decomposed_events = result.get("decomposed_events", [])
            
            if not decomposed_events or len(decomposed_events) != len(major_event_skeletons):
                self.logger.warning(f"  ⚠️ 批量分解返回事件数量不匹配: 期望{len(major_event_skeletons)}, 实际{len(decomposed_events)}")
                return self._fallback_to_individual_decomposition(
                    major_event_skeletons, stage_name, stage_range,
                    novel_title, novel_synopsis, creative_seed,
                    overall_stage_plan, global_novel_data,
                    stage_emotional_arc, overall_emotional_blueprint
                )
            
            self.logger.info(f"  ✅ 批量分解成功: {len(decomposed_events)} 个事件")
            
            # 验证并修正每个事件的章节范围
            for i, (event, skeleton) in enumerate(zip(decomposed_events, major_event_skeletons)):
                if event:
                    event["chapter_range"] = skeleton.get("chapter_range", event.get("chapter_range", ""))
            
            return decomposed_events
            
        except Exception as e:
            self.logger.error(f"  ❌ 批量分解出错: {e}")
            return self._fallback_to_individual_decomposition(
                major_event_skeletons, stage_name, stage_range,
                novel_title, novel_synopsis, creative_seed,
                overall_stage_plan, global_novel_data,
                stage_emotional_arc, overall_emotional_blueprint
            )
    
    def _fallback_to_individual_decomposition(self, major_event_skeletons: List[Dict],
                                             stage_name: str, stage_range: str,
                                             novel_title: str, novel_synopsis: str,
                                             creative_seed: Dict, overall_stage_plan: Dict,
                                             global_novel_data: Dict,
                                             stage_emotional_arc: Optional[Dict] = None,
                                             overall_emotional_blueprint: Optional[Dict] = None) -> List[Dict]:
        """批量分解失败时的回退：逐个分解"""
        self.logger.info("  🔄 回退到逐个分解模式...")
        results = []
        
        for skeleton in major_event_skeletons:
            try:
                result = self.decompose_major_event(
                    major_event_skeleton=skeleton,
                    stage_name=stage_name,
                    stage_range=stage_range,
                    novel_title=novel_title,
                    novel_synopsis=novel_synopsis,
                    creative_seed=creative_seed,
                    overall_stage_plan=overall_stage_plan,
                    global_novel_data=global_novel_data,
                    stage_emotional_arc=stage_emotional_arc,
                    overall_emotional_blueprint=overall_emotional_blueprint
                )
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"    ❌ 分解事件 '{skeleton.get('name', '未命名')}' 失败: {e}")
        
        return results
    
    def _build_batch_decomposition_prompt(self, major_event_skeletons: List[Dict],
                                         stage_name: str, stage_range: str,
                                         top_level_context: str,
                                         stage_emotional_arc: Optional[Dict] = None,
                                         overall_emotional_blueprint: Optional[Dict] = None) -> str:
        """构建批量事件分解的prompt"""
        
        # 构建事件列表
        events_list = []
        for i, skeleton in enumerate(major_event_skeletons, 1):
            events_list.append(f"""
### 事件{i}: {skeleton.get('name')}
- **章节范围**: {skeleton.get('chapter_range')}
- **核心目标**: {skeleton.get('main_goal', '推进主情节')}
- **在阶段弧线中的角色**: {skeleton.get('role_in_stage_arc', '未定义')}
""")
        
        events_str = "\n".join(events_list)
        
        # 构建情绪弧线指导
        emotional_guidance = ""
        if stage_emotional_arc:
            emotional_guidance = f"""
## 阶段情绪弧线指导（战略级指导）
- **阶段起点情绪**: {stage_emotional_arc.get('start_emotion', '未定义')}
- **阶段终点情绪**: {stage_emotional_arc.get('end_emotion', '未定义')}
- **阶段情绪发展**: {stage_emotional_arc.get('description', '未定义')}

**关键要求**: 
1. 每个重大事件的情绪必须服务于阶段整体情绪弧线
2. 事件之间情绪转换要自然流畅，不能突兀
3. 后一个事件的情绪起点应该承接前一个事件的情绪终点
"""
        
        # 构建情感光谱指导
        emotional_spectrum_guidance = ""
        if overall_emotional_blueprint and "emotional_spectrum" in overall_emotional_blueprint:
            spectrum = overall_emotional_blueprint.get("emotional_spectrum", [])
            if spectrum:
                emotional_spectrum_guidance = f"""
## 全书情感光谱参考
核心情感驱动力: {', '.join(spectrum)}

这是本小说的情感底色，所有情绪发展都应该与之呼应。
"""
        
        # 构建事件间连贯性要求
        continuity_requirements = """
## 事件间连贯性要求（关键）
1. **时间线连续**: 后一个事件必须紧接着前一个事件的时间线开始，不能跳跃
2. **情节承接**: 后一个事件必须知道前一个事件的结果状态，并在此基础上发展
3. **情绪连贯**: 事件之间的情绪转换要自然，形成整体的情绪弧线
4. **伏笔呼应**: 如果事件1埋下了伏笔，事件2或后续事件需要有所呼应或推进
5. **避免重复**: 不同事件之间不能有重复的情节设计
"""
        
        return f"""# 任务：批量重大事件"分形解剖"
你的任务是将多个宏观的"重大事件"，根据其在全书蓝图中的战略地位，**一次性分解**为具体的、可执行的【中型事件】。

{top_level_context}

{emotional_guidance}

{emotional_spectrum_guidance}

{continuity_requirements}

## 待分解的重大事件列表（共{len(major_event_skeletons)}个）
{events_str}

## 核心原则：从事件推导情绪（不是从情绪规划事件）

**正确的逻辑**:
1. **事件优先**: 首先规划每个重大事件"起承转合"应该发生什么事件
2. **情绪推导**: 基于发生的事件，推导主角/读者会感受到什么情绪
3. **情绪连贯**: 确保情绪发展符合阶段情绪弧线的方向，事件间情绪转换自然

**错误的做法**（严禁）:
- ❌ 先规定"要压抑"，再去找压抑的事件
- ❌ 情绪和事件割裂，没有因果联系
- ❌ 不同事件之间重复相似的情节设计

## 分解原则与规则 (必须严格遵守)
1. **目标继承与服务**: 每个【中型事件】都必须是为实现【所属重大事件核心目标】和【顶层战略背景】服务的。
2. **结构完整**: 每个重大事件内的中型事件必须构成服务于其目标的、逻辑连贯的"起、承、转、合"结构。
3. **【绝对覆盖指令】**: 所有中型事件的chapter_range必须完整且无缝地覆盖父级"重大事件"的整个章节范围。
4. **【🔥黄金三章特殊规则 - 整体式设计】**:
   - **当重大事件标记为is_golden_arc=true且章节范围为1-3章时**
   - **黄金三章是一个完整的整体，不需要内部分解为"起承转合"结构**
   - **该重大事件必须只包含一个中型事件**，覆盖全部1-3章
   - **严禁将黄金三章拆分为多个中型事件**
   - **composition中只有"起"包含这一个事件，"承、转、合"必须为空数组[]**
   - 黄金三章本身就是一个完整的开局叙事，不需要再用起承转合细分
   - 此中型事件的情节点数量要求：12-18个（3章 × 每章4-6个），自然形成完整节奏
5. **【🔥绝对禁止时间重叠】**: 每个中型事件必须紧接着上一个中型事件结束的地方开始，严禁重新描述前一个中型事件已经完成的情节。
6. **【事件间连贯】**: 不同重大事件之间也要保持时间线连续，后一个重大事件的第一个中型事件必须承接前一个重大事件的最后一个中型事件的结尾状态。

## 【🔥强制规则】情节点数量要求

每个中型事件的 plot_outline 必须严格遵循以下数量规则：

| 章节数 | 情节点数量 | 计算方式 |
|-------|----------|---------|
| 1章   | 4-6个    | 每章4-6个 |
| 2章   | 8-12个   | 每章4-6个 × 2 |
| 3章   | 12-18个  | 每章4-6个 × 3 |
| n章   | n×4 到 n×6个 | 每章4-6个 × n |

**⚠️ 这是硬性要求，不是建议！**
- 如果生成的情节点数量不足，将被判定为不合格
- 情节点数量宁多勿少（在范围内）
- 每个情节点必须是具体、可展开的内容，不能空洞

## 【重要】特殊情感事件设计原则

特殊情感事件不是独立的章节事件，而是**附着在中型事件上的情感元素**，用于深化角色关系、调整叙事节奏。

**关键要求**：
1. **附着到中型事件**：每个特殊情感事件必须明确附着到某个具体的中型事件
2. **指定目标章节**：如果中型事件跨越多章，必须明确特殊情感事件发生在哪一章
3. **不要分配chapter_range**：特殊情感事件不占用独立章节，只需要指定目标章节号
4. **提供融合线索**：给出情感基调、关键元素，让第二阶段的场景生成自然融合

## 输出格式: 严格遵守规则，返回包含所有事件的JSON对象

```json
{{
    "decomposed_events": [
        {{
            "name": "事件1名称",
            "type": "major_event",
            "role_in_stage_arc": "角色描述",
            "main_goal": "核心目标",
            "chapter_range": "章节范围",
            "composition": {{
                "起": [
                    {{
                        "name": "中型事件名",
                        "type": "medium_event",
                        "chapter_range": "string",
                        "main_goal": "目标",
                        "plot_outline": [
                            "情节点1：具体发生了什么",
                            "情节点2：然后发生了什么",
                            "情节点3：转折点",
                            "情节点4：高潮",
                            "情节点5：结尾"
                        ],
                        "description": "一句话概括",
                        "stage_context": {{
                            "stage_name": "{stage_name}",
                            "stage_goal": "阶段目标",
                            "contribution_to_stage": "贡献"
                        }},
                        "emotional_derivation": {{
                            "trigger_event": "触发事件",
                            "emotional_response": "情绪反应",
                            "emotional_intensity": "low/medium/high",
                            "emotional_beats": ["节拍1", "节拍2"]
                        }},
                        "alignment_with_stage_arc": {{
                            "position_in_arc": "起/承/转/合",
                            "contribution_to_stage_emotion": "贡献"
                        }},
                        "contribution_to_major": "对重大事件的贡献",
                        "special_emotional_events": [
                            {{
                                "name": "情感互动名称",
                                "target_chapter": 10,
                                "purpose": "目的",
                                "emotional_tone": "基调",
                                "key_elements": ["元素1", "元素2"],
                                "context_hint": "上下文提示"
                            }}
                        ]
                    }}
                ],
                "承": [],
                "转": [],
                "合": []
            }},
            "emotional_arc_summary": "情绪弧线总结"
        }},
        // 事件2、事件3... 同样结构
    ],
    "batch_coherence_analysis": "对整个批次事件连贯性的分析"
}}
```

注意：
1. 必须返回 **decomposed_events** 数组，包含所有{len(major_event_skeletons)}个事件
2. 事件顺序必须与输入顺序一致
3. 每个事件的 structure 与单个分解时相同
4. **batch_coherence_analysis** 字段简要说明这些事件之间如何保持连贯性
5. **🔥 plot_outline 数量强制规则**：必须严格遵守"每章4-6个情节点"的规则
6. 事件间的时间线必须连续，不能有任何跳跃或重复
"""