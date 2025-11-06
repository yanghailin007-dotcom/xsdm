import re
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import WorldStateManager

class QualityAssessor:
    def __init__(self, api_client, storage_path: str = "./quality_data"):
        self.api_client = api_client
        self.storage_path = storage_path
        
        # 初始化世界状态管理器
        self.world_state_manager = WorldStateManager.WorldStateManager(storage_path)
        
        self.unified_quality_standards = {
            # === 质量等级标准 ===
            "quality_grades": {
                "perfect": 10.0,      # 完美 - 无需优化
                "excellent": 9.8,     # 优秀 - 轻微优化
                "good": 9.5,          # 良好 - 建议优化
                "acceptable": 9.0,    # 合格 - 必须优化
                "needs_rewrite": 8.5  # 需要重写
            },
            
            # === 优化决策阈值 ===
            "optimization_thresholds": {
                # 章节内容相对宽松（考虑创作难度）
                "chapter_content": 9.0,
                # 其他内容要求更高标准
                "market_analysis": 9.0,
                "writing_plan": 9.0,
                "core_worldview": 9.0,
                "character_design": 9.0,
                "creative_seed": 9.0,
                "novel_plan": 9.0
            },
            
            # === 番茄新鲜度评分 ===
            "freshness_standards": {
                "excellent": 6.5,     # 有一定创新性，同时保留经典元素
                "good": 5.0,          # 适当融合套路和创新
                "average": 4.0,       # 常见套路但执行良好
                "cliche": 3.0         # 过度老套重复
            },
            
            # === 黄金三章特殊标准 ===
            "golden_chapters": {
                1: {"min_quality": 9.2, "min_freshness": 9.0},
                2: {"min_quality": 9.1, "min_freshness": 8.8},
                3: {"min_quality": 9.0, "min_freshness": 8.5}
            }
        }
        
        # 新鲜度评估标准
        self.freshness_evaluation_criteria = {
            "concept_originality": {
                "weight": 0.3,
                "description": "核心概念的新颖程度",
                "evaluation_points": [
                    "是否使用了过度常见的套路模板",
                    "世界观设定是否有创新点", 
                    "主角设定是否独特",
                    "金手指/系统设计是否有新意"
                ]
            },
            "execution_uniqueness": {
                "weight": 0.25,
                "description": "执行方式的独特性",
                "evaluation_points": [
                    "情节展开方式是否新颖",
                    "角色互动模式是否有特色",
                    "冲突设计是否避免俗套",
                    "情感表达方式是否独特"
                ]
            },
            "market_differentiation": {
                "weight": 0.25,
                "description": "与市场上同类作品的区分度", 
                "evaluation_points": [
                    "与热门作品的相似度",
                    "是否有明显的差异化优势",
                    "目标读者群体是否明确",
                    "市场定位是否清晰"
                ]
            },
            "creative_risk": {
                "weight": 0.2,
                "description": "创意冒险程度",
                "evaluation_points": [
                    "是否敢于尝试新元素",
                    "是否打破常规设定",
                    "创新与传统的平衡", 
                    "读者接受度预估"
                ]
            }
        }

    def assess_freshness(self, content: Dict, content_type: str) -> Dict:
        """评估内容的新鲜度 - 直接使用新结构"""
        try:
            freshness_prompt = self._generate_freshness_assessment_prompt(content, content_type)
            
            result = self.api_client.generate_content_with_retry(
                "freshness_assessment",
                freshness_prompt,
                purpose=f"{content_type}新鲜度评估"
            )
            
            # 直接验证新结构
            if not result or "score" not in result:
                return self._get_default_freshness_assessment()
            
            # 确保新结构的所有必需字段都存在
            return self._validate_freshness_result(result)
            
        except Exception as e:
            print(f"  ❌ 新鲜度评估失败: {e}")
            return self._get_default_freshness_assessment()

    def _validate_freshness_result(self, result: Dict) -> Dict:
        """验证新鲜度评估结果的新结构"""
        # 确保所有必需的字段都存在
        required_structure = {
            "score": {
                "total": 0,
                "core_concept_novelty": 0,
                "system_innovation": 0,
                "market_scarcity": 0
            },
            "analysis": {
                "core_concept_novelty": "",
                "system_innovation": "", 
                "market_scarcity": ""
            },
            "verdict": "中规中矩",
            "suggestions": []
        }
        
        # 确保顶层字段存在
        for key, default_value in required_structure.items():
            if key not in result:
                result[key] = default_value
            elif isinstance(default_value, dict):
                # 确保嵌套字典字段存在
                for sub_key, sub_default in default_value.items():
                    if sub_key not in result[key]:
                        result[key][sub_key] = sub_default
        
        return result

    def _get_default_freshness_assessment(self) -> Dict:
        """获取默认的新鲜度评估结果 - 新结构"""
        return {
            "score": {
                "total": 6.0,
                "core_concept_novelty": 6.0,
                "system_innovation": 6.0,
                "market_scarcity": 6.0
            },
            "analysis": {
                "core_concept_novelty": "评估异常",
                "system_innovation": "评估异常",
                "market_scarcity": "评估异常"
            },
            "verdict": "评估异常",
            "suggestions": ["重新评估内容新鲜度", "增加创新元素", "避免常见套路"]
        }

    def _generate_freshness_assessment_prompt(self, content: Dict, content_type: str) -> str:
        """生成新鲜度评估提示词 - 使用完整方案"""
        
        import json
        # 将完整方案转换为JSON字符串
        content_json = json.dumps(content, ensure_ascii=False, indent=2)
        
        return f"""
    你是一位顶级的网络小说市场分析师，精通数据分析，对起点、番茄、飞卢等主流平台的流行趋势、读者偏好和内容稀缺性了如指掌。

    ## 核心任务
    你的核心任务是基于用户提供的完整小说创作方案，从市场角度进行严格、客观、数据驱动的新鲜度评估，并提供可行的改进建议，帮助创意脱颖而出。

    ## 完整方案内容
    {content_json}

        """

    def should_optimize_comprehensive(self, assessment: Dict, content_type: str, 
                                    chapter_number: int = None) -> Tuple[bool, str]:
        """综合优化决策 - 使用新的新鲜度评分结构"""
        quality_score = assessment.get("overall_score", 0)
        
        # 从新结构中获取新鲜度分数
        freshness_data = assessment.get("freshness_assessment", {})
        if "score" in freshness_data:
            freshness_score = freshness_data["score"]["total"]
        else:
            freshness_score = assessment.get("freshness_score", 10.0)  # 向后兼容
        
        standards = self.unified_quality_standards
        
        # 章节内容和非章节内容使用不同的标准
        if content_type == "chapter_content":
            # 章节内容只检查质量
            quality_threshold = standards["optimization_thresholds"]["chapter_content"]
            
            # 黄金三章特殊检查
            if chapter_number in [1, 2, 3]:
                golden_standard = standards["golden_chapters"][chapter_number]
                if quality_score < golden_standard["min_quality"]:
                    return True, f"黄金第{chapter_number}章质量分{quality_score:.1f}低于{golden_standard['min_quality']}"
            
            # 常规质量检查
            if quality_score < quality_threshold:
                return True, f"质量分{quality_score:.1f}低于阈值{quality_threshold}"
            
            return False, f"质量{quality_score:.1f}达标"
        
        else:
            # 非章节内容检查质量和新鲜度
            quality_threshold = standards["optimization_thresholds"].get(content_type, 9.8)
            freshness_threshold = standards["freshness_standards"]["good"]
            
            # 质量检查
            if quality_score < quality_threshold:
                return True, f"质量分{quality_score:.1f}低于阈值{quality_threshold}"
            
            # 新鲜度检查（使用新结构的分数）
            if freshness_score < freshness_threshold:
                return True, f"新鲜度{freshness_score:.1f}低于阈值{freshness_threshold}"
            
            return False, f"质量{quality_score:.1f}和新鲜度{freshness_score:.1f}均达标"

    def assess_chapter_quality(self, assessment_params: Dict) -> Optional[Dict]:
        """评估章节质量（包含一致性检查）- 增强黄金三章评估"""
        user_prompt = self._generate_chapter_assessment_prompt(assessment_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_quality_assessment", 
            user_prompt, 
            temperature=0.3, 
            purpose=f"第{assessment_params.get('chapter_number', 1)}章节质量评估"
        )
        
        # 如果评估成功，处理黄金三章的特殊逻辑
        if result and 'overall_score' in result:
            # ⭐️ 新增：从 assessment_params 获取变量
            novel_title = assessment_params.get('novel_title', 'unknown')
            chapter_number = assessment_params.get('chapter_number', 0)
            protagonist_name = assessment_params.get('protagonist_name', '主角')
            
            # ⭐️ 新增：处理主角心境变化
            if 'protagonist_mindset_changes' in result:
                mindset_changes = result['protagonist_mindset_changes']
                if isinstance(mindset_changes, dict) and mindset_changes:
                    self.world_state_manager.manage_character_mindset(
                        novel_title,         # 使用修复后的变量
                        protagonist_name,
                        mindset_changes,
                        chapter_number       # 使用修复后的变量
                    )
                    
            if "emotional_delivery_assessment" not in result:
                result["emotional_delivery_assessment"] = {
                    "achieved_score": 7.0, # 默认分
                    "intensity_score": 7.0,
                    "transition_quality": "良好",
                    "analysis": "AI未能返回情绪评估结果。",
                    "suggestions": ["请检查章节是否有效传达了目标情绪。"]
                } 
                # (可选) 根据情绪分调整总分
                emotional_score = result["emotional_delivery_assessment"].get("achieved_score", 7.0)
                if emotional_score < 6.0:
                    print(f"⚠️ 情绪传达不力，评分从 {result['overall_score']} 微调。")
                    result['overall_score'] = max(0, result['overall_score'] - 0.5)

            chapter_number = assessment_params.get('chapter_number', 0)
            novel_title = assessment_params.get('novel_title', 'unknown')
            
            # 如果是黄金三章，应用更严格的标准
            if 1 <= chapter_number <= 3:
                result = self._apply_golden_chapters_standards(result, chapter_number)
            
            # 1. 首先处理角色状态变化
            character_status_changes = result.get('character_status_changes', [])
            for status_change in character_status_changes:
                character_name = status_change.get('character_name')
                status = status_change.get('status')
                if character_name and status in ['dead', 'exited']:
                    print(f"🔄 AI检测到角色状态变化: {character_name} -> {status}")
                    self.world_state_manager._simplify_character_status(novel_title, character_name, status, chapter_number)
            
            # 2. 处理世界状态增量更新
            if 'world_state_changes' in result:
                print("🧹 清洗世界状态变化数据...")
                print(f"   原始数据类型: {type(result['world_state_changes'])}")
                
                # 调试：打印原始数据结构
                for category, elements in result['world_state_changes'].items():
                    print(f"   {category}: {type(elements)} - {len(elements) if hasattr(elements, '__len__') else 'N/A'}")
                cleaned_changes = self.world_state_manager._validate_and_clean_world_state_changes(
                    result['world_state_changes'], 
                    chapter_number
                )
                if 'characters' in cleaned_changes:
                    for char_name, char_data in cleaned_changes['characters'].items():
                        if 'attributes' in char_data and 'money' in char_data['attributes']:
                            money_value = char_data['attributes']['money']
                            if money_value is not None:
                                try:
                                    # 确保金钱值是数值类型
                                    char_data['attributes']['money'] = float(money_value)
                                except (TypeError, ValueError):
                                    # 如果转换失败，设置为0并记录警告
                                    print(f"⚠️ 角色 {char_name} 的金钱值无效: {money_value}，已重置为0")
                                    char_data['attributes']['money'] = 0

                money_issues = self.world_state_manager.validate_money_consistency(
                    novel_title, 
                    chapter_number,
                    cleaned_changes  # 使用清洗后的数据
                )
                
                # 如果有金钱一致性问题，大幅降低评分
                if money_issues:
                    original_score = result.get('overall_score', 0)
                    # 根据问题严重程度降低评分
                    severe_issues = [issue for issue in money_issues if issue.get('severity') == '高']
                    moderate_issues = [issue for issue in money_issues if issue.get('severity') == '中']
                    
                    penalty = len(severe_issues) * 2.0 + len(moderate_issues) * 1.0
                    new_score = max(0, original_score - penalty)
                    
                    result['overall_score'] = new_score
                    result['quality_verdict'] = self.get_quality_verdict(new_score)
                    
                    # 记录扣分原因
                    result['money_consistency_penalty'] = {
                        'original_score': original_score,
                        'penalty': penalty,
                        'new_score': new_score,
                        'issues': money_issues
                    }
                    
                    print(f"💰 金钱一致性检查: 发现{len(money_issues)}个问题，评分从{original_score}降至{new_score}")

                if cleaned_changes:
                    self.world_state_manager._update_world_state_incrementally(novel_title, cleaned_changes, chapter_number)
                    result['updated_world_state'] = self.world_state_manager.current_world_state
                    result['world_state_changes'] = cleaned_changes
                    
                    # === 修复：从世界状态变化中提取角色信息，更新角色发展表 ===
                    self._update_character_development_from_world_state(novel_title, cleaned_changes, chapter_number)
                else:
                    print("⚠️ 世界状态变化数据清洗后为空")
            
            # 3. 保存评估数据
            self.world_state_manager.save_assessment_data(novel_title, chapter_number, result)
            
            # 4. 从评估结果更新角色发展表（原有的逻辑）
            self.world_state_manager.update_character_development_from_assessment(novel_title, result, chapter_number)
        return result

    def _update_character_development_from_world_state(self, novel_title: str, world_state_changes: Dict, chapter_number: int):
        """从世界状态变化中更新角色发展表"""
        characters_changes = world_state_changes.get('characters', {})
        
        for character_name, character_data in characters_changes.items():
            # 构建角色发展数据
            development_data = {
                "name": character_name,
                "role_type": character_data.get("attributes", {}).get("role_type", "次要配角"),
                "status": character_data.get("attributes", {}).get("status", "active")
            }
            
            # 添加修为信息
            attributes = character_data.get("attributes", {})
            cultivation_level = attributes.get("cultivation_level")
            cultivation_system = attributes.get("cultivation_system")
            
            if cultivation_level or cultivation_system:
                if "cultivation_info" not in development_data:
                    development_data["cultivation_info"] = {}
                if cultivation_level:
                    development_data["cultivation_info"]["level"] = cultivation_level
                if cultivation_system:
                    development_data["cultivation_info"]["system"] = cultivation_system
            
            # 更新角色发展表
            print(f"🔄 从世界状态更新角色发展表: {character_name}")
            self.world_state_manager.manage_character_development_table(
                novel_title, 
                development_data, 
                chapter_number, 
                "update"
            )

    def _apply_golden_chapters_standards(self, assessment_result: Dict, chapter_number: int) -> Dict:
        """对黄金三章应用更严格的、以留存为导向的诊断标准"""
        
        # 黄金三章的特殊诊断和评分维度
        golden_chapters_criteria = {
            1: {
                "name": "开篇之章：生死钩",
                "focus_points": { # 评估重点和权重
                    "opening_hook": {"weight": 0.3, "desc": "开篇吸引力与即时冲突"},
                    "protagonist_intro_in_conflict": {"weight": 0.25, "desc": "主角在困境中的登场"},
                    "core_conflict_setup": {"weight": 0.25, "desc": "核心悬念和主要矛盾的建立"},
                    "pacing": {"weight": 0.2, "desc": "叙事节奏是否紧凑无冗余"}
                },
                "minimum_acceptable": 8.8, # 提高合格门槛
                "failure_focus": "未能立即抓住读者，冲突建立过慢，缺乏吸引力。"
            },
            2: {
                "name": "承接之章：冲突升级",
                "focus_points": {
                    "conflict_development": {"weight": 0.3, "desc": "第一章冲突的有效延续和升级"},
                    "plot_progression": {"weight": 0.3, "desc": "主线情节是否有实质性推进"},
                    "suspense_building": {"weight": 0.25, "desc": "悬念的强化和新悬念的引入"},
                    "character_deepening": {"weight": 0.15, "desc": "通过行动深化主角形象"}
                },
                "minimum_acceptable": 8.6,
                "failure_focus": "情节推进乏力，未能有效承接和发展首章冲突。"
            },
            3: {
                "name": "爆发之章：强力钩子",
                "focus_points": {
                    "initial_climax": {"weight": 0.35, "desc": "开篇小高潮的营造和爆发力"},
                    "strong_ending_hook": {"weight": 0.35, "desc": "结尾是否设置了无法抗拒的追读钩子"},
                    "reader_payoff": {"weight": 0.2, "desc": "是否对前两章的铺垫给予了初步回报"},
                    "series_foreshadowing": {"weight": 0.1, "desc": "对后续长线发展的伏笔"}
                },
                "minimum_acceptable": 8.5,
                "failure_focus": "缺乏高潮和强力钩子，读者追读欲望不足。"
            }
        }
        
        chapter_spec = golden_chapters_criteria.get(chapter_number)
        if not chapter_spec:
            return assessment_result
        
        original_score = assessment_result.get("overall_score", 0)
        detailed_scores = assessment_result.get("detailed_scores", {})
        
        # 将现有评估分数映射到黄金三章的关注点 (这是一个近似映射)
        score_mapping = {
            "opening_hook": detailed_scores.get("chapter_connection", original_score),
            "protagonist_intro_in_conflict": detailed_scores.get("character_consistency", original_score),
            "core_conflict_setup": detailed_scores.get("plot_coherence", original_score),
            "pacing": detailed_scores.get("writing_quality", original_score),
            "conflict_development": detailed_scores.get("plot_coherence", original_score),
            "plot_progression": detailed_scores.get("plot_coherence", original_score),
            "suspense_building": detailed_scores.get("next_chapter_hook_score", detailed_scores.get("emotional_impact", original_score)),
            "character_deepening": detailed_scores.get("character_consistency", original_score),
            "initial_climax": detailed_scores.get("emotional_impact", original_score),
            "strong_ending_hook": detailed_scores.get("next_chapter_hook_score", detailed_scores.get("emotional_impact", original_score)),
            "reader_payoff": detailed_scores.get("emotional_impact", original_score),
            "series_foreshadowing": detailed_scores.get("plot_coherence", original_score),
        }
        
        focus_scores = {}
        weighted_score = 0
        total_weight = sum(spec["weight"] for spec in chapter_spec["focus_points"].values())

        for key, spec in chapter_spec["focus_points"].items():
            score = score_mapping.get(key, original_score)
            weighted_score += score * spec["weight"]
            focus_scores[key] = round(score, 1)

        final_golden_score = (weighted_score / total_weight) if total_weight > 0 else original_score

        # 惩罚机制：如果任何一项低于8.0，总分再额外扣分
        low_points = [k for k, v in focus_scores.items() if v < 8.0]
        if low_points:
            penalty = len(low_points) * 0.5
            final_golden_score = max(0, final_golden_score - penalty)
            
        assessment_result["overall_score"] = round(final_golden_score, 2)
        assessment_result['quality_verdict'] = self.get_quality_verdict(final_golden_score)[0]
        
        is_acceptable = final_golden_score >= chapter_spec["minimum_acceptable"]
        
        assessment_result["golden_chapters_assessment"] = {
            "chapter_number": chapter_number,
            "assessment_name": chapter_spec["name"],
            "is_acceptable": is_acceptable,
            "golden_score": round(final_golden_score, 2),
            "minimum_required_score": chapter_spec["minimum_acceptable"],
            "focus_point_scores": focus_scores,
            "improvement_suggestions": self._generate_golden_chapters_suggestions(
                chapter_number, focus_scores, is_acceptable
            )
        }
        
        if not is_acceptable:
            weaknesses = assessment_result.get("weaknesses", [])
            if not any("黄金章节不合格" in w for w in weaknesses):
                 weaknesses.insert(0, f"【黄金章节不合格】: {chapter_spec['failure_focus']}")
            assessment_result["weaknesses"] = weaknesses

        return assessment_result

    def _get_golden_chapters_quality_tier(self, score: float) -> str:
        """获取黄金三章质量等级"""
        if score >= 9.2:
            return "S级 - 完美开篇"
        elif score >= 8.8:
            return "A级 - 优秀开篇" 
        elif score >= 8.5:
            return "B级 - 合格开篇"
        else:
            return "C级 - 需要重写"

    def _generate_golden_chapters_suggestions(self, chapter_number: int, focus_scores: Dict, is_acceptable: bool) -> List[str]:
        """根据黄金三章的诊断结果生成具体的、可操作的改进建议"""
        if is_acceptable:
            return ["整体表现符合黄金章节要求，可微调以追求极致。"]

        suggestions = []
        # 按分数从低到高排序，优先解决最严重的问题
        sorted_issues = sorted(focus_scores.items(), key=lambda item: item[1])

        suggestion_map = {
            1: {
                "opening_hook": "重写开篇500字，必须以一个意外事件、一个尖锐问题或一个危险处境开局，立即将读者拖入情节。",
                "protagonist_intro_in_conflict": "修改主角登场方式，不要平淡介绍，让他在一个正在发生的冲突或危机中首次亮相。",
                "core_conflict_setup": "明确并前置核心矛盾。在第一章结尾，读者必须清楚主角面临的巨大威胁或渴望达成的迫切目标。",
                "pacing": "删减所有非必要的环境描写和心理活动，用动作和对话推动情节，确保节奏极快。"
            },
            2: {
                "conflict_development": "检查与第一章的衔接，确保冲突是直接升级而非转向。加大压力，提高赌注。",
                "plot_progression": "确保本章有至少一个推动主线的关键进展（如获得线索、遭遇关键敌人、做出关键决定）。",
                "suspense_building": "在情节中加入新的谜团或威胁，并在结尾强化悬念，让读者对下一章的走向产生强烈好奇。",
                "character_deepening": "通过主角在压力下的选择和行动来展现其性格，而不是通过内心独白。"
            },
            3: {
                "initial_climax": "设计一个情节点，让开篇以来的矛盾在这里有一个小规模的爆发，给予读者初步的情绪释放。",
                "strong_ending_hook": "重写结尾。必须是一个强力的反转、一个生死攸关的抉择、或是一个揭示惊人秘密的场景。",
                "reader_payoff": "确保本章解决了前两章制造的某个小悬念，给予读者“原来如此”的满足感，同时引出更大悬念。",
                "series_foreshadowing": "在情节的细微处（如一句对话、一个物品）植入与全书主线相关的长线伏笔。"
            }
        }
        
        for key, score in sorted_issues:
            if score < 8.5: # 只为分数低的项生成建议
                if chapter_number in suggestion_map and key in suggestion_map[chapter_number]:
                    suggestions.append(suggestion_map[chapter_number][key])

        if not suggestions:
            suggestions.append("整体分数偏低，请全面检查节奏、冲突和钩子，确保每一段都在推动情节发展。")
            
        return suggestions[:3] # 返回最重要的3条建议

    def detect_ai_artifacts(self, content: str) -> List[str]:
        """检测AI痕迹"""
        artifacts = []
        
        marker_patterns = [
            r'\*\*.*?：\*\*',
            r'【.*?】',
            r'第一[点、]|第二[点、]|第三[点、]',
            r'首先，|其次，|然后，|最后，',
            r'总的来说，|综上所述，|总而言之，',
            r'伏笔植入|铺垫手法|情节设计|结构安排',
            r'人物塑造|角色刻画|性格描写|形象建立',
            r'主题表达|思想内涵|深层意义|价值取向',
            r'情感渲染|气氛营造|情绪铺垫|感染力',
            r'叙事视角|叙述方式|描写手法|表现技巧',
            r'节奏控制|张弛有度|高潮部分|结局处理',
            r'象征意义|隐喻手法|对比运用|反复强调',
            r'在此基础上，|进一步来说，|值得注意的是，',
            r'从另一个角度|换而言之|具体而言',
            r'需要指出的是|值得关注的是|不容忽视的是',
            r'^[\d一二三四五六七八九十]、',
            r'^[•\-*]\s',
            r'^[A-Za-z]\.',
            r'使故事更加|让情节更|增强了作品的',
            r'提升了文章的|丰富了内容的|深化了主题的',
            r'达到了.*效果|产生了.*影响|具有.*价值',
            r'人物关系方面，|角色互动上，|彼此之间',
            r'父子关系|母女关系|夫妻关系|朋友关系',
            r'矛盾冲突|情感纠葛|关系发展|互动模式',
            r'开头部分|中间段落|结尾处|整体结构',
            r'起承转合|前后呼应|层层递进|环环相扣',
            r'艺术特色|文学价值|创作特点|风格特征',
            r'语言优美|文字精炼|表达生动|描写细腻'
        ]
        
        for pattern in marker_patterns:
            matches = re.findall(pattern, content)
            if matches:
                artifacts.append(f"模式化标记: {matches[:3]}")
        
        sentences = re.split(r'[。！？]', content)
        
        for sentence in sentences:
            if len(sentence) > 10:
                if "一边" in sentence and sentence.count("一边") > 1:
                    artifacts.append("重复句式: 一边...一边...")
                if "不仅" in sentence and "而且" in sentence:
                    artifacts.append("重复句式: 不仅...而且...")
        
        overused_words = ["显然", "无疑", "实际上", "事实上", "可以说", "值得注意的是"]
        for word in overused_words:
            count = content.count(word)
            if count > 3:
                artifacts.append(f"过度使用词汇: '{word}'出现{count}次")
        
        return artifacts[:10]

    def _generate_chapter_assessment_prompt(self, params: Dict) -> str:
        """生成章节质量评估提示词（包含内部生成的强一致性检查清单）"""
        
        novel_title = params.get('novel_title', 'unknown')
        
        # 1. 加载之前的世界状态
        previous_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        world_state_str = json.dumps(previous_world_state, ensure_ascii=False, indent=2) if previous_world_state else "{}"

        # 2. 【核心修改】基于世界状态，在本函数内部构建一致性检查清单
        consistency_check_section = self._build_consistency_check_prompt_section(previous_world_state)
        
        character_development_data = self._load_character_development_data(novel_title)
        character_development_str = json.dumps(character_development_data, ensure_ascii=False, indent=2) if character_development_data else "{}"        

        # 新增：从 params 获取情绪指导
        emotional_guidance = params.get('emotional_guidance', {})
        target_emotion = emotional_guidance.get('target_emotion_keyword', '无')
        emotional_task = emotional_guidance.get('core_emotional_task', '无')

        # 新增：构建情绪评估部分
        emotional_assessment_section = f"""
    ### 任务三：情绪传达评估 (必须在质量评估后进行！)
    本章的核心情绪目标是传达 **【{target_emotion}】**。
    - **核心任务描述**: {emotional_task}
    请评估        
    """
        protagonist_name = params.get('protagonist_name', '主角') # 假设我们可以获取主角名
        # ⭐️ 新增：获取主角当前心境
        current_mindset = self.world_state_manager.get_current_mindset(novel_title, protagonist_name)
        current_mindset_str = json.dumps(current_mindset, ensure_ascii=False, indent=2)

        # ⭐️ 新增：构建心境演变分析部分
        mindset_evolution_section = f"""
### 任务四：主角心境演变分析 (针对主角：{protagonist_name})
基于本章发生的核心事件，分析对主角心境的冲击和改变。

#### 主角当前心境状态 (参考):
{current_mindset_str}

#### 分析要求:
1.  **识别触发事件 (Triggering Event)**: 本章中哪个事件对主角的内心冲击最大？
2.  **分析变化过程 (Change Analysis)**: 这个事件如何挑战或印证了他的核心信念、欲望或恐惧？
3.  **定义新状态 (New State)**: 基于以上分析，主角的信念、欲望、恐惧或内在矛盾是否发生了 subtle (微妙的) 或 significant (显著的) 的变化？
4.  **返回结构化数据**: 在返回JSON的 "protagonist_mindset_changes" 字段中报告你的分析。
"""
        # 3. 将一致性检查清单注入到最终的Prompt中
        return f"""
内容：
你是一位资深的番茄小说内容分析师与世界观架构师。
你的任务分为三步：一致性审查、全面质量评估、情绪传达评估。

{consistency_check_section}

### 任务一：一致性审查 (必须最先执行！)
请严格对照以上【一致性铁律】，检查【章节内容预览】是否存在矛盾，特别是：
1.  **死者复活**: 【绝对禁止】名单中的角色是否出现？
2.  **状态矛盾**: 角色的位置、修为、金钱状况是否与快照冲突？
3.  **物品错乱**: 已消耗的物品是否被再次使用？物品是否出现在了错误的拥有者手中？
4.  **技能突变**: 角色的技能等级是否发生不合理的跳跃？
5.  **关系重置**: 已经认识的角色是否在重新自我介绍？
请在返回JSON的 "consistency_issues" 字段中报告所有违规行为。

### 任务二：质量评估与状态提取
完成审查后，再对章节进行整体质量评估，并提取世界观变化。

{emotional_assessment_section} # <--- 新增的情绪评估任务

---
### 评估所需信息

#### 1. 小说与章节信息
- **小说标题**: {params.get('novel_title', '未知')}
- **章节标题**: {params.get('chapter_title', '未知')}
- **章节编号**: {params.get('chapter_number', '未知')}
- **前情提要**: {params.get('previous_summary', '无')}

#### 2. 当前章节的世界状态 (完整版，供参考)
{world_state_str}

#### 3. 现有角色发展数据:
{character_development_str}

#### 4. 本章内容预览:
{params.get('chapter_content', '')}
---

请严格按照我在System Prompt中定义的JSON格式返回包含评估和世界观变化的完整结果。
"""

    def optimize_chapter_content(self, optimization_params: Dict) -> Optional[Dict]:
        """优化章节内容 - 返回标准章节格式"""
        try:
            user_prompt = self._generate_optimization_prompt(optimization_params)
            result = self.api_client.generate_content_with_retry(
                "chapter_optimization", 
                user_prompt, 
                purpose="章节内容优化",
            )
            
            # 验证优化结果并转换为标准章节格式
            if result and isinstance(result, dict) and result.get("optimized_content"):
                print(f"  ✅ 章节优化成功，生成内容长度: {len(result.get('optimized_content', ''))}")
                
                # 构建标准章节格式的返回数据
                standard_chapter_data = {
                    "content": result.get("optimized_content"),
                    "word_count": result.get("word_count", len(result.get("optimized_content", ""))),
                    # 保留优化器返回的额外信息，但放在单独的字段中
                    "optimization_details": {
                        "optimization_summary": result.get("optimization_summary", ""),
                        "changes_made": result.get("changes_made", []),
                        "quality_improvement": result.get("quality_improvement", "")
                    }
                }
                
                return standard_chapter_data
            else:
                print(f"  ❌ 章节优化失败，返回无效结果: {type(result)}")
                return None
                
        except Exception as e:
            print(f"  ❌ 章节优化过程异常: {e}")
            return None

    def _generate_optimization_prompt(self, params: Dict) -> str:
        """生成章节优化提示词 - 要求返回标准章节格式"""
        try:
            assessment = json.loads(params.get("assessment_results", "{}"))
        except:
            assessment = {}
            
        original_content = params.get("original_content", "")
        novel_title = params.get("novel_title", "未知小说")
        chapter_number = params.get("chapter_number", 0)
        chapter_title = params.get("chapter_title", "")
        writing_style_guide = params.get("writing_style_guide", {})
        
        # 获取完整的世界状态用于参考
        full_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        # 构建优化指导
        weaknesses = assessment.get('weaknesses', [])
        consistency_issues = assessment.get('consistency_issues', [])
        
        optimization_guide = "## 主要优化方向\n"
        if weaknesses:
            optimization_guide += "### 质量问题修复\n"
            for i, weakness in enumerate(weaknesses[:3], 1):
                optimization_guide += f"{i}. {weakness}\n"
        
        if consistency_issues:
            optimization_guide += "### 一致性问题修复\n"
            for i, issue in enumerate(consistency_issues[:2], 1):
                optimization_guide += f"{i}. {issue.get('description', '')} - 建议: {issue.get('suggestion', '')}\n"
        
        return f"""
    你是一个专业的小说编辑，需要对以下章节内容进行优化。请保持原有的章节结构和风格，只针对质量问题进行调整。

    ## 优化任务信息
    - **小说标题**: {novel_title}
    - **章节标题**: {chapter_title}
    - **章节编号**: 第{chapter_number}章
    - **当前评分**: {assessment.get('overall_score', 0)}/10分
    - **质量评级**: {assessment.get('quality_verdict', '未知')}

    ## 需要优化的主要问题
    {optimization_guide}

    ## 写作风格参考
    {json.dumps(writing_style_guide, ensure_ascii=False, indent=2) if writing_style_guide else "无特定风格要求"}

    ## 世界状态参考（请确保一致性）
    {json.dumps(full_world_state, ensure_ascii=False, indent=2) if full_world_state else "无世界状态数据"}

    ## 原始章节内容
    {original_content}

    ## 优化要求
    1. **保持核心情节**：不改变主要情节发展
    2. **提升文笔质量**：改善语言表达，消除AI痕迹
    3. **修复一致性问题**：确保角色、物品、关系等要素的一致性
    4. **增强可读性**：优化段落结构和叙事节奏
    5. **保持原有结构**：章节标题、段落结构等保持不变
    6. **目标字数**：优化后内容长度应在2000-3500字之间

    ## 输出格式要求
    请返回优化后的完整章节内容，使用以下标准的JSON格式：
    {{
        "content": "优化后的完整章节内容，保持原有的章节标题和段落结构",
        "word_count": 优化后的字数统计,
        "optimization_summary": "简要说明优化重点",
        "changes_made": ["具体修改1", "具体修改2", "具体修改3"],
        "quality_improvement": "质量提升说明"
    }}

    请确保返回的内容可以直接替换原始章节内容，同时保持所有必要的章节元素。
    """

    def _quick_optimize_chapter(self, chapter_data: Dict, assessment: Dict) -> Optional[Dict]:
        """快速优化章节（包含一致性修复）"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        consistency_issues = assessment.get("consistency_issues", [])
        
        intensity_config = self.get_optimization_intensity(score, consistency_issues)
        
        if intensity_config["max_issues"] == 0:
            return None
        
        # 优先处理一致性问題
        priority_issues = []
        severe_consistency = [issue for issue in consistency_issues 
                            if issue.get('severity') == '高']
        
        # 添加严重一致性问題
        for issue in severe_consistency[:2]:
            priority_issues.append(f"修复一致性问題: {issue.get('description')}")
        
        # 添加其他弱点
        remaining_slots = intensity_config["max_issues"] - len(priority_issues)
        if remaining_slots > 0:
            priority_issues.extend(weaknesses[:remaining_slots])
        
        if not priority_issues:
            if score < self.quality_thresholds["needs_optimization"]:
                priority_issues = ["提升情节连贯性", "增强角色表现", "改善文笔质量"]
            else:
                return None
        
        optimization_params = {
            "assessment_results": json.dumps({
                "weaknesses": weaknesses,
                "consistency_issues": consistency_issues,
                "updated_world_state": assessment.get("updated_world_state", {}),
                "overall_score": score,
                "optimization_intensity": intensity_config["description"]
            }, ensure_ascii=False),
            "original_content": chapter_data.get("content", ""),
            "priority_fix_1": priority_issues[0] if len(priority_issues) > 0 else "提升整体质量",
            "priority_fix_2": priority_issues[1] if len(priority_issues) > 1 else "",
            "priority_fix_3": priority_issues[2] if len(priority_issues) > 2 else "",
            "optimization_intensity": intensity_config["description"]
        }
        
        return self.optimize_chapter_content(optimization_params)

    def should_optimize_chapter(self, assessment: Dict) -> Tuple[bool, str]:
        """判断是否需要优化章节（考虑黄金三章特殊要求）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        chapter_info = assessment.get("golden_chapters_assessment", {})
        
        # 检查是否为黄金三章
        is_golden_chapter = chapter_info.get("chapter_number", 0) in [1, 2, 3]
        
        # 黄金三章的特殊优化逻辑
        if is_golden_chapter:
            golden_minimum = 8.5
            if score < golden_minimum:
                return True, f"黄金三章评分低于{golden_minimum}分，必须优化"
            elif not chapter_info.get("is_acceptable", True):
                return True, "黄金三章未达到可接受标准"
        
        # 原有的优化逻辑（严重一致性问题的处理）
        severe_consistency_issues = [issue for issue in consistency_issues 
                                if issue.get('severity') == '高']
        
        if severe_consistency_issues:
            return True, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        thresholds = self.quality_thresholds
        
        if score >= thresholds["excellent"]:
            return False, "质量优秀，无需优化"
        elif score >= thresholds["good"]:
            return False, "质量良好，可选优化"
        elif score >= thresholds["acceptable"]:
            return True, "质量合格，建议优化"
        elif score >= thresholds["needs_optimization"]:
            return True, "需要优化提升质量"
        else:
            return True, "质量不合格，需要重点优化"

    def get_quality_verdict(self, score: float) -> Tuple[str, str]:
        """获取质量评级"""
        grades = self.unified_quality_standards["quality_grades"]
        
        if score >= grades["excellent"]:
            return "优秀", "质量很高，无需优化"
        elif score >= grades["good"]:
            return "良好", "质量良好，可轻微优化"
        elif score >= grades["acceptable"]:
            return "合格", "建议优化以提升质量"
        elif score >= grades["needs_rewrite"]:
            return "需要优化", "需要重点优化"
        else:
            return "需要重写", "质量不合格，建议重写"

    def should_skip_optimization(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """判断是否应该跳过优化（考虑一致性因素）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        skip_config = self.optimization_settings["skip_optimization_conditions"]
        
        # 如果有严重一致性问題，不跳过优化
        severe_consistency_issues = [issue for issue in consistency_issues 
                                   if issue.get('severity') == '高']
        if severe_consistency_issues:
            return False, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        if score >= skip_config["min_score_skip"]:
            return True, "质量优秀，跳过优化"
        
        ai_score = assessment.get("detailed_scores", {}).get("ai_artifacts_detected", 2)
        if ai_score >= skip_config["min_ai_score_skip"]:
            return True, "AI痕迹较少，跳过优化"
        
        word_count = chapter_data.get("word_count", 0)
        word_range = skip_config["word_count_range"]
        if word_range[0] <= word_count <= word_range[1]:
            if score >= skip_config["min_score_with_good_words"]:
                return True, "字数合适且质量良好，跳过优化"
        
        return False, "需要优化"

    def get_optimization_intensity(self, score: float, consistency_issues: List = None) -> Dict:
        """获取优化强度配置（考虑一致性因素）"""
        intensity_configs = self.optimization_settings["optimization_intensity"]
        
        # 如果有严重一致性问題，提高优化强度
        severe_issues = [issue for issue in (consistency_issues or []) 
                        if issue.get('severity') == '高']
        
        if severe_issues:
            return {
                "max_issues": len(severe_issues) + 2,
                "description": f"重点优化（包含{len(severe_issues)}个严重一致性问題）"
            }
        
        if score < intensity_configs["high"]["threshold"]:
            return intensity_configs["high"]
        elif score < intensity_configs["medium"]["threshold"]:
            return intensity_configs["medium"]
        elif score < intensity_configs["low"]["threshold"]:
            return intensity_configs["low"]
        else:
            return {"max_issues": 0, "description": "无需优化"}

    # ==================== 快速评估方法 ====================

    def quick_assess_chapter_quality(self, chapter_content: str, chapter_title: str, 
                                chapter_number: int, novel_title: str, previous_summary: str, 
                                word_count: int = 0, novel_data: Dict = None) -> Dict:
        """快速评估章节质量（包含一致性检查）"""
        # 加载之前的世界状态
        self.world_state_manager.current_world_state = self.world_state_manager.load_previous_assessments(novel_title, novel_data)
        
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": 100,
            "word_count": word_count
        })

    # ==================== 其他内容类型评估 ====================

    def assess_market_analysis_quality(self, market_analysis: Dict) -> Dict:
        """评估市场分析质量"""
        if not market_analysis:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_market_analysis_assessment_prompt(market_analysis)
        
        result = self.api_client.generate_content_with_retry(
            "market_analysis_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="市场分析质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_market_analysis_assessment_prompt(self, market_analysis: Dict) -> str:
        """生成市场分析评估提示词"""
        return f"""
请评估以下市场分析内容的质量：

市场分析内容:
{json.dumps(market_analysis, ensure_ascii=False, indent=2)}

评估维度：
1. 市场洞察深度 (2分): 对目标市场和读者需求的分析是否深入
2. 竞争分析准确性 (2分): 对竞争环境和自身优势的分析是否准确
3. 卖点提炼有效性 (2分): 核心卖点和差异化优势是否清晰有力
4. 数据支撑充分性 (2分): 是否有充分的数据和市场依据支撑分析
5. 可行性评估 (2分): 提出的策略和方向是否具备可行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_writing_plan_quality(self, writing_plan: Dict) -> Dict:
        """评估写作计划质量"""
        if not writing_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_writing_plan_assessment_prompt(writing_plan)
        
        result = self.api_client.generate_content_with_retry(
            "writing_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="写作计划质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_writing_plan_assessment_prompt(self, writing_plan: Dict) -> str:
        """生成写作计划评估提示词"""
        return f"""
请评估以下写作计划的质量：

写作计划内容:
{json.dumps(writing_plan, ensure_ascii=False, indent=2)}

评估维度：
1. 结构合理性 (2分): 章节节奏和情节分布是否合理
2. 角色成长设计 (2分): 主角成长轨迹是否清晰合理
3. 冲突设计质量 (2分): 主要冲突和矛盾设计是否吸引人
4. 伏笔设计 (2分): 伏笔线和情感线设计是否有机融合
5. 可行性评估 (2分): 计划是否具备可执行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_core_worldview_quality(self, worldview: Dict) -> Dict:
        """评估世界观质量"""
        if not worldview:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_worldview_assessment_prompt(worldview)
        
        result = self.api_client.generate_content_with_retry(
            "core_worldview_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="世界观质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_worldview_assessment_prompt(self, worldview: Dict) -> str:
        """生成世界观评估提示词"""
        return f"""
请评估以下世界观设定的质量：

世界观内容:
{json.dumps(worldview, ensure_ascii=False, indent=2)}

"""

    def assess_character_design_quality(self, character_design: Dict) -> Dict:
        """评估角色设计质量"""
        if not character_design:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_character_design_assessment_prompt(character_design)
        
        result = self.api_client.generate_content_with_retry(
            "character_design_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="角色设计质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_character_design_assessment_prompt(self, character_design: Dict) -> str:
        """生成角色设计评估提示词"""
        return f"""
内容:
请根据你作为角色设计顾问的专业身份，使用系统提示中定义的评估体系和JSON格式，对以下角色设计进行全面评估。

待评估的角色设计内容：
{json.dumps(character_design, ensure_ascii=False, indent=2)}

"""

    def optimize_market_analysis(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化市场分析 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_market_analysis_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "market_analysis_optimization", 
            user_prompt, 
            purpose="市场分析优化"
        )
        return result

    def optimize_writing_plan(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化写作计划 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_writing_plan_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "writing_plan_optimization", 
            user_prompt, 
            purpose="写作计划优化"
        )
        return result
    
    def optimize_core_worldview(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化世界观 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_worldview_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "core_worldview_optimization", 
            user_prompt, 
            purpose="世界观优化"
        )
        return result


    def optimize_novel_plan(self, plan_to_optimize, optimization_params):
        market_analysis = optimization_params.get("market_competitor_analysis")
        """优化小说方案 - 支持新鲜度要求"""
        optimization_prompt = f"""
    作为一名顶级的、具备敏锐市场嗅觉的网文策划总监，你的任务是结合【内部评估】和【外部市场竞品分析】，对以下小说方案进行最终的、决定性的战略优化。

    ## 1. 待优化方案 ##
    {json.dumps(plan_to_optimize, ensure_ascii=False, indent=2)}

    ## 2. 内部评估报告 (我们自己的专家意见) ##
    {json.dumps(optimization_params.get("quality_assessment"), ensure_ascii=False, indent=2)}

    ## 3. 外部市场竞品分析 (当前头部作品打法) ##
    {json.dumps(market_analysis, ensure_ascii=False, indent=2)}

    ## 4. 【！！！核心优化任务！！！】 ##
    你的目标是让待优化方案【超越】所有市场竞品。请按以下思路执行：
    1.  **分析市场**: 从竞品分析中，总结出当前市场的【成功公式】和【饱和区域】。
    2.  **对比定位**: 将我们的方案与市场竞品进行对比。我们的金手指和卖点是真正【新颖独特】，还是只是【竞品的微小变种】？我们的优势区间在哪里？
    3.  **战略优化**: 基于以上分析，对方案进行手术刀式的精准修改：
        *   **强化独特性**: 如果方案有独特的亮点，将其放大，做到极致，成为读者选择我们的唯一理由。
        *   **差异化突围**: 如果方案与竞品过于同质化，必须修改金手指的核心玩法或故事的切入点，找到蓝海赛道。
        *   **优化钩子**: 改写简介和核心卖点，使其比所有竞品都更具吸引力、更吊人胃口。

    ## 5. 输出要求 ##
    请返回一个【完整的、经过你优化后】的小说方案JSON。除了优化部分，其他字段结构必须保持不变。不要任何解释，直接输出JSON。
    """
        result = self.api_client.generate_content_with_retry(
            "novel_plan_optimization", 
            optimization_prompt, 
            purpose="小说方案优化"
        )
        return result

    def optimize_character_design(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化角色设计 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_character_design_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "character_design_optimization", 
            user_prompt, 
            purpose="角色设计优化"
        )
        return result


    def calculate_quality_statistics(self, quality_records: Dict) -> Dict:
        """计算质量统计数据"""
        if not quality_records:
            return {}
        
        scores = []
        ai_scores = []
        detailed_scores = {
            "plot_coherence": [],
            "character_consistency": [],
            "chapter_connection": [],
            "writing_quality": [],
            "ai_artifacts_detected": [],
            "emotional_impact": []
        }
        
        for chapter_num, record in quality_records.items():
            assessment = record.get("assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            
            # 收集详细分数
            detailed = assessment.get("detailed_scores", {})
            for key in detailed_scores.keys():
                if key in detailed:
                    detailed_scores[key].append(detailed[key])
            
            # 特别收集AI痕迹分数
            ai_score = detailed.get('ai_artifacts_detected', 2)
            ai_scores.append(ai_score)
        
        if not scores:
            return {}
        
        # 计算统计信息
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 2
        
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= self.quality_thresholds["excellent"]]),
            "良好": len([s for s in scores if self.quality_thresholds["good"] <= s < self.quality_thresholds["excellent"]]),
            "合格": len([s for s in scores if self.quality_thresholds["acceptable"] <= s < self.quality_thresholds["good"]]),
            "需要优化": len([s for s in scores if s < self.quality_thresholds["acceptable"]])
        }
        
        # 计算AI痕迹分布
        ai_distribution = {
            "优秀(2分)": len([s for s in ai_scores if s == 2]),
            "良好(1.5-2分)": len([s for s in ai_scores if 1.5 <= s < 2]),
            "需改进(1-1.5分)": len([s for s in ai_scores if 1 <= s < 1.5]),
            "较差(<1分)": len([s for s in ai_scores if s < 1])
        }
        
        # 计算详细分数平均值
        avg_detailed_scores = {}
        for key, values in detailed_scores.items():
            if values:
                avg_detailed_scores[key] = round(sum(values) / len(values), 2)
        
        return {
            "total_chapters_assessed": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "quality_distribution": quality_distribution,
            "average_detailed_scores": avg_detailed_scores,
            "ai_quality": {
                "average_ai_score": round(avg_ai_score, 2),
                "ai_distribution": ai_distribution,
                "chapters_with_ai_artifacts": len([s for s in ai_scores if s < 2])
            }
        }

    # ==================== 缺失的方法修复 ====================

    def _load_character_development_data(self, novel_title: str) -> Dict:
        """加载角色发展数据 - 修复缺失的方法"""
        return self.world_state_manager._load_character_development_data(novel_title)

    def get_comprehensive_previous_summary_enhanced(self, novel_title: str, chapter_number: int) -> str:
        """增强版前情提要生成"""
        character_status = self.world_state_manager.get_character_comprehensive_status_enhanced(novel_title)
        
        if not character_status:
            return "暂无角色状态信息"
        
        summary_parts = ["【主要角色状态】"]
        
        for char_name, status in character_status.items():
            char_summary = self._format_character_summary_enhanced(char_name, status, chapter_number)
            summary_parts.append(char_summary)
        
        return "\n".join(summary_parts)

    def _format_character_summary_enhanced(self, char_name: str, status: Dict, current_chapter: int) -> str:
        """增强版角色摘要格式化"""
        parts = []
        
        basic_info = status["basic_info"]
        cultivation_info = status["cultivation_info"]
        mental_state = status["mental_state"]
        
        # 基础状态行 - 增强位置和状态显示
        status_line = f"{char_name}"
        if cultivation_info.get("cultivation_level") and cultivation_info["cultivation_level"] != "未知":
            status_line += f"（{cultivation_info['cultivation_level']}）"
        
        location = cultivation_info.get("location", "")
        location_status = cultivation_info.get("location_status", "")
        
        if location_status == "移动中":
            status_line += f" 🚶{location}"
        else:
            status_line += f" 📍{location}"
        
        parts.append(status_line)
        
        # 心理状态和情绪 - 使用推断的情绪
        emotional_state = mental_state.get("recent_emotional_state", "平静")
        if mental_state.get("core_traits"):
            traits = "、".join(mental_state["core_traits"][:2])
            parts.append(f"  💭{traits}，情绪：{emotional_state}")
        
        # 重要关系 - 使用清理后的关系
        relationships = status["relationships"][:2]
        if relationships:
            rel_icons = {
                "师徒": "👥", "竞争师徒": "⚔️👥", "对手": "⚔️", 
                "敌对": "🔥", "盟友": "🤝", "道侣": "❤️"
            }
            
            rel_texts = []
            for rel in relationships:
                icon = rel_icons.get(rel["type"], "•")
                rel_texts.append(f"{icon}{rel['character']}（{rel['type']}）")
            
            parts.append(f"  🔗关系：{'，'.join(rel_texts)}")
        
        # 近期发展
        recent_dev = status["recent_development"]
        if recent_dev.get("milestones"):
            latest_milestone = recent_dev["milestones"][-1]
            milestone_icon = "⭐" if latest_milestone.get("type") in ["突破", "获得宝物"] else "📌"
            parts.append(f"  {milestone_icon}近期：{latest_milestone.get('description', '有所进展')}")
        
        return "\n".join(parts)

    def _get_recent_important_events(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取近期重要事件"""
        events = []
        
        # 检查角色状态变化（死亡、重伤等）
        characters = world_state.get("characters", {})
        for char_name, char_data in characters.items():
            attributes = char_data.get("attributes", {})
            last_updated = char_data.get("last_updated", 0)
            
            # 只关注最近3章内的事件
            if current_chapter - last_updated <= 3:
                status = attributes.get("status", "")
                if status in ["死亡", "重伤", "失踪"]:
                    events.append(f"• {char_name}{status}")
        
        return events[:3]  # 最多返回3个事件

    def _get_key_updates(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取关键物品和功法更新"""
        updates = []
        
        # 高品质物品获取
        cultivation_items = world_state.get("cultivation_items", {})
        for item_name, item_data in cultivation_items.items():
            last_updated = item_data.get("last_updated", 0)
            quality = item_data.get("quality", "")
            owner = item_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}获得{quality}物品「{item_name}」")
        
        # 重要功法掌握
        cultivation_skills = world_state.get("cultivation_skills", {})
        for skill_name, skill_data in cultivation_skills.items():
            last_updated = skill_data.get("last_updated", 0)
            quality = skill_data.get("quality", "")
            owner = skill_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}掌握{quality}功法「{skill_name}」")
        
        return updates[:3]  # 最多返回3个更新


    def load_previous_assessments(self, novel_title: str, novel_data: Dict = None) -> Dict:
        """向后兼容：加载之前章节的评估数据"""
        return self.world_state_manager.load_previous_assessments(novel_title, novel_data)

    def save_assessment_data(self, novel_title: str, chapter_number: int, assessment_data: Dict):
        """向后兼容：保存评估数据"""
        self.world_state_manager.save_assessment_data(novel_title, chapter_number, assessment_data)

    def assess_character_importance(self, character_data: Dict, chapter_content: str = "") -> str:
        """向后兼容：评估角色重要性"""
        return self.world_state_manager.assess_character_importance(character_data, chapter_content)

    def manage_character_development_table(self, novel_title: str, character_data: Dict, 
                                        current_chapter: int, action: str = "update") -> Dict:
        """向后兼容：管理角色发展表"""
        return self.world_state_manager.manage_character_development_table(novel_title, character_data, current_chapter, action)

    def get_character_development_suggestions(self, character_name: str, novel_title: str, current_chapter: int) -> List[Dict]:
        """向后兼容：获取角色发展建议"""
        return self.world_state_manager.get_character_development_suggestions(character_name, novel_title, current_chapter)

    def assess_character_development(self, chapter_content: str, characters_in_chapter: List[str], 
                                novel_title: str, chapter_number: int) -> Dict:
        """向后兼容：评估角色发展质量"""
        return self.world_state_manager.assess_character_development(chapter_content, characters_in_chapter, novel_title, chapter_number)

    def update_character_development_from_assessment(self, novel_title: str, assessment: Dict, chapter_number: int):
        """向后兼容：从评估结果更新角色发展表"""
        self.world_state_manager.update_character_development_from_assessment(novel_title, assessment, chapter_number)

    def initialize_world_state_from_novel_data(self, novel_title: str, novel_data: Dict):
        """向后兼容：基于小说数据初始化世界状态"""
        return self.world_state_manager.initialize_world_state_from_novel_data(novel_title, novel_data)

    def cleanup_characters_by_strategy(self, novel_title: str, strategy_config: Dict) -> Dict:
        """向后兼容：根据策略清理角色数据"""
        return self.world_state_manager.cleanup_characters_by_strategy(novel_title, strategy_config)

    def get_novel_consistency_report(self, novel_title: str) -> Dict:
        """向后兼容：获取小说的整体一致性报告"""
        return self.world_state_manager.get_novel_consistency_report(novel_title)
    
    def _generate_market_analysis_optimization_prompt(self, params: Dict) -> str:
        """市场分析优化提示词 - 使用新结构"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        
        # 使用新结构获取数据
        freshness_score = freshness_assessment.get("score", {}).get("total", 0)
        suggestions = freshness_assessment.get("suggestions", [])
        
        freshness_guidance = ""
        if suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 新鲜度评分
    当前新鲜度评分: {freshness_score:.1f}/10分
    目标新鲜度评分: 9.0分以上

    ### 改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in suggestions)}

    ### 新鲜度提升方向
    1. **挖掘独特市场切入点**：避免泛泛而谈，找到具体的、差异化的市场机会
    2. **提供深度洞察**：不只是罗列数据，要提供有见地的分析
    3. **差异化竞争策略**：提出与现有作品明显不同的竞争策略
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升分析深度**：确保每个观点都有充分的数据和逻辑支撑
    2. **优化结构逻辑**：使分析报告结构清晰，逻辑连贯
    3. **增强可读性**：使用更生动、专业的表达方式
    4. **加强数据支撑**：为每个结论提供充分的市场依据
    """
        
        return f"""
    你是一个专业的市场分析优化专家，需要对以下市场分析内容进行优化，同时提升质量和新鲜度。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始市场分析内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心结论**：不改变原有的核心市场判断和结论
    2. **提升分析深度**：为每个观点提供更充分的数据和逻辑支撑
    3. **增强独特性**：避免套路化分析，提供独特的市场洞察
    4. **优化表达方式**：使用更专业、生动的语言表达

    ### 质量标准
    - 分析逻辑严密，数据支撑充分
    - 结构清晰，层次分明
    - 观点鲜明，结论明确
    - 语言专业，表达准确

    ### 新鲜度标准  
    - 避免常见的市场分析套路
    - 提供独特的市场视角和洞察
    - 挖掘差异化的竞争策略
    - 提出创新的营销建议

    ## 输出格式
    请返回优化后的完整市场分析内容，保持原有的JSON结构，但提升内容的质量和新鲜度。
    """

    def _generate_writing_plan_optimization_prompt(self, params: Dict) -> str:
        """写作计划优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升写作计划的创新性"}

    ### 新鲜度提升方向
    1. **创新情节结构**：避免千篇一律的起承转合，尝试新的叙事结构
    2. **独特角色成长**：设计非传统的角色成长路径和转折点
    3. **新颖冲突设计**：创造独特的矛盾冲突，避免常见的情感套路
    4. **创新伏笔设置**：设计出人意料但又合理的伏笔和反转
    5. **差异化节奏控制**：尝试新的节奏变化模式，增强读者体验
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **优化结构合理性**：确保章节节奏和情节分布更加合理
    2. **加强角色成长设计**：使主角成长轨迹更加清晰和吸引人
    3. **提升冲突设计质量**：强化主要冲突的吸引力和张力
    4. **完善伏笔设计**：使伏笔线与情感线更好地融合
    5. **增强可行性**：确保计划具备良好的可执行性
    """
        
        return f"""
    你是一个专业的写作计划优化专家，需要对以下写作计划进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始写作计划内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心框架**：不改变原有的主要情节框架和角色设定
    2. **提升计划深度**：为每个阶段提供更详细和合理的规划
    3. **增强创新性**：避免套路化情节，提供独特的叙事设计
    4. **优化可行性**：确保计划在现实中具备良好的可执行性

    ### 质量标准
    - 情节结构合理，节奏把控得当
    - 角色成长轨迹清晰可信
    - 冲突设计有吸引力
    - 伏笔设置巧妙合理
    - 整体计划具备可执行性

    ### 新鲜度标准
    - 避免常见的情节套路和模板
    - 提供独特的叙事视角和结构
    - 设计创新的角色发展路径
    - 创造新颖的矛盾冲突类型
    - 设置出人意料的伏笔和转折

    ## 输出格式
    请返回优化后的完整写作计划内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def _generate_worldview_optimization_prompt(self, params: Dict) -> str:
        """世界观优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升世界观的独特性"}

    ### 新鲜度提升方向
    1. **创新世界观基础**：避免常见的修仙/异能/科幻设定，创造独特的世界观基础
    2. **独特力量体系**：设计非传统的修炼体系或能力系统
    3. **新颖社会结构**：创造独特的社会组织形态和权力结构
    4. **创新文化背景**：构建具有特色的文化习俗和价值观念
    5. **差异化地理环境**：设计独特的地理环境和生态体系
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升体系完整性**：确保世界观各个要素之间逻辑自洽
    2. **加强细节丰富度**：为世界观提供更丰富的细节支撑
    3. **优化层次结构**：使世界观呈现清晰的层次结构
    4. **增强扩展性**：确保世界观有足够的扩展空间和发展潜力
    5. **完善内在逻辑**：强化世界观内部各要素的逻辑关系
    """
        
        return f"""
    你是一个专业的世界观架构优化专家，需要对以下世界观设定进行优化，同时提升质量和独特性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始世界观内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心概念**：不改变世界观的基本概念和核心设定
    2. **提升体系完整性**：使世界观各个要素更加协调和完整
    3. **增强独特性**：避免常见的世界观套路，提供独特的设定
    4. **优化逻辑自洽**：确保世界观内部逻辑更加严密和合理

    ### 质量标准
    - 世界观体系完整，逻辑自洽
    - 各个要素协调统一，层次清晰
    - 设定丰富具体，细节充分
    - 扩展性强，有发展潜力
    - 与故事主题和情节匹配度高

    ### 新鲜度标准
    - 避免常见的世界观设定套路
    - 提供独特的世界观基础和概念
    - 设计创新的力量体系和社会结构
    - 构建具有特色的文化背景
    - 创造新颖的地理环境和生态

    ## 输出格式
    请返回优化后的完整世界观内容，保持原有的JSON结构，但提升内容的质量和独特性。
    """

    def _generate_character_design_optimization_prompt(self, params: Dict) -> str:
        """角色设计优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升角色设计的创新性"}

    ### 新鲜度提升方向
    1. **创新角色设定**：避免脸谱化角色，创造独特的人物形象
    2. **独特成长路径**：设计非传统的角色发展轨迹
    3. **新颖关系网络**：构建独特的角色关系和互动模式
    4. **创新性格特质**：设计具有特色的性格特点和心理特征
    5. **差异化背景故事**：创造独特的角色背景和成长经历
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升角色深度**：使角色形象更加立体和丰满
    2. **加强动机合理性**：确保角色行为和动机更加合理可信
    3. **优化关系设计**：使角色关系更加复杂和有趣
    4. **增强成长弧线**：强化角色的成长轨迹和发展变化
    5. **完善背景设定**：为角色提供更丰富的背景故事
    """
        
        return f"""
    你是一个专业的角色设计优化专家，需要对以下角色设计进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始角色设计内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心特质**：不改变角色的核心性格和基本设定
    2. **提升角色深度**：使角色形象更加立体和丰满
    3. **增强独特性**：避免脸谱化角色，提供独特的人物设计
    4. **优化关系网络**：使角色关系更加复杂和有趣

    ### 质量标准
    - 角色形象立体丰满，性格鲜明
    - 行为动机合理可信，成长轨迹清晰
    - 角色关系复杂有趣，互动模式多样
    - 背景故事丰富具体，与角色特质匹配
    - 角色设计符合世界观和故事需求

    ### 新鲜度标准
    - 避免常见的角色设定套路
    - 提供独特的角色形象和性格
    - 设计创新的成长路径和发展
    - 构建新颖的角色关系和互动
    - 创造具有特色的背景故事

    ## 输出格式
    请返回优化后的完整角色设计内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def _generate_novel_plan_optimization_prompt(self, params: Dict) -> str:
        """小说方案优化提示词 - 增强新鲜度要求"""
        # 直接从 params 中获取 assessment_results，它现在是字典而不是字符串
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升小说方案的创新性"}

    ### 新鲜度提升方向
    1. **创新核心概念**：避免常见的小说套路，创造独特的故事概念
    2. **独特情节设计**：设计非传统的情节发展和转折
    3. **新颖角色设定**：创造具有特色的主角和配角设定
    4. **创新金手指设计**：避免常见的系统设定，提供独特的能力设计
    5. **差异化世界观**：构建独特的世界观背景和设定
    6. **【标题长度约束】**：优化后的标题必须严格保持在15个字以内（含标点符号），确保简洁有力。
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升概念完整性**：使小说概念更加完整和吸引人
    2. **加强情节合理性**：确保情节发展更加合理和连贯
    3. **优化角色设计**：使角色设定更加立体和有趣
    4. **增强市场匹配度**：确保方案符合目标读者需求
    5. **完善核心设定**：强化金手指、世界观等核心设定
    """
        
        return f"""
    你是一个专业的小说方案优化专家，需要对以下小说方案进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始小说方案内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心创意**：不改变小说的核心创意和基本方向
    2. **提升方案完整性**：使小说方案更加完整和详细
    3. **增强创新性**：避免常见的小说套路，提供独特的故事设计
    4. **优化市场适应性**：确保方案符合市场需求和读者喜好

    ### 质量标准
    - 概念完整清晰，吸引力强
    - 情节设计合理，发展连贯
    - 角色设定立体，特点鲜明
    - 核心设定有趣，扩展性强
    - 市场定位准确，读者明确

    ### 新鲜度标准
    - 避免常见的小说创作套路
    - 提供独特的故事概念和创意
    - 设计创新的情节发展模式
    - 创造新颖的角色形象设定
    - 构建独特的金手指和世界观

    ## 输出格式
    请返回优化后的完整小说方案内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def assess_novel_plan_quality(self, novel_plan: Dict) -> Dict:
        """评估小说方案质量"""
        if not novel_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_novel_plan_assessment_prompt(novel_plan)
        
        result = self.api_client.generate_content_with_retry(
            "novel_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="小说方案质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_novel_plan_assessment_prompt(self, novel_plan: Dict) -> str:
        """生成小说方案评估提示词"""
        return f"""
    请评估以下小说方案的质量：

    小说方案内容:
    {json.dumps(novel_plan, ensure_ascii=False, indent=2)}

    评估维度：
    1. 概念完整性 (2分): 核心概念是否完整清晰，吸引力如何
    2. 情节设计质量 (2分): 情节设计是否合理，发展是否连贯
    3. 角色设定质量 (2分): 角色设定是否立体，特点是否鲜明
    4. 核心设定创新性 (2分): 金手指、世界观等核心设定是否有创新
    5. 市场适应性 (2分): 方案是否符合市场需求和读者喜好

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": 总体评分(满分10分),
        "quality_verdict": "质量评级",
        "strengths": ["优点列表"],
        "weaknesses": ["待改进方面列表"],
        "optimization_suggestions": ["优化建议列表"]
    }}
    """
    def _get_sorted_entities(self, entities: dict) -> list:
        """一个通用的辅助函数，用于获取排序后的实体列表"""
        if not entities or not isinstance(entities, dict):
            return []
        # 假设实体数据中有 'update_count' 用于排序，如果没有则不排序
        if all('update_count' in v for v in entities.values()):
            return sorted(
                entities.items(),
                key=lambda item: item[1].get('update_count', 0),
                reverse=True
            )
        return list(entities.items())

    def _build_consistency_check_prompt_section(self, world_state: Dict) -> str:
        """【QualityAssessor内部使用】根据世界状态，构建强约束的一致性检查清单"""
        if not world_state:
            return "# 警告：无世界状态信息，无法进行一致性检查。\n"

        guidance_parts = ["\n--- 一致性铁律 (请严格按此标准审查) ---\n"]
        
        characters = world_state.get('characters', {})
        items = world_state.get('cultivation_items', world_state.get('items', {})) # 兼容旧的 'items' 键
        skills = world_state.get('cultivation_skills', world_state.get('skills', {})) # 兼容旧的 'skills' 键
        relationships = world_state.get('relationships', {})

        # 1. 【最高优先级】死亡/退场名单
        dead_or_exited_chars = [
            name for name, data in characters.items() 
            if data.get('attributes', {}).get('status', 'active').lower() in ['dead', 'exited', '死亡', '退场']
        ]
        if dead_or_exited_chars:
            guidance_parts.append(f"【🔴绝对禁止】以下角色已死亡或永久退场，绝不能以任何存活形式出现：`{', '.join(dead_or_exited_chars)}`")

        # 2. 【角色核心状态】 (最重要的5个)
        char_list = self._get_sorted_entities(characters)
        if char_list:
            guidance_parts.append("\n【🟡角色当前状态 (必须遵守)】")
            for char_name, char_data in char_list[:5]:
                if char_name in dead_or_exited_chars: continue
                attrs = char_data.get('attributes', {})
                status = attrs.get('status', '活跃')
                location = attrs.get('location', '未知')
                level = attrs.get('cultivation_level', '')
                money = attrs.get('money', None)
                
                state_summary = f"- **{char_name}**: 状态:`{status}`, 位置:`{location}`"
                if level: state_summary += f", 修为:`{level}`"
                if money is not None: state_summary += f", 金钱:`{money}`"
                guidance_parts.append(state_summary)

        # 3. 【物品归属】 (最重要的5件)
        item_list = self._get_sorted_entities(items)
        if item_list:
            guidance_parts.append("\n【🟡关键物品归属 (必须遵守)】")
            for item_name, item_data in item_list[:5]:
                owner = item_data.get('owner', '无主')
                status = item_data.get('status', '完好')
                if status.lower() in ['used', 'destroyed', 'consumed', '已使用', '已消耗', '已损毁']:
                    guidance_parts.append(f"- `{item_name}`: 状态:`{status}`，【不可再次使用】。")
                else:
                    guidance_parts.append(f"- `{item_name}`: 目前归属于 `{owner}`。")

        # 4. 【功法/技能状态】 (最重要的5个)
        skill_list = self._get_sorted_entities(skills)
        if skill_list:
            guidance_parts.append("\n【🟡功法/技能状态 (必须遵守)】")
            for skill_name, skill_data in skill_list[:5]:
                owner = skill_data.get('owner', '未知')
                level = skill_data.get('level', '未知')
                guidance_parts.append(f"- `{owner}` 的技能 `{skill_name}` 当前等级为 `{level}`。")

        # 5. 【关键人物关系】 (最重要的7组)
        rel_list = self._get_sorted_entities(relationships)
        if rel_list:
            guidance_parts.append("\n【🟡关键人物关系 (禁止重复建立)】")
            for rel_key, rel_data in rel_list[:7]:
                parties = rel_key.split('-') if isinstance(rel_key, str) else rel_key
                if len(parties) == 2:
                    char_a, char_b = parties
                    rel_type = rel_data.get('type', '未知')
                    guidance_parts.append(f"- `{char_a}` 与 `{char_b}` 的关系是: `{rel_type}`。他们已经认识！")
        
        guidance_parts.append("\n" + "-"*37 + "\n")
        return "\n".join(guidance_parts)
