"""
自定义API端点管理器
支持用户添加自己的API端点，消耗50%创造点
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# 自定义端点存储路径
CUSTOM_ENDPOINTS_FILE = Path("data/custom_endpoints.json")

# 默认折扣率
default_custom_discount = 50  # 50%

# Demo格式示例
DEMO_ENDPOINT = {
    "name": "my-custom-api",
    "api_url": "https://api.example.com/v1/chat/completions",
    "api_key": "sk-your-api-key-here",
    "model": "gpt-4",
    "assessment": "gpt-3.5-turbo",
    "priority": 1,
    "enabled": True,
    "timeout": 300,
    "max_retries": 3,
    "discount": 50,  # 50% 消耗
    "provider": "custom",  # 自定义提供商
    "description": "我的自定义API端点",
    "pros": ["价格便宜", "响应快"],
    "cons": ["稳定性待测试"]
}


class CustomEndpointManager:
    """自定义端点管理器"""
    
    def __init__(self):
        self.endpoints: List[Dict[str, Any]] = []
        self._ensure_data_dir()
        self._load_endpoints()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        CUSTOM_ENDPOINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_endpoints(self):
        """从文件加载自定义端点"""
        if CUSTOM_ENDPOINTS_FILE.exists():
            try:
                with open(CUSTOM_ENDPOINTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.endpoints = data.get('endpoints', [])
            except Exception as e:
                print(f"[CustomEndpoint] 加载失败: {e}")
                self.endpoints = []
        else:
            self.endpoints = []
    
    def _save_endpoints(self):
        """保存端点到文件"""
        try:
            data = {
                'endpoints': self.endpoints,
                'updated_at': datetime.now().isoformat()
            }
            with open(CUSTOM_ENDPOINTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[CustomEndpoint] 保存失败: {e}")
            return False
    
    def get_all_endpoints(self) -> List[Dict[str, Any]]:
        """获取所有自定义端点"""
        return [ep for ep in self.endpoints if ep.get('enabled', True)]
    
    def get_endpoint_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称获取端点"""
        for ep in self.endpoints:
            if ep.get('name') == name:
                return ep
        return None
    
    def add_endpoint(self, endpoint: Dict[str, Any]) -> tuple[bool, str]:
        """
        添加自定义端点
        
        Args:
            endpoint: 端点配置
            
        Returns:
            (成功, 消息)
        """
        # 验证必填字段
        required_fields = ['name', 'api_url', 'api_key', 'model']
        for field in required_fields:
            if not endpoint.get(field):
                return False, f"缺少必填字段: {field}"
        
        # 检查名称是否已存在
        if self.get_endpoint_by_name(endpoint['name']):
            return False, f"端点名称已存在: {endpoint['name']}"
        
        # 设置默认值
        endpoint.setdefault('provider', 'custom')
        endpoint.setdefault('priority', 1)
        endpoint.setdefault('enabled', True)
        endpoint.setdefault('timeout', 300)
        endpoint.setdefault('max_retries', 3)
        endpoint.setdefault('discount', 50)  # 默认50%消耗
        endpoint.setdefault('assessment', endpoint.get('model'))
        endpoint.setdefault('description', '自定义API端点')
        endpoint.setdefault('pros', ['自定义配置'])
        endpoint.setdefault('cons', ['需自行维护'])
        endpoint.setdefault('created_at', datetime.now().isoformat())
        
        self.endpoints.append(endpoint)
        
        if self._save_endpoints():
            return True, "添加成功"
        else:
            return False, "保存失败"
    
    def update_endpoint(self, name: str, updates: Dict[str, Any]) -> tuple[bool, str]:
        """
        更新端点配置
        
        Args:
            name: 端点名称
            updates: 更新的字段
            
        Returns:
            (成功, 消息)
        """
        endpoint = self.get_endpoint_by_name(name)
        if not endpoint:
            return False, f"端点不存在: {name}"
        
        # 更新字段（不允许修改名称）
        updates.pop('name', None)
        updates.pop('created_at', None)
        updates['updated_at'] = datetime.now().isoformat()
        
        endpoint.update(updates)
        
        if self._save_endpoints():
            return True, "更新成功"
        else:
            return False, "保存失败"
    
    def delete_endpoint(self, name: str) -> tuple[bool, str]:
        """
        删除端点
        
        Args:
            name: 端点名称
            
        Returns:
            (成功, 消息)
        """
        endpoint = self.get_endpoint_by_name(name)
        if not endpoint:
            return False, f"端点不存在: {name}"
        
        self.endpoints.remove(endpoint)
        
        if self._save_endpoints():
            return True, "删除成功"
        else:
            return False, "保存失败"
    
    def toggle_endpoint(self, name: str) -> tuple[bool, str]:
        """
        切换端点启用状态
        
        Args:
            name: 端点名称
            
        Returns:
            (成功, 消息)
        """
        endpoint = self.get_endpoint_by_name(name)
        if not endpoint:
            return False, f"端点不存在: {name}"
        
        endpoint['enabled'] = not endpoint.get('enabled', True)
        
        if self._save_endpoints():
            status = "启用" if endpoint['enabled'] else "禁用"
            return True, f"已{status}"
        else:
            return False, "保存失败"
    
    def get_demo_endpoint(self) -> Dict[str, Any]:
        """获取Demo格式示例"""
        return DEMO_ENDPOINT.copy()
    
    def get_formatted_endpoints(self) -> List[Dict[str, Any]]:
        """
        获取格式化后的端点列表（用于前端展示）
        """
        formatted = []
        for ep in self.endpoints:
            formatted.append({
                'name': ep.get('name', ''),
                'api_url': ep.get('api_url', ''),
                'api_key': self._mask_api_key(ep.get('api_key', '')),
                'model': ep.get('model', ''),
                'assessment': ep.get('assessment', ''),
                'priority': ep.get('priority', 1),
                'enabled': ep.get('enabled', True),
                'timeout': ep.get('timeout', 300),
                'discount': ep.get('discount', 50),
                'description': ep.get('description', ''),
                'pros': ep.get('pros', []),
                'cons': ep.get('cons', []),
                'provider': ep.get('provider', 'custom'),
                'is_custom': True
            })
        return formatted
    
    def _mask_api_key(self, api_key: str) -> str:
        """脱敏显示API Key"""
        if len(api_key) <= 10:
            return "***"
        return api_key[:6] + "***" + api_key[-4:]
    
    def to_api_client_format(self) -> List[Dict[str, Any]]:
        """
        转换为APIClient可用的格式
        """
        result = []
        for ep in self.endpoints:
            if not ep.get('enabled', True):
                continue
            result.append({
                'name': ep.get('name'),
                'api_url': ep.get('api_url'),
                'api_key': ep.get('api_key'),
                'model': ep.get('model'),
                'assessment': ep.get('assessment', ep.get('model')),
                'priority': ep.get('priority', 1),
                'enabled': True,
                'timeout': ep.get('timeout', 300),
                'max_retries': ep.get('max_retries', 3),
                'discount_rate': ep.get('discount', 50),  # 🔥 使用 discount_rate 字段名
                'is_custom': True
            })
        return result


# 全局管理器实例
custom_endpoint_manager = CustomEndpointManager()
