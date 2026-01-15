# VeO视频404错误诊断报告

## 问题描述

从日志中发现大量404错误：
```
GET /static/generated_videos/veo_f8626bae6e04.mp4 HTTP/1.1" 404
GET /static/generated_videos/veo_da1285381190.mp4 HTTP/1.1" 404
GET /generated_videos/veo_265084b612ad.mp4 HTTP/1.1" 404
```

## 根本原因

### 1. **VeO视频使用AI-WX API的远程URL**
- 从 [`src/managers/VeOVideoManager.py:496-502`](src/managers/VeOVideoManager.py:496-502) 可以看到：
```python
video = VeOVideoResult(
    id=f"video_{uuid.uuid4().hex[:8]}",
    url=video_url,  # 这是AI-WX返回的远程URL，如 https://xxx.com/veo_xxx.mp4
    duration_seconds=float(10),
    ...
)
```

### 2. **前端错误地尝试从本地static路径访问**
- 前端尝试访问：`/static/generated_videos/veo_xxx.mp4`
- 但实际视频存储在：AI-WX的远程服务器（如 `https://aiwx.com/videos/veo_xxx.mp4`）

### 3. **数据存储位置**
- 任务数据存储在：`veo_video_generations/*.json` 文件
- 每个任务包含 `result.videos[0].url` 字段，存储远程URL
- **不是本地文件路径**

### 4. **路径使用规范**
✅ **正确做法**：
- VeO视频：使用完整URL（`https://aiwx.com/videos/veo_xxx.mp4`）
- 本地生成视频：使用相对路径（`/static/generated_videos/xxx.mp4`）

❌ **错误做法**：
- 将远程URL当作本地路径处理
- 前端硬编码 `/static/generated_videos/` 前缀

## 数据流向

```
AI-WX API → VeOVideoManager → veo_video_generations/*.json
              ↓
         存储远程URL (https://...)
              ↓
         API返回给前端
              ↓
         前端应直接使用URL
              ↓
    ❌ 但前端错误地添加了 /static/ 前缀
```

## 修复方案

### 方案1：前端修复（推荐）
检查前端代码，确保直接使用API返回的`result.videos[0].url`，而不是拼接本地路径。

### 方案2：API响应规范化
确保API响应明确区分：
- `video_url`: 远程URL（VeO视频）
- `local_path`: 本地路径（本地生成视频）

### 方案3：添加代理端点（可选）
如果需要跨域访问，可以添加：
```python
@app.route('/api/veo/video/<task_id>')
def serve_veo_video(task_id):
    """代理访问VeO视频"""
    task = manager.retrieve_generation(task_id)
    if task and task.result and task.result.videos:
        video_url = task.result.videos[0].url
        return redirect(video_url)
```

## 需要检查的代码位置

1. **前端视频显示逻辑**：
   - 搜索 `/static/generated_videos/` 的硬编码
   - 检查视频播放器的URL构造逻辑

2. **API响应格式**：
   - 确认 `/api/veo/tasks` 返回的格式
   - 确保视频URL字段正确传递

3. **任务列表显示**：
   - 检查任务历史记录中视频缩略图的加载逻辑

## 临时解决方案

如果前端无法立即修改，可以添加静态文件代理：

```python
# 在 web_server_refactored.py 中添加
@app.route('/static/generated_videos/<path:filename>')
def proxy_generated_video(filename):
    """代理访问生成的视频"""
    task_id = filename.replace('.mp4', '').replace('veo_', '')
    
    # 从VeO管理器获取任务
    manager = get_veo_video_manager()
    task = manager.retrieve_generation(f"veo_{task_id}")
    
    if task and task.result and task.result.videos:
        video_url = task.result.videos[0].url
        # 重定向到真实的视频URL
        return redirect(video_url)
    
    # 如果不是VeO任务，尝试本地文件
    return send_from_directory('generated_videos', filename)
```

## 预防措施

1. **统一路径管理**
   - 创建路径配置文件
   - 明确区分本地路径和远程URL

2. **添加类型标识**
   - 在任务数据中添加 `source_type` 字段
   - `local` 或 `remote`

3. **改进错误提示**
   - 当视频加载失败时，显示更清晰的错误信息
   - 包括正确的URL来源

## 相关文件

- `src/managers/VeOVideoManager.py` - VeO视频管理器
- `src/models/veo_models.py` - 数据模型定义
- `web/api/veo_video_api.py` - API路由
- `static/js/video-task-manager.js` - 前端任务管理
- `static/js/video-generation.js` - 前端视频生成

## 总结

这个404错误**不是因为视频文件被删除**，而是因为：
1. VeO视频存储在AI-WX的远程服务器
2. 前端错误地尝试从本地static路径访问
3. 应该直接使用API返回的完整URL

**素材库确实应该使用相对路径或URL**，具体取决于：
- 本地生成的视频：使用相对路径（如 `/static/...`）
- VeO远程视频：使用完整URL（如 `https://...`）
