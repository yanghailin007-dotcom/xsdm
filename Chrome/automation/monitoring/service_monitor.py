#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务监控模块
监控签约上传独立进程的状态，提供管理和控制功能
"""

import os
import sys
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Chrome.automation.api.contract_api import contract_api


class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.monitoring = False
        self.monitor_thread = None
        self.status_history = []
        self.max_history_size = 1000
        self.alert_thresholds = {
            "memory_usage_percent": 80,
            "cpu_usage_percent": 70,
            "task_queue_size": 10,
            "response_time_seconds": 30
        }
        self.status_file = Path("logs/service_monitor_status.json")
        self.alerts_file = Path("logs/service_alerts.json")
        
        # 确保日志目录存在
        self.status_file.parent.mkdir(exist_ok=True)
        
    def start_monitoring(self, interval: int = 10):
        """启动监控"""
        if self.monitoring:
            return True
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print("✅ 服务监控已启动")
        return True
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        print("✅ 服务监控已停止")
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.monitoring:
            try:
                status = self._collect_service_status()
                self._process_status(status)
                time.sleep(interval)
            except Exception as e:
                print(f"监控循环出错: {e}")
                time.sleep(interval)
    
    def _collect_service_status(self) -> Dict[str, Any]:
        """收集服务状态"""
        try:
            # 获取签约服务状态
            service_status = contract_api.get_service_status()
            
            # 获取系统资源信息
            system_info = self._get_system_info()
            
            # 获取进程信息
            process_info = self._get_process_info(service_status)
            
            # 合并状态信息
            status = {
                "timestamp": datetime.now().isoformat(),
                "service": service_status,
                "system": system_info,
                "process": process_info
            }
            
            return status
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "monitoring_failed": True
            }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "uptime": time.time() - psutil.boot_time()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_process_info(self, service_status: Dict[str, Any]) -> Dict[str, Any]:
        """获取进程信息"""
        process_info = {}
        
        try:
            service_pid = service_status.get("service_pid")
            if service_pid:
                try:
                    process = psutil.Process(service_pid)
                    process_info = {
                        "pid": service_pid,
                        "status": process.status(),
                        "cpu_percent": process.cpu_percent(),
                        "memory_info": process.memory_info()._asdict(),
                        "memory_percent": process.memory_percent(),
                        "create_time": process.create_time(),
                        "num_threads": process.num_threads(),
                        "connections": len(process.connections())
                    }
                except psutil.NoSuchProcess:
                    process_info = {"error": "进程不存在"}
                except Exception as e:
                    process_info = {"error": str(e)}
            
            # 获取当前进程信息
            current_process = psutil.Process()
            process_info["monitor_process"] = {
                "pid": current_process.pid,
                "cpu_percent": current_process.cpu_percent(),
                "memory_percent": current_process.memory_percent()
            }
            
        except Exception as e:
            process_info["error"] = str(e)
        
        return process_info
    
    def _process_status(self, status: Dict[str, Any]):
        """处理状态信息"""
        # 添加到历史记录
        self.status_history.append(status)
        
        # 限制历史记录大小
        if len(self.status_history) > self.max_history_size:
            self.status_history.pop(0)
        
        # 检查告警条件
        alerts = self._check_alerts(status)
        
        # 保存状态到文件
        self._save_status_to_file(status)
        
        # 如果有告警，处理告警
        if alerts:
            self._handle_alerts(alerts)
    
    def _check_alerts(self, status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查告警条件"""
        alerts = []
        
        try:
            # 检查服务状态
            if not status.get("service", {}).get("running", False):
                alerts.append({
                    "type": "service_down",
                    "severity": "critical",
                    "message": "签约服务已停止运行",
                    "timestamp": status["timestamp"]
                })
            
            # 检查系统资源
            system_info = status.get("system", {})
            if "cpu_percent" in system_info and system_info["cpu_percent"] > self.alert_thresholds["cpu_usage_percent"]:
                alerts.append({
                    "type": "high_cpu",
                    "severity": "warning",
                    "message": f"CPU使用率过高: {system_info['cpu_percent']:.1f}%",
                    "timestamp": status["timestamp"],
                    "value": system_info["cpu_percent"]
                })
            
            if "memory_percent" in system_info and system_info["memory_percent"] > self.alert_thresholds["memory_usage_percent"]:
                alerts.append({
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"内存使用率过高: {system_info['memory_percent']:.1f}%",
                    "timestamp": status["timestamp"],
                    "value": system_info["memory_percent"]
                })
            
            # 检查进程状态
            process_info = status.get("process", {})
            if "error" in process_info and process_info.get("pid"):
                alerts.append({
                    "type": "process_error",
                    "severity": "critical",
                    "message": f"服务进程异常: {process_info['error']}",
                    "timestamp": status["timestamp"]
                })
            
        except Exception as e:
            alerts.append({
                "type": "monitor_error",
                "severity": "error",
                "message": f"监控检查异常: {str(e)}",
                "timestamp": status["timestamp"]
            })
        
        return alerts
    
    def _save_status_to_file(self, status: Dict[str, Any]):
        """保存状态到文件"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存状态文件失败: {e}")
    
    def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """处理告警"""
        try:
            # 读取现有告警
            existing_alerts = []
            if self.alerts_file.exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    existing_alerts = json.load(f)
            
            # 添加新告警
            for alert in alerts:
                alert["id"] = f"{alert['type']}_{int(time.time())}"
                existing_alerts.append(alert)
                print(f"🚨 告警: {alert['message']}")
            
            # 限制告警历史大小
            if len(existing_alerts) > 1000:
                existing_alerts = existing_alerts[-1000:]
            
            # 保存告警
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(existing_alerts, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"处理告警失败: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        try:
            if self.status_history:
                return self.status_history[-1]
            else:
                return self._collect_service_status()
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取状态历史"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_history = []
            for status in self.status_history:
                try:
                    status_time = datetime.fromisoformat(status["timestamp"])
                    if status_time >= cutoff_time:
                        filtered_history.append(status)
                except:
                    continue
            
            return filtered_history
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取告警历史"""
        try:
            if not self.alerts_file.exists():
                return []
            
            with open(self.alerts_file, 'r', encoding='utf-8') as f:
                alerts = json.load(f)
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_alerts = []
            for alert in alerts:
                try:
                    alert_time = datetime.fromisoformat(alert["timestamp"])
                    if alert_time >= cutoff_time:
                        filtered_alerts.append(alert)
                except:
                    continue
            
            return filtered_alerts
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            history = self.get_status_history(hours)
            
            if not history:
                return {"error": "没有历史数据"}
            
            # 计算统计数据
            cpu_values = []
            memory_values = []
            response_times = []
            
            for status in history:
                system_info = status.get("system", {})
                if "cpu_percent" in system_info:
                    cpu_values.append(system_info["cpu_percent"])
                if "memory_percent" in system_info:
                    memory_values.append(system_info["memory_percent"])
                
                # 计算响应时间（模拟）
                if "timestamp" in status:
                    response_times.append(1.0)  # 模拟响应时间
            
            summary = {
                "period_hours": hours,
                "data_points": len(history),
                "cpu": {
                    "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                    "max": max(cpu_values) if cpu_values else 0,
                    "min": min(cpu_values) if cpu_values else 0
                },
                "memory": {
                    "avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                    "max": max(memory_values) if memory_values else 0,
                    "min": min(memory_values) if memory_values else 0
                },
                "response_time": {
                    "avg": sum(response_times) / len(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0
                },
                "uptime_percentage": self._calculate_uptime_percentage(history)
            }
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_uptime_percentage(self, history: List[Dict[str, Any]]) -> float:
        """计算服务可用时间百分比"""
        try:
            if not history:
                return 0.0
            
            uptime_count = 0
            for status in history:
                service_status = status.get("service", {})
                if service_status.get("running", False):
                    uptime_count += 1
            
            return (uptime_count / len(history)) * 100.0
            
        except Exception:
            return 0.0


# 创建全局监控器实例
service_monitor = ServiceMonitor()