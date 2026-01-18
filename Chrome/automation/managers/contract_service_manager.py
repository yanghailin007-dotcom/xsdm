#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约服务管理器 - 进程安全的单例模式
确保整个应用只有一个contract_api实例
"""

import threading
from Chrome.automation.api.contract_api import ContractAPI

class ContractServiceManager:
    """签约服务管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.api = ContractAPI()
        print(f"✅ [服务管理器] 创建单例ContractAPI: {id(self.api)}")
        print(f"✅ [服务管理器] 客户端队列ID: task_queue={id(self.api.client.task_queue)}, result_queue={id(self.api.client.result_queue)}")
    
    def get_api(self):
        """获取API实例"""
        return self.api

# 全局单例
_service_manager = None

def get_service_manager():
    """获取服务管理器单例"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ContractServiceManager()
    return _service_manager

def get_contract_api():
    """获取ContractAPI实例（兼容接口）"""
    return get_service_manager().get_api()
