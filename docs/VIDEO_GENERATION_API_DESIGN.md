# 视频生成系统 API 接口设计文档

> **基于分镜头脚本的逐步视频生成API**
> 
> 设计时间：2025-12-31
> 版本：v1.0

---

## 📋 目录

1. [API概述](#api概述)
2. [项目管理API](#项目管理api)
3. [任务管理API](#任务管理api)
4. [视频生成API](#视频生成api)
5. [WebSocket接口](#websocket接口)
6. [错误处理](#错误处理)
7. [认证授权](#认证授权)

---

## API概述

### 基础信息

- **Base URL**: `http://localhost:5000/api/video`
- **协议**: HTTP/HTTPS + WebSocket
- **数据格式**: JSON
- **认证方式**: Session-based (from existing auth system)

### 通用响应格式

```json
{
    "success": true/false,
    "data": {},
    "error": "错误信息",
    "code": "ERROR_CODE",
    "timestamp": "2025-12-31T12:00:00Z"
}
```

### 通用状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 项目管理API

### 1. 创建视频项目

创建一个新的视频项目，关联分镜头脚本。

**Endpoint**: `POST /api/video/projects`

**Request**:
```json
{
    "project_name": "我的动画项目",
    "novel_title": "仙侠传说",
    "video_type": "long_series",
    "storyboard": {
        "video_type": "long_series",
        "series_info": {...},
        "units": [...]
    },
    "config": {
        "aspect_ratio": "16:9",
        "video_quality": "HD",
        "enable_audio": true
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "project_name": "我的动画项目",
        "status": "created",
        "total_shots": 100,
        "created_at": "2025-12-31T12:00:00Z",
        "config": {...}
    }
}
```

### 2. 获取项目详情

获取指定项目的详细信息。

**Endpoint**: `GET /api/video/projects/{project_id}`

**Response**:
```json
{
    "success": true,
    "data": {
        "project_id": "...",
        "project_name": "我的动画项目",
        "status": "generating",
        "total_shots": 100,
        "completed_shots": 45,
        "failed_shots": 2,
        "created_at": "2025-12-31T12:00:00Z",
        "updated_at": "2025-12-31T13:00:00Z",
        "config": {...},
        "storyboard": {...},
        "current_task": {
            "task_id": "...",
            "status": "running",
            "progress": 0.45
        }
    }
}
```

### 3. 列出所有项目

获取用户的视频项目列表。

**Endpoint**: `GET /api/video/projects`

**Query Parameters**:
- `status`: (optional) 按状态筛选 (created/generating/completed/failed)
- `page`: (optional) 页码，默认1
- `limit`: (optional) 每页数量，默认20

**Response**:
```json
{
    "success": true,
    "data": {
        "projects": [
            {
                "project_id": "...",
                "project_name": "我的动画项目",
                "status": "generating",
                "total_shots": 100,
                "completed_shots": 45,
                "created_at": "2025-12-31T12:00:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 5,
            "total_pages": 1
        }
    }
}
```

### 4. 删除项目

删除指定的视频项目及其所有文件。

**Endpoint**: `DELETE /api/video/projects/{project_id}`

**Response**:
```json
{
    "success": true,
    "message": "项目已删除"
}
```

### 5. 导出项目

导出项目的最终视频或分镜头脚本。

**Endpoint**: `POST /api/video/projects/{project_id}/export`

**Request**:
```json
{
    "format": "video",
    "quality": "HD",
    "include_audio": true
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "export_url": "/static/videos/.../final_video.mp4",
        "download_url": "/api/video/projects/.../download",
        "file_size": 104857600,
        "duration": 300
    }
}
```

---

## 任务管理API

### 1. 创建生成任务

创建视频生成任务。

**Endpoint**: `POST /api/video/tasks`

**Request**:
```json
{
    "project_id": "...",
    "shot_indices": [0, 1, 2, 3, 4],
    "config": {
        "concurrent_limit": 3,
        "retry_limit": 3,
        "retry_delay": 60,
        "enable_audio": true
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "project_id": "...",
        "total_shots": 5,
        "status": "pending",
        "created_at": "2025-12-31T12:00:00Z",
        "config": {...}
    }
}
```

### 2. 启动任务

启动已创建的任务。

**Endpoint**: `POST /api/video/tasks/{task_id}/start`

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "status": "running",
        "started_at": "2025-12-31T12:00:00Z",
        "message": "任务已启动"
    }
}
```

### 3. 暂停任务

暂停正在运行的任务。

**Endpoint**: `POST /api/video/tasks/{task_id}/pause`

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "status": "paused",
        "message": "任务已暂停"
    }
}
```

### 4. 恢复任务

恢复已暂停的任务。

**Endpoint**: `POST /api/video/tasks/{task_id}/resume`

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "status": "running",
        "message": "任务已恢复"
    }
}
```

### 5. 取消任务

取消任务（正在运行或待处理）。

**Endpoint**: `POST /api/video/tasks/{task_id}/cancel`

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "status": "cancelled",
        "cancelled_at": "2025-12-31T12:00:00Z",
        "message": "任务已取消"
    }
}
```

### 6. 获取任务状态

获取任务的当前状态和进度。

**Endpoint**: `GET /api/video/tasks/{task_id}/status`

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "status": "running",
        "total_shots": 100,
        "completed_shots": 45,
        "failed_shots": 2,
        "current_shot_index": 46,
        "progress": {
            "overall": 0.45,
            "current_shot": 0.75
        },
        "timing": {
            "created_at": "2025-12-31T12:00:00Z",
            "started_at": "2025-12-31T12:01:00Z",
            "estimated_completion": "2025-12-31T12:15:00Z",
            "estimated_remaining_seconds": 600
        },
        "shots": [
            {
                "shot_index": 0,
                "status": "completed",
                "video_url": "/static/videos/.../shot_000.mp4"
            },
            {
                "shot_index": 45,
                "status": "processing",
                "progress": 0.75
            },
            {
                "shot_index": 50,
                "status": "failed",
                "error": "API限流"
            }
        ]
    }
}
```

### 7. 重试失败镜头

重新生成失败的镜头。

**Endpoint**: `POST /api/video/tasks/{task_id}/retry`

**Request**:
```json
{
    "shot_indices": [50, 55, 60]
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "retry_count": 3,
        "message": "已提交3个镜头重试"
    }
}
```

### 8. 获取任务历史

获取任务的事件历史。

**Endpoint**: `GET /api/video/tasks/{task_id}/history`

**Query Parameters**:
- `limit`: (optional) 返回数量，默认50

**Response**:
```json
{
    "success": true,
    "data": {
        "task_id": "...",
        "events": [
            {
                "timestamp": "2025-12-31T12:00:00Z",
                "event_type": "task_created",
                "message": "任务已创建"
            },
            {
                "timestamp": "2025-12-31T12:01:00Z",
                "event_type": "task_started",
                "message": "任务开始执行"
            },
            {
                "timestamp": "2025-12-31T12:02:00Z",
                "event_type": "shot_started",
                "shot_index": 0,
                "message": "开始生成镜头1"
            },
            {
                "timestamp": "2025-12-31T12:03:00Z",
                "event_type": "shot_completed",
                "shot_index": 0,
                "message": "镜头1生成完成",
                "video_path": "/static/videos/.../shot_000.mp4"
            }
        ]
    }
}
```

---

## 视频生成API

### 1. 生成分镜头脚本

从提示词生成视频分镜头脚本。

**Endpoint**: `POST /api/video/generate-storyboard`

**Request (小说模式)**:
```json
{
    "title": "仙侠传说",
    "video_type": "long_series"
}
```

**Request (自定义模式)**:
```json
{
    "prompt": "一个仙侠风格的视频场景...",
    "video_type": "short_film"
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "storyboard": {
            "video_type": "long_series",
            "video_type_name": "长篇剧集",
            "series_info": {
                "title": "仙侠传说",
                "total_units": 10
            },
            "visual_style_guide": {...},
            "pacing_guidelines": {...},
            "units": [...]
        },
        "shots": [
            {
                "shot_index": 0,
                "shot_number": 1,
                "shot_type": "全景",
                "camera_movement": "固定",
                "duration_seconds": 3,
                "description": "场景环境建立",
                "generation_prompt": "...",
                "audio_cue": "环境音",
                "status": "pending"
            }
        ],
        "total_shots": 100
    }
}
```

### 2. 生成单个镜头

立即生成单个镜头视频（同步）。

**Endpoint**: `POST /api/video/shots/generate`

**Request**:
```json
{
    "project_id": "...",
    "shot_index": 0,
    "prompt": "镜头生成提示词...",
    "duration": 5.0,
    "config": {
        "aspect_ratio": "16:9",
        "video_quality": "HD",
        "enable_audio": true
    }
}
```

**Response**:
```json
{
    "success": true,
    "data": {
        "shot_id": "...",
        "shot_index": 0,
        "status": "processing",
        "message": "镜头生成已提交"
    }
}
```

### 3. 获取镜头状态

获取单个镜头的生成状态。

**Endpoint**: `GET /api/video/shots/{shot_id}/status`

**Response**:
```json
{
    "success": true,
    "data": {
        "shot_id": "...",
        "shot_index": 0,
        "status": "completed",
        "progress": 1.0,
        "video_url": "/static/videos/.../shot_000.mp4",
        "thumbnail_url": "/static/videos/.../shot_000_thumb.jpg",
        "duration": 5.2,
        "created_at": "2025-12-31T12:00:00Z",
        "completed_at": "2025-12-31T12:01:00Z"
    }
}
```

### 4. 下载镜头视频

下载生成的镜头视频。

**Endpoint**: `GET /api/video/shots/{shot_id}/download`

**Response**: 视频文件流

---

## WebSocket接口

### 连接端点

```
ws://localhost:5000/ws/video/{task_id}
```

### 消息格式

#### 1. 进度更新

服务器 → 客户端

```json
{
    "type": "progress",
    "data": {
        "task_id": "...",
        "total_shots": 100,
        "completed_shots": 45,
        "failed_shots": 2,
        "current_shot_index": 46,
        "current_shot_progress": 0.75,
        "overall_progress": 0.45,
        "estimated_remaining_seconds": 600,
        "status_message": "正在生成镜头46...",
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 2. 镜头开始

服务器 → 客户端

```json
{
    "type": "shot_started",
    "data": {
        "task_id": "...",
        "shot_index": 46,
        "shot_description": "主角在云端修行",
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 3. 镜头完成

服务器 → 客户端

```json
{
    "type": "shot_completed",
    "data": {
        "task_id": "...",
        "shot_index": 46,
        "video_url": "/static/videos/.../shot_046.mp4",
        "thumbnail_url": "/static/videos/.../shot_046_thumb.jpg",
        "duration": 5.2,
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 4. 镜头失败

服务器 → 客户端

```json
{
    "type": "shot_failed",
    "data": {
        "task_id": "...",
        "shot_index": 50,
        "error": "API限流",
        "retry_count": 1,
        "can_retry": true,
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 5. 任务完成

服务器 → 客户端

```json
{
    "type": "task_completed",
    "data": {
        "task_id": "...",
        "total_shots": 100,
        "completed_shots": 100,
        "failed_shots": 0,
        "output_video": "/static/videos/.../final.mp4",
        "duration": 300,
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 6. 任务失败

服务器 → 客户端

```json
{
    "type": "task_failed",
    "data": {
        "task_id": "...",
        "error": "失败镜头过多",
        "failed_shots": [50, 55, 60],
        "timestamp": "2025-12-31T12:00:00Z"
    }
}
```

#### 7. 客户端控制

客户端 → 服务器

```json
{
    "action": "pause",
    "task_id": "..."
}
```

支持的操作：
- `pause`: 暂停任务
- `resume`: 恢复任务
- `cancel`: 取消任务

---

## 错误处理

### 错误码定义

| 错误码 | 说明 |
|--------|------|
| `INVALID_PARAMS` | 请求参数无效 |
| `PROJECT_NOT_FOUND` | 项目不存在 |
| `TASK_NOT_FOUND` | 任务不存在 |
| `SHOT_NOT_FOUND` | 镜头不存在 |
| `VEO3_API_ERROR` | Veo3 API调用失败 |
| `VEO3_RATE_LIMIT` | Veo3 API限流 |
| `VEO3_TIMEOUT` | Veo3 API超时 |
| `STORAGE_ERROR` | 文件存储失败 |
| `TASK_CANCELLED` | 任务已取消 |
| `TASK_TIMEOUT` | 任务超时 |
| `QUOTA_EXCEEDED` | 配额超限 |

### 错误响应示例

```json
{
    "success": false,
    "error": "Veo3 API限流",
    "code": "VEO3_RATE_LIMIT",
    "details": {
        "retry_after": 60,
        "suggestion": "请60秒后重试"
    },
    "timestamp": "2025-12-31T12:00:00Z"
}
```

---

## 认证授权

### 认证方式

使用现有的Session-based认证系统：

```python
from web.auth import login_required

@video_api.route('/projects', methods=['POST'])
@login_required
def create_project():
    # 处理请求
    pass
```

### 权限控制

- 用户只能访问自己创建的项目
- 项目资源路径包含用户ID作为隔离
- WebSocket连接验证用户权限

---

## API使用示例

### 完整工作流示例

```javascript
// 1. 创建项目
const projectResponse = await fetch('/api/video/projects', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        project_name: '我的动画',
        video_type: 'long_series',
        storyboard: {...}
    })
});
const project = await projectResponse.json();

// 2. 创建任务
const taskResponse = await fetch('/api/video/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        project_id: project.data.project_id,
        config: {concurrent_limit: 3}
    })
});
const task = await taskResponse.json();

// 3. 启动任务
await fetch(`/api/video/tasks/${task.data.task_id}/start`, {
    method: 'POST'
});

// 4. 建立WebSocket连接
const ws = new WebSocket(`ws://localhost:5000/ws/video/${task.data.task_id}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message.type, message.data);
};

// 5. 监听完成
ws.addEventListener('task_completed', (data) => {
    console.log('任务完成!', data);
    // 下载视频
    window.open(data.output_video);
});
```

---

**文档版本**：v1.0  
**最后更新**：2025-12-31  
**维护者**：Kilo Code