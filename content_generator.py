import json
from typing import Dict, Optional

class ContentGenerator:
    def __init__(self, api_client, config, quality_assessor=None):
        self.api_client = api_client
        self.config = config
        self.quality_assessor = quality_assessor  # 添加 quality_assessor
        self.custom_main_character_name = None
    
    def set_custom_main_character_name(self, name: str):
        """设置自定义主角名字"""
        self.custom_main_character_name = name
        print(f"✓ 内容生成器已设置主角名字: {name}")
    
    def _inject_main_character_name(self, prompt: str, context: str = "") -> str:
        """在所有提示词中注入主角名字"""
        if not self.custom_main_character_name:
            return prompt
        
        # 在提示词开头添加主角名字要求
        name_instruction = f"\n\n【重要提示】主角的名字必须是: {self.custom_main_character_name}\n"
        
        # 检查是否已经有重要提示，避免重复
        if "【重要提示】" in prompt:
            # 替换已有的主角名字提示
            import re
            prompt = re.sub(r"【重要提示】.*?\n", name_instruction, prompt)
        else:
            # 在系统提示词后添加
            lines = prompt.split('\n')
            if lines and lines[0].startswith('你是一位'):
                # 在角色描述后插入
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
        """确保内容中包含自定义主角名字"""
        if not self.custom_main_character_name:
            return content
        
        if content_type == "three_plans":
            # 检查三套方案中是否使用了主角名字
            for plan in content.get("plans", []):
                if self.custom_main_character_name not in plan.get("synopsis", "") and self.custom_main_character_name not in plan.get("title", ""):
                    print(f"⚠️  方案中未使用主角名字 '{self.custom_main_character_name}'，正在修正...")
                    # 在简介中插入主角名字
                    plan["synopsis"] = plan["synopsis"].replace("主角", self.custom_main_character_name)
        
        elif content_type == "market_analysis":
            # 市场分析中可能不需要直接提及主角名字
            pass
        
        elif content_type == "writing_plan":
            # 确保写作计划中提到主角名字
            writing_approach = content.get("writing_approach", "")
            character_growth = content.get("character_growth_arc", "")
            
            if self.custom_main_character_name not in writing_approach and self.custom_main_character_name not in character_growth:
                print(f"⚠️  写作计划中未使用主角名字，正在修正...")
                if "主角" in writing_approach:
                    content["writing_approach"] = writing_approach.replace("主角", self.custom_main_character_name)
                if "主角" in character_growth:
                    content["character_growth_arc"] = character_growth.replace("主角", self.custom_main_character_name)
        
        elif content_type == "core_worldview":
            # 世界观中可能不需要直接提及主角名字
            pass
        
        return content

    def safe_format(self, template: str, **kwargs) -> str:
        """安全的字符串格式化，避免JSON结构被误格式化"""
        # 先将所有花括号转义
        escaped_template = template.replace('{', '{{').replace('}', '}}')
        
        # 然后只取消转义我们需要替换的字段
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            escaped_placeholder = f"{{{{{key}}}}}"
            escaped_template = escaped_template.replace(escaped_placeholder, placeholder)
        
        # 现在安全地进行格式化
        return escaped_template.format(**kwargs)
    
    def generate_three_plans(self, creative_seed: str) -> Optional[Dict]:
        """生成三套完整的小说方案 - 包含主角名字"""
        print("=== 步骤1: 基于番茄小说流量趋势生成三套方案 ===")
        
        user_prompt = f"创意种子: {creative_seed}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        # 使用API客户端生成内容
        result = self.api_client.generate_content_with_retry("three_plans", user_prompt, purpose="生成三套小说方案")
        if result:
            result = self._ensure_main_character_in_content(result, "three_plans")
        return result

    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析和卖点提炼 - 包含主角名字"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        if result:
            result = self._ensure_main_character_in_content(result, "market_analysis")
        return result

    def generate_writing_plan(self, creative_seed: str, selected_plan: Dict, 
                            market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        """生成写作计划 - 修复版本"""
        print("=== 步骤3: 制定写作计划 ===")
        
        try:
            prompt_template = self.config["prompts"]["writing_plan"]
            system_prompt = self.safe_format(prompt_template, total_chapters=total_chapters)
            
            user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}\n市场分析: {json.dumps(market_analysis, ensure_ascii=False)}"
            if self.custom_main_character_name:
                user_prompt += f"\n主角名字: {self.custom_main_character_name}"
            
            result = self.api_client.generate_content_with_retry("writing_plan", user_prompt, purpose="制定写作计划")
            if result:
                result = self._ensure_main_character_in_content(result, "writing_plan")
                result = self.fix_writing_plan_chapters(result, total_chapters)
            return result
        except Exception as e:
            print(f"❌ 生成写作计划时出错: {e}")
            return None

    def fix_writing_plan_chapters(self, writing_plan: Dict, total_chapters: int) -> Dict:
        """修复写作计划中的章节分配，确保与总章节数匹配"""
        if not writing_plan or "chapter_rhythm" not in writing_plan:
            return writing_plan
        
        chapter_rhythm = writing_plan["chapter_rhythm"]
        
        # 计算合理的章节分配
        chapter_ranges = self.calculate_chapter_ranges(total_chapters)
        
        # 更新章节节奏描述
        if "opening_chapters" in chapter_rhythm:
            # 保留原有的描述风格，只更新章节数
            original_desc = chapter_rhythm["opening_chapters"]
            # 提取原有的描述内容（去除章节数部分）
            import re
            # 移除开头的章节数描述
            cleaned_desc = re.sub(r'^前\d+章\s*', '', original_desc)
            chapter_rhythm["opening_chapters"] = f"前{chapter_ranges['opening']}章{cleaned_desc}"
        
        # 类似地更新其他阶段
        if "development_phase" in chapter_rhythm:
            original_desc = chapter_rhythm["development_phase"]
            # 移除开头的章节数描述
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
        """根据总章节数计算合理的章节范围"""
        # 标准分配比例 - 可以根据需要调整
        opening_ratio = 0.1      # 开局阶段 10%
        development_ratio = 0.5  # 发展阶段 50%
        climax_ratio = 0.3       # 高潮阶段 30%
        ending_ratio = 0.1       # 收尾阶段 10%
        
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
        """生成核心世界观 - 包含主角名字"""
        print("=== 步骤4: 构建核心世界观 ===")
        
        context = f"""小说标题: {novel_title}
            小说简介: {novel_synopsis}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            写作计划: {json.dumps(writing_plan, ensure_ascii=False)}"""
        
        if self.custom_main_character_name:
            context += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="构建世界观")
        if result:
            result = self._ensure_main_character_in_content(result, "core_worldview")
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, writing_plan: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计 - 增强版：确保使用自定义主角名字"""
        print("=== 步骤5: 设计主要角色 ===")
        
        # 优先使用传入的自定义名字，如果没有则使用类属性
        main_character_name = custom_main_character_name or self.custom_main_character_name
        
        context = f"""小说标题: {novel_title}
            核心世界观: {json.dumps(core_worldview, ensure_ascii=False)}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            写作计划: {json.dumps(writing_plan, ensure_ascii=False)}"""
        
        if main_character_name:
            context += f"\n\n【强制要求】主角的名字必须是: {main_character_name}"
            print(f"✓ 角色设计使用主角名字: {main_character_name}")
        
        result = self.api_client.generate_content_with_retry("character_design", context, purpose="角色设计")
        
        # 强制确保主角名字正确
        if result and main_character_name:
            result = self.ensure_main_character_name(result, main_character_name)
        
        return result

    def ensure_main_character_name(self, character_design: Dict, custom_name: str) -> Dict:
        """确保主角使用自定义名字"""
        if "main_character" in character_design and "name" in character_design["main_character"]:
            original_name = character_design["main_character"]["name"]
            if original_name != custom_name:
                print(f"⚠️  将主角名字从 '{original_name}' 改为 '{custom_name}'")
                character_design["main_character"]["name"] = custom_name
                character_design["main_character"]["original_name"] = original_name  # 保留原始名字记录
        
        return character_design

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节内容 - 修复版本：添加默认参数处理"""
        # 检查必需参数
        required_keys = ['chapter_number', 'total_chapters', 'novel_title', 'novel_synopsis', 
                        'worldview_info', 'character_info', 'writing_plan_info', 
                        'previous_chapters_summary', 'main_plot_progress', 'plot_direction',
                        'chapter_connection_note']
        
        missing_keys = [key for key in required_keys if key not in chapter_params]
        if missing_keys:
            print(f"❌ 缺少必需参数: {missing_keys}")
            return None
        
        try:
            # 确保所有格式化参数都有值
            safe_params = chapter_params.copy()
            
            # 为可能缺失的参数设置默认值
            safe_params.setdefault('major_event_info', '')
            safe_params.setdefault('event_specific_requirements', '')
            safe_params.setdefault('foreshadowing_guidance', '')
            safe_params.setdefault('character_development_focus', '')
            safe_params.setdefault('main_character_instruction', '')
            
            user_prompt = self.config["prompts"]["chapter_generation"].format(**safe_params)
            result = self.api_client.generate_content_with_retry("chapter_generation", user_prompt, purpose=f"生成第{safe_params['chapter_number']}章内容")
            return result
        except KeyError as e:
            print(f"❌ 格式化提示词时缺少参数: {e}")
            print(f"当前参数键: {list(chapter_params.keys())}")
            return None
        except Exception as e:
            print(f"❌ 生成章节内容时出错: {e}")
            return None
        
    def _assess_and_optimize_content(self, content: Dict, content_type: str, original_purpose: str) -> Dict:
        """评估并优化基础内容 - 修复版本"""
        if not content:
            return content
        
        # 如果没有 quality_assessor，跳过质量检查
        if not hasattr(self, 'quality_assessor') or self.quality_assessor is None:
            print(f"  ⚠️  跳过{original_purpose}质量检查 (quality_assessor 未设置)")
            return content
        
        print(f"🔍 评估{original_purpose}质量...")
        
        try:
            # 评估质量
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
            
            # 如果评分低于阈值，进行优化
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
                    # 重新评估优化后的内容
                    new_assessment = None
                    if content_type == "market_analysis":
                        new_assessment = self.quality_assessor.assess_market_analysis_quality(optimized_content)
                    elif content_type == "writing_plan":
                        new_assessment = self.quality_assessor.assess_writing_plan_quality(optimized_content)
                    elif content_type == "core_worldview":
                        new_assessment = self.quality_assessor.assess_core_worldview_quality(optimized_content)
                    elif content_type == "character_design":
                        new_assessment = self.quality_assessor.assess_character_design_quality(optimized_content)
                    
                    if new_assessment:
                        new_score = new_assessment.get("overall_score", 0)
                        improvement = new_score - score
                        print(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{improvement:+.1f}分)")
                        return optimized_content
                    else:
                        print(f"  ✓ 使用优化后的{original_purpose}")
                        return optimized_content
                else:
                    print(f"  ⚠️ 优化失败，保持原内容")
            
            return content
        
        except Exception as e:
            print(f"  ⚠️  质量检查过程中出错: {e}")
            return content  # 出错时返回原始内容

    # 修改现有的生成方法，添加质量检查
    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析和卖点提炼 - 包含质量检查"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}"
        if self.custom_main_character_name:
            user_prompt += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("market_analysis", user_prompt, purpose="市场分析")
        if result:
            # 质量检查和优化
            result = self._assess_and_optimize_content(result, "market_analysis", "市场分析")
            result = self._ensure_main_character_in_content(result, "market_analysis")
        return result

    def generate_writing_plan(self, creative_seed: str, selected_plan: Dict, 
                            market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        """生成写作计划 - 修复版本，包含质量检查"""
        print("=== 步骤3: 制定写作计划 ===")
        
        try:
            prompt_template = self.config["prompts"]["writing_plan"]
            system_prompt = self.safe_format(prompt_template, total_chapters=total_chapters)
            
            user_prompt = f"创意种子: {creative_seed}\n选定方案: {json.dumps(selected_plan, ensure_ascii=False)}\n市场分析: {json.dumps(market_analysis, ensure_ascii=False)}"
            if self.custom_main_character_name:
                user_prompt += f"\n主角名字: {self.custom_main_character_name}"
            
            result = self.api_client.generate_content_with_retry("writing_plan", user_prompt, purpose="制定写作计划")
            if result:
                # 质量检查和优化
                result = self._assess_and_optimize_content(result, "writing_plan", "写作计划")
                result = self._ensure_main_character_in_content(result, "writing_plan")
                result = self.fix_writing_plan_chapters(result, total_chapters)
            return result
        except Exception as e:
            print(f"❌ 生成写作计划时出错: {e}")
            return None

    def generate_core_worldview(self, novel_title: str, novel_synopsis: str, selected_plan: Dict, writing_plan: Dict) -> Optional[Dict]:
        """生成核心世界观 - 包含质量检查"""
        print("=== 步骤4: 构建核心世界观 ===")
        
        context = f"""小说标题: {novel_title}
            小说简介: {novel_synopsis}
            选定方案: {json.dumps(selected_plan, ensure_ascii=False)}
            写作计划: {json.dumps(writing_plan, ensure_ascii=False)}"""
        
        if self.custom_main_character_name:
            context += f"\n主角名字: {self.custom_main_character_name}"
        
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="构建世界观")
        if result:
            # 质量检查和优化
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观")
            result = self._ensure_main_character_in_content(result, "core_worldview")
        return result

    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict, writing_plan: Dict, custom_main_character_name: str = None) -> Optional[Dict]:
        """生成角色设计 - 增强版：包含质量检查"""
        print("=== 步骤5: 设计主要角色 ===")
        
        # 优先使用传入的自定义名字，如果没有则使用类属性
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
            # 质量检查和优化
            result = self._assess_and_optimize_content(result, "character_design", "角色设计")
            # 强制确保主角名字正确
            if main_character_name:
                result = self.ensure_main_character_name(result, main_character_name)
        
        return result    