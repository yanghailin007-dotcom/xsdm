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
from src.core.content_generation.chapter_state_manager import (
    ChapterStateManager,
    ChapterEndState,
    SceneTimelineTracker,
    SceneTimelineInfo
)
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
            # 使用 novel_title 和 username 初始化，以使用统一路径配置
            # 关键修复：从 novel_generator 获取 _username，而不是 ContentGenerator 自身
            username = getattr(self.generator.novel_generator, '_username', None)
            wsm = WorldStateManager(novel_title=novel_title, username=username)
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
        self.prompts = Prompts()
        self.event_bus = event_bus
        self.quality_assessor:QualityAssessor = quality_assessor
        self.custom_main_character_name = None
        # 章节状态管理器（延迟初始化）
        self._chapter_state_manager: Optional[ChapterStateManager] = None
        # 场景时间线追踪器（延迟初始化）
        self._timeline_tracker: Optional[SceneTimelineTracker] = None
        # 初始化日志系统
        self.logger = get_logger("ContentGenerator")
        # ▼▼▼ 添加下面两行 ▼▼▼
        project_path = getattr(self.novel_generator, 'project_path', Path.cwd())
        self.design_dir = project_path / "章节详细设计"
        # ▲▲▲ 添加结束 ▲▲▲
        # 初始化辅助类实例
        self._prompt_builder = self._PromptBuilder(self)
        self._consistency_gatherer = self._ConsistencyGatherer(self)

        # 🆕 初始化 MediumEvent 场景管理器
        self._medium_event_manager = None
        self._ensure_medium_event_manager_initialized()
    
    def _ensure_quality_assessor_initialized(self, novel_data: Dict):
        """确保 quality_assessor 已初始化
        
        Raises:
            ValueError: 如果无法获取 novel_title
            RuntimeError: 如果 QualityAssessor 初始化失败
        """
        if self.quality_assessor is not None:
            return  # 已经初始化
        
        self.logger.info("  🔧 QualityAssessor 未初始化，正在初始化...")
        
        from src.core.QualityAssessor import QualityAssessor
        novel_title = novel_data.get("novel_title")
        
        if not novel_title:
            error_msg = "无法初始化 QualityAssessor：novel_title 为空"
            self.logger.error(f"  ❌ {error_msg}")
            raise ValueError(error_msg)
        
        try:
            # 关键修复：从 novel_generator 获取 _username
            username = getattr(self.novel_generator, '_username', None)
            self.quality_assessor = QualityAssessor(
                api_client=self.api_client,
                novel_title=novel_title,
                username=username
            )
            self.logger.info(f"  ✅ QualityAssessor 初始化成功: {novel_title}")
            
        except Exception as e:
            error_msg = f"QualityAssessor 初始化失败: {e}"
            self.logger.error(f"  ❌ {error_msg}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(error_msg) from e

    def _ensure_medium_event_manager_initialized(self):
        """确保 MediumEventSceneManager 已初始化"""
        if self._medium_event_manager is not None:
            return  # 已经初始化

        try:
            from src.managers.MediumEventSceneManager import MediumEventSceneManager
            project_path = getattr(self.novel_generator, 'project_path', Path.cwd())
            self._medium_event_manager = MediumEventSceneManager(project_path=project_path)
            self.logger.info(f"  ✅ MediumEventSceneManager 初始化完成")
        except Exception as e:
            self.logger.error(f"  ❌ MediumEventSceneManager 初始化失败: {e}")
            self._medium_event_manager = None

    def _ensure_chapter_state_manager_initialized(self, novel_data: Dict):
        """确保 ChapterStateManager 已初始化"""
        if self._chapter_state_manager is not None:
            return  # 已经初始化

        novel_title = novel_data.get("novel_title")
        if not novel_title:
            self.logger.warning("  ⚠️ 无法初始化 ChapterStateManager：novel_title 为空")
            return

        try:
            self._chapter_state_manager = ChapterStateManager(
                novel_title=novel_title,
                api_client=self.api_client
            )
            self.logger.info(f"  ✅ ChapterStateManager 初始化成功: {novel_title}")
        except Exception as e:
            self.logger.error(f"  ❌ ChapterStateManager 初始化失败: {e}")

    def _ensure_timeline_tracker_initialized(self, novel_data: Dict):
        """确保 SceneTimelineTracker 已初始化"""
        if self._timeline_tracker is not None:
            return  # 已经初始化

        novel_title = novel_data.get("novel_title")
        if not novel_title:
            self.logger.warning("  ⚠️ 无法初始化 SceneTimelineTracker：novel_title 为空")
            return

        try:
            self._timeline_tracker = SceneTimelineTracker(
                novel_title=novel_title
            )
            self.logger.info(f"  ✅ SceneTimelineTracker 初始化成功: {novel_title}")
        except Exception as e:
            self.logger.error(f"  ❌ SceneTimelineTracker 初始化失败: {e}")

    def get_timeline_tracker(self) -> Optional[SceneTimelineTracker]:
        """获取场景时间线追踪器"""
        return self._timeline_tracker

    def _get_previous_chapter_end_state(self, current_chapter: int, novel_data: Dict) -> Optional[ChapterEndState]:
        """获取上一章的结尾状态"""
        self.logger.info(f"  🔍 [衔接系统] 正在获取第{current_chapter}章的上一章结尾状态...")
        self._ensure_chapter_state_manager_initialized(novel_data)

        if not self._chapter_state_manager:
            self.logger.warning(f"  ⚠️ [衔接系统] 状态管理器未初始化")
            return None

        # 尝试从状态管理器获取
        end_state = self._chapter_state_manager.get_previous_end_state(current_chapter)
        if end_state:
            self.logger.info(f"  ✅ [衔接系统] 从状态管理器获取到上一章结尾状态: {end_state}")
            return end_state

        # 如果状态管理器中没有，尝试从生成的章节文件中读取已保存的end_state
        if current_chapter > 1:
            self.logger.info(f"  📁 [衔接系统] 状态管理器中无状态，尝试从文件加载第{current_chapter-1}章...")
            prev_chapter_data = self._load_chapter_content(current_chapter - 1, novel_data)
            if prev_chapter_data:
                # 检查是否有直接保存的end_state
                end_state_dict = prev_chapter_data.get("end_state")
                if end_state_dict:
                    try:
                        end_state = ChapterEndState.from_dict(end_state_dict)
                        self._chapter_state_manager.set_end_state(end_state)
                        self.logger.info(f"  ✅ [衔接系统] 从文件加载并保存结尾状态: {end_state}")
                        return end_state
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ 解析上一章结尾状态失败: {e}")
                else:
                    self.logger.warning(f"  ⚠️ [衔接系统] 第{current_chapter-1}章文件中没有end_state字段")

        self.logger.info(f"  ℹ️ [衔接系统] 未找到上一章结尾状态，将使用默认衔接")
        return None

    def _build_continuity_context(self, previous_end_state: Optional[ChapterEndState]) -> str:
        """基于上一章结尾状态构建衔接上下文"""
        if not previous_end_state:
            return "这是开篇第一章，需要建立故事基础。"

        return previous_end_state.to_prompt_context()

    def _get_previous_chapter_scenes_summary(self, current_chapter: int, context: 'GenerationContext') -> Optional[Dict]:
        """获取前几章的场景信息概要，用于跨事件场景连续性

        即使章节属于不同的medium_event，前几章的场景信息也应该传递给当前章节，
        以确保AI知道哪些场景已经发生过，避免重复。

        Args:
            current_chapter: 当前章节号
            context: 生成上下文

        Returns:
            包含前几章场景概要的字典，如果没有则返回None
        """
        if current_chapter <= 1:
            return None

        # 通过 stage_plan_manager 获取 plan_container（与 _ensure_scenes_are_ready_for_chapter 一致）
        plan_container = self.novel_generator.stage_plan_manager.get_stage_plan_for_chapter(current_chapter)
        if not plan_container:
            return None

        event_system = plan_container.get("event_system", {})
        chapter_scene_events = event_system.get("chapter_scene_events", [])

        if not chapter_scene_events:
            return None

        # 获取前3章的场景（最多3章，从最近到最远）
        previous_chapters = []
        for i in range(1, min(4, current_chapter)):  # 前1-3章
            prev_chapter_num = current_chapter - i
            for chap_entry in chapter_scene_events:
                if chap_entry.get("chapter_number") == prev_chapter_num:
                    previous_chapters.append({
                        "chapter_number": prev_chapter_num,
                        "scene_events": chap_entry.get("scene_events", [])
                    })
                    break

        if not previous_chapters:
            return None

        # 构建场景概要
        chapters_summary = []
        for prev_chap in previous_chapters:
            chap_num = prev_chap["chapter_number"]
            scenes = prev_chap["scene_events"]

            # 构建该章的详细场景列表
            scene_details = []
            for scene in scenes:
                name = scene.get("name", "未命名场景")
                purpose = scene.get("purpose", "")
                key_actions = scene.get("key_actions", [])
                emotional_impact = scene.get("emotional_impact", "")
                conflict_point = scene.get("conflict_point", "")
                position = scene.get("position", "")

                # 构建详细场景描述
                detail_parts = [f"- **{name}**"]
                if position:
                    detail_parts.append(f" [{position}]")
                if purpose:
                    detail_parts.append(f"\n  目标: {purpose}")
                if key_actions and isinstance(key_actions, list):
                    # 限制关键动作数量，避免过长
                    actions_str = "、".join(key_actions[:3])
                    if actions_str:
                        detail_parts.append(f"\n  关键动作: {actions_str}")
                if conflict_point:
                    detail_parts.append(f"\n  冲突: {conflict_point}")
                if emotional_impact:
                    detail_parts.append(f"\n  情感: {emotional_impact}")

                scene_details.append("".join(detail_parts))

            chapters_summary.append({
                "chapter": chap_num,
                "scene_count": len(scenes),
                "scene_names": scene_details
            })

        return {
            "chapters": chapters_summary,
            "total_chapters": len(previous_chapters),
            "summary_text": self._format_previous_chapters_scenes_summary(chapters_summary)
        }

    def _format_previous_chapters_scenes_summary(self, chapters_summary: list) -> str:
        """格式化前几章场景概要为文本

        Args:
            chapters_summary: 章节概要列表

        Returns:
            格式化的文本字符串
        """
        if not chapters_summary:
            return ""

        lines = ["## 前几章场景概要（用于保持连续性）", ""]
        lines.append("以下是前几章已经发生的场景，请确保本章不重复这些场景，并注意承接上一章的结尾：")
        lines.append("")

        for chap in chapters_summary:
            lines.append(f"### 第{chap['chapter']}章（共{chap['scene_count']}个场景）:")
            for scene_info in chap['scene_names']:
                lines.append(f"  {scene_info}")
            lines.append("")

        return "\n".join(lines)

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
                self.logger.warning(f"  ⚠️ 检测到复杂设定问题: {', '.join(complexity_issues)}")
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
                        self.logger.warning(f"  ⚠️ 优化后新鲜度仍不足，继续重新生成...")
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
                self.logger.warning(f"  ⚠️ QualityAssessor 未初始化，跳过代入感评估。")
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
        self.logger.info(f"📥 输入参数 - novel_title: {novel_title}, selected_plan type: {type(selected_plan)}, market_analysis type: {type(market_analysis)}")
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
        self.logger.info(f"🔄 准备调用 API 生成世界观, context length: {len(context)} chars")
        result = self.api_client.generate_content_with_retry("core_worldview", context, purpose="世界观构建")
        self.logger.info(f"🔄 API 返回结果类型: {type(result)}")
        if result:
            self.logger.info("🔄 开始评估和优化内容...")
            result = self._assess_and_optimize_content(result, "core_worldview", "世界观构建")
            self.logger.info("✅ 世界观构建完成")
        else:
            self.logger.warning("⚠️ API 返回 None，世界观构建失败")
        return result
    def generate_faction_system(self, novel_title: str, core_worldview: Dict,
                               selected_plan: Dict, market_analysis: Dict) -> Optional[Dict]:
        """
        生成势力/阵营系统
        
        Args:
            novel_title: 小说标题
            core_worldview: 核心世界观
            selected_plan: 选定的小说方案
            market_analysis: 市场分析
            
        Returns:
            生成的势力系统数据，失败返回None
        """
        self.logger.info("=== 步骤3.5: 构建势力/阵营系统 ===")
        
        # 构建用户提示词
        user_prompt = f"""
# 故事蓝图
- 小说标题: {novel_title}
- 世界观: {json.dumps(core_worldview, ensure_ascii=False, indent=2)}
- 核心冲突: {selected_plan.get('core_settings', {}).get('world_background', '')}
- 核心卖点: {selected_plan.get('core_settings', {}).get('core_selling_points', [])}

请基于以上信息，设计一个完整的势力/阵营系统，包括：
1. 主要势力列表（3-7个）
2. 每个势力的背景、目标、优劣势
3. 势力间的关系网络（敌对、盟友、中立）
4. 势力在剧情中的作用
5. 推荐主角的初始势力
"""
        
        result = self.api_client.generate_content_with_retry(
            "faction_system_design",
            user_prompt,
            purpose="生成势力/阵营系统"
        )
        
        if result:
            # 应用评估和优化
            result = self._assess_and_optimize_content(result, "faction_system", "势力系统设计")
            if result:
                self.logger.info("✅ 势力/阵营系统生成成功")
                return result
            else:
                self.logger.error("❌ 势力/阵营系统优化失败")
                return None
        else:
            self.logger.error("❌ 势力/阵营系统生成失败")
            return None
    
    def generate_worldview_with_factions(self, novel_title: str, novel_synopsis: str, selected_plan: Dict,
                                         market_analysis: Dict) -> Optional[Dict]:
        """
        🔥 合并优化：同时生成世界观和势力系统
        将两次API调用合并为一次，节省时间且保持连贯性
        """
        self.logger.info("=== 步骤3: 合并构建世界观与势力系统 ===")
        
        # 从selected_plan中提取核心设定
        core_settings = selected_plan.get("core_settings", {})
        story_development = selected_plan.get("story_development", {})
        world_background = core_settings.get("world_background", "")
        golden_finger = core_settings.get("golden_finger", "")
        core_selling_points = core_settings.get("core_selling_points", [])
        protagonist_position = story_development.get("protagonist_position", "")
        main_plot = story_development.get("main_plot", [])
        
        user_prompt = f"""
## 小说信息
- **小说标题**: {novel_title}
- **小说简介**: {novel_synopsis}
- **市场分析**: {json.dumps(market_analysis, ensure_ascii=False)}
- **核心设定**:
  - 世界观背景: {world_background}
  - 金手指/系统: {golden_finger}
  - 核心爽点: {', '.join(core_selling_points) if isinstance(core_selling_points, list) else core_selling_points}
  - 主角定位: {protagonist_position}
  - 主线脉络: {', '.join(main_plot) if isinstance(main_plot, list) else main_plot}

## 核心任务
请同时构建【世界观框架】和【势力系统】，确保两者在逻辑上完全自洽统一。

### 第一部分：世界观框架 (core_worldview)
请提供以下字段：
- world_overview: 世界概览（整体描述）
- power_system: 力量体系（修炼/能力系统详细说明）
- world_rules: 世界规则（运行法则和限制）
- key_locations: 关键地点（列表，3-5个重要场景）
- time_background: 时间背景

### 第二部分：势力系统 (faction_system)
请提供以下字段：
- factions: 势力列表（3-7个主要势力），每个包含：
  - name: 势力名称
  - description: 势力描述
  - goals: 势力目标
  - strengths: 优势
  - weaknesses: 劣势
  - relationships: 与其他势力的关系
- main_conflict: 主要冲突（势力间核心矛盾）
- faction_power_balance: 势力力量对比
- recommended_starting_faction: 推荐主角初始势力

## 设计要求
1. **逻辑自洽**：势力系统必须与世界观设定（尤其是力量体系）保持一致
2. **冲突驱动**：势力间关系要有明确的矛盾点和冲突潜力
3. **主角切入点**：提供主角如何融入这个世界的清晰路径
4. **创新性**：避免常见套路，追求独特性和新颖性

请以JSON格式返回，包含 core_worldview 和 faction_system 两个顶层字段。
"""
        
        try:
            result = self.api_client.generate_content_with_retry(
                "worldview_with_factions",
                user_prompt,
                purpose="合并生成世界观和势力系统"
            )
            
            if result and isinstance(result, dict):
                # 检查结果是否包含两个部分
                has_worldview = 'core_worldview' in result or any(k in result for k in ['world_overview', 'power_system', 'world_rules'])
                has_factions = 'faction_system' in result or 'factions' in result
                
                if has_worldview and has_factions:
                    self.logger.info("✅ 合并世界观与势力系统生成成功")
                    return result
                else:
                    self.logger.warning(f"  ⚠️ 返回格式不完整，尝试兼容处理")
                    return {
                        'core_worldview': result.get('core_worldview', result),
                        'faction_system': result.get('faction_system', result)
                    }
            else:
                self.logger.error("❌ 合并世界观与势力系统生成失败")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 合并生成世界观与势力系统时出错: {e}")
            return None
    
    def generate_character_design(self, novel_title: str, core_worldview: Dict, selected_plan: Dict,
                                  market_analysis: Dict, design_level: str,
                                  existing_characters: Optional[Dict] = None,
                                  stage_info: Optional[Dict] = None,
                                  global_growth_plan: Optional[Dict] = None,       # <-- 新增
                                  overall_stage_plans: Optional[Dict] = None,
                                  custom_main_character_name: str = None,
                                  faction_system: Optional[Dict] = None,
                                  protagonist_only: bool = False) -> Optional[Dict]:
        """
        生成角色设计
        
        Args:
            novel_title: 小说标题
            core_worldview: 核心世界观
            selected_plan: 选定的小说方案
            market_analysis: 市场分析
            design_level: 设计层级 (core/supplementary/protagonist_only)
            existing_characters: 已有角色（补充模式需要）
            stage_info: 阶段信息（补充模式需要）
            global_growth_plan: 全局成长计划
            overall_stage_plans: 整体阶段计划
            custom_main_character_name: 自定义主角名字
            faction_system: 势力系统数据
            protagonist_only: 是否只生成主角
            
        Returns:
            生成的角色设计数据
        """
        self.logger.info(f"  -> 角色设计启动，模式: 【{design_level}】")
        main_character_name = custom_main_character_name or self.custom_main_character_name
        prompt_type = ""
        prompt_context = {}
        purpose = ""
        
        # 🆕 新增：protagonist_only 模式
        if protagonist_only or design_level == "protagonist_only":
            self.logger.info("  🎯 【主角优先模式】只生成主角，暂不生成其他角色")
            prompt_type = "character_design_core"
            # 准备主角设计所需的上下文
            story_blueprint = {
                "novel_title": novel_title,
                "selected_plan": selected_plan,
                "core_worldview": core_worldview,
                "market_analysis": market_analysis,
                "global_growth_plan": global_growth_plan,
                "overall_stage_plans": overall_stage_plans,
                "faction_system": faction_system  # 🆕 添加势力系统信息
            }
            design_requirements = {
                "main_character_name": main_character_name,
                "protagonist_only": True,  # 标记为只生成主角
                "faction_system": faction_system  # 🆕 添加势力系统信息
            }
            prompt_context = {
                "STORY_BLUEPRINT": json.dumps(story_blueprint, ensure_ascii=False, indent=2),
                "DESIGN_REQUIREMENTS": json.dumps(design_requirements, ensure_ascii=False, indent=2)
            }
            purpose = f"为《{novel_title}》设计主角（仅生成主角）"
        # 1. 根据设计层级，选择正确的Prompt并准备上下文
        elif design_level == "core":
            prompt_type = "character_design_core"
            # 准备核心设计所需的上下文
            story_blueprint = {
                "novel_title": novel_title,
                "selected_plan": selected_plan,
                "core_worldview": core_worldview,
                "market_analysis": market_analysis,
                "global_growth_plan": global_growth_plan,
                "overall_stage_plans": overall_stage_plans,
                "faction_system": faction_system  # 🆕 添加势力系统信息
            }
            design_requirements = {
                "main_character_name": main_character_name,
                "required_roles": ["核心盟友/女主", "核心反派"],
                "faction_system": faction_system  # 🆕 添加势力系统信息
            }
            prompt_context = {
                "STORY_BLUEPRINT": json.dumps(story_blueprint, ensure_ascii=False, indent=2),
                "DESIGN_REQUIREMENTS": json.dumps(design_requirements, ensure_ascii=False, indent=2)
            }
            purpose = f"为《{novel_title}》设计核心角色"
        elif design_level == "supplementary":
            # ▼▼▼ 核心修改区域开始 ▼▼▼
            if not existing_characters or not stage_info:
                self.logger.warning("  ⚠️ 补充角色模式缺少'已有角色'或'阶段信息'，操作已取消。")
                return existing_characters
            prompt_type = "character_design_supplementary"
            # 【智能推断】: 不再使用写死的角色，而是根据情节动态推断
            inferred_roles = self._infer_required_roles_for_stage(stage_info, existing_characters)
            # 准备补充设计所需的上下文
            stage_requirements = {
                "stage_name": stage_info.get("stage_name", "当前阶段"),
                "stage_summary": stage_info.get("stage_overview", "未知"), # 从 stage_overview 获取摘要
                "new_character_roles": inferred_roles, # 使用动态推断出的角色！
                "faction_system": faction_system  # 🆕 添加势力系统信息
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
        # 🔧 修复：应该记录序列化后的字符串长度，而不是字典的键值对数量
        # prompt_context_str 已经在上面构建好了，使用它的长度
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
        if design_level == "core" or protagonist_only or design_level == "protagonist_only":
            # 核心模式或主角优先模式直接返回完整的新角色设计
            self.logger.info("  ✅ 角色设计生成成功。")
            if main_character_name:
                result_json = self.ensure_main_character_name(result_json, main_character_name)
            return result_json
        elif design_level == "supplementary":
            # 补充模式需要将新角色合并到旧数据中
            new_characters = result_json.get("newly_added_characters", [])
            if not new_characters:
                self.logger.warning("  ⚠️ 补充角色API调用成功，但未返回新角色。")
                return existing_characters
            self.logger.info(f"  ✅ 成功生成 {len(new_characters)} 个补充角色，正在合并...")
            # 使用深拷贝以确保数据安全
            updated_characters = copy.deepcopy(existing_characters)
            if "important_characters" not in updated_characters:
                updated_characters["important_characters"] = []
            updated_characters["important_characters"].extend(new_characters)
            return updated_characters
    def _infer_required_roles_for_stage(self, stage_info: Dict, existing_characters: Dict) -> List[str]:
        """
        🆕 增强版：事件驱动的角色推断
        
        基于阶段中的事件系统，智能推断所需的角色类型和数量
        
        Args:
            stage_info: 阶段信息
            existing_characters: 已有角色
            
        Returns:
            需要的角色类型列表
        """
        self.logger.info("    -> 正在动态分析阶段情节，推断所需角色...")
        
        # 1. 提取关键情节信息
        event_system = stage_info.get("stage_writing_plan", {}).get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        # 🆕 增强信息收集：分析事件类型、冲突点、特殊情感事件
        plot_summary_parts = [
            f"阶段总体目标: {stage_info.get('stage_overview', '未知')}",
            f"\n## 事件系统分析"
        ]
        
        # 分析主要事件
        for i, event in enumerate(major_events[:5], 1):  # 分析前5个主要事件
            event_name = event.get('name', '')
            event_goal = event.get('main_goal', '')
            event_type = event.get('type', '普通事件')
            plot_summary_parts.append(
                f"{i}. 【{event_type}】{event_name}\n"
                f"   目标: {event_goal}\n"
                f"   章节范围: {event.get('chapter_range', '未知')}"
            )
            
            # 🆕 分析事件组成（中型事件）
            composition = event.get('composition', {})
            if composition:
                for phase_key, phase_events in composition.items():
                    if isinstance(phase_events, list) and phase_events:
                        plot_summary_parts.append(
                            f"   {phase_key}阶段包含 {len(phase_events)} 个中型事件"
                        )
        
        # 🆕 分析特殊情感事件
        special_events = event_system.get("special_emotional_events", [])
        if special_events:
            plot_summary_parts.append(f"\n## 特殊情感事件 ({len(special_events)}个)")
            for i, special in enumerate(special_events[:3], 1):
                plot_summary_parts.append(
                    f"{i}. {special.get('name', '')} - {special.get('purpose', '')}"
                )
        
        stage_plot_summary = "\n".join(plot_summary_parts)
        
        # 2. 提取已有角色名和势力信息
        existing_names = [char.get("name") for char in existing_characters.get("important_characters", [])]
        if existing_characters.get("main_character"):
            existing_names.append(existing_characters["main_character"].get("name"))
        
        # 🆕 提取势力信息
        existing_factions = set()
        for char in existing_characters.get("important_characters", []):
            faction = char.get("faction_affiliation", {}).get("current_faction")
            if faction:
                existing_factions.add(faction)
        
        if existing_characters.get("main_character"):
            main_faction = existing_characters["main_character"].get("faction_affiliation", {}).get("current_faction")
            if main_faction:
                existing_factions.add(main_faction)
        
        faction_info = f"已有势力: {', '.join(existing_factions)}" if existing_factions else "尚未分配势力"
        
        # 3. 构建增强的Prompt上下文
        prompt_context = {
            "STAGE_PLOT_SUMMARY": stage_plot_summary,
            "EXISTING_CHARACTERS": ", ".join(filter(None, existing_names)),
            "FACTION_INFO": faction_info,
            "INFERENCE_GUIDANCE": """
请基于以上事件系统分析，推断出必需的角色类型。
特别注意：
1. 如果事件涉及多个势力的冲突，需要为每个势力生成代表性角色
2. 如果事件包含战斗或竞争，需要生成对手或竞争对手
3. 如果事件需要特定功能（如传授功法、提供情报），需要生成功能性NPC
4. 优先推断与势力系统相关的角色
"""
        }
        
        prompt_context_str = json.dumps(prompt_context, ensure_ascii=False)
        
        # 4. 调用API进行推断
        try:
            roles_data = self.api_client.generate_content_with_retry(
                "role_inference_for_stage",
                prompt_context_str,
                purpose=f"为阶段 '{stage_info.get('stage_name')}' 推断新角色"
            )
            
            if roles_data:
                required_roles = roles_data.get("required_roles", [])
                if required_roles:
                    self.logger.info(f"    -> ✅ 推断成功，需要角色: {', '.join(required_roles)}")
                    return required_roles
        except Exception as e:
            self.logger.warning(f"    -> ⚠️ 角色推断API调用失败: {e}")
        
        # 🆕 改进的回退逻辑：基于事件类型生成更智能的默认角色
        self.logger.info("    -> 使用智能默认值生成角色需求")
        default_roles = []
        
        # 基于主要事件类型生成角色
        if major_events:
            first_event = major_events[0]
            event_goal = first_event.get('main_goal', '').lower()
            
            if any(keyword in event_goal for keyword in ['战斗', '对决', '击败', '复仇']):
                default_roles.extend(["战斗对手", "可能的帮手"])
            elif any(keyword in event_goal for keyword in ['探索', '寻宝', '任务']):
                default_roles.extend(["任务发布者", "同行伙伴"])
            elif any(keyword in event_goal for keyword in ['修炼', '突破', '学习']):
                default_roles.extend(["导师/师长", "竞争对手"])
            else:
                default_roles.extend(["功能性NPC", "阶段性配角"])
        
        # 如果特殊情感事件需要特定角色
        if special_events and not default_roles:
            for special in special_events[:2]:
                purpose = special.get('purpose', '').lower()
                if '感情' in purpose or '爱情' in purpose:
                    default_roles.append("感情线角色")
                    break
        
        return default_roles if default_roles else ["阶段性反派", "功能性NPC"]
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
                    self.logger.warning("  ⚠️ “名场面导演”返回的JSON中snippet为空或过短。")
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
                self.logger.warning(f"⚠️  将主角名字从 '{original_name}' 改为 '{custom_name}'")
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
                    self.logger.warning(f"  ⚠️ {original_purpose}优化失败，使用原内容")
            return content
        except Exception as e:
            self.logger.warning(f"  ⚠️ 评估过程中出错: {e}")
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
                    # 🔧 修复：确保 quality_assessor 已初始化（如果失败会抛出异常）
                    self._ensure_quality_assessor_initialized(novel_data)
                    # 执行到这里说明 quality_assessor 已成功初始化
                    self.quality_assessor.world_state_manager.initialize_world_state_from_novel_data(novel_data["novel_title"], novel_data)
                # 🔧 修复：确保所有章节的 quality_assessor 都已初始化（不只是第1章）
                elif self.quality_assessor is None:
                    self._ensure_quality_assessor_initialized(novel_data)
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

                # 🔥 新增：清理content中的重复标题
                chapter_data = self._clean_duplicate_title_in_content(chapter_data, chapter_number)

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
                    self.logger.warning(f"⚠️ 质量评估失败（API调用失败），使用默认评分")
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
                                self.logger.warning(f"  ⚠️ 第{retry+1}次优化失败，返回空结果")
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
                        self.logger.warning(f"  ⚠️ 所有优化尝试均失败，保持原内容")
                        chapter_data["optimization_info"] = {
                            "optimized": False,
                            "reason": "优化过程失败",
                            "original_score": score
                        }
                else:
                    self.logger.info(f"  ✓ {optimize_reason}")
                    chapter_data["quality_assessment"] = assessment

                # 🆕 提取并保存结尾状态（用于下一章衔接）
                self.logger.info(f"  🔍 [衔接系统] 准备提取第{chapter_number}章结尾状态...")
                end_state = self._extract_and_save_end_state(chapter_data, chapter_number, novel_data)
                if end_state:
                    self.logger.info(f"  ✅ [衔接系统] 第{chapter_number}章结尾状态已保存")
                else:
                    self.logger.warning(f"  ⚠️ [衔接系统] 第{chapter_number}章结尾状态提取失败")

                # AI俏皮开场白
                if chapter_number == 1:
                    try:
                        chapter_data = self.novel_generator._add_ai_spicy_opening_to_first_chapter(
                            chapter_data, novel_data.get("novel_title", ""), novel_data.get("novel_synopsis", ""), novel_data.get("category", "默认")
                        )
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")
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
        """加载章节内容 - 优先从内存加载，失败后从文件系统加载"""
        novel_title = novel_data.get("novel_title", "")
        
        # 步骤1: 首先尝试从内存中加载
        chapter_key = str(chapter_number)
        if chapter_key in novel_data.get("generated_chapters", {}):
            self.logger.info(f"  ✅ 从内存中加载第{chapter_number}章")
            return novel_data["generated_chapters"][chapter_key]
        # 也尝试整数键以保持向后兼容性
        if chapter_number in novel_data.get("generated_chapters", {}):
            self.logger.info(f"  ✅ 从内存中加载第{chapter_number}章 (整数键)")
            return novel_data["generated_chapters"][chapter_number]
        
        # 步骤2: 内存中没有，尝试从文件系统加载
        try:
            from pathlib import Path
            import json
            
            # 构建章节文件路径
            safe_title = novel_title.replace("：", "_").replace("：", "_").replace(" ", "_").replace("：", "_")
            # 更安全的文件名处理
            import re
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', novel_title)
            
            # 获取用户隔离基础路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                user_base_dir = get_user_novel_dir(create=False)
            except Exception:
                user_base_dir = Path("小说项目")
            
            chapters_dir = user_base_dir / safe_title / "chapters"
            if not chapters_dir.exists():
                # 兼容旧路径
                chapters_dir = Path(f"小说项目/{safe_title}/chapters")
                if not chapters_dir.exists():
                    self.logger.warning(f"  ⚠️ 章节目录不存在: {chapters_dir}")
                    return None
            
            # 查找可能的章节文件
            possible_patterns = [
                f"第{chapter_number:03d}章",  # 第001章
                f"第{chapter_number:02d}章",  # 第01章
                f"第{chapter_number}章",      # 第1章
            ]
            
            for pattern in possible_patterns:
                # 查找匹配的文件
                matching_files = list(chapters_dir.glob(f"{pattern}*.json"))
                if matching_files:
                    chapter_file = matching_files[0]  # 使用第一个匹配的文件
                    self.logger.info(f"  📁 从文件加载第{chapter_number}章: {chapter_file.name}")
                    
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    
                    # 可选：将加载的章节数据缓存回内存
                    if "generated_chapters" not in novel_data:
                        novel_data["generated_chapters"] = {}
                    novel_data["generated_chapters"][chapter_key] = chapter_data
                    self.logger.info(f"  ✅ 第{chapter_number}章已缓存到内存")
                    
                    return chapter_data
            
            self.logger.warning(f"  ⚠️ 未找到第{chapter_number}章的文件")
            return None
            
        except Exception as e:
            self.logger.error(f"  ❌ 从文件加载第{chapter_number}章失败: {e}")
            import traceback
            traceback.print_exc()
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
                self.logger.warning(f"  ⚠️  方法 '{method.__name__}' 提取失败: {e}")
                continue
        # 所有方法都失败，使用最后200字作为备选
        fallback_ending = content[-200:] if content_length > 200 else content
        self.logger.warning(f"  ⚠️  所有提取方法失败，使用备选结尾: {fallback_ending[:100]}...")
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
        # 🔧 修复：确保 used_chapter_titles 集合存在
        if "used_chapter_titles" not in novel_data:
            novel_data["used_chapter_titles"] = set()
            self.logger.info("  ✓ 初始化 used_chapter_titles 集合")

        # 🔧 修复：确保返回 chapter_data
        return chapter_data

    def _clean_duplicate_title_in_content(self, chapter_data: Dict, chapter_number: int) -> Dict:
        """清理content中的重复标题"""
        import re

        content = chapter_data.get("content", "")
        chapter_title = chapter_data.get("chapter_title", "")

        if not content or not chapter_title:
            return chapter_data

        # 尝试匹配并移除开头的标题行
        # 匹配模式：第X章 标题 或 第X章：标题 或 直接的标题
        patterns = [
            rf"^第{chapter_number}章[：:\s]+{re.escape(chapter_title)}\s*\n+",  # 第X章：标题
            rf"^第{chapter_number}章\s+{re.escape(chapter_title)}\s*\n+",      # 第X章 标题
            rf"^{re.escape(chapter_title)}\s*\n+",                              # 直接标题
        ]

        cleaned_content = content
        for pattern in patterns:
            match = re.match(pattern, cleaned_content)
            if match:
                cleaned_content = cleaned_content[match.end():]
                self.logger.info(f"  🧹 已清理content开头的重复标题")
                break

        chapter_data["content"] = cleaned_content
        return chapter_data
        
        original_title = chapter_data.get("chapter_title", "")
        if not original_title:
            return chapter_data
        # 检查是否重复
        is_unique, duplicate_chapter = self._is_chapter_title_unique(original_title, chapter_number, novel_data)
        if is_unique:
            novel_data["used_chapter_titles"].add(original_title)
            chapter_data["title_was_changed"] = False
            return chapter_data
        self.logger.warning(f"⚠️  章节标题重复: '{original_title}' 与第{duplicate_chapter}章重复，正在生成新标题...")
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
    def _should_optimize_based_on_config(self, assessment: Dict, retry_count: int = 0, chapter_number: int = None) -> Tuple[bool, str]:
        """基于配置决定是否需要优化 - 使用渐进式阈值

        Args:
            assessment: 质量评估结果
            retry_count: 当前重试次数（0=首次尝试）
            chapter_number: 章节号（用于黄金三章特殊处理）

        Returns:
            (是否需要优化, 原因说明)
        """
        score = assessment.get("overall_score", 0)

        # 使用渐进式质量阈值（根据重试次数动态调整）
        quality_threshold = self.quality_assessor.get_chapter_threshold_for_retry(
            retry_count=retry_count,
            chapter_number=chapter_number
        )

        # 记录当前使用的阈值（方便调试）
        chapter_info = f"第{chapter_number}章" if chapter_number else "当前章节"
        self.logger.info(f"  📊 [{chapter_info} 第{retry_count}次尝试] 使用质量阈值: {quality_threshold:.1f}分")

        # 强制优化阈值
        if score < quality_threshold:
            return True, f"评分{score:.1f}低于优化阈值{quality_threshold:.1f}分（第{retry_count}次尝试），需要优化"

        # 检查字数偏差（可配置阈值）
        word_count_deviation = assessment.get('word_count_deviation', False)
        word_count = assessment.get('word_count', 0)
        if word_count_deviation:
            min_threshold = assessment.get('min_word_threshold', 1500)
            max_threshold = assessment.get('max_word_threshold', 3500)
            if word_count < min_threshold:
                return True, f"字数{word_count}低于阈值{min_threshold}字，需要重新生成"
            else:
                return True, f"字数{word_count}高于阈值{max_threshold}字，需要重新生成"

        # 检查严重一致性问题的存在
        consistency_issues = assessment.get("consistency_issues", [])
        severe_issues = [issue for issue in consistency_issues if issue.get('severity') == '高']
        if severe_issues:
            for issue in severe_issues:
                self.logger.info(f"  - {issue}")
            return True, f"存在{len(severe_issues)}个严重一致性问题，需要优化"

        return False, f"评分{score:.1f}良好，字数符合要求，跳过优化"

    def _build_transition_requirement(self, previous_end_state, chapter_number: int) -> str:
        """构建衔接场景要求"""
        self.logger.info(f"  🔧 [衔接系统] 构建第{chapter_number}章衔接要求...")

        if not previous_end_state or chapter_number == 1:
            self.logger.info(f"  ℹ️ [衔接系统] 第一章或无上一章状态，使用默认衔接")
            return "- **前情提要**: 这是开篇第一章，需要建立故事基础。\n- **衔接要求**: 直接开始故事，无需与上一章衔接。"

        # 根据上一章结尾状态构建衔接要求
        hint = previous_end_state.next_transition_hint or "自然衔接"
        event_status = "已完结" if previous_end_state.event_concluded else "进行中"

        requirement = f"""- **上一章结尾状态**:
  - 时间: {previous_end_state.time_point}
  - 地点: {previous_end_state.location}
  - 氛围: {previous_end_state.atmosphere}
  - 当前事件: {previous_end_state.current_event}（{event_status}）"""

        if previous_end_state.characters:
            requirement += "\n  - 角色状态:"
            for char in previous_end_state.characters[:3]:  # 最多显示3个角色
                char_info = f"    · {char.get('name', '')}"
                if char.get('action'):
                    char_info += f": {char['action']}"
                if char.get('emotion'):
                    char_info += f"（{char['emotion']}）"
                requirement += f"\n{char_info}"

        if previous_end_state.hook:
            requirement += f"\n  - 上一章悬念: {previous_end_state.hook}"

        requirement += f"\n- **衔接建议**: {hint}"

        # 根据事件状态给出具体衔接指导
        if not previous_end_state.event_concluded:
            requirement += "\n- **衔接方式**: 【直接继续】上一章的动作/对话，保持紧迫感，无缝连接。"
        elif hint and "时间" in hint:
            requirement += "\n- **衔接方式**: 【时间跳跃】简述时间流逝和场景变化，然后开始新事件。"
        else:
            requirement += "\n- **衔接方式**: 【事件切换】简短收尾上一事件，自然过渡到本章新事件。"

        self.logger.info(f"  ✅ [衔接系统] 衔接要求构建完成")
        return requirement

    def _extract_and_save_end_state(self, chapter_data: Dict, chapter_number: int, novel_data: Dict) -> Optional[Dict]:
        """从章节生成返回的JSON中提取并保存结尾状态"""
        self.logger.info(f"  🔍 [衔接系统] 提取第{chapter_number}章结尾状态...")

        # 直接从返回的chapter_data中获取end_state
        end_state = chapter_data.get("end_state")

        if not end_state:
            self.logger.warning(f"  ⚠️ [衔接系统] 章节生成结果中无end_state字段")
            return None

        try:
            # 保存结尾状态
            self._ensure_chapter_state_manager_initialized(novel_data)
            if self._chapter_state_manager:
                chapter_end_state = ChapterEndState.from_dict(end_state)
                self._chapter_state_manager.set_end_state(chapter_end_state)
                self.logger.info(f"  📌 [衔接系统] 第{chapter_number}章结尾状态已保存")
                return end_state
        except Exception as e:
            self.logger.warning(f"  ⚠️ [衔接系统] 保存结尾状态失败: {e}")

        return end_state

    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        self.logger.info(f"  🔍 进入【优化版】generate_chapter_content方法...")
        chapter_number = chapter_params.get('chapter_number', '未知')
        pre_designed_scenes = chapter_params.get("pre_designed_scenes", [])
        if not pre_designed_scenes:
            self.logger.error(f"  ❌ 第 {chapter_number} 章缺少预设的场景事件，无法直接生成内容。")
            return None
        # ▼▼▼ 核心修改部分：构建一个能体现6段式结构功能和情绪强度的Prompt ▼▼▼
        # 🆕 第一步：提取和分析本章的情绪强度
        chapter_emotional_intensity = "medium"  # 默认中等强度
        chapter_emotional_focus = []
        intensity_guidance_map = {
            "low": """
## 🌊 情绪强度指南 - 平和节奏 (LOW INTENSITY)
本章采用【平和、内敛】的情绪节奏：
- **情感表达**: 重点在于角色内心的微妙变化和思考，而非外部冲突爆发
- **语言特点**: 使用细腻、温和的语言，避免过度夸张的情感词汇
- **节奏控制**: 节奏较慢，多用内心独白和细腻描写，让读者感受平静中的暗流
- **适用场景**: 日常描写、角色互动、世界观展示、铺垫性章节
""",
            "medium": """
## 🌊 情绪强度指南 - 标准节奏 (MEDIUM INTENSITY)
本章采用【张弛有度、情绪适中】的节奏：
- **情感表达**: 情感真实自然，不过分夸张，让读者产生共鸣
- **语言特点**: 语言流畅自然，平衡叙述和对话，适当使用感叹和强调
- **节奏控制**: 在平静与紧张之间保持平衡，情节推进稳健
- **适用场景**: 推进情节、建立冲突、展现角色成长的标准章节
""",
            "high": """
## 🌊 情绪强度指南 - 激昂节奏 (HIGH INTENSITY)
本章采用【高强度、强冲击】的情绪节奏：
- **情感表达**: 情感表达要强烈、直接、富有张力，使用短句和感叹增强冲击力
- **语言特点**: 语言紧凑有力，多用短句和感叹，营造紧迫感和氛围
- **节奏控制**: 节奏快速，冲突密集，让读者感受到强烈的情绪冲击
- **适用场景**: 高潮章节、重大转折、强烈冲突、情感爆发的关键章节
"""
        }
        
        # 🆕 第二步：分析所有场景的情绪强度，确定本章的整体强度
        intensity_votes = []
        emotional_focus_list = []
        
        for scene in pre_designed_scenes:
            if "emotional_intensity" in scene:
                intensity_votes.append(scene["emotional_intensity"])
            if "emotional_impact" in scene:
                emotional_focus_list.append(f"- 场景「{scene.get('name', '未知场景')}」的情感冲击: {scene['emotional_impact']}")
        
        # 根据场景的情绪强度投票决定本章的整体强度
        if intensity_votes:
            # 统计每种强度的出现次数
            low_count = intensity_votes.count("low")
            medium_count = intensity_votes.count("medium")
            high_count = intensity_votes.count("high")
            
            # 简单的加权逻辑：high的权重最高
            if high_count > 0:
                chapter_emotional_intensity = "high"
            elif low_count > medium_count * 2:  # low占明显多数
                chapter_emotional_intensity = "low"
            else:
                chapter_emotional_intensity = "medium"
        
        self.logger.info(f"  💓 本章情绪强度分析结果: {chapter_emotional_intensity} (投票: {len(intensity_votes)}个场景参与)")
        
        # 🆕 第三步：构建情绪强度指导
        intensity_guidance = intensity_guidance_map.get(chapter_emotional_intensity, intensity_guidance_map["medium"])
        
        # 🆕 第四步：如果场景有情感冲击描述，添加到指导中
        if emotional_focus_list:
            intensity_guidance += f"""
## 🎯 本章情感冲击要点
{chr(10).join(emotional_focus_list[:5])}  # 只显示前5个
"""
        
        # 定义场景定位的中文名称和功能解释
        scene_position_map = {
            "opening": {"name": "开场场景", "function": "建立情境，引入本章核心冲突的起点，快速吸引读者。", "percentage": "15-20%"},
            "development1": {"name": "发展场景1 (Development 1)", "function": "推进情节，深化初始冲突，引入新信息或角色。", "percentage": "20-25%"},
            "development2": {"name": "发展场景2 (Development 2)", "function": "冲突升级，增加紧张感，为高潮做足铺垫。", "percentage": "20-25%"},
            "climax": {"name": "高潮场景", "function": "【本章重点】情感的集中爆发点！这是本章最关键的转折和最强烈的情感冲击所在。", "percentage": "15-20%"},
            "falling": {"name": "回落场景", "function": "处理高潮带来的直接后果，让情绪和节奏得到短暂缓和。", "percentage": "10-15%"},
            "ending": {"name": "结尾场景", "function": "收束本章内容，并设置一个强有力的悬念（钩子），引导读者追读下一章。", "percentage": "5-10%"}
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

        # 🔥 优化：精简写作风格指南，只保留核心要素
        # 注意：writing_style_guide.json 的实际结构是：
        # - core_style (字符串)
        # - dialogue_style (字典)
        # - key_principles (数组)
        # - language_characteristics, narration_techniques, chapter_techniques (字典)
        writing_guide_full = chapter_params.get("writing_style_guide", {})
        if writing_guide_full:
            # 安全地获取对话风格（可能是字典）
            dialogue_style = writing_guide_full.get("dialogue_style", {})
            if isinstance(dialogue_style, dict):
                dialogue_str = "; ".join([f"{k}:{v}" for k, v in dialogue_style.items()])
            else:
                dialogue_str = str(dialogue_style)

            # 安全地获取关键原则（可能是数组）
            key_principles = writing_guide_full.get("key_principles", [])
            if isinstance(key_principles, list):
                principles_str = "; ".join(key_principles)
            else:
                principles_str = str(key_principles)

            writing_style_compressed = {
                "核心风格": writing_guide_full.get("core_style", ""),
                "对话风格": dialogue_str,
                "关键原则": principles_str
            }
        else:
            writing_style_compressed = {}

        # 🔥 优化：将JSON转换为易读的文字格式
        # 世界观：JSON转文字
        worldview_info_json = chapter_params.get("worldview_info", "{}")
        if worldview_info_json and worldview_info_json != "{}":
            try:
                worldview_data = json.loads(worldview_info_json) if isinstance(worldview_info_json, str) else worldview_info_json
                parts = [f"{k}：{v}" for k, v in worldview_data.items()]
                worldview_text = "；".join(parts)
            except:
                worldview_text = worldview_info_json
        else:
            worldview_text = "无特殊设定"

        # 人物：JSON转文字
        character_info_json = chapter_params.get("character_info", "{}")
        if character_info_json and character_info_json != "{}":
            try:
                character_data = json.loads(character_info_json) if isinstance(character_info_json, str) else character_info_json
                parts = [f"{k}：{v}" for k, v in character_data.items()]
                character_text = "；".join(parts)
            except:
                character_text = character_info_json
        else:
            character_text = "无角色信息"

        # 构建章节生成提示词
        # 🆕 获取上一章结尾状态，构建衔接要求
        previous_end_state = chapter_params.get("previous_end_state")
        transition_requirement = self._build_transition_requirement(previous_end_state, chapter_number)

        # 🆕 获取前几章场景概要（用于跨事件场景连续性）
        previous_chapter_scenes = chapter_params.get("previous_chapter_scenes")
        previous_scenes_section = ""
        if previous_chapter_scenes and previous_chapter_scenes.get("summary_text"):
            previous_scenes_section = f"\n{previous_chapter_scenes['summary_text']}\n"

        chapter_generation_prompt = f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_number}章。

{intensity_guidance}

{scenes_input_str}

## 2. 背景与衔接
{transition_requirement}

- **本章核心目标**: {chapter_params.get("chapter_goal_from_plan", "推进主线情节")}
- **本章写作重点**: {chapter_params.get("writing_focus_from_plan", "保持节奏，制造悬念")}

{previous_scenes_section}

## 3. 角色与世界观
- **世界观**: {worldview_text}
- **人物**: {character_text}
- **一致性铁律**: {chapter_params.get("consistency_guidance", "保持前后文一致")}

## 4. 风格指南
- **小说整体写作风格**: {json.dumps(writing_style_compressed, ensure_ascii=False)}

---

请你作为一名优秀的小说家，根据以上所有指令，直接创作出本章的完整内容。
你的任务是将【写作蓝图】中的六段式场景要点，流畅地、富有文采地串联成一篇完整的、高质量的小说章节。请特别注意每个场景的【功能定位】和【篇幅占比】，确保章节结构清晰，节奏感强。

## 5. 字数要求（严格执行）
**目标字数：约2000字（建议范围：1800-2500字）**
- 字数统计包含汉字和标点符号
- 少于{chapter_params.get('min_word_threshold', 1500)}字：情节过于单薄，将被要求重新生成
- 多于{chapter_params.get('max_word_threshold', 3500)}字：内容过于冗长，将被要求重新生成
- 建议控制在1800-2500字之间，确保内容充实且节奏紧凑

**重要提醒**：请严格遵循上述【情绪强度指南】，确保本章的情感表达和节奏控制符合要求的强度级别。
"""
        
        # 保存章节生成提示词到文件
        self._save_chapter_generation_prompt(
            chapter_params.get('novel_title', ''),
            chapter_number,
            chapter_generation_prompt
        )
        
        user_prompt = chapter_generation_prompt  # 使用保存的提示词进行生成
        # ▲▲▲ 核心修改结束 ▲▲▲
        max_retries = 3
        final_result = None
        
        # 🔧 修复：验证并补充场景名称
        for i, scene in enumerate(pre_designed_scenes):
            if not scene.get('name'):
                # 如果缺少name字段，根据position和description生成一个
                position = scene.get('position', 'unknown')
                description = scene.get('description', '')
                purpose = scene.get('purpose', '')
                
                # 生成有意义的场景名称
                if position == 'opening':
                    scene['name'] = '开篇场景：' + (description[:8] if len(description) > 8 else description)
                elif position == 'development1':
                    scene['name'] = '发展场景1：' + (purpose[:8] if len(purpose) > 8 else purpose)
                elif position == 'development2':
                    scene['name'] = '发展场景2：' + (purpose[:8] if len(purpose) > 8 else purpose)
                elif position == 'climax':
                    # 尝试从description或purpose提取有意义的名称
                    if description and len(description) > 0:
                        scene['name'] = '高潮：' + (description[:10] if len(description) > 10 else description)
                    elif purpose and len(purpose) > 0:
                        scene['name'] = '高潮：' + (purpose[:10] if len(purpose) > 10 else purpose)
                    else:
                        scene['name'] = '高潮场景'
                elif position == 'falling':
                    if description and len(description) > 0:
                        scene['name'] = '回落：' + (description[:10] if len(description) > 10 else description)
                    elif purpose and len(purpose) > 0:
                        scene['name'] = '回落：' + (purpose[:10] if len(purpose) > 10 else purpose)
                    else:
                        scene['name'] = '回落场景'
                elif position == 'ending':
                    # 尝试从description或purpose提取有意义的名称
                    if description and len(description) > 0:
                        scene['name'] = '结尾：' + (description[:10] if len(description) > 10 else description)
                    elif purpose and len(purpose) > 0:
                        scene['name'] = '结尾：' + (purpose[:10] if len(purpose) > 10 else purpose)
                    else:
                        scene['name'] = '结尾场景'
                else:
                    scene['name'] = f'场景{i+1}'
                
                self.logger.warning(f"  ⚠️ 场景{i+1}缺少name字段，已自动补充: {scene['name']}")
        
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
                self.logger.warning(f"  ⚠️ 第{attempt + 1}次尝试失败或字数不足 ({word_count}字)。")
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
                    self.logger.warning(f"  ⚠️ 字数变化较大，建议检查内容完整性")
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
                self.logger.warning(f"  ⚠️ 优化结果验证失败，使用原始内容")
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
    def _build_layered_character_info(self, character_design: Dict, scene_events: List[Dict]) -> str:
        """
        构建分层的角色信息，优化token使用

        策略：
        - 主角：完整信息
        - 前3个核心配角：完整信息
        - 其他配角：只传摘要（名称+角色+标签）
        - 场景中提到的角色：确保有完整信息

        Args:
            character_design: 完整的角色设计数据
            scene_events: 本章的场景事件列表

        Returns:
            JSON格式的分层角色信息字符串
        """
        if not character_design:
            return "{}"

        # 提取主角完整信息
        main_character = character_design.get("main_character", {})
        important_characters = character_design.get("important_characters", [])

        # 从场景事件中提取可能涉及的角色名
        scene_character_names = set()
        for scene in scene_events:
            # 从各个文本字段中提取角色名
            for field in ["description", "key_actions", "dialogue_highlights", "purpose", "name"]:
                text = str(scene.get(field, ""))
                # 简单提取：如果文本中包含某个角色的名字，加入集合
                # 这里用后续的匹配逻辑来处理
                pass

        # 构建角色名列表（用于匹配）
        all_character_names = []
        if main_character.get("name"):
            all_character_names.append(main_character["name"])
        for char in important_characters:
            if char.get("name"):
                all_character_names.append(char["name"])

        # 检查场景文本中出现的角色名
        scene_text = ""
        for scene in scene_events:
            for field in ["description", "key_actions", "dialogue_highlights", "purpose", "conflict_point"]:
                if scene.get(field):
                    scene_text += str(scene[field]) + " "

        # 匹配场景中出现的角色名
        for char_name in all_character_names:
            if char_name in scene_text:
                scene_character_names.add(char_name)

        # 构建分层结构
        layered_info = {
            "protagonist": main_character,  # 主角完整信息
            "key_supporting": [],  # 前3个核心配角完整信息
            "mentioned_characters": [],  # 场景中提到的角色（完整信息）
            "other_characters": []  # 其他角色摘要
        }

        # 处理配角
        mentioned_names = scene_character_names - {main_character.get("name")}
        processed = set()

        for char in important_characters:
            char_name = char.get("name", "")
            if not char_name:
                continue

            if char_name in mentioned_names:
                # 场景中提到的角色，完整信息
                layered_info["mentioned_characters"].append(char)
                processed.add(char_name)
            elif len(layered_info["key_supporting"]) < 3:
                # 前3个核心配角，完整信息
                layered_info["key_supporting"].append(char)
                processed.add(char_name)
            else:
                # 其他角色，只传摘要
                summary = {
                    "name": char_name,
                    "role": char.get("role", char.get("position", "未知角色")),
                    "tag": char.get("tag", char.get("personality_tag", char.get("archetype", "")))
                }
                # 如果有soul_matrix，提取核心特质
                if char.get("soul_matrix"):
                    soul = char["soul_matrix"]
                    if isinstance(soul, list) and len(soul) > 0:
                        summary["core_traits"] = soul[:2]  # 只取前2个核心特质
                layered_info["other_characters"].append(summary)

        # 记录日志
        total_chars = 1 + len(important_characters)
        full_info_chars = 1 + len(layered_info["key_supporting"]) + len(layered_info["mentioned_characters"])
        summary_chars = len(layered_info["other_characters"])

        self.logger.info(f"  📊 角色信息分层: 总{total_chars}个角色 → 完整信息{full_info_chars}个 + 摘要{summary_chars}个")

        return json.dumps(layered_info, ensure_ascii=False)

    def _prepare_chapter_params(self, chapter_number: int, novel_data: Dict) -> Dict:
        self.logger.info(f"  🔍 准备第{chapter_number}章参数...")
        novel_title = novel_data["novel_title"]
        context: GenerationContext = novel_data.get('_current_generation_context')

        # 🆕 确保时间线追踪器已初始化
        self._ensure_timeline_tracker_initialized(novel_data)

        # 【【【核心修正：提前生成！】】】
        # ----------------------------------------------------------------------
        # 1. 提前获取世界状态
        world_state = self._get_previous_world_state(novel_title)
        # 2. 提前构建一致性指导，这是后续函数需要的关键数据
        consistency_guidance = self._build_consistency_guidance(world_state, novel_title)
        # 3. 🔥 新增：添加时间线约束到一致性指导
        consistency_guidance = self._add_timeline_constraint_to_guidance(consistency_guidance, chapter_number)
        # ----------------------------------------------------------------------
        # 4. 将一致性指导作为参数，传入场景准备函数
        scene_events, chapter_goal_from_plan, writing_focus_from_plan = self._ensure_scenes_are_ready_for_chapter(
            chapter_number,
            context,
            novel_data,
            consistency_guidance  # <-- 将"接力棒"传下去
        )
        # --- 后续的参数准备逻辑基本不变 ---
        character_development_guidance = self._get_character_development_guidance(chapter_number, novel_data)
        event_context = context.event_context if context else {}
        growth_context = context.growth_context if context else {}
        stage_writing_plan = context.stage_plan if context and hasattr(context, 'stage_plan') else {}
        total_chapters = novel_data["current_progress"]["total_chapters"]
        plot_direction = self._get_plot_direction_for_chapter(chapter_number, total_chapters)
        writing_style_guide = novel_data.get("writing_style_guide", {})

        # 🔍 诊断：打印 writing_style_guide 的加载情况
        if writing_style_guide:
            self.logger.info(f"  ✅ 写作风格指南已加载，包含键: {list(writing_style_guide.keys())}")
        else:
            self.logger.warning(f"  ⚠️ 写作风格指南为空！novel_data中未找到writing_style_guide键或值为空")

        # 🔧 修复：安全获取 novel_synopsis，处理不同的数据结构
        novel_synopsis = None
        if "novel_synopsis" in novel_data:
            novel_synopsis = novel_data["novel_synopsis"]
        elif "novel_info" in novel_data and isinstance(novel_data["novel_info"], dict):
            novel_synopsis = novel_data["novel_info"].get("synopsis")
        elif "synopsis" in novel_data:
            novel_synopsis = novel_data["synopsis"]

        # 如果还是找不到，使用默认值
        if not novel_synopsis:
            novel_synopsis = novel_data.get("novel_title", "未知小说")
            self.logger.warning(f"  ⚠️  未能找到 novel_synopsis，使用标题作为替代")

        # 🆕 使用分层角色信息优化token使用
        character_design = novel_data.get("character_design")
        character_info = self._build_layered_character_info(character_design, scene_events) if character_design else "{}"

        # 🆕 获取上一章结尾状态，用于衔接
        previous_end_state = self._get_previous_chapter_end_state(chapter_number, novel_data)
        continuity_context = self._build_continuity_context(previous_end_state)

        # 🆕 获取前几章的场景信息（用于跨事件场景连续性）
        previous_chapter_scenes_summary = self._get_previous_chapter_scenes_summary(chapter_number, context)
        if previous_chapter_scenes_summary:
            self.logger.info(f"  📜 [场景连续性] 已获取前几章场景概要，共 {len(previous_chapter_scenes_summary.get('chapters', []))} 章")

        params = {
            "chapter_number": chapter_number,
            "pre_designed_scenes": scene_events,
            "chapter_goal_from_plan": chapter_goal_from_plan,
            "writing_focus_from_plan": writing_focus_from_plan,
            "total_chapters": total_chapters,
            "novel_title": novel_data["novel_title"],
            "novel_synopsis": novel_synopsis,
            "writing_style_guide": writing_style_guide,
            "worldview_info": json.dumps(novel_data["core_worldview"], ensure_ascii=False) if novel_data.get("core_worldview") else "{}",
            "character_info": character_info,
            "character_development_guidance": character_development_guidance,
            "stage_writing_plan": stage_writing_plan,
            # 使用新的衔接上下文替代旧的 previous_chapters_summary
            "previous_chapters_summary": continuity_context,
            "previous_end_state": previous_end_state,  # 新增：原始结尾状态对象
            "previous_chapter_scenes": previous_chapter_scenes_summary,  # 新增：前几章场景概要
            "plot_direction": plot_direction["plot_direction"],
            "chapter_connection_note": self._get_chapter_connection_note(chapter_number),
            "character_development_focus": plot_direction.get("character_development_focus", ""),
            "main_character_instruction": self._get_main_character_instruction(novel_data),
            "event_context": json.dumps(event_context, ensure_ascii=False),
            "growth_context": json.dumps(growth_context, ensure_ascii=False),
            "consistency_guidance": consistency_guidance,  # <-- 将提前生成好的指导放入最终参数
            # 🔥 新增：字数阈值参数
            "min_word_threshold": novel_data.get('min_word_threshold', 1500),
            "max_word_threshold": novel_data.get('max_word_threshold', 3500),
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
                self.logger.warning(f"  ⚠️ 动态查找：未找到具体的中型事件，返回覆盖此章节的重大事件 '{major_event.get('name')}'。")
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
        """准备章节场景 - 支持同一 medium_event 场景共享

        核心策略：
        - 跨度=1章：单章生成
        - 跨度=2-3章：一次性生成全部场景，然后分配到各章
        - 跨度>3章：逐章生成，但继承同一 medium_event 内的场景

        降级策略：
        - 如果阶段计划获取失败，尝试使用备用数据源或生成默认场景
        - 如果找不到覆盖章节的中型事件，生成紧急场景
        """
        self.logger.info(f"\n--- 核心诊断: 进入 _ensure_scenes_are_ready_for_chapter (第 {chapter_number} 章) ---")
        self.logger.info("  [步骤1a] 委托 NovelGenerator 的管理器获取本章的阶段计划...")
        plan_container = self.novel_generator.stage_plan_manager.get_stage_plan_for_chapter(chapter_number)

        # 🔥 新增：降级处理 - 阶段计划获取失败
        if not plan_container:
            self.logger.warning(f"  ⚠️ [降级] 从 StagePlanManager 未能获取到第 {chapter_number} 章的阶段计划，尝试生成默认场景...")
            return self._generate_fallback_scenes_for_chapter(chapter_number, novel_data, consistency_guidance,
                                                           reason="阶段计划获取失败")

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

        # 🆕 获取 medium_event 信息
        medium_event = self._find_event_for_decomposition(chapter_number, plan_container)

        # 🔥 新增：降级处理 - 找不到中型事件
        if not medium_event:
            self.logger.warning(f"  ⚠️ [降级] 在阶段 '{plan_container.get('stage_name')}' 的计划中，未能找到任何覆盖第 {chapter_number} 章的中型事件。")
            self.logger.warning(f"  ⚠️ [降级] 尝试使用阶段计划信息生成紧急场景...")
            # 尝试从阶段计划中获取一些上下文信息
            stage_goal = plan_container.get("stage_overview", "推进剧情发展")
            return self._generate_fallback_scenes_for_chapter(chapter_number, novel_data, consistency_guidance,
                                                           reason="中型事件未找到",
                                                           stage_goal=stage_goal,
                                                           plan_container=plan_container)

        # 🆕 计算章节跨度
        chapter_range = medium_event.get('chapter_range', '1-1')
        start_ch, end_ch = self.parse_chapter_range(chapter_range)
        chapter_span = end_ch - start_ch + 1
        event_name = medium_event.get('name', '未知事件')

        self.logger.info(f"  [步骤3] 成功定位到中型事件: '{event_name}'，章节范围: {chapter_range}，跨度: {chapter_span}章")

        # 🆕 根据跨度选择不同的生成策略
        if chapter_span == 1:
            # ===== 单章生成 =====
            self.logger.info(f"  [策略] 单章生成模式 (跨度=1)")
            return self._generate_single_chapter_scenes(
                medium_event, chapter_number, context, novel_data, plan_container, consistency_guidance
            )

        elif chapter_span <= 3:
            # ===== 一次性生成 + 分配 (2-3章) =====
            self.logger.info(f"  [策略] 一次性生成+分配模式 (跨度={chapter_span}<=3)")
            return self._generate_and_distribute_small_event(
                medium_event, chapter_number, start_ch, end_ch, chapter_span,
                context, novel_data, plan_container, consistency_guidance
            )

        else:
            # ===== 逐章生成 + 继承 (>3章) =====
            self.logger.info(f"  [策略] 逐章生成+继承模式 (跨度={chapter_span}>3)")
            return self._generate_multi_chapter_with_inheritance(
                medium_event, chapter_number, start_ch, end_ch,
                context, novel_data, plan_container, consistency_guidance
            )

    # ===========================================================================
    # 🆕 MediumEvent 场景共享机制 - 三个核心方法
    # ===========================================================================

    def _generate_single_chapter_scenes(self, medium_event: Dict, chapter_number: int,
                                       context: GenerationContext, novel_data: Dict,
                                       plan_container: Dict, consistency_guidance: str) -> Tuple[List[Dict], str, str]:
        """单章生成模式 (跨度=1)

        直接调用原有的场景分解逻辑，但也会检查是否有同一medium_event之前章节的场景。
        """
        self.logger.info(f"    >> [单章模式] 为第{chapter_number}章生成场景...")

        event_id = self._medium_event_manager.get_event_id(medium_event, plan_container.get('stage_name', ''))

        # 🆕 即使是单章生成，也检查是否有之前章节的场景需要继承
        inheritance_context = ""
        cached_data = self._medium_event_manager.get_cached_scenes(event_id, chapter_number)
        if cached_data:
            self.logger.info(f"    >> [单章模式] 找到同事件之前章节的场景: {cached_data['previous_chapters']}")
            inheritance_context = self._build_inheritance_context(cached_data, medium_event)

        # 将继承上下文合并到 consistency_guidance
        enhanced_consistency = consistency_guidance + "\n" + inheritance_context

        newly_generated_scenes = self._decompose_event_into_scenes(
            medium_event, chapter_number, context, novel_data, plan_container, enhanced_consistency
        )

        if not newly_generated_scenes:
            return [], "", ""

        # 🔥 新增：验证场景时间递进关系
        if hasattr(self.novel_generator, 'chapter_state_manager'):
            validation_result = self.novel_generator.chapter_state_manager.validate_scene_time_progression(
                chapter_number, newly_generated_scenes
            )
            if not validation_result.get("is_valid"):
                self.logger.warning(f"  ⚠️ 场景时间递进验证发现问题，但仍然使用生成的场景")
            for warning in validation_result.get("warnings", []):
                self.logger.info(f"  ℹ️ {warning}")

        # 🆕 保存当前章节的场景到缓存
        self._update_medium_event_cache(event_id, chapter_number, newly_generated_scenes, medium_event)

        chapter_goal_from_plan = medium_event.get("main_goal", f"完成事件'{medium_event.get('name')}'")
        writing_focus_from_plan = medium_event.get("emotional_focus", "集中描写关键转折")

        return newly_generated_scenes, chapter_goal_from_plan, writing_focus_from_plan

    def _generate_and_distribute_small_event(self, medium_event: Dict, chapter_number: int,
                                           start_ch: int, end_ch: int, chapter_span: int,
                                           context: GenerationContext, novel_data: Dict,
                                           plan_container: Dict, consistency_guidance: str) -> Tuple[List[Dict], str, str]:
        """一次性生成+分配模式 (跨度2-3章)

        一次性生成所有章节的场景，然后智能分配到各章。
        避免同一medium_event被拆分成多次独立生成导致的重复。
        """
        self.logger.info(f"    >> [一次性生成模式] 为跨{chapter_span}章的事件生成所有场景...")

        event_id = self._medium_event_manager.get_event_id(medium_event, plan_container.get('stage_name', ''))

        # 检查是否已生成过
        if self._medium_event_manager.is_event_completed(event_id):
            self.logger.info(f"    >> 事件 {event_id} 已完成，从缓存获取场景")
            cached_scenes = self._medium_event_manager.get_scenes_for_chapter(event_id, chapter_number)
            if cached_scenes:
                return cached_scenes, medium_event.get("main_goal", ""), medium_event.get("emotional_focus", "")

        # 一次性生成所有章节的场景
        all_scenes_by_chapter = self._generate_all_scenes_for_small_event(
            medium_event, start_ch, end_ch, chapter_span,
            context, novel_data, plan_container, consistency_guidance
        )

        if not all_scenes_by_chapter:
            return [], "", ""

        # 构建场景摘要
        event_summary = self._build_event_summary(all_scenes_by_chapter, medium_event)

        # 保存到缓存
        event_data = {
            "medium_event_id": event_id,
            "event_name": medium_event.get('name'),
            "chapter_range": medium_event.get('chapter_range'),
            "total_chapters": chapter_span,
            "status": "completed",
            "scenes": {str(ch): scenes for ch, scenes in all_scenes_by_chapter.items()},
            "global_scene_summary": event_summary
        }
        self._medium_event_manager.save_event_scenes(event_id, event_data)

        # 🆕 同时保存到计划的 chapter_scene_events 数组中（与单章生成保持一致）
        self._save_multi_chapter_scenes_to_plan(
            event_id, plan_container, all_scenes_by_chapter, medium_event, start_ch, end_ch
        )

        # 返回当前请求章节的场景
        current_scenes = all_scenes_by_chapter.get(chapter_number, [])
        return current_scenes, medium_event.get("main_goal", ""), medium_event.get("emotional_focus", "")

    def _save_multi_chapter_scenes_to_plan(self, event_id: str, plan_container: Dict, all_scenes_by_chapter: Dict[int, List[Dict]],
                                          medium_event: Dict, start_ch: int, end_ch: int):
        """将多章生成的场景保存到计划的 chapter_scene_events 数组中

        Args:
            event_id: 中型事件ID（用于清理缓存）
            plan_container: 阶段计划容器
            all_scenes_by_chapter: {chapter_number: [scenes]} 字典
            medium_event: 中型事件数据
            start_ch: 起始章节
            end_ch: 结束章节
        """
        stage_name = plan_container.get('stage_name', '')
        self.logger.info(f"    >> 正在将多章场景同步到计划并持久化...")

        # 确保 plan_container 的结构完整
        if "event_system" not in plan_container:
            plan_container["event_system"] = {}
        if "chapter_scene_events" not in plan_container["event_system"]:
            plan_container["event_system"]["chapter_scene_events"] = []

        chapter_scene_events = plan_container["event_system"]["chapter_scene_events"]

        # 为每个章节保存场景
        for ch_num, scenes in all_scenes_by_chapter.items():
            # 查找该章节是否已存在条目
            chapter_entry = next((item for item in chapter_scene_events if item.get("chapter_number") == ch_num), None)
            if chapter_entry:
                # 如果存在，则更新其场景列表
                self.logger.info(f"    >> 更新章节 {ch_num} 的场景列表 ({len(scenes)} 个场景)")
                chapter_entry["scene_events"] = scenes
            else:
                # 如果不存在，则创建新条目并添加
                self.logger.info(f"    >> 为章节 {ch_num} 创建新的场景条目 ({len(scenes)} 个场景)")
                new_entry = {
                    "chapter_number": ch_num,
                    "chapter_goal": f"完成事件 '{medium_event.get('name', '未命名')}' 的相关情节",
                    "writing_focus": medium_event.get('purpose', '深化情感，推进剧情'),
                    "scene_events": scenes
                }
                chapter_scene_events.append(new_entry)

        # 保持章节有序
        chapter_scene_events.sort(key=lambda x: x.get("chapter_number", 0))

        # 调用 StagePlanManager 的方法来保存更新后的 plan_container
        try:
            self.novel_generator.stage_plan_manager.save_and_cache_stage_plan(
                stage_name=stage_name,
                plan_data=plan_container
            )
            self.logger.info(f"    >> 多章场景已成功保存到计划文件")
        except Exception as e:
            self.logger.error(f"    >> [持久化失败] 保存多章场景时发生错误: {e}")
            return

        # 🔥 场景已整合到写作计划，标记并清理缓存
        try:
            if self._medium_event_manager.mark_event_integrated(event_id):
                # 可选：立即清理缓存，或保留用于调试
                # self._medium_event_manager.clear_event_after_integration(event_id)
                self.logger.info(f"    >> 事件缓存已标记为可清理: {event_id}")
        except Exception as e:
            self.logger.warning(f"    >> 清理事件缓存时出错（非致命）: {e}")

    def _generate_multi_chapter_with_inheritance(self, medium_event: Dict, chapter_number: int,
                                               start_ch: int, end_ch: int,
                                               context: GenerationContext, novel_data: Dict,
                                               plan_container: Dict, consistency_guidance: str) -> Tuple[List[Dict], str, str]:
        """逐章生成+继承模式 (跨度>3章)

        逐章生成，但每次生成时都能看到同一medium_event内之前章节的场景。
        """
        self.logger.info(f"    >> [继承模式] 为第{chapter_number}章生成场景，继承之前章节的场景...")

        event_id = self._medium_event_manager.get_event_id(medium_event, plan_container.get('stage_name', ''))

        # 获取之前章节已生成的场景
        cached_data = self._medium_event_manager.get_cached_scenes(event_id, chapter_number)

        # 构建继承上下文
        inheritance_context = ""
        if cached_data:
            self.logger.info(f"    >> 找到之前章节的场景: {cached_data['previous_chapters']}")
            inheritance_context = self._build_inheritance_context(cached_data, medium_event)

        # 将继承上下文合并到 consistency_guidance
        enhanced_consistency = consistency_guidance + "\n" + inheritance_context

        # 生成当前章节的场景
        newly_generated_scenes = self._decompose_event_into_scenes(
            medium_event, chapter_number, context, novel_data, plan_container, enhanced_consistency
        )

        if not newly_generated_scenes:
            return [], "", ""

        # 🔥 新增：验证场景时间递进关系
        if hasattr(self.novel_generator, 'chapter_state_manager'):
            validation_result = self.novel_generator.chapter_state_manager.validate_scene_time_progression(
                chapter_number, newly_generated_scenes
            )
            if not validation_result.get("is_valid"):
                self.logger.warning(f"  ⚠️ 场景时间递进验证发现问题，但仍然使用生成的场景")
            for warning in validation_result.get("warnings", []):
                self.logger.info(f"  ℹ️ {warning}")

        # 更新缓存
        self._update_medium_event_cache(event_id, chapter_number, newly_generated_scenes, medium_event)

        return newly_generated_scenes, medium_event.get("main_goal", ""), medium_event.get("emotional_focus", "")

    def _generate_all_scenes_for_small_event(self, medium_event: Dict, start_ch: int, end_ch: int, chapter_span: int,
                                            context: GenerationContext, novel_data: Dict,
                                            plan_container: Dict, consistency_guidance: str) -> Dict[int, List[Dict]]:
        """一次性生成跨2-3章的所有场景

        Returns:
            {chapter_number: [scenes]} 字典
        """
        self.logger.info(f"      >> 一次性生成第{start_ch}-{end_ch}章的所有场景...")

        # 构建多章场景生成的prompt
        prompt = self._build_multi_chapter_scene_prompt(
            medium_event, start_ch, end_ch, chapter_span,
            context, novel_data, plan_container, consistency_guidance
        )

        # 调用API生成
        try:
            result = self.api_client.generate_content_with_retry(
                "multi_chapter_scene_design",  # 修正：使用API支持的内容类型
                prompt,
                purpose=f"一次性生成跨{chapter_span}章的场景"
            )
        except Exception as e:
            self.logger.error(f"      >> API调用失败: {e}")
            return {}

        if not result:
            self.logger.error(f"      >> 生成结果为空")
            return {}

        # 解析结果 (API返回的是已解析的字典，不是包含content字段的对象)
        scenes_by_chapter = self._parse_multi_chapter_scenes(result, start_ch, end_ch)

        self.logger.info(f"      >> 成功生成 {len(scenes_by_chapter)} 个章节的场景")
        for ch, scenes in scenes_by_chapter.items():
            self.logger.info(f"         第{ch}章: {len(scenes)}个场景")

        return scenes_by_chapter

    def _build_multi_chapter_scene_prompt(self, medium_event: Dict, start_ch: int, end_ch: int, chapter_span: int,
                                         context: GenerationContext, novel_data: Dict,
                                         plan_container: Dict, consistency_guidance: str) -> str:
        """构建多章场景生成的prompt"""
        from src.utils.SceneContextBuilder import get_scene_context_builder

        stage_name = plan_container.get('stage_name', '未知阶段')
        novel_title = novel_data.get('novel_title', '未知书名')
        novel_synopsis = novel_data.get('novel_synopsis', '')

        # 获取所属重大事件
        major_event = self._find_major_event_for_medium(medium_event, plan_container)

        # 使用共享的上下文构建器
        context_builder = get_scene_context_builder()
        comprehensive_context = context_builder.build_comprehensive_context(
            medium_event, major_event, novel_data, stage_name
        )

        prompt = f"""
# 任务：为跨{chapter_span}章的中型事件生成完整场景序列

## 中型事件信息
- **事件名称**: {medium_event.get('name')}
- **章节范围**: 第{start_ch}章 - 第{end_ch}章
- **事件目标**: {medium_event.get('main_goal', '推进情节')}
- **总章节数**: {chapter_span}
- **情绪重点**: {medium_event.get('emotional_focus', '')}

## 小说信息
- **小说标题**: {novel_title}
- **小说简介**: {novel_synopsis}

{comprehensive_context}

--- 一致性铁律 (AI必须严格遵守) ---

{consistency_guidance}

## 核心要求

1. **完整性**: 这{chapter_span}章共同构成一个完整的故事单元
2. **各章侧重**: 每章应该有不同的重点，避免重复
3. **自然衔接**: 场景在各章之间要流畅过渡
4. **不可重复**: 不要让不同章节处理相同的情节（比如不要两章都写"退婚"）
5. **角色一致性**: 严格遵守角色信息中的设定，确保姓名、性格、修为等一致

## 场景分配建议

"""

        # 添加各章侧重建议
        for i in range(chapter_span):
            ch_num = start_ch + i
            if i == 0:
                focus = f"侧重：[开篇引入 + 初步冲突]。应包含场景序列的开场部分，建立本章核心冲突的起点。"
            elif i == chapter_span - 1:
                focus = f"侧重：[高潮/转折 + 收尾]。应包含场景序列的高潮和结尾，为下一个事件做好铺垫。"
            else:
                focus = f"侧重：[冲突升级 + 中段发展]。应承接上章，深化冲突，推进情节向高潮发展。"

            prompt += f"\n**第{ch_num}章** (约4-6个场景):\n- {focus}\n"

        prompt += """

## 输出格式

请为每一章生成场景列表，每个场景必须包含完整的字段信息：

```json
{{
  "chapter_scenes": {{
    "{start_ch}": [
      {{
        "name": "场景名称（4-12字，有画面感）",
        "sequence": 1,
        "role": "起",
        "position": "opening",
        "description": "场景的详细描述",
        "purpose": "这个场景的核心目的",
        "key_actions": ["关键动作1", "关键动作2"],
        "emotional_intensity": "low",
        "emotional_impact": "带给读者的情感冲击",
        "dialogue_highlights": ["示例对话1", "示例对话2"],
        "conflict_point": "本场景的核心冲突点",
        "sensory_details": "感官细节（视觉、听觉、触觉等）",
        "transition_to_next": "如何过渡到下一个场景",
        "estimated_word_count": 500
      }},
      {{
        "position": "development1",
        "name": "场景名称",
        "sequence": 2,
        "role": "承",
        ...
      }},
      {{
        "position": "climax",
        "name": "场景名称",
        "sequence": 3,
        "role": "转",
        ...
      }},
      {{
        "position": "ending",
        "name": "场景名称",
        "sequence": 4,
        "role": "合",
        ...
      }}
    ],
    "{start_ch + 1}": [
      {{
        "position": "opening",
        "name": "场景名称",
        "sequence": 1,
        "role": "起",
        ...
      }},
      ...
    ]
  }},
  "event_summary": "整个{chapter_span}章的情节摘要（100字以内）"
}}
```

**重要**：
1. 每个场景必须包含全部字段：name, sequence, role, position, description, purpose, key_actions[], emotional_intensity, emotional_impact, dialogue_highlights[], conflict_point, sensory_details, transition_to_next, estimated_word_count
2. sequence 字段表示场景在本章中的顺序（从1开始）
3. role 字段表示场景在戏剧结构中的作用：起/承/转/合
4. emotional_intensity 必须是 low/medium/high 之一
5. key_actions 和 dialogue_highlights 必须是数组格式

请开始生成。
"""
        return prompt

    def _find_major_event_for_medium(self, medium_event: Dict, plan_container: Dict) -> Optional[Dict]:
        """根据中型事件查找所属的重大事件

        Args:
            medium_event: 中型事件
            plan_container: 写作计划容器

        Returns:
            重大事件字典，如果找不到则返回None
        """
        # 从写作计划中获取事件系统
        stage_writing_plan = plan_container.get("stage_writing_plan", {})
        event_system = stage_writing_plan.get("event_system", {})

        # 遍历所有重大事件
        major_events = event_system.get("major_events", [])
        for major_event in major_events:
            composition = major_event.get("composition", {})
            # 检查所有阶段的中型事件
            for phase_events in composition.values():
                for event in phase_events:
                    # 通过名称匹配
                    if event.get("name") == medium_event.get("name"):
                        return major_event

        # 如果没找到，返回空字典而不是None
        return {}

    def _parse_multi_chapter_scenes(self, content, start_ch: int, end_ch: int) -> Dict[int, List[Dict]]:
        """解析多章场景生成结果

        Args:
            content: 可以是字典（已解析）或字符串（JSON文本）
            start_ch: 起始章节
            end_ch: 结束章节
        """
        import json
        import re

        scenes_by_chapter = {}

        # 如果content已经是字典，直接使用
        if isinstance(content, dict):
            result = content
            chapter_scenes = result.get("chapter_scenes", {})
            for ch_str, scenes in chapter_scenes.items():
                ch_num = int(ch_str)
                if start_ch <= ch_num <= end_ch:
                    scenes_by_chapter[ch_num] = scenes
            return scenes_by_chapter

        # 否则尝试从字符串中提取JSON
        # 首先尝试直接解析
        try:
            result = json.loads(content.strip())
            chapter_scenes = result.get("chapter_scenes", {})
            for ch_str, scenes in chapter_scenes.items():
                ch_num = int(ch_str)
                if start_ch <= ch_num <= end_ch:
                    scenes_by_chapter[ch_num] = scenes
            return scenes_by_chapter
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试提取markdown代码块中的JSON
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                chapter_scenes = result.get("chapter_scenes", {})
                for ch_str, scenes in chapter_scenes.items():
                    ch_num = int(ch_str)
                    if start_ch <= ch_num <= end_ch:
                        scenes_by_chapter[ch_num] = scenes
                return scenes_by_chapter
            except json.JSONDecodeError:
                pass

        # 如果JSON解析失败，尝试其他方法
        self.logger.warning("      >> JSON解析失败，尝试备用解析方法")
        # 简化版：为每章生成默认场景
        for ch in range(start_ch, end_ch + 1):
            scenes_by_chapter[ch] = [
                {"position": "opening", "name": f"第{ch}章开场", "purpose": "引入冲突", "key_actions": "", "emotional_impact": "", "estimated_word_count": 500},
                {"position": "development1", "name": f"第{ch}章发展1", "purpose": "推进情节", "key_actions": "", "emotional_impact": "", "estimated_word_count": 500},
                {"position": "climax", "name": f"第{ch}章高潮", "purpose": "冲突爆发", "key_actions": "", "emotional_impact": "", "estimated_word_count": 600},
                {"position": "ending", "name": f"第{ch}章收尾", "purpose": "过渡衔接", "key_actions": "", "emotional_impact": "", "estimated_word_count": 400},
            ]

        return scenes_by_chapter

    def _build_inheritance_context(self, cached_data: Dict, medium_event: Dict) -> str:
        """构建场景继承上下文"""
        previous_chapters = cached_data.get('previous_chapters', [])
        all_previous_scenes = cached_data.get('all_previous_scenes', [])
        event_summary = cached_data.get('event_summary', '')

        context = f"""
## 【同一情节单元的已处理场景 - 请在此基础上继续】

当前中型事件：「{cached_data.get('event_name', medium_event.get('name'))}」
章节范围：{cached_data.get('chapter_range', medium_event.get('chapter_range'))}

此事件跨越多个章节，以下章节**已经处理过**：
"""

        for ch in previous_chapters:
            ch_scenes = cached_data.get('scenes_by_chapter', {}).get(str(ch), [])
            scene_names = [s.get('name', '未命名') for s in ch_scenes]
            context += f"\n- **第{ch}章** ({len(ch_scenes)}个场景): {', '.join(scene_names[:3])}{'...' if len(scene_names) > 3 else ''}"

        context += f"\n\n**事件摘要**: {event_summary}"

        context += """

**重要提醒**：
1. 当前章节是上述已处理章节的**后续**
2. **不要重复**上述章节已经处理过的情节
3. 应该在上述情节的基础上继续推进故事
4. 确保场景之间的自然衔接
"""

        return context

    def _build_event_summary(self, scenes_by_chapter: Dict[int, List[Dict]], medium_event: Dict) -> str:
        """构建事件摘要"""
        total_scenes = sum(len(scenes) for scenes in scenes_by_chapter.values())
        return f"事件「{medium_event.get('name')}」共{len(scenes_by_chapter)}章，{total_scenes}个场景"

    def _update_medium_event_cache(self, event_id: str, chapter_number: int,
                                  scenes: List[Dict], medium_event: Dict):
        """更新medium_event缓存"""
        # 获取现有缓存
        cache_file = self._medium_event_manager.get_cache_file_path(event_id)

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
            except:
                event_data = {
                    "medium_event_id": event_id,
                    "event_name": medium_event.get('name'),
                    "chapter_range": medium_event.get('chapter_range'),
                    "scenes": {},
                    "status": "in_progress"
                }
        else:
            event_data = {
                "medium_event_id": event_id,
                "event_name": medium_event.get('name'),
                "chapter_range": medium_event.get('chapter_range'),
                "scenes": {},
                "status": "in_progress"
            }

        # 更新当前章节的场景
        if "scenes" not in event_data:
            event_data["scenes"] = {}
        event_data["scenes"][str(chapter_number)] = scenes

        # 保存
        self._medium_event_manager.save_event_scenes(event_id, event_data)

    # ===========================================================================
    # 结束：MediumEvent 场景共享机制
    # ===========================================================================

    def _generate_fallback_scenes_for_chapter(self, chapter_number: int, novel_data: Dict,
                                              consistency_guidance: str,
                                              reason: str = "未知原因",
                                              stage_goal: str = None,
                                              plan_container: Dict = None) -> Tuple[List[Dict], str, str]:
        """
        生成降级场景 - 当正常流程失败时使用

        Args:
            chapter_number: 章节号
            novel_data: 小说数据
            consistency_guidance: 一致性指导
            reason: 降级原因
            stage_goal: 阶段目标（如果有）
            plan_container: 计划容器（如果有）

        Returns:
            (场景列表, 章节目标, 写作重点)
        """
        self.logger.warning(f"  🚨 [降级模式] 启动，为第{chapter_number}章生成紧急场景")
        self.logger.warning(f"  🚨 [降级原因] {reason}")

        # 尝试获取基本信息
        novel_title = novel_data.get("novel_title", "未知")
        novel_synopsis = novel_data.get("novel_synopsis", "")

        # 获取章节目标
        chapter_goal = stage_goal or f"推进第{chapter_number}章剧情"
        writing_focus = "根据已有内容自然延续，保持连贯性"

        # 生成4个默认场景（起承转合结构）
        default_scenes = [
            {
                "name": f"第{chapter_number}章开篇",
                "sequence": 1,
                "role": "起",
                "position": "opening",
                "description": f"承接上文的自然开篇，建立本章基础情境",
                "purpose": "引入本章内容，与上文保持连贯",
                "key_actions": ["承接上文", "建立情境", "引入新元素"],
                "emotional_intensity": "low" if chapter_number > 1 else "medium",
                "emotional_impact": "平稳过渡",
                "dialogue_highlights": [],
                "conflict_point": "本章核心冲突的萌芽",
                "sensory_details": "注重氛围描写",
                "transition_to_next": "自然过渡到发展部分",
                "estimated_word_count": 500,
                "chapter_hook": ""
            },
            {
                "name": f"第{chapter_number}章发展",
                "sequence": 2,
                "role": "承",
                "position": "development",
                "description": f"推进情节发展，深化冲突",
                "purpose": "展开本章核心内容，增加复杂性",
                "key_actions": ["情节推进", "角色互动", "信息揭示"],
                "emotional_intensity": "medium",
                "emotional_impact": "逐步上升",
                "dialogue_highlights": [],
                "conflict_point": "冲突逐步显现",
                "sensory_details": "增强细节描写",
                "transition_to_next": "为高潮做铺垫",
                "estimated_word_count": 600,
                "chapter_hook": ""
            },
            {
                "name": f"第{chapter_number}章高潮",
                "sequence": 3,
                "role": "转",
                "position": "climax",
                "description": f"本章的高潮部分，冲突达到顶点",
                "purpose": "形成本章的情感或冲突顶点",
                "key_actions": ["冲突爆发", "关键转折", "情感高潮"],
                "emotional_intensity": "high",
                "emotional_impact": "本章最高点",
                "dialogue_highlights": [],
                "conflict_point": "核心冲突爆发",
                "sensory_details": "强化感官体验",
                "transition_to_next": "开始收束",
                "estimated_word_count": 700,
                "chapter_hook": ""
            },
            {
                "name": f"第{chapter_number}章收尾",
                "sequence": 4,
                "role": "合",
                "position": "ending",
                "description": f"收束本章内容，为下一章铺垫",
                "purpose": "解决本章部分问题，埋下后续伏笔",
                "key_actions": ["收束情节", "解决部分问题", "埋下伏笔"],
                "emotional_intensity": "medium",
                "emotional_impact": "余韵悠长",
                "dialogue_highlights": [],
                "conflict_point": "留下悬念",
                "sensory_details": "营造结束氛围",
                "transition_to_next": "为下一章做好铺垫",
                "estimated_word_count": 400,
                "chapter_hook": "留下吸引读者继续阅读的钩子"
            }
        ]

        # 添加一致性指导到场景描述中
        if consistency_guidance:
            for scene in default_scenes:
                scene["consistency_note"] = "严格遵守一致性指导，不与之前内容冲突"

        self.logger.info(f"  ✅ [降级模式] 已生成{len(default_scenes)}个默认场景")
        return default_scenes, chapter_goal, writing_focus

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
            self.logger.warning("  ⚠️ 伏笔上下文为空，返回默认指导")
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
                    self.logger.warning(f"  ⚠️ 元素{i}不是字典类型: {type(element)}")
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
                    self.logger.warning(f"  ⚠️ 发展元素{i}不是字典类型: {type(element)}")
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
    
    def generate_foundation_planning(self, creative_seed: str, category: str, selected_plan: Dict, novel_title: str, novel_synopsis: str) -> Optional[Dict]:
        """
        🔥 合并优化：同时生成写作风格指南和市场分析
        将两次API调用合并为一次，节省时间且保持质量
        """
        self.logger.info(f"  🎯 合并生成基础规划（写作风格+市场分析）...")
        try:
            # 构建合并提示词
            user_prompt = f"""
请为以下小说同时生成【写作风格指南】和【市场分析】两部分内容。

## 小说信息
小说标题: {novel_title}
小说简介: {novel_synopsis}
小说分类: {category}
小说创意: {creative_seed}
核心主题: {selected_plan.get('core_direction', '')}
目标读者: {selected_plan.get('target_audience', '')}

## 输出要求

### 第一部分：写作风格指南 (writing_style_guide)
请提供以下字段：
- core_style: 核心风格定位（简洁描述，100字以内）
- language_characteristics: 语言特点（列表，3-5个关键词）
- narration_techniques: 叙事技巧（列表，2-3个要点）
- dialogue_style: 对话风格（简洁描述）
- chapter_techniques: 章节技巧（列表）
- key_principles: 核心原则（列表，3-5条）

### 第二部分：市场分析 (market_analysis)
请提供以下字段：
- target_platform: 目标平台（如：番茄小说）
- genre_positioning: 类型定位
- core_selling_points: 核心卖点（列表，3-5条，必须具体且有吸引力）
- target_audience: 目标读者画像（详细描述）
- competitive_advantages: 竞争优势（列表）
- market_risks: 市场风险（列表）
- confidence_score: 信心评分（1-10分）

【创新要求】请提供有深度的分析，避免泛泛而谈，挖掘独特的市场切入点

请以JSON格式返回，包含 writing_style_guide 和 market_analysis 两个顶层字段。
"""
            
            result = self.api_client.generate_content_with_retry(
                "foundation_planning",
                user_prompt,
                purpose="合并生成写作风格指南和市场分析"
            )
            
            if result and isinstance(result, dict):
                # 检查结果是否包含两个部分
                if 'writing_style_guide' in result and 'market_analysis' in result:
                    self.logger.info(f"  ✅ 合并基础规划生成成功")
                    return result
                else:
                    # 尝试兼容旧格式
                    self.logger.warning(f"  ⚠️ 返回格式不完整，尝试兼容处理")
                    return {
                        'writing_style_guide': result.get('writing_style_guide', result),
                        'market_analysis': result.get('market_analysis', result)
                    }
            else:
                self.logger.error(f"  ❌ 合并基础规划生成失败")
                return None
                
        except Exception as e:
            self.logger.error(f"  ❌ 合并生成基础规划时出错: {e}")
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
            self.logger.warning("   ⚠️ [ContentGenerator] 未能加载最新角色数据，回退使用 world_state 中的角色数据。")
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

    def _add_timeline_constraint_to_guidance(self, consistency_guidance: str, chapter_number: int) -> str:
        """
        为一致性指导添加时间线约束

        Args:
            consistency_guidance: 原有的一致性指导
            chapter_number: 当前章节号

        Returns:
            添加了时间线约束的一致性指导
        """
        if chapter_number == 1:
            return consistency_guidance  # 第一章不需要时间线约束

        # 检查是否有时间线追踪器
        if not hasattr(self, '_timeline_tracker') or self._timeline_tracker is None:
            return consistency_guidance

        # 获取上一章的时间线信息
        previous_timeline = self._timeline_tracker.get_previous_timeline(chapter_number)
        if not previous_timeline:
            return consistency_guidance

        # 构建时间线约束
        timeline_constraint = f"""
【🔴时间线铁律 (必须严格遵守)】
- **上一章时间范围**: {previous_timeline.start_time} → {previous_timeline.end_time}
- **上一章关键事件**: {'; '.join(previous_timeline.key_events[-2:]) if previous_timeline.key_events else '无'}
- **绝对禁止**: 严禁从 '{previous_timeline.start_time}' 或之前的时间点重新开始描写
- **正确做法**: 本章必须从 '{previous_timeline.end_time}' 之后的时间点继续，或进行合理的时间跳跃
- **禁止重复**: 不要重复描写上一章已经写过的场景和事件

"""

        # 将时间线约束插入到一致性指导的开头
        if "--- 一致性铁律" in consistency_guidance:
            # 替换原有的分隔符
            consistency_guidance = consistency_guidance.replace(
                "--- 一致性铁律 (AI必须严格遵守) ---\n",
                timeline_constraint + "--- 一致性铁律 (AI必须严格遵守) ---\n"
            )
        else:
            # 如果没有找到原有的分隔符，直接添加到开头
            consistency_guidance = timeline_constraint + consistency_guidance

        return consistency_guidance

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
            self.logger.warning("  ⚠️ 原始场景计划为空，跳过精炼。")
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
            self.logger.warning(f"⚠️ 保存失败记录时出错: {e}")
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
        
        # 🆕 检查是否包含背景资料信息
        background_info_note = ""
        try:
            if isinstance(creative_seed, str):
                # 尝试解析创意种子，检查是否包含背景资料
                creative_data = json.loads(creative_seed)
                if "original_work_background" in creative_data:
                    background_info = creative_data["original_work_background"]
                    verification_result = background_info.get("verification_result", {})
                    if verification_result.get("is_credible", False):
                        work_name = creative_data.get("original_work_name", "未知作品")
                        credibility_level = verification_result.get("credibility_level", "未知")
                        confidence_score = verification_result.get("confidence_score", 0)
                        background_info_note = f"""
##【🎯 背景资料已验证并可用】
- 原著作品: {work_name}
- 可信度等级: {credibility_level}
- 置信度评分: {confidence_score:.2f}
- 状态: 背景资料已成功整合，请严格基于这些设定进行创作

【重要提醒】：
1. 所有方案必须严格遵循提供的背景资料设定
2. 角色性格、世界观、修炼体系等必须与原著保持一致
3. 不得与背景资料中的关键设定产生冲突
4. 充分利用背景资料中的信息来丰富方案设计
"""
                        self.logger.info(f"  ✅ 检测到背景资料: {work_name} ({credibility_level}, 置信度: {confidence_score:.2f})")
                    else:
                        background_info_note = """
##【⚠️ 背景资料验证未通过】
- 状态: 背景资料存在但可信度验证未通过
- 建议: 请谨慎使用背景资料，以创意种子中的核心设定为准
"""
                        self.logger.warning(f"  ⚠️ 背景资料验证未通过，仍将包含在提示中")
        except (json.JSONDecodeError, Exception) as e:
            self.logger.debug(f"  📝 创意种子解析失败或无背景资料: {e}")
        
        # 🔥 优化版本：生成2个高质量方案，自带评分（减少API调用次数）
        full_prompt = f"""
内容：
创意种子：{creative_seed}
小说分类：{category}
{background_info_note}
##【！！！最高指令：追求完美并自我评估！！！】
你必须生成**2个**（不是3个）不同风格的、追求极致完美的小说方案。

对于**每一个方案**，在生成完整内容的同时，你必须进行严格的自我评估并给出分数：

### 方案质量评分标准（满分10分）：
1. **创新性 (0-3分)**: 金手指和核心设定是否新颖独特，避免套路化
2. **吸引力 (0-3分)**: 标题和核心卖点是否能瞬间抓住读者眼球
3. **可执行性 (0-2分)**: 设定能否在长篇故事中持续展现和升级
4. **完整性 (0-2分)**: 世界观、角色、情节是否自洽完整

### 新鲜度评分标准（满分5分）：
1. **题材新颖度 (0-2分)**: 与当前热门作品的差异化程度
2. **设定独特性 (0-2分)**: 金手指和核心机制的独特程度  
3. **创意突破 (0-1分)**: 是否有令人眼前一亮的创新点

### 完美主义规则：
1.  **金手指设计 (必须完美)**:
    *   金手指必须具备被市场验证过的可行性
    *   金手指必须具备高度的【新颖性】和【独特性】
    *   金手指必须与【主角人设】或【世界观】深度绑定
    *   金手指必须具备清晰的【成长潜力】和多种【趣味玩法】
2.  **核心卖点设计 (必须完美)**:
    *   卖点必须【清晰明确】，一句话就能概括
    *   卖点必须【极具吸引力】，能瞬间抓住读者眼球
    *   卖点必须【可执行性强】，能持续展现和升级
3.  **标题约束**: 每个方案的标题都**必须严格控制在4-15个字符之间**
4.  **风格差异**: 2个方案的核心设定必须有明显的区别
5.  **背景资料遵循**: 如有背景资料，必须严格遵循原著设定

### 输出要求：
每个方案必须包含以下评估字段：
- `_quality_score`: 质量总分（满分10分，8.0以上视为优秀）
- `_freshness_score`: 新鲜度总分（满分5分，3.0以上视为合格）
- `_total_score`: 综合总分（质量×0.7 + 新鲜度×0.6，满分10分）
- `_evaluation_notes`: 对各维度的简要评价（50字以内）

只有综合评分8.5分以上的方案才值得返回。
请严格按照JSON格式返回结果。
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
    
    def refine_creative_work_for_ai(self, creative_work: dict, novel_title: str) -> str:
        """
        【指令精炼层 - 核心方法】
        将用户提供的原始创意JSON，转换为对AI具有高度约束力的、结构化的文本指令。
        并将精炼后的指令保存到文本文件中。

        Args:
            creative_work (dict): 用户输入的原始创意JSON对象。
            novel_title (str): 小说标题，用于生成文件名。

        Returns:
            str: 精炼后的、可直接用作AI Prompt的文本指令。
        """
        print("⚙️  正在执行【指令精炼】，将人类创意转换为AI必须遵守的硬性指令...")
        print(f"  📋 输入参数检查:")
        print(f"    - creative_work类型: {type(creative_work)}")
        print(f"    - novel_title: {novel_title}")
        
        # 1. 提取核心组件
        core_setting = creative_work.get("coreSetting", "未提供核心设定。")
        core_selling_points = creative_work.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_work.get("completeStoryline", {})
        
        print(f"  📊 核心组件提取:")
        print(f"    - core_setting长度: {len(core_setting)} 字符")
        print(f"    - core_selling_points长度: {len(core_selling_points)} 字符")
        print(f"    - storyline键数量: {len(storyline)} 个")
        
        # 2. 构建AI精炼提示词
        refinement_prompt = f"""
请将以下小说创意转换为对AI具有高度约束力的、结构化的创作指令：

【原始创意】
核心设定：{core_setting}
核心卖点：{core_selling_points}
故事线：{storyline}

【转换要求】
1. 将创意转换为严格的AI创作指令，包含世界观边界、绝对禁止事项、阶段性目标
2. 强调时间线和地理范围的限制
3. 明确角色行为的约束条件
4. 突出核心卖点的实现路径
5. 用命令式的语言，确保AI必须遵守
6. 结构清晰，分为世界观边界、核心卖点执行纲领、分阶段框架等部分

请生成一个完整的、可直接用作AI Prompt的严格指令：
        """
        
        print(f"  📝 精炼提示词构建完成，长度: {len(refinement_prompt)} 字符")
        
        refined_instruction = None
        try:
            # 3. 调用AI进行真正的精炼
            print("  🤖 开始调用AI进行创意精炼...")
            print(f"  🔍 API客户端检查: {type(self.api_client)}")
            print(f"  🔍 API客户端方法: {hasattr(self.api_client, 'call_api')}")
            
            if not hasattr(self.api_client, 'call_api'):
                print("  ❌ API客户端缺少call_api方法，尝试使用generate_content_with_retry")
                if hasattr(self.api_client, 'generate_content_with_retry'):
                    refined_instruction = self.api_client.generate_content_with_retry(
                        "refine_creative_work_for_ai",
                        refinement_prompt,
                        purpose="创意精炼为AI指令"
                    )
                else:
                    print("  ❌ API客户端没有可用的调用方法")
            else:
                refined_instruction = self.api_client.call_api(
                    "refine_creative_work_for_ai",
                    refinement_prompt,
                    0.7,  # 适度创造性
                    purpose="创意精炼为AI指令"
                )
            
            print(f"  📊 AI调用结果检查:")
            print(f"    - 结果类型: {type(refined_instruction)}")
            print(f"    - 结果是否为None: {refined_instruction is None}")
            if refined_instruction:
                print(f"    - 结果长度: {len(refined_instruction)} 字符")
            
            if not refined_instruction or not isinstance(refined_instruction, str):
                print("  ⚠️ AI精炼失败或返回无效结果，使用基础模板")
                refined_instruction = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
            else:
                print("  ✅ AI精炼成功")
            
            # 4. 保存到文件（使用用户隔离路径）
            print("  💾 开始保存精炼指令到文件...")
            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                
                # 🔥 使用用户隔离路径（从 NovelGenerator 获取用户名）
                try:
                    from web.utils.path_utils import get_user_novel_dir
                    username = getattr(self.novel_generator, '_username', None)
                    output_dir = get_user_novel_dir(username=username, create=True)
                except Exception as e:
                    # 如果失败，使用默认路径
                    print(f"  ⚠️ 获取用户隔离路径失败: {e}，使用默认路径")
                    output_dir = "小说项目"
                
                os.makedirs(output_dir, exist_ok=True)
                output_filepath = os.path.join(output_dir, f"{safe_title}_Refined_AI_Brief.txt")
                
                print(f"  📁 文件路径: {output_filepath}")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(refined_instruction)
                
                print(f"✅  指令精炼完成，已保存至: {output_filepath}")
                print(f"✅  文件大小: {len(refined_instruction)} 字符")
                
                # 验证文件是否真的被创建
                if os.path.exists(output_filepath):
                    file_size = os.path.getsize(output_filepath)
                    print(f"✅  文件验证成功，实际大小: {file_size} 字节")
                else:
                    print(f"❌ 文件验证失败，文件不存在: {output_filepath}")
                    
            except Exception as e:
                print(f"⚠️  保存精炼指令文件失败: {e}")
                import traceback
                traceback.print_exc()
                
            print(f"✅  refine_creative_work_for_ai方法执行完成")
            print(f"  📤 返回结果类型: {type(refined_instruction)}")
            print(f"  📤 返回结果长度: {len(refined_instruction) if refined_instruction else 0} 字符")
            
            return refined_instruction
            
        except Exception as e:
            print(f"❌ AI精炼过程出错: {e}")
            import traceback
            traceback.print_exc()
            print("  🔄 降级到基础模板")
            # 降级到基础模板
            try:
                fallback_result = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
                print(f"✅  基础模板生成成功，长度: {len(fallback_result)} 字符")
                return fallback_result
            except Exception as fallback_error:
                print(f"❌ 基础模板生成也失败: {fallback_error}")
                # 返回一个最基本的指令
                return f"# AI创作指令\n\n请基于以下创意进行创作：\n核心设定：{core_setting}\n核心卖点：{core_selling_points}"
    
    def _save_chapter_generation_prompt(self, novel_title: str, chapter_number: int, prompt: str):
        """保存章节生成提示词到文件，用于内容审核"""
        try:
            import re
            from pathlib import Path
            
            # 清理标题
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', novel_title)
            
            # 获取用户隔离基础路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                user_base_dir = get_user_novel_dir(create=True)
            except Exception:
                user_base_dir = Path("小说项目")
            
            # 创建提示词目录
            prompts_dir = user_base_dir / safe_title / "generation_prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存提示词文件
            prompt_file = prompts_dir / f"第{chapter_number:03d}章_生成提示词.txt"
            
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(f"# 第{chapter_number}章生成提示词\n\n")
                f.write(f"生成时间: {self._get_current_timestamp()}\n")
                f.write(f"小说标题: {novel_title}\n\n")
                f.write("="*60 + "\n")
                f.write("## 完整生成提示词\n\n")
                f.write(prompt)
            
            self.logger.info(f"  💾 第{chapter_number}章生成提示词已保存: {prompt_file}")
            
        except Exception as e:
            self.logger.warning(f"  ⚠️ 保存第{chapter_number}章生成提示词失败: {e}")
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _build_basic_instruction_template(self, core_setting: str, core_selling_points: str, storyline: dict) -> str:
        """
        构建基础指令模板，当AI精炼失败时使用
        
        Args:
            core_setting (str): 核心设定
            core_selling_points (str): 核心卖点
            storyline (dict): 故事线
            
        Returns:
            str: 基础指令模板
        """
        template = f"""
# AI创作指令 - 基础模板

## 世界观边界设定
- 核心世界观：{core_setting}
- 严格遵循以上设定，不得自行添加或修改世界观元素
- 保持设定的逻辑一致性和完整性

## 核心卖点执行纲领
- 主要卖点：{core_selling_points}
- 必须在故事中充分展现和强化上述卖点
- 确保卖点贯穿整个故事主线

## 故事发展框架
- 故事线概要：{storyline}
- 按照既定故事线推进情节发展
- 保持情节的逻辑性和连贯性

## 创作约束
1. 严格遵守世界观设定，不得自相矛盾
2. 角色行为必须符合其性格和背景设定
3. 情节发展要服务核心卖点
4. 保持故事节奏和张力
5. 确保内容的创新性和独特性

请严格按照以上指令进行创作。
        """
        return template.strip()
