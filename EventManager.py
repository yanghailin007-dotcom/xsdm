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
        """基于阶段类型计算最优事件密度"""
        stage_density_profiles = {
            "opening_stage": {
                "description": "高密度重大事件，快速吸引读者",
                "major_ratio": 0.4,    # 重大事件40%
                "medium_ratio": 0.4,   # 中型事件40%
                "minor_ratio": 0.2,    # 小型事件20%
                "min_major": 3,        # 至少3个重大事件
                "min_medium": 2,       # 至少2个中型事件
                "max_minor": 5         # 最多5个小事件
            },
            "development_stage": {
                "description": "平衡发展，中型事件为主",
                "major_ratio": 0.3,    # 重大事件30%
                "medium_ratio": 0.5,   # 中型事件50%  
                "minor_ratio": 0.2,    # 小型事件20%
                "min_major": 2,
                "min_medium": 4,
                "max_minor": 8
            },
            "climax_stage": {
                "description": "重大事件密集，高潮迭起",
                "major_ratio": 0.5,    # 重大事件50%
                "medium_ratio": 0.3,   # 中型事件30%
                "minor_ratio": 0.2,    # 小型事件20%
                "min_major": 4,
                "min_medium": 3,
                "max_minor": 6
            },
            "ending_stage": {
                "description": "解决冲突，收束支线",
                "major_ratio": 0.4,    # 重大事件40%
                "medium_ratio": 0.4,   # 中型事件40%
                "minor_ratio": 0.2,    # 小型事件20%
                "min_major": 2,
                "min_medium": 3,
                "max_minor": 4
            },
            "final_stage": {
                "description": "专注结局，减少冗余",
                "major_ratio": 0.6,    # 重大事件60%
                "medium_ratio": 0.3,   # 中型事件30%
                "minor_ratio": 0.1,    # 小型事件10%
                "min_major": 2,
                "min_medium": 2,
                "max_minor": 2
            }
        }
        
        profile = stage_density_profiles.get(stage_name, stage_density_profiles["development_stage"])
        
        # 基于阶段长度计算事件数量
        base_events = max(8, stage_length // 2)  # 基础事件数
        
        return {
            "major_events": max(profile["min_major"], int(base_events * profile["major_ratio"])),
            "medium_events": max(profile["min_medium"], int(base_events * profile["medium_ratio"])),
            "minor_events": min(profile["max_minor"], int(base_events * profile["minor_ratio"]))
        }

    def validate_event_density(self, writing_plan: Dict, stage_range: str) -> bool:
        """验证事件密度是否合理"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 修正：正确访问嵌套的事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        medium_events = events.get("medium_events", [])
        minor_events = events.get("minor_events", [])
        special_events = events.get("special_events", [])
        
        # 计算事件密度
        total_events = len(major_events) + len(medium_events) + len(minor_events) + len(special_events)
        
        # 获取最优事件密度
        density_dict = self.calculate_optimal_event_density(stage_length)
        expected_min_events = (
            density_dict.get("major_events", 0) + 
            density_dict.get("medium_events", 0) + 
            density_dict.get("minor_events", 0)
        )
        
        if total_events < expected_min_events:
            print(f"  ⚠️ 事件密度不足：期望至少{expected_min_events}个事件，实际只有{total_events}个")
            print(f"    重大事件: {len(major_events)}, 中型事件: {len(medium_events)}, 小型事件: {len(minor_events)}, 特殊事件: {len(special_events)}")
            return False
        
        print(f"  ✅ 事件密度验证通过：实际{total_events}个事件，期望至少{expected_min_events}个")
        return True

    def validate_stage_event_density(self, writing_plan: Dict, stage_name: str, stage_range: str) -> bool:
        """验证阶段特定的事件密度是否合理"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 获取阶段特定的密度要求
        density_requirements = self.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        
        # 修正：正确访问嵌套的事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        medium_events = events.get("medium_events", [])
        minor_events = events.get("minor_events", [])
        special_events = events.get("special_events", [])
        
        # 计算实际事件数量
        actual_major = len(major_events)
        actual_medium = len(medium_events)
        actual_minor = len(minor_events)
        actual_special = len(special_events)
        
        # 验证是否满足阶段特定要求
        major_ok = actual_major >= density_requirements["major_events"]
        medium_ok = actual_medium >= density_requirements["medium_events"]
        minor_ok = actual_minor <= density_requirements["minor_events"]  # 小型事件要控制上限
        
        if not (major_ok and medium_ok and minor_ok):
            print(f"  ⚠️ {stage_name}阶段事件密度不符合要求：")
            print(f"    重大事件: 实际{actual_major}个, 要求至少{density_requirements['major_events']}个")
            print(f"    中型事件: 实际{actual_medium}个, 要求至少{density_requirements['medium_events']}个")
            print(f"    小型事件: 实际{actual_minor}个, 要求最多{density_requirements['minor_events']}个")
            print(f"    特殊事件: 实际{actual_special}个")
            return False
        
        print(f"  ✅ {stage_name}阶段事件密度验证通过")
        return True

    def validate_main_thread_continuity(self, writing_plan: Dict, stage_name: str) -> bool:
        """验证主线连贯性 - 阶段特定版本"""
        # 修正：正确访问嵌套的事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 确保 major_events 存在
        if "major_events" not in events:
            return False
            
        major_events = events.get("major_events", [])
        
        # 阶段特定的最大间隔
        stage_max_gaps = {
            "opening_stage": 5,    # 开局阶段间隔更短
            "development_stage": 8,
            "climax_stage": 6,     # 高潮阶段间隔较短
            "ending_stage": 7,
            "final_stage": 10      # 结局阶段可以稍长
        }
        
        max_allowed_gap = stage_max_gaps.get(stage_name, 8)
        
        # 检查是否有超过允许间隔没有核心事件
        max_gap = self.calculate_max_event_gap(major_events)
        
        if max_gap > max_allowed_gap:
            print(f"  ⚠️ 警告：{stage_name}阶段事件间隔过长，最长{max_gap}章没有核心事件（允许最大{max_allowed_gap}章）")
            return False
        
        print(f"  ✅ {stage_name}阶段主线连贯性验证通过：最大事件间隔{max_gap}章")
        return True

    def supplement_events_with_ai(self, writing_plan: Dict, stage_range: str, creative_seed: str, 
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """使用AI补充事件以提高密度 - 阶段特定版本"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 🆕 获取当前阶段名称
        stage_name = None
        for name, plan in self.generator.novel_data.get("stage_writing_plans", {}).items():
            if plan == writing_plan:
                stage_name = name
                break
        
        if not stage_name:
            # 尝试从章节范围推断阶段
            if start_chap == 1:
                stage_name = "opening_stage"
            else:
                stage_name = "development_stage"  # 默认
        
        # 🆕 使用阶段特定的密度要求
        density_requirements = self.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        
        # 提取事件数据
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 计算当前事件密度
        current_major = len(events.get("major_events", []))
        current_medium = len(events.get("medium_events", []))
        current_minor = len(events.get("minor_events", []))
        current_special = len(events.get("special_events", []))
        
        # 🆕 使用阶段特定的目标密度
        target_major = density_requirements["major_events"]
        target_medium = density_requirements["medium_events"]
        target_minor = density_requirements["minor_events"]
        
        # 如果事件密度不足，提示AI补充
        if current_major < target_major or current_medium < target_medium or current_minor > target_minor:
            print(f"  🤖 {stage_name}阶段事件密度不符合要求，使用AI补充事件...")
            
            supplement_prompt = f"""
    请为小说阶段补充事件设计，使事件密度更加合理。

    ## 小说核心信息
    - **小说标题**: {novel_title}
    - **小说简介**: {novel_synopsis}
    - **创意种子**: {creative_seed}
    - **阶段名称**: {stage_name}
    - **阶段范围**: {stage_range}章 (共{stage_length}章)

    ## 全书大纲 (上下文)
    {json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)}

    ## 🆕 阶段特定事件规划要求
    {self.stage_plan_manager.get_stage_specific_guidance(stage_name)}

    ## 事件密度目标
    - 重大事件: {current_major}个 -> 需要达到{target_major}个
    - 中型事件: {current_medium}个 -> 需要达到{target_medium}个  
    - 小型事件: {current_minor}个 -> 需要控制在{target_minor}个以内
    - 特殊事件: {current_special}个

    ## 现有事件
    {json.dumps(events, ensure_ascii=False, indent=2)}

    ## 补充要求
    请根据现有事件和故事逻辑，补充合适的事件来达到上述密度目标。
    特别注意：{stage_name}阶段需要{density_requirements.get('description', '合理的事件分布')}

    请返回补充的事件设计：
    {{
        "supplemental_events": {{
            "major_events": [],
            "medium_events": [],
            "minor_events": [],
            "special_events": []
        }}
    }}
    """
            
            try:
                supplement_result = self.generator.api_client.generate_content_with_retry(
                    "event_supplement",
                    supplement_prompt,
                    purpose=f"补充{stage_name}阶段事件"
                )
                
                if supplement_result and "supplemental_events" in supplement_result:
                    supplemental_events = supplement_result["supplemental_events"]
                    
                    # 验证补充的事件
                    validated_events = self._validate_supplemental_events(supplemental_events, start_chap, end_chap)
                    
                    # 合并补充的事件
                    for event_type in ["major_events", "medium_events", "minor_events", "special_events"]:
                        if event_type in validated_events and validated_events[event_type]:
                            if event_type not in events:
                                events[event_type] = []
                            events[event_type].extend(validated_events[event_type])
                    
                    # 重新排序事件
                    events = self._sort_events_by_chapter(events)
                    
                    # 更新事件系统
                    if "stage_writing_plan" in writing_plan:
                        writing_plan["stage_writing_plan"]["event_system"] = events
                    else:
                        writing_plan["event_system"] = events
                    
                    # 记录补充结果
                    added_major = len(validated_events.get('major_events', []))
                    added_medium = len(validated_events.get('medium_events', []))
                    added_minor = len(validated_events.get('minor_events', []))
                    added_special = len(validated_events.get('special_events', []))
                    
                    if added_major > 0 or added_medium > 0 or added_minor > 0 or added_special > 0:
                        print(f"  ✅ AI为{stage_name}阶段补充了{added_major}个重大事件，{added_medium}个中型事件，{added_minor}个小型事件，{added_special}个特殊事件")
                        
            except Exception as e:
                print(f"  ❌ AI补充事件出错: {e}")
        
        return writing_plan

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

    def calculate_max_event_gap(self, events: List) -> int:
        """计算最大事件间隔"""
        if not events:
            return 999  # 没有事件，间隔极大
        
        # 按开始章节排序
        sorted_events = sorted(events, key=lambda x: x.get('start_chapter', 0))
        
        max_gap = 0
        
        # 检查第一个事件之前的间隔（假设阶段从第1章开始）
        first_event_start = sorted_events[0].get('start_chapter', 1)
        if first_event_start > 1:
            max_gap = max(max_gap, first_event_start - 1)
        
        # 检查事件之间的间隔
        for i in range(1, len(sorted_events)):
            prev_event = sorted_events[i-1]
            current_event = sorted_events[i]
            
            prev_event_end = prev_event.get('end_chapter', prev_event.get('start_chapter', 0))
            current_event_start = current_event.get('start_chapter', 0)
            
            gap = current_event_start - prev_event_end - 1
            max_gap = max(max_gap, gap)
        
        return max_gap

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