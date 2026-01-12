# 视频URL字段名不匹配问题修复

## 问题描述

从服务器日志可以看到，AI-WX API成功返回了视频数据：

```json
{
  'id': 'video_d5b740b4-ddc9-440e-983f-9f2859ee2d5e',
  'status': 'completed',
  'video_url': 'https://midjourney-plus.oss-us-west-1.aliyuncs.com/...',
  'size': '720x1280',
  'seconds': '10',
  'progress': 100
}
```

但前端没有显示视频。

## 根本原因

**API返回的字段名与代码期望的字段名不匹配**

### 实际API返回：
- 字段名：`video_url`
- 示例：`'video_url': 'https://midjourney-plus.oss-us-west-1.aliyuncs.com/...'`

### 原代码期望：
- 优先查找：`url` 字段
- 备用查找：`video_url` 字段

但查找顺序错误，导致无法正确提取视频URL。

## 修复方案

### 1. 后端修复

更新 [`src/managers/AiWxVideoManager.py`](src/managers/AiWxVideoManager.py:431) 的 [`_parse_api_result()`](src/managers/AiWxVideoManager.py:431) 方法：

**修复前：**
```python
# 优先查找 url 字段（错误）
video_url = api_data.get('url', '')

if not video_url:
    # 备用查找 video_url
    video_url = api_data.get('video_url', '')
```

**修复后：**
```python
# 优先查找 video_url 字段（AI-WX API实际返回的字段名）
video_url = api_data.get('video_url', '')

# 如果没有video_url，尝试其他可能的字段名
if not video_url:
    video_url = api_data.get('url', '')
    
self.logger.info(f"✅ 成功提取视频URL: {video_url}")
```

### 2. 前端修复

更新 [`web/static/js/video-studio.js`](web/static/js/video-studio.js:217) 的 [`showResult()`](web/static/js/video-studio.js:217) 方法：

**修复前：**
```javascript
if (result.video_url) {
    videoElement.src = result.video_url;
}
```

**修复后：**
```javascript
if (result.videos && result.videos.length > 0) {
    const video = result.videos[0];
    videoElement.src = video.url;
} else if (result.video_url) {
    // 兼容旧格式
    videoElement.src = result.video_url;
}
```

## 数据流程

### 完整的数据流向：

1. **AI-WX API** → 返回 `{'video_url': 'https://...'}`
2. **AiWxVideoManager._parse_api_result()** → 提取 `video_url` 字段
3. **GenerationResult** → 转换为 `VideoResult(url=video_url)`
4. **VideoGenerationResponse.to_dict()** → 序列化为 `{'result': {'videos': [{'url': ...}]}}`
5. **前端 JavaScript** → 访问 `result.videos[0].url`

### 关键转换点：

在 [`src/models/video_openai_models.py`](src/models/video_openai_models.py:271) 的 [`to_dict()`](src/models/video_openai_models.py:249) 方法中：

```python
if self.result:
    result["result"] = {
        "videos": [
            {
                "url": v.url,  # 这里将 video_url 转换为标准的 url
                ...
            }
            for v in self.result.videos
        ]
    }
```

## 测试验证

### 重启服务器

由于修改了后端代码，需要重启服务器：

```bash
# 停止当前服务器
Ctrl+C

# 重新启动
python web/wsgi.py
```

### 验证步骤

1. **刷新浏览器**（Ctrl+F5）
2. **生成新视频**
3. **查看日志** - 应该看到：
   ```
   🔍 解析API返回数据: {...}
   ✅ 成功提取视频URL: https://...
   ```
4. **前端显示** - 视频应该正常显示并自动播放

## 相关文件

### 后端
- [`src/managers/AiWxVideoManager.py`](src/managers/AiWxVideoManager.py:431) - API响应解析
- [`src/models/video_openai_models.py`](src/models/video_openai_models.py:249) - 数据序列化

### 前端
- [`web/static/js/video-studio.js`](web/static/js/video-studio.js:217) - 视频显示逻辑
- [`web/templates/video-studio.html`](web/templates/video-studio.html) - HTML结构
- [`web/static/css/video-studio.css`](web/static/css/video-studio.css) - 样式

### API
- [`web/api/openai_video_api.py`](web/api/openai_video_api.py) - API路由

## 经验教训

1. **字段名不一致**
   - 不同API提供商使用不同的字段名
   - 需要仔细阅读API文档
   - 应该优先使用API实际返回的字段名

2. **错误处理**
   - 添加详细的日志记录
   - 在关键步骤添加验证
   - 提供清晰的错误信息

3. **测试策略**
   - 先测试API返回的原始数据
   - 验证数据转换的每个环节
   - 使用真实数据进行端到端测试

## 后续优化

1. **配置化字段名**
   ```python
   VIDEO_URL_FIELDS = ['video_url', 'url', 'videoUrl']
   ```

2. **增强日志**
   ```python
   self.logger.info(f"📥 API响应: {json.dumps(api_data, indent=2)}")
   self.logger.info(f"🔍 尝试提取字段: {VIDEO_URL_FIELDS}")
   ```

3. **单元测试**
   ```python
   def test_parse_api_result():
       api_data = {'video_url': 'https://...'}
       result = manager._parse_api_result(api_data, task)
       assert result.videos[0].url == 'https://...'