"""端到端全流程小说生成测试 - 带详细日志追踪"""

import sys
import json
import time
import requests
import subprocess
import threading
import logging
from pathlib import Path
import signal
import os

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / 'debug_web_full_flow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FullFlowTest")

class WebServerManager:
    """Web服务器管理器"""

    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.log_thread = None
        self.stop_event = threading.Event()

    def start_server(self):
        """启动Web服务器"""
        logger.info("🚀 启动Web服务器...")

        try:
            # 清理可能存在的进程
            self._kill_existing_processes()

            # 启动服务器
            self.server_process = subprocess.Popen(
                [sys.executable, "run_web.py"],
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            # 启动日志监听线程
            self.log_thread = threading.Thread(target=self._monitor_logs)
            self.log_thread.daemon = True
            self.log_thread.start()

            # 等待服务器启动
            logger.info("⏳ 等待服务器启动...")
            time.sleep(3)

            # 检查服务器是否运行
            if self._check_server_health():
                self.is_running = True
                logger.info("✅ Web服务器启动成功")
                return True
            else:
                logger.error("❌ Web服务器启动失败")
                self.stop_server()
                return False

        except Exception as e:
            logger.error(f"❌ 启动服务器异常: {e}")
            return False

    def _kill_existing_processes(self):
        """清理现有进程"""
        logger.info("🧹 清理现有Web服务器进程...")

        try:
            # Windows下清理进程
            import psutil
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'python' in proc.info['name'].lower():
                        # 检查是否是我们的Web服务器
                        if any('run_web.py' in cmd for cmd in proc.cmdline()):
                            logger.info(f"杀死进程 PID={proc.pid}")
                            proc.kill()
                            killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed > 0:
                logger.info(f"清理了 {killed} 个Web服务器进程")
                time.sleep(2)  # 等待进程完全退出

        except ImportError:
            logger.warning("psutil不可用，跳过进程清理")

    def _monitor_logs(self):
        """监控服务器日志输出"""
        if not self.server_process:
            return

        logger.info("👀 开始监控服务器日志...")

        try:
            while not self.stop_event.is_set():
                if self.server_process.poll() is not None:
                    # 进程已退出
                    break

                # 读取stdout
                if self.server_process.stdout:
                    line = self.server_process.stdout.readline()
                    if line:
                        logger.debug(f"[SERVER] {line.strip()}")

                # 读取stderr
                if self.server_process.stderr:
                    line = self.server_process.stderr.readline()
                    if line:
                        logger.warning(f"[SERVER ERROR] {line.strip()}")

                time.sleep(0.1)

        except Exception as e:
            logger.error(f"日志监控异常: {e}")

        logger.info("🛑 停止监控服务器日志")

    def _check_server_health(self):
        """检查服务器健康状态"""
        try:
            response = requests.get("http://localhost:5000/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def stop_server(self):
        """停止Web服务器"""
        logger.info("🛑 停止Web服务器...")

        self.stop_event.set()

        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                logger.info("✅ Web服务器已停止")
            except subprocess.TimeoutExpired:
                logger.warning("服务器未正常退出，强制终止")
                self.server_process.kill()
            except Exception as e:
                logger.error(f"停止服务器异常: {e}")

        self.is_running = False

class FullFlowTester:
    """完整流程测试器"""

    def __init__(self):
        self.web_manager = WebServerManager()
        self.base_url = "http://localhost:5000"
        self.test_results = []

    def run_full_test(self):
        """运行完整测试"""
        logger.info("🎯 开始端到端全流程测试")
        logger.info("=" * 80)

        try:
            # 步骤1: 启动Web服务器
            if not self._test_server_startup():
                return False

            # 步骤2: 测试健康检查
            if not self._test_health_check():
                return False

            # 步骤3: 测试小说生成请求
            if not self._test_novel_generation():
                return False

            # 步骤4: 监控生成过程
            if not self._test_generation_monitoring():
                return False

            # 步骤5: 测试各种边界情况
            self._test_edge_cases()

            logger.info("🎉 所有测试步骤完成")
            return True

        except Exception as e:
            logger.error(f"❌ 测试过程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        finally:
            # 清理
            self.web_manager.stop_server()

    def _test_server_startup(self):
        """测试服务器启动"""
        logger.info("\n[步骤1] 测试Web服务器启动")
        logger.info("-" * 50)

        success = self.web_manager.start_server()
        self.test_results.append(("服务器启动", success))

        if success:
            logger.info("✅ 服务器启动测试通过")
        else:
            logger.error("❌ 服务器启动测试失败")

        return success

    def _test_health_check(self):
        """测试健康检查"""
        logger.info("\n[步骤2] 测试健康检查")
        logger.info("-" * 50)

        try:
            logger.debug("发送健康检查请求...")
            response = requests.get(f"{self.base_url}/api/health", timeout=5)

            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")

            if response.status_code == 200:
                logger.info("✅ 健康检查通过")
                success = True
            else:
                logger.error(f"❌ 健康检查失败: {response.status_code}")
                success = False

        except Exception as e:
            logger.error(f"❌ 健康检查异常: {e}")
            success = False

        self.test_results.append(("健康检查", success))
        return success

    def _test_novel_generation(self):
        """测试小说生成请求"""
        logger.info("\n[步骤3] 测试小说生成请求")
        logger.info("-" * 50)

        import uuid
        unique_title = f"全流程测试_{str(uuid.uuid4())[:8]}"

        # 测试数据 - 包含可能触发错误的情况
        test_request = {
            "title": unique_title,
            "prompt": "这是一个端到端测试故事，主角叫林云，是修仙者，包含复杂的剧情",
            "total_chapters": 3,
            "start_chapter": 1,
            "end_chapter": 3,
            # 添加可能触发问题的字段
            "creative_seed": "修仙世界，宗门林立，主角林云天赋异禀",  # 字符串种子
            "use_creative_file": True
        }

        logger.info("📤 发送小说生成请求:")
        logger.info(json.dumps(test_request, ensure_ascii=False, indent=2))

        try:
            logger.debug("正在发送POST请求到 /api/start-generation...")
            response = requests.post(
                f"{self.base_url}/api/start-generation",
                json=test_request,
                timeout=30
            )

            logger.info(f"📥 响应状态码: {response.status_code}")
            logger.info(f"📥 响应头: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info("📥 响应JSON:")
                    logger.info(json.dumps(result, ensure_ascii=False, indent=2))

                    if result.get("success"):
                        task_id = result.get("task_id")
                        logger.info(f"✅ 生成请求成功，任务ID: {task_id}")

                        # 保存task_id用于后续测试
                        self.current_task_id = task_id
                        success = True
                    else:
                        logger.error(f"❌ 请求失败: {result}")
                        success = False

                except json.JSONDecodeError as e:
                    logger.error(f"❌ 无法解析JSON响应: {e}")
                    logger.error(f"原始响应: {response.text[:1000]}")
                    success = False
            else:
                logger.error(f"❌ HTTP请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text[:1000]}")
                success = False

        except requests.exceptions.Timeout:
            logger.error("❌ 请求超时（超过30秒）")
            success = False
        except Exception as e:
            logger.error(f"❌ 请求异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            success = False

        self.test_results.append(("小说生成请求", success))
        return success

    def _test_generation_monitoring(self):
        """测试生成过程监控"""
        logger.info("\n[步骤4] 测试生成过程监控")
        logger.info("-" * 50)

        if not hasattr(self, 'current_task_id'):
            logger.error("❌ 没有任务ID，跳过监控测试")
            return False

        task_id = self.current_task_id
        max_attempts = 30  # 最多等待5分钟
        success = False

        logger.info(f"🔍 开始监控任务: {task_id}")

        for attempt in range(max_attempts):
            try:
                logger.debug(f"查询任务状态 (第{attempt+1}次)...")
                response = requests.get(
                    f"{self.base_url}/api/task/{task_id}/status",
                    timeout=10
                )

                logger.debug(f"状态查询响应码: {response.status_code}")

                if response.status_code == 200:
                    try:
                        status_data = response.json()
                        logger.debug(f"状态数据: {json.dumps(status_data, ensure_ascii=False)}")

                        status = status_data.get("status", "unknown")
                        progress = status_data.get("progress", 0)
                        error = status_data.get("error")

                        logger.info(f"📊 任务状态: {status}, 进度: {progress}%")

                        if error:
                            logger.warning(f"⚠️ 任务错误: {error}")

                        if status == "completed":
                            logger.info("✅ 任务完成！")
                            success = True
                            break
                        elif status == "failed":
                            logger.error(f"❌ 任务失败: {error}")
                            success = False
                            break
                        elif status == "running":
                            logger.debug("⏳ 任务正在运行，继续监控...")
                        else:
                            logger.warning(f"⚠️ 未知状态: {status}")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ 无法解析状态JSON: {e}")
                        logger.error(f"原始响应: {response.text[:500]}")
                else:
                    logger.error(f"❌ 状态查询失败: {response.status_code}")
                    logger.error(f"响应内容: {response.text[:500]}")

            except Exception as e:
                logger.error(f"❌ 状态查询异常: {e}")

            # 等待10秒再查
            if attempt < max_attempts - 1:
                logger.debug("等待10秒后再次查询...")
                time.sleep(10)

        if not success:
            logger.error("❌ 监控超时，任务未完成")

        self.test_results.append(("生成过程监控", success))
        return success

    def _test_edge_cases(self):
        """测试边界情况"""
        logger.info("\n[步骤5] 测试边界情况")
        logger.info("-" * 50)

        edge_cases = [
            {
                "name": "重复标题测试",
                "request": {
                    "title": "测试重复标题",
                    "prompt": "测试重复标题的情况",
                    "total_chapters": 2
                },
                "expected_should_fail": False  # 现在应该支持重复标题
            },
            {
                "name": "空标题测试",
                "request": {
                    "title": "",
                    "prompt": "测试空标题",
                    "total_chapters": 2
                },
                "expected_should_fail": True
            },
            {
                "name": "覆盖模式测试",
                "request": {
                    "title": "覆盖测试",
                    "prompt": "测试覆盖模式",
                    "total_chapters": 2,
                    "overwrite": True
                },
                "expected_should_fail": False
            }
        ]

        for case in edge_cases:
            logger.info(f"\n🧪 测试: {case['name']}")

            try:
                response = requests.post(
                    f"{self.base_url}/api/start-generation",
                    json=case["request"],
                    timeout=10
                )

                success = response.status_code == 200 and response.json().get("success", False)
                should_fail = case["expected_should_fail"]

                if success and not should_fail:
                    logger.info(f"✅ {case['name']} 通过")
                elif not success and should_fail:
                    logger.info(f"✅ {case['name']} 正确失败")
                else:
                    logger.warning(f"⚠️ {case['name']} 结果不符合预期")

            except Exception as e:
                logger.error(f"❌ {case['name']} 异常: {e}")

def main():
    """主函数"""
    print("=" * 80)
    print("🎯 端到端全流程小说生成测试 - 详细日志追踪")
    print("=" * 80)

    # 创建测试器
    tester = FullFlowTester()

    # 运行完整测试
    success = tester.run_full_test()

    # 输出测试结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    passed = 0
    total = len(tester.test_results)

    for test_name, test_result in tester.test_results:
        status = "✅ 通过" if test_result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if test_result:
            passed += 1

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if success and passed == total:
        print("🎉 所有测试通过！Web端生成流程完全正常！")
    else:
        print("⚠️ 部分测试失败，请查看详细日志")

    print("
📝 详细日志已保存到: debug_web_full_flow.log"    print("=" * 80)

if __name__ == "__main__":
    # 处理中断信号
    def signal_handler(signum, frame):
        print("\n\n🛑 收到中断信号，正在清理...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试程序异常: {e}")
        import traceback
        traceback.print_exc()