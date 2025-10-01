import json
from typing import Dict, Optional

class ContentGenerator:
    def __init__(self, api_client, config, quality_assessor=None):
        self.api_client = api_client
        self.config = config
        self.quality_assessor = quality_assessor
        self.custom_main_character_name = None
    
    def set_custom_main_character_name(self, name: str):
        self.custom_main_character_name = name
        print(f"✓ 内容生成器已设置主角名字: {name}")
    
    def _inject_main_character_name(self, prompt: str, context: str = "") -> str:
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
        if not self.custom_main_character_name:
            return content
        
        if content_type == "three_plans":
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
        escaped_template = template.replace('{', '{{').replace('}', '}}')
        
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            escaped_placeholder = f"{{{{{key}}}}}"
            escaped_template = escaped_template.replace(escaped_placeholder, placeholder)
        
        return escaped_template.format(**kwargs)
    
    def generate_three_plans(self, creative_seed: str) -> Optional[Dict]:
        print("=== 步骤1: 基于番茄小说流量趋势生成三套方案 ===")
        
        user_prompt = f"创意种子: {creative_seed}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("three_plans", user_prompt, purpose="生成三套小说方案")
        if result:
            result = self._ensure_main_character_in_content(result, "three_plans")
        return result

    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        if result:
            result = self._assess_and_optimize_content(result, "market_analysis", "市场分析")
            result = self._ensure_main_character_in_content(result, "market_analysis")
        return result

    def generate_writing_plan(self, creative_seed: str, selected_plan: Dict, 
                            market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        print("=== 步骤3: 制定写作计划 ===")
        
        try:
            prompt_template = self.config["prompts"]["writing_plan"]
            system_prompt = self.safe_format(prompt_template, total_chapters=total_chapters)
            
            user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}\n市场分析: {json.dumps(market_analysis, ensure_ascii=False)}"
            if self.custom_main_character_name:
                user_prompt += f"\n主角名字: {self.custom_main_character_name}"
            
            complete_user_prompt = f"{system_prompt}\n\n{user_prompt}\n\n# 额外要求\n请确保严格遵循上述所有要求，特别是JSON格式输出。"
            
            result = self.api_client.generate_content_with_retry("writing_plan", complete_user_prompt, purpose="制定写作计划")
            if result:
                result = self._assess_and_optimize_content(result, "writing_plan", "写作计划")
                result = self._ensure_main_character_in_content(result, "writing_plan")
                result = self.fix_writing_plan_chapters(result, total_chapters)
            return result
        except Exception as e:
            print(f"❌ 生成写作计划时出错: {e}")
            return None

    def fix_writing_plan_chapters(self, writing_plan: Dict, total_chapters: int) -> Dict:
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

    def generate_core_worldview(self, novel_title: str, novel_synopsis: str, selected_plan: Dict, writing_plan: Dict) -> Optional[Dict]:
        print("=== 步骤4: 构建核心世界观 ===")
        
        context = f"""小说标题: {novel_title}
            小说简介: {novel_synopsis}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            写作计划: {json.dumps(writing_plan, ensure_ascii=False)}"""
        
        if self.custom_main_character_name:
            context += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="构建世界观")
        if result:
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观")
            result = self._ensure_main_character_in_content(result, "core_worldview")
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, writing_plan: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        print("=== 步骤5: 设计主要角色 ===")
        
        main_character_name = custom_main_character_name or self.custom_main_character_name
        
        context = f"""小说标题: {novel_title}
            核心世界观: {json.dumps(core_worldview, ensure_ascii=False)}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            写作计划: {json.dumps(writing_plan, ensure_ascii=False)}"""
        
        if main_character_name:
            context += f"\n\n【强制要求】主角的名字必须是: {main_character_name}"
            print(f"✓ 角色设计使用主角名字: {main_character_name}")
        
        result = self.api_client.generate_content_with_retry("character_design", context, purpose="角色设计")
        
        if result:
            result = self._assess_and_optimize_content(result, "character_design", "角色设计")
            if main_character_name:
                result = self.ensure_main_character_name(result, main_character_name)
        
        return result

    def ensure_main_character_name(self, character_design: Dict, custom_name: str) -> Dict:
        if "main_character" in character_design and "name" in character_design["main_character"]:
            original_name = character_design["main_character"]["name"]
            if original_name != custom_name:
                print(f"⚠️  将主角名字从 '{original_name}' 改为 '{custom_name}'")
                character_design["main_character"]["name"] = custom_name
                character_design["main_character"]["original_name"] = original_name
        
        return character_design

    def _assess_and_optimize_content(self, content: Dict, content_type: str, original_purpose: str) -> Dict:
        if not content or not hasattr(self, 'quality_assessor') or self.quality_assessor is None:
            return content
        
        print(f"🔍 评估{original_purpose}质量...")
        
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

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        required_keys = ['chapter_number', 'total_chapters', 'novel_title', 'novel_synopsis', 
                        'worldview_info', 'character_info', 'writing_plan_info', 'event_driven_guidance','foreshadowing_guidance',
                        'previous_chapters_summary', 'main_plot_progress', 'plot_direction',
                        'chapter_connection_note']
        
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
            safe_params = chapter_params.copy()
            safe_params.setdefault('major_event_info', '')
            safe_params.setdefault('event_specific_requirements', '')
            safe_params.setdefault('foreshadowing_guidance', '')
            safe_params.setdefault('character_development_focus', '')
            safe_params.setdefault('main_character_instruction', '')
            safe_params.setdefault('event_driven_guidance', '')
            
            prompt_template = self.config["prompts"]["chapter_generation"]
            user_prompt = prompt_template.format(**safe_params)
            
            result = self.api_client.generate_content_with_retry(
                "chapter_generation", 
                user_prompt, 
                purpose=f"生成第{safe_params['chapter_number']}章内容"
            )
            
            return result
        except KeyError as e:
            print(f"❌ 格式化提示词时缺少参数: {e}")
            return None
        except Exception as e:
            print(f"❌ 生成章节内容时出错: {e}")
            return None