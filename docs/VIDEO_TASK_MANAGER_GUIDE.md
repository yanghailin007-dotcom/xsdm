# 视频任务管理系统使用指南

## 概述

视频任务管理系统是基于Google Veo3的企业级视频生成系统的任务管理模块，提供完整的任务生命周期管理功能。

## 核心功能

### 1. 任务创建与管理
- ✅ 创建视频生成任务
- ✅ 支持单个镜头生成
- ✅ 支持批量镜头生成
- ✅ 任务优先级管理
- ✅ 自定义并发数

### 2. 任务控制
- ✅ 启动任务
- ✅ 暂停任务
- ✅ 恢复任务
- ✅ 取消任务
- ✅ 重试失败的镜头

### 3. 实时进度跟踪
- ✅ 实时显示任务进度
- ✅ 镜头状态更新
- ✅ WebSocket推送（可选）
- ✅ 进度条可视化

### 4. 文件管理
- ✅ 支持首尾帧上传
- ✅ 生成的视频存储
- ✅ 任务历史记录

## 快速开始

### 1. 初始化系统

运行初始化脚本：

```bash
python scripts/init_video_task_system.py
```

这将创建所有必要的目录结构并验证依赖。

### 2. 注册API路由

在 `web/__init__.py` 或主服务器文件中添加：

```python
from web.api.video_task_api import register_video_task_routes

# 注册路由
register_video_task_routes(app)
```

### 3. 添加页面路由

在web服务器中添加路由：

```python
@app.route('/video-task-manager')
@login_required
def video_task_manager_page():
    return render_template('video-task-manager.html')
```

### 4. 安装可选依赖

为了支持WebSocket实时推送功能，建议安装：

```bash
pip install flask-socketio
```

## 使用流程

### 创建任务

1. **配置任务类型**
   - 单个镜头：生成单个视频片段
   - 批量生成：一次添加多个镜头
   - 项目导入：从现有项目导入

2. **输入提示词**
   - 在文本框中输入视频生成提示词
   - 或使用快速模板（科幻、自然、都市、奇幻）

3. **设置参数**
   - 视频类型：短片/长剧集/短视频
   - 景别：大远景到特写
   - 运镜：固定、推近、拉远等
   - 时长：1-60秒
   - 并发数：1-10

4. **上传首尾帧（可选）**
   - 可上传参考图片作为首帧和尾帧

5. **添加镜头**
   - 点击"添加镜头"按钮将配置添加到任务
   - 可重复添加多个镜头

6. **创建任务**
   - 点击"创建任务"按钮生成任务
   - 系统会分配任务ID

### 管理任务

1. **启动任务**
   - 点击"启动"按钮开始生成
   - Worker会自动处理镜头队列
   - 实时显示进度

2. **暂停/恢复**
   - 点击"暂停"可暂时停止生成
   - 点击"继续"恢复执行

3. **取消任务**
   - 点击"取消"终止任务
   - 已完成的镜头会保留

4. **重试失败**
   - 如果有镜头失败，可重试
   - 最多自动重试3次

### 查看结果

1. **实时进度**
   - 进度条显示总体完成度
   - 每个镜头状态实时更新
   - 状态：待处理、生成中、已完成、失败

2. **生成结果**
   - 任务完成后显示在结果区域
   - 可预览视频
   - 可下载单个视频

3. **任务历史**
   - 右侧显示历史任务列表
   - 可点击查看详情
   - 显示任务状态和进度

## API接口

### 创建任务

```http
POST /api/video/tasks
Content-Type: application/json

{
  "project_id": "project_123",
  "shots": [
    {
      "shot_index": 0,
      "shot_type": "中景",
      "camera_movement": "固定",
      "duration_seconds": 10.0,
      "description": "场景描述",
      "generation_prompt": "完整提示词",
      "audio_prompt": "音频提示词"
    }
  ],
  "config": {
    "max_concurrent": 3,
    "auto_start": false
  }
}
```

### 启动任务

```http
POST /api/video/tasks/{task_id}/start
```

### 暂停任务

```http
POST /api/video/tasks/{task_id}/pause
```

### 恢复任务

```http
POST /api/video/tasks/{task_id}/resume
```

### 取消任务

```http
POST /api/video/tasks/{task_id}/cancel
```

### 获取任务状态

```http
GET /api/video/tasks/{task_id}/status
```

### 列出所有任务

```http
GET /api/video/tasks
```

### 重试失败的镜头

```http
POST /api/video/tasks/{task_id}/retry
```

## WebSocket事件

### 连接

```javascript
const socket = io();
socket.emit('subscribe_task', { task_id: 'task_123' });
```

### 进度更新

```javascript
socket.on('progress_update', (data) => {
  console.log('任务ID:', data.task_id);
  console.log('事件:', data.event);
  console.log('数据:', data.data);
});
```

### 事件类型

- `task_created` - 任务创建
- `task_started` - 任务开始
- `task_paused` - 任务暂停
- `task_resumed` - 任务恢复
- `task_completed` - 任务完成
- `task_cancelled` - 任务取消
- `shot_started` - 镜头开始
- `shot_progress` - 镜头进度
- `shot_completed` - 镜头完成
- `shot_failed` - 镜头失败

## 配置说明

### 任务配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_concurrent` | int | 3 | 最大并发Worker数 |
| `auto_start` | bool | false | 创建后自动启动 |
| `retry_limit` | int | 3 | 失败重试次数 |
| `task_timeout` | int | 3600 | 任务超时时间（秒） |

### 镜头配置参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `shot_index` | int | 镜头索引 |
| `shot_type` | str | 景别（大远景/全景/中景/近景/特写/大特写） |
| `camera_movement` | str | 运镜（固定/推近/拉远/平移/跟随/环绕） |
| `duration_seconds` | float | 时长（秒） |
| `generation_prompt` | str | 生成提示词 |
| `audio_prompt` | str | 音频提示词（可选） |

## 文件结构

```
src/
├── models/
│   └── video_task_models.py      # 数据模型
├── schedulers/
│   └── video_task_scheduler.py    # 任务调度器
├── workers/
│   └── video_worker.py            # Worker实现
└── websocket/
    └── video_progress_ws.py         # WebSocket服务

web/
├── api/
│   └── video_task_api.py           # API接口
├── templates/
│   └── video-task-manager.html      # 任务管理页面
├── static/
│   ├── css/
│   │   └── video-task-manager.css   # 样式文件
│   └── js/
│       └── video-task-manager.js    # 前端脚本

视频项目/                           # 视频存储目录
```

## 故障排除

### 问题1: 任务创建失败

**症状**: 点击创建任务后没有响应

**解决方案**:
1. 检查浏览器控制台错误
2. 确认API路由已正确注册
3. 验证网络连接

### 问题2: 进度不更新

**症状**: 进度条始终为0%

**解决方案**:
1. 检查Worker是否正常启动
2. 查看服务器日志
3. 确认任务状态正确更新

### 问题3: WebSocket连接失败

**症状**: 无法接收实时更新

**解决方案**:
1. 安装flask-socketio: `pip install flask-socketio`
2. 检查服务器是否启动了WebSocket支持
3. 确认防火墙设置

### 问题4: 文件保存失败

**症状**: 生成的视频无法保存

**解决方案**:
1. 检查`视频项目/`目录权限
2. 确保磁盘空间充足
3. 查看服务器日志中的错误信息

## 性能优化建议

1. **调整并发数**
   - 根据服务器性能调整`max_concurrent`
   - 建议: 3-5个并发Worker

2. **优化轮询间隔**
   - 默认2秒轮询一次进度
   - 可根据需要调整

3. **启用WebSocket**
   - 使用WebSocket替代轮询
   - 减少服务器负载

4. **清理旧任务**
   - 定期清理已完成的历史任务
   - 避免存储空间不足

## 扩展开发

### 添加新的视频生成服务

1. 创建新的Worker类继承`VideoWorker`
2. 实现`_generate_video`方法
3. 在调度器中注册新Worker

### 自定义进度计算

1. 修改`VideoTask.get_progress()`
2. 添加自定义进度逻辑
3. 通过WebSocket推送更新

### 集成其他存储后端

1. 修改`VideoTaskScheduler._save_task()`
2. 实现S3/OSS存储适配器
3. 更新文件路径生成逻辑

## 最佳实践

1. **任务分批处理**
   - 大型项目建议分批创建任务
   - 每批不超过100个镜头

2. **错误处理**
   - 设置合理的重试次数
   - 记录详细的错误日志
   - 提供用户友好的错误提示

3. **资源管理**
   - 定期清理临时文件
   - 监控磁盘使用情况
   - 设置任务超时保护

4. **用户体验**
   - 提供清晰的进度反馈
   - 支持任务暂停/恢复
   - 允许用户重试失败的操作

## 更新日志

### v1.0.0 (2025-12-31)

- ✅ 初始版本发布
- ✅ 实现核心任务管理功能
- ✅ 支持任务创建、启动、暂停、恢复、取消
- ✅ 实现实时进度跟踪
- ✅ 创建Web管理界面
- ✅ 集成WebSocket支持（可选）

## 联系支持

如有问题或建议，请通过以下方式联系：

- 创建Issue
- 查看项目文档
- 提交Pull Request

---

**文档版本**: v1.0  
**最后更新**: 2025-12-31  
**维护者**: Kilo Code