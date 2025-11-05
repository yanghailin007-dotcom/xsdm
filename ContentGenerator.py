"""内容生成器类 - 专注内容生成"""

import json
import re
import time
from typing import Any, Dict, Optional, List, Tuple

import APIClient
from Contexts import GenerationContext
import Contexts
import NovelGenerator
from Prompts import Prompts
import QualityAssessor

class ContentGenerator:
    def __init__(self, novel_generator, api_client: APIClient.APIClient, config, event_bus, quality_assessor):
        self.novel_generator:NovelGenerator.NovelGenerator = novel_generator
        self.api_client = api_client
        self.config = config
        self.prompts = Prompts
        self.event_bus = event_bus
        self.quality_assessor:QualityAssessor.QualityAssessor = quality_assessor
        self.custom_main_character_name = None

    def set_custom_main_character_name(self, name: str):
        """设置主角名字"""
        self.custom_main_character_name = name
        print(f"✓ 内容生成器已设置主角名字: {name}")
    
    def _inject_main_character_name(self, prompt: str, context: str = "") -> str:
        """在提示词中注入主角名字"""
        if not self.custom_main_character_name:
            return prompt
        
        name_instruction = f"\n\n【重要提示】主角的名字必须是: {self.custom_main_character_name}\n"
        
        if "【重要提示】" in prompt:
            import re
            prompt = re.sub(r"【重要提示】.*?\n", name_instruction, prompt)
        else:
            lines = prompt.split('\n')
            if lines and lines[0].startswith('你是一位'):
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('你是一位') and not line.startswith('请'):
                        lines.insert(i, name_instruction)
                        break
                else:
                    lines.insert(1, name_instruction)
                prompt = '\n'.join(lines)
            else:
                prompt = name_instruction + prompt
        
        return prompt
    
    def _ensure_main_character_in_content(self, content: Dict, content_type: str) -> Dict:
        """确保内容中包含主角名字"""
        if not self.custom_main_character_name:
            return content
        
        if content_type == "one_plans":
            for plan in content.get("plans", []):
                if self.custom_main_character_name not in plan.get("synopsis", "") and self.custom_main_character_name not in plan.get("title", ""):
                    plan["synopsis"] = plan["synopsis"].replace("主角", self.custom_main_character_name)
        
        elif content_type == "writing_plan":
            writing_approach = content.get("writing_approach", "")
            character_growth = content.get("character_growth_arc", "")
            
            if self.custom_main_character_name not in writing_approach and self.custom_main_character_name not in character_growth:
                if "主角" in writing_approach:
                    content["writing_approach"] = writing_approach.replace("主角", self.custom_main_character_name)
                if "主角" in character_growth:
                    content["character_growth_arc"] = character_growth.replace("主角", self.custom_main_character_name)
        
        return content

    def safe_format(self, template: str, **kwargs) -> str:
        """安全的字符串格式化"""
        escaped_template = template.replace('{', '{{').replace('}', '}}')
        
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            escaped_placeholder = f"{{{{{key}}}}}"
            escaped_template = escaped_template.replace(escaped_placeholder, placeholder)
        
        return escaped_template.format(**kwargs)

    def generate_single_plan(self, creative_seed: str, category: str = None) -> Optional[Dict]:
        """生成单一小说方案 - 增加代入感和沉浸感，避免复杂设定"""
        print("=== 步骤1: 基于创意种子和分类生成小说方案 ===")
        
        # 如果提供了分类，自动生成适合该分类的主角名字
        if category:
            generated_name = self._generate_character_name_by_category(category, creative_seed)
            if generated_name:
                self.set_custom_main_character_name(generated_name)
                print(f"✓ 根据分类 '{category}' 自动生成主角名字: {generated_name}")

        user_prompt = {
            "小说分类": category,
            "主角名字": self.custom_main_character_name,
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
            print(f"  🔄 生成方案尝试 {attempt + 1}/{max_retries}")
            user_prompt_str = json.dumps(user_prompt, ensure_ascii=False)
            result = self.api_client.generate_content_with_retry("one_plans", user_prompt_str, purpose="生成小说方案")
            
            if not result:
                continue
                
            # 评估方案的新鲜度 - 使用新的评估格式
            freshness_assessment = self.quality_assessor.assess_freshness(result, "novel_plan")
            
            # 从新的格式中提取分数
            score_data = freshness_assessment.get("score", {})
            freshness_score = score_data.get("total", 0)
            core_concept_novelty = score_data.get("core_concept_novelty", 0)
            system_innovation = score_data.get("system_innovation", 0)
            market_scarcity = score_data.get("market_scarcity", 0)
            
            print(f"  🆕 方案新鲜度评分: {freshness_score:.1f}/10")
            print(f"  📊 核心设定新颖性: {core_concept_novelty:.1f}/4")
            print(f"  📊 系统创新性: {system_innovation:.1f}/3") 
            print(f"  📊 市场稀缺性: {market_scarcity:.1f}/3")
            
            # 显示评估结果
            analysis = freshness_assessment.get("analysis", {})
            verdict = freshness_assessment.get("verdict", "未知")
            suggestions = freshness_assessment.get("suggestions", [])
            
            print(f"  📈 综合判定: {verdict}")
            
            # 显示分析摘要
            if analysis.get("core_concept_novelty"):
                print(f"  💡 核心设定分析: {analysis['core_concept_novelty'][:100]}...")
            
            # 显示改进建议
            if suggestions:
                print(f"  💡 改进建议: {suggestions[0]}")
                
            # 检查是否存在复杂设定问题
            complexity_issues = self._check_setting_complexity(result)
            if complexity_issues:
                print(f"  ⚠️ 检测到复杂设定问题: {', '.join(complexity_issues)}")
                freshness_score = max(0, freshness_score - 2)  # 复杂设定扣分
            
            # 如果新鲜度达标，使用该方案
            if freshness_score >= 8.5:  # 稍微降低阈值，更注重故事性
                print(f"  ✅ 方案新鲜度达标")
                break
            else:
                print(f"  🔄 方案新鲜度不足，尝试优化...")
                
                # 先尝试优化，如果优化失败再重新生成
                optimization_params = {
                    "quality_assessment": {"overall_score": 8.5},
                    "freshness_assessment": freshness_assessment,
                    "complexity_issues": complexity_issues,
                    "optimization_reason": f"新鲜度{freshness_score:.1f}低于8.5分，或存在复杂设定问题"
                }
                
                optimized_result = self.quality_assessor.optimize_novel_plan(result, optimization_params)
                if optimized_result:
                    # 重新评估优化后的新鲜度
                    new_freshness = self.quality_assessor.assess_freshness(optimized_result, "novel_plan")
                    new_score_data = new_freshness.get("score", {})
                    new_score = new_score_data.get("total", 0)
                    print(f"  🆕 优化后新鲜度: {new_score:.1f}/10")
                    
                    if new_score >= 7.0:
                        print(f"  ✅ 优化成功，新鲜度达标")
                        result = optimized_result
                        break
                    else:
                        print(f"  ⚠️ 优化后新鲜度仍不足，继续重新生成...")
                
                # 如果优化失败或优化后仍不达标，更新提示词重新生成
                if suggestions:
                    first_suggestion = suggestions[0]
                else:
                    first_suggestion = "增加代入感和沉浸感，避免复杂设定"
                
                # 添加复杂设定警告
                complexity_text = ""
                if complexity_issues:
                    complexity_text = f"避免以下复杂设定: {', '.join(complexity_issues)}。"
                
                user_prompt["创新要求"] = f"必须创新！{complexity_text}要求: {first_suggestion}。重点在于有趣的故事和真实的情感。"
        
        if result:
            result = self._ensure_main_character_in_content(result, "one_plans")
            # 记录最终新鲜度评分
            if 'freshness_assessment' not in locals():
                freshness_assessment = self.quality_assessor.assess_freshness(result, "novel_plan")
                score_data = freshness_assessment.get("score", {})
                freshness_score = score_data.get("total", 0)
            
            result["freshness_score"] = freshness_score
            result["freshness_assessment"] = freshness_assessment
            
            # 添加代入感评估
            immersion_score = self._assess_immersion_level(result)
            result["immersion_score"] = immersion_score
            print(f"  💫 代入感评分: {immersion_score:.1f}/10")
        
        return result

    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析 - 增加新鲜度评估"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        # 强调创新要求
        user_prompt += "\n\n【创新要求】请提供有深度的市场分析，避免泛泛而谈，挖掘独特的市场切入点"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        
        if result:
            # 应用新的评估逻辑（包含新鲜度检查）
            result = self._assess_and_optimize_content(result, "market_analysis", "市场分析")
        
        return result

    def generate_core_worldview(self, novel_title: str, novel_synopsis: str, selected_plan: Dict, market_analysis: Dict) -> Optional[Dict]:
        """生成核心世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        # 从selected_plan中提取核心设定
        core_settings = selected_plan.get("core_settings", {})
        story_development = selected_plan.get("story_development", {})
        
        # 提取核心设定信息
        world_background = core_settings.get("world_background", "")
        golden_finger = core_settings.get("golden_finger", "")
        core_selling_points = core_settings.get("core_selling_points", [])
        
        # 提取故事发展信息
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
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观构建")
        
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, market_analysis: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计 - 使用优化后的提示词结构，强调生活化和灵动性"""
        print("=== 步骤5: 设计主要角色 ===")
        
        main_character_name = custom_main_character_name or self.custom_main_character_name
        
        # 从选定方案中提取核心设定
        core_settings = selected_plan.get("core_settings", {})
        story_development = selected_plan.get("story_development", {})
        
        # 构建优化后的提示词 - 强调生活化和灵动性
        context = f"""
    ## 1. 小说核心设定 (STORY_BLUEPRINT)

    *   **世界观背景**: {core_settings.get("world_background", "NA")}
    *   **金手指/系统**: {core_settings.get("golden_finger", "NA")}
    *   **核心爽点/卖点**: {', '.join(core_settings.get("core_selling_points", ["NA", "NA", "NA"])) if isinstance(core_settings.get("core_selling_points"), list) else core_settings.get("core_selling_points", "NA")}
    *   **主角定位**: {story_development.get("protagonist_position", "NA")}
    *   **主线脉络**: {story_development.get("main_plot", ["NA", "NA", "NA"]) if isinstance(story_development.get("main_plot"), list) else story_development.get("main_plot", "NA")}

    ## 2. 角色设计要求 (DESIGN_REQUIREMENTS)

    *   **主角姓名**: {main_character_name or "请根据主角定位生成合适的中文名字"}
    *   **核心配角列表**: 
        *   角色功能: 引导者与支持者
        *   角色功能: 辅助与补充者  
        *   角色功能: 竞争与参照者
        *   角色功能: 主要敌对势力代表

    ## 3. 【重要】角色设计原则

    ### 生活化要求：
    - **避免模板化**: 每个角色都要有独特的生活细节、小习惯、口头禅
    - **情感层次**: 展现角色内心的矛盾、脆弱和复杂性
    - **日常真实**: 加入吃饭、睡觉、闲聊等生活场景，让角色像真人一样生活

    ### 灵动性要求：
    - **意外互动**: 角色关系要有出人意料却又合理的发展
    - **成长变化**: 展现角色在互动中的相互影响和改变
    - **幽默时刻**: 适当的幽默和轻松时刻，让角色更亲切

    ### 具体示例：
    - ✅ 好的设计："主角有起床气，每天早上要喝特定茶才能清醒"
    - ✅ 好的设计："反派其实怕黑，这个弱点在关键时刻暴露"
    - ✅ 好的设计："两个死对头因为共同爱好意外成为朋友"
    - ❌ 坏的设计："主角完美无缺，没有任何生活习惯"
    - ❌ 坏的设计："角色关系一成不变，没有发展"

    ## 4. 创新要求
    - 角色设计应避免脸谱化，追求独特性和深度
    - **配角名字必须严格符合世界观背景**，避免使用常见固定名字
    - 每个配角都要有自己的生活、目标和困境
    - 角色互动要自然生动，有火花和化学反应
    """
        
        if main_character_name:
            print(f"  ✓ 角色设计使用主角名字: {main_character_name}")
        else:
            print("  🔍 将由AI根据世界观生成主角名字")
        
        result = self.api_client.generate_content_with_retry("character_design", context, purpose="角色设计")
        
        if result:
            result = self._assess_and_optimize_content(result, "character_design", "角色设计")
            if main_character_name:
                result = self.ensure_main_character_name(result, main_character_name)
        
        return result

    def _generate_highlight_scene_snippet(self, scene_brief: str, character_design: Dict, emotional_focus: str, writing_style_guide: Dict) -> Optional[str]:
        """
        通过 generate_content_with_retry 调用“导演”角色Prompt，生成场景片段。
        【已修改】：现在会接收并遵循 writing_style_guide。
        """
        print("  🎬 [API Call] 正在调用“名场面导演”模块...")

        # 1. 准备角色信息
        involved_chars_prompt_parts = []
        main_char = character_design.get("main_character", {})
        if main_char:
            char_name = main_char.get("name", "主角")
            soul_matrix = main_char.get("soul_matrix", [])
            involved_chars_prompt_parts.append(f"主角 [{char_name}] 的核心性格-行为: {json.dumps(soul_matrix, ensure_ascii=False, indent=2)}")

        important_chars = character_design.get("important_characters", [])
        if important_chars:
            first_sidekick = important_chars[0] 
            char_name = first_sidekick.get("name", "配角")
            soul_matrix = first_sidekick.get("soul_matrix", [])
            involved_chars_prompt_parts.append(f"配角 [{char_name}] 的核心性格-行为: {json.dumps(soul_matrix, ensure_ascii=False, indent=2)}")
        
        involved_chars_str = "\n".join(involved_chars_prompt_parts)

        # 【新增】: 将写作风格指南格式化，注入到Prompt中
        style_guide_prompt_part = ""
        if writing_style_guide:
            style_guide_prompt_part = f"""
### 3. 写作风格指南 (必须严格遵守！)
*   **核心风格**: {writing_style_guide.get('core_style', '默认')}
*   **语言特点**: {writing_style_guide.get('language_characteristics', {})}
*   **叙事技巧**: {writing_style_guide.get('narration_techniques', {})}
*   **关键原则**: {', '.join(writing_style_guide.get('key_principles', []))}

请确保你生成的场景片段严格符合上述写作风格，与小说整体基调保持一致。
"""

        # 2. 构建将要传递给 prompt 的 context 字符串
        director_context = f"""
## [CONTEXT] ##

### 1. 场景简报
*   **情境**: {scene_brief}
*   **情绪焦点**: {emotional_focus}

### 2. 角色核心设定
{involved_chars_str}
{style_guide_prompt_part}
"""
        try:
            # 3. API调用部分无需改变
            result = self.api_client.generate_content_with_retry(
                "highlight_scene_snippet",
                director_context,
                purpose="生成高光场景片段"
            )

            # 4. 解析部分无需改变
            if result and isinstance(result, dict):
                scene_snippet = result.get("scene_snippet")
                if scene_snippet and isinstance(scene_snippet, str) and len(scene_snippet.strip()) > 50:
                    print("  ✅ “名场面导演”成功生成【风格一致的】场景片段。")
                    return scene_snippet.strip()
                else:
                    print("  ⚠️ “名场面导演”返回的JSON中snippet为空或过短。")
                    return None
            else:
                print(f"  ❌ “名场面导演”返回结果格式错误，期望是字典但收到了: {type(result)}")
                return None

        except Exception as e:
            print(f"  ❌ 在调用“名场面导演”模块时发生异常: {e}")
            return None

    def ensure_main_character_name(self, character_design: Dict, custom_name: str) -> Dict:
        """确保角色设计中使用正确的主角名字"""
        if "main_character" in character_design and "name" in character_design["main_character"]:
            original_name = character_design["main_character"]["name"]
            if original_name != custom_name:
                print(f"⚠️  将主角名字从 '{original_name}' 改为 '{custom_name}'")
                character_design["main_character"]["name"] = custom_name
                character_design["main_character"]["original_name"] = original_name
        
        return character_design

    def _assess_and_optimize_content(self, content: Dict, content_type: str, original_purpose: str) -> Dict:
        """修正版内容评估和优化 - 支持小说方案优化"""
        if not content or not hasattr(self, 'quality_assessor') or self.quality_assessor is None:
            return content
        
        print(f"  🔍 评估{original_purpose}...")
        
        try:
            # 1. 质量评估（所有内容类型都需要）
            quality_assessment = None
            if content_type == "market_analysis":
                quality_assessment = self.quality_assessor.assess_market_analysis_quality(content)
            elif content_type == "writing_plan":
                quality_assessment = self.quality_assessor.assess_writing_plan_quality(content)
            elif content_type == "core_worldview":
                quality_assessment = self.quality_assessor.assess_core_worldview_quality(content)
            elif content_type == "character_design":
                quality_assessment = self.quality_assessor.assess_character_design_quality(content)
            elif content_type == "novel_plan":
                quality_assessment = self.quality_assessor.assess_novel_plan_quality(content)
            
            if not quality_assessment:
                return content
            
            quality_score = quality_assessment.get("overall_score", 0)
            print(f"  {original_purpose}质量评估: {quality_score:.1f}/10")
            
            # 2. 新鲜度评估（只有非章节内容需要）
            freshness_score = 10.0  # 章节内容默认满分，不评估新鲜度
            freshness_assessment = {}
            should_optimize = False
            reason = ""
            
            if content_type != "chapter_content":  # 非章节内容需要新鲜度评估
                freshness_assessment = self.quality_assessor.assess_freshness(content, content_type)
                
                # 从新的格式中提取分数
                score_data = freshness_assessment.get("score", {})
                freshness_score = score_data.get("total", 8.0)
                
                print(f"  {original_purpose}新鲜度评估: {freshness_score:.1f}/10")
                
                # 显示详细分数
                core_concept_novelty = score_data.get("core_concept_novelty", 0)
                system_innovation = score_data.get("system_innovation", 0)
                market_scarcity = score_data.get("market_scarcity", 0)
                
                print(f"  📊 核心设定新颖性: {core_concept_novelty:.1f}/4")
                print(f"  📊 系统创新性: {system_innovation:.1f}/3")
                print(f"  📊 市场稀缺性: {market_scarcity:.1f}/3")
                
                # 显示评估结果
                verdict = freshness_assessment.get("verdict", "未知")
                print(f"  📈 综合判定: {verdict}")
                
                # 综合优化决策（质量+新鲜度）
                should_optimize, reason = self.quality_assessor.should_optimize_comprehensive(
                    {"overall_score": quality_score, "freshness_score": freshness_score},
                    content_type
                )
            else:
                # 章节内容只基于质量评估
                should_optimize, reason = self.quality_assessor.should_optimize_comprehensive(
                    {"overall_score": quality_score},
                    content_type
                )
            
            # 3. 优化决策
            if should_optimize:
                print(f"  🔧 进行{original_purpose}优化: {reason}")
                
                # 准备优化参数
                optimization_params = {
                    "quality_assessment": quality_assessment,
                    "overall_score": quality_score,
                    "optimization_reason": reason
                }
                
                # 非章节内容添加新鲜度评估
                if content_type != "chapter_content":
                    optimization_params["freshness_assessment"] = freshness_assessment
                    optimization_params["freshness_score"] = freshness_score
                
                optimized_content = None
                #if content_type == "market_analysis":市场分析不需要优化
                #    optimized_content = self.quality_assessor.optimize_market_analysis(content, optimization_params)
                #el
                if content_type == "writing_plan":
                    optimized_content = self.quality_assessor.optimize_writing_plan(content, optimization_params)
                elif content_type == "core_worldview":
                    optimized_content = self.quality_assessor.optimize_core_worldview(content, optimization_params)
                elif content_type == "character_design":
                    optimized_content = self.quality_assessor.optimize_character_design(content, optimization_params)
                elif content_type == "novel_plan":
                    optimized_content = self.quality_assessor.optimize_novel_plan(content, optimization_params)
                
                if optimized_content:
                    print(f"  ✅ {original_purpose}优化完成")
                    return optimized_content
                else:
                    print(f"  ⚠️ {original_purpose}优化失败，使用原内容")
            
            return content
        
        except Exception as e:
            print(f"  ⚠️ 评估过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return content

    # ==================== vvv 全新、完整的 generate_chapter_content_for_novel 函数 vvv ====================
    
    def generate_chapter_content_for_novel(self, chapter_number: int, novel_data: Dict, context: GenerationContext = None) -> Optional[Dict]:
        """
        为小说生成章节内容 - 整合参数准备和内容生成 (已增加健壮的章节级重试机制)
        """
        print(f"🎬 开始生成第{chapter_number}章内容...")
    
        # ==================== 新增：章节级重试循环 ====================
        MAX_CHAPTER_RETRIES = 5  # 为一整个章节设置最多3次重试机会
        RETRY_WAIT_SECONDS = 20  # 每次重试前等待20秒，给API和网络缓冲时间
    
        for attempt in range(MAX_CHAPTER_RETRIES):
            # 每次循环都打印尝试次数
            if attempt > 0:
                print(f"  - 章节生成失败，将在 {RETRY_WAIT_SECONDS} 秒后进行第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次重试...")
                time.sleep(RETRY_WAIT_SECONDS)
            
            print(f"  🔄 第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次尝试生成第 {chapter_number} 章...")
    
            failure_reason = None
            failure_details = {}
    
            try:
                # --- 核心生成逻辑被包裹在循环内部 ---
                # 仅在第一次尝试时初始化世界状态
                if chapter_number == 1 and attempt == 0:
                    print("🔄 初始化世界状态...")
                    self.quality_assessor.initialize_world_state_from_novel_data(novel_data["novel_title"], novel_data)
    
                # 存储上下文供后续使用
                novel_data['_current_generation_context'] = context
    
                # 准备章节参数
                chapter_params = self._prepare_chapter_params(chapter_number, novel_data)
    
                if not chapter_params or not self._validate_chapter_params(chapter_params):
                    failure_reason = "参数准备失败"
                    failure_details = {"missing_params": [key for key, val in chapter_params.items() if not val]}
                    print(f"  ❌ 第{chapter_number}章参数准备失败。")
                    continue  # 进入下一次重试
    
                print(f"  ✅ 第{chapter_number}章所有参数验证通过。")
                print(f"  🚀 开始调用核心内容生成...")
                chapter_data = self.generate_chapter_content(chapter_params)
    
                if not chapter_data:
                    failure_reason = "核心内容生成失败 (generate_chapter_content返回None)"
                    failure_details = {"step": "generate_chapter_content"}
                    print(f"  ❌ 第{chapter_number}章核心内容生成失败。")
                    continue  # 进入下一次重试
                
                # --- 后续的质量评估、优化等逻辑保持不变 ---
                print(f"  ✨ 核心内容生成完毕，开始后处理...")
    
                # 确保章节标题唯一性
                chapter_data = self._handle_chapter_title_uniqueness(chapter_data, chapter_number, novel_data)
    
                # 新增：记录情绪信息
                emotional_guidance = self._get_emotional_guidance_for_chapter(chapter_number, novel_data)
                chapter_data["emotional_design"] = {
                    "planned_focus": emotional_guidance.get("current_emotional_focus", ""),
                    "target_intensity": emotional_guidance.get("target_intensity", "中"),
                    "is_turning_point": emotional_guidance.get("is_emotional_turning_point", False)
                }
    
                # 质量评估
                print(f"  📊 开始质量评估...")
                assessment = self.quality_assessor.quick_assess_chapter_quality(
                    chapter_data.get("content", ""),
                    chapter_data.get("chapter_title", ""),
                    chapter_number,
                    novel_data["novel_title"],
                    chapter_params.get("previous_chapters_summary", ""),
                    chapter_data.get("word_count", 0),
                    novel_data=novel_data
                )
                
                score = assessment.get("overall_score", 0)
                chapter_data["quality_score"] = score
                chapter_data["quality_assessment"] = assessment
                print(f"  质量评分: {score:.1f}分")
    
                # 根据质量决定是否优化
                optimize_needed, optimize_reason = self._should_optimize_based_on_config(assessment)
                
                if optimize_needed:
                    print(f"  🔧 进行优化: {optimize_reason}")
                    
                    max_optimization_retries = 2
                    optimized_data = None
                    
                    for retry in range(max_optimization_retries):
                        try:
                            optimized_data = self.quality_assessor.optimize_chapter_content({
                                "assessment_results": json.dumps(assessment, ensure_ascii=False),
                                "original_content": chapter_data.get("content", ""),
                                "priority_fix_1": assessment.get("weaknesses", [""])[0] if assessment.get("weaknesses") else "提升质量",
                                "priority_fix_2": assessment.get("weaknesses", [""])[1] if len(assessment.get("weaknesses", [])) > 1 else "",
                                "priority_fix_3": assessment.get("weaknesses", [""])[2] if len(assessment.get("weaknesses", [])) > 2 else "",
                                "novel_title": novel_data["novel_title"],
                                "chapter_number": chapter_number,
                                "chapter_title": chapter_data.get("chapter_title", ""),
                                "writing_style_guide": novel_data.get("writing_style_guide", {})
                            })
                            
                            if optimized_data and optimized_data.get("content"):
                                print(f"  ✅ 第{retry+1}次优化成功")
                                break
                            else:
                                print(f"  ⚠️ 第{retry+1}次优化失败，返回空结果")
                                optimized_data = None
                                
                        except Exception as e:
                            print(f"  ❌ 第{retry+1}次优化过程异常: {e}")
                            optimized_data = None
                    
                    if optimized_data and optimized_data.get("content"):
                        chapter_data["content"] = optimized_data.get("content")
                        chapter_data["word_count"] = len(optimized_data.get("content", ""))
                        chapter_data["optimization_info"] = {
                            "optimized": True,
                            "original_score": score,
                            "retry_count": retry + 1
                        }
                        
                        new_assessment = self.quality_assessor.quick_assess_chapter_quality(
                            chapter_data.get("content", ""),
                            chapter_data.get("chapter_title", ""),
                            chapter_number,
                            novel_data["novel_title"],
                            chapter_params.get("previous_chapters_summary", ""),
                            chapter_data.get("word_count", 0),
                            novel_data=novel_data
                        )
                        new_score = new_assessment.get("overall_score", 0)
                        print(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{new_score - score:+.1f}分)")
                        chapter_data["quality_score"] = new_score
                        chapter_data["quality_assessment"] = new_assessment
                    else:
                        print(f"  ⚠️ 所有优化尝试均失败，保持原内容")
                        chapter_data["optimization_info"] = {
                            "optimized": False,
                            "reason": "优化过程失败",
                            "original_score": score
                        }
                else:
                    print(f"  ✓ {optimize_reason}")
                    chapter_data["quality_assessment"] = assessment
                
                # AI俏皮开场白
                if chapter_number == 1:
                    try:
                        chapter_data = self.novel_generator._add_ai_spicy_opening_to_first_chapter(
                            chapter_data, novel_data.get("novel_title", ""), novel_data.get("novel_synopsis", ""), novel_data.get("category", "默认")
                        )
                    except Exception as e:
                        print(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")
    
                # ==================== 成功！返回章节数据并跳出重试循环 ====================
                print(f"🎉 第 {chapter_number} 章在第 {attempt + 1} 次尝试中生成成功！")
                return chapter_data
    
            except Exception as e:
                # 捕获所有异常，包括你遇到的 AttributeError
                failure_reason = f"生成过程异常: {str(e)}"
                failure_details = {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "chapter_number": chapter_number,
                    "traceback": self._get_traceback_info()
                }
                print(f"  ❌ 第{chapter_number}章在第 {attempt + 1} 次尝试中出现严重异常: {e}")
                import traceback
                traceback.print_exc()
                # 异常发生后，循环会继续，进入下一次重试
    
        # ==================== 如果所有重试都失败了 ====================
        print(f"🔥🔥🔥 严重错误: 第 {chapter_number} 章在 {MAX_CHAPTER_RETRIES} 次尝试后彻底失败！")
        # 保存最终的失败记录
        self._save_chapter_failure(novel_data, chapter_number, failure_reason or "未知原因导致所有重试失败", failure_details)
        return None  # 彻底失败后，返回 None
    
    # ==================== ^^^ 全新、完整的 generate_chapter_content_for_novel 函数 ^^^ ====================

    def _get_traceback_info(self) -> str:
        """获取当前异常的堆栈信息"""
        import traceback
        import io
        f = io.StringIO()
        traceback.print_exc(file=f)
        return f.getvalue()

    def _get_plot_direction_for_chapter(self, chapter_number: int, total_chapters: int) -> Dict[str, str]:
        """根据章节位置确定情节发展方向"""
        progress_ratio = chapter_number / total_chapters
        
        if progress_ratio <= 0.1:
            return {
                "plot_direction": "引入核心冲突，建立主角初始状态，埋下故事伏笔",
                "main_plot_progress": "展现世界观基础，介绍主角背景，引发初始事件",
                "character_development_focus": "展示主角性格特点，建立读者共鸣"
            }
        elif progress_ratio <= 0.3:
            return {
                "plot_direction": "主角开始成长，遇到重要盟友和敌人，小冲突不断",
                "main_plot_progress": "推进主线任务，引入重要支线，建立势力关系",
                "character_development_focus": "角色能力提升，人际关系深化"
            }
        elif progress_ratio <= 0.7:
            return {
                "plot_direction": "主要冲突激化，重大转折发生，主角面临重大挑战",
                "main_plot_progress": "核心矛盾爆发，关键事件发生，故事走向转折",
                "character_development_focus": "角色经历重大变化，价值观可能重塑"
            }
        elif progress_ratio <= 0.9:
            return {
                "plot_direction": "冲突走向解决，各条线索开始收束",
                "main_plot_progress": "准备最终决战，解决主要矛盾",
                "character_development_focus": "角色完成最终成长，准备迎接结局"
            }
        else:
            return {
                "plot_direction": "故事圆满收尾，交代各角色最终命运",
                "main_plot_progress": "解决所有矛盾，完成故事主线",
                "character_development_focus": "展示角色最终状态和未来展望"
            }

    def _generate_previous_chapters_summary(self, current_chapter: int, novel_data: Dict) -> str:
        """生成前情提要"""
        if current_chapter == 1:
            return "这是开篇第一章，需要建立故事基础。"
        
        # 获取上一章的详细结尾信息
        previous_ending_info = self._get_previous_chapter_ending(current_chapter, novel_data)
        
        # 尝试加载最近10章的摘要信息
        summary_parts = []
        for i in range(max(1, current_chapter-10), current_chapter):
            chapter_data = self._load_chapter_content(i, novel_data)
            
            if chapter_data:
                chapter_summary = chapter_data.get('plot_advancement') or chapter_data.get('summary')
                if not chapter_summary:
                    chapter_summary = "（该章摘要信息缺失）"
                summary_line = f"第{i}章《{chapter_data.get('chapter_title', '未知标题')}》: {chapter_summary}"
                summary_parts.append(summary_line)
        
        if summary_parts:
            return f"{previous_ending_info}\n\n最近章节摘要：\n" + "\n".join(summary_parts)
        else:
            return previous_ending_info

    def _get_previous_chapter_ending(self, current_chapter: int, novel_data: Dict) -> str:
        """获取上一章的结尾内容和悬念，用于衔接"""
        if current_chapter <= 1:
            print(f"  📖 第{current_chapter}章是开篇第一章，无需获取前一章结尾")
            return "这是开篇第一章，需要建立故事基础。"
        
        prev_chapter_data = self._load_chapter_content(current_chapter - 1, novel_data)
        
        if prev_chapter_data:
            chapter_summary = prev_chapter_data.get("plot_advancement") or prev_chapter_data.get("key_events", "")
            chapter_ending = self._extract_content_ending(prev_chapter_data.get("content", ""))
            next_chapter_hook = prev_chapter_data.get("next_chapter_hook", "")
            
            # 构建详细的上一章结尾描述
            summary_description = f"上一章核心情节: {chapter_summary}" if chapter_summary else "上一章具体情节内容暂不可用。"
            ending_description = f"上一章结尾: {chapter_ending}" if chapter_ending else ""
            hook_description = f"上一章设置的悬念: {next_chapter_hook}" if next_chapter_hook else "上一章未明确设置悬念。"
            
            result_parts = [summary_description]
            if ending_description:
                result_parts.append(ending_description)
            if hook_description:
                result_parts.append(hook_description)
                
            result = "\n\n".join(result_parts)
            print(f"  ✅ 第{current_chapter-1}章结尾信息组合成功，长度: {len(result)}字符")
            return result
        
        error_msg = f"第{current_chapter-1}章的内容无法加载，请确保该章已成功生成并保存。"
        print(f"  ❌❌ {error_msg}")
        return error_msg

    def _load_chapter_content(self, chapter_number: int, novel_data: Dict) -> Optional[Dict]:
        """加载章节内容"""
        if chapter_number in novel_data.get("generated_chapters", {}):
            return novel_data["generated_chapters"][chapter_number]
        return None

    def _extract_content_ending(self, content: str) -> str:
        """提取内容结尾部分"""
        content_length = len(content)
        print(f"  📏 章节内容长度: {content_length}字符")
        
        # 尝试多种方法提取结尾
        extraction_methods = [
            self._extract_by_paragraphs,
            self._extract_by_sentences,
            self._extract_by_length
        ]
        
        for method in extraction_methods:
            try:
                ending = method(content)
                if ending and len(ending.strip()) > 50:
                    print(f"  ✅ 成功提取结尾: {ending[:100]}...")
                    return ending
            except Exception as e:
                print(f"  ⚠️  方法 '{method.__name__}' 提取失败: {e}")
                continue
        
        # 所有方法都失败，使用最后200字作为备选
        fallback_ending = content[-200:] if content_length > 200 else content
        print(f"  ⚠️  所有提取方法失败，使用备选结尾: {fallback_ending[:100]}...")
        return fallback_ending

    def _extract_by_paragraphs(self, content: str) -> str:
        """通过段落分割提取结尾"""
        paragraph_separators = ['\n\n', '\n', '。', '！', '？']
        
        for separator in paragraph_separators:
            paragraphs = [p.strip() for p in content.split(separator) if p.strip()]
            if len(paragraphs) >= 2:
                ending_paragraphs = paragraphs[-2:] if len(paragraphs) >= 3 else paragraphs[-1:]
                ending = separator.join(ending_paragraphs)
                if len(ending) > 50:
                    return ending
        
        return content[-300:] if len(content) > 300 else content

    def _extract_by_sentences(self, content: str) -> str:
        """通过句子分割提取结尾"""
        sentence_endings = ['。', '！', '？', '……', '」', '」']
        
        last_end_pos = -1
        for i in range(len(content)-1, max(0, len(content)-500), -1):
            if content[i] in sentence_endings:
                last_end_pos = i
                break
        
        if last_end_pos != -1:
            sentences = []
            sentence_count = 0
            for i in range(last_end_pos, max(0, last_end_pos-500), -1):
                if content[i] in sentence_endings and i != last_end_pos:
                    sentence_count += 1
                    if sentence_count >= 2:
                        return content[i+1:last_end_pos+1]
            
            return content[max(0, last_end_pos-200):last_end_pos+1]
        
        return content[-200:] if len(content) > 200 else content

    def _extract_by_length(self, content: str) -> str:
        """根据内容长度按比例提取结尾"""
        content_length = len(content)
        
        if content_length > 3000:
            return content[-500:]
        elif content_length > 1500:
            return content[-300:]
        else:
            return content[-200:]

    def _get_chapter_connection_note(self, chapter_number: int) -> str:
        """根据章节位置生成衔接提示"""
        if chapter_number == 1:
            return "这是开篇第一章，需要建立故事基础，吸引读者继续阅读。"
        else:
            return f"本章必须自然承接第{chapter_number-1}章的结尾，特别是要处理好上一章设置的悬念，确保情节连贯性。"

    def _get_main_character_instruction(self, novel_data: Dict) -> str:
        """获取主角名字指令"""
        if self.custom_main_character_name:
            return f"\n【重要提示】主角的名字必须是: {self.custom_main_character_name}"
        return ""

    def _validate_chapter_params(self, params: Dict) -> bool:
        """验证章节参数是否完整"""
        required = [
            'chapter_number', 'novel_title', 'novel_synopsis', 'plot_direction',
            'foreshadowing_guidance'
        ]
        for key in required:
            if key not in params or not params[key]:
                print(f"❌ 参数验证失败: 缺少 {key}")
                return False
        return True

    def _handle_chapter_title_uniqueness(self, chapter_data: Dict, chapter_number: int, novel_data: Dict) -> Dict:
        """处理章节标题唯一性 - 修复版本"""
        original_title = chapter_data.get("chapter_title", "")
        if not original_title:
            return chapter_data
        
        # 检查是否重复
        is_unique, duplicate_chapter = self._is_chapter_title_unique(original_title, chapter_number, novel_data)
        if is_unique:
            novel_data["used_chapter_titles"].add(original_title)
            chapter_data["title_was_changed"] = False
            return chapter_data
        
        print(f"⚠️  章节标题重复: '{original_title}' 与第{duplicate_chapter}章重复，正在生成新标题...")
        
        # 使用智能重命名
        new_title = self._generate_unique_chapter_title(original_title, chapter_number, novel_data)
        
        if new_title != original_title:
            # 只更新章节标题，保持其他结构不变
            chapter_data["chapter_title"] = new_title
            chapter_data["title_was_changed"] = True
            chapter_data["original_title"] = original_title
            novel_data["used_chapter_titles"].add(new_title)
            print(f"✓ 使用新标题: '{new_title}'")
        
        return chapter_data

    def _is_chapter_title_unique(self, title: str, exclude_chapter: int, novel_data: Dict) -> Tuple[bool, Optional[int]]:
        """检查章节标题是否唯一，返回是否唯一和重复的章节号"""
        for chapter_num, chapter_data in novel_data.get("generated_chapters", {}).items():
            if exclude_chapter and chapter_num == exclude_chapter:
                continue
            existing_title = chapter_data.get("chapter_title", "")
            if existing_title and existing_title == title:
                return False, chapter_num
        return True, None

    def _generate_unique_chapter_title(self, original_title: str, chapter_number: int, novel_data: Dict, retry_count: int = 0) -> str:
        """生成与主要事件关联的吸引人章节标题"""
        if retry_count >= 2:
            return self._generate_event_related_title(chapter_number, novel_data)
        
        # 获取当前章节的主要事件信息
        event_context = novel_data.get('_current_generation_context', {}).get('event_context', {})
        active_events = event_context.get('active_events', [])
        
        # 构建基于事件的标题提示词
        event_context_str = ""
        if active_events:
            current_event = active_events[0]  # 取当前主要事件
            event_name = current_event.get('name', '')
            event_goal = current_event.get('main_goal', '')
            event_context_str = f"\n当前主要事件: {event_name}\n事件目标: {event_goal}"
        
        title_prompt = f"""
    请为小说的第{chapter_number}章生成一个吸引人的章节标题。

    **要求**：
    1. 必须与当前主要事件相关：{event_context_str}
    2. 通俗易懂，让读者一眼就能理解本章重点
    3. 激发追读欲望，让人想知道后续发展
    4. 长度6-14字
    5. 避免与已有章节标题重复

    **标题风格示例**：
    - "危机四伏！神秘敌人现身"
    - "绝境突破！主角获得新能力"  
    - "惊天秘密！幕后黑手浮出水面"
    - "生死一线！最后的希望"
    - "意外转折！真相令人震惊"

    已有章节标题: {list(novel_data.get("used_chapter_titles", set()))[-5:]}

    请只返回标题文本，不要其他内容。
    """
        
        try:
            new_title = self.api_client.call_api('deepseek', "你是小说章节标题生成专家", title_prompt, 0.7, purpose="生成吸引人章节标题")
            if new_title and new_title.strip():
                new_title = new_title.strip().strip('"').strip("'").strip()
                new_title = re.sub(r'^["\']|["\']$', '', new_title)
                
                # 检查唯一性
                is_unique, _ = self._is_chapter_title_unique(new_title, chapter_number, novel_data)
                if is_unique and len(new_title) >= 4:
                    return new_title
                else:
                    return self._generate_unique_chapter_title(original_title, chapter_number, novel_data, retry_count + 1)
        except Exception as e:
            print(f"生成新标题失败: {e}")
        
        return self._generate_event_related_title(chapter_number, novel_data)

    def _generate_event_related_title(self, chapter_number: int, novel_data: Dict) -> str:
        """生成与事件相关的备选标题"""
        event_context = novel_data.get('_current_generation_context', {}).get('event_context', {})
        active_events = event_context.get('active_events', [])
        
        if active_events:
            event_name = active_events[0].get('name', '当前事件')
            # 基于事件名称生成标题变体
            event_templates = [
                f"{event_name}的惊人发展",
                f"{event_name}·危机时刻", 
                f"{event_name}·转折点",
                f"{event_name}·真相大白",
                f"{event_name}·最终对决"
            ]
            
            for title in event_templates:
                is_unique, _ = self._is_chapter_title_unique(title, chapter_number, novel_data)
                if is_unique:
                    return title
        
        # 默认标题
        return f"第{chapter_number}章 风云再起"

    def _generate_deterministic_title(self, original_title: str, chapter_number: int) -> str:
        """使用确定性方法生成标题"""
        base_title = re.sub(r'[（(].*[）)]', '', original_title).strip()
        
        alternatives = [
            f"{base_title}·新篇",
            f"{base_title}·风云再起",
            f"{base_title}·波澜再起",
            f"{base_title}·暗流涌动",
            f"{base_title}·转折时刻",
            f"{base_title}·命运交错",
            f"第{chapter_number}章 {base_title}",
            f"{base_title}（续）"
        ]
        
        for alt in alternatives:
            # 这里我们无法检查唯一性，但至少避免完全重复
            if alt != original_title:
                return alt
        
        return f"第{chapter_number}章 {base_title}"

    def _should_optimize_based_on_config(self, assessment: Dict) -> Tuple[bool, str]:
        """基于配置决定是否需要优化 - 使用统一标准"""
        score = assessment.get("overall_score", 0) 
        
        # 使用统一质量标准
        quality_threshold = self.quality_assessor.unified_quality_standards["optimization_thresholds"]["chapter_content"]
        
        # 强制优化阈值
        if score < quality_threshold:
            return True, f"评分{score:.1f}低于优化阈值{quality_threshold}分，需要优化"
        
        # 检查严重一致性问题的存在
        consistency_issues = assessment.get("consistency_issues", [])
        severe_issues = [issue for issue in consistency_issues if issue.get('severity') == '高']
        
        if severe_issues:
            for issue in severe_issues:
                print(f"  - {issue}")
            return True, f"存在{len(severe_issues)}个严重一致性问题，需要优化"
        
        return False, f"评分{score:.1f}良好，跳过优化"

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节内容 - 严格三步法：先设计方案，再生成内容，最后专项优化"""
        print(f"  🔍 进入generate_chapter_content方法，参数类型: {type(chapter_params)}")
        
        required_keys = ['chapter_number', 'total_chapters', 'novel_title', 'novel_synopsis', 
                        'worldview_info', 'character_info', 'event_driven_guidance','foreshadowing_guidance',
                        'previous_chapters_summary', 'main_plot_progress', 'plot_direction',
                        'chapter_connection_note']
        
        # 参数验证和修复逻辑
        missing_keys = [key for key in required_keys if key not in chapter_params]
        if missing_keys:
            print(f"  ⚠️ 缺少必要参数: {missing_keys}")
            for key in missing_keys:
                if key == 'event_driven_guidance':
                    chapter_params[key] = "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"
                elif key == 'foreshadowing_guidance':
                    chapter_params[key] = "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
                elif key == 'character_development_focus':
                    chapter_params[key] = "角色正常发展"
                else:
                    chapter_params[key] = "未提供"
        
        try:
            # 第一步：生成章节设计方案
            chapter_number = chapter_params['chapter_number']
            print(f"  📝 生成第{chapter_number}章设计方案...")
            chapter_design = self.generate_chapter_design(chapter_params)
            
            # 检查设计方案类型
            print(f"  🔍 设计方案类型: {type(chapter_design)}")
            if not chapter_design:
                print(f"  ❌ 第{chapter_number}章设计方案生成失败，终止生成")
                return None
            
            if not isinstance(chapter_design, dict):
                print(f"  ❌ 设计方案不是字典类型，而是: {type(chapter_design)}")
                print(f"     内容: {str(chapter_design)[:200]}...")
                return None
                
            # 第二步：根据设计方案生成内容，并加入重试机制
            max_retries = 3
            chapter_content = None
            
            for attempt in range(max_retries):
                print(f"  ✍️ 第{attempt + 1}次尝试生成第{chapter_number}章内容...")
                current_content = self.generate_chapter_content_from_design(chapter_params, chapter_design)
                
                # 检查生成内容的类型
                if current_content is None:
                    print(f"  ❌ 第{attempt + 1}次内容生成失败，返回None")
                    continue
                    
                if not isinstance(current_content, dict):
                    print(f"  ❌ 第{attempt + 1}次内容生成返回非字典类型: {type(current_content)}")
                    print(f"     内容: {str(current_content)[:200]}...")
                    if attempt == max_retries - 1:
                        print(f"  ❌ 达到最大重试次数，第{chapter_number}章生成失败")
                        return None
                    continue
                
                # 检查字数
                word_count = current_content.get("word_count", 0)
                content_length = len(current_content.get("content", ""))
                
                print(f"  📝 第{attempt + 1}次生成结果: {word_count}字 (内容长度: {content_length}字符)")
                
                # 保存当前生成的内容
                chapter_content = current_content
                
                # 如果字数达标，直接使用
                if content_length >= 1800:
                    print(f"  ✅ 字数达标: {word_count}字")
                    break
                
                # 【【【新增的清理步骤】】】
                # 在内容生成之后，优化之前，进行标记清理
                if chapter_content and 'content' in chapter_content and isinstance(chapter_content['content'], str):
                    content_with_markers = chapter_content['content']
                    if '[SCENE_BLOCK_START]' in content_with_markers:
                        print("  🧹 正在清理最终内容中的内部标记...")
                        
                        # 执行清理
                        cleaned_content = content_with_markers.replace('[SCENE_BLOCK_START]', '')
                        cleaned_content = cleaned_content.replace('[SCENE_BLOCK_END]', '')
                        
                        # 移除可能因替换产生的多余空行
                        cleaned_content = cleaned_content.strip()
                        
                        # 更新章节内容和字数统计
                        chapter_content['content'] = cleaned_content
                        chapter_content['word_count'] = len(cleaned_content)
                        print("  ✅ 内部标记已成功移除，正文已净化。")
                
                # 如果是最后一次尝试，使用当前内容
                if attempt == max_retries - 1:
                    print(f"  ❌ 达到最大重试次数，使用当前内容")
         
            # 第三步：专项优化 - 使用CHAPTER_REFINEMENT_PROMPT进行平台风格优化
            if chapter_content:
                print(f"  🎯 开始第{chapter_number}章专项优化...")
                #optimized_content = self.refine_chapter_content(chapter_content)
                
                #if optimized_content:
                #    print(f"  ✅ 第{chapter_number}章优化成功")
                #    return optimized_content
                #else:
                print(f"  ⚠️ 第{chapter_number}章优化失败，使用原始内容")
                return chapter_content
            else:
                print(f"  ❌ 第{chapter_number}章所有生成尝试均失败")
                return None
                
        except Exception as e:
            print(f"❌ 生成第{chapter_params['chapter_number']}章内容时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def refine_chapter_content(self, chapter_content: Dict) -> Dict:
        """
        使用CHAPTER_REFINEMENT_PROMPT对章节内容进行专项优化
        
        Args:
            chapter_content: 包含章节标题和内容的字典
            chapter_params: 包含章节编号等参数的字典
        
        Returns:
            更新后的章节内容，只修改content和word_count字段
        """
        try:
            # 从chapter_content中提取标题和内容
            chapter_title = chapter_content.get("chapter_title", "")
            original_content = chapter_content.get("content", "")
            original_word_count = chapter_content.get("word_count", 0)
            chapter_number = chapter_content.get("chapter_number", 0)
            
            # 构建用户提示词，明确要求保持字数稳定
            user_prompt = f"""
    请优化以下章节内容，特别注意保持字数稳定：

    ## 章节标题
    {chapter_title}

    ## 章节内容
    {original_content}

    ## 重要要求
    1. 优化内容质量，但保持字数在{original_word_count}字左右（±10%）
    2. 保持原有的情节发展和关键事件
    3. 按照系统提示的要求进行番茄风格优化
    4. 返回指定格式的JSON结果
    """
            
            print(f"  🎨 正在优化第{chapter_number}章: {chapter_title}")
            print(f"  📊 原始字数: {original_word_count}字")
            
            # 使用API进行优化，传入系统提示词和用户提示词
            optimized_result = self.api_client.generate_content_with_retry(
                "chapter_refinement", 
                user_prompt,
                purpose=f"优化第{chapter_number}章内容"
            )
            
            # 验证优化结果
            if self._validate_optimized_result(optimized_result):
                new_content = optimized_result.get("content", "")
                new_word_count = optimized_result.get("word_count", 0)
                score = optimized_result.get('quality_assessment', {}).get('overall_score', 'N/A')
                notes = optimized_result.get('quality_assessment', {}).get('refinement_notes', 'N/A')
                
                # 计算字数变化
                word_count_change = new_word_count - original_word_count
                change_percent = (word_count_change / original_word_count) * 100 if original_word_count > 0 else 0
                
                print(f"  ✅ 章节优化完成")
                print(f"  📊 优化后字数: {new_word_count}字 ({change_percent:+.1f}%)")
                print(f"  ⭐ 质量评分: {score}/10")
                
                if notes != 'N/A':
                    print(f"  📝 优化说明: {notes}")
                
                # 如果字数变化过大，给出警告但继续使用
                if abs(change_percent) > 20:
                    print(f"  ⚠️ 字数变化较大，建议检查内容完整性")
                
                # 只更新content和word_count字段，保留其他所有字段
                updated_content = chapter_content.copy()
                updated_content["content"] = new_content
                updated_content["word_count"] = new_word_count
                
                # 添加quality_assessment信息（如果不存在则创建）
                if "quality_assessment" not in updated_content:
                    updated_content["quality_assessment"] = {}
                
                # 更新质量评估信息
                updated_content["quality_assessment"].update({
                    "optimized": True,
                    "optimization_score": score,
                    "optimization_notes": notes
                })
                
                return updated_content
            else:
                print(f"  ⚠️ 优化结果验证失败，使用原始内容")
                return chapter_content  # 直接返回原始内容，不做任何修改
                
        except Exception as e:
            print(f"  ❌ 章节优化过程中出错: {e}")
            return chapter_content  # 出错时返回原始内容

    def _validate_optimized_result(self, result: Any) -> bool:
        """修复版优化结果验证 - 支持多种字段名"""
        if not result or not isinstance(result, dict):
            print(f"  ❌ 验证失败: 结果为空或不是字典类型")
            return False
        
        # 支持多种内容字段名
        content_fields = ["optimized_content", "content", "chapter_content"]
        content = None
        for field in content_fields:
            if field in result and result[field]:
                content = result[field]
                break
        
        if not content or not isinstance(content, str) or not content.strip():
            print(f"  ❌ 验证失败: 内容为空或无效")
            print(f"      可用字段: {list(result.keys())}")
            return False
        
        # 检查是否有足够的内容长度
        if len(content.strip()) < 500:  # 最小500字符
            print(f"  ❌ 验证失败: 内容过短 ({len(content)}字符)")
            return False
        
        print(f"  ✅ 优化结果验证通过: {len(content)}字符")
        return True

    def _create_fallback_content(self, chapter_title: str, content: str, word_count: int) -> Dict:
        """创建优化失败时的回退内容结构"""
        return {
            "chapter_title": chapter_title,
            "content": content,
            "word_count": word_count,
            "quality_assessment": {
                "overall_score": 0,
                "quality_verdict": "未优化",
                "refinement_notes": "优化过程失败，使用原始内容"
            }
        }

    def generate_chapter_design(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节详细设计方案 - 使用优化后的提示词模板"""
        # 提取情绪参数
        emotional_guidance = chapter_params.get("emotional_guidance", {})
        
        current_emotional_focus = emotional_guidance.get("current_emotional_focus", "")
        target_intensity = emotional_guidance.get("target_intensity", "中")
        is_turning_point = emotional_guidance.get("is_emotional_turning_point", False)
        event_guidance_str = chapter_params.get("event_driven_guidance", "")
        is_key_event = "对峙" in event_guidance_str or "高潮" in event_guidance_str or "冲突激化" in event_guidance_str
        
        highlight_scene_block = None

        if is_turning_point or is_key_event:
            scene_brief = f"本章的核心高潮场面：{emotional_guidance.get('key_scenes_design', '关键情节转折')}"
            try:
                character_info_dict = json.loads(chapter_params.get("character_info", "{}"))
            except json.JSONDecodeError:
                character_info_dict = {}

            # 【修改】: 从 chapter_params 中获取 writing_style_guide
            writing_style_guide = chapter_params.get("writing_style_guide", {})

            # 调用我们适配好的新方法
            snippet = self._generate_highlight_scene_snippet(
                scene_brief,
                character_info_dict,
                emotional_guidance.get("current_emotional_focus", ""),
                writing_style_guide
            )

            if snippet:
                print("  🛡️ 将场景片段封装为“不可篡改的场景模块”。")
                highlight_scene_block = f"\n[SCENE_BLOCK_START]\n{snippet}\n[SCENE_BLOCK_END]\n"
        is_break_chapter = emotional_guidance.get("is_emotional_break_chapter", False)
        break_activities = emotional_guidance.get("break_activities", [])
        target_reader_emotion = emotional_guidance.get("target_reader_emotion", "期待与投入")
        key_scenes_design = emotional_guidance.get("key_scenes_design", "根据情节自然发展")
        
        # 构建本章重点推进列表
        chapter_focus_points = [
            f"情绪发展: {current_emotional_focus} (强度: {target_intensity})",
            f"目标读者情绪: {target_reader_emotion}",
            f"关键场景: {key_scenes_design}"
        ]
        
        # 根据事件指导添加重点
        event_guidance = chapter_params.get("event_driven_guidance", "")
        if "活跃事件执行" in event_guidance:
            chapter_focus_points.append("执行当前活跃事件任务")
        
        if "情感填充事件" in event_guidance:
            chapter_focus_points.append("处理情感填充事件")
        
        # 构建小说基础设定JSON
        novel_settings = {
            "worldview": chapter_params.get("worldview_info", {}),
            "characters": chapter_params.get("character_info", {}),
            "writing_plan": chapter_params.get("stage_writing_plan", {}),
            "emotional_design": {
                "current_focus": current_emotional_focus,
                "target_intensity": target_intensity,
                "is_turning_point": is_turning_point,
                "is_break_chapter": is_break_chapter,
                "break_activities": break_activities,
                "target_reader_emotion": target_reader_emotion,
                "key_scenes": key_scenes_design
            }
        }
        
        # 从前情提要中提取关键信息
        previous_summary = chapter_params.get("previous_chapters_summary", "")
        previous_chapter_summary = ""
        previous_chapter_hook = ""
        
        # 尝试提取上一章核心情节和悬念
        if "上一章核心情节:" in previous_summary:
            parts = previous_summary.split("上一章核心情节:")
            if len(parts) > 1:
                previous_chapter_summary = parts[1].split("上一章结尾:")[0].strip() if "上一章结尾:" in parts[1] else parts[1].strip()
        
        if "上一章设置的悬念:" in previous_summary:
            parts = previous_summary.split("上一章设置的悬念:")
            if len(parts) > 1:
                previous_chapter_hook = parts[1].strip()
        
        # 如果提取失败，使用默认值
        if not previous_chapter_summary:
            previous_chapter_summary = "开篇章节，建立故事基础"
        if not previous_chapter_hook:
            previous_chapter_hook = "情节发展悬念"
        
        # 构建优化后的提示词
        design_prompt = f"""
    # 任务
    作为一名顶级的网络小说总编辑，请根据下方提供的【核心输入】和【背景资料】，为小说《{chapter_params.get("novel_title", "未知小说")}》的第 {chapter_params.get("chapter_number", 1)} 章，生成一份详尽、可执行的JSON格式"章节创作蓝图"。

    # 核心输入
    *   **章节编号**: {chapter_params.get("chapter_number", 1)}
    *   **本章重点推进**: 
        - {chapter_focus_points[0]}
        - {chapter_focus_points[1] if len(chapter_focus_points) > 1 else "推进主线情节发展"}
        - {chapter_focus_points[2] if len(chapter_focus_points) > 2 else "保持角色一致性"}
        - {chapter_focus_points[3] if len(chapter_focus_points) > 3 else "设置后续情节伏笔"}
    *   **字数目标 (参考)**: 2000-
    
    {self._get_golden_chapter_design_variant( # <--- 在这里注入黄金三章的特殊指令
        chapter_params.get("chapter_number", 1),
        chapter_params.get("novel_title", ""),
        self.custom_main_character_name or "主角"
    )}

    # 背景资料
    ## 1. 小说基础设定 (世界观、角色、大纲等)
    ```json
    {json.dumps(novel_settings, ensure_ascii=False, indent=2)}

    2. 最近章节摘要
    {chapter_params.get("previous_chapters_summary", "暂无更多章节信息")}

    3. 事件执行指导
    {chapter_params.get("event_driven_guidance", "按主线情节自然推进")}

    4. 伏笔铺垫指导
    {chapter_params.get("foreshadowing_guidance", "暂无特定伏笔任务")}

    5. 角色发展指导
    {chapter_params.get("character_development_guidance", "保持角色行为一致性")}

    请严格按照System Prompt中定义的JSON格式输出创作蓝图。
    """
        print(f"  📝 生成第{chapter_params.get('chapter_number', 1)}章设计方案...")
        design_result = self.api_client.generate_content_with_retry(
            "chapter_design", 
            design_prompt, 
            purpose=f"制定第{chapter_params.get('chapter_number', 1)}章设计方案"
        )
        
        if design_result:
            if highlight_scene_block:
                print("  🔧 将预生成的高光场景注入设计蓝图的高潮部分。")
                if "plot_structure" not in design_result:
                    design_result["plot_structure"] = {}
                design_result["plot_structure"]["climax_point"] = highlight_scene_block
                design_result["chapter_focus"] = f"【核心任务：无缝衔接预生成的高光场景，见高潮部分】\n" + design_result.get("chapter_focus", "")
            
            print(f"  ✅ 第{chapter_params.get('chapter_number', 1)}章设计方案生成成功")
            # 验证情绪设计是否被正确包含
            if "emotional_design" not in design_result:
                print(f"  ⚠️ 设计方案未包含情绪设计")
            return design_result
        else:
            print(f"  ❌ 第{chapter_params.get('chapter_number', 1)}章设计方案生成失败")
            return None
                

    def _prepare_chapter_params(self, chapter_number: int, novel_data: Dict) -> Dict:
        """准备章节参数 - 移除重复的情绪缓冲逻辑"""
        print(f"  🔍 准备第{chapter_number}章参数...")

        # 获取之前的世界状态
        novel_title = novel_data["novel_title"]
        world_state = self._get_previous_world_state(novel_title)
        character_development_guidance = self._get_character_development_guidance(chapter_number, novel_data)
        
        # 获取上下文
        context:Contexts.GenerationContext = novel_data.get('_current_generation_context')
        
        
        if context:
            print(f"  ✅ 使用上下文信息准备参数")
            # 使用上下文中的详细信息
            event_context = context.event_context
            foreshadowing_context = context.foreshadowing_context  
            growth_context = context.growth_context
            stage_writing_plan = context.stage_plan if hasattr(context, 'stage_plan') else {}

            print(f"  📊 上下文信息:")
            print(f"    - 事件上下文: {len(event_context.get('active_events', []))} 个活跃事件")
            print(f"    - 伏笔上下文: {len(foreshadowing_context.get('elements_to_introduce', []))} 个待引入元素") 
            print(f"    - 成长上下文: {len(growth_context.get('chapter_specific', {}))} 项成长规划")  
            
            # 获取事件指导（优先使用上下文中的信息）
            event_guidance = self._get_event_guidance_from_context(event_context, chapter_number)
            foreshadowing_guidance = self._get_foreshadowing_guidance_from_context(foreshadowing_context, chapter_number)
            
            # 确保 event_guidance 不是 None
            if event_guidance is None:
                event_guidance = "# 🎯 事件执行指导\n\n本章暂无特定事件任务，按主线推进即可。"
                print(f"  ⚠️ 事件指导为空，使用默认指导")
            
            print(f"    - 事件指导: \n{event_guidance} ") 
            print(f"    - 伏笔指导: \n{foreshadowing_guidance} ") 
        else:
            print(f"  ⚠️ 无上下文，使用传统方式获取指导")
            # 回退到传统方式
            event_guidance = self._get_event_driven_guidance(chapter_number, novel_data)
            foreshadowing_guidance = self._get_foreshadowing_guidance(chapter_number, novel_data)
            event_context = {}
            foreshadowing_context = {}
            growth_context = {}
            stage_writing_plan = {}
        
        # 准备基础参数
        total_chapters = novel_data["current_progress"]["total_chapters"]
        plot_direction = self._get_plot_direction_for_chapter(chapter_number, total_chapters)
        
        # 新增：获取情绪指导（统一来源）
        emotional_guidance = self._get_emotional_guidance_for_chapter(chapter_number, novel_data)
        
        writing_style_guide = novel_data.get("writing_style_guide", {})
        params = {
            "chapter_number": chapter_number,
            "total_chapters": total_chapters,
            "novel_title": novel_data["novel_title"],
            "novel_synopsis": novel_data["novel_synopsis"],
            "writing_style_guide": writing_style_guide,
            "worldview_info": json.dumps(novel_data["core_worldview"], ensure_ascii=False) if novel_data["core_worldview"] else "{}",
            "character_info": json.dumps(novel_data["character_design"], ensure_ascii=False) if novel_data["character_design"] else "{}",
            "character_development_guidance": character_development_guidance,
            "stage_writing_plan": stage_writing_plan,
            "previous_chapters_summary": self._generate_previous_chapters_summary(chapter_number, novel_data),
            "main_plot_progress": plot_direction["plot_direction"],
            "plot_direction": plot_direction["plot_direction"],
            "chapter_connection_note": self._get_chapter_connection_note(chapter_number),
            "character_development_focus": plot_direction.get("character_development_focus", ""),
            "main_character_instruction": self._get_main_character_instruction(novel_data),
            "event_driven_guidance": event_guidance,
            "foreshadowing_guidance": foreshadowing_guidance,
            # === 修改：使用统一的情绪指导系统 ===
            "emotional_guidance": emotional_guidance,
            "current_emotional_focus": emotional_guidance.get("current_emotional_focus", ""),
            "target_emotional_intensity": emotional_guidance.get("target_intensity", "中"),
            "is_emotional_turning_point": emotional_guidance.get("is_emotional_turning_point", False),
            "is_emotional_break_chapter": emotional_guidance.get("is_emotional_break_chapter", False),
            "emotional_break_activities": emotional_guidance.get("break_activities", []),
            "emotional_turning_point_info": emotional_guidance.get("turning_point_info", {}),
            "emotional_supporting_elements": emotional_guidance.get("emotional_supporting_elements", {}),
            "event_context": json.dumps(event_context, ensure_ascii=False),
            "foreshadowing_context": json.dumps(foreshadowing_context, ensure_ascii=False),
            "growth_context": json.dumps(growth_context, ensure_ascii=False),
            "event_tasks": self._format_event_tasks(event_context),
            "foreshadowing_elements": self._format_foreshadowing_elements(foreshadowing_context),
            "character_growth_focus": self._get_growth_focus(growth_context, "character"),
            "ability_development_focus": self._get_growth_focus(growth_context, "ability"),
            "faction_development_focus": self._get_growth_focus(growth_context, "faction")
        }
        
        print(f"  ✅ 第{chapter_number}章参数准备完成")
        print(f"    - 事件任务: {len(params['event_tasks'].splitlines())} 项")
        print(f"    - 伏笔元素: {len(params['foreshadowing_elements'].splitlines())} 项")
        print(f"    - 情绪重点: {params['current_emotional_focus']}")
        print(f"    - 情感强度: {params['target_emotional_intensity']}")
        if params['is_emotional_break_chapter']:
            print(f"    - 本章为情感缓冲章节")
        if params['is_emotional_turning_point']:
            print(f"    - 本章为情感转折点")
        
        params = self._add_consistency_requirements(params, world_state)
        relationship_note = self._get_relationship_consistency_note(world_state)
        if relationship_note:
            if "event_driven_guidance" in params:
                params["event_driven_guidance"] += f"\n\n{relationship_note}"
        return params

    def _get_emotional_guidance_for_chapter(self, chapter_number: int, novel_data: Dict) -> Dict:
        """获取章节的情绪指导 - 统一来源，避免重复"""
        try:
            # 优先从阶段计划管理器中获取情绪指导
            stage_plan_manager = self.novel_generator.stage_plan_manager
            if hasattr(stage_plan_manager, 'get_chapter_writing_context'):
                writing_context = stage_plan_manager.get_chapter_writing_context(chapter_number)
                emotional_guidance = writing_context.get("emotional_guidance", {})
                
                if emotional_guidance:
                    print(f"  💖 从阶段计划管理器获取情绪指导")
                    return emotional_guidance
        except Exception as e:
            print(f"  ⚠️ 从阶段计划管理器获取情绪指导失败: {e}")
        
        # 其次尝试从全局成长规划器获取
        try:
            global_growth_planner = self.novel_generator.global_growth_planner
            if hasattr(global_growth_planner, 'get_chapter_content_context'):
                growth_context = global_growth_planner.get_chapter_content_context(chapter_number)
                emotional_context = growth_context.get("emotional_guidance", {})
                
                if emotional_context:
                    print(f"  💖 从全局成长规划器获取情绪指导")
                    return emotional_context
        except Exception as e:
            print(f"  ⚠️ 从全局成长规划器获取情绪指导失败: {e}")
        
        # 最后使用基于章节位置的回退指导
        print(f"  💖 使用回退情绪指导")
        return self._get_fallback_emotional_guidance(chapter_number, novel_data)

    def _get_fallback_emotional_guidance(self, chapter_number: int, novel_data: Dict) -> Dict:
        """回退情绪指导 - 基于章节位置，简化版本"""
        total_chapters = novel_data["current_progress"]["total_chapters"]
        progress_ratio = chapter_number / total_chapters
        
        if progress_ratio <= 0.2:
            return {
                "current_emotional_focus": "建立情感连接和读者认同",
                "target_intensity": "中",
                "is_emotional_turning_point": False,
                "is_emotional_break_chapter": progress_ratio > 0.15,  # 在20%进度附近安排缓冲
                "break_activities": ["日常互动", "角色反思"],
                "reader_emotional_journey": "让读者对主角产生好奇和认同"
            }
        elif progress_ratio <= 0.5:
            return {
                "current_emotional_focus": "深化情感冲突和发展关系", 
                "target_intensity": "中高",
                "is_emotional_turning_point": progress_ratio > 0.4,
                "is_emotional_break_chapter": progress_ratio > 0.35,  # 在35-40%进度安排缓冲
                "break_activities": ["关系建设", "支线探索"],
                "reader_emotional_journey": "让读者深度投入情感世界"
            }
        elif progress_ratio <= 0.8:
            return {
                "current_emotional_focus": "情感高潮和重大转折",
                "target_intensity": "高",
                "is_emotional_turning_point": progress_ratio > 0.7,
                "is_emotional_break_chapter": progress_ratio > 0.75,  # 在75%进度后安排缓冲
                "break_activities": ["情感消化", "准备最终冲突"],
                "reader_emotional_journey": "让读者经历情感冲击和共鸣"
            }
        else:
            return {
                "current_emotional_focus": "情感解决和成长体现",
                "target_intensity": "中高", 
                "is_emotional_turning_point": progress_ratio > 0.9,
                "is_emotional_break_chapter": False,  # 结局阶段通常不需要缓冲
                "break_activities": [],
                "reader_emotional_journey": "让读者感受到情感满足和成长"
            }
    def _get_event_guidance_from_context(self, event_context: Dict, chapter_number: int) -> str:
        """从事件上下文中生成指导 - 修复键名错误版本"""
        
        if not event_context:
            print("   - 事件上下文为空，返回默认指导")
            return "# 🎯 事件执行指导\n\n事件上下文为空，按常规情节推进。"
        
        try:
            guidance_parts = ["# 🎯 事件执行指导"]
            
            # 🆕 添加事件时间线信息
            event_timeline = event_context.get("event_timeline", {})
            timeline_summary = event_timeline.get("timeline_summary", "")
            
            if timeline_summary:
                guidance_parts.extend([
                    "## ⏰ 事件时间线概览",
                    timeline_summary,
                    ""
                ])
            
            # 🆕 添加上下文衔接指导 - 修复键名问题
            previous_event = event_timeline.get("previous_event")
            next_event = event_timeline.get("next_event")
            
            if previous_event or next_event:
                guidance_parts.append("## 🔗 情节衔接指导")
                
                if previous_event:
                    # 🆕 修复：使用正确的键名获取章节号
                    prev_chapter = previous_event.get("start_chapter", previous_event.get("chapter", "未知"))
                    guidance_parts.extend([
                        f"### 📖 承接前情 (第{prev_chapter}章)",
                        f"- **事件**: {previous_event['name']}",
                        f"- **类型**: {previous_event['type']}事件",
                        f"- **衔接重点**: 自然承接上一章的{previous_event.get('significance', '情节发展')}",
                        f"- **情感延续**: 保持{previous_event.get('emotional_impact', '情感基调')}的连贯性",
                        ""
                    ])
                
                if next_event:
                    # 🆕 修复：使用正确的键名获取章节号
                    next_chapter = next_event.get("start_chapter", next_event.get("chapter", "未知"))
                    guidance_parts.extend([
                        f"### 🔮 铺垫后续 (第{next_chapter}章)",
                        f"- **即将发生**: {next_event['name']}",
                        f"- **事件类型**: {next_event['type']}事件",
                        f"- **铺垫重点**: 为下一章的{next_event.get('significance', '重要事件')}做好情感和情节准备",
                        f"- **伏笔设置**: 适当埋下与下一章事件相关的线索",
                        ""
                    ])
            
            # 检查是否有活跃事件
            active_events = event_context.get("active_events", [])
            if not active_events:
                print("   - 无活跃事件，返回空窗期指导")
                empty_guidance = self._get_empty_period_guidance(chapter_number, event_context)
                # 确保返回的是字符串
                if empty_guidance and isinstance(empty_guidance, str):
                    guidance_parts.append(empty_guidance)
                else:
                    guidance_parts.extend([
                        "## 📝 空窗期写作重点",
                        "本章暂无特定事件任务，重点推进：",
                        "- 角色情感发展和关系深化",
                        "- 世界观细节的丰富和展现", 
                        "- 主线情节的渐进推进",
                        "- 为后续重大事件做好铺垫"
                    ])
                
                result = "\n".join(guidance_parts)
                print(f"✅ [_get_event_guidance_from_context] 空窗期指导生成成功，长度: {len(result)}")
                return result
            
            # 处理活跃事件
            guidance_parts.append("## 🎪 活跃事件执行")
            
            for event in active_events:
                print(f"   - 处理事件: {event.get('name')}")
                
                # 添加错误处理，确保关键字段存在
                event_name = event.get("name", "未知事件")
                main_goal = event.get("main_goal", "推进事件发展")
                current_stage_focus = event.get("current_stage_focus", "按计划推进")
                event_type = event.get("type", "普通事件")
                
                guidance_parts.extend([
                    f"### {event_name} ({event_type})",
                    f"**核心目标**: {main_goal}",
                    f"**当前阶段重点**: {current_stage_focus}",
                    f"**情节衔接**: 确保与前后事件逻辑连贯",
                    f"**关键时刻**:"
                ])
                
                # 处理关键时刻
                key_moments = event.get('key_moments', [])
                if key_moments:
                    for moment in key_moments:
                        if isinstance(moment, dict):
                            description = moment.get('description', '')
                            impact = moment.get('impact', '')
                            if impact:
                                guidance_parts.append(f"- {description} (影响度: {impact})")
                            else:
                                guidance_parts.append(f"- {description}")
                        else:
                            guidance_parts.append(f"- {moment}")
                else:
                    guidance_parts.append("- 按事件发展自然推进关键情节")
                
                guidance_parts.append("")  # 空行分隔事件
            
            # 🆕 添加情感填充事件指导
            filler_guidance = event_context.get("filler_guidance", {})
            if filler_guidance.get("has_filler_event", False):
                guidance_parts.append("## 💝 情感填充事件")
                guidance_parts.append("本章包含情感填充事件，重点抓住读者兴趣：")
                
                for event in filler_guidance.get("filler_events", []):
                    guidance_parts.extend([
                        f"### {event.get('name', '情感事件')}",
                        f"- **情感风格**: {event.get('romance_style', '情感发展')}",
                        f"- **主线关联**: {event.get('main_thread_integration', '自然融入主线')}",
                        f"- **情节设计**: {event.get('plot_design', '情感互动')}",
                        f"- **读者吸引**: {event.get('reader_hook', '保持读者兴趣')}",
                        f"- **写作重点**: {event.get('writing_focus', '情感描写')}"
                    ])
                    
                    key_moments = event.get("key_moments", [])
                    if key_moments:
                        guidance_parts.append(f"- **关键时刻**: {', '.join(key_moments)}")
            
            # 🆕 添加事件连贯性检查
            guidance_parts.extend([
                "",
                "## 🔍 事件连贯性检查",
                "写作时请确保：",
                "✅ 与上一章事件自然衔接，不出现逻辑断层",
                "✅ 为下一章事件做好适当铺垫，保持情节流畅", 
                "✅ 事件发展与角色情感变化协调一致",
                "✅ 保持主线情节的连贯性和推进感"
            ])
            
            result = "\n".join(guidance_parts)
            print(f"✅ [_get_event_guidance_from_context] 事件指导生成成功，长度: {len(result)}")
            return result
            
        except Exception as e:
            print(f"❌ [_get_event_guidance_from_context] 生成事件指导时出错: {e}")
            import traceback
            traceback.print_exc()
            return "# 🎯 事件执行指导\n\n事件指导生成失败，请按常规情节推进。"

    def _get_foreshadowing_guidance_from_context(self, foreshadowing_context: Dict, chapter_number: int) -> str:
        """从伏笔上下文中生成指导 - 修复版本"""
        print(f"  🎭 生成第{chapter_number}章伏笔指导...")
        
        if not foreshadowing_context:
            print("  ⚠️ 伏笔上下文为空，返回默认指导")
            return "# 🎭 伏笔铺垫指导\n\n本章暂无特定的伏笔任务。"
        
        guidance_parts = ["# 🎭 伏笔铺垫指导"]
        
        # 添加伏笔焦点
        focus = foreshadowing_context.get('foreshadowing_focus', f'第{chapter_number}章伏笔管理')
        guidance_parts.append(f"## {focus}")
        
        # 处理待引入元素 - 添加详细检查
        elements_to_introduce = foreshadowing_context.get("elements_to_introduce", [])
        print(f"  📊 待引入元素数量: {len(elements_to_introduce)}")
        
        if elements_to_introduce:
            guidance_parts.append("## 🆕 需要引入的元素:")
            for i, element in enumerate(elements_to_introduce):
                if not isinstance(element, dict):
                    print(f"  ⚠️ 元素{i}不是字典类型: {type(element)}")
                    continue
                    
                element_name = element.get('name', f'未知元素{i}')
                element_type = element.get('type', '未知类型')
                purpose = element.get('purpose', '推进情节发展')
                
                guidance_parts.append(f"- **{element_name}** ({element_type}): {purpose}")
                print(f"  ✅ 添加引入元素: {element_name}")
        else:
            guidance_parts.append("## 🆕 需要引入的元素: 暂无")
        
        # 处理待发展元素
        elements_to_develop = foreshadowing_context.get("elements_to_develop", [])
        print(f"  📊 待发展元素数量: {len(elements_to_develop)}")
        
        if elements_to_develop:
            guidance_parts.append("## 📈 需要发展的元素:")
            for i, element in enumerate(elements_to_develop):
                if not isinstance(element, dict):
                    print(f"  ⚠️ 发展元素{i}不是字典类型: {type(element)}")
                    continue
                    
                element_name = element.get('name', f'未知元素{i}')
                element_type = element.get('type', '未知类型')
                development_arc = element.get('development_arc', '进一步发展')
                
                guidance_parts.append(f"- **{element_name}** ({element_type}): {development_arc}")
                print(f"  ✅ 添加发展元素: {element_name}")
        else:
            guidance_parts.append("## 📈 需要发展的元素: 暂无")
        
        result = "\n".join(guidance_parts)
        print(f"  ✅ 伏笔指导生成完成，长度: {len(result)}")
        return result

    def _format_event_tasks(self, event_context: Dict) -> str:
        """格式化事件任务"""
        tasks = event_context.get("event_tasks", [])
        if not tasks:
            return "本章无特定事件任务，按主线推进即可。"
        
        task_lines = []
        for task in tasks:
            priority_icon = {"high": "🔴", "critical": "🟠", "medium": "🟡", "low": "🟢"}.get(task.get("priority", "medium"), "⚪")
            task_lines.append(f"{priority_icon} {task.get('description', '')}")
        
        return "\n".join(task_lines)

    def _format_foreshadowing_elements(self, foreshadowing_context: Dict) -> str:
        """格式化伏笔元素"""
        elements = []
        
        # 处理要引入的元素
        for element in foreshadowing_context.get("elements_to_introduce", []):
            elements.append(f"✨ 引入{element.get('type', '元素')}「{element.get('name', '')}」: {element.get('purpose', '')}")
        
        # 处理要发展的元素
        for element in foreshadowing_context.get("elements_to_develop", []):
            elements.append(f"📈 发展{element.get('type', '元素')}「{element.get('name', '')}」: {element.get('development_arc', '')}")
        
        return "\n".join(elements) if elements else "本章无特定伏笔任务，保持故事连贯性即可。"

    def _get_growth_focus(self, growth_context: Dict, focus_type: str) -> str:
        """获取成长规划重点"""
        if not growth_context:
            return ""
        
        chapter_specific = growth_context.get("chapter_specific", {})
        content_focus = chapter_specific.get("content_focus", {})
        
        focus_map = {
            "character": content_focus.get("character_growth", ""),
            "ability": content_focus.get("ability_advancement", ""), 
            "faction": content_focus.get("faction_development", "")
        }
        
        return focus_map.get(focus_type, "")

    def generate_chapter_content_from_design(self, chapter_params: Dict, chapter_design: Dict) -> Optional[Dict]:
        """根据设计方案生成章节内容 - 修复版本，添加情绪设计验证"""
        # 准备内容生成参数，包含所有基础设定
        content_params = chapter_params.copy()
        # 确保所有基础设定参数都存在
        required_base_params = [
            'worldview_info', 'character_info', 'stage_writing_plan',
            'novel_title', 'novel_synopsis', 'main_character_instruction'
        ]
        
        for param in required_base_params:
            if param not in content_params or not content_params[param]:
                # 设置默认值
                if param == 'main_character_instruction' and not content_params.get(param):
                    content_params[param] = ""
        # 获取关键一致性信息
        character_state = chapter_params.get('character_state', '')
        world_state = chapter_params.get('world_state', '')
        writing_style = chapter_design.get('writing_style', {})
        
        # 提取关键设计元素
        emotional_design = chapter_design.get('emotional_design', {})
        plot_structure = chapter_design.get('plot_structure', {})
        character_performance = chapter_design.get('character_performance', {})
        
        # 提取风格关键词
        style_keywords = []
        if writing_style:
            style_keywords.append(writing_style.get('core_style', ''))
            if writing_style.get('language_characteristics'):
                lang_chars = writing_style['language_characteristics']
                style_keywords.extend([
                    lang_chars.get('sentence_structure', ''),
                    lang_chars.get('vocabulary_style', ''),
                    lang_chars.get('rhythm_control', '')
                ])
        
        # 构建保留关键上下文的提示词
        user_prompt = f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_params['chapter_number']}章。

## ‼️ 核心融合任务 (最高优先级) ##
在下方的【情节结构】-【高潮】部分，你会看到一个被 `[SCENE_BLOCK_START]` 和 `[SCENE_BLOCK_END]` 包裹的【高光场景模块】。

你的任务是：
1.  **无痕融入**: 将这个【高光场景模块】的内容，逐字不差地、完美地融入到你的行文中。你需要创作它之前和之后的情节，让整个高潮部分读起来天衣无缝，就像完全是你自己一气呵成写出来的。
2.  **主动净化**: 在你的最终输出中，**绝对不能包含 `[SCENE_BLOCK_START]` 或 `[SCENE_BLOCK_END]` 这两个标记**。你要在创作过程中就将它们“吸收”掉，只留下纯净的故事情节。


## 情感设计 ##
- 目标情绪: {emotional_design.get('target_emotion', '')}
- 情感强度: {emotional_design.get('emotional_intensity', '')}
- 关键情绪时刻: {emotional_design.get('key_emotional_moments', [])}

## 情节结构 ##
- 开场: {plot_structure.get('opening_scene', '')}
- 冲突发展: {plot_structure.get('conflict_development', '')}
- 高潮: {plot_structure.get('climax_point', '')}
- 结尾钩子: {plot_structure.get('ending_hook', '')}

## 人物表现 ##
- 主角发展: {character_performance.get('main_character_development', '')}
- 关键对话: {character_performance.get('key_dialogues', [])}

## 一致性要求 ##
- 人物状态: {character_state}
- 世界状态: {world_state}
- 写作风格: {', '.join([kw for kw in style_keywords if kw])}

## 章节重点 ##
{chapter_design.get('chapter_focus', '')}

请确保严格遵循以上所有设计要求，保持情感表达准确、情节连贯、人物和世界状态一致。
"""
        print(f"  ✍️ 根据设计方案生成第{chapter_params['chapter_number']}章内容...")
        content_result = self.api_client.generate_content_with_retry(
            "chapter_content_generation", 
            user_prompt, 
            purpose=f"生成第{chapter_params['chapter_number']}章内容"
        )
        
        if content_result:
            # 记录使用的设计方案和基础设定
            content_result["chapter_design"] = chapter_design
            content_result["design_followed"] = True
            content_result["base_settings_used"] = {
                "worldview": bool(chapter_params.get("worldview_info")),
                "character": bool(chapter_params.get("character_info")),
                "writing_plan": bool(chapter_params.get("stage_writing_plan"))
            }
            
            # 记录情绪设计信息
            content_result["emotional_design_applied"] = {
                "planned_focus": emotional_design.get('target_emotion', ''),
                "target_intensity": emotional_design.get('emotional_intensity', ''),
                "key_moments": emotional_design.get('key_emotional_moments', [])
            }
            
            print(f"  ✅ 第{chapter_params['chapter_number']}章内容生成成功")
            print(f"  🎭 应用的情绪设计: {content_result['emotional_design_applied']}")
            return content_result
        else:
            print(f"  ❌ 第{chapter_params['chapter_number']}章内容生成失败")
            return None
                
        
    def generate_writing_style_guide(self, creative_seed: str, category: str, selected_plan: Dict, market_analysis: Dict) -> Optional[Dict]:
        """生成写作风格指南"""
        print(f"  🎨 为分类'{category}'生成写作风格指南...")
        
        try:
            # 构建提示词
            user_prompt = f"""
内容:
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
                # 确保返回的结构完整
                required_keys = ['core_style', 'language_characteristics', 'narration_techniques', 
                            'dialogue_style', 'chapter_techniques', 'key_principles']
                
                for key in required_keys:
                    if key not in result:
                        if key == 'language_features':
                            result[key] = ["简洁明了", "生动形象", "节奏感强"]
                        elif key == 'description_focus':
                            result[key] = ["人物动作", "环境氛围", "心理活动"]
                        elif key == 'important_notes':
                            result[key] = ["保持风格一致性", "注意节奏控制", "强化读者代入感"]
                        else:
                            result[key] = "待补充"
                
                print(f"  ✅ 写作风格指南生成成功")
                return result
            else:
                print(f"  ❌ 写作风格指南生成失败")
                return None
                
        except Exception as e:
            print(f"  ❌ 生成写作风格指南时出错: {e}")
            return None  
    
    def _get_empty_period_guidance(self, chapter_number: int, event_context: Dict) -> str:
        """生成事件空窗期的指导内容 - 确保返回字符串"""
        
        return "# 🎯 事件执行指导\n\n当前处于事件空窗期，重点推进主线情节和角色发展。"
    def _get_previous_world_state(self, novel_title: str) -> Dict:
        """获取之前章节的世界状态"""
        if not hasattr(self, 'quality_assessor') or not self.quality_assessor:
            return {}
        
        try:
            return self.quality_assessor.load_previous_assessments(novel_title)
        except Exception as e:
            print(f"⚠️ 加载世界状态失败: {e}")
            return {}


    def _build_consistency_guidance(self, world_state: Dict) -> str:
        """构建【全面且强约束】的一致性指导内容，包含角色、物品、技能、金钱。"""
        if not world_state:
            return ""

        guidance_parts = ["\n--- 一致性铁律 (AI必须严格遵守) ---\n"]
        
        characters = world_state.get('characters', {})
        items = world_state.get('cultivation_items', {}) # 适配QualityAssessor中的新结构
        skills = world_state.get('cultivation_skills', {}) # 适配QualityAssessor中的新结构
        relationships = world_state.get('relationships', {})

        # 1. 【最高优先级】死亡/退场名单
        dead_or_exited_chars = [
            name for name, data in characters.items() 
            if data.get('attributes', {}).get('status', 'active').lower() in ['dead', 'exited', '死亡', '退场']
        ]
        if dead_or_exited_chars:
            guidance_parts.append(f"【🔴绝对禁止】以下角色已死亡或永久退场，绝不能以任何存活形式出现：`{', '.join(dead_or_exited_chars)}`")

        # 按更新次数/重要性排序，提取最重要的信息
        def get_sorted_entities(entities: dict):
            if not entities or not isinstance(entities, dict):
                return []
            return sorted(
                [item for item in entities.items() if item[0] not in dead_or_exited_chars],
                key=lambda item: item[1].get('update_count', 0), # 假设有update_count字段
                reverse=True
            )

        # 2. 【角色核心状态】 (最重要的5个)
        char_list = get_sorted_entities(characters)
        if char_list:
            guidance_parts.append("\n【🟡角色当前状态 (必须遵守)】")
            for char_name, char_data in char_list[:5]:
                attrs = char_data.get('attributes', {})
                status = attrs.get('status', '活跃')
                location = attrs.get('location', '未知')
                faction = attrs.get('faction', '无')
                level = attrs.get('cultivation_level', '')
                money = attrs.get('money', None)
                
                state_summary = f"- **{char_name}**: 状态:`{status}`, 位置:`{location}`, 势力:`{faction}`"
                if level: state_summary += f", 修为:`{level}`"
                if money is not None:
                    # 对金钱进行模糊化处理，告知AI大概范围即可，避免精确数字的困扰
                    wealth_desc = "普通"
                    if money > 10000: wealth_desc = "非常富有"
                    elif money > 1000: wealth_desc = "富裕"
                    elif money < 100: wealth_desc = "拮据"
                    state_summary += f", 经济:`{wealth_desc}`"
                guidance_parts.append(state_summary)

        # 3. 【物品归属】 (最重要的5件)
        item_list = get_sorted_entities(items)
        if item_list:
            guidance_parts.append("\n【🟡关键物品归属 (必须遵守)】")
            for item_name, item_data in item_list[:5]:
                owner = item_data.get('owner', '无主/公共')
                status = item_data.get('status', '完好')
                # 如果物品已消耗或损坏，则标记为不可用
                if status.lower() in ['used', 'destroyed', 'consumed', '已使用', '已消耗', '已损毁']:
                    guidance_parts.append(f"- `{item_name}`: 状态:`{status}`，【不可再次使用】。")
                else:
                    guidance_parts.append(f"- `{item_name}`: 目前归属于 `{owner}`，状态:`{status}`。")

        # 4. 【功法/技能状态】 (主角和重要角色的关键技能)
        skill_list = get_sorted_entities(skills)
        if skill_list:
            guidance_parts.append("\n【🟡功法/技能状态 (必须遵守)】")
            # 优先展示主角的技能
            main_char_name = self.custom_main_character_name
            main_char_skills = [(n, d) for n, d in skill_list if d.get('owner') == main_char_name]
            other_skills = [(n, d) for n, d in skill_list if d.get('owner') != main_char_name]
            
            for skill_name, skill_data in (main_char_skills + other_skills)[:5]:
                owner = skill_data.get('owner', '未知')
                level = skill_data.get('level', '未知')
                guidance_parts.append(f"- `{owner}` 的技能 `{skill_name}` 当前等级为 `{level}`。")

        # 5. 【关键人物关系】 (最重要的7组)
        rel_list = get_sorted_entities(relationships)
        if rel_list:
            guidance_parts.append("\n【🟡关键人物关系 (禁止重复建立)】")
            for rel_key, rel_data in rel_list[:7]:
                # 兼容 "角色A-角色B" 和元组 key
                parties = rel_key.split('-') if isinstance(rel_key, str) else rel_key
                if len(parties) == 2:
                    char_a, char_b = parties
                    rel_type = rel_data.get('type', '未知')
                    guidance_parts.append(f"- `{char_a}` 与 `{char_b}` 的关系是: `{rel_type}`。他们已经认识！")
        
        guidance_parts.append("\n" + "-"*35 + "\n")
        return "\n".join(guidance_parts)


    def _calculate_update_count(self, element_data: Dict) -> int:
        """计算元素的更新次数 - 简化版本（使用准确计数器）"""
        try:
            return int(element_data.get('update_count', 1))
        except Exception:
            return 1  # 默认至少更新一次

    def _safe_get(self, obj, key, default=None):
        """安全获取字典值，避免任何异常"""
        try:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default
        except Exception:
            return default

    def _format_known_relationships(self, relationships: Dict) -> str:
        """格式化已知关系用于显示"""
        if not relationships:
            return "暂无已建立的关系记录"
        
        formatted = []
        for rel_key, rel_data in list(relationships.items())[:10]:  # 最多显示10个关系
            parties = rel_key.split('-')
            if len(parties) == 2:
                char_a, char_b = parties
                rel_type = rel_data.get('type', '未知关系')
                formatted.append(f"- {char_a} ↔ {char_b}: {rel_type}")
        
        return "\n".join(formatted)

    def _add_consistency_requirements(self, chapter_params: Dict, world_state: Dict) -> Dict:
        if not world_state:
            return chapter_params
        
        # 构建一致性指导
        consistency_guidance = self._build_consistency_guidance(world_state)
        
        # 在现有指导基础上添加一致性要求
        if "foreshadowing_guidance" in chapter_params:
            chapter_params["foreshadowing_guidance"] += f"\n\n## 🔄 一致性要求\n{consistency_guidance}"
        
        # 存储世界状态供生成使用
        chapter_params["previous_world_state"] = json.dumps(world_state, ensure_ascii=False, indent=2)
        
        # 特别添加关系检查标志
        chapter_params["relationship_consistency_check"] = True
        chapter_params["known_relationships"] = world_state.get('relationships', {})
        
        return chapter_params

    def _get_relationship_consistency_note(self, world_state: Dict) -> str:
        """生成关系一致性特别提示"""
        relationships = world_state.get('relationships', {})
        if not relationships:
            return ""
        
        note_parts = ["## 🤝 已知人物关系（禁止重复建立）"]
        
        # 按角色分组显示关系
        character_relations = {}
        for rel_key, rel_data in relationships.items():
            parties = rel_key.split('-')
            if len(parties) == 2:
                char_a, char_b = parties
                rel_type = rel_data.get('type', '未知')
                
                # 为每个角色记录关系
                if char_a not in character_relations:
                    character_relations[char_a] = []
                character_relations[char_a].append(f"{char_b}({rel_type})")
                
                if char_b not in character_relations:
                    character_relations[char_b] = []
                character_relations[char_b].append(f"{char_a}({rel_type})")
        
        # 显示每个角色的关系网络
        for char_name, relations in list(character_relations.items())[:10]:  # 显示前6个角色
            note_parts.append(f"- **{char_name}** 认识: {', '.join(relations)}")
        
        note_parts.extend([
            "",
            "### ❌ 禁止行为",
            "- 让已经认识的角色重新自我介绍",
            "- 忽略已有的关系状态",
            "- 建立与现有关系冲突的新关系",
            "- 忘记角色间的重要历史互动"
        ])
        
        return "\n".join(note_parts) 


    def _get_character_development_guidance(self, chapter_number: int, novel_data: Dict) -> str:
        """获取角色发展指导 - 基于章节进度，避免重复提及已建立的人设"""
        if not hasattr(self, 'quality_assessor') or not self.quality_assessor:
            return ""
        
        novel_title = novel_data["novel_title"]
        
        # 获取角色发展数据
        character_development_data = self.quality_assessor._load_character_development_data(novel_title)
        if not character_development_data:
            return ""
        
        guidance_parts = ["# 🎭 角色发展指导"]
        guidance_parts.append(f"## 当前章节: 第{chapter_number}章")
        
        # 为每个重要角色生成发展建议
        important_chars = []
        for char_name, char_data in character_development_data.items():
            role_type = char_data.get("role_type", "")
            if role_type in ["主角", "重要配角"]:
                important_chars.append((char_name, char_data))
        
        # 按最后出场时间排序，优先处理长时间未出现的角色
        important_chars.sort(key=lambda x: x[1].get("last_updated_chapter", 0))
        
        for char_name, char_data in important_chars[:4]:  # 只处理前4个重要角色
            last_seen = char_data.get("last_updated_chapter", 0)
            total_appearances = char_data.get("total_appearances", 1)
            chapter_gap = chapter_number - last_seen
            
            # 判断角色人设是否已充分建立
            is_character_established = total_appearances >= 5 and chapter_gap <= 10
            
            guidance_parts.append(f"## 👤 {char_name}")
            guidance_parts.append(f"- 角色类型: {char_data.get('role_type', '未知')}")
            guidance_parts.append(f"- 总出场次数: {total_appearances}次")
            guidance_parts.append(f"- 最后出场: 第{last_seen}章")
            guidance_parts.append(f"- 当前章节差距: {chapter_gap}章")
            
            if is_character_established:
                guidance_parts.append(f"- 状态: ✅ 人设已充分建立")
            
            suggestions = self.quality_assessor.get_character_development_suggestions(
                char_name, novel_title, chapter_number
            )
            
            if suggestions:
                guidance_parts.append("### 📋 发展建议:")
                for suggestion in suggestions:
                    # 如果角色已充分建立，过滤掉基础性建议
                    if is_character_established and suggestion['type'] in ["添加名场面", "背景故事"]:
                        continue  # 跳过基础性建议
                        
                    guidance_parts.append(f"- **{suggestion['type']}** ({suggestion['priority']}优先级)")
                    guidance_parts.append(f"  - 建议: {suggestion['description']}")
                    guidance_parts.append(f"  - 原因: {suggestion.get('reason', '')}")
                    guidance_parts.append(f"  - 实现: {suggestion['implementation']}")
            else:
                if is_character_established:
                    guidance_parts.append("### ✅ 人设已充分建立，保持角色一致性即可")
                else:
                    guidance_parts.append("### ✅ 当前无特殊发展建议，保持角色一致性即可")
            
            guidance_parts.append("")  # 空行分隔
        
        # 如果没有重要角色或者所有角色都已充分建立，返回简化的指导
        if len(guidance_parts) <= 3 or all(
            "人设已充分建立" in part for part in guidance_parts if "状态:" in part
        ):
            return "# 🎭 角色发展指导\n\n所有主要角色人设已充分建立，本章重点保持角色行为一致性。"
        
        return "\n".join(guidance_parts)

    # 在 ContentGenerator.py 中
    def _save_chapter_failure(self, novel_data: Dict, chapter_number: int, failure_reason: str, failure_details: Dict):
        """保存章节生成失败信息"""
        try:
            # 准备一个可序列化的上下文摘要
            context_summary = "No context available"
            current_context = novel_data.get('_current_generation_context')
            if current_context:
                # 只记录关键信息，避免过大
                context_summary = {
                    "event_context": {
                        "active_events_count": len(current_context.event_context.get('active_events', [])),
                        "timeline_summary": current_context.event_context.get('event_timeline', {}).get('timeline_summary', '')
                    },
                    "foreshadowing_context_count": len(current_context.foreshadowing_context.get('elements_to_introduce', [])),
                    "growth_context_focus": current_context.growth_context.get('chapter_specific', {}).get('content_focus', {})
                }


            failure_record = {
                "novel_title": novel_data.get("novel_title", "未知小说"),
                "chapter_number": chapter_number,
                "failure_time": self._get_current_timestamp(),
                "failure_reason": failure_reason,
                "failure_details": failure_details,
                "main_character": self.custom_main_character_name,
                "generation_context_summary": context_summary # 使用摘要
            }
            
            # 同时保存到本地文件备份
            self._save_failure_to_local(failure_record)
            
            print(f"💾 已保存第{chapter_number}章失败记录: {failure_reason}")
            
        except Exception as e:
            print(f"⚠️ 保存失败记录时出错: {e}")

    def _save_failure_to_local(self, failure_record: Dict):
        """保存失败记录到本地文件"""
        try:
            import os
            failures_dir = "chapter_failures"
            os.makedirs(failures_dir, exist_ok=True)
            
            filename = f"{failures_dir}/failures_{failure_record['novel_title']}.json"
            
            # 读取现有记录
            existing_failures = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_failures = json.load(f)
            
            # 添加新记录
            existing_failures.append(failure_record)
            
            # 保存回文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(existing_failures, f, ensure_ascii=False, indent=2)
                
            print(f"  💾 失败记录已保存到本地: {filename}")
            
        except Exception as e:
            print(f"  ❌ 本地保存失败: {e}")    

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_multiple_plans(self, creative_seed: str, category: str) -> Dict:
        """生成多个不同金手指和主线剧情的小说方案"""
        print(f"  🎯 生成3个不同风格的小说方案...")
            
        full_prompt = f"""
内容：
创意种子：{creative_seed}
小说分类：{category}

##【重要指令】
你必须生成3个不同风格的小说方案。对于**每一个方案**，都必须遵守以下规则：
1.  **标题约束**: 每个方案的标题都**必须严格控制在4-15个字符之间（包含标点）**。标题要简洁、有冲击力。
2.  **风格差异**: 3个方案的核心设定（尤其是金手指）和主线发展必须有明显的区别。

请严格按照你的System Prompt中定义的JSON格式返回结果。
"""
        
        try:
            # 调用API生成内容
            result = self.api_client.generate_content_with_retry(
                "multiple_plans",
                full_prompt,
                purpose="生成多个小说方案"
            )
            
            if result and 'plans' in result:
                print(f"  ✅ 成功生成 {len(result['plans'])} 个不同方案")
                return result
            else:
                print("  ❌ 生成多个方案失败，返回格式不正确")
                # 如果返回格式不正确，尝试解析或返回空结果
                return {}
                
        except Exception as e:
            print(f"  ❌ 生成多个方案时出错: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _get_golden_chapter_design_variant(self, chapter_number: int, novel_title: str, main_character_name: str) -> str:
        """为黄金三章生成差异化的、高强度的设计指导"""
        if chapter_number == 1:
            return f"""
    # 🔥 黄金第一章：生死看淡，不服就干！
    1.  **极速开局**: 必须在开篇500字内，让主角 {main_character_name} 陷入一个具体的、尖锐的困境或羞辱场景（例如：被退婚、被背叛、被嘲笑、身陷绝境）。
    2.  **金手指激活**: 困境中，金手指（系统）必须被激活，并立即提供一个能解决当前小困境的直接帮助。不要解释来源，直接用！
    3.  **首次打脸**: 主角必须利用金手指的初次帮助，完成一次小范围但效果惊人的“打脸”或“逆袭”，让之前的轻视者震惊。
    4.  **强烈悬念**: 章节结尾必须留下一个强烈的钩子，例如：一个更强大的敌人出现、一个惊人的秘密被揭露一角、或者金手指发布了一个看似不可能完成的重磅任务。
    """
        elif chapter_number == 2:
            return f"""
    # 💥 黄金第二章：矛盾升级，初显锋芒！
    1.  **承接悬念并激化**: 必须立刻回应第一章的悬念，并将冲突升级。例如，更强的敌人开始行动，或第一章的打脸行为引来了更大的麻烦。
    2.  **金手指实战**: 主角需要更深入地使用金手指，展示其更强大的功能，解决一个比第一章更棘手的难题。
    3.  **关键配角登场**: 引入一个关键配角（未来的盟友、导师或更重要的反派），与主角发生强互动。
    4.  **建立小目标**: 为主角树立一个短期内清晰可见、能带来巨大回报的小目标（例如：三天后的家族比武、一周后的宗门考核）。
    5.  **结尾再造悬念**: 结尾要制造新的期待感，例如：主角即将奔赴一个充满机遇与危险的地方，或者一个重要人物对他发起了挑战。
    """
        elif chapter_number == 3:
            return f"""
    # 🚀 黄金第三章：奠定基调，引爆期待！
    1.  **完成小目标与震撼打脸**: 主角必须在这一章完成第二章设立的小目标，并完成一次让所有人都意想不到的、规模更大的打脸。这次打脸要足以颠覆周围人对他的认知。
    2.  **确立爽点模式**: 通过这次打脸，明确本书的核心爽点模式（例如：扮猪吃虎、无限升级、神级炼丹等）。
    3.  **引出主线**: 必须引出一条更宏大的主线故事线索（例如：主角的身世之谜、金手指的真正目的、一个巨大的阴谋等）。
    4.  **付费点钩子**: 结尾必须设置一个“不看下一章就百爪挠心”的强力付费点钩子。这通常是主角做出了一个惊人的决定，或者他即将面临一个生死攸关的重大转折。
    """
        return ""
        