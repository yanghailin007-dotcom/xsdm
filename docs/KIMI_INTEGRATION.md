# Kimi (Moonshot AI) API 集成指南

## 简介

Kimi 是 Moonshot AI 推出的大语言模型，支持超长上下文（最高 200 万字），非常适合小说生成任务。

## 支持的模型

| 模型 | 上下文长度 | 适用场景 |
|------|-----------|---------|
| `moonshot-v1-8k` | 8K | 单章生成、短内容 |
| `moonshot-v1-32k` | 32K | 长章节、复杂情节 |
| `moonshot-v1-128k` | 128K | 大纲生成、批量章节 |

## 快速开始

### 1. 获取 API Key

1. 访问 [Moonshot AI 开放平台](https://platform.moonshot.cn/)
2. 注册账号并创建 API Key
3. 复制你的 API Key（格式：`sk-...`）

### 2. 配置 Kimi

**方式一：通过配置文件（推荐）**

编辑 `config/api_config.json`：

```json
{
  "api_endpoints": {
    "kimi": [
      {
        "name": "kimi-primary",
        "api_url": "https://api.moonshot.cn/v1/chat/completions",
        "api_key": "sk-your-api-key-here",
        "model": "moonshot-v1-32k",
        "priority": 1,
        "enabled": true
      }
    ]
  },
  "default_provider": "kimi"
}
```

**方式二：通过环境变量**

```bash
export KIMI_API_KEY="sk-your-api-key-here"
export KIMI_API_URL="https://api.moonshot.cn/v1/chat/completions"
export KIMI_MODEL="moonshot-v1-32k"
```

**方式三：通过 Web UI 配置**

1. 登录大文娱创作平台
2. 进入「模型配置」页面
3. 添加 Kimi 端点
4. 设置 API Key 和模型参数

### 3. 使用 Kimi 生成小说

```python
from src.core.APIClient import APIClient
from src.core.Config import Config

# 加载配置
config = Config()

# 创建 API 客户端
client = APIClient(config)

# 使用 Kimi 生成大纲
outline = client.call_api(
    system_prompt="你是一个专业的小说作家...",
    user_prompt="请生成一部玄幻小说的详细大纲...",
    provider="kimi",
    model_name="moonshot-v1-128k"
)

# 生成章节
chapter = client.call_api(
    system_prompt="根据大纲生成具体章节内容...",
    user_prompt="生成第1章...",
    provider="kimi",
    model_name="moonshot-v1-32k"
)
```

## 模型路由配置

为不同任务配置最优模型：

```json
{
  "model_routing": {
    "enabled": true,
    "routes": {
      "outline": "moonshot-v1-128k",    // 大纲用长上下文
      "chapter": "moonshot-v1-32k",     // 章节用中等上下文
      "content": "moonshot-v1-8k",      // 短内容用标准上下文
      "refinement": "moonshot-v1-32k"   // 润色用中等上下文
    }
  }
}
```

## 多 Kimi 账号配置（负载均衡）

如果你有多个 Kimi API Key，可以配置多个端点实现负载均衡：

```json
{
  "api_endpoints": {
    "kimi": [
      {
        "name": "kimi-account-1",
        "api_url": "https://api.moonshot.cn/v1/chat/completions",
        "api_key": "sk-account-1-key",
        "model": "moonshot-v1-32k",
        "priority": 1,
        "enabled": true
      },
      {
        "name": "kimi-account-2",
        "api_url": "https://api.moonshot.cn/v1/chat/completions",
        "api_key": "sk-account-2-key",
        "model": "moonshot-v1-32k",
        "priority": 2,
        "enabled": true
      }
    ]
  }
}
```

## Kimi 优势

1. **超长上下文**：最高支持 200 万字，适合长篇小说生成
2. **中文优化**：针对中文文学创作优化
3. **OpenAI 兼容**：使用标准 OpenAI API 格式
4. **稳定可靠**：企业级服务保障

## 故障排除

### API 调用失败

1. 检查 API Key 是否正确（以 `sk-` 开头）
2. 确认账户余额充足
3. 检查网络连接

### 响应缓慢

- 尝试切换到 `moonshot-v1-8k` 模型（速度更快）
- 检查 `max_tokens` 设置是否合理

### 内容截断

- 增加 `max_tokens` 值
- 切换到更大上下文的模型（如 128k）

## 参考链接

- [Kimi 官方文档](https://platform.moonshot.cn/docs)
- [API 参考](https://platform.moonshot.cn/docs/api-reference)
- [模型定价](https://platform.moonshot.cn/docs/pricing)
