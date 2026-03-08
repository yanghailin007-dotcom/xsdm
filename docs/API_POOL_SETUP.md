# API 端点池配置指南

## 已完成的功能

### 1. 核心功能
- [x] **多API端点池**：支持为每个提供商配置多个API端点
- [x] **优先级调度**：数字越小优先级越高，优先使用高优先级端点
- [x] **故障转移**：主端点失败时自动切换到备用端点
- [x] **健康检查**：自动监控端点状态（健康/降级/不健康）
- [x] **向后兼容**：未配置新格式时自动使用旧配置

### 2. 文件变更
- `src/core/APIEndpointPool.py` - 新增：端点池核心实现
- `src/core/APIClient.py` - 修改：集成端点池功能
- `config/config.py` - 修改：添加 `api_endpoints` 配置示例

---

## 快速配置

### 步骤1: 在 config/config.py 中添加新配置

```python
CONFIG = {
    # ... 其他配置 ...
    
    # 新的多API端点池配置
    "api_endpoints": {
        "gemini": [
            {
                "name": "lemon-api",
                "api_url": "https://new.lemonapi.site/v1",
                "api_key": "sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg",
                "model": "gemini-3.1-pro-preview",
                "priority": 1,
                "enabled": True,
                "timeout": 120,
                "max_retries": 3
            },
            {
                "name": "xiaochuang-backup",
                "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
                "api_key": "sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw",
                "model": "gemini-3-pro-preview",
                "priority": 2,
                "enabled": True,
                "timeout": 120,
                "max_retries": 3
            }
        ]
    },
    
    # 旧的配置（保留用于向后兼容）
    "api_keys": { ... },
    "api_urls": { ... },
    "models": { ... }
}
```

### 步骤2: 重启服务

配置更改后重启Web服务即可生效。

---

## 工作原理

```
用户请求
    |
    v
APIClient.call_api()
    |
    v
获取 EndpointPool("gemini")
    |
    v
按优先级尝试端点:
    1. lemon-api (priority=1) --> 失败?
    2. xiaochuang-backup (priority=2) --> 失败?
    3. ...更多备用端点
    |
    v
返回结果或全部失败错误
```

---

## 端点状态流转

```
健康(HEALTHY) 
    |
    | 连续失败3次
    v
降级(DEGRADED) 
    |
    | 连续失败5次
    v
不健康(UNHEALTHY) 
    |
    | 5分钟后自动尝试恢复
    v
降级(DEGRADED) --成功--> 健康(HEALTHY)
```

---

## 日志标识说明

启动时：
```
初始化 gemini 端点池: 2 个端点
✅ 初始化 gemini 端点池: 2 个端点
   gemini: 2/2 个端点可用
       lemon-api (P1) - healthy - 成功率:100.00%
       xiaochuang-backup (P2) - healthy - 成功率:100.00%
```

调用时：
```
🚀 开始API调用 [提供商:gemini] 目的:章节生成
   可用端点: ['lemon-api', 'xiaochuang-backup']
   尝试端点: lemon-api (优先级:1)
   ✅ 端点 lemon-api 调用成功
```

故障转移时：
```
   ⚠️ 端点 lemon-api 调用失败，尝试下一个...
   尝试端点: xiaochuang-backup (优先级:2)
   ✅ 端点 xiaochuang-backup 调用成功
```

---

## 监控端点状态

在代码中获取端点池状态：

```python
from web.app import get_generator_for_user

# 获取生成器
generator = get_generator_for_user(user_id)
api_client = generator.api_client

# 查看所有端点状态
stats = api_client.get_endpoint_pool_stats()
print(stats)

# 手动管理端点
api_client.disable_endpoint("gemini", "xiaochuang-backup")  # 禁用
api_client.enable_endpoint("gemini", "xiaochuang-backup")   # 启用
api_client.reset_endpoint("gemini", "lemon-api")            # 重置状态
```

---

## 配置建议

### 生产环境（推荐）
```python
"api_endpoints": {
    "gemini": [
        {
            "name": "lemon-primary",      # 主API
            "api_url": "https://new.lemonapi.site/v1",
            "api_key": os.getenv('LEMON_API_KEY'),
            "model": "gemini-3.1-pro-preview",
            "priority": 1,
            "enabled": True,
            "timeout": 120,
            "max_retries": 3
        },
        {
            "name": "xiaochuang-backup",  # 备用API
            "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
            "api_key": os.getenv('GEMINI_API_KEY'),
            "model": "gemini-3-pro-preview",
            "priority": 2,
            "enabled": True,
            "timeout": 180,  # 备用可以设置更长超时
            "max_retries": 2
        }
    ]
}
```

### 使用环境变量（安全推荐）

在 `.env` 文件中：
```
LEMON_API_KEY=sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg
GEMINI_API_KEY=sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw
```

在 `config/config.py` 中：
```python
import os

"api_endpoints": {
    "gemini": [
        {
            "name": "lemon-api",
            "api_url": "https://new.lemonapi.site/v1",
            "api_key": os.getenv('LEMON_API_KEY', ''),  # 从环境变量读取
            "model": "gemini-3.1-pro-preview",
            "priority": 1,
            "enabled": True,
            "timeout": 120,
            "max_retries": 3
        }
    ]
}
```

---

## 故障排查

### Q: 配置了多个端点但只使用第一个？
A: 检查第一个端点是否真的失败了。系统只有在失败时才会切换到备用端点。

### Q: 端点被标记为不健康如何恢复？
A: 不健康端点会在5分钟后自动尝试恢复，或手动调用 `reset_endpoint()`。

### Q: 如何查看当前使用的端点？
A: 查看日志中的 `尝试端点: xxx` 信息。

### Q: 可以配置3个或更多端点吗？
A: 可以，没有数量限制，按需添加。

---

## 总结

新的API端点池功能提供了：

1. **高可用性**：自动故障转移，避免单点故障
2. **智能调度**：基于优先级和成功率选择端点
3. **健康监控**：自动检测和恢复故障端点
4. **灵活配置**：支持任意数量的备用端点
5. **向后兼容**：现有配置无需修改

现在你的系统会：
- 优先使用 **Lemon API** 的 **gemini-3.1-pro-preview** 模型
- 当 Lemon API 失败时，自动切换到备用 API
- 自动监控各端点健康状态
- 完全兼容现有代码逻辑
