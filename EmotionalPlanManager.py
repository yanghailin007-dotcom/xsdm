# EmotionalPlanManager.py
import json
import re
from typing import Dict, List, Optional
from utils import parse_chapter_range

class EmotionalPlanManager:
    """情绪计划管理器 - 负责情绪计划生成、情绪指导、情感转折点处理等"""
    
    def __init__(self, stage_plan_manager):
        self.stage_plan_manager = stage_plan_manager
        self.generator = stage_plan_manager.generator

    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, 
                                    global_emotional_plan: Dict) -> Dict:
        """生成阶段详细情绪计划"""
        print(f"  💞 生成{stage_name}的详细情绪计划...")
        
        novel_data = self.generator.novel_data
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        user_prompt = f"""
基于全书情绪规划和阶段特点，制定{stage_name}的详细情绪计划：

**阶段信息**：
- 阶段：{stage_name}
- 章节范围：{stage_range} (共{stage_length}章)
- 全书情绪规划：{json.dumps(global_emotional_plan, ensure_ascii=False)}

**小说信息**：
- 标题：{novel_data["novel_title"]}
- 简介：{novel_data["novel_synopsis"]}
- 主角：{novel_data.get('custom_main_character_name', '主角')}
"""
        
        emotional_plan = self.generator.api_client.generate_content_with_retry(
            "stage_emotional_planning",
            user_prompt,
            purpose=f"生成{stage_name}情绪计划"
        )
        
        if emotional_plan:
            # 存储到阶段写作计划中
            if "stage_writing_plans" not in novel_data:
                novel_data["stage_writing_plans"] = {}
            
            if stage_name not in novel_data["stage_writing_plans"]:
                novel_data["stage_writing_plans"][stage_name] = {}
            
            novel_data["stage_writing_plans"][stage_name]["emotional_plan"] = emotional_plan
            print(f"  ✅ {stage_name}情绪计划生成完成")
            return emotional_plan
        else:
            print(f"  ⚠️ {stage_name}情绪计划生成失败，使用默认计划")
            return self._create_default_stage_emotional_plan(stage_name, stage_range)

    def get_emotional_plan_for_stage(self, stage_name: str) -> Dict:
        """获取阶段的情绪计划 - 修复嵌套结构访问"""
        novel_data = self.generator.novel_data
        stage_plans = novel_data.get("stage_writing_plans", {})
        
        print(f"  🔍 获取阶段 '{stage_name}' 的情绪计划")
        print(f"  🔍 阶段计划键: {list(stage_plans.keys())}")
        
        if stage_name in stage_plans:
            stage_plan = stage_plans[stage_name]
            print(f"  🔍 阶段计划类型: {type(stage_plan)}")
            print(f"  🔍 阶段计划键: {list(stage_plan.keys())}")
            
            # 检查嵌套结构：stage_plan -> stage_writing_plan -> emotional_plan
            if "stage_writing_plan" in stage_plan:
                print(f"  🔍 检测到嵌套结构 stage_writing_plan")
                writing_plan = stage_plan["stage_writing_plan"]
                print(f"  🔍 stage_writing_plan 键: {list(writing_plan.keys())}")
                
                if "emotional_plan" in writing_plan:
                    emotional_plan = writing_plan["emotional_plan"]
                    print(f"  ✅ 成功获取情绪计划，包含键: {list(emotional_plan.keys())}")
                    
                    # 检查情绪分段
                    emotional_breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
                    print(f"  🔍 情绪分段数量: {len(emotional_breakdown)}")
                    for i, breakdown in enumerate(emotional_breakdown):
                        print(f"    {i+1}. {breakdown.get('chapter_range', '未知范围')} -> {breakdown.get('emotional_focus', '未知重点')}")
                    
                    return emotional_plan
                else:
                    print(f"  ⚠️ stage_writing_plan 中没有 emotional_plan")
            else:
                print(f"  ⚠️ 阶段计划中没有 stage_writing_plan")
                
            # 回退：直接检查 emotional_plan
            if "emotional_plan" in stage_plan:
                print(f"  🔄 使用直接的情绪计划")
                return stage_plan["emotional_plan"]
        
        # 如果没有情绪计划，生成一个默认的
        print(f"  ⚠️ 没有找到情绪计划，使用默认计划")
        stage_range = self.stage_plan_manager._get_stage_range(stage_name)
        return self._create_default_stage_emotional_plan(stage_name, stage_range)

    def generate_emotional_guidance_for_chapter(self, chapter_number: int, 
                                            emotional_plan: Dict, stage_name: str) -> Dict:
        """为章节生成详细情绪指导 - 精确匹配版本"""
        print(f"  🎭 开始为第{chapter_number}章生成情绪指导")
        print(f"  🔍 传入的情绪计划类型: {type(emotional_plan)}")
        print(f"  🔍 情绪计划键: {list(emotional_plan.keys()) if emotional_plan else '空'}")
        
        # 获取章节在阶段中的位置
        stage_range = self.stage_plan_manager._get_stage_range(stage_name)
        start_chap, end_chap = parse_chapter_range(stage_range)
        chapter_position = chapter_number - start_chap + 1
        total_chapters_in_stage = end_chap - start_chap + 1
        
        print(f"  📊 阶段信息: {stage_name} ({stage_range}), 章节位置: {chapter_position}/{total_chapters_in_stage}")
        
        # 基于进度确定情绪重点
        emotional_breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
        print(f"  🔍 情绪分段数量: {len(emotional_breakdown)}")
        
        # 初始化明确的未匹配状态
        current_emotional_focus = "未匹配到情绪分段"
        target_intensity = "未知"
        target_reader_emotion = "未知"
        key_scenes_design = "未匹配到情绪分段"
        matched_range = "无"
        
        # 修复：正确解析章节范围
        for i, breakdown in enumerate(emotional_breakdown):
            breakdown_range = breakdown.get("chapter_range", "")
            emotional_focus = breakdown.get("emotional_focus", "")
            print(f"  🔍 检查情绪分段 {i+1}: {breakdown_range} -> {emotional_focus}")
            
            if self._is_chapter_in_emotional_range(chapter_number, breakdown_range):
                current_emotional_focus = emotional_focus
                target_intensity = breakdown.get("intensity_level", "未知")
                target_reader_emotion = breakdown.get("target_reader_emotion", "未知")
                key_scenes_design = breakdown.get("key_scenes_design", "未指定")
                matched_range = breakdown_range
                print(f"  ✅ 匹配情绪分段: {breakdown_range} -> {current_emotional_focus}")
                break
        else:
            print(f"  ❌ 第{chapter_number}章未匹配任何情绪分段")
        
        # 检查是否为情感转折点 - 添加详细调试
        turning_points = emotional_plan.get("emotional_turning_points", [])
        is_turning_point = False
        turning_point_info = {}
        
        print(f"  🔍 检查转折点，共{len(turning_points)}个转折点")
        for i, point in enumerate(turning_points):
            approx_chapter = point.get("approximate_chapter", "")
            emotional_shift = point.get("emotional_shift", "")
            print(f"  🔍 转折点{i+1}: '{approx_chapter}' -> '{emotional_shift}'")
            
            if self._is_chapter_near_turning_point(chapter_number, approx_chapter):
                is_turning_point = True
                turning_point_info = point
                print(f"  ✅ 识别为转折点: {emotional_shift}")
                break
        else:
            print(f"  ⚠️ 第{chapter_number}章不是转折点")
        
        # 检查是否为情感缓冲章节 - 修复解析
        break_planning = emotional_plan.get("emotional_break_planning", {})
        break_chapters = break_planning.get("break_chapters", [])
        is_break_chapter = False
        
        print(f"  🔍 缓冲章节列表: {break_chapters}")
        # 修复：正确解析缓冲章节，处理带括号的格式
        for break_chap in break_chapters:
            if isinstance(break_chap, str):
                print(f"  🔍 解析缓冲章节字符串: '{break_chap}'")
                # 使用正则表达式提取纯数字范围
                numbers = re.findall(r'\d+', break_chap)
                
                if len(numbers) >= 2:
                    # 处理范围格式 "11-12章"
                    try:
                        start_break = int(numbers[0])
                        end_break = int(numbers[1])
                        if start_break <= chapter_number <= end_break:
                            is_break_chapter = True
                            print(f"  ✅ 识别为缓冲章节范围: {start_break}-{end_break}")
                            break
                    except Exception as e:
                        print(f"  ⚠️ 解析缓冲章节范围失败: {break_chap}, 错误: {e}")
                elif len(numbers) == 1:
                    # 处理单个章节格式
                    try:
                        chap_num = int(numbers[0])
                        if chapter_number == chap_num:
                            is_break_chapter = True
                            print(f"  ✅ 识别为缓冲章节: 第{chap_num}章")
                            break
                    except Exception as e:
                        print(f"  ⚠️ 解析缓冲章节失败: {break_chap}, 错误: {e}")
            elif isinstance(break_chap, int) and chapter_number == break_chap:
                is_break_chapter = True
                print(f"  ✅ 识别为缓冲章节: 第{break_chap}章")
                break
        
        result = {
            "current_emotional_focus": current_emotional_focus,
            "target_intensity": target_intensity,
            "target_reader_emotion": target_reader_emotion,
            "key_scenes_design": key_scenes_design,
            "is_emotional_turning_point": is_turning_point,
            "turning_point_info": turning_point_info,
            "is_emotional_break_chapter": is_break_chapter,
            "break_activities": break_planning.get("break_activities", []),
            "emotional_supporting_elements": emotional_plan.get("emotional_supporting_elements", {}),
            "reader_emotional_journey": f"本章读者应该感受到{current_emotional_focus}的情感体验",
            "emotional_strategy": emotional_plan.get("stage_emotional_strategy", {}),
            "matched_emotional_range": matched_range  # 新增：记录匹配的范围
        }
        
        print(f"  🎭 第{chapter_number}章情绪指导生成完成:")
        print(f"    - 匹配范围: {matched_range}")
        print(f"    - 情感重点: {current_emotional_focus}")
        print(f"    - 情感强度: {target_intensity}")
        print(f"    - 目标读者情绪: {target_reader_emotion}")
        print(f"    - 是否转折点: {is_turning_point}")
        print(f"    - 是否缓冲章节: {is_break_chapter}")
        
        return result

    def _create_default_stage_emotional_plan(self, stage_name: str, stage_range: str) -> Dict:
        """创建默认的阶段情绪计划"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 基于阶段名称设置默认情感特征
        stage_emotional_profiles = {
            "opening_stage": {
                "goal": "建立情感连接和读者认同",
                "pace": "逐步加强情感投入",
                "intensity": "低到中"
            },
            "development_stage": {
                "goal": "深化情感冲突和发展关系",
                "pace": "起伏变化，快慢结合", 
                "intensity": "中"
            },
            "climax_stage": {
                "goal": "情感爆发和高潮体验",
                "pace": "紧张加速，高潮集中",
                "intensity": "高"
            },
            "ending_stage": {
                "goal": "情感解决和成长体现",
                "pace": "逐渐放缓，情感升华",
                "intensity": "中到高"
            },
            "final_stage": {
                "goal": "情感圆满和主题共鸣",
                "pace": "平稳深沉，余韵绵长",
                "intensity": "中"
            }
        }
        
        profile = stage_emotional_profiles.get(stage_name, {
            "goal": "情感发展和角色成长",
            "pace": "自然流畅",
            "intensity": "中"
        })
        
        return {
            "stage_emotional_strategy": {
                "overall_emotional_goal": profile["goal"],
                "emotional_pacing_plan": profile["pace"],
                "key_emotional_arcs": ["主角情感成长", "主要关系发展"],
                "emotional_intensity_curve": f"从{profile['intensity']}强度开始，根据情节需要变化"
            },
            "chapter_emotional_breakdown": [
                {
                    "chapter_range": f"{start_chap}-{start_chap + stage_length//3}",
                    "emotional_focus": "建立阶段情感基础",
                    "target_reader_emotion": "投入和期待",
                    "key_scenes_design": "情感建立场景",
                    "intensity_level": "中"
                }
            ],
            "emotional_turning_points": [
                {
                    "approximate_chapter": f"约第{start_chap + stage_length//2}章",
                    "emotional_shift": "情感深化或转折",
                    "preparation_chapters": f"第{start_chap}章开始铺垫",
                    "impact_description": "推动角色情感成长"
                }
            ],
            "emotional_supporting_elements": {
                "settings_for_emotion": ["适合情感表达的关键场景"],
                "symbolic_elements": ["情感象征物"],
                "relationship_developments": ["重要关系进展"]
            },
            "emotional_break_planning": {
                "break_chapters": [f"第{start_chap + stage_length//4}章", f"第{start_chap + stage_length*3//4}章"],
                "break_activities": ["日常互动", "角色反思", "关系建设"],
                "purpose": "给读者情感缓冲和消化空间"
            }
        }

    def _is_chapter_in_emotional_range(self, chapter: int, chapter_range: str) -> bool:
        """检查章节是否在情绪范围段内 - 修复单个章节和范围格式"""
        if not chapter_range:
            return False
        
        try:
            print(f"  🔍 解析情绪范围: '{chapter_range}'")
            
            # 处理 "1章" 这样的单个章节格式
            if "章" in chapter_range and "-" not in chapter_range:
                # 提取单个章节号
                numbers = re.findall(r'\d+', chapter_range)
                if len(numbers) == 1:
                    chap_num = int(numbers[0])
                    result = chapter == chap_num
                    print(f"  🔍 单个章节解析: {chap_num}, 第{chapter}章匹配: {result}")
                    return result
            
            # 处理 "3-4章" 这样的范围格式
            if "-" in chapter_range:
                range_str = chapter_range.replace("章", "").strip()
                numbers = re.findall(r'\d+', range_str)
                
                if len(numbers) >= 2:
                    start_chap = int(numbers[0])
                    end_chap = int(numbers[1])
                    result = start_chap <= chapter <= end_chap
                    print(f"  🔍 范围解析: {start_chap}-{end_chap}, 第{chapter}章在其中: {result}")
                    return result
            
            print(f"  ❌ 无法解析范围: {chapter_range}, 提取的数字: {numbers}")
            return False
            
        except Exception as e:
            print(f"  ❌ 解析情绪章节范围失败: {chapter_range}, 错误: {e}")
            return False

    def _is_chapter_near_turning_point(self, chapter: int, approx_chapter: str) -> bool:
        """检查章节是否接近情感转折点 - 精确解析版本"""
        if not approx_chapter:
            return False
        
        try:
            print(f"  🔍 检查转折点: 当前章节{chapter}, 转折点描述'{approx_chapter}'")
            
            # 使用正则表达式提取所有数字
            numbers = re.findall(r'\d+', approx_chapter)
            print(f"  🔍 从转折点描述中提取的数字: {numbers}")
            
            # 检查是否有匹配的章节号
            for num_str in numbers:
                chap_num = int(num_str)
                if abs(chapter - chap_num) <= 2:  # 前后2章内视为接近
                    print(f"  ✅ 识别为转折点: 当前第{chapter}章接近转折点第{chap_num}章")
                    return True
            
            print(f"  ❌ 未识别为转折点: 当前第{chapter}章与解析的章节{numbers}不匹配")
            return False
            
        except Exception as e:
            print(f"  ⚠️ 解析转折点章节失败: {approx_chapter}, 错误: {e}")
            return False

    def analyze_emotional_arc_consistency(self, stage_name: str, emotional_plan: Dict) -> Dict:
        """分析情绪弧线的一致性"""
        print(f"  📊 分析{stage_name}情绪弧线一致性...")
        
        analysis_result = {
            "stage_name": stage_name,
            "emotional_arc_consistency": "良好",
            "identified_issues": [],
            "recommendations": [],
            "emotional_progression": "流畅"
        }
        
        # 检查情绪转折点的连贯性
        turning_points = emotional_plan.get("emotional_turning_points", [])
        if len(turning_points) < 1:
            analysis_result["identified_issues"].append("缺少明显的情感转折点")
            analysis_result["recommendations"].append("建议在阶段中期添加情感转折")
        
        # 检查情绪分段的覆盖范围
        breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
        if len(breakdown) < 2:
            analysis_result["identified_issues"].append("情绪分段过少")
            analysis_result["recommendations"].append("建议将阶段分为3-4个情绪段落")
        
        # 检查情绪强度变化
        intensity_levels = [b.get("intensity_level", "") for b in breakdown]
        if all(level == intensity_levels[0] for level in intensity_levels):
            analysis_result["identified_issues"].append("情绪强度缺乏变化")
            analysis_result["recommendations"].append("建议设计情绪起伏，增加张力")
        
        # 基于问题数量调整一致性评级
        issue_count = len(analysis_result["identified_issues"])
        if issue_count == 0:
            analysis_result["emotional_arc_consistency"] = "优秀"
        elif issue_count <= 2:
            analysis_result["emotional_arc_consistency"] = "良好"
        elif issue_count <= 4:
            analysis_result["emotional_arc_consistency"] = "一般"
        else:
            analysis_result["emotional_arc_consistency"] = "需要改进"
        
        print(f"  ✅ {stage_name}情绪弧线分析完成: {analysis_result['emotional_arc_consistency']}")
        return analysis_result

    def generate_emotional_intensity_curve(self, stage_name: str, stage_range: str, emotional_plan: Dict) -> Dict:
        """生成情绪强度曲线"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 基于情绪分段生成强度曲线
        breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
        intensity_curve = []
        
        for segment in breakdown:
            segment_range = segment.get("chapter_range", "")
            intensity = segment.get("intensity_level", "中")
            emotional_focus = segment.get("emotional_focus", "")
            
            # 解析章节范围
            numbers = re.findall(r'\d+', segment_range)
            if len(numbers) >= 2:
                seg_start = int(numbers[0])
                seg_end = int(numbers[1])
                
                # 将强度转换为数值
                intensity_value = self._convert_intensity_to_value(intensity)
                
                intensity_curve.append({
                    "chapter_range": f"{seg_start}-{seg_end}",
                    "intensity_level": intensity,
                    "intensity_value": intensity_value,
                    "emotional_focus": emotional_focus,
                    "segment_length": seg_end - seg_start + 1
                })
        
        # 如果没有分段，创建默认曲线
        if not intensity_curve:
            intensity_curve = [
                {
                    "chapter_range": f"{start_chap}-{start_chap + stage_length//3}",
                    "intensity_level": "低到中",
                    "intensity_value": 3,
                    "emotional_focus": "建立情感基础",
                    "segment_length": stage_length // 3
                },
                {
                    "chapter_range": f"{start_chap + stage_length//3 + 1}-{start_chap + stage_length*2//3}",
                    "intensity_level": "中到高", 
                    "intensity_value": 6,
                    "emotional_focus": "情感发展和冲突",
                    "segment_length": stage_length // 3
                },
                {
                    "chapter_range": f"{start_chap + stage_length*2//3 + 1}-{end_chap}",
                    "intensity_level": "高到中",
                    "intensity_value": 4,
                    "emotional_focus": "情感解决和升华",
                    "segment_length": stage_length - (stage_length * 2 // 3)
                }
            ]
        
        curve_analysis = {
            "stage_name": stage_name,
            "stage_range": stage_range,
            "total_segments": len(intensity_curve),
            "average_intensity": sum(seg["intensity_value"] for seg in intensity_curve) / len(intensity_curve),
            "max_intensity": max(seg["intensity_value"] for seg in intensity_curve),
            "min_intensity": min(seg["intensity_value"] for seg in intensity_curve),
            "intensity_curve": intensity_curve,
            "curve_quality": self._assess_curve_quality(intensity_curve)
        }
        
        print(f"  📈 {stage_name}情绪强度曲线生成完成: {curve_analysis['curve_quality']}")
        return curve_analysis

    def _convert_intensity_to_value(self, intensity: str) -> int:
        """将情绪强度描述转换为数值"""
        intensity_mapping = {
            "极低": 1,
            "很低": 2, 
            "低": 3,
            "低到中": 4,
            "中": 5,
            "中到高": 6,
            "高": 7,
            "很高": 8,
            "极高": 9,
            "未知": 5
        }
        return intensity_mapping.get(intensity, 5)

    def _assess_curve_quality(self, intensity_curve: List[Dict]) -> str:
        """评估情绪曲线质量"""
        if len(intensity_curve) < 2:
            return "单调"
        
        intensities = [seg["intensity_value"] for seg in intensity_curve]
        
        # 检查是否有明显的变化
        max_diff = max(intensities) - min(intensities)
        if max_diff < 2:
            return "平缓"
        elif max_diff < 4:
            return "适中"
        elif max_diff < 6:
            return "起伏明显"
        else:
            return "戏剧性强"

    def validate_emotional_plan_integrity(self, emotional_plan: Dict, stage_name: str) -> Dict:
        """验证情绪计划的完整性"""
        print(f"  🔍 验证{stage_name}情绪计划完整性...")
        
        validation_result = {
            "stage_name": stage_name,
            "is_complete": True,
            "missing_elements": [],
            "strengths": [],
            "improvement_suggestions": []
        }
        
        required_elements = [
            "stage_emotional_strategy",
            "chapter_emotional_breakdown", 
            "emotional_turning_points",
            "emotional_supporting_elements"
        ]
        
        # 检查必需元素
        for element in required_elements:
            if element not in emotional_plan:
                validation_result["missing_elements"].append(element)
                validation_result["is_complete"] = False
        
        # 检查情绪分段
        breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
        if len(breakdown) < 2:
            validation_result["improvement_suggestions"].append("建议增加情绪分段以提供更详细的指导")
        
        # 检查转折点
        turning_points = emotional_plan.get("emotional_turning_points", [])
        if len(turning_points) == 0:
            validation_result["improvement_suggestions"].append("建议添加情感转折点以增强戏剧性")
        
        # 识别优势
        if len(breakdown) >= 3:
            validation_result["strengths"].append("情绪分段详细")
        if len(turning_points) >= 2:
            validation_result["strengths"].append("情感转折丰富")
        if emotional_plan.get("emotional_break_planning"):
            validation_result["strengths"].append("考虑了情感缓冲")
        
        print(f"  ✅ {stage_name}情绪计划完整性验证: {'通过' if validation_result['is_complete'] else '未通过'}")
        return validation_result