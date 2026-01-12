# OpenAI 标准视频生成 API 使用指南

本文档介绍如何使用符合 OpenAI API 标准的视频生成接口。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [API 端点](#api-端点)
- [认证](#认证)
- [请求格式](#请求格式)
- [响应格式](#响应格式)
- [流式响应](#流式响应)
- [错误处理](#错误处理)
- [Python SDK 示例](#python-sdk-示例)
- [最佳实践](#最佳实践)

## 概述

本 API 提供符合 OpenAI 标准的视频生成接口，支持：

- ✅ 多模态输入（文本、图片、视频、音频）
- ✅ 异步任务处理
- ✅ 流式响应（Server-Sent Events）
- ✅ 任务状态查询
- ✅ 安全设置
- ✅ 灵活的生成配置

## 快速开始

### 1. 启动服务器

```bash
python web/wsgi.py
```

服务器将在 `http://localhost:5000` 启动。

### 2. 创建视频生成任务

```python
import requests

url = "http://localhost:5000/v1/videos/generations"

payload = {
    "model": "video-model-v1",
    "prompt": "一位仙风道骨的剑仙，白发如雪，身穿白色仙袍",
    "generation_config": {
        "duration_seconds": 5,
        "resolution": "1080p",
        "fps": 24
    }
}

response = requests.post(url, json=payload)
data = response.json()

print(f"任务 ID: {data['id']}")
print(f"状态: {data['status']}")
```

### 3. 查询生成状态

```python
generation_id = data['id']
url = f"http://localhost:5000/v1/videos/generations/{generation_id}"

response = requests.get(url)
data = response.json()

print(f"状态: {data['status']}")
if data['status'] == 'completed':
    for video in data['result']['videos']:
        print(f"视频 URL: {video['url']}")
```

## API 端点

### 创建视频生成任务

**端点:** `POST /v1/videos/generations`

**请求体:**
```json
{
  "model": "video-model-v1",
  "prompt": "视频生成的文本描述",
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
      "threshold": "BLOCK_MEDIUM_AND_ABOVE",
      "method": "PROBABILITY"
    }
  ],
  "system_instruction": "生成高质量视频内容",
  "metadata": {
    "user_id": "user_123",
    "project_id": "project_456",
    "labels": {
      "purpose": "marketing"
    }
  }
}
```

**响应 (202 Accepted):**
```json
{
  "id": "gen_abc123xyz456",
  "object": "video.generation",
  "created": 1699874567,
  "model": "video-model-v1",
  "status": "processing",
  "prompt": "视频生成的文本描述",
  "generation_config": {
    "duration_seconds": 5,
    "resolution": "1080p",
    "aspect_ratio": "16:9",
    "fps": 24
  },
  "estimated_completion_time": "2024-01-12T10:30:00Z"
}
```

### 查询生成状态

**端点:** `GET /v1/videos/generations/{generation_id}`

**响应 (200 OK):**
```json
{
  "id": "gen_abc123xyz456",
  "object": "video.generation",
  "created": 1699874567,
  "completed": 1699875200,
  "model": "video-model-v1",
  "status": "completed",
  "result": {
    "videos": [
      {
        "id": "video_001",
        "url": "http://localhost:5000/static/generated_videos/gen_abc123.mp4",
        "duration_seconds": 5.0,
        "resolution": "1920x1080",
        "fps": 24,
        "size_bytes": 52428800,
        "format": "mp4",
        "thumbnail_url": "http://localhost:5000/static/generated_videos/gen_abc123_thumb.jpg"
      }
    ],
    "finish_reason": "FINISH_REASON_STOP"
  },
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 0,
    "total_tokens": 150,
    "video_seconds": 5.0
  }
}
```

### 列出生成任务

**端点:** `GET /v1/videos/generations`

**查询参数:**
- `limit`: 返回数量限制（默认 20）
- `status`: 状态过滤（`processing`, `completed`, `failed`）
- `order`: 排序方式（`desc` 或 `asc`）

**响应 (200 OK):**
```json
{
  "data": [
    {
      "id": "gen_abc123",
      "status": "completed",
      "created": 1699874567
    }
  ],
  "object": "list",
  "total": 1
}
```

### 取消生成任务

**端点:** `POST /v1/videos/generations/{generation_id}/cancel`

**响应 (200 OK):**
```json
{
  "success": true,
  "message": "Generation cancelled"
}
```

### 流式生成

**端点:** `POST /v1/videos/generations/stream`

**响应:** Server-Sent Events (SSE) 流

```
event: generation_started
data: {"id":"gen_abc123","status":"processing","progress":0}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":25,"stage":"analyzing_prompt"}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":50,"stage":"generating_frames"}

event: progress_update
data: {"id":"gen_abc123","status":"processing","progress":75,"stage":"encoding_video"}

event: generation_complete
data: {"id":"gen_abc123","status":"completed","result":{...}}

event: done
data: {}
```

## 认证

目前 API 不需要认证。在生产环境中，建议添加以下认证方式：

- API Key 认证
- OAuth 2.0
- JWT Token

## 请求格式

### 核心参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 使用的模型名称 |
| `prompt` | string | 是 | 视频生成的文本描述 |

### generation_config 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `duration_seconds` | int | 5 | 视频时长（秒）|
| `resolution` | string | "1080p" | 视频分辨率 |
| `aspect_ratio` | string | "16:9" | 宽高比 |
| `fps` | int | 24 | 帧率 |
| `style` | string | "cinematic" | 视频风格 |
| `temperature` | float | 1.0 | 生成随机性 (0.0-2.0) |
| `top_p` | float | 0.95 | 核采样参数 |
| `top_k` | int | 40 | Top-K 采样 |
| `seed` | int | 随机 | 随机种子 |
| `num_videos` | int | 1 | 生成视频数量 |

### output_config 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `format` | string | "mp4" | 输出格式 |
| `codec` | string | "h264" | 视频编码 |
| `quality` | string | "high" | 质量级别 |
| `include_audio` | bool | true | 是否包含音频 |

### safety_settings 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `category` | enum | 安全类别 |
| `threshold` | enum | 屏蔽阈值 |
| `method` | enum | 屏蔽方法 |

**安全类别:**
- `HARM_CATEGORY_HATE_SPEECH` - 仇恨言论
- `HARM_CATEGORY_DANGEROUS_CONTENT` - 危险内容
- `HARM_CATEGORY_HARASSMENT` - 骚扰
- `HARM_CATEGORY_SEXUALLY_EXPLICIT` - 露骨色情

**屏蔽阈值:**
- `BLOCK_NONE` - 不屏蔽
- `BLOCK_ONLY_HIGH` - 仅屏蔽高阈值
- `BLOCK_MEDIUM_AND_ABOVE` - 屏蔽中等及以上
- `BLOCK_LOW_AND_ABOVE` - 屏蔽低及以上

## 响应格式

### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 202 | 任务已接受（异步处理）|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 完成原因

| 值 | 说明 |
|-----|------|
| `FINISH_REASON_STOP` | 自然停止 |
| `FINISH_REASON_MAX_TOKENS` | 达到 token 限制 |
| `FINISH_REASON_SAFETY` | 安全过滤 |
| `FINISH_REASON_OTHER` | 其他原因 |

## 流式响应

流式响应使用 Server-Sent Events (SSE) 格式，实时推送生成进度。

### Python 示例

```python
import requests
import json

url = "http://localhost:5000/v1/videos/generations/stream"

payload = {
    "model": "video-model-v1",
    "prompt": "赛博朋克城市夜景",
    "generation_config": {
        "duration_seconds": 5
    }
}

response = requests.post(url, json=payload, stream=True)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('event:'):
            event = line.split(':', 1)[1].strip()
        elif line.startswith('data:'):
            data = json.loads(line.split(':', 1)[1].strip())
            print(f"事件: {event}, 数据: {data}")
```

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "message": "Missing required parameter: model",
    "type": "invalid_request_error"
  }
}
```

### 错误类型

| 类型 | 说明 |
|------|------|
| `invalid_request_error` | 请求参数错误 |
| `authentication_error` | 认证失败 |
| `rate_limit_error` | 速率限制 |
| `internal_error` | 服务器内部错误 |

## Python SDK 示例

### 异步生成

```python
import requests
import time

class VideoGenerator:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
    
    def create_generation(self, prompt, config=None):
        """创建生成任务"""
        url = f"{self.base_url}/v1/videos/generations"
        
        payload = {
            "model": "video-model-v1",
            "prompt": prompt,
            "generation_config": config or {}
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        return data['id']
    
    def wait_for_completion(self, generation_id, timeout=300):
        """等待生成完成"""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("生成超时")
            
            url = f"{self.base_url}/v1/videos/generations/{generation_id}"
            response = requests.get(url)
            data = response.json()
            
            if data['status'] == 'completed':
                return data['result']
            elif data['status'] == 'failed':
                raise Exception(data.get('error', '生成失败'))
            
            time.sleep(2)
    
    def generate(self, prompt, config=None):
        """同步生成视频"""
        gen_id = self.create_generation(prompt, config)
        return self.wait_for_completion(gen_id)

# 使用示例
generator = VideoGenerator()

result = generator.generate(
    "一位仙风道骨的剑仙在云端御剑飞行",
    config={
        "duration_seconds": 10,
        "resolution": "1080p",
        "fps": 24
    }
)

for video in result['videos']:
    print(f"视频 URL: {video['url']}")
```

### 流式生成

```python
def stream_generate(prompt, config=None):
    """流式生成视频"""
    url = f"{self.base_url}/v1/videos/generations/stream"
    
    payload = {
        "model": "video-model-v1",
        "prompt": prompt,
        "generation_config": config or {}
    }
    
    response = requests.post(url, json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data:'):
                data = json.loads(line.split(':', 1)[1].strip())
                yield data

# 使用示例
for event in stream_generate("赛博朋克城市"):
    if event.get('progress'):
        print(f"进度: {event['progress']}% - {event.get('stage', '')}")
    elif 'result' in event:
        print(f"完成! 视频URL: {event['result']['videos'][0]['url']}")
```

## 最佳实践

### 1. 参数调优

```python
# 高质量视频
config = {
    "resolution": "4k",
    "fps": 60,
    "quality": "high",
    "temperature": 0.7  # 降低随机性
}

# 快速生成
config = {
    "duration_seconds": 3,
    "resolution": "720p",
    "fps": 24,
    "quality": "medium"
}

# 创意风格
config = {
    "style": "anime",  # 或 "cinematic", "realistic", "artistic"
    "temperature": 1.2  # 提高创意性
}
```

### 2. 错误处理

```python
def generate_with_retry(prompt, max_retries=3):
    """带重试的生成"""
    for attempt in range(max_retries):
        try:
            result = generator.generate(prompt)
            return result
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            print(f"超时，重试 {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"生成失败: {e}")
            raise
```

### 3. 批量生成

```python
def batch_generate(prompts, max_concurrent=3):
    """批量生成"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(generator.generate, prompt): prompt 
            for prompt in prompts
        }
        
        for future in as_completed(futures):
            prompt = futures[future]
            try:
                result = future.result()
                results.append((prompt, result))
                print(f"✅ 完成: {prompt[:30]}...")
            except Exception as e:
                print(f"❌ 失败: {prompt[:30]}... - {e}")
    
    return results
```

### 4. 进度监控

```python
def generate_with_progress(prompt):
    """带进度监控的生成"""
    gen_id = generator.create_generation(prompt)
    
    while True:
        url = f"{generator.base_url}/v1/videos/generations/{gen_id}"
        response = requests.get(url)
        data = response.json()
        
        print(f"状态: {data['status']}")
        
        if data['status'] == 'completed':
            return data['result']
        elif data['status'] == 'failed':
            raise Exception(data.get('error'))
        
        time.sleep(2)
```

## 测试

运行测试脚本验证 API 功能：

```bash
python test_openai_video_api.py
```

测试内容包括：
- ✅ 创建生成任务
- ✅ 查询生成状态
- ✅ 列出生成任务
- ✅ 取消生成任务
- ✅ 流式生成
- ✅ 错误处理

## 故障排查

### 问题：服务器无响应

**解决方案：**
1. 检查服务器是否运行：`ps aux | grep wsgi.py`
2. 检查端口是否被占用：`netstat -an | grep 5000`
3. 查看服务器日志

### 问题：生成失败

**解决方案：**
1. 检查请求参数是否完整
2. 验证 `model` 参数是否正确
3. 查看错误消息详情

### 问题：流式响应中断

**解决方案：**
1. 检查网络连接稳定性
2. 增加超时时间
3. 使用异步生成代替流式生成

## 下一步

- 集成实际的视频生成引擎
- 添加用户认证
- 实现视频存储和 CDN
- 添加更多视频风格和特效
- 优化生成性能

## 支持

如有问题，请查看：
- [API 设计文档](VIDEO_GENERATION_OPENAI_API_DESIGN.md)
- [现有视频生成系统](VIDEO_GENERATION_SYSTEM_GUIDE.md)
- 测试脚本：`test_openai_video_api.py`