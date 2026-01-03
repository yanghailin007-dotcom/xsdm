"""方案生成器 - 专门负责小说方案和规划相关的生成逻辑"""
import copy
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.logger import get_logger


class PlanGenerator:
    """方案生成器 - 处理小说方案、角色设计、世界观等生成逻辑"""
    
    def __init__(self, content_generator):
        self.logger = get_logger("PlanGenerator")
        self.cg = content_generator  # 对主生成器的引用
        self.api_client = content_generator.api_client
        self.quality_assessor = content_generator.quality_assessor
    
    def generate_single_plan(self, creative_seed: str, category: str = None) -> Optional[Dict]:
        """生成单一小说方案"""
        self.logger.info("=== 步骤1: 基于创意种子和分类生成小说方案 ===")
        
        # 如果提供了分类，自动生成适合该分类的主角名字
        if category:
            generated_name = self._generate_character_name_by_category(category, creative_seed)
            if generated_name:
                self.cg.set_custom_main_character_name(generated_name)
                self.logger.info(f"✓ 根据分类 '{category}' 自动生成主角名字: {generated_name}")
        
        user_prompt = {
            "小说分类": category,
            "主角名字": self.cg.custom_main_character_name,
            "核心创意": creative_seed,
            "核心情节": "AI根据创意生成",
            "主角设定": "AI根据创意生成", 
            "金手指": "AI根据创意生成",
            "标题要求": "小说标题必须严格控制在15个字以内（包含所有标点符号），风格要像番茄小说一样简洁、有冲击力、一眼就能抓住读者眼球。例如：《开局女帝认我作父》或《末日：我能无限升级》。",
            "创新要求": "追求新颖独特，强调代入感和沉浸感。避免复杂的世界观解释、外星人、超能力、阴谋论等宏大设定。重点在于有趣的故事、真实的情感、贴近生活的体验。系统或金手指不需要解释来源，直接使用即可。读者关心的是有趣的故事和情感共鸣，而不是复杂的设定。"
        }
        
        max_retries = 2
        result = None
        
        for attempt in range(max_retries):
            self.logger.info(f"  🔄 生成方案尝试 {attempt + 1}/{max_retries}")
            user_prompt_str = json.dumps(user_prompt, ensure_ascii=False)
            result = self.api_client.generate_content_with_retry("one_plans", user_prompt_str, purpose="生成小说方案")
            
            if not result:
                continue
            
            # 评估方案的新鲜度
            freshness_assessment = self.quality_assessor.assess_freshness(result, "novel_plan")
            score_data = freshness_assessment.get("score", {})
            freshness_score = score_data.get("total", 0)
            
            self.logger.info(f"  🆕 方案新鲜度评分: {freshness_score:.1f}/10")
            
            # 检查是否存在复杂设定问题
            complexity_issues = self._check_setting_complexity(result)
            if complexity_issues:
                self.logger.warn(f"  ⚠️ 检测到复杂设定问题: {', '.join(complexity_issues)}")
                freshness_score = max(0, freshness_score - 2)
            
            if freshness_score >= 8.5:
                self.logger.info(f"  ✅ 方案新鲜度达标")
                break
            else:
                self.logger.info(f"  🔄 方案新鲜度不足，尝试优化...")
                optimization_params = {
                    "quality_assessment": {"overall_score": 8.5},
                    "freshness_assessment": freshness_assessment,
                    "complexity_issues": complexity_issues,
                    "optimization_reason": f"新鲜度{freshness_score:.1f}低于8.5分，或存在复杂设定问题"
                }
                optimized_result = self.quality_assessor.optimize_novel_plan(result, optimization_params)
                
                if optimized_result:
                    new_freshness = self.quality_assessor.assess_freshness(optimized_result, "novel_plan")
                    new_score_data = new_freshness.get("score", {})
                    new_score = new_score_data.get("total", 0)
                    self.logger.info(f"  🆕 优化后新鲜度: {new_score:.1f}/10")
                    if new_score >= 7.0:
                        self.logger.info(f"  ✅ 优化成功，新鲜度达标")
                        result = optimized_result
                        break
                    else:
                        self.logger.warn(f"  ⚠️ 优化后新鲜度仍不足，继续重新生成...")
        
        if result:
            result = self.cg._ensure_main_character_in_content(result, "one_plans")
            if 'freshness_assessment' not in locals():
                freshness_assessment = self.quality_assessor.assess_freshness(result, "novel_plan")
                score_data = freshness_assessment.get("score", {})
                freshness_score = score_data.get("total", 0)
            result["freshness_score"] = freshness_score
            result["freshness_assessment"] = freshness_assessment
            
            if self.quality_assessor:
                immersion_score = self.quality_assessor.assess_immersion_level(result)
                result["immersion_score"] = immersion_score
                self.logger.info(f"  💫 代入感评分: {immersion_score:.1f}/10")
            else:
                self.logger.warn(f"  ⚠️ QualityAssessor 未初始化，跳过代入感评估。")
                result["immersion_score"] = 0
        
        return result
    
    def _generate_character_name_by_category(self, category: str, creative_seed: str) -> Optional[str]:
        """根据分类生成主角名字"""
        # 简化的名字生成逻辑
        name_map = {
            "玄幻": "林轩",
            "都市": "陈凡",
            "仙侠": "李青云",
            "科幻": "张浩然",
            "历史": "王云飞"
        }
        return name_map.get(category, "主角")
    
    def _check_setting_complexity(self, result: Dict) -> List[str]:
        """检查是否存在复杂设定问题"""
        issues = []
        synopsis = result.get("synopsis", "")
        
        # 简化的复杂设定检查
        complex_keywords = ["外星人", "阴谋论", "宇宙起源", "多重宇宙", "量子纠缠"]
        for keyword in complex_keywords:
            if keyword in synopsis:
                issues.append(f"包含复杂设定: {keyword}")
        
        return issues
    
    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析"""
        self.logger.info("=== 步骤2: 进行市场分析和卖点提炼 ===")
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        
        if self.cg.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.cg.custom_main_character_name}"
        
        user_prompt += "\n\n【创新要求】请提供有深度的市场分析，避免泛泛而谈，挖掘独特的市场切入点"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        
        if result:
            result = self.cg._assess_and_optimize_content(result, "market_analysis", "市场分析")
        
        return result
    
    def generate_core_worldview(self, novel_title: str, novel_synopsis: str, selected_plan: Dict, 
                               market_analysis: Dict) -> Optional[Dict]:
        """生成核心世界观"""
        self.logger.info("=== 步骤3: 构建核心世界观 ===")
        
        core_settings = selected_plan.get("core_settings", {})
        story_development = selected_plan.get("story_development", {})
        
        world_background = core_settings.get("world_background", "")
        golden_finger = core_settings.get("golden_finger", "")
        core_selling_points = core_settings.get("core_selling_points", [])
        protagonist_position = story_development.get("protagonist_position", "")
        main_plot = story_development.get("main_plot", [])
        
        context = f"""
## 小说信息
- **小说标题**: {novel_title}
- **小说简介**: {novel_synopsis}
- **市场分析**: {json.dumps(market_analysis, ensure_ascii=False)}
- **选定方案**: {json.dumps(selected_plan, ensure_ascii=False)}

### 核心设定（从选定方案提取）
- **世界观背景**: {world_background}
- **金手指/系统**: {golden_finger}
- **核心爽点**: {', '.join(core_selling_points) if isinstance(core_selling_points, list) else core_selling_points}
- **主角定位**: {protagonist_position}
- **主线脉络**: {', '.join(main_plot) if isinstance(main_plot, list) else main_plot}

## 世界观构建要求
基于以上信息，构建一个完整、自洽且符合番茄平台风格的世界观框架。
世界观需要与核心设定和故事发展保持一致，并提供足够的扩展空间。
"""
        
        context += "\n\n## 创新要求\n世界观构建需要避免常见套路，追求独特性和创新性，提供新颖的世界观设定。"
        
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="世界观构建")
        
        if result:
            result = self.cg._assess_and_optimize_content(result, "core_worldview", "世界观构建")
        
        return result
    
    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict,
                                market_analysis: Dict, design_level: str,
                                existing_characters: Optional[Dict] = None,
                                stage_info: Optional[Dict] = None,
                                global_growth_plan: Optional[Dict] = None,
                                overall_stage_plans: Optional[Dict] = None,
                                custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计"""
        self.logger.info(f"  -> 角色设计启动，模式: 【{design_level}】")
        
        main_character_name = custom_main_character_name or self.cg.custom_main_character_name
        prompt_type = ""
        prompt_context = {}
        purpose = ""
        
        if design_level == "core":
            prompt_type = "character_design_core"
            story_blueprint = {
                "novel_title": novel_title,
                "selected_plan": selected_plan,
                "core_worldview": core_worldview,
                "market_analysis": market_analysis,
                "global_growth_plan": global_growth_plan,
                "overall_stage_plans": overall_stage_plans
            }
            design_requirements = {
                "main_character_name": main_character_name,
                "required_roles": ["核心盟友/女主", "核心反派"]
            }
            prompt_context = {
                "STORY_BLUEPRINT": json.dumps(story_blueprint, ensure_ascii=False, indent=2),
                "DESIGN_REQUIREMENTS": json.dumps(design_requirements, ensure_ascii=False, indent=2)
            }
            purpose = f"为《{novel_title}》设计核心角色"
            
        elif design_level == "supplementary":
            if not existing_characters or not stage_info:
                self.logger.warn("  ⚠️ 补充角色模式缺少'已有角色'或'阶段信息'，操作已取消。")
                return existing_characters
            
            prompt_type = "character_design_supplementary"
            inferred_roles = self._infer_required_roles_for_stage(stage_info, existing_characters)
            
            stage_requirements = {
                "stage_name": stage_info.get("stage_name", "当前阶段"),
                "stage_summary": stage_info.get("stage_overview", "未知"),
                "new_character_roles": inferred_roles
            }
            prompt_context = {
                "EXISTING_CHARACTERS": json.dumps(existing_characters, ensure_ascii=False, indent=2),
                "STAGE_REQUIREMENTS": json.dumps(stage_requirements, ensure_ascii=False, indent=2)
            }
            purpose = f"为《{novel_title}》的 '{stage_requirements['stage_name']}' 阶段补充配角"
        else:
            self.logger.error(f"  ❌ 未知的角色设计层级: '{design_level}'")
            return None
        
        if not isinstance(prompt_context, dict):
            self.logger.error("  ❌ 角色设计提示词上下文构建失败")
            return None
        
        try:
            prompt_context_str = json.dumps(prompt_context, ensure_ascii=False, indent=2)
        except TypeError as e:
            self.logger.error(f"  ❌ 无法将提示词上下文序列化为JSON: {e}")
            return None
        
        # 🔧 修复：记录序列化后的JSON字符串长度，而不是字典的键值对数量
        self.logger.info(f"  📝 角色设计提示词长度: {len(prompt_context_str)} 字符")
        
        api_result = self.api_client.generate_content_with_retry(
            prompt_type,
            prompt_context_str,
            purpose=purpose
        )
        
        if not api_result:
            self.logger.error(f"  ❌ 角色设计API调用失败 (模式: {design_level})")
            return existing_characters if design_level == "supplementary" else None
        
        result_json = None
        try:
            if isinstance(api_result, dict):
                self.logger.info("  ✅ 角色设计API已返回解析好的JSON字典。")
                result_json = api_result
            elif isinstance(api_result, str):
                self.logger.info("  ✅ 角色设计API返回JSON字符串，正在解析...")
                result_json = json.loads(api_result)
            else:
                self.logger.error(f"  ❌ 角色设计API返回了未知类型: {type(api_result)}")
                return existing_characters if design_level == "supplementary" else None
        except json.JSONDecodeError:
            self.logger.error(f"  ❌ 解析角色设计JSON字符串失败 (模式: {design_level})")
            return existing_characters if design_level == "supplementary" else None
        
        if design_level == "core":
            self.logger.info("  ✅ 核心角色设计生成成功。")
            if main_character_name:
                result_json = self.cg.ensure_main_character_name(result_json, main_character_name)
            return result_json
        elif design_level == "supplementary":
            new_characters = result_json.get("newly_added_characters", [])
            if not new_characters:
                self.logger.warn("  ⚠️ 补充角色API调用成功，但未返回新角色。")
                return existing_characters
            
            self.logger.info(f"  ✅ 成功生成 {len(new_characters)} 个补充角色，正在合并...")
            updated_characters = copy.deepcopy(existing_characters)
            
            if "important_characters" not in updated_characters:
                updated_characters["important_characters"] = []
            
            updated_characters["important_characters"].extend(new_characters)
            return updated_characters
    
    def _infer_required_roles_for_stage(self, stage_info: Dict, existing_characters: Dict) -> List[str]:
        """为阶段推断所需角色"""
        self.logger.info("    -> 正在动态分析阶段情节，推断所需角色...")
        
        event_system = stage_info.get("stage_writing_plan", {}).get("event_system", {})
        major_events = event_system.get("major_events", [])
        plot_summary_parts = [f"阶段总体目标: {stage_info.get('stage_overview', '未知')}"]
        
        for event in major_events[:10]:
            plot_summary_parts.append(f"- 主要事件: {event.get('name', '')} (目标: {event.get('main_goal', '')})")
        
        stage_plot_summary = "\n".join(plot_summary_parts)
        
        existing_names = [char.get("name") for char in existing_characters.get("important_characters", [])]
        if existing_characters.get("main_character"):
            existing_names.append(existing_characters["main_character"].get("name"))
        
        prompt_context = {
            "STAGE_PLOT_SUMMARY": stage_plot_summary,
            "EXISTING_CHARACTERS": ", ".join(filter(None, existing_names))
        }
        
        prompt_context_str = json.dumps(prompt_context, ensure_ascii=False)
        
        roles_data = self.api_client.generate_content_with_retry(
            "role_inference_for_stage",
            prompt_context_str,
            purpose=f"为阶段 '{stage_info.get('stage_name')}' 推断新角色"
        )
        
        try:
            if roles_data:
                required_roles = roles_data.get("required_roles", [])
                if required_roles:
                    self.logger.info(f"    -> 推断成功，需要角色: {', '.join(required_roles)}")
                    return required_roles
        except json.JSONDecodeError:
            self.logger.info("    -> 角色推断失败：无法解析API返回的JSON。")
        
        self.logger.info("    -> 角色推断失败或无结果，使用通用默认值。")
        return ["阶段性反派", "功能性NPC"]
    
    def generate_writing_style_guide(self, creative_seed: str, category: str, selected_plan: Dict, 
                                    market_analysis: Dict) -> Optional[Dict]:
        """生成写作风格指南"""
        self.logger.info(f"  🎨 为分类'{category}'生成写作风格指南...")
        
        try:
            user_prompt = f"""
内容：
编辑，请根据以下【小说核心简报】，为我生成一份专业的写作风格指南。
## 小说核心简报 ##
小说分类: {category}
小说创意: {creative_seed}
核心主题: {selected_plan.get('core_direction', '')}
核心卖点: {market_analysis.get('core_selling_points', '')}
目标读者: {selected_plan.get('target_audience', '')}
"""
            
            result = self.api_client.generate_content_with_retry(
                "writing_style_guide",
                user_prompt,
                purpose="生成写作风格指南"
            )
            
            if result:
                required_keys = [
                    'core_style', 'language_characteristics', 'narration_techniques',
                    'dialogue_style', 'chapter_techniques', 'key_principles'
                ]
                
                for key in required_keys:
                    if key not in result:
                        result[key] = "待补充"
                
                self.logger.info(f"  ✅ 写作风格指南生成成功")
                return result
            else:
                self.logger.error(f"  ❌ 写作风格指南生成失败")
                return None
        except Exception as e:
            self.logger.error(f"  ❌ 生成写作风格指南时出错: {e}")
            return None