"""内容生成器类 - 专注内容生成"""

import json
import re
from typing import Dict, Optional, List, Tuple

import APIClient
from Contexts import GenerationContext
from Prompts import Prompts

class ContentGenerator:
    def __init__(self, novel_generator, api_client: APIClient, config, event_bus, quality_assessor):
        self.novel_generator = novel_generator
        self.api_client = api_client
        self.config = config
        self.prompts = Prompts
        self.event_bus = event_bus
        self.quality_assessor = None
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
        
        user_prompt = f"创意种子: {creative_seed}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        if category:
            user_prompt += f"\n小说分类: {category}"
        
        result = self.api_client.generate_content_with_retry("one_plans", user_prompt, purpose="生成小说方案")
        if result:
            result = self._ensure_main_character_in_content(result, "one_plans")
        return result
    
    def _generate_character_name_by_category(self, category: str, creative_seed: str) -> str:
        """根据分类生成适合的主角名字"""
        try:
            print(f"  🎯 开始为分类 '{category}' 生成主角名字...")
            
            user_prompt = f"\n小说分类：{category}\n创意种子：{creative_seed}"
            
            result = self.api_client.generate_content_with_retry(
                "character_naming",
                user_prompt,
                purpose="生成主角名字"
            )
            
            if result:
                # 直接使用解析后的字典，不需要再调用 json.loads
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
            "西方奇幻": "艾伦",
            "东方仙侠": "林风", 
            "科幻末世": "陆晨",
            "男频衍生": "陈默",
            "都市高武": "张扬",
            "悬疑灵异": "秦风",
            "悬疑脑洞": "时雨",
            "抗战谍战": "李战",
            "历史古代": "赵明",
            "历史脑洞": "楚云",
            "都市种田": "王磊",
            "都市脑洞": "苏哲",
            "都市日常": "刘阳",
            "玄幻脑洞": "萧炎",
            "战神赘婿": "叶枫",
            "动漫衍生": "星尘",
            "游戏体育": "陈飞",
            "传统玄幻": "林凡",
            "都市修真": "张凡"
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

    def generate_writing_plan(self, creative_seed: str, selected_plan: Dict, 
                            market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        """生成写作计划"""
        print("=== 步骤3: 制定写作计划 ===")
        
        try:
            prompt_template = self.prompts["prompts"]["overall_stage_plan"]
            system_prompt = self.safe_format(prompt_template, total_chapters=total_chapters)
            
            user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}\n"
            if self.custom_main_character_name:
                user_prompt += f"\n主角名字: {self.custom_main_character_name}"
            
            complete_user_prompt = f"{system_prompt}\n\n{user_prompt}\n\n# 额外要求\n请确保严格遵循上述所有要求，特别是JSON格式输出。"
            
            result = self.api_client.generate_content_with_retry("overall_stage_plan", complete_user_prompt, purpose="制定写作计划")
            if result:
                result = self._assess_and_optimize_content(result, "writing_plan", "写作计划")
                result = self._ensure_main_character_in_content(result, "writing_plan")
                result = self.fix_writing_plan_chapters(result, total_chapters)
            return result
        except Exception as e:
            print(f"❌ 生成写作计划时出错: {e}")
            return None

    def fix_writing_plan_chapters(self, writing_plan: Dict, total_chapters: int) -> Dict:
        """修复写作计划中的章节范围"""
        if not writing_plan or "chapter_rhythm" not in writing_plan:
            return writing_plan
        
        chapter_rhythm = writing_plan["chapter_rhythm"]
        chapter_ranges = self.calculate_chapter_ranges(total_chapters)
        
        import re
        
        if "opening_chapters" in chapter_rhythm:
            original_desc = chapter_rhythm["opening_chapters"]
            cleaned_desc = re.sub(r'^前\d+章\s*', '', original_desc)
            chapter_rhythm["opening_chapters"] = f"前{chapter_ranges['opening']}章{cleaned_desc}"
        
        if "development_phase" in chapter_rhythm:
            original_desc = chapter_rhythm["development_phase"]
            cleaned_desc = re.sub(r'^\d+-\d+章\s*', '', original_desc)
            chapter_rhythm["development_phase"] = f"{chapter_ranges['development_start']}-{chapter_ranges['development_end']}章{cleaned_desc}"
        
        if "climax_phase" in chapter_rhythm:
            original_desc = chapter_rhythm["climax_phase"]
            cleaned_desc = re.sub(r'^\d+-\d+章\s*', '', original_desc)
            chapter_rhythm["climax_phase"] = f"{chapter_ranges['climax_start']}-{chapter_ranges['climax_end']}章{cleaned_desc}"
        
        if "ending_phase" in chapter_rhythm:
            original_desc = chapter_rhythm["ending_phase"]
            cleaned_desc = re.sub(r'^\d+-\d+章\s*', '', original_desc)
            chapter_rhythm["ending_phase"] = f"{chapter_ranges['ending_start']}-{chapter_ranges['ending_end']}章{cleaned_desc}"
        
        writing_plan["chapter_rhythm"] = chapter_rhythm
        return writing_plan

    def calculate_chapter_ranges(self, total_chapters: int) -> Dict:
        """计算章节范围"""
        opening_ratio = 0.1
        development_ratio = 0.5
        climax_ratio = 0.3
        ending_ratio = 0.1
        
        opening_end = int(total_chapters * opening_ratio)
        development_start = opening_end + 1
        development_end = development_start + int(total_chapters * development_ratio) - 1
        climax_start = development_end + 1
        climax_end = climax_start + int(total_chapters * climax_ratio) - 1
        ending_start = climax_end + 1
        ending_end = total_chapters
        
        return {
            "opening": opening_end,
            "development_start": development_start,
            "development_end": development_end,
            "climax_start": climax_start,
            "climax_end": climax_end,
            "ending_start": ending_start,
            "ending_end": ending_end
        }

    def generate_core_worldview(self, novel_title: str, novel_synopsis: str, selected_plan: Dict, market_analysis: Dict) -> Optional[Dict]:
        """生成核心世界观"""
        
        context = f"""小说标题: {novel_title}
            小说简介: {novel_synopsis}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            市场分析: {json.dumps(market_analysis, ensure_ascii=False)}"""
        
        if self.custom_main_character_name:
            context += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="构建世界观")
        if result:
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观")
            result = self._ensure_main_character_in_content(result, "core_worldview")
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, market_analysis: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计"""
        print("=== 步骤5: 设计主要角色 ===")
        
        main_character_name = custom_main_character_name or self.custom_main_character_name
        
        context = f"""小说标题: {novel_title}
            核心世界观: {json.dumps(core_worldview, ensure_ascii=False)}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"""
        
        if main_character_name:
            context += f"\n\n【强制要求】主角的名字必须是: {main_character_name}"
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

        # 存储上下文供后续使用
        novel_data['_current_generation_context'] = context
        
        # 记录上下文信息
        print(f"  📊 上下文信息:")
        print(f"    - 事件上下文: {len(context.event_context)} 项")
        print(f"    - 伏笔上下文: {len(context.foreshadowing_context)} 项") 
        print(f"    - 成长上下文: {len(context.growth_context)} 项")  

        # 准备章节参数
        chapter_params = self._prepare_chapter_params(chapter_number, novel_data)
        
        if not chapter_params or not self._validate_chapter_params(chapter_params):
            print(f"❌ 第{chapter_number}章参数准备失败")
            return None
        
        print(f"  ✅ 第{chapter_number}章所有参数验证通过")
        
        # 使用严格的两步法生成章节内容，包含字数检查
        max_retries = 3
        for attempt in range(max_retries):
            chapter_data = self.generate_chapter_content(chapter_params)
            if not chapter_data:
                print(f"✗ 第{chapter_number}章生成失败")
                return None
            
            # 检查字数
            word_count = chapter_data.get("word_count", 0)
            content_length = len(chapter_data.get("content", ""))
            
            print(f"  📝 第{attempt + 1}次生成结果: {word_count}字 (内容长度: {content_length}字符)")
            
            # 如果字数少于1500，重新生成
            if word_count >= 1500:
                print(f"  ✅ 字数达标: {word_count}字")
                break
            else:
                print(f"  ⚠️ 字数不足: {word_count}字 < 1500字，重新生成...")
                if attempt == max_retries - 1:
                    print(f"  ❌ 达到最大重试次数，使用当前内容")
        
        # 确保章节标题唯一性
        chapter_data = self._handle_chapter_title_uniqueness(chapter_data, chapter_number, novel_data)
        
        # 质量评估
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
                    print(f"  ✅ 成功提取结尾: {ending[:120]}...")
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
            'event_driven_guidance', 'foreshadowing_guidance'
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
        if score < 7.5:
            return True, f"评分低于优化阈值7.5分，需要优化"
        
        # 建议优化范围
        if score < 8.0:
            return True, "质量合格但建议优化提升"
        
        return False, "质量良好，跳过优化"

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节内容 - 严格两步法：先设计方案，再生成内容"""
        required_keys = ['chapter_number', 'total_chapters', 'novel_title', 'novel_synopsis', 
                        'worldview_info', 'character_info', 'writing_plan_info', 'event_driven_guidance','foreshadowing_guidance',
                        'previous_chapters_summary', 'main_plot_progress', 'plot_direction',
                        'chapter_connection_note']
        
        # 参数验证和修复逻辑
        missing_keys = [key for key in required_keys if key not in chapter_params]
        if missing_keys:
            for key in missing_keys:
                if key == 'event_driven_guidance':
                    chapter_params[key] = "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"
                elif key == 'foreshadowing_guidance':
                    chapter_params[key] = "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
                elif key == 'character_development_focus':
                    chapter_params[key] = "角色正常发展"
                else:
                    chapter_params[key] = "未提供"
        
        empty_params = [key for key in required_keys if key in chapter_params and not chapter_params[key]]
        if empty_params:
            for key in empty_params:
                if key == 'foreshadowing_guidance':
                    chapter_params[key] = "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
                elif key == 'event_driven_guidance':
                    chapter_params[key] = "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"
        
        try:
            # 第一步：生成章节设计方案
            print(f"  📝 生成第{chapter_params['chapter_number']}章设计方案...")
            chapter_design = self.generate_chapter_design(chapter_params)
            if not chapter_design:
                print(f"  ❌ 第{chapter_params['chapter_number']}章设计方案生成失败，终止生成")
                return None
            
            print(f"  ✍️ 根据设计方案生成第{chapter_params['chapter_number']}章内容...")
            chapter_content = self.generate_chapter_content_from_design(chapter_params, chapter_design)
            if not chapter_content:
                print(f"  ❌ 第{chapter_params['chapter_number']}章内容生成失败")
                return None
            
            print(f"  ✅ 第{chapter_params['chapter_number']}章生成成功")
            return chapter_content
                
        except Exception as e:
            print(f"❌ 生成第{chapter_params['chapter_number']}章内容时出错: {e}")
            return None
        
    def generate_chapter_design(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节详细设计方案"""
        try:
            design_prompt = f"""你是一位资深的网络小说策划编辑。请为第{chapter_params.get("chapter_number", 1)}章制定详细的写作设计方案。

    # 故事基础设定（必须严格遵循）
    **小说标题**: 
    {chapter_params.get("novel_title", "未知小说")}
    **小说简介**: 
    {chapter_params.get("novel_synopsis", "")}
    **世界观设定**: 
    {chapter_params.get("worldview_info", "{}")}
    **角色设定**: 
    {chapter_params.get("character_info", "{}")}
    **写作计划**: 
    {chapter_params.get("stage_writing_plan", "{}")}

    {chapter_params.get("main_character_instruction", "")}

    # 上下文信息
    **前情提要**: 
    {chapter_params.get("previous_chapters_summary", "")}
    **本章定位**: 
    第{chapter_params.get("chapter_number", 1)}/{chapter_params.get("total_chapters", 30)}章 - {chapter_params.get("plot_direction", "")}
    **重点推进**: 
    {chapter_params.get("main_plot_progress", "")}
    **角色发展重点**: 
    {chapter_params.get("character_development_focus", "")}
    **衔接要求**: 
    {chapter_params.get("chapter_connection_note", "")}

    # 事件驱动指导
    {chapter_params.get("event_driven_guidance", "123")}

    # 伏笔铺垫指导
    {chapter_params.get("foreshadowing_guidance", "123")}
"""

            print(f"  📝 生成第{chapter_params.get('chapter_number', 1)}章设计方案...")
            design_result = self.api_client.generate_content_with_retry(
                "chapter_design", 
                design_prompt, 
                purpose=f"制定第{chapter_params.get('chapter_number', 1)}章设计方案"
            )
            
            if design_result:
                print(f"  ✅ 第{chapter_params.get('chapter_number', 1)}章设计方案生成成功")
                return design_result
            else:
                print(f"  ❌ 第{chapter_params.get('chapter_number', 1)}章设计方案生成失败")
                return None
                
        except Exception as e:
            print(f"  ❌ 生成章节设计方案时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _prepare_chapter_params(self, chapter_number: int, novel_data: Dict) -> Dict:
        """准备章节参数 - 增强版本，使用上下文"""
        print(f"  🔍 准备第{chapter_number}章参数...")
        
        # 获取上下文
        context = novel_data.get('_current_generation_context')
        
        if context:
            print(f"  ✅ 使用上下文信息准备参数")
            # 使用上下文中的详细信息
            event_context = context.event_context
            foreshadowing_context = context.foreshadowing_context  
            growth_context = context.growth_context

            print(f"  📊 上下文信息:")
            print(f"    - 事件上下文: {len(event_context.get('active_events', []))} 个活跃事件")
            print(f"    - 伏笔上下文: {len(foreshadowing_context.get('elements_to_introduce', []))} 个待引入元素") 
            print(f"    - 成长上下文: {len(growth_context.get('chapter_specific', {}))} 项成长规划")  
            
            # 获取事件指导（优先使用上下文中的信息）
            event_guidance = self._get_event_guidance_from_context(event_context)
            foreshadowing_guidance = self._get_foreshadowing_guidance_from_context(foreshadowing_context, chapter_number)
            print(f"    - 事件指导: \n{event_guidance} ") 
            print(f"    - 伏笔指导: \n{foreshadowing_guidance} ") 
            # 从上下文中获取阶段计划
            stage_writing_plan = context.stage_plan if hasattr(context, 'stage_plan') else {}
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
        
        params = {
            "chapter_number": chapter_number,
            "total_chapters": total_chapters,
            "novel_title": novel_data["novel_title"],
            "novel_synopsis": novel_data["novel_synopsis"],
            "worldview_info": json.dumps(novel_data["core_worldview"], ensure_ascii=False) if novel_data["core_worldview"] else "{}",
            "character_info": json.dumps(novel_data["character_design"], ensure_ascii=False) if novel_data["character_design"] else "{}",
            "stage_writing_plan": stage_writing_plan,
            "previous_chapters_summary": self._generate_previous_chapters_summary(chapter_number, novel_data),
            "main_plot_progress": plot_direction["plot_direction"],
            "plot_direction": plot_direction["plot_direction"],
            "chapter_connection_note": self._get_chapter_connection_note(chapter_number),
            "character_development_focus": plot_direction.get("character_development_focus", ""),
            "main_character_instruction": self._get_main_character_instruction(novel_data),
            "event_driven_guidance": event_guidance,
            "foreshadowing_guidance": foreshadowing_guidance,
            # 新增：上下文详细信息
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
        
        return params

    def _get_event_guidance_from_context(self, event_context: Dict) -> str:
        """从事件上下文中生成指导 - 添加错误处理"""
        print(f"   - 输入event_context类型: {type(event_context)}")
        print(f"   - 输入event_context键: {list(event_context.keys()) if event_context else 'None'}")
        
        if not event_context or not event_context.get("active_events"):
            print("   - 无活跃事件，返回默认指导")
            return "# 🎯 事件执行指导\n\n本章暂无特定事件执行任务。"
        
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
        """从伏笔上下文中生成指导"""
        if not foreshadowing_context:
            return "# 🎭 伏笔铺垫指导\n\n本章暂无特定的伏笔任务。"
        
        guidance_parts = ["# 🎭 伏笔铺垫指导", f"## {foreshadowing_context.get('foreshadowing_focus', '本章伏笔重点')}"]
        
        elements_to_introduce = foreshadowing_context.get("elements_to_introduce", [])
        if elements_to_introduce:
            guidance_parts.append("## 需要引入的元素:")
            for element in elements_to_introduce:
                guidance_parts.append(f"- **{element.get('name', '')}** ({element.get('type', '')}): {element.get('purpose', '')}")
        
        elements_to_develop = foreshadowing_context.get("elements_to_develop", [])
        if elements_to_develop:
            guidance_parts.append("## 需要发展的元素:")
            for element in elements_to_develop:
                guidance_parts.append(f"- **{element.get('name', '')}** ({element.get('type', '')}): {element.get('development_arc', '')}")
        
        return "\n".join(guidance_parts)

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
        """根据设计方案生成章节内容 - 修复版本"""
        try:
            # 准备内容生成参数，包含所有基础设定
            content_params = chapter_params.copy()
            content_params["chapter_design"] = json.dumps(chapter_design, ensure_ascii=False, indent=2)
            content_params["chapter_title"] = chapter_design.get("chapter_title", f"第{chapter_params['chapter_number']}章")
            content_params["main_character_instruction"] = content_params.get("main_character_instruction", "")
            
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
            
            # 直接构建内容生成提示词，不依赖 self.prompts
            user_prompt = f"""你是一位优秀的网络小说作家。请根据以下详细设计方案和基础设定，生成第{chapter_params['chapter_number']}章的完整内容。

    # 基础设定（必须严格遵循）
    **小说标题**: 
    {content_params.get('novel_title', '未知小说')}
    **小说简介**: 
    {content_params.get('novel_synopsis', '')}
    {content_params.get('main_character_instruction', '')}

    # 章节详细设计方案
    {content_params.get('chapter_design', '{}')}

    # 核心写作要求

    ## 1. 严格遵循设定
    - **世界观一致性**: 所有元素必须符合世界观设定：
    {content_params.get('worldview_info', '{}')}
    - **角色一致性**: 角色行为必须符合角色设定：
    {content_params.get('character_info', '{}')}
    - **情节连贯性**: 必须遵循写作计划：
    {content_params.get('stage_writing_plan', '{}')}

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
                print(f"  ✅ 第{chapter_params['chapter_number']}章内容生成成功")
                return content_result
            else:
                print(f"  ❌ 第{chapter_params['chapter_number']}章内容生成失败")
                return None
                
        except Exception as e:
            print(f"  ❌ 根据设计方案生成章节内容时出错: {e}")
            import traceback
            traceback.print_exc()
            return None