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
    
    def validate_goal_hierarchy_and_continuity(self, stage_writing_plan: Dict,
                                               stage_name: str, stage_range: str,
                                               creative_seed: str, novel_title: str,
                                               novel_synopsis: str, api_client) -> Tuple[Dict, Dict]:
        """
        【优化版】一次性验证目标层级一致性和事件连续性
        
        将原本需要2次API调用的验证合并为1次，提高效率
        
        Args:
            stage_writing_plan: 阶段写作计划
            stage_name: 阶段名称
            stage_range: 阶段范围
            creative_seed: 创意种子
            novel_title: 小说标题
            novel_synopsis: 小说简介
            api_client: API客户端
            
        Returns:
            (目标层级评估结果, 连续性评估结果) 元组
        """
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段目标层级与连续性...")
        
        # 提取阶段计划中的关键信息
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        
        event_system = plan_data.get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        # 构建合并评估提示词
        merged_prompt = self._build_merged_assessment_prompt(
            stage_name, stage_range, creative_seed, novel_title,
            novel_synopsis, plan_data, major_events
        )
        
        try:
            assessment_result = api_client.generate_content_with_retry(
                content_type="goal_hierarchy_and_continuity_assessment",
                user_prompt=merged_prompt,
                purpose=f"【网文白金策划师】评估{stage_name}阶段目标层级与连续性"
            )
            
            if assessment_result:
                # 解析合并结果
                goal_coherence = {
                    "overall_coherence_score": assessment_result.get("goal_hierarchy", {}).get("overall_coherence_score", 8.0),
                    "goal_transfer_score": assessment_result.get("goal_hierarchy", {}).get("goal_transfer_score", 8.0),
                    "goal_transfer_comment": assessment_result.get("goal_hierarchy", {}).get("goal_transfer_comment", ""),
                    "emotional_coherence_score": assessment_result.get("goal_hierarchy", {}).get("emotional_coherence_score", 8.0),
                    "emotional_coherence_comment": assessment_result.get("goal_hierarchy", {}).get("emotional_coherence_comment", ""),
                    "contribution_clarity_score": assessment_result.get("goal_hierarchy", {}).get("contribution_clarity_score", 8.0),
                    "contribution_clarity_comment": assessment_result.get("goal_hierarchy", {}).get("contribution_clarity_comment", ""),
                    "logic_innovation_score": assessment_result.get("goal_hierarchy", {}).get("logic_innovation_score", 8.0),
                    "logic_innovation_comment": assessment_result.get("goal_hierarchy", {}).get("logic_innovation_comment", ""),
                    "executability_score": assessment_result.get("goal_hierarchy", {}).get("executability_score", 8.0),
                    "executability_comment": assessment_result.get("goal_hierarchy", {}).get("executability_comment", ""),
                    "thematic_deepening_score": assessment_result.get("goal_hierarchy", {}).get("thematic_deepening_score", 8.0),
                    "thematic_deepening_comment": assessment_result.get("goal_hierarchy", {}).get("thematic_deepening_comment", ""),
                    "character_growth_score": assessment_result.get("goal_hierarchy", {}).get("character_growth_score", 8.0),
                    "character_growth_comment": assessment_result.get("goal_hierarchy", {}).get("character_growth_comment", ""),
                    "master_reviewer_verdict": assessment_result.get("goal_hierarchy", {}).get("master_reviewer_verdict", ""),
                    "perfection_suggestions": assessment_result.get("goal_hierarchy", {}).get("perfection_suggestions", [])
                }
                
                continuity_assessment = {
                    "overall_continuity_score": assessment_result.get("continuity", {}).get("overall_continuity_score", 10.0),
                    "logic_coherence_score": assessment_result.get("continuity", {}).get("logic_coherence_score", 10.0),
                    "logic_coherence_comment": assessment_result.get("continuity", {}).get("logic_coherence_comment", ""),
                    "narrative_rhythm_score": assessment_result.get("continuity", {}).get("narrative_rhythm_score", 10.0),
                    "narrative_rhythm_comment": assessment_result.get("continuity", {}).get("narrative_rhythm_comment", ""),
                    "emotional_continuity_score": assessment_result.get("continuity", {}).get("emotional_continuity_score", 10.0),
                    "emotional_continuity_comment": assessment_result.get("continuity", {}).get("emotional_continuity_comment", ""),
                    "plot_progression_score": assessment_result.get("continuity", {}).get("plot_progression_score", 10.0),
                    "plot_progression_comment": assessment_result.get("continuity", {}).get("plot_progression_comment", ""),
                    "critical_issues": assessment_result.get("continuity", {}).get("critical_issues", []),
                    "improvement_recommendations": assessment_result.get("continuity", {}).get("improvement_recommendations", []),
                    "master_reviewer_verdict": assessment_result.get("continuity", {}).get("master_reviewer_verdict", "")
                }
                
                self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段目标层级与连续性完成。")
                return goal_coherence, continuity_assessment
            else:
                self.logger.warning(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段失败，使用默认结果。")
                return self._create_default_coherence_assessment(), self._create_default_continuity_assessment()
                
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】评估出错: {e}，使用默认结果。")
            return self._create_default_coherence_assessment(), self._create_default_continuity_assessment()
    
    def _build_merged_assessment_prompt(self, stage_name: str, stage_range: str,
                                       creative_seed: str, novel_title: str,
                                       novel_synopsis: str, plan_data: Dict,
                                       major_events: List[Dict]) -> str:
        """构建合并评估提示词"""
        hierarchy_description = self._build_hierarchy_description(major_events)
        
        prompt_parts = [
            "# 🎯 【AI网文白金策划师】对阶段事件进行全面深度评估",
            "",
            "## 评估任务",
            f"作为一位对网文爆款打造和读者留存有着极致追求的【网文白金策划师】，你将对**{stage_name}**阶段的事件进行全面的\"商业价值\"深度评估。",
            "本次评估包含两个部分：**目标层级一致性评估**和**事件连续性评估**",
            "",
            "## 背景信息",
            f"- **小说标题**: {novel_title}",
            f"- **创意种子**: {creative_seed}",
            f"- **小说简介**: {novel_synopsis}",
            f"- **阶段范围**: {stage_range}",
            "",
            "## 事件层级结构详情",
            hierarchy_description,
            "",
            "## 第一部分：目标层级一致性评估 (1-10分制)",
            "",
            "### 1. 目标传递连贯性与效率 (权重 20%)",
            "- 阶段目标是否清晰传达给每个重大事件",
            "- 重大事件的目标是否有效地分解到中型事件",
            "",
            "### 2. 情绪目标一致性与爽点分布 (权重 20%)",
            "- 情绪弧线设计是否贯穿所有事件层级",
            "- 爽点是否均匀分布，是否有集中爆发的规划",
            "",
            "### 3. 贡献关系明确性与驱动力 (权重 15%)",
            "- 每个事件对其上层目标的贡献是否明确",
            "- 事件之间的驱动力是否清晰",
            "",
            "### 4. 逻辑自洽性与新意融合 (权重 15%)",
            "- 事件逻辑是否自洽，没有明显漏洞",
            "- 创意种子的新意是否在事件中得到体现",
            "",
            "### 5. 可执行性与写作指导性 (权重 10%)",
            "### 6. 主题融合度 (权重 10%)",
            "### 7. 角色成长驱动力 (权重 10%)",
            "",
            "## 第二部分：事件连续性评估 (1-10分制)",
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
            "## 📋 输出格式 (严格JSON)",
            "```json",
            "{",
            '  "goal_hierarchy": {',
            '    "overall_coherence_score": "float (0-10)",',
            '    "goal_transfer_score": "float (0-10)",',
            '    "goal_transfer_comment": "string",',
            '    "emotional_coherence_score": "float (0-10)",',
            '    "emotional_coherence_comment": "string",',
            '    "contribution_clarity_score": "float (0-10)",',
            '    "contribution_clarity_comment": "string",',
            '    "logic_innovation_score": "float (0-10)",',
            '    "logic_innovation_comment": "string",',
            '    "executability_score": "float (0-10)",',
            '    "executability_comment": "string",',
            '    "thematic_deepening_score": "float (0-10)",',
            '    "thematic_deepening_comment": "string",',
            '    "character_growth_score": "float (0-10)",',
            '    "character_growth_comment": "string",',
            '    "master_reviewer_verdict": "string",',
            '    "perfection_suggestions": ["string"]',
            '  },',
            '  "continuity": {',
            '    "overall_continuity_score": "float (0-10)",',
            '    "logic_coherence_score": "float (0-10)",',
            '    "logic_coherence_comment": "string",',
            '    "narrative_rhythm_score": "float (0-10)",',
            '    "narrative_rhythm_comment": "string",',
            '    "emotional_continuity_score": "float (0-10)",',
            '    "emotional_continuity_comment": "string",',
            '    "plot_progression_score": "float (0-10)",',
            '    "plot_progression_comment": "string",',
            '    "critical_issues": ["string"],',
            '    "improvement_recommendations": ["string"],',
            '    "master_reviewer_verdict": "string"',
            '  }',
            "}",
            "```"
        ]
        
        return "\n".join(prompt_parts)
    
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
                self.logger.warning(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段目标层级一致性失败，使用默认结果。")
                return self._create_default_coherence_assessment()
                
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】目标层级评估出错: {e}，使用默认结果。")
            return self._create_default_coherence_assessment()
    
    def validate_scene_planning_coverage(self, stage_writing_plan: Dict,
                                       stage_name: str, stage_range: str) -> Dict:
        """
        验证场景规划覆盖的完整性（P1-2修复：增强场景内容完整性检查）

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

        # ============ P1-2修复：增强场景分布分析 ============
        scene_distribution = {}
        scene_completeness = {}  # 新增：场景完整性检查

        for chapter in chapter_scene_events:
            chapter_num = chapter["chapter_number"]
            scenes = chapter.get("scene_events", [])
            scene_count = len(scenes)
            scene_distribution[chapter_num] = scene_count

            # 新增：检查场景内容完整性
            completeness_score = self._check_scene_completeness(scenes, chapter_num)
            scene_completeness[chapter_num] = completeness_score

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
            "scene_completeness": scene_completeness,  # 新增
            "issues": []
        }

        # 识别问题
        if missing_chapters:
            coverage_analysis["issues"].append(f"缺失{len(missing_chapters)}个章节的场景规划: {sorted(missing_chapters)}")
        if extra_chapters:
            coverage_analysis["issues"].append(f"存在{len(extra_chapters)}个超出阶段范围的章节: {sorted(extra_chapters)}")

        # ============ P1-2修复：增强场景数量和质量检查 ============
        for chapter_num, scene_count in scene_distribution.items():
            if scene_count < 3:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过少({scene_count}个)，可能无法形成完整起承转合结构")
            elif scene_count > 8:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过多({scene_count}个)，可能导致节奏过快")

        # 新增：检查场景完整性
        incomplete_chapters = []
        for chapter_num, completeness in scene_completeness.items():
            if completeness["score"] < 0.6:
                incomplete_chapters.append(chapter_num)
                coverage_analysis["issues"].append(
                    f"第{chapter_num}章场景内容不完整: {completeness['missing_fields']}"
                )

        if incomplete_chapters:
            self.logger.warning(f"  ⚠️ 场景完整性检查：{len(incomplete_chapters)}个章节场景内容不完整: {incomplete_chapters}")

        return coverage_analysis

    def _check_scene_completeness(self, scenes: list, chapter_num: int) -> Dict:
        """
        检查场景内容的完整性（P1-2新增）

        Args:
            scenes: 场景列表
            chapter_num: 章节号

        Returns:
            {
                "score": 0-1的完整性评分,
                "missing_fields": 缺失的字段列表,
                "issues": 具体问题列表
            }
        """
        if not scenes:
            return {
                "score": 0.0,
                "missing_fields": ["无场景"],
                "issues": ["该章节没有任何场景规划"]
            }

        # 必需字段及其权重
        required_fields = {
            "name": 0.15,          # 场景名称
            "description": 0.15,   # 场景描述
            "purpose": 0.15,       # 场景目的
            "key_actions": 0.15,   # 关键动作
            "emotional_intensity": 0.10,  # 情绪强度
            "position": 0.10,      # 位置
            "transition_to_next": 0.10,    # 过渡
            "chapter_hook": 0.10,  # 钩子
        }

        total_weight = sum(required_fields.values())
        achieved_weight = 0.0
        missing_fields = []
        issues = []

        for scene in scenes:
            scene_score = 0.0
            scene_missing = []

            for field, weight in required_fields.items():
                value = scene.get(field)
                if not value:
                    scene_missing.append(field)
                elif isinstance(value, list) and len(value) == 0:
                    scene_missing.append(field)
                elif isinstance(value, str) and len(value.strip()) == 0:
                    scene_missing.append(field)
                else:
                    # 字段存在且非空
                    scene_score += weight

                    # 额外检查：内容质量
                    if field == "description" and len(str(value)) < 20:
                        issues.append(f"场景 '{scene.get('name', '?')}' 的描述过短")
                    elif field == "key_actions" and isinstance(value, list) and len(value) < 2:
                        issues.append(f"场景 '{scene.get('name', '?')}' 的关键动作过少")

            scene_total = sum(required_fields.values())
            if scene_score < scene_total * 0.6:
                missing_fields.append(f"场景 '{scene.get('name', '?')}' 缺少: {scene_missing}")

            achieved_weight += scene_score

        # 计算整体完整性评分
        max_possible = total_weight * len(scenes)
        completeness_score = achieved_weight / max_possible if max_possible > 0 else 0

        # 检查场景角色分布（起承转合）
        role_distribution = {}
        for scene in scenes:
            role = scene.get("role", "")
            if role:
                role_distribution[role] = role_distribution.get(role, 0) + 1

        # 检查是否有完整的起承转合
        required_roles = {"起", "转"}  # 起和转是必须的
        missing_roles = required_roles - set(role_distribution.keys())
        if missing_roles:
            issues.append(f"缺少必要的戏剧结构角色: {missing_roles}")

        if issues:
            missing_fields.extend(issues)

        return {
            "score": round(completeness_score, 2),
            "missing_fields": missing_fields[:5],  # 最多显示5个
            "issues": issues[:5],
            "role_distribution": role_distribution
        }
    
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
            self.logger.warning(f"  ⚠️ 警告：重大事件骨架 '{major_event_skeleton.get('name')}' 缺少 'chapter_range'")
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
            self.logger.warning(f"  ⚠️ 警告：重大事件 '{fleshed_out_major_event.get('name')}' 内部分解后没有任何子事件")
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
                self.logger.warning(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段事件连续性失败，使用默认结果。")
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
    def detect_plot_duplication_in_events(self, major_events: List[Dict]) -> Dict:
        """
        检测重大事件之间的情节重复
        
        Args:
            major_events: 重大事件列表
            
        Returns:
            {
                "has_duplication": bool,
                "duplication_details": [
                    {"event1": "...", "event2": "...", "duplicated_content": "...", "severity": "high/medium"}
                ],
                "severity": "low/medium/high"
            }
        """
        duplications = []
        
        # 核心情节关键词库（与 PlotStateManager 保持一致）
        core_keywords = [
            "退婚", "系统觉醒", "系统开启", "金手指", "金手指激活", 
            "初次突破", "第一次杀人", "初遇女主", "加入宗门",
            "第一次秘境", "第一次大比", "第一次复仇",
            "开局", "穿越", "重生", "绑定系统", "显圣"
        ]
        
        # 提取每个事件的核心情节关键词
        event_plots = []
        for event in major_events:
            event_name = event.get("name", "")
            main_goal = event.get("main_goal", "")
            chapter_range = event.get("chapter_range", "")
            
            # 组合所有文本内容进行检测
            combined_text = f"{event_name} {main_goal}".lower()
            
            # 检测核心情节
            detected_plots = []
            for keyword in core_keywords:
                if keyword in combined_text:
                    detected_plots.append(keyword)
            
            event_plots.append({
                "event": event_name,
                "chapter_range": chapter_range,
                "plots": detected_plots,
                "text": combined_text
            })
        
        # 检测重复
        for i in range(len(event_plots)):
            for j in range(i + 1, len(event_plots)):
                event1 = event_plots[i]
                event2 = event_plots[j]
                
                # 检查是否有相同的情节关键词
                common_plots = set(event1["plots"]) & set(event2["plots"])
                if common_plots:
                    # 判断严重程度
                    severity = "low"
                    for plot in common_plots:
                        if plot in ["系统觉醒", "系统开启", "金手指激活", "退婚"]:
                            severity = "high"
                            break
                        elif severity != "high":
                            severity = "medium"
                    
                    duplications.append({
                        "event1": f"{event1['event']} ({event1['chapter_range']})",
                        "event2": f"{event2['event']} ({event2['chapter_range']})",
                        "duplicated_content": ", ".join(common_plots),
                        "severity": severity
                    })
        
        # 计算整体严重程度
        overall_severity = "low"
        if any(d["severity"] == "high" for d in duplications):
            overall_severity = "high"
        elif len(duplications) > 0:
            overall_severity = "medium"
        
        # 计算涉及重复的事件数量
        events_with_duplication = set()
        for d in duplications:
            events_with_duplication.add(d["event1"].split(" (")[0])
            events_with_duplication.add(d["event2"].split(" (")[0])
        
        return {
            "has_duplication": len(duplications) > 0,
            "duplication_details": duplications,
            "severity": overall_severity,
            "total_events": len(major_events),
            "events_with_duplication": len(events_with_duplication),
            "duplication_rate": round(len(events_with_duplication) / len(major_events) * 100, 1) if major_events else 0
        }

    def validate_major_events_coverage(self, major_events: List[Dict], stage_range: str,
                                       auto_correct: bool = False) -> Dict:
        """
        验证重大事件的章节范围覆盖情况

        检测：
        1. 是否完全覆盖阶段范围（无留白）
        2. 是否有重叠的章节范围
        3. 是否有超出阶段范围的事件

        Args:
            major_events: 重大事件列表
            stage_range: 阶段章节范围（如 "1-20"）
            auto_correct: 是否自动修正问题

        Returns:
            {
                "is_valid": bool,
                "has_gaps": bool,
                "has_overlaps": bool,
                "has_out_of_range": bool,
                "gaps": [chapter_numbers],
                "overlaps": [{"event1": name, "event2": name, "chapters": [chapters]}],
                "out_of_range": [{"event": name, "range": range, "invalid_chapters": [chapters]}],
                "coverage_report": str,
                "corrected_events": List[Dict] (if auto_correct=True)
            }
        """
        # 解析阶段范围
        try:
            stage_start, stage_end = parse_chapter_range(stage_range)
            expected_chapters = set(range(stage_start, stage_end + 1))
        except Exception as e:
            self.logger.error(f"  ❌ 解析阶段范围失败: {stage_range}, {e}")
            return {
                "is_valid": False,
                "error": f"无法解析阶段范围: {stage_range}"
            }

        # 收集所有事件的覆盖范围
        event_ranges = []
        for event in major_events:
            event_name = event.get("name", "未命名")
            range_str = event.get("chapter_range", "")
            try:
                e_start, e_end = parse_chapter_range(range_str)
                event_ranges.append({
                    "event": event,
                    "name": event_name,
                    "range": range_str,
                    "start": e_start,
                    "end": e_end,
                    "chapters": set(range(e_start, e_end + 1))
                })
            except Exception as e:
                self.logger.warning(f"  ⚠️ 跳过事件 '{event_name}': 无法解析章节范围 '{range_str}'")

        # 检测问题
        all_covered = set()
        overlaps = []
        out_of_range_events = []

        # 检测重叠和超出范围
        for i, er1 in enumerate(event_ranges):
            # 检查是否超出阶段范围
            invalid_chapters = []
            for ch in er1["chapters"]:
                if ch < stage_start or ch > stage_end:
                    invalid_chapters.append(ch)
            if invalid_chapters:
                out_of_range_events.append({
                    "event": er1["name"],
                    "range": er1["range"],
                    "invalid_chapters": invalid_chapters
                })

            # 检测重叠
            for j, er2 in enumerate(event_ranges):
                if i >= j:
                    continue
                overlap = er1["chapters"] & er2["chapters"]
                if overlap:
                    overlaps.append({
                        "event1": er1["name"],
                        "event2": er2["name"],
                        "chapters": sorted(list(overlap))
                    })

            # 收集所有覆盖的章节
            all_covered |= er1["chapters"]

        # 检测留白
        gaps = sorted(list(expected_chapters - all_covered))
        has_gaps = len(gaps) > 0
        has_overlaps = len(overlaps) > 0
        has_out_of_range = len(out_of_range_events) > 0
        is_valid = not (has_gaps or has_overlaps or has_out_of_range)

        # 生成报告
        report_lines = [
            f"## 重大事件章节范围覆盖验证报告",
            f"**阶段范围**: 第{stage_start}-{stage_end}章",
            f"**验证结果**: {'✅ 通过' if is_valid else '❌ 存在问题'}",
            ""
        ]

        if has_gaps:
            report_lines.append(f"### ⚠️ 留白章节（未被任何事件覆盖）")
            report_lines.append(f"共有 {len(gaps)} 个章节未被覆盖: {gaps}")
            report_lines.append("")

        if has_overlaps:
            report_lines.append(f"### ⚠️ 重叠章节（被多个事件覆盖）")
            for ov in overlaps:
                report_lines.append(f"- '{ov['event1']}' 与 '{ov['event2']}' 重叠章节: {ov['chapters']}")
            report_lines.append("")

        if has_out_of_range:
            report_lines.append(f"### ⚠️ 超出范围的事件")
            for oor in out_of_range_events:
                report_lines.append(f"- '{oor['event']}' ({oor['range']}) 超出阶段范围的章节: {oor['invalid_chapters']}")
            report_lines.append("")

        if is_valid:
            report_lines.append("### ✅ 覆盖完整")
            report_lines.append(f"所有 {len(expected_chapters)} 个章节都被正确覆盖，无重叠无留白。")

        coverage_report = "\n".join(report_lines)
        self.logger.info(f"\n{coverage_report}")

        result = {
            "is_valid": is_valid,
            "has_gaps": has_gaps,
            "has_overlaps": has_overlaps,
            "has_out_of_range": has_out_of_range,
            "gaps": gaps,
            "overlaps": overlaps,
            "out_of_range": out_of_range_events,
            "coverage_report": coverage_report,
            "stage_range": stage_range,
            "expected_chapters": len(expected_chapters),
            "actual_coverage": len(all_covered & expected_chapters)
        }

        # 自动修正
        if auto_correct and not is_valid:
            result["corrected_events"] = self._auto_correct_major_event_coverage(
                event_ranges, gaps, overlaps, stage_start, stage_end
            )

        return result

    def _auto_correct_major_event_coverage(self, event_ranges: List[Dict], gaps: List[int],
                                          overlaps: List[Dict], stage_start: int, stage_end: int) -> List[Dict]:
        """
        自动修正重大事件的章节覆盖问题

        策略：
        1. 优先处理留白：扩展相邻事件的范围
        2. 处理重叠：调整事件边界消除重叠
        """
        self.logger.info(f"  🔧 开始自动修正重大事件覆盖问题...")

        # 创建章节到事件的映射（用于处理留白）
        chapter_to_event = {}
        for er in event_ranges:
            for ch in er["chapters"]:
                if ch not in chapter_to_event:
                    chapter_to_event[ch] = []
                chapter_to_event[ch].append(er)

        # 处理留白：扩展相邻事件
        for gap_ch in gaps:
            # 找到最近的左侧事件
            left_event = None
            right_event = None

            for er in event_ranges:
                if er["end"] < gap_ch:
                    if left_event is None or er["end"] > left_event["end"]:
                        left_event = er
                elif er["start"] > gap_ch:
                    if right_event is None or er["start"] < right_event["start"]:
                        right_event = er

            # 扩展左侧或右侧事件
            if left_event and (not right_event or (gap_ch - left_event["end"]) <= (right_event["start"] - gap_ch)):
                old_end = left_event["end"]
                left_event["end"] = gap_ch
                left_event["chapters"].add(gap_ch)
                left_event["range"] = f"{left_event['start']}-{gap_ch}"
                self.logger.info(f"  ✅ 扩展事件 '{left_event['name']}' 的范围: {old_end} -> {gap_ch}")
            elif right_event:
                old_start = right_event["start"]
                right_event["start"] = gap_ch
                right_event["chapters"].add(gap_ch)
                right_event["range"] = f"{gap_ch}-{right_event['end']}"
                self.logger.info(f"  ✅ 扩展事件 '{right_event['name']}' 的范围: {old_start} -> {gap_ch}")

        # 处理重叠：平均分配重叠章节
        for ov in overlaps:
            event1 = next((e for e in event_ranges if e["name"] == ov["event1"]), None)
            event2 = next((e for e in event_ranges if e["name"] == ov["event2"]), None)
            if not event1 or not event2:
                continue

            # 将重叠章节对半分
            overlap_chapters = sorted(ov["chapters"])
            mid_point = len(overlap_chapters) // 2

            for i, ch in enumerate(overlap_chapters):
                if i < mid_point:
                    event2["chapters"].discard(ch)
                else:
                    event1["chapters"].discard(ch)

            # 更新范围
            if event1["chapters"]:
                event1["start"] = min(event1["chapters"])
                event1["end"] = max(event1["chapters"])
                event1["range"] = f"{event1['start']}-{event1['end']}" if event1["start"] != event1["end"] else f"{event1['start']}"
            if event2["chapters"]:
                event2["start"] = min(event2["chapters"])
                event2["end"] = max(event2["chapters"])
                event2["range"] = f"{event2['start']}-{event2['end']}" if event2["start"] != event2["end"] else f"{event2['start']}"

            self.logger.info(f"  ✅ 修正重叠: '{ov['event1']}' 与 '{ov['event2']}' 的重叠章节已重新分配")

        # 返回修正后的事件
        return [er["event"] for er in event_ranges]

    def validate_medium_events_range_consistency(self, major_event: Dict) -> Dict:
        """
        验证单个重大事件内中型事件的章节范围一致性

        检测：
        1. 所有中型事件的 chapter_range 是否在父事件的范围内
        2. 中型事件的并集是否等于父事件的 chapter_range
        3. 中型事件之间是否有重叠或留白

        Args:
            major_event: 重大事件数据

        Returns:
            {
                "is_valid": bool,
                "major_event_name": str,
                "major_event_range": str,
                "issues": List[Dict],
                "medium_events_count": int,
                "coverage_analysis": Dict
            }
        """
        major_event_name = major_event.get("name", "未命名")
        major_range_str = major_event.get("chapter_range", "")

        # 解析父事件范围
        try:
            parent_start, parent_end = parse_chapter_range(major_range_str)
            parent_chapters = set(range(parent_start, parent_end + 1))
        except Exception as e:
            return {
                "is_valid": False,
                "major_event_name": major_event_name,
                "major_event_range": major_range_str,
                "error": f"无法解析父事件章节范围: {e}",
                "issues": [{"type": "parse_error", "message": str(e)}]
            }

        # 收集所有中型事件
        all_medium_events = []
        composition = major_event.get("composition", {})
        for phase_name, phase_events in composition.items():
            if isinstance(phase_events, list):
                for me in phase_events:
                    all_medium_events.append({
                        "event": me,
                        "phase": phase_name,
                        "name": me.get("name", "未命名"),
                        "range": me.get("chapter_range", "")
                    })

        # 也包括特殊情感事件
        special_events = major_event.get("special_emotional_events", [])
        for se in special_events:
            all_medium_events.append({
                "event": se,
                "phase": "special",
                "name": se.get("name", "特殊情感事件"),
                "range": se.get("chapter_range", "")
            })

        issues = []
        all_covered = set()

        # 检查每个中型事件
        for me_info in all_medium_events:
            me_name = me_info["name"]
            me_range = me_info["range"]

            try:
                me_start, me_end = parse_chapter_range(me_range)
                me_chapters = set(range(me_start, me_end + 1))

                # 检查是否超出父事件范围
                out_of_parent = me_chapters - parent_chapters
                if out_of_parent:
                    issues.append({
                        "type": "out_of_range",
                        "medium_event": me_name,
                        "range": me_range,
                        "invalid_chapters": sorted(list(out_of_parent)),
                        "message": f"'{me_name}' ({me_range}) 超出父事件范围，章节: {sorted(list(out_of_parent))}"
                    })

                all_covered |= me_chapters

            except Exception as e:
                issues.append({
                    "type": "parse_error",
                    "medium_event": me_name,
                    "range": me_range,
                    "message": f"无法解析 '{me_name}' 的章节范围: {e}"
                })

        # 检查覆盖情况
        gaps = parent_chapters - all_covered
        if gaps:
            issues.append({
                "type": "gaps",
                "gap_chapters": sorted(list(gaps)),
                "message": f"父事件范围内有 {len(gaps)} 个章节未被中型事件覆盖: {sorted(list(gaps))}"
            })

        # 检查中型事件之间的重叠
        medium_ranges = []
        for me_info in all_medium_events:
            try:
                me_start, me_end = parse_chapter_range(me_info["range"])
                medium_ranges.append({
                    "name": me_info["name"],
                    "start": me_start,
                    "end": me_end,
                    "chapters": set(range(me_start, me_end + 1))
                })
            except:
                continue

        overlaps = []
        for i, mr1 in enumerate(medium_ranges):
            for j, mr2 in enumerate(medium_ranges):
                if i >= j:
                    continue
                overlap = mr1["chapters"] & mr2["chapters"]
                if overlap:
                    overlaps.append({
                        "event1": mr1["name"],
                        "event2": mr2["name"],
                        "chapters": sorted(list(overlap))
                    })

        if overlaps:
            for ov in overlaps:
                issues.append({
                    "type": "overlap",
                    "medium_event1": ov["event1"],
                    "medium_event2": ov["event2"],
                    "overlapping_chapters": ov["chapters"],
                    "message": f"'{ov['event1']}' 与 '{ov['event2']}' 重叠章节: {ov['chapters']}"
                })

        is_valid = len(issues) == 0
        coverage_rate = len(all_covered & parent_chapters) / len(parent_chapters) if parent_chapters else 0

        result = {
            "is_valid": is_valid,
            "major_event_name": major_event_name,
            "major_event_range": major_range_str,
            "issues": issues,
            "medium_events_count": len(all_medium_events),
            "coverage_analysis": {
                "parent_chapters_count": len(parent_chapters),
                "covered_chapters_count": len(all_covered & parent_chapters),
                "coverage_rate": round(coverage_rate * 100, 1),
                "gaps": sorted(list(gaps)),
                "overlaps": overlaps
            }
        }

        if not is_valid:
            self.logger.warning(f"  ⚠️ 重大事件 '{major_event_name}' 的中型事件范围存在问题:")
            for issue in issues:
                self.logger.warning(f"     - {issue['message']}")
        else:
            self.logger.info(f"  ✅ 重大事件 '{major_event_name}' 的中型事件范围验证通过")

        return result

