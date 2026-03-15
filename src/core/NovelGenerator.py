"""
小说生成器主类 - 重构版本
这是一个轻量级的控制器，负责协调各个专门模块的工作
"""

import sys
import signal
import time
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union, Any, List, Tuple

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# 导入原有的核心组件
from src.core.APIClient import APIClient
from src.core.ContentGenerator import ContentGenerator
from src.core.Contexts import GenerationContext
from src.core.MaterialManager import MaterialManager
from src.core.EventBus import EventBus
from src.core.ProjectManager import ProjectManager
from src.core.QualityAssessor import QualityAssessor

# 导入管理器
from src.managers.EmotionalBlueprintManager import EmotionalBlueprintManager
from src.managers.EmotionalPlanManager import EmotionalPlanManager
from src.managers.EventDrivenManager import EventDrivenManager
from src.managers.ExpectationManager import ExpectationManager, ExpectationType
from src.managers.GlobalGrowthPlanner import GlobalGrowthPlanner
from src.managers.RomancePatternManager import RomancePatternManager
from src.managers.StagePlanManager import StagePlanManager

# 导入新的模块化组件
from src.core.generation.PlanGenerator import PlanGenerator
from src.core.ImprovedFanfictionDetector import ImprovedFanfictionDetector
from src.core.content.CoverGenerator import CoverGenerator

# 导入拆分后的模块
from src.core.PhaseGenerator import PhaseGenerator
from src.core.ResumeManager import ResumeManager

# 导入批量生成模块
from src.core.batch_generation.integration import BatchGenerationAdapter

# 导入工具组件
from src.utils.DouBaoImageGenerator import DouBaoImageGenerator
from src.core.ContentVerifier import ContentVerifier
# 直接导入doubaoconfig，避免路径冲突
import sys
import os
from pathlib import Path

# 确保项目根目录在路径中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
config_path = project_root / "config" / "doubaoconfig.py"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 使用importlib来动态导入
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("doubaoconfig", config_path)
    if spec is not None and spec.loader is not None:
        doubaoconfig_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(doubaoconfig_module)
    else:
        raise ImportError("无法创建模块规格")
    
    # 将所有变量导入到当前命名空间
    for attr_name in dir(doubaoconfig_module):
        if not attr_name.startswith('_'):
            globals()[attr_name] = getattr(doubaoconfig_module, attr_name)
    
except Exception as e:
    print(f"警告：无法导入doubaoconfig: {e}")
    # 设置默认值
    ARK_API_KEY = None

# 导入提示词
from src.prompts.Prompts import Prompts

# 导入工具
from src.utils.logger import get_logger


class NovelGenerator:
    """
    小说生成器主类 - 重构版本（支持并发）
    这是一个轻量级的控制器，负责协调各个专门模块的工作
    
    🔥 并发支持：每个任务有独立的上下文，通过 task_contexts 管理
    """

    def __init__(self, config):
        """初始化小说生成器"""
        self.config = config
        
        # 核心组件初始化
        self._initialize_core_components()
        
        # 模块化组件初始化
        self._initialize_modular_components()
        
        # 管理器初始化
        self._initialize_managers()
        
        # 事件系统设置
        self._setup_event_handlers()
        
        # 数据结构初始化
        self._initialize_data_structures()
        
        # 进度回调支持（动态设置）
        self._update_task_status_callback = None
        self._current_task_id = None
        self._phase_two_progress_callback = None
        self._phase_two_from_chapter = None
        self._phase_two_total_chapters = None
        
        # API调用扣费追踪
        self._api_points_consumed = 0  # API调用实际消耗的点数
        self._user_id = None  # 当前用户ID（用于扣费）
        
        # 信号处理
        self._setup_signal_handlers()
        
        # 初始化拆分后的模块
        self._initialize_modular_managers()
        
        # 打印初始化信息
        self._print_initialization_info()

    def _initialize_core_components(self):
        """初始化核心组件"""
        # 日志器（必须最先初始化）
        self.logger = get_logger("NovelGenerator")
        
        # API客户端
        self.api_client = APIClient(self.config)
        # 设置API调用扣费回调
        self.api_client.set_api_call_callback(self._on_api_call_deduct_points)
        
        # 质量评估器 - 延迟初始化（需要 novel_title）
        self.quality_assessor = None
        
        # 内容生成器和项目管理者
        self.content_generator = ContentGenerator(
            novel_generator=self,
            api_client=self.api_client,
            config=self.config,
            event_bus=EventBus(),  # 临时创建，后面会被覆盖
            quality_assessor=None
        )
        
        # 初始化批量生成适配器
        self.content_generator.batch_adapter = BatchGenerationAdapter(
            self.content_generator
        )
        
        self.project_manager = ProjectManager()
        
        # 事件总线（重新创建以正确的引用）
        self.event_bus = EventBus()
        self.content_generator.event_bus = self.event_bus
        
        # 材料管理器（延迟初始化）
        self.material_manager = None
        
        # 内容验证器
        self.content_verifier = ContentVerifier()
        
        # 提示词管理器
        self.Prompts = Prompts()

    def _initialize_modular_components(self):
        """初始化模块化组件"""
        # 方案生成器
        self.plan_generator = PlanGenerator(
            api_client=self.api_client,
            quality_assessor=self.quality_assessor,
            content_generator=self.content_generator
        )
        
        # 同人小说检测器（使用改进版，支持功法名排除）
        self.fanfiction_detector = ImprovedFanfictionDetector(api_client=self.api_client)
        
        # 封面生成器
        cover_generator = None
        try:
            doubao_api_key = ARK_API_KEY
            if doubao_api_key:
                cover_generator = DouBaoImageGenerator()
                self.logger.info("封面生成器初始化成功")
            else:
                self.logger.info("未配置豆包API密钥，封面生成功能不可用")
        except Exception as e:
            self.logger.info(f"封面生成器初始化失败: {e}")
        
        self.cover_generator = CoverGenerator(cover_generator)
        
        # 章节生成器（暂时使用原方式，后续可以进一步模块化）
        self.chapter_generator = None  # 暂时设为None，避免导入问题

    def _initialize_managers(self):
        """初始化各管理器"""
        # 事件驱动管理器
        self.event_driven_manager = EventDrivenManager(novel_generator=self)
        
        # 期待感管理器（替代原伏笔管理器）
        self.expectation_manager = ExpectationManager()
        
        # 全局成长规划器
        self.global_growth_planner = GlobalGrowthPlanner(novel_generator=self)
        
        # 阶段计划管理器
        self.stage_plan_manager = StagePlanManager(novel_generator=self)
        
        # 情感蓝图管理器
        self.emotional_blueprint_manager = EmotionalBlueprintManager(novel_generator=self)
        
        # 情感计划管理器
        self.emotional_plan_manager = EmotionalPlanManager(novel_generator=self)
        
        # 联姻模式管理器
        self.romance_manager = RomancePatternManager(self.stage_plan_manager)

    def _initialize_modular_managers(self):
        """初始化拆分后的模块管理器"""
        # 阶段生成器
        self.phase_generator = PhaseGenerator(self)
        
        # 恢复模式管理器
        self.resume_manager = ResumeManager(self)
        
        self.logger.info("模块化管理器初始化完成")

    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.event_bus.subscribe('chapter.generated', self._on_chapter_generated)
        self.event_bus.subscribe('chapter.assessed', self._on_chapter_assessed)
        self.event_bus.subscribe('error.occurred', self._on_error_occurred)
    
    def _on_api_call_deduct_points(self, purpose: str, attempt: int):
        """API调用扣费回调 - 每次成功API调用扣除1点"""
        try:
            # 增加内部计数
            self._api_points_consumed += 1
            
            # 如果设置了用户ID，则实际扣除点数
            if self._user_id:
                from web.models.point_model import point_model
                result = point_model.spend_points(
                    user_id=self._user_id,
                    amount=1,
                    source='api_call',
                    description=f'API调用: {purpose}',
                    related_id=self._current_task_id
                )
                if result['success']:
                    self.logger.info(f"💰 API调用扣费成功: {purpose} (-1点, 总计: {self._api_points_consumed})")
                else:
                    self.logger.error(f"❌ API调用扣费失败: {result.get('error')}")
            
            # 发布点数消耗事件（用于前端实时更新）
            self.event_bus.publish('points.consumed', {
                'consumed': self._api_points_consumed,
                'purpose': purpose,
                'task_id': self._current_task_id
            })
            
        except Exception as e:
            self.logger.error(f"❌ API调用扣费回调出错: {e}")
    
    def set_user_id(self, user_id: int):
        """设置当前用户ID（用于扣费）"""
        self._user_id = user_id
        self.logger.info(f"👤 已设置用户ID: {user_id}")
    
    def set_username(self, username: str):
        """设置当前用户名（用于用户隔离路径和API日志）"""
        self._username = username
        self.logger.info(f"👤 已设置用户名: {username}")
        
        # 🔥 同时设置 APIClient 的用户名，用于日志区分
        if hasattr(self, 'api_client') and self.api_client:
            try:
                self.api_client.set_username(username)
            except Exception as e:
                self.logger.debug(f"设置 APIClient 用户名失败: {e}")
    
    def get_api_points_consumed(self) -> int:
        """获取API调用消耗的点数"""
        return self._api_points_consumed
    
    def reset_api_points_counter(self):
        """重置API调用点数计数器"""
        self._api_points_consumed = 0
        self.api_client.reset_api_call_counter()
        self.logger.info("🔄 API调用点数计数器已重置")

    def _initialize_data_structures(self):
        """初始化数据结构（支持并发）"""
        # 🔥 并发支持：每个任务有独立的上下文
        import threading
        self._task_lock = threading.Lock()
        self._task_contexts = {}  # {task_id: novel_data}
        
        # 保留默认 novel_data 用于向后兼容（无任务ID时使用）
        self.novel_data = self._create_default_novel_data()
    
    def _create_default_novel_data(self) -> Dict:
        """创建默认的 novel_data 结构"""
        return {
            "current_progress": {
                "completed_chapters": 0,
                "total_chapters": 0,
                "stage": "未开始",
                "current_stage": "第一阶段",
                "current_batch": 0,
                "start_time": None
            },
            "generated_chapters": {},
            "used_chapter_titles": set(),
            "previous_chapter_endings": {},
            "plot_progression": [],
            "chapter_quality_records": {},
            "optimization_history": {},
            "is_resuming": False,
            "resume_data": None
        }
    
    @property
    def _ctx(self) -> Dict:
        """
        获取当前任务上下文（便捷属性）
        
        Returns:
            任务的 novel_data 字典
        """
        return self._get_task_context()
    
    def _get_task_context(self, task_id: str = None) -> Dict:
        """
        获取任务上下文（支持并发）
        
        Args:
            task_id: 任务ID，如果为None则使用当前任务ID或返回默认上下文
            
        Returns:
            任务的 novel_data 字典
        """
        if task_id is None:
            task_id = getattr(self, '_current_task_id', None)
        
        if task_id is None:
            return self.novel_data  # 向后兼容，使用默认上下文
        
        with self._task_lock:
            if task_id not in self._task_contexts:
                self._task_contexts[task_id] = self._create_default_novel_data()
            return self._task_contexts[task_id]
    
    def _cleanup_task_context(self, task_id: str) -> None:
        """
        清理任务上下文（任务完成后调用）
        
        Args:
            task_id: 任务ID
        """
        with self._task_lock:
            if task_id in self._task_contexts:
                del self._task_contexts[task_id]
                self.logger.info(f"🧹 任务 {task_id}: 上下文已清理")

    def _setup_signal_handlers(self):
        """设置中断信号处理 - 需要按两次 Ctrl+C 才会退出"""
        self._sigint_count = 0
        self._sigint_last_time = 0
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
        except ValueError:
            pass  # signal only works in main thread of the main interpreter

    def _print_initialization_info(self):
        """打印初始化信息"""
        default_provider = self.api_client.get_default_provider()
        current_model = self.api_client.get_current_model()
        print(f"默认提供商: {default_provider}")
        print(f"当前模型: {current_model}")

    def _check_stop_requested(self, context: str = "") -> None:
        """🔥 检查是否被请求停止生成
        
        Args:
            context: 当前上下文描述，用于日志
            
        Raises:
            InterruptedError: 当停止标志被设置时
        """
        try:
            if hasattr(self, '_stop_check_callback'):
                # 调用停止检查回调
                self._stop_check_callback()
                # 如果没有抛出异常，说明没有被停止
        except InterruptedError:
            self.logger.info(f"🛑 生成被用户停止{' - ' + context if context else ''}")
            raise
        except Exception as e:
            # 检查失败时不中断生成，只记录日志
            self.logger.debug(f"停止检查失败: {e}")
    
    def _call_api_with_stop_check(self, system_prompt: str, user_prompt: str, 
                                  temperature: float = 0.7, purpose: str = "未知", 
                                  context: str = "") -> Optional[str]:
        """🔥 包装API调用，在调用前检查停止标志
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            purpose: API调用目的
            context: 停止检查上下文描述
            
        Returns:
            API响应内容，如果停止则返回None
            
        Raises:
            InterruptedError: 当停止标志被设置时
        """
        # 在API调用前检查停止标志
        self._check_stop_requested(context or f"API调用({purpose})前")
        
        # 执行API调用
        result = self.api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            purpose=purpose
        )
        
        # API调用后也检查一次（快速返回的情况）
        self._check_stop_requested(context or f"API调用({purpose})后")
        
        return result
    
    def _update_step_status(self, step_name: str, step_state: str, message: str = None):
        """🔥 更新单个步骤的状态（用于前端进度显示）
        
        Args:
            step_name: 步骤名称，如 'writing_style', 'worldview', 'character_design' 等
            step_state: 步骤状态，'waiting'/'active'/'completed'/'failed'
            message: 可选的状态描述消息（已废弃，保持兼容）
        """
        # 🔥 检查是否被请求停止（只在步骤开始时检查）
        if step_state == 'active':
            self._check_stop_requested(f"步骤 '{step_name}' 开始前")
        
        try:
            if hasattr(self, '_update_task_status_callback'):
                task_id = getattr(self, '_current_task_id', None)
                if task_id and callable(self._update_task_status_callback):
                    # 🔥 统一格式：使用简单的 {step_name: status} 格式
                    step_status = {step_name: step_state}
                    # 🔥 修复：不传入固定的进度值(0)，让外部保持已有进度
                    # 传入 None 表示不修改进度，只更新步骤状态
                    # 🔥 传递 points_consumed 点数消耗
                    points_consumed = getattr(self, '_api_points_consumed', 0)
                    self._update_task_status_callback(
                        task_id, 
                        'generating', 
                        None,  # 🔥 传入 None，让外部保持已有进度
                        None,
                        step_name,  # current_step
                        step_status,
                        points_consumed  # 🔥 添加点数消耗
                    )
                    self.logger.info(f"🔄 步骤状态更新: {step_name} -> {step_state}")
        except Exception as callback_error:
            print(f"⚠️ 步骤状态更新回调失败: {callback_error}")

    # ==================== 主要接口方法 ====================

    def phase_one_generation(self, creative_seed, total_chapters: Optional[int] = None, start_new: bool = False, target_platform: str = "fanqie"):
        """
        第一阶段生成：只执行到"第一章生成前"
        包括：方案生成、基础规划、世界观、角色设计、全书规划等准备工作
        支持从检查点恢复
        
        Args:
            creative_seed: 创意种子
            total_chapters: 总章节数
            start_new: 是否从头开始（忽略检查点）
            target_platform: 目标平台 (fanqie/qidian/zhihu)  # 🔥 新增平台参数
        """
        # 🔥 保存平台信息到novel_data
        self._ctx["target_platform"] = target_platform
        def notify_failure(error_msg: str):
            """通知任务失败"""
            try:
                if hasattr(self, '_update_task_status_callback'):
                    task_id = getattr(self, '_current_task_id', None)
                    if task_id and callable(self._update_task_status_callback):
                        self._update_task_status_callback(task_id, 'failed', 0, error_msg)
            except Exception as callback_error:
                print(f"⚠️ 失败通知回调失败: {callback_error}")
        
        self.logger.info("[START] 开始第一阶段设定生成...")
        self.logger.info(f"[PARAM] start_new={start_new}, target_platform={target_platform}")
        
        # 🔥 检查是否被请求停止
        self._check_stop_requested("生成开始前")
        
        # 不打印完整的创意种子，避免过长输出
        if isinstance(creative_seed, dict):
            novel_title = creative_seed.get('novelTitle') or creative_seed.get('novel_title')
            if novel_title:
                self.logger.info(f"创意种子标题: {novel_title}")
            else:
                self.logger.info(f"创意种子类型: {type(creative_seed).__name__}")
        else:
            self.logger.info(f"创意种子类型: {type(creative_seed).__name__}")

        if total_chapters is None:
            total_chapters = self.config.get("defaults", {}).get("total_chapters", 200)
        # 确保总章节数是整数
        assert total_chapters is not None, "total_chapters 必须是整数"
        temp_title_for_filename = f"未定稿创意_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 🔥 修复：只有当 start_new=False 时才检查检查点
        # 如果用户选择"从新开始"（start_new=True），则跳过检查点恢复
        if not start_new:
            self.logger.info("🔍 检查是否有可恢复的检查点...")
            # 检查是否有检查点可以恢复
            checkpoint_data = self._check_for_resume_checkpoint(creative_seed, total_chapters)
            if checkpoint_data:
                self.logger.info(f"🔄 检测到检查点，从步骤 '{checkpoint_data['current_step']}' 恢复")
                return self._resume_phase_one_from_checkpoint(checkpoint_data, creative_seed, total_chapters)
            else:
                self.logger.info("ℹ️ 未检测到检查点，将从头开始")
        else:
            self.logger.info("🆕 用户选择从头开始，跳过检查点恢复")
        
        # 没有检查点或用户选择从头开始，从头开始生成
        self.logger.info("🆕 从头开始生成")
        
        # 重置API调用点数计数器
        self.reset_api_points_counter()
        
        # 注意：初始检查点将在方案生成完成后再创建，那时才会有所有必要字段
        
        if isinstance(creative_seed, str):
            try:
                # 尝试解析JSON字符串
                creative_work_dict = json.loads(creative_seed)
            except:
                # 如果解析失败，创建一个基础字典结构
                creative_work_dict = {
                    "coreSetting": creative_seed,
                    "coreSellingPoints": "",
                    "completeStoryline": {}
                }
        else:
            creative_work_dict = creative_seed

        # 更新进度：开始创意精炼
        try:
            if hasattr(self, '_update_task_status_callback'):
                task_id = getattr(self, '_current_task_id', None)
                if task_id and callable(self._update_task_status_callback):
                    self._update_task_status_callback(
                        task_id, 'generating', 5, None,
                        current_step='creative_refinement',
                        step_status={'creative_refinement': 'active'}
                    )
                    self.logger.info(f"[phase_one] 步骤状态更新: creative_refinement -> active")
        except Exception as e:
            self.logger.error(f"[phase_one] 步骤状态更新失败: creative_refinement, 错误: {e}")

        try:
            refined_creative_seed = self.refine_creative_work_for_ai(creative_work_dict, temp_title_for_filename)
            
            # 更新进度：创意精炼完成，开始同人检测
            try:
                if hasattr(self, '_update_task_status_callback'):
                    task_id = getattr(self, '_current_task_id', None)
                    if task_id and callable(self._update_task_status_callback):
                        self._update_task_status_callback(
                            task_id, 'generating', 10, None,
                            current_step='fanfiction_detection',
                            step_status={
                                'creative_refinement': 'completed',
                                'fanfiction_detection': 'active'
                            }
                        )
                        self.logger.info(f"[phase_one] 步骤状态更新: creative_refinement -> completed, fanfiction_detection -> active")
            except Exception as e:
                self.logger.error(f"[phase_one] 步骤状态更新失败: fanfiction_detection, 错误: {e}")

            # 预处理：检测同人小说并获取背景资料
            processed_creative_seed = self._preprocess_creative_seed(refined_creative_seed)
            
            # 更新进度：同人检测完成，开始生成多个方案
            try:
                if hasattr(self, '_update_task_status_callback'):
                    task_id = getattr(self, '_current_task_id', None)
                    if task_id and callable(self._update_task_status_callback):
                        self._update_task_status_callback(
                            task_id, 'generating', 15, None,
                            current_step='multiple_plans',
                            step_status={
                                'creative_refinement': 'completed',
                                'fanfiction_detection': 'completed',
                                'multiple_plans': 'active'
                            }
                        )
                        self.logger.info(f"[phase_one] 步骤状态更新: fanfiction_detection -> completed, multiple_plans -> active")
            except Exception as e:
                self.logger.error(f"[phase_one] 步骤状态更新失败: multiple_plans, 错误: {e}")
            
            # 第一步：生成和选择方案（🔥 传递平台参数）
            selected_plan = self.plan_generator.generate_and_select_plan(
                processed_creative_seed,
                self.content_generator,
                target_platform=self._ctx.get("target_platform", "fanqie")
            )
            if not selected_plan:
                error_msg = "方案生成失败：无法生成符合要求的创作方案"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False

            # 更新进度：方案生成完成
            try:
                if hasattr(self, '_update_task_status_callback'):
                    task_id = getattr(self, '_current_task_id', None)
                    if task_id and callable(self._update_task_status_callback):
                        self._update_task_status_callback(
                            task_id, 'generating', 30, None,
                            current_step='plan_selection',
                            step_status={
                                'creative_refinement': 'completed',
                                'fanfiction_detection': 'completed',
                                'multiple_plans': 'completed',
                                'freshness_assessment': 'completed',
                                'plan_selection': 'completed'
                            }
                        )
                        self.logger.info(f"[phase_one] 步骤状态更新: multiple_plans -> completed, plan_selection -> completed")
            except Exception as e:
                self.logger.error(f"[phase_one] 步骤状态更新失败: plan_selection, 错误: {e}")

            # 第二步：设置基础信息
            if not self._setup_novel_info(selected_plan, creative_seed, total_chapters):
                error_msg = "小说基础信息设置失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False

            # 现在有了所有必要信息，创建初始检查点（在第一个实际步骤之前）
            self.resume_manager.create_initial_checkpoint(creative_seed, total_chapters)

            # 第三步：执行第一阶段准备工作（委托给PhaseGenerator）
            return self.phase_generator.generate_phase_one_preparations()

        except Exception as e:
            error_msg = f"第一阶段生成发生异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            notify_failure(error_msg)
            return False

    def full_auto_generation(self, creative_seed, total_chapters: Optional[int] = None):
        """
        全自动生成完整小说 - 重构版本
        使用模块化的方式处理生成流程
        """
        print("[START] 开始全自动小说生成 (重构版本)...")
        
        # 重置API调用点数计数器
        self.reset_api_points_counter()
        
        # 不打印完整的创意种子，避免过长输出
        if isinstance(creative_seed, dict):
            novel_title = creative_seed.get('novelTitle') or creative_seed.get('novel_title')
            if novel_title:
                print(f"创意种子标题: {novel_title}")
            else:
                print(f"创意种子类型: {type(creative_seed).__name__}")
        else:
            print(f"创意种子类型: {type(creative_seed).__name__}")

        if total_chapters is None:
            total_chapters = self.config.get("defaults", {}).get("total_chapters", 200)
        temp_title_for_filename = f"未定稿创意_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if isinstance(creative_seed, str):
            try:
                # 尝试解析JSON字符串
                creative_work_dict = json.loads(creative_seed)
            except:
                # 如果解析失败，创建一个基础字典结构
                creative_work_dict = {
                    "coreSetting": creative_seed,
                    "coreSellingPoints": "",
                    "completeStoryline": {}
                }
        else:
            creative_work_dict = creative_seed

        refined_creative_seed = self.refine_creative_work_for_ai(creative_work_dict, temp_title_for_filename)

        try:
            # 预处理：检测同人小说并获取背景资料
            processed_creative_seed = self._preprocess_creative_seed(refined_creative_seed)
            
            # 第一步：生成和选择方案
            selected_plan = self.plan_generator.generate_and_select_plan(processed_creative_seed, self.content_generator)
            if not selected_plan:
                print("❌ 方案生成失败")
                return False

            # 第二步：设置基础信息
            if not self._setup_novel_info(selected_plan, creative_seed, total_chapters):
                return False

            # 第三步：生成完整小说（委托给PhaseGenerator）
            return self.phase_generator.generate_phase_one_preparations()

        except Exception as e:
            print(f"❌ 全自动生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _setup_novel_info(self, selected_plan: Dict, creative_seed, total_chapters: Optional[int]) -> bool:
        """设置小说基础信息"""
        try:
            self._ctx["selected_plan"] = selected_plan
            self.novel_title = selected_plan["title"]
            self._ctx["novel_title"] = self.novel_title
            self._ctx["novel_synopsis"] = selected_plan["synopsis"]
            self._ctx["creative_seed"] = creative_seed
            self._ctx["category"] = selected_plan.get('tags', {}).get('main_category', '未分类')
            self._ctx["current_progress"]["total_chapters"] = total_chapters
            self._ctx["current_progress"]["start_time"] = datetime.now().isoformat()
            
            # 🔥 同步更新 novel_data（PhaseGenerator 使用 novel_data）
            self.novel_data["novel_title"] = self.novel_title
            self.novel_data["novel_synopsis"] = selected_plan["synopsis"]
            self.novel_data["creative_seed"] = creative_seed
            self.novel_data["category"] = selected_plan.get('tags', {}).get('main_category', '未分类')
            self.novel_data["selected_plan"] = selected_plan
            if "current_progress" not in self.novel_data:
                self.novel_data["current_progress"] = {}
            self.novel_data["current_progress"]["total_chapters"] = total_chapters
            self.novel_data["current_progress"]["start_time"] = datetime.now().isoformat()

            # 现在有了 novel_title，初始化质量评估器（使用统一路径配置）
            from src.core.QualityAssessor import QualityAssessor
            username = getattr(self, '_username', None)
            self.quality_assessor = QualityAssessor(
                api_client=self.api_client,
                novel_title=self.novel_title,
                username=username
            )
            # 更新 content_generator 的 quality_assessor 引用
            self.content_generator.quality_assessor = self.quality_assessor

            # 初始化材料管理器
            self._initialize_material_manager()

            print(f"✅ 小说信息设置完成: 《{selected_plan['title']}》")
            print(f"✅ 质量评估器已初始化，使用统一路径配置")
            return True

        except Exception as e:
            print(f"❌ 设置小说信息失败: {e}")
            return False

    def _generate_complete_novel(self) -> bool:
        """生成完整小说"""
        try:
            print("开始生成完整小说...")
            
            # 第一阶段：基础规划
            print("🔄 开始第一阶段：基础规划...")
            if not self._generate_foundation_planning():
                print("❌ 第一阶段失败")
                return False
            print("✅ 第一阶段完成")
            
            # 第二阶段：世界观与角色设计
            print("🔄 开始第二阶段：世界观与角色设计...")
            if not self._generate_worldview_and_characters():
                print("❌ 第二阶段失败")
                return False
            print("✅ 第二阶段完成")
            
            # 第三阶段：全书规划
            if not self._generate_overall_planning():
                return False
            
            # 第四阶段：内容生成准备
            if not self._prepare_content_generation():
                return False
            
            # 第五阶段：章节内容生成
            total_chapters = self._ctx["current_progress"]["total_chapters"]
            return self._generate_all_chapters(total_chapters)

        except Exception as e:
            print(f"❌ 小说生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ==================== 事件处理器 ====================

    def _on_chapter_generated(self, data):
        """处理章节生成完成事件"""
        chapter_number = data.get('chapter_number')
        result = data.get('result')
        print(f"✅ 第{chapter_number}章生成完成: {result.get('chapter_title', '未知标题')}")
        
        # 更新novel_data
        if chapter_number and result:
            self._ctx.setdefault("generated_chapters", {})[chapter_number] = result
            self._ctx["current_progress"]["completed_chapters"] = len(self._ctx["generated_chapters"])
            
            # 保存章节（传递用户名确保用户隔离）
            username = getattr(self, '_username', None)
            self.project_manager.save_single_chapter(
                self._ctx["novel_title"], 
                chapter_number, 
                result,
                username=username
            )

    def _on_chapter_assessed(self, data):
        """处理章节评估完成事件"""
        chapter_number = data.get('chapter_number')
        assessment = data.get('assessment')
        print(f"📊 第{chapter_number}章质量评估完成: {assessment.get('overall_score', 0):.1f}分")

    def _on_error_occurred(self, data):
        """处理错误事件"""
        error_type = data.get('type')
        chapter = data.get('chapter', '未知')
        message = data.get('message') or data.get('error', '未知错误')
        print(f"❌ 错误({error_type}) 第{chapter}章: {message}")
        
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
        self.logger.info("⚙️  正在执行【指令精炼】，将人类创意转换为AI必须遵守的硬性指令...")
        
        # 🔥 更新步骤状态为进行中（黄色）- 步骤1: 创意精炼
        self._update_step_status('creative_refinement', 'active', '正在调用AI进行创意精炼...')
        
        # 1. 提取核心组件
        core_setting = creative_work.get("coreSetting", "未提供核心设定。")
        core_selling_points = creative_work.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_work.get("completeStoryline", {})
        
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
        
        refined_instruction = None
        try:
            # 3. 调用AI进行真正的精炼
            self.logger.info("  🤖 正在调用AI进行创意精炼...")
            
            if not hasattr(self.api_client, 'call_api'):
                print("  ❌ API客户端缺少call_api方法，尝试使用generate_content_with_retry")
                if hasattr(self.api_client, 'generate_content_with_retry'):
                    # 🔥 在调用前检查停止标志
                    self._check_stop_requested("创意精炼(API备用路径)前")
                    refined_instruction = self.api_client.generate_content_with_retry(
                        "refine_creative_work_for_ai",
                        refinement_prompt,
                        purpose="创意精炼为AI指令"
                    )
                    # 🔥 调用后也检查
                    self._check_stop_requested("创意精炼(API备用路径)后")
                else:
                    print("  ❌ API客户端没有可用的调用方法")
            else:
                refined_instruction = self._call_api_with_stop_check(
                    "refine_creative_work_for_ai",
                    refinement_prompt,
                    0.7,  # 适度创造性
                    purpose="创意精炼为AI指令",
                    context="创意精炼阶段"
                )
            
            if not refined_instruction or not isinstance(refined_instruction, str):
                print("  ⚠️ AI精炼失败或返回无效结果，使用基础模板")
                refined_instruction = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
            else:
                print("  ✅ AI精炼成功")
            
            # 4. 保存到文件（使用用户隔离路径）
            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                
                # 🔥 使用用户隔离路径（优先使用已设置的用户名）
                try:
                    from web.utils.path_utils import get_user_novel_dir
                    username = getattr(self, '_username', None)
                    output_dir = get_user_novel_dir(username=username, create=True)
                except Exception as e:
                    # 如果失败，使用默认路径
                    self.logger.warning(f"获取用户隔离路径失败: {e}，使用默认路径")
                    output_dir = Path("小说项目")
                    output_dir.mkdir(exist_ok=True)
                
                output_filepath = os.path.join(output_dir, f"{safe_title}_Refined_AI_Brief.txt")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(refined_instruction)
                
                self.logger.info(f"✅  指令精炼完成，已保存至: {output_filepath}")
                
                # 🔥 更新步骤状态为已完成（绿色）- 步骤1: 创意精炼
                self._update_step_status('creative_refinement', 'completed', '创意精炼完成')
                    
            except Exception as e:
                print(f"⚠️  保存精炼指令文件失败: {e}")
                import traceback
                traceback.print_exc()
                
            return refined_instruction
            
        except Exception as e:
            print(f"❌ AI精炼过程出错: {e}")
            # 🔥 更新步骤状态为失败（红色）- 步骤1: 创意精炼
            self._update_step_status('creative_refinement', 'failed', f'AI精炼失败: {str(e)[:50]}')
            import traceback
            traceback.print_exc()
            print("  🔄 降级到基础模板")
            # 降级到基础模板
            try:
                fallback_result = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
                return fallback_result
            except Exception as fallback_error:
                print(f"❌ 基础模板生成也失败: {fallback_error}")
                # 返回一个最基本的指令
                return f"# AI创作指令\n\n请基于以下创意进行创作：\n核心设定：{core_setting}\n核心卖点：{core_selling_points}"

    # ==================== 预处理方法 ====================
    def _build_basic_instruction_template(self, core_setting: str, core_selling_points: str, storyline: dict) -> str:
        """构建基础指令模板（降级方案）"""
        print("  🛠️ 使用基础指令模板...")
        
        instructions = []
        instructions.append("# AI创作最高指令：创作大纲与绝对约束")
        instructions.append("你是一位顶级的小说策划AI。以下内容是你本次创作的【唯一真相来源】和【绝对行为准则】。你必须严格、完整、精确地遵循所有指令，任何偏离或遗漏都将被视为任务失败。")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第一部分：世界观与不可逾越的边界")
        instructions.append(f"\n**核心设定：**\n{core_setting}")
        
        # 自动生成否定约束
        negative_constraints = []
        if "凡人" in core_setting and "落云宗" in core_setting:
            negative_constraints.append("**绝对禁止**：故事时间线在韩立从乱星海回归之后，因此**严禁**让主角前往乱星海、参与虚天殿夺宝等已发生的剧情。主角在结婴前的活动范围**必须**锁定在天南大陆。")
        else:
            negative_constraints.append("**绝对禁止**：你的一切情节设计都不能超出上述【核心设定】所定义的范围。不要引入设定之外的时间段、地点或世界背景。")
        
        instructions.append("\n**绝对禁止事项：**")
        instructions.extend([f"- {constraint}" for constraint in negative_constraints])
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第二部分：核心卖点与执行纲领")
        instructions.append("你的所有情节设计，都必须以服务和凸显以下核心卖点为首要目标：")
        instructions.append(f"\n{core_selling_points}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第三部分：分阶段故事线框架")
        instructions.append("你必须严格按照以下阶段的设定来构建故事的起承转合。")
        
        if storyline:
            for stage_key, stage_data in storyline.items():
                stage_name = stage_data.get('stageName', '未知阶段')
                summary = stage_data.get('summary', '无')
                arc_goal = stage_data.get('arc_goal', '无')
                
                instructions.append(f"\n### {stage_name}")
                instructions.append(f"- **情节概要：** {summary}")
                instructions.append(f"- **强制目标：** {arc_goal}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 最终指令确认")
        instructions.append("以上所有内容是不可违背的创作铁律。现在，请基于这份【最高指令】，开始你的工作。")
        
        return "\n".join(instructions)
    
    def _preprocess_creative_seed(self, creative_seed):
        """
        预处理创意种子，检测同人小说并获取背景资料
        
        Args:
            creative_seed: 原始创意种子
            
        Returns:
            处理后的创意种子（包含背景资料信息）
        """
        print("🔍 预处理创意种子：检测同人小说并获取背景资料...")
        
        # 如果是字符串，转换为字典格式
        if isinstance(creative_seed, str):
            try:
                creative_work = json.loads(creative_seed)
            except:
                creative_work = {"coreSetting": creative_seed, "coreSellingPoints": "", "completeStoryline": {}}
        else:
            creative_work = creative_seed
        
        # 检测是否为同人小说
        is_fanfiction, work_name = self.fanfiction_detector.detect_fanfiction(creative_work)
        
        if not is_fanfiction:
            print("    ✅ 检测为原创作品，无需背景资料")
            return creative_seed
        
        print(f"    ✅ 检测为同人小说：《{work_name}》")
        
        # 获取背景资料并进行可信度验证（ImprovedFanfictionDetector内部使用ImprovedContentVerifier）
        background_info = self.fanfiction_detector.get_original_work_background(
            work_name,
            creative_work
        )
        
        if background_info:
            # 检查验证结果
            verification_result = background_info.get("verification_result")
            if verification_result:
                if verification_result["is_credible"]:
                    print(f"    ✅ 背景资料可信度验证通过 (置信度: {verification_result['confidence_score']:.2f})")
                else:
                    print(f"    ⚠️ 背景资料可信度验证未通过 (置信度: {verification_result['confidence_score']:.2f})")
                    print(f"    📊 等级: {verification_result['credibility_level']}")
                    if verification_result["issues_found"]:
                        print(f"    ❌ 发现问题: {len(verification_result['issues_found'])}个")
                        for issue in verification_result["issues_found"][:3]:  # 只显示前3个问题
                            print(f"       - {issue}")
            
            # 将背景资料添加到创意种子中
            creative_work["original_work_background"] = background_info
            creative_work["is_fanfiction"] = True
            creative_work["original_work_name"] = work_name
            
            print(f"    ✅ 背景资料已整合到创意种子中")
            
            # 返回更新后的创意种子（转换为JSON字符串格式）
            return json.dumps(creative_work, ensure_ascii=False)
        else:
            print(f"    ⚠️ 无法获取《{work_name}》的背景资料，使用原始创意种子")
            return creative_seed

    # ==================== 辅助方法 ====================

    def _initialize_material_manager(self):
        """初始化材料管理器"""
        try:
            novel_title = self._ctx.get("novel_title")
            if novel_title:
                # 🔥 传递用户名用于用户隔离路径
                username = getattr(self, '_username', None)
                self.material_manager = MaterialManager(novel_title, username=username)
                print(f"✅ 材料管理器初始化成功: {novel_title} (用户: {username})")
                
                # 保存项目信息到材料管理器
                self._save_project_info_to_materials()
            else:
                print("⚠️ 小说标题未确定，延迟初始化材料管理器")
        except Exception as e:
            print(f"❌ 材料管理器初始化失败: {e}")
            self.material_manager = None

    def _save_project_info_to_materials(self):
        """保存项目基础信息到材料管理器"""
        if not self.material_manager:
            return
            
        try:
            project_info = {
                "novel_title": self._ctx.get("novel_title"),
                "category": self._ctx.get("category"),
                "synopsis": self._ctx.get("novel_synopsis"),
                "creative_seed": self._ctx.get("creative_seed"),
                "selected_plan": self._ctx.get("selected_plan"),
                "total_chapters": self._ctx.get("current_progress", {}).get("total_chapters", 0),
                "start_time": self._ctx.get("current_progress", {}).get("start_time"),
                "generation_config": self.config,
                "created_time": datetime.now().isoformat()
            }
            
            result = self.material_manager.create_material("项目信息", project_info)
            if result.get("success"):
                print("✅ 项目信息已保存到材料管理器")
            else:
                print(f"⚠️ 项目信息保存失败: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ 保存项目信息到材料管理器失败: {e}")

    def signal_handler(self, signum, frame):
        """处理中断信号 - 需要按两次 Ctrl+C 才会退出"""
        import time
        import os
        current_time = time.time()
        
        # 🔥 Windows 兼容：使用环境变量存储计数器（避免实例变量被重置）
        count_key = '_NOVEL_GENERATOR_SIGINT_COUNT'
        time_key = '_NOVEL_GENERATOR_SIGINT_TIME'
        
        # 获取当前计数
        try:
            count = int(os.environ.get(count_key, '0'))
            last_time = float(os.environ.get(time_key, '0'))
        except:
            count = 0
            last_time = 0
        
        # 如果超过 3 秒，重置计数器
        if current_time - last_time > 3:
            count = 0
        
        count += 1
        os.environ[count_key] = str(count)
        os.environ[time_key] = str(current_time)
        
        print(f"\n\n{'='*60}")
        print(f"⚠️  收到中断信号 (Ctrl+C) - 第 {count} 次")
        print(f"{'='*60}")
        
        if count == 1:
            print("📝 正在保存进度...")
            try:
                # 🔥 确保用户名被传递到 _ctx
                if hasattr(self, '_username') and self._username:
                    self._ctx['_username'] = self._username
                self.project_manager.save_project_progress(self._ctx)
                print("✅ 进度已保存")
            except Exception as e:
                print(f"⚠️ 保存进度失败: {e}")
            print("\n💡 提示：3 秒内再按一次 Ctrl+C 才会退出")
            print("      不按则继续生成...\n")
            # 🔥 关键：不退出，让程序继续运行
            return
        else:
            print("🚪 收到第二次中断信号，正在退出...")
            sys.exit(0)

    # ==================== 兼容性方法 ====================
    # 为了保持向后兼容，保留一些常用的方法签名

    def load_project_data(self, filename: str) -> bool:
        """加载项目数据（兼容性方法）"""
        try:
            data = self.project_manager.load_project(filename)
            if not data:
                return False
                
            self._ctx = data
            print(f"✅ 项目数据加载完成: {self._ctx.get('novel_title', '未知标题')}")
            return True
            
        except Exception as e:
            print(f"❌ 加载项目数据失败: {e}")
            return False

    def resume_generation(self, total_chapters: int = 200) -> bool:
        """继续生成小说（兼容性方法）"""
        print("继续生成小说...")
        
        # 检查是否有续写数据
        if not self._ctx.get("is_resuming"):
            print("❌ 没有续写数据，无法执行续写")
            return False
        
        resume_data = self._ctx.get("resume_data", {})
        from_chapter = resume_data.get("from_chapter", 1)
        additional_chapters = resume_data.get("additional_chapters", 10)
        
        print(f"从第{from_chapter}章开始续写{additional_chapters}章")
        
        try:
            # 执行续写生成
            end_chapter = from_chapter + additional_chapters - 1
            return self.generate_chapters_batch(from_chapter, end_chapter)
            
        except Exception as e:
            print(f"❌ 续写生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """
        批量生成章节
        
        优化：使用中型事件批量生成，减少API调用次数
        """
        print(f"\n🚀 启动批量生成优化模式（第{start_chapter}-{end_chapter}章）")
        
        # 尝试导入批量生成模块
        try:
            from src.core.batch_generation import MediumEventBatchProcessor
            batch_processor = MediumEventBatchProcessor(self.api_client, self)
            use_batch_mode = True
            print("✅ 批量生成模块加载成功")
        except Exception as e:
            print(f"⚠️ 批量生成模块加载失败，回退到逐章生成: {e}")
            use_batch_mode = False
        
        # 如果使用批量生成，先初始化事件系统
        if use_batch_mode:
            # 确保事件系统已初始化（这样才能获取中型事件）
            if hasattr(self, 'event_driven_manager') and self.event_driven_manager:
                print("   🔄 初始化事件系统...")
                try:
                    self.event_driven_manager.initialize_event_system()
                    print("   ✅ 事件系统初始化完成")
                except Exception as e:
                    print(f"   ⚠️ 事件系统初始化失败: {e}")
            
            return self._generate_chapters_by_medium_event(
                start_chapter, end_chapter, batch_processor
            )
        else:
            # 回退到逐章生成
            return self._generate_chapters_one_by_one(start_chapter, end_chapter)
    
    def _generate_chapters_by_medium_event(
        self, 
        start_chapter: int, 
        end_chapter: int,
        batch_processor
    ) -> bool:
        """
        按中型事件批量生成章节
        
        这是优化后的生成方式，可以节省50-60%的API调用
        """
        print(f"\n📦 按中型事件批量生成（第{start_chapter}-{end_chapter}章）")
        
        # 获取中型事件列表
        medium_events = self._get_medium_events_in_range(start_chapter, end_chapter)
        
        if not medium_events:
            print("⚠️ 未找到中型事件信息，回退到逐章生成")
            return self._generate_chapters_one_by_one(start_chapter, end_chapter)
        
        print(f"📋 找到 {len(medium_events)} 个中型事件")
        
        # 准备novel_data
        novel_data = {
            'novel_title': self._ctx.get('novel_title', 'Unknown'),
            'novel_synopsis': self._ctx.get('novel_synopsis', ''),
            'username': getattr(self, '_username', None),
            'creative_seed': self._ctx.get('creative_seed', {}),
            'selected_plan': self._ctx.get('selected_plan', {}),
            'stage_writing_plans': self._ctx.get('stage_writing_plans', {}),
            'overall_stage_plans': self._ctx.get('overall_stage_plans', {}),
            'core_worldview': self._ctx.get('core_worldview', {}),
            'character_design': self._ctx.get('character_design', {}),
            'writing_style_guide': self._ctx.get('writing_style_guide', {}),
            # 🔥 新增：字数阈值参数
            'min_word_threshold': self._ctx.get('min_word_threshold', 1500),
            'max_word_threshold': self._ctx.get('max_word_threshold', 3500)
        }
        
        # 🔥 修复：检测黄金三章范围（第1-3章），合并所有相关事件信息整体生成
        golden_chapters_range = None
        golden_event = None
        if start_chapter <= 1 and end_chapter >= 3:
            # 找到第1-3章的所有事件
            golden_events = [e for e in medium_events 
                           if self._parse_chapter_range(e.get('chapter_range', ''))[0] in [1, 2, 3]]
            if golden_events:
                golden_chapters_range = (1, min(3, end_chapter))
                print(f"\n✨ 检测到黄金三章范围，将整体生成第1-{golden_chapters_range[1]}章")
                print(f"   涉及事件: {', '.join(e.get('name', 'Unknown') for e in golden_events)}")
                
                # 🔥 关键修复：合并所有黄金三章事件的信息
                golden_event = {
                    "name": "开局黄金三章（整体）",
                    "type": "golden_opening",
                    "chapter_range": "1-3",
                    "main_goal": "完整呈现开局阶段：从诡异降临到初步破局",
                    "description": "合并第1-3章所有事件的整体描述",
                    "plot_outline": [],
                    "emotional_arc": "从危机降临→冷静应对→初步破局",
                    "composition": {}
                }
                
                # 合并所有事件的情节大纲和场景规划
                for i, event in enumerate(golden_events):
                    event_name = event.get('name', f'事件{i+1}')
                    event_range = event.get('chapter_range', '')
                    print(f"   📦 合并事件: {event_name} ({event_range})")
                    
                    # 合并plot_outline
                    if event.get('plot_outline'):
                        golden_event['plot_outline'].extend(event['plot_outline'])
                    
                    # 合并composition中的场景
                    if event.get('composition'):
                        golden_event['composition'].update(event['composition'])
                    elif event.get('plot_outline'):
                        # 如果没有composition，用plot_outline构建
                        phase_key = ['起', '承', '转', '合'][i] if i < 4 else f'第{i+1}部分'
                        golden_event['composition'][phase_key] = event['plot_outline']
        
        # 如果有黄金三章，先整体生成
        if golden_chapters_range and golden_event:
            print(f"\n🎯 [黄金三章] 整体生成第1-{golden_chapters_range[1]}章")
            print(f"   📋 合并后情节大纲: {len(golden_event.get('plot_outline', []))} 个要点")
            try:
                result = batch_processor.process_medium_event(
                    medium_event=golden_event,
                    chapter_range=golden_chapters_range,
                    novel_data=novel_data,
                    skip_assessment=False
                )
                
                if result.success:
                    print(f"   ✅ 黄金三章整体生成成功: {len(result.chapters)}章")
                    print(f"   💰 创造点消耗: {result.points_consumed}点，节省: {result.points_saved}点")
                    
                    # 保存生成的章节
                    for ch_num, chapter_content in result.chapters.items():
                        chapter_result = {
                            'chapter_number': ch_num,
                            'chapter_title': chapter_content.title,
                            'content': chapter_content.content,
                            'word_count': len(chapter_content.content),
                            'key_events': chapter_content.key_events,
                            'character_states': chapter_content.character_states
                        }
                        
                        self.event_bus.publish('chapter.generated', {
                            'chapter_number': ch_num,
                            'result': chapter_result
                        })
                        
                        if hasattr(self, '_phase_two_progress_callback') and callable(self._phase_two_progress_callback):
                            chapter_data = {
                                "status": "completed",
                                "chapter_title": chapter_content.title,
                                "word_count": len(chapter_content.content)
                            }
                            self._phase_two_progress_callback(ch_num, "completed", chapter_data)
                    
                    # 累加章节计数
                    current_generated = self._ctx['current_progress'].get('chapters_generated', 0)
                    self._ctx['current_progress']['chapters_generated'] = current_generated + len(result.chapters)
                else:
                    print(f"   ❌ 黄金三章整体生成失败: {result.error}")
                    # 回退到逐章生成黄金三章
                    for ch_num in range(1, golden_chapters_range[1] + 1):
                        self._generate_single_chapter(ch_num)
                        # 累加计数
                        current_generated = self._ctx['current_progress'].get('chapters_generated', 0)
                        self._ctx['current_progress']['chapters_generated'] = current_generated + 1
            except Exception as e:
                print(f"   ❌ 黄金三章处理异常: {e}")
                import traceback
                traceback.print_exc()
            
            # 从列表中移除已处理的黄金三章事件
            medium_events = [e for e in medium_events 
                           if self._parse_chapter_range(e.get('chapter_range', ''))[0] > 3]
            print(f"   📋 剩余 {len(medium_events)} 个中型事件待处理")
        
        # 如果没有中型事件但需要生成更多章节，使用逐章生成
        if not medium_events and end_chapter > 3:
            print(f"\n⚠️ 没有中型事件信息，但还需生成第4-{end_chapter}章")
            print(f"   🔄 回退到逐章生成模式...")
            for ch_num in range(max(4, start_chapter), end_chapter + 1):
                print(f"\n📖 逐章生成第{ch_num}章...")
                if not self._generate_single_chapter(ch_num):
                    print(f"   ❌ 第{ch_num}章生成失败")
                    return False
                # 累加计数
                current_generated = self._ctx['current_progress'].get('chapters_generated', 0)
                self._ctx['current_progress']['chapters_generated'] = current_generated + 1
            return True
        
        # 按中型事件批量生成剩余章节
        print(f"\n🚀 开始处理剩余 {len(medium_events)} 个中型事件...")
        generated_chapter_numbers = set()
        for i, medium_event in enumerate(medium_events, 1):
            event_name = medium_event.get('name', f'事件{i}')
            chapter_range = medium_event.get('chapter_range', '')
            
            print(f"\n🎯 [{i}/{len(medium_events)}] 处理中型事件: {event_name}")
            print(f"   章节范围: {chapter_range}")
            
            try:
                # 解析章节范围
                start_ch, end_ch = self._parse_chapter_range(chapter_range)
                
                # 限制在要生成的范围内
                start_ch = max(start_ch, start_chapter)
                end_ch = min(end_ch, end_chapter)
                
                if start_ch > end_ch:
                    continue
                
                # 调用批量生成
                result = batch_processor.process_medium_event(
                    medium_event=medium_event,
                    chapter_range=(start_ch, end_ch),
                    novel_data=novel_data,
                    skip_assessment=False
                )
                
                if result.success:
                    print(f"   ✅ 批量生成成功: {len(result.chapters)}章")
                    print(f"   💰 创造点消耗: {result.points_consumed}点，节省: {result.points_saved}点")
                    
                    # 保存生成的章节
                    for ch_num, chapter_content in result.chapters.items():
                        # 转换格式并保存
                        chapter_result = {
                            'chapter_number': ch_num,
                            'chapter_title': chapter_content.title,
                            'content': chapter_content.content,
                            'word_count': len(chapter_content.content),
                            'key_events': chapter_content.key_events,
                            'character_states': chapter_content.character_states
                        }
                        
                        # 发布事件
                        self.event_bus.publish('chapter.generated', {
                            'chapter_number': ch_num,
                            'result': chapter_result
                        })
                        
                        # 进度回调
                        if hasattr(self, '_phase_two_progress_callback') and callable(self._phase_two_progress_callback):
                            chapter_data = {
                                "status": "completed",
                                "chapter_title": chapter_content.title,
                                "word_count": len(chapter_content.content)
                            }
                            self._phase_two_progress_callback(ch_num, "completed", chapter_data)
                    
                    # 更新统计（累加）
                    current_generated = self._ctx['current_progress'].get('chapters_generated', 0)
                    self._ctx['current_progress']['chapters_generated'] = current_generated + len(result.chapters)
                    
                else:
                    print(f"   ❌ 批量生成失败: {result.error}")
                    # 回退到逐章生成这个事件
                    print(f"   🔄 回退到逐章生成...")
                    for ch_num in range(start_ch, end_ch + 1):
                        self._generate_single_chapter(ch_num)
                        # 累加计数
                        current_generated = self._ctx['current_progress'].get('chapters_generated', 0)
                        self._ctx['current_progress']['chapters_generated'] = current_generated + 1
                        
            except Exception as e:
                print(f"   ❌ 处理中型事件时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return True
    
    def _generate_chapters_one_by_one(self, start_chapter: int, end_chapter: int) -> bool:
        """逐章生成（原始方式）"""
        print(f"\n📖 逐章生成模式（第{start_chapter}-{end_chapter}章）")
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            if not self._generate_single_chapter(chapter_num):
                return False
        
        return True
    
    def _generate_single_chapter(self, chapter_num: int) -> bool:
        """生成单个章节"""
        try:
            print(f"\n📖 开始生成第{chapter_num}章...")
            
            # 进度回调
            if hasattr(self, '_phase_two_progress_callback') and callable(self._phase_two_progress_callback):
                self._phase_two_progress_callback(chapter_num, "generating")
            
            # 准备上下文
            context = self._prepare_generation_context(chapter_num)
            if context is None:
                print(f"❌ 第{chapter_num}章生成上下文为None")
                return False
            
            # 生成内容
            chapter_result = self.content_generator.generate_chapter_content_for_novel(
                chapter_num, self._ctx, context
            )
            
            if not chapter_result:
                print(f"❌ 第{chapter_num}章内容生成失败")
                return False
            
            # 发布事件
            self.event_bus.publish('chapter.generated', {
                'chapter_number': chapter_num,
                'result': chapter_result,
                'context': context
            })
            
            # 进度回调
            if hasattr(self, '_phase_two_progress_callback') and callable(self._phase_two_progress_callback):
                chapter_data = {
                    "status": "completed",
                    "chapter_title": chapter_result.get('chapter_title', f"第{chapter_num}章"),
                    "word_count": chapter_result.get('word_count', len(chapter_result.get('content', '')))
                }
                self._phase_two_progress_callback(chapter_num, "completed", chapter_data)
            
            print(f"✅ 第{chapter_num}章生成完成")
            return True
            
        except Exception as e:
            print(f"❌ 生成第{chapter_num}章时出错: {e}")
            return False
    
    def _get_medium_events_in_range(self, start_ch: int, end_ch: int) -> List[Dict]:
        """获取指定章节范围内的中型事件"""
        medium_events = []
        
        try:
            # 优先从event_driven_manager获取事件
            if hasattr(self, 'event_driven_manager') and self.event_driven_manager:
                print(f"   🔍 从EventDrivenManager获取中型事件...")
                
                # 获取所有活跃的中型事件 (active_events是字典)
                active_events_dict = getattr(self.event_driven_manager, 'active_events', {})
                
                for event_name, event in active_events_dict.items():
                    # 类型检查：确保 event 是字典
                    if not isinstance(event, dict):
                        print(f"      ⚠️ 跳过非字典事件: {event_name} = {event} (类型: {type(event)})")
                        continue
                    
                    if event.get('type') == 'medium_event':
                        event_range = event.get('chapter_range', '')
                        if not event_range:
                            # 如果没有chapter_range，使用start/end_chapter
                            start = event.get('start_chapter', 0)
                            end = event.get('end_chapter', 0)
                            event_range = f"{start}-{end}"
                            event['chapter_range'] = event_range
                        
                        event_start, event_end = self._parse_chapter_range(event_range)
                        
                        # 检查是否与要生成的范围重叠
                        if event_start <= end_ch and event_end >= start_ch:
                            medium_events.append(event)
                            print(f"      ✅ 找到中型事件: {event.get('name', 'Unknown')} ({event_range})")
                
                if medium_events:
                    print(f"   📋 从EventDrivenManager找到 {len(medium_events)} 个中型事件")
            
            # 如果从EventDrivenManager没有找到，尝试从stage_writing_plans获取
            if not medium_events:
                print(f"   🔍 从stage_writing_plans获取中型事件...")
                stage_plans = self._ctx.get('stage_writing_plans', {})
                
                for stage_name, plan in stage_plans.items():
                    event_system = plan.get('event_system', {})
                    
                    # 遍历重大事件
                    for major_event in event_system.get('major_events', []):
                        # 遍历中型事件
                        for phase, events in major_event.get('composition', {}).items():
                            # 类型检查：确保 events 是列表
                            if not isinstance(events, list):
                                print(f"      ⚠️ composition['{phase}'] 不是列表: {type(events)}")
                                continue
                            for event in events:
                                # 类型检查：确保 event 是字典
                                if not isinstance(event, dict):
                                    print(f"      ⚠️ 跳过非字典事件项: {event} (类型: {type(event)})")
                                    continue
                                event_range = event.get('chapter_range', '')
                                event_start, event_end = self._parse_chapter_range(event_range)
                                
                                # 检查是否与要生成的范围重叠
                                if event_start <= end_ch and event_end >= start_ch:
                                    event['type'] = 'medium'  # 确保类型标记
                                    medium_events.append(event)
            
            # 按章节范围排序
            medium_events.sort(key=lambda e: self._parse_chapter_range(e.get('chapter_range', '0-0'))[0])
            
            print(f"   📊 总共找到 {len(medium_events)} 个中型事件")
            
        except Exception as e:
            print(f"⚠️ 获取中型事件时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return medium_events
    
    def _parse_chapter_range(self, chapter_range: str) -> tuple:
        """解析章节范围字符串"""
        try:
            if '-' in chapter_range:
                parts = chapter_range.split('-')
                start = int(parts[0])
                end = int(parts[1])
            else:
                start = end = int(chapter_range)
            return (start, end)
        except:
            return (0, 0)

    def _prepare_generation_context(self, chapter_num: int):
        """准备生成上下文"""
        try:
            print(f"🔍 开始准备第{chapter_num}章生成上下文...")
            
            # 初始化所有上下文变量
            event_context = {}
            foreshadowing_context = {}
            growth_context = {}
            stage_plan = {}
            
            # 获取各个管理器的上下文
            print(f"  📊 获取事件上下文...")
            if hasattr(self, 'event_driven_manager') and hasattr(self.event_driven_manager, 'get_context'):
                try:
                    event_context = self.event_driven_manager.get_context(chapter_num)
                    print(f"    ✅ 事件上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取事件上下文失败: {e}")
                    event_context = {}
            
            print(f"  🎭 获取期待感上下文...")
            if hasattr(self, 'expectation_manager') and hasattr(self.expectation_manager, 'pre_generation_check'):
                try:
                    # 使用期待感管理器的预生成检查
                    expectation_constraints = self.expectation_manager.pre_generation_check(
                        chapter_num,
                        event_context
                    )
                    foreshadowing_context = {
                        "expectation_constraints": expectation_constraints,
                        "active_expectations": len([
                            e for e in self.expectation_manager.expectations.values()
                            if e.status.value in ["planted", "fermenting"]
                        ])
                    }
                    print(f"    ✅ 期待感上下文获取成功: {len(expectation_constraints)}个约束")
                except Exception as e:
                    print(f"    ⚠️ 获取期待感上下文失败: {e}")
                    foreshadowing_context = {}
            
            print(f"  📈 获取成长规划上下文...")
            if hasattr(self, 'global_growth_planner') and hasattr(self.global_growth_planner, 'get_context'):
                try:
                    growth_context = self.global_growth_planner.get_context(chapter_num)
                    print(f"    ✅ 成长规划上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取成长规划上下文失败: {e}")
                    growth_context = {}
            
            print(f"  🎯 获取阶段计划...")
            if hasattr(self, 'stage_plan_manager'):
                try:
                    stage_plan = self.stage_plan_manager.get_stage_plan_for_chapter(chapter_num) or {}
                    print(f"    ✅ 阶段计划获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取阶段计划失败: {e}")
                    stage_plan = {}
            
            # 检查novel_data
            print(f"  📚 检查novel_data...")
            if not hasattr(self, 'novel_data') or not self._ctx:
                print(f"    ⚠️ novel_data不存在或为空，创建基础结构")
                self._initialize_data_structures()
            
            # 检查current_progress键是否存在
            if "current_progress" not in self._ctx or not self._ctx["current_progress"]:
                print(f"    ⚠️ current_progress不存在或为空，重新初始化数据结构")
                self._initialize_data_structures()
            
            # 使用安全的字典访问方式，提供默认值
            total_chapters = self._ctx.get("current_progress", {}).get("total_chapters", 30)
            print(f"    ✅ novel_data存在, 总章节数: {total_chapters}")
            
            context = GenerationContext(
                chapter_number=chapter_num,
                total_chapters=total_chapters,
                novel_data=self._ctx,
                stage_plan=stage_plan,
                event_context=event_context,
                foreshadowing_context=foreshadowing_context,
                growth_context=growth_context
            )
            
            print(f"  ✅ 第{chapter_num}章上下文准备完成")
            
            return context
            
        except Exception as e:
            print(f"❌ 准备生成上下文失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回基础上下文，确保不会返回None
            print(f"🔄 返回基础上下文作为备选...")
            try:
                base_context = GenerationContext(
                    chapter_number=chapter_num,
                    total_chapters=self._ctx.get("current_progress", {}).get("total_chapters", 30) if hasattr(self, '_ctx') and self._ctx else 30,
                    novel_data=self._ctx if hasattr(self, '_ctx') else {},
                    stage_plan={},
                    event_context={},
                    foreshadowing_context={},
                    growth_context={}
                )
                # generator引用在重构版本中不是必需的
                return base_context
            except Exception as base_error:
                print(f"❌ 创建基础上下文也失败: {base_error}")
                return None

    def choose_category(self):
        """让用户选择小说分类（兼容性方法）"""
        categories = [
            "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武",
            "悬疑灵异", "悬疑脑洞", "抗战谍战", "历史古代", "历史脑洞",
            "都市种田", "都市脑洞", "都市日常", "玄幻脑洞", "战神赘婿",
            "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
        ]
        
        print("\n📚 请选择小说分类:")
        for i, category in enumerate(categories, 1):
            print(f"  {i:2d}. {category}")
        
        # 简化版本，直接返回第一个分类
        selected_category = categories[0]
        self._ctx["category"] = selected_category
        print(f"  ✓ 已选择分类: {selected_category}")
        return selected_category

    # ==================== 完整的生成流程方法 ====================

    def _generate_foundation_planning(self) -> bool:
        """生成基础规划"""
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划")
        print("="*60)
        
        # 生成写作风格指南
        self._ctx["current_progress"]["stage"] = "写作风格制定"
        if not self._generate_writing_style_guide():
            print("⚠️ 写作风格指南生成失败，使用默认风格")
        
        # 市场分析
        self._ctx["current_progress"]["stage"] = "市场分析"
        if not self._generate_market_analysis():
            return False
        
        return True

    def _generate_worldview_and_characters(self) -> bool:
        """生成世界观、势力和角色设计"""
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与势力系统设计")
        print("="*60)
        
        # 世界观构建
        print("🔄 开始构建世界观...")
        self._ctx["current_progress"]["stage"] = "世界观构建"
        if not self._generate_worldview():
            print("❌ 世界观构建失败")
            return False
        print("✅ 世界观构建完成")
        
        # 【新增】势力/阵营系统构建
        print("=== 步骤3.5: 构建势力/阵营系统 ===")
        self._ctx["current_progress"]["stage"] = "势力系统设计"
        
        # 🔥 更新步骤状态为进行中（黄色）
        self._update_step_status('faction_system', 'active', '正在构建势力/阵营系统...')
        
        faction_system = self.content_generator.generate_faction_system(
            novel_title=self._ctx["novel_title"],
            core_worldview=self._ctx.get("core_worldview", {}),
            selected_plan=self._ctx["selected_plan"],
            market_analysis=self._ctx.get("market_analysis", {})
        )
        
        if faction_system:
            self._ctx["faction_system"] = faction_system
            print("✅ 势力/阵营系统构建完成")
            # 🔥 更新步骤状态为已完成（绿色）
            self._update_step_status('faction_system', 'completed', '势力/阵营系统构建完成')
            # 保存到材料管理器
            self._save_material_to_manager("势力系统", faction_system, novel_title=self._ctx["novel_title"])
        else:
            print("⚠️ 势力/阵营系统生成失败，将使用默认设定")
            # 🔥 更新步骤状态为失败（红色）
            self._update_step_status('faction_system', 'failed', '势力系统生成失败，使用默认设定')
            # 创建一个基础的势力系统结构，确保后续流程不会出错
            self._ctx["faction_system"] = {
                "factions": [],
                "main_conflict": "待定",
                "faction_power_balance": "待定",
                "recommended_starting_faction": "待定"
            }
        
        # 核心角色设计（现在可以基于势力系统）
        print("=== 步骤4: 设计核心角色 (主角/核心盟友/宿敌) ===")
        self._ctx["current_progress"]["stage"] = "核心角色设计"
        
        # 🔥 更新步骤状态为进行中（黄色）
        self._update_step_status('character_design', 'active', '正在设计核心角色...')
        
        core_characters = self.content_generator.generate_character_design(
            novel_title=self._ctx["novel_title"],
            core_worldview=self._ctx.get("core_worldview", {}),
            selected_plan=self._ctx["selected_plan"],
            market_analysis=self._ctx.get("market_analysis", {}),
            design_level="core",
            global_growth_plan=self._ctx.get("global_growth_plan"),
            overall_stage_plans=self._ctx.get("overall_stage_plans"),
            custom_main_character_name=getattr(self, 'custom_main_character_name', None) or ""
        )
        
        if not core_characters:
            print("❌ 核心角色设计失败，终止生成")
            # 🔥 更新步骤状态为失败（红色）
            self._update_step_status('character_design', 'failed', '核心角色设计失败')
            return False
        
        # 🔥 更新步骤状态为已完成（绿色）
        self._update_step_status('character_design', 'completed', '核心角色设计完成')
        
        # 持久化核心角色数据
        print("=== 步骤 4.5: 持久化核心角色数据 ===")
        
        # 检查 quality_assessor 是否已初始化
        if self.quality_assessor is not None:
            self.quality_assessor.persist_initial_character_designs(
                novel_title=self._ctx["novel_title"],
                character_design=core_characters
            )
        else:
            # 如果还没有初始化，使用临时保存
            print("⚠️ 质量评估器尚未初始化，将延迟持久化")
            # TODO: 在后续流程中会通过质量评估器进行持久化
        
        self._ctx["character_design"] = core_characters
        print("✅ 核心角色设计完成，已建立角色基础库。")
        
        return True

    def _generate_overall_planning(self, update_step_status=None) -> bool:
        """生成全书规划"""
        print("\n" + "="*60)
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 使用传入的回调或默认的内部方法
        _update_step = update_step_status if update_step_status else self._update_step_status
        
        # 生成情绪蓝图
        self._ctx["current_progress"]["stage"] = "情绪蓝图规划"
        _update_step('emotional_growth_planning', 'active', '正在生成情绪蓝图...')
        if not self.emotional_blueprint_manager.generate_emotional_blueprint(
            self._ctx["novel_title"],
            self._ctx["novel_synopsis"],
            self._ctx["creative_seed"]
        ):
            print("❌ 情绪蓝图生成失败，无法进行后续情绪引导。")
            _update_step('emotional_growth_planning', 'failed', '情绪蓝图生成失败')
            return False
        _update_step('emotional_growth_planning', 'completed', '情绪蓝图生成完成')
        
        # 全局成长规划
        self._ctx["current_progress"]["stage"] = "成长规划"
        if not self._generate_global_growth_plan():
            print("⚠️ 全局成长规划生成失败，使用基础框架")
        
        # 生成全书阶段计划
        self._ctx["current_progress"]["stage"] = "阶段计划"
        _update_step('stage_plan', 'active', '正在生成全书阶段计划...')
        creative_seed = self._ctx["creative_seed"]
        total_chapters = self._ctx["current_progress"]["total_chapters"]
        
        overall_stage_plans = self.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self._ctx["novel_title"],
            self._ctx["novel_synopsis"],
            self._ctx.get("market_analysis", {}),
            self._ctx.get("global_growth_plan", {}),
            self._ctx.get("emotional_blueprint", {}),
            total_chapters
        )
        
        # 🔥 修复：同时更新 _ctx 和 novel_data
        self._ctx["overall_stage_plans"] = overall_stage_plans
        self.novel_data["overall_stage_plans"] = overall_stage_plans
        
        if not overall_stage_plans:
            print("⚠️ 全书阶段计划生成失败，使用默认阶段划分")
        
        _update_step('stage_plan', 'completed', '全书阶段计划生成完成')
        
        # 生成阶段详细写作计划
        self._ctx["current_progress"]["stage"] = "阶段详细计划"
        _update_step('detailed_stage_plans', 'active', '正在生成阶段详细写作计划...')
        if not self._generate_stage_writing_plans(update_step_status=_update_step):
            print("❌ 生成阶段详细写作计划失败")
            _update_step('detailed_stage_plans', 'failed', '阶段详细写作计划生成失败')
            return False
        _update_step('detailed_stage_plans', 'completed', '阶段详细写作计划生成完成')
        
        # 元素登场时机已由期待感系统管理
        print("✅ 元素登场时机由期待感系统统一管理")
        
        # 初始化系统
        self._ctx["current_progress"]["stage"] = "系统初始化"
        _update_step('system_init', 'active', '正在初始化系统...')
        self._initialize_systems()
        _update_step('system_init', 'completed', '系统初始化完成')
        
        return True

    def _prepare_content_generation(self) -> bool:
        """准备内容生成"""
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 创建项目目录和保存初始进度
        self._ctx["current_progress"]["stage"] = "项目初始化"
        self._initialize_project()
        
        return True

    def _generate_all_chapters(self, total_chapters: int, start_chapter: int = 1) -> bool:
        """生成所有章节内容"""
        print("\n" + "="*60)
        print("📖 第五阶段：章节内容生成")
        print("="*60)
        
        print(f"开始生成第{start_chapter}-{total_chapters}章小说内容...")
        print("基于选定方案和创作方向进行创作")
        print("每章生成后将进行质量评估和优化")
        print("特别优化章节衔接，确保情节连贯性")
        print("🤖 新增AI痕迹检测和消除功能")
        print("每章将单独保存为包含质量评估的JSON文件")
        print("这个过程可能需要较长时间，请耐心等待...")
        print("提示: 按Ctrl+C可以安全中断，下次可继续生成")
        
        # 对于大规模生成，使用更小的批次
        actual_chapters_per_batch = min(3, self.config.get("defaults", {}).get("chapters_per_batch", 3))
        
        for batch_start in range(start_chapter, total_chapters + 1, actual_chapters_per_batch):
            batch_end = min(batch_start + actual_chapters_per_batch - 1, total_chapters)
            self._ctx["current_progress"]["current_batch"] += 1
            
            print(f"\n批次{self._ctx['current_progress']['current_batch']}: 第{batch_start}-{batch_end}章")
            
            if not self.generate_chapters_batch(batch_start, batch_end):
                print(f"❌ 批次{self._ctx['current_progress']['current_batch']}生成失败")
                continue_gen = input("是否继续生成后续章节？(y/n): ").lower()
                if continue_gen != 'y':
                    break
            
            # 批次间延迟
            batch_delay = 2 if total_chapters > 100 else 2
            if batch_end < total_chapters:
                print(f"等待{batch_delay}秒后继续下一批次...")
                time.sleep(batch_delay)
        
        return self._finalize_generation()

    # ==================== 辅助生成方法 ====================

    def _generate_writing_style_guide(self) -> bool:
        """生成写作风格指南"""
        print("=== 步骤1.5: 生成写作风格指南 ===")
        
        try:
            creative_seed = self._ctx["creative_seed"]
            category = self._ctx.get("category", "未分类")
            selected_plan = self._ctx["selected_plan"]
            market_analysis = self._ctx.get("market_analysis", {})
            
            writing_style = self.content_generator.generate_writing_style_guide(
                creative_seed, category, selected_plan, market_analysis
            )
            
            if writing_style:
                # 🔥 修复：同时更新 _ctx 和 novel_data
                self._ctx["writing_style_guide"] = writing_style
                self.novel_data["writing_style_guide"] = writing_style
                print("✅ 写作风格指南生成完成")
                self._save_writing_style_to_file(writing_style)
                return True
            else:
                print("⚠️ 写作风格指南生成失败，使用默认风格")
                default_style = self._get_default_writing_style(category)
                self._ctx["writing_style_guide"] = default_style
                self.novel_data["writing_style_guide"] = default_style
                return True
                
        except Exception as e:
            print(f"⚠️ 生成写作风格指南时出错: {e}")
            default_style = self._get_default_writing_style(category)
            self._ctx["writing_style_guide"] = default_style
            self.novel_data["writing_style_guide"] = default_style
            return True

    def _generate_market_analysis(self) -> bool:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        creative_seed = self._ctx["creative_seed"]
        selected_plan = self._ctx["selected_plan"]
        
        market_analysis = self.content_generator.generate_market_analysis(creative_seed, selected_plan)
        
        self._ctx["market_analysis"] = market_analysis
        
        if not market_analysis:
            print("  ❌ 市场分析失败，终止生成")
            return False
        
        print("  ✅ 市场分析完成")
        
        # 保存到材料管理器
        self._save_material_to_manager("市场分析", market_analysis, creative_seed=creative_seed)
        return True

    def _generate_worldview(self) -> bool:
        """生成世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        # 🔥 更新步骤状态为进行中（黄色）
        self._update_step_status('worldview', 'active', '正在构建核心世界观...')
        
        print("🔄 调用 content_generator.generate_core_worldview...")
        print(f"   - novel_title: {self._ctx.get('novel_title', 'N/A')}")
        print(f"   - selected_plan keys: {list(self._ctx.get('selected_plan', {}).keys())}")
        print(f"   - market_analysis keys: {list(self._ctx.get('market_analysis', {}).keys())}")
        
        core_worldview = self.content_generator.generate_core_worldview(
            self._ctx["novel_title"],
            self._ctx["novel_synopsis"],
            self._ctx["selected_plan"],
            self._ctx.get("market_analysis", {})
        )
        
        print(f"🔄 generate_core_worldview 返回: {type(core_worldview)}")
        
        self._ctx["core_worldview"] = core_worldview
        
        if not core_worldview:
            print("❌ 世界观构建失败，终止生成")
            # 🔥 更新步骤状态为失败（红色）
            self._update_step_status('worldview', 'failed', '世界观构建失败')
            return False
        
        print("✅ 世界观构建完成")
        # 🔥 更新步骤状态为已完成（绿色）
        self._update_step_status('worldview', 'completed', '世界观构建完成')
        
        # 保存到材料管理器
        self._save_material_to_manager("世界观", core_worldview, novel_title=self._ctx["novel_title"])
        return True

    def _generate_global_growth_plan(self) -> bool:
        """生成全局成长规划"""
        print("=== 步骤5: 制定全书成长规划框架 ===")
        
        try:
            global_growth_plan = self.global_growth_planner.generate_global_growth_plan()
            
            if global_growth_plan:
                # 🔥 关键修复：同时更新 _ctx 和 novel_data
                self._ctx["global_growth_plan"] = global_growth_plan
                self.novel_data["global_growth_plan"] = global_growth_plan
                
                # 同时更新 GlobalGrowthPlanner 中的引用
                self.global_growth_planner.global_growth_plan = global_growth_plan
                
                print("✅ 全书成长规划框架制定完成")
                return True
            else:
                print("❌ 全书成长规划生成失败，使用基础框架")
                # 使用默认规划
                default_plan = self.global_growth_planner._create_default_global_plan(
                    self._ctx.get("current_progress", {}).get("total_chapters", 100)
                )
                self._ctx["global_growth_plan"] = default_plan
                self.novel_data["global_growth_plan"] = default_plan
                self.global_growth_planner.global_growth_plan = default_plan
                return False
                
        except Exception as e:
            print(f"⚠️ 全局成长规划器出错: {e}，使用基础框架")
            # 出错时也使用默认规划
            try:
                default_plan = self.global_growth_planner._create_default_global_plan(
                    self._ctx.get("current_progress", {}).get("total_chapters", 100)
                )
                self._ctx["global_growth_plan"] = default_plan
                self.novel_data["global_growth_plan"] = default_plan
                self.global_growth_planner.global_growth_plan = default_plan
            except Exception as e2:
                print(f"⚠️ 使用默认规划也失败: {e2}")
            return False

    def _generate_stage_writing_plans(self, update_step_status=None) -> bool:
        """生成各阶段详细写作计划"""
        print("=== 步骤6: 生成各阶段详细写作计划 ===")
        
        # 使用传入的回调或默认的内部方法
        _update_step = update_step_status if update_step_status else self._update_step_status
        
        # 更新步骤状态为进行中
        _update_step('detailed_stage_plans', 'active', '正在并行生成各阶段详细写作计划...')
        
        overall_stage_plans = self._ctx.get("overall_stage_plans", {})
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            stage_plan_container = overall_stage_plans
            stage_plan_dict = stage_plan_container["overall_stage_plan"]
            
            self._ctx["stage_writing_plans"] = {}
            
            # 🔥 优化：先批量生成所有阶段的情绪计划（单次API调用）
            print("  💖 批量生成所有阶段的情绪计划...")
            emotional_blueprint = self.novel_data.get("emotional_blueprint", {})
            stages_info = []
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                stages_info.append({'stage_name': stage_name, 'stage_range': stage_range})
            
            all_stages_emotional_plans = self.emotional_plan_manager.generate_all_stages_emotional_plan(
                stages_info, emotional_blueprint
            )
            print(f"  ✅ 成功生成 {len(all_stages_emotional_plans)} 个阶段的情绪计划")
            
            # 🚀 批量生成所有阶段的主龙骨（将 4 次 API 调用合并为 1 次）
            print("  🚀 批量生成所有阶段的主龙骨...")
            stages_config = []
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                stage_length = max(1, int(numbers[1]) - int(numbers[0]) + 1) if len(numbers) >= 2 else 3
                
                # 计算事件密度
                density = self.stage_plan_manager.event_manager.calculate_optimal_event_density_by_stage(
                    stage_name, stage_length
                )
                
                stages_config.append({
                    'stage_name': stage_name,
                    'stage_range': stage_range,
                    'density_requirements': density,
                    'stage_emotional_plan': all_stages_emotional_plans.get(stage_name)
                })
            
            all_stages_skeletons = self.stage_plan_manager.major_event_generator.generate_all_stages_skeletons_batch(
                stages_config=stages_config,
                creative_seed=self._ctx["creative_seed"],
                global_novel_data=self.novel_data,
                overall_stage_plan=stage_plan_dict,
                novel_title=self._ctx["novel_title"]
            )
            
            if all_stages_skeletons:
                total_events = sum(len(events) for events in all_stages_skeletons.values())
                print(f"  ✅ 批量生成主龙骨成功: {len(all_stages_skeletons)} 个阶段, {total_events} 个重大事件")
            else:
                print("  ⚠️ 批量生成主龙骨失败，将使用逐个生成模式")
                all_stages_skeletons = {}
            
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                
                # 获取预生成的情绪计划和主龙骨
                pre_generated_emotional_plan = all_stages_emotional_plans.get(stage_name)
                pre_generated_skeletons = all_stages_skeletons.get(stage_name) if all_stages_skeletons else None
                
                print(f"  📋 生成 {stage_name} 的详细写作计划...")
                print(f"  📋 章节范围: {stage_range}")
                if pre_generated_skeletons:
                    print(f"  🚀 使用预生成主龙骨: {len(pre_generated_skeletons)} 个事件")
                
                stage_plan = self.stage_plan_manager.generate_stage_writing_plan(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=self._ctx["creative_seed"],
                    novel_title=self._ctx["novel_title"],
                    novel_synopsis=self._ctx["novel_synopsis"],
                    overall_stage_plan=stage_plan_dict,
                    stage_emotional_plan=pre_generated_emotional_plan,
                    pre_generated_skeletons=pre_generated_skeletons
                )
                
                if stage_plan:
                    self._ctx["stage_writing_plans"][stage_name] = stage_plan
                    print(f"  ✅ {stage_name} 详细计划生成成功")
                else:
                    print(f"  ❌ {stage_name} 详细计划生成失败")
            
            success_count = len(self._ctx["stage_writing_plans"])
            if success_count > 0:
                print(f"✅ 阶段详细计划生成完成: {success_count}/{len(stage_plan_dict)} 个阶段")
                # 🔥 修复：同时更新 novel_data
                self.novel_data["stage_writing_plans"] = self._ctx["stage_writing_plans"]
                self._save_material_to_manager("阶段计划", self._ctx["stage_writing_plans"], total_stages=success_count)
                
                # 📝 注意：全书补充角色生成已移至 PhaseGenerator 作为独立步骤
                # 在 _generate_overall_planning 中的 'supplementary_characters' 步骤执行
                
                return True
            else:
                print("❌ 所有阶段详细计划生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 生成阶段详细写作计划时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ElementTimingPlanner已移除，元素登场时机由期待感系统统一管理
    # 期待感系统会在事件规划时自动处理元素登场时机

    def _initialize_systems(self):
        """初始化各种系统"""
        print("=== 步骤7: 初始化系统 ===")
        
        # 🔥 修复：先加载写作计划到内存，这样事件系统才能找到它们
        if hasattr(self, 'stage_plan_manager') and self.stage_plan_manager:
            loaded_count = self.stage_plan_manager.load_and_merge_all_plans()
            print(f"✅ 已加载 {loaded_count} 个阶段的写作计划到内存")
        else:
            print("⚠️ 阶段计划管理器未初始化，跳过写作计划加载")
        
        if self._ctx["overall_stage_plans"]:
            self.event_driven_manager.initialize_event_system()
            print("✅ 事件系统初始化完成")
        
        if self._ctx["character_design"]:
            # 期待感管理系统将在事件规划时自动初始化
            print("✅ 期待感管理系统已就绪")
        
        print("✅ 第一阶段详细写作计划已生成")

    def _initialize_project(self):
        """初始化项目"""
        import re
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self._ctx["novel_title"])
        import os
        
        # 使用新的路径配置系统
        from src.config.path_config import path_config
        username = getattr(self, '_username', None)
        paths = path_config.ensure_directories(self._ctx["novel_title"], username=username)
        
        print(f"✅ 项目目录已创建: {paths['project_root']}")
        print(f"📁 章节目录: {paths['chapters_dir']}")
        
        # 🔥 确保用户名被传递到 _ctx
        if hasattr(self, '_username') and self._username:
            self._ctx['_username'] = self._username
        self.project_manager.save_project_progress(self._ctx)
        print("✅ 项目初始进度已保存")

    def _finalize_generation(self) -> bool:
        """完成生成过程"""
        self._ctx["current_progress"]["stage"] = "完成"
        
        # 🔥 确保用户名被传递到 _ctx
        if hasattr(self, '_username') and self._username:
            self._ctx['_username'] = self._username
        # 保存最终进度和导出总览
        self.project_manager.save_project_progress(self._ctx)
        self.project_manager.export_novel_overview(self._ctx)
        
        # 生成小说封面 - 只有当所有章节都生成完成时才生成
        total_chapters = self._ctx["current_progress"]["total_chapters"]
        completed_chapters = self._ctx["current_progress"]["completed_chapters"]
        
        if completed_chapters >= total_chapters:
            print("\n" + "="*60)
            print("🎨 最后一步：生成小说封面")
            print("="*60)
            self._ctx["current_progress"]["stage"] = "封面生成"
            if not self._generate_novel_cover():
                print("⚠️ 封面生成失败，项目已完成但无封面。")
        else:
            print(f"\n⚠️ 当前已完成 {completed_chapters}/{total_chapters} 章，封面将在所有章节生成完成后生成。")
        
        # 注释：项目文件复制已禁用，因为目录结构已经就绪
        # print("\n" + "="*60)
        # print("🚚 正在复制项目文件到执行目录...")
        # print("="*60)
        #
        # target_dir = r"C:\work1.0\Chrome\小说项目"
        # novel_title = self._ctx.get("novel_title")
        #
        # if novel_title:
        #     copy_success = self.project_manager.copy_project_to_directory(novel_title, target_dir)
        #     if not copy_success:
        #         print(f"⚠️ 项目《{novel_title}》文件复制失败。")
        # else:
        #     print("❌ 无法复制项目文件，因为小说标题未知。")
        
        # 材料管理器导出功能
        if self.material_manager:
            print("\n" + "="*60)
            print("📦 正在生成材料包...")
            print("="*60)
            
            try:
                bundle_result = self.material_manager.create_material_bundle(
                    bundle_name="完整生成材料",
                    material_types=[],
                    time_range=("", ""),
                    include_metadata=True
                )
                
                if isinstance(bundle_result, dict) and bundle_result.get("success"):
                    print(f"✅ 完整材料包生成成功: {bundle_result.get('bundle_name')}")
                    print(f"📁 包含材料数量: {bundle_result.get('total_materials', 0)}个")
                    print(f"📍 保存路径: {bundle_result.get('bundle_path')}")
                else:
                    print(f"⚠️ 材料包生成失败")
                
                manifest = self.material_manager.generate_material_manifest()
                if manifest:
                    print(f"✅ 材料清单生成成功")
                    print(f"📊 材料统计: {manifest.get('total_materials', 0)}个材料")
                    print(f"📂 材料类别: {len(manifest.get('material_categories', {}))}类")
                
                statistics = self.material_manager.get_material_statistics()
                if statistics:
                    print(f"✅ 材料统计完成")
                    print(f"📈 总材料数: {statistics.get('total_materials', 0)}个")
                    print(f"💾 总大小: {statistics.get('total_size', 0)}字节")
                    print(f"📋 材料类型: {len(statistics.get('by_type', {}))}种")
                    
            except Exception as e:
                print(f"❌ 材料导出过程出错: {e}")
        
        print("\n🎉 小说生成完成！")
        self._print_generation_summary()
        return True

    def _generate_novel_cover(self) -> bool:
        """生成小说封面"""
        # 使用你指定的作者名
        author_name = "北莽王庭的达延"
        
        result = self.cover_generator.generate_novel_cover(
            self._ctx.get("novel_title", ""),
            self._ctx.get("novel_synopsis", ""),
            self._ctx.get("category", "未分类"),
            author_name
        )
        
        if result.get("success"):
            self._ctx["cover_image"] = result.get("local_path")
            self._ctx["cover_generated"] = True
            return True
        else:
            return False

    # ==================== 其他辅助方法 ====================

    def initialize_expectation_elements(self):
        """初始化需要铺垫的重要元素（使用期待感系统）"""
        # 优先从 novel_data 获取，如果不存在则尝试从 _ctx 获取
        core_worldview = self.novel_data.get("core_worldview") or self._ctx.get("core_worldview")
        character_design = self.novel_data.get("character_design") or self._ctx.get("character_design")
        
        if core_worldview:
            factions = core_worldview.get("major_factions", [])
            for i, faction in enumerate(factions):
                intro_chapter = 10 + (i * 15)
                # 使用期待感系统注册势力
                self.expectation_manager.tag_event_with_expectation(
                    event_id=f"faction_{faction}",
                    expectation_type=ExpectationType.MYSTERY_FORESHADOW,
                    planting_chapter=1,
                    description=f"势力 '{faction}' 的介绍和铺垫",
                    target_chapter=min(intro_chapter, 50)
                )
                print(f"✓ 从世界观注册势力期待: {faction}")
        
        if character_design:
            important_chars = character_design.get("important_characters", [])
            for i, char in enumerate(important_chars):
                if i < 3:
                    intro_chapter = 5 + (i * 8)
                    # 使用期待感系统注册角色
                    self.expectation_manager.tag_event_with_expectation(
                        event_id=f"character_{char['name']}",
                        expectation_type=ExpectationType.MYSTERY_FORESHADOW,
                        planting_chapter=1,
                        description=f"角色 '{char['name']}' 的介绍和铺垫",
                        target_chapter=intro_chapter
                    )
                    print(f"✓ 从角色设计注册角色期待: {char['name']}")

    def _save_writing_style_to_file(self, writing_style: Dict):
        """保存写作风格指南到JSON文件"""
        import os
        try:
            from src.utils.path_manager import path_manager
            
            novel_title = self._ctx.get("novel_title", "unknown")
            print(f"🔥 [_save_writing_style_to_file] 开始保存写作风格指南: {novel_title}")
            
            # 🔥 获取用户名用于用户隔离路径
            username = getattr(self, '_username', None)
            print(f"🔥 [_save_writing_style_to_file] 使用用户名: {username}")
            
            style_data = {
                "novel_title": novel_title,
                "category": self._ctx.get("category", "未分类"),
                "creative_seed": self._ctx.get("creative_seed", ""),
                "created_time": datetime.now().isoformat(),
                "writing_style_guide": writing_style
            }
            
            # 🔥 确保目录存在（使用用户隔离路径）
            paths = path_manager.path_config.get_project_paths(novel_title, username=username)
            style_path = paths.get("writing_style_guide")
            if style_path:
                os.makedirs(os.path.dirname(style_path), exist_ok=True)
                print(f"🔥 目录已确保存在: {os.path.dirname(style_path)}")
            
            success = path_manager.save_writing_style_guide(novel_title, writing_style, username=username)
            
            if success:
                paths = path_manager.path_config.get_project_paths(novel_title, username=username)
                actual_path = paths["writing_style_guide"]
                print(f"✅ 写作风格指南已保存到: {actual_path}")
                # 🔥 验证文件存在
                if os.path.exists(actual_path):
                    file_size = os.path.getsize(actual_path)
                    print(f"✅ 文件验证成功: {actual_path} ({file_size} bytes)")
                else:
                    print(f"❌ 文件验证失败: 文件不存在 {actual_path}")
            else:
                print(f"⚠️ 写作风格指南保存失败 (path_manager返回False)")

        except Exception as e:
            print(f"⚠️ 保存写作风格指南失败: {e}")
            import traceback
            traceback.print_exc()

    def _get_default_writing_style(self, category: str) -> Dict:
        """根据分类获取默认的写作风格"""
        # 这里可以返回一个基础的默认风格
        return {
            "core_style": "语言流畅自然，情节推进合理",
            "language_features": ["表达清晰", "描写生动", "节奏适中"],
            "narrative_pace": "稳步推进，高潮适当",
            "dialogue_style": "符合人物身份，自然流畅",
            "description_focus": ["情节推进", "人物刻画", "环境描写"],
            "emotional_tone": "情感真实，有感染力",
            "chapter_structure": "章节完整，衔接自然",
            "important_notes": ["保持风格一致性", "注意情节逻辑", "强化读者代入感"]
        }

    def _save_material_to_manager(self, material_type: str, content: Any, **kwargs):
        """保存材料到材料管理器的通用方法"""
        if not self.material_manager:
            return
            
        try:
            result = self.material_manager.create_material(material_type, content, **kwargs)
            if result.get("success"):
                print(f"✅ {material_type}已保存到材料管理器")
            else:
                print(f"⚠️ {material_type}保存失败: {result.get('error')}")
        except Exception as e:
            print(f"❌ 保存{material_type}到材料管理器失败: {e}")
        
        # 🔥 关键修复：同时直接保存到文件（确保阶段一产物落地）
        try:
            self._force_save_material_to_file(material_type, content)
        except Exception as e:
            print(f"⚠️ 强制保存{material_type}到文件失败: {e}")
    
    def _force_save_material_to_file(self, material_type: str, content: Any):
        """强制保存材料到项目目录（不依赖材料管理器）"""
        import os
        import json
        from src.utils.path_manager import path_manager
        
        novel_title = self._ctx.get("novel_title") or self.novel_data.get("novel_title")
        if not novel_title:
            print(f"⚠️ 无法保存{material_type}: 小说标题未知")
            return
        
        # 🔥 获取用户名用于用户隔离路径
        username = getattr(self, '_username', None)
        
        paths = path_manager.path_config.get_project_paths(novel_title, username=username)
        safe_title = path_manager.path_config.get_safe_title(novel_title)
        
        # 根据材料类型确定保存路径
        file_mappings = {
            "市场分析": (paths.get("market_analysis"), "market_analysis"),
            "世界观": (os.path.join(paths.get("worldview_dir", ""), f"{safe_title}_世界观.json"), "core_worldview"),
            "势力系统": (os.path.join(paths.get("worldview_dir", ""), f"{safe_title}_势力系统.json"), "faction_system"),
        }
        
        file_path, data_key = file_mappings.get(material_type, (None, None))
        if not file_path:
            print(f"⚠️ 未知的材料类型: {material_type}")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 准备数据
        data_to_save = {
            "novel_title": novel_title,
            "material_type": material_type,
            "created_time": datetime.now().isoformat(),
            data_key or "content": content
        }
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        # 验证
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"🔥 [强制保存] {material_type}已保存: {file_path} ({file_size} bytes)")
        else:
            print(f"❌ [强制保存] {material_type}保存失败: 文件未创建")

    def _print_generation_summary(self):
        """打印生成摘要"""
        print("\n" + "="*60)
        print("🎊 小说生成完成摘要")
        print("="*60)
        
        print(f"📖 小说标题: {self._ctx['novel_title']}")
        print(f"📚 小说分类: {self._ctx.get('category', '未分类')}")
        print(f"📝 总章节数: {self._ctx['current_progress']['completed_chapters']}/{self._ctx['current_progress']['total_chapters']}")
        
        # 字数统计
        total_words = sum(chapter.get('word_count', 0) for chapter in self._ctx["generated_chapters"].values())
        print(f"📊 总字数: {total_words}字")
        
        print("="*60)

    # ==================== 恢复模式支持方法 ====================
    # 这些方法现在委托给ResumeManager处理
    
    def _check_for_resume_checkpoint(self, creative_seed, total_chapters: int) -> Optional[Dict]:
        """检查是否有可恢复的检查点（委托给ResumeManager）"""
        return self.resume_manager.check_for_resume_checkpoint(creative_seed, total_chapters)
    
    def _resume_phase_one_from_checkpoint(self, checkpoint_data: Dict, creative_seed, total_chapters: int) -> bool:
        """
        从检查点恢复第一阶段生成（委托给ResumeManager）
        
        Args:
            checkpoint_data: 检查点数据
            creative_seed: 创意种子
            total_chapters: 总章节数
            
        Returns:
            是否成功
        """
        return self.resume_manager.resume_phase_one_from_checkpoint(
            checkpoint_data, creative_seed, total_chapters
        )

    # ==================== 第二阶段生成方法 ====================
    
    def phase_two_generation(
        self, 
        novel_title: str, 
        from_chapter: int, 
        chapters_to_generate: int,
        min_word_threshold: int = 1500,
        max_word_threshold: int = 3500
    ) -> bool:
        """
        第二阶段生成：从第一阶段产物继续生成章节内容
        
        Args:
            novel_title: 小说标题
            from_chapter: 起始章节号
            chapters_to_generate: 要生成的章节数
            min_word_threshold: 最少字数限制（默认1500）
            max_word_threshold: 最多字数限制（默认3500）
            
        Returns:
            是否成功
        """
        # 🔥 保存字数阈值到上下文
        self._ctx["min_word_threshold"] = min_word_threshold
        self._ctx["max_word_threshold"] = max_word_threshold
        self.logger.info(f"📝 字数阈值设置: {min_word_threshold}-{max_word_threshold}字")
        try:
            print("\n" + "="*60)
            print("🚀 开始第二阶段章节生成")
            print("="*60)
            
            # 🔥 修复：确保novel_data中有novel_title和current_progress
            if not self._ctx.get("novel_title"):
                self._ctx["novel_title"] = novel_title

            # 关键修复：同时设置 self.novel_data，供 StagePlanPersistence 使用
            if not self.novel_data.get("novel_title"):
                self.novel_data["novel_title"] = novel_title
                self.logger.info(f"已设置 novel_data['novel_title'] = {novel_title}")
            
            # 关键修复：将 novel_data 中的关键数据同步到 _ctx
            for key in ["overall_stage_plans", "global_growth_plan", "stage_writing_plans", 
                       "character_design", "core_worldview", "novel_synopsis", "creative_seed"]:
                if self.novel_data.get(key) and not self._ctx.get(key):
                    self._ctx[key] = self.novel_data[key]
                    self.logger.info(f"已同步 {key} 到 _ctx")
            
            # 🔥 修复：确保current_progress结构存在并正确初始化
            if "current_progress" not in self._ctx or not self._ctx["current_progress"]:
                print("📋 初始化 current_progress 结构...")
                self._ctx["current_progress"] = {
                    "completed_chapters": 0,
                    "total_chapters": self._ctx.get("total_chapters", 200),
                    "stage": "第二阶段生成",
                    "current_stage": "第二阶段",
                    "start_time": datetime.now().isoformat()
                }
                print(f"✅ current_progress 已初始化: 总章节数 = {self._ctx['current_progress']['total_chapters']}")
            
            print(f"📚 小说标题: {self._ctx.get('novel_title', '未知')}")
            print(f"📖 起始章节: {from_chapter}")
            print(f"📊 生成章节数: {chapters_to_generate}")
            
            # 确保有novel_title
            if not self._ctx.get("novel_title"):
                print("❌ 小说标题未设置，无法继续生成")
                return False
            
            # 确保材料管理器已初始化
            if not self.material_manager:
                self._initialize_material_manager()
            
            # 计算结束章节
            end_chapter = from_chapter + chapters_to_generate - 1
            
            print(f"\n📝 开始生成第{from_chapter}-{end_chapter}章...")
            print("这个过程可能需要较长时间，请耐心等待...")
            
            # 批量生成章节
            success = self.generate_chapters_batch(from_chapter, end_chapter)
            
            if success:
                print("\n✅ 第二阶段章节生成完成")
                
                # 保存进度
                # 🔥 确保用户名被传递到 _ctx
                if hasattr(self, '_username') and self._username:
                    self._ctx['_username'] = self._username
                self.project_manager.save_project_progress(self._ctx)
                
                return True
            else:
                print("\n❌ 第二阶段章节生成失败")
                return False
                
        except Exception as e:
            print(f"\n❌ 第二阶段生成过程异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 注意：以下方法已被移到 ResumeManager 中
    # - _execute_phase_one_step
    # - _step_worldview_generation
    # - _step_character_generation
    # - _step_stage_plan
    # - _step_quality_assessment
    # - _step_finalization
    # - _create_initial_checkpoint
    # - _phase_one_generation_resume
    # - _resume_initialization
    # - _resume_worldview_generation
    # - _resume_character_generation
    # - _resume_stage_plan
    # - _resume_quality_assessment
    # - _resume_finalization
    # - _generate_faction_system