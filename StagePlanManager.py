# StagePlanManager.py
import json
import re
import os
from typing import Dict, Optional, List
from pathlib import Path
from EventManager import EventManager
from datetime import datetime
from EmotionalPlanManager import EmotionalPlanManager
from StagePlanUtils import is_chapter_in_range, parse_chapter_range
from WritingGuidanceManager import WritingGuidanceManager
from RomancePatternManager import RomancePatternManager

class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}
        
        # 初始化各个管理器
        self.event_manager = EventManager(self)
        self.writing_guidance_manager = WritingGuidanceManager(self)

        # 为阶段计划创建专用的存储目录
        self.plans_dir = Path("./quality_data/plans")
        os.makedirs(self.plans_dir, exist_ok=True)

        # 阶段特性描述（"起承转合"四段式）
        self.stage_characteristics = {
            "opening_stage": {
                "name": "起 (开局阶段)",
                "focus": "快速建立强烈冲突，立即吸引读者",
                "pace": "极快节奏，前3章必须建立核心冲突",
                "key_elements": "主角惊艳登场、立即冲突、强力悬念、读者共鸣",
                "critical_requirements": [
                    "前3000字内必须建立强烈冲突",
                    "第1章结尾必须有强力追读钩子", 
                    "减少世界观介绍，增加行动和冲突",
                    "主角特质在前2章完全展现"
                ]
            },
            "development_stage": {
                "name": "承 (发展阶段)",
                "focus": "深化矛盾，推进角色成长，扩展世界",
                "pace": "变化节奏，快慢结合，包含多个小高潮",
                "key_elements": "能力提升、盟友敌人、支线展开、伏笔埋设"
            },
            "climax_stage": {
                "name": "转 (高潮阶段)",
                "focus": "主要矛盾全面爆发，剧情发生重大转折",
                "pace": "紧张节奏，逐步加速，直至顶点",
                "key_elements": "关键对决、真相揭露、角色蜕变、情感宣泄"
            },
            "ending_stage": {
                "name": "合 (结局阶段)",
                "focus": "解决所有核心矛盾，收束全部线索，升华主题",
                "pace": "逐渐放缓，情感升华，带来圆满或引人深思的结局",
                "key_elements": "矛盾解决、伏笔回收、角色归宿、主题升华、情感共鸣"
            }
        }

    @property
    def emotional_manager(self):
        return self.generator.emotional_plan_manager

    @property
    def romance_manager(self):
        return getattr(self.generator, 'romance_manager', None)
    
    def generate_overall_stage_plan(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                market_analysis: Dict, global_growth_plan: Dict, 
                                emotional_blueprint: Dict,
                                total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划（"起承转合"四段式）"""
        print("=== 生成全书阶段计划 ===")
        stage_arcs = emotional_blueprint.get("stage_emotional_arcs", {})
        emotional_goals_prompt = []
        if stage_arcs:
            stage_name_map = {
                "opening_stage": "起 (开局阶段)",
                "development_stage": "承 (发展阶段)",
                "climax_stage": "转 (高潮阶段)",
                "ending_stage": "合 (结局阶段)" 
            }
            for stage_key, arc_info in stage_arcs.items():
                stage_name_cn = stage_name_map.get(stage_key, stage_key)
                emotional_goals_prompt.append(f"- **{stage_name_cn}**: {arc_info.get('description', '无特定情绪目标')}")
        
        emotional_goals_str = "\n".join(emotional_goals_prompt)
        
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = f"""
最高指令：以"情绪发展蓝图"和"创意种子"为绝对准则。
你的任务是设计一个服务于小说情绪发展的【剧情阶段规划】。所有剧情安排都必须为了实现预设的读者情绪目标。

# 情感战略目标 (来自情绪蓝图)
{emotional_goals_str}

# 核心参考资料 
创意种子: {creative_seed}
小说标题: {novel_title}
小说简介: {novel_synopsis}
总章节数: {total_chapters}

# 阶段划分要求
请将全书{total_chapters}章，按照经典的"起、承、转、合"四阶段结构进行划分，并为每个阶段制定详细的写作重点：

## 1. 起 (开局阶段，约前15%)
- **章节范围**: 第1章-第{boundaries['opening_end']}章
- **核心任务**: 快速建立故事基础，引入核心冲突，用强力钩子吸引读者。
- **【强制指令：开局核心目标】**: 你必须为这个阶段设定一个明确、具体、能驱动读者追读到第{boundaries['opening_end']}章的"开局核心目标 (opening_arc_goal)"。

## 2. 承 (发展阶段，约35%)
- **章节范围**: 第{boundaries['development_start']}章-第{boundaries['development_end']}章  
- **核心任务**: 深化并扩大矛盾，角色获得成长，世界观逐步展开。

## 3. 转 (高潮阶段，约30%)
- **章节范围**: 第{boundaries['climax_start']}章-第{boundaries['climax_end']}章
- **核心任务**: 主要矛盾全面爆发，迎来决定性的重大转折，情感集中宣泄。  

## 4. 合 (结局阶段，约20%)
- **章节范围**: 第{boundaries['ending_start']}章-第{total_chapters}章
- **核心任务**: 解决所有核心冲突，回收全部重要伏笔，交代角色归宿，升华主题。
"""
        
        result = self.generator.api_client.generate_content_with_retry(
            content_type="overall_stage_plan", 
            user_prompt=user_prompt, 
            purpose="制定全书阶段计划"
        )
        
        if result and isinstance(result, dict):
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            self.generator.novel_data["overall_stage_plans"] = result
            print("✓ 全书阶段计划生成成功")
            return result
        else:
            print("❌ 全书阶段计划生成失败")
            return None

    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        """计算"起承转合"四阶段的边界"""
        # 比例: 起(15%), 承(35%), 转(30%), 合(20%)
        ratios = [0.15, 0.35, 0.30, 0.20]
        chapters = [0]
        cumulative_ratio = 0
        for ratio in ratios[:-1]:
            cumulative_ratio += ratio
            chapters.append(int(total_chapters * cumulative_ratio))
        chapters.append(total_chapters)

        return {
            "opening_end": chapters[1],
            "development_start": chapters[1] + 1,
            "development_end": chapters[2], 
            "climax_start": chapters[2] + 1,
            "climax_end": chapters[3],
            "ending_start": chapters[3] + 1,
        }
    
    def print_stage_overview(self):
        """打印详细的阶段计划概览"""
        if not self.overall_stage_plans:
            print("暂无阶段计划数据")
            return
        
        print("\n" + "=" * 60)
        print("                   小说阶段计划概览")
        print("=" * 60)
        
        total_chapters = 0
        stage_plan_dict = self.overall_stage_plans.get("overall_stage_plan", {})
        
        stage_map = {
            "opening_stage": "起 (开局阶段)",
            "development_stage": "承 (发展阶段)",
            "climax_stage": "转 (高潮阶段)",
            "ending_stage": "合 (结局阶段)"
        }
        for i, (stage_key, stage_info) in enumerate(stage_plan_dict.items(), 1):
            stage_name = stage_map.get(stage_key, stage_key)
            chapter_range = stage_info.get('chapter_range', '1-1')
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            total_chapters += chapter_count
            
            print(f"\n📚 阶段 {i}: {stage_name}")
            print(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            print(f"   🎯 目标: {stage_info.get('stage_goal', stage_info.get('core_tasks', '暂无目标描述'))}")
            print(f"   ⚡ 关键发展: {stage_info.get('key_developments', stage_info.get('key_content', '暂无关键事件'))}")
            if stage_info.get('core_conflicts'):
                print(f"   ⚔️ 核心冲突: {stage_info.get('core_conflicts')}")
        
        print(f"\n📈 总计: {len(stage_plan_dict)}个阶段，{total_chapters}章")
        print("=" * 60)

    def _generate_basic_stage_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """生成阶段基础计划（不包含详细事件）"""
        user_prompt = f"""
    请为小说阶段生成基础写作计划。

    ## 阶段信息
    - 阶段名称: {stage_name}
    - 章节范围: {stage_range}
    - 小说标题: {novel_title}
    - 小说简介: {novel_synopsis}
    - 创意种子: {creative_seed}

    ## 阶段总体目标
    {overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")}

    请重点描述阶段策略、目标和关键节点，不要输出详细的事件列表。
    """
        
        result = self.generator.api_client.generate_content_with_retry(
            content_type="stage_writing_plan", 
            user_prompt=user_prompt, 
            purpose=f"生成{stage_name}基础计划"
        )
        
        return result

    def _assemble_final_plan(self, stage_name, stage_range, final_major_events, overall_stage_plan,
                        novel_title: str = "", novel_synopsis: str = "", creative_seed: str = "") -> Dict:
        """工作流第四阶段：将所有生成的部分组装成最终的JSON计划。"""
        
        print(f"  🔍 检查最终组装：收到 {len(final_major_events)} 个重大事件")
        
        for i, major_event in enumerate(final_major_events):
            print(f"    重大事件 {i+1}: {major_event.get('name')}")
            composition = major_event.get("composition", {})
            for phase, events in composition.items():
                for j, event in enumerate(events):
                    decomp_type = event.get('decomposition_type', '未分解')
                    print(f"      {phase}-{j+1}: {event.get('name')} [{decomp_type}]")

        # 收集所有场景事件（按章节组织）
        chapter_scene_map = {}  # 章节号 -> 场景事件列表
        
        # 同时收集情绪相关信息
        emotional_summary = {
            "stage_emotional_arc": overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("emotional_goal", ""),
            "major_events_emotional_summary": []
        }
        
        for major_event in final_major_events:
            # 收集重大事件的情绪信息
            emotional_summary["major_events_emotional_summary"].append({
                "name": major_event.get("name"),
                "emotional_goal": major_event.get("emotional_goal", ""),
                "emotional_arc_summary": major_event.get("emotional_arc_summary", "")
            })
            
            composition = major_event.get("composition", {})
            for phase_events in composition.values():
                for medium_event in phase_events:
                    # 收集中型事件的情绪信息
                    if "emotional_focus" in medium_event:
                        emotional_summary.setdefault("medium_events_emotional_focus", []).append({
                            "name": medium_event.get("name"),
                            "emotional_focus": medium_event.get("emotional_focus"),
                            "emotional_intensity": medium_event.get("emotional_intensity", "medium")
                        })
                    
                    decomposition_type = medium_event.get("decomposition_type", "")
                    
                    if decomposition_type == "chapter_then_scene":
                        # 包含章节事件的情况（章节事件内包含场景结构）
                        chapter_events = medium_event.get("chapter_events", [])
                        for chapter_event in chapter_events:
                            chapter_range = chapter_event.get('chapter_range', '0-0')
                            start_ch, end_ch = parse_chapter_range(chapter_range)
                            
                            # 提取场景事件
                            scene_structure = chapter_event.get("scene_structure", {})
                            scenes = scene_structure.get("scenes", [])
                            
                            # 按章节存储场景事件
                            for chapter_num in range(start_ch, end_ch + 1):
                                if chapter_num not in chapter_scene_map:
                                    chapter_scene_map[chapter_num] = []
                                chapter_scene_map[chapter_num].extend(scenes)
                    
                    elif decomposition_type == "direct_scene":
                        # 直接包含场景序列的情况
                        scene_sequences = medium_event.get("scene_sequences", [])
                        for sequence in scene_sequences:
                            chapter_range = sequence.get('chapter_range', '0-0')
                            start_ch, end_ch = parse_chapter_range(chapter_range)
                            
                            # 提取场景事件
                            scene_events = sequence.get("scene_events", [])
                            
                            # 按章节存储场景事件
                            for chapter_num in range(start_ch, end_ch + 1):
                                if chapter_num not in chapter_scene_map:
                                    chapter_scene_map[chapter_num] = []
                                chapter_scene_map[chapter_num].extend(scene_events)
        
        # 构建按章节组织的场景事件列表
        chapter_scene_events = []
        for chapter_num in sorted(chapter_scene_map.keys()):
            chapter_scene_events.append({
                "chapter_number": chapter_num,
                "scene_events": chapter_scene_map[chapter_num]
            })

        # 构建最终的计划结构，确保包含情绪信息
        stage_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A"),
                "novel_metadata": {  # 新增小说元数据
                    "title": novel_title,
                    "synopsis": novel_synopsis,
                    "creative_seed": creative_seed,
                    "generation_timestamp": datetime.now().isoformat()
                },
                "emotional_summary": emotional_summary,
                "event_system": {
                    "overall_approach": "采用智能分形设计：根据章节数自动选择分解策略，最终基于场景事件构建章节。",
                    "major_events": final_major_events,
                    "chapter_scene_events": chapter_scene_events
                },
            }
        }
        return stage_plan
    
    @staticmethod
    def parse_chapter_range(range_str: str) -> tuple:
        """
        解析章节范围字符串，返回(start, end)元组。
        支持格式："1-100"、"1-100章"、"109-110章"等。
        如果解析失败，返回默认值(1, 100)。
        """
        try:
            # 移除"章"字和其他非数字字符（除了横杠和数字）
            cleaned_str = range_str.replace("章", "").strip()
            
            if "-" in cleaned_str:
                parts = cleaned_str.split("-")
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    return start, end
            else:
                # 如果只有单个数字
                chapter = int(cleaned_str)
                return chapter, chapter
                
        except (ValueError, AttributeError, IndexError):
            print(f"⚠️ 解析章节范围失败: '{range_str}'，使用默认值(1, 100)")
            return 1, 100

    def _smart_decompose_medium_events(self, major_event: Dict, stage_name: str,
                                    novel_title: str, novel_synopsis: str, creative_seed: str) -> Dict:
        """智能分解中型事件：根据章节数选择分解策略，确保服务于中型事件自身目标"""
        
        # 收集所有中型事件
        all_medium_events = []
        composition = major_event.get("composition", {})
        for phase_events in composition.values():
            all_medium_events.extend(phase_events)
        
        # 为每个中型事件智能选择分解策略
        decomposed_medium_events = []
        for medium_event in all_medium_events:
            chapter_range = medium_event.get('chapter_range', '0-0')
            start_ch, end_ch = self.parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            
            if chapter_count > 3:
                # 章节数>3，先分解为章节事件，再分解为场景事件
                print(f"    -> 中型事件'{medium_event['name']}'({chapter_count}章) 进行章节事件+场景事件分解")
                decomposed_event = self._decompose_medium_to_chapter_then_scene(
                    medium_event, major_event, stage_name, novel_title, novel_synopsis, creative_seed
                )
            else:
                # 章节数<3，直接分解为场景事件
                print(f"    -> 中型事件'{medium_event['name']}'({chapter_count}章) 直接进行场景事件分解")
                decomposed_event = self._decompose_medium_direct_to_scene(
                    medium_event, major_event, stage_name, novel_title, novel_synopsis, creative_seed
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
        
        # 修复：正确更新重大事件的composition
        major_event_copy = major_event.copy()
        major_event_copy["composition"] = {}
        
        for phase_name, phase_events in composition.items():
            major_event_copy["composition"][phase_name] = []
            for event in phase_events:
                # 找到对应的分解后中型事件
                decomposed_event = next((de for de in decomposed_medium_events 
                                    if de['name'] == event['name']), event)  # 如果没找到，使用原事件
                major_event_copy["composition"][phase_name].append(decomposed_event)
        
        return major_event_copy

    def _decompose_medium_to_chapter_then_scene(self, medium_event: Dict, major_event: Dict, stage_name: str,
                                            novel_title: str, novel_synopsis: str, creative_seed: str) -> Dict:
        """中型事件≥3章：先分解为章节事件，再分解为场景事件，服务于中型事件目标"""
        
        # 第一步：分解为章节事件
        chapter_events_prompt = f"""
# 任务：中型事件"章节分解" - 服务于中型事件目标
你需要将一个多章的中型事件分解为具体的章节事件，每个章节事件覆盖1章，确保服务于中型事件的目标。

## 当前中型事件信息
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event.get('name')}
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **服务重大事件**: {medium_event.get('contribution_to_major')}

## 分解要求
请将这个中型事件分解为{medium_event.get('chapter_range')}范围内的各个章节事件，确保：
1. 每个章节事件有明确的目标，服务于中型事件的核心目标
2. 章节之间要有连贯性和递进关系，服务于中型事件的emotional_focus
3. 形成完整的"起承转合"结构，服务于中型事件在重大事件中的角色

## 输出格式
{{
    "name": "{medium_event.get('name')}",
    "type": "medium_event",
    "chapter_range": "{medium_event.get('chapter_range')}",
    "main_goal": "{medium_event.get('main_goal')}",
    "emotional_focus": "{medium_event.get('emotional_focus')}",
    "description": "{medium_event.get('description')}",
    "decomposition_type": "chapter_then_scene",
    "contribution_to_major": "{medium_event.get('contribution_to_major')}",
    "chapter_events": [
        {{
            "name": "章节事件名称",
            "type": "chapter_event", 
            "chapter_range": "string // 单章范围，例如：'49-49章'",
            "main_goal": "该章节要达成的具体目标（服务于中型事件目标）",
            "emotional_focus": "本章的情绪重点（服务于中型事件emotional_focus）",
            "emotional_turn": "本章的情感转折点",
            "structural_role": "在事件中的结构作用 (起/承/转/合)",
            "contribution_to_medium": "如何服务于中型事件目标"
        }},
        // ... 更多章节事件
    ]
}}
    """
        
        chapter_events_result = self.generator.api_client.generate_content_with_retry(
            content_type="medium_event_decomposition", 
            user_prompt=chapter_events_prompt, 
            purpose=f"分解中型事件'{medium_event.get('name')}'为章节事件"
        )
        
        if not chapter_events_result:
            return None
        
        # 第二步：为每个章节事件分解为场景事件
        scene_structured_chapters = []
        for chapter_event in chapter_events_result.get("chapter_events", []):
            scene_structure_prompt = f"""
    # 任务：章节事件"场景结构构建" - 服务于章节事件目标
    你需要为一个章节事件设计完整的场景结构，确保章节内部有完整的戏剧发展和情感弧线，服务于章节事件的目标。

    ## 当前章节事件信息
    - **所属阶段**: {stage_name}
    - **所属重大事件**: {major_event.get('name')}
    - **所属中型事件**: {medium_event.get('name')}
    - **章节事件名称**: {chapter_event.get('name')}
    - **章节范围**: {chapter_event.get('chapter_range')}
    - **章节目标**: {chapter_event.get('main_goal')}
    - **章节情绪重点**: {chapter_event.get('emotional_focus')}
    - **情感转折**: {chapter_event.get('emotional_turn')}
    - **结构作用**: {chapter_event.get('structural_role')}
    - **服务中型事件**: {chapter_event.get('contribution_to_medium')}

    ## 场景构建要求
    请为这个章节设计4-6个场景事件，形成完整的戏剧结构，服务于章节目标：

    ### 场景结构要求：
    1. **开场场景** (15-20%)：建立情境，引入冲突，服务于章节目标
    2. **发展场景1** (20-25%)：推进情节，深化冲突，服务于章节目标  
    3. **发展场景2** (20-25%)：冲突升级，逼近高潮，服务于章节目标
    4. **高潮场景** (15-20%)：情感爆发，关键转折，服务于章节目标
    5. **回落场景** (10-15%)：处理后果，情感沉淀，服务于章节目标
    6. **结尾场景** (5-10%)：设置悬念，引导下一章，服务于章节目标

    ## 输出格式
    {{
        "name": "{chapter_event.get('name')}",
        "type": "chapter_event",
        "chapter_range": "{chapter_event.get('chapter_range')}",
        "main_goal": "{chapter_event.get('main_goal')}",
        "emotional_focus": "{chapter_event.get('emotional_focus')}",
        "emotional_turn": "{chapter_event.get('emotional_turn')}",
        "structural_role": "{chapter_event.get('structural_role')}",
        "contribution_to_medium": "{chapter_event.get('contribution_to_medium')}",
        "scene_structure": {{
            "overall_pace": "string // 本章节奏描述",
            "emotional_arc": "string // 本章情感发展曲线",
            "scenes": [
                {{
                    "name": "场景名称",
                    "type": "scene_event",
                    "position": "opening/development1/development2/climax/falling/ending",
                    "purpose": "场景的戏剧目的（服务于章节目标）",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "场景的情感冲击（服务于章节emotional_focus）",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "冲突的具体表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "预估字数范围，需要非常精炼",
                    "contribution_to_chapter": "如何服务于章节目标"
                }},
                // ... 更多场景事件 (总共4-6个)
            ],
            "chapter_hook": "string // 章节结尾的悬念钩子",
            "writing_focus": "string // 本章写作重点提示"
        }}
    }}
    """
            
            scene_result = self.generator.api_client.generate_content_with_retry(
                content_type="chapter_event_design", 
                user_prompt=scene_structure_prompt, 
                purpose=f"为章节事件'{chapter_event.get('name')}'构建场景结构"
            )
            
            if scene_result:
                scene_structured_chapters.append(scene_result)
            else:
                # 如果场景结构生成失败，至少保留章节事件
                scene_structured_chapters.append(chapter_event)
        
        # 修复：确保更新章节事件为场景结构化版本
        if scene_structured_chapters:
            chapter_events_result["chapter_events"] = scene_structured_chapters
        
        return chapter_events_result

    def validate_goal_hierarchy_coherence(self, stage_writing_plan: Dict, stage_name: str) -> Dict:
        """AI评估目标层级一致性：阶段→重大事件→中型事件→章节事件→场景事件"""
        
        print(f"  🤖 AI评估{stage_name}阶段目标层级一致性...")
        
        # 提取阶段计划中的关键信息
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        
        event_system = plan_data.get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        # 构建目标层级评估提示词
        coherence_prompt = self._build_goal_hierarchy_prompt(
            stage_name, plan_data, major_events
        )
        
        try:
            coherence_assessment = self.generator.api_client.generate_content_with_retry(
                content_type="goal_hierarchy_coherence_assessment",
                user_prompt=coherence_prompt,
                purpose=f"评估{stage_name}阶段目标层级一致性"
            )
            
            if coherence_assessment:
                print(f"  ✅ {stage_name}阶段目标层级一致性评估完成")
                return coherence_assessment
            else:
                print(f"  ⚠️ {stage_name}阶段目标层级一致性评估失败")
                return self._create_default_coherence_assessment()
                
        except Exception as e:
            print(f"  ❌ AI目标层级评估出错: {e}")
        return self._create_default_coherence_assessment()

    def _build_goal_hierarchy_prompt(self, stage_name: str, plan_data: Dict, major_events: List[Dict]) -> str:
        """构建目标层级一致性评估提示词"""
        
        # 构建事件层级结构的详细描述
        hierarchy_description = self._build_hierarchy_description(major_events)
        
        prompt_parts = [
            "# 🎯 小说事件目标层级一致性深度评估",
            "",
            "## 评估任务",
            f"请对**{stage_name}**阶段的事件目标层级进行深度评估。",
            "重点分析从重大事件→中型事件→章节事件→场景事件的目标传递连贯性和逻辑一致性。",
            "",
            "## 事件层级结构详情",
            hierarchy_description,
            "",
            "## 评估维度",
            "请基于以上事件层级结构，分析以下维度：",
            "",
            "### 1. 目标传递连贯性",
            "- 重大事件目标是否清晰分解到中型事件？",
            "- 中型事件目标是否有效服务于重大事件目标？", 
            "- 章节事件目标是否明确支持中型事件目标？",
            "- 场景事件目标是否具体服务于章节事件目标？",
            "- 是否存在目标传递断裂或模糊的情况？",
            "",
            "### 2. 情绪目标一致性",
            "- 情绪目标是否在层级间保持连贯？",
            "- 情绪强度是否合理递进？",
            "- 情感节拍是否服务于整体情绪目标？",
            "",
            "### 3. 贡献关系明确性",
            "- 每个事件是否明确说明了对上一级事件的贡献？",
            "- 贡献描述是否具体、可执行？",
            "- 是否存在贡献关系模糊或缺失的情况？",
            "",
            "### 4. 逻辑合理性",
            "- 事件分解是否逻辑合理？",
            "- 章节分配是否满足目标实现的需求？",
            "- 场景安排是否有效支持事件目标的达成？",
            "",
            "### 5. 可执行性评估",
            "- 最底层的事件目标是否足够具体，可以直接指导写作？",
            "- 是否存在目标过于抽象或模糊的情况？",
            "",
            "## 🎯 评估要求",
            "请提供具体的、可操作的评估结果和改进建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_coherence_score": 0-10的带一位小数的评分,',
            '  "hierarchy_strengths": ["优势1", "优势2", ...],',
            '  "critical_breakpoints": [',
            '    {"level": "重大事件→中型事件/中型事件→章节事件/...", "event_name": "事件名称", "issue": "具体问题描述", "severity": "high/medium/low"},',
            '    ...',
            '  ],',
            '  "goal_alignment_analysis": {',
            '    "major_to_medium": "重大事件到中型事件的目标对齐分析",',
            '    "medium_to_chapter": "中型事件到章节事件的目标对齐分析",',
            '    "chapter_to_scene": "章节事件到场景事件的目标对齐分析"',
            '  },',
            '  "emotional_consistency_analysis": "情绪目标一致性分析",',
            '  "improvement_recommendations": [',
            '    {"breakpoint": "具体的断裂点", "suggestion": "改进建议", "priority": "high/medium/low"},',
            '    ...',
            '  ],',
            '  "exemplary_chains": ["优秀的目标链示例1", "优秀的目标链示例2"],',
            '  "risk_events": ["存在高风险的事件列表"]',
            "}"
        ]
        
        return "\n".join(prompt_parts)

    def _build_hierarchy_description(self, major_events: List[Dict]) -> str:
        """构建事件层级结构的详细描述"""
        
        if not major_events:
            return "当前阶段没有重大事件。"
        
        description_parts = []
        
        for i, major_event in enumerate(major_events, 1):
            description_parts.append(f"### 🚨 重大事件 {i}: {major_event.get('name', '未命名')}")
            description_parts.append(f"- **章节范围**: {major_event.get('chapter_range', '未指定')}")
            description_parts.append(f"- **核心目标**: {major_event.get('main_goal', '未指定')}")
            description_parts.append(f"- **情绪目标**: {major_event.get('emotional_goal', '未指定')}")
            description_parts.append(f"- **在阶段中的角色**: {major_event.get('role_in_stage_arc', '未指定')}")
            
            # 中型事件层级
            composition = major_event.get("composition", {})
            medium_events_count = sum(len(events) for events in composition.values())
            description_parts.append(f"- **包含 {medium_events_count} 个中型事件**:")
            
            for phase_name, medium_events in composition.items():
                for j, medium_event in enumerate(medium_events, 1):
                    description_parts.append(f"  #### 📈 中型事件 {j} ({phase_name}): {medium_event.get('name', '未命名')}")
                    description_parts.append(f"  - **章节范围**: {medium_event.get('chapter_range', '未指定')}")
                    description_parts.append(f"  - **核心目标**: {medium_event.get('main_goal', '未指定')}")
                    description_parts.append(f"  - **情绪重点**: {medium_event.get('emotional_focus', '未指定')}")
                    description_parts.append(f"  - **服务重大事件**: {medium_event.get('contribution_to_major', '未指定')}")
                    
                    # 章节事件层级（如果存在）
                    if medium_event.get("decomposition_type") == "chapter_then_scene":
                        chapter_events = medium_event.get("chapter_events", [])
                        description_parts.append(f"  - **包含 {len(chapter_events)} 个章节事件**:")
                        
                        for k, chapter_event in enumerate(chapter_events, 1):
                            description_parts.append(f"    ##### 📖 章节事件 {k}: {chapter_event.get('name', '未命名')}")
                            description_parts.append(f"    - **章节范围**: {chapter_event.get('chapter_range', '未指定')}")
                            description_parts.append(f"    - **核心目标**: {chapter_event.get('main_goal', '未指定')}")
                            description_parts.append(f"    - **情绪重点**: {chapter_event.get('emotional_focus', '未指定')}")
                            description_parts.append(f"    - **服务中型事件**: {chapter_event.get('contribution_to_medium', '未指定')}")
                            
                            # 场景事件层级（如果存在）
                            scene_structure = chapter_event.get("scene_structure", {})
                            scenes = scene_structure.get("scenes", [])
                            if scenes:
                                description_parts.append(f"    - **包含 {len(scenes)} 个场景事件**:")
                                for l, scene in enumerate(scenes[:3], 1):  # 只显示前3个场景
                                    description_parts.append(f"      ###### 🎬 场景 {l}: {scene.get('name', '未命名')}")
                                    description_parts.append(f"      - **目的**: {scene.get('purpose', '未指定')}")
                                    description_parts.append(f"      - **情感冲击**: {scene.get('emotional_impact', '未指定')}")
                                    description_parts.append(f"      - **服务章节**: {scene.get('contribution_to_chapter', '未指定')}")
                                if len(scenes) > 3:
                                    description_parts.append(f"      - ... 还有{len(scenes)-3}个场景事件")
                    
                    elif medium_event.get("decomposition_type") == "direct_scene":
                        scene_sequences = medium_event.get("scene_sequences", [])
                        description_parts.append(f"  - **直接包含 {len(scene_sequences)} 个场景序列**:")
                        
                        for seq in scene_sequences:
                            scene_events = seq.get("scene_events", [])
                            description_parts.append(f"    - **章节 {seq.get('chapter_range', '未指定')}**: {len(scene_events)}个场景事件")
            
            description_parts.append("")  # 空行分隔重大事件
        
        return "\n".join(description_parts)

    def _create_default_coherence_assessment(self) -> Dict:
        """创建默认的一致性评估结果"""
        return {
            "overall_coherence_score": 5.0,
            "hierarchy_strengths": ["基础结构完整"],
            "critical_breakpoints": [
                {
                    "level": "评估系统暂时不可用",
                    "event_name": "系统",
                    "issue": "AI评估服务暂时不可用",
                    "severity": "medium"
                }
            ],
            "goal_alignment_analysis": {
                "major_to_medium": "无法进行评估",
                "medium_to_chapter": "无法进行评估", 
                "chapter_to_scene": "无法进行评估"
            },
            "emotional_consistency_analysis": "无法进行评估",
            "improvement_recommendations": [
                {
                    "breakpoint": "评估系统",
                    "suggestion": "等待AI评估服务恢复后重新评估",
                    "priority": "medium"
                }
            ],
            "exemplary_chains": [],
            "risk_events": ["所有事件（因无法评估）"]
        }

    def _assess_goal_alignment(self, sub_goal: str, parent_goal: str) -> str:
        """评估子目标与父目标的对齐度"""
        if not sub_goal or not parent_goal:
            return "low"
        
        sub_goal_lower = sub_goal.lower()
        parent_goal_lower = parent_goal.lower()
        
        # 简单的关键词匹配
        parent_keywords = parent_goal_lower.split()
        matches = sum(1 for keyword in parent_keywords if keyword in sub_goal_lower)
        
        if matches >= 2:
            return "high"
        elif matches >= 1:
            return "medium"
        else:
            return "low"

    def _decompose_medium_direct_to_scene(self, medium_event: Dict, major_event: Dict, stage_name: str,
                                        novel_title: str, novel_synopsis: str, creative_seed: str) -> Dict:
        """中型事件<3章：直接分解为场景事件，明确每个场景的章节归属和服务关系"""
        
        chapter_range = medium_event.get('chapter_range', '0-0')
        start_ch, end_ch = parse_chapter_range(chapter_range)
        chapter_count = end_ch - start_ch + 1
        
        # 构建详细的章节分配说明
        chapter_breakdown = ""
        for i in range(chapter_count):
            chapter_num = start_ch + i
            chapter_breakdown += f"- 第{chapter_num}章: 需要完成中型事件目标的{['起始','发展','高潮','收尾'][min(i, 3)]}部分\n"
        
        prompt = f"""
# 任务：中型事件"多章场景构建" - 明确章节归属和服务关系
你需要为一个跨{chapter_count}章的中型事件设计详细的场景事件序列，明确每个场景的章节归属，确保每章都有完整的场景结构。

## 当前中型事件信息
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event.get('name')}
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')} (共{chapter_count}章)
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **事件描述**: {medium_event.get('description')}
- **服务重大事件**: {medium_event.get('contribution_to_major')}

## 章节分配要求
{chapter_breakdown}

## 场景构建要求
请为这{chapter_count}章分别设计完整的场景事件序列，确保：

### 每章的结构要求：
1. **第1章** (起始章): 建立情境，引入冲突，开启中型事件
- 开场场景：建立基础情境
- 发展场景：引入主要冲突
- 高潮场景：确立本章核心冲突点
- 结尾场景：设置悬念，引导下一章

2. **中间章节** (发展章): 深化冲突，推进情节
- 开场场景：承接上一章悬念
- 发展场景1：推进情节发展
- 发展场景2：冲突升级
- 高潮场景：本章情感爆发点
- 结尾场景：新的悬念或转折

3. **最后一章** (收尾章): 解决冲突，完成中型事件目标
- 开场场景：处理上一章遗留问题
- 发展场景：向最终解决推进
- 高潮场景：中型事件的核心解决时刻
- 回落场景：处理后果和影响
- 结尾场景：中型事件收尾，衔接后续内容

### 跨章连贯性要求：
- 确保章节间场景的平滑过渡
- 保持情绪发展的连贯性
- 每章都要有明确的服务于中型事件目标的贡献

## 输出格式
{{
    "name": "{medium_event.get('name')}",
    "type": "medium_event", 
    "chapter_range": "{medium_event.get('chapter_range')}",
    "main_goal": "{medium_event.get('main_goal')}",
    "emotional_focus": "{medium_event.get('emotional_focus')}",
    "description": "{medium_event.get('description')}",
    "decomposition_type": "direct_scene",
    "contribution_to_major": "{medium_event.get('contribution_to_major')}",
    "chapter_breakdown": {{
        "overall_arc": "整个中型事件的情节发展弧线",
        "emotional_progression": "跨章情绪发展轨迹",
        "key_turning_points": ["转折点1", "转折点2"]
    }},
    "scene_sequences": [
        {{
            "chapter_range": "{start_ch}-{start_ch}",
            "chapter_role": "起始章",
            "chapter_goal": "本章要达成的具体目标（服务于中型事件目标的起始部分）",
            "emotional_focus": "本章的情绪重点",
            "structural_arc": "本章的结构弧线",
            "contribution_to_medium": "本章如何服务于中型事件目标",
            "scene_events": [
                {{
                    "name": "场景1名称",
                    "type": "scene_event",
                    "position": "opening",
                    "purpose": "场景的戏剧目的（服务于本章目标）", 
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "场景的情感冲击",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "冲突的具体表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景2名称", 
                    "type": "scene_event",
                    "position": "development1",
                    "purpose": "推进情节发展",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "深化情感冲突",
                    "dialogue_highlights": ["关键对话1", "关键对话2"], 
                    "conflict_point": "冲突升级表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景3名称",
                    "type": "scene_event", 
                    "position": "climax",
                    "purpose": "本章情感爆发点",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "强烈情感冲击",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "核心冲突解决或升级",
                    "sensory_details": "需要突出的感官细节", 
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景4名称",
                    "type": "scene_event",
                    "position": "ending", 
                    "purpose": "设置悬念，引导下一章",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "悬念带来的期待感",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "未解决的冲突或新出现的矛盾",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一章",
                    "estimated_word_count": "300-500字", 
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                // ... 更多章节的场景序列
            ],
            "chapter_hook": "本章结尾的悬念钩子",
            "writing_focus": "本章写作重点提示",
            "connection_to_next": "如何连接到下一章"
        }}        ]
}}
    """
        
        result = self.generator.api_client.generate_content_with_retry(
            content_type="multi_chapter_scene_design", 
            user_prompt=prompt, 
            purpose=f"为中型事件'{medium_event.get('name')}'构建多章场景序列"
        )
        
        return result

    def validate_scene_planning_coverage(self, stage_writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        """验证场景规划是否完整覆盖所有章节"""
        
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        
        event_system = plan_data.get("event_system", {})
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        
        # 解析阶段范围
        start_ch, end_ch = parse_chapter_range(stage_range)
        expected_chapters = set(range(start_ch, end_ch + 1))
        
        # 获取实际覆盖的章节
        covered_chapters = set(chapter["chapter_number"] for chapter in chapter_scene_events)
        
        # 找出缺失的章节
        missing_chapters = expected_chapters - covered_chapters
        extra_chapters = covered_chapters - expected_chapters
        
        # 分析场景分布
        scene_distribution = {}
        for chapter in chapter_scene_events:
            chapter_num = chapter["chapter_number"]
            scene_count = len(chapter.get("scene_events", []))
            scene_distribution[chapter_num] = scene_count
        
        coverage_analysis = {
            "stage_name": stage_name,
            "stage_range": stage_range,
            "expected_chapters": len(expected_chapters),
            "covered_chapters": len(covered_chapters),
            "coverage_rate": len(covered_chapters) / len(expected_chapters) if expected_chapters else 0,
            "missing_chapters": sorted(missing_chapters),
            "extra_chapters": sorted(extra_chapters),
            "average_scenes_per_chapter": sum(scene_distribution.values()) / len(scene_distribution) if scene_distribution else 0,
            "scene_distribution": scene_distribution,
            "issues": []
        }
        
        # 识别问题
        if missing_chapters:
            coverage_analysis["issues"].append(f"缺失{len(missing_chapters)}个章节的场景规划: {sorted(missing_chapters)}")
        
        if extra_chapters:
            coverage_analysis["issues"].append(f"存在{len(extra_chapters)}个超出阶段范围的章节: {sorted(extra_chapters)}")
        
        # 检查场景数量合理性
        for chapter_num, scene_count in scene_distribution.items():
            if scene_count < 3:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过少({scene_count}个)，可能无法形成完整结构")
            elif scene_count > 8:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过多({scene_count}个)，可能导致节奏过快")
        
        return coverage_analysis    

    def _optimize_based_on_coherence_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        """
        【AI驱动版】基于目标层级一致性评估结果，调用AI来优化事件目标层级。
        """
        critical_breakpoints = assessment.get("critical_breakpoints", [])
        improvement_recommendations = assessment.get("improvement_recommendations", [])

        if not critical_breakpoints and not improvement_recommendations:
            print("  ✅ AI评估未发现严重的目标层级问题，无需优化。")
            return writing_plan
        
        print(f"  🔧 指示AI根据目标层级评估，开始优化 {stage_name} 阶段事件目标链...")

        # 构建优化指令
        optimization_prompt = self._build_hierarchy_optimization_prompt(
            writing_plan, assessment, stage_name, stage_range
        )

        # 调用AI进行优化
        try:
            optimization_result = self.generator.api_client.generate_content_with_retry(
                content_type="ai_hierarchy_optimization",
                user_prompt=optimization_prompt,
                purpose=f"优化{stage_name}阶段事件目标层级"
            )
            
            if optimization_result and "optimized_event_system" in optimization_result:
                # 用AI返回的优化后的事件系统替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan

                # 核心操作：替换整个事件系统
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["hierarchy_optimized"] = True
                
                # 打印AI提供的修改摘要
                summary = optimization_result.get("summary_of_hierarchy_changes", "AI未提供修改摘要。")
                print(f"  ✅ AI目标层级优化执行完成。修改摘要: {summary}")

            else:
                print("  ⚠️ AI目标层级优化失败，未能返回有效的优化后事件系统。")

        except Exception as e:
            print(f"  ❌ 在执行AI目标层级优化时发生错误: {e}")

        return writing_plan

    def _build_hierarchy_optimization_prompt(self, writing_plan: Dict, assessment: Dict, 
                                    stage_name: str, stage_range: str) -> str:
        """构建目标层级优化提示词"""
        
        # 提取当前事件系统
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})

        # 构建优化提示词
        prompt = f"""
    # 任务：小说事件目标层级优化

    作为一名顶尖的剧情架构师，你刚刚对一份小说事件计划的目标层级进行了评估，发现了一些目标传递断裂的问题。现在，你的任务是**亲自动手**，根据评估建议来修复这些目标层级问题。

    ## 1. 当前的事件计划 ({stage_name}, {stage_range})

    这是你需要修复目标层级问题的原始事件计划：
    ```json
    {json.dumps(event_system, ensure_ascii=False, indent=2)}
2. 目标层级评估发现的问题
这是评估发现的关键问题：

json
{json.dumps(assessment.get('critical_breakpoints', []), ensure_ascii=False, indent=2)}
3. 具体的改进建议
这是针对上述问题的改进建议：

json
{json.dumps(assessment.get('improvement_recommendations', []), ensure_ascii=False, indent=2)}
4. 修复指令
请严格遵循评估建议，对上述的"当前事件计划"进行目标层级修复：

修复重点：
目标传递断裂: 修复重大事件→中型事件→章节事件→场景事件之间的目标传递断裂

贡献关系模糊: 为缺少明确贡献关系的事件添加具体的contribution_to_*字段

情绪目标不一致: 确保情绪目标在层级间保持连贯

目标过于抽象: 将抽象的目标转化为具体、可执行的目标

修复方法：
对于目标传递断裂：重新设计断裂点事件的目标，确保其明确服务于上一级事件目标

对于贡献关系模糊：在对应事件的contribution_to_*字段中添加具体说明

对于情绪目标不一致：调整情绪相关字段，确保情绪发展逻辑连贯

对于目标过于抽象：将目标分解为更具体、可衡量的子目标

保持结构完整：
确保你返回的最终结果是一个完整且格式正确的event_system JSON对象。

5. 返回格式
请严格按照以下JSON格式返回你的工作成果。不要包含任何额外的解释。

{{
"optimized_event_system": {{
"major_events": [
// ... 修复目标层级后的重大事件列表
],
"medium_events": [
// ... 修复目标层级后的中型事件列表
],
"minor_events": [
// ... 修复目标层级后的小型事件列表
],
"special_events": [
// ... 修复目标层级后的特殊事件列表
]
}},
"summary_of_hierarchy_changes": "用一句话总结你在目标层级方面所做的主要修改。例如：'修复了3处目标传递断裂，为5个事件添加了明确的贡献关系说明。'"
}}
"""
        return prompt

    def generate_stage_writing_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                    novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """【智能分形版】生成阶段详细写作计划 - 带增强重试"""
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]

        print(f"🎬 开始为【{stage_name}】生成智能分形写作计划...")

        start_chap, end_chap = self.parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
        stage_emotional_plan = self.generator.emotional_plan_manager.generate_stage_emotional_plan(
            stage_name, stage_range, emotional_blueprint
        )
        density_requirements = self.event_manager.calculate_optimal_event_density_by_stage(stage_name, stage_length)

        print("   fase 1: 规划阶段的'主龙骨' (重大事件框架)...")
        # 增加重试机制
        major_event_skeletons = None
        for attempt in range(3):
            try:
                major_event_skeletons = self._generate_major_event_skeleton(
                    stage_name, stage_range, novel_title, novel_synopsis, creative_seed,
                    stage_emotional_plan, overall_stage_plan, density_requirements
                )
                if major_event_skeletons:
                    break
                else:
                    print(f"    ⚠️ 第{attempt+1}次生成主龙骨失败")
            except Exception as e:
                print(f"    ❌ 第{attempt+1}次生成主龙骨出错: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
        
        # 如果所有重试都失败，记录错误并返回空
        if not major_event_skeletons:
            print(f"    🚨 主龙骨生成失败，所有重试均失败")
            return {}

        print("   fase 2: 逐一'解剖'重大事件，填充中型事件...")
        fleshed_out_major_events = []
        for skeleton in major_event_skeletons:
            print(f"    -> 正在解剖重大事件: '{skeleton['name']}' ({skeleton['chapter_range']})")
            
            # 增加重试机制
            fleshed_out_event = None
            for attempt in range(3):
                try:
                    fleshed_out_event = self._decompose_major_event(
                        skeleton, stage_name, stage_range, novel_title, novel_synopsis, creative_seed
                    )
                    if fleshed_out_event:
                        break
                    else:
                        print(f"      ⚠️ 第{attempt+1}次解剖失败")
                except Exception as e:
                    print(f"      ❌ 第{attempt+1}次解剖出错: {e}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
            
            if fleshed_out_event:
                fleshed_out_major_events.append(fleshed_out_event)
            else:
                print(f"    🚨 重大事件 '{skeleton['name']}' 解剖失败，所有重试均失败")
                # 不创建回退，直接跳过这个事件

        # 如果没有成功解剖任何重大事件，记录错误并返回空
        if not fleshed_out_major_events:
            print(f"    🚨 所有重大事件解剖失败，无法继续生成写作计划")
            return {}

        # 🆕 调整：在生成场景之前进行验证
        print("   🔍 验证事件结构和连续性...")
        
        # 构建临时计划用于验证（不包含场景事件）
        temp_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "event_system": {
                    "major_events": fleshed_out_major_events
                }
            }
        }
        
        # 验证目标层级一致性
        goal_coherence = self.validate_goal_hierarchy_coherence(temp_plan, stage_name)
        
        # 验证事件连续性
        continuity_assessment = self.assess_stage_event_continuity(
            temp_plan, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )
        
        # 根据验证结果优化事件结构
        if goal_coherence.get("overall_coherence_score", 10) < 8.0:
            print(f"  ⚠️ 目标层级一致性评分较低 ({goal_coherence.get('overall_coherence_score', 0):.1f})，进行优化...")
            temp_plan = self._optimize_based_on_coherence_assessment(
                temp_plan, goal_coherence, stage_name, stage_range
            )
            fleshed_out_major_events = temp_plan["stage_writing_plan"]["event_system"]["major_events"]
        
        if continuity_assessment.get("overall_continuity_score", 10) < 9.5:
            print(f"  ⚠️ 阶段事件连续性评分较低，进行优化...")
            temp_plan = self._optimize_based_on_continuity_assessment(
                temp_plan, continuity_assessment, stage_name, stage_range
            )
            fleshed_out_major_events = temp_plan["stage_writing_plan"]["event_system"]["major_events"]

        # 🆕 调整：验证通过后再生成场景
        print("   fase 3: 智能分解中型事件...")
        final_major_events = []
        for major_event in fleshed_out_major_events:
            print(f"    -> 正在智能分解: '{major_event['name']}'")
            
            # 增加重试机制
            smart_decomposed_event = None
            for attempt in range(3):
                try:
                    smart_decomposed_event = self._smart_decompose_medium_events(
                        major_event, stage_name, novel_title, novel_synopsis, creative_seed
                    )
                    if smart_decomposed_event:
                        break
                    else:
                        print(f"      ⚠️ 第{attempt+1}次智能分解失败")
                except Exception as e:
                    print(f"      ❌ 第{attempt+1}次智能分解出错: {e}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
            
            if smart_decomposed_event:
                final_major_events.append(smart_decomposed_event)
            else:
                print(f"    🚨 重大事件 '{major_event['name']}' 智能分解失败，所有重试均失败")
                # 不创建回退，直接跳过这个事件

        # 如果没有成功分解任何重大事件，记录错误并返回空
        if not final_major_events:
            print(f"    🚨 所有重大事件智能分解失败，无法继续生成写作计划")
            return {}

        print("   fase 4: 组装最终的写作计划...")
        final_writing_plan = self._assemble_final_plan(
            stage_name, stage_range, final_major_events, overall_stage_plan,
            novel_title, novel_synopsis, creative_seed
        )

        # 🆕 调整：只进行轻量级的场景覆盖验证
        print("   🎬 进行场景规划覆盖验证...")
        scene_coverage = self.validate_scene_planning_coverage(final_writing_plan, stage_name, stage_range)
        
        if scene_coverage["coverage_rate"] < 1.0:
            print(f"  ⚠️ 场景规划覆盖不完整 ({scene_coverage['coverage_rate']:.1%})")
            for issue in scene_coverage["issues"][:2]:  # 只显示前2个问题
                print(f"     ⚠️ {issue}")

        # 保存验证结果
        if "stage_writing_plan" in final_writing_plan:
            final_writing_plan["stage_writing_plan"]["goal_hierarchy_assessment"] = goal_coherence
            final_writing_plan["stage_writing_plan"]["continuity_assessment"] = continuity_assessment
            final_writing_plan["stage_writing_plan"]["scene_coverage_analysis"] = scene_coverage
        else:
            final_writing_plan["goal_hierarchy_assessment"] = goal_coherence
            final_writing_plan["continuity_assessment"] = continuity_assessment
            final_writing_plan["scene_coverage_analysis"] = scene_coverage

        # 最终验证和保存
        final_writing_plan = self._validate_and_optimize_writing_plan(
            final_writing_plan, stage_name, stage_range
        )

        if final_writing_plan:
            # 保存到文件，并更新主数据文件中的路径
            file_path = self._save_plan_to_file(stage_name, final_writing_plan)
            
            self.stage_writing_plans_cache[cache_key] = final_writing_plan
            
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            
            # 修复：使用安全的路径处理方式
            if file_path:
                # 尝试获取项目路径，如果不存在则使用当前工作目录
                try:
                    project_path = getattr(self.generator, 'project_path', Path.cwd())
                    relative_path = file_path.relative_to(project_path)
                except (AttributeError, ValueError):
                    # 如果无法获取相对路径，则使用绝对路径
                    relative_path = file_path
            else:
                relative_path = f"plans/{stage_name}_writing_plan.json"
            
            self.generator.novel_data["stage_writing_plans"][stage_name] = {"path": str(relative_path)}
            
            print(f"  ✅ 【{stage_name}】分形写作计划生成完成！")
            self._print_fractal_plan_summary(final_writing_plan)
            return final_writing_plan
        else:
            print(f"  🚨 【{stage_name}】写作计划生成失败。")
            return {}

    def _generate_major_event_skeleton(self, stage_name, stage_range, novel_title, novel_synopsis,
                                       creative_seed, stage_emotional_plan, overall_stage_plan,
                                       density_requirements) -> List[Dict]:
        """工作流第一阶段：仅生成重大事件的框架。"""
        prompt = f"""
# 任务：小说阶段"主龙骨"设计
作为顶级的剧情架构师，你的任务是为小说的【{stage_name}】({stage_range})规划出宏观的"主龙骨"。你只需专注于设计 **{density_requirements['major_events']}个** 相互关联、构成完整"起承转合"结构的**重大事件**。

## 核心上下文
- **小说**: {novel_title} - {novel_synopsis}
- **阶段总体目标**: {overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")}
- **阶段情绪弧线**: {stage_emotional_plan.get('main_emotional_arc', 'N/A')}

## 设计要求
1.  **结构**: 你设计的这 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于【阶段总体目标】的"起、承、转、合"叙事链条。
2.  **分工**: 明确每个重大事件在阶段"起承转合"中的作用。
3.  **章节估算**: 为每个重大事件估算一个大致的章节范围，确保它们能覆盖整个 {stage_range}。

## 输出格式: 严格返回一个JSON列表
[
    {{
        "name": "string // 第一个重大事件的名称",
        "role_in_stage_arc": "起",
        "chapter_range": "string // 估算的章节范围 (例如：'49-58章')",
        "main_goal": "string // 这个重大事件的核心目标",
        "emotional_arc": "string // 此事件要带给读者的核心情感体验",
        "description": "string // 对该事件的简要描述"
    }},
    // ... more major events
]
"""
        result = self.generator.api_client.generate_content_with_retry(
            content_type="stage_major_event_skeleton", 
            user_prompt=prompt, 
            purpose=f"生成{stage_name}主龙骨"
        )
        return result if isinstance(result, list) else None

    def _decompose_major_event(self, major_event_skeleton: Dict, stage_name: str, stage_range: str,
                            novel_title: str, novel_synopsis: str, creative_seed: str) -> Dict:
        """工作流第二阶段：将单个重大事件分解为服务其目标的中型事件"""
        
        prompt = f"""
    # 任务：重大事件"分形解剖" - 服务于重大事件目标
    你需要将一个宏观的"重大事件"进行"解剖"，为其设计内部的、更为详细的"起承转合"结构，由3-5个中型事件构成。

    ## 当前重大事件信息
    - **所属阶段**: {stage_name}
    - **重大事件名称**: {major_event_skeleton.get('name')}
    - **事件章节范围**: {major_event_skeleton.get('chapter_range')}
    - **事件核心目标**: {major_event_skeleton.get('main_goal')}
    - **事件情绪目标**: {major_event_skeleton.get('emotional_goal')}

    ## 分解原则
    1. **目标继承**: 每个中型事件必须服务于其所属重大事件的【核心目标】和【情绪目标】
    2. **情绪递进**: 中型事件的排列要形成情绪递进，服务于重大事件的情绪目标
    3. **功能分工**: 每个中型事件在重大事件内部承担明确的"起承转合"功能

    ## 输出格式: 严格返回一个包含'composition'字段的JSON对象
    {{
        "name": "{major_event_skeleton.get('name')}",
        "type": "major_event",
        "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
        "main_goal": "{major_event_skeleton.get('main_goal')}",
        "emotional_goal": "{major_event_skeleton.get('emotional_goal')}",
        "chapter_range": "{major_event_skeleton.get('chapter_range')}",
        "composition": {{
            "起": [ 
                {{ 
                    "name": "中型事件名", 
                    "type": "medium_event", 
                    "chapter_range": "string // 章节范围，例如：'49-52章'", 
                    "main_goal": "目标（服务于重大事件目标的起部分）",
                    "emotional_focus": "string // 此中型事件的情绪重点（服务于重大事件情绪目标的起始部分）",
                    "emotional_intensity": "low/medium/high",
                    "key_emotional_beats": ["情感节拍1", "情感节拍2"],
                    "description": "描述",
                    "contribution_to_major": "string // 如何服务于重大事件目标"
                }} 
            ],
            "承": [ 
                {{ 
                    "name": "中型事件名", 
                    "type": "medium_event", 
                    "chapter_range": "string // 章节范围，例如：'53-55章'", 
                    "main_goal": "目标（服务于重大事件目标的承部分）",
                    "emotional_focus": "string // 此中型事件的情绪重点（服务于重大事件情绪目标的发展部分）", 
                    "emotional_intensity": "low/medium/high",
                    "key_emotional_beats": ["情感节拍1", "情感节拍2"],
                    "description": "描述",
                    "contribution_to_major": "string // 如何服务于重大事件目标"
                }} 
            ],
            "转": [ 
                {{ 
                    "name": "中型事件名", 
                    "type": "medium_event", 
                    "chapter_range": "string // 章节范围，例如：'56-57章'", 
                    "main_goal": "目标（服务于重大事件目标的转部分）",
                    "emotional_focus": "string // 此中型事件的情绪重点（服务于重大事件情绪目标的高潮部分）",
                    "emotional_intensity": "low/medium/high", 
                    "key_emotional_beats": ["情感节拍1", "情感节拍2"],
                    "description": "描述",
                    "contribution_to_major": "string // 如何服务于重大事件目标"
                }} 
            ],
            "合": [ 
                {{ 
                    "name": "中型事件名", 
                    "type": "medium_event", 
                    "chapter_range": "string // 章节范围，例如：'58-58章'", 
                    "main_goal": "目标（服务于重大事件目标的合部分）",
                    "emotional_focus": "string // 此中型事件的情绪重点（服务于重大事件情绪目标的收尾部分）",
                    "emotional_intensity": "low/medium/high",
                    "key_emotional_beats": ["情感节拍1", "情感节拍2"],
                    "description": "描述",
                    "contribution_to_major": "string // 如何服务于重大事件目标"
                }} 
            ]
        }},
        "emotional_arc_summary": "string // 整个重大事件的情绪发展总结",
        "aftermath": "string // 整个重大事件结束后的长远影响"
    }}
    """

        result = self.generator.api_client.generate_content_with_retry(
            content_type="major_event_decomposition", 
            user_prompt=prompt, 
            purpose=f"解剖事件'{major_event_skeleton.get('name')}'（服务重大事件目标）"
        )
        
        return result

    def _validate_and_optimize_writing_plan(self, writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        """验证并优化写作计划"""
        if not writing_plan:
            print(f"  ⚠️ {stage_name}写作计划为空，跳过验证")
            return {}
        
        print(f"  🔍 对 {stage_name} 进行最终验证和优化...")
        
        # 确保所有事件都有正确的chapter_range字段
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 验证重大事件结构
        major_events = event_system.get("major_events", [])
        for event in major_events:
            if "chapter_range" not in event:
                print(f"  ⚠️ 重大事件 '{event.get('name')}' 缺少chapter_range字段")
            else:
                # 验证chapter_range格式是否正确
                try:
                    start_ch, end_ch = parse_chapter_range(event['chapter_range'])
                    if start_ch > end_ch:
                        print(f"  ⚠️ 重大事件 '{event.get('name')}' 的chapter_range格式错误: {event['chapter_range']}")
                except Exception as e:
                    print(f"  ⚠️ 解析重大事件 '{event.get('name')}' 的chapter_range失败: {e}")
        
        # 验证中型事件结构  
        medium_events = event_system.get("medium_events", [])
        for event in medium_events:
            if "chapter_range" not in event:
                print(f"  ⚠️ 中型事件 '{event.get('name')}' 缺少chapter_range字段")
        
        # 增强大事件结构
        writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 验证事件密度
        event_density_ok = self.event_manager.validate_stage_event_density(writing_plan, stage_name, stage_range)
        if not event_density_ok:
            print(f"  ⚠️ {stage_name} 最终事件密度不符合要求。")
        
        # 验证大事件结构
        major_validation = self.event_manager.validate_major_event_structure(major_events)
        
        if not major_validation["is_valid"]:
            print(f"  ⚠️ {stage_name}大事件结构存在问题，进行优化...")
            writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 验证主线连贯性
        is_continuous = self.event_manager.validate_main_thread_continuity(writing_plan, stage_name)
        if not is_continuous:
            print(f"  ⚠️ {stage_name}写作计划存在事件间隔过长问题")
        
        return writing_plan
    
    def _print_fractal_plan_summary(self, writing_plan: Dict):
        """打印分形设计写作计划的摘要，包含场景规划信息"""
        plan = writing_plan.get("stage_writing_plan", {})
        event_system = plan.get("event_system", {})
        major_events = event_system.get("major_events", [])
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        
        # 获取分析结果
        hierarchy_assessment = plan.get("goal_hierarchy_assessment", {})
        coherence_score = hierarchy_assessment.get("overall_coherence_score", "未评估")
        scene_coverage = plan.get("scene_coverage_analysis", {})
        coverage_rate = scene_coverage.get("coverage_rate", 0)
        
        print("=" * 60)
        print(f"📄 阶段计划摘要: {plan.get('stage_name')} ({plan.get('chapter_range')})")
        print(f"🎯 目标层级一致性: {coherence_score}/10 | 🎬 场景覆盖: {coverage_rate:.1%}")
        
        # 场景规划统计
        total_scenes = sum(len(chapter["scene_events"]) for chapter in chapter_scene_events)
        avg_scenes = total_scenes / len(chapter_scene_events) if chapter_scene_events else 0
        print(f"📊 场景规划: {len(chapter_scene_events)}章, {total_scenes}个场景 (平均{avg_scenes:.1f}场景/章)")
        
        if hierarchy_assessment.get("hierarchy_strengths"):
            print(f"✅ 优势: {', '.join(hierarchy_assessment['hierarchy_strengths'][:2])}")
        
        if scene_coverage.get("issues"):
            print(f"⚠️  场景问题: {scene_coverage['issues'][0]}" if scene_coverage['issues'] else "")
        
        print(f"\n🚨 主龙骨包含 {len(major_events)} 个重大事件:")
        
        for i, major_event in enumerate(major_events, 1):
            name = major_event.get('name')
            role = major_event.get('role_in_stage_arc')
            ch_range = major_event.get('chapter_range', 'N/A')
            composition = major_event.get('composition', {})
            sub_event_count = sum(len(v) for v in composition.values())
            print(f"    {i}. 【{role}】{name} ({ch_range})")
            print(f"       - 目标: {major_event.get('main_goal')}")
            print(f"       - 情绪目标: {major_event.get('emotional_goal', '未指定')}")
            print(f"       - 分解为 {sub_event_count} 个中型事件")
            
            # 显示中型事件简要信息
            for phase, events in composition.items():
                for event in events[:2]:  # 只显示前2个中型事件
                    decomp_type = event.get('decomposition_type', '')
                    scene_count = len(event.get('scene_sequences', [])) if decomp_type == 'direct_scene' else '多层分解'
                    print(f"         ◦ {event.get('name')} ({phase}, {scene_count}场景序列)")
        print("=" * 60)

    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文 - 基于场景事件"""
        context = self.writing_guidance_manager.get_chapter_writing_context(chapter_number)
        
        stage_name = self._get_current_stage(chapter_number)
        if not stage_name:
            return context

        stage_plan_data = self.get_stage_writing_plan_by_name(stage_name)
        if not stage_plan_data:
            return context
            
        event_system = stage_plan_data.get("stage_writing_plan", {}).get("event_system", {})
        
        # 获取该章节的场景事件
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        current_chapter_scenes = None
        
        for chapter_scene in chapter_scene_events:
            if chapter_scene.get("chapter_number") == chapter_number:
                current_chapter_scenes = chapter_scene.get("scene_events", [])
                break
        
        context['scene_events'] = current_chapter_scenes
        
        return context

    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        return self.writing_guidance_manager.generate_writing_guidance_prompt(chapter_number)

    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """【重构版】通过阶段名称获取写作计划，优先从缓存和文件加载。"""
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        # 尝试从文件加载
        plan = self._load_plan_from_file(stage_name)
        if plan:
            print(f"  📂 从文件加载了 {stage_name} 的写作计划。")
            self.stage_writing_plans_cache[cache_key] = plan
            return plan
        
        # 如果文件不存在，则可能需要触发生成流程
        print(f"  ⚠️ {stage_name} 的写作计划文件未找到，需要生成。")
        return {}
    
    def _save_plan_to_file(self, stage_name: str, plan_data: Dict) -> Path:
        """将阶段计划保存到JSON文件。"""
        # 使用小说标题作为文件名的一部分，避免覆盖
        novel_title = plan_data.get("stage_writing_plan", {}).get("novel_metadata", {}).get("title", "unknown")
        safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # 限制长度
        
        file_path = self.plans_dir / f"{safe_title}_{stage_name}_writing_plan.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=4)
            print(f"  💾 阶段计划已保存到: {file_path}")
            return file_path
        except Exception as e:
            print(f"  ❌ 保存计划文件失败: {file_path}, 错误: {e}")
            return None

    def _load_plan_from_file(self, stage_name: str) -> Optional[Dict]:
        """从JSON文件加载阶段计划。"""
        # 尝试构建可能的文件名模式
        novel_title = self.generator.novel_data.get("novel_title", "unknown")
        safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]
        
        # 尝试新的命名模式
        new_pattern_file = self.plans_dir / f"{safe_title}_{stage_name}_writing_plan.json"
        
        if new_pattern_file.exists():
            try:
                with open(new_pattern_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ❌ 加载或解析计划文件失败: {new_pattern_file}, 错误: {e}")
        
        # 回退到旧的路径查找方式
        path_info = self.generator.novel_data.get("stage_writing_plans", {}).get(stage_name, {})
        if "path" in path_info:
            file_path = self.generator.project_path / path_info["path"]
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  ❌ 加载或解析计划文件失败: {file_path}, 错误: {e}")
        
        return None
    
    def get_stage_plan_for_chapter(self, chapter_number: int) -> Dict:
        """为指定章节获取阶段计划 - 此方法现在会通过文件加载。"""
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            print(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
            return {}
        
        stage_plan_data = self.get_stage_writing_plan_by_name(current_stage)
        
        if not stage_plan_data:
            print(f"  ⚠️ 没有找到或加载 {current_stage} 的写作计划")
            return {}
        
        return stage_plan_data.get("stage_writing_plan", stage_plan_data)
                
    def export_events_to_json(self, file_path: str = "novel_events.json"):
        """导出事件到JSON"""
        return self.event_manager.export_events_to_json(file_path)
    
    def get_events_summary(self) -> Dict:
        """获取事件摘要"""
        return self.event_manager.get_events_summary()
    
    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, global_emotional_plan: Dict) -> Dict:
        """生成阶段情绪计划"""
        return self.emotional_manager.generate_stage_emotional_plan(stage_name, stage_range, global_emotional_plan)

    def _get_current_stage(self, chapter_number: int) -> str:
        """获取当前章节所属的阶段名称。"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        if not stage_plan_dict:
            print("  ⚠️ 没有可用的整体阶段计划来确定当前阶段")
            return None
        
        for stage_name, stage_info in stage_plan_dict.items():
            chapter_range_str = stage_info.get("chapter_range", "")
            if is_chapter_in_range(chapter_number, chapter_range_str):
                return stage_name
        
        print(f"  ⚠️ 第{chapter_number}章不在任何已定义的阶段范围内")
        return None

    @staticmethod
    def is_chapter_in_range(chapter: int, range_str: str) -> bool:
        """
        检查指定章节是否在给定的章节范围内。
        支持格式："1-100"、"1-100章"、"109-110章"等。
        """
        try:
            # 移除"章"字和其他非数字字符（除了横杠和数字）
            cleaned_str = range_str.replace("章", "").strip()
            
            if "-" in cleaned_str:
                parts = cleaned_str.split("-")
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    return start <= chapter <= end
            else:
                # 如果只有单个数字
                target_chapter = int(cleaned_str)
                return chapter == target_chapter
                
        except (ValueError, AttributeError, IndexError):
            print(f"⚠️ 解析章节范围失败: '{range_str}'，返回False")
            return False

    def _get_stage_length(self, stage_range: str) -> int:
        """获取阶段长度"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        return end_chap - start_chap + 1

    def get_stage_specific_guidance(self, stage_name: str) -> str:
        """获取阶段特定的写作指导"""
        stage_guidance = {
            "opening_stage": "## 🚀 起 (开局阶段): 一切为7日留存服务。核心是快速建立冲突，用强力钩子抓住读者。",
            "development_stage": "## 📈 承 (发展阶段): 节奏变化与全面升级。核心是深化矛盾，让角色在挑战中成长，并扩展世界观。",
            "climax_stage": "## ⚡ 转 (高潮阶段): 矛盾总爆与情感宣泄。核心是让所有线索汇集并爆发，带来颠覆性转折和情感顶点。",
            "ending_stage": "## 🏁 合 (结局阶段): 尘埃落定与意蕴悠长。核心是解决所有问题，回收所有伏笔，给予读者情感满足和回味空间。"
        }
        return stage_guidance.get(stage_name, "## 阶段写作指导\n\n请根据故事发展需要合理安排事件。")

    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)

    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_plans or "overall_stage_plan" not in overall_plans:
            print(f"  ⚠️ 无法从整体计划中找到 {stage_name} 的范围，使用默认值。")
            return "1-100" 
        
        stage_plan_dict = overall_plans["overall_stage_plan"]
        stage_info = stage_plan_dict.get(stage_name)
        
        if stage_info and "chapter_range" in stage_info:
            return stage_info["chapter_range"]
        
        print(f"  ⚠️ 在整体计划字典中未找到 {stage_name} 的章节范围，使用默认值。")
        return "1-100"

    def assess_stage_event_continuity(self, stage_writing_plan: Dict, stage_name: str, 
                                    stage_range: str, creative_seed: str, 
                                    novel_title: str, novel_synopsis: str) -> Dict:
        """AI评估阶段事件连续性 - 新增方法"""
        print(f"  🤖 AI评估{stage_name}阶段事件连续性...")
        
        # 提取事件系统
        if "stage_writing_plan" in stage_writing_plan:
            event_system = stage_writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = stage_writing_plan.get("event_system", {})
        
        # 构建连续性评估提示词
        continuity_prompt = self._build_stage_continuity_prompt(
            event_system, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )
        
        try:
            continuity_assessment = self.generator.api_client.generate_content_with_retry(
                content_type="stage_event_continuity",
                user_prompt=continuity_prompt,
                purpose=f"评估{stage_name}阶段事件连续性"
            )
            
            if continuity_assessment:
                # 将评估结果整合到写作计划中
                if "stage_writing_plan" in stage_writing_plan:
                    stage_writing_plan["stage_writing_plan"]["continuity_assessment"] = continuity_assessment
                else:
                    stage_writing_plan["continuity_assessment"] = continuity_assessment
                
                print(f"  ✅ {stage_name}阶段事件连续性评估完成")
                return continuity_assessment
            else:
                print(f"  ⚠️ {stage_name}阶段事件连续性评估失败")
                return {}
                
        except Exception as e:
            print(f"  ❌ AI连续性评估出错: {e}")
            return {}

    def _build_stage_continuity_prompt(self, event_system: Dict, stage_name: str, stage_range: str,
                                    creative_seed: str, novel_title: str, novel_synopsis: str) -> str:
        """构建阶段事件连续性评估提示词"""
        
        # 提取和格式化事件信息
        major_events = event_system.get("major_events", [])
        medium_events = event_system.get("medium_events", [])
        minor_events = event_system.get("minor_events", [])
        
        prompt_parts = [
            "# 🎯 阶段事件连续性深度评估",
            "",
            "## 评估任务",
            f"请对**{stage_name}**阶段（{stage_range}）的事件安排进行连续性深度评估。",
            "重点分析事件之间的逻辑连贯性、节奏合理性和情感发展连续性。",
            "",
            "## 小说基本信息",
            f"- 标题: {novel_title}",
            f"- 简介: {novel_synopsis}",
            f"- 创意种子: {creative_seed}",
            f"- 阶段: {stage_name} ({stage_range})",
            "",
            "## 事件安排详情"
        ]
        
        # 重大事件详情
        if major_events:
            prompt_parts.extend([
                "### 🚨 重大事件安排",
                "| 事件名称 | 章节范围 | 核心目标 |",
                "|---------|---------|----------|"
            ])
            for event in major_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | {event.get('chapter_range', '?')} | {event.get('main_goal', '未指定')} |"
                )
            prompt_parts.append("")
        
        # 中型事件详情
        if medium_events:
            prompt_parts.extend([
                "### 📈 中型事件安排",
                "| 事件名称 | 章节范围 | 核心目标 | 关联重大事件 |",
                "|---------|---------|----------|-------------|"
            ])
            for event in medium_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | {event.get('chapter_range', '?')} | "
                    f"{event.get('main_goal', '未指定')} | {event.get('connection_to_major', '独立')} |"
                )
            prompt_parts.append("")
        
        # 小型事件详情
        if minor_events:
            prompt_parts.extend([
                "### 🔍 小型事件安排",
                f"共{len(minor_events)}个小型事件，分布在各个章节"
            ])
            # 只显示前几个小型事件作为示例
            for i, event in enumerate(minor_events[:3]):
                prompt_parts.append(f"- {event.get('name', '未命名')} ({event.get('chapter_range', '?')}): {event.get('function', '未指定功能')}")
            if len(minor_events) > 3:
                prompt_parts.append(f"- ... 还有{len(minor_events)-3}个小型事件")
            prompt_parts.append("")
        
        # 事件时间线分析
        prompt_parts.extend([
            "## 📊 事件时间线分析",
            "请基于以上事件安排，分析以下维度：",
            "",
            "### 1. 逻辑连贯性分析",
            "- 事件之间的因果关系是否清晰？",
            "- 是否存在逻辑断层或跳跃？", 
            "- 事件发展是否符合角色动机和世界观设定？",
            "- 伏笔设置和回收是否合理？",
            "",
            "### 2. 节奏合理性分析",
            "- 事件密度分布是否合理？",
            "- 高潮与平缓的交替是否恰当？",
            "- 是否有事件过于密集或稀疏的区域？",
            "- 节奏是否符合该阶段的特点？",
            "",
            "### 3. 情感发展连续性",
            "- 情感弧线是否连贯自然？",
            "- 情感高潮的铺垫是否充分？",
            "- 情感变化是否符合角色发展轨迹？",
            "",
            "### 4. 主线推进连贯性", 
            "- 主线情节是否持续有推进？",
            "- 是否存在主线停滞过久的问题？",
            "- 支线与主线的关联是否合理？",
            "",
            "### 5. 阶段过渡合理性",
            "- 与前后阶段的衔接是否自然？",
            "- 阶段内部的事件安排是否服务于阶段目标？",
            "",
            "## 🎯 评估要求",
            "请提供具体的、可操作的评估结果和改进建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_continuity_score": 0-10的带一位小数的评分,',
            '  "logic_coherence_analysis": "逻辑连贯性详细分析",',
            '  "rhythm_analysis": "节奏合理性详细分析",',
            '  "emotional_continuity_analysis": "情感发展连续性分析",',
            '  "main_thread_analysis": "主线推进连贯性分析",',
            '  "stage_transition_analysis": "阶段过渡合理性分析",',
            '  "critical_issues": ["关键问题1", "关键问题2", ...],',
            '  "improvement_recommendations": [',
            '    {"issue": "具体问题", "suggestion": "改进建议", "priority": "high/medium/low"},',
            '    ...',
            '  ],',
            '  "event_adjustment_suggestions": [',
            '    {"event_name": "事件名称", "current_arrangement": "当前安排", "suggested_adjustment": "调整建议"},',
            '    ...',
            '  ],',
            '  "risk_chapters": ["存在风险的章节列表"],',
            '  "strengths": ["优势1", "优势2", ...]',
            "}"
        ])
        
        return "\n".join(prompt_parts)

    def _optimize_based_on_continuity_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        """
        【AI驱动版】基于连续性评估结果，调用AI来执行事件安排的优化。
        """
        all_suggestions = assessment.get("improvement_recommendations", []) + \
                        assessment.get("event_adjustment_suggestions", [])

        if not all_suggestions:
            print("  ✅ AI评估未提出具体事件调整建议，无需优化。")
            return writing_plan
        
        print(f"  🔧 指示AI根据评估建议，开始优化 {stage_name} 阶段事件安排...")

        # 1. 构建一个清晰的指令，让AI执行自己的建议
        optimization_prompt = self._build_optimization_prompt(writing_plan, assessment, stage_name, stage_range)

        # 2. 调用AI，让它返回一个修改后的完整事件系统
        try:
            optimization_result = self.generator.api_client.generate_content_with_retry(
                content_type="ai_event_plan_optimization",
                user_prompt=optimization_prompt,
                purpose=f"执行对{stage_name}阶段的事件优化"
            )
            
            if optimization_result and "optimized_event_system" in optimization_result:
                # 3. 用AI返回的优化后的事件系统，替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan

                # **核心操作：替换整个事件系统**
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["optimized_based_on_continuity"] = True
                
                # 打印AI提供的修改摘要，让日志清晰可查
                summary = optimization_result.get("summary_of_changes", "AI未提供修改摘要。")
                print(f"  ✅ AI优化执行完成。修改摘要: {summary}")

                # 对AI修改后的事件列表进行排序
                for key in ["major_events", "medium_events", "minor_events", "special_events"]:
                    if key in plan_container["event_system"]:
                        def get_start_chapter(event):
                            chapter_range = event.get('chapter_range', '0-0')
                            start_ch, _ = parse_chapter_range(chapter_range)
                            return start_ch
                        plan_container["event_system"][key].sort(key=get_start_chapter)

            else:
                print("  ⚠️ AI优化失败，未能返回有效的优化后事件系统。")

        except Exception as e:
            print(f"  ❌ 在执行AI优化时发生错误: {e}")

        return writing_plan

    def _build_optimization_prompt(self, writing_plan: Dict, assessment: Dict, 
                            stage_name: str, stage_range: str) -> str:
        """构建一个提示词，指示AI根据评估建议来修改事件计划。"""

        # 提取当前事件系统和优化建议
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})

        all_suggestions = assessment.get("improvement_recommendations", []) + \
                        assessment.get("event_adjustment_suggestions", [])

        prompt = f"""
# 任务：小说事件计划修订

作为一名顶尖的剧情编辑，你刚刚对一份小说事件计划进行了评估，并提出了一些改进建议。现在，你的任务是**亲自动手**，根据你自己的建议来修订这份计划。

## 1. 当前的事件计划 ({stage_name}, {stage_range})

这是你需要修改的原始事件计划：
```json
{json.dumps(event_system, ensure_ascii=False, indent=2)}
2. 你的评估与改进建议
这是你之前提出的需要执行的修改清单：

json
{json.dumps(all_suggestions, ensure_ascii=False, indent=2)}
3. 修订指令
请严格遵循你的建议，对上述的"当前事件计划"进行修改。

对于"插入事件"的建议：请在对应的事件列表（如 medium_events）中添加一个新的事件对象。请确保新事件有 name, chapter_range, description 字段。

对于"调整事件"的建议：请找到对应的事件，并在其 description 字段中追加一条备注，说明进行了何种调整。例如："description": "原有描述... [AI优化备注：增加与主角的情感互动，激化矛盾]"。

对于"拆分/合并"等复杂建议：尽力执行。如果一个事件被拆分，请删除旧事件，并添加两个或多个新事件。

保持结构完整：确保你返回的最终结果是一个完整且格式正确的 event_system JSON 对象。

4. 返回格式
请严格按照以下JSON格式返回你的工作成果。不要包含任何额外的解释。

{{
"optimized_event_system": {{
"major_events": [
// ... 修改后的重大事件列表
],
"medium_events": [
// ... 修改后的中型事件列表（可能包含你新插入的事件）
],
"minor_events": [
// ... 修改后的小型事件列表
],
"special_events": [
// ... 修改后的特殊事件列表
]
}},
"summary_of_changes": "用一句话总结你所做的主要修改。例如：'根据建议，在第72章插入了一个中型事件"前哨战"，并调整了"神之子降生"事件的描述。'"
}}
"""
        return prompt