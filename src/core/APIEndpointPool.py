"""
API端点池 - 支持多API配置和故障转移
"""
import time
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from src.utils.logger import get_logger


class EndpointStatus(Enum):
    """端点状态"""
    HEALTHY = "healthy"      # 健康
    DEGRADED = "degraded"    # 性能下降
    UNHEALTHY = "unhealthy"  # 不健康
    DISABLED = "disabled"    # 已禁用


@dataclass
class APIEndpoint:
    """API端点配置"""
    name: str                      # 端点名称（如：lemon-api, xiaochuang）
    api_url: str                   # API地址
    api_key: str                   # API密钥
    model: str                     # 模型名称
    provider: str                  # 所属提供商（gemini/deepseek等）
    priority: int = 1              # 优先级（数字越小优先级越高）
    enabled: bool = True           # 是否启用
    timeout: int = 500             # 超时时间（秒）- 支持长时间生成任务
    max_retries: int = 3           # 最大重试次数
    
    # 运行时统计
    total_requests: int = field(default=0)
    successful_requests: int = field(default=0)
    failed_requests: int = field(default=0)
    last_failure_time: Optional[float] = field(default=None)
    consecutive_failures: int = field(default=0)
    avg_response_time: float = field(default=0.0)
    status: EndpointStatus = field(default=EndpointStatus.HEALTHY)
    
    def __post_init__(self):
        self.logger = get_logger(f"APIEndpoint-{self.name}")
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """检查端点是否可用 - 连续失败不会禁用，只会降低优先级"""
        if not self.enabled:
            return False
        if self.status == EndpointStatus.DISABLED:
            return False
        return True
    
    @property
    def dynamic_priority(self) -> int:
        """动态优先级：连续失败会降低优先级，但保持可用"""
        # 基础优先级
        base = self.priority
        # 连续失败惩罚：每次失败降低10个优先级（相当于放到最后）
        penalty = self.consecutive_failures * 10
        return base + penalty
    
    def record_success(self, response_time: float):
        """记录成功请求"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        # 更新平均响应时间（指数移动平均）
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = 0.7 * self.avg_response_time + 0.3 * response_time
        
        # 如果成功率恢复，提升状态
        if self.status == EndpointStatus.DEGRADED and self.success_rate > 0.8:
            self.status = EndpointStatus.HEALTHY
    
    def record_failure(self, error_type: str = "unknown"):
        """记录失败请求 - 只降低优先级，不禁用端点"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        
        # 连续失败只会降低优先级，不会禁用端点
        if self.consecutive_failures >= 3:
            self.status = EndpointStatus.DEGRADED
            self.logger.warning(f"端点 {self.name} 连续失败 {self.consecutive_failures} 次，优先级降低至 {self.dynamic_priority}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取端点配置（用于API调用）"""
        return {
            "api_url": self.api_url,
            "api_key": self.api_key,
            "model": self.model,
            "timeout": self.timeout,
            "name": self.name
        }
    
    def __str__(self) -> str:
        return f"APIEndpoint(name={self.name}, provider={self.provider}, priority={self.priority}, status={self.status.value})"


class APIEndpointPool:
    """API端点池 - 管理同一提供商的多个API端点"""
    
    def __init__(self, provider: str, endpoints_config: List[Dict[str, Any]]):
        """
        初始化API端点池
        
        Args:
            provider: 提供商名称（如：gemini）
            endpoints_config: 端点配置列表
        """
        self.provider = provider
        self.logger = get_logger(f"APIEndpointPool-{provider}")
        self.endpoints: List[APIEndpoint] = []
        self._current_index = 0
        
        # 从配置创建端点
        for config in endpoints_config:
            if not config.get("enabled", True):
                continue
            endpoint = APIEndpoint(
                name=config.get("name", f"{provider}-{len(self.endpoints)}"),
                api_url=config["api_url"],
                api_key=config["api_key"],
                model=config["model"],
                provider=provider,
                priority=config.get("priority", 99),
                enabled=config.get("enabled", True),
                timeout=config.get("timeout", 120),
                max_retries=config.get("max_retries", 3)
            )
            self.endpoints.append(endpoint)
            self.logger.info(f"添加端点: {endpoint}")
        
        # 按优先级排序
        self.endpoints.sort(key=lambda e: e.priority)
        
        if not self.endpoints:
            self.logger.warning(f"提供商 {provider} 没有可用的端点")
        else:
            self.logger.info(f"端点池初始化完成，共 {len(self.endpoints)} 个端点")
    
    def get_available_endpoints(self) -> List[APIEndpoint]:
        """获取所有可用的端点（按动态优先级排序，连续失败的端点排在最后）"""
        available = [ep for ep in self.endpoints if ep.is_available]
        # 按动态优先级排序（连续失败多的端点优先级会被降低）
        return sorted(available, key=lambda e: (e.dynamic_priority, -e.success_rate))
    
    def get_next_endpoint(self) -> Optional[APIEndpoint]:
        """获取下一个可用的端点（轮询+动态优先级）"""
        available = self.get_available_endpoints()
        if not available:
            return None
        
        # 优先返回动态优先级最高的
        return available[0]
    
    def get_endpoint_by_name(self, name: str) -> Optional[APIEndpoint]:
        """根据名称获取端点"""
        for ep in self.endpoints:
            if ep.name == name:
                return ep
        return None
    
    def execute_with_fallback(
        self, 
        call_func: Callable[[Dict[str, Any]], Any],
        purpose: str = "API调用"
    ) -> tuple[Any, Optional[APIEndpoint]]:
        """
        执行API调用，支持故障转移
        
        Args:
            call_func: 实际的API调用函数，接收端点配置作为参数
            purpose: 调用目的（用于日志）
            
        Returns:
            (结果, 使用的端点) - 如果所有端点都失败，返回 (None, None)
        """
        tried_endpoints = []
        available = self.get_available_endpoints()
        
        if not available:
            self.logger.error(f"没有可用的 {self.provider} API端点")
            return None, None
        
        for endpoint in available:
            tried_endpoints.append(endpoint.name)
            self.logger.info(f"尝试使用端点 {endpoint.name} (优先级:{endpoint.priority}) 进行{purpose}")
            
            config = endpoint.get_config()
            start_time = time.time()
            
            try:
                result = call_func(config)
                response_time = time.time() - start_time
                
                if result is not None:
                    endpoint.record_success(response_time)
                    self.logger.info(f"端点 {endpoint.name} 调用成功 (耗时:{response_time:.2f}s)")
                    return result, endpoint
                else:
                    # 返回None视为失败
                    endpoint.record_failure("empty_response")
                    self.logger.warning(f"端点 {endpoint.name} 返回空结果")
                    
            except Exception as e:
                response_time = time.time() - start_time
                endpoint.record_failure(type(e).__name__)
                self.logger.error(f"端点 {endpoint.name} 调用失败: {e}")
        
        # 所有端点都失败
        self.logger.error(f"所有 {self.provider} 端点均失败，已尝试: {tried_endpoints}")
        return None, None
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取端点池统计信息"""
        return {
            "provider": self.provider,
            "total_endpoints": len(self.endpoints),
            "available_endpoints": len(self.get_available_endpoints()),
            "endpoints": [
                {
                    "name": ep.name,
                    "priority": ep.priority,
                    "dynamic_priority": ep.dynamic_priority,
                    "status": ep.status.value,
                    "is_available": ep.is_available,
                    "success_rate": f"{ep.success_rate:.2%}",
                    "total_requests": ep.total_requests,
                    "avg_response_time": f"{ep.avg_response_time:.2f}s",
                    "consecutive_failures": ep.consecutive_failures
                }
                for ep in sorted(self.endpoints, key=lambda e: e.priority)
            ]
        }
    
    def reset_endpoint(self, name: str) -> bool:
        """重置指定端点的状态（手动恢复）"""
        endpoint = self.get_endpoint_by_name(name)
        if endpoint:
            endpoint.status = EndpointStatus.HEALTHY
            endpoint.consecutive_failures = 0
            endpoint.last_failure_time = None
            self.logger.info(f"手动重置端点 {name} 状态为健康")
            return True
        return False
    
    def disable_endpoint(self, name: str) -> bool:
        """禁用指定端点"""
        endpoint = self.get_endpoint_by_name(name)
        if endpoint:
            endpoint.enabled = False
            endpoint.status = EndpointStatus.DISABLED
            self.logger.info(f"禁用端点 {name}")
            return True
        return False
    
    def enable_endpoint(self, name: str) -> bool:
        """启用指定端点"""
        endpoint = self.get_endpoint_by_name(name)
        if endpoint:
            endpoint.enabled = True
            endpoint.status = EndpointStatus.HEALTHY
            endpoint.consecutive_failures = 0
            self.logger.info(f"启用端点 {name}")
            return True
        return False
    
    def reset_all_endpoints(self) -> int:
        """重置所有端点为健康状态，返回重置的端点数量"""
        reset_count = 0
        for endpoint in self.endpoints:
            if endpoint.status != EndpointStatus.HEALTHY or endpoint.consecutive_failures > 0:
                old_status = endpoint.status
                endpoint.status = EndpointStatus.HEALTHY
                endpoint.consecutive_failures = 0
                endpoint.last_failure_time = None
                self.logger.info(f"🔄 重置端点 {endpoint.name}: {old_status.value} -> healthy")
                reset_count += 1
        if reset_count > 0:
            self.logger.info(f"✅ 共重置 {reset_count} 个端点")
        return reset_count
