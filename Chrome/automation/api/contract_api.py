#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约上传API接口
为Web服务器提供签约上传功能的API接口
"""

import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# 导入签约服务客户端
from ..services.enhanced_contract_service import enhanced_contract_client


class ContractAPI:
    """签约上传API类"""
    
    def __init__(self):
        """初始化API"""
        self.client = enhanced_contract_client
        self.active_tasks = {}  # 存储活动任务的信息
        self.task_results = {}  # 存储任务结果缓存
        
        # 启动结果监控线程
        self.result_monitor_thread = threading.Thread(target=self._monitor_results, daemon=True)
        self.result_monitor_thread.start()
    
    def _monitor_results(self):
        """监控任务结果的后台线程"""
        while True:
            try:
                # 获取任务结果
                result = self.client.get_task_result(timeout=1.0)
                if result:
                    task_id = result.get("task_id")
                    if task_id:
                        self.task_results[task_id] = {
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        # 如果任务完成，从活动任务中移除
                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]
                
                # 清理过期的任务结果（保留1小时）
                current_time = datetime.now()
                expired_tasks = []
                for task_id, task_data in self.task_results.items():
                    task_time = datetime.fromisoformat(task_data["timestamp"])
                    if (current_time - task_time).seconds > 3600:
                        expired_tasks.append(task_id)
                
                for task_id in expired_tasks:
                    del self.task_results[task_id]
                
            except Exception as e:
                print(f"监控任务结果时出错: {e}")
            
            import time
            time.sleep(2)  # 每2秒检查一次
    
    def start_service(self) -> Dict[str, Any]:
        """启动签约服务"""
        try:
            success = self.client.start_service()
            return {
                "success": success,
                "message": "签约服务启动成功" if success else "签约服务启动失败",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "启动签约服务时发生异常",
                "timestamp": datetime.now().isoformat()
            }
    
    def stop_service(self) -> Dict[str, Any]:
        """停止签约服务"""
        try:
            success = self.client.stop_service()
            return {
                "success": success,
                "message": "签约服务停止成功" if success else "签约服务停止失败",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "停止签约服务时发生异常",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            status = self.client.get_service_status()
            status["api_active"] = True
            status["active_tasks_count"] = len(self.active_tasks)
            status["cached_results_count"] = len(self.task_results)
            return status
        except Exception as e:
            return {
                "running": False,
                "api_active": True,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def submit_contract_management_task(self, **kwargs) -> Dict[str, Any]:
        """提交签约管理任务"""
        try:
            task_id = self.client.submit_task("contract_management", **kwargs)
            self.active_tasks[task_id] = {
                "task_type": "contract_management",
                "status": "submitted",
                "submit_time": datetime.now().isoformat(),
                **kwargs
            }
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "签约管理任务已提交",
                "task_type": "contract_management",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "提交签约管理任务失败",
                "timestamp": datetime.now().isoformat()
            }
    
    def submit_recommendation_management_task(self, **kwargs) -> Dict[str, Any]:
        """提交作品推荐任务"""
        try:
            task_id = self.client.submit_task("recommendation_management", **kwargs)
            self.active_tasks[task_id] = {
                "task_type": "recommendation_management",
                "status": "submitted",
                "submit_time": datetime.now().isoformat(),
                **kwargs
            }
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "作品推荐任务已提交",
                "task_type": "recommendation_management",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "提交作品推荐任务失败",
                "timestamp": datetime.now().isoformat()
            }
    
    def submit_switch_user_task(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """提交用户切换任务"""
        try:
            if not user_id:
                return {
                    "success": False,
                    "error": "用户ID不能为空",
                    "message": "用户切换任务提交失败",
                    "timestamp": datetime.now().isoformat()
                }
            
            task_id = self.client.submit_task("switch_user", user_id=user_id, **kwargs)
            self.active_tasks[task_id] = {
                "task_type": "switch_user",
                "status": "submitted",
                "submit_time": datetime.now().isoformat(),
                "user_id": user_id,
                **kwargs
            }
            
            return {
                "success": True,
                "task_id": task_id,
                "message": f"用户切换任务已提交: {user_id}",
                "task_type": "switch_user",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "提交用户切换任务失败",
                "timestamp": datetime.now().isoformat()
            }
    
    def submit_validate_user_task(self, **kwargs) -> Dict[str, Any]:
        """提交用户验证任务"""
        try:
            task_id = self.client.submit_task("validate_user", **kwargs)
            self.active_tasks[task_id] = {
                "task_type": "validate_user",
                "status": "submitted",
                "submit_time": datetime.now().isoformat(),
                **kwargs
            }
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "用户验证任务已提交",
                "task_type": "validate_user",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "提交用户验证任务失败",
                "timestamp": datetime.now().isoformat()
            }
    
    def submit_upload_novel_task(self, novel_title: str, **kwargs) -> Dict[str, Any]:
        """提交小说上传任务"""
        try:
            if not novel_title:
                return {
                    "success": False,
                    "error": "小说标题不能为空",
                    "message": "小说上传任务提交失败",
                    "timestamp": datetime.now().isoformat()
                }
            
            task_id = self.client.submit_task("upload_novel", novel_title=novel_title, **kwargs)
            self.active_tasks[task_id] = {
                "task_type": "upload_novel",
                "status": "submitted",
                "submit_time": datetime.now().isoformat(),
                "novel_title": novel_title,
                **kwargs
            }
            
            return {
                "success": True,
                "task_id": task_id,
                "message": f"小说上传任务已提交: {novel_title}",
                "task_type": "upload_novel",
                "novel_title": novel_title,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "提交小说上传任务失败",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            # 检查是否在活动任务中
            if task_id in self.active_tasks:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "processing",
                    "task_info": self.active_tasks[task_id],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 检查是否在结果缓存中
            if task_id in self.task_results:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "completed",
                    "result": self.task_results[task_id]["result"],
                    "completed_time": self.task_results[task_id]["timestamp"],
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "success": False,
                "error": "任务不存在",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务信息"""
        try:
            return {
                "success": True,
                "active_tasks": self.active_tasks,
                "completed_tasks": {
                    task_id: task_data["result"] 
                    for task_id, task_data in self.task_results.items()
                },
                "active_count": len(self.active_tasks),
                "completed_count": len(self.task_results),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_service_logs(self, lines: int = 100) -> Dict[str, Any]:
        """获取服务日志"""
        try:
            log_file = Path("logs/enhanced_contract_service.log")
            if not log_file.exists():
                return {
                    "success": True,
                    "logs": [],
                    "message": "日志文件不存在",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 读取最后几行日志
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return {
                "success": True,
                "logs": [line.strip() for line in recent_lines],
                "total_lines": len(all_lines),
                "showing_lines": len(recent_lines),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 创建全局API实例
contract_api = ContractAPI()