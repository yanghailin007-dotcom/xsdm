# 视频比例解析问题修复

## 问题描述

用户选择横屏16:9，但系统错误地解析成竖屏（portrait）。

从日志可以看到：
```
📐 方向: portrait
📏 尺寸: large
```

但用户实际选择的是横屏16:9。

## 根本原因

**后端代码只检查了`resolution`字段，忽略了前端发送的`aspect_ratio`字段**

### 前端发送的数据：
```javascript
{
  generation_config: {
    aspect_ratio: '16:9',  // ✅ 前端发送的是这个字段
    resolution: '1080p'
  }
}
```

### 后端原代码（错误）：
```python
if generation_config.resolution:
    if "1920x1080" in generation_config.resolution:
        orientation = "landscape"
    # ...
```

**问题：** `resolution` 是 "1080p"，不包含 "1920x1080"，所以无法匹配到横屏，使用了默认的竖屏设置。

## 修复方案

### 更新 [`src/managers/AiWxVideoManager.py`](src/managers/AiWxVideoManager.py:252)

**修复后：**
```python
if generation_config:
    # 优先检查 aspect_ratio（前端发送的宽高比）
    if generation_config.aspect_ratio:
        aspect_ratio = generation_config.aspect_ratio
        if aspect_ratio == '16:9' or aspect_ratio == '4:3':
            orientation = "landscape"  # 横屏
            self.logger.info(f"📐 根据宽高比 {aspect_ratio} 设置为横屏")
        elif aspect_ratio == '9:16':
            orientation = "portrait"  # 竖屏
            self.logger.info(f"📐 根据宽高比 {aspect_ratio} 设置为竖屏")
        elif aspect_ratio == '1:1':
            orientation = "square"  # 方形
            self.logger.info(f"📐 根据宽高比 {aspect_ratio} 设置为方形")
    # 备用：检查分辨率
    elif generation_config.resolution:
        if "1920x1080" in generation_config.resolution:
            orientation = "landscape"
        # ...
```

### 修复要点

1. **优先检查 `aspect_ratio`** - 这是前端实际发送的字段
2. **添加详细日志** - 记录比例解析过程
3. **支持多种比例** - 16:9, 9:16, 1:1, 4:3
4. **保留备用方案** - 如果没有aspect_ratio，仍然检查resolution

## 测试验证

### 重启服务器
```bash
# 按 Ctrl+C 停止服务器
# 重新启动
python web/wsgi.py
```

### 验证步骤

1. **刷新浏览器**（Ctrl+F5）
2. **选择横屏16:9**
3. **生成视频**
4. **查看日志** - 应该看到：
   ```
   📐 根据宽高比 16:9 设置为横屏
   📐 方向: landscape
   ```
5. **验证结果** - 生成的视频应该是横屏16:9

## 支持的视频比例

| 前端选择 | 后端解析 | AI-WX API参数 | 说明 |
|---------|---------|--------------|------|
| 16:9 (横屏) | landscape | "landscape" | 宽屏视频 |
| 9:16 (竖屏) | portrait | "portrait" | 手机竖屏 |
| 1:1 (方形) | square | "square" | 正方形 |
| 4:3 (传统) | landscape | "landscape" | 传统电视比例 |

## 数据流程

1. **用户选择** → 点击"横屏 16:9"按钮
2. **前端JavaScript** → 设置 `this.selectedRatio = '16:9'`
3. **发送请求** → `generation_config.aspect_ratio = '16:9'`
4. **后端解析** → 检测到 `'16:9'` → 设置 `orientation = "landscape"`
5. **AI-WX API** → 接收到 `"orientation": "landscape"` → 生成横屏视频
6. **返回结果** → 横屏视频URL

## 相关文件

- [`src/managers/AiWxVideoManager.py`](src/managers/AiWxVideoManager.py:252) - 比例解析逻辑
- [`web/static/js/video-studio.js`](web/static/js/video-studio.js:141) - 前端比例选择
- [`web/templates/video-studio.html`](web/templates/video-studio.html:94) - 比例选择按钮

## 其他修复

本次还包含了以下修复：
1. ✅ 视频URL字段名不匹配问题（`video_url` vs `url`）
2. ✅ 前端数据结构访问错误（`result.videos[0].url`）
3. ✅ 添加全屏播放功能
4. ✅ 添加更大的视频展示窗口

## 后续优化

1. **添加比例预览**
   - 在选择比例时显示预览图
   - 标注推荐使用场景

2. **自定义比例**
   - 支持用户输入自定义宽高比
   - 验证比例的有效性

3. **智能推荐**
   - 根据提示词内容推荐合适的比例
   - 例如：人物肖像推荐9:16，风景推荐16:9