# OpenAI 标准视频生成接口设计

基于 Google Vertex AI Gemini API 文档，设计符合 OpenAI API 规范的视频生成接口。

## 概述

本设计参考了 OpenAI API 的标准格式，同时针对视频生成场景进行了扩展，支持多模态输入（文本、图片、音频）生成视频内容。

## API 端点

### 1. 创建视频生成任务

```
POST /v1/videos/generations
```

### 2. 查询生成状态

```
GET /v1/videos/generations/{generation_id}
```

### 3. 列出生成任务

```
GET /v1/videos/generations
```

### 4. 取消生成任务

```
POST /v1/videos/generations/{generation_id}/cancel
```

### 5. 流式生成（Server-Sent Events）

```
POST /v1/videos/generations/stream
```

---

## 请求格式

### 创建视频生成任务

**端点:** `POST /v1/videos/generations`

**请求头:**
```
Content-Type: application/json
Authorization: Bearer {api_key}
```

**请求体:**

```json
{
  "model": "video-model-name",
  "prompt": "视频生成的文本描述",
  "input": {
    "type": "multimodal",
    "text": "主提示文本",
    "images": [
      {
        "type": "image_url",
        "image_url": {
          "url": "https://example.com/image.jpg",
          "detail": "high"
        }
      }
    ],
    "video": {
      "type": "video_url",
      "video_url": {
        "url": "gs://bucket/video.mp4",
        "metadata": {
          "start_offset": {
            "seconds": 0,
            "nanos": 0
          },
          "end_offset": {
            "seconds": 10,
            "nanos": 0
          },
          "fps": 24.0
        }
      }
    },
    "audio": {
      "type": "audio_url",
      "audio_url": {
        "url": "gs://bucket/audio.mp3"
      }
    }
  },
  "generation_config": {
    "duration_seconds": 5,
    "resolution": "1080p",
    "aspect_ratio": "16:9",
    "fps": 24,
    "style": "cinematic",
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 40,
    "seed": 42,
    "num_videos": 1
  },
  "output_config": {
    "format": "mp4",
    "codec": "h264",
    "quality": "high",
    "include_audio": true
  },
  "safety_settings": [
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
  ],
  "system_instruction": "生成高质量、专业风格的视频内容",
  "metadata": {
    "user_id": "user_123",
    "project_id": "project_456",
    "labels": {
      "purpose": "marketing",
      "version": "v1.0"
    }
  }
}
```

### 请求参数说明

#### 顶层参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 使用的视频生成模型名称 |
| `prompt` | string | 是 | 视频生成的主要文本描述 |
| `input` | object | 否 | 多模态输入配置 |
| `generation_config` | object | 否 | 生成配置参数 |
| `output_config` | object | 否 | 输出配置参数 |
| `safety_settings` | array | 否 | 安全设置 |
| `system_instruction` | string | 否 | 系统指令，引导生成行为 |
| `metadata` | object | 否 | 元数据标签 |

#### input 对象参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `type` | string | 输入类型：`multimodal` 或 `text_only` |
| `text` | string | 文本输入内容 |
| `images` | array | 图片输入数组 |
| `video` | object | 视频参考输入 |
| `audio` | object | 音频输入 |

#### generation_config 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `duration_seconds` | integer | 5 | 生成视频时长（秒） |
| `resolution` | string | "1080p" | 视频分辨率：`720p`, `1080p`, `4k` |
| `aspect_ratio` | string | "16:9" | 宽高比：`16:9`, `9:16`, `1:1`, `4:3` |
| `fps` | integer | 24 | 帧率：`24`, `30`, `60` |
| `style` | string | "cinematic" | 视频风格：`cinematic`, `anime`, `realistic`, `artistic` |
| `temperature` | float | 1.0 | 生成随机性（0.0-2.0） |
| `top_p` | float | 0.95 | 核采样参数（0.0-1.0） |
| `top_k` | integer | 40 | Top-K 采样参数 |
| `seed` | integer | 随机 | 随机种子，用于确定性生成 |
| `num_videos` | integer | 1 | 生成视频数量（1-8） |

#### output_config 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `format` | string | "mp4" | 输出格式：`mp4`, `webm`, `mov` |
| `codec` | string | "h264" | 视频编码：`h264`, `h265`, `vp9` |
| `quality` | string | "high" | 质量级别：`low`, `medium`, `high` |
| `include_audio` | boolean | true | 是否包含音频 |

#### safety_settings 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | enum | 安全类别（见下方枚举值） |
| `threshold` | enum | 屏蔽阈值（见下方枚举值） |
| `method` | enum | 屏蔽方法：`PROBABILITY` 或 `SEVERITY` |

**安全类别 (HarmCategory):**
- `HARM_CATEGORY_HATE_SPEECH` - 仇恨言论
- `HARM_CATEGORY_DANGEROUS_CONTENT` - 危险内容
- `HARM_CATEGORY_HARASSMENT` - 骚扰
- `HARM_CATEGORY_SEXUALLY_EXPLICIT` - 露骨色情内容

**屏蔽阈值 (HarmBlockThreshold):**
- `BLOCK_NONE` - 不屏蔽
- `BLOCK_ONLY_HIGH` - 仅屏蔽高阈值
- `BLOCK_MEDIUM_AND_ABOVE` - 屏蔽中等及以上
- `BLOCK_LOW_AND_ABOVE` - 屏蔽低及以上

---

## 响应格式

### 创建任务响应（202 Accepted）

```json
{
  "id": "gen_abc123xyz456",
  "object": "video.generation",
  "created": 1699874567,
  "model": "video-model-name",
  "status": "processing",
  "prompt": "视频生成的文本描述",
  "generation_config": {
    "duration_seconds": 5,
    "resolution": "1080p",
    "aspect_ratio": "16:9",
    "fps": 24
  },
  "estimated_completion_time": "2024-01-12T10:30:00Z",
  "metadata": {
    "user_id": "user_123",
    "project_id": "project_456"
  }
}
```

### 查询状态响应（200 OK）

```json
{
  "id": "gen_abc123xyz456",
  "object": "video.generation",
  "created": 1699874567,
  "completed": 1699875200,
  "model": "video-model-name",
  "status": "completed",
  "prompt": "视频生成的文本描述",
  "result": {
    "videos": [
      {
        "id": "video_001",
        "url": "https://cdn.example.com/videos/gen_abc123xyz456_001.mp4",
        "duration_seconds": 5.0,
        "resolution": "1920x1080",
        "fps": 24,
        "size_bytes": 52428800,
        "format": "mp4",
        "thumbnail_url": "https://cdn.example.com/thumbnails/gen_abc123xyz456_001.jpg",
        "metadata": {
          "codec": "h264",
          "bitrate": "8000000",
          "has_audio": true
        }
      }
    ],
    "finish_reason": "STOP",
    "safety_ratings": [
      {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "probability": "NEGLIGIBLE",
        "blocked": false
      }
    ]
  },
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 0,
    "total_tokens": 150,
    "video_seconds": 5.0
  },
  "error": null
}
```

### 错误响应

```json
{
  "error": {
    "message": "Invalid request: duration_seconds must be between 1 and 60",
    "type": "invalid_request_error",
    "param": "generation_config.duration_seconds",
    "code": "invalid_duration"
  }
}
```

---

## 流式响应格式

使用 Server-Sent Events (SSE) 进行流式传输。

**请求:**
```bash
curl -X POST https://api.example.com/v1/videos/generations/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {api_key}" \
  -d '{
    "model": "video-model-name",
    "prompt": "生成视频"
  }'
```

**事件流:**

```text
event: generation_started
data: {"id":"gen_abc123","status":"processing","progress":0}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":25,"stage":"analyzing_prompt"}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":50,"stage":"generating_frames"}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":75,"stage":"encoding_video"}

event: generation_complete
data: {"id":"gen_abc123","status":"completed","result":{"videos":[{"url":"https://..."}]}}

event: done
data: {}
```

---

## 使用示例

### Python SDK 示例

```python
import openai

# 配置客户端
client = openai.OpenAI(
    base_url="https://api.example.com/v1",
    api_key="your-api-key"
)

# 创建视频生成任务
response = client.videos.generations.create(
    model="video-model-v1",
    prompt="一位仙风道骨的剑仙，白发如雪，身穿白色仙袍，手持发光的长剑，在云端御剑飞行",
    generation_config={
        "duration_seconds": 10,
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "fps": 24,
        "style": "cinematic",
        "temperature": 1.0
    },
    input={
        "images": [
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://example.com/reference.jpg"
                }
            }
        ]
    }
)

print(f"Generation ID: {response.id}")
print(f"Status: {response.status}")

# 查询状态
generation = client.videos.generations.retrieve(response.id)
if generation.status == "completed":
    for video in generation.result.videos:
        print(f"Video URL: {video.url}")
```

### 流式生成示例

```python
import openai

client = openai.OpenAI(
    base_url="https://api.example.com/v1",
    api_key="your-api-key"
)

stream = client.videos.generations.stream(
    model="video-model-v1",
    prompt="生成一个美丽的日出场景"
)

for event in stream:
    if event.event == "progress_update":
        print(f"Progress: {event.data['progress']}% - {event.data['stage']}")
    elif event.event == "generation_complete":
        print(f"Complete! Video URL: {event.data['result']['videos'][0]['url']}")
```

### 列出生成任务

```python
generations = client.videos.generations.list(
    limit=10,
    status="completed",
    order="desc"
)

for gen in generations.data:
    print(f"{gen.id}: {gen.status} - {gen.created}")
```

---

## 错误代码

| 错误代码 | HTTP 状态 | 说明 |
|---------|----------|------|
| `invalid_request_error` | 400 | 请求参数无效 |
| `invalid_api_key` | 401 | API 密钥无效 |
| `insufficient_quota` | 429 | 配额不足 |
| `model_not_found` | 404 | 模型不存在 |
| `content_policy_violation` | 400 | 违反内容政策 |
| `generation_failed` | 500 | 生成失败 |
| `timeout` | 408 | 请求超时 |
| `rate_limit_exceeded` | 429 | 超过速率限制 |

---

## 注意事项

1. **Token 计算**: 视频生成请求中的文本和图片会转换为 token 计费
2. **视频时长限制**: 不同模型有不同的时长限制
3. **异步处理**: 视频生成是异步操作，需要轮询或使用 Webhook
4. **存储期限**: 生成的视频有存储期限，建议及时下载
5. **并发限制**: 根据账户等级有并发生成限制

---

## 最佳实践

1. **使用系统指令**: 通过 `system_instruction` 引导模型生成更符合需求的内容
2. **设置合理参数**: 根据场景调整 `temperature` 和其他生成参数
3. **参考图片**: 使用高质量参考图片可提升生成效果
4. **安全设置**: 根据应用场景配置适当的安全级别
5. **错误处理**: 实现完善的错误处理和重试机制

---

## 版本管理

建议使用版本化的模型名称：
- `video-model-v1` - 稳定版本
- `video-model-v2` - 最新版本
- `video-model` - 自动更新到最新版本

使用不带版本号的模型名称会自动更新到最新版本，但可能带来不兼容变更。