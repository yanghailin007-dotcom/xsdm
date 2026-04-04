"""
会话编排器 - 负责按顺序执行各域会话、传递 Context Brief、保存检查点、映射进度
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
from src.utils.logger import get_logger


class SessionOrchestrator:
    """
    小说生成会话编排器
    
    职责：
    1. 按顺序启动 Foundation -> Character -> Structure -> StageWriting 会话
    2. 在上游会话完成后提取 Context Brief，传递给下游会话
    3. 每个会话完成后保存坚固检查点（包含 context_briefs）
    4. 将内部会话进度实时映射到现有的 15 步骤体系
    5. 支持从检查点恢复，包括恢复 context_briefs
    """

    # 一阶段 15 步骤的进度映射（与现有系统保持一致）
    STEP_PROGRESS_MAP = {
        'creative_refinement': 5,
        'fanfiction_detection': 10,
        'multiple_plans': 15,
        'plan_selection': 30,
        'foundation_planning': 35,   # Session A 完成点
        'worldview_with_factions': 40,
        'character_design': 45,      # Session B 中点
        'emotional_growth_planning': 55,
        'stage_plan': 62,            # Session C 起点
        'detailed_stage_plans': 72,
        'supplementary_characters': 78,
        'expectation_mapping': 82,
        'system_init': 88,
        'saving': 92,
        'quality_assessment': 100,
    }

    # 会话域 -> 负责的标准步骤映射
    DOMAIN_STEPS = {
        'creative_planning': ['creative_planning'],
        'foundation': ['foundation_planning'],
        'character': ['character_design', 'emotional_growth_planning'],
        'structure': ['stage_plan', 'detailed_stage_plans', 'supplementary_characters', 
                      'expectation_mapping', 'system_init'],
    }

    def __init__(self, novel_generator):
        """
        Args:
            novel_generator: NovelGenerator 实例，用于访问 api_client、novel_data、回调等
        """
        self.generator = novel_generator
        self.logger = get_logger("SessionOrchestrator")
        
        # 会话过程中累积的 context_briefs
        self.context_briefs: Dict[str, str] = {}
        
        # 进度回调封装
        self._progress_callback: Optional[Callable] = None
        self._step_status_callback: Optional[Callable] = None
        self._notify_failure_callback: Optional[Callable] = None
        
        # 检查点管理器（延迟初始化，需要 novel_title）
        self._checkpoint_mgr: Optional[GenerationCheckpoint] = None

    # ------------------------------------------------------------------
    # 初始化与辅助
    # ------------------------------------------------------------------
    def _init_checkpoint_manager(self) -> Optional[GenerationCheckpoint]:
        """初始化检查点管理器"""
        if self._checkpoint_mgr is not None:
            return self._checkpoint_mgr
        
        title = self.generator.novel_data.get("novel_title") or self.generator.novel_data.get("title")
        if not title:
            self.logger.warning("无法初始化检查点管理器：缺少 novel_title")
            return None
        
        username = getattr(self.generator, '_username', None)
        self._checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
        return self._checkpoint_mgr

    def _get_api_client(self):
        """获取 API 客户端"""
        return getattr(self.generator, 'api_client', None)

    def _get_provider_and_model(self) -> tuple:
        """获取当前 provider 和 model 名称"""
        api_client = self._get_api_client()
        if not api_client:
            return "kimi", None
        
        provider = getattr(api_client, 'default_provider', 'kimi')
        model_name = api_client.config.get('models', {}).get(provider) if hasattr(api_client, 'config') else None
        return provider, model_name

    def _check_stop_requested(self, context: str = ""):
        """检查用户是否请求停止"""
        if hasattr(self.generator, '_stop_check_callback'):
            try:
                self.generator._stop_check_callback()
            except InterruptedError:
                self.logger.info(f"🛑 编排器生成被用户停止{' - ' + context if context else ''}")
                raise

    # ------------------------------------------------------------------
    # 进度与状态回调
    # ------------------------------------------------------------------
    def set_callbacks(
        self,
        progress_callback: Optional[Callable] = None,
        step_status_callback: Optional[Callable] = None,
        notify_failure_callback: Optional[Callable] = None,
    ):
        """设置进度回调"""
        self._progress_callback = progress_callback
        self._step_status_callback = step_status_callback
        self._notify_failure_callback = notify_failure_callback

    def _update_progress(self, step_name: str, progress: int, message: str, step_status: Optional[Dict] = None):
        """更新进度（映射到 15 步骤体系）"""
        self._check_stop_requested(f"步骤 {step_name}")
        
        try:
            if self._progress_callback:
                self._progress_callback(step_name, progress, message, step_status)
        except Exception as e:
            self.logger.debug(f"进度回调失败: {e}")

    def _update_step_status(self, step_name: str, status: str, progress: int = None):
        """更新单个步骤状态"""
        self._check_stop_requested(f"步骤状态 {step_name}")
        
        try:
            if self._step_status_callback:
                self._step_status_callback(step_name, status, progress)
        except Exception as e:
            self.logger.debug(f"步骤状态回调失败: {e}")

    def _notify_failure(self, error_msg: str):
        """通知失败"""
        self.logger.error(f"❌ {error_msg}")
        if self._notify_failure_callback:
            try:
                self._notify_failure_callback(error_msg)
            except Exception as e:
                self.logger.debug(f"失败通知回调失败: {e}")

    # ------------------------------------------------------------------
    # 检查点操作
    # ------------------------------------------------------------------
    def _save_session_checkpoint(
        self,
        phase: str,
        step: str,
        step_status: str,
        extra_data: Optional[Dict] = None,
    ) -> bool:
        """保存坚固检查点，包含 context_briefs"""
        checkpoint_mgr = self._init_checkpoint_manager()
        if not checkpoint_mgr:
            return False
        
        data = {
            'progress': self.STEP_PROGRESS_MAP.get(step, 0),
            'step_status': {step: step_status},
            'context_briefs': self.context_briefs,
            'timestamp': datetime.now().isoformat(),
        }
        
        if extra_data:
            data.update(extra_data)
        
        # 保存 novel_data 快照（用于恢复）
        try:
            data['novel_data_snapshot'] = self._prepare_novel_data_snapshot()
        except Exception as e:
            self.logger.warning(f"准备 novel_data 快照失败: {e}")
        
        try:
            checkpoint_mgr.create_checkpoint(
                phase=phase,
                step=step,
                data=data,
                step_status=step_status,
            )
            self.logger.info(f"✅ 检查点已保存: {step} ({step_status})")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存检查点失败: {e}")
            return False

    def _prepare_novel_data_snapshot(self) -> Dict:
        """准备可序列化的 novel_data 快照"""
        import copy
        snapshot = copy.deepcopy(self.generator.novel_data)
        
        # 处理不可序列化的对象（如 set）
        if 'used_chapter_titles' in snapshot and isinstance(snapshot['used_chapter_titles'], set):
            snapshot['used_chapter_titles'] = list(snapshot['used_chapter_titles'])
        
        return snapshot

    def load_from_checkpoint(self, checkpoint_data: Dict) -> bool:
        """从检查点恢复 context_briefs 和 novel_data"""
        try:
            data = checkpoint_data.get('data', {})
            loaded_briefs = data.get('context_briefs', {})
            if loaded_briefs:
                self.context_briefs = loaded_briefs
                self.logger.info(f"✅ 从检查点恢复 {len(loaded_briefs)} 个 Context Briefs")
            
            snapshot = data.get('novel_data_snapshot')
            if snapshot and isinstance(snapshot, dict):
                self.generator.novel_data.update(snapshot)
                self.logger.info("✅ 从检查点恢复 novel_data 快照")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ 从检查点恢复失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 一阶段执行
    # ------------------------------------------------------------------
    def run_phase_one(self) -> bool:
        """
        执行一阶段全部分域会话
        
        顺序: FoundationSession -> CharacterSession -> StructureSession
        """
        self.logger.info("=" * 60)
        self.logger.info("🚀 启动分域会话模式（一阶段）")
        self.logger.info("=" * 60)
        
        provider, model_name = self._get_provider_and_model()
        api_client = self._get_api_client()
        
        if not api_client:
            self._notify_failure("API 客户端不可用")
            return False
        
        # 尝试从检查点恢复
        resume_state = self._try_load_checkpoint()
        
        # 标记前置步骤已完成
        pre_steps = ['creative_refinement', 'fanfiction_detection', 'multiple_plans', 'plan_selection']
        for step in pre_steps:
            self._update_step_status(step, 'completed', self.STEP_PROGRESS_MAP.get(step, 0))
        
        try:
            # 🔥 如果已经有交互式策划产出的 final_plan_brief，直接跳过 CreativePlanningSession
            existing_plan_brief = self.generator.novel_data.get('final_plan_brief')
            if existing_plan_brief:
                self.logger.info("[CreativePlanningSession] 检测到已有 final_plan_brief，跳过创意策划")
                self._update_progress('creative_planning', 31, "创意策划已完成（交互式）")
                self._update_step_status('creative_planning', 'completed', 31)
                if 'creative_planning_brief' not in self.context_briefs:
                    # 尝试从 final_plan_brief 重建 brief
                    try:
                        from src.prompts.Prompts import Prompts
                        prompts = Prompts()
                        template = prompts.get("creative_planning_brief_generation", "")
                        if template:
                            import json
                            brief = template.format(
                                final_plan_json=json.dumps(existing_plan_brief, ensure_ascii=False, indent=2)
                            )
                            self.context_briefs['creative_planning'] = brief
                    except Exception as e:
                        self.logger.warning(f"重建 creative_planning brief 失败: {e}")
            else:
                # ---------- Session 0: Creative Planning ----------
                if resume_state in ['creative_planning_done', 'foundation_done', 'character_done', 'structure_done', 'all_done']:
                    self.logger.info("[CreativePlanningSession] 检查点显示已完成，跳过")
                    self._update_step_status('creative_planning', 'completed', 31)
                else:
                    self._update_progress('creative_planning', 30, "正在执行创意策划会话...")
                    self._update_step_status('creative_planning', 'active', 30)
                    
                    planning_success = self._run_creative_planning_session(api_client, provider, model_name)
                    if not planning_success:
                        self._notify_failure("创意策划会话失败")
                        return False
                    self._update_step_status('creative_planning', 'completed', 31)
                    self._save_session_checkpoint('phase_one', 'creative_planning', 'completed')
            
            # ---------- Session A: Foundation ----------
            if resume_state in ['foundation_done', 'character_done', 'structure_done', 'all_done']:
                self.logger.info("[FoundationSession] 检查点显示已完成，跳过")
                self._update_progress('foundation_planning', 38, "创作基线会话已从检查点恢复")
                self._update_step_status('foundation_planning', 'completed', 38)
            else:
                self._update_progress('foundation_planning', 32, "正在执行创作基线会话...")
                self._update_step_status('foundation_planning', 'active', 32)
                
                foundation_success = self._run_foundation_session(api_client, provider, model_name)
                if not foundation_success:
                    self._notify_failure("创作基线会话 (Foundation) 失败")
                    return False
            
            # ---------- Session B: Character ----------
            if resume_state in ['character_done', 'structure_done', 'all_done']:
                self.logger.info("[CharacterSession] 检查点显示已完成，跳过")
                self._update_progress('character_design', 58, "角色与叙事会话已从检查点恢复")
                self._update_step_status('character_design', 'completed', 46)
                self._update_step_status('emotional_growth_planning', 'completed', 58)
            else:
                self._update_progress('character_design', 42, "正在执行角色与叙事会话...")
                self._update_step_status('character_design', 'active', 42)
                
                character_success = self._run_character_session(api_client, provider, model_name)
                if not character_success:
                    self._notify_failure("角色与叙事会话 (Character) 失败")
                    return False
            
            # ---------- Session C: Structure ----------
            if resume_state in ['structure_done', 'all_done']:
                self.logger.info("[StructureSession] 检查点显示已完成，跳过")
                for step in self.DOMAIN_STEPS['structure']:
                    self._update_step_status(step, 'completed', self.STEP_PROGRESS_MAP.get(step, 80))
            else:
                self._update_progress('stage_plan', 62, "正在执行结构规划会话...")
                self._update_step_status('stage_plan', 'active', 62)
                
                structure_success = self._run_structure_session(api_client, provider, model_name)
                if not structure_success:
                    self._notify_failure("结构规划会话 (Structure) 失败")
                    return False
            
            # ---------- 保存与评估 ----------
            if resume_state == 'all_done':
                self.logger.info("一阶段已从检查点完整恢复，跳过保存与评估")
            else:
                self._update_progress('saving', 92, "正在保存一阶段结果...")
                self._update_step_status('saving', 'active', 92)
                self._save_phase_one_result()
                self._update_step_status('saving', 'completed', 95)
                self._save_session_checkpoint('phase_one', 'saving', 'completed')
                
                # 质量评估（保持与现有系统一致）
                self._update_progress('quality_assessment', 98, "正在进行质量评估...")
                self._update_step_status('quality_assessment', 'active', 98)
                self._run_phase_one_quality_assessment()
                self._update_step_status('quality_assessment', 'completed', 100)
                self._save_session_checkpoint('phase_one', 'quality_assessment', 'completed')
            
            # 最终完成状态
            final_status = {step: 'completed' for step in self.STEP_PROGRESS_MAP.keys()}
            final_status['completed'] = 'completed'
            self._update_progress('completed', 100, "一阶段设定生成完成（分域会话模式）", final_status)
            
            self.logger.info("=" * 60)
            self.logger.info("🎉 一阶段分域会话模式执行完成")
            self.logger.info("=" * 60)
            return True
            
        except InterruptedError:
            self.logger.info("🛑 一阶段生成被用户中断")
            raise
        except Exception as e:
            self._notify_failure(f"一阶段分域会话发生异常: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _try_load_checkpoint(self) -> str:
        """
        尝试加载检查点并判断恢复状态
        
        Returns:
            'none' | 'creative_planning_done' | 'foundation_done' | 'character_done' | 'structure_done' | 'all_done'
        """
        try:
            title = self.generator.novel_data.get('novel_title') or self.generator.novel_data.get('title')
            username = getattr(self.generator, '_username', None)
            if not title:
                return 'none'
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            checkpoint = checkpoint_mgr.load_checkpoint()
            if not checkpoint:
                return 'none'
            
            current_step = checkpoint.get('current_step', '')
            step_status = checkpoint.get('step_status', 'unknown')
            
            # 加载数据
            self.load_from_checkpoint(checkpoint)
            
            # 判断恢复状态
            if current_step in ['quality_assessment', 'saving'] and step_status == 'completed':
                self.logger.info(f"检查点恢复: 一阶段已完成 ({current_step})")
                return 'all_done'
            elif current_step in ['system_init', 'expectation_mapping', 'supplementary_characters', 
                                   'detailed_stage_plans', 'stage_plan'] and step_status == 'completed':
                self.logger.info(f"检查点恢复: StructureSession 已完成 ({current_step})")
                return 'structure_done'
            elif current_step == 'emotional_growth_planning' and step_status == 'completed':
                self.logger.info(f"检查点恢复: CharacterSession 已完成 ({current_step})")
                return 'character_done'
            elif current_step == 'foundation_planning' and step_status == 'completed':
                self.logger.info(f"检查点恢复: FoundationSession 已完成 ({current_step})")
                return 'foundation_done'
            elif current_step == 'creative_planning' and step_status == 'completed':
                self.logger.info(f"检查点恢复: CreativePlanningSession 已完成 ({current_step})")
                return 'creative_planning_done'
            else:
                self.logger.info(f"检查点恢复: 从 {current_step} ({step_status}) 继续")
                return 'none'
                
        except Exception as e:
            self.logger.warning(f"检查点加载失败: {e}")
            return 'none'

    # ------------------------------------------------------------------
    # 各域会话实现
    # ------------------------------------------------------------------
    def _run_creative_planning_session(self, api_client, provider, model_name) -> bool:
        """执行创意策划会话：从原始创意到爆款方案"""
        from src.core.session_mode.sessions.creative_planning_session import (
            CreativePlanningSession,
            PlanningMode,
        )
        
        # 从 NovelGenerator 配置读取用户选择的模式
        mode = PlanningMode.AUTO
        max_iterations = 3
        try:
            generator_config = getattr(self.generator, 'config', {})
            if isinstance(generator_config, dict):
                mode_str = generator_config.get('creative_planning_mode', 'auto')
                if mode_str == 'interactive':
                    mode = PlanningMode.INTERACTIVE
                max_iterations = generator_config.get('creative_planning_auto_iterations', 3)
        except Exception:
            pass
        
        # 如果用户选择了 interactive 模式但没有交互会话状态，
        # 说明方案策划将在前端交互页面完成，Orchestrator 无需在后台执行自动流程
        if mode == PlanningMode.INTERACTIVE:
            if not self.generator.novel_data.get('creative_planning_session_state'):
                self.logger.info(
                    "[CreativePlanningSession] 用户选择了对话模式，"
                    "将前往交互页面完成方案策划，Orchestrator 跳过自动步骤"
                )
                self._update_step_status('creative_planning', 'completed', 31)
                return True
        
        session = CreativePlanningSession(
            api_client=api_client,
            mode=mode,
            max_auto_iterations=max_iterations,
            context_briefs=[],
            novel_data=self.generator.novel_data,
            provider=provider,
            model_name=model_name,
        )
        
        self.logger.info(f"[CreativePlanningSession] 开始执行，模式: {mode.value}...")
        success = session.execute_all_steps()
        
        if success:
            results = session.export_results()
            # 将 final_plan_brief 注入 novel_data，供下游所有 session 使用
            final_plan_brief = results.get('final_plan_brief', {})
            if final_plan_brief:
                self.generator.novel_data['final_plan_brief'] = final_plan_brief
                self.generator.novel_data['creative_planning_results'] = results
                self.logger.info(
                    f"[CreativePlanningSession] 完成，爆款对齐评分: "
                    f"{final_plan_brief.get('market_alignment', {}).get('score', 'N/A')}"
                )
            
            # 生成并保存 Context Brief
            brief = session.generate_brief(results)
            if brief:
                self.context_briefs['creative_planning'] = brief
            
            self.logger.info("[CreativePlanningSession] 完成")
            return True
        
        return False

    def _run_foundation_session(self, api_client, provider, model_name) -> bool:
        """执行创作基线会话：写作风格 + 市场分析 + 世界观 + 势力系统"""
        from src.core.session_mode.sessions.foundation_session import FoundationSession
        
        # 收集 context briefs：创意策划 brief + 同人背景资料 brief
        briefs = []
        cp_brief = self.context_briefs.get("creative_planning", "")
        if cp_brief:
            briefs.append(cp_brief)
        fanfiction_brief = self.generator.novel_data.get("fanfiction_brief", "")
        if fanfiction_brief:
            briefs.append(fanfiction_brief)
        
        session = FoundationSession(
            api_client=api_client,
            domain="foundation",
            context_briefs=briefs,
            novel_data=self.generator.novel_data,
            provider=provider,
            model_name=model_name,
        )
        
        self.logger.info("[FoundationSession] 开始执行...")
        success = session.execute_all_steps()
        
        if success:
            # 导出结果到 novel_data
            results = session.export_results()
            self.generator.novel_data.update(results)
            
            # 🔥 同步到现有系统：保存写作风格指南到文件
            try:
                writing_style = results.get('writing_style_guide', {})
                if writing_style and hasattr(self.generator, '_save_writing_style_to_file'):
                    self.generator._save_writing_style_to_file(writing_style)
                    self.logger.info("✅ 写作风格指南已保存到文件")
            except Exception as e:
                self.logger.warning(f"⚠️ 保存写作风格指南失败: {e}")
            
            # 🔥 同步到现有系统：保存市场分析到材料管理器
            try:
                market_analysis = results.get('market_analysis', {})
                if market_analysis and hasattr(self.generator, '_save_material_to_manager'):
                    creative_seed = self.generator.novel_data.get('creative_seed', {})
                    self.generator._save_material_to_manager("市场分析", market_analysis, creative_seed=creative_seed)
                    self.logger.info("✅ 市场分析已保存到材料管理器")
            except Exception as e:
                self.logger.warning(f"⚠️ 保存市场分析失败: {e}")
            
            # 生成并保存 Context Brief
            brief = session.generate_brief(results)
            if brief:
                self.context_briefs['foundation'] = brief
            
            # 保存检查点
            self._update_step_status('foundation_planning', 'completed', 38)
            self._save_session_checkpoint('phase_one', 'foundation_planning', 'completed')
            self.logger.info("[FoundationSession] 完成")
            return True
        
        return False

    def _run_character_session(self, api_client, provider, model_name) -> bool:
        """执行角色与叙事会话：核心角色 + 情绪蓝图 + 成长规划"""
        from src.core.session_mode.sessions.character_session import CharacterSession
        
        briefs = [self.context_briefs.get('foundation', "")] if self.context_briefs.get('foundation') else []
        
        session = CharacterSession(
            api_client=api_client,
            domain="character",
            context_briefs=briefs,
            novel_data=self.generator.novel_data,
            provider=provider,
            model_name=model_name,
        )
        
        self.logger.info("[CharacterSession] 开始执行...")
        success = session.execute_all_steps()
        
        if success:
            results = session.export_results()
            self.generator.novel_data.update(results)
            
            # 🔥 同步到现有系统：持久化核心角色设计
            try:
                character_design = results.get('character_design', {})
                if character_design and hasattr(self.generator, 'quality_assessor') and self.generator.quality_assessor:
                    if hasattr(self.generator.quality_assessor, 'persist_initial_character_designs'):
                        novel_title = self.generator.novel_data.get('novel_title', '')
                        self.generator.quality_assessor.persist_initial_character_designs(
                            novel_title=novel_title,
                            character_design=character_design
                        )
                        self.logger.info("✅ 核心角色设计已持久化")
            except Exception as e:
                self.logger.warning(f"⚠️ 持久化核心角色设计失败: {e}")
            
            brief = session.generate_brief(results)
            if brief:
                self.context_briefs['character'] = brief
            
            self._update_step_status('character_design', 'completed', 46)
            self._update_step_status('emotional_growth_planning', 'completed', 58)
            self._save_session_checkpoint('phase_one', 'emotional_growth_planning', 'completed')
            self.logger.info("[CharacterSession] 完成")
            return True
        
        return False

    def _run_structure_session(self, api_client, provider, model_name) -> bool:
        """执行结构规划会话：阶段划分 + 详细计划 + 补充角色"""
        from src.core.session_mode.sessions.structure_session import StructureSession
        
        briefs = []
        if self.context_briefs.get('foundation'):
            briefs.append(self.context_briefs['foundation'])
        if self.context_briefs.get('character'):
            briefs.append(self.context_briefs['character'])
        
        session = StructureSession(
            api_client=api_client,
            domain="structure",
            context_briefs=briefs,
            novel_data=self.generator.novel_data,
            provider=provider,
            model_name=model_name,
        )
        
        self.logger.info("[StructureSession] 开始执行...")
        success = session.execute_all_steps()
        
        if success:
            results = session.export_results()
            self.generator.novel_data.update(results)
            
            # 🔥 同步到现有系统：运行阶段计划相关的 manager 初始化
            try:
                # 触发 stage_plan_manager 的相关初始化（如果需要）
                if hasattr(self.generator, 'stage_plan_manager') and self.generator.stage_plan_manager:
                    # 将 overall_stage_plans 同步到 stage_plan_manager 的内部状态
                    overall_plans = results.get('overall_stage_plans', {})
                    if overall_plans and hasattr(self.generator.stage_plan_manager, 'overall_stage_plan_data'):
                        self.generator.stage_plan_manager.overall_stage_plan_data = overall_plans
                        self.logger.info("✅ 阶段计划已同步到 StagePlanManager")
            except Exception as e:
                self.logger.warning(f"⚠️ 同步阶段计划失败: {e}")
            
            brief = session.generate_brief(results)
            if brief:
                self.context_briefs['structure'] = brief
            
            # Structure 包含多个步骤，全部标记完成
            for step in self.DOMAIN_STEPS['structure']:
                self._update_step_status(step, 'completed', self.STEP_PROGRESS_MAP.get(step, 80))
            
            self._save_session_checkpoint('phase_one', 'system_init', 'completed')
            self.logger.info("[StructureSession] 完成")
            return True
        
        return False

    # ------------------------------------------------------------------
    # 二阶段执行（按阶段）
    # ------------------------------------------------------------------
    def run_phase_two_stage(self, stage_number: int) -> bool:
        """
        执行二阶段指定阶段的写作会话
        
        Args:
            stage_number: 阶段序号（从 1 开始）
        """
        from src.core.session_mode.sessions.stage_writing_session import StageWritingSession
        
        self.logger.info(f"[StageWritingSession-{stage_number}] 开始执行...")
        
        provider, model_name = self._get_provider_and_model()
        api_client = self._get_api_client()
        
        if not api_client:
            self._notify_failure("API 客户端不可用")
            return False
        
        # 收集所有上游 briefs
        briefs = [
            self.context_briefs.get('foundation', ""),
            self.context_briefs.get('character', ""),
            self.context_briefs.get('structure', ""),
        ]
        # 如果有上一阶段的 summary，也加入
        prev_summary = self.context_briefs.get(f'stage_{stage_number - 1}_summary', "")
        if prev_summary:
            briefs.append(prev_summary)
        
        session = StageWritingSession(
            api_client=api_client,
            domain="writing",
            context_briefs=briefs,
            novel_data=self.generator.novel_data,
            provider=provider,
            model_name=model_name,
            stage_number=stage_number,
        )
        
        try:
            success = session.execute_all_steps()
            
            if success:
                # 保存生成的章节
                chapters = session.get_generated_chapters()
                for chapter_num, chapter_data in chapters.items():
                    self._save_single_chapter(chapter_num, chapter_data)
                
                # 保存阶段 summary 作为下一阶段的输入
                stage_summary = session.get_stage_summary()
                if stage_summary:
                    self.context_briefs[f'stage_{stage_number}_summary'] = stage_summary
                
                self.logger.info(f"[StageWritingSession-{stage_number}] 完成，共生成 {len(chapters)} 章")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[StageWritingSession-{stage_number}] 执行失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    # ------------------------------------------------------------------
    # 兼容现有系统的辅助方法
    # ------------------------------------------------------------------
    def _save_phase_one_result(self):
        """调用现有方法保存一阶段结果"""
        try:
            if hasattr(self.generator, 'project_manager'):
                username = getattr(self.generator, '_username', None)
                title = self.generator.novel_data.get('novel_title')
                if title:
                    self.generator.project_manager.save_project(
                        title,
                        self.generator.novel_data,
                        username=username
                    )
                    self.logger.info("✅ 一阶段结果已保存到项目文件")
        except Exception as e:
            self.logger.warning(f"⚠️ 保存一阶段项目文件失败: {e}")

    def _save_single_chapter(self, chapter_number: int, chapter_data: Dict):
        """保存单章"""
        try:
            if hasattr(self.generator, 'project_manager'):
                username = getattr(self.generator, '_username', None)
                title = self.generator.novel_data.get('novel_title')
                if title:
                    self.generator.project_manager.save_single_chapter(
                        title, chapter_number, chapter_data, username=username
                    )
        except Exception as e:
            self.logger.warning(f"⚠️ 保存第 {chapter_number} 章失败: {e}")

    def _run_phase_one_quality_assessment(self):
        """调用一阶段质量评估（兼容现有逻辑）"""
        try:
            # 尝试调用 PhaseGenerator 上的评估方法
            if hasattr(self.generator, 'phase_generator'):
                pg = self.generator.phase_generator
                if hasattr(pg, '_run_phase_one_optimization'):
                    opt_result = pg._run_phase_one_optimization()
                    if opt_result:
                        self.generator.novel_data["phase_one_optimization"] = opt_result
                if hasattr(pg, '_assess_writing_plan_quality'):
                    assessment = pg._assess_writing_plan_quality()
                    if assessment:
                        self.generator.novel_data["quality_assessment"] = assessment
        except Exception as e:
            self.logger.warning(f"⚠️ 一阶段质量评估失败（不影响流程）: {e}")
