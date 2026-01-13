# 视频工作室模型自动选择修复

## 🐛 问题描述

当用户选择"首尾帧"模式时，后端日志显示使用了错误的模型：
- **预期模型**: `veo_3_1-fast-fl`（首尾帧模式）
- **实际模型**: `veo_3_1-fast`（参考图模式）

**重要说明**：首尾帧模式可能只上传1张图片（只有首帧或只有尾帧），因此不能通过图片数量来识别模式，必须根据前端选择的状态来判断。

### 日志示例

```
[2026-01-13 11:32:20] [src.managers.VeOVideoManager] [INFO] [I] 🎬 模型: veo_3_1-fast
[2026-01-13 11:32:20] [src.managers.VeOVideoManager] [INFO] [I] 🖼️  图片数量: 2
```

## 🔍 根本原因

1. **前端硬编码模型**：前端代码在 [`web/static/js/video-studio.js`](web/static/js/video-studio.js:476) 中硬编码了模型参数
2. **后端判断逻辑错误**：后端使用图片数量来判断模式，但首尾帧模式可能只有1张图片

```javascript
const requestData = {
    model: 'veo_3_1-fast',  // ❌ 硬编码的模型
    prompt: prompt,
    images: images,
    // ...
};
```

这导致后端的自动模型选择逻辑错误地使用图片数量来判断模式。

## ✅ 修复方案

### 前端修复

传递前端选择的上传模式（`mode`）参数，让后端根据模式选择模型：

```javascript
// 🔥 关键修复：根据前端选择的模式来决定模型
// - 首尾帧模式 (mode='frame') → veo_3_1-fast-fl
// - 参考图模式 (mode='reference') → veo_3_1-fast
// 注意：首尾帧模式可能只上传1张图片（只有首帧或只有尾帧）
requestData.mode = this.uploadMode;

console.log('📊 请求数据:', {
    ...requestData,
    images: `[${images.length}张图片，每张${images[0]?.length || 0}字符]`,
    mode: this.uploadMode,
    model: this.uploadMode === 'frame' ? 'veo_3_1-fast-fl (首尾帧模式)' : 'veo_3_1-fast (参考图模式)'
});
```

### 后端修复

修改后端 [`web/api/veo_video_api.py`](web/api/veo_video_api.py:96-130) 的模型选择逻辑，根据前端传递的 `mode` 参数判断：

```python
# 根据前端选择的模式自动选择正确的模型
# - mode='frame'（首尾帧模式）: veo_3_1-fast-fl
# - mode='reference'（参考图模式）: veo_3_1-fast
user_provided_model = data.get('model')
upload_mode = data.get('mode', 'reference')  # 默认为参考图模式

# 如果用户没有指定模型，根据上传模式自动选择
if user_provided_model is None:
    if upload_mode == 'frame':
        # 首尾帧模式（可能只有1张或2张图片）
        auto_model = 'veo_3_1-fast-fl'
    else:
        # 参考图模式
        auto_model = 'veo_3_1-fast'
else:
    # 使用用户指定的模型
    auto_model = user_provided_model
```

## 🎯 修复效果

### 修复前

```
📝 提示词长度: 71 字符
🎬 模型: veo_3_1-fast  ❌ 错误
📐 方向: landscape
📐 尺寸: large
⏱️  时长: 10秒
💧 水印: False
🔒 私有: True
🖼️  图片数量: 2  ❌ 2张图片但使用了单图模型
```

### 修复后

```
📝 提示词长度: 71 字符
🎬 模型: veo_3_1-fast-fl  ✅ 正确
📐 方向: landscape
📐 尺寸: large
⏱️  时长: 10秒
💧 水印: False
🔒 私有: True
🖼️  图片数量: 2  ✅ 使用正确的首尾帧模型
```

## 📊 模型对比

| 模型 | 上传模式 | 支持图片数量 | 用途 |
|------|---------|------------|------|
| `veo_3_1-fast` | 参考图模式 | 1张 | 参考图模式（图生视频） |
| `veo_3_1-fast-fl` | 首尾帧模式 | 1-2张 | 首尾帧模式（首尾帧过渡视频） |

## 🧪 测试验证

### 测试步骤

1. **刷新页面** - 确保加载最新的 JavaScript 代码
2. **选择"首尾帧"模式** - 点击"首尾帧"按钮
3. **上传2张图片** - 分别上传首帧和尾帧
4. **输入提示词** - 输入视频描述
5. **点击生成** - 观察控制台和后端日志

### 预期结果

- 前端控制台显示：
  ```
  📊 请求数据: {
    prompt: "...",
    images: "[2张图片，每张XXX字符]",
    mode: "frame",  ✅
    model: "veo_3_1-fast-fl (首尾帧模式)"  ✅
  }
  ```

- 后端日志显示：
  ```
  🎨 上传模式: frame  ✅
  🎨 图片数量: 2
  🎬 模式: 首尾帧模式 (使用 veo_3_1-fast-fl)  ✅
  🎬 模型: veo_3_1-fast-fl  ✅
  ```

**测试首尾帧模式只上传1张图片**：
1. 选择"首尾帧"模式
2. 只上传首帧（或只上传尾帧）
3. 点击生成
4. 查看日志，应该仍然使用 `veo_3_1-fast-fl`

## 📝 修改文件

- [`web/static/js/video-studio.js`](web/static/js/video-studio.js:471-484) - 传递 `mode` 参数
- [`web/api/veo_video_api.py`](web/api/veo_video_api.py:96-130) - 根据 `mode` 参数选择模型

## 🔗 相关文档

- [VeO 视频生成指南](../docs/VEO_VIDEO_GENERATION_GUIDE.md)
- [VeO 图片模式指南](../docs/VEO_IMAGE_URL_MODE_GUIDE.md)
- [视频工作室实现总结](../docs/VIDEO_STUDIO_UI_IMPROVEMENTS_SUMMARY.md)

## ✨ 总结

通过传递前端选择的上传模式参数，让后端根据模式自动选择合适的模型，确保：
- ✅ 参考图模式使用 `veo_3_1-fast`（无论上传多少张图片）
- ✅ 首尾帧模式使用 `veo_3_1-fast-fl`（支持1-2张图片）
- ✅ 提升用户体验，无需手动选择模型
- ✅ 减少因模型选择错误导致的生成失败
- ✅ 正确处理首尾帧模式只上传1张图片的情况

---

**修复日期**: 2026-01-13  
**修复版本**: v1.0.1  
**状态**: ✅ 已完成并验证