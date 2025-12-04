"""内容生成器类 - 专注内容生成"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import copy
import json
import os
import re
import time
from typing import Any, Dict, Optional, List, Tuple
from src.core.APIClient import APIClient
from src.core.Contexts import GenerationContext
from src.core.QualityAssessor import QualityAssessor
from src.prompts.Prompts import Prompts
from src.utils.logger import get_logger
class ContentGenerator:
    # ============================================================================
    # 内部辅助类 - Prompt 构建器 (已整合多个方法)
    # ============================================================================
    class _PromptBuilder:
        """统一的提示词构建器 - 整合所有提示词生成逻辑"""
        def __init__(self, generator):
            self.logger = get_logger("_PromptBuilder")
            self.generator = generator
        def build_character_prompt(self, plan, main_char_name=None):
            """构建核心角色提示词 (原 _build_core_character_prompt_for_plan)"""
            if not plan:
                return ""
            synopsis = plan.get("synopsis", "")
            system_info = plan.get("system", {})
            prompt = f"""作为一位优秀的角色设计专家，请根据以下小说方案，为主角 {main_char_name or '主角'} 设计详细的角色卡：
【小说方案摘要】
{synopsis}
【系统/金手指】
{json.dumps(system_info, ensure_ascii=False, indent=2)}
请为主角设计以下方面：
1. 人物基本信息（年龄、外貌、身份等）
2. 性格特点（3-5个核心性格特征）
3. 初始能力和背景
4. 核心目标和动机
5. 性格成长空间
返回JSON格式的角色卡。"""
            return prompt
        def build_consistency_prompt(self, context_dict):
            """构建一致性检查提示词"""
            prompt = f"""请根据以下上下文信息，提供内容一致性检查：
【已有信息】
{json.dumps(context_dict, ensure_ascii=False, indent=2)}
请检查：
1. 角色性格的一致性
2. 世界观的一致性
3. 情节逻辑的一致性
4. 语气风格的一致性
返回检查结果。"""
            return prompt
    # ============================================================================
    # 内部辅助类 - 一致性收集器 (已整合多个方法)
    # ============================================================================
    class _ConsistencyGatherer:
        """统一的一致性收集器 - 整合所有一致性数据收集逻辑"""
        def __init__(self, generator):
            self.logger = get_logger("_ConsistencyGatherer")
            self.generator = generator
        def gather_all(self, novel_title: str, chapter_num: int, novel_data: Dict = None) -> Dict:
            """一次性收集所有一致性数据"""
            world_state = self._get_previous_world_state(novel_title)
            consistency_guid = self._build_consistency_guidance(world_state, novel_title)
            relationships = self._get_relationship_consistency_note(world_state)
            char_dev = self._get_character_development_guidance(chapter_num, novel_data)
            return {
                "world_state": world_state,
                "consistency_guidance": consistency_guid,
                "relationships": relationships,
                "character_development": char_dev
            }
        def _get_previous_world_state(self, novel_title: str) -> Dict:
            """从文件中加载前面章节的世界状态"""
            from src.managers.WorldStateManager import WorldStateManager
            wsm = WorldStateManager("quality_data")
            return wsm.get_novel_world_state(novel_title)
        def _build_consistency_guidance(self, world_state: Dict, novel_title: str) -> str:
            """基于世界状态构建一致性指导（使用压缩后的数据）"""
            # 使用与QualityAssessor相同的压缩机制
            if hasattr(self.generator, 'quality_assessor') and self.generator.quality_assessor:
                compressed_state = self.generator.quality_assessor._compress_world_state_for_assessment(
                    world_state, max_chars=8000
                )
                return f"【一致性指导】\n请保持与以下已有信息的一致性：\n{compressed_state}"
            else:
                # 回退到简化版本
                return f"【一致性指导】\n请保持与已有世界设定的一致性"
        def _get_relationship_consistency_note(self, world_state: Dict) -> str:
            """获取关系一致性说明"""
            relationships = world_state.get("relationships", {})
            return f"已有关系：{json.dumps(relationships, ensure_ascii=False)}"
        def _get_character_development_guidance(self, chapter_num: int, novel_data: Dict = None) -> str:
            """获取角色发展指导"""
            if novel_data is None:
                return f"第 {chapter_num} 章的角色应该有相应的发展和变化"
            # 使用 novel_data 构建更完整的指导（代理给主类方法）
            if hasattr(self.generator, 'quality_assessor') and self.generator.quality_assessor:
                novel_title = novel_data.get("novel_title", "Unknown")
                char_dev_data = self.generator.quality_assessor._load_character_development_data(novel_title)
                if char_dev_data:
                    return f"第 {chapter_num} 章 - 角色发展指导已根据历史数据生成"
            return f"第 {chapter_num} 章的角色应该有相应的发展和变化"
    # ============================================================================
    # ContentGenerator 主类初始化
    # ============================================================================
    def __init__(self, novel_generator, api_client: APIClient, config, event_bus, quality_assessor):
        self.logger = get_logger("_ConsistencyGatherer")
        self.novel_generator:NovelGenerator = novel_generator
        self.api_client = api_client
        self.config = config
        self.prompts = Prompts
        self.event_bus = event_bus
        self.quality_assessor:QualityAssessor = quality_assessor
        self.custom_main_character_name = None
        # 初始化日志系统
        self.logger = get_logger("ContentGenerator")
        # ▼▼▼ 添加下面两行 ▼▼▼
        project_path = getattr(self.novel_generator, 'project_path', Path.cwd())
        self.design_dir = project_path / "章节详细设计"
        # ▲▲▲ 添加结束 ▲▲▲
        # 初始化辅助类实例
        self._prompt_builder = self._PromptBuilder(self)
        self._consistency_gatherer = self._ConsistencyGatherer(self)
    def set_custom_main_character_name(self, name: str):
        """设置主角名字"""
        self.custom_main_character_name = name
        self.logger.info(f"✓ 内容生成器已设置主角名字: {name}")
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
        self.logger.info("=== 步骤1: 基于创意种子和分类生成小说方案 ===")
        # 如果提供了分类，自动生成适合该分类的主角名字
        if category:
            generated_name = self._generate_character_name_by_category(category, creative_seed)
            if generated_name:
                self.set_custom_main_character_name(generated_name)
                self.logger.info(f"✓ 根据分类 '{category}' 自动生成主角名字: {generated_name}")
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
            self.logger.info(f"  🔄 生成方案尝试 {attempt + 1}/{max_retries}")
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
            self.logger.info(f"  🆕 方案新鲜度评分: {freshness_score:.1f}/10")
            self.logger.info(f"  📊 核心设定新颖性: {core_concept_novelty:.1f}/4")
            self.logger.info(f"  📊 系统创新性: {system_innovation:.1f}/3") 
            self.logger.info(f"  📊 市场稀缺性: {market_scarcity:.1f}/3")
            # 显示评估结果
            analysis = freshness_assessment.get("analysis", {})
            verdict = freshness_assessment.get("verdict", "未知")
            suggestions = freshness_assessment.get("suggestions", [])
            self.logger.info(f"  📈 综合判定: {verdict}")
            # 显示分析摘要
            if analysis.get("core_concept_novelty"):
                self.logger.info(f"  💡 核心设定分析: {analysis['core_concept_novelty'][:100]}...")
            # 显示改进建议
            if suggestions:
                self.logger.info(f"  💡 改进建议: {suggestions[0]}")
            # 检查是否存在复杂设定问题
            complexity_issues = self._check_setting_complexity(result)
            if complexity_issues:
                self.logger.warn(f"  ⚠️ 检测到复杂设定问题: {', '.join(complexity_issues)}")
                freshness_score = max(0, freshness_score - 2)  # 复杂设定扣分
            # 如果新鲜度达标，使用该方案
            if freshness_score >= 8.5:  # 稍微降低阈值，更注重故事性
                self.logger.info(f"  ✅ 方案新鲜度达标")
                break
            else:
                self.logger.info(f"  🔄 方案新鲜度不足，尝试优化...")
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
                    self.logger.info(f"  🆕 优化后新鲜度: {new_score:.1f}/10")
                    if new_score >= 7.0:
                        self.logger.info(f"  ✅ 优化成功，新鲜度达标")
                        result = optimized_result
                        break
                    else:
                        self.logger.warn(f"  ⚠️ 优化后新鲜度仍不足，继续重新生成...")
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
            if self.quality_assessor: # 确保 quality_assessor 存在
                immersion_score = self.quality_assessor.assess_immersion_level(result)
                result["immersion_score"] = immersion_score
                self.logger.info(f"  💫 代入感评分: {immersion_score:.1f}/10")
            else:
                self.logger.warn(f"  ⚠️ QualityAssessor 未初始化，跳过代入感评估。")
                result["immersion_score"] = 0 # 默认值为 0 如果未评估
        return result
    def generate_market_analysis(self, creative_seed: str, selected_plan: Dict) -> Optional[Dict]:
        """生成市场分析 - 增加新鲜度评估"""
        self.logger.info("=== 步骤2: 进行市场分析和卖点提炼 ===")
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
        self.logger.info("=== 步骤3: 构建核心世界观 ===")
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
    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict,
                                  market_analysis: Dict, design_level: str,
                                  existing_characters: Optional[Dict] = None,
                                  stage_info: Optional[Dict] = None,
                                  global_growth_plan: Optional[Dict] = None,       # <-- 新增
                                  overall_stage_plans: Optional[Dict] = None,
                                  custom_main_character_name: str = None) -> Optional[Dict]:
        self.logger.info(f"  -> 角色设计启动，模式: 【{design_level}】")
        main_character_name = custom_main_character_name or self.custom_main_character_name
        prompt_type = ""
        prompt_context = {}
        purpose = ""
        # 1. 根据设计层级，选择正确的Prompt并准备上下文
        if design_level == "core":
            prompt_type = "character_design_core"
            # 准备核心设计所需的上下文
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
            # ▼▼▼ 核心修改区域开始 ▼▼▼
            if not existing_characters or not stage_info:
                self.logger.warn("  ⚠️ 补充角色模式缺少'已有角色'或'阶段信息'，操作已取消。")
                return existing_characters
            prompt_type = "character_design_supplementary"
            # 【智能推断】: 不再使用写死的角色，而是根据情节动态推断
            inferred_roles = self._infer_required_roles_for_stage(stage_info, existing_characters)
            # 准备补充设计所需的上下文
            stage_requirements = {
                "stage_name": stage_info.get("stage_name", "当前阶段"),
                "stage_summary": stage_info.get("stage_overview", "未知"), # 从 stage_overview 获取摘要
                "new_character_roles": inferred_roles # 使用动态推断出的角色！
            }
            prompt_context = {
                "EXISTING_CHARACTERS": json.dumps(existing_characters, ensure_ascii=False, indent=2),
                "STAGE_REQUIREMENTS": json.dumps(stage_requirements, ensure_ascii=False, indent=2)
            }
            purpose = f"为《{novel_title}》的 '{stage_requirements['stage_name']}' 阶段补充配角"
            # ▲▲▲ 核心修改区域结束 ▲▲▲
        else:
            self.logger.error(f"  ❌ 未知的角色设计层级: '{design_level}'")
            return None
        # 🆕 修复：确保 prompt_context 不为 None
        if prompt_context is None:
            self.logger.error("  ❌ 角色设计提示词上下文构建失败")
            return None
        # 1. 确保 prompt_context 是一个字典
        if not isinstance(prompt_context, dict):
            self.logger.error(f"  ❌ 角色设计提示词上下文构建失败，期望是字典，却是 {type(prompt_context)}")
            return None
        # 2. 将字典正确序列化为 JSON 字符串
        try:
            prompt_context_str = json.dumps(prompt_context, ensure_ascii=False, indent=2)
        except TypeError as e:
            self.logger.error(f"  ❌ 无法将提示词上下文序列化为JSON: {e}")
            return None
        self.logger.info(f"  📝 角色设计提示词长度: {len(prompt_context)} 字符")
        # 1. 将变量重命名为更通用的名字，因为它可能不是字符串
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
            # 2. 检查返回结果的类型
            if isinstance(api_result, dict):
                # 如果已经是字典，直接使用
                self.logger.info("  ✅ 角色设计API已返回解析好的JSON字典。")
                result_json = api_result
            elif isinstance(api_result, str):
                # 如果是字符串，则进行解析
                self.logger.info("  ✅ 角色设计API返回JSON字符串，正在解析...")
                result_json = json.loads(api_result)
            else:
                # 处理未知类型
                self.logger.error(f"  ❌ 角色设计API返回了未知类型: {type(api_result)}")
                return existing_characters if design_level == "supplementary" else None
        except json.JSONDecodeError:
            self.logger.error(f"  ❌ 解析角色设计JSON字符串失败 (模式: {design_level})")
            return existing_characters if design_level == "supplementary" else None
        # 3. 根据模式处理和返回结果
        if design_level == "core":
            # 核心模式直接返回完整的新角色设计
            self.logger.info("  ✅ 核心角色设计生成成功。")
            if main_character_name:
                result_json = self.ensure_main_character_name(result_json, main_character_name)
            return result_json
        elif design_level == "supplementary":
            # 补充模式需要将新角色合并到旧数据中
            new_characters = result_json.get("newly_added_characters", [])
            if not new_characters:
                self.logger.warn("  ⚠️ 补充角色API调用成功，但未返回新角色。")
                return existing_characters
            self.logger.info(f"  ✅ 成功生成 {len(new_characters)} 个补充角色，正在合并...")
            # 使用深拷贝以确保数据安全
            updated_characters = copy.deepcopy(existing_characters)
            if "important_characters" not in updated_characters:
                updated_characters["important_characters"] = []
            updated_characters["important_characters"].extend(new_characters)
            return updated_characters
    def _infer_required_roles_for_stage(self, stage_info: Dict, existing_characters: Dict) -> List[str]:
        self.logger.info("    -> 正在动态分析阶段情节，推断所需角色...")
        # 1. 提取关键情节信息
        event_system = stage_info.get("stage_writing_plan", {}).get("event_system", {})
        major_events = event_system.get("major_events", [])
        plot_summary_parts = [f"阶段总体目标: {stage_info.get('stage_overview', '未知')}"]
        for event in major_events[:10]: # 只分析前3个主要事件以控制成本和聚焦
            plot_summary_parts.append(f"- 主要事件: {event.get('name', '')} (目标: {event.get('main_goal', '')})")
        stage_plot_summary = "\n".join(plot_summary_parts)
        # 2. 提取已有角色名
        existing_names = [char.get("name") for char in existing_characters.get("important_characters", [])]
        if existing_characters.get("main_character"):
            existing_names.append(existing_characters["main_character"].get("name"))
        # 3. 构建Prompt上下文
        prompt_context = {
            "STAGE_PLOT_SUMMARY": stage_plot_summary,
            "EXISTING_CHARACTERS": ", ".join(filter(None, existing_names))
        }
        # 应该在这里转换
        prompt_context_str = json.dumps(prompt_context, ensure_ascii=False) 
        # 4. 调用API进行推断
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
        return ["阶段性反派", "功能性NPC"] # API调用失败或未返回角色时的安全回退
    def _build_core_character_prompt_for_plan(self, plan: Dict, main_character_name: Optional[str]) -> str:
        # 从方案中智能提取反派线索，使其通用化
        storyline = plan.get('completeStoryline', {})
        ending_summary = storyline.get('ending', {}).get('summary', '')
        main_plot = plan.get('story_development', {}).get('main_plot', [])
        antagonist_clue = "请设计一个贯穿故事前中期的主要反派或敌对势力，他/它将是主角成长的主要外部驱动力。"
        if "解决" in ending_summary and ("仇" in ending_summary or "敌" in ending_summary or "boss" in ending_summary.lower()):
            antagonist_clue = f"在故事的结局阶段，主角需要解决一个重大的威胁或最终的敌人。结局线索: '{ending_summary}'。请基于此设计这个核心反派。"
        elif main_plot:
            antagonist_clue = f"故事的主线脉络是: {' -> '.join(main_plot)}。请设计一个与这条主线深度绑定的核心反派或对立面。"
        return f"""
# 设计任务：【核心角色骨架设计 (A级)】
请为以下小说方案，设计3-4个对故事有决定性影响的核心支柱角色。
## 小说方案信息
- **标题**: 《{plan.get('title', 'N/A')}》
- **简介**: {plan.get('synopsis', 'N/A')}
- **金手指**: {plan.get('core_settings', {}).get('golden_finger', 'N/A')}
- **主角定位**: {plan.get('story_development', {}).get('protagonist_position', 'N/A')}
## 角色设计要求
1.  **主角 (main_character)**: {f"姓名固定为: {main_character_name}" if main_character_name else "请根据定位生成一个合适的名字"}。必须深度塑造其性格和动机。
2.  **核心盟友/女主**: 设计一个与主角关系最紧密、贯穿始终的重要伙伴。
3.  **【最重要】核心反派**:
    - **设计线索**: {antagonist_clue}
    - **设计指令**: 必须将这个概念性的“最终敌人”具象化。给他一个名号、背景、动机和独特的行事风格。他的存在必须是主角成长的最终目标和巨大阴影。
## 输出格式
请严格以JSON格式返回，包含`main_character`和`important_characters`列表。列表中必须包含上述的核心盟友和核心反派。
"""
    def _build_supplementary_character_prompt_for_stage(self, existing_characters: Dict, stage_info: Dict) -> str:
        """【通用】为任何小说的开局阶段构建补充角色设计的Prompt"""
        existing_names = [char.get("name") for char in existing_characters.get("important_characters", [])]
        if existing_characters.get("main_character"):
            existing_names.append(existing_characters["main_character"].get("name"))
        stage_goal = stage_info.get("stage_writing_plan", {}).get("stage_overview", "暂无")
        major_events = stage_info.get("stage_writing_plan", {}).get("event_system", {}).get("major_events", [])
        event_names = [event.get("name") for event in major_events if event.get("name")]
        return f"""
# 设计任务：【开局阶段配角补充 (B/C级)】
在已有的核心角色基础上，为小说的开局阶段补充必要的、功能性的配角和“新手村”小反派。
## 已有核心角色 (请勿重复设计)
{", ".join(filter(None, existing_names))}
## 开局阶段核心信息
- **阶段目标**: {stage_goal}
- **主要事件**: {", ".join(event_names)}
## 设计要求
1.  **功能性优先**: 设计1-2个能够推动开局剧情发展的角色（例如：前期导师、提供任务的NPC、有趣的同伴）。
2.  **典型反派**: 设计一个符合“欺软怕硬、贪婪”特质的前期小反派，他将成为主角第一个展示智谋和手段的“垫脚石”。
3.  **简洁高效**: 设计需要符合其在故事中的定位，无需像核心角色那样复杂。
## 输出格式
请严格以JSON格式返回，只包含一个`important_characters`列表，其中是你新设计的1-2个阶段性角色。
""" 
    def _generate_highlight_scene_snippet(self, scene_brief: str, character_design: Dict, emotional_focus: str, writing_style_guide: Dict) -> Optional[str]:
        self.logger.info("  🎬 [API Call] 正在调用“名场面导演”模块...")
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
                    self.logger.info("  ✅ “名场面导演”成功生成【风格一致的】场景片段。")
                    return scene_snippet.strip()
                else:
                    self.logger.warn("  ⚠️ “名场面导演”返回的JSON中snippet为空或过短。")
                    return None
            else:
                self.logger.error(f"  ❌ “名场面导演”返回结果格式错误，期望是字典但收到了: {type(result)}")
                return None
        except Exception as e:
            self.logger.error(f"  ❌ 在调用“名场面导演”模块时发生异常: {e}")
            return None
    def ensure_main_character_name(self, character_design: Dict, custom_name: str) -> Dict:
        if "main_character" in character_design and "name" in character_design["main_character"]:
            original_name = character_design["main_character"]["name"]
            if original_name != custom_name:
                self.logger.warn(f"⚠️  将主角名字从 '{original_name}' 改为 '{custom_name}'")
                character_design["main_character"]["name"] = custom_name
                character_design["main_character"]["original_name"] = original_name
        return character_design
    def _assess_and_optimize_content(self, content: Dict, content_type: str, original_purpose: str) -> Dict:
        """修正版内容评估和优化 - 支持小说方案优化"""
        if not content or not hasattr(self, 'quality_assessor') or self.quality_assessor is None:
            return content
        self.logger.info(f"  🔍 评估{original_purpose}...")
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
            self.logger.info(f"  {original_purpose}质量评估: {quality_score:.1f}/10")
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
                self.logger.info(f"  {original_purpose}新鲜度评估: {freshness_score:.1f}/10")
                # 显示详细分数
                core_concept_novelty = score_data.get("core_concept_novelty", 0)
                system_innovation = score_data.get("system_innovation", 0)
                market_scarcity = score_data.get("market_scarcity", 0)
                self.logger.info(f"  📊 核心设定新颖性: {core_concept_novelty:.1f}/4")
                self.logger.info(f"  📊 系统创新性: {system_innovation:.1f}/3")
                self.logger.info(f"  📊 市场稀缺性: {market_scarcity:.1f}/3")
                # 显示评估结果
                verdict = freshness_assessment.get("verdict", "未知")
                self.logger.info(f"  📈 综合判定: {verdict}")
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
                self.logger.info(f"  🔧 进行{original_purpose}优化: {reason}")
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
                    self.logger.info(f"  ✅ {original_purpose}优化完成")
                    return optimized_content
                else:
                    self.logger.warn(f"  ⚠️ {original_purpose}优化失败，使用原内容")
            return content
        except Exception as e:
            self.logger.warn(f"  ⚠️ 评估过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return content
    # ==================== vvv 全新、完整的 generate_chapter_content_for_novel 函数 vvv ====================
    def generate_chapter_content_for_novel(self, chapter_number: int, novel_data: Dict, context: GenerationContext = None) -> Optional[Dict]:
        self.logger.info(f"🎬 开始生成第{chapter_number}章内容...")
        # ==================== 新增：章节级重试循环 ====================
        MAX_CHAPTER_RETRIES = 5  # 为一整个章节设置最多3次重试机会
        RETRY_WAIT_SECONDS = 20  # 每次重试前等待20秒，给API和网络缓冲时间
        for attempt in range(MAX_CHAPTER_RETRIES):
            # 每次循环都打印尝试次数
            if attempt > 0:
                self.logger.info(f"  - 章节生成失败，将在 {RETRY_WAIT_SECONDS} 秒后进行第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次重试...")
                time.sleep(RETRY_WAIT_SECONDS)
            self.logger.info(f"  🔄 第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次尝试生成第 {chapter_number} 章...")
            failure_reason = None
            failure_details = {}
            try:
                # --- 核心生成逻辑被包裹在循环内部 ---
                # 仅在第一次尝试时初始化世界状态
                if chapter_number == 1 and attempt == 0:
                    self.logger.info("🔄 初始化世界状态...")
                    self.quality_assessor.world_state_manager.initialize_world_state_from_novel_data(novel_data["novel_title"], novel_data)
                # 存储上下文供后续使用
                novel_data['_current_generation_context'] = context
                # 准备章节参数
                chapter_params = self._prepare_chapter_params(chapter_number, novel_data)
                if not chapter_params or not self._validate_chapter_params(chapter_params):
                    failure_reason = "参数准备失败"
                    failure_details = {"missing_params": [key for key, val in chapter_params.items() if not val]}
                    self.logger.error(f"  ❌ 第{chapter_number}章参数准备失败。")
                    continue  # 进入下一次重试
                self.logger.info(f"  ✅ 第{chapter_number}章所有参数验证通过。")
                self.logger.info(f"  🚀 开始调用核心内容生成...")
                chapter_data = self.generate_chapter_content(chapter_params)
                if not chapter_data:
                    failure_reason = "核心内容生成失败 (generate_chapter_content返回None)"
                    failure_details = {"step": "generate_chapter_content"}
                    self.logger.error(f"  ❌ 第{chapter_number}章核心内容生成失败。")
                    continue  # 进入下一次重试
                # --- 后续的质量评估、优化等逻辑保持不变 ---
                self.logger.info(f"  ✨ 核心内容生成完毕，开始后处理...")
                # 确保章节标题唯一性
                chapter_data = self._handle_chapter_title_uniqueness(chapter_data, chapter_number, novel_data)
                # 新增：从设计蓝图中提取情绪信息，并置于顶层以兼容旧结构
                if chapter_data and chapter_data.get("chapter_design", {}).get("emotional_design"):
                    chapter_data["emotional_design"] = chapter_data["chapter_design"]["emotional_design"]
                    self.logger.info(f"  💖 已从设计蓝图中提取情绪设计: {chapter_data['emotional_design'].get('target_emotion', '未知')}")
                else:
                    chapter_data["emotional_design"] = {} # 保留空字典以防后续代码出错
                # ▲▲▲ 新代码块结束 ▲▲▲
                # 质量评估
                self.logger.info(f"  📊 开始质量评估...")
                # 🔧 防御性检查：确保 content 是字符串
                chapter_content = chapter_data.get("content", "")
                if not isinstance(chapter_content, str):
                    self.logger.error(f"❌ chapter_content 类型错误: {type(chapter_content)}")
                    chapter_content = str(chapter_content) if chapter_content else ""

                assessment = self.quality_assessor.quick_assess_chapter_quality(
                    chapter_content,
                    chapter_data.get("chapter_title", ""),
                    chapter_number,
                    novel_data["novel_title"],
                    chapter_params.get("previous_chapters_summary", ""),
                    chapter_data.get("word_count", 0),
                    novel_data=novel_data
                )
                # 修复：处理 assessment 为 None 的情况
                if assessment is None:
                    self.logger.warn(f"⚠️ 质量评估失败（API调用失败），使用默认评分")
                    assessment = {
                        "overall_score": 6.0,
                        "quality_verdict": "API调用失败，使用默认评分",
                        "weaknesses": [],
                        "strengths": []
                    }
                score = assessment.get("overall_score", 0)
                chapter_data["quality_score"] = score
                chapter_data["quality_assessment"] = assessment
                self.logger.info(f"  质量评分: {score:.1f}分")
                # 根据质量决定是否优化
                optimize_needed, optimize_reason = self._should_optimize_based_on_config(assessment)
                if optimize_needed:
                    self.logger.info(f"  🔧 进行优化: {optimize_reason}")
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
                                self.logger.info(f"  ✅ 第{retry+1}次优化成功")
                                break
                            else:
                                self.logger.warn(f"  ⚠️ 第{retry+1}次优化失败，返回空结果")
                                optimized_data = None
                        except Exception as e:
                            self.logger.error(f"  ❌ 第{retry+1}次优化过程异常: {e}")
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
                        self.logger.info(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{new_score - score:+.1f}分)")
                        chapter_data["quality_score"] = new_score
                        chapter_data["quality_assessment"] = new_assessment
                    else:
                        self.logger.warn(f"  ⚠️ 所有优化尝试均失败，保持原内容")
                        chapter_data["optimization_info"] = {
                            "optimized": False,
                            "reason": "优化过程失败",
                            "original_score": score
                        }
                else:
                    self.logger.info(f"  ✓ {optimize_reason}")
                    chapter_data["quality_assessment"] = assessment
                # AI俏皮开场白
                if chapter_number == 1:
                    try:
                        chapter_data = self.novel_generator._add_ai_spicy_opening_to_first_chapter(
                            chapter_data, novel_data.get("novel_title", ""), novel_data.get("novel_synopsis", ""), novel_data.get("category", "默认")
                        )
                    except Exception as e:
                        self.logger.warn(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")
                # ==================== 成功！返回章节数据并跳出重试循环 ====================
                self.logger.info(f"🎉 第 {chapter_number} 章在第 {attempt + 1} 次尝试中生成成功！")
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
                self.logger.error(f"  ❌ 第{chapter_number}章在第 {attempt + 1} 次尝试中出现严重异常: {e}")
                import traceback
                traceback.print_exc()
                # 异常发生后，循环会继续，进入下一次重试
        # ==================== 如果所有重试都失败了 ====================
        self.logger.info(f"🔥🔥🔥 严重错误: 第 {chapter_number} 章在 {MAX_CHAPTER_RETRIES} 次尝试后彻底失败！")
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
    def _generate_previous_chapters_summary(self, current_chapter: int, novel_data: Dict) -> str:
        """生成前情提要"""
        if current_chapter == 1:
            return "这是开篇第一章，需要建立故事基础。"
        # 获取上一章的详细结尾信息
        previous_ending_info = self._get_previous_chapter_ending(current_chapter, novel_data)
        return previous_ending_info
    def _get_previous_chapter_ending(self, current_chapter: int, novel_data: Dict) -> str:
        """获取上一章的结尾内容和悬念，用于衔接"""
        if current_chapter <= 1:
            self.logger.info(f"  📖 第{current_chapter}章是开篇第一章，无需获取前一章结尾")
            return "这是开篇第一章，需要建立故事基础。"
        prev_chapter_data = self._load_chapter_content(current_chapter - 1, novel_data)
        if prev_chapter_data:
            chapter_ending = self._extract_content_ending(prev_chapter_data.get("content", ""))
            next_chapter_hook = prev_chapter_data.get("next_chapter_hook", "")
            ending_description = f"上一章结尾: {chapter_ending}" if chapter_ending else ""
            hook_description = f"上一章设置的悬念: {next_chapter_hook}" if next_chapter_hook else "上一章未明确设置悬念。"
            result_parts = [ending_description]
            if hook_description:
                result_parts.append(hook_description)
            result = "\n\n".join(result_parts)
            self.logger.info(f"  ✅ 第{current_chapter-1}章结尾信息组合成功，长度: {len(result)}字符")
            return result
        error_msg = f"第{current_chapter-1}章的内容无法加载，请确保该章已成功生成并保存。"
        self.logger.error(f"  ❌❌ {error_msg}")
        return error_msg
    def _load_chapter_content(self, chapter_number: int, novel_data: Dict) -> Optional[Dict]:
        """加载章节内容"""
        # 处理字典键可能是字符串的情况
        chapter_key = str(chapter_number)
        if chapter_key in novel_data.get("generated_chapters", {}):
            return novel_data["generated_chapters"][chapter_key]
        # 也尝试整数键以保持向后兼容性
        if chapter_number in novel_data.get("generated_chapters", {}):
            return novel_data["generated_chapters"][chapter_number]
        return None
    def _extract_content_ending(self, content: str) -> str:
        """提取内容结尾部分"""
        content_length = len(content)
        self.logger.info(f"  📏 章节内容长度: {content_length}字符")
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
                    self.logger.info(f"  ✅ 成功提取结尾: {ending[:100]}...")
                    return ending
            except Exception as e:
                self.logger.warn(f"  ⚠️  方法 '{method.__name__}' 提取失败: {e}")
                continue
        # 所有方法都失败，使用最后200字作为备选
        fallback_ending = content[-200:] if content_length > 200 else content
        self.logger.warn(f"  ⚠️  所有提取方法失败，使用备选结尾: {fallback_ending[:100]}...")
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
            'chapter_number', 'novel_title', 'novel_synopsis', 'plot_direction'
        ]
        for key in required:
            if key not in params or not params[key]:
                self.logger.error(f"❌ 参数验证失败: 缺少 {key}")
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
        self.logger.warn(f"⚠️  章节标题重复: '{original_title}' 与第{duplicate_chapter}章重复，正在生成新标题...")
        # 使用智能重命名
        new_title = self._generate_unique_chapter_title(original_title, chapter_number, novel_data)
        if new_title != original_title:
            # 只更新章节标题，保持其他结构不变
            chapter_data["chapter_title"] = new_title
            chapter_data["title_was_changed"] = True
            chapter_data["original_title"] = original_title
            novel_data["used_chapter_titles"].add(new_title)
            self.logger.info(f"✓ 使用新标题: '{new_title}'")
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
        # 修复：处理 _current_generation_context 可能是 GenerationContext 对象的情况
        context_obj = novel_data.get('_current_generation_context')
        if hasattr(context_obj, 'event_context'):
            event_context = context_obj.event_context
        elif isinstance(context_obj, dict):
            event_context = context_obj.get('event_context', {})
        else:
            event_context = {}
        # 确保 event_context 是字典
        if not isinstance(event_context, dict):
            event_context = {}
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
            # 修复：使用正确的 generate_content_with_retry 参数
            new_title = self.api_client.generate_content_with_retry(
                content_type="chapter_title_generation",
                user_prompt=title_prompt,
                temperature=0.7,
                purpose="生成章节标题"
            )
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
            self.logger.info(f"生成新标题失败: {e}")
        return self._generate_event_related_title(chapter_number, novel_data)
    def _generate_event_related_title(self, chapter_number: int, novel_data: Dict) -> str:
        """生成与事件相关的备选标题"""
        try:
            # 修复：处理 _current_generation_context 可能是 GenerationContext 对象的情况
            context_obj = novel_data.get('_current_generation_context')
            if hasattr(context_obj, 'event_context'):
                event_context = context_obj.event_context
            elif isinstance(context_obj, dict):
                event_context = context_obj.get('event_context', {})
            else:
                event_context = {}
            # 确保 event_context 是字典
            if not isinstance(event_context, dict):
                event_context = {}
            active_events = event_context.get('active_events', []) if event_context else []
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
        except Exception as e:
            self.logger.error(f"_generate_event_related_title 出错: {e}")
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
                self.logger.info(f"  - {issue}")
            return True, f"存在{len(severe_issues)}个严重一致性问题，需要优化"
        return False, f"评分{score:.1f}良好，跳过优化"
    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        self.logger.info(f"  🔍 进入【优化版】generate_chapter_content方法...")
        chapter_number = chapter_params.get('chapter_number', '未知')
        pre_designed_scenes = chapter_params.get("pre_designed_scenes", [])
        if not pre_designed_scenes:
            self.logger.error(f"  ❌ 第 {chapter_number} 章缺少预设的场景事件，无法直接生成内容。")
            return None
        # ▼▼▼ 核心修改部分：构建一个能体现6段式结构功能的Prompt ▼▼▼
        # 定义场景定位的中文名称和功能解释
        scene_position_map = {
            "opening": {"name": "开场场景 (Opening Scene)", "function": "建立情境，引入本章核心冲突的起点，快速吸引读者。", "percentage": "15-20%"},
            "development1": {"name": "发展场景1 (Development 1)", "function": "推进情节，深化初始冲突，引入新信息或角色。", "percentage": "20-25%"},
            "development2": {"name": "发展场景2 (Development 2)", "function": "冲突升级，增加紧张感，为高潮做足铺垫。", "percentage": "20-25%"},
            "climax": {"name": "高潮场景 (Climax Scene)", "function": "【本章重点】情感的集中爆发点！这是本章最关键的转折和最强烈的情感冲击所在。", "percentage": "15-20%"},
            "falling": {"name": "回落场景 (Falling Action)", "function": "处理高潮带来的直接后果，让情绪和节奏得到短暂缓和。", "percentage": "10-15%"},
            "ending": {"name": "结尾场景 (Ending Scene)", "function": "收束本章内容，并设置一个强有力的悬念（钩子），引导读者追读下一章。", "percentage": "5-10%"}
        }
        scenes_str_parts = ["# 1. 写作蓝图：本章的六段式场景结构 (必须严格遵守)"]
        scenes_str_parts.append("你必须严格按照下面每个场景的功能定位和内容要点来创作，确保章节节奏张弛有度，高潮突出。")
        for scene in pre_designed_scenes:
            position_key = scene.get('position', 'unknown').lower()
            # 兼容 development1 和 development2
            if 'development' in position_key and position_key not in scene_position_map:
                # 尝试匹配 development1 或 development2
                if '1' in position_key: position_key = 'development1'
                elif '2' in position_key: position_key = 'development2'
                else: # 如果都没有，就用一个通用的
                    position_key = 'development1'
            scene_info = scene_position_map.get(position_key, {"name": f"场景 ({scene.get('position', '未知')})", "function": "按计划推进情节。", "percentage": "N/A"})
            scenes_str_parts.append(f"\n## ### {scene_info['name']} - 预估篇幅占比: {scene_info['percentage']}")
            # ▼▼▼【核心修改】动态遍历场景字典，防止信息丢失 ▼▼▼
            # 为了让Prompt更易读，定义一个键名到中文的映射
            key_display_map = {
                "name": "场景名称",
                "purpose": "核心目标",
                "key_actions": "关键动作/事件",
                "emotional_impact": "情感冲击",
                "dialogue_highlights": "关键对话高光",
                "conflict_point": "冲突焦点",
                "sensory_details": "感官细节",
                "transition_to_next": "场景过渡",
                "estimated_word_count": "预估字数",
                "contribution_to_chapter": "对本章贡献"
            }
            for key, value in scene.items():
                # 跳过已处理或不需要展示的键
                if key in ['position', 'type']:
                    continue
                # 获取展示用的键名，如果没在map里，就用原键名
                display_key = key_display_map.get(key, key)
                # 仅在值存在时才添加到Prompt
                if value:
                    # 如果值是列表，则用逗号连接成字符串
                    if isinstance(value, list):
                        formatted_value = ', '.join(map(str, value))
                    else:
                        formatted_value = str(value)
                    # 再次检查格式化后的值是否为空
                    if formatted_value:
                        scenes_str_parts.append(f"- **{display_key}**: {formatted_value}")
            # ▲▲▲【核心修改结束】▲▲▲
        scenes_input_str = "\n".join(scenes_str_parts)
        user_prompt = f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_number}章。
{scenes_input_str}
## 2. 背景与衔接
- **前情提要**: {chapter_params.get("previous_chapters_summary", "无")}
- **本章核心目标**: {chapter_params.get("chapter_goal_from_plan", "推进主线情节")}
- **本章写作重点**: {chapter_params.get("writing_focus_from_plan", "保持节奏，制造悬念")}
## 3. 角色与世界观
- **世界观设定**: {chapter_params.get("worldview_info", "{}")}
- **人物设定**: {chapter_params.get("character_info", "{}")}
- **一致性铁律**: {chapter_params.get("consistency_guidance", "保持前后文一致")}
## 4. 风格指南
- **小说整体写作风格**: {json.dumps(chapter_params.get("writing_style_guide", {}), ensure_ascii=False)}
---
请你作为一名优秀的小说家，根据以上所有指令，直接创作出本章的完整内容。
你的任务是将【写作蓝图】中的六段式场景要点，流畅地、富有文采地串联成一篇完整的、高质量的小说章节。请特别注意每个场景的【功能定位】和【篇幅占比】，确保章节结构清晰，节奏感强。
"""
        # ▲▲▲ 核心修改结束 ▲▲▲
        max_retries = 3
        final_result = None
        for attempt in range(max_retries):
            self.logger.info(f"  ✍️ 第{attempt + 1}/{max_retries}次尝试直接生成第{chapter_number}章内容...")
            # 诊断打印：检查场景是否正确传递
            self.logger.info(f"  [诊断] 第{chapter_number}章场景数量: {len(pre_designed_scenes)}")
            for i, scene in enumerate(pre_designed_scenes[:8]):  # 只打印前2个避免过多输出
                self.logger.info(f"    场景{i+1}: {scene.get('name', 'Unknown')} - {scene.get('position', 'Unknown position')}")
            # 使用你现有的 chapter_content_generation Prompt类型，但传入新的、更丰富的 user_prompt
            # 这个Prompt应该指导LLM直接输出最终的章节JSON
            content_result = self.api_client.generate_content_with_retry(
                "chapter_content_generation",
                user_prompt,
                purpose=f"直接从场景事件生成第{chapter_number}章内容"
            )
            # 诊断打印：检查API返回的结果
            self.logger.info(f"  [诊断] API返回结果类型: {type(content_result).__name__}")
            if isinstance(content_result, dict):
                has_content = 'content' in content_result
                has_title = 'chapter_title' in content_result or 'title' in content_result
                word_count = len(content_result.get("content", "")) if content_result else 0
                success = content_result.get("success", None)
                self.logger.info(f"  [诊断] API结果 - has_content: {has_content}, has_title: {has_title}, word_count: {word_count}, success: {success}")
            if content_result and isinstance(content_result, dict) and len(content_result.get("content", "")) >= 1800:
                self.logger.info(f"  ✅ 第{chapter_number}章内容生成成功，字数达标。")
                final_result = content_result
                break
            else:
                word_count = len(content_result.get("content", "")) if content_result else 0
                self.logger.warn(f"  ⚠️ 第{attempt + 1}次尝试失败或字数不足 ({word_count}字)。")
        if final_result:
            self.logger.info(f"  [诊断] 成功返回最终结果")
            return final_result
        else:
            self.logger.error(f"  ❌ 第{chapter_number}章所有直接生成尝试均失败")
            return None
    def refine_chapter_content(self, chapter_content: Dict) -> Dict:
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
            self.logger.info(f"  🎨 正在优化第{chapter_number}章: {chapter_title}")
            self.logger.info(f"  📊 原始字数: {original_word_count}字")
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
                self.logger.info(f"  ✅ 章节优化完成")
                self.logger.info(f"  📊 优化后字数: {new_word_count}字 ({change_percent:+.1f}%)")
                self.logger.info(f"  ⭐ 质量评分: {score}/10")
                if notes != 'N/A':
                    self.logger.info(f"  📝 优化说明: {notes}")
                # 如果字数变化过大，给出警告但继续使用
                if abs(change_percent) > 20:
                    self.logger.warn(f"  ⚠️ 字数变化较大，建议检查内容完整性")
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
                self.logger.warn(f"  ⚠️ 优化结果验证失败，使用原始内容")
                return chapter_content  # 直接返回原始内容，不做任何修改
        except Exception as e:
            self.logger.error(f"  ❌ 章节优化过程中出错: {e}")
            return chapter_content  # 出错时返回原始内容
    def _validate_optimized_result(self, result: Any) -> bool:
        """修复版优化结果验证 - 支持多种字段名"""
        if not result or not isinstance(result, dict):
            self.logger.error(f"  ❌ 验证失败: 结果为空或不是字典类型")
            return False
        # 支持多种内容字段名
        content_fields = ["optimized_content", "content", "chapter_content"]
        content = None
        for field in content_fields:
            if field in result and result[field]:
                content = result[field]
                break
        if not content or not isinstance(content, str) or not content.strip():
            self.logger.error(f"  ❌ 验证失败: 内容为空或无效")
            self.logger.info(f"      可用字段: {list(result.keys())}")
            return False
        # 检查是否有足够的内容长度
        if len(content.strip()) < 500:  # 最小500字符
            self.logger.error(f"  ❌ 验证失败: 内容过短 ({len(content)}字符)")
            return False
        self.logger.info(f"  ✅ 优化结果验证通过: {len(content)}字符")
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
    def _prepare_chapter_params(self, chapter_number: int, novel_data: Dict) -> Dict:
        self.logger.info(f"  🔍 准备第{chapter_number}章参数...")
        novel_title = novel_data["novel_title"]
        context: GenerationContext = novel_data.get('_current_generation_context')
        # 【【【核心修正：提前生成！】】】
        # ----------------------------------------------------------------------
        # 1. 提前获取世界状态
        world_state = self._get_previous_world_state(novel_title)
        # 2. 提前构建一致性指导，这是后续函数需要的关键数据
        consistency_guidance = self._build_consistency_guidance(world_state, novel_title)
        # ----------------------------------------------------------------------
        # 3. 将一致性指导作为参数，传入场景准备函数
        scene_events, chapter_goal_from_plan, writing_focus_from_plan = self._ensure_scenes_are_ready_for_chapter(
            chapter_number, 
            context, 
            novel_data,
            consistency_guidance  # <-- 将“接力棒”传下去
        )
        # --- 后续的参数准备逻辑基本不变 ---
        character_development_guidance = self._get_character_development_guidance(chapter_number, novel_data)
        event_context = context.event_context if context else {}
        growth_context = context.growth_context if context else {}
        stage_writing_plan = context.stage_plan if context and hasattr(context, 'stage_plan') else {}
        total_chapters = novel_data["current_progress"]["total_chapters"]
        plot_direction = self._get_plot_direction_for_chapter(chapter_number, total_chapters)
        writing_style_guide = novel_data.get("writing_style_guide", {})
        params = {
            "chapter_number": chapter_number,
            "pre_designed_scenes": scene_events,
            "chapter_goal_from_plan": chapter_goal_from_plan,
            "writing_focus_from_plan": writing_focus_from_plan,
            "total_chapters": total_chapters,
            "novel_title": novel_data["novel_title"],
            "novel_synopsis": novel_data["novel_synopsis"],
            "writing_style_guide": writing_style_guide,
            "worldview_info": json.dumps(novel_data["core_worldview"], ensure_ascii=False) if novel_data.get("core_worldview") else "{}",
            "character_info": json.dumps(novel_data["character_design"], ensure_ascii=False) if novel_data.get("character_design") else "{}",
            "character_development_guidance": character_development_guidance,
            "stage_writing_plan": stage_writing_plan,
            "previous_chapters_summary": self._generate_previous_chapters_summary(chapter_number, novel_data),
            "plot_direction": plot_direction["plot_direction"],
            "chapter_connection_note": self._get_chapter_connection_note(chapter_number),
            "character_development_focus": plot_direction.get("character_development_focus", ""),
            "main_character_instruction": self._get_main_character_instruction(novel_data),
            "event_context": json.dumps(event_context, ensure_ascii=False),
            "growth_context": json.dumps(growth_context, ensure_ascii=False),
            "consistency_guidance": consistency_guidance,  # <-- 将提前生成好的指导放入最终参数
        }
        self.logger.info(f"  ✅ 第{chapter_number}章参数准备完成")
        return params
    # 请用此版本完全替换旧的 _find_event_for_decomposition 函数
    def _find_event_for_decomposition(self, chapter_number: int, stage_plan_data: Dict) -> Optional[Dict]:
        self.logger.info(f"  🔍 [动态查找] 正在为第 {chapter_number} 章寻找可分解的父事件...")
        if not stage_plan_data:
            self.logger.error(f"  ❌ 动态查找失败: 传入的计划数据为空。")
            return None
        major_events = stage_plan_data.get("event_system", {}).get("major_events", [])
        if not major_events:
            self.logger.error(f"  ❌ 动态查找失败: 计划中没有任何重大事件。")
            return None
        # 第一优先级：深度搜索 major_event -> composition -> medium_event
        for major_event in major_events:
            major_start, major_end = self.parse_chapter_range(major_event.get("chapter_range", "0-0"))
            if not (major_start <= chapter_number <= major_end):
                continue
            composition = major_event.get("composition")
            if isinstance(composition, dict):
                for part_key in ["起", "承", "转", "合"]:
                    medium_events = composition.get(part_key)
                    if isinstance(medium_events, list):
                        for medium_event in medium_events:
                            med_start, med_end = self.parse_chapter_range(medium_event.get("chapter_range", "0-0"))
                            if med_start <= chapter_number <= med_end:
                                self.logger.info(f"  ✅ 动态查找成功: 第 {chapter_number} 章精确定位到中型事件 '{medium_event.get('name')}'。")
                                return medium_event
        # 第二优先级（兼容旧版/无嵌套计划）：如果深度搜索未找到，则查找并返回整个重大事件
        for major_event in major_events:
            major_start, major_end = self.parse_chapter_range(major_event.get("chapter_range", "0-0"))
            if major_start <= chapter_number <= major_end:
                self.logger.warn(f"  ⚠️ 动态查找：未找到具体的中型事件，返回覆盖此章节的重大事件 '{major_event.get('name')}'。")
                return major_event
        self.logger.error(f"  ❌ 动态查找失败: 在整个计划中都未找到任何覆盖第 {chapter_number} 章的事件。")
        return None
    @staticmethod
    def parse_chapter_range(chapter_range: str) -> Tuple[int, int]:
        """解析章节范围字符串，返回(start, end)元组"""
        if not chapter_range:
            return 1, 1
        # 提取所有数字
        numbers = re.findall(r'\d+', chapter_range)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            return int(numbers[0]), int(numbers[0])
        else:
            return 1, 1
    def _find_special_event_for_chapter(self, chapter_number: int, stage_plan: Dict) -> Optional[Dict]:
        event_system = stage_plan.get("event_system", {})
        # 从 major_events 的嵌套结构中查找
        for major_event in event_system.get("major_events", []):
            for special_event in major_event.get("special_emotional_events", []):
                if self.novel_generator.stage_plan_manager.is_chapter_in_range(chapter_number, special_event.get("chapter_range", "")):
                    self.logger.info(f"    -> 定位到章节 {chapter_number} 对应的特殊情感事件: '{special_event.get('name')}'")
                    # 将父事件名称附加到事件数据中，供后续使用
                    special_event['_parent_major_event_name'] = major_event.get('name', '未知重大事件')
                    return special_event
        # 也可从顶级的 special_emotional_events 列表中查找（作为备用）
        for special_event in event_system.get("special_emotional_events", []):
             if self.novel_generator.stage_plan_manager.is_chapter_in_range(chapter_number, special_event.get("chapter_range", "")):
                 self.logger.info(f"    -> 定位到章节 {chapter_number} 对应的特殊情感事件: '{special_event.get('name')}'")
                 return special_event
        return None
    def _ensure_scenes_are_ready_for_chapter(self, chapter_number: int, context: GenerationContext, novel_data: Dict, consistency_guidance: str) -> Tuple[List[Dict], str, str]:
        self.logger.info(f"\n--- 核心诊断: 进入 _ensure_scenes_are_ready_for_chapter (第 {chapter_number} 章) ---")
        self.logger.info("  [步骤1a] 委托 NovelGenerator 的管理器获取本章的阶段计划...")
        plan_container = self.novel_generator.ensure_stage_plan_for_chapter(chapter_number)
        if not plan_container:
            self.logger.info(f"  [致命错误] 从 StagePlanManager 未能获取到第 {chapter_number} 章的阶段计划。动态生成无法继续。")
            return [], "", ""
        self.logger.info(f"  [步骤1b] 成功从管理器获取到阶段计划: '{plan_container.get('stage_name', '未知阶段名')}'")
        # 检查预设场景
        existing_scenes = []
        if plan_container.get("event_system", {}).get("chapter_scene_events"):
            for chap_events in plan_container["event_system"]["chapter_scene_events"]:
                if chap_events.get("chapter_number") == chapter_number:
                    existing_scenes = chap_events.get("scene_events", [])
                    break
        self.logger.info(f"  [步骤2] 检查预设场景: 在获取到的阶段计划中为第 {chapter_number} 章找到 {len(existing_scenes)} 个场景。")
        if existing_scenes:
            self.logger.info(f"  [决策] 使用 {len(existing_scenes)} 个预设场景，跳过动态生成。")
            event_for_context = self._find_event_for_decomposition(chapter_number, plan_container)
            goal = event_for_context.get("main_goal", "推进预设剧情") if event_for_context else "推进预设剧情"
            focus = event_for_context.get("emotional_focus", "遵循已有场景安排") if event_for_context else "遵循已有场景安排"
            self.logger.info("--- 核心诊断: 流程结束，返回预设场景。 ---\n")
            return existing_scenes, goal, focus
        self.logger.info("  [决策] 未发现可用预设场景，启动【动态生成】流程...")
        major_event_to_process = self._find_event_for_decomposition(chapter_number, plan_container)
        if not major_event_to_process:
            self.logger.info(f"  [错误] 动态生成失败：在阶段 '{plan_container.get('stage_name')}' 的计划中，未能找到任何覆盖第 {chapter_number} 章的父事件。")
            self.logger.info("--- 核心诊断: 流程结束，返回空列表。 ---\n")
            return [], "", ""
        event_name = major_event_to_process.get('name', '未知事件')
        self.logger.info(f"  [步骤3] 成功定位到父事件: '{event_name}'，准备将其分解为场景。")
        # 【【【核心修正：将 consistency_guidance 传入下一层！】】】
        newly_generated_scenes = self._decompose_event_into_scenes(
            major_event_to_process,
            chapter_number,
            context,
            novel_data,
            plan_container,
            consistency_guidance  # <-- 继续传递“接力棒”
        )
        if not newly_generated_scenes:
            self.logger.info(f"  [错误] 动态生成失败：事件'{event_name}'分解后未产生任何场景。")
            self.logger.info("--- 核心诊断: 流程结束，返回空列表。 ---\n")
            return [], "", ""
        self.logger.info(f"  [步骤4] 成功从 StagePlanManager 获得 {len(newly_generated_scenes)} 个新场景。")
        # 持久化新场景
        if "chapters" not in novel_data: novel_data["chapters"] = {}
        if str(chapter_number) not in novel_data["chapters"]: novel_data["chapters"][str(chapter_number)] = {}
        novel_data["chapters"][str(chapter_number)]["scene_events"] = newly_generated_scenes
        self.logger.info("  [步骤5] 已将新生成的场景数据更新回 novel_data['chapters']，供后续使用。")
        chapter_goal_from_plan = major_event_to_process.get("main_goal", f"完成事件'{event_name}'的一部分")
        writing_focus_from_plan = major_event_to_process.get("emotional_focus", "集中描写关键转折")
        self.logger.info(f"  [成功] 动态生成完成。目标: {chapter_goal_from_plan} | 焦点: {writing_focus_from_plan}")
        self.logger.info("--- 核心诊断: 流程结束，返回新生成的场景。 ---\n")
        return newly_generated_scenes, chapter_goal_from_plan, writing_focus_from_plan
    def _decompose_event_into_scenes(self, event_data: Dict, chapter_number: int, context: GenerationContext, novel_data: Dict, plan_container: Dict, consistency_guidance: str) -> List[Dict]:
        self.logger.info(f"    >> 进入真实的场景生成桥接函数 _decompose_event_into_scenes...")
        # --- 准备上下文信息 ---
        top_level_plan_data = novel_data.get("stage_writing_plans", {}).get(plan_container.get("stage_name", ""), {})
        novel_metadata = top_level_plan_data.get("novel_metadata", novel_data)
        novel_title = novel_metadata.get("title", novel_data.get("novel_title", "未知书名"))
        novel_synopsis = novel_metadata.get("synopsis", novel_data.get("novel_synopsis", "未知大纲"))
        plan = plan_container
        if not plan:
            self.logger.info("    >> [错误] 上层函数未能传入有效的 plan_container。")
            return []
        stage_name = plan.get("stage_name", "未知阶段")
        major_event_name = "未知主事件"
        event_name_to_find = event_data.get("name")
        if event_name_to_find:
            for major_event in plan.get("event_system", {}).get("major_events", []):
                found = False
                for phase_events in major_event.get("composition", {}).values():
                    for medium_event in phase_events:
                        if medium_event.get("name") == event_name_to_find:
                            major_event_name = major_event.get("name", "未知主事件")
                            found = True
                            break
                    if found: break
                if found: break
        generated_scenes = []
        try:
            generated_scenes = self.novel_generator.stage_plan_manager._generate_scenes_for_single_chapter_event(
                event_data=event_data,
                chapter_num=chapter_number,
                stage_name=stage_name,
                major_event_name=major_event_name,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                consistency_guidance=consistency_guidance
            )
        except Exception as e:
            self.logger.info(f"    >> [调用异常] 调用 StagePlanManager 时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return []
        if not generated_scenes:
            self.logger.info(f"    >> StagePlanManager 未能生成场景，或返回为空。")
            return []
        self.logger.info(f"    >> StagePlanManager 已成功返回 {len(generated_scenes)} 个场景。")
        # ▼▼▼【核心修改点：更新计划对象并调用持久化方法】▼▼▼
        self.logger.info(f"    >> 正在将新生成的 {len(generated_scenes)} 个场景同步到章节 {chapter_number} 并持久化...")
        # 确保 plan_container 的结构完整
        if "event_system" not in plan:
            plan["event_system"] = {}
        if "chapter_scene_events" not in plan["event_system"]:
            plan["event_system"]["chapter_scene_events"] = []
        chapter_scene_events = plan["event_system"]["chapter_scene_events"]
        # 查找该章节是否已存在条目
        chapter_entry = next((item for item in chapter_scene_events if item.get("chapter_number") == chapter_number), None)
        if chapter_entry:
            # 如果存在，则更新其场景列表
            self.logger.info(f"    >> 更新章节 {chapter_number} 的场景列表。")
            chapter_entry["scene_events"] = generated_scenes
        else:
            # 如果不存在，则创建新条目并添加
            self.logger.info(f"    >> 为章节 {chapter_number} 创建新的场景条目。")
            new_entry = {
                "chapter_number": chapter_number,
                "chapter_goal": f"完成特殊事件 '{event_data.get('name', '未命名')}' 的相关情节",
                "writing_focus": event_data.get('purpose', '深化情感，推进剧情'),
                "scene_events": generated_scenes
            }
            chapter_scene_events.append(new_entry)
            # 保持章节有序
            chapter_scene_events.sort(key=lambda x: x.get("chapter_number", 0))
        # 调用 StagePlanManager 的新公共方法来保存更新后的 plan_container
        try:
            self.novel_generator.stage_plan_manager.save_and_cache_stage_plan(
                stage_name=stage_name,
                plan_data=plan
            )
        except Exception as e:
            self.logger.info(f"    >> [持久化失败] 调用 save_and_cache_stage_plan 时发生错误: {e}")
        # ▲▲▲【核心修改点结束】▲▲▲
        return generated_scenes
    def _get_event_guidance_from_context(self, event_context: Dict, chapter_number: int) -> str:
        """从事件上下文中生成指导 - 修复键名错误版本"""
        if not event_context:
            self.logger.info("   - 事件上下文为空，返回默认指导")
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
                self.logger.info("   - 无活跃事件，返回空窗期指导")
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
                self.logger.info(f"✅ [_get_event_guidance_from_context] 空窗期指导生成成功，长度: {len(result)}")
                return result
            # 处理活跃事件
            guidance_parts.append("## 🎪 活跃事件执行")
            for event in active_events:
                self.logger.info(f"   - 处理事件: {event.get('name')}")
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
            self.logger.info(f"✅ [_get_event_guidance_from_context] 事件指导生成成功，长度: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"❌ [_get_event_guidance_from_context] 生成事件指导时出错: {e}")
            import traceback
            traceback.print_exc()
            return "# 🎯 事件执行指导\n\n事件指导生成失败，请按常规情节推进。"
    def _get_foreshadowing_guidance_from_context(self, foreshadowing_context: Dict, chapter_number: int) -> str:
        """从伏笔上下文中生成指导 - 修复版本"""
        self.logger.info(f"  🎭 生成第{chapter_number}章伏笔指导...")
        if not foreshadowing_context:
            self.logger.warn("  ⚠️ 伏笔上下文为空，返回默认指导")
            return "# 🎭 伏笔铺垫指导\n\n本章暂无特定的伏笔任务。"
        guidance_parts = ["# 🎭 伏笔铺垫指导"]
        # 添加伏笔焦点
        focus = foreshadowing_context.get('foreshadowing_focus', f'第{chapter_number}章伏笔管理')
        guidance_parts.append(f"## {focus}")
        # 处理待引入元素 - 添加详细检查
        elements_to_introduce = foreshadowing_context.get("elements_to_introduce", [])
        self.logger.info(f"  📊 待引入元素数量: {len(elements_to_introduce)}")
        if elements_to_introduce:
            guidance_parts.append("## 🆕 需要引入的元素:")
            for i, element in enumerate(elements_to_introduce):
                if not isinstance(element, dict):
                    self.logger.warn(f"  ⚠️ 元素{i}不是字典类型: {type(element)}")
                    continue
                element_name = element.get('name', f'未知元素{i}')
                element_type = element.get('type', '未知类型')
                purpose = element.get('purpose', '推进情节发展')
                guidance_parts.append(f"- **{element_name}** ({element_type}): {purpose}")
                self.logger.info(f"  ✅ 添加引入元素: {element_name}")
        else:
            guidance_parts.append("## 🆕 需要引入的元素: 暂无")
        # 处理待发展元素
        elements_to_develop = foreshadowing_context.get("elements_to_develop", [])
        self.logger.info(f"  📊 待发展元素数量: {len(elements_to_develop)}")
        if elements_to_develop:
            guidance_parts.append("## 📈 需要发展的元素:")
            for i, element in enumerate(elements_to_develop):
                if not isinstance(element, dict):
                    self.logger.warn(f"  ⚠️ 发展元素{i}不是字典类型: {type(element)}")
                    continue
                element_name = element.get('name', f'未知元素{i}')
                element_type = element.get('type', '未知类型')
                development_arc = element.get('development_arc', '进一步发展')
                guidance_parts.append(f"- **{element_name}** ({element_type}): {development_arc}")
                self.logger.info(f"  ✅ 添加发展元素: {element_name}")
        else:
            guidance_parts.append("## 📈 需要发展的元素: 暂无")
        result = "\n".join(guidance_parts)
        self.logger.info(f"  ✅ 伏笔指导生成完成，长度: {len(result)}")
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
    def generate_writing_style_guide(self, creative_seed: str, category: str, selected_plan: Dict, market_analysis: Dict) -> Optional[Dict]:
        """生成写作风格指南"""
        self.logger.info(f"  🎨 为分类'{category}'生成写作风格指南...")
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
                self.logger.info(f"  ✅ 写作风格指南生成成功")
                return result
            else:
                self.logger.error(f"  ❌ 写作风格指南生成失败")
                return None
        except Exception as e:
            self.logger.error(f"  ❌ 生成写作风格指南时出错: {e}")
            return None  
    def _get_empty_period_guidance(self, chapter_number: int, event_context: Dict) -> str:
        return "# 🎯 事件执行指导\n\n当前处于事件空窗期，重点推进主线情节和角色发展。"
    def _get_previous_world_state(self, novel_title: str) -> Dict:
        return self._consistency_gatherer._get_previous_world_state(novel_title)
    def _build_consistency_guidance(self, world_state: Dict, novel_title: str) -> str:
        if not world_state:
            return ""
        guidance_parts = ["\n--- 一致性铁律 (AI必须严格遵守) ---\n"]
        # 1. 从 world_state 中获取非角色数据
        items = world_state.get('cultivation_items', world_state.get('items', {}))
        skills = world_state.get('cultivation_skills', world_state.get('skills', {}))
        relationships = world_state.get('relationships', {})
        # 2. 从正确的数据源 (character_development.json) 获取角色的“唯一真实来源”数据
        characters = {}
        if novel_title and self.quality_assessor:
            # 通过 quality_assessor 访问其内部方法来加载最新角色数据
            character_dev_data = self.quality_assessor._load_character_development_data(novel_title)
            # 转换为后续代码可用的兼容格式
            for name, data in character_dev_data.items():
                char_status = data.get("status", data.get("attributes", {}).get("status", "active"))
                char_attributes = data.get("attributes", {})
                char_attributes["status"] = char_status
                characters[name] = {"attributes": char_attributes, "update_count": data.get("total_appearances", 1)}
            self.logger.info("   ✅ [ContentGenerator] 已从 character_development.json 加载角色数据用于一致性指导。")
        else:
            # 回退到旧逻辑，以防万一
            characters = world_state.get('characters', {})
            self.logger.warn("   ⚠️ [ContentGenerator] 未能加载最新角色数据，回退使用 world_state 中的角色数据。")
        # ▲▲▲ 核心修复结束 ▲▲▲
        # 1. 【最高优先级】死亡/退场名单
        dead_or_exited_chars = [
            name for name, data in characters.items() 
            if data.get('attributes', {}).get('status', 'active').lower() in ['dead', 'exited', '死亡', '退场']
        ]
        if dead_or_exited_chars:
            guidance_parts.append(f"【🔴绝对禁止】以下角色已死亡或永久退场，绝不能以任何存活形式出现：`{', '.join(dead_or_exited_chars)}`")
        # 2. 【角色核心状态】 (最重要的5个)
        char_list = self._get_sorted_entities(characters) # 使用刚刚添加的辅助函数
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
    def _refine_chapter_plan_with_world_state(self, chapter_number: int, novel_title: str, original_scenes: List[Dict], world_state: Dict, consistency_guidance: str) -> List[Dict]:
        self.logger.info(f"  🧠 [计划精炼] 开始根据世界状态，主动修正第 {chapter_number} 章的场景计划...")
        if not original_scenes:
            self.logger.warn("  ⚠️ 原始场景计划为空，跳过精炼。")
            return []
        # 将核心数据打包成JSON字符串
        original_scenes_str = json.dumps(original_scenes, ensure_ascii=False, indent=2)
        world_state_summary_str = consistency_guidance # 一致性铁律是世界状态的最好摘要
        prompt = f"""
你是一位逻辑严谨、心思缜密的小说连续性编辑。你的唯一任务是确保故事计划与已发生的事实（世界状态）完全一致。
## 任务背景
- 小说: 《{novel_title}》
- 章节: 第 {chapter_number} 章
## 已确定的事实 (世界状态摘要 - Ground Truth)
这是到上一章为止，世界中不可改变的事实。任何与此冲突的计划都必须被修正。
{world_state_summary_str}
## 原始场景计划 (待修正的蓝图)
这是系统根据故事大纲生成的原始计划，它可能没有考虑到最新的世界状态变化。
{original_scenes_str}
## 你的任务
1.  **审查与对比**：逐一检查【原始场景计划】中的每一个场景，将其与【已确定的事实】进行对比。
2.  **识别冲突**：找出所有逻辑矛盾点。例如：
    - 计划让一个已经死亡/退场的角色出场。
    - 计划使用一个已经被消耗/摧毁的物品。
    - 计划让角色出现在一个他逻辑上不可能到达的位置。
    - 计划的情节与已确立的角色关系（如仇人突然合作）相悖。
3.  **修正计划**：在保留原始场景【核心目标(purpose)】和【情感冲击(emotional_impact)】的前提下，修改【关键动作/事件(key_actions)】或其他细节，以解决所有逻辑冲突。你的修改应该是最小化且最合理的。
4.  **返回结果**：返回一个经过修正的、100%符合世界状态的【最终场景计划】。
## 输出要求
# ▼▼▼ 修改开始 ▼▼▼
- 你的输出必须是一个**单一的JSON对象**。
- 此对象必须包含一个唯一的顶级键：`"refined_scenes"`。
- `"refined_scenes"`的值必须是一个包含所有修正后场景的JSON数组。
- 不要添加任何解释性文字，直接返回精炼后的JSON。
"""
        try:
            result = self.api_client.generate_content_with_retry(
                "chapter_plan_refinement", # 这是一个新的Prompt类型
                prompt,
                purpose=f"精炼第{chapter_number}章场景计划"
            )
            # 验证结果
            if result and isinstance(result, dict) and isinstance(result.get("refined_scenes"), list):
                self.logger.info(f"  ✅ [计划精炼] 成功！场景计划已根据世界状态完成修正。")
                return result["refined_scenes"]
            else:
                self.logger.error(f"  ❌ [计划精炼] 失败！AI返回格式不正确，将使用原始计划。返回类型: {type(result)}")
                return original_scenes # 失败时安全回退
        except Exception as e:
            self.logger.error(f"  ❌ [计划精炼] 发生异常: {e}，将使用原始计划。")
            return original_scenes # 异常时安全回退
    def _add_consistency_requirements(self, chapter_params: Dict, world_state: Dict) -> Dict:
        if not world_state:
            return chapter_params
        # ▼▼▼ 修改开始 ▼▼▼
        # 构建一致性指导，并传入 novel_title
        consistency_guidance = self._build_consistency_guidance(world_state, chapter_params.get("novel_title"))
        # ▲▲▲ 修改结束 ▲▲▲
        chapter_params["consistency_guidance"] = f"\n\n## 🔄 一致性要求\n{consistency_guidance}"
        # 存储世界状态供生成使用（使用压缩版本以节省token）
        if hasattr(self, 'quality_assessor') and self.quality_assessor:
            compressed_world_state = self.quality_assessor._compress_world_state_for_assessment(
                world_state, max_chars=8000
            )
            chapter_params["previous_world_state"] = compressed_world_state
        else:
            # 回退：只存储必要的关键字段
            chapter_params["previous_world_state"] = json.dumps({
                "characters": world_state.get("characters", {}),
                "relationships": world_state.get("relationships", {})
            }, ensure_ascii=False, indent=2)
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
            suggestions = self.quality_assessor.world_state_manager.get_character_development_suggestions(
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
                # 修复：正确处理 GenerationContext 对象的属性
                try:
                    event_ctx = current_context.event_context if hasattr(current_context, 'event_context') else {}
                    foreshadowing_ctx = current_context.foreshadowing_context if hasattr(current_context, 'foreshadowing_context') else {}
                    growth_ctx = current_context.growth_context if hasattr(current_context, 'growth_context') else {}
                    context_summary = {
                        "event_context": {
                            "active_events_count": len(event_ctx.get('active_events', [])) if isinstance(event_ctx, dict) else 0,
                            "timeline_summary": event_ctx.get('event_timeline', {}).get('timeline_summary', '') if isinstance(event_ctx, dict) else ''
                        },
                        "foreshadowing_context_count": len(foreshadowing_ctx.get('elements_to_introduce', [])) if isinstance(foreshadowing_ctx, dict) else 0,
                        "growth_context_focus": growth_ctx.get('chapter_specific', {}).get('content_focus', {}) if isinstance(growth_ctx, dict) else {}
                    }
                except Exception as e:
                    context_summary = f"Error extracting context: {e}"
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
            self.logger.info(f"💾 已保存第{chapter_number}章失败记录: {failure_reason}")
        except Exception as e:
            self.logger.warn(f"⚠️ 保存失败记录时出错: {e}")
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
            self.logger.info(f"  💾 失败记录已保存到本地: {filename}")
        except Exception as e:
            self.logger.error(f"  ❌ 本地保存失败: {e}")    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def generate_multiple_plans(self, creative_seed: str, category: str) -> Dict:
        """生成多个不同金手指和主线剧情的小说方案"""
        self.logger.info(f"  🎯 生成3个不同风格的、追求完美的小说方案...")
        # 核心修改：强化Prompt，从源头要求完美设计
        full_prompt = f"""
内容：
创意种子：{creative_seed}
小说分类：{category}
##【！！！最高指令：追求完美！！！】
你必须生成3个不同风格的小说方案。对于**每一个方案**，都必须遵守以下“完美主义”规则：
1.  **金手指设计 (必须完美)**:
    *   金手指必须具备被市场验证过的，可行的金手指方案。
    *   金手指必须具备高度的【新颖性】和【独特性】。
    *   金手指必须与【主角人设】或【世界观】深度绑定，成为故事有机的一部分，而不是一个工具。
    *   金手指必须具备清晰的【成长潜力】和多种【趣味玩法】。
2.  **核心卖点设计 (必须完美)**:
    *   卖点必须【清晰明确】，一句话就能概括。
    *   卖点必须【极具吸引力】，能瞬间抓住读者眼球。
    *   卖点必须【可执行性强】，能够在整个长篇故事中被反复、持续地展现和升级。
3.  **标题约束**: 每个方案的标题都**必须严格控制在4-15个字符之间（包含标点）**。标题要简洁、有冲击力。
4.  **风格差异**: 3个方案的核心设定（尤其是金手指）和主线发展必须有明显的区别。
如果无法满足上述对“金手指”和“核心卖点”的完美要求，则视为任务失败。
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
                self.logger.info(f"  ✅ 成功生成 {len(result['plans'])} 个不同方案")
                return result
            else:
                self.logger.error("  ❌ 生成多个方案失败，返回格式不正确")
                # 如果返回格式不正确，尝试解析或返回空结果
                return {}
        except Exception as e:
            self.logger.error(f"  ❌ 生成多个方案时出错: {e}")
            import traceback
            traceback.print_exc()
            return {}
