"""
并行性能诊断工具
运行此脚本来分析为什么某些阶段生成特别慢
"""
import time
import sys
sys.path.insert(0, '.')

from src.utils.async_task_scheduler import run_parallel_with_stats, run_with_thread_pool


def mock_api_call(task_name: str, duration: float):
    """模拟 API 调用"""
    print(f"  🚀 [{task_name}] 开始执行 (预计 {duration}s)")
    start = time.time()
    time.sleep(duration)  # 模拟 API 延迟
    actual = time.time() - start
    print(f"  ✅ [{task_name}] 完成，实际耗时 {actual:.1f}s")
    return f"{task_name}_result"


def test_current_implementation():
    """测试当前实现 - 模拟 4 个阶段的生成"""
    print("\n" + "="*60)
    print("测试当前 ThreadPoolExecutor 实现")
    print("="*60)
    
    # 模拟 4 个阶段，其中一个特别慢
    tasks = [
        ("exposition_stage", mock_api_call, ("exposition_stage", 3.0), {}),
        ("rising_stage", mock_api_call, ("rising_stage", 3.5), {}),
        ("climax_stage", mock_api_call, ("climax_stage", 4.0), {}),
        ("ending_stage", mock_api_call, ("ending_stage", 8.0)),  # 这个慢很多
    ]
    
    start = time.time()
    results, stats = run_with_thread_pool(tasks, max_workers=4, timeout=300)
    total = time.time() - start
    
    print(f"\n⏱️  总耗时: {total:.1f}s (由最慢的 ending_stage 决定)")
    print(f"📊 优化空间: {stats.max_duration - stats.avg_duration:.1f}s")


def test_reduced_workers():
    """测试减少线程数的效果"""
    print("\n" + "="*60)
    print("测试减少线程数 (4 -> 2) - 避免 API 限流")
    print("="*60)
    
    tasks = [
        ("exposition_stage", mock_api_call, ("exposition_stage", 3.0), {}),
        ("rising_stage", mock_api_call, ("rising_stage", 3.5), {}),
        ("climax_stage", mock_api_call, ("climax_stage", 4.0), {}),
        ("ending_stage", mock_api_call, ("ending_stage", 8.0)),
    ]
    
    start = time.time()
    results, stats = run_with_thread_pool(tasks, max_workers=2, timeout=300)
    total = time.time() - start
    
    print(f"\n⏱️  总耗时: {total:.1f}s")
    print("💡 如果 API 有并发限制，减少线程数可能反而更快")


def analyze_real_problem():
    """分析问题根本原因"""
    print("\n" + "="*60)
    print("🔍 并行执行慢的根本原因分析")
    print("="*60)
    
    analysis = """
可能的原因:

1. 【API 响应不均衡】⭐ 最常见
   - ending_stage 的 Prompt 通常更长、更复杂
   - LLM 处理时间不是线性的，复杂任务可能慢 2-3 倍
   
   解决方法:
   - 优化 ending_stage 的 Prompt
   - 将其拆分为多个小任务

2. 【API 并发限制】⭐⭐ 次常见
   - 4 个线程同时调用 API，触发限流 (rate limiting)
   - 某些请求被延迟或重试
   
   解决方法:
   - 减少 max_workers 到 2 或 3
   - 添加指数退避重试

3. 【Python GIL 限制】
   - 如果生成逻辑是 CPU 密集型，多线程无法真正并行
   
   解决方法:
   - 使用多进程 (ProcessPoolExecutor) 代替多线程

4. 【网络 I/O 瓶颈】
   - 网络带宽或连接数限制

诊断建议:
=========
1. 在 generate_stage_writing_plan 函数开头和结尾添加时间日志
2. 对比单线程串行执行的总时间
3. 检查 LLM API 的响应时间日志
"""
    print(analysis)


def suggest_optimizations():
    """提供优化建议"""
    print("\n" + "="*60)
    print("🚀 优化建议 (按效果排序)")
    print("="*60)
    
    suggestions = """
1. 【立即见效】减少线程数避免限流
   
   在 PhaseGenerator.py 中修改:
   
   当前: max_workers=4
   建议: max_workers=2
   
   原因: 4 个并发可能触发 API 限流，导致排队

2. 【中期优化】为 ending_stage 单独优化 Prompt
   
   ending_stage 通常需要总结全书，Prompt 最长
   可以:
   - 预生成 ending_stage 的关键信息
   - 减少上下文长度

3. 【长期优化】使用 Async API 调用
   
   将阻塞的 API 调用改为异步:
   
   # 当前 (阻塞)
   response = requests.post(...)
   
   # 优化 (异步)
   async with aiohttp.ClientSession() as session:
       async with session.post(...) as response:
           ...

4. 【备选方案】优先级调度
   
   先并行生成 3 个快阶段，再单独生成 ending_stage:
   
   stages_batch1 = [exposition, rising, climax]  # 并行
   ending_stage = ending  # 单独，不阻塞其他

5. 【监控】添加详细时间日志
   
   在 generate_stage_writing_plan 中添加:
   
   import time
   start = time.time()
   # ... 生成逻辑 ...
   logger.info(f"[{stage_name}] 耗时: {time.time()-start:.1f}s")
"""
    print(suggestions)


if __name__ == "__main__":
    print("🧪 并行性能诊断工具")
    print("运行此工具来理解为什么多线程执行不均衡")
    
    test_current_implementation()
    test_reduced_workers()
    analyze_real_problem()
    suggest_optimizations()
    
    print("\n" + "="*60)
    print("诊断完成！")
    print("="*60)
    print("\n💡 实际建议:")
    print("1. 先运行日志观察每个阶段的实际耗时")
    print("2. 尝试将 max_workers 从 4 减到 2")
    print("3. 如果 ending_stage 确实慢，考虑预生成关键信息")
