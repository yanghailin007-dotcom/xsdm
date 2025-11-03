# EventManager.py
import json
import re
import os
from typing import Dict, List, Optional
from utils import parse_chapter_range

class EventManager:
    """事件管理器 - 负责事件密度、验证、补充、导出等"""
    
    def __init__(self, stage_plan_manager):
        self.stage_plan_manager = stage_plan_manager
        self.generator = stage_plan_manager.generator

    def calculate_optimal_event_density(self, stage_length: int) -> Dict:
        """根据阶段长度智能计算最优事件密度"""
        if stage_length <= 20:
            # 短阶段：减少事件数量
            return {
                "major_events": max(1, stage_length // 20),
                "medium_events": max(2, stage_length // 10),
                "minor_events": max(3, stage_length // 6)
            }
        elif stage_length <= 40:
            # 中等阶段：适中密度
            return {
                "major_events": max(1, stage_length // 15),
                "medium_events": max(2, stage_length // 8),
                "minor_events": max(3, stage_length // 5)
            }
        else:
            # 长阶段：控制最大数量，避免过度复杂
            return {
                "major_events": min(5, stage_length // 15),  # 最多5个重大事件
                "medium_events": min(8, stage_length // 8),  # 最多8个中型事件
                "minor_events": min(12, stage_length // 5)   # 最多12个小型事件
            }

    def calculate_optimal_event_density_by_stage(self, stage_name: str, stage_length: int) -> Dict:
        """基于阶段类型计算最优事件密度 - 大幅优化版本"""
        stage_density_profiles = {
            "opening_stage": {
                "description": "集中几个强力大事件快速吸引读者",
                "major_ratio": 0.7,    # 重大事件70%
                "medium_ratio": 0.2,   # 中型事件20%
                "minor_ratio": 0.1,    # 小型事件10%
                "min_major": 2,        # 至少2个跨章节大事件
                "min_medium": 1,
                "max_minor": 5, 
                "min_major_duration": 3,
                "avg_major_duration": 5
            },
            "development_stage": {
                "description": "2-3个核心大事件贯穿发展阶段",
                "major_ratio": 0.4,    # 重大事件40% - 降低比例，减少数量
                "medium_ratio": 0.4,   # 中型事件40% - 提高比例
                "minor_ratio": 0.2,    # 小型事件20%
                "min_major": 3,        # 最少3个重大事件
                "max_major": 5,        # 新增：最多5个重大事件
                "min_medium": 4,       # 最少4个中型事件
                "max_minor": 8, 
                "min_major_duration": 4,
                "avg_major_duration": 6
            },
            "climax_stage": {
                "description": "重大事件密集，高潮迭起",
                "major_ratio": 0.75,   # 重大事件75% - 进一步提高
                "medium_ratio": 0.2,   # 中型事件20%
                "minor_ratio": 0.05,   # 小型事件5% - 极少
                "min_major": 4,
                "min_medium": 2,
                "max_minor": 5, 
                "min_major_duration": 5,
                "avg_major_duration": 8
            },
            "ending_stage": {
                "description": "解决冲突，收束支线",
                "major_ratio": 0.7,    # 重大事件70%
                "medium_ratio": 0.25,  # 中型事件25%
                "minor_ratio": 0.05,   # 小型事件5%
                "min_major": 2,
                "min_medium": 2,
                "max_minor": 5, 
                "min_major_duration": 4,
                "avg_major_duration": 6
            },
            "final_stage": {
                "description": "专注结局，减少冗余",
                "major_ratio": 0.8,    # 重大事件80% - 极高比例
                "medium_ratio": 0.15,  # 中型事件15%
                "minor_ratio": 0.05,   # 小型事件5%
                "min_major": 2,
                "min_medium": 1,
                "max_minor": 5, 
                "min_major_duration": 3,
                "avg_major_duration": 5
            }
        }
        
        profile = stage_density_profiles.get(stage_name, stage_density_profiles["development_stage"])
        
        # 基于阶段长度计算事件数量 - 更加合理的计算
        if stage_name == "development_stage":
            # 发展阶段：更少但更长的重大事件
            base_events = max(6, min(15, stage_length // 5))  # 减少基础事件数
            major_events = min(profile.get("max_major", 6), 
                            max(profile["min_major"], int(base_events * profile["major_ratio"])))
        else:
            base_events = max(4, min(12, stage_length // 4))
            major_events = max(profile["min_major"], int(base_events * profile["major_ratio"]))
        
        return {
            "major_events": major_events,
            "medium_events": max(profile["min_medium"], int(base_events * profile["medium_ratio"])),
            "minor_events": min(profile.get("max_minor", 10), int(base_events * profile["minor_ratio"])),
            "min_major_duration": profile["min_major_duration"],
            "avg_major_duration": profile["avg_major_duration"],
            "description": profile["description"]
        }
    
    def validate_major_event_structure(self, major_events: List) -> Dict:
        """验证大事件结构是否完整"""
        validation_result = {
            "is_valid": True,
            "issues": [],
            "suggestions": []
        }
        
        for i, event in enumerate(major_events):
            event_name = event.get('name', f'未命名事件{i+1}')
            
            # 检查持续时间
            start_chapter = event.get('start_chapter', 0)
            end_chapter = event.get('end_chapter', start_chapter)
            duration = end_chapter - start_chapter + 1
            
            if duration < 3:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"大事件'{event_name}'持续时间过短：仅{duration}章，建议至少3章")
            
            # 检查是否有完整的事件节点
            key_nodes = event.get('key_nodes', {})
            required_nodes = ['start', 'development', 'climax', 'end']
            missing_nodes = [node for node in required_nodes if node not in key_nodes]
            
            if missing_nodes:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"大事件'{event_name}'缺少关键节点：{', '.join(missing_nodes)}")
            
            # 检查是否有反转设计
            if 'reversal' not in event and 'twist' not in str(event).lower():
                validation_result["suggestions"].append(f"建议为大事件'{event_name}'添加意外反转元素")
            
            # 检查情感弧线
            if 'emotional_arc' not in event:
                validation_result["suggestions"].append(f"建议为大事件'{event_name}'明确情感发展弧线")
        
        return validation_result

    def enhance_major_events_structure(self, writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        """
        增强大事件结构完整性 - 优化版：均匀分配章节
        """
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 获取事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        
        if not major_events:
            return writing_plan
        
        num_major_events = len(major_events)
        
        # 获取平均事件持续时间
        density_reqs = self.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        avg_duration = density_reqs.get("avg_major_duration", 5)

        # 计算每个事件大致可以占据的“时间片”
        # +1 是为了在事件之间留出空隙
        time_slice_per_event = stage_length // (num_major_events + 1) if num_major_events > 0 else stage_length

        enhanced_major_events = []
        
        # 只筛选出那些没有章节号，需要我们分配的事件
        events_to_distribute = [e for e in major_events if 'start_chapter' not in e]
        # 已经有章节号的事件，保持原样
        pre_assigned_events = [e for e in major_events if 'start_chapter' in e]

        # 对需要分配的事件进行均匀分配
        for i, event in enumerate(events_to_distribute):
            # 计算事件的理想起始点
            # 在每个时间片的开头部分开始
            ideal_start = start_chap + (i + 1) * time_slice_per_event
            
            # 确保事件不会超出阶段范围
            event_start = max(start_chap, min(ideal_start, end_chap - avg_duration + 1))
            event_end = min(end_chap, event_start + avg_duration - 1)
            
            # 将计算好的章节号“注入”到事件中，再进行增强
            event['start_chapter'] = event_start
            event['end_chapter'] = event_end
            
            enhanced_event = self._apply_big_event_template(event, stage_name, start_chap, end_chap)
            enhanced_major_events.append(enhanced_event)

        # 将预先分配好章节的事件和我们新分配的事件合并
        all_enhanced_events = sorted(enhanced_major_events + pre_assigned_events, key=lambda x: x['start_chapter'])
        
        # 更新事件系统
        events["major_events"] = all_enhanced_events
        
        if "stage_writing_plan" in writing_plan:
            writing_plan["stage_writing_plan"]["event_system"] = events
        else:
            writing_plan["event_system"] = events
        
        print(f"  ✅ 已增强并均匀分配了{len(major_events)}个大事件的结构")
        return writing_plan

    def _apply_big_event_template(self, event: Dict, stage_name: str, start_chap: int, end_chap: int) -> Dict:
        """应用大事件模板，确保结构完整"""
        event_name = event.get('name', '未命名事件')
        start_chapter = event.get('start_chapter', start_chap)
        end_chapter = event.get('end_chapter', start_chapter + 4)  # 默认5章
        
        # 确保持续时间合理
        duration = end_chapter - start_chapter + 1
        if duration < 2:
            end_chapter = start_chapter + 1  # 至少3章
        
        # 构建完整的事件节点结构
        base_structure = {
            "foreshadowing": f"第{start_chapter}章：事件铺垫，制造期待",
            "trigger": f"第{start_chapter+1}章：事件正式触发",
            "development": f"第{start_chapter+2}章-第{end_chapter-1}章：冲突升级发展",
            "climax": f"第{end_chapter-1}章：高潮爆发",
            "reversal": f"第{end_chapter}章：意外转折",
            "resolution": f"第{end_chapter}章：事件收尾"
        }
        
        # 合并原有结构和基础结构
        existing_key_nodes = event.get('key_nodes', {})
        merged_key_nodes = {**base_structure, **existing_key_nodes}
        
        # 确保情感弧线完整
        emotional_arc = event.get('emotional_arc', 
            "期待→紧张→焦虑→震撼→满足")
        
        # 构建增强后的事件
        enhanced_event = {
            **event,
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "duration": end_chapter - start_chapter + 1,
            "key_nodes": merged_key_nodes,
            "emotional_arc": emotional_arc,
            "plot_impact": event.get('plot_impact', '推动主线重大进展'),
            "character_growth": event.get('character_growth', '主角获得重要成长'),
            "required_elements": [
                "前期铺垫制造期待",
                "明确的事件触发点", 
                "冲突逐步升级",
                "情感高潮时刻",
                "意外反转设计",
                "深远影响后果"
            ]
        }
        
        return enhanced_event    

    def validate_stage_event_density(self, writing_plan: Dict, stage_name: str, stage_range: str) -> bool:
        """验证阶段特定的事件密度是否合理 - 考虑章节占用情况"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 获取阶段特定的密度要求
        density_requirements = self.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        
        # 获取事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 🆕 计算实际可用的章节数（考虑事件占用）
        occupied_chapters = set()
        
        # 收集所有被占用的章节
        for event_type in ["major_events", "medium_events", "minor_events", "special_events"]:
            for event in events.get(event_type, []):
                if event_type == "major_events":
                    start = event.get("start_chapter", 0)
                    end = event.get("end_chapter", start)
                    occupied_chapters.update(range(start, end + 1))
                else:
                    chapter = event.get("chapter", event.get("start_chapter", 0))
                    occupied_chapters.add(chapter)
        
        available_chapter_count = stage_length - len(occupied_chapters)
        
        # 🆕 基于可用章节调整期望值
        adjusted_requirements = self._adjust_density_for_availability(
            density_requirements, available_chapter_count, stage_length
        )
        
        major_events = events.get("major_events", [])
        medium_events = events.get("medium_events", [])
        minor_events = events.get("minor_events", [])
        special_events = events.get("special_events", [])
        
        # 计算实际事件数量
        actual_major = len(major_events)
        actual_medium = len(medium_events)
        actual_minor = len(minor_events)
        actual_special = len(special_events)
        total_events = actual_major + actual_medium + actual_minor + actual_special
        
        # 验证是否满足阶段特定要求（使用调整后的要求）
        major_ok = actual_major >= adjusted_requirements["major_events"]
        medium_ok = actual_medium >= adjusted_requirements["medium_events"]
        minor_ok = actual_minor >= adjusted_requirements["minor_events"]
        
        # 验证大事件持续时间
        duration_ok = True
        for event in major_events:
            duration = event.get('end_chapter', 0) - event.get('start_chapter', 0) + 1
            if duration < adjusted_requirements["min_major_duration"]:
                duration_ok = False
                print(f"  ⚠️ 大事件'{event.get('name')}'持续时间过短：{duration}章，要求至少{adjusted_requirements['min_major_duration']}章")
        
        if not (major_ok and medium_ok and minor_ok and duration_ok):
            print(f"  ⚠️ {stage_name}阶段事件密度不符合要求：")
            print(f"    重大事件: 实际{actual_major}个, 要求至少{adjusted_requirements['major_events']}个")
            print(f"    中型事件: 实际{actual_medium}个, 要求至少{adjusted_requirements['medium_events']}个")
            print(f"    小型事件: 实际{actual_minor}个, 要求至少{adjusted_requirements['minor_events']}个")
            print(f"    特殊事件: 实际{actual_special}个")
            print(f"    大事件最小持续时间: {adjusted_requirements['min_major_duration']}章")
            print(f"    章节占用情况: {len(occupied_chapters)}/{stage_length}章被占用")
            return False
        
        # 计算大事件比例
        major_ratio = actual_major / total_events if total_events > 0 else 0
        print(f"  ✅ {stage_name}阶段事件密度验证通过")
        print(f"  📊 大事件比例：{major_ratio:.1%}）")
        print(f"  📊 章节占用：{len(occupied_chapters)}/{stage_length}章")
        return True

    def _identify_specific_gaps(self, major_events: List, stage_name: str) -> List[Dict]:
        """识别具体的间隔位置"""
        if not major_events:
            return []
        
        sorted_events = sorted(major_events, key=lambda x: x.get('start_chapter', 0))
        gaps = []
        
        # 检查第一个事件之前的间隔
        first_start = sorted_events[0].get('start_chapter', 1)
        if first_start > 1:
            gaps.append({
                "gap_start": 1,
                "gap_end": first_start - 1,
                "gap_length": first_start - 1,
                "description": f"阶段开始到第一个事件之间的间隔"
            })
        
        # 检查事件之间的间隔
        for i in range(1, len(sorted_events)):
            prev_event = sorted_events[i-1]
            current_event = sorted_events[i]
            
            prev_end = prev_event.get('end_chapter', prev_event.get('start_chapter', 0))
            current_start = current_event.get('start_chapter', 0)
            
            gap_length = current_start - prev_end - 1
            if gap_length > 0:
                gaps.append({
                    "gap_start": prev_end + 1,
                    "gap_end": current_start - 1,
                    "gap_length": gap_length,
                    "description": f"'{prev_event.get('name')}' 和 '{current_event.get('name')}' 之间的间隔"
                })
        
        # 只返回超过允许长度的间隔
        stage_max_gaps = {
            "opening_stage": 5,
            "development_stage": 8,
            "climax_stage": 6,
            "ending_stage": 7,
            "final_stage": 10
        }
        max_allowed = stage_max_gaps.get(stage_name, 8)
        
        return [gap for gap in gaps if gap["gap_length"] > max_allowed]

    def _calculate_event_distribution_score(self, major_events: List, stage_name: str) -> float:
        """计算事件分布得分 - 确保事件均匀分布"""
        if not major_events:
            return 0.0
        
        # 获取阶段章节范围
        stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
        stage_info = stage_plans.get("overall_stage_plan", {}).get(stage_name, {})
        chapter_range = stage_info.get("chapter_range", "1-100")
        start_chap, end_chap = parse_chapter_range(chapter_range)
        stage_length = end_chap - start_chap + 1
        
        # 计算事件章节位置
        event_positions = []
        for event in major_events:
            start = event.get('start_chapter', 0)
            end = event.get('end_chapter', start)
            # 使用事件中点作为位置
            midpoint = (start + end) / 2
            event_positions.append(midpoint)
        
        # 理想均匀分布位置
        ideal_positions = []
        for i in range(len(major_events)):
            ideal_pos = start_chap + (i + 1) * (stage_length / (len(major_events) + 1))
            ideal_positions.append(ideal_pos)
        
        # 计算位置偏差
        total_deviation = 0
        for actual, ideal in zip(sorted(event_positions), ideal_positions):
            deviation = abs(actual - ideal) / stage_length
            total_deviation += deviation
        
        average_deviation = total_deviation / len(major_events)
        distribution_score = 1 - average_deviation
        
        return max(0.0, min(1.0, distribution_score))
    
    def supplement_events_with_ai(self, writing_plan: Dict, stage_range: str, creative_seed: str, 
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """使用AI补充事件以提高密度 - 修复空窗期检测版本"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        
        # 获取当前阶段名称
        stage_name = None
        for name, plan in self.generator.novel_data.get("stage_writing_plans", {}).items():
            if plan == writing_plan:
                stage_name = name
                break
        
        if not stage_name:
            if start_chap == 1:
                stage_name = "opening_stage"
            else:
                stage_name = "development_stage"
        
        # 🆕 首先获取真正可用的空窗期章节
        truly_empty_chapters = self._get_truly_empty_chapters(writing_plan, stage_range)
        
        if not truly_empty_chapters:
            print(f"  ✅ {stage_name}阶段没有真正的空窗期章节，无需情感事件")
            return writing_plan
        
        print(f"  🔍 检测到{len(truly_empty_chapters)}个真正空窗期章节: {truly_empty_chapters}")
        
        # 🆕 策略性选择关键章节（数量要少！）
        selected_chapters = self._select_strategic_emotional_chapters(
            truly_empty_chapters, stage_name, len(truly_empty_chapters)
        )
        
        if not selected_chapters:
            print(f"  ✅ {stage_name}阶段无需情感事件补充")
            return writing_plan
        
        print(f"  🤖 将在{len(selected_chapters)}个关键章节添加情感事件: {selected_chapters}")
        
        # 提取事件数据
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 构建提示词，只请求为选中的少量章节生成情感事件
        supplement_prompt = self._build_focused_emotional_event_prompt(
            selected_chapters, novel_title, novel_synopsis, creative_seed,
            stage_name, stage_range, overall_stage_plan, events
        )
        
        try:
            supplement_result = self.generator.api_client.generate_content_with_retry(
                "focused_emotional_supplement",
                supplement_prompt,
                purpose=f"为{stage_name}阶段在{len(selected_chapters)}个关键章节添加情感事件"
            )
            
            if supplement_result and "emotional_events" in supplement_result:
                emotional_events = supplement_result["emotional_events"]
                
                # 验证情感事件
                validated_events = self._validate_emotional_events(emotional_events, selected_chapters)
                
                if validated_events:
                    # 添加到特殊事件
                    if "special_events" not in events:
                        events["special_events"] = []
                    events["special_events"].extend(validated_events)
                    
                    # 更新事件系统
                    if "stage_writing_plan" in writing_plan:
                        writing_plan["stage_writing_plan"]["event_system"] = events
                    else:
                        writing_plan["event_system"] = events
                    
                    print(f"  ✅ 成功添加{len(validated_events)}个情感事件")
                    
        except Exception as e:
            print(f"  ❌ AI生成情感事件出错: {e}")
        
        return writing_plan
    
    def _get_truly_empty_chapters(self, writing_plan: Dict, stage_range: str) -> List[int]:
        """获取真正没有被任何事件占用的空窗期章节 - 修复版本"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        
        # 获取事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 收集所有被占用的章节
        occupied_chapters = set()
        
        # 重大事件
        for event in events.get("major_events", []):
            start = event.get("start_chapter", 0)
            end = event.get("end_chapter", start)
            # 修复：只计算阶段范围内的章节
            for chapter in range(max(start, start_chap), min(end, end_chap) + 1):
                occupied_chapters.add(chapter)
        
        # 中型事件
        for event in events.get("medium_events", []):
            chapter = event.get("chapter", event.get("start_chapter", 0))
            if start_chap <= chapter <= end_chap:
                occupied_chapters.add(chapter)
        
        # 小型事件
        for event in events.get("minor_events", []):
            chapter = event.get("chapter", event.get("start_chapter", 0))
            if start_chap <= chapter <= end_chap:
                occupied_chapters.add(chapter)
        
        # 特殊事件
        for event in events.get("special_events", []):
            chapter = event.get("chapter", event.get("start_chapter", 0))
            if start_chap <= chapter <= end_chap:
                occupied_chapters.add(chapter)
        
        # 找出真正空窗的章节
        all_chapters = set(range(start_chap, end_chap + 1))
        empty_chapters = sorted(list(all_chapters - occupied_chapters))
        
        print(f"  📊 章节占用统计: {stage_range}共{end_chap-start_chap+1}章, 占用{len(occupied_chapters)}章, 空窗{len(empty_chapters)}章")
        
        return empty_chapters

    def _select_strategic_emotional_chapters(self, empty_chapters: List[int], stage_name: str, total_empty: int) -> List[int]:
        """策略性选择情感事件章节 - 数量要严格控制！"""
        
        # 根据阶段制定不同的情感事件策略
        emotional_strategies = {
            "opening_stage": {
                "max_events": min(5, total_empty // 3),  # 动态计算，最多5个
                "preference": "early_and_mid",
                "min_gap": 3  # 从4改为3
            },
            "development_stage": {
                "max_events": 5,
                "preference": "mid",  # 偏好中期
                "min_gap": 3
            },
            "climax_stage": {
                "max_events": 2,  # 高潮阶段情感事件极少
                "preference": "before_climax",  # 大高潮前
                "min_gap": 5
            },
            "ending_stage": {
                "max_events": 3,
                "preference": "resolution",  # 解决阶段
                "min_gap": 4
            },
            "final_stage": {
                "max_events": 2,
                "preference": "emotional_closure",  # 情感收尾
                "min_gap": 6
            }
        }
        
        strategy = emotional_strategies.get(stage_name, emotional_strategies["development_stage"])
        max_events = min(strategy["max_events"], total_empty)  # 不能超过空窗期数量
        
        if not empty_chapters or max_events == 0:
            return []
        
        selected = []
        
        if strategy["preference"] == "early_and_mid":
            # 选择前期和中期章节
            early_mid = [chap for chap in empty_chapters if chap <= len(empty_chapters) * 2 // 3]
            selected = early_mid[:max_events]
        
        elif strategy["preference"] == "mid":
            # 选择中期章节
            mid_start = len(empty_chapters) // 3
            mid_end = 2 * len(empty_chapters) // 3
            mid_chapters = empty_chapters[mid_start:mid_end]
            selected = mid_chapters[:max_events]
        
        elif strategy["preference"] == "before_climax":
            # 选择后半段章节
            later_chapters = [chap for chap in empty_chapters if chap > len(empty_chapters) // 2]
            selected = later_chapters[:max_events]
        
        else:
            # 默认：均匀选择
            step = max(1, len(empty_chapters) // max_events)
            selected = [empty_chapters[i] for i in range(0, len(empty_chapters), step)][:max_events]
        
        # 确保最小间隔
        final_selection = []
        for chap in selected:
            if not final_selection or chap - final_selection[-1] >= strategy["min_gap"]:
                final_selection.append(chap)
        
        return final_selection[:max_events]

    def _build_focused_emotional_event_prompt(self, selected_chapters: List[int], novel_title: str, 
                                        novel_synopsis: str, creative_seed: str, stage_name: str,
                                        stage_range: str, overall_stage_plan: Dict, events: Dict) -> str:
        """构建聚焦的情感事件提示词"""
        
        return f"""
    请为以下小说的特定空窗期章节生成情感特殊事件：

    小说信息：
    - 标题：{novel_title}
    - 简介：{novel_synopsis}
    - 创意种子：{creative_seed}

    当前阶段：{stage_name}
    **需要填充的特定章节：{selected_chapters}**

    ## 🎯 重要说明
    这些章节是经过筛选的真正空窗期，请**只为这些特定章节**生成情感事件，不要为其他章节生成！

    ## 📋 现有事件系统
    {json.dumps(events, ensure_ascii=False, indent=2)}

    ## 🎭 情感事件要求
    1. **精准定位**：每个情感事件必须精确对应指定的章节
    2. **服务主线**：情感事件应该与前后主线事件有逻辑关联
    3. **质量优先**：精心设计每个情感互动，确保有明确的情感发展
    4. **避免重复**：不要生成重复或类似的情感事件

    ## 📝 返回格式
    请只为以下{len(selected_chapters)}个章节生成情感事件：

    {{
        "emotional_events": [
            {{
                "name": "事件名称",
                "type": "特殊事件",
                "subtype": "情感填充", 
                "chapter": {selected_chapters[0]},  // 必须精确匹配
                "purpose": "为什么在这个章节添加情感事件",
                "emotional_development": "推动的情感发展",
                "connection_to_plot": "与主线情节的关联",
                "plot_design": "具体情节设计",
                "description": "详细描述"
            }}
            // 只为提供的{len(selected_chapters)}个章节生成，不要多也不要少！
        ]
    }}
    """

    def build_event_chains(self, events: List) -> List:
        """构建事件链条，确保逻辑连贯"""
        if not events:
            return []
            
        chains = []
        current_chain = []
        
        for event in sorted(events, key=lambda x: x.get('start_chapter', 0)):
            if not current_chain:
                current_chain.append(event)
            else:
                last_event = current_chain[-1]
                # 检查事件是否连贯
                last_event_end = last_event.get('end_chapter', last_event.get('start_chapter', 0))
                current_event_start = event.get('start_chapter', 0)
                
                if current_event_start - last_event_end <= 5:
                    current_chain.append(event)
                else:
                    chains.append(current_chain)
                    current_chain = [event]
        
        if current_chain:
            chains.append(current_chain)
        
        return chains

    def calculate_max_event_gap(self, events: List, stage_start_chapter: int, stage_end_chapter: int) -> int:
        """计算最大事件间隔 - 修复版本：考虑所有类型事件，添加 stage_end_chapter 参数"""
        if not events:
            return stage_end_chapter - stage_start_chapter + 1
        
        # 按开始章节排序
        sorted_events = sorted(events, key=lambda x: x.get('start_chapter', 0))
        
        max_gap = 0
        
        # 检查第一个事件与阶段起点的间隔
        first_event_start = sorted_events[0].get('start_chapter', 0)
        
        if first_event_start > stage_start_chapter:
            gap_at_start = first_event_start - stage_start_chapter
            max_gap = max(max_gap, gap_at_start)
        
        # 检查事件之间的间隔
        for i in range(1, len(sorted_events)):
            prev_event = sorted_events[i-1]
            current_event = sorted_events[i]
            
            # 获取前一个事件的结束章节
            prev_event_end = prev_event.get('end_chapter', prev_event.get('start_chapter', 0))
            # 如果是单章事件，结束章节就是开始章节
            if prev_event_end < prev_event.get('start_chapter', 0):
                prev_event_end = prev_event.get('start_chapter', 0)
                
            current_event_start = current_event.get('start_chapter', 0)
            
            if current_event_start > prev_event_end:
                gap = current_event_start - prev_event_end - 1
                max_gap = max(max_gap, gap)
        
        # 检查最后一个事件与阶段终点的间隔
        last_event = sorted_events[-1]
        last_event_end = last_event.get('end_chapter', last_event.get('start_chapter', 0))
        if last_event_end < last_event.get('start_chapter', 0):
            last_event_end = last_event.get('start_chapter', 0)
            
        if last_event_end < stage_end_chapter:
            gap_at_end = stage_end_chapter - last_event_end
            max_gap = max(max_gap, gap_at_end)
        
        return max_gap

    def validate_main_thread_continuity(self, writing_plan: Dict, stage_name: str) -> bool:
        """验证主线连贯性 - 修复逻辑版本：考虑所有类型事件"""
        try:
            # 获取阶段范围信息
            stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
            stage_info = stage_plans.get("overall_stage_plan", {}).get(stage_name, {})
            chapter_range = stage_info.get("chapter_range", "1-100")
            start_chap, end_chap = parse_chapter_range(chapter_range)
            
            if "stage_writing_plan" in writing_plan:
                events = writing_plan["stage_writing_plan"].get("event_system", {})
            else:
                events = writing_plan.get("event_system", {})
            
            # 收集所有类型的事件
            all_events = []
            
            # 重大事件
            major_events = events.get("major_events", [])
            all_events.extend(major_events)
            
            # 中型事件
            medium_events = events.get("medium_events", [])
            for event in medium_events:
                # 为中型事件添加start_chapter字段（如果不存在）
                if 'start_chapter' not in event and 'chapter' in event:
                    event['start_chapter'] = event['chapter']
                    event['end_chapter'] = event['chapter']
                all_events.append(event)
            
            # 小型事件
            minor_events = events.get("minor_events", [])
            for event in minor_events:
                if 'start_chapter' not in event and 'chapter' in event:
                    event['start_chapter'] = event['chapter']
                    event['end_chapter'] = event['chapter']
                all_events.append(event)
            
            # 特殊事件
            special_events = events.get("special_events", [])
            for event in special_events:
                if 'start_chapter' not in event and 'chapter' in event:
                    event['start_chapter'] = event['chapter']
                    event['end_chapter'] = event['chapter']
                all_events.append(event)
            
            if not all_events:
                print(f"  ⚠️ 警告：{stage_name}阶段没有任何事件")
                return True  # 暂时返回True避免阻塞流程
            
            # 严格的最大间隔要求
            strict_max_gaps = {
                "opening_stage": 8,    # 适当放宽要求
                "development_stage": 12,
                "climax_stage": 10,     
                "ending_stage": 15,     
                "final_stage": 20      
            }
            
            max_allowed_gap = strict_max_gaps.get(stage_name, 12)
            max_gap = self.calculate_max_event_gap(all_events, start_chap, end_chap)
            
            print(f"  📊 {stage_name}阶段连续性检查: 最大间隔{max_gap}章, 允许{max_allowed_gap}章")
            print(f"  📊 事件统计: 重大{len(major_events)}个, 中型{len(medium_events)}个, 小型{len(minor_events)}个, 特殊{len(special_events)}个")
            
            if max_gap > max_allowed_gap:
                print(f"  ❌ 连续性检查失败：事件间隔过长")
                return False
            
            # 重大事件分布检查（只做警告不阻塞）
            if major_events:
                distribution_score = self._calculate_event_distribution_score(major_events, stage_name)
                if distribution_score < 0.6:
                    print(f"  ⚠️ 连续性警告：重大事件分布需要优化 (得分: {distribution_score:.1%})")
            
            print(f"  ✅ {stage_name}阶段主线连续性检查通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 连续性检查过程出错: {e}")
            return True  # 出错时保守返回True

    def identify_event_gaps(self, writing_plan: Dict, stage_range: str) -> List[Dict]:
        """识别事件空窗期章节，并获取上下文事件信息"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        
        # 获取所有事件及其章节信息
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 构建事件时间线
        timeline = []
        
        # 重大事件
        for event in event_system.get("major_events", []):
            timeline.append({
                "chapter": event.get("start_chapter", 0),
                "type": "major",
                "name": event.get("name", ""),
                "description": event.get("description", ""),
                "event": event
            })
        
        # 中型事件  
        for event in event_system.get("medium_events", []):
            timeline.append({
                "chapter": event.get("chapter", event.get("start_chapter", 0)),
                "type": "medium", 
                "name": event.get("name", ""),
                "description": event.get("description", ""),
                "event": event
            })
        
        # 特殊事件
        for event in event_system.get("special_events", []):
            timeline.append({
                "chapter": event.get("chapter", event.get("start_chapter", 0)),
                "type": "special",
                "subtype": event.get("subtype", "情感填充"),
                "name": event.get("name", ""),
                "description": event.get("description", ""),
                "event": event
            })
        
        # 按章节排序
        timeline.sort(key=lambda x: x["chapter"])
        
        # 识别空窗期并获取上下文
        gap_chapters_with_context = []
        
        for chapter in range(start_chap, end_chap + 1):
            # 检查当前章节是否有事件
            has_event = any(event["chapter"] == chapter for event in timeline)
            
            if not has_event:
                # 获取前后事件作为上下文
                prev_events = [e for e in timeline if e["chapter"] < chapter][-2:]  # 前2个事件
                next_events = [e for e in timeline if e["chapter"] > chapter][:2]   # 后2个事件
                
                gap_chapters_with_context.append({
                    "chapter": chapter,
                    "previous_events": prev_events,
                    "next_events": next_events,
                    "context_summary": self._generate_gap_context(prev_events, next_events)
                })
        
        # 只返回连续空窗期（至少3章）
        continuous_gaps = []
        current_gap_sequence = []
        
        for gap_info in gap_chapters_with_context:
            chapter = gap_info["chapter"]
            
            if not current_gap_sequence:
                current_gap_sequence.append(gap_info)
            else:
                last_chapter = current_gap_sequence[-1]["chapter"]
                if chapter == last_chapter + 1:
                    current_gap_sequence.append(gap_info)
                else:
                    if len(current_gap_sequence) >= 3:
                        continuous_gaps.extend(current_gap_sequence)
                    current_gap_sequence = [gap_info]
        
        # 处理最后一段
        if len(current_gap_sequence) >= 3:
            continuous_gaps.extend(current_gap_sequence)
        
        print(f"  📊 识别到{len(continuous_gaps)}个有上下文的空窗期章节")
        return continuous_gaps

    def export_events_to_json(self, file_path: str = "novel_events.json"):
        """导出所有事件到JSON文件，按章节排序 - 修复嵌套结构版本"""
        import os
        quality_dir = "quality_data"
        os.makedirs(quality_dir, exist_ok=True)
        
        # 构建完整路径
        full_path = os.path.join(quality_dir, file_path)
        
        print(f"\n📋 开始提取所有事件并保存到 {full_path}")
        
        all_events = []
        
        # 获取所有阶段写作计划
        stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_plan in stage_plans.items():
            print(f"  🔍 处理阶段: {stage_name}")
            
            # 修复：正确处理嵌套结构
            if "stage_writing_plan" in stage_plan:
                # 嵌套结构：stage_plan -> stage_writing_plan -> event_system
                actual_plan = stage_plan["stage_writing_plan"]
                print(f"  🔍 检测到嵌套结构 stage_writing_plan，使用嵌套数据")
            else:
                # 平面结构：stage_plan -> event_system
                actual_plan = stage_plan
                print(f"  🔍 未检测到嵌套结构，使用原始数据")
            
            # 获取事件系统
            event_system = actual_plan.get("event_system", {})
            print(f"  🔍 {stage_name}的事件系统键: {list(event_system.keys())}")
            
            # 提取重大事件
            major_events = event_system.get("major_events", [])
            print(f"  🔍 {stage_name}的重大事件数量: {len(major_events)}")
            for event in major_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("start_chapter", 0),
                    "end_chapter": event.get("end_chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", "未知重要性"),
                    "description": event.get("description", ""),
                    "type": "major",
                    "stage": stage_name
                }
                all_events.append(event_data)
            
            # 提取中型事件
            medium_events = event_system.get("medium_events", [])
            print(f"  🔍 {stage_name}的中型事件数量: {len(medium_events)}")
            for event in medium_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", event.get("main_goal", "未知重要性")),
                    "description": event.get("description", ""),
                    "type": "medium", 
                    "stage": stage_name
                }
                all_events.append(event_data)
            
            # 提取小型事件
            minor_events = event_system.get("minor_events", [])
            print(f"  🔍 {stage_name}的小型事件数量: {len(minor_events)}")
            for event in minor_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", event.get("function", "未知重要性")),
                    "description": event.get("description", ""),
                    "type": "minor",
                    "stage": stage_name
                }
                all_events.append(event_data)
            
            # 🆕 提取特殊事件
            special_events = event_system.get("special_events", [])
            print(f"  🔍 {stage_name}的特殊事件数量: {len(special_events)}")
            for event in special_events:
                event_data = {
                    "name": event.get("name", "未命名特殊事件"),
                    "start_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", "情感发展和读者兴趣维持"),
                    "description": event.get("description", ""),
                    "type": "special",
                    "subtype": event.get("subtype", "情感填充"),
                    "stage": stage_name,
                    "romance_style": event.get("romance_style", ""),
                    "event_category": event.get("event_category", "情感特殊事件")
                }
                all_events.append(event_data)
        
        # 按开始章节排序
        all_events.sort(key=lambda x: x["start_chapter"])
        
        # 构建输出数据结构
        output_data = {
            "novel_title": self.generator.novel_data.get("novel_title", "未知小说"),
            "total_events": len(all_events),
            "events_by_type": {
                "major": len([e for e in all_events if e["type"] == "major"]),
                "medium": len([e for e in all_events if e["type"] == "medium"]),
                "minor": len([e for e in all_events if e["type"] == "minor"]),
                "special": len([e for e in all_events if e["type"] == "special"])  # 🆕 特殊事件统计
            },
            "special_events_breakdown": {  # 🆕 特殊事件详细分类
                "emotional_filler": len([e for e in all_events if e.get("subtype") == "情感填充"])
            },
            "events": all_events
        }
        
        # 保存到JSON文件
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2, sort_keys=True)
            
            print(f"✅ 成功导出 {len(all_events)} 个事件到 {full_path}")
            print(f"   📊 事件统计: 重大事件{output_data['events_by_type']['major']}个, "
                f"中型事件{output_data['events_by_type']['medium']}个, "
                f"小型事件{output_data['events_by_type']['minor']}个, "
                f"特殊事件{output_data['events_by_type']['special']}个")  # 🆕 显示特殊事件数量
            
            # 打印前几个事件预览
            if all_events:
                print(f"\n📖 事件预览 (前5个):")
                for i, event in enumerate(all_events[:5]):
                    event_type = f"{event['type']}({event.get('subtype', '')})" if event.get('subtype') else event['type']
                    print(f"   {i+1}. 第{event['start_chapter']}章: {event['name']} ({event_type})")
                    
        except Exception as e:
            print(f"❌ 导出事件到JSON文件失败: {e}")

        print("\n🎯 开始全书事件线整体评价...")
        timeline_evaluation = self.evaluate_overall_event_timeline()
        if timeline_evaluation:
            evaluation_path = os.path.join(quality_dir, "event_timeline_evaluation.json")
            with open(evaluation_path, 'w', encoding='utf-8') as f:
                json.dump(timeline_evaluation, f, ensure_ascii=False, indent=2)
            print(f"✅ 事件线评价已保存: {evaluation_path}")
            print(f"   整体评分: {timeline_evaluation.get('overall_score', 'N/A')}/10")

        return output_data

    def get_events_summary(self) -> Dict:
        """获取事件摘要统计"""
        # 不实际保存文件，直接在内存中处理
        all_events = []
        stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_plan in stage_plans.items():
            # 正确处理嵌套结构
            if "stage_writing_plan" in stage_plan:
                actual_plan = stage_plan["stage_writing_plan"]
            else:
                actual_plan = stage_plan
            
            event_system = actual_plan.get("event_system", {})
            
            # 提取所有类型的事件
            for event_type, type_key in [("major", "major_events"), ("medium", "medium_events"), ("minor", "minor_events"), ("special", "special_events")]:
                events = event_system.get(type_key, [])
                for event in events:
                    if event_type == "major":
                        start_chapter = event.get("start_chapter", 0)
                        end_chapter = event.get("end_chapter", start_chapter)
                    else:
                        start_chapter = event.get("chapter", event.get("start_chapter", 0))
                        end_chapter = start_chapter
                    
                    event_data = {
                        "name": event.get("name", "未命名事件"),
                        "start_chapter": start_chapter,
                        "end_chapter": end_chapter,
                        "type": event_type,
                        "subtype": event.get("subtype", ""),
                        "stage": stage_name
                    }
                    all_events.append(event_data)
        
        # 按阶段统计
        stage_stats = {}
        for event in all_events:
            stage = event["stage"]
            if stage not in stage_stats:
                stage_stats[stage] = {"major": 0, "medium": 0, "minor": 0, "special": 0}
            stage_stats[stage][event["type"]] += 1
        
        summary = {
            "total_events": len(all_events),
            "events_by_type": {
                "major": len([e for e in all_events if e["type"] == "major"]),
                "medium": len([e for e in all_events if e["type"] == "medium"]),
                "minor": len([e for e in all_events if e["type"] == "minor"]),
                "special": len([e for e in all_events if e["type"] == "special"])
            },
            "events_by_stage": stage_stats,
            "chapter_coverage": self._calculate_chapter_coverage(all_events)
        }
        
        return summary

    # === 私有辅助方法 ===

    def _validate_supplemental_events(self, supplemental_events: Dict, start_chap: int, end_chap: int) -> Dict:
        """简单验证补充的事件 - 只验证章节范围"""
        validated = {
            "major_events": [],
            "medium_events": [], 
            "minor_events": [],
            "special_events": []
        }
        
        # 验证重大事件
        for event in supplemental_events.get("major_events", []):
            if all(key in event for key in ["name", "start_chapter", "end_chapter"]):
                if start_chap <= event["start_chapter"] <= end_chap and start_chap <= event["end_chapter"] <= end_chap:
                    validated["major_events"].append(event)
        
        # 验证中型事件
        for event in supplemental_events.get("medium_events", []):
            if all(key in event for key in ["name", "chapter"]):
                if start_chap <= event["chapter"] <= end_chap:
                    validated["medium_events"].append(event)
        
        # 验证小型事件
        for event in supplemental_events.get("minor_events", []):
            if all(key in event for key in ["name", "chapter"]):
                if start_chap <= event["chapter"] <= end_chap:
                    validated["minor_events"].append(event)
        
        # 验证特殊事件
        for event in supplemental_events.get("special_events", []):
            if all(key in event for key in ["name", "chapter"]):
                if start_chap <= event["chapter"] <= end_chap:
                    validated["special_events"].append(event)
        
        return validated

    def _sort_events_by_chapter(self, events: Dict) -> Dict:
        """按章节排序事件"""
        for event_type in ["major_events", "medium_events", "minor_events", "special_events"]:
            if event_type in events:
                if event_type == "major_events":
                    events[event_type] = sorted(events[event_type], key=lambda x: x.get('start_chapter', 0))
                else:
                    events[event_type] = sorted(events[event_type], key=lambda x: x.get('chapter', 0))
        
        return events

    def _calculate_chapter_coverage(self, events: List[Dict]) -> Dict:
        """计算章节覆盖情况"""
        if not events:
            return {"covered_chapters": 0, "total_chapters": 0, "coverage_rate": 0}
        
        # 获取总章节数
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        # 计算有事件的章节
        covered_chapters = set()
        for event in events:
            start = event["start_chapter"]
            end = event["end_chapter"]
            for chapter in range(start, end + 1):
                if 1 <= chapter <= total_chapters:
                    covered_chapters.add(chapter)
        
        coverage_rate = len(covered_chapters) / total_chapters if total_chapters > 0 else 0
        
        return {
            "covered_chapters": len(covered_chapters),
            "total_chapters": total_chapters,
            "coverage_rate": round(coverage_rate * 100, 2)
        }

    def _generate_gap_context(self, prev_events: List, next_events: List) -> str:
        """生成空窗期的上下文摘要"""
        context_parts = []
        
        if prev_events:
            context_parts.append("之前事件:")
            for event in prev_events:
                event_type = f"{event['type']}({event.get('subtype', '')})" if event.get('subtype') else event['type']
                context_parts.append(f"  - 第{event['chapter']}章: {event['name']} ({event_type})")
        
        if next_events:
            context_parts.append("即将发生:")
            for event in next_events:
                event_type = f"{event['type']}({event.get('subtype', '')})" if event.get('subtype') else event['type']
                context_parts.append(f"  - 第{event['chapter']}章: {event['name']} ({event_type})")
        
        return "\n".join(context_parts) if context_parts else "无明确上下文事件"

    def _basic_event_supplement(self, writing_plan: Dict, stage_range: str) -> Dict:
        """基础事件补充方法"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 确保 event_system 存在
        if "event_system" not in writing_plan:
            writing_plan["event_system"] = {}
        
        events = writing_plan["event_system"]
        
        # 确保各种事件列表存在
        if "major_events" not in events:
            events["major_events"] = []
        if "medium_events" not in events:
            events["medium_events"] = []
        if "minor_events" not in events:
            events["minor_events"] = []
        if "special_events" not in events:
            events["special_events"] = []
        
        # 如果没有重大事件，在阶段中间添加一个
        if not events["major_events"]:
            mid_chapter = (start_chap + end_chap) // 2
            events["major_events"].append({
                "name": "阶段核心事件",
                "start_chapter": max(start_chap, mid_chapter - 2),
                "end_chapter": min(end_chap, mid_chapter + 2),
                "significance": "推动阶段核心目标",
                "description": "自动生成的核心事件"
            })
        
        return writing_plan

    def is_chapter_available(self, writing_plan: Dict, chapter: int, event_type: str) -> bool:
        """检查章节是否可用于新事件 - 生成时调用"""
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 检查重大事件占用
        for event in events.get("major_events", []):
            start = event.get("start_chapter", 0)
            end = event.get("end_chapter", start)
            if start <= chapter <= end:
                return False
        
        # 检查中型事件占用
        for event in events.get("medium_events", []):
            event_chapter = event.get("chapter", event.get("start_chapter", 0))
            if event_chapter == chapter:
                return False
        
        # 检查小型事件占用
        for event in events.get("minor_events", []):
            event_chapter = event.get("chapter", event.get("start_chapter", 0))
            if event_chapter == chapter:
                return False
        
        # 检查特殊事件占用
        for event in events.get("special_events", []):
            event_chapter = event.get("chapter", event.get("start_chapter", 0))
            if event_chapter == chapter:
                return False
        
        return True

    def get_available_chapters_for_generation(self, writing_plan: Dict, stage_range: str, 
                                        event_type: str = "special") -> List[int]:
        """获取可用于生成新事件的章节列表 - 生成时调用"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        available_chapters = []
        
        for chapter in range(start_chap, end_chap + 1):
            if self.is_chapter_available(writing_plan, chapter, event_type):
                available_chapters.append(chapter)
        
        print(f"  📊 生成时可用章节检查: 阶段{stage_range}共{end_chap - start_chap + 1}章, 可用{len(available_chapters)}章")
        return available_chapters

    def _adjust_density_for_availability(self, requirements: Dict, available_chapters: int, 
                                    total_chapters: int) -> Dict:
        """根据可用章节数调整密度要求"""
        adjusted = requirements.copy()
        
        # 如果可用章节较少，适当降低期望
        availability_ratio = available_chapters / total_chapters if total_chapters > 0 else 0
        
        if availability_ratio < 0.3:
            # 可用章节很少，大幅降低期望
            adjusted["minor_events"] = max(1, int(requirements["minor_events"] * 0.3))
        elif availability_ratio < 0.6:
            # 可用章节适中，适度降低期望
            adjusted["minor_events"] = max(2, int(requirements["minor_events"] * 0.6))
        
        print(f"  📊 密度调整: 可用{available_chapters}/{total_chapters}章, "
            f"小型事件从{requirements['minor_events']}调整到{adjusted['minor_events']}")
        
        return adjusted    
    
# -------------------------------------------------------------
    # ▼▼▼ 修改开始：重写全书事件线评价逻辑 ▼▼▼
    # -------------------------------------------------------------

    def _get_all_events_sorted(self) -> List[Dict]:
        """
        获取、整合并按章节排序全书的所有事件。
        这是新版连续性评价的数据基础。
        """
        all_events = []
        stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_plan in stage_plans.items():
            # 正确处理可能的嵌套结构
            actual_plan = stage_plan.get("stage_writing_plan", stage_plan)
            event_system = actual_plan.get("event_system", {})
            
            # 统一处理所有类型的事件
            event_types_map = {
                "major": event_system.get("major_events", []),
                "medium": event_system.get("medium_events", []),
                "minor": event_system.get("minor_events", []),
                "special": event_system.get("special_events", [])
            }

            for event_type, events in event_types_map.items():
                for event in events:
                    start_chapter = 0
                    end_chapter = 0
                    if event_type == "major":
                        start_chapter = event.get("start_chapter", 0)
                        end_chapter = event.get("end_chapter", start_chapter)
                    else: # medium, minor, special 都是单章节事件
                        start_chapter = event.get("chapter", event.get("start_chapter", 0))
                        end_chapter = start_chapter

                    if start_chapter > 0: # 只添加有有效章节的事件
                        all_events.append({
                            "name": event.get("name", "未命名事件"),
                            "start_chapter": start_chapter,
                            "end_chapter": end_chapter,
                            "type": event.get("subtype", event_type), # 优先使用subtype
                            "stage": stage_name
                        })
        
        # 严格按开始章节排序，构建时间线
        all_events.sort(key=lambda x: x["start_chapter"])
        return all_events

    def _build_overall_continuity_prompt(self, sorted_events: List[Dict]) -> str:
        """
        根据排序后的全书事件时间线，构建用于深度连续性评估的Prompt。
        """
        # 将事件列表格式化为易于阅读的Markdown表格
        event_timeline_str = "| 事件名称 | 类型 | 起止章节 | 所属阶段 |\n|---|---|---|---|\n"
        for event in sorted_events:
            chapter_range = f"第{event['start_chapter']}章"
            if event['start_chapter'] != event['end_chapter']:
                chapter_range += f"-{event['end_chapter']}章"
            
            event_timeline_str += f"| {event['name']} | {event['type']} | {chapter_range} | {event['stage']} |\n"

        prompt = f"""
    作为顶尖小说策划编辑，请对以下小说按时间线排列的【全书事件规划】进行一次全面、深刻、数据驱动的连续性分析。

    ## 核心任务
    你的所有评价都必须紧密结合下方提供的【事件时间线】。不要进行宏观统计，而是要分析事件与事件之间的具体衔接。

    ## 小说信息
    - 标题：{self.generator.novel_data.get('novel_title', '未知')}
    - 总章节：{self.generator.novel_data.get('current_progress', {}).get('total_chapters', '未知')}

    ## 全书事件时间线 (按章节排序)
    {event_timeline_str}

    ## 评估维度与要求
    请基于以上时间线，深入分析以下维度：
    1.  **事件密度与节奏 (Density & Rhythm)**:
        -   是否存在事件过于密集，导致读者疲劳的章节区间？
        -   是否存在事件过于稀疏，导致主线停滞、剧情平淡的章节区间？
        -   整体节奏（紧张-平缓-紧张）的交替是否自然？请指出具体的事件作为例子。

    2.  **事件类型分布与平衡性 (Balance)**:
        -   主线（major）事件的推进是否连贯？是否存在长时间没有主线事件的空窗期？
        -   情感（special）事件是否有效地插入在主线事件之间，起到了调节节奏、深化角色的作用？还是说它们显得突兀或与主线脱节？
        -   次要（medium/minor）事件是否很好地为主线服务，起到了铺垫和丰富世界观的作用？

    3.  **阶段间过渡的自然性 (Transition)**:
        -   请重点分析【阶段边界】的事件衔接。例如，`development_stage`的最后一个事件和`climax_stage`的第一个事件衔接是否流畅？有没有做好足够的铺垫？
        -   从一个阶段到下一个阶段的过渡，在情绪和节奏上是平滑过渡，还是生硬跳跃？

    4.  **整体逻辑连贯性 (Overall Coherence)**:
        -   通读整个事件链，是否存在逻辑断层或因果关系不明确的地方？
        -   事件的发生顺序是否合理？有没有看起来像是为了情节而强行安排的事件？

    ## 返回格式要求
    请严格按照以下JSON格式返回你的专业评价报告。评价内容必须具体、可落地，直接引用时间线中的事件名称作为论据。

    {{
        "overall_score": 0-10,
        "density_evaluation": "（必须具体指出过密/过疏的章节范围和事件）",
        "balance_evaluation": "（必须具体分析主线、情感等事件类型的搭配问题）", 
        "transition_evaluation": "（必须具体评价阶段边界的事件衔接好坏）",
        "rhythm_evaluation": "（现在重命名为'continuity_and_rhythm_evaluation'，作为对整体时间线连贯性和节奏的总结性评价）",
        "key_issues": ["（列出最关键的1-3个具体问题，如：'第XX章到YY章主线停滞过久'）"],
        "improvement_suggestions": ["（提出可执行的修改建议，如：'建议在事件A和事件B之间增加一个过渡性情感事件'）"]
    }}
    """
        return prompt

    def evaluate_overall_event_timeline(self) -> Dict:
        """【新版】对全书事件线进行基于时间线的深度连续性评价"""
        try:
            # 步骤1：获取并排序全书所有事件，形成时间线
            sorted_events = self._get_all_events_sorted()
            
            if not sorted_events:
                print("  ⚠️ 无法进行全书事件线评价：未找到任何已规划的事件。")
                return {"overall_score": 0, "error": "Not enough event data to evaluate."}

            # 步骤2：根据时间线构建新的、更深入的评估Prompt
            prompt = self._build_overall_continuity_prompt(sorted_events)
            
            # 步骤3：调用AI进行评估
            evaluation_result = self.generator.api_client.generate_content_with_retry(
                "event_timeline_continuity_evaluation", # 使用新的调用标识
                prompt,
                purpose="全书事件线连续性评价"
            )

            # 步骤4：处理并返回结果
            if evaluation_result:
                # 兼容旧字段名，将'continuity_and_rhythm_evaluation'的内容赋给'rhythm_evaluation'
                if "continuity_and_rhythm_evaluation" in evaluation_result:
                    evaluation_result["rhythm_evaluation"] = evaluation_result.pop("continuity_and_rhythm_evaluation")
                return evaluation_result
            else:
                 return {
                    "overall_score": 0, "density_evaluation": "评价失败", "balance_evaluation": "评价失败",
                    "transition_evaluation": "评价失败", "rhythm_evaluation": "评价失败", 
                    "key_issues": ["AI评价服务暂不可用"], "improvement_suggestions": ["请人工审核事件规划"]
                }
            
        except Exception as e:
            print(f"  ❌ 全书事件线连续性评价过程中发生严重错误: {e}")
            return {"overall_score": 0, "error": str(e)}

    # =========================================================================
    # ▼▼▼ 新增：统一的智能事件补充入口 ▼▼▼
    # =========================================================================
    def strategically_supplement_events(self, writing_plan: Dict, stage_name: str, stage_range: str,
                                        romance_pattern: Dict, creative_seed: str, novel_title: str,
                                        novel_synopsis: str) -> Dict:
        """
        统一的事件补充入口。
        智能识别空窗期，并根据情感模式和阶段需求，策略性地生成并整合补充事件。
        """
        print(f"  🔄 开始对 {stage_name} 进行统一的事件补充...")

        # 1. 识别真正可用的空窗期章节
        available_chapters = self.get_available_chapters_for_generation(writing_plan, stage_range, "any")
        if not available_chapters:
            print("  ✅ 阶段内无可用空窗期，无需补充事件。")
            return writing_plan

        print(f"  🔍 找到 {len(available_chapters)} 个可用章节: {available_chapters[:10]}...")

        # 2. 策略性地选择需要填充的章节 (逻辑从 StagePlanManager 移入)
        selected_chapters = self._select_strategic_chapters_for_supplementation(available_chapters, stage_name)
        if not selected_chapters:
            print("  ✅ 根据策略，当前阶段无需补充事件。")
            return writing_plan

        print(f"  🎯 策略选择 {len(selected_chapters)} 个关键章节进行填充: {selected_chapters}")

        # 3. 调用AI生成补充事件 (逻辑融合了 RomancePatternManager)
        supplemental_events = self._generate_supplemental_events_with_ai(
            selected_chapters, stage_name, romance_pattern,
            creative_seed, novel_title, novel_synopsis, writing_plan
        )

        # 4. 将生成的事件整合到写作计划中 (逻辑从 RomancePatternManager 移入)
        if supplemental_events:
            writing_plan = self._integrate_supplemental_events(writing_plan, supplemental_events)

        return writing_plan

    def _select_strategic_chapters_for_supplementation(self, available_chapters: List[int], stage_name: str) -> List[int]:
        """
        策略性选择用于补充的章节，严格控制数量。
        (此方法从 StagePlanManager._select_emotional_chapters_strategically 移动并通用化)
        """
        stage_limits = {
            "opening_stage": 2,
            "development_stage": 4,
            "climax_stage": 1,
            "ending_stage": 3,
            "final_stage": 2
        }
        max_events = stage_limits.get(stage_name, 3)
        max_events = min(max_events, len(available_chapters))

        if not available_chapters or max_events == 0:
            return []

        # 简单均匀分布策略
        if len(available_chapters) <= max_events:
            return available_chapters

        step = len(available_chapters) // max_events
        selected = [available_chapters[i * step] for i in range(max_events)]
        return selected

    def _generate_supplemental_events_with_ai(self, chapters_to_fill: List[int], stage_name: str,
                                              romance_pattern: Dict, creative_seed: str, novel_title: str,
                                              novel_synopsis: str, writing_plan: Dict) -> List[Dict]:
        """
        使用AI为空窗期生成补充事件（情感或过渡情节）。
        (此方法融合了 RomancePatternManager.generate_romance_filler_events 的核心思想)
        """
        event_system = writing_plan.get("stage_writing_plan", {}).get("event_system", {})

        filler_prompt = f"""
        请为以下小说的指定空窗期章节，生成与主线情节关联的补充性特殊事件。

        小说信息：
        - 标题：{novel_title}
        - 简介：{novel_synopsis}
        - 创意种子：{creative_seed}
        - 情感模式：{romance_pattern.get('romance_type', '未知')} ({romance_pattern.get('emotional_style', '未知')})

        当前阶段：{stage_name}
        现有事件概览：{json.dumps(event_system.get("major_events", []), ensure_ascii=False, indent=2)}
        **需要填充的特定章节：{chapters_to_fill}**

        ## 核心要求
        1. **服务主线**: 事件必须作为前后主线事件的“润滑剂”，或深化角色关系为后续主线服务。
        2. **情感/节奏**: 根据 `{romance_pattern.get('filler_focus', '角色互动')}` 的指导，决定事件是侧重情感发展，还是情节过渡。
        3. **精准定位**: 每个事件必须精确对应一个指定的章节。
        4. **高质量**: 避免模板化，设计有意义的互动。

        ## 返回格式
        请为每个需要填充的章节生成一个补充事件:
        {{
            "supplemental_events": [
                {{
                    "name": "能体现事件核心功能的名称",
                    "type": "special",
                    "subtype": "emotional_filler_or_plot_transition", // 根据功能填写 emotional_filler 或 plot_transition
                    "chapter": 章节号, // 必须是 {chapters_to_fill} 中的一个
                    "purpose": "该事件的核心目的 (例如：缓和节奏，深化A与B的关系，为下个大事件铺垫情绪)",
                    "plot_design": "具体的简要情节设计",
                    "connection_to_plot": "此事件如何与前后主线事件相关联",
                    "significance": "对角色关系、读者情绪或后续情节的简要影响"
                }}
            ]
        }}
        """
        result = self.generator.api_client.generate_content_with_retry(
            "supplemental_event_generation",
            filler_prompt,
            purpose=f"为{stage_name}生成补充事件"
        )

        if result and "supplemental_events" in result:
            events = result["supplemental_events"]
            print(f"  💖 成功生成 {len(events)} 个补充事件。")
            return events
        return []


    def _integrate_supplemental_events(self, writing_plan: Dict, supplemental_events: List[Dict]) -> Dict:
        """
        将补充事件整合到写作计划中。
        (此方法从 RomancePatternManager.integrate_filler_events 移动并通用化)
        """
        if not supplemental_events:
            return writing_plan

        # 定位 event_system
        plan_container = writing_plan.get("stage_writing_plan", writing_plan)
        if "event_system" not in plan_container:
            plan_container["event_system"] = {}
        event_system = plan_container["event_system"]

        # 整合到 special_events 列表
        if "special_events" not in event_system:
            event_system["special_events"] = []
        event_system["special_events"].extend(supplemental_events)
        
        # 排序以保证章节顺序
        event_system["special_events"].sort(key=lambda x: x.get('chapter', 0))

        print(f"  ✅ 成功整合 {len(supplemental_events)} 个补充事件到计划中。")
        return writing_plan

    # =========================================================================
    # ▲▲▲ 新增结束 ▲▲▲
    # =========================================================================
