"""
API 端点工具函数 - 支持 enabled 字段过滤
"""

from config.config import CONFIG


def get_enabled_endpoints(provider=None):
    """
    获取启用的 API 端点列表
    
    Args:
        provider: 指定提供商，为 None 则返回所有启用的端点
    
    Returns:
        dict: 按 provider 分组的启用端点列表
    """
    api_endpoints = CONFIG.get("api_endpoints", {})
    
    if provider:
        # 返回指定提供商的启用端点
        endpoints = api_endpoints.get(provider, [])
        return [ep for ep in endpoints if ep.get("enabled", True)]
    
    # 返回所有启用端点，按 provider 分组
    result = {}
    for prov, endpoints in api_endpoints.items():
        enabled = [ep for ep in endpoints if ep.get("enabled", True)]
        if enabled:  # 只返回有启用端点的提供商
            result[prov] = enabled
    
    return result


def get_enabled_providers():
    """
    获取启用的提供商列表
    
    Returns:
        list: 启用的提供商名称列表
    """
    api_endpoints = CONFIG.get("api_endpoints", {})
    
    enabled_providers = []
    for provider, endpoints in api_endpoints.items():
        # 如果提供商下有启用的端点，则该提供商启用
        if any(ep.get("enabled", True) for ep in endpoints):
            enabled_providers.append(provider)
    
    return enabled_providers


def get_enabled_provider_priority():
    """
    获取启用的提供商优先级列表
    
    Returns:
        list: 启用的提供商优先级列表
    """
    all_priority = CONFIG.get("provider_priority", [])
    enabled_providers = set(get_enabled_providers())
    
    # 过滤掉禁用的提供商，保持原有优先级顺序
    return [p for p in all_priority if p in enabled_providers]


def is_endpoint_enabled(provider, endpoint_name):
    """
    检查指定端点是否启用
    
    Args:
        provider: 提供商名称
        endpoint_name: 端点名称
    
    Returns:
        bool: 是否启用
    """
    api_endpoints = CONFIG.get("api_endpoints", {})
    endpoints = api_endpoints.get(provider, [])
    
    for ep in endpoints:
        if ep.get("name") == endpoint_name:
            return ep.get("enabled", True)
    
    return False


def get_default_provider():
    """
    获取默认提供商（必须是启用的）
    
    Returns:
        str: 默认提供商名称
    """
    default = CONFIG.get("default_provider", "gemini")
    enabled_providers = get_enabled_providers()
    
    # 如果默认提供商被禁用，使用第一个启用的提供商
    if default not in enabled_providers and enabled_providers:
        return enabled_providers[0]
    
    return default
