# VeO 视频生成系统使用指南

## 概述

VeO 视频生成系统是基于 AI-WX API (https://jyapi.ai-wx.cn) 的视频生成服务，支持 OpenAI 标准格式的视频生成 API。

## 核心特性

### 1. 支持的模型

- `veo_3_1` - 基础模型
- `veo_3_1-portrait` - 竖屏视频
- `veo_3_1-landscape` - 横屏视频
- `veo_3_1-fast` - 快速模式
- `veo_3_1-fl` - 首尾帧模式

### 2. 支持的功能

- ✅ 文本生成视频
- ✅ 图片生成视频（单张参考图）
- ✅ 首尾帧模式（两张图片生成视频）
- ✅ 竖屏/横屏选择
- ✅ 流式响应支持

### 3. 视频参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| orientation | 视频方向 | `portrait` (竖屏), `landscape` (横屏) |
| size | 视频尺寸 | `small` (720p), `large` (1080p) |
| duration | 视频时长 | `10` 秒（目前仅支持10秒） |
| aspect_ratio | 宽高比 | `16:9` (横屏), `9:16` (竖屏) |
| enable_upsample | 是否高清 | `true` (仅横屏), `false` |

## 快速开始

### 1. 环境配置

设置 API 密钥：

```bash
# Linux/Mac
export AIWX_API_KEY='your_api_key_here'

# Windows (PowerShell)
$env:AIWX_API_KEY='your_api_key_here'

# Windows (CMD)
set AIWX_API_KEY=your_api_key_here
```

### 2. 基本使用

#### 文本生成视频

```python
from src.models.veo_models import VeOVideoRequest
from src.managers.VeOVideoManager import get_veo_video_manager

# 创建请求（OpenAI 格式）
request = VeOVideoRequest(
    model="veo_3_1",
    stream=True,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "一只可爱的橘猫在阳光下打盹"
                }
            ]
        }
    ]
)

# 获取管理器并创建任务
manager = get_veo_video_manager()
response = manager.create_generation(request)

print(f"任务ID: {response.id}")
print(f"状态: {response.status}")
```

#### 图片生成视频

```python
request = VeOVideoRequest(
    model="veo_3_1",
    stream=True,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "根据图片生成动态视频"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/image.jpg"
                    }
                }
            ]
        }
    ]
)

manager = get_veo_video_manager()
response = manager.create_generation(request)
```

#### 横屏视频

```python
request = VeOVideoRequest(
    model="veo_3_1-landscape",
    stream=True,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "美丽的日落风景"
                }
            ]
        }
    ]
)
```

#### 首尾帧模式

```python
request = VeOVideoRequest(
    model="veo_3_1-fl",
    stream=True,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "从首帧过渡到尾帧"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/frame1.jpg"  # 首帧
                    }
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/frame2.jpg"  # 尾帧
                    }
                }
            ]
        }
    ]
)
```

### 3. 查询任务状态

```python
# 查询任务状态
status_response = manager.retrieve_generation(response.id)

if status_response.status == VideoStatus.COMPLETED:
    # 获取视频结果
    if status_response.result and status_response.result.videos:
        for video in status_response.result.videos:
            print(f"视频URL: {video.url}")
            print(f"时长: {video.duration_seconds}s")
            print(f"分辨率: {video.resolution}")
```

### 4. 列出所有任务

```python
from src.models.veo_models import VideoStatus

# 列出所有任务
generations = manager.list_generations(limit=20)

# 只列出已完成的任务
completed = manager.list_generations(
    limit=10,
    status=VideoStatus.COMPLETED
)

for gen in generations:
    print(f"ID: {gen.id}, 状态: {gen.status}")
```

### 5. 流式生成

```python
# 使用流式生成
for event in manager.stream_generation(request):
    event_type = event.get("event")
    data = event.get("data", {})
    
    if event_type == "generation_started":
        print(f"任务开始: {data['id']}")
    
    elif event_type == "progress_update":
        print(f"进度: {data['progress']}% - {data['stage']}")
    
    elif event_type == "generation_complete":
        print(f"生成完成!")
        print(data)
    
    elif event_type == "generation_failed":
        print(f"生成失败: {data.get('error')}")
```

## API 参考

### VeOVideoRequest

OpenAI 标准格式的视频生成请求。

**参数:**
- `model` (str): 模型名称，如 `veo_3_1`, `veo_3_1-landscape`
- `stream` (bool): 是否使用流式响应
- `messages` (List[Dict]): 消息列表

**messages 格式:**
```python
[
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "视频描述"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "图片URL"
                }
            }
        ]
    }
]
```

### VeOGenerationResponse

视频生成响应。

**属性:**
- `id` (str): 任务ID
- `status` (VideoStatus): 任务状态
- `created` (int): 创建时间戳
- `completed` (int): 完成时间戳
- `model` (str): 使用的模型
- `prompt` (str): 提示词
- `result` (VeOGenerationResult): 生成结果
- `error` (str): 错误信息
- `usage` (VeOUsageMetadata): 使用统计

### VideoStatus

任务状态枚举。

**值:**
- `PENDING`: 等待处理
- `PROCESSING`: 处理中
- `COMPLETED`: 已完成
- `FAILED`: 失败
- `CANCELLED`: 已取消

## 配置文件

### config/aiwx_video_config.py

主要配置项：

```python
# API 配置
AIWX_BASE_URL = "https://jyapi.ai-wx.cn"
AIWX_VIDEO_CREATE_URL = f"{AIWX_BASE_URL}/v1/video/create"

# 模型配置
AIWX_MODEL_SORA_2 = "sora-2"
DEFAULT_AIWX_MODEL = AIWX_MODEL_SORA_2

# 请求配置
REQUEST_CONFIG = {
    'timeout': 300,  # 5分钟超时
    'max_retries': 3,
    'retry_delay': 2,
}

# 轮询配置
POLLING_CONFIG = {
    'enabled': True,
    'max_attempts': 60,
    'poll_interval': 5,
}
```

## 常见问题

### Q1: 如何获取 API 密钥？

联系 AI-WX 平台获取 API 密钥，然后设置环境变量 `AIWX_API_KEY`。

### Q2: 支持哪些视频时长？

目前仅支持 10 秒的视频。

### Q3: 竖屏和横屏有什么区别？

- **竖屏 (portrait)**: 9:16 宽高比，适合手机观看
- **横屏 (landscape)**: 16:9 宽高比，适合电脑/电视观看

### Q4: 首尾帧模式和参考图模式有什么区别？

- **首尾帧模式** (`-fl`): 需要两张图片，第一张作为首帧，第二张作为尾帧，生成从首帧过渡到尾帧的视频
- **参考图模式** (普通模式): 使用单张图片作为参考，生成与图片相关的视频

### Q5: 如何提高视频质量？

1. 使用 `landscape` 横屏模式
2. 设置 `enable_upsample=True` (仅横屏支持)
3. 使用 `size=large`

### Q6: 为什么任务一直处于 PENDING 状态？

可能的原因：
1. API 密钥未设置或无效
2. 网络连接问题
3. API 服务暂时不可用

检查配置并查看日志获取详细信息。

## 测试

运行测试脚本：

```bash
python test_veo_video_generation.py
```

测试脚本会：
1. 验证配置
2. 创建文本生成视频任务
3. 创建图片生成视频任务
4. 创建横屏视频任务
5. 列出所有任务

## 架构

```
┌─────────────────────────────────────────┐
│         应用层 (Flask API)              │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      VeOVideoManager (管理器)           │
│  - 任务管理                             │
│  - 队列处理                             │
│  - 状态轮询                             │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       AI-WX VeO API                     │
│  https://jyapi.ai-wx.cn/v1/video/create│
└─────────────────────────────────────────┘
```

## 注意事项

1. **API 密钥安全**: 不要在代码中硬编码 API 密钥，使用环境变量
2. **并发限制**: 注意 API 的并发请求限制
3. **错误处理**: 始终检查响应状态和错误信息
4. **超时设置**: 根据网络情况调整超时时间
5. **存储管理**: 定期清理已完成的任务文件

## 更新日志

### v1.0.0 (2025-01-12)
- ✅ 初始版本
- ✅ 支持 OpenAI 格式 API
- ✅ 支持文本生成视频
- ✅ 支持图片生成视频
- ✅ 支持首尾帧模式
- ✅ 支持流式响应
- ✅ 任务管理和轮询

## 相关文件

- `config/aiwx_video_config.py` - API 配置
- `src/models/veo_models.py` - 数据模型
- `src/managers/VeOVideoManager.py` - 管理器
- `test_veo_video_generation.py` - 测试脚本