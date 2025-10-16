"""内容生成器类 - 专注内容生成"""

import json
import re
from typing import Dict, Optional, List, Tuple

import APIClient
from Contexts import GenerationContext
import Contexts
import EventDrivenManager
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
        """生成单一小说方案 - 根据分类自动生成主角名字"""
        print("=== 步骤1: 基于创意种子和分类生成小说方案 ===")
        
        # 如果提供了分类，自动生成适合该分类的主角名字
        if category :
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
            "金手指": "AI根据创意生成"
        }            
        user_prompt_str = json.dumps(user_prompt, ensure_ascii=False)
        result = self.api_client.generate_content_with_retry("one_plans", user_prompt_str, purpose="生成小说方案")
        if result:
            result = self._ensure_main_character_in_content(result, "one_plans")
        return result
    
    def _generate_character_name_by_category(self, category: str, creative_seed: str) -> str:
        """根据分类生成适合的主角名字"""
        try:
            print(f"  🎯 开始为分类 '{category}' 创意种子：{creative_seed} 生成主角名字...")
            
            user_prompt = f"\n小说分类：{category}\n创意种子：{creative_seed}"
            
            result = self.api_client.generate_content_with_retry(
                "character_naming",
                user_prompt,
                purpose="生成主角名字"
            )
            
            if result:
                # 解析新的JSON格式
                suggestions = result.get("suggestions", [])
                if suggestions:
                    # 获取第一个建议的名字
                    name = suggestions[0].get("name")
                    if name and 2 <= len(name) <= 3:
                        print(f"  ✅ 获取主角名字: {name}")
                        return name
                
                # 如果没有找到名字，尝试其他可能的字段
                name = result.get("name")
                if name and 2 <= len(name) <= 3:
                    print(f"  ✅ 获取主角名字: {name}")
                    return name
            
            # 如果API调用失败，使用默认名字
            default_name = self._get_default_name_by_category(category)
            print(f"  🔄 使用默认名字: {default_name}")
            return default_name
            
        except Exception as e:
            print(f"  ❌ 生成主角名字时出错: {e}")
            default_name = self._get_default_name_by_category(category)
            return default_name

    def _get_default_name_by_category(self, category: str) -> str:
        """根据分类获取默认主角名字"""
        default_names = {
            "男频衍生": "陈默"
        }
        return default_names.get(category, "林风")

    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        #if result:
            #result = self._assess_and_optimize_content(result, "market_analysis", "市场分析")
            #result = self._ensure_main_character_in_content(result, "market_analysis")
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

        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="世界观构建")
        
        if result:
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观构建")
        
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, market_analysis: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计"""
        print("=== 步骤5: 设计主要角色 ===")
        
        main_character_name = custom_main_character_name or self.custom_main_character_name
        
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
    ## Story Context

    ### 小说信息
    - **小说标题**: {novel_title}
    - **核心世界观**: {json.dumps(core_worldview, ensure_ascii=False)}
    - **市场分析**: {json.dumps(market_analysis, ensure_ascii=False)}
    - **选定方案**: {json.dumps(selected_plan, ensure_ascii=False)}

    ### 核心设定（从选定方案提取）
    - **世界观背景**: {world_background}
    - **金手指/系统**: {golden_finger}
    - **核心爽点**: {', '.join(core_selling_points) if isinstance(core_selling_points, list) else core_selling_points}
    - **主角定位**: {protagonist_position}
    - **主线脉络**: {', '.join(main_plot) if isinstance(main_plot, list) else main_plot}

    ## Design Requirements

    ### 强制要求
    1. **主角设定**
    - 姓名必须为: {main_character_name}
    - 身份和背景必须符合世界观设定
    - 核心能力必须与金手指/系统一致
    - 性格特点要服务于核心冲突和故事发展

    2. **核心配角设定** (必须包含以下4种功能定位)
    - **引导者与支持者**: 主角的早期引导者或庇护者，为主角提供初始平台和资源
    - **辅助与补充者**: 弥补主角能力短板的角色，负责主角不擅长的领域
    - **竞争与参照者**: 与主角有竞争关系或作为参照的角色，用于侧面展现主角成长
    - **主要敌对势力**: 代表核心冲突的反派角色，具有明确的动机和威胁性

    3. **敌对势力设计要求**
    - 必须具有合理的动机和背景
    - 威胁程度要与主角成长阶段相匹配
    - 体现世界观中的核心冲突
    - 具有清晰的成长路径和升级空间

    4. **角色关系网络**
    - 角色间要有明确的互动关系和情感纽带
    - 建立清晰的盟友-敌对关系网络
    - 确保角色间存在合理的利益冲突和合作基础

    5. **角色设计原则**
    - 保持世界观设定的一致性
    - 突出核心冲突中的角色定位
    - 体现金手指/系统对角色能力的影响
    - 符合核心爽点的角色功能需求
    - 确保角色间有明确的互动关系和成长弧线

    ### 输出要求
    必须严格按照角色设计JSON格式输出，确保主角和4位核心配角的设计完整且符合上述要求。
    """

        if main_character_name:
            print(f"  ✓ 角色设计使用主角名字: {main_character_name}")
        
        result = self.api_client.generate_content_with_retry("character_design", context, purpose="角色设计")
        
        if result:
            result = self._assess_and_optimize_content(result, "character_design", "角色设计")
            if main_character_name:
                result = self.ensure_main_character_name(result, main_character_name)
        
        return result

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
        """评估和优化内容质量"""
        if not content or not hasattr(self, 'quality_assessor') or self.quality_assessor is None:
            return content
        
        print(f"  🔍 评估{original_purpose}质量...")
        
        try:
            assessment = None
            if content_type == "market_analysis":
                assessment = self.quality_assessor.assess_market_analysis_quality(content)
            elif content_type == "writing_plan":
                assessment = self.quality_assessor.assess_writing_plan_quality(content)
            elif content_type == "core_worldview":
                assessment = self.quality_assessor.assess_core_worldview_quality(content)
            elif content_type == "character_design":
                assessment = self.quality_assessor.assess_character_design_quality(content)
            
            if not assessment:
                return content
            
            score = assessment.get("overall_score", 0)
            verdict = assessment.get("quality_verdict", "未知")
            print(f"  {original_purpose}质量评分: {score:.1f}/10分 - {verdict}")
            
            if score < 9.0:
                print(f"  🔧 进行{original_purpose}优化...")
                
                optimized_content = None
                if content_type == "market_analysis":
                    optimized_content = self.quality_assessor.optimize_market_analysis(content, assessment)
                elif content_type == "writing_plan":
                    optimized_content = self.quality_assessor.optimize_writing_plan(content, assessment)
                elif content_type == "core_worldview":
                    optimized_content = self.quality_assessor.optimize_core_worldview(content, assessment)
                elif content_type == "character_design":
                    optimized_content = self.quality_assessor.optimize_character_design(content, assessment)
                
                if optimized_content:
                    return optimized_content
            
            return content
        
        except Exception as e:
            print(f"  ⚠️  质量检查过程中出错: {e}")
            return content

    def generate_chapter_content_for_novel(self, chapter_number: int, novel_data: Dict, context: GenerationContext = None) -> Optional[Dict]:
        """为小说生成章节内容 - 整合参数准备和内容生成"""
        print(f"生成第{chapter_number}章内容...")
        
        # 初始化失败信息
        failure_reason = None
        failure_details = {}
        
        try:
            # 如果是第一章，初始化世界状态
            if chapter_number == 1:
                print("🔄 初始化世界状态...")
                self.quality_assessor.initialize_world_state_from_novel_data(novel_data["novel_title"], novel_data)
            
            # 存储上下文供后续使用
            novel_data['_current_generation_context'] = context
            
            # 准备章节参数
            chapter_params = self._prepare_chapter_params(chapter_number, novel_data)
            
            if not chapter_params or not self._validate_chapter_params(chapter_params):
                failure_reason = "参数准备失败"
                failure_details = {
                    "missing_params": [key for key in ['chapter_number', 'novel_title', 'novel_synopsis', 'plot_direction', 'foreshadowing_guidance'] 
                                    if key not in chapter_params or not chapter_params[key]],
                    "chapter_params_keys": list(chapter_params.keys()) if chapter_params else []
                }
                print(f"❌ 第{chapter_number}章参数准备失败")
                self._save_chapter_failure(novel_data, chapter_number, failure_reason, failure_details)
                return None
            
            print(f"  ✅ 第{chapter_number}章所有参数验证通过")
            
            # 生成章节内容 - 添加详细的类型检查
            print(f"  🚀 开始生成第{chapter_number}章内容...")
            chapter_data = self.generate_chapter_content(chapter_params)
            
            if not chapter_data:
                failure_reason = "内容生成失败"
                failure_details = {
                    "step": "generate_chapter_content",
                    "chapter_params_summary": {k: str(v)[:100] + "..." if len(str(v)) > 100 else str(v) 
                                            for k, v in chapter_params.items() if k in ['chapter_number', 'novel_title']}
                }
                print(f"❌ 第{chapter_number}章内容生成失败")
                self._save_chapter_failure(novel_data, chapter_number, failure_reason, failure_details)
                return None

            # 确保章节标题唯一性
            chapter_data = self._handle_chapter_title_uniqueness(chapter_data, chapter_number, novel_data)

            # === 新增：如果是第一章，添加AI俏皮开场白 ===
            if chapter_number == 1:
                category = novel_data.get("category", "默认")
                novel_title = novel_data.get("novel_title", "")
                novel_synopsis = novel_data.get("novel_synopsis", "")
                
                # 使用AI生成俏皮开场白
                try:
                    chapter_data = self.novel_generator._add_ai_spicy_opening_to_first_chapter(
                        chapter_data, novel_title, novel_synopsis, category
                    )
                except Exception as e:
                    print(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")

            if chapter_data:
                # 新增：记录情绪信息
                emotional_guidance = self._get_emotional_guidance_for_chapter(chapter_number, novel_data)
                chapter_data["emotional_design"] = {
                    "planned_focus": emotional_guidance.get("current_emotional_focus", ""),
                    "target_intensity": emotional_guidance.get("target_intensity", "中"),
                    "is_turning_point": emotional_guidance.get("is_emotional_turning_point", False)
                }       

            # 质量评估 - 添加类型检查
            print(f"  📊 开始质量评估...")
            try:
                assessment = self.quality_assessor.quick_assess_chapter_quality(
                    chapter_data.get("content", ""),
                    chapter_data.get("chapter_title", ""),
                    chapter_number,
                    novel_data["novel_title"],
                    chapter_params.get("previous_chapters_summary", ""),
                    chapter_data.get("word_count", 0)
                )
                
                # 设置质量评分
                score = assessment.get("overall_score", 0)
                chapter_data["quality_score"] = score
                chapter_data["quality_assessment"] = assessment
                
                print(f"  质量评分: {score:.1f}分")
                
                # 根据质量决定是否优化
                optimize_needed, optimize_reason = self._should_optimize_based_on_config(assessment, chapter_data)
                
                if optimize_needed:
                    print(f"  🔧 进行优化: {optimize_reason}")
                    optimized_data = self.quality_assessor.optimize_chapter_content({
                        "assessment_results": json.dumps(assessment, ensure_ascii=False),
                        "original_content": chapter_data.get("content", ""),
                        "priority_fix_1": assessment.get("weaknesses", [""])[0] if assessment.get("weaknesses") else "提升质量",
                        "priority_fix_2": assessment.get("weaknesses", [""])[1] if len(assessment.get("weaknesses", [])) > 1 else "",
                        "priority_fix_3": assessment.get("weaknesses", [""])[2] if len(assessment.get("weaknesses", [])) > 2 else ""
                    })
                    if optimized_data:
                        chapter_data.update(optimized_data)
                        # 重新评估优化后的质量
                        new_assessment = self.quality_assessor.quick_assess_chapter_quality(
                            chapter_data.get("content", ""),
                            chapter_data.get("chapter_title", ""),
                            chapter_number,
                            novel_data["novel_title"],
                            chapter_params.get("previous_chapters_summary", ""),
                            chapter_data.get("word_count", 0)
                        )
                        new_score = new_assessment.get("overall_score", 0)
                        improvement = new_score - score
                        print(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{improvement:+.1f}分)")
                        chapter_data["quality_assessment"] = new_assessment
                    else:
                        print(f"  ⚠️ 优化失败，保持原内容")
                        chapter_data["quality_assessment"] = assessment
                else:
                    print(f"  ✓ {optimize_reason}")
                    chapter_data["quality_assessment"] = assessment
                
                return chapter_data
                
            except Exception as e:
                print(f"  ❌ 质量评估过程中出错: {e}")
                import traceback
                traceback.print_exc()
                # 即使质量评估失败，也返回章节内容
                return chapter_data
                
        except Exception as e:
            failure_reason = f"生成过程异常: {str(e)}"
            failure_details = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "chapter_number": chapter_number,
                "traceback": self._get_traceback_info()  # 新增：获取堆栈信息
            }
            print(f"❌ 第{chapter_number}章生成过程中出现异常: {e}")
            import traceback
            print(f"详细堆栈信息:")
            traceback.print_exc()
            self._save_chapter_failure(novel_data, chapter_number, failure_reason, failure_details)
            return None

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
        
        # 尝试加载最近3章的摘要信息
        summary_parts = []
        for i in range(max(1, current_chapter-3), current_chapter):
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
                    print(f"  ✅ 成功提取结尾: {ending[:200]}...")
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
        """处理章节标题唯一性"""
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
        """生成唯一的章节标题"""
        if retry_count >= 2:
            return self._generate_deterministic_title(original_title, chapter_number)
        
        # 基于情节方向生成新标题
        plot_direction = self._get_plot_direction_for_chapter(chapter_number, novel_data["current_progress"]["total_chapters"])
        
        title_prompt = f"""
请为小说的第{chapter_number}章生成一个新的、富有吸引力的章节标题。

原始标题（已重复）: {original_title}
情节发展方向: {plot_direction["plot_direction"]}

要求:
1. 与原始标题风格一致但完全不同
2. 反映本章情节发展
3. 长度8-15字
4. 避免与已有章节标题重复
5. 富有文学性和吸引力

已有章节标题: {list(novel_data.get("used_chapter_titles", set()))[-10:]}

请只返回标题文本，不要其他内容。
"""
        
        try:
            new_title = self.api_client.call_api('deepseek', "你是小说章节标题生成专家", title_prompt, 0.7, purpose="生成唯一章节标题")
            if new_title and new_title.strip():
                new_title = new_title.strip().strip('"').strip("'").strip()
                new_title = re.sub(r'^["\']|["\']$', '', new_title)
                
                # 再次检查唯一性
                is_unique, _ = self._is_chapter_title_unique(new_title, chapter_number, novel_data)
                if is_unique and len(new_title) >= 4:
                    return new_title
                else:
                    return self._generate_unique_chapter_title(original_title, chapter_number, novel_data, retry_count + 1)
        except Exception as e:
            print(f"生成新标题失败: {e}")
        
        return self._generate_deterministic_title(original_title, chapter_number)

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

    def _should_optimize_based_on_config(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """基于配置决定是否需要优化"""
        score = assessment.get("overall_score", 0)
        
        # 强制优化阈值
        if score < 8.0:
            return True, f"评分低于优化阈值7.5分，需要优化"
        
        # 建议优化范围
        if score < 8.0:
            return True, "质量合格但建议优化提升"
        
        return False, "质量良好，跳过优化"

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节内容 - 严格两步法：先设计方案，再生成内容"""
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
                
                # 字数不足的处理
                print(f"  ⚠️ 字数不足: {content_length}字 < 1800字")
                
                # 如果是最后一次尝试，使用当前内容
                if attempt == max_retries - 1:
                    print(f"  ❌ 达到最大重试次数，使用当前内容")
            
            # 确保最终有数据返回
            if chapter_content:
                print(f"  ✅ 第{chapter_number}章生成成功")
                return chapter_content
            else:
                print(f"  ❌ 第{chapter_number}章所有生成尝试均失败")
                return None
                
        except Exception as e:
            print(f"❌ 生成第{chapter_params['chapter_number']}章内容时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def generate_chapter_design(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节详细设计方案 - 修复情绪指导整合"""
        # 提取情绪参数 - 添加详细调试信息
        emotional_guidance = chapter_params.get("emotional_guidance", {})
        
        current_emotional_focus = emotional_guidance.get("current_emotional_focus", "")
        target_intensity = emotional_guidance.get("target_intensity", "中")
        is_turning_point = emotional_guidance.get("is_emotional_turning_point", False)
        is_break_chapter = emotional_guidance.get("is_emotional_break_chapter", False)
        break_activities = emotional_guidance.get("break_activities", [])
        target_reader_emotion = emotional_guidance.get("target_reader_emotion", "期待与投入")
        key_scenes_design = emotional_guidance.get("key_scenes_design", "根据情节自然发展")
        
        # 构建情绪相关的提示词部分 - 修复版本
        emotional_context_parts = [
            f"**情绪发展指导**: {current_emotional_focus} (目标强度: {target_intensity})",
            f"**目标读者情绪**: {target_reader_emotion}",
            f"**关键场景设计**: {key_scenes_design}"
        ]
        
        if is_turning_point:
            turning_info = emotional_guidance.get("turning_point_info", {})
            emotional_shift = turning_info.get("emotional_shift", "重要情感变化")
            emotional_context_parts.append(f"**本章为情感转折点**: {emotional_shift}")
        
        if is_break_chapter:
            activities_text = ", ".join(break_activities)
            emotional_context_parts.append(f"**本章为情感缓冲章节**: 重点安排活动 - {activities_text}")
        
        emotional_context = "\n".join(emotional_context_parts)
        
        # 修复：正确构建 emotional_design 部分的 JSON 字符串
        emotional_design_extra = ""
        if is_break_chapter:
            emotional_design_extra += f',\n        "is_emotional_buffer": true,\n        "buffer_activities": {json.dumps(break_activities, ensure_ascii=False)}'
        
        if is_turning_point:
            turning_info = emotional_guidance.get("turning_point_info", {})
            emotional_shift = turning_info.get("emotional_shift", "重要情感变化")
            impact_description = turning_info.get("impact_description", "推动故事发展")
            
            if emotional_design_extra:
                emotional_design_extra += f',\n        "is_turning_point": true,\n        "turning_description": "{emotional_shift}",\n        "turning_impact": "{impact_description}"'
            else:
                emotional_design_extra += f',\n        "is_turning_point": true,\n        "turning_description": "{emotional_shift}",\n        "turning_impact": "{impact_description}"'
        
        # 如果没有任何额外内容，确保格式正确
        if not emotional_design_extra:
            emotional_design_extra = ""

        design_prompt = f"""
    你是一位顶级的网络小说总编辑。你的任务是消化所有背景资料，为一位顶级写手制定一份详尽的、自包含的"章节创作蓝图"。
    这位写手只会看到你输出的这份蓝图，所以你必须将所有必要的写作指令、风格要求、一致性提醒都整合进这份蓝图中。

    # 故事基础设定（供你参考）
    **小说标题**: {chapter_params.get("novel_title")}
    **小说简介**: {chapter_params.get("novel_synopsis")}
    {emotional_context}
    **世界观/角色/写作计划**: {chapter_params.get("worldview_info")}, {chapter_params.get("character_info")}, {chapter_params.get("stage_writing_plan")}
    **前情提要**: 
    {chapter_params.get("previous_chapters_summary")}
    **上下文指导**: 
    {chapter_params.get("event_driven_guidance")}, 
    {chapter_params.get("foreshadowing_guidance")}
    **角色发展指导**: 
    {chapter_params.get("character_development_guidance")}

    # 你的任务
    请根据以上所有信息，为第 {chapter_params.get("chapter_number")} 章生成一份JSON格式的"创作蓝图"。

    **【输出要求】**
    必须严格按照以下JSON结构输出，不要有任何增减或修改：
    {{
        "chapter_number": {chapter_params.get("chapter_number")},
        "chapter_title": "（为本章起一个富有吸引力的标题）",
        "chapter_summary": "（用一句话总结本章的核心内容和目的）",
        "emotional_design": {{
            "target_emotion": "{current_emotional_focus}",
            "emotional_intensity": "{target_intensity}",
            "emotional_arc_within_chapter": "（描述本章内部的情感发展曲线）",
            "key_emotional_moments": ["（列出本章的关键情感时刻）"],
            "reader_emotional_journey": "{target_reader_emotion}"{emotional_design_extra}
        }},
        "writing_style_directives": {{
            "core_tone": "（根据本章情节和情绪重点，指定核心基调）",
            "narrative_pace": "（指定叙事节奏，要配合情感强度）",
            "description_focus": ["（列出本章描写的重点，要服务于情感表达）"]
        }},
        "consistency_cheatsheet": {{
            "reminder": "（生成一段简短的一致性提醒，例如：'注意：主角此时还不知道反派的真实身份，不要在内心独白中泄露'）",
            "key_character_status": ["（列出本章出场角色的关键状态，例如：'秦峥：表面镇定，内心在谋划反击'）"],
            "relationship_check": ["（列出需要特别注意的人物关系，例如：'秦峥与卢斌的关系是初步震慑，互动时需体现卢斌的敬畏'）"]
        }},
        "scene_by_scene_outline": [
            {{
                "scene_number": 1,
                "scene_goal": "（明确场景目标，例如：'通过对话，展示主角的智谋和布局能力'）",
                "emotional_emphasis": "（这个场景要强调的情感）",
                "key_actions_and_dialogues": "（描述场景中的关键动作和对话要点）",
                "character_focus": "（指出这个场景主要刻画哪个角色的哪方面特质）"
            }},
            {{
                "scene_number": 2,
                "scene_goal": "...",
                "key_actions_and_dialogues": "...",
                "character_focus": "..."
            }}
        ],
        "foreshadowing_and_events": {{
            "elements_to_introduce": ["（明确列出本章需要首次引入的伏笔元素）"],
            "elements_to_develop": ["（明确列出本章需要进一步发展的已有伏笔）"]
        }},
        "next_chapter_hook": "（设计一个具体的、能引发读者好奇心的结尾悬念）"
    }}
    """
        print(f"  📝 生成第{chapter_params.get('chapter_number', 1)}章设计方案...")
        design_result = self.api_client.generate_content_with_retry(
            "chapter_design", 
            design_prompt, 
            purpose=f"制定第{chapter_params.get('chapter_number', 1)}章设计方案"
        )
        
        if design_result:
            print(f"  ✅ 第{chapter_params.get('chapter_number', 1)}章设计方案生成成功")
            # 验证情绪设计是否被正确包含
            if "emotional_design" in design_result:
                print(f"  🎭 设计方案包含情绪设计: {len['emotional_design']}")
            else:
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
        """从事件上下文中生成指导 - 添加错误处理"""
        
        if not event_context:
            print("   - 事件上下文为空，返回默认指导")
            return "# 🎯 事件执行指导\n\n事件上下文为空，按常规情节推进。"
        
        # 检查是否有活跃事件
        active_events = event_context.get("active_events", [])
        if not active_events:
            print("   - 无活跃事件，返回空窗期指导")
            empty_guidance = self._get_empty_period_guidance(chapter_number, event_context)
            # 确保返回的是字符串
            return empty_guidance if empty_guidance is not None else "# 🎯 事件执行指导\n\n本章暂无特定事件任务，按主线推进即可。"
        
        try:
            guidance_parts = ["# 🎯 事件执行指导", "## 活跃事件"]
            
            for event in event_context.get("active_events", []):
                print(f"   - 处理事件: {event.get('name')}")
                
                # 添加错误处理，确保关键字段存在
                event_name = event.get("name", "未知事件")
                main_goal = event.get("main_goal", "推进事件发展")
                current_stage_focus = event.get("current_stage_focus", "按计划推进")
                
                guidance_parts.extend([
                    f"### {event_name}",
                    f"**目标**: {main_goal}",
                    f"**当前重点**: {current_stage_focus}",
                    f"**关键时刻**:"
                ])
                
                # 处理关键时刻
                key_moments = event.get('key_moments', [])
                for moment in key_moments:
                    if isinstance(moment, dict):
                        description = moment.get('description', '')
                        guidance_parts.append(f"- {description}")
                    else:
                        guidance_parts.append(f"- {moment}")
            
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
        cultivation_text = self.quality_assessor.get_comprehensive_previous_summary_enhanced(chapter_params.get('novel_title'), chapter_design.get('chapter_number'))
        # 检查设计方案中的情绪设计
        emotional_design = chapter_design.get("emotional_design", {})
        print(f"  🎭 设计方案中的情绪设计: {emotional_design}")
        
        user_prompt = f"""
你是一位顶级的网络小说作家，文笔精湛，擅长叙事。

你的唯一任务是：严格、完整、并富有文采地执行以下【章节创作蓝图】，创作出小说《{chapter_params.get('novel_title')}》的第 {chapter_design.get('chapter_number')} 章。

【章节创作蓝图】
{json.dumps(chapter_design, ensure_ascii=False, indent=2)}
【写作风格】
{content_params.get('writing_style_guide',{})}
**前情提要**:
注意上下文衔接 
{chapter_params.get("previous_chapters_summary")}
{cultivation_text}
## 🎭 特别情绪指导
请特别关注情绪设计部分，确保本章的情感表达与以下要求一致：
- 情感重点: {emotional_design.get('target_emotion', '推进情感发展')}
- 情感强度: {emotional_design.get('emotional_intensity', '中')}
- 读者情感体验: {emotional_design.get('reader_emotional_journey', '期待与投入')}

在写作过程中，请时刻记住这些情感目标，通过对话、描写和心理活动来传达相应的情感。
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
                required_keys = ['core_style', 'language_features', 'narrative_pace', 
                            'dialogue_style', 'description_focus', 'emotional_tone',
                            'chapter_structure', 'important_notes']
                
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
        """构建一致性指导内容 - 按更新次数排序，重要元素优先"""
        guidance_parts = ["请严格确保与之前章节的一致性："]
        
        # 角色一致性 - 按更新次数排序
        characters = world_state.get('characters', {})
        if characters and isinstance(characters, dict):
            guidance_parts.append("### 👥 角色一致性（重要）")
            
            # 计算每个角色的更新次数并排序
            character_list = []
            for char_name, char_data in characters.items():
                if not isinstance(char_data, dict):
                    continue
                    
                try:
                    # 计算更新次数
                    update_count = self._calculate_update_count(char_data)
                    
                    # 安全提取字段
                    description = self._safe_get(char_data, 'description', '暂无描述')
                    
                    # 处理attributes字段
                    attributes = self._safe_get(char_data, 'attributes', {})
                    if not isinstance(attributes, dict):
                        attributes = {}
                    
                    status = self._safe_get(attributes, 'status') or self._safe_get(char_data, 'status', '活跃')
                    location = self._safe_get(attributes, 'location') or self._safe_get(char_data, 'location', '未知地点')
                    last_updated = self._safe_get(char_data, 'last_updated') or self._safe_get(char_data, 'last_updated_chapter', 0)
                    
                    character_list.append({
                        'name': char_name,
                        'description': description,
                        'status': status,
                        'location': location,
                        'last_updated': last_updated,
                        'update_count': update_count
                    })
                    
                except Exception as e:
                    print(f"⚠️ 处理角色 {char_name} 时出错: {e}")
                    continue
            
            # 按更新次数降序排序
            character_list.sort(key=lambda x: x['update_count'], reverse=True)
            
            # 显示前20个最重要的角色
            for char_info in character_list[:20]:
                guidance_parts.append(f"- **{char_info['name']}** (更新{char_info['update_count']}次)")
                guidance_parts.append(f"  - 状态: {char_info['status']}")
                guidance_parts.append(f"  - 位置: {char_info['location']}")
                guidance_parts.append(f"  - 最后更新: 第{char_info['last_updated']}章")
                
                if len(char_info['description']) > 80:
                    guidance_parts.append(f"  - 描述: {char_info['description'][:80]}...")
                else:
                    guidance_parts.append(f"  - 描述: {char_info['description']}")
        
        # 人物关系一致性 - 按更新次数排序
        relationships = world_state.get('relationships', {})
        if relationships and isinstance(relationships, dict):
            guidance_parts.append("### 🤝 人物关系（关键检查项）")
            
            relationship_list = []
            for rel_key, rel_data in relationships.items():
                if not isinstance(rel_data, dict):
                    continue
                    
                try:
                    # 计算更新次数
                    update_count = self._calculate_update_count(rel_data)
                    
                    rel_type = self._safe_get(rel_data, 'type') or self._safe_get(rel_data, 'relationship_type', '未知关系')
                    description = self._safe_get(rel_data, 'description', '暂无描述')
                    
                    parties = rel_key.split('-')
                    if len(parties) == 2:
                        relationship_list.append({
                            'key': rel_key,
                            'type': rel_type,
                            'description': description,
                            'parties': parties,
                            'update_count': update_count
                        })
                        
                except Exception as e:
                    print(f"⚠️ 处理关系 {rel_key} 时出错: {e}")
                    continue
            
            # 按更新次数降序排序
            relationship_list.sort(key=lambda x: x['update_count'], reverse=True)
            
            # 显示前32个最重要的关系
            for rel_info in relationship_list[:32]:
                char_a, char_b = rel_info['parties']
                guidance_parts.append(f"- **{char_a}** ↔ **{char_b}** (更新{rel_info['update_count']}次)")
                guidance_parts.append(f"  - 关系类型: {rel_info['type']}")
                
                if len(rel_info['description']) > 60:
                    guidance_parts.append(f"  - 关系描述: {rel_info['description'][:60]}...")
                else:
                    guidance_parts.append(f"  - 关系描述: {rel_info['description']}")
        
        # 物品一致性 - 按更新次数排序
        items = world_state.get('items', {})
        if items and isinstance(items, dict):
            guidance_parts.append("### 🎁 物品归属")
            
            item_list = []
            for item_name, item_data in items.items():
                if not isinstance(item_data, dict):
                    continue
                    
                try:
                    # 计算更新次数
                    update_count = self._calculate_update_count(item_data)
                    
                    owner = self._safe_get(item_data, 'owner', '未知')
                    status = self._safe_get(item_data, 'status') or self._safe_get(item_data, 'item_status', '未知状态')
                    description = self._safe_get(item_data, 'description', '暂无描述')
                    location = self._safe_get(item_data, 'location', '未知位置')
                    
                    item_list.append({
                        'name': item_name,
                        'owner': owner,
                        'status': status,
                        'description': description,
                        'location': location,
                        'update_count': update_count
                    })
                    
                except Exception as e:
                    print(f"⚠️ 处理物品 {item_name} 时出错: {e}")
                    continue
            
            # 按更新次数降序排序
            item_list.sort(key=lambda x: x['update_count'], reverse=True)
            
            # 显示前16个最重要的物品
            for item_info in item_list[:16]:
                guidance_parts.append(f"- **{item_info['name']}** (更新{item_info['update_count']}次)")
                guidance_parts.append(f"  - 拥有者: {item_info['owner']}")
                guidance_parts.append(f"  - 状态: {item_info['status']}")
                guidance_parts.append(f"  - 位置: {item_info['location']}")
                
                if len(item_info['description']) > 60:
                    guidance_parts.append(f"  - 描述: {item_info['description'][:60]}...")
                else:
                    guidance_parts.append(f"  - 描述: {item_info['description']}")
        
        # 技能一致性 - 按更新次数排序
        skills = world_state.get('skills', {})
        if skills and isinstance(skills, dict):
            guidance_parts.append("### 🔧 技能状态")
            
            skill_list = []
            for skill_name, skill_data in skills.items():
                if not isinstance(skill_data, dict):
                    continue
                    
                try:
                    # 计算更新次数
                    update_count = self._calculate_update_count(skill_data)
                    
                    owner = self._safe_get(skill_data, 'owner', '未知')
                    level = self._safe_get(skill_data, 'level') or self._safe_get(skill_data, 'skill_level', '未知等级')
                    description = self._safe_get(skill_data, 'description', '暂无描述')
                    
                    skill_list.append({
                        'name': skill_name,
                        'owner': owner,
                        'level': level,
                        'description': description,
                        'update_count': update_count
                    })
                    
                except Exception as e:
                    print(f"⚠️ 处理技能 {skill_name} 时出错: {e}")
                    continue
            
            # 按更新次数降序排序
            skill_list.sort(key=lambda x: x['update_count'], reverse=True)
            
            # 显示前3个最重要的技能
            for skill_info in skill_list[:3]:
                guidance_parts.append(f"- **{skill_info['name']}** (更新{skill_info['update_count']}次)")
                guidance_parts.append(f"  - 拥有者: {skill_info['owner']}")
                guidance_parts.append(f"  - 等级: {skill_info['level']}")
                
                if len(skill_info['description']) > 60:
                    guidance_parts.append(f"  - 描述: {skill_info['description'][:60]}...")
                else:
                    guidance_parts.append(f"  - 描述: {skill_info['description']}")
        
        # 地点一致性 - 按更新次数排序
        locations = world_state.get('locations', {})
        if locations and isinstance(locations, dict):
            guidance_parts.append("### 🗺️ 地点状态")
            
            location_list = []
            for loc_name, loc_data in locations.items():
                if not isinstance(loc_data, dict):
                    continue
                    
                try:
                    # 计算更新次数
                    update_count = self._calculate_update_count(loc_data)
                    
                    description = self._safe_get(loc_data, 'description', '暂无描述')
                    
                    location_list.append({
                        'name': loc_name,
                        'description': description,
                        'update_count': update_count
                    })
                    
                except Exception as e:
                    print(f"⚠️ 处理地点 {loc_name} 时出错: {e}")
                    continue
            
            # 按更新次数降序排序
            location_list.sort(key=lambda x: x['update_count'], reverse=True)
            
            # 显示前12个最重要的地点
            for loc_info in location_list[:12]:
                guidance_parts.append(f"- **{loc_info['name']}** (更新{loc_info['update_count']}次): {loc_info['description']}")
        
        # 添加关系检查的特别提醒
        guidance_parts.extend([
            "",
            "## ⚠️ 关系一致性特别提醒",
            "1. **禁止重复建立关系**: 已经认识的角色之间不需要再次介绍或建立关系",
            "2. **关系状态延续**: 保持角色间已有的关系状态（友好、敌对、合作等）", 
            "3. **关系发展自然**: 如需改变关系状态，必须有合理的情节发展",
            "4. **避免关系矛盾**: 新建立的关系不能与已有关系冲突",
            "5. **关系记忆**: 角色应该记得彼此之前的重要互动"
        ])
        
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

    def _save_chapter_failure(self, novel_data: Dict, chapter_number: int, failure_reason: str, failure_details: Dict):
        """保存章节生成失败信息"""
        try:
            failure_record = {
                "novel_title": novel_data.get("novel_title", "未知小说"),
                "chapter_number": chapter_number,
                "failure_time": self._get_current_timestamp(),
                "failure_reason": failure_reason,
                "failure_details": failure_details,
                "novel_category": novel_data.get("category", "未知分类"),
                "main_character": self.custom_main_character_name,
                "generation_context": {
                    "has_context": novel_data.get('_current_generation_context') is not None,
                    "context_keys": list(novel_data.keys()) if novel_data else []
                }
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