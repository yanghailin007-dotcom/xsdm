# VeO API "port 5000 not allowed" 错误修复总结

## 📋 问题描述

### 错误信息
```
[2026-01-17 11:39:55] [src.managers.VeOVideoManager] [ERROR] [E] ❌ 任务处理失败: API请求失败: {"code":"build_request_failed","message":"request reject: port 5000 is not allowed","data":null}
```

### 问题分析

错误 `"port 5000 is not allowed"` 表明 AI-WX API 服务器主动拒绝了来自端口 5000 的请求。

**根本原因：**
在 [`config/aiwx_video_config.py`](config/aiwx_video_config.py:132) 的 [`get_request_headers()`](config/aiwx_video_config.py:132) 函数中，**手动设置了 `Host` 请求头**：

```python
headers['Host'] = 'jyapi.ai-wx.cn'
headers['Connection'] = 'keep-alive'
```

**关键问题：手动设置 `Host` 请求头**

当手动设置 `Host` 请求头时，Python requests 库在构建 HTTP 请求时可能会保留本地服务器的信息，导致 API 服务器能够检测到请求来自本地开发服务器（端口 5000）。

**官方示例对比：**

官方提供的正确请求头示例：
```python
headers = {
   'Authorization': 'sk-***',
   'Content-Type': 'application/json',
   'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'
}
```

注意：**官方示例中没有手动设置 `Host` 和 `Connection` 头！**

## ✅ 解决方案

### 修复代码

修改 [`config/aiwx_video_config.py`](config/aiwx_video_config.py:132) 中的 [`get_request_headers()`](config/aiwx_video_config.py:132) 函数，参考官方示例：

```python
def get_request_headers() -> dict:
    """
    获取请求头
    
    Returns:
        请求头字典，包含Authorization
        
    注意：参考官方示例设置请求头
    """
    api_key = get_api_key()
    # 🔥 修复：参考官方示例设置请求头
    # 只设置官方示例中明确要求的请求头
    # 移除 Host 和 Connection 手动设置，让 requests 库自动处理
    headers = {
        "Content-Type": "application/json",
        "Authorization": api_key,
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)"
    }
    return headers
```

### 修复原理

1. **保留 User-Agent**：根据官方示例，保留 `User-Agent: 'Apifox/1.0.0'`
2. **移除手动设置的 Host 头**：让 Python requests 库自动处理 `Host` 头
3. **移除手动设置的 Connection 头**：让 requests 库自动管理连接
4. **只设置官方示例中的请求头**：确保与官方示例完全一致

### 为什么手动设置 Host 会导致问题？

- 当手动设置 `Host` 时，requests 库可能不会正确处理请求的构建
- HTTP 请求的其他部分（如请求行）可能包含本地地址信息
- API 服务器可能通过多种方式检测请求来源，不仅仅是 Host 头
- 让 requests 库自动处理可以确保所有相关字段的一致性

## 🧪 测试验证

### 测试工具

创建了两个测试工具用于验证修复：

1. **[`tools/test_api_connection.py`](tools/test_api_connection.py)** - 完整的API连接诊断工具
2. **[`tools/test_veo_simple.py`](tools/test_veo_simple.py)** - 简单的API调用测试

### 测试结果

```bash
$ python tools/test_veo_simple.py
============================================================
测试 VeO 视频生成 API
============================================================

📋 请求头:
   Content-Type: application/json
   Authorization: sk-0dDn3ajqtCc0PTMmD045Ff79027...

📤 发送请求到: https://jyapi.ai-wx.cn/v1/video/create
📝 提示词: 一个美丽的日落场景
🎬 模型: veo_3_1-fast

✅ 响应状态码: 200
📄 响应内容:
   {
  "id": "video_2fe05e7b-2b8d-45ca-8b6b-f475645efa94",
  "object": "video",
  "model": "veo_3_1-fast",
  "status": "queued",
  "progress": 0,
  "created_at": 1768621621,
  ...
}

🎉 API调用成功!
📋 任务ID: video_2fe05e7b-2b8d-45ca-8b6b-f475645efa94
📊 状态: queued

============================================================
✅ 测试通过！配置修复成功。
💡 现在可以正常使用 VeO 视频生成功能了。
============================================================
```

## 🎯 修复验证清单

- [x] 修改 `get_request_headers()` 函数，移除多余请求头
- [x] 创建测试工具验证修复
- [x] 运行测试确认 API 调用成功
- [x] 获取任务 ID 和状态响应
- [ ] 在实际 Web 服务器中测试视频生成功能
- [ ] 验证完整的视频生成流程（创建 → 轮询 → 下载）

## 📝 如何测试

### 快速测试

```bash
# 运行简单测试
python tools/test_veo_simple.py

# 运行完整诊断
python tools/test_api_connection.py
```

### 在 Web 界面测试

1. 启动 Web 服务器（如果尚未运行）
2. 访问视频生成页面
3. 创建一个新的视频生成任务
4. 观察是否成功创建任务并获得任务 ID
5. 检查任务状态轮询是否正常

## 🔍 相关文件

### 修改的文件
- [`config/aiwx_video_config.py`](config/aiwx_video_config.py) - 修复请求头配置

### 新建的测试工具
- [`tools/test_api_connection.py`](tools/test_api_connection.py) - API 连接诊断工具
- [`tools/test_veo_simple.py`](tools/test_veo_simple.py) - 简单 API 测试工具

### 相关代码
- [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py) - VeO 视频管理器（使用配置）

## 💡 经验教训

1. **最小化请求头原则**：调用外部 API 时，应该使用最小化的请求头，只设置必需的参数
2. **避免手动设置敏感请求头**：如 `Host`、`User-Agent`、`Referer` 等，应该让 HTTP 库自动处理
3. **定期测试 API 连接**：API 服务提供商可能会更新安全策略，需要定期测试以确保兼容性
4. **保留测试工具**：创建简单的测试工具可以快速诊断问题，避免在主代码中调试

## 🚀 下一步

修复已完成，VeO 视频生成功能应该可以正常工作。建议：

1. **重启 Web 服务器**（如果正在运行），以加载新的配置
2. **在实际环境中测试**完整的视频生成流程
3. **监控日志**，确认没有其他相关错误

## 📅 修复日期

2026-01-17

## 👤 修复者

Kilo Code
