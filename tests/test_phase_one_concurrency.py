#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一阶段生成并发测试
验证多用户同时启动一阶段生成时的数据隔离和并发安全
"""
import sys
import os

# 设置控制台编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import time
import threading
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.NovelGenerator import NovelGenerator


class PhaseOneConcurrencyTest:
    """第一阶段并发测试类"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        
    def load_config(self):
        """加载测试配置"""
        try:
            import importlib.util
            config_path = Path(__file__).parent.parent / "config" / "config.py"
            spec = importlib.util.spec_from_file_location("config_module", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            return config_module.CONFIG
        except Exception as e:
            print(f"⚠️ 无法加载配置，使用默认配置: {e}")
            return {
                "defaults": {
                    "total_chapters": 100,
                    "chapters_per_batch": 3
                }
            }
    
    def test_task_context_isolation(self):
        """测试1: 任务上下文隔离"""
        print("\n[Test 1] 任务上下文隔离")
        print("-" * 60)
        
        try:
            config = self.load_config()
            ng = NovelGenerator(config)
            
            # 模拟两个不同用户的一阶段任务
            task_id_1 = "phase1_user_a_001"
            task_id_2 = "phase1_user_b_002"
            
            # 设置任务1 - 用户A
            ng._current_task_id = task_id_1
            ctx1 = ng._get_task_context(task_id_1)
            ctx1["novel_title"] = "用户A的小说"
            ctx1["creative_seed"] = {"novelTitle": "用户A创意"}
            ctx1["core_worldview"] = {"name": "世界观A"}
            
            # 设置任务2 - 用户B
            ng._current_task_id = task_id_2
            ctx2 = ng._get_task_context(task_id_2)
            ctx2["novel_title"] = "用户B的小说"
            ctx2["creative_seed"] = {"novelTitle": "用户B创意"}
            ctx2["core_worldview"] = {"name": "世界观B"}
            
            # 验证隔离
            ng._current_task_id = task_id_1
            ctx1_check = ng._get_task_context(task_id_1)
            assert ctx1_check["novel_title"] == "用户A的小说", "任务1数据被污染"
            assert ctx1_check["core_worldview"]["name"] == "世界观A", "任务1世界观被污染"
            
            ng._current_task_id = task_id_2
            ctx2_check = ng._get_task_context(task_id_2)
            assert ctx2_check["novel_title"] == "用户B的小说", "任务2数据被污染"
            assert ctx2_check["core_worldview"]["name"] == "世界观B", "任务2世界观被污染"
            
            # 验证不同对象
            assert id(ctx1) != id(ctx2), "任务上下文应该是不同对象"
            
            print(f"✅ 任务1: {ctx1['novel_title']}")
            print(f"✅ 任务2: {ctx2['novel_title']}")
            print("✅ 任务上下文隔离正常")
            
            # 清理
            ng._cleanup_task_context(task_id_1)
            ng._cleanup_task_context(task_id_2)
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            self.errors.append(("test_task_context_isolation", str(e)))
            return False
    
    def test_concurrent_phase_one_start(self):
        """测试2: 并发启动一阶段任务"""
        print("\n[Test 2] 并发启动一阶段任务")
        print("-" * 60)
        
        try:
            config = self.load_config()
            ng = NovelGenerator(config)
            
            results = {"success": 0, "failed": 0}
            errors = []
            lock = threading.Lock()
            
            def run_phase_one_task(user_id: str, task_id: str, title: str):
                """模拟一阶段生成任务"""
                try:
                    # 设置任务上下文
                    ng._current_task_id = task_id
                    ctx = ng._get_task_context(task_id)
                    
                    # 模拟一阶段数据写入
                    ctx["novel_title"] = title
                    ctx["creative_seed"] = {"novelTitle": title}
                    ctx["core_worldview"] = {"name": f"世界观_{user_id}"}
                    ctx["character_design"] = {"protagonist": f"主角_{user_id}"}
                    ctx["stage_plans"] = [{"stage": 1, "user": user_id}]
                    
                    # 模拟一些处理时间
                    time.sleep(0.1)
                    
                    # 验证数据未被其他任务覆盖
                    assert ctx["novel_title"] == title, f"数据被覆盖: {title}"
                    
                    with lock:
                        results["success"] += 1
                        
                except Exception as e:
                    with lock:
                        results["failed"] += 1
                        errors.append(f"{task_id}: {e}")
            
            # 启动5个并发一阶段任务
            threads = []
            for i in range(5):
                user_id = f"user_{i}"
                task_id = f"phase1_{user_id}_{int(time.time()*1000)}"
                title = f"小说_{user_id}"
                t = threading.Thread(target=run_phase_one_task, args=(user_id, task_id, title))
                threads.append(t)
            
            # 启动所有线程
            for t in threads:
                t.start()
            
            # 等待完成
            for t in threads:
                t.join()
            
            print(f"✅ 成功: {results['success']}")
            print(f"❌ 失败: {results['failed']}")
            if errors:
                print(f"错误详情: {errors}")
            
            assert results["success"] == 5, f"应有5个成功，实际{results['success']}"
            assert results["failed"] == 0, f"应有0个失败，实际{results['failed']}"
            
            print("✅ 并发一阶段任务测试通过")
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            self.errors.append(("test_concurrent_phase_one_start", str(e)))
            return False
    
    def test_user_isolation_paths(self):
        """测试3: 用户路径隔离"""
        print("\n[Test 3] 用户路径隔离")
        print("-" * 60)
        
        try:
            from web.utils.path_utils import get_user_novel_dir
            
            # 测试不同用户的路径
            user_a_path = get_user_novel_dir("user_a", create=False)
            user_b_path = get_user_novel_dir("user_b", create=False)
            
            assert "user_a" in str(user_a_path), "用户A路径应包含用户名"
            assert "user_b" in str(user_b_path), "用户B路径应包含用户名"
            assert user_a_path != user_b_path, "不同用户路径应不同"
            
            print(f"✅ 用户A路径: {user_a_path}")
            print(f"✅ 用户B路径: {user_b_path}")
            print("✅ 用户路径隔离正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            self.errors.append(("test_user_isolation_paths", str(e)))
            return False
    
    def test_stop_flag_mechanism(self):
        """测试4: 停止标志机制"""
        print("\n[Test 4] 停止标志机制")
        print("-" * 60)
        
        try:
            from web.managers.novel_manager import NovelGenerationManager
            
            manager = NovelGenerationManager()
            
            # 设置停止标志
            task_id = "test_phase1_stop_001"
            manager._stop_flags[task_id] = True
            
            # 验证停止标志
            assert manager.is_task_stopped(task_id), "停止标志应被设置"
            
            # 验证检查函数
            try:
                manager._check_stop_flag(task_id, "测试停止")
                assert False, "应抛出异常"
            except InterruptedError:
                print("✅ 停止检查正常抛出InterruptedError")
            
            # 验证其他任务不受影响
            other_task = "test_phase1_stop_002"
            assert not manager.is_task_stopped(other_task), "其他任务不应受影响"
            
            print("✅ 停止标志机制正常")
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            self.errors.append(("test_stop_flag_mechanism", str(e)))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print(" " * 20 + "第一阶段并发测试")
        print("=" * 70)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python版本: {sys.version}")
        print("=" * 70)
        
        tests = [
            ("任务上下文隔离", self.test_task_context_isolation),
            ("并发启动一阶段", self.test_concurrent_phase_one_start),
            ("用户路径隔离", self.test_user_isolation_paths),
            ("停止标志机制", self.test_stop_flag_mechanism),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n❌ 测试 {name} 异常: {e}")
                results.append((name, False))
        
        # 打印测试报告
        print("\n" + "=" * 70)
        print(" " * 25 + "测试报告")
        print("=" * 70)
        
        passed_count = sum(1 for _, p in results if p)
        for name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  [{status}] {name}")
        
        print("-" * 70)
        print(f"总计: {passed_count}/{len(results)} 通过")
        print("=" * 70)
        
        return passed_count == len(results)


if __name__ == "__main__":
    test = PhaseOneConcurrencyTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
