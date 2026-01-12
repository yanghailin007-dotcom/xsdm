# AI-WX 视频生成集成指南

## 概述

本系统已集成 AI-WX 视频生成 API (https://jyapi.ai-wx.cn)，替代了原有的 Google AI Platform API。AI-WX 提供稳定可靠的视频生成服务，使用 **Veo 3.1** 模型。

## 为什么切换到 AI-WX？

原有 Google AI Platform API 遇到连接问题：
```
ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。')
```

AI-WX API 的优势：
- ✅ 稳定的连接和服务
- ✅ 支持 Veo 3.1 先进模型
- ✅ 使用 OpenAI Chat 兼容格式
- ✅ 完善的任务管理和轮询机制
- ✅ 国内访问速度快
- ✅ 支持横屏/竖屏视频生成

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       Web 应用层                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  OpenAI 标准 API (web/api/openai_video_api.py)        │  │
│  │  - POST /v1/videos/generations                       │  │
│  │  - GET /v1/videos/generations/{id}                   │  │
│  │  - GET /v1/videos/generations                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    管理器层                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AiWxVideoManager (src/managers/AiWxVideoManager.py)  │  │
│  │  - 任务队列管理                                       │  │
│  │  - 状态轮询                                          │  │
│  │  - 错误处理                                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI-WX API                                  │
│  https://jyapi.ai-wx.cn/v1/video/create                     │
└─────────────────────────────────────────────────────────────┘
```

## 配置说明

### API 密钥配置

在 [`config/aiwx_video_config.py`](config/aiwx_video_config.py) 中配置 API 密钥：

```python
# API密钥配置
AIWX_API_KEY = 'sk-0dDn3ajqtCc0PTMmD045Ff7902774431Ad0304E396C856E7'
```

### 支持的模型

| 模型 | 说明 |
|------|------|
| `veo_3_1` | 默认模型 |
| `veo_3_1-portrait` | 竖屏视频 (720x1280) |
| `veo_3_1-landscape` | 横屏视频 (1280x720) |
| `veo_3_1-fast` | 快速模式 |
| `veo_3_1-fl` | 帧转视频模式 |

### API 格式

AI-WX 使用 **OpenAI Chat Completions** 格式：

```json
{
  "model": "veo_3_1-portrait",
  "stream": false,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "视频描述文本"
        }
      ]
    }
  ]
}
```

### 支持的参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `model` | 模型名称 | `veo_3_1`, `veo_3_1-portrait`, `veo_3_1-landscape` 等 |
| `stream` | 是否流式 | `false` (目前不支持流式) |
| `messages` | 消息列表 | OpenAI Chat 格式 |

## 使用方法

### 1. 通过 Web API 创建视频生成任务

**请求示例：**

```bash
curl -X POST http://localhost:5000/v1/videos/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sora-2",
    "prompt": "一只可爱的橘猫在阳光下打哈欠，镜头缓慢推进",
    "generation_config": {
      "duration_seconds": 10,
      "resolution": "1280x720"
    }
  }'
```

**响应示例：**

```json
{
  "id": "aiwx_abc123def456",
  "object": "video.generation",
  "created": 1736655200,
  "model": "sora-2",
  "status": "processing",
  "prompt": "一只可爱的橘猫在阳光下打哈欠，镜头缓慢推进"
}
```

### 2. 查询生成状态

```bash
curl http://localhost:5000/v1/videos/generations/aiwx_abc123def456
```

**响应（处理中）：**

```json
{
  "id": "aiwx_abc123def456",
  "status": "processing",
  "created": 1736655200
}
```

**响应（完成）：**

```json
{
  "id": "aiwx_abc123def456",
  "status": "completed",
  "created": 1736655200,
  "completed": 1736655260,
  "result": {
    "videos": [
      {
        "id": "video_xyz789",
        "url": "https://jyapi.ai-wx.cn/videos/xxx.mp4",
        "duration_seconds": 10,
        "resolution": "1280x720",
        "fps": 24,
        "format": "mp4"
      }
    ],
    "finish_reason": "FINISH_REASON_STOP"
  }
}
```

### 3. 列出所有生成任务

```bash
curl "http://localhost:5000/v1/videos/generations?limit=20&status=completed"
```

### 4. Python 代码示例

```python
from src.managers.AiWxVideoManager import get_aiwx_video_manager
from src.models.video_openai_models import (
    VideoGenerationRequest,
    GenerationConfig
)

# 获取管理器
manager = get_aiwx_video_manager()

# 创建请求
request = VideoGenerationRequest(
    model="sora-2",
    prompt="一只可爱的橘猫在阳光下打哈欠",
    generation_config=GenerationConfig(
        duration_seconds=10,
        resolution="1280x720"
    )
)

# 创建生成任务
response = manager.create_generation(request)
print(f"任务ID: {response.id}")
print(f"状态: {response.status}")

# 轮询等待完成
import time
while True:
    current = manager.retrieve_generation(response.id)
    if current.status == "completed":
        print("生成完成!")
        print(f"视频URL: {current.result.videos[0].url}")
        break
    elif current.status == "failed":
        print(f"生成失败: {current.error}")
        break
    time.sleep(5)
```

## API 端点参考

### POST /v1/videos/generations

创建新的视频生成任务。

**请求体：**
```json
{
  "model": "sora-2",
  "prompt": "视频描述文本",
  "generation_config": {
    "duration_seconds": 10,
    "resolution": "1280x720"
  }
}
```

**响应：** `202 Accepted`

### GET /v1/videos/generations/{id}

查询生成任务状态。

**响应：** `200 OK`

### GET /v1/videos/generations

列出所有生成任务。

**查询参数：**
- `limit`: 返回数量（默认20）
- `status`: 状态过滤（processing/completed/failed）
- `order`: 排序（desc/asc）

**响应：** `200 OK`

### POST /v1/videos/generations/{id}/cancel

取消生成任务。

**响应：** `200 OK`

## 工作流程

```
用户请求
   │
   ▼
创建任务 → 返回任务ID
   │
   ▼
后台处理（轮询）
   │
   ├─ processing → 继续轮询
   ├─ completed → 返回视频URL
   └─ failed → 返回错误信息
```

## 轮询配置

在 [`config/aiwx_video_config.py`](config/aiwx_video_config.py) 中配置轮询参数：

```python
POLLING_CONFIG = {
    'enabled': True,
    'max_attempts': 60,      # 最大轮询次数
    'poll_interval': 5,      # 轮询间隔（秒）
    'progress_update_interval': 5,  # 进度更新间隔（秒）
}
```

## 错误处理

系统会自动处理以下错误：

1. **网络错误**：自动重试（最多3次）
2. **API 错误**：记录日志并标记任务为失败
3. **超时**：达到最大轮询次数后标记为失败

## 存储位置

生成的任务数据存储在：
```
d:/work6.05/aiwx_video_generations/
```

每个任务对应一个 JSON 文件：
```
aiwx_abc123def456.json
```

## 测试

运行测试脚本验证集成：

```bash
python test_aiwx_video_generation.py
```

测试脚本会：
1. 验证配置
2. 创建视频生成任务
3. 轮询等待完成
4. 显示结果

## 故障排除

### 问题：API 密钥无效

**解决方案：**
1. 检查 [`config/aiwx_video_config.py`](config/aiwx_video_config.py) 中的 `AIWX_API_KEY`
2. 确保密钥格式正确（以 `sk-` 开头）
3. 联系 AI-WX 获取新的 API 密钥

### 问题：连接超时

**解决方案：**
1. 检查网络连接
2. 增加 `REQUEST_CONFIG['timeout']` 值
3. 检查防火墙设置

### 问题：生成失败

**解决方案：**
1. 查看日志文件了解详细错误
2. 检查提示词是否符合规范
3. 确认账户余额充足

## 与旧系统的兼容性

本系统保持了与 OpenAI 标准 API 的兼容性：

- ✅ 相同的请求/响应格式
- ✅ 相同的状态码
- ✅ 相同的错误处理
- ❌ 不支持流式生成（AI-WX API 限制）

## 性能优化建议

1. **批量处理**：使用任务队列管理多个请求
2. **缓存结果**：保存已生成的视频URL
3. **并行查询**：使用多个线程查询任务状态
4. **超时设置**：合理设置轮询超时时间

## 后续改进计划

- [ ] 添加更多 AI-WX 支持的模型
- [ ] 实现视频预览功能
- [ ] 添加视频编辑能力
- [ ] 支持批量生成
- [ ] 实现视频下载到本地

## 相关文件

- [`src/managers/AiWxVideoManager.py`](src/managers/AiWxVideoManager.py) - AI-WX 视频生成管理器
- [`config/aiwx_video_config.py`](config/aiwx_video_config.py) - AI-WX API 配置
- [`web/api/openai_video_api.py`](web/api/openai_video_api.py) - OpenAI 标准 API 路由
- [`test_aiwx_video_generation.py`](test_aiwx_video_generation.py) - 测试脚本

## 联系支持

如有问题，请联系：
- AI-WX API 文档：https://jyapi.ai-wx.cn
- 技术支持：查看项目日志文件

---

**最后更新：** 2026-01-12
**版本：** 1.0.0