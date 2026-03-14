"""
线程池管理器 - 安全的线程池使用和清理
解决线程泄漏问题
"""
import weakref
import atexit
import signal
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 全局线程池监控器
_global_executors = weakref.WeakSet()


def cleanup_all_executors():
    """清理所有线程池 - 在程序退出时调用"""
    logger.info(f"🚿 正在关闭 {_global_executors.__len__()} 个线程池...")
    
    for executor in list(_global_executors):
        try:
            if hasattr(executor, '_shutdown'):
                continue  # 已经关闭
            
            logger.info(f"  正在关闭线程池...")
            executor.shutdown(wait=False, cancel_futures=True)
            logger.info(f"  ✅ 线程池已关闭")
        except Exception as e:
            logger.warning(f"  ⚠️ 关闭线程池时出错: {e}")


# 注册程序退出时的清理
atexit.register(cleanup_all_executors)

# 处理信号中断
def _signal_handler(signum, frame):
    logger.info(f"🔴 收到信号 {signum}，正在清理线程池...")
    cleanup_all_executors()
    # 重新提出信号
    signal.default_int_handler(signum, frame)

try:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
except (ValueError, OSError):
    pass  # 在非主线程中可能无法设置信号处理器


class ManagedThreadPool:
    """
    可管理的线程池 - 带有超时和自动清理机制
    """
    
    def __init__(self, max_workers: int = 4, thread_name_prefix: str = "ManagedPool", 
                 timeout: float = 300, task_timeout: float = 60):
        """
        初始化管理线程池
        
        Args:
            max_workers: 最大线程数
            thread_name_prefix: 线程名前缀
            timeout: 整体超时时间（秒）
            task_timeout: 单个任务超时时间（秒）
        """
        self.max_workers = max_workers
        self.thread_name_prefix = thread_name_prefix
        self.timeout = timeout
        self.task_timeout = task_timeout
        self.executor: Optional[ThreadPoolExecutor] = None
        self._closed = False
        
    def __enter__(self):
        """上下文管理器入口"""
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.thread_name_prefix
        )
        _global_executors.add(self.executor)
        logger.info(f"🔽 创建线程池: {self.thread_name_prefix} (最大{self.max_workers}线程)")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 确保关闭"""
        self.close()
        return False  # 不抑制异常
    
    def submit(self, fn: Callable, *args, **kwargs) -> Any:
        """提交任务"""
        if self._closed or not self.executor:
            raise RuntimeError("线程池已关闭")
        return self.executor.submit(fn, *args, **kwargs)
    
    def map(self, fn: Callable, iterable) -> List[Any]:
        """并行执行"""
        if self._closed or not self.executor:
            raise RuntimeError("线程池已关闭")
        return list(self.executor.map(fn, iterable, timeout=self.task_timeout))
    
    def close(self, wait: bool = False):
        """关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        if self._closed:
            return
            
        self._closed = True
        
        if self.executor:
            try:
                logger.info(f"🚿 正在关闭线程池: {self.thread_name_prefix}")
                # 尝试取消所有未完成的任务
                self.executor.shutdown(wait=wait, cancel_futures=True)
                _global_executors.discard(self.executor)
                logger.info(f"✅ 线程池已关闭: {self.thread_name_prefix}")
            except Exception as e:
                logger.warning(f"⚠️ 关闭线程池时出错: {e}")
            finally:
                self.executor = None


@contextmanager
def managed_thread_pool(max_workers: int = 4, thread_name_prefix: str = "ManagedPool",
                        timeout: float = 300, task_timeout: float = 60):
    """
    管理线程池上下文管理器
    
    使用示例:
        with managed_thread_pool(max_workers=4) as pool:
            futures = [pool.submit(task_func, arg) for arg in args_list]
            for future in as_completed(futures, timeout=300):
                result = future.result(timeout=60)
    """
    pool = ManagedThreadPool(max_workers, thread_name_prefix, timeout, task_timeout)
    try:
        pool.__enter__()
        yield pool
    finally:
        pool.close(wait=False)


def get_active_thread_count() -> int:
    """获取当前活动线程数"""
    import threading
    return threading.active_count()


def get_executor_stats() -> Dict[str, Any]:
    """获取线程池统计信息"""
    return {
        "active_executors": len(_global_executors),
        "active_threads": get_active_thread_count(),
        "executor_names": [getattr(e, '_thread_name_prefix', 'unknown') 
                          for e in _global_executors]
    }


# 导出使用
__all__ = [
    'ManagedThreadPool',
    'managed_thread_pool',
    'cleanup_all_executors',
    'get_active_thread_count',
    'get_executor_stats'
]
