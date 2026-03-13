"""
小说生成管理器
"""
import os
import json
import re
import threading
import uuid
import time
import atexit
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from web.web_config import logger, BASE_DIR, CREATIVE_IDEAS_FILE


# 🔥 全局清理函数：主进程退出时停止所有子线程
def _cleanup_on_exit():
    """主进程退出时清理所有生成任务"""
    logger.info("🧹 主进程退出，开始清理生成任务...")
    try:
        # 获取全局管理器实例并停止所有任务
        global _thread_monitor
        if '_thread_monitor' in globals():
            _thread_monitor.stop_monitoring()
            
        # 尝试获取 novel_manager 实例并停止所有活跃任务
        global novel_manager
        if 'novel_manager' in globals() and novel_manager:
            # 停止所有活跃任务
            for task_id in list(novel_manager.active_tasks.keys()):
                logger.info(f"⏹️ 停止任务: {task_id}")
                novel_manager.stop_task(task_id)
            
            # 停止所有任务线程
            for task_id, thread in list(novel_manager.task_threads.items()):
                if thread.is_alive():
                    logger.info(f"⏹️ 等待线程结束: {task_id}")
                    # 设置停止标志
                    novel_manager._stop_flags[task_id] = True
                    # 等待线程结束（最多3秒）
                    thread.join(timeout=3)
                    
        logger.info("✅ 清理完成")
    except Exception as e:
        logger.error(f"❌ 清理过程出错: {e}")


def force_kill_all_threads():
    """
    强制终止所有生成线程（仅在极端情况下使用）
    使用 os._exit 强制退出，不执行任何清理
    """
    logger.warning("⚠️ 强制终止所有线程！")
    os._exit(1)


# 🔥 信号处理器：捕获进程终止信号
def _signal_handler(signum, frame):
    """处理进程终止信号"""
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(f"📡 收到信号 {sig_name}，准备退出...")
    _cleanup_on_exit()
    # 使用 os._exit 强制退出所有线程
    os._exit(0)


# 注册 atexit 清理函数
atexit.register(_cleanup_on_exit)

# 注册信号处理器（在 Windows 上 SIGTERM 可能不可用，所以用 try-except）
try:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
except (AttributeError, ValueError):
    pass  # 在某些平台上信号可能不可用


# 🔥 线程监控器：确保后台线程健康运行
class ThreadMonitor:
    """线程健康监控器，检测线程是否存活并在必要时恢复"""
    
    def __init__(self, check_interval=30):
        self.check_interval = check_interval  # 检查间隔（秒）
        self.monitored_threads = {}  # {task_id: {'thread': thread, 'restart_func': func, 'last_alive': timestamp}}
        self._stop_event = threading.Event()
        self._monitor_thread = None
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """启动监控线程"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, name="ThreadMonitor")
            self._monitor_thread.daemon = False  # 重要：不是daemon线程
            self._monitor_thread.start()
            logger.info("✅ 线程监控器已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            logger.info("⏹️ 线程监控器已停止")
    
    def register_thread(self, task_id, thread, restart_func):
        """注册要监控的线程
        
        Args:
            task_id: 任务ID
            thread: 线程对象
            restart_func: 线程死亡时的恢复函数，格式：restart_func(task_id) -> new_thread
        """
        with self._lock:
            self.monitored_threads[task_id] = {
                'thread': thread,
                'restart_func': restart_func,
                'last_alive': time.time(),
                'restart_count': 0
            }
            logger.info(f"📋 注册线程监控: {task_id}")
    
    def unregister_thread(self, task_id):
        """取消注册线程"""
        with self._lock:
            if task_id in self.monitored_threads:
                del self.monitored_threads[task_id]
                logger.info(f"🗑️ 取消线程监控: {task_id}")
    
    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self._check_threads()
            except Exception as e:
                logger.error(f"❌ 线程监控异常: {e}")
            
            # 等待检查间隔
            self._stop_event.wait(self.check_interval)
    
    def _check_threads(self):
        """检查所有注册的线程"""
        with self._lock:
            dead_threads = []
            
            for task_id, info in self.monitored_threads.items():
                thread = info['thread']
                
                if not thread.is_alive():
                    # 线程已死亡
                    info['last_alive'] = time.time()
                    info['restart_count'] += 1
                    
                    if info['restart_count'] <= 3:  # 最多重启3次
                        logger.warning(f"⚠️ 检测到线程死亡: {task_id}，第{info['restart_count']}次重启")
                        try:
                            # 调用恢复函数
                            new_thread = info['restart_func'](task_id)
                            if new_thread:
                                info['thread'] = new_thread
                                logger.info(f"✅ 线程已重启: {task_id}")
                            else:
                                logger.error(f"❌ 线程重启失败: {task_id}，恢复函数返回None")
                                dead_threads.append(task_id)
                        except Exception as e:
                            logger.error(f"❌ 线程重启异常: {task_id} - {e}")
                            dead_threads.append(task_id)
                    else:
                        logger.error(f"❌ 线程重启次数超过限制: {task_id}，不再尝试重启")
                        dead_threads.append(task_id)
            
            # 清理无法恢复的线程
            for task_id in dead_threads:
                del self.monitored_threads[task_id]


# 全局线程监控器实例
_thread_monitor = ThreadMonitor()
from web.utils.path_utils import (
    get_user_novel_dir,
    get_public_projects_dir,
    find_novel_project,
    list_user_projects,
    is_admin,
    get_current_username,
    NOVEL_PROJECTS_ROOT
)

# 🔥 全局单例：NovelGenerator 实例（延迟初始化）
_novel_generator_instance = None
_novel_generator_lock = threading.Lock()

def get_novel_generator(config):
    """获取 NovelGenerator 单例实例（线程安全）"""
    global _novel_generator_instance
    if _novel_generator_instance is None:
        with _novel_generator_lock:
            if _novel_generator_instance is None:
                logger.info("🚀 首次初始化 NovelGenerator（这可能需要几秒钟）...")
                import time
                start = time.time()
                
                logger.info("  [1/3] 导入 NovelGenerator...")
                from src.core.NovelGenerator import NovelGenerator
                logger.info(f"  [1/3] 导入完成，耗时: {time.time()-start:.2f}s")
                
                logger.info("  [2/3] 创建 NovelGenerator 实例...")
                start2 = time.time()
                _novel_generator_instance = NovelGenerator(config)
                logger.info(f"  [2/3] 创建完成，耗时: {time.time()-start2:.2f}s")
                
                # 🔥 设置停止检查回调（使用全局停止标志）
                def stop_check_callback():
                    from web.web_server_refactored import is_stop_requested
                    if is_stop_requested():
                        raise InterruptedError("用户请求停止生成")
                setattr(_novel_generator_instance, '_stop_check_callback', stop_check_callback)
                
                logger.info(f"✅ NovelGenerator 初始化完成，总耗时: {time.time()-start:.2f}s")
    return _novel_generator_instance

def preinitialize_novel_generator():
    """预初始化 NovelGenerator（在服务器启动时调用）"""
    try:
        import sys
        from pathlib import Path
        
        # 确保项目根目录在路径中
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # 使用importlib来动态导入config
        try:
            import importlib.util
            config_path = project_root / "config" / "config.py"
            spec = importlib.util.spec_from_file_location("config_module", config_path)
            if spec is not None and spec.loader is not None:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                CONFIG = config_module.CONFIG
            else:
                raise ImportError("无法创建config模块规格")
        except Exception as e:
            logger.error(f"无法导入配置文件: {e}")
            CONFIG = {
                "defaults": {
                    "total_chapters": 200,
                    "chapters_per_batch": 3
                }
            }
        
        logger.info("🔄 预初始化 NovelGenerator 中...")
        get_novel_generator(CONFIG)
        logger.info("🎉 NovelGenerator 预初始化完成，后续请求将快速响应")
    except Exception as e:
        logger.error(f"❌ 预初始化 NovelGenerator 失败: {e}")


class NovelGenerationManager:
    """小说生成管理器"""
    
    def __init__(self):
        self.task_results = {}
        self.task_progress = {}
        self.novel_projects = {}
        self.active_tasks = {}
        self.task_threads = {}
        
        # 🔥 新增：任务停止标志字典 {task_id: True/False}
        self._stop_flags = {}
        
        # 🔥 新增：初始化检查点管理器
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            self.checkpoint_enabled = True
            logger.info("✅ 检查点功能已启用")
        except Exception as e:
            self.checkpoint_enabled = False
            logger.warning(f"⚠️ 检查点功能未启用: {e}")
        
        logger.info("🔧 NovelGenerationManager 初始化开始")
        self.load_existing_novels()
        
        # 🔥 加载历史任务（包括进行中的任务）
        self._load_persisted_tasks()
        
        # 🔥 启动线程监控器
        global _thread_monitor
        _thread_monitor.start_monitoring()
        logger.info("✅ 线程监控器已启动")
        
        logger.info(f"🔧 NovelGenerationManager 初始化完成，加载了 {len(self.novel_projects)} 个小说项目，{len(self.task_results)} 个任务")

    def _load_persisted_tasks(self):
        """从文件加载持久化的任务数据"""
        try:
            from web.utils.task_persistence import TaskPersistence
            
            # 加载所有历史任务（包括已完成和失败的）
            all_tasks = TaskPersistence.load_all_tasks(
                include_completed=True,
                include_failed=True
            )
            
            loaded_count = 0
            for task_data in all_tasks:
                task_id = task_data.get('task_id')
                if task_id:
                    self.task_results[task_id] = task_data
                    loaded_count += 1
            
            # 检查是否有进行中的任务（服务器重启后这些任务实际上已不再运行）
            active_tasks = TaskPersistence.load_active_tasks()
            for task_data in active_tasks:
                task_id = task_data.get('task_id')
                if task_id and task_id in self.task_results:
                    # 标记为异常中断
                    self.task_results[task_id]['status'] = 'failed'
                    self.task_results[task_id]['error'] = '服务器重启导致任务中断'
                    self.task_results[task_id]['updated_at'] = datetime.now().isoformat()
                    # 保存更新后的状态
                    TaskPersistence.save_task(self.task_results[task_id])
                    logger.warning(f"⚠️ 任务 {task_id} 因服务器重启被标记为失败")
            
            logger.info(f"✅ 已加载 {loaded_count} 个历史任务（{len(active_tasks)} 个因重启被标记为失败）")
            
            # 🔥 启动定期清理任务
            self._start_cleanup_timer()
            
        except Exception as e:
            logger.error(f"❌ 加载持久化任务失败: {e}")

    def _start_cleanup_timer(self):
        """启动定期清理过期任务的定时器"""
        def cleanup_and_reschedule():
            try:
                from web.utils.task_persistence import TaskPersistence
                cleaned = TaskPersistence.cleanup_old_tasks()
                if cleaned > 0:
                    logger.info(f"🧹 定期清理完成，已删除 {cleaned} 个过期任务")
            except Exception as e:
                logger.error(f"❌ 定期清理任务失败: {e}")
            
            # 重新启动定时器（每24小时执行一次）
            self._cleanup_timer = threading.Timer(24 * 3600, cleanup_and_reschedule)
            self._cleanup_timer.daemon = True
            self._cleanup_timer.start()
        
        # 启动第一次定时器
        self._cleanup_timer = threading.Timer(24 * 3600, cleanup_and_reschedule)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
        logger.info("✅ 已启动任务定期清理定时器（每24小时）")

    def stop_task(self, task_id: str) -> bool:
        """
        请求停止指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功设置停止标志
        """
        if task_id in self.active_tasks:
            self._stop_flags[task_id] = True
            logger.info(f"🛑 任务 {task_id}: 已设置停止标志")
            return True
        logger.warning(f"⚠️ 任务 {task_id}: 未找到活跃任务，无法设置停止标志")
        return False
    
    def is_task_stopped(self, task_id: str) -> bool:
        """
        检查任务是否被请求停止
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否已请求停止
        """
        return self._stop_flags.get(task_id, False)
    
    def _check_stop_flag(self, task_id: str, message: str = "任务被用户停止") -> None:
        """
        检查停止标志，如果设置了则抛出异常中断执行
        
        Args:
            task_id: 任务ID
            message: 停止时的异常消息
            
        Raises:
            InterruptedError: 当停止标志被设置时
        """
        # 检查本地停止标志
        if self._stop_flags.get(task_id, False):
            logger.info(f"🛑 任务 {task_id}: {message}")
            raise InterruptedError(message)
        
        # 🔥 检查全局 Ctrl+C 停止标志（双击 Ctrl+C）
        try:
            from web.web_server_refactored import is_stop_requested
            if is_stop_requested():
                logger.info(f"🛑 任务 {task_id}: 检测到 Ctrl+C 停止信号")
                raise InterruptedError("用户按 Ctrl+C 请求停止")
        except ImportError:
            pass  # 如果导入失败，忽略

    def _update_task_status(self, task_id: str, status: str, progress: int = None, error: Optional[str] = None, 
                            current_step: str = None, step_status: Dict = None, points_consumed: int = None):
        """更新任务状态和进度 - 支持详细步骤状态和创造点消耗
        
        Args:
            progress: 进度值(0-100)，如果为None则保持已有进度不变
        """
        # 🔥 修复：即使task_id不在task_results中，也要初始化它（防止任务初始化失败导致的404）
        if task_id not in self.task_results:
            logger.info(f"⚠️ 任务 {task_id} 不在 task_results 中，初始化基础结构")
            self.task_results[task_id] = {
                "task_id": task_id,
                "status": status,
                "progress": progress if progress is not None else 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "step_status": {},
                "sub_step_progress": {},  # 🔥 新增：子步骤进度跟踪
                "points_consumed": 0,
                "points_total": 400
            }
        else:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            # 🔥 修复：只有当 progress 不为 None 时才更新进度
            if progress is not None:
                update_data["progress"] = progress
            self.task_results[task_id].update(update_data)
            if error:
                self.task_results[task_id]["error"] = error

        # 🔥 修复：始终更新task_progress，确保get_task_progress能返回数据
        task_progress_data = {
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        # 🔥 修复：只有当 progress 不为 None 时才更新进度
        if progress is not None:
            task_progress_data["progress"] = progress
        else:
            # 保持已有进度
            task_progress_data["progress"] = self.task_results[task_id].get("progress", 0)
        
        self.task_progress[task_id] = task_progress_data
        if error:
            self.task_progress[task_id]["error"] = error
        
        # 更新当前步骤（如果提供了）
        if current_step:
            self.task_results[task_id]["current_step"] = current_step
            self.task_progress[task_id]["current_step"] = current_step
            
            # 🔥 基于 14 个标准步骤重新计算进度百分比（支持子步骤细粒度进度）
            phase_one_steps = [
                'creative_refinement',      # 1. 创意精炼
                'fanfiction_detection',     # 2. 同人检测
                'multiple_plans',           # 3. 生成多个方案
                'plan_selection',           # 4. 选择最佳方案
                'foundation_planning',      # 5. 基础规划（写作风格+市场分析）
                'worldview_with_factions',  # 6. 世界观与势力系统
                'character_design',         # 7. 核心角色设计
                'emotional_growth_planning', # 8. 情绪蓝图与成长规划
                'stage_plan',               # 9. 全书阶段计划
                'detailed_stage_plans',     # 10. 阶段详细计划
                'expectation_mapping',      # 11. 期待感映射
                'system_init',              # 12. 系统初始化
                'saving',                   # 13. 保存设定结果
                'quality_assessment'        # 14. AI质量评估
            ]
            
            # 🔥 修复：自动更新 step_status，将当前步骤及之前的步骤标记为完成
            if "step_status" not in self.task_results[task_id]:
                self.task_results[task_id]["step_status"] = {}
            if "sub_step_progress" not in self.task_results[task_id]:
                self.task_results[task_id]["sub_step_progress"] = {}
            
            if current_step in phase_one_steps:
                step_index = phase_one_steps.index(current_step)
                
                # 🔥 获取当前已有进度（如果 progress 为 None，使用已有进度）
                current_progress = self.task_results[task_id].get("progress", 0)
                
                # 🔥 修复：优先使用传入的进度，只在需要时计算基础进度
                calculated_progress = int((step_index / (len(phase_one_steps) - 1)) * 100)
                
                # 只有在以下情况才使用计算进度：
                # 1. 没有传入进度（为0或None）
                # 2. 传入进度明显异常（与计算进度相差超过50%，可能是错误值）
                if progress is None or progress == 0:
                    progress = calculated_progress
                elif abs(progress - calculated_progress) > 50:
                    # 传入进度与计算进度相差过大，可能是错误，使用计算进度
                    self.logger.warning(f"任务 {task_id}: 传入进度 {progress}% 与计算进度 {calculated_progress}% 相差过大，使用计算进度")
                    progress = calculated_progress
                # 否则保留传入的进度（信任调用方提供的精确值）
                
                # 🔥 新增：如果是 detailed_stage_plans，根据子步骤计算细粒度进度
                if current_step == 'detailed_stage_plans':
                    if step_status and isinstance(step_status, dict) and 'sub_step' in step_status:
                        sub_progress = self._calculate_detailed_stage_progress(task_id, step_status)
                        # 将子步骤进度叠加到基础进度上（detailed_stage_plans 占 69% ~ 77%，跨度8%）
                        progress = 69 + int(sub_progress * 0.08)
                    else:
                        # 如果没有子步骤信息，使用默认进度（69% + 阶段内偏移）
                        progress = 69
                
                self.task_results[task_id]["progress"] = progress
                
                # 🔥 更新所有步骤状态：之前的完成，当前的进行中，之后的等待中
                for i, step in enumerate(phase_one_steps):
                    if i < step_index:
                        self.task_results[task_id]["step_status"][step] = "completed"
                    elif i == step_index:
                        self.task_results[task_id]["step_status"][step] = "active"
                    else:
                        if step not in self.task_results[task_id]["step_status"]:
                            self.task_results[task_id]["step_status"][step] = "waiting"
            else:
                # 对于不在标准列表中的步骤，只标记当前为active
                self.task_results[task_id]["step_status"][current_step] = "active"
        else:
            # 🔥 修复：检查是否是第二阶段任务
            task_result = self.task_results.get(task_id, {})
            is_phase_two = task_result.get("generation_mode") == "phase_two_only" or \
                          (task_result.get("from_chapter") is not None and task_result.get("chapters_to_generate") is not None)
            
            if is_phase_two:
                # 第二阶段步骤映射
                step_mapping = {
                    0: "initialization",
                    10: "initializing",
                    20: "initializing", 
                    25: "loading_project",
                    30: "preparing",
                    35: "starting_generation",
                    40: "generating_chapters",
                    60: "generating_chapters",
                    80: "generating_chapters",
                    100: "completed"
                }
            else:
                # 使用进度映射（基于 13 个步骤的粗略映射）- 第一阶段
                step_mapping = {
                    0: "initialization",
                    8: "writing_style",
                    15: "market_analysis",
                    23: "worldview",
                    31: "faction_system",
                    38: "character_design",
                    46: "emotional_blueprint",
                    54: "growth_plan",
                    62: "stage_plan",
                    69: "detailed_stage_plans",
                    77: "expectation_mapping",
                    85: "system_init",
                    92: "saving",
                    100: "quality_assessment"
                }
            # 找到最接近的进度
            closest_progress = min(step_mapping.keys(), key=lambda x: abs(x - progress))
            current_step = step_mapping.get(closest_progress, "initialization")
            self.task_results[task_id]["current_step"] = current_step
            self.task_progress[task_id]["current_step"] = current_step
        
        # 更新详细步骤状态（如果提供了）
        if step_status:
            if "step_status" not in self.task_results[task_id]:
                self.task_results[task_id]["step_status"] = {}
            
            # 🔥 统一格式：简单的 {step_name: status} 字典
            if isinstance(step_status, dict):
                self.task_results[task_id]["step_status"].update(step_status)
                logger.info(f"任务 {task_id}: 更新步骤状态: {step_status}")
        
        # 更新创造点消耗（如果提供了）
        if points_consumed is not None:
            self.task_results[task_id]["points_consumed"] = points_consumed
        
        # 🔥 修复：处理 progress 为 None 的情况
        log_progress = progress if progress is not None else self.task_results[task_id].get("progress", 0)
        logger.info(f"任务 {task_id}: 进度更新 {log_progress}% - 当前步骤: {current_step}")
        
        # 🔥 新增：持久化保存任务状态
        try:
            from web.utils.task_persistence import TaskPersistence
            TaskPersistence.save_task(self.task_results[task_id])
        except Exception as e:
            logger.warning(f"⚠️ 保存任务状态失败: {e}")

    def update_step_status(self, task_id: str, step_name: str, status: str, points_cost: int = 0):
        """更新特定步骤的状态和创造点消耗"""
        if task_id not in self.task_results:
            return
        
        # 初始化步骤状态
        if "step_status" not in self.task_results[task_id]:
            self.task_results[task_id]["step_status"] = {}
        
        # 更新步骤状态
        self.task_results[task_id]["step_status"][step_name] = status
        
        # 累加创造点消耗
        if points_cost > 0:
            current_points = self.task_results[task_id].get("points_consumed", 0)
            self.task_results[task_id]["points_consumed"] = current_points + points_cost
        
        logger.info(f"任务 {task_id}: 步骤 {step_name} 更新为 {status}, 创造点: +{points_cost}")

    def _calculate_detailed_stage_progress(self, task_id: str, step_status: Dict) -> int:
        """
        计算 detailed_stage_plans 步骤的子步骤进度
        
        detailed_stage_plans 步骤包含4个阶段（起承转合），每个阶段有7个子步骤：
        1. emotional_plan - 情绪计划
        2. major_event_skeletons - 重大事件骨架
        3. event_decomposition - 事件分解
        4. continuity_assessment - 连续性评估
        5. scene_assembly - 场景组装
        6. character_inference - 角色推断
        7. supporting_characters - 配角生成
        
        总共 4 * 7 = 28 个子步骤
        """
        try:
            # 获取当前阶段和子步骤
            sub_step = step_status.get('sub_step', '')
            stage_name = step_status.get('stage_name', '')
            sub_step_status = step_status.get('sub_step_status', '')
            
            # 定义阶段顺序
            stages = ['opening_stage', 'rising_stage', 'turning_stage', 'resolution_stage']
            # 定义子步骤顺序
            sub_steps = [
                'emotional_plan',
                'major_event_skeletons', 
                'event_decomposition',
                'continuity_assessment',
                'scene_assembly',
                'character_inference',
                'supporting_characters'
            ]
            
            # 计算已完成的子步骤数量
            completed_count = 0
            
            # 计算已完成阶段数
            current_stage_index = stages.index(stage_name) if stage_name in stages else 0
            completed_count += current_stage_index * len(sub_steps)
            
            # 计算当前阶段已完成的子步骤数
            if sub_step in sub_steps:
                current_sub_index = sub_steps.index(sub_step)
                if sub_step_status in ['completed', 'active']:
                    completed_count += current_sub_index + 1
                else:
                    completed_count += current_sub_index
            
            # 计算进度百分比（0-100）
            total_sub_steps = len(stages) * len(sub_steps)  # 28
            progress = int((completed_count / total_sub_steps) * 100)
            
            return min(progress, 100)
            
        except Exception as e:
            logger.warning(f"计算详细阶段进度失败: {e}")
            return 0

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id not in self.task_results:
            return {"error": "任务不存在"}
        return self.task_results[task_id]

    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度 - 包含详细步骤状态和点数消耗"""
        progress = self.task_progress.get(task_id, {})
        
        if task_id in self.task_results:
            task_data = self.task_results[task_id]
            # 🔥 添加详细步骤状态
            step_status = task_data.get("step_status", {})
            if step_status:
                progress["step_status"] = step_status
            # 🔥 添加点数消耗信息
            progress["points_consumed"] = task_data.get("points_consumed", 0)
            progress["points_total"] = task_data.get("points_total", 400)
        
        return progress

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return list(self.task_results.values())

    def load_existing_novels(self):
        """从文件系统加载已存在的小说项目 - 支持新旧路径结构"""
        # 添加线程锁保护，避免并发调用导致文件I/O错误
        import threading
        lock = getattr(self, '_load_lock', None)
        if lock is None:
            lock = threading.Lock()
            self._load_lock = lock
        
        with lock:
            self._load_existing_novels_impl()
    
    def _load_existing_novels_impl(self):
        """实际加载小说项目的实现 - 支持用户隔离"""
        try:
            # 导入路径配置
            from src.config.path_config import path_config
            
            username = get_current_username()
            logger.info(f"👤 当前用户: {username} (管理员: {is_admin(username)})")
            
            # 获取所有可访问的项目
            projects = list_user_projects(username, include_public=True)
            
            if not projects:
                logger.info("📁 没有找到小说项目")
                return
            
            logger.info(f"🔍 扫描到 {len(projects)} 个可访问的小说项目...")

            for project in projects:
                try:
                    project_path = Path(project['path'])
                    title = project['title']
                    owner = project['owner']
                    
                    # 查找项目信息文件
                    project_info_path = self._find_project_info_file(project_path)
                    
                    if project_info_path and project_info_path.exists():
                        # 🔥 使用 utf-8-sig 编码来处理带 BOM 的 UTF-8 文件
                        with open(project_info_path, 'r', encoding='utf-8-sig') as f:
                            content = f.read()
                            novel_data = json.loads(content)
                        
                        # 加载项目数据，添加 owner 信息
                        self._load_project_from_data(title, novel_data, title, owner=owner)
                        
                        owner_label = "[公共]" if project['is_public'] else f"[{owner}]"
                        logger.info(f"✅ 加载小说项目 {owner_label}: {title}")
                    else:
                        logger.warning(f"⚠️ 项目信息文件不存在: {project_path}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON解析失败 {project['path']}: {e}")
                except Exception as e:
                    logger.error(f"❌ 加载项目失败 {project['title']}: {e}")

            logger.info(f"📚 总共加载了 {len(self.novel_projects)} 个小说项目")

        except Exception as e:
            logger.error(f"❌ 加载已存在小说项目失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
    
    def _find_project_info_file(self, project_path: Path) -> Optional[Path]:
        """查找项目信息文件"""
        # 🔥 修复：优先查找新的标准文件名 "项目信息.json"
        info_file = project_path / "项目信息.json"
        if info_file.exists():
            return info_file
        
        # 备选：旧版本的 "小说名_项目信息.json"
        info_file = project_path / f"{project_path.name}_项目信息.json"
        if info_file.exists():
            return info_file
        
        # 备选：project_info.json
        info_file = project_path / "project_info.json"
        if info_file.exists():
            return info_file
        
        # 备选：project_info/ 子目录
        info_dir = project_path / "project_info"
        if info_dir.is_dir():
            json_files = list(info_dir.glob("*_项目信息*.json"))
            if json_files:
                return json_files[0]
        
        return None

    def _load_project_from_data(self, title: str, novel_data: Dict, path_key: str, owner: str = None):
        """从已加载的数据中提取并加载项目信息（辅助方法）"""
        try:
            from src.config.path_config import path_config
            
            # 添加所有者信息
            if owner:
                novel_data['owner'] = owner
            
            # 🔥 修复：使用owner作为username获取正确的用户隔离路径
            # 如果owner为None，尝试从novel_data获取
            username = owner if owner else novel_data.get('owner')
            logger.info(f"[DEBUG] 加载项目 {title}, username={username}, owner={owner}")
            paths = path_config.get_project_paths(title, username=username)
            logger.info(f"[DEBUG] chapters_dir={paths.get('chapters_dir')}")
            chapter_dirs = [
                Path(paths["chapters_dir"]),  # 新路径：小说项目/小说名/chapters
                Path("小说项目") / f"{title}_章节",   # 旧路径：小说项目/小说名_章节
                Path("小说项目") / title / "chapters"  # 兼容路径：小说项目/小说名/chapters
            ]
            
            generated_chapters = {}
            actual_chapter_dir = None

            # 尝试从多个可能的章节目录加载
            logger.info(f"[DEBUG] 尝试加载章节，目录列表: {[str(d) for d in chapter_dirs]}")
            for chapter_dir in chapter_dirs:
                logger.info(f"[DEBUG] 检查目录: {chapter_dir}, exists={chapter_dir.exists()}")
                if chapter_dir.exists():
                    actual_chapter_dir = chapter_dir
                    
                    # 查找章节文件（支持.txt和.json格式）
                    chapter_files = list(chapter_dir.glob("第*.txt")) + list(chapter_dir.glob("第*.json"))
                    logger.info(f"[DEBUG] 找到 {len(chapter_files)} 个章节文件")
                    
                    for chapter_file in chapter_files:
                        # 提取章节号
                        try:
                            match = re.search(r'第(\d+)章', chapter_file.name)
                            if match:
                                chapter_num = int(match.group(1))
                            else:
                                continue
                            with open(chapter_file, 'r', encoding='utf-8') as cf:
                                file_content = cf.read()

                            # 尝试解析JSON文件并提取内容
                            try:
                                chapter_json = json.loads(file_content)
                                chapter_content = chapter_json.get("content", file_content)
                                chapter_title = chapter_json.get("chapter_title", chapter_file.stem.replace("第", "").replace("章", ""))
                                chapter_word_count = chapter_json.get("word_count", len(chapter_content))
                                # 🔥 新增：读取质量分和质量评估
                                chapter_quality_score = chapter_json.get("quality_score")
                                chapter_quality_assessment = chapter_json.get("quality_assessment", {})

                            except json.JSONDecodeError:
                                # 如果不是JSON格式，直接使用原始内容
                                chapter_content = file_content
                                chapter_title = chapter_file.stem.replace("第", "").replace("章", "")
                                chapter_word_count = len(chapter_content)
                                chapter_quality_score = None
                                chapter_quality_assessment = {}

                            generated_chapters[chapter_num] = {
                                "chapter_number": chapter_num,
                                "title": chapter_title,
                                "content": chapter_content,
                                "word_count": chapter_word_count,
                                "file_path": str(chapter_file),
                                # 🔥 新增：保存质量分信息
                                "quality_score": chapter_quality_score,
                                "quality": chapter_quality_assessment
                            }
                        except Exception as e:
                            logger.info(f"⚠️ 加载章节 {chapter_file.name} 失败: {e}")
                    
                    break  # 找到有效的章节目录后停止搜索

            # 更新小说数据
            novel_data["generated_chapters"] = generated_chapters
            novel_data["creation_time"] = novel_data.get("creation_time", datetime.now().isoformat())
            
            # 添加章节目录信息
            if actual_chapter_dir:
                novel_data["chapter_directory"] = str(actual_chapter_dir)

            # 加载质量数据
            quality_data = self.load_quality_data(title, username=username)
            novel_data["quality_data"] = quality_data

            # 🔥 修复：从独立文件加载写作风格指南
            try:
                writing_style_path = Path(paths.get("writing_style_guide", ""))
                if writing_style_path.exists():
                    with open(writing_style_path, 'r', encoding='utf-8') as f:
                        writing_style_guide = json.load(f)
                    novel_data["writing_style_guide"] = writing_style_guide
                    logger.info(f"  ✅ 已加载写作风格指南: {len(writing_style_guide)} 个键")
                else:
                    # 如果独立文件不存在，尝试从项目信息中获取
                    if novel_data.get("writing_style_guide"):
                        logger.info(f"  ✅ 从项目信息中获取写作风格指南")
                    else:
                        # 只在非 anonymous 用户时打印警告，避免启动时大量警告
                        if username and username != 'anonymous':
                            logger.warning(f"  ⚠️ 写作风格指南文件不存在: {writing_style_path}")
                        novel_data["writing_style_guide"] = {}
            except Exception as e:
                logger.warning(f"  ⚠️ 加载写作风格指南失败: {e}")
                novel_data["writing_style_guide"] = novel_data.get("writing_style_guide", {})

            # 添加到项目集合
            self.novel_projects[title] = novel_data
            logger.info(f"[DEBUG] 项目 {title} 已加载 {len(generated_chapters)} 章, 实际目录: {actual_chapter_dir}")

        except Exception as e:
            logger.error(f"❌ 处理项目数据 {title} 失败: {e}")

    def load_quality_data(self, title: str, username: str = None) -> Dict[str, Any]:
        """加载小说的质量数据"""
        # 导入路径配置
        from src.config.path_config import path_config
        
        # 获取安全的标题
        safe_title = path_config.get_safe_title(title)
        
        quality_data = {
            "character_development": {},
            "world_state": {},
            "events": [],
            "writing_plans": {},
            "relationships": {},
            "chapter_failures": []
        }

        try:
            # 🔥 修复：使用username获取正确的用户隔离路径
            paths = path_config.get_project_paths(title, username=username)
            
            # 基础路径 - 使用新的目录结构
            novel_base = Path(paths["project_root"])
            quality_base = Path("quality_data")  # 保留作为后备
            chapter_base = Path("chapter_failures")

            # 加载角色发展数据 - 优先从新路径加载
            character_file = Path(paths.get("character_development", novel_base / "character_development" / f"{title}_character_development.json"))
            if not character_file.exists():
                character_file = quality_base / f"{title}_character_development.json"
            
            if character_file.exists():
                with open(character_file, 'r', encoding='utf-8') as f:
                    quality_data["character_development"] = json.load(f)

            # 加载世界观数据 - 优先从新路径加载
            world_file = Path(paths["world_state"])
            if not world_file.exists():
                world_file = quality_base / f"{title}_world_state.json"
            
            if world_file.exists():
                with open(world_file, 'r', encoding='utf-8') as f:
                    quality_data["world_state"] = json.load(f)

            # 加载事件数据 - 优先从新路径加载
            events_file = Path(paths.get("events", novel_base / "events" / f"{title}_events.json"))
            if not events_file.exists():
                events_file = quality_base / f"{title}_events.json"
            
            if events_file.exists():
                with open(events_file, 'r', encoding='utf-8') as f:
                    quality_data["events"] = json.load(f)

            # 加载思维设定数据 - 新增
            mindset_dir = Path(paths.get("mindset_dir", novel_base / "mindset"))
            if mindset_dir.exists():
                quality_data["mindset"] = {}
                mindset_files = list(mindset_dir.glob(f"{title}_mindset_*.json"))
                for mindset_file in mindset_files:
                    with open(mindset_file, 'r', encoding='utf-8') as f:
                        mindset_data = json.load(f)
                        character_name = mindset_file.stem.replace(f"{title}_mindset_", "")
                        quality_data["mindset"][character_name] = mindset_data

            # 加载事件详细记录（JSONL格式）
            events_jsonl = quality_base / "events" / f"{title}_events.jsonl"
            if events_jsonl.exists():
                events = []
                with open(events_jsonl, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                quality_data["detailed_events"] = events

            # 加载写作计划 - 从新路径加载（支持 planning 和 plans 两个目录）
            planning_dir = Path(paths.get("writing_plans_dir", novel_base / "planning"))
            plans_dir = novel_base / "plans"  # 🔥 新增：也支持 plans 目录
            
            # 检查两个目录
            plan_files = []
            
            # 优先从 plans 目录加载（包含四个阶段文件）
            if plans_dir.exists():
                plan_files = list(plans_dir.glob(f"*_stage_writing_plan.json"))
                if plan_files:
                    logger.info(f"✅ 从 plans 目录找到 {len(plan_files)} 个阶段写作计划文件")
            
            # 如果 plans 目录没有，尝试 planning 目录
            if not plan_files and planning_dir.exists():
                plan_files = list(planning_dir.glob(f"{title}*writing_plan*.json"))
                
                # 如果没找到，尝试直接匹配常见文件名格式
                if not plan_files:
                    common_names = [
                        planning_dir / f"{title}_写作计划.json",
                        planning_dir / f"{safe_title}_写作计划.json"
                    ]
                    for common_name in common_names:
                        if common_name.exists():
                            plan_files = [common_name]
                            logger.info(f"✅ 通过常见文件名找到写作计划: {common_name}")
                            break
            
            # 🔥 修复：处理找到的所有计划文件（无论来自哪个目录）
            for plan_file in plan_files:
                try:
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan_data = json.load(f)
                    
                    # 🔥 修复：从文件名提取阶段名
                    # 文件名格式：吞噬万界：从一把生锈铁剑开始_opening_stage_writing_plan.json
                    # 🔥 调试：打印文件名
                    logger.info(f"[PLAN_DEBUG] 处理文件: {plan_file.name}, 路径: {plan_file}")
                    
                    # 🔥 改进：更 robust 的阶段名提取
                    stage_name = None
                    
                    # 方法1：从文件名提取
                    match = re.search(r'_(.+?)_stage_writing_plan\.json$', plan_file.name)
                    if match:
                        stage_name = match.group(1)
                        logger.info(f"[PLAN_DEBUG] 正则匹配成功: {plan_file.name} -> stage_name={stage_name}")
                    
                    # 方法2：尝试从stem提取（备用）
                    if not stage_name:
                        stem = plan_file.stem  # 例如: 诡异降临：我的首秀是带货_opening_stage
                        parts = stem.split('_')
                        for i, part in enumerate(parts):
                            if 'stage' in part.lower() and i > 0:
                                # 重建阶段名
                                stage_parts = []
                                for j in range(max(0, i-2), i+1):  # 多取几个部分确保完整
                                    if j < len(parts):
                                        stage_parts.append(parts[j])
                                stage_name = '_'.join(stage_parts)
                                # 清理阶段名
                                stage_name = stage_name.replace('_writing', '').replace('_plan', '')
                                if stage_name:
                                    logger.info(f"[PLAN_DEBUG] 从stem提取阶段名: {plan_file.name} -> {stage_name}")
                                    break
                    
                    # 方法3：从文件内容提取
                    if not stage_name:
                        logger.info(f"[PLAN_DEBUG] 尝试从数据中提取: {plan_file.name}")
                        if isinstance(plan_data, dict):
                            stage_writing_plan = plan_data.get("stage_writing_plan", {})
                            if isinstance(stage_writing_plan, dict):
                                stage_name = stage_writing_plan.get("stage_name", "")
                            if not stage_name:
                                # 尝试从其他字段提取
                                stage_name = plan_data.get("stage_name", "")
                        if stage_name:
                            logger.info(f"[PLAN_DEBUG] 从数据中提取阶段名: {stage_name}")
                    
                    # 如果都失败了，使用unknown
                    if not stage_name:
                        stage_name = "unknown"
                        logger.warning(f"[PLAN_DEBUG] 无法提取阶段名，使用unknown: {plan_file.name}")
                    
                    quality_data["writing_plans"][stage_name] = plan_data
                    logger.info(f"✅ 已加载写作计划: {plan_file.name} -> 阶段: {stage_name}")
                except Exception as e:
                    logger.error(f"❌ 加载写作计划失败 {plan_file}: {e}")

            # 加载关系数据
            relationships_file = Path(paths.get("relationships", novel_base / "relationships.json"))
            if not relationships_file.exists():
                relationships_file = quality_base / "relationships" / f"{title}_relationships.json"
            
            if relationships_file.exists():
                with open(relationships_file, 'r', encoding='utf-8') as f:
                    quality_data["relationships"] = json.load(f)

            # 加载章节失败记录
            failures_file = chapter_base / f"failures_{title}.json"
            if failures_file.exists():
                with open(failures_file, 'r', encoding='utf-8') as f:
                    failures = json.load(f)
                    # 按章节号组织失败记录
                    chapter_failures = {}
                    for failure in failures if isinstance(failures, list) else [failures]:
                        chapter_num = failure.get("chapter_number", 0)
                        if chapter_num not in chapter_failures:
                            chapter_failures[chapter_num] = []
                        chapter_failures[chapter_num].append(failure)
                    quality_data["chapter_failures"] = chapter_failures

            logger.info(f"📊 加载质量数据完成: {title}")

        except Exception as e:
            logger.error(f"❌ 加载质量数据失败 {title}: {e}")

        return quality_data

    def get_novel_projects(self) -> List[Dict[str, Any]]:
        """获取所有小说项目（根据当前用户过滤）- 动态加载"""
        projects = []
        current_user = get_current_username()
        is_user_admin = is_admin(current_user)
        
        # 🔥 动态加载当前用户的项目，而不是使用启动时缓存的 self.novel_projects
        from web.utils.path_utils import list_user_projects
        user_projects = list_user_projects(current_user, include_public=True)
        
        # 重新加载项目数据
        for project_info in user_projects:
            try:
                title = project_info['title']
                owner = project_info['owner']
                project_path = Path(project_info['path'])
                
                # 查找项目信息文件
                project_info_path = self._find_project_info_file(project_path)
                
                if project_info_path and project_info_path.exists():
                    # 🔥 使用 utf-8-sig 编码来处理带 BOM 的 UTF-8 文件
                    with open(project_info_path, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)
                    # 添加 owner 信息
                    data['owner'] = owner
                else:
                    # 如果没有项目信息文件，创建基本数据结构
                    data = {
                        'novel_title': title,
                        'owner': owner,
                        'generated_chapters': {},
                        'creation_time': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"❌ 动态加载项目失败 {title}: {e}")
                continue
            
            # 🔥 确保数据被添加到 self.novel_projects 缓存（如果不存在）
            if title not in self.novel_projects:
                self.novel_projects[title] = data
            # 用户隔离：只返回当前用户的项目 + 公开项目
            owner = data.get('owner', 'unknown')
            is_public = owner == 'public'
            
            # 非管理员只能看到自己的项目和公开项目
            if not is_user_admin and owner != current_user and not is_public:
                continue
            generated_chapters = data.get("generated_chapters", {})
            completed_chapters = len(generated_chapters)
            
            # 🔥 关键修复：如果内存中没有章节数据，直接从文件系统读取
            if completed_chapters == 0:
                try:
                    chapters_dir = project_path / "chapters"
                    if chapters_dir.exists():
                        chapter_files = list(chapters_dir.glob('第*.json')) + list(chapters_dir.glob('第*.txt'))
                        file_chapter_count = len(chapter_files)
                        if file_chapter_count > 0:
                            completed_chapters = file_chapter_count
                            logger.info(f"[GET_NOVEL_PROJECTS] 项目 {title}: 从文件系统读取到 {file_chapter_count} 个章节文件")
                except Exception as e:
                    logger.warning(f"[GET_NOVEL_PROJECTS] 从文件系统读取章节失败: {e}")
            
            # 计算总字数
            total_word_count = 0
            for chapter_num, chapter_data in generated_chapters.items():
                if isinstance(chapter_data, dict):
                    total_word_count += chapter_data.get("word_count", 0)
                else:
                    total_word_count += len(str(chapter_data))
            
            # 计算平均评分
            total_score = 0
            scored_chapters = 0
            for chapter_num, chapter_data in generated_chapters.items():
                if isinstance(chapter_data, dict):
                    quality_assessment = chapter_data.get("quality_assessment", {})
                    if quality_assessment and "overall_score" in quality_assessment:
                        total_score += quality_assessment["overall_score"]
                        scored_chapters += 1
            
            average_score = total_score / scored_chapters if scored_chapters > 0 else 0
            
            # 辅助函数：安全获取整数章节数
            def _get_int_chapters(data_dict, *keys, default=0):
                """安全地从嵌套字典中获取整数章节数"""
                try:
                    val = data_dict
                    for key in keys:
                        if not isinstance(val, dict):
                            return default
                        val = val.get(key, default)
                    # 转换为整数
                    return int(val) if val is not None else default
                except (ValueError, TypeError):
                    return default
            
            # 获取目标章节数，优先从数据中获取，否则使用已生成章节数
            # 修复：正确的字段路径是 progress.total_chapters，而不是 current_progress.total_chapters
            # 修复：确保所有值都转换为整数后再比较
            target_chapters = (
                _get_int_chapters(data, "progress", "total_chapters") if _get_int_chapters(data, "progress", "total_chapters") > 0 else
                (_get_int_chapters(data, "total_chapters") if _get_int_chapters(data, "total_chapters") > 0 else
                (_get_int_chapters(data, "novel_info", "total_chapters") if _get_int_chapters(data, "novel_info", "total_chapters") > 0 else
                (_get_int_chapters(data, "novel_info", "creative_seed", "totalChapters") if _get_int_chapters(data, "novel_info", "creative_seed", "totalChapters") > 0 else
                completed_chapters)))
            )
            
            # 获取核心设定和简介
            creative_seed = data.get("creative_seed", {})
            core_setting = creative_seed.get("coreSetting", "") if isinstance(creative_seed, dict) else str(creative_seed)[:200]
            synopsis = data.get("novel_synopsis", "") or data.get("synopsis", "")
            
            projects.append({
                "title": title,
                "novel_title": title,  # 🔥 修复：添加 novel_title 字段以匹配前端期望
                "total_chapters": int(target_chapters),
                "completed_chapters": completed_chapters,
                "word_count": total_word_count,
                "average_score": round(average_score, 1),
                "created_at": data.get("creation_time", datetime.now().isoformat()),
                "last_updated": data.get("current_progress", {}).get("last_updated", ""),
                "status": "completed" if completed_chapters >= target_chapters and target_chapters > 0 else "generating",
                # 添加前端需要的字段
                "story_synopsis": synopsis,
                "core_setting": core_setting,
                "synopsis": synopsis,  # 保留向后兼容
                # 用户隔离相关字段
                "owner": owner,
                "is_public": is_public,
                "is_owner": owner == current_user or is_public
            })
        return sorted(projects, key=lambda x: x["last_updated"], reverse=True)

    def get_novel_detail(self, title: str) -> Optional[Dict[str, Any]]:
        """获取小说详情，并标准化字段名以兼容前端"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return None
        
        # 获取核心世界观数据 - 尝试从多个字段获取
        core_worldview = novel_data.get("core_worldview", {})
        
        # 如果 core_worldview 为空，尝试从其他字段获取
        if not core_worldview or (isinstance(core_worldview, dict) and len(core_worldview) == 0):
            # 尝试从 quality_data 获取
            quality_data = novel_data.get("quality_data", {})
            if quality_data:
                # 从 world_state 获取世界观信息
                world_state = quality_data.get("world_state", {})
                if world_state:
                    core_worldview = {
                        "worldview": world_state.get("worldview", {}),
                        "setting": world_state.get("setting", {}),
                        "rules": world_state.get("rules", {})
                    }
                
                # 如果仍然为空，尝试从 creative_seed 构建
                if not core_worldview or (isinstance(core_worldview, dict) and len(core_worldview) == 0):
                    creative_seed = novel_data.get("creative_seed", {})
                    if creative_seed:
                        core_worldview = {
                            "core_setting": creative_seed.get("coreSetting", ""),
                            "genre": creative_seed.get("genre", ""),
                            "target_platform": creative_seed.get("targetPlatform", ""),
                            "source_material": creative_seed.get("sourceMaterial", "")
                        }
        
        # 标准化字段名，确保前端能正确读取
        standardized_data = {
            # 保留所有原始字段
            **novel_data,

            # 🔥 修复：同时添加 title 和 novel_title 字段以匹配前端期望
            "title": title,
            "novel_title": title,
            
            # 添加前端期望的字段名映射
            "story_synopsis": novel_data.get("novel_synopsis", "") or novel_data.get("synopsis", ""),
            "core_setting": novel_data.get("creative_seed", {}).get("coreSetting", ""),
            # 🔥 新增：添加 core_worldview 字段，用于视频生成
            "core_worldview": core_worldview if core_worldview else {},
        }
        
        # 🔥 修复：确保 stage_writing_plans 字段存在
        # 从 quality_data.writing_plans 映射到 stage_writing_plans
        if "stage_writing_plans" not in standardized_data or not standardized_data["stage_writing_plans"]:
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                standardized_data["stage_writing_plans"] = writing_plans
                logger.info(f"✅ 从 quality_data.writing_plans 映射到 stage_writing_plans: {len(writing_plans)} 个阶段")
        
        # 🔥 修复：确保 overall_stage_plans 字段存在
        if "overall_stage_plans" not in standardized_data or not standardized_data.get("overall_stage_plans", {}):
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                # 从所有阶段的写作计划中提取 overall_stage_plan
                overall_stage_plan = {}
                for stage_name, stage_data in writing_plans.items():
                    if isinstance(stage_data, dict) and "stage_writing_plan" in stage_data:
                        stage_plan = stage_data["stage_writing_plan"]
                        overall_stage_plan[stage_name] = {
                            "chapter_range": stage_plan.get("chapter_range", ""),
                            "stage_overview": stage_plan.get("stage_overview", ""),
                            "event_system": stage_plan.get("event_system", {})
                        }
                
                if overall_stage_plan:
                    standardized_data["overall_stage_plans"] = {"overall_stage_plan": overall_stage_plan}
                    logger.info(f"✅ 从 writing_plans 构建 overall_stage_plans: {len(overall_stage_plan)} 个阶段")
        
        # 🔥 修复：确保 global_growth_plan 字段存在
        if "global_growth_plan" not in standardized_data or not standardized_data.get("global_growth_plan", {}):
            # 从写作计划中提取成长规划信息
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                # 构建基础的全局成长规划
                global_growth_plan = {
                    "growth_stages": [],
                    "power_systems": {},
                    "world_building": {}
                }
                standardized_data["global_growth_plan"] = global_growth_plan
                logger.info("✅ 创建基础 global_growth_plan 结构")

        # 🔥 修复：确保 writing_style_guide 字段存在（动态加载）
        if "writing_style_guide" not in standardized_data or not standardized_data.get("writing_style_guide"):
            try:
                from src.config.path_config import path_config
                # 🔥 修复：从 novel_data 获取 owner 作为 username
                username = novel_data.get('owner')
                writing_style_path = Path(path_config.get_project_paths(title, username=username).get("writing_style_guide", ""))
                if writing_style_path.exists():
                    with open(writing_style_path, 'r', encoding='utf-8') as f:
                        writing_style_guide = json.load(f)
                    standardized_data["writing_style_guide"] = writing_style_guide
                    logger.info(f"✅ 动态加载写作风格指南成功: {len(writing_style_guide)} 个键")
                else:
                    logger.warning(f"⚠️ 写作风格指南文件不存在: {writing_style_path}")
                    standardized_data["writing_style_guide"] = {}
            except Exception as e:
                logger.warning(f"⚠️ 动态加载写作风格指南失败: {e}")
                standardized_data["writing_style_guide"] = {}

        return standardized_data

    def get_chapter_detail(self, title: str, chapter_num: int) -> Optional[Dict[str, Any]]:
        """获取章节详情"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return None
        return novel_data.get("generated_chapters", {}).get(chapter_num)

    def get_chapter_quality_data(self, title: str, chapter_num: int) -> Dict[str, Any]:
        """获取章节质量数据"""
        quality_data = {
            "character_development": {},
            "world_state": {},
            "events": [],
            "generation_context": {},
            "chapter_failures": [],
            "writing_plan": {},
            "character_relationships": {}
        }

        try:
            # 从项目的质量数据中提取章节相关信息
            novel_data = self.novel_projects.get(title)
            if not novel_data or "quality_data" not in novel_data:
                return quality_data

            project_quality = novel_data["quality_data"]

            # 获取角色发展数据（过滤到当前章节）
            character_data = project_quality.get("character_development", {})
            if character_data and isinstance(character_data, dict):
                # 提取在当前章节活跃的角色
                active_characters = {}
                for char_name, char_info in character_data.items():
                    if isinstance(char_info, dict) and char_info.get("first_appearance_chapter", 0) <= chapter_num <= char_info.get("last_updated_chapter", 0):
                        active_characters[char_name] = char_info
                quality_data["character_development"] = active_characters

            # 获取世界观数据
            quality_data["world_state"] = project_quality.get("world_state", {})

            # 获取事件数据（过滤到当前章节）
            all_events = project_quality.get("detailed_events", [])
            if isinstance(all_events, list):
                chapter_events = [event for event in all_events if isinstance(event, dict) and event.get("chapter_number") == chapter_num]
            else:
                chapter_events = []
            quality_data["events"] = chapter_events

            # 获取章节失败记录
            chapter_failures_data = project_quality.get("chapter_failures", {})
            if isinstance(chapter_failures_data, dict):
                chapter_failures = chapter_failures_data.get(chapter_num, [])
                if not isinstance(chapter_failures, list):
                    chapter_failures = []
            else:
                chapter_failures = []
            quality_data["chapter_failures"] = chapter_failures

            # 获取当前章节的写作计划
            writing_plans = project_quality.get("writing_plans", {})
            for stage_name, plan_data in writing_plans.items():
                # 确保plan_data是字典类型
                if not isinstance(plan_data, dict):
                    continue
                
                stage_writing_plan = plan_data.get("stage_writing_plan", {})
                # 确保stage_writing_plan也是字典类型
                if not isinstance(stage_writing_plan, dict):
                    continue
                    
                chapter_range = stage_writing_plan.get("chapter_range", "")
                if self._is_chapter_in_range(chapter_num, chapter_range):
                    quality_data["writing_plan"] = plan_data
                    break

            # 获取关系数据
            quality_data["character_relationships"] = project_quality.get("relationships", {})

        except Exception as e:
            logger.error(f"❌ 获取章节质量数据失败 {title} 第{chapter_num}章: {e}")

        return quality_data

    def _is_chapter_in_range(self, chapter_num: int, chapter_range: str) -> bool:
        """检查章节是否在范围内"""
        try:
            if not chapter_range or "-" not in chapter_range:
                return False

            start_str, end_str = chapter_range.replace(" ", "").split("-")
            start = int(start_str)
            end = int(end_str)
            return start <= chapter_num <= end
        except:
            return False

    def export_novel(self, title: str, format_type: str = "json", username: str = None) -> Dict[str, Any]:
        """导出小说"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return {"error": "小说不存在"}

        if format_type == "json":
            return novel_data
        elif format_type == "text":
            # 生成文本格式
            text_content = []
            text_content.append(f"# {novel_data.get('novel_title', '未命名')}")
            text_content.append(f"## 简介\n{novel_data.get('story_synopsis', '')}")
            text_content.append("---\n")

            # 🔥 修复：从文件系统加载章节内容（支持用户隔离路径）
            try:
                from src.utils.path_manager import path_manager
                
                # 如果没有提供username，尝试从novel_data获取owner
                if not username and 'owner' in novel_data:
                    username = novel_data['owner']
                
                # 从文件系统加载所有章节
                chapters = path_manager.get_all_chapters(title, username=username)
                
                if not chapters:
                    # 如果文件系统没有，回退到内存数据
                    chapters = novel_data.get("generated_chapters", {})
                    
                for chapter_num in sorted(chapters.keys()):
                    chapter = chapters[chapter_num]
                    chapter_title = chapter.get('chapter_title', f'第{chapter_num}章')
                    text_content.append(f"## {chapter_title}")
                    text_content.append(chapter.get('content', ''))
                    text_content.append("\n---\n")
                    
            except Exception as e:
                logger.error(f"❌ 导出时加载章节失败: {e}")
                # 回退到内存数据
                chapters = novel_data.get("generated_chapters", {})
                for chapter_num in sorted(chapters.keys()):
                    chapter = chapters[chapter_num]
                    text_content.append(f"## {chapter.get('outline', {}).get('章节标题', f'第{chapter_num}章')}")
                    text_content.append(chapter.get('content', ''))
                    text_content.append("\n---\n")

            return {
                "content": "\n".join(text_content),
                "title": novel_data.get('novel_title', '未命名'),
                "format": "text"
            }
        else:
            return {"error": "不支持的导出格式"}

    def start_generation(self, config: Dict[str, Any]) -> str:
        """启动小说生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        self.task_results[task_id] = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": config,
            "title": config.get("title", "未命名小说"),
            "synopsis": config.get("synopsis", ""),
            "total_chapters": config.get("total_chapters", 200),
            "generation_mode": config.get("generation_mode", "full_auto")
        }
        
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 🔥 新增：持久化保存新创建的任务
        try:
            from web.utils.task_persistence import TaskPersistence
            TaskPersistence.save_task(self.task_results[task_id])
        except Exception as e:
            logger.warning(f"⚠️ 保存新任务失败: {e}")
        
        # 启动后台任务
        def run_generation():
            logger.info(f"任务 {task_id}: 后台线程启动")
            try:
                generation_mode = config.get("generation_mode", "full_auto")
                logger.info(f"任务 {task_id}: 生成模式 = {generation_mode}")
                if generation_mode == "phase_one_only":
                    self._run_phase_one_task(task_id, config)
                else:
                    self._run_generation_task(task_id, config)
            except Exception as e:
                logger.error(f"任务 {task_id}: 生成任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
            finally:
                # 任务结束，取消线程监控
                _thread_monitor.unregister_thread(task_id)
                logger.info(f"任务 {task_id}: 后台线程结束")
        
        # 🔥 修复：使用非daemon线程，并注册到监控器
        thread = threading.Thread(target=run_generation, name=f"Generation-{task_id[:8]}")
        thread.daemon = False  # 重要：改为False，确保线程不被强制终止
        thread.start()
        
        self.task_threads[task_id] = thread
        
        # 注册到线程监控器
        def restart_generation_thread(tid):
            """恢复生成任务"""
            logger.info(f"🔄 尝试恢复任务: {tid}")
            # 检查任务状态，如果还在运行则不重启
            task_info = self.task_results.get(tid, {})
            if task_info.get('status') in ['completed', 'failed']:
                logger.info(f"任务 {tid} 已结束，无需恢复")
                return None
            
            # 重新创建线程
            new_thread = threading.Thread(target=run_generation, name=f"Generation-{tid[:8]}-R")
            new_thread.daemon = False
            new_thread.start()
            self.task_threads[tid] = new_thread
            return new_thread
        
        _thread_monitor.register_thread(task_id, thread, restart_generation_thread)
        
        return task_id

    def _run_phase_one_task(self, task_id: str, config: Dict[str, Any]):
        """执行第一阶段生成任务"""
        logger.info(f"任务 {task_id}: _run_phase_one_task 开始执行")
        try:
            title = config.get("title", "未命名小说")
            is_resume_mode = config.get("is_resume_mode", False)
            
            # 🔥 存储当前用户名供其他方法使用
            self._current_username = config.get('username') or 'unknown'
            
            # 🔥 新增：获取 start_new 参数，用户选择"从新开始"时应删除现有检查点
            start_new = config.get("start_new", False)
            username = config.get('username')
            if start_new:
                logger.info(f"🆕 用户选择从头开始，将删除现有检查点 (用户: {username})")
                self._delete_existing_checkpoint(title, username)
            
            # 创建初始检查点（仅在非恢复模式下）
            if self.checkpoint_enabled and not is_resume_mode:
                self._create_initial_checkpoint(title, config, task_id, self._current_username)
            
            # 🔥 修复：当 start_new=True 时，跳过预更新进度，让 phase_one_generation 全权控制
            # 避免进度从 60% 跳回 0% 的奇怪现象
            if not start_new:
                self._update_task_status(task_id, "generating", 10, current_step="creative_refinement")
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            # 初始化NovelGenerator（使用单例模式，首次初始化后复用）
            try:
                import sys
                from pathlib import Path
                
                # 确保项目根目录在路径中
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                # 使用importlib来动态导入config
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置 - 使用完整的CONFIG而不是简化的配置
                generator_config = CONFIG.copy()
                # 更新一些默认值
                generator_config["defaults"]["total_chapters"] = config.get("total_chapters", 200)
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 🔥 使用单例模式获取生成器实例（首次初始化后复用）
                logger.info(f"任务 {task_id}: 获取 NovelGenerator 实例...")
                novel_generator = get_novel_generator(generator_config)
                logger.info(f"任务 {task_id}: NovelGenerator 实例获取完成")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            
            # 🔥 修复：当 start_new=True 时，跳过预更新进度
            if not start_new:
                # 更新进度
                self._update_task_status(task_id, "generating", 20, current_step="fanfiction_detection")
                
                # 🔥 新增：更新检查点 - 初始化完成
                if self.checkpoint_enabled:
                    self._update_checkpoint(title, "phase_one", "initialization", {"status": "generator_initialized"}, step_status="completed")
                
                logger.info(f"任务 {task_id}: 📋 分析创意种子 (40%)")
                self._update_task_status(task_id, "generating", 40, current_step="multiple_plans")
                
                # 更新检查点 - 开始世界观构建
                if self.checkpoint_enabled:
                    self._update_checkpoint(title, "phase_one", "worldview", {"status": "analyzing_seed"}, step_status="in_progress")
                self._update_task_status(task_id, "generating", 60, current_step="worldview_with_factions")
                
                # 更新检查点 - 开始角色设计（在实际调用前保存为 in_progress）
                if self.checkpoint_enabled:
                    self._update_checkpoint(title, "phase_one", "character_design", {"status": "generating_worldview"}, step_status="in_progress")
            
            try:
                # 为生成器设置进度回调（使用动态属性设置）
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                # 🔥 设置停止检查回调
                setattr(novel_generator, '_stop_check_callback', lambda: self._check_stop_flag(task_id))
                
                # 🔥 设置用户名用于用户隔离路径
                username = config.get('username')
                logger.info(f"任务 {task_id}: 从config获取用户名: {username}")
                if username:
                    novel_generator.set_username(username)
                    logger.info(f"任务 {task_id}: 已设置用户名 {username} 用于用户隔离路径")
                else:
                    logger.warning(f"任务 {task_id}: config中没有用户名，将使用anonymous")
                
                # 🔥 设置用户ID用于API调用实时扣费
                user_id = config.get('user_id')
                if user_id:
                    novel_generator.set_user_id(user_id)
                    logger.info(f"任务 {task_id}: 已设置用户ID {user_id} 用于API调用扣费")
                
                # 🔥 传递 start_new 和 target_platform 参数给生成器
                logger.info(f"任务 {task_id}: 🚀 开始调用 phase_one_generation...")
                logger.info(f"任务 {task_id}: 📋 创意种子: {creative_seed.get('novelTitle', 'N/A')}")
                
                import time
                start_time = time.time()
                success = novel_generator.phase_one_generation(
                    creative_seed,
                    total_chapters,
                    start_new=config.get("start_new", False),
                    target_platform=config.get("target_platform", "fanqie")
                )
                elapsed = time.time() - start_time
                logger.info(f"任务 {task_id}: ✅ phase_one_generation 完成，耗时: {elapsed:.2f}秒, 结果: {success}")
                
                if success:
                    # 标记步骤完成 - 质量评估完成
                    if self.checkpoint_enabled:
                        self._update_checkpoint(title, "phase_one", "quality_assessment", {"status": "completed"}, step_status="completed")
                    
                    self._update_task_status(task_id, "completed", 100, current_step="quality_assessment")
                    
                    # 保存第一阶段结果到任务结果中
                    task_result = self.task_results.get(task_id, {})
                    task_result["result"] = {
                        "novel_title": novel_generator.novel_data.get("novel_title", "未命名"),
                        "total_chapters": total_chapters,
                        "phase_one_completed": True,
                        "next_phase": "second_phase_content_generation",
                        "novel_data_summary": {
                            "core_worldview": novel_generator.novel_data.get("core_worldview", {}),
                            "character_design": novel_generator.novel_data.get("character_design", {}),
                            "overall_stage_plans": novel_generator.novel_data.get("overall_stage_plans", {}),
                            "market_analysis": novel_generator.novel_data.get("market_analysis", {})
                        }
                    }
                    self.task_results[task_id] = task_result
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 第一阶段设定生成失败")
                    self._update_task_status(task_id, "failed", 0, "第一阶段设定生成返回 False")
                    
                    # 标记步骤失败，保留检查点以便恢复
                    if self.checkpoint_enabled:
                        self._update_checkpoint(title, "phase_one", "character_design", {"status": "failed", "error": "第一阶段设定生成返回 False"}, step_status="failed")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: phase_one_generation 执行异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"第一阶段生成过程异常: {str(e)}")
                
                # 标记步骤失败
                if self.checkpoint_enabled:
                    self._update_checkpoint(title, "phase_one", "character_design", {"status": "failed", "error": str(e)}, step_status="failed")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 第一阶段生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")
    
    def _create_initial_checkpoint(self, title: str, config: Dict[str, Any], task_id: str, username: str = None):
        """创建初始检查点，保存创意标题到实际书名的映射"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
             
            # 获取创意标题和创意ID
            creative_seed = config.get("creative_seed", {})
            creative_title = None
            creative_seed_id = None
            
            if isinstance(creative_seed, dict):
                # 尝试从不同字段获取创意标题
                creative_title = (
                    creative_seed.get("novelTitle") or
                    creative_seed.get("title") or
                    creative_seed.get("coreSetting", "")[:50]  # 使用核心设定作为后备
                )
                # 获取创意ID（如果存在）
                creative_seed_id = creative_seed.get("id") or creative_seed.get("seedId")
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
             
            logger.info(f"📁 检查点目录: {checkpoint_mgr.checkpoint_dir}")
            logger.info(f"📄 检查点文件: {checkpoint_mgr.checkpoint_file}")
            
            # 创建检查点数据，包含创意标题映射
            checkpoint_data = {
                'generation_params': config,
                'task_id': task_id,
                'status': 'started',
                'created_at': datetime.now().isoformat()
            }
            
            # 添加创意标题映射信息
            if creative_title:
                checkpoint_data['creative_title'] = creative_title
                logger.info(f"💾 保存创意标题映射: {creative_title} -> {title}")
            
            if creative_seed_id:
                checkpoint_data['creative_seed_id'] = creative_seed_id
                logger.info(f"💾 保存创意ID: {creative_seed_id}")
             
            checkpoint_mgr.create_checkpoint(
                phase='phase_one',
                step='initialization',
                data=checkpoint_data
            )
             
            logger.info(f"✅ 初始检查点已创建: {title}")
             
        except Exception as e:
            logger.error(f"❌ 创建初始检查点失败: {e}")
    
    def _delete_existing_checkpoint(self, title: str, username: str = None):
        """删除现有检查点（用于从头开始生成）"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            
            # 🔥 优先使用传入的用户名，否则使用当前用户名
            actual_username = username or getattr(self, '_current_username', None)
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=actual_username)
            checkpoint_mgr.delete_checkpoint()
             
            logger.info(f"✅ 已删除现有检查点: {title} (用户: {actual_username})")
             
        except Exception as e:
            logger.error(f"❌ 删除检查点失败: {e}")
    
    def _update_checkpoint(self, title: str, phase: str, step: str, data: Dict, step_status: str = "in_progress"):
        """
        更新检查点
        
        Args:
            title: 小说标题
            phase: 生成阶段
            step: 当前步骤
            data: 要保存的数据
            step_status: 步骤状态 (pending/in_progress/completed/failed)
        """
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            
            username = getattr(self, '_current_username', None)
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            
            # 保留原有的生成参数
            existing_checkpoint = checkpoint_mgr.load_checkpoint()
            if existing_checkpoint and 'data' in existing_checkpoint:
                existing_data = existing_checkpoint['data']
                data = {**existing_data, **data}
            
            checkpoint_mgr.create_checkpoint(phase, step, data, step_status)
            logger.info(f"✅ 检查点已更新: {title} - {step} (状态: {step_status})")
            
        except Exception as e:
            logger.error(f"❌ 更新检查点失败: {e}")
    
    def _complete_checkpoint(self, title: str):
        """完成任务时删除检查点"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            
            username = getattr(self, '_current_username', None)
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            success = checkpoint_mgr.delete_checkpoint()
            
            if success:
                logger.info(f"✅ 检查点已删除: {title}（任务完成）")
            
        except Exception as e:
            logger.error(f"❌ 删除检查点失败: {e}")

    def _run_generation_task(self, task_id: str, config: Dict[str, Any]):
        """执行完整生成任务（兼容原有逻辑）"""
        try:
            self._update_task_status(task_id, "generating", 10)
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                
                # 导入完整配置 - 使用绝对路径避免冲突
                import sys
                from pathlib import Path
                
                # 确保项目根目录在路径中
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                # 使用importlib来动态导入config
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置 - 使用完整的CONFIG而不是简化的配置
                generator_config = CONFIG.copy()
                # 更新一些默认值
                generator_config["defaults"]["total_chapters"] = config.get("total_chapters", 200)
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            
            # 更新进度
            self._update_task_status(task_id, "generating", 20)
            self._update_task_status(task_id, "generating", 40)
            self._update_task_status(task_id, "generating", 60)
            try:
                # 为生成器设置进度回调
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                # 🔥 设置停止检查回调（使用全局停止标志）
                def stop_check_callback():
                    from web.web_server_refactored import is_stop_requested
                    if is_stop_requested():
                        raise InterruptedError("用户请求停止生成")
                setattr(novel_generator, '_stop_check_callback', stop_check_callback)
                
                success = novel_generator.full_auto_generation(creative_seed, total_chapters)
                
                if success:
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                        # 检查是否真的生成了文件
                        self._check_generated_files(task_id, config)
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 小说生成失败")
                    self._update_task_status(task_id, "failed", 0, "小说生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: full_auto_generation 执行异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def _check_generated_files(self, task_id: str, config: Dict[str, Any]):
        """检查是否真的生成了小说文件"""
        try:
            # 获取小说标题（从配置或创意种子）
            novel_title = config.get("title") or config.get("creative_seed", {}).get("novelTitle", "未命名小说")
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 🔥 使用用户隔离路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                project_dir = get_user_novel_dir(create=False)
            except Exception:
                project_dir = Path("小说项目")
            
            if not project_dir.exists():
                return False
            
            # 检查具体的小说文件 - 优先使用用户隔离路径
            novel_dir = project_dir / safe_title / "chapters"
            if not novel_dir.exists():
                # 回退到默认路径
                fallback_dir = Path("小说项目")
                novel_dir = fallback_dir / safe_title / "chapters"
                if not novel_dir.exists():
                    novel_dir = fallback_dir / f"{safe_title}_章节"
            
            if novel_dir.exists():
                chapter_files = list(novel_dir.glob("*.txt"))
                
                # 检查文件内容是否为空
                empty_files = 0
                for file_path in chapter_files:
                    if file_path.stat().st_size == 0:
                        empty_files += 1
                
                total_words = 0
                for file_path in chapter_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 尝试解析JSON格式
                            try:
                                chapter_data = json.loads(content)
                                content = chapter_data.get("content", content)
                            except json.JSONDecodeError:
                                # 如果不是JSON格式，使用原始文本
                                pass
                            total_words += len(content)
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 读取章节文件失败: {e}")
                
                return True
                
            else:
                return False
                
        except Exception as e:
            logger.error(f"任务 {task_id}: 检查生成文件时出错: {e}")
            return False

    def _run_resume_task(self, task_id: str, title: str, from_chapter: int, additional_chapters: int):
        """执行续写任务"""
        try:
            logger.info(f"任务 {task_id}: 🚀 开始续写小说: {title}")
            logger.info(f"任务 {task_id}: 从第{from_chapter}章开始，续写{additional_chapters}章")
            
            self._update_task_status(task_id, "loading_data", 10)
            
            # 加载现有小说数据
            novel_detail = self.get_novel_detail(title)
            if not novel_detail:
                logger.error(f"任务 {task_id}: ❌ 无法加载小说数据: {title}")
                self._update_task_status(task_id, "failed", 0, f"无法加载小说数据: {title}")
                return
            
            logger.info(f"任务 {task_id}: ✅ 成功加载小说数据")
            self._update_task_status(task_id, "initializing_generator", 20)
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                # 使用和上面相同的方式导入配置
                try:
                    import importlib.util
                    from pathlib import Path
                    
                    # 确保项目根目录在路径中
                    current_file = Path(__file__).resolve()
                    project_root = current_file.parent.parent.parent
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": from_chapter + additional_chapters,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置
                generator_config = CONFIG.copy()
                generator_config["defaults"]["total_chapters"] = from_chapter + additional_chapters
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                logger.info(f"任务 {task_id}: ✅ NovelGenerator 初始化成功")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 创建 NovelGenerator 失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            self._update_task_status(task_id, "preparing_resume", 30)
            
            # 准备续写数据
            try:
                # 设置小说数据到生成器
                novel_generator.novel_data = novel_detail
                novel_generator.novel_data["is_resuming"] = True
                novel_generator.novel_data["resume_data"] = {
                    "from_chapter": from_chapter,
                    "additional_chapters": additional_chapters,
                    "total_target_chapters": from_chapter + additional_chapters
                }
                
                # 更新进度信息
                novel_generator.novel_data["current_progress"]["total_chapters"] = from_chapter + additional_chapters
                novel_generator.novel_data["current_progress"]["stage"] = "续写生成"
                
                logger.info(f"任务 {task_id}: ✅ 续写数据准备完成")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 准备续写数据失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"准备续写数据失败: {str(e)}")
                return
            
            self._update_task_status(task_id, "generating", 50)
            
            # 🔥 设置停止检查回调（使用全局停止标志）
            def stop_check_callback_resume():
                from web.web_server_refactored import is_stop_requested
                if is_stop_requested():
                    raise InterruptedError("用户请求停止生成")
            setattr(novel_generator, '_stop_check_callback', stop_check_callback_resume)
            
            # 执行续写生成
            try:
                logger.info(f"任务 {task_id}: 📝 开始续写章节生成...")
                
                # 计算实际需要生成的章节范围
                end_chapter = from_chapter + additional_chapters - 1
                
                # 批量生成章节
                success = novel_generator.generate_chapters_batch(from_chapter, end_chapter)
                
                if success:
                    logger.info(f"任务 {task_id}: ✅ 续写生成完成")
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                        logger.info(f"任务 {task_id}: ✅ 项目数据重新加载完成")
                    except Exception as e:
                        logger.info(f"任务 {task_id}: ⚠️ 重新加载项目数据失败: {e}")
                        
                else:
                    logger.error(f"任务 {task_id}: ❌ 续写生成失败")
                    self._update_task_status(task_id, "failed", 0, "续写生成返回失败")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 续写生成过程异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"续写生成异常: {str(e)}")
                
        except Exception as e:
            logger.error(f"任务 {task_id}: 🔥 续写任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def start_resume_generation(self, title: str, from_chapter: int, additional_chapters: int) -> str:
        """启动续写生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化续写任务
        resume_task = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": {
                "title": title,
                "from_chapter": from_chapter,
                "additional_chapters": additional_chapters,
                "total_chapters": from_chapter + additional_chapters,
                "novel_data": self.get_novel_detail(title)
            }
        }
        
        self.task_results[task_id] = resume_task
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 启动后台续写任务
        def run_resume_generation():
            try:
                self._run_resume_task(task_id, title, from_chapter, additional_chapters)
            except Exception as e:
                logger.error(f"续写任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
            finally:
                # 任务结束，取消线程监控
                _thread_monitor.unregister_thread(task_id)
                logger.info(f"续写任务 {task_id}: 后台线程结束")
        
        # 🔥 修复：使用非daemon线程
        thread = threading.Thread(target=run_resume_generation, name=f"Resume-{task_id[:8]}")
        thread.daemon = False
        thread.start()
        
        self.task_threads[task_id] = thread
        
        # 注册到线程监控器
        def restart_resume_thread(tid):
            """恢复续写任务"""
            logger.info(f"🔄 尝试恢复续写任务: {tid}")
            task_info = self.task_results.get(tid, {})
            if task_info.get('status') in ['completed', 'failed']:
                return None
            
            new_thread = threading.Thread(target=run_resume_generation, name=f"Resume-{tid[:8]}-R")
            new_thread.daemon = False
            new_thread.start()
            self.task_threads[tid] = new_thread
            return new_thread
        
        _thread_monitor.register_thread(task_id, thread, restart_resume_thread)
        
        return task_id

    def start_phase_two_generation(self, config: Dict[str, Any]) -> str:
        """启动第二阶段章节生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化第二阶段任务
        phase_two_task = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": config,
            "novel_title": config.get("novel_title", "未命名小说"),
            "phase_one_file": config.get("phase_one_file", ""),
            "from_chapter": config.get("from_chapter", 1),
            "chapters_to_generate": config.get("chapters_to_generate"),
            "generation_mode": "phase_two_only"
        }
        
        self.task_results[task_id] = phase_two_task
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 🔥 新增：持久化保存新创建的任务
        try:
            from web.utils.task_persistence import TaskPersistence
            TaskPersistence.save_task(phase_two_task)
        except Exception as e:
            logger.warning(f"⚠️ 保存新任务失败: {e}")
        
        # 启动后台第二阶段任务
        def run_phase_two_generation():
            try:
                self._run_phase_two_task(task_id, config)
            except Exception as e:
                logger.error(f"第二阶段任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
            finally:
                # 任务结束，取消线程监控
                _thread_monitor.unregister_thread(task_id)
                logger.info(f"第二阶段任务 {task_id}: 后台线程结束")
        
        # 🔥 修复：使用非daemon线程
        thread = threading.Thread(target=run_phase_two_generation, name=f"Phase2-{task_id[:8]}")
        thread.daemon = False
        thread.start()
        
        self.task_threads[task_id] = thread
        
        # 注册到线程监控器
        def restart_phase2_thread(tid):
            """恢复第二阶段任务"""
            logger.info(f"🔄 尝试恢复第二阶段任务: {tid}")
            task_info = self.task_results.get(tid, {})
            if task_info.get('status') in ['completed', 'failed']:
                return None
            
            new_thread = threading.Thread(target=run_phase_two_generation, name=f"Phase2-{tid[:8]}-R")
            new_thread.daemon = False
            new_thread.start()
            self.task_threads[tid] = new_thread
            return new_thread
        
        _thread_monitor.register_thread(task_id, thread, restart_phase2_thread)
        
        return task_id

    def _run_phase_two_task(self, task_id: str, config: Dict[str, Any]):
        """执行第二阶段生成任务"""
        try:
            novel_title = config.get("novel_title", "未命名小说")
            phase_one_file = config.get("phase_one_file", "")
            from_chapter = config.get("from_chapter", 1)
            chapters_to_generate = config.get("chapters_to_generate", 200)
            
            logger.info(f"任务 {task_id}: 🚀 开始第二阶段章节生成")
            logger.info(f"任务 {task_id}: 📚 小说标题: {novel_title}")
            logger.info(f"任务 {task_id}: 📖 起始章节: {from_chapter}")
            logger.info(f"任务 {task_id}: 📊 生成章节数: {chapters_to_generate}")
            
            # 初始化章节进度跟踪字典
            chapter_progress_dict = {}
            for i in range(chapters_to_generate):
                chapter_num = from_chapter + i
                chapter_progress_dict[chapter_num] = {
                    "chapter_number": chapter_num,
                    "status": "pending",
                    "chapter_title": "",
                    "word_count": 0,
                    "error": None
                }
            
            # 定义第二阶段进度计算函数
            def update_phase_two_progress(chapter_num: int, step: str = "generating",
                                         chapter_data: Optional[Dict[str, Any]] = None):
                """根据已生成章节数动态更新进度"""
                # 计算进度：准备阶段30% + 生成阶段(已完成章节数/总章节数)*60%
                if chapter_num < from_chapter:
                    progress = 10  # 初始化阶段
                else:
                    completed = chapter_num - from_chapter + 1
                    progress = 30 + min(int((completed / chapters_to_generate) * 60), 60)
                
                # 更新章节状态
                if chapter_num in chapter_progress_dict and chapter_data:
                    chapter_progress_dict[chapter_num].update({
                        "status": chapter_data.get("status", step),
                        "chapter_title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                        "word_count": chapter_data.get("word_count", 0),
                        "error": chapter_data.get("error")
                    })
                    logger.info(f"任务 {task_id}: 📖 第{chapter_num}章状态: {chapter_progress_dict[chapter_num]['status']}, 字数: {chapter_progress_dict[chapter_num]['word_count']}")
                
                # 更新进度，包含章节进度列表
                self._update_task_status(task_id, step, progress)
                
                # 将章节进度同步到 task_progress 中，供前端查询使用
                if task_id in self.task_progress:
                    # 转换为列表格式供前端使用
                    chapter_progress_list = list(chapter_progress_dict.values())
                    self.task_progress[task_id]["chapter_progress"] = chapter_progress_list
                    self.task_progress[task_id]["current_chapter"] = {
                        "number": chapter_num,
                        "title": chapter_progress_dict.get(chapter_num, {}).get("chapter_title", f"第{chapter_num}章")
                    }
                    self.task_progress[task_id]["total_chapters"] = chapters_to_generate
            
            # 初始化阶段 (10%)
            self._update_task_status(task_id, "initializing", 10)
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                
                import sys
                from pathlib import Path
                
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                generator_config = CONFIG.copy()
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                novel_generator = NovelGenerator(generator_config)
                
                # 🔥 关键修复：设置用户名，确保文件路径正确
                username = config.get("username")
                if username:
                    novel_generator._username = username
                    logger.info(f"任务 {task_id}: 👤 设置用户名: {username}")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            # 初始化完成 (20%)
            self._update_task_status(task_id, "initializing", 20)
            
            # 🔥 修复：加载现有项目数据到NovelGenerator (25%)
            self._update_task_status(task_id, "loading_project", 25)
            
            # 加载现有项目数据
            novel_detail = self.get_novel_detail(novel_title)
            if not novel_detail:
                logger.error(f"任务 {task_id}: ❌ 无法加载小说数据: {novel_title}")
                self._update_task_status(task_id, "failed", 30, f"无法加载小说数据: {novel_title}")
                return
            
            # 关键修复：将 overall_stage_plans 同步到 novel_generator.novel_data
            if "overall_stage_plans" in novel_detail:
                novel_generator.novel_data["overall_stage_plans"] = novel_detail["overall_stage_plans"]
                logger.info(f"任务 {task_id}: ✅ 已加载 overall_stage_plans")
            else:
                logger.warning(f"任务 {task_id}: ⚠️ 项目数据中没有 overall_stage_plans")
            
            # 同步其他关键数据
            for key in ["novel_title", "novel_synopsis", "creative_seed", "category", "selected_plan", 
                        "global_growth_plan", "stage_writing_plans", "character_design", "core_worldview"]:
                if key in novel_detail and novel_detail[key]:
                    novel_generator.novel_data[key] = novel_detail[key]
                    logger.info(f"任务 {task_id}: ✅ 已同步 {key}")
            
            logger.info(f"任务 {task_id}: ✅ 成功加载小说数据，开始准备第二阶段生成")
            
            # 🔥 并发支持：设置任务上下文
            # 为当前任务创建独立的上下文，避免多任务数据冲突
            setattr(novel_generator, '_current_task_id', task_id)
            with novel_generator._task_lock:
                novel_generator._task_contexts[task_id] = novel_detail.copy()
                novel_generator._task_contexts[task_id]["is_resuming"] = True
                novel_generator._task_contexts[task_id]["resume_data"] = {
                    "from_chapter": from_chapter,
                    "chapters_to_generate": chapters_to_generate
                }
            logger.info(f"任务 {task_id}: ✅ 任务上下文已设置，数据隔离已启用")
            
            # 🔥 修复：先设置用户名，再初始化材料管理器
            username = config.get('username')
            if username:
                novel_generator._username = username
                novel_generator.set_username(username)
                logger.info(f"任务 {task_id}: 已设置用户名 {username} 用于用户隔离路径")
                
                # 🔥 关键修复：刷新 StagePlanManager 的缓存路径
                if hasattr(novel_generator, 'stage_plan_manager') and novel_generator.stage_plan_manager:
                    # 重新初始化 plans_dir 缓存
                    novel_generator.stage_plan_manager._init_plans_dir()
                    logger.info(f"任务 {task_id}: 已刷新 StagePlanManager 路径缓存")
            
            # 初始化材料管理器（如果需要）- 必须在设置用户名之后
            if not novel_generator.material_manager:
                novel_generator._initialize_material_manager()
            
            # 加载第一阶段数据完成 (30%)
            self._update_task_status(task_id, "preparing", 30)
            
            try:
                # 设置进度回调 - 用于在生成过程中动态更新进度
                setattr(novel_generator, '_phase_two_progress_callback', update_phase_two_progress)
                setattr(novel_generator, '_phase_two_from_chapter', from_chapter)
                setattr(novel_generator, '_phase_two_total_chapters', chapters_to_generate)
                
                # 🔥 设置停止检查回调
                setattr(novel_generator, '_stop_check_callback', lambda: self._check_stop_flag(task_id))
                
                # 🔥 设置用户ID用于API调用实时扣费
                user_id = config.get('user_id')
                if user_id:
                    novel_generator.set_user_id(user_id)
                    logger.info(f"任务 {task_id}: 已设置用户ID {user_id} 用于API调用扣费")
                
                # 🔥 修复：传递novel_title而不是phase_one_file
                # 🔥 新增：传递字数阈值参数
                success = novel_generator.phase_two_generation(
                    novel_title,  # 使用实际的小说标题
                    from_chapter,
                    chapters_to_generate,
                    min_word_threshold=config.get('min_word_threshold', 1500),
                    max_word_threshold=config.get('max_word_threshold', 3500)
                )
                
                if success:
                    logger.info(f"任务 {task_id}: 第二阶段章节生成成功")
                    self._update_task_status(task_id, "completed", 100)
                    
                    task_result = self.task_results.get(task_id, {})
                    # 🔥 并发安全：使用任务上下文获取生成的章节数据
                    task_ctx = novel_generator._get_task_context(task_id)
                    generated_chapters = task_ctx.get("generated_chapters", {})
                    task_result["result"] = {
                        "novel_title": novel_title,
                        "from_chapter": from_chapter,
                        "chapters_to_generate": chapters_to_generate,
                        "phase_two_completed": True,
                        "generated_chapters": generated_chapters,
                        "total_generated": len(generated_chapters)
                    }
                    self.task_results[task_id] = task_result
                    
                    try:
                        self.load_existing_novels()
                    except Exception as e:
                        logger.info(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 第二阶段章节生成失败")
                    self._update_task_status(task_id, "failed", 0, "第二阶段章节生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: phase_two_generation 执行异常: {e}")
                self._update_task_status(task_id, "failed", 0, f"第二阶段生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 第二阶段生成任务异常: {e}")
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")