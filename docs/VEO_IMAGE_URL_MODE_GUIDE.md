# VeO 视频生成 - 图片输入模式指南

## 概述

AI-WX VeO API 现在支持两种图片输入模式，解决了 "message too large" 错误问题。

## 两种输入模式

### 1. 图片 URL 模式（推荐）✅

**优点：**
- ✅ 不会出现 "message too large" 错误
- ✅ 传输速度快，无需 base64 编码
- ✅ 支持任意大小的图片
- ✅ API 直接从 URL 下载图片

**使用方法：**

```json
{
  "model": "veo_3_1-fast",
  "prompt": "一个美丽的日出场景",
  "image_urls": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ],
  "orientation": "portrait",
  "size": "large"
}
```

**示例：**

```python
import requests

url = "http://localhost:5000/api/veo/generate"
payload = {
    "prompt": "一个美丽的日出场景",
    "image_urls": [
        "https://your-cdn.com/image1.jpg",
        "https://your-cdn.com/image2.jpg"
    ],
    "orientation": "portrait",
    "size": "large"
}

response = requests.post(url, json=payload)
print(response.json())
```

### 2. Base64 图片模式（备用）

**适用场景：**
- 无法提供图片 URL
- 图片存储在本地

**特点：**
- ⚠️ 会自动压缩图片（最大 2 MB）
- ⚠️ 会调整分辨率（最大 1920x1920）
- ⚠️ 适合小图片（< 1 MB）

**使用方法：**

```json
{
  "model": "veo_3_1-fast",
  "prompt": "一个美丽的日出场景",
  "images": [
    "base64_encoded_image_data_1",
    "base64_encoded_image_data_2"
  ],
  "orientation": "portrait",
  "size": "large"
}
```

## API 参数说明

### 新增参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `image_urls` | `array[string]` | 否 | 图片 URL 列表（推荐使用） |
| `images` | `array[string]` | 否 | Base64 编码的图片数据（会自动压缩） |

### 优先级

1. **优先使用 `image_urls`**（如果提供）
2. 否则使用 `images`（base64 模式）

## 最佳实践

### 推荐做法 ✅

1. **使用图片 URL**
   - 将图片上传到 CDN 或对象存储（如阿里云 OSS、腾讯云 COS）
   - 使用公开可访问的 URL
   - 确保 URL 稳定可靠

2. **图片格式**
   - 使用 JPEG 格式（比 PNG 更小）
   - 分辨率：720p-1080p 即可
   - 文件大小：< 2 MB（URL 模式无此限制）

3. **URL 要求**
   - 使用 HTTPS（更安全）
   - 确保 URL 可公开访问
   - 避免使用需要认证的 URL

### 不推荐做法 ❌

1. ❌ 传输大图片的 base64（> 2 MB）
2. ❌ 使用 4K 或更高分辨率
3. ❌ 使用未压缩的 PNG 格式
4. ❌ 使用需要认证的 URL

## 错误处理

### "message too large" 错误

**原因：**
- 使用 base64 模式上传大图片

**解决方案：**
1. **方案一（推荐）**：改用图片 URL 模式
   ```python
   # 不推荐
   payload = {
       "images": [large_base64_string]
   }
   
   # 推荐
   payload = {
       "image_urls": ["https://cdn.example.com/image.jpg"]
   }
   ```

2. **方案二**：手动压缩图片
   - 降低分辨率到 1080p
   - 使用 JPEG 格式
   - 降低质量到 85%

## 示例代码

### Python 示例（URL 模式）

```python
import requests

# 使用图片 URL
url = "http://localhost:5000/api/veo/generate"

payload = {
    "prompt": "一个美丽的日出，云彩绚丽，阳光从地平线升起",
    "image_urls": [
        "https://your-cdn.com/sunrise_start.jpg",
        "https://your-cdn.com/sunrise_end.jpg"
    ],
    "orientation": "landscape",
    "size": "large"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"任务ID: {result['id']}")
print(f"状态: {result['status']}")

# 查询任务状态
status_url = f"http://localhost:5000/api/veo/status/{result['id']}"
status_response = requests.get(status_url)
print(status_response.json())
```

### Python 示例（Base64 模式）

```python
import requests
import base64

# 将本地图片转换为 base64
def image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

url = "http://localhost:5000/api/veo/generate"

payload = {
    "prompt": "一个美丽的日出",
    "images": [
        image_to_base64("image1.jpg"),
        image_to_base64("image2.jpg")
    ],
    "orientation": "portrait",
    "size": "large"
}

# 系统会自动压缩图片
response = requests.post(url, json=payload)
print(response.json())
```

### JavaScript 示例（URL 模式）

```javascript
async function generateVideo() {
    const response = await fetch('http://localhost:5000/api/veo/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: '一个美丽的日出',
            image_urls: [
                'https://your-cdn.com/image1.jpg',
                'https://your-cdn.com/image2.jpg'
            ],
            orientation: 'portrait',
            size: 'large'
        })
    });
    
    const result = await response.json();
    console.log('任务ID:', result.id);
    console.log('状态:', result.status);
    
    return result;
}
```

## API 响应示例

### 成功响应

```json
{
  "id": "veo_abc123def456",
  "object": "video.generation",
  "created": 1705166400,
  "model": "veo_3_1-fast",
  "status": "pending",
  "prompt": "一个美丽的日出",
  "generation_config": {
    "model": "veo_3_1-fast",
    "orientation": "portrait",
    "size": "large",
    "duration": 10,
    "aspect_ratio": "9:16",
    "enable_upsample": false
  }
}
```

### 完成响应

```json
{
  "id": "veo_abc123def456",
  "status": "completed",
  "result": {
    "videos": [
      {
        "id": "video_xyz789",
        "url": "https://cdn.example.com/video.mp4",
        "duration_seconds": 10,
        "resolution": "1080x1920"
      }
    ]
  }
}
```

## 相关文档

- [`docs/VEO_IMAGE_SIZE_LIMIT_FIX.md`](VEO_IMAGE_SIZE_LIMIT_FIX.md) - 图片压缩功能详解
- [`docs/VEO_VIDEO_GENERATION_GUIDE.md`](VEO_VIDEO_GENERATION_GUIDE.md) - VeO 视频生成完整指南
- [`src/models/veo_models.py`](../src/models/veo_models.py) - 数据模型定义
- [`web/api/veo_video_api.py`](../web/api/veo_video_api.py) - API 端点实现

## 更新日志

- **2026-01-13**: 新增图片 URL 模式支持，解决 "message too large" 问题
- **2026-01-13**: 添加自动图片压缩功能（base64 模式）