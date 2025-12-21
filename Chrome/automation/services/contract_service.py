#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约上传独立进程服务
提供签约和上传功能的独立进程，不干扰主进程的web后端任务
"""

import os
import sys
import json
import time
import signal
import threading
import multiprocessing
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Chrome.automation.utils.config_loader import ConfigLoader, get_config_loader
from Chrome.automation.managers.contract_manager import ContractManager


class ContractService:
    """签约上传服务类 - 在独立进程中运行"""
    
    def __init__(self):
        """初始化签约服务"""
        self.config_loader = get_config_loader()
        self.contract_manager = ContractManager(self.config_loader)
        self.running = False
        self.current_task = None
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.status_file = Path("logs/contract_service_status.json")
        self.log_file = Path("logs/contract_service.log")
        
        # 确保日志目录存在
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.log(f"收到信号 {signum}，正在优雅关闭服务...")
        self.running = False
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}")
    
    def update_status(self, status: Dict[str, Any]):
        """更新服务状态"""
        try:
            status["timestamp"] = datetime.now().isoformat()
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"更新状态文件失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前服务状态"""
        return {
            "running": self.running,
            "current_task": self.current_task,
            "timestamp": datetime.now().isoformat(),
            "service_pid": os.getpid()
        }
    
    def process_contract_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理签约任务"""
        task_id = task.get("task_id", "unknown")
        task_type = task.get("task_type", "contract_management")
        
        self.log(f"开始处理任务: {task_id} ({task_type})")
        
        try:
            # 更新任务状态
            self.current_task = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "processing",
                "start_time": datetime.now().isoformat()
            }
            self.update_status(self.get_status())
            
            result = {"success": False, "task_id": task_id}
            
            if task_type == "contract_management":
                # 处理签约管理任务
                result = self._handle_contract_management(task)
            elif task_type == "recommendation_management":
                # 处理作品推荐任务
                result = self._handle_recommendation_management(task)
            elif task_type == "switch_user":
                # 处理切换用户任务
                result = self._handle_switch_user(task)
            elif task_type == "validate_user":
                # 处理验证用户任务
                result = self._handle_validate_user(task)
            else:
                result["error"] = f"不支持的任务类型: {task_type}"
            
            self.log(f"任务完成: {task_id} - {'成功' if result['success'] else '失败'}")
            
        except Exception as e:
            self.log(f"任务处理异常: {task_id} - {str(e)}")
            result = {
                "success": False,
                "task_id": task_id,
                "error": str(e)
            }
        
        finally:
            # 清除当前任务状态
            self.current_task = None
            self.update_status(self.get_status())
        
        return result
    
    def _handle_contract_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理签约管理任务"""
        try:
            # 这里需要集成浏览器自动化逻辑
            # 由于在独立进程中，需要重新初始化浏览器连接
            
            self.log("开始执行签约管理流程...")
            
            # 模拟签约管理过程
            # 实际实现中，这里会调用浏览器自动化代码
            time.sleep(2)  # 模拟处理时间
            
            # 返回处理结果
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "processed_count": 5,  # 示例数据
                "skipped_count": 2,
                "message": "签约管理检查完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"签约管理处理失败: {str(e)}"
            }
    
    def _handle_recommendation_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理作品推荐任务"""
        try:
            self.log("开始执行作品推荐流程...")
            
            # 模拟作品推荐过程
            time.sleep(3)
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "processed_count": 3,
                "message": "作品推荐检查完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"作品推荐处理失败: {str(e)}"
            }
    
    def _handle_switch_user(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理切换用户任务"""
        try:
            user_id = task.get("user_id")
            if not user_id:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "缺少用户ID"
                }
            
            self.log(f"切换到用户: {user_id}")
            
            # 调用合同管理器的用户切换功能
            success = self.contract_manager.switch_user(user_id)
            
            return {
                "success": success,
                "task_id": task.get("task_id"),
                "user_id": user_id,
                "message": f"已切换到用户: {user_id}" if success else "用户切换失败"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"用户切换失败: {str(e)}"
            }
    
    def _handle_validate_user(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证用户任务"""
        try:
            self.log("验证当前用户配置...")
            
            # 调用合同管理器的用户验证功能
            is_valid = self.contract_manager.validate_current_user()
            user_info = self.contract_manager.get_current_user_info()
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "is_valid": is_valid,
                "user_info": user_info,
                "message": "用户配置验证完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"用户验证失败: {str(e)}"
            }
    
    def run_service(self):
        """运行服务主循环"""
        self.running = True
        self.log("签约上传服务启动")
        self.log(f"服务进程ID: {os.getpid()}")
        
        # 初始化状态
        self.update_status(self.get_status())
        
        try:
            while self.running:
                try:
                    # 检查是否有新任务（非阻塞）
                    if not self.task_queue.empty():
                        task = self.task_queue.get(timeout=1)
                        self.log(f"接收到新任务: {task}")
                        
                        # 处理任务
                        result = self.process_contract_task(task)
                        
                        # 将结果放入结果队列
                        self.result_queue.put(result)
                    
                    else:
                        # 没有任务时短暂休眠
                        time.sleep(0.1)
                
                except multiprocessing.queues.Empty:
                    continue
                except Exception as e:
                    self.log(f"处理任务时发生错误: {e}")
                    continue
        
        except KeyboardInterrupt:
            self.log("收到键盘中断信号")
        except Exception as e:
            self.log(f"服务运行时发生严重错误: {e}")
        finally:
            self.running = False
            self.log("签约上传服务停止")
    
    def start_task(self, task: Dict[str, Any]) -> str:
        """启动新任务（从主进程调用）"""
        task_id = task.get("task_id", f"task_{int(time.time())}")
        task["task_id"] = task_id
        
        try:
            self.task_queue.put(task, timeout=5)
            self.log(f"任务已添加到队列: {task_id}")
            return task_id
        except Exception as e:
            self.log(f"添加任务到队列失败: {e}")
            raise
    
    def get_task_result(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """获取任务结果（从主进程调用）"""
        try:
            if self.result_queue.empty():
                return None
            
            result = self.result_queue.get(timeout=timeout or 0.1)
            return result
        except multiprocessing.queues.Empty:
            return None
        except Exception as e:
            self.log(f"获取任务结果失败: {e}")
            return None


def run_contract_service_process(task_queue: multiprocessing.Queue, 
                               result_queue: multiprocessing.Queue):
    """在独立进程中运行签约服务的入口函数"""
    # 创建服务实例
    service = ContractService()
    
    # 设置队列
    service.task_queue = task_queue
    service.result_queue = result_queue
    
    # 运行服务
    service.run_service()


class ContractServiceClient:
    """签约服务客户端 - 在主进程中使用"""
    
    def __init__(self):
        """初始化客户端"""
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.service_process = None
        self.running = False
    
    def start_service(self) -> bool:
        """启动签约服务进程"""
        if self.running:
            return True
        
        try:
            # 创建服务进程
            self.service_process = multiprocessing.Process(
                target=run_contract_service_process,
                args=(self.task_queue, self.result_queue),
                name="ContractService"
            )
            
            self.service_process.daemon = True
            self.service_process.start()
            self.running = True
            
            print(f"✅ 签约服务进程已启动，PID: {self.service_process.pid}")
            return True
            
        except Exception as e:
            print(f"❌ 启动签约服务失败: {e}")
            return False
    
    def stop_service(self) -> bool:
        """停止签约服务进程"""
        if not self.running:
            return True
        
        try:
            if self.service_process and self.service_process.is_alive():
                self.service_process.terminate()
                self.service_process.join(timeout=5)
                
                if self.service_process.is_alive():
                    self.service_process.kill()
                    self.service_process.join()
            
            self.running = False
            print("✅ 签约服务进程已停止")
            return True
            
        except Exception as e:
            print(f"❌ 停止签约服务失败: {e}")
            return False
    
    def is_service_running(self) -> bool:
        """检查服务是否运行中"""
        return self.running and self.service_process and self.service_process.is_alive()
    
    def submit_task(self, task_type: str, **kwargs) -> str:
        """提交任务到签约服务"""
        if not self.is_service_running():
            raise RuntimeError("签约服务未运行")
        
        task = {
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        try:
            self.task_queue.put(task, timeout=5)
            task_id = task.get("task_id", f"task_{int(time.time())}")
            print(f"✅ 任务已提交: {task_id} ({task_type})")
            return task_id
        except Exception as e:
            print(f"❌ 提交任务失败: {e}")
            raise
    
    def get_task_result(self, timeout: Optional[float] = 30.0) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        if not self.is_service_running():
            return None
        
        try:
            result = self.result_queue.get(timeout=timeout)
            return result
        except multiprocessing.queues.Empty:
            return None
        except Exception as e:
            print(f"❌ 获取任务结果失败: {e}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            # 读取状态文件
            status_file = Path("logs/contract_service_status.json")
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "running": False,
                    "error": "状态文件不存在"
                }
        except Exception as e:
            return {
                "running": False,
                "error": f"读取状态文件失败: {str(e)}"
            }


if __name__ == "__main__":
    # 直接运行服务时，启动独立进程模式
    service = ContractService()
    service.run_service()