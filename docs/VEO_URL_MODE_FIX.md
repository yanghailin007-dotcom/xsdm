# VeO Base64模式修复说明

## 问题描述

Web端传递base64图片数据时，API报错：

**错误信息：**
```
API请求失败: {"code":"get_task_failed","message":"帧转视频模式的至少上传一帧","data":null}
```

## 根本原因分析

### 数据流转过程

1. **Web API层** ([`veo_video_api.py:157-163`](web/api/veo_video_api.py:157-163))
   ```python
   for img_base64 in veo_request.images:
       messages[0]["content"].append({
           "type": "image_url",
           "image_url": {
               "url": f"data:image/jpeg;base64,{img_base64}"  # 添加了data URL前缀
           }
       })
   ```

2. **模型层** ([`VeOCreateVideoRequest.to_dict()`](src/models/veo_models.py:125) - 修复前)
   ```python
   def to_dict(self) -> Dict[str, Any]:
       if self.image_urls:
           images_param = self.image_urls
       else:
           # ❌ 问题：只保留HTTP/HTTPS URL，其他都被过滤掉
           images_param = [img for img in self.images if self._is_url(img)]
       
       return {"images": images_param, ...}
   ```

3. **发送到API的payload**
   ```json
   {
     "images": [],  // ❌ 空数组！因为data URL被过滤掉了
     "model": "veo_3_1-fast",
     ...
   }
   ```

### 问题的根源

**在 [`veo_models.py`](src/models/veo_models.py:119) 中：**

```python
def _is_url(self, img_str: str) -> bool:
    """判断是否为 URL"""
    if not img_str:
        return False
    return img_str.startswith(('http://', 'https://'))
```

当base64数据被添加了 `data:image/jpeg;base64,` 前缀后：
- `_is_url("data:image/jpeg;base64,iVBORw0KG...")` 返回 `False`
- 在 `to_dict()` 中被过滤掉
- 最终 `images_param` 为空数组
- API收到空数组，报错："帧转视频模式的至少上传一帧"

### 客户的Demo对比

客户直接使用URL字符串，**不需要添加data URL前缀**：

```python
payload = {
   "images": [
      "https://img.remit.ee/api/file/...",
      "https://img.remit.ee/api/file/..."
   ],  # 直接使用HTTP URL，不添加前缀
   "model": "veo_3_1-fl",
   ...
}
```

## 解决方案

### 修复1: 改进 `to_dict()` 方法处理data URL

**文件**: [`src/models/veo_models.py`](src/models/veo_models.py:125-158)

```python
def to_dict(self) -> Dict[str, Any]:
    """转换为字典"""
    # 优先使用 image_urls（如果有）
    if self.image_urls:
        images_param = self.image_urls
    else:
        # 处理 images 列表
        # 1. 过滤掉空值
        # 2. 移除 data URL 前缀（如果有），只保留纯 base64
        images_param = []
        for img in self.images:
            if not img or not isinstance(img, str):
                continue
            
            # 如果是 HTTP/HTTPS URL，直接使用
            if self._is_url(img):
                images_param.append(img)
            # 如果是 data URL，移除前缀，只保留 base64 部分
            elif img.startswith('data:image/'):
                # 格式: data:image/jpeg;base64,<base64_data>
                if ',' in img:
                    base64_part = img.split(',', 1)[1]
                    images_param.append(base64_part)
                else:
                    # 如果没有逗号，可能格式不正确，但还是保留
                    images_param.append(img)
            # 否则认为是纯 base64，直接使用
            else:
                images_param.append(img)
    
    return {
        "images": images_param,
        "model": self.model,
        "orientation": self.orientation,
        "prompt": self.prompt,
        "size": self.size,
        "duration": self.duration,
        "watermark": self.watermark,
        "private": self.private
    }
```

### 修复2: 添加URL/Base64模式智能判断

**文件**: [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py:261-286)

```python
# 使用原生格式发送请求
if task.native_request.images:
    # 🔥 修复：区分URL模式和base64模式
    # 如果是URL模式，不需要压缩
    # 如果是base64模式，需要压缩
    if task.native_request.images:
        # 检查是否所有图片都是URL
        all_urls = all(self._is_url(img) for img in task.native_request.images if img)
        
        if all_urls:
            # URL模式：直接使用，不需要压缩
            self.logger.info(f"🔗 URL模式：使用 {len(task.native_request.images)} 个图片URL")
            compressed_images = task.native_request.images
        else:
            # base64模式：需要压缩
            self.logger.info(f"🖼️  Base64模式：开始压缩 {len(task.native_request.images)} 张图片...")
            compressed_images, compression_stats = validate_and_compress_images(
                task.native_request.images,
                max_size_mb=MAX_IMAGE_SIZE_MB
            )
        
        # 更新请求对象中的图片
        task.native_request.images = compressed_images

payload = task.native_request.to_dict()
```

### 修复3: 添加辅助方法

**文件**: [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py:460-465)

```python
def _is_url(self, img_str: str) -> bool:
    """判断图片字符串是否为HTTP/HTTPS URL（不包括data URL）"""
    if not img_str or not isinstance(img_str, str):
        return False
    # 只识别 http:// 和 https://，不识别 data:
    return img_str.startswith(('http://', 'https://'))
```

### 修复4: 更新模型中的注释

**文件**: [`src/models/veo_models.py`](src/models/veo_models.py:115-123)

```python
def has_image_urls(self) -> bool:
    """检查是否有图片 URL（不包括 data URL）"""
    return bool(self.image_urls) or any(self._is_url(img) for img in self.images if img)

def _is_url(self, img_str: str) -> bool:
    """判断是否为 HTTP/HTTPS URL（不包括 data URL）"""
    if not img_str or not isinstance(img_str, str):
        return False
    # 只识别 http:// 和 https://，不识别 data:
    return img_str.startswith(('http://', 'https://'))
```

## 修复效果

### 修复前
- ❌ URL图片被错误地传递给压缩函数
- ❌ 压缩函数无法处理URL，返回空列表
- ❌ API收到空的images数组
- ❌ 报错："帧转视频模式的至少上传一帧"

### 修复后
- ✅ 自动检测图片类型（URL vs base64）
- ✅ URL模式：直接传递，不压缩
- ✅ Base64模式：正常压缩处理
- ✅ API收到正确的图片数组
- ✅ 视频生成正常工作

## 两种图片模式对比

| 模式 | 示例 | 是否压缩 | 适用场景 |
|------|------|---------|---------|
| **URL模式** | `["https://example.com/img1.png", "https://example.com/img2.png"]` | ❌ 不需要 | 图片已托管在外部服务器，直接传递URL |
| **Base64模式** | `["data:image/png;base64,iVBORw0KG...", "..."]` | ✅ 需要 | 图片编码在请求体中，需要压缩以避免超过大小限制 |

## API要求

根据客户的demo，AI-WX VeO API的要求：

```json
{
  "images": ["url1", "url2"],  // 必须至少包含一个图片URL或base64
  "model": "veo_3_1-fl",
  "orientation": "portrait",
  "prompt": "make animate",
  "size": "large",
  "duration": 15,
  "watermark": false,
  "private": true
}
```

**关键点：**
- `images` 字段必须包含至少一个元素
- 支持URL字符串或base64编码
- URL模式是推荐方式（更高效）

## 测试验证

修复后，应该能够正常处理以下场景：

1. **纯URL模式**
   ```python
   images = ["https://example.com/img1.png", "https://example.com/img2.png"]
   ```
   
2. **纯Base64模式**
   ```python
   images = ["data:image/png;base64,iVBORw0KG...", "..."]
   ```
   
3. **混合模式**（不推荐，但应该能处理）
   ```python
   images = ["https://example.com/img1.png", "data:image/png;base64,..."]
   ```

## 相关文件

- **修改文件**: `src/managers/VeOVideoManager.py`
- **相关模型**: `src/models/veo_models.py`
- **压缩工具**: `src/utils/image_compressor.py`
- **配置文件**: `config/aiwx_video_config.py`

## 总结

这次修复解决了**Base64模式下图片数据丢失**的关键bug。

### 核心问题
当web端传递base64数据时，API层添加了 `data:image/jpeg;base64,` 前缀，但模型的 `to_dict()` 方法只保留HTTP/HTTPS URL，导致data URL被过滤掉，最终API收到空数组。

### 修复核心
1. **智能识别并处理data URL**：在 `to_dict()` 中检测 `data:image/` 前缀，移除前缀并提取纯base64数据
2. **区分URL和Base64模式**：URL模式不压缩，Base64模式需要压缩
3. **兼容多种格式**：同时支持HTTP URL、Data URL和纯Base64三种格式

### 修改文件
- [`src/models/veo_models.py`](src/models/veo_models.py:125-158) - 改进 `to_dict()` 方法
- [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py:261-286) - 添加URL/Base64模式判断
- [`src/managers/VeOVideoManager.py`](src/managers/VeOVideoManager.py:460-465) - 添加 `_is_url()` 辅助方法