# 视频生成配置快速指南

## 📋 配置清单

### 1️⃣ 获取 API 密钥

访问 [Google AI Studio](https://makersuite.google.com/app/apikey) 创建 API 密钥

### 2️⃣ 配置 API 密钥

**方式 A: 环境变量（推荐）**

在项目根目录创建 `.env` 文件：

```bash
GOOGLE_AI_API_KEY=你的API密钥
```

**方式 B: 直接配置**

编辑 [`config/videoconfig.py`](../config/videoconfig.py:19)：

```python
GOOGLE_AI_API_KEY = '你的API密钥'
```

### 3️⃣ 验证配置

运行测试脚本：

```bash
python test_video_config.py
```

## 📁 配置文件说明

### [`config/videoconfig.py`](../config/videoconfig.py)

主配置文件，包含：

- **API 密钥**: `GOOGLE_AI_API_KEY`
- **API 端点**: `GOOGLE_AI_BASE_URL`
- **默认模型**: `DEFAULT_GOOGLE_MODEL = "gemini-2.5-flash-lite"`
- **视频配置**: `DEFAULT_VIDEO_CONFIG`
- **请求配置**: `REQUEST_CONFIG`

### [`src/managers/VideoGenerationManager.py`](../src/managers/VideoGenerationManager.py)

视频生成管理器，支持：

- ✅ 任务队列管理
- ✅ 流式响应处理
- ✅ 进度跟踪
- ✅ Google AI Platform API 集成

## 🚀 快速开始

### 基础使用

```python
from src.managers.VideoGenerationManager import get_video_generation_manager
from src.models.video_openai_models import VideoGenerationRequest

# 获取管理器
manager = get_video_generation_manager()

# 创建请求
request = VideoGenerationRequest(
    model="gemini-2.5-flash-lite",
    prompt="生成一个10秒的日落海滩视频"
)

# 生成视频
response = manager.create_generation(request)
print(f"任务ID: {response.id}")
```

### 查询状态

```python
# 查询任务
status = manager.retrieve_generation(response.id)
print(f"状态: {status.status}")

# 如果完成，获取视频URL
if status.result and status.result.videos:
    video_url = status.result.videos[0].url
    print(f"视频: {video_url}")
```

## 🎬 支持的模型

| 模型 | 说明 |
|------|------|
| `gemini-2.5-flash-lite` | 轻量级快速模型（默认） |
| `gemini-2.5-pro` | 专业高质量模型 |
| `gemini-2.0-flash` | Flash 模型 |

## 📐 视频参数

### 分辨率
- `1920x1080` - Full HD (16:9)
- `1280x720` - HD (16:9)
- `1080x1920` - 竖屏 (9:16)
- `1080x1080` - 方形 (1:1)

### 时长
5秒、10秒、15秒、20秒、30秒

### 帧率
24 fps（默认）

## 🔗 API 端点

### 流式端点（推荐）
```
https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:streamGenerateContent?key={api_key}
```

### 非流式端点
```
https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent?key={api_key}
```

## ⚙️ 配置参数

```python
DEFAULT_VIDEO_CONFIG = {
    "duration_seconds": 10,
    "resolution": "1920x1080",
    "aspect_ratio": "16:9",
    "fps": 24,
    "style": "realistic",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_videos": 1,
}
```

## 🧪 测试

```bash
# 运行配置测试
python test_video_config.py

# 运行视频生成测试
python test_openai_video_api.py
```

## 📚 相关文档

- [完整配置指南](./VIDEO_GENERATION_GOOGLE_AI_GUIDE.md)
- [系统架构文档](./VIDEO_GENERATION_SYSTEM_GUIDE.md)
- [API 设计文档](./VIDEO_GENERATION_OPENAI_API_DESIGN.md)

## ⚠️ 注意事项

1. **API 密钥安全**: 不要提交到版本控制
2. **使用限制**: 注意 Google AI 的配额限制
3. **费用监控**: 在 Google Cloud Console 监控使用量
4. **网络连接**: 确保能访问 Google AI Platform

## 🔧 故障排除

### "API密钥未设置"
→ 检查 `.env` 文件或配置文件中的密钥设置

### "HTTP 401"
→ API 密钥无效，请重新生成

### "HTTP 400"
→ 请求参数错误，检查模型名称和参数

### "生成超时"
→ 增加超时时间或简化提示词

## ✅ 配置验证

运行以下命令验证配置：

```bash
python -c "from config.videoconfig import validate_config; print(validate_config())"
```

预期输出：
```
(True, '配置验证通过')
```

## 🎉 完成！

配置完成后，您可以使用以下功能：

- ✅ 视频生成
- ✅ 任务管理
- ✅ 进度跟踪
- ✅ 流式响应
- ✅ 批量处理