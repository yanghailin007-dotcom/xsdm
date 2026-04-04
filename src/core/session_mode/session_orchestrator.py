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
        
        # 标记前置步骤已完成
        pre_steps = ['creative_refinement', 'fanfiction_detection', 'multiple_plans', 'plan_selection']
        for step in pre_steps:
            self._update_step_status(step, 'completed', self.STEP_PROGRESS_MAP.get(step, 0))
        
        try:
            # ---------- Session A: Foundation ----------
            self._update_progress('foundation_planning', 32, "正在执行创作基线会话...")
            self._update_step_status('foundation_planning', 'active', 32)
            
            foundation_success = self._run_foundation_session(api_client, provider, model_name)
            if not foundation_success:
                self._notify_failure("创作基线会话 (Foundation) 失败")
                return False
            
            # ---------- Session B: Character ----------
            self._update_progress('character_design', 42, "正在执行角色与叙事会话...")
            self._update_step_status('character_design', 'active', 42)
            
            character_success = self._run_character_session(api_client, provider, model_name)
            if not character_success:
                self._notify_failure("角色与叙事会话 (Character) 失败")
                return False
            
            # ---------- Session C: Structure ----------
            self._update_progress('stage_plan', 62, "正在执行结构规划会话...")
            self._update_step_status('stage_plan', 'active', 62)
            
            structure_success = self._run_structure_session(api_client, provider, model_name)
            if not structure_success:
                self._notify_failure("结构规划会话 (Structure) 失败")
                return False
            
            # ---------- 保存与评估 ----------
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

    # ------------------------------------------------------------------
    # 各域会话实现
    # ------------------------------------------------------------------
    def _run_foundation_session(self, api_client, provider, model_name) -> bool:
        """执行创作基线会话：写作风格 + 市场分析 + 世界观 + 势力系统"""
        from src.core.session_mode.sessions.foundation_session import FoundationSession
        
        session = FoundationSession(
            api_client=api_client,
            domain="foundation",
            context_briefs=[],
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
