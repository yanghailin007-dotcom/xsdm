# Google AI Platform 视频生成配置指南

## 概述

本项目已配置支持 Google AI Platform 的视频生成功能，使用 Gemini 2.5 Flash Lite 等模型。

## 配置文件

### 1. 主配置文件

**位置**: [`config/videoconfig.py`](../config/videoconfig.py)

该文件包含所有视频生成相关的配置：

- API 密钥和端点
- 模型配置
- 请求参数
- 文件保存配置

### 2. 管理器

**位置**: [`src/managers/VideoGenerationManager.py`](../src/managers/VideoGenerationManager.py)

视频生成管理器，处理：
- 任务队列管理
- 流式响应处理
- 进度跟踪
- 结果保存

## 配置步骤

### 第一步：获取 Google AI API 密钥

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建新的 API 密钥
3. 复制 API 密钥

### 第二步：配置 API 密钥

有三种方式配置 API 密钥：

#### 方式 1：环境变量（推荐）

在 `.env` 文件中添加：

```bash
GOOGLE_AI_API_KEY=your_api_key_here
```

#### 方式 2：直接在配置文件中设置

编辑 [`config/videoconfig.py`](../config/videoconfig.py):

```python
# 在文件顶部找到这一行
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', '')

# 修改为
GOOGLE_AI_API_KEY = 'your_actual_api_key_here'
```

#### 方式 3：系统环境变量

在 Windows 上：

```cmd
setx GOOGLE_AI_API_KEY "your_api_key_here"
```

在 Linux/Mac 上：

```bash
export GOOGLE_AI_API_KEY="your_api_key_here"
```

### 第三步：验证配置

运行配置验证脚本：

```bash
python config/videoconfig.py
```

成功输出应该类似：

```
✅ 配置验证通过
📡 API端点: https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:streamGenerateContent?key=YOUR_API_KEY
🎬 默认模型: gemini-2.5-flash-lite
```

## 支持的模型

当前配置支持以下 Google AI 模型：

1. **gemini-2.5-flash-lite** (默认)
   - 轻量级快速模型
   - 适合快速生成
   
2. **gemini-2.5-pro**
   - 专业模型
   - 更高质量输出
   
3. **gemini-2.0-flash**
   - Flash 模型
   - 平衡性能和质量

## API 端点格式

### 流式端点（默认）

```
https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:streamGenerateContent?key={api_key}
```

### 非流式端点

```
https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent?key={api_key}
```

## 使用示例

### 基础使用

```python
from src.managers.VideoGenerationManager import get_video_generation_manager
from src.models.video_openai_models import VideoGenerationRequest, GenerationConfig

# 获取管理器实例
manager = get_video_generation_manager()

# 创建请求
request = VideoGenerationRequest(
    model="gemini-2.5-flash-lite",
    prompt="生成一个10秒的风景视频，展示日落时分的海滩",
    generation_config=GenerationConfig(
        duration_seconds=10,
        resolution="1920x1080",
        fps=24
    )
)

# 创建生成任务
response = manager.create_generation(request)

print(f"任务ID: {response.id}")
print(f"状态: {response.status}")
```

### 查询任务状态

```python
# 查询任务状态
generation_id = response.id
status_response = manager.retrieve_generation(generation_id)

print(f"当前状态: {status_response.status}")
if status_response.result and status_response.result.videos:
    for video in status_response.result.videos:
        print(f"视频URL: {video.url}")
```

### 列出所有任务

```python
# 列出最近20个任务
tasks = manager.list_generations(limit=20)

for task in tasks:
    print(f"ID: {task.id}, 状态: {task.status}, 创建时间: {task.created}")
```

### 流式生成

```python
# 流式生成（Server-Sent Events）
for event in manager.stream_generation(request):
    event_type = event.get("event")
    data = event.get("data")
    
    if event_type == "progress_update":
        print(f"进度: {data['progress']}% - {data['stage']}")
    elif event_type == "generation_complete":
        print("生成完成！")
        print(data)
    elif event_type == "generation_failed":
        print(f"生成失败: {data['error']}")
```

## 配置参数说明

### DEFAULT_VIDEO_CONFIG

默认视频生成配置：

```python
DEFAULT_VIDEO_CONFIG = {
    "duration_seconds": 10,      # 视频时长（秒）
    "resolution": "1920x1080",   # 分辨率
    "aspect_ratio": "16:9",      # 宽高比
    "fps": 24,                   # 帧率
    "style": "realistic",        # 风格
    "temperature": 0.7,          # 温度参数
    "top_p": 0.9,               # Top-p 采样
    "top_k": 40,                # Top-k 采样
    "num_videos": 1,            # 生成视频数量
}
```

### 支持的分辨率

- `1920x1080` - Full HD (16:9)
- `1280x720` - HD (16:9)
- `1080x1920` - Portrait (9:16)
- `720x1280` - Portrait HD (9:16)
- `1080x1080` - Square (1:1)

### 支持的时长

5秒、10秒、15秒、20秒、30秒

### REQUEST_CONFIG

请求配置：

```python
REQUEST_CONFIG = {
    'timeout': 300,        # 5分钟超时
    'max_retries': 3,      # 最大重试次数
    'retry_delay': 2,      # 重试延迟（秒）
    'default_headers': {
        "Content-Type": "application/json",
    }
}
```

## 测试配置

创建测试脚本 `test_video_config.py`:

```python
from config.videoconfig import get_api_endpoint, validate_config

# 验证配置
is_valid, message = validate_config()
if not is_valid:
    print(f"❌ 配置错误: {message}")
    exit(1)

# 获取API端点
endpoint = get_api_endpoint()
print(f"✅ API端点: {endpoint}")

# 测试请求（可选）
import requests

payload = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": "Hello"}]
        }
    ]
}

try:
    response = requests.post(endpoint, json=payload, timeout=10)
    print(f"✅ API连接成功: HTTP {response.status_code}")
except Exception as e:
    print(f"❌ API连接失败: {e}")
```

运行测试：

```bash
python test_video_config.py
```

## 故障排除

### 问题1: "API密钥未设置"

**解决方案**:
- 检查环境变量 `GOOGLE_AI_API_KEY` 是否设置
- 确认 `.env` 文件存在且包含正确的密钥
- 验证配置文件中的密钥格式

### 问题2: "API请求失败: HTTP 401"

**原因**: API密钥无效或过期

**解决方案**:
- 重新生成 API 密钥
- 确认密钥复制正确（没有多余空格）
- 检查密钥权限

### 问题3: "API请求失败: HTTP 400"

**原因**: 请求参数错误

**解决方案**:
- 检查模型名称是否正确
- 验证请求参数格式
- 查看响应错误详情

### 问题4: "生成超时"

**原因**: 请求时间过长

**解决方案**:
- 增加 `REQUEST_CONFIG['timeout']` 值
- 检查网络连接
- 尝试更简单的提示词

### 问题5: "配置验证失败"

**解决方案**:
```python
from config.videoconfig import validate_config

is_valid, message = validate_config()
print(message)
```

根据错误消息进行相应修复。

## API 使用限制

注意 Google AI Platform 的使用限制：

- 每分钟请求数限制
- 每天token限制
- 并发请求限制

查看您的 [Google Cloud Console](https://console.cloud.google.com/) 了解具体限制。

## 最佳实践

1. **环境变量管理**: 使用 `.env` 文件管理敏感信息
2. **错误处理**: 始终处理API请求可能的错误
3. **重试机制**: 配置合理的重试策略
4. **超时设置**: 根据任务复杂度调整超时时间
5. **进度跟踪**: 使用回调函数跟踪生成进度
6. **资源清理**: 及时取消不需要的任务

## 安全建议

1. **不要提交API密钥到版本控制**
2. **使用 `.gitignore` 排除 `.env` 文件**
3. **定期轮换API密钥**
4. **监控API使用量和费用**
5. **限制API密钥的权限范围**

## 相关文档

- [Google AI Platform API 文档](https://cloud.google.com/vertex-ai/docs/generative-ai/start/client-libraries)
- [Gemini API 参考文档](https://ai.google.dev/docs)
- [视频生成管理器文档](./VIDEO_GENERATION_SYSTEM_GUIDE.md)

## 更新日志

- 2026-01-12: 初始配置，添加 Google AI Platform 支持
- 支持 Gemini 2.5 Flash Lite 模型
- 实现流式响应处理
- 添加配置验证和测试脚本