# 番茄上传轮询停止修复

## 问题描述

前端在上传任务完成后仍然持续轮询状态查询接口，即使后端返回404错误也不停止。

### 日志表现
```
INFO:werkzeug:127.0.0.1 - - [26/Dec/2025 05:54:06] "GET /api/fanqie/upload/status/upload_1766672833_凡人：我能掠夺词条 HTTP/1.1" 404 -
INFO:werkzeug:127.0.0.1 - - [26/Dec/2025 05:54:08] "GET /api/fanqie/upload/status/upload_1766672833_凡人：我能掠夺词条 HTTP/1.1" 404 -
INFO:werkzeug:127.0.0.1 - - [26/Dec/2025 05:54:10] "GET /api/fanqie/upload/status/upload_1766672833_凡人：我能掠夺词条 HTTP/1.1" 404 -
```

任务已经完成并从后端清理，但前端轮询没有停止。

## 根本原因

1. **前端问题**：
   - 在轮询停止的多个分支中没有清空 `currentTaskId` 全局变量
   - 模态框关闭事件处理不完善，没有确保状态清理

2. **后端问题**：
   - 任务完成后立即从 `upload_tasks` 字典中移除
   - 导致前端在获取最终状态时收到404错误

## 解决方案

### 前端修复（web/templates/fanqie_upload.html）

在所有轮询停止的地方添加 `currentTaskId = null`：

```javascript
// 1. 任务不存在（404）时
if (response.status === 404) {
    clearInterval(progressInterval);
    currentTaskId = null; // ✅ 新增：清空任务ID
    return;
}

// 2. 任务完成时
if (data.task.status === 'completed') {
    clearInterval(progressInterval);
    currentTaskId = null; // ✅ 新增：清空任务ID
    modal.hide();
}

// 3. 任务失败时
if (data.task.status === 'failed') {
    clearInterval(progressInterval);
    currentTaskId = null; // ✅ 新增：清空任务ID
    modal.hide();
}

// 4. 网络错误时
catch (error) {
    clearInterval(progressInterval);
    currentTaskId = null; // ✅ 新增：清空任务ID
    modal.hide();
}

// 5. 模态框关闭时
modalElement.addEventListener('hidden.bs.modal', () => {
    clearInterval(progressInterval);
    currentTaskId = null; // ✅ 新增：清空任务ID
});
```

### 后端修复（src/integration/fanqie_uploader.py）

实现任务延迟清理机制：

```python
class FanqieUploader:
    # 任务保留时间：完成后保留5分钟
    TASK_RETENTION_TIME = 300  # 300秒 = 5分钟
    
    def __init__(self):
        self.upload_tasks = {}
        self.upload_status = {}
        self.task_completion_times = {}  # ✅ 新增：记录任务完成时间
        
        # ✅ 新增：启动定期清理线程
        self._start_task_cleanup_thread()
    
    def _update_task_status(self, task_id, status, progress, message=""):
        # ... 原有代码 ...
        
        # ✅ 新增：记录任务完成时间
        if status in ['completed', 'failed']:
            self.task_completion_times[task_id] = time.time()
            self.logger.info(f"任务 {task_id} 状态更新为 {status}，将在 {self.TASK_RETENTION_TIME} 秒后清理")
    
    def _start_task_cleanup_thread(self):
        """✅ 新增：定期清理已完成任务"""
        def cleanup_old_tasks():
            while True:
                current_time = time.time()
                tasks_to_remove = []
                
                # 查找超过保留时间的任务
                for task_id, completion_time in self.task_completion_times.items():
                    if current_time - completion_time > self.TASK_RETENTION_TIME:
                        tasks_to_remove.append(task_id)
                
                # 清理过期任务
                for task_id in tasks_to_remove:
                    del self.upload_tasks[task_id]
                    del self.upload_status[task_id]
                    del self.task_completion_times[task_id]
                    self.logger.info(f"清理过期任务: {task_id}")
                
                time.sleep(60)  # 每60秒检查一次
        
        cleanup_thread = threading.Thread(target=cleanup_old_tasks, daemon=True)
        cleanup_thread.start()
```

## 工作流程

### 正常流程

1. **启动上传**：
   - 前端：设置 `currentTaskId`，显示进度模态框
   - 后端：创建任务，开始上传

2. **轮询状态**（每2秒）：
   - 前端：请求 `/api/fanqie/upload/status/{task_id}`
   - 后端：返回当前任务状态（初始 → 准备 → 上传 → 完成）

3. **任务完成**：
   - 后端：将状态设为 "completed"，记录完成时间，保留任务5分钟
   - 前端：收到完成状态，清空 `currentTaskId`，停止轮询，关闭模态框

4. **自动清理**（5分钟后）：
   - 后端清理线程：删除已完成5分钟以上的任务

### 异常流程

1. **网络错误**：
   - 前端：捕获异常，清空 `currentTaskId`，停止轮询

2. **任务不存在（404）**：
   - 前端：收到404，清空 `currentTaskId`，停止轮询
   - 后端：任务可能已完成且超过5分钟被清理

3. **用户关闭模态框**：
   - 前端：触发关闭事件，清空 `currentTaskId`，停止轮询

## 优势

1. **防止无限轮询**：确保任何情况下轮询都会正确停止
2. **内存管理**：自动清理过期任务，避免内存泄漏
3. **用户体验**：即使任务已完成，用户仍能在5分钟内查看最终状态
4. **日志清晰**：每个关键操作都有明确的日志记录

## 测试建议

1. **正常完成**：启动上传，等待完成，确认轮询停止且 `currentTaskId` 被清空
2. **网络中断**：上传过程中断开网络，确认轮询停止
3. **多次上传**：连续启动多个上传任务，确认不会有重复轮询
4. **模态框关闭**：上传过程中手动关闭模态框，确认轮询停止
5. **延迟清理**：等待5分钟后，确认任务被自动清理

## 相关文件

- `web/templates/fanqie_upload.html` - 前端轮询逻辑
- `src/integration/fanqie_uploader.py` - 后端任务管理
- `web/web_server_refactored.py` - API路由

## 修复日期

2025-12-26