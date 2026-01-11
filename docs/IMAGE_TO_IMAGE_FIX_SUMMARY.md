# Nano Banana 图生图功能修复总结

## 问题描述

图生图功能（使用参考图片生成新图片）无法正常工作。

## 根本原因分析

对比官方demo代码，发现以下关键差异：

### 1. **字段命名格式错误**
```python
# ❌ 错误格式
parts.append({
    "inlineData": {  # 驼峰命名
        "mimeType": mime_type,  # 驼峰命名
        "data": ref_image_base64
    }
})

# ✅ 正确格式
parts.append({
    "inline_data": {  # 下划线命名
        "mime_type": mime_type,  # 下划线命名
        "data": ref_image_base64
    }
})
```

### 2. **parts数组顺序错误**
```python
# ❌ 错误顺序（先图片后文本）
parts = []
if reference_image:
    parts.append({"inline_data": {...}})  # 图片在前
parts.append({"text": prompt})  # 文本在后

# ✅ 正确顺序（先文本后图片，符合API规范）
parts = []
parts.append({"text": prompt})  # 文本在前
if reference_image:
    parts.append({"inline_data": {...}})  # 图片在后
```

### 3. **请求体结构问题**
```python
# ❌ 错误结构（包含role字段）
request_body = {
    "contents": [
        {
            "role": "user",  # 多余的字段
            "parts": parts
        }
    ],
    ...
}

# ✅ 正确结构（简化结构）
request_body = {
    "contents": [
        {
            "parts": parts  # 直接包含parts
        }
    ],
    ...
}
```

### 4. **响应解析兼容性不足**
增加了对 `inline_data` 和 `inlineData` 两种格式的兼容支持。

## 修复内容

### 1. 修正字段命名格式
- `inlineData` → `inline_data`
- `mimeType` → `mime_type`

### 2. 调整parts数组顺序
- 先添加文本提示词
- 后添加参考图片（如果存在）

### 3. 简化请求体结构
- 移除不必要的 `role` 字段
- 使用更简洁的 `contents` 结构

### 4. 增强响应解析
- 兼容 `inlineData` 和 `inline_data` 两种格式
- 保持原有的多种响应格式支持

## 测试方法

运行测试脚本：
```bash
python test_image_to_image.py
```

测试包含三个场景：
1. **文生图** - 纯文本生成图片
2. **图生图** - 使用参考图转换风格
3. **人物剧照+参考图** - 基于参考图生成人物剧照

## 使用示例

```python
from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator

generator = NanoBananaImageGenerator()

# 图生图示例
result = generator.generate_image(
    prompt="将这张图片转换成水墨画风格，保持主要构图",
    aspect_ratio="16:9",
    image_size="2K",
    save_path="output.png",
    reference_image="reference.png"  # 参考图路径
)

if result["success"]:
    print(f"生成成功: {result['local_path']}")
else:
    print(f"生成失败: {result['error']}")
```

## 技术细节

### API端点
```
https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent
```

### 认证方式
```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
```

### 超时设置
- 无参考图: 60秒（默认）
- 有参考图: 300秒（自动延长5倍）

## 日志调试

详细日志保存在：
```
logs/nanobanana_detailed.log
```

查看日志可了解：
- API请求详情
- 响应结构分析
- Base64数据大小
- 错误原因追踪

## 注意事项

1. **图片格式支持**: JPEG, PNG等常见格式
2. **图片大小**: 建议不超过5MB
3. **超时设置**: 有参考图时请求时间较长，已自动调整超时
4. **API配额**: 注意API调用频率限制

## 相关文件

- [`src/utils/NanoBananaImageGenerator.py`](../src/utils/NanoBananaImageGenerator.py) - 主实现文件
- [`test_image_to_image.py`](../test_image_to_image.py) - 测试脚本
- [`config/config.py`](../config/config.py) - 配置文件

## 更新日志

### 2025-01-11
- ✅ 修复字段命名格式（inline_data, mime_type）
- ✅ 调整parts数组顺序（文本优先）
- ✅ 简化请求体结构（移除role字段）
- ✅ 增强响应解析兼容性
- ✅ 添加完整测试套件