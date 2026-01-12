# 视频生成连接错误诊断报告

**日期**: 2026-01-12  
**错误**: `ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。')`

---

## 🔴 问题根源分析

### 1. API Key 格式错误 ❌

**当前配置**:
```python
GOOGLE_AI_API_KEY = 'AQ.Ab8RN6I5dQ7J9KUmxSILiedrL8tFXMl7py6TtXS4WBpHqHzlVw'
```

**问题**:
- 当前API Key以 `AQ.` 开头
- 这是一个**访问令牌（Access Token）**，不是**API密钥（API Key）**
- 标准 Google AI API Key 应该以 `AIza` 开头

**影响**:
- Google AI Platform 无法识别此凭证
- 服务器直接拒绝连接，导致 `ConnectionResetError(10054)`

---

### 2. Google Gemini 不支持视频生成 ⚠️

**关键发现**:
- Google Gemini API 主要用于**文本生成**
- **不提供视频生成功能**
- 当前代码尝试使用 Gemini API 生成视频，这是不可能的

**日志证据**:
```
[2026-01-12 14:04:27] 📤 发送请求到: 
https://aiplatform.googleapis.com/v1/publishers/google/models/video-model:streamGenerateContent
```

问题：
- 使用了不存在的模型名称 `video-model`
- 即使有正确的API Key，此端点也无法生成视频

---

## 📋 完整错误链

```
1. 用户发起视频生成请求
   ↓
2. VideoGenerationManager 使用错误的API Key (AQ.xxx)
   ↓
3. 请求发送到 Google AI Platform (错误的服务)
   ↓
4. Google服务器无法识别凭证
   ↓
5. 服务器主动关闭连接 (ConnectionResetError 10054)
   ↓
6. 任务失败: "远程主机强迫关闭了一个现有的连接"
```

---

## ✅ 解决方案

### 方案 A: 使用专业的视频生成服务（推荐）

#### 1. OpenAI Sora API
```python
# 配置示例
OPENAI_API_KEY = "sk-..."  # 标准OpenAI API Key
OPENAI_VIDEO_MODEL = "sora-1.0"
OPENAI_VIDEO_ENDPOINT = "https://api.openai.com/v1/videos/generations"
```

**优点**:
- 官方支持，稳定性高
- 视频质量优秀
- 文档完善

**缺点**:
- 需要申请访问权限
- 成本较高

#### 2. Runway Gen-2 API
```python
# 配置示例
RUNWAY_API_KEY = "rf_..."  # Runway API Key
RUNWAY_MODEL = "gen2"
RUNWAY_ENDPOINT = "https://api.runwayml.com/v1/generate"
```

**优点**:
- 专业的视频生成
- 支持多种风格
- 可靠的服务

#### 3. Replicate Video APIs
```python
# 配置示例
REPLICATE_API_TOKEN = "r8_..."
REPLICATE_MODELS = {
    "stability-ai/stable-video-diffusion": "稳定扩散视频",
    "anotherjesse/zeroscope-v2-xl": "高质量视频"
}
```

**优点**:
- 多种模型选择
- 灵活的定价
- 易于集成

---

### 方案 B: 使用 Google Gemini + 视频API组合

```python
# 工作流程
1. 使用 Gemini API 生成详细的视频脚本描述
2. 将描述传递给专业视频生成API（如 Runway）
3. 返回生成的视频

# 代码示例
def generate_video_with_gemini(prompt: str):
    # 步骤1: 使用 Gemini 生成详细描述
    gemini_response = call_gemini_api(prompt)
    detailed_prompt = gemini_response.text
    
    # 步骤2: 使用专业API生成视频
    video_url = call_video_api(detailed_prompt)
    return video_url
```

---

## 🔧 立即修复步骤

### 步骤 1: 获取正确的API Key

**对于 OpenAI Sora**:
1. 访问: https://platform.openai.com/
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的API Key（格式: `sk-...`）
5. 申请 Sora 访问权限

**对于 Runway**:
1. 访问: https://runwayml.com/
2. 注册开发者账号
3. 获取API Key（格式: `rf_...`）

### 步骤 2: 更新配置文件

创建 `config/videoconfig_openai.py`:
```python
"""
OpenAI 视频生成配置
"""
OPENAI_API_KEY = "sk-..."  # 替换为你的API Key
OPENAI_VIDEO_MODEL = "sora-1.0"
OPENAI_VIDEO_ENDPOINT = "https://api.openai.com/v1/videos/generations"
```

### 步骤 3: 修改 VideoGenerationManager

更新 `src/managers/VideoGenerationManager.py`:
```python
# 在 _process_task 方法中
def _process_task(self, task: VideoGenerationTask):
    # 使用 OpenAI API 而非 Google AI
    api_url = "https://api.openai.com/v1/videos/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sora-1.0",
        "prompt": task.request.prompt,
        "duration": task.request.generation_config.duration_seconds
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    # ... 处理响应
```

---

## 📊 成本对比

| 服务 | 成本（每分钟视频） | 免费额度 |
|------|------------------|---------|
| OpenAI Sora | ~$0.20 | 100分钟/月 |
| Runway Gen-2 | ~$0.05 | 50分钟/月 |
| Replicate | $0.01-0.10 | 取决于模型 |

---

## 🎯 推荐方案

基于你的项目需求，我推荐：

**短期方案**（立即可用）:
1. 使用 **Replicate** 上的 Stable Video Diffusion
2. 成本低，易于集成
3. 视频质量可接受

**长期方案**（生产环境）:
1. 申请 **OpenAI Sora** 访问权限
2. 使用 **Runway Gen-2** 作为备选
3. 实现多提供商切换逻辑

---

## 📝 配置文件更新示例

```python
# config/videoconfig.py

# ============================================================================
# 视频生成服务配置
# ============================================================================

# 主要服务
VIDEO_SERVICE = "replicate"  # 可选: "openai", "runway", "replicate"

# OpenAI Sora 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VIDEO_MODEL = "sora-1.0"
OPENAI_VIDEO_ENDPOINT = "https://api.openai.com/v1/videos/generations"

# Runway 配置
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
RUNWAY_MODEL = "gen2"
RUNWAY_ENDPOINT = "https://api.runwayml.com/v1/generate"

# Replicate 配置
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_MODELS = {
    "stable-video": "stability-ai/stable-video-diffusion",
    "zeroscope": "anotherjesse/zeroscope-v2-xl"
}

# ============================================================================
# Google Gemini 配置（仅用于文本生成）
# ============================================================================

# Google AI API Key（用于 Gemini 文本生成）
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
GOOGLE_TEXT_MODEL = "gemini-2.5-flash-lite"
```

---

## 🚀 快速开始

### 1. 测试 Replicate 集成

```bash
# 安装依赖
pip install replicate

# 设置环境变量
export REPLICATE_API_TOKEN="r8_..."

# 运行测试
python test_video_generation_replicate.py
```

### 2. 测试 OpenAI 集成

```bash
# 安装依赖
pip install openai

# 设置环境变量
export OPENAI_API_KEY="sk-..."

# 运行测试
python test_video_generation_openai.py
```

---

## 📚 相关资源

- [OpenAI Sora 文档](https://platform.openai.com/docs/guides/sora)
- [Runway API 文档](https://dev.runwayml.com/)
- [Replicate Python SDK](https://github.com/replicate/replicate-python)
- [Stable Video Diffusion](https://stability.ai/)

---

## ⚠️ 重要提醒

1. **不要使用当前的 Google API Key**: 它是一个访问令牌，不是API密钥
2. **Google Gemini 无法生成视频**: 它是文本生成模型
3. **使用专业的视频生成服务**: OpenAI Sora, Runway, 或 Replicate
4. **注意API成本**: 视频生成比文本生成贵得多
5. **实现速率限制**: 避免超出API配额

---

## 📞 需要帮助？

如果需要帮助集成任何视频生成服务，请参考以下文档：
- `docs/VIDEO_GENERATION_OPENAI_API_DESIGN.md`
- `docs/VIDEO_GENERATION_ARCHITECTURE.md`
- `docs/VIDEO_GENERATION_QUICK_START.md`

---

**最后更新**: 2026-01-12  
**状态**: 🟡 需要配置正确的API服务