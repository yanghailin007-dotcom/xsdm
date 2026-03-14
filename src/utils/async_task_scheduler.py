"""
异步任务调度器 - 优化 API 密集型并行任务
解决线程池执行不均衡问题
"""
import asyncio
import time
import logging
from typing import Callable, Any, List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class TaskStats:
    """任务统计信息"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    task_times: Dict[str, float] = field(default_factory=dict)
    
    def add_result(self, result: TaskResult):
        self.completed_tasks += 1
        self.total_duration += result.duration
        self.min_duration = min(self.min_duration, result.duration)
        self.max_duration = max(self.max_duration, result.duration)
        self.task_times[result.task_id] = result.duration
        
    @property
    def avg_duration(self) -> float:
        if self.completed_tasks == 0:
            return 0.0
        return self.total_duration / self.completed_tasks
    
    def report(self) -> str:
        """生成执行报告"""
        lines = [
            "\n📊 并行执行统计报告",
            "=" * 50,
            f"总任务数: {self.total_tasks}",
            f"成功: {self.completed_tasks - self.failed_tasks}",
            f"失败: {self.failed_tasks}",
            f"\n⏱️  时间统计:",
            f"  最短: {self.min_duration:.1f}s",
            f"  平均: {self.avg_duration:.1f}s",
            f"  最长: {self.max_duration:.1f}s",
            f"  总耗时: {self.total_duration:.1f}s",
            f"\n⚠️  潜在问题:"
        ]
        
        # 找出异常慢的任务
        if self.avg_duration > 0:
            for task_id, duration in sorted(self.task_times.items(), key=lambda x: -x[1]):
                ratio = duration / self.avg_duration
                if ratio > 1.5:
                    lines.append(f"  🔴 {task_id}: {duration:.1f}s (比平均慢 {ratio:.1f}x)")
                    
        return "\n".join(lines)


class AsyncTaskScheduler:
    """
    异步任务调度器
    
    特点：
    1. 使用 asyncio + ThreadPoolExecutor 实现真正的并发
    2. 自动监控每个任务的执行时间
    3. 支持任务优先级（先提交的先执行）
    4. 支持超时控制和取消
    """
    
    def __init__(self, max_workers: int = 4, enable_stats: bool = True):
        self.max_workers = max_workers
        self.enable_stats = enable_stats
        self.stats = TaskStats()
        
    async def run_tasks(
        self, 
        tasks: List[Tuple[str, Callable, tuple, dict]], 
        timeout: Optional[float] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, TaskResult]:
        """
        并行执行多个任务
        
        Args:
            tasks: [(task_id, func, args, kwargs), ...]
            timeout: 整体超时时间
            progress_callback: 进度回调 (task_id, completed, total)
            
        Returns:
            {task_id: TaskResult, ...}
        """
        self.stats = TaskStats(total_tasks=len(tasks))
        results = {}
        
        # 使用 semaphore 控制并发数
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def run_with_limit(task_id: str, func: Callable, args: tuple, kwargs: dict):
            """带并发限制的任务执行"""
            async with semaphore:
                return await self._execute_task(task_id, func, args, kwargs)
        
        # 创建所有任务
        coroutines = [
            run_with_limit(task_id, func, args, kwargs)
            for task_id, func, args, kwargs in tasks
        ]
        
        # 执行并收集结果
        start_time = time.time()
        
        if timeout:
            # 带超时的执行
            pending = set(asyncio.create_task(c) for c in coroutines)
            completed_count = 0
            
            while pending:
                elapsed = time.time() - start_time
                remaining_timeout = max(0.1, timeout - elapsed)
                
                done, pending = await asyncio.wait(
                    pending, 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=remaining_timeout
                )
                
                for task in done:
                    try:
                        result = await task
                        results[result.task_id] = result
                        completed_count += 1
                        
                        if self.enable_stats:
                            self.stats.add_result(result)
                        if progress_callback:
                            progress_callback(result.task_id, completed_count, len(tasks))
                            
                    except Exception as e:
                        logger.error(f"任务执行失败: {e}")
                        
                if elapsed >= timeout:
                    logger.warning(f"整体超时，取消 {len(pending)} 个未完成任务")
                    for p in pending:
                        p.cancel()
                    break
        else:
            # 无限制执行
            completed_results = await asyncio.gather(*coroutines, return_exceptions=True)
            for result in completed_results:
                if isinstance(result, TaskResult):
                    results[result.task_id] = result
                    if self.enable_stats:
                        self.stats.add_result(result)
        
        if self.enable_stats:
            logger.info(self.stats.report())
            
        return results
    
    async def _execute_task(
        self, 
        task_id: str, 
        func: Callable, 
        args: tuple, 
        kwargs: dict
    ) -> TaskResult:
        """执行单个任务并记录时间"""
        start_time = time.time()
        
        try:
            # 在线程池中执行阻塞函数
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
            
            return TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                start_time=start_time,
                end_time=time.time()
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                start_time=start_time,
                end_time=time.time()
            )


def run_parallel_with_stats(
    tasks: List[Tuple[str, Callable, tuple, dict]],
    max_workers: int = 4,
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """
    同步接口：并行执行任务并返回统计信息
    
    使用示例:
        def my_task(x):
            time.sleep(x)
            return x * 2
            
        tasks = [
            ("task1", my_task, (1,), {}),
            ("task2", my_task, (2,), {}),
            ("task3", my_task, (5,), {}),  # 这个会慢很多
        ]
        
        results, stats = run_parallel_with_stats(tasks, max_workers=3)
        # stats.report() 会显示 task3 比平均慢很多
    """
    scheduler = AsyncTaskScheduler(max_workers=max_workers, enable_stats=True)
    
    async def main():
        return await scheduler.run_tasks(tasks, timeout=timeout)
    
    results = asyncio.run(main())
    
    # 提取结果值
    output = {
        task_id: r.result if r.success else None
        for task_id, r in results.items()
    }
    
    return output, scheduler.stats


# 兼容性：传统的线程池（如果发现异步版本有问题可以回退）
def run_with_thread_pool(
    tasks: List[Tuple[str, Callable, tuple, dict]],
    max_workers: int = 4,
    timeout: float = 300
) -> Dict[str, Any]:
    """使用传统 ThreadPoolExecutor 的并行执行（兼容性接口）"""
    from concurrent.futures import as_completed, TimeoutError
    
    results = {}
    stats = TaskStats(total_tasks=len(tasks))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(func, *args, **kwargs): task_id
            for task_id, func, args, kwargs in tasks
        }
        
        start_time = time.time()
        for future in as_completed(future_to_id, timeout=timeout):
            task_id = future_to_id[future]
            try:
                result = future.result(timeout=60)
                results[task_id] = result
                stats.add_result(TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    start_time=start_time,
                    end_time=time.time()
                ))
            except Exception as e:
                stats.add_result(TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    start_time=start_time,
                    end_time=time.time()
                ))
    
    logger.info(stats.report())
    return results, stats
