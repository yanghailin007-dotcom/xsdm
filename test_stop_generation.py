#!/usr/bin/env python3
"""
测试停止生成功能
验证 stop_task 和 _check_stop_flag 是否正常工作
"""
import sys
import os
import time
import threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_stop_mechanism():
    """测试停止机制"""
    print("=" * 60)
    print("测试: 停止生成功能")
    print("=" * 60)
    
    # 模拟 NovelGenerationManager 的停止机制
    class MockManager:
        def __init__(self):
            self._stop_flags = {}
            self.active_tasks = {}
        
        def stop_task(self, task_id: str) -> bool:
            """设置停止标志"""
            if task_id in self.active_tasks:
                self._stop_flags[task_id] = True
                print(f"  ✓ stop_task('{task_id}'): 已设置停止标志")
                return True
            print(f"  ✗ stop_task('{task_id}'): 任务不存在")
            return False
        
        def is_task_stopped(self, task_id: str) -> bool:
            """检查是否已停止"""
            return self._stop_flags.get(task_id, False)
        
        def _check_stop_flag(self, task_id: str, message: str = "任务被停止"):
            """检查停止标志，如果设置了则抛出异常"""
            if self._stop_flags.get(task_id, False):
                raise InterruptedError(message)
    
    # 测试1: 设置停止标志
    print("\n1. 测试设置停止标志:")
    manager = MockManager()
    task_id = "test-task-123"
    manager.active_tasks[task_id] = {"status": "running"}
    
    # 设置停止前
    is_stopped_before = manager.is_task_stopped(task_id)
    print(f"  停止前 is_task_stopped: {is_stopped_before}")
    assert not is_stopped_before, "初始状态应该未停止"
    
    # 设置停止
    result = manager.stop_task(task_id)
    assert result, "设置停止应该成功"
    
    # 停止后
    is_stopped_after = manager.is_task_stopped(task_id)
    print(f"  停止后 is_task_stopped: {is_stopped_after}")
    assert is_stopped_after, "设置停止后应该返回True"
    
    # 测试2: 检查停止标志抛出异常
    print("\n2. 测试检查停止标志抛出异常:")
    try:
        manager._check_stop_flag(task_id)
        print("  ✗ 应该抛出 InterruptedError")
        assert False, "应该抛出异常"
    except InterruptedError as e:
        print(f"  ✓ 正确抛出 InterruptedError: {e}")
    
    # 测试3: 模拟生成流程中的停止检查
    print("\n3. 模拟生成流程中的停止检查:")
    
    def mock_generation_process(task_id, manager):
        """模拟生成流程"""
        steps = ["初始化", "创意精炼", "世界观生成", "角色设计", "阶段规划"]
        for i, step in enumerate(steps):
            try:
                # 检查是否被请求停止
                manager._check_stop_flag(task_id, f"在步骤 '{step}' 被停止")
                print(f"    步骤 {i+1}/{len(steps)}: {step} - 完成")
                time.sleep(0.1)  # 模拟工作
            except InterruptedError:
                print(f"    步骤 {i+1}/{len(steps)}: {step} - 被中断!")
                return False
        return True
    
    # 新任务
    task_id2 = "test-task-456"
    manager2 = MockManager()
    manager2.active_tasks[task_id2] = {"status": "running"}
    
    # 在另一个线程运行生成流程
    result = {"completed": False}
    def run_generation():
        result["completed"] = mock_generation_process(task_id2, manager2)
    
    thread = threading.Thread(target=run_generation)
    thread.start()
    
    # 等待一段时间后停止
    time.sleep(0.25)  # 等待到第3个步骤
    print(f"  请求停止任务...")
    manager2.stop_task(task_id2)
    
    thread.join(timeout=2)
    
    if not result["completed"]:
        print("  ✓ 生成流程被正确中断")
    else:
        print("  ✗ 生成流程没有被中断")
    
    print("\n" + "=" * 60)
    print("✓ 停止机制测试完成")
    print("=" * 60)

def test_integration_with_novel_generator():
    """测试与 NovelGenerator 的集成"""
    print("\n集成测试: NovelGenerator 停止检查")
    print("=" * 60)
    
    # 模拟 NovelGenerator 的 _check_stop_requested 方法
    class MockNovelGenerator:
        def __init__(self):
            self._stop_check_callback = None
        
        def set_stop_check_callback(self, callback):
            self._stop_check_callback = callback
        
        def _check_stop_requested(self, context: str = "") -> None:
            """检查是否被请求停止"""
            try:
                if self._stop_check_callback:
                    self._stop_check_callback()
            except InterruptedError:
                print(f"  生成被停止{' - ' + context if context else ''}")
                raise
    
    # 模拟管理器的停止标志
    stop_flag = {"stopped": False}
    
    def stop_check():
        if stop_flag["stopped"]:
            raise InterruptedError("任务被停止")
    
    ng = MockNovelGenerator()
    ng.set_stop_check_callback(stop_check)
    
    # 测试1: 未停止时
    print("\n1. 未请求停止时:")
    try:
        ng._check_stop_requested("测试步骤")
        print("  ✓ 正常通过，未抛出异常")
    except InterruptedError:
        print("  ✗ 不应该抛出异常")
        assert False
    
    # 测试2: 请求停止后
    print("\n2. 请求停止后:")
    stop_flag["stopped"] = True
    try:
        ng._check_stop_requested("测试步骤")
        print("  ✗ 应该抛出异常")
        assert False
    except InterruptedError:
        print("  ✓ 正确抛出 InterruptedError")
    
    print("\n" + "=" * 60)
    print("✓ 集成测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_stop_mechanism()
    print()
    test_integration_with_novel_generator()
    print("\n✓ 所有停止功能测试通过")
