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
                            overall_emotional_blueprint: Optional[Dict] = None) -> Optional[Dict]:
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
                stage_emotional_arc, overall_emotional_blueprint
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
        # 收集所有中型事件
        all_medium_events = []
        composition = major_event.get("composition", {})
        for phase_events in composition.values():
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
                self.logger.warn(f"      ⚠️ 中型事件'{medium_event['name']}'分解失败，保留原始结构")
                decomposed_medium_events.append(medium_event)
        
        # 更新重大事件的composition
        major_event_copy = major_event.copy()
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
            self.logger.warn(f"构建顶层上下文时发生错误: {e}, 使用简化版上下文。")
            return "# 顶层战略背景\n简化版上下文"
    
    def _build_decomposition_prompt(self, major_event_skeleton: Dict,
                                   stage_name: str, top_level_context: str,
                                   stage_emotional_arc: Optional[Dict] = None,
                                   overall_emotional_blueprint: Optional[Dict] = None) -> str:
        """构建事件分解prompt（从事件推导情绪）"""
        
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

## 【重要】特殊情感事件设计原则

特殊情感事件不是独立的章节事件，而是**附着在中型事件上的情感元素**，用于深化角色关系、调整叙事节奏。

**关键要求**：
1. **附着到中型事件**：每个特殊情感事件必须明确附着到某个具体的中型事件
2. **指定目标章节**：如果中型事件跨越多章，必须明确特殊情感事件发生在哪一章
3. **不要分配chapter_range**：特殊情感事件不占用独立章节，只需要指定目标章节号
4. **提供融合线索**：给出情感基调、关键元素，让第二阶段的场景生成自然融合

## 输出格式: 严格遵守规则，返回包含'composition'字段的JSON对象
{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
    "main_goal": "{major_event_skeleton.get('main_goal')}",
    "chapter_range": "{major_event_skeleton.get('chapter_range')}",
    "composition": {{
        "起": [
            {{
                "name": "中型事件名",
                "type": "medium_event",
                "chapter_range": "string",
                "main_goal": "目标",
                "description": "事件描述",
                
                // === 从事件推导的情绪 ===
                "emotional_derivation": {{
                    "trigger_event": "触发这个情绪的具体事件描述",
                    "emotional_response": "基于事件，主角/读者自然的情绪反应",
                    "emotional_intensity": "low/medium/high",
                    "emotional_beats": ["情绪节拍1", "情绪节拍2"]
                }},
                
                // === 与阶段情绪弧线对齐 ===
                "alignment_with_stage_arc": {{
                    "position_in_arc": "起/承/转/合",
                    "contribution_to_stage_emotion": "这个事件如何推动阶段情绪发展"
                }},
                
                "contribution_to_major": "对重大事件的贡献",
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
    "emotional_arc_summary": "重大事件整体情绪弧线总结"
}}

注意：
1. emotional_derivation 和 alignment_with_stage_arc 是新增的必需字段
2. special_emotional_events 是中型事件的子字段，不是重大事件的顶级字段
3. 情绪必须从事件中自然推导，不能为了符合目标而强行编造
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
        
        chapter_events_prompt = f"""
# 任务：中型事件"章节分解" - 服务于中型事件目标
{consistency_block}
你需要将一个多章的中型事件分解为具体的章节事件。

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
            
            scene_structure_prompt = f"""
# 任务：章节事件"场景结构构建"
你需要为一个章节事件设计完整的场景结构。

## 当前章节事件信息
- **章节事件名称**: {event_name}
- **章节范围**: {chapter_range}
- **章节目标**: {main_goal}
{previous_context}

## 场景构建要求
请为这个章节设计4-6个场景事件，形成完整的戏剧结构。
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
        
        prompt = f"""
# 任务：中型事件"多章场景构建"
{consistency_block}
你需要为一个跨{chapter_count}章的中型事件设计详细的场景事件序列。

## 当前中型事件信息
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')}
- **事件核心目标**: {medium_event.get('main_goal')}
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
{{
    "name": "{medium_event.get('name')}",
    "chapter_range": "{medium_event.get('chapter_range')}",
    "decomposition_type": "direct_scene",
    "chapter_breakdown": {{
        "overall_arc": "整个中型事件的情节发展弧线"
    }},
    "scene_sequences": [
        {{
            "chapter_range": "{start_ch}-{start_ch}",
            "chapter_role": "起始章",
            "chapter_goal": "本章目标",
            "scene_events": [...]
        }}
    ]
}}
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
        
        prompt = f"""
# 任务：中型事件"智能场景分解" - AI自由决策最优结构
{consistency_block}
你需要为一个中型事件设计最优的场景分解结构。

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

## 输出格式（根据你的决策选择合适的格式）

### 方案A：不分解章节，直接生成场景序列
适用于：连续的情节，章节之间紧密相关
{{
    "name": "{medium_event.get('name')}",
    "chapter_range": "{chapter_range}",
    "decomposition_type": "ai_free_direct_scenes",
    "ai_decision": "说明你为什么选择这种结构",
    "chapter_breakdown": {{
        "overall_arc": "整个{chapter_count}章的情节发展弧线"
    }},
    "scene_sequences": [
        {{
            "chapter_range": "{start_ch}-{end_ch}",
            "chapter_role": "整体推进",
            "chapter_goal": "在{chapter_count}章内完成什么",
            "scene_events": [
                {{
                    "sequence": 1,
                    "role": "起/承/转/合/其他",
                    "description": "场景描述",
                    "emotional_intensity": "low/medium/high",
                    "target_chapter": "{start_ch}"
                }},
                ...
            ]
        }}
    ]
}}

### 方案B：分解为章节事件，每章独立场景
适用于：章节之间相对独立，每章有自己的小目标
{{
    "name": "{medium_event.get('name')}",
    "chapter_range": "{chapter_range}",
    "decomposition_type": "ai_free_chapter_events",
    "ai_decision": "说明你为什么选择这种结构",
    "chapter_events": [
        {{
            "name": "第X章事件名称",
            "chapter_range": "X-X",
            "main_goal": "本章的目标",
            "scene_structure": {{
                "scenes": [
                    {{
                        "sequence": 1,
                        "role": "起/承/转/合",
                        "description": "场景描述",
                        "emotional_intensity": "low/medium/high"
                    }},
                    ...
                ]
            }}
        }},
        ...
    ]
}}

### 方案C：混合方案（你自己设计）
如果你认为有更好的结构，可以自由设计输出格式，但要确保包含：
- scene_events 或 scenes 字段
- 每个场景的 description 和 emotional_intensity
- 明确的章节范围对应关系

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
                                                    consistency_guidance: Optional[str] = None) -> Optional[Dict]:
        """
        为单章中型事件生成完整的起承转合场景
        
        这个方法专门处理只有1章的中型事件，直接生成一个完整的起承转合场景序列，
        确保单章也能形成完整的戏剧结构。
        
        Args:
            medium_event: 单章中型事件
            major_event: 所属重大事件
            其他参数同上
            
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
        
        prompt = f"""
# 任务：单章中型事件"完整起承转合场景构建"
{consistency_block}
你需要为一个单章中型事件设计完整的起承转合场景结构。

## 当前中型事件信息
- **中型事件名称**: {medium_event.get('name')}
- **章节范围**: {chapter_range}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **情绪强度**: {medium_event.get('emotional_intensity', 'medium')}
{special_emotional_context}

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

## ⚠️ 重要：输出格式要求
你必须严格按照以下JSON格式返回结果，不得使用其他格式：

{{
    "name": "{medium_event.get('name')}",
    "chapter_range": "{chapter_range}",
    "decomposition_type": "single_chapter_complete_arc",
    "chapter_breakdown": {{
        "overall_arc": "整个单章事件的完整起承转合弧线"
    }},
    "scene_sequences": [
        {{
            "chapter_range": "{start_ch}-{start_ch}",
            "chapter_role": "单章完整",
            "chapter_goal": "在单章内完成起承转合",
            "scene_events": [
                {{
                    "sequence": 1,
                    "role": "起",
                    "position": "opening",
                    "description": "开篇场景描述",
                    "purpose": "场景目的",
                    "key_actions": ["动作1", "动作2"],
                    "emotional_intensity": "low",
                    "emotional_impact": "情感冲击",
                    "dialogue_highlights": ["对话示例"],
                    "conflict_point": "冲突焦点",
                    "sensory_details": "感官细节",
                    "transition_to_next": "过渡说明",
                    "estimated_word_count": "预计字数"
                }},
                {{
                    "sequence": 2,
                    "role": "承",
                    "position": "development1",
                    "description": "发展场景描述",
                    "purpose": "场景目的",
                    "key_actions": ["动作1", "动作2"],
                    "emotional_intensity": "medium",
                    "emotional_impact": "情感冲击",
                    "dialogue_highlights": ["对话示例"],
                    "conflict_point": "冲突焦点",
                    "sensory_details": "感官细节",
                    "transition_to_next": "过渡说明",
                    "estimated_word_count": "预计字数"
                }},
                {{
                    "sequence": 3,
                    "role": "转",
                    "position": "climax",
                    "description": "高潮场景描述",
                    "purpose": "场景目的",
                    "key_actions": ["动作1", "动作2"],
                    "emotional_intensity": "high",
                    "emotional_impact": "情感冲击",
                    "dialogue_highlights": ["对话示例"],
                    "conflict_point": "冲突焦点",
                    "sensory_details": "感官细节",
                    "transition_to_next": "过渡说明",
                    "estimated_word_count": "预计字数"
                }},
                {{
                    "sequence": 4,
                    "role": "合",
                    "position": "ending",
                    "description": "收尾场景描述",
                    "purpose": "场景目的",
                    "key_actions": ["动作1", "动作2"],
                    "emotional_intensity": "medium",
                    "emotional_impact": "情感冲击",
                    "dialogue_highlights": ["对话示例"],
                    "conflict_point": "冲突焦点",
                    "sensory_details": "感官细节",
                    "transition_to_next": "过渡说明",
                    "estimated_word_count": "预计字数"
                }}
            ]
        }}
    ]
}}

请严格按照上述格式返回JSON，不要添加任何其他字段或结构。
"""
        
        result = self.api_client.generate_content_with_retry(
            content_type="chapter_event_design",  # 使用已支持的内容类型
            user_prompt=prompt,
            purpose=f"为单章中型事件'{medium_event.get('name')}'生成完整起承转合场景"
        )
        
        if result:
            # 检查返回的数据结构
            if 'scene_sequences' in result and result['scene_sequences']:
                scene_count = len(result['scene_sequences'][0].get('scene_events', []))
                self.logger.info(f"      ✅ 成功为单章事件生成完整起承转合场景（{scene_count}个场景）")
            else:
                self.logger.warn(f"      ⚠️ API返回数据格式不符合预期")
                self.logger.info(f"      📋 返回的键: {list(result.keys())}")
                self.logger.info(f"      📋 完整数据: {json.dumps(result, ensure_ascii=False)[:500]}")
        else:
            self.logger.error(f"      ❌ 生成单章完整场景失败，API返回为空")
        
        return result