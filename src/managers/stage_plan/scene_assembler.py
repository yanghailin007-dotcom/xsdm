"""
场景组装器 - 负责将分解后的事件组装成最终的写作计划
"""
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.utils.logger import get_logger
from src.managers.StagePlanUtils import parse_chapter_range


class SceneAssembler:
    """场景组装器 - 组装最终的阶段写作计划"""
    
    def __init__(self, api_client, logger_name: str = "SceneAssembler"):
        self.api_client = api_client
        self.logger = get_logger(logger_name)
    
    def assemble_final_plan(self, stage_name: str, stage_range: str,
                          final_major_events: List[Dict], overall_stage_plan: Dict,
                          novel_title: str = "", novel_synopsis: str = "",
                          creative_seed: Any = "") -> Dict:
        """
        组装最终的阶段写作计划（第一阶段版 - 只包含中型事件）
        
        ⚠️ 第一阶段限制：
        - 第一阶段只生成到中级事件（medium events）和特殊情感事件
        - 章节事件和场景事件将在第二阶段生成
        - 因此这里不生成 chapter_scene_events
        
        Args:
            stage_name: 阶段名称
            stage_range: 阶段范围
            final_major_events: 最终的重大事件列表（包含中型事件）
            overall_stage_plan: 整体阶段计划
            novel_title: 小说标题
            novel_synopsis: 小说简介
            creative_seed: 创意种子
            
        Returns:
            组装后的阶段写作计划
        """
        self.logger.info(f"\n  -> [第一阶段] 正在为阶段 '{stage_name}' ({stage_range}) 组装计划。")
        self.logger.info(f"  -> 收到 {len(final_major_events)} 个已分解的重大事件。")
        
        # 构建情感摘要
        emotional_summary = {
            "stage_emotional_arc": overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("emotional_goal", ""),
            "major_events_emotional_summary": [],
            "medium_events_emotional_focus": []
        }
        
        # 统计中型事件和特殊情感事件数量
        total_medium_events = 0
        total_special_events = 0
        
        # 遍历所有重大事件，收集中型事件信息和特殊情感事件
        for major_event in final_major_events:
            self.logger.info(f"    -> 正在处理重大事件: '{major_event.get('name')}'")
            
            # 1. 收集重大事件的情感摘要
            emotional_summary["major_events_emotional_summary"].append({
                "name": major_event.get("name"),
                "emotional_goal": major_event.get("emotional_goal", ""),
                "emotional_arc_summary": major_event.get("emotional_arc_summary", "")
            })
            
            # 2. 遍历重大事件的 'composition'，收集中型事件信息和特殊情感事件
            # 🔥 修复：支持黄金三章的数组格式和标准事件的字典格式
            composition = major_event.get("composition", {})
            if not composition:
                self.logger.warning(f"      ⚠️ 警告: 重大事件 '{major_event.get('name')}' 缺少 'composition' 字段。")
                continue
            
            # 统一处理为(phase_name, events)列表
            composition_items = []
            if isinstance(composition, list):
                # 黄金三章格式：composition是数组，虚拟一个phase_name
                composition_items = [("整体", composition)]
            elif isinstance(composition, dict):
                # 标准事件格式：composition是起承转合字典
                composition_items = composition.items()
            
            for phase_name, phase_events in composition_items:
                if not isinstance(phase_events, list):
                    self.logger.warning(f"      ⚠️ 警告: 重大事件 '{major_event.get('name')}' 的 '{phase_name}' 部分不是一个列表。")
                    continue
                
                for medium_event in phase_events:
                    total_medium_events += 1
                    self.logger.info(f"      -> 中型事件: '{medium_event.get('name')}' (位于'{phase_name}'阶段, 范围: {medium_event.get('chapter_range', 'N/A')})")
                    
                    # 收集中型事件的情感焦点
                    if "emotional_focus" in medium_event:
                        emotional_summary["medium_events_emotional_focus"].append({
                            "name": medium_event.get("name"),
                            "emotional_focus": medium_event.get("emotional_focus"),
                            "emotional_intensity": medium_event.get("emotional_intensity", "medium")
                        })
                    
                    # 3. 收集中型事件中包含的特殊情感事件
                    if "special_emotional_events" in medium_event:
                        special_events = medium_event["special_emotional_events"]
                        if special_events and isinstance(special_events, list):
                            total_special_events += len(special_events)
                            self.logger.info(f"         💫 包含 {len(special_events)} 个特殊情感事件")
                        else:
                            self.logger.warning(f"         ⚠️ 中型事件 '{medium_event.get('name')}' 的 special_emotional_events 字段为空或不是列表")
        
        self.logger.info(f"  ✅ 第一阶段统计：共 {len(final_major_events)} 个重大事件，{total_medium_events} 个中型事件，{total_special_events} 个特殊情感事件")
        
        # 获取阶段概览
        stage_info = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {})
        stage_overview_text = stage_info.get("stage_goal", stage_info.get("core_tasks", "N/A"))
        
        # 组装最终的阶段计划（第一阶段版 - 不包含 chapter_scene_events）
        stage_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": stage_overview_text,
                "novel_metadata": {
                    "title": novel_title,
                    "synopsis": novel_synopsis,
                    "creative_seed": creative_seed,
                    "generation_timestamp": datetime.now().isoformat(),
                    "generation_phase": "phase_one"  # 标记为第一阶段生成
                },
                "emotional_summary": emotional_summary,
                "event_system": {
                    "overall_approach": "第一阶段生成：包含重大事件、中型事件（特殊情感事件附着在中级事件上）。章节事件和场景事件将在第二阶段生成。",
                    "major_events": final_major_events,
                    "chapter_scene_events": []  # 第一阶段为空，第二阶段填充
                },
            }
        }
        
        self.logger.info(f"  ✅ 阶段 '{stage_name}' 的第一阶段计划组装完成！")
        return stage_plan
    
    def generate_fallback_scenes_for_chapter(self, chapter_number: int, stage_name: str,
                                           final_major_events: List[Dict], overall_stage_plan: Dict,
                                           novel_title: str, novel_synopsis: str,
                                           core_worldview: Dict, character_design: Dict,
                                           writing_style_guide: Dict,
                                           previous_chapters_summary: str) -> List[Dict]:
        """
        为缺失场景的章节生成紧急场景规划
        
        Args:
            chapter_number: 章节号
            stage_name: 阶段名称
            final_major_events: 重大事件列表
            overall_stage_plan: 整体阶段计划
            其他参数：上下文信息
            
        Returns:
            生成的场景列表
        """
        self.logger.info(f"  🚑 [补救措施] 启动，为第 {chapter_number} 章生成紧急场景规划...")
        
        # 1. 查找该章节的上下文
        event_context = self._find_chapter_event_context(chapter_number, final_major_events)
        
        # 2. 构建紧急生成Prompt
        stage_goal = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")
        
        prompt = self._build_fallback_scene_prompt(
            chapter_number, novel_title, novel_synopsis, stage_name, stage_goal,
            event_context, previous_chapters_summary, core_worldview,
            character_design, writing_style_guide
        )
        
        # 3. 调用API
        try:
            fallback_result = self.api_client.generate_content_with_retry(
                content_type="fallback_scene_generation",
                user_prompt=prompt,
                purpose=f"紧急补全第{chapter_number}章场景"
            )
            
            if (isinstance(fallback_result, dict) and 
                "fallback_scenes" in fallback_result and 
                isinstance(fallback_result["fallback_scenes"], list) and
                len(fallback_result["fallback_scenes"]) > 0):
                
                scenes_list = fallback_result["fallback_scenes"]
                self.logger.info(f"  ✅ 第 {chapter_number} 章补救成功，生成了 {len(scenes_list)} 个场景。")
                
                # 为每个场景添加默认值
                for scene in scenes_list:
                    scene.setdefault('type', 'scene_event')
                
                return scenes_list
            else:
                self.logger.error(f"  ❌ 第 {chapter_number} 章补救失败，AI未返回有效格式的场景对象。")
                return []
                
        except Exception as e:
            self.logger.error(f"  ❌ 调用补救API时发生错误: {e}")
            return []
    
    def _add_scenes_from_decomposed_event(self, decomposed_event_data: Dict, chapter_scene_map: Dict):
        """从分解的事件中累积场景到章节映射"""
        chapter_range = decomposed_event_data.get("chapter_range")
        if not chapter_range:
            self.logger.warning(f"  ⚠️ 分解事件缺少 'chapter_range'，跳过场景累积: {decomposed_event_data.get('name', '未知事件')}")
            return
        
        start_chapter, end_chapter = parse_chapter_range(chapter_range)
        decomposition_type = decomposed_event_data.get("decomposition_type", "")
        
        if decomposition_type == "chapter_then_scene":
            # 处理章节事件类型
            chapter_events = decomposed_event_data.get("chapter_events", [])
            for chapter_entry in chapter_events:
                target_chapter_num_start, target_chapter_num_end = parse_chapter_range(chapter_entry.get('chapter_range', '0-0'))
                chapter_goal = chapter_entry.get("main_goal", "")
                scene_structure = chapter_entry.get("scene_structure", {})
                writing_focus = scene_structure.get("writing_focus", chapter_entry.get("writing_focus", "未指定写作重点"))
                scenes = scene_structure.get("scenes", [])
                
                target_chapter_num = target_chapter_num_start
                if start_chapter <= target_chapter_num <= end_chapter:
                    if target_chapter_num not in chapter_scene_map:
                        chapter_scene_map[target_chapter_num] = {
                            "chapter_goal": chapter_goal,
                            "writing_focus": writing_focus,
                            "scene_events": []
                        }
                    elif "scene_events" not in chapter_scene_map[target_chapter_num]:
                        chapter_scene_map[target_chapter_num]["scene_events"] = []
                    
                    chapter_scene_map[target_chapter_num]["scene_events"].extend(scenes)
                    
        elif decomposition_type == "direct_scene":
            # 处理直接场景序列类型
            scene_sequences = decomposed_event_data.get("scene_sequences", [])
            if not scene_sequences:
                self.logger.warning(f"  ⚠️ direct_scene 类型中型事件缺少场景序列: {decomposed_event_data.get('name', '未知事件')}")
                return
            
            for sequence in scene_sequences:
                seq_chapter_range = sequence.get('chapter_range', '0-0')
                seq_start_ch, seq_end_ch = parse_chapter_range(seq_chapter_range)
                chapter_goal = sequence.get("chapter_goal", "")
                writing_focus = sequence.get("writing_focus", "")
                scene_events = sequence.get("scene_events", [])
                
                for chapter_num_in_seq in range(seq_start_ch, seq_end_ch + 1):
                    if start_chapter <= chapter_num_in_seq <= end_chapter:
                        if chapter_num_in_seq not in chapter_scene_map:
                            chapter_scene_map[chapter_num_in_seq] = {
                                "chapter_goal": chapter_goal,
                                "writing_focus": writing_focus,
                                "scene_events": []
                            }
                        elif "scene_events" not in chapter_scene_map[chapter_num_in_seq]:
                            chapter_scene_map[chapter_num_in_seq]["scene_events"] = []
                        
                        chapter_scene_map[chapter_num_in_seq]["scene_events"].extend(scene_events)
    
    def _convert_chapter_map_to_list(self, chapter_scene_map: Dict) -> List[Dict]:
        """将章节映射转换为列表"""
        chapter_scene_events_list = []
        all_chapter_nums = sorted(chapter_scene_map.keys())
        
        self.logger.info(f"  -> 场景累积完成，共覆盖 {len(all_chapter_nums)} 个章节。正在转换为最终列表...")
        
        for chapter_num in all_chapter_nums:
            chapter_info = chapter_scene_map[chapter_num]
            if "scene_events" not in chapter_info:
                chapter_info["scene_events"] = []
            
            chapter_scene_events_list.append({
                "chapter_number": chapter_num,
                "chapter_goal": chapter_info.get("chapter_goal", f"完成第{chapter_num}章内容"),
                "writing_focus": chapter_info.get("writing_focus", "保持章节内容连贯性和吸引力"),
                "scene_events": chapter_info.get("scene_events", [])
            })
        
        return chapter_scene_events_list
    
    def _find_chapter_event_context(self, chapter_number: int, major_events: List[Dict]) -> str:
        """查找章节所属的事件上下文"""
        event_context = "未知，请根据阶段总体目标进行常规推进。"
        
        for major_event in major_events:
            if self._is_chapter_in_range(chapter_number, major_event.get("chapter_range", "")):
                event_context = (f"本章属于重大事件 '{major_event.get('name')}'，"
                               f"其目标是: {major_event.get('main_goal')}")
                
                # 进一步查找中型事件（支持两种composition格式）
                composition = major_event.get("composition", {})
                if isinstance(composition, list):
                    # 黄金三章格式：直接遍历数组
                    for medium_event in composition:
                        if self._is_chapter_in_range(chapter_number, medium_event.get("chapter_range", "")):
                            event_context += (f"\n更具体地，属于中型事件 '{medium_event.get('name')}'，"
                                           f"其目标是: {medium_event.get('main_goal')}")
                            break
                elif isinstance(composition, dict):
                    # 标准事件格式：遍历起承转合字典
                    for phase_events in composition.values():
                        for medium_event in phase_events:
                            if self._is_chapter_in_range(chapter_number, medium_event.get("chapter_range", "")):
                                event_context += (f"\n更具体地，属于中型事件 '{medium_event.get('name')}'，"
                                               f"其目标是: {medium_event.get('main_goal')}")
                                break
                break
        
        return event_context
    
    def _is_chapter_in_range(self, chapter: int, range_str: str) -> bool:
        """检查章节是否在范围内"""
        try:
            start, end = parse_chapter_range(range_str)
            return start <= chapter <= end
        except:
            return False
    
    def _build_fallback_scene_prompt(self, chapter_number: int, novel_title: str,
                                    novel_synopsis: str, stage_name: str, stage_goal: str,
                                    event_context: str, previous_summary: str,
                                    core_worldview: Dict, character_design: Dict,
                                    writing_style_guide: Dict) -> str:
        """构建补救场景生成的prompt"""
        worldview_str = str(core_worldview) if core_worldview else "未提供世界观设定。"
        character_str = str(character_design) if character_design else "未提供角色设计。"
        style_guide_str = str(writing_style_guide) if writing_style_guide else "未提供写作风格指南。"
        
        return f"""
任务：紧急场景补全
你好，我是小说生成系统。在我的计划中，第 {chapter_number} 章的场景规划意外丢失了。我需要你根据以下上下文，为这一章紧急生成一个包含4-6个场景的完整场景列表。

上下文信息
小说标题: {novel_title}
小说简介: {novel_synopsis}
当前阶段: {stage_name} (目标: {stage_goal})
本章所属事件: {event_context}
前情提要: {previous_summary}

核心世界观设定:
{worldview_str}

角色设计概览:
{character_str}

写作风格指南:
{style_guide_str}

场景构建要求
请为本章设计 4 到 6 个场景，确保它们共同构成一个有"起、承、转、合"的完整戏剧结构。
每个场景都必须紧密围绕本章的叙事任务和所属阶段目标展开，并与上述世界观、角色和写作风格保持高度一致。
结尾场景应包含一个明确的钩子 (hook)，以吸引读者继续阅读下一章。
"""