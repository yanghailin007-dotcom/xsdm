# API端点池配置指南

## 概述

API端点池功能允许你配置多个API提供商和端点，实现：

1. **优先级调度**：高优先级端点优先使用
2. **故障转移**：主端点失败时自动切换到备用端点
3. **健康检查**：自动监控端点可用性，动态调整优先级
4. **灵活配置**：支持添加任意数量的备用端点

## 快速开始

### 1. 配置端点池

在 `config/config.py` 中配置 `api_endpoints`：

```python
CONFIG = {
    # ... 其他配置 ...
    
    "api_endpoints": {
        "gemini": [
            {
                "name": "lemon-api",           # 端点名称
                "api_url": "https://new.lemonapi.site/v1",
                "api_key": "sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg",
                "model": "gemini-3.1-pro-preview",
                "priority": 1,                 # 优先级（1最高）
                "enabled": True,
                "timeout": 120,
                "max_retries": 3
            },
            {
                "name": "xiaochuang",          # 备用端点
                "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
                "api_key": "sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw",
                "model": "gemini-3-pro-preview",
                "priority": 2,                 # 优先级较低
                "enabled": True,
                "timeout": 120,
                "max_retries": 3
            }
        ]
    }
}
```

### 2. 优先级规则

- **priority = 1**：最高优先级，首先尝试
- **priority = 2**：备用，主端点失败时尝试
- **priority 越大**：优先级越低

### 3. 故障转移机制

系统会按以下顺序尝试：

1. 尝试优先级最高的可用端点
2. 如果失败（超时、网络错误、5xx错误），自动切换到下一个优先级端点
3. 记录每个端点的成功率和失败次数
4. 连续失败5次的端点会被标记为"不健康"，暂时跳过

## 高级功能

### 查看端点池状态

```python
from src.core.APIClient import APIClient

# 获取所有端点统计
stats = api_client.get_endpoint_pool_stats()
print(stats)

# 获取特定提供商状态
gemini_stats = api_client.get_endpoint_pool_stats("gemini")
print(gemini_stats)
```

输出示例：
```json
{
  "gemini": {
    "provider": "gemini",
    "total_endpoints": 2,
    "available_endpoints": 2,
    "endpoints": [
      {
        "name": "lemon-api",
        "priority": 1,
        "status": "healthy",
        "success_rate": "98.50%",
        "total_requests": 200,
        "avg_response_time": "3.24s",
        "consecutive_failures": 0
      },
      {
        "name": "xiaochuang",
        "priority": 2,
        "status": "healthy",
        "success_rate": "95.00%",
        "total_requests": 100,
        "avg_response_time": "4.56s",
        "consecutive_failures": 0
      }
    ]
  }
}
```

### 手动管理端点

```python
# 禁用某个端点
api_client.disable_endpoint("gemini", "xiaochuang")

# 启用某个端点
api_client.enable_endpoint("gemini", "xiaochuang")

# 重置端点状态（手动恢复）
api_client.reset_endpoint("gemini", "lemon-api")
```

### 自动恢复机制

- 不健康的端点会在**5分钟**后自动恢复为"降级"状态
- 降级状态的端点会被尝试使用
- 如果成功，状态恢复为"健康"
- 如果继续失败，重新标记为"不健康"

## 配置建议

### 生产环境配置

```python
"api_endpoints": {
    "gemini": [
        {
            "name": "lemon-primary",
            "api_url": "https://new.lemonapi.site/v1",
            "api_key": os.getenv('LEMON_API_KEY'),  # 使用环境变量
            "model": "gemini-3.1-pro-preview",
            "priority": 1,
            "enabled": True,
            "timeout": 120,
            "max_retries": 3
        },
        {
            "name": "lemon-secondary",
            "api_url": "https://new.lemonapi.site/v1",  # 同一提供商的不同账号
            "api_key": os.getenv('LEMON_API_KEY_BACKUP'),
            "model": "gemini-3-pro-preview",
            "priority": 2,
            "enabled": True,
            "timeout": 120,
            "max_retries": 3
        },
        {
            "name": "xiaochuang-backup",
            "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
            "api_key": os.getenv('XIAOCHUANG_API_KEY'),
            "model": "gemini-3-pro-preview",
            "priority": 3,
            "enabled": True,
            "timeout": 180,  # 备用端点可以设置更长超时
            "max_retries": 2
        }
    ]
}
```

### 测试环境配置

```python
"api_endpoints": {
    "gemini": [
        {
            "name": "test-endpoint",
            "api_url": "https://new.lemonapi.site/v1",
            "api_key": "sk-test-key",
            "model": "gemini-3.1-pro-preview",
            "priority": 1,
            "enabled": True,
            "timeout": 60,  # 测试环境超时短一些
            "max_retries": 1
        }
    ]
}
```

## 向后兼容

如果未配置 `api_endpoints`，系统会自动从旧的配置（`api_keys`, `api_urls`, `models`）创建单端点池：

```python
# 旧配置仍然有效
"api_keys": {"gemini": "sk-xxx"},
"api_urls": {"gemini": "https://api.xxx.com/v1"},
"models": {"gemini": "gemini-3-pro-preview"}
# 会自动转换为单端点池
```

## 故障排查

### 日志标识

- `🚀 开始API调用`：开始新的API调用
- `📡 发起API请求 [端点: xxx]`：正在尝试特定端点
- `✅ 端点 xxx 调用成功`：端点调用成功
- `⚠️ 端点 xxx 调用失败`：端点调用失败，将尝试下一个
- `💥 所有端点均失败`：所有端点都不可用

### 常见问题

**Q: 为什么配置了多个端点但只使用第一个？**
A: 检查第一个端点是否真的失败了（超时或错误），以及失败次数是否达到阈值。

**Q: 如何查看端点健康状态？**
A: 调用 `api_client.get_endpoint_pool_stats()` 查看详细统计。

**Q: 端点被标记为不健康后如何恢复？**
A: 等待5分钟自动恢复，或手动调用 `api_client.reset_endpoint("gemini", "端点名")`。

## API密钥安全

**强烈建议**使用环境变量存储API密钥：

```python
"api_key": os.getenv('LEMON_API_KEY', 'default-key')
```

在 `.env` 文件中：
```
LEMON_API_KEY=sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg
GEMINI_API_KEY=sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw
```

## 总结

新的API端点池功能提供了：

1. ✅ **高可用性**：自动故障转移，避免单点故障
2. ✅ **灵活性**：支持任意数量的备用端点
3. ✅ **智能调度**：基于成功率和优先级的智能选择
4. ✅ **向后兼容**：现有配置无需修改即可使用
5. ✅ **可观测性**：详细的统计信息和日志

建议在生产环境配置至少2个端点，确保服务稳定性。
