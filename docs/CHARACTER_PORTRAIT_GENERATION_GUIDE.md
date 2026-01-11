# 人物剧照生成功能使用指南

## 功能概述

人物剧照生成功能是一个专门用于生成小说角色图像的工具，支持以下特性：

- ✅ **参考图像支持**：可以上传参考图像，AI会基于参考图像的风格和特征生成新图像
- ✅ **自动提示词生成**：基于角色设计自动生成高质量的图像生成提示词
- ✅ **自定义提示词**：支持添加自定义描述来调整生成效果
- ✅ **多种比例和质量**：支持 16:9、9:16、1:1、4:3 等多种比例，1K/2K/4K 质量选项
- ✅ **生成历史**：自动保存生成历史，方便查看和管理

## 技术实现

### 后端架构

#### 1. NanoBananaImageGenerator 扩展

**文件位置**: [`src/utils/NanoBananaImageGenerator.py`](src/utils/NanoBananaImageGenerator.py)

**关键改动**:
- 新增 `reference_image` 参数支持图像输入
- 自动处理参考图像的 base64 编码
- 兼容 Gemini API 的多模态输入格式

**核心代码**:
```python
def generate_image(
    self,
    prompt: str,
    aspect_ratio: str = "16:9",
    image_size: str = "4K",
    save_path: Optional[str] = None,
    retry_count: int = 0,
    reference_image: Optional[str] = None  # 🔥 新增参数
) -> Dict[str, Any]:
```

#### 2. API 路由

**文件位置**: [`web/api/video_generation_api.py`](web/api/video_generation_api.py)

**接口端点**: `POST /api/video/generate-character-portrait`

**请求参数**:
```json
{
  "title": "小说标题",
  "character_id": "角色ID或名称",
  "character_data": {
    "name": "角色名称",
    "role": "角色定位",
    "description": "角色描述"
  },
  "aspect_ratio": "9:16",
  "image_size": "4K",
  "reference_image": "/path/to/reference.jpg"  // 可选
}
```

**响应结果**:
```json
{
  "success": true,
  "image_path": "/本地路径",
  "image_url": "/generated_images/xxx.png",
  "prompt": "使用的提示词",
  "character_name": "角色名称",
  "used_reference_image": true,
  "message": "生成成功"
}
```

### 前端架构

#### 1. 页面模板

**文件位置**: [`web/templates/character-portrait.html`](web/templates/character-portrait.html)

**页面结构**:
- 左侧配置面板（3步骤）
  1. 选择小说
  2. 选择角色
  3. 配置生成参数
- 右侧结果面板
  - 角色信息展示
  - 生成结果展示
  - 生成历史记录

#### 2. 样式文件

**文件位置**: [`web/static/css/character-portrait.css`](web/static/css/character-portrait.css)

**设计特点**:
- 现代化渐变背景
- 卡片式布局
- 响应式设计
- 流畅的动画效果

#### 3. 交互逻辑

**文件位置**: [`web/static/js/character-portrait.js`](web/static/js/character-portrait.js)

**核心功能**:
- 小说列表加载
- 角色选择和管理
- 参考图像上传（支持拖拽）
- 图像生成和预览
- 历史记录管理

## 使用步骤

### 1. 访问页面

在浏览器中访问: `http://localhost:8080/character-portrait`

### 2. 选择小说

从下拉列表中选择已完成的小说项目。只有完成第一阶段设定的小说才会显示在列表中。

### 3. 选择角色

系统会自动加载所选小说的所有角色设计。点击角色卡片选择要生成剧照的角色。

### 4. 配置生成参数

#### 4.1 参考图像（可选）

勾选"使用参考图像"后，可以上传一张图片作为参考：

- 支持拖拽上传
- 支持 JPG、PNG 格式
- 建议分辨率 500x500 以上

**使用场景**:
- 保持角色风格一致性
- 基于已有图像生成变体
- 参考特定画风或构图

#### 4.2 图片比例

- **9:16** (竖屏) - 适合角色展示，默认选项
- **16:9** (横屏) - 适合场景展示
- **1:1** (正方形) - 适合头像或社交媒体
- **4:3** (标准) - 传统比例

#### 4.3 图片质量

- **4K** - 最高质量，生成时间较长
- **2K** - 高质量，平衡选择
- **1K** - 标准质量，生成速度快

#### 4.4 自定义提示词（可选）

可以添加额外的描述来调整生成效果：

```
添加具体的表情、动作
指定背景环境
描述光影效果
```

### 5. 生成剧照

点击"生成剧照"按钮，系统会：

1. 基于角色设计生成提示词
2. 如果有参考图像，会将其编码为 base64 并附加到请求中
3. 调用 NanoBanana API 生成图像
4. 显示生成的图像
5. 保存到历史记录

### 6. 管理结果

生成的图像支持以下操作：

- **下载**：保存到本地
- **用作参考图**：将当前生成的图像设置为参考图像，用于下一次生成
- **查看历史**：点击历史记录中的图像可以重新查看

## API 配置

### Nano Banana 配置

**配置文件**: [`config/config.py`](config/config.py)

```python
"nanobanana": {
    "base_url": "https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent",
    "api_key": "your-api-key",
    "enabled": True,
    "default_config": {
        "responseModalities": ["TEXT", "IMAGE"],
        "imageConfig": {
            "aspectRatio": "16:9",
            "imageSize": "4K"
        }
    },
    "supported_aspect_ratios": ["16:9", "4:3", "1:1", "9:16"],
    "supported_image_sizes": ["1K", "2K", "4K"],
    "timeout": 300,
    "max_retries": 3
}
```

### 环境变量

如果需要使用环境变量配置 API Key：

```bash
export NANO_BANANA_API_KEY="your-api-key"
```

## 常见问题

### Q1: 生成的图像质量不高怎么办？

**A**: 
1. 尝试使用更高的图片质量（2K 或 4K）
2. 添加详细的自定义提示词
3. 上传高质量的参考图像
4. 检查角色设计是否完整

### Q2: 参考图像不起作用？

**A**: 
1. 确认参考图像已成功上传（会显示预览）
2. 检查图像格式是否支持（JPG、PNG）
3. 查看浏览器控制台是否有错误信息
4. 确认后端 API 支持图像输入

### Q3: 生成速度很慢？

**A**: 
1. 图像生成通常需要 30-60 秒
2. 降低图片质量可以加快生成速度
3. 检查网络连接是否稳定
4. 查看 API 配置中的 timeout 设置

### Q4: 如何批量生成多个角色的剧照？

**A**: 
目前不支持批量生成，需要逐个选择角色生成。未来版本可能会添加批量生成功能。

### Q5: 生成的图像可以用于商业用途吗？

**A**: 
这取决于使用的 API 服务条款。请查阅 Nano Banana API 的使用协议。

## 开发说明

### 文件结构

```
项目根目录/
├── src/
│   └── utils/
│       └── NanoBananaImageGenerator.py    # 图像生成器
├── web/
│   ├── api/
│   │   └── video_generation_api.py        # API 路由
│   ├── routes/
│   │   └── auth_routes.py                 # 页面路由
│   ├── templates/
│   │   └── character-portrait.html        # 页面模板
│   └── static/
│       ├── css/
│       │   └── character-portrait.css     # 样式文件
│       └── js/
│           └── character-portrait.js      # 前端逻辑
├── config/
│   └── config.py                          # 配置文件
└── generated_images/                      # 生成图像保存目录
```

### 扩展功能建议

1. **批量生成**: 支持一次选择多个角色批量生成
2. **图像编辑**: 添加简单的图像编辑功能（裁剪、旋转等）
3. **风格迁移**: 支持选择不同的艺术风格
4. **导出功能**: 导出为特定格式或尺寸
5. **分享功能**: 生成分享链接

## 更新日志

### v1.0.0 (2026-01-11)

- ✅ 初始版本发布
- ✅ 支持参考图像输入
- ✅ 支持自定义提示词
- ✅ 支持多种比例和质量
- ✅ 支持生成历史记录

## 技术支持

如有问题或建议，请联系开发团队或提交 Issue。

---

**文档版本**: 1.0.0  
**最后更新**: 2026-01-11  
**维护者**: Kilo Code