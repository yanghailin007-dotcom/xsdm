#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二阶段生成并发测试
验证多用户同时启动二阶段生成时的数据隔离和并发安全
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


class PhaseTwoConcurrencyTest:
    """第二阶段并发测试类"""
    
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
                    "total_chapters": 200,
                    "chapters_per_batch": 3
                }
            }
    
    def test_phase_two_context_isolation(self):
        """测试1: 二阶段任务上下文隔离"""
        print("\n[Test 1] 二阶段任务上下文隔离")
        print("-" * 60)
        
        try:
            config = self.load_config()
            ng = NovelGenerator(config)
            
            # 模拟两个不同用户的二阶段任务
            task_id_1 = "phase2_user_a_001"
            task_id_2 = "phase2_user_b_002"
            
            # 设置任务1 - 用户A，从第1章开始
            ng._current_task_id = task_id_1
            ctx1 = ng._get_task_context(task_id_1)
            ctx1["novel_title"] = "用户A的小说"
            ctx1["current_progress"] = {
                "completed_chapters": 0,
                "total_chapters": 100,
                "stage": "第二阶段生成"
            }
            ctx1["generated_chapters"] = {
                "1": {"title": "第1章", "content": "内容A"}
            }
            ctx1["resume_data"] = {
                "from_chapter": 1,
                "chapters_to_generate": 10
            }
            
            # 设置任务2 - 用户B，从第11章开始（续写）
            ng._current_task_id = task_id_2
            ctx2 = ng._get_task_context(task_id_2)
            ctx2["novel_title"] = "用户B的小说"
            ctx2["current_progress"] = {
                "completed_chapters": 10,
                "total_chapters": 100,
                "stage": "第二阶段生成"
            }
            ctx2["generated_chapters"] = {
                "11": {"title": "第11章", "content": "内容B"}
            }
            ctx2["resume_data"] = {
                "from_chapter": 11,
                "chapters_to_generate": 10
            }
            
            # 验证隔离 - 任务1
            ng._current_task_id = task_id_1
            ctx1_check = ng._get_task_context(task_id_1)
            assert ctx1_check["novel_title"] == "用户A的小说", "任务1数据被污染"
            assert ctx1_check["resume_data"]["from_chapter"] == 1, "任务1起始章节被污染"
            
            # 验证隔离 - 任务2
            ng._current_task_id = task_id_2
            ctx2_check = ng._get_task_context(task_id_2)
            assert ctx2_check["novel_title"] == "用户B的小说", "任务2数据被污染"
            assert ctx2_check["resume_data"]["from_chapter"] == 11, "任务2起始章节被污染"
            
            # 验证章节数据不混叠
            assert "11" not in ctx1_check.get("generated_chapters", {}), "任务1不应有任务2的章节"
            assert "1" not in ctx2_check.get("generated_chapters", {}), "任务2不应有任务1的章节"
            
            print(f"✅ 任务1: {ctx1['novel_title']}, 起始章节: {ctx1['resume_data']['from_chapter']}")
            print(f"✅ 任务2: {ctx2['novel_title']}, 起始章节: {ctx2['resume_data']['from_chapter']}")
            print("✅ 二阶段任务上下文隔离正常")
            
            # 清理
            ng._cleanup_task_context(task_id_1)
            ng._cleanup_task_context(task_id_2)
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(("test_phase_two_context_isolation", str(e)))
            return False
    
    def test_concurrent_phase_two_generation(self):
        """测试2: 并发二阶段生成"""
        print("\n[Test 2] 并发二阶段生成")
        print("-" * 60)
        
        try:
            config = self.load_config()
            ng = NovelGenerator(config)
            
            results = {"success": 0, "failed": 0, "chapters_generated": 0}
            errors = []
            lock = threading.Lock()
            
            def run_phase_two_task(user_id: str, task_id: str, start_chapter: int):
                """模拟二阶段生成任务"""
                try:
                    # 设置任务上下文
                    ng._current_task_id = task_id
                    ctx = ng._get_task_context(task_id)
                    
                    # 模拟从检查点恢复的数据
                    ctx["novel_title"] = f"小说_{user_id}"
                    ctx["current_progress"] = {
                        "completed_chapters": start_chapter - 1,
                        "total_chapters": 100,
                        "stage": "第二阶段生成"
                    }
                    ctx["generated_chapters"] = {}
                    
                    # 模拟生成多个章节
                    for i in range(3):
                        chapter_num = start_chapter + i
                        ctx["generated_chapters"][str(chapter_num)] = {
                            "title": f"第{chapter_num}章",
                            "content": f"用户{user_id}的章节内容",
                            "word_count": 2000
                        }
                        
                        # 模拟处理时间
                        time.sleep(0.05)
                    
                    # 验证数据完整性
                    assert ctx["novel_title"] == f"小说_{user_id}", f"数据被覆盖: {user_id}"
                    assert len(ctx["generated_chapters"]) == 3, "章节数量不对"
                    
                    with lock:
                        results["success"] += 1
                        results["chapters_generated"] += 3
                        
                except Exception as e:
                    with lock:
                        results["failed"] += 1
                        errors.append(f"{task_id}: {e}")
            
            # 启动3个并发二阶段任务（不同用户，不同起始章节）
            threads = []
            scenarios = [
                ("user_a", 1),   # 用户A，从第1章开始
                ("user_b", 11),  # 用户B，从第11章开始（续写）
                ("user_c", 21),  # 用户C，从第21章开始（续写）
            ]
            
            for user_id, start_chapter in scenarios:
                task_id = f"phase2_{user_id}_{int(time.time()*1000)}"
                t = threading.Thread(target=run_phase_two_task, args=(user_id, task_id, start_chapter))
                threads.append((task_id, t))
            
            # 启动所有线程
            for _, t in threads:
                t.start()
            
            # 等待完成
            for _, t in threads:
                t.join()
            
            print(f"✅ 成功任务: {results['success']}")
            print(f"❌ 失败任务: {results['failed']}")
            print(f"📊 生成章节数: {results['chapters_generated']}")
            if errors:
                print(f"错误详情: {errors}")
            
            assert results["success"] == 3, f"应有3个成功，实际{results['success']}"
            assert results["failed"] == 0, f"应有0个失败，实际{results['failed']}"
            
            print("✅ 并发二阶段生成测试通过")
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(("test_concurrent_phase_two_generation", str(e)))
            return False
    
    def test_phase_two_continue_generation(self):
        """测试3: 二阶段继续生成（续写）"""
        print("\n[Test 3] 二阶段继续生成（续写）")
        print("-" * 60)
        
        try:
            config = self.load_config()
            ng = NovelGenerator(config)
            
            # 模拟第一次生成（1-5章）
            task_id_1 = "phase2_continue_001"
            ng._current_task_id = task_id_1
            ctx1 = ng._get_task_context(task_id_1)
            ctx1["novel_title"] = "续写测试小说"
            ctx1["generated_chapters"] = {
                str(i): {"title": f"第{i}章", "content": f"内容{i}"}
                for i in range(1, 6)
            }
            ctx1["current_progress"] = {"completed_chapters": 5}
            
            # 模拟第二次生成（6-10章，续写）
            task_id_2 = "phase2_continue_002"
            ng._current_task_id = task_id_2
            ctx2 = ng._get_task_context(task_id_2)
            
            # 使用深拷贝复制之前的章节（避免引用共享）
            import copy
            ctx2.update(copy.deepcopy(ctx1))
            ctx2["resume_data"] = {
                "from_chapter": 6,
                "chapters_to_generate": 5
            }
            
            # 添加新章节
            for i in range(6, 11):
                ctx2["generated_chapters"][str(i)] = {
                    "title": f"第{i}章",
                    "content": f"续写内容{i}"
                }
            ctx2["current_progress"]["completed_chapters"] = 10
            
            # 验证两次任务的独立性（深拷贝后，两个任务的章节数据应独立）
            assert len(ctx1["generated_chapters"]) == 5, f"任务1应保持5章，实际{len(ctx1['generated_chapters'])}章"
            assert len(ctx2["generated_chapters"]) == 10, f"任务2应有10章，实际{len(ctx2['generated_chapters'])}章"
            
            print(f"✅ 第一次生成: {len(ctx1['generated_chapters'])} 章")
            print(f"✅ 继续生成后: {len(ctx2['generated_chapters'])} 章")
            print("✅ 续写功能正常，任务数据独立")
            
            # 清理
            ng._cleanup_task_context(task_id_1)
            ng._cleanup_task_context(task_id_2)
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(("test_phase_two_continue_generation", str(e)))
            return False
    
    def test_username_in_api_logs(self):
        """测试4: API日志中的用户名标识"""
        print("\n[Test 4] API日志用户名标识")
        print("-" * 60)
        
        try:
            from src.core.APIClient import APIClient
            
            # 创建APIClient实例
            client = APIClient({})
            
            # 设置用户名
            test_username = "test_user_001"
            client.set_username(test_username)
            
            # 验证用户名设置
            username_str = client._get_username_str()
            assert f"[{test_username}]" in username_str, f"用户名应包含在日志前缀中: {username_str}"
            
            print(f"✅ 用户名设置: {test_username}")
            print(f"✅ 日志前缀: {username_str}")
            print("✅ API日志用户名标识正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(("test_username_in_api_logs", str(e)))
            return False
    
    def test_stop_flag_isolation_phase_two(self):
        """测试5: 二阶段停止标志隔离"""
        print("\n[Test 5] 二阶段停止标志隔离")
        print("-" * 60)
        
        try:
            from web.managers.novel_manager import NovelGenerationManager
            
            manager = NovelGenerationManager()
            
            # 模拟3个并发的二阶段任务（需要先添加到active_tasks）
            task_ids = ["phase2_stop_a", "phase2_stop_b", "phase2_stop_c"]
            for tid in task_ids:
                manager.active_tasks[tid] = {"status": "generating"}
            
            # 只停止中间的任务
            manager.stop_task(task_ids[1])
            
            # 验证
            assert not manager.is_task_stopped(task_ids[0]), "任务A不应被停止"
            assert manager.is_task_stopped(task_ids[1]), "任务B应被停止"
            assert not manager.is_task_stopped(task_ids[2]), "任务C不应被停止"
            
            # 验证停止检查时只有任务B会抛出异常
            for i, task_id in enumerate(task_ids):
                try:
                    manager._check_stop_flag(task_id, f"检查{task_id}")
                    if i == 1:
                        assert False, f"{task_id} 应抛出异常"
                except InterruptedError:
                    if i != 1:
                        assert False, f"{task_id} 不应抛出异常"
            
            print("✅ 任务A: 未停止")
            print("✅ 任务B: 已停止")
            print("✅ 任务C: 未停止")
            print("✅ 二阶段停止标志隔离正常")
            
            return True
            
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(("test_stop_flag_isolation_phase_two", str(e)))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print(" " * 20 + "第二阶段并发测试")
        print("=" * 70)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python版本: {sys.version}")
        print("=" * 70)
        
        tests = [
            ("二阶段任务上下文隔离", self.test_phase_two_context_isolation),
            ("并发二阶段生成", self.test_concurrent_phase_two_generation),
            ("二阶段继续生成", self.test_phase_two_continue_generation),
            ("API日志用户名标识", self.test_username_in_api_logs),
            ("二阶段停止标志隔离", self.test_stop_flag_isolation_phase_two),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n❌ 测试 {name} 异常: {e}")
                import traceback
                traceback.print_exc()
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
    test = PhaseTwoConcurrencyTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
