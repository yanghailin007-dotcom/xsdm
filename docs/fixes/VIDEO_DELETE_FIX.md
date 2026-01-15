# 视频删除功能修复

## 问题描述

用户在视频素材库中删除视频时，即使后端返回400错误（任务不存在），前端仍然会从本地列表中移除该视频。这导致前端显示的视频列表与后端实际存储的数据不同步。

## 根本原因

在 [`web/static/js/video-studio.js`](web/static/js/video-studio.js:530-553) 的 [`deleteVideo()`](web/static/js/video-studio.js:530) 方法中：

```javascript
async deleteVideo(videoId) {
    try {
        const response = await fetch(`/api/veo/tasks/${videoId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        // 从列表中移除
        this.videoLibrary = this.videoLibrary.filter(v => v.id !== videoId);
        this.renderVideoLibrary();
        this.showToast('视频已删除', 'success');
        
    } catch (error) {
        console.error('删除失败:', error);
        this.showToast('删除失败: ' + error.message, 'error');
    }
}
```

**问题**：即使在 `catch` 块中捕获了删除失败的错误，前端也没有阻止列表更新，导致用户看到视频被"删除"了，但实际上后端任务仍然存在。

## 修复方案

### 1. 改进错误处理

解析后端返回的详细错误信息，而不是简单地显示HTTP状态码：

```javascript
if (!response.ok) {
    // 解析错误信息
    const errorData = await response.json();
    const errorMessage = errorData.error?.message || `HTTP ${response.status}`;
    throw new Error(errorMessage);
}
```

### 2. 确保状态同步

**只有在删除成功时才从列表中移除视频**：

```javascript
// 只有在成功时才从列表中移除
this.videoLibrary = this.videoLibrary.filter(v => v.id !== videoId);
this.renderVideoLibrary();
this.showToast('视频已删除', 'success');
```

这段代码只在 `response.ok` 为 true 时执行，确保删除成功才更新UI。

### 3. 自动重新加载

**删除失败时自动重新加载视频列表**，确保前后端数据一致：

```javascript
catch (error) {
    console.error('删除失败:', error);
    this.showToast('删除失败: ' + error.message, 'error');
    // 🔥 修复：删除失败时重新加载列表，确保前后端同步
    this.loadVideoLibrary();
}
```

## 修复效果

### 修复前
1. 用户点击删除按钮
2. 后端返回 400 错误（任务不存在）
3. 前端仍从列表中移除视频
4. 用户误以为删除成功
5. 刷新页面后视频又出现

### 修复后
1. 用户点击删除按钮
2. 后端返回 400 错误（任务不存在）
3. 前端显示详细错误信息
4. 自动重新加载视频列表
5. 用户看到正确的视频列表

## 测试场景

### 场景1：删除不存在的任务
- **操作**：尝试删除一个不存在的任务ID（如 `veo_165d3ceb9de1`）
- **预期**：显示错误提示"删除失败: Failed to delete generation: veo_165d3ceb9de1"，并重新加载列表
- **结果**：✅ 符合预期

### 场景2：删除存在的任务
- **操作**：删除一个存在的任务
- **预期**：显示成功提示"视频已删除"，并从列表中移除
- **结果**：✅ 符合预期

### 场景3：删除后刷新页面
- **操作**：删除任务后刷新页面
- **预期**：列表显示与删除前一致（不存在的任务不会消失）
- **结果**：✅ 符合预期

## 相关文件

- [`web/static/js/video-studio.js`](web/static/js/video-studio.js:530-553) - 前端删除逻辑
- [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py:651-686) - 后端删除逻辑
- [`web/api/veo_video_api.py`](web/api/veo_video_api.py:328-366) - API路由

## 后续建议

1. **添加防抖机制**：防止用户快速重复点击删除按钮
2. **优化错误提示**：针对不同错误类型显示不同的提示信息
3. **添加批量删除**：支持一次删除多个视频
4. **添加删除确认**：在删除前显示更详细的确认信息

## 修复时间

2026-01-15 14:13:00

## 修复者

Kilo Code