"""
第一阶段对话编排器 - PhaseOneConversationOrchestrator
======================================================

职责：
1. 管理4个 Session 的执行顺序
2. 处理 Context Brief 传递
3. 映射进度到15步骤体系
4. 集成检查点管理
5. 支持失败回退和恢复

架构：
    PhaseOneConversationOrchestrator
    ├── Session A: FoundationPlanningSession
    │   └── 产物: foundation_brief
    ├── Session B: CharacterNarrativeSession  
    │   └── 产物: character_brief
    ├── Session C: StructurePlanningSession
    │   └── 产物: structure_brief
    └── Session D: ExpectationSystemSession
        └── 产物: expectation_brief

使用示例：
    orchestrator = PhaseOneConversationOrchestrator(novel_generator)
    success = orchestrator.execute_phase_one(
        progress_callback=update_progress,
        step_status_callback=update_step_status
    )
"""

import json
import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

# 导入验证器和回退管理器
from src.core.session_mode.validators import (
    ValidatorFactory, 
    compare_session_outputs,
    generate_comparison_report,
    quick_validate
)
from src.core.session_mode.fallback_manager import (
    FallbackManager,
    ExecutionMode,
    create_fallback_manager_from_config
)

# 导入 Session（将在后续开发中实现）
try:
    from src.core.session_mode.sessions.foundation_planning_session import (
        FoundationPlanningSession
    )
    FOUNDATION_SESSION_AVAILABLE = True
except ImportError:
    FOUNDATION_SESSION_AVAILABLE = False

try:
    from src.core.session_mode.sessions.character_narrative_session import (
        CharacterNarrativeSession
    )
    CHARACTER_SESSION_AVAILABLE = False
except ImportError:
    CHARACTER_SESSION_AVAILABLE = False

try:
    from src.core.session_mode.sessions.structure_session import StructureSession
    STRUCTURE_SESSION_AVAILABLE = True
except ImportError:
    STRUCTURE_SESSION_AVAILABLE = False

try:
    from src.core.session_mode.sessions.expectation_system_session import (
        ExpectationSystemSession
    )
    EXPECTATION_SESSION_AVAILABLE = False
except ImportError:
    EXPECTATION_SESSION_AVAILABLE = False

logger = get_logger("PhaseOneConversationOrchestrator")


@dataclass
class SessionContext:
    """Session 上下文信息"""
    session_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_mode: Optional[ExecutionMode] = None
    result: Any = None
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class PhaseOneContext:
    """第一阶段完整上下文"""
    foundation_brief: Dict[str, Any] = field(default_factory=dict)
    character_brief: Dict[str, Any] = field(default_factory=dict)
    structure_brief: Dict[str, Any] = field(default_factory=dict)
    expectation_brief: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "foundation_brief": self.foundation_brief,
            "character_brief": self.character_brief,
            "structure_brief": self.structure_brief,
            "expectation_brief": self.expectation_brief,
            "version": "1.0"
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhaseOneContext':
        context = cls()
        context.foundation_brief = data.get("foundation_brief", {})
        context.character_brief = data.get("character_brief", {})
        context.character_brief = data.get("character_brief", {})
        context.structure_brief = data.get("structure_brief", {})
        context.expectation_brief = data.get("expectation_brief", {})
        return context


class PhaseOneConversationOrchestrator:
    """
    第一阶段对话编排器
    
    将第一阶段的剩余步骤（5-15）编排为4个对话Session
    """
    
    # 15步骤进度映射
    STEP_PROGRESS_MAP = {
        'foundation_planning': 45,
        'worldview_with_factions': 55,
        'character_design': 65,
        'emotional_growth_planning': 72,
        'stage_plan': 78,
        'detailed_stage_plans': 82,
        'supplementary_characters': 85,
        'expectation_mapping': 88,
        'system_init': 92,
        'saving': 96,
        'quality_assessment': 100
    }
    
    # Session 顺序定义
    SESSION_ORDER = [
        "foundation_planning",
        "character_narrative", 
        "structure_planning",
        "expectation_system"
    ]
    
    def __init__(
        self,
        novel_generator,
        fallback_manager: Optional[FallbackManager] = None,
        enable_comparison_test: bool = False
    ):
        """
        初始化编排器
        
        Args:
            novel_generator: NovelGenerator 实例
            fallback_manager: 回退管理器（可选）
            enable_comparison_test: 是否启用对比测试模式
        """
        self.generator = novel_generator
        self.logger = get_logger("PhaseOneOrchestrator")
        
        # 回退管理器
        self.fallback_manager = fallback_manager or get_default_fallback_manager()
        
        # 对比测试模式
        self.enable_comparison_test = enable_comparison_test
        self.comparison_results: List[Dict] = []
        
        # 执行上下文
        self.context = PhaseOneContext()
        self.session_contexts: Dict[str, SessionContext] = {}
        
        # 检查点管理器（延迟初始化）
        self._checkpoint_mgr = None
        
        # 进度回调
        self._progress_callback: Optional[Callable[[str, int, str], None]] = None
        self._step_status_callback: Optional[Callable[[str, str, int], None]] = None
        
        self.logger.info("PhaseOneConversationOrchestrator 初始化完成")
    
    # =====================================================================
    # 主入口方法
    # =====================================================================
    
    def execute_phase_one(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        step_status_callback: Optional[Callable[[str, str, int], None]] = None,
        resume_from_session: Optional[str] = None
    ) -> bool:
        """
        执行第一阶段全部对话Session
        
        Args:
            progress_callback: 进度回调(stage_name, progress, message)
            step_status_callback: 步骤状态回调(step_name, status, progress)
            resume_from_session: 从指定Session恢复（可选）
            
        Returns:
            是否全部成功
        """
        self._progress_callback = progress_callback
        self._step_status_callback = step_status_callback
        
        start_session_idx = 0
        if resume_from_session:
            try:
                start_session_idx = self.SESSION_ORDER.index(resume_from_session)
                self.logger.info(f"从 Session {resume_from_session} 恢复执行")
            except ValueError:
                self.logger.warning(f"未知的Session名称: {resume_from_session}")
        
        try:
            # 执行各个Session
            for i, session_name in enumerate(self.SESSION_ORDER[start_session_idx:], 
                                            start=start_session_idx):
                self.logger.info(f"开始执行 Session {i+1}/4: {session_name}")
                
                success = self._execute_session(session_name)
                if not success:
                    self.logger.error(f"Session {session_name} 执行失败")
                    return False
                
                # 保存检查点
                self._save_checkpoint(session_name)
            
            # 执行最后的保存和质量评估步骤
            self._execute_final_steps()
            
            self.logger.info("✅ 第一阶段全部完成")
            return True
            
        except Exception as e:
            self.logger.error(f"第一阶段执行出错: {e}", exc_info=True)
            return False
    
    def execute_single_session(
        self,
        session_name: str,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        step_status_callback: Optional[Callable[[str, str, int], None]] = None
    ) -> Tuple[bool, Any]:
        """
        执行单个Session（用于测试和调试）
        
        Args:
            session_name: Session名称
            progress_callback: 进度回调
            step_status_callback: 步骤状态回调
            
        Returns:
            (成功状态, 结果)
        """
        self._progress_callback = progress_callback
        self._step_status_callback = step_status_callback
        
        if session_name not in self.SESSION_ORDER:
            self.logger.error(f"未知的Session: {session_name}")
            return False, None
        
        return self._execute_session(session_name), \
               self.session_contexts.get(session_name, SessionContext(session_name)).result
    
    # =====================================================================
    # Session 执行
    # =====================================================================
    
    def _execute_session(self, session_name: str) -> bool:
        """执行指定Session"""
        session_ctx = SessionContext(session_name=session_name)
        session_ctx.start_time = datetime.now()
        self.session_contexts[session_name] = session_ctx
        
        try:
            if session_name == "foundation_planning":
                success = self._execute_foundation_session(session_ctx)
            elif session_name == "character_narrative":
                success = self._execute_character_session(session_ctx)
            elif session_name == "structure_planning":
                success = self._execute_structure_session(session_ctx)
            elif session_name == "expectation_system":
                success = self._execute_expectation_session(session_ctx)
            else:
                self.logger.error(f"未知的Session: {session_name}")
                return False
            
            session_ctx.end_time = datetime.now()
            
            if success:
                self.logger.info(
                    f"✅ Session {session_name} 完成，"
                    f"耗时 {session_ctx.duration_seconds:.1f} 秒"
                )
            
            return success
            
        except Exception as e:
            session_ctx.end_time = datetime.now()
            session_ctx.error = str(e)
            self.logger.error(f"❌ Session {session_name} 异常: {e}", exc_info=True)
            return False
    
    def _execute_foundation_session(self, session_ctx: SessionContext) -> bool:
        """执行 FoundationPlanningSession (Session A)"""
        self._update_step_status('foundation_planning', 'active', 45)
        
        if FOUNDATION_SESSION_AVAILABLE:
            # 使用对话模式
            def conversation_func():
                session = FoundationPlanningSession(
                    api_client=self.generator.api_client,
                    novel_data=self.generator.novel_data,
                    provider=getattr(self.generator, 'provider', 'gemini'),
                    model_name=getattr(self.generator, 'model_name', None),
                    temperature=getattr(self.generator, 'temperature', 0.7)
                )
                
                # 设置进度回调
                if self._progress_callback:
                    session.set_progress_callback(
                        lambda p, m: self._progress_callback('foundation_planning', p, m)
                    )
                
                result = session.execute_all_steps()
                
                # 同步结果到 novel_data
                self._sync_foundation_results(result)
                
                # 生成 Context Brief 传递给下一个Session
                self.context.foundation_brief = session.export_context_brief()
                
                return result
        else:
            conversation_func = None
        
        # 传统模式回退函数
        def traditional_func():
            from src.core.PhaseGenerator import PhaseGenerator
            pg = PhaseGenerator(self.generator)
            
            # 执行基础规划
            if not pg._generate_foundation_planning(update_step_status=self._step_status_callback):
                raise RuntimeError("基础规划生成失败")
            
            # 执行世界观与势力
            if not pg._generate_worldview_and_factions(update_step_status=self._step_status_callback):
                raise RuntimeError("世界观与势力生成失败")
            
            # 从 novel_data 构建结果
            return {
                "writing_style_guide": self.generator.novel_data.get("writing_style_guide", {}),
                "market_analysis": self.generator.novel_data.get("market_analysis", {}),
                "core_worldview": self.generator.novel_data.get("core_worldview", {}),
                "faction_system": self.generator.novel_data.get("faction_system", {})
            }
        
        # 验证函数
        def validator_func(result):
            return quick_validate('foundation_planning', result)
        
        # 执行（带回退）
        if conversation_func:
            success, result, mode = self.fallback_manager.execute_with_fallback(
                "foundation_planning",
                conversation_func,
                traditional_func,
                validator_func,
                self._progress_callback
            )
        else:
            self.logger.info("FoundationPlanningSession 不可用，使用传统模式")
            result = traditional_func()
            success = True
            mode = ExecutionMode.TRADITIONAL
        
        session_ctx.result = result
        session_ctx.execution_mode = mode
        
        # 对比测试
        if self.enable_comparison_test and conversation_func and mode == ExecutionMode.TRADITIONAL:
            self._run_comparison_test("foundation_planning", conversation_func, traditional_func)
        
        self._update_step_status('worldview_with_factions', 'completed', 55)
        return success
    
    def _execute_character_session(self, session_ctx: SessionContext) -> bool:
        """执行 CharacterNarrativeSession (Session B)"""
        self._update_step_status('character_design', 'active', 65)
        
        # 暂时使用传统模式（等待Session实现）
        def traditional_func():
            from src.core.PhaseGenerator import PhaseGenerator
            pg = PhaseGenerator(self.generator)
            
            # 执行角色设计
            if not pg._generate_character_design(update_step_status=self._step_status_callback):
                raise RuntimeError("角色设计生成失败")
            
            # 执行情绪蓝图与成长规划
            if not pg._generate_emotional_and_growth_plan(update_step_status=self._step_status_callback):
                raise RuntimeError("情绪与成长规划生成失败")
            
            return {
                "character_design": self.generator.novel_data.get("character_design", {}),
                "emotional_blueprint": self.generator.novel_data.get("emotional_blueprint", {}),
                "global_growth_plan": self.generator.novel_data.get("global_growth_plan", {})
            }
        
        # TODO: 实现对话模式后替换
        result = traditional_func()
        success = True
        mode = ExecutionMode.TRADITIONAL
        
        session_ctx.result = result
        session_ctx.execution_mode = mode
        
        self._update_step_status('emotional_growth_planning', 'completed', 72)
        return success
    
    def _execute_structure_session(self, session_ctx: SessionContext) -> bool:
        """执行 StructurePlanningSession (Session C)"""
        self._update_step_status('stage_plan', 'active', 78)
        
        # 暂时使用传统模式
        def traditional_func():
            from src.core.PhaseGenerator import PhaseGenerator
            pg = PhaseGenerator(self.generator)
            
            # 执行全书规划
            if not pg._generate_overall_planning(update_step_status=self._step_status_callback):
                raise RuntimeError("全书规划生成失败")
            
            return {
                "overall_stage_plans": self.generator.novel_data.get("overall_stage_plans", {}),
                "stage_writing_plans": self.generator.novel_data.get("stage_writing_plans", {}),
                "supplementary_characters": self.generator.novel_data.get("supplementary_characters", [])
            }
        
        result = traditional_func()
        success = True
        mode = ExecutionMode.TRADITIONAL
        
        session_ctx.result = result
        session_ctx.execution_mode = mode
        
        self._update_step_status('supplementary_characters', 'completed', 85)
        return success
    
    def _execute_expectation_session(self, session_ctx: SessionContext) -> bool:
        """执行 ExpectationSystemSession (Session D)"""
        self._update_step_status('expectation_mapping', 'active', 88)
        
        # 暂时使用传统模式
        def traditional_func():
            # 期待感映射和系统初始化在传统模式中是自动完成的
            return {
                "expectation_mapping": self.generator.novel_data.get("expectation_mapping", {}),
                "system_init": {"status": "completed"}
            }
        
        result = traditional_func()
        success = True
        mode = ExecutionMode.TRADITIONAL
        
        session_ctx.result = result
        session_ctx.execution_mode = mode
        
        self._update_step_status('system_init', 'completed', 92)
        return success
    
    def _execute_final_steps(self):
        """执行最后的保存和质量评估步骤"""
        # 保存结果
        self._update_step_status('saving', 'active', 96)
        from src.core.PhaseGenerator import PhaseGenerator
        pg = PhaseGenerator(self.generator)
        pg._save_phase_one_result()
        self._update_step_status('saving', 'completed', 96)
        
        # 质量评估
        self._update_step_status('quality_assessment', 'active', 100)
        pg._assess_writing_plan_quality()
        self._update_step_status('quality_assessment', 'completed', 100)
    
    # =====================================================================
    # 结果同步
    # =====================================================================
    
    def _sync_foundation_results(self, result: Dict):
        """同步 Foundation Session 结果到 novel_data"""
        if result.get("writing_style_guide"):
            self.generator.novel_data["writing_style_guide"] = result["writing_style_guide"]
        
        if result.get("market_analysis"):
            self.generator.novel_data["market_analysis"] = result["market_analysis"]
        
        if result.get("core_worldview"):
            self.generator.novel_data["core_worldview"] = result["core_worldview"]
        
        if result.get("faction_system"):
            self.generator.novel_data["faction_system"] = result["faction_system"]
    
    # =====================================================================
    # 检查点管理
    # =====================================================================
    
    def _get_checkpoint_manager(self):
        """获取检查点管理器"""
        if self._checkpoint_mgr is None:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            
            title = self.generator.novel_data.get("novel_title") or \
                    self.generator.novel_data.get("title", "")
            username = getattr(self.generator, '_username', None)
            
            if title:
                self._checkpoint_mgr = GenerationCheckpoint(
                    title, Path.cwd(), username=username
                )
        
        return self._checkpoint_mgr
    
    def _save_checkpoint(self, session_name: str):
        """保存检查点"""
        checkpoint_mgr = self._get_checkpoint_manager()
        if not checkpoint_mgr:
            return
        
        try:
            checkpoint_data = {
                "context": self.context.to_dict(),
                "session_contexts": {
                    name: {
                        "execution_mode": ctx.execution_mode.value if ctx.execution_mode else None,
                        "error": ctx.error
                    }
                    for name, ctx in self.session_contexts.items()
                },
                "novel_data_snapshot": dict(self.generator.novel_data)
            }
            
            checkpoint_mgr.create_checkpoint(
                phase='phase_one',
                step=session_name,
                data=checkpoint_data,
                step_status='completed'
            )
            
            self.logger.info(f"检查点已保存: {session_name}")
        except Exception as e:
            self.logger.warning(f"保存检查点失败: {e}")
    
    def restore_from_checkpoint(self) -> bool:
        """从检查点恢复"""
        checkpoint_mgr = self._get_checkpoint_manager()
        if not checkpoint_mgr:
            return False
        
        try:
            checkpoint = checkpoint_mgr.load_checkpoint('phase_one')
            if not checkpoint:
                return False
            
            data = checkpoint.get('data', {})
            
            # 恢复上下文
            if 'context' in data:
                self.context = PhaseOneContext.from_dict(data['context'])
            
            # 恢复 novel_data
            if 'novel_data_snapshot' in data:
                self.generator.novel_data.update(data['novel_data_snapshot'])
            
            self.logger.info(f"已从检查点恢复: {checkpoint.get('step', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"从检查点恢复失败: {e}")
            return False
    
    # =====================================================================
    # 对比测试
    # =====================================================================
    
    def _run_comparison_test(
        self,
        session_name: str,
        conversation_func: Callable,
        traditional_func: Callable
    ):
        """运行对比测试"""
        self.logger.info(f"运行对比测试: {session_name}")
        
        try:
            # 使用对话模式生成
            conv_result = conversation_func()
            
            # 使用传统模式生成
            trad_result = traditional_func()
            
            # 对比
            comparison = compare_session_outputs(trad_result, conv_result, session_name)
            self.comparison_results.append(comparison)
            
            # 记录结果
            if comparison.get("is_compatible"):
                self.logger.info(f"✅ {session_name} 对比测试通过")
            else:
                self.logger.warning(
                    f"⚠️ {session_name} 对比测试发现差异: "
                    f"{comparison.get('difference_summary', '')}"
                )
                
        except Exception as e:
            self.logger.error(f"对比测试失败: {e}")
    
    def generate_comparison_report(self) -> str:
        """生成对比测试报告"""
        return generate_comparison_report(self.comparison_results)
    
    # =====================================================================
    # 辅助方法
    # =====================================================================
    
    def _update_step_status(self, step_name: str, status: str, progress: int):
        """更新步骤状态"""
        if self._step_status_callback:
            self._step_status_callback(step_name, status, progress)
    
    def _update_progress(self, stage_name: str, progress: int, message: str):
        """更新进度"""
        if self._progress_callback:
            self._progress_callback(stage_name, progress, message)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "sessions": {
                name: {
                    "mode": ctx.execution_mode.value if ctx.execution_mode else None,
                    "duration": ctx.duration_seconds,
                    "error": ctx.error
                }
                for name, ctx in self.session_contexts.items()
            },
            "total_duration": sum(
                ctx.duration_seconds for ctx in self.session_contexts.values()
            ),
            "comparison_results": self.comparison_results
        }


# =============================================================================
# 便捷函数
# =============================================================================

def create_phase_one_orchestrator(
    novel_generator,
    config: Optional[Dict] = None
) -> PhaseOneConversationOrchestrator:
    """
    创建第一阶段编排器
    
    Args:
        novel_generator: NovelGenerator 实例
        config: 配置字典
        
    配置示例:
        {
            "fallback_config": {
                "foundation_planning": {"mode": "auto"},
                "character_narrative": {"mode": "traditional"}
            },
            "enable_comparison_test": False
        }
    """
    config = config or {}
    
    # 创建回退管理器
    fallback_config = config.get("fallback_config", {})
    fallback_manager = create_fallback_manager_from_config(fallback_config)
    
    # 创建编排器
    return PhaseOneConversationOrchestrator(
        novel_generator=novel_generator,
        fallback_manager=fallback_manager,
        enable_comparison_test=config.get("enable_comparison_test", False)
    )
