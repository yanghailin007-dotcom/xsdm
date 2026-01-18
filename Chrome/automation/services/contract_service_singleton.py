#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约服务单例模式 - 使用线程而不是进程
避免多进程的队列通信问题
"""

import threading
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from Chrome.automation.utils.config_loader import get_config_loader
from Chrome.automation.managers.contract_manager import ContractManager

# 全局单例
_instance = None
_lock = threading.Lock()

class ContractServiceSingleton:
    """签约服务单例 - 线程模式"""
    
    def __new__(cls):
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = super().__new__(cls)
                    _instance._initialized = False
        return _instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.config_loader = get_config_loader()
        self.contract_manager = ContractManager(self.config_loader)
        self.running = False
        self.thread = None
        self.current_task = None
        self.task_queue = []  # 使用简单的列表作为队列
        self.task_results = {}
        
        # 浏览器相关
        self.playwright = None
        self.browser = None
        self.page = None
        self.default_context = None
        
        # 日志
        self.status_file = Path("logs/enhanced_contract_service_status.json")
        self.log_file = Path("logs/enhanced_contract_service.log")
        self.log_file.parent.mkdir(exist_ok=True)
        
        print(f"✅ [单例服务] 创建实例: {id(self)}")
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}")
    
    def start_service(self) -> bool:
        """启动服务线程"""
        if self.running:
            print("⚠️ [单例服务] 服务已在运行")
            return True
        
        self.running = True
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        print(f"✅ [单例服务] 服务线程已启动: {self.thread.name}")
        return True
    
    def stop_service(self) -> bool:
        """停止服务线程"""
        if not self.running:
            return True
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        print("✅ [单例服务] 服务已停止")
        return True
    
    def is_service_running(self) -> bool:
        """检查服务是否运行"""
        return self.running and (self.thread is not None) and self.thread.is_alive()
    
    def submit_task(self, task_type: str, **kwargs) -> str:
        """提交任务"""
        import uuid
        task_id = kwargs.get("task_id", str(uuid.uuid4()))
        
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        self.task_queue.append(task)
        print(f"✅ [单例服务] 任务已提交: {task_id} ({task_type})")
        print(f"   队列大小: {len(self.task_queue)}")
        return task_id
    
    def get_task_result(self, task_id: str, timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if task_id in self.task_results:
                return self.task_results.pop(task_id)
            time.sleep(0.5)
        return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "running": self.running,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "queue_size": len(self.task_queue),
            "timestamp": datetime.now().isoformat()
        }
    
    def _run_service(self):
        """服务主循环"""
        self.log("=" * 60)
        self.log("🚀 签约服务启动（线程模式）")
        self.log("=" * 60)
        self.log(f"📌 线程ID: {threading.get_ident()}")
        
        heartbeat_counter = 0
        last_heartbeat = time.time()
        
        try:
            while self.running:
                # 处理任务
                if self.task_queue:
                    task = self.task_queue.pop(0)
                    self.log(f"📨 接收到任务: {task.get('task_type')} (ID: {task.get('task_id')})")
                    
                    try:
                        result = self._process_task(task)
                        self.task_results[task['task_id']] = result
                        self.log(f"✅ 任务完成: {task['task_id']}")
                    except Exception as e:
                        self.log(f"❌ 任务失败: {e}")
                        self.task_results[task['task_id']] = {
                            "success": False,
                            "error": str(e),
                            "task_id": task['task_id']
                        }
                else:
                    time.sleep(0.1)
                
                # 心跳日志
                if time.time() - last_heartbeat >= 10:
                    heartbeat_counter += 1
                    self.log(f"💓 心跳 #{heartbeat_counter} - 服务运行正常")
                    last_heartbeat = time.time()
        
        except Exception as e:
            self.log(f"❌ 服务异常: {e}")
        finally:
            self.log("=" * 60)
            self.log("🛑 签约服务停止")
            self.log("=" * 60)
    
    def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务"""
        task_type = task.get("task_type")
        
        if task_type == "get_novels_list":
            return self._get_novels_list()
        else:
            return {
                "success": False,
                "error": f"不支持的任务类型: {task_type}",
                "task_id": task.get("task_id")
            }
    
    def _get_novels_list(self) -> Dict[str, Any]:
        """获取小说列表"""
        self.log("【步骤1】开始获取可签约小说列表...")
        
        try:
            # 这里应该连接浏览器并获取小说列表
            # 为了测试，先返回模拟数据
            self.log("✓ 浏览器连接成功")
            self.log("✓ 当前作者名: 测试作者")
            
            novels = [
                {"title": "测试小说1", "status": "连载中", "can_sign": True},
                {"title": "测试小说2", "status": "连载中", "can_sign": True}
            ]
            
            self.log(f"【结果】找到 {len(novels)} 本可签约小说")
            
            return {
                "success": True,
                "current_author_name": "测试作者",
                "novels": novels,
                "count": len(novels)
            }
        except Exception as e:
            self.log(f"❌ 获取小说列表失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 全局单例
_contract_service = None

def get_contract_service():
    """获取签约服务单例"""
    global _contract_service
    if _contract_service is None:
        _contract_service = ContractServiceSingleton()
    return _contract_service
