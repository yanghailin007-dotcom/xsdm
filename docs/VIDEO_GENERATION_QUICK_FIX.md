# 视频生成连接错误 - 快速修复指南

## 🚨 问题摘要

你的视频生成失败是因为：

1. **API Key 格式错误** ❌
   - 当前: `AQ.Ab8RN6I5dQ7J9KUmxSILiedrL8tFXMl7py6TtXS4WBpHqHzlVw`
   - 这是**访问令牌**，不是**API密钥**
   - 正确的 Google AI API Key 应该以 `AIza` 开头

2. **Google Gemini 不支持视频生成** ⚠️
   - Gemini 是**文本生成模型**
   - 无法生成视频内容
   - 需要使用专业的视频生成API

---

## ⚡ 快速解决方案（3步）

### 步骤 1: 选择视频生成服务

**选项 A: Replicate（推荐 - 立即可用）**
```bash
# 安装
pip install replicate

# 注册获取 API Token
# 访问: https://replicate.com/account/api-tokens
export REPLICATE_API_TOKEN="r8_..."
```

**选项 B: Runway Gen-2**
```bash
# 注册获取 API Key
# 访问: https://runwayml.com/
export RUNWAY_API_KEY="rf_..."
```

**选项 C: OpenAI Sora（需申请权限）**
```bash
# 注册并申请 Sora 访问权限
# 访问: https://platform.openai.com/
export OPENAI_API_KEY="sk-..."
```

---

### 步骤 2: 创建新的配置文件

创建 `config/video_generation_services.py`:

```python
"""
视频生成服务配置
支持多个提供商
"""
import os
from typing import Optional

# ============================================================================
# Replicate 配置（推荐）
# ============================================================================
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_DEFAULT_MODEL = "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438"

# ============================================================================
# Runway 配置
# ============================================================================
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
RUNWAY_MODEL = "gen2"

# ============================================================================
# OpenAI Sora 配置
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VIDEO_MODEL = "sora-1.0"

# ============================================================================
# 默认服务选择
# ============================================================================
DEFAULT_VIDEO_SERVICE = "replicate"  # 可选: "runway", "openai"

def get_api_key(service: str = None) -> Optional[str]:
    """获取指定服务的 API Key"""
    service = service or DEFAULT_VIDEO_SERVICE
    
    if service == "replicate":
        return REPLICATE_API_TOKEN
    elif service == "runway":
        return RUNWAY_API_KEY
    elif service == "openai":
        return OPENAI_API_KEY
    return None

def validate_config(service: str = None) -> tuple[bool, str]:
    """验证配置"""
    service = service or DEFAULT_VIDEO_SERVICE
    api_key = get_api_key(service)
    
    if not api_key:
        return False, f"{service.upper()} API Key 未设置"
    
    return True, f"{service.upper()} 配置有效"

# 配置检查
if __name__ == "__main__":
    is_valid, msg = validate_config()
    print(f"✅ {msg}" if is_valid else f"❌ {msg}")
```

---

### 步骤 3: 测试配置

创建测试脚本 `test_video_generation_simple.py`:

```python
"""
简单的视频生成测试
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config.video_generation_services import (
    DEFAULT_VIDEO_SERVICE,
    get_api_key,
    validate_config
)

def test_replicate():
    """测试 Replicate 服务"""
    try:
        import replicate
        
        print("🧪 测试 Replicate 服务...")
        
        # 生成一个简单的视频
        output = replicate.run(
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={
                "cond_aug": 0.02,
                "decoding_t": 7,
                "input_image": "https://replicate.delivery/pbxt/JqKLLJhNRGLlUldvSKKbZLJGgFMhORnYcYkjd9DxQJXhLhR/rocket.png",
                "video_length": "14_frames_with_svd",
                "sizing_strategy": "maintain_aspect_ratio",
                "motion_bucket_id": 127,
                "frames_per_second": 6
            }
        )
        
        print(f"✅ 视频生成成功!")
        print(f"📹 视频URL: {output}")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_runway():
    """测试 Runway 服务"""
    print("🧪 测试 Runway 服务...")
    print("⚠️  Runway 需要单独的测试流程")
    print("📚 参考: https://dev.runwayml.com/")
    return False

def test_openai():
    """测试 OpenAI Sora 服务"""
    print("🧪 测试 OpenAI Sora 服务...")
    print("⚠️  Sora 需要申请访问权限")
    print("📚 参考: https://platform.openai.com/docs/guides/sora")
    return False

def main():
    """主测试函数"""
    print("="*60)
    print("🎬 视频生成服务测试")
    print("="*60)
    
    # 验证配置
    is_valid, msg = validate_config()
    print(f"\n配置验证: {msg}")
    
    if not is_valid:
        print("\n❌ 请先设置 API Key:")
        print("   export REPLICATE_API_TOKEN='r8_...'")
        print("   或")
        print("   export RUNWAY_API_KEY='rf_...'")
        print("   或")
        print("   export OPENAI_API_KEY='sk-...'")
        return
    
    # 根据服务测试
    service = DEFAULT_VIDEO_SERVICE
    print(f"\n🔧 测试服务: {service}")
    
    if service == "replicate":
        success = test_replicate()
    elif service == "runway":
        success = test_runway()
    elif service == "openai":
        success = test_openai()
    else:
        print(f"❌ 未知的服务: {service}")
        success = False
    
    if success:
        print("\n✅ 测试通过! 可以开始使用视频生成功能")
    else:
        print("\n❌ 测试失败，请检查配置")

if __name__ == "__main__":
    main()
```

---

## 🎯 立即运行

```bash
# 1. 设置环境变量（选择一个）
export REPLICATE_API_TOKEN="your_token_here"

# 2. 安装依赖
pip install replicate

# 3. 运行测试
python test_video_generation_simple.py
```

---

## 📝 更新现有代码

### 修改 `VideoGenerationManager.py`

在 `src/managers/VideoGenerationManager.py` 的 `_process_task` 方法中：

```python
def _process_task(self, task: VideoGenerationTask):
    """处理视频生成任务"""
    try:
        # 导入新的配置
        from config.video_generation_services import (
            DEFAULT_VIDEO_SERVICE,
            get_api_key
        )
        
        # 根据服务调用不同的API
        if DEFAULT_VIDEO_SERVICE == "replicate":
            return self._process_with_replicate(task)
        elif DEFAULT_VIDEO_SERVICE == "runway":
            return self._process_with_runway(task)
        elif DEFAULT_VIDEO_SERVICE == "openai":
            return self._process_with_openai(task)
        else:
            raise Exception(f"不支持的服务: {DEFAULT_VIDEO_SERVICE}")
            
    except Exception as e:
        self.logger.error(f"任务处理失败: {e}")
        task.fail(str(e))

def _process_with_replicate(self, task: VideoGenerationTask):
    """使用 Replicate 生成视频"""
    import replicate
    
    # 调用 Replicate API
    output = replicate.run(
        "stability-ai/stable-video-diffusion:...",
        input={
            "prompt": task.request.prompt,
            # ... 其他参数
        }
    )
    
    # 处理结果
    video_url = output
    # ... 创建 VideoResult
    
    return result
```

---

## 🔗 有用的链接

- **Replicate**: https://replicate.com/
- **Runway**: https://runwayml.com/
- **OpenAI Sora**: https://platform.openai.com/docs/guides/sora
- **完整诊断报告**: `docs/VIDEO_GENERATION_ERROR_DIAGNOSIS.md`

---

## ❓ 常见问题

### Q: 我应该使用哪个服务？
**A**: 
- **快速开始**: 使用 Replicate
- **生产环境**: 使用 Runway 或申请 OpenAI Sora
- **预算有限**: Replicate 成本最低

### Q: 当前配置还能用吗？
**A**: 不能。需要：
1. 获取正确的 API Key
2. 切换到支持视频生成的服务

### Q: Google Gemini 还能用吗？
**A**: 可以用于：
- 生成视频脚本描述
- 优化提示词
- 但不能直接生成视频

---

## 📞 需要帮助？

如果需要完整的集成代码，请参考：
- `docs/VIDEO_GENERATION_ARCHITECTURE.md`
- `docs/VIDEO_GENERATION_OPENAI_API_DESIGN.md`

---

**最后更新**: 2026-01-12  
**状态**: 🟡 等待配置正确的API服务