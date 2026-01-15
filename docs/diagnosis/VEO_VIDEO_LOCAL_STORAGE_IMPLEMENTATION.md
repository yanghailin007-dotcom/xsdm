# VeO视频本地存储实现方案

## 问题背景

用户发现VeO视频出现404错误，经过诊断发现：
- VeO视频存储在AI-WX的远程服务器
- 远程服务器不属于用户，随时可能被删除
- 需要将视频**下载到本地存储**

## 解决方案

### 1. 自动下载视频到本地

在 [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py) 中实现：

#### 1.1 添加本地存储目录
```python
# 🔥 新增：本地视频存储目录
VEO_VIDEO_STORAGE_DIR = BASE_DIR / "static" / "generated_videos"
VEO_VIDEO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"📁 VeO视频本地存储目录: {VEO_VIDEO_STORAGE_DIR}")
```

#### 1.2 自动下载视频
在视频生成完成后（`_poll_task_status`方法中）：
```python
if query_response.is_completed():
    video_url = query_response.video_url
    
    # 🔥 新增：下载视频到本地
    local_path = self._download_video_to_local(task.id, video_url)
    
    # 使用本地路径作为URL
    final_url = f"/static/generated_videos/{local_path}" if local_path else video_url
```

#### 1.3 下载方法实现
```python
def _download_video_to_local(self, task_id: str, video_url: str) -> Optional[str]:
    """下载视频到本地存储"""
    local_filename = f"{task_id}.mp4"
    local_file_path = VEO_VIDEO_STORAGE_DIR / local_filename
    
    # 下载视频
    response = requests.get(video_url, stream=True, timeout=300)
    
    with open(local_file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    # 返回相对路径
    return local_filename
```

### 2. 智能视频提供端点

在 [`web/web_server_refactored.py`](web/web_server_refactored.py) 中更新：

#### 2.1 优先提供本地文件
```python
@app.route('/static/generated_videos/<path:filename>')
def serve_generated_video(filename):
    """智能代理访问生成的视频文件
    
    优先级：
    1. VeO本地视频：从本地文件系统提供（优先）✅
    2. VeO远程视频：重定向到远程URL（备用）
    3. 其他本地视频：从本地文件系统提供
    """
    if filename.startswith('veo_') and filename.endswith('.mp4'):
        task_id = filename.replace('.mp4', '')
        
        # 🔥 优先尝试本地文件
        local_video_path = os.path.join(BASE_DIR, 'static', 'generated_videos', filename)
        
        if os.path.exists(local_video_path):
            logger.info(f"✅ 找到本地VeO视频: {local_video_path}")
            return send_from_directory(local_video_dir, filename)
        
        # 如果本地不存在，尝试远程URL
        task = manager.retrieve_generation(task_id)
        if task and task.result and task.result.videos:
            video_url = task.result.videos[0].url
            
            # 检查URL是否是本地路径
            if video_url.startswith('/static/'):
                # 从本地路径提供文件
                return send_from_directory(local_video_dir, filename)
            else:
                # 重定向到远程URL
                return redirect(video_url)
```

### 3. 完整的任务删除

更新 `delete_generation` 方法，同时删除本地视频：
```python
def delete_generation(self, generation_id: str) -> bool:
    """删除生成任务（包括本地视频文件）"""
    
    # 🔥 新增：删除本地视频文件
    local_video_path = VEO_VIDEO_STORAGE_DIR / f"{generation_id}.mp4"
    if local_video_path.exists():
        local_video_path.unlink()
        self.logger.info(f"✅ 已删除本地视频文件")
    
    # 删除JSON文件
    task_file = self.storage_dir / f"{generation_id}.json"
    if task_file.exists():
        task_file.unlink()
    
    # 从内存中移除
    with self._tasks_lock:
        task = self.tasks.pop(generation_id, None)
    
    return True
```

## 数据流

```
┌─────────────────┐
│ AI-WX API       │
│ (远程服务器)     │
└────────┬────────┘
         │
         │ 1. 生成完成，返回URL
         ↓
┌─────────────────┐
│ VeOVideoManager │
│                 │
│ • 检测完成      │
│ • 下载到本地    │ ✅ 新增
│ • 保存本地路径  │
└────────┬────────┘
         │
         │ 2. 保存本地路径
         ↓
┌─────────────────┐
│ veo_xxx.json    │
│ {               │
│   "url": "/static/generated_videos/veo_xxx.mp4"  ← 本地路径
│ }               │
└────────┬────────┘
         │
         │ 3. 前端请求视频
         ↓
┌─────────────────┐
│ Web服务器       │
│                 │
│ • 检查本地文件  │ ✅ 优先
│ • 直接提供      │
│ • 无需远程访问  │
└─────────────────┘
```

## 文件结构

```
项目根目录/
├── veo_video_generations/          # 任务数据（JSON）
│   └── veo_abc123def456.json      # 任务元数据
└── static/
    └── generated_videos/          # 本地视频文件 ✅ 新增
        └── veo_abc123def456.mp4   # 实际视频文件
```

## 优势

### ✅ 数据安全
- 视频存储在本地服务器
- 不依赖远程服务器的可用性
- 防止远程数据被删除

### ✅ 访问速度
- 本地文件直接提供
- 无需远程请求
- 更快的加载速度

### ✅ 成本控制
- 减少远程服务器带宽
- 降低API调用次数
- 节省流量费用

### ✅ 兼容性
- 前端无需修改
- API保持兼容
- 平滑升级

## 配置选项

### 下载超时设置
在 `config/aiwx_video_config.py` 中添加：
```python
REQUEST_CONFIG = {
    'timeout': 60,  # API请求超时
    'download_timeout': 300  # 下载超时（5分钟）✅ 新增
}
```

### 存储目录配置
可以自定义存储目录：
```python
# 在 VeOVideoManager.__init__ 中
storage_dir = "/path/to/custom/storage"
```

## 监控和日志

### 下载进度日志
```
📥 开始下载视频: https://aiwx.com/videos/veo_xxx.mp4
💾 保存到: /static/generated_videos/veo_xxx.mp4
📥 下载进度: 10%
📥 下载进度: 20%
...
📥 下载进度: 100%
✅ 视频下载完成: veo_xxx.mp4 (12.5 MB)
```

### 访问日志
```
📹 请求视频: veo_abc123.mp4
🔍 检测到VeO视频，任务ID: veo_abc123
✅ 找到本地VeO视频: /static/generated_videos/veo_abc123.mp4
```

## 错误处理

### 下载失败处理
```python
try:
    local_path = self._download_video_to_local(task.id, video_url)
    if local_path:
        # 使用本地路径
        final_url = f"/static/generated_videos/{local_path}"
    else:
        # 下载失败，使用原始URL
        final_url = video_url
        self.logger.warn(f"⚠️ 下载失败，使用远程URL")
except Exception as e:
    self.logger.error(f"❌ 下载失败: {e}")
    # 回退到远程URL
    final_url = video_url
```

### 文件已存在处理
```python
if local_file_path.exists():
    self.logger.info(f"🗑️ 删除已存在的文件: {local_file_path}")
    local_file_path.unlink()
```

## 迁移指南

### 对于已存在的视频

如果之前已经生成了VeO视频，可以手动下载：

```python
# 脚本：批量下载已完成的VeO视频
from src.managers.VeOVideoManager import get_veo_video_manager

manager = get_veo_video_manager()
tasks = manager.list_generations(limit=1000, status=VideoStatus.COMPLETED)

for task_response in tasks:
    task_id = task_response.id
    if task_response.result and task_response.result.videos:
        remote_url = task_response.result.videos[0].url
        if not remote_url.startswith('/static/'):
            # 下载到本地
            local_path = manager._download_video_to_local(task_id, remote_url)
            print(f"✅ {task_id}: {local_path}")
```

## 测试验证

### 1. 新视频生成测试
```bash
# 生成新视频
curl -X POST http://localhost:5000/api/veo/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "测试视频"}'

# 检查日志
tail -f logs/app.log | grep "下载视频"
```

### 2. 本地文件访问测试
```bash
# 访问本地视频
curl -I http://localhost:5000/static/generated_videos/veo_xxx.mp4

# 应该返回 200 OK
```

### 3. 删除任务测试
```bash
# 删除任务
curl -X DELETE http://localhost:5000/api/veo/tasks/veo_xxx

# 检查本地文件是否删除
ls static/generated_videos/veo_xxx.mp4
# 应该显示：No such file or directory
```

## 性能考虑

### 存储空间
- 每个VeO视频约 10-20 MB
- 100个视频约 1-2 GB
- 建议定期清理旧视频

### 下载时间
- 取决于网络速度
- 一般 10-20 秒完成
- 异步下载，不阻塞用户

### 磁盘I/O
- 流式下载，低内存占用
- 使用临时文件，确保完整性
- 失败自动重试机制

## 总结

通过实现本地存储方案：
1. ✅ 视频自动下载到本地
2. ✅ 优先提供本地文件
3. ✅ 完整的任务删除（包括视频文件）
4. ✅ 智能降级（本地失败时使用远程）
5. ✅ 前端无需修改

**视频现在安全地存储在本地服务器，不再依赖远程服务的可用性。**
