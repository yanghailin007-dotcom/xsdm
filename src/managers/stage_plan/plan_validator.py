"""
计划验证器 - 负责验证写作计划的各种指标
"""
import json
from typing import Dict, List, Optional, Tuple
from itertools import groupby
from operator import itemgetter
from src.utils.logger import get_logger
from src.managers.StagePlanUtils import parse_chapter_range


class PlanValidator:
    """计划验证器 - 验证写作计划的完整性和合理性"""
    
    def __init__(self, logger_name: str = "PlanValidator"):
        self.logger = get_logger(logger_name)
    
    def validate_goal_hierarchy_coherence(self, stage_writing_plan: Dict, 
                                        stage_name: str, api_client) -> Dict:
        """
        验证目标层级一致性
        
        Args:
            stage_writing_plan: 阶段写作计划
            stage_name: 阶段名称
            api_client: API客户端
            
        Returns:
            评估结果字典
        """
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段目标层级一致性...")
        
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
            coherence_assessment = api_client.generate_content_with_retry(
                content_type="goal_hierarchy_coherence_assessment_master_reviewer",
                user_prompt=coherence_prompt,
                purpose=f"【网文白金策划师】评估{stage_name}阶段目标层级一致性"
            )
            
            if coherence_assessment:
                self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段目标层级一致性完成。")
                return coherence_assessment
            else:
                self.logger.warn(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段目标层级一致性失败，使用默认结果。")
                return self._create_default_coherence_assessment()
                
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】目标层级评估出错: {e}，使用默认结果。")
            return self._create_default_coherence_assessment()
    
    def validate_scene_planning_coverage(self, stage_writing_plan: Dict, 
                                       stage_name: str, stage_range: str) -> Dict:
        """
        验证场景规划覆盖的完整性
        
        Args:
            stage_writing_plan: 阶段写作计划
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            
        Returns:
            覆盖率分析结果
        """
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
    
    def validate_and_correct_major_event_coverage(self, major_event_skeleton: Dict,
                                                 fleshed_out_major_event: Dict) -> Dict:
        """
        验证并修正单个重大事件内部的章节覆盖率
        
        Args:
            major_event_skeleton: 重大事件骨架
            fleshed_out_major_event: 分解后的重大事件
            
        Returns:
            修正后的重大事件
        """
        if not major_event_skeleton or not fleshed_out_major_event:
            return fleshed_out_major_event
        
        target_range_str = major_event_skeleton.get("chapter_range")
        if not target_range_str:
            self.logger.warn(f"  ⚠️ 警告：重大事件骨架 '{major_event_skeleton.get('name')}' 缺少 'chapter_range'")
            return fleshed_out_major_event
        
        try:
            target_start, target_end = parse_chapter_range(target_range_str)
            target_chapters = set(range(target_start, target_end + 1))
        except Exception as e:
            self.logger.error(f"  ❌ 错误：解析重大事件骨架范围 '{target_range_str}' 失败: {e}")
            return fleshed_out_major_event
        
        # 收集所有已覆盖的章节
        covered_chapters = set()
        all_sub_events = []
        
        composition = fleshed_out_major_event.get("composition", {})
        if composition:
            for phase_events in composition.values():
                if isinstance(phase_events, list):
                    all_sub_events.extend(phase_events)
        
        special_events = fleshed_out_major_event.get("special_emotional_events", [])
        if special_events:
            all_sub_events.extend(special_events)
        
        if not all_sub_events:
            self.logger.warn(f"  ⚠️ 警告：重大事件 '{fleshed_out_major_event.get('name')}' 内部分解后没有任何子事件")
            return fleshed_out_major_event
        
        for event in all_sub_events:
            range_str = event.get("chapter_range")
            if range_str:
                try:
                    start, end = parse_chapter_range(range_str)
                    for i in range(start, end + 1):
                        covered_chapters.add(i)
                except Exception:
                    pass
        
        # 找出遗漏的章节
        missing_chapters = sorted(list(target_chapters - covered_chapters))
        if not missing_chapters:
            return fleshed_out_major_event
        
        self.logger.info(f"  🔧 检测到重大事件 '{fleshed_out_major_event.get('name')}' 遗漏章节: {missing_chapters}，启动自动修正...")
        
        # 找到最后一个事件并扩展其范围
        last_event_to_extend = None
        max_end_chapter = -1
        
        for event in all_sub_events:
            range_str = event.get("chapter_range")
            if range_str:
                try:
                    _, end = parse_chapter_range(range_str)
                    if end > max_end_chapter:
                        max_end_chapter = end
                        last_event_to_extend = event
                except Exception:
                    continue
        
        if last_event_to_extend:
            original_range = last_event_to_extend["chapter_range"]
            start, end = parse_chapter_range(original_range)
            new_end = max(end, max(missing_chapters))
            
            if start == new_end:
                new_range_str = f"{start}-{start}章"
            else:
                new_range_str = f"{start}-{new_end}章"
            
            last_event_to_extend["chapter_range"] = new_range_str
            self.logger.info(f"  ✅ 自动修正成功：将事件 '{last_event_to_extend.get('name')}' 的章节范围从 '{original_range}' 扩展为 '{new_range_str}'。")
        else:
            self.logger.error(f"  ❌ 自动修正失败：在 '{fleshed_out_major_event.get('name')}' 中未找到可供扩展范围的子事件。")
        
        return fleshed_out_major_event
    
    def _build_goal_hierarchy_prompt(self, stage_name: str, plan_data: Dict, 
                                    major_events: List[Dict]) -> str:
        """构建目标层级评估提示词"""
        hierarchy_description = self._build_hierarchy_description(major_events)
        
        prompt_parts = [
            "# 🎯 【AI网文白金策划师】对阶段事件目标层级一致性进行\"商业价值\"深度评估",
            "",
            "## 评估任务",
            f"作为一位对网文爆款打造和读者留存有着极致追求的【网文白金策划师】，你将对**{stage_name}**阶段的事件目标层级进行\"商业价值\"深度评估。",
            "",
            "## 事件层级结构详情",
            hierarchy_description,
            "",
            "## 评估维度 (请以\"爆款网文\"的标准进行评判，1-10分制)：",
            "",
            "### 1. 目标传递连贯性与效率 (权重 20%)",
            "### 2. 情绪目标一致性与爽点分布 (权重 20%)",
            "### 3. 贡献关系明确性与驱动力 (权重 15%)",
            "### 4. 逻辑自洽性与新意融合 (权重 15%)",
            "### 5. 可执行性与写作指导性 (权重 10%)",
            "### 6. 主题融合度 (权重 10%)",
            "### 7. 角色成长驱动力 (权重 10%)",
            "",
            "## 📋 输出格式",
            "{",
            '  "overall_coherence_score": "float",',
            '  "goal_transfer_score": "float",',
            '  "goal_transfer_comment": "string",',
            '  "emotional_coherence_score": "float",',
            '  "emotional_coherence_comment": "string",',
            '  "contribution_clarity_score": "float",',
            '  "contribution_clarity_comment": "string",',
            '  "logic_innovation_score": "float",',
            '  "logic_innovation_comment": "string",',
            '  "executability_score": "float",',
            '  "executability_comment": "string",',
            '  "thematic_deepening_score": "float",',
            '  "thematic_deepening_comment": "string",',
            '  "character_growth_score": "float",',
            '  "character_growth_comment": "string",',
            '  "master_reviewer_verdict": "string",',
            '  "perfection_suggestions": ["string"]',
            "}"
        ]
        
        return "\n".join(prompt_parts)
    
    def _build_hierarchy_description(self, major_events: List[Dict]) -> str:
        """构建事件层级结构描述"""
        if not major_events:
            return "当前阶段没有重大事件。"
        
        description_parts = []
        for i, major_event in enumerate(major_events, 1):
            major_event_name = major_event.get('name', '未命名')
            description_parts.append(f"### 🚨 重大事件 {i}: {major_event_name}")
            description_parts.append(f"- **章节范围**: {major_event.get('chapter_range', '未指定')}")
            description_parts.append(f"- **核心目标**: {major_event.get('main_goal', '未指定')}")
            
            composition = major_event.get("composition", {})
            medium_events_count = sum(len(events) for events in composition.values() if isinstance(events, list))
            description_parts.append(f"- **包含 {medium_events_count} 个中型事件**")
            
            for phase_name, medium_events in composition.items():
                if not isinstance(medium_events, list):
                    continue
                for j, medium_event in enumerate(medium_events, 1):
                    if not isinstance(medium_event, dict):
                        continue
                    description_parts.append(f"  #### 📈 中型事件 {j} ({phase_name}): {medium_event.get('name', '未命名')}")
        
        return "\n".join(description_parts)
    
    def _create_default_coherence_assessment(self) -> Dict:
        """创建默认的一致性评估结果"""
        return {
            "overall_coherence_score": 5.0,
            "goal_transfer_score": 5.0,
            "goal_transfer_comment": "评估系统暂时不可用",
            "emotional_coherence_score": 5.0,
            "emotional_coherence_comment": "评估系统暂时不可用",
            "contribution_clarity_score": 5.0,
            "contribution_clarity_comment": "评估系统暂时不可用",
            "logic_innovation_score": 5.0,
            "logic_innovation_comment": "评估系统暂时不可用",
            "executability_score": 5.0,
            "executability_comment": "评估系统暂时不可用",
            "thematic_deepening_score": 5.0,
            "thematic_deepening_comment": "评估系统暂时不可用",
            "character_growth_score": 5.0,
            "character_growth_comment": "评估系统暂时不可用",
            "master_reviewer_verdict": "评估系统暂时不可用",
            "perfection_suggestions": ["等待AI评估服务恢复后重新评估"]
        }
    
    def validate_event_continuity(self, stage_writing_plan: Dict, stage_name: str,
                                  stage_range: str, creative_seed: str,
                                  novel_title: str, novel_synopsis: str,
                                  api_client) -> Dict:
        """
        验证事件连续性
        
        Args:
            stage_writing_plan: 阶段写作计划
            stage_name: 阶段名称
            stage_range: 阶段范围
            creative_seed: 创意种子
            novel_title: 小说标题
            novel_synopsis: 小说简介
            api_client: API客户端
            
        Returns:
            连续性评估结果字典
        """
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段事件连续性...")
        
        # 提取阶段计划中的关键信息
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        
        event_system = plan_data.get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        # 构建连续性评估提示词
        continuity_prompt = self._build_continuity_assessment_prompt(
            stage_name, stage_range, creative_seed, novel_title,
            novel_synopsis, major_events
        )
        
        try:
            continuity_assessment = api_client.generate_content_with_retry(
                content_type="stage_event_continuity",
                user_prompt=continuity_prompt,
                purpose=f"【网文白金策划师】评估{stage_name}阶段事件连续性"
            )
            
            if continuity_assessment:
                self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段事件连续性完成。")
                return continuity_assessment
            else:
                self.logger.warn(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段事件连续性失败，使用默认结果。")
                return self._create_default_continuity_assessment()
                
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】连续性评估出错: {e}，使用默认结果。")
            return self._create_default_continuity_assessment()
    
    def _build_continuity_assessment_prompt(self, stage_name: str, stage_range: str,
                                           creative_seed: str, novel_title: str,
                                           novel_synopsis: str, major_events: List[Dict]) -> str:
        """构建连续性评估提示词"""
        events_description = self._build_events_description(major_events)
        
        prompt_parts = [
            "# 🎯 【AI网文白金策划师】对阶段事件连续性进行\"商业价值\"深度评估",
            "",
            "## 评估任务",
            f"作为一位对网文爆款打造和读者留存有着极致追求的【网文白金策划师】，你将对**{stage_name}**阶段的事件连续性进行\"商业价值\"深度评估。",
            "",
            "## 背景信息",
            f"- **小说标题**: {novel_title}",
            f"- **创意种子**: {creative_seed}",
            f"- **小说简介**: {novel_synopsis}",
            f"- **阶段范围**: {stage_range}",
            "",
            "## 事件详情",
            events_description,
            "",
            "## 评估维度 (请以\"爆款网文\"的标准进行评判，1-10分制)：",
            "",
            "### 1. 逻辑连贯性 (权重 25%)",
            "- 事件之间的因果关系是否清晰",
            "- 前后事件是否有合理的铺垫和呼应",
            "",
            "### 2. 节奏合理性 (权重 25%)",
            "- 事件密度是否恰当",
            "- 是否有张弛有度的节奏变化",
            "",
            "### 3. 情感连续性 (权重 25%)",
            "- 情绪发展是否自然流畅",
            "- 是否符合情绪弧线设计",
            "",
            "### 4. 主线推进效率 (权重 25%)",
            "- 事件是否有效推进主线",
            "- 是否有冗余或偏离主线的事件",
            "",
            "## 📋 输出格式",
            "{",
            '  "overall_continuity_score": "float (0-10)",',
            '  "logic_coherence_score": "float (0-10)",',
            '  "logic_coherence_comment": "string",',
            '  "narrative_rhythm_score": "float (0-10)",',
            '  "narrative_rhythm_comment": "string",',
            '  "emotional_continuity_score": "float (0-10)",',
            '  "emotional_continuity_comment": "string",',
            '  "plot_progression_score": "float (0-10)",',
            '  "plot_progression_comment": "string",',
            '  "critical_issues": [',
            '    "string - 列出最关键的3-5个连续性问题"',
            '  ],',
            '  "improvement_recommendations": [',
            '    "string - 给出3-5条具体可行的改进建议"',
            '  ],',
            '  "master_reviewer_verdict": "string - 总体评价"',
            "}"
        ]
        
        return "\n".join(prompt_parts)
    
    def _build_events_description(self, major_events: List[Dict]) -> str:
        """构建事件描述"""
        if not major_events:
            return "当前阶段没有重大事件。"
        
        description_parts = []
        for i, major_event in enumerate(major_events, 1):
            major_event_name = major_event.get('name', '未命名')
            description_parts.append(f"### 🚨 重大事件 {i}: {major_event_name}")
            description_parts.append(f"- **章节范围**: {major_event.get('chapter_range', '未指定')}")
            description_parts.append(f"- **核心目标**: {major_event.get('main_goal', '未指定')}")
            description_parts.append(f"- **阶段角色**: {major_event.get('role_in_stage_arc', '未指定')}")
            
            composition = major_event.get("composition", {})
            medium_events_count = sum(len(events) for events in composition.values() if isinstance(events, list))
            description_parts.append(f"- **包含 {medium_events_count} 个中型事件**")
            
            for phase_name, medium_events in composition.items():
                if not isinstance(medium_events, list):
                    continue
                for j, medium_event in enumerate(medium_events, 1):
                    if not isinstance(medium_event, dict):
                        continue
                    description_parts.append(f"  #### 📈 中型事件 {j} ({phase_name}): {medium_event.get('name', '未命名')}")
                    description_parts.append(f"     - 范围: {medium_event.get('chapter_range', '未指定')}")
                    description_parts.append(f"     - 目标: {medium_event.get('main_goal', '未指定')}")
        
        return "\n".join(description_parts)
    
    def _create_default_continuity_assessment(self) -> Dict:
        """创建默认的连续性评估结果"""
        return {
            "overall_continuity_score": 10.0,
            "logic_coherence_score": 10.0,
            "narrative_rhythm_score": 10.0,
            "emotional_continuity_score": 10.0,
            "plot_progression_score": 10.0,
            "logic_coherence_comment": "评估系统暂时不可用",
            "narrative_rhythm_comment": "评估系统暂时不可用",
            "emotional_continuity_comment": "评估系统暂时不可用",
            "plot_progression_comment": "评估系统暂时不可用",
            "critical_issues": [],
            "improvement_recommendations": [],
            "master_reviewer_verdict": "评估系统暂时不可用，使用满分默认值"
        }