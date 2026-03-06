"""
剧情骨架设计器 - 重构版
专注如何将内容转化为剧情（怎么写）

此模块已经过重构，将原来的大型类拆分为多个专职组件：
- EventDecomposer: 负责事件分解
- PlanValidator: 负责计划验证
- StagePlanPersistence: 负责持久化
- EventOptimizer: 负责事件优化
- MajorEventGenerator: 负责重大事件生成
- SceneAssembler: 负责场景组装
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import os
import copy
import json

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger
from src.managers.EventManager import EventManager
from src.managers.WritingGuidanceManager import WritingGuidanceManager
from src.managers.EmotionalPlanManager import EmotionalPlanManager
from src.managers.StagePlanUtils import is_chapter_in_range, parse_chapter_range
from src.managers.MediumEventSceneManager import MediumEventSceneManager
from src.managers.stage_plan import (
    EventDecomposer,
    PlanValidator,
    StagePlanPersistence,
    EventOptimizer,
    MajorEventGenerator,
    SceneAssembler
)


class StagePlanManager:
    """
    剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）
    
    重构后的版本，使用专职组件来处理不同职责。
    """
    
    def __init__(self, novel_generator):
        """
        初始化阶段计划管理器
        
        Args:
            novel_generator: 小说生成器实例
        """
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}
        
        # 初始化日志系统
        self.logger = get_logger("StagePlanManager")
        
        # 为阶段计划创建专用的存储目录（必须在初始化组件之前）
        self.plans_dir = Path("./小说项目").resolve()
        os.makedirs(self.plans_dir, exist_ok=True)
        
        # 初始化各个管理器
        self.event_manager = EventManager(self)
        self.writing_guidance_manager = WritingGuidanceManager(self)
        
        # 初始化专职组件
        self._init_components()
        
        # 阶段特性描述（"起承转合"四段式）
        self.stage_characteristics = {
            "opening_stage": {
                "name": "起 (开局阶段)",
                "focus": "快速建立强烈冲突，立即吸引读者",
                "pace": "极快节奏，前3章必须建立核心冲突",
                "key_elements": "主角惊艳登场、立即冲突、强力悬念、读者共鸣",
                "critical_requirements": [
                    "前3000字内必须建立强烈冲突",
                    "第1章结尾必须有强力追读钩子", 
                    "减少世界观介绍，增加行动和冲突",
                    "主角特质在前2章完全展现"
                ]
            },
            "development_stage": {
                "name": "承 (发展阶段)",
                "focus": "深化矛盾，推进角色成长，扩展世界",
                "pace": "变化节奏，快慢结合，包含多个小高潮",
                "key_elements": "能力提升、盟友敌人、支线展开、伏笔埋设"
            },
            "climax_stage": {
                "name": "转 (高潮阶段)",
                "focus": "主要矛盾全面爆发，剧情发生重大转折",
                "pace": "紧张节奏，逐步加速，直至顶点",
                "key_elements": "关键对决、真相揭露、角色蜕变、情感宣泄"
            },
            "ending_stage": {
                "name": "合 (结局阶段)",
                "focus": "解决所有核心矛盾，收束全部线索，升华主题",
                "pace": "逐渐放缓，情感升华，带来圆满或引人深思的结局",
                "key_elements": "矛盾解决、伏笔回收、角色归宿、主题升华、情感共鸣"
            }
        }
    
    def _init_components(self):
        """初始化专职组件"""
        api_client = self.generator.api_client
        project_path = getattr(self.generator, 'project_path', Path.cwd())

        # 🔥 获取小说标题，用于创建项目隔离的缓存目录
        novel_title = None
        if hasattr(self.generator, 'novel_data') and self.generator.novel_data:
            novel_title = self.generator.novel_data.get('novel_title')

        self.event_decomposer = EventDecomposer(api_client)
        self.plan_validator = PlanValidator()
        self.plan_persistence = StagePlanPersistence(
            self.plans_dir,
            lambda: self.generator.novel_data
        )
        self.event_optimizer = EventOptimizer(api_client)
        self.major_event_generator = MajorEventGenerator(api_client)
        self.scene_assembler = SceneAssembler(api_client)

        # 🔥 新增：初始化中型事件场景管理器（用于跨章场景共享和避免重复）
        # 传入 novel_title 实现项目级别的缓存隔离
        self.medium_event_scene_manager = MediumEventSceneManager(project_path, novel_title)
        self.logger.info(f"MediumEventSceneManager 初始化完成 (项目: {novel_title or '未指定'})")
    
    # ========================================================================
    # 属性访问器
    # ========================================================================
    
    @property
    def emotional_manager(self) -> EmotionalPlanManager:
        """获取情绪计划管理器"""
        return self.generator.emotional_plan_manager
    
    @property
    def romance_manager(self):
        """获取感情管理器"""
        return getattr(self.generator, 'romance_manager', None)
    
    # ========================================================================
    # 主要公开方法
    # ========================================================================
    
    def generate_overall_stage_plan(self, creative_seed: Any, novel_title: str,
                                   novel_synopsis: str, market_analysis: Dict,
                                   global_growth_plan: Dict, emotional_blueprint: Dict,
                                   total_chapters: int) -> Optional[Dict]:
        """
        生成全书阶段计划（"起承转合"四段式）
        
        Args:
            creative_seed: 创意种子
            novel_title: 小说标题
            novel_synopsis: 小说简介
            market_analysis: 市场分析
            global_growth_plan: 全局成长计划
            emotional_blueprint: 情绪蓝图
            total_chapters: 总章节数
            
        Returns:
            生成的阶段计划，失败返回None
        """
        self.logger.info("=== 生成全书阶段计划 ===")
        
        # 🔥 修复：确保 total_chapters 是整数
        total_chapters = int(total_chapters)
        
        stage_arcs = emotional_blueprint.get("stage_emotional_arcs", {})
        emotional_goals_prompt = []
        
        if stage_arcs:
            stage_name_map = {
                "opening_stage": "起 (开局阶段)",
                "development_stage": "承 (发展阶段)",
                "climax_stage": "转 (高潮阶段)",
                "ending_stage": "合 (结局阶段)" 
            }
            for stage_key, arc_info in stage_arcs.items():
                stage_name_cn = stage_name_map.get(stage_key, stage_key)
                emotional_goals_prompt.append(
                    f"- **{stage_name_cn}**: {arc_info.get('description', '无特定情绪目标')}"
                )
        
        emotional_goals_str = "\n".join(emotional_goals_prompt)
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = self._build_overall_stage_prompt(
            creative_seed, novel_title, novel_synopsis, total_chapters,
            boundaries, emotional_goals_str
        )
        
        result = self.generator.api_client.generate_content_with_retry(
            content_type="overall_stage_plan", 
            user_prompt=user_prompt, 
            purpose="制定全书阶段计划"
        )
        
        if result and isinstance(result, dict):
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            self.generator.novel_data["overall_stage_plans"] = result
            self.logger.info("✓ 全书阶段计划生成成功")
            return result
        else:
            self.logger.error("❌ 全书阶段计划生成失败")
            return None
    
    def generate_stage_writing_plan(self, stage_name: str, stage_range: str,
                                   creative_seed: Any, novel_title: str,
                                   novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """
        生成阶段写作计划（重构版 - 使用专职组件）
        
        Args:
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            creative_seed: 创意种子
            novel_title: 小说标题
            novel_synopsis: 小说简介
            overall_stage_plan: 整体阶段计划
            
        Returns:
            生成的阶段写作计划
        """
        # 测试模式快速通道（从配置读取，不再使用环境变量）
        try:
            from config.config import CONFIG
            use_mock_api = CONFIG.get('test_mode', {}).get('use_mock_api', False)
        except ImportError:
            use_mock_api = False
            
        if use_mock_api:
            self.logger.info(f"   [测试模式快速通道] 为【{stage_name}】返回简化版写作计划...")
            return self._generate_simple_stage_plan_for_test(stage_name, stage_range, overall_stage_plan)
        
        # 规范化创意种子
        try:
            from src.utils.seed_utils import ensure_seed_dict
            creative_seed = ensure_seed_dict(creative_seed)
        except Exception:
            if not isinstance(creative_seed, dict):
                creative_seed = {"coreSetting": str(creative_seed)}
        
        # 检查缓存
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            self.logger.info(f"🎬 从缓存加载【{stage_name}】分形写作计划...")
            return self.stage_writing_plans_cache[cache_key]
        
        self.logger.info(f"🎬 开始为【{stage_name}】生成智能分形写作计划...")
        
        # Phase 1: 生成主龙骨（重大事件骨架）
        self.logger.info("   Phase 1: 规划阶段的'主龙骨' (重大事件框架)...")
        major_event_skeletons = self._generate_major_event_skeletons_with_retry(
            stage_name, stage_range, creative_seed, novel_title, novel_synopsis, overall_stage_plan
        )
        
        if not major_event_skeletons:
            self.logger.error(f"    🚨 主龙骨生成失败")
            return {}
        
        # Phase 2: 分解重大事件为中型事件（第一阶段到此为止）
        self.logger.info("   Phase 2: 逐一'解剖'重大事件，填充中型事件...")
        fleshed_out_major_events = self._decompose_major_events_to_medium_only(
            major_event_skeletons, stage_name, stage_range, creative_seed,
            novel_title, novel_synopsis, overall_stage_plan
        )
        
        if not fleshed_out_major_events:
            self.logger.error(f"    🚨 所有重大事件解剖失败")
            return {}
        
        # Phase 3: 验证和优化事件层级
        self.logger.info("   Phase 3: 验证并优化事件层级和连续性...")
        goal_coherence, continuity_assessment = self._validate_and_optimize_events(
            fleshed_out_major_events, stage_name, stage_range, overall_stage_plan
        )
        
        # Phase 4: 组装最终计划并生成补充角色
        self.logger.info("   Phase 4: 组装最终的写作计划...")
        final_writing_plan = self.scene_assembler.assemble_final_plan(
            stage_name, stage_range, fleshed_out_major_events, overall_stage_plan,
            novel_title, novel_synopsis, creative_seed
        )
        
        # 🆕 Phase 4.5: 生成阶段补充角色
        self.logger.info("   Phase 4.5: 为当前阶段生成补充角色...")
        final_writing_plan = self._generate_supplementary_characters_for_stage(
            stage_name, stage_range, final_writing_plan, creative_seed,
            novel_title, novel_synopsis, overall_stage_plan
        )
        
        # 添加评估结果
        if "stage_writing_plan" in final_writing_plan:
            plan_container = final_writing_plan["stage_writing_plan"]
        else:
            plan_container = final_writing_plan
        
        if goal_coherence:
            plan_container["goal_hierarchy_assessment"] = goal_coherence
        if continuity_assessment:
            plan_container["continuity_assessment"] = continuity_assessment
        
        # Phase 5: 验证和保存
        self.logger.info("   Phase 5: 进行最终整体验证和保存...")
        final_writing_plan = self._validate_and_optimize_writing_plan(
            final_writing_plan, stage_name, stage_range
        )
        
        # 🆕 Phase 5.5: 生成期待感映射
        self.logger.info("   Phase 5.5: 为事件生成期待感标签...")
        final_writing_plan = self._generate_expectation_mapping(
            final_writing_plan, stage_name
        )
        
        if final_writing_plan:
            # 保存到文件
            file_path = self.plan_persistence.save_plan_to_file(stage_name, final_writing_plan)
            self.stage_writing_plans_cache[cache_key] = final_writing_plan
            
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            
            if file_path:
                try:
                    project_path = getattr(self.generator, 'project_path', Path.cwd())
                    relative_path = file_path.relative_to(project_path)
                except (AttributeError, ValueError):
                    relative_path = file_path
            else:
                relative_path = f"plans/{stage_name}_writing_plan.json"
            
            self.generator.novel_data["stage_writing_plans"][stage_name] = {"path": str(relative_path)}
            self.logger.info(f"  ✅ 【{stage_name}】分形写作计划生成完成！")
            self._print_fractal_plan_summary(final_writing_plan)
            return final_writing_plan
        else:
            self.logger.error(f"    🚨 【{stage_name}】写作计划生成失败。")
            return {}
    
    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """通过阶段名称获取写作计划"""
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        # 尝试从文件加载
        plan = self.plan_persistence.load_plan_from_file(stage_name)
        if plan:
            self.logger.info(f"  📂 从文件加载了 {stage_name} 的写作计划。")
            self.stage_writing_plans_cache[cache_key] = plan
            return plan
        
        return {}
    
    def load_and_merge_all_plans(self) -> int:
        """加载并合并所有阶段计划到内存"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        
        # 兼容两种数据结构
        if "overall_stage_plan" in overall_plans:
            stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        else:
            stage_plan_dict = overall_plans
        
        if not stage_plan_dict:
            self.logger.warning("  ⚠️ 在 overall_stage_plans 中未找到阶段定义")
            return 0
        
        available_stages = list(stage_plan_dict.keys())
        self.logger.info(f"📋 发现 {len(available_stages)} 个阶段，开始加载并合并写作计划")
        
        loaded_count = 0
        for stage_name in available_stages:
            if self.get_stage_writing_plan_by_name(stage_name):
                loaded_count += 1
        
        if loaded_count > 0:
            self.logger.info(f"  ✅ 成功加载 {loaded_count}/{len(available_stages)} 个阶段的写作计划")
        else:
            self.logger.warning("  ⚠️ 未能加载任何阶段的写作计划")
        
        return loaded_count
    
    def repair_writing_plan(self, plan_container: dict) -> tuple:
        """修复写作计划的场景覆盖完整性"""
        self.logger.info("  - 正在检查计划的场景覆盖完整性...")
        repaired_plan = copy.deepcopy(plan_container)
        
        plan_data = repaired_plan.get("stage_writing_plan", repaired_plan)
        
        # 提取上下文信息
        novel_title = plan_data.get("novel_metadata", {}).get("title", "未知标题")
        novel_synopsis = plan_data.get("novel_metadata", {}).get("synopsis", "未知简介")
        stage_name = plan_data.get("stage_name", "未知阶段")
        
        # 验证场景覆盖
        stage_range = plan_data.get("chapter_range", "1-100")
        coverage_analysis = self.plan_validator.validate_scene_planning_coverage(
            repaired_plan, stage_name, stage_range
        )
        
        missing_chapters = coverage_analysis.get("missing_chapters", [])
        if not missing_chapters:
            self.logger.info("  ✅ 场景覆盖完整，无需修复。")
            return repaired_plan, False
        
        self.logger.warning(f"  ⚠️ 检测到 {len(missing_chapters)} 个章节缺少场景，正在尝试修复")
        
        # 获取必要上下文
        final_major_events = plan_data.get("event_system", {}).get("major_events", [])
        overall_stage_plan = self.generator.novel_data.get("overall_stage_plans", {})
        novel_global_data = self.generator.novel_data
        
        core_worldview = novel_global_data.get("core_worldview", {})
        character_design = novel_global_data.get("character_design", {})
        writing_style_guide = novel_global_data.get("writing_style_guide", {})
        previous_chapters_summary = novel_global_data.get("novel_synopsis", "前情提要不详")
        
        chapters_repaired_count = 0
        for chapter_num in missing_chapters:
            fallback_scenes = self.scene_assembler.generate_fallback_scenes_for_chapter(
                chapter_number=chapter_num,
                stage_name=stage_name,
                final_major_events=final_major_events,
                overall_stage_plan=overall_stage_plan,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                core_worldview=core_worldview,
                character_design=character_design,
                writing_style_guide=writing_style_guide,
                previous_chapters_summary=previous_chapters_summary
            )
            
            if fallback_scenes:
                plan_data.get("event_system", {}).get("chapter_scene_events", []).append({
                    "chapter_number": chapter_num,
                    "scene_events": fallback_scenes
                })
                chapters_repaired_count += 1
                self.logger.info(f"    -> 第 {chapter_num} 章修复成功。")
            else:
                self.logger.error(f"    -> ❌ 第 {chapter_num} 章修复失败。")
        
        if chapters_repaired_count > 0:
            plan_data.get("event_system", {}).get("chapter_scene_events", []).sort(
                key=lambda x: x["chapter_number"]
            )
            self.logger.info(f"  🎉 成功修复了 {chapters_repaired_count} 个章节！")
            return repaired_plan, True
        
        return repaired_plan, False
    
    # ========================================================================
    # 辅助方法
    # ========================================================================
    
    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        """
        计算"起承转合"四阶段的边界
        
        优先从创意设定读取章节范围，失败时使用固定比例作为fallback
        这样实现动态章节划分，适应每本书的创意设定。
        """
        from src.managers.StageBoundaryParser import parse_stage_boundaries
        
        # 🔥 修复：确保 total_chapters 是整数
        total_chapters = int(total_chapters)
        
        # 获取创意设定
        creative_seed = self.generator.novel_data.get("creative_seed", {})
        
        # 使用统一的解析器
        boundaries = parse_stage_boundaries(creative_seed, total_chapters)
        
        # 记录使用的方式
        if creative_seed.get("completeStoryline"):
            self.logger.info("✅ 尝试从创意设定读取章节范围")
        else:
            self.logger.info("ℹ️ 创意设定中没有 completeStoryline，使用固定比例")
        
        return boundaries
    
    def print_stage_overview(self):
        """打印详细的阶段计划概览"""
        if not self.overall_stage_plans:
            self.logger.info("暂无阶段计划数据")
            return
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("                   小说阶段计划概览")
        self.logger.info("=" * 60)
        
        total_chapters = 0
        stage_plan_dict = self.overall_stage_plans.get("overall_stage_plan", {})
        stage_map = {
            "opening_stage": "起 (开局阶段)",
            "development_stage": "承 (发展阶段)",
            "climax_stage": "转 (高潮阶段)",
            "ending_stage": "合 (结局阶段)"
        }
        
        for i, (stage_key, stage_info) in enumerate(stage_plan_dict.items(), 1):
            stage_name = stage_map.get(stage_key, stage_key)
            chapter_range = stage_info.get('chapter_range', '1-1')
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            total_chapters += chapter_count
            
            self.logger.info(f"\n📚 阶段 {i}: {stage_name}")
            self.logger.info(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            self.logger.info(f"   🎯 目标: {stage_info.get('stage_goal', stage_info.get('core_tasks', '暂无'))}")
            self.logger.info(f"   ⚡ 关键发展: {stage_info.get('key_developments', stage_info.get('key_content', '暂无'))}")
            
            if stage_info.get('core_conflicts'):
                self.logger.info(f"   ⚔️ 核心冲突: {stage_info.get('core_conflicts')}")
        
        self.logger.info(f"\n📈 总计: {len(stage_plan_dict)}个阶段，{total_chapters}章")
        self.logger.info("=" * 60)
    
    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文"""
        context = self.writing_guidance_manager.get_chapter_writing_context(chapter_number)
        stage_name = self._get_current_stage(chapter_number)
        
        if not stage_name:
            return context
        
        stage_plan_data = self.get_stage_writing_plan_by_name(stage_name)
        if not stage_plan_data:
            return context
        
        event_system = stage_plan_data.get("stage_writing_plan", {}).get("event_system", {})
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        
        current_chapter_scenes = None
        for chapter_scene in chapter_scene_events:
            if chapter_scene.get("chapter_number") == chapter_number:
                current_chapter_scenes = chapter_scene.get("scene_events", [])
                break
        
        # 应用分层上下文压缩
        from src.utils.LayeredContextManager import LayeredContextManager
        context_manager = LayeredContextManager()
        
        compressed_stage_plan = context_manager.compress_context(
            stage_plan_data, chapter_number,
            self._get_stage_start_chapter(stage_name) if stage_name else 1,
            "plot"
        )
        
        context['scene_events'] = current_chapter_scenes
        context['stage_plan'] = compressed_stage_plan
        context['all_chapter_scenes'] = chapter_scene_events
        
        return context
    
    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        return self.writing_guidance_manager.generate_writing_guidance_prompt(chapter_number)
    
    def get_stage_plan_for_chapter(self, chapter_number: int) -> Dict:
        """为指定章节获取阶段计划"""
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            self.logger.warning(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
            return {}
        
        stage_plan_data = self.get_stage_writing_plan_by_name(current_stage)
        if not stage_plan_data:
            self.logger.warning(f"  ⚠️ 没有找到或加载 {current_stage} 的写作计划")
            return {}
        
        return stage_plan_data.get("stage_writing_plan", stage_plan_data)
    
    @staticmethod
    def is_chapter_in_range(chapter: int, range_str: str) -> bool:
        """静态方法：检查章节是否在范围内"""
        try:
            from src.managers.StagePlanUtils import parse_chapter_range
            cleaned_str = range_str.replace("章", "").replace("第", "").strip()
            if "-" in cleaned_str:
                parts = cleaned_str.split("-")
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    return start <= chapter <= end
            else:
                target_chapter = int(cleaned_str)
                return chapter == target_chapter
        except (ValueError, AttributeError, IndexError):
            logger = get_logger("StagePlanManager")
            logger.warning(f"⚠️ 解析章节范围失败: '{range_str}'，返回False")
            return False
        
        # 确保所有路径都有返回值
        return False
    
    # ========================================================================
    # 私有辅助方法
    # ========================================================================
    
    def _build_overall_stage_prompt(self, creative_seed: str, novel_title: str,
                                   novel_synopsis: str, total_chapters: int,
                                   boundaries: Dict, emotional_goals_str: str) -> str:
        """构建整体阶段计划的prompt"""
        return f"""
最高指令：以"情绪发展蓝图"和"创意种子"为绝对准则。
你的任务是设计一个服务于小说情绪发展的【剧情阶段规划】。

# 情感战略目标 (来自情绪蓝图)
{emotional_goals_str}

# 核心参考资料 
创意种子: {creative_seed}
小说标题: {novel_title}
小说简介: {novel_synopsis}
总章节数: {total_chapters}

# 阶段划分要求
请将全书{total_chapters}章，按照经典的"起、承、转、合"四阶段结构进行划分。

## 1. 起 (开局阶段，约前15%)
- **章节范围**: 第1章-第{boundaries['opening_end']}章
- **核心任务**: 快速建立故事基础，引入核心冲突
## 2. 承 (发展阶段，约35%)
- **章节范围**: 第{boundaries['development_start']}章-第{boundaries['development_end']}章
- **核心任务**: 深化并扩大矛盾
## 3. 转 (高潮阶段，约30%)
- **章节范围**: 第{boundaries['climax_start']}章-第{boundaries['climax_end']}章
- **核心任务**: 主要矛盾全面爆发
## 4. 合 (结局阶段，约20%)
- **章节范围**: 第{boundaries['ending_start']}章-第{total_chapters}章
- **核心任务**: 解决所有核心冲突
"""
    
    def _generate_major_event_skeletons_with_retry(self, stage_name: str, stage_range: str,
                                                 creative_seed: Dict, novel_title: str,
                                                 novel_synopsis: str, overall_stage_plan: Dict) -> List[Dict]:
        """生成重大事件骨架（带重试）"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = max(1, end_chap - start_chap + 1)
        
        # 生成阶段情绪计划
        emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
        stage_emotional_plan = self.emotional_manager.generate_stage_emotional_plan(
            stage_name, stage_range, emotional_blueprint
        )
        
        # 计算事件密度
        density_requirements = self.event_manager.calculate_optimal_event_density_by_stage(
            stage_name, stage_length
        )
        
        # 使用重大事件生成器
        for attempt in range(3):
            try:
                result = self.major_event_generator.generate_major_event_skeletons(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=creative_seed,
                    global_novel_data=self.generator.novel_data,
                    stage_emotional_plan=stage_emotional_plan,
                    overall_stage_plan=overall_stage_plan,
                    density_requirements=density_requirements,
                    novel_title=novel_title
                )
                
                if result:
                    return result
                else:
                    self.logger.warning(f"    ⚠️ 第{attempt+1}次生成主龙骨失败")
            except Exception as e:
                self.logger.error(f"    ❌ 第{attempt+1}次生成主龙骨出错: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
        
        return []
    
    def _decompose_major_events_to_medium_only(self, major_event_skeletons: List[Dict],
                                             stage_name: str, stage_range: str,
                                             creative_seed: Dict, novel_title: str,
                                             novel_synopsis: str, overall_stage_plan: Dict) -> List[Dict]:
        """分解重大事件为中型事件（第一阶段专用 - 不进行场景分解）"""
        self.logger.info("    [第一阶段] 只分解到中型事件，不进行场景分解...")
        fleshed_out_major_events = []
        
        # 获取情绪蓝图和阶段情绪弧线（从事件推导情绪，而不是预先规划）
        emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
        stage_emotional_arc = emotional_blueprint.get("stage_emotional_arcs", {}).get(stage_name)
        
        if stage_emotional_arc:
            self.logger.info(f"    💭 使用阶段情绪弧线指导: {stage_emotional_arc.get('start_emotion', '未定义')} → {stage_emotional_arc.get('end_emotion', '未定义')}")
        else:
            self.logger.warning(f"    ⚠️ 未找到 {stage_name} 的情绪弧线，将仅基于事件分解")
        
        # 🔥 新增：初始化情节状态管理器
        from src.managers.PlotStateManager import PlotStateManager
        plot_manager = PlotStateManager()
        plot_manager.register_plot_points_from_events(major_event_skeletons)
        self.logger.info(f"    📊 情节管理器已初始化，注册了 {len(plot_manager.tracked_plot_points)} 个核心情节跟踪点")
        
        for idx, skeleton in enumerate(major_event_skeletons):
            self.logger.info(f"    -> 正在解剖重大事件: '{skeleton['name']}' ({skeleton['chapter_range']})")
            
            # 🔥 新增：获取情节约束上下文
            plot_constraint_context = plot_manager.get_context_for_next_event(fleshed_out_major_events)
            if idx > 0:  # 只在非第一个事件时显示
                self.logger.info(f"       📋 情节约束：已完成 {len(plot_manager.event_state_chain)} 个前置事件")
            
            fleshed_out_event = None
            for attempt in range(3):
                try:
                    fleshed_out_event = self.event_decomposer.decompose_major_event(
                        major_event_skeleton=skeleton,
                        stage_name=stage_name,
                        stage_range=stage_range,
                        novel_title=novel_title,
                        novel_synopsis=novel_synopsis,
                        creative_seed=creative_seed,
                        overall_stage_plan=overall_stage_plan,
                        global_novel_data=self.generator.novel_data,
                        stage_emotional_arc=stage_emotional_arc,
                        overall_emotional_blueprint=emotional_blueprint,
                        plot_constraint_context=plot_constraint_context  # 🔥 新增参数
                    )
                    
                    if fleshed_out_event:
                        self.logger.info(f"      ✅ 成功分解为中型事件（第一阶段到此为止）")
                        break
                    else:
                        self.logger.warning(f"      ⚠️ 第{attempt+1}次解剖失败")
                except Exception as e:
                    self.logger.error(f"      ❌ 第{attempt+1}次解剖出错: {e}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
            
            if fleshed_out_event:
                # 🔥 新增：检查情节重复
                duplication_issues = plot_manager.check_plot_duplication(fleshed_out_event)
                if duplication_issues:
                    self.logger.warning(f"       ⚠️ 检测到情节重复问题：{duplication_issues}")
                else:
                    self.logger.info(f"       ✅ 情节唯一性检查通过")

                # 🔥 新增：标记事件完成，更新状态链
                event_state = plot_manager.mark_event_completed(fleshed_out_event, idx)
                self.logger.info(f"       📝 已记录事件状态：完成 {len(event_state.completed_plot_points)} 个情节点")
                
                # 验证并修正章节覆盖率
                fleshed_out_event = self.plan_validator.validate_and_correct_major_event_coverage(
                    skeleton, fleshed_out_event
                )
                
                fleshed_out_major_events.append(fleshed_out_event)
            else:
                self.logger.error(f"    🚨 重大事件 '{skeleton['name']}' 解剖失败")
        
        # 🔥 新增：输出情节状态摘要
        state_summary = plot_manager.get_state_summary()
        self.logger.info(f"    📊 情节状态摘要：")
        self.logger.info(f"       - 总计跟踪情节：{state_summary['total_tracked_plots']}")
        self.logger.info(f"       - 已完成情节：{state_summary['completed_plots']}")
        self.logger.info(f"       - 进行中情节：{state_summary['in_progress_plots']}")
        self.logger.info(f"       - 已处理事件：{state_summary['events_processed']}")
        
        self.logger.info(f"    ✅ 第一阶段事件分解完成：共{len(fleshed_out_major_events)}个重大事件")
        return fleshed_out_major_events

    def _decompose_major_event_to_medium_only(self, major_event: Dict) -> Dict:
        """
        只保留中型事件分解结果，移除场景分解
        
        Args:
            major_event: 已分解的重大事件
            
        Returns:
            只包含中型事件的重大事件
        """
        # 重大事件已经包含了中型事件的composition
        # 第一阶段只需要这个结构，不需要进一步的场景分解
        return major_event
    
    def _validate_and_optimize_events(self, fleshed_out_major_events: List[Dict],
                                     stage_name: str, stage_range: str,
                                     overall_stage_plan: Dict) -> tuple:
        """验证和优化事件系统"""
        # 构建临时计划结构
        temp_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "event_system": {
                    "major_events": fleshed_out_major_events,
                },
            }
        }
        
        # 验证目标层级一致性
        goal_coherence = self.plan_validator.validate_goal_hierarchy_coherence(
            temp_plan, stage_name, self.generator.api_client
        )
        
        # 验证连续性
        creative_seed = overall_stage_plan.get("creative_seed", "")
        novel_title = self.generator.novel_data.get("novel_title", "")
        novel_synopsis = self.generator.novel_data.get("novel_synopsis", "")
        
        continuity_assessment = self.assess_stage_event_continuity(
            temp_plan, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )

        # 🔥 新增：验证重大事件章节范围覆盖
        coverage_validation = self.plan_validator.validate_major_events_coverage(
            fleshed_out_major_events, stage_range, auto_correct=True
        )

        if not coverage_validation.get("is_valid"):
            self.logger.warning(f"  ⚠️ 重大事件覆盖验证发现问题，已自动修正")
            # 如果进行了自动修正，使用修正后的事件
            if "corrected_events" in coverage_validation:
                fleshed_out_major_events = coverage_validation["corrected_events"]
                temp_plan["stage_writing_plan"]["event_system"]["major_events"] = fleshed_out_major_events

        # 🔥 新增：验证每个重大事件内中型事件的章节范围一致性
        medium_events_valid = True
        for major_event in fleshed_out_major_events:
            medium_validation = self.plan_validator.validate_medium_events_range_consistency(
                major_event
            )
            if not medium_validation.get("is_valid"):
                medium_events_valid = False
                # 可以在这里添加自动修正逻辑

        if not medium_events_valid:
            self.logger.warning(f"  ⚠️ 部分重大事件的中型事件范围存在问题")

        # 根据验证结果优化
        try:
            coherence_score = float(goal_coherence.get("overall_coherence_score", 10))
        except (ValueError, TypeError):
            coherence_score = 10
        
        if coherence_score < 8.0:
            self.logger.warning(f"  ⚠️ 目标层级一致性评分较低 ({coherence_score:.1f})，进行优化...")
            temp_plan = self.event_optimizer.optimize_based_on_coherence_assessment(
                temp_plan, goal_coherence, stage_name, stage_range
            )
            fleshed_out_major_events = temp_plan["stage_writing_plan"]["event_system"]["major_events"]
        
        continuity_score = float(continuity_assessment.get("overall_continuity_score", 10))
        if continuity_score < 9.5:
            self.logger.warning(f"  ⚠️ 阶段事件连续性评分较低 ({continuity_score:.1f})，进行优化...")
            temp_plan = self.event_optimizer.optimize_based_on_continuity_assessment(
                temp_plan, continuity_assessment, stage_name, stage_range
            )
            fleshed_out_major_events = temp_plan["stage_writing_plan"]["event_system"]["major_events"]
        
        return goal_coherence, continuity_assessment
    
    def _validate_and_optimize_writing_plan(self, writing_plan: Dict,
                                          stage_name: str, stage_range: str) -> Dict:
        """验证和优化写作计划（第一阶段版 - 验证中型事件覆盖）"""
        self.logger.info(f"  🔍 [第一阶段] 对 {stage_name} 进行中型事件覆盖率验证...")
        
        if not writing_plan or "stage_writing_plan" not in writing_plan:
            self.logger.warning(f"  ⚠️ {stage_name} 写作计划为空或结构错误")
            return writing_plan
        
        event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        if not major_events:
            self.logger.warning(f"  ⚠️ {stage_name} 计划中不包含任何重大事件")
            return writing_plan
        
        try:
            stage_start, stage_end = parse_chapter_range(stage_range)
        except (ValueError, TypeError):
            self.logger.error(f"  ❌ 关键错误: 无法解析阶段章节范围 '{stage_range}'")
            return writing_plan
        
        # 提取所有中型事件和特殊情感事件的范围
        all_event_ranges = []
        for major_event in major_events:
            composition = major_event.get('composition', {})
            if composition:
                for phase_key, phase_events in composition.items():
                    if isinstance(phase_events, list):
                        for medium_event in phase_events:
                            if 'chapter_range' in medium_event:
                                try:
                                    start, end = parse_chapter_range(medium_event['chapter_range'])
                                    all_event_ranges.append((start, end))
                                except:
                                    pass
            
            special_events = major_event.get('special_emotional_events', [])
            if special_events:
                for special_event in special_events:
                    if 'chapter_range' in special_event:
                        try:
                            start, end = parse_chapter_range(special_event['chapter_range'])
                            all_event_ranges.append((start, end))
                        except:
                            pass
        
        if not all_event_ranges:
            self.logger.warning(f"  ⚠️ {stage_name} 计划中未找到任何有效的事件章节范围")
            return writing_plan
        
        # 检查中型事件的覆盖率
        total_chapters = stage_end - stage_start + 1
        coverage_map = [False] * total_chapters
        
        for start, end in all_event_ranges:
            for i in range(start, end + 1):
                if stage_start <= i <= stage_end:
                    coverage_map[i - stage_start] = True
        
        uncovered_chapters = [i + stage_start for i, covered in enumerate(coverage_map) if not covered]
        
        if not uncovered_chapters:
            self.logger.info(f"  ✅ 第一阶段中型事件覆盖率验证通过！")
        else:
            self.logger.warning(f"  ⚠️ 第一阶段存在未覆盖章节: {uncovered_chapters}")
            self.logger.info(f"     这些章节将在第二阶段通过进一步分解来覆盖")
        
        return writing_plan
    
    def _print_fractal_plan_summary(self, writing_plan: Dict):
        """打印分形设计写作计划的摘要（第一阶段版）"""
        plan = writing_plan.get("stage_writing_plan", {})
        event_system = plan.get("event_system", {})
        major_events = event_system.get("major_events", [])
        special_events = event_system.get("special_emotional_events", [])
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        
        hierarchy_assessment = plan.get("goal_hierarchy_assessment", {})
        coherence_score = hierarchy_assessment.get("overall_coherence_score", "未评估")
        
        self.logger.info("=" * 60)
        self.logger.info(f"📄 [第一阶段] 阶段计划摘要: {plan.get('stage_name')} ({plan.get('chapter_range')})")
        self.logger.info(f"🎯 目标层级一致性: {coherence_score}/10")
        
        # 统计中型事件
        total_medium_events = 0
        for major_event in major_events:
            composition = major_event.get('composition', {})
            total_medium_events += sum(len(v) for v in composition.values())
        
        self.logger.info(f"📊 第一阶段结构: {len(major_events)}个重大事件 → {total_medium_events}个中型事件 → {len(special_events)}个特殊情感事件")
        self.logger.info(f"   章节场景规划: {len(chapter_scene_events)}章 (将在第二阶段生成)")
        
        self.logger.info(f"\n🚨 主龙骨包含 {len(major_events)} 个重大事件:")
        for i, major_event in enumerate(major_events, 1):
            name = major_event.get('name')
            role = major_event.get('role_in_stage_arc')
            ch_range = major_event.get('chapter_range', 'N/A')
            composition = major_event.get('composition', {})
            sub_event_count = sum(len(v) for v in composition.values())
            self.logger.info(f"    {i}. 【{role}】{name} ({ch_range})")
            self.logger.info(f"       - 目标: {major_event.get('main_goal')}")
            self.logger.info(f"       - 分解为 {sub_event_count} 个中型事件")
        
        if special_events:
            self.logger.info(f"\n💫 特殊情感事件 ({len(special_events)}个):")
            for i, special in enumerate(special_events[:5], 1):  # 只显示前5个
                self.logger.info(f"    {i}. {special.get('name')} ({special.get('chapter_range', 'N/A')}) - {special.get('purpose', '')}")
            if len(special_events) > 5:
                self.logger.info(f"    ... 还有 {len(special_events) - 5} 个特殊情感事件")
        
        self.logger.info("=" * 60)
    
    def _get_current_stage(self, chapter_number: int) -> str:
        """获取当前章节所属的阶段名称"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        
        # 兼容两种数据结构：
        # 1. 新格式: {"overall_stage_plan": {"opening_stage": {...}, ...}}
        # 2. 旧格式: {"opening_stage": {...}, "development_stage": {...}, ...}
        if "overall_stage_plan" in overall_plans:
            stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        else:
            # 直接使用 overall_plans 作为 stage_plan_dict
            stage_plan_dict = overall_plans
        
        if not stage_plan_dict:
            self.logger.warning("  ⚠️ 没有可用的整体阶段计划")
            return ""
        
        for stage_name, stage_info in stage_plan_dict.items():
            chapter_range_str = stage_info.get("chapter_range", "")
            if is_chapter_in_range(chapter_number, chapter_range_str):
                return stage_name
        
        self.logger.warning(f"  ⚠️ 第{chapter_number}章不在任何已定义的阶段范围内")
        return ""
    
    def _get_stage_start_chapter(self, stage_name: str) -> int:
        """获取阶段起始章节"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        
        # 兼容两种数据结构
        if "overall_stage_plan" in overall_plans:
            stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        else:
            stage_plan_dict = overall_plans
        
        stage_info = stage_plan_dict.get(stage_name, {})
        
        if stage_info and "chapter_range" in stage_info:
            start, _ = parse_chapter_range(stage_info["chapter_range"])
            return start
        
        return 1
    
    def assess_stage_event_continuity(self, stage_writing_plan: Dict, stage_name: str,
                                    stage_range: str, creative_seed: str,
                                    novel_title: str, novel_synopsis: str) -> Dict:
        """评估阶段事件连续性 - 调用PlanValidator进行AI评估"""
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段事件连续性...")
        
        # 使用PlanValidator进行评估
        assessment = self.plan_validator.validate_event_continuity(
            stage_writing_plan, stage_name, stage_range,
            creative_seed, novel_title, novel_synopsis, self.generator.api_client
        )
        
        if assessment:
            self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段事件连续性完成。")
            return assessment
        else:
            self.logger.warning(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段事件连续性失败，使用默认结果。")
            return self._create_default_continuity_assessment()
    
    def _create_default_continuity_assessment(self) -> Dict:
        """创建默认的连续性评估结果"""
        return {
            "overall_continuity_score": 10.0,
            "logic_coherence_score": 10.0,
            "narrative_rhythm_score": 10.0,
            "critical_issues": [],
            "improvement_recommendations": [],
            "master_reviewer_verdict": "评估系统暂时不可用，使用满分默认值"
        }
    
    def _generate_simple_stage_plan_for_test(self, stage_name: str, stage_range: str,
                                           overall_stage_plan: Dict) -> Dict:
        """在测试模式下返回简化版阶段写作计划"""
        start, end = parse_chapter_range(stage_range)
        stage_info = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {})
        stage_goal = stage_info.get("stage_arc_goal", f"{stage_name} stage goal")
        
        return {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": stage_goal,
                "event_system": {
                    "major_events": [
                        {
                            "name": f"{stage_name} - Major Event 1",
                            "chapter_range": f"{start}-{start + (end-start)//2}",
                            "main_goal": "推进主情节",
                            "composition": {
                                "起": [{
                                    "name": "Scene 1",
                                    "chapter_range": f"{start}-{start + (end-start)//4}",
                                    "main_goal": "引入事件"
                                }]
                            }
                        }
                    ]
                },
                "summary": f"Simplified test plan for {stage_name}"
            }
        }
    
    def _generate_supplementary_characters_for_stage(self, stage_name: str, stage_range: str,
                                                     writing_plan: Dict, creative_seed: Dict,
                                                     novel_title: str, novel_synopsis: str,
                                                     overall_stage_plan: Dict) -> Dict:
        """
        为阶段生成补充角色
        
        Args:
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            writing_plan: 写作计划
            creative_seed: 创意种子
            novel_title: 小说标题
            novel_synopsis: 小说简介
            overall_stage_plan: 整体阶段计划
            
        Returns:
            更新后的写作计划（包含补充角色）
        """
        self.logger.info(f"    -> 开始为【{stage_name}】生成补充角色...")
        
        # 获取已有角色
        existing_characters = self.generator.novel_data.get("character_design", {})
        if not existing_characters or not existing_characters.get("main_character"):
            self.logger.warning("    ⚠️ 尚未生成主角，跳过补充角色生成")
            return writing_plan
        
        # 获取势力系统信息
        faction_system = self.generator.novel_data.get("faction_system", {})
        
        # 准备阶段信息
        stage_info = {
            "stage_name": stage_name,
            "stage_range": stage_range,
            "stage_overview": writing_plan.get("stage_writing_plan", {}).get("stage_overview", ""),
            "stage_writing_plan": writing_plan.get("stage_writing_plan", {})
        }
        
        try:
            # 调用 ContentGenerator 生成补充角色
            updated_characters = self.generator.content_generator.generate_character_design(
                novel_title=novel_title,
                core_worldview=self.generator.novel_data.get("core_worldview", {}),
                selected_plan=self.generator.novel_data.get("selected_plan", {}),
                market_analysis=self.generator.novel_data.get("market_analysis", {}),
                design_level="supplementary",
                existing_characters=existing_characters,
                stage_info=stage_info,
                global_growth_plan=self.generator.novel_data.get("global_growth_plan", {}),
                overall_stage_plans=overall_stage_plan,
                faction_system=faction_system
            )
            
            if updated_characters and updated_characters != existing_characters:
                # 更新 novel_data 中的角色设计
                self.generator.novel_data["character_design"] = updated_characters
                
                # 在写作计划中记录生成的角色
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan
                
                new_characters_count = len(updated_characters.get("important_characters", [])) - \
                                      len(existing_characters.get("important_characters", []))
                
                plan_container["supplementary_characters_generated"] = new_characters_count
                plan_container["supplementary_characters_note"] = \
                    f"为 {stage_name} 阶段生成了 {new_characters_count} 个补充角色"
                
                self.logger.info(f"    ✅ 成功为【{stage_name}】生成 {new_characters_count} 个补充角色")
            else:
                self.logger.info(f"    ℹ️ 【{stage_name}】无需生成额外补充角色")
                
        except Exception as e:
            self.logger.error(f"    ❌ 为【{stage_name}】生成补充角色时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return writing_plan
    
    def _generate_expectation_mapping(self, writing_plan: Dict, stage_name: str) -> Dict:
        """
        为写作计划生成期待感映射（使用AI智能分析）
        
        Args:
            writing_plan: 写作计划
            stage_name: 阶段名称
            
        Returns:
            包含期待感映射的写作计划
        """
        try:
            from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator
            import re
            import json
            from pathlib import Path
            
            self.logger.info(f"    -> 开始为【{stage_name}】生成期待感映射（AI智能分析）...")
            
            # 初始化期待感管理器
            expectation_manager = ExpectationManager()
            expectation_integrator = ExpectationIntegrator(expectation_manager)
            
            # 获取写作计划容器
            if "stage_writing_plan" in writing_plan:
                plan_container = writing_plan["stage_writing_plan"]
            else:
                plan_container = writing_plan
            
            # 获取重大事件
            event_system = plan_container.get("event_system", {})
            major_events = event_system.get("major_events", [])
            
            if not major_events:
                self.logger.info(f"    ℹ️ 【{stage_name}】没有重大事件，跳过期待感映射生成")
                return writing_plan
            
            # 🤖 使用AI分析事件并添加期待感标签
            self.logger.info(f"    🤖 AI正在分析【{stage_name}】的 {len(major_events)} 个重大事件...")
            analysis_result = expectation_integrator.analyze_and_tag_events(
                major_events=major_events,
                stage_name=stage_name,
                api_client=self.generator.api_client,
                novel_title=self.generator.novel_data.get("novel_title", "")
            )
            
            total_tagged = analysis_result.get("tagged_count", 0)
            self.logger.info(f"    ✅ AI成功为【{stage_name}】的 {total_tagged} 个事件生成期待感标签")
            
            # 生成期待感映射
            expectation_map = expectation_manager.export_expectation_map()
            
            # 将期待感映射添加到写作计划中
            plan_container["expectation_map"] = expectation_map
            
            # 保存期待感映射到项目目录（以便API可以加载）
            try:
                novel_title = self.generator.novel_data.get("novel_title", "")
                if novel_title:
                    # 清理文件名（添加冒号到不允许的字符列表中）
                    safe_title = re.sub(r'[\\/*?"<>|:]', "_", novel_title)
                    
                    # 🔥 使用用户隔离路径（从 generator 获取用户名）
                    try:
                        from web.utils.path_utils import get_user_novel_dir
                        username = getattr(self.generator, '_username', None)
                        user_dir = get_user_novel_dir(username=username, create=True)
                        project_dir = user_dir / novel_title
                    except Exception as e:
                        # 如果失败，使用默认路径
                        self.logger.warning(f"获取用户隔离路径失败: {e}，使用默认路径")
                        project_dir = Path("小说项目") / novel_title
                    
                    if not project_dir.exists():
                        project_dir = Path("小说项目") / safe_title
                    
                    # 确保目录存在
                    project_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 保存期待感映射文件
                    expectation_map_file = project_dir / "expectation_map.json"
                    with open(expectation_map_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'novel_title': novel_title,
                            'stage_name': stage_name,
                            'expectation_map': expectation_map,
                            'generated_at': datetime.now().isoformat(),
                            'total_tagged': total_tagged
                        }, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"      ✅ 期待感映射已保存: {expectation_map_file}")
            except Exception as save_error:
                self.logger.warning(f"      ⚠️ 保存期待感映射文件失败: {save_error}")
            
            self.logger.info(f"    ✅ 成功为【{stage_name}】的 {total_tagged} 个事件生成期待感标签")
            
            return writing_plan
            
        except Exception as e:
            self.logger.error(f"    ❌ 为【{stage_name}】生成期待感映射时出错: {e}")
            import traceback
            traceback.print_exc()
            return writing_plan
    
    def _generate_scenes_for_single_chapter_event(self, event_data: Dict, chapter_num: int,
                                                   stage_name: str, major_event_name: str,
                                                   novel_title: str, novel_synopsis: str,
                                                   consistency_guidance: Optional[str] = None) -> List[Dict]:
        """
        为单章节事件生成场景（桥接方法）

        这是 ContentGenerator 调用的桥接方法，委托给 EventDecomposer 处理

        Args:
            event_data: 事件数据（中型事件）
            chapter_num: 章节号
            stage_name: 阶段名称
            major_event_name: 重大事件名称
            novel_title: 小说标题
            novel_synopsis: 小说简介
            consistency_guidance: 一致性指导

        Returns:
            生成的场景列表
        """
        self.logger.info(f"  🎬 [桥接] 为单章事件 '{event_data.get('name')}' 生成场景...")

        # 获取必要的上下文
        creative_seed = self.generator.novel_data.get("creative_seed", {})
        overall_stage_plan = self.generator.novel_data.get("overall_stage_plans", {})
        global_novel_data = self.generator.novel_data

        # 🔥 新增：获取前几章已完成场景信息（用于避免重复）
        previous_chapters_scenes = self._get_previous_chapters_scenes_for_event(
            chapter_num, event_data, stage_name, global_novel_data
        )

        if previous_chapters_scenes:
            self.logger.info(f"  📜 [场景连续性] 已获取前几章场景概要，共 {len(previous_chapters_scenes.get('previous_chapters', []))} 章")

        # 构建临时重大事件结构（EventDecomposer 需要这个参数）
        temp_major_event = {
            "name": major_event_name,
            "chapter_range": event_data.get("chapter_range", f"{chapter_num}-{chapter_num}")
        }

        try:
            # 调用 EventDecomposer 的单章场景生成方法，传递前几章场景
            result = self.event_decomposer._decompose_single_chapter_with_complete_arc(
                medium_event=event_data,
                major_event=temp_major_event,
                stage_name=stage_name,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                creative_seed=creative_seed,
                overall_stage_plan=overall_stage_plan,
                global_novel_data=global_novel_data,
                consistency_guidance=consistency_guidance,
                previous_chapters_scenes=previous_chapters_scenes  # 🔥 传递前几章场景
            )
            
            if result and "scene_sequences" in result:
                scene_sequences = result["scene_sequences"]
                if scene_sequences and len(scene_sequences) > 0:
                    # 提取场景事件
                    scene_events = scene_sequences[0].get("scene_events", [])
                    self.logger.info(f"  ✅ 成功生成 {len(scene_events)} 个场景")
                    return scene_events
            
            self.logger.warning(f"  ⚠️ 场景生成未返回有效结果")
            return []
            
        except Exception as e:
            self.logger.error(f"  ❌ 生成场景时出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _get_previous_chapters_scenes_for_event(self, chapter_num: int, event_data: Dict,
                                               stage_name: str, global_novel_data: Dict) -> Optional[Dict]:
        """
        获取指定中型事件的前几章已完成场景信息（用于避免重复）

        这是方案3的核心实现：在生成新章节场景时，先检查该中型事件是否在之前的章节
        已经生成过场景，如果是，则将这些场景信息传递给场景生成器，确保不会重复。

        Args:
            chapter_num: 当前章节号
            event_data: 中型事件数据
            stage_name: 阶段名称
            global_novel_data: 全局小说数据

        Returns:
            包含前几章场景信息的字典，格式：
            {
                "previous_chapters": [1],  # 已生成场景的章节号列表
                "all_previous_scenes": [...],  # 所有之前章节的场景
                "scenes_by_chapter": {"1": [...]},  # 按章节分组的场景
                "event_summary": "事件摘要",
                "event_name": "事件名称",
                "chapter_range": "章节范围"
            }
            如果没有前几章场景，返回None
        """
        # 🔥 只在前3章启用场景连续性检查（这是用户明确要求的）
        if chapter_num > 3:
            self.logger.debug(f"  跳过场景连续性检查：第{chapter_num}章超过前3章范围")
            return None

        # 生成事件ID
        event_id = self.medium_event_scene_manager.get_event_id(event_data, stage_name)

        # 从缓存获取前几章的场景
        cached_scenes = self.medium_event_scene_manager.get_cached_scenes(event_id, chapter_num)

        if not cached_scenes:
            self.logger.debug(f"  未找到事件 '{event_data.get('name')}' 的前几章场景缓存")
            return None

        self.logger.info(f"  ✅ [场景连续性] 找到事件 '{event_data.get('name')}' 的前几章场景："
                        f"第{cached_scenes.get('previous_chapters', [])}章")

        return cached_scenes

    def save_and_cache_stage_plan(self, stage_name: str, plan_data: Dict):
        """
        保存并缓存阶段计划
        
        Args:
            stage_name: 阶段名称
            plan_data: 计划数据
        """
        # 保存到文件
        file_path = self.plan_persistence.save_plan_to_file(stage_name, plan_data)
        
        # 更新缓存
        cache_key = f"{stage_name}_writing_plan"
        self.stage_writing_plans_cache[cache_key] = plan_data
        
        # 更新 novel_data
        if "stage_writing_plans" not in self.generator.novel_data:
            self.generator.novel_data["stage_writing_plans"] = {}
        
        if file_path:
            try:
                project_path = getattr(self.generator, 'project_path', Path.cwd())
                relative_path = file_path.relative_to(project_path)
            except (AttributeError, ValueError):
                relative_path = file_path
        else:
            relative_path = f"plans/{stage_name}_writing_plan.json"
        
        self.generator.novel_data["stage_writing_plans"][stage_name] = {"path": str(relative_path)}
        
        self.logger.info(f"  ✅ 阶段计划已保存并缓存: {stage_name}")