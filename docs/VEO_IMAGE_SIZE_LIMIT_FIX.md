# VeO 视频生成图片大小限制修复

## 问题描述

### 错误信息
```
API请求失败: {"code":"fail_to_fetch_task","message":"r.ParseMultipartForm failed: multipart: message too large","data":null}
```

### 错误原因
AI-WX VeO API 对请求体大小有限制。当上传的图片（base64 编码）太大时，服务器会返回 "message too large" 错误。

**常见原因：**
- 上传的图片分辨率过高（如 4K、8K 图片）
- 图片质量过高（未压缩的 PNG 或高质量 JPEG）
- 一次上传多张大图片

## 解决方案

### 1. 自动图片压缩

系统现在会自动压缩上传到 VeO API 的图片：

**压缩参数：**
- **最大单张图片大小**: 2 MB
- **最大图片尺寸**: 1920x1920 像素
- **默认压缩质量**: 85%
- **最低压缩质量**: 60%

**压缩策略：**
1. 如果图片超过 1920 像素，会先缩小尺寸
2. 使用 JPEG 格式重新编码，质量从 85% 开始
3. 如果压缩后仍然超过 2 MB，逐步降低质量（每次降 5%）
4. 直到达到 2 MB 以下或达到最低质量 60%

### 2. 代码实现

#### 新增文件：`src/utils/image_compressor.py`

提供以下功能：
- `compress_image()` - 压缩单张图片
- `validate_and_compress_images()` - 批量验证和压缩图片
- 自动计算压缩率和统计信息

#### 修改文件：`src/managers/VeOVideoManager.py`

在发送请求到 API 之前自动压缩图片：
```python
# 压缩图片（如果有）
if task.native_request.images:
    self.logger.info(f"🖼️  开始压缩 {len(task.native_request.images)} 张图片...")
    compressed_images, compression_stats = validate_and_compress_images(
        task.native_request.images,
        max_size_mb=MAX_IMAGE_SIZE_MB
    )
    task.native_request.images = compressed_images
```

### 3. 使用建议

#### 推荐的图片格式和大小

**最佳实践：**
- ✅ 使用 JPEG 格式（而不是 PNG）
- ✅ 分辨率：720p-1080p（1280x720 或 1920x1080）
- ✅ 单张图片 < 1 MB
- ✅ 最多上传 2 张图片

**避免：**
- ❌ 使用 4K 或更高分辨率
- ❌ 上传未压缩的 PNG 图片
- ❌ 一次上传多张大图片

#### 图片压缩示例

**原始图片：**
- 分辨率：3840x2160 (4K)
- 格式：PNG
- 大小：8.5 MB

**压缩后：**
- 分辨率：1920x1080 (1080p)
- 格式：JPEG
- 质量：85%
- 大小：1.2 MB
- 压缩率：85.9%

### 4. 日志输出

系统会输出详细的压缩日志：

```
📸 原始图片大小: 8.50 MB
🔄 调整图片尺寸: 3840x2160 -> 1920x1080
🔄 质量 85: 1.20 MB
✅ 压缩成功: 8.50 MB -> 1.20 MB (85.9% 减少)

📊 压缩统计:
  总数: 2
  压缩: 2
  跳过: 0
  失败: 0
  总大小: 12.50 MB -> 2.40 MB
  压缩率: 80.8%
```

### 5. 常见问题

#### Q: 为什么我的图片上传失败？
A: 可能是图片太大。系统会自动压缩，但如果压缩后仍然超过限制，请手动减小图片尺寸或质量。

#### Q: 压缩会影响视频质量吗？
A: 通常不会明显影响。VeO API 主要使用图片的构图和内容，轻微的压缩不会显著影响最终视频质量。

#### Q: 我可以手动压缩图片吗？
A: 可以。使用任何图片编辑工具（如 Photoshop、GIMP、在线工具）将图片调整为推荐的格式和大小。

#### Q: 如果压缩失败怎么办？
A: 系统会记录错误日志，并尝试使用原始图片。如果仍然失败，请检查图片格式是否正确（支持 JPEG、PNG 等常见格式）。

### 6. 配置调整

如果需要修改压缩参数，可以编辑 `src/utils/image_compressor.py`：

```python
# VeO API 最大请求体大小限制（保守估计）
MAX_IMAGE_SIZE_MB = 2  # 修改此值调整最大图片大小

# 推荐的压缩质量
DEFAULT_QUALITY = 85  # 修改此值调整默认压缩质量
MIN_QUALITY = 60  # 修改此值调整最低压缩质量

# 推荐的最大尺寸
MAX_DIMENSION = 1920  # 修改此值调整最大边长（像素）
```

### 7. 依赖要求

需要安装 Pillow 库：

```bash
pip install Pillow
```

或者更新 requirements.txt：

```
Pillow>=10.0.0
```

## 测试

### 测试压缩功能

```python
from src.utils.image_compressor import compress_image

# 测试单张图片压缩
with open('test_image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

compressed = compress_image(image_data, max_size_mb=2)
print(f"压缩完成")
```

### 测试 API 请求

```python
from src.managers.VeOVideoManager import get_veo_video_manager

manager = get_veo_video_manager()
# 系统会自动压缩图片
```

## 相关文件

- `src/utils/image_compressor.py` - 图片压缩工具
- `src/managers/VeOVideoManager.py` - VeO 视频生成管理器（集成压缩）
- `config/aiwx_video_config.py` - AI-WX API 配置

## 更新日志

- **2026-01-13**: 添加自动图片压缩功能，解决 "message too large" 错误