"""
API 密钥和 URL 配置文件
本文件包含所有 API 密钥和端点 URL

⚠️ 安全警告 ⚠️
- 生产环境必须设置对应的环境变量，不要使用默认值
- 默认值仅用于本地开发环境
- 确保此文件不被提交到版本控制（已在 .gitignore 中）

必要的环境变量：
- GEMINI_API_KEY: Gemini API 密钥
- DEEPSEEK_API_KEY: DeepSeek API 密钥

可选的环境变量：
- GEMINI_BASE_URL: Gemini API 基础 URL
- DEEPSEEK_BASE_URL: DeepSeek API 基础 URL
- YUANBAO_API_KEY: Yuanbao API 密钥
- AIWX_API_KEY: AI-WX 视频生成 API 密钥
- ARK_API_KEY: 豆包 API 密钥
- NANOBANANA_XIAOCHUANG_KEY: NanoBanana 图像生成密钥
- MINIMAX_TTS_API_KEY: MiniMax TTS API 密钥
"""
import os

# ============================================================================
# API 密钥配置 - 优先读取环境变量，否则使用硬编码值（本地开发用）
# ============================================================================

# Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'sk-zwgxnnUut1E7zJMxXjCAQ3zeUefeM8tm9HYQCY50lVTM53CD')
GEMINI_BASE_URL = os.getenv('GEMINI_BASE_URL', 'https://newapi.xiaochuang.cc/v1/chat/completions')

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1/chat/completions')

# Yuanbao API
YUANBAO_API_KEY = os.getenv('YUANBAO_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b')
YUANBAO_BASE_URL = os.getenv('YUANBAO_BASE_URL', 'https://api.deepseek.com/v1/chat/completions')

# ============================================================================
# 图像生成 API
# ============================================================================

# NanoBanana - Xiaochuang 供应商
NANOBANANA_XIAOCHUANG_KEY = os.getenv('NANOBANANA_XIAOCHUANG_KEY', 'sk-i7g2FApDs7X5cdIgpjDMcgIbCCaACIfgzmkIocX2xZBbqnSH')
NANOBANANA_XIAOCHUANG_URL = 'http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent'

# NanoBanana - AI-WX 供应商
NANOBANANA_AIWX_KEY = os.getenv('NANOBANANA_AIWX_KEY', 'sk-zO9XLgXnznOLwFEM2cE7543942F94dFa92EcBe4a8bF483C8')
NANOBANANA_AIWX_URL = 'https://jyapi.ai-wx.cn/v1/images/generations'

# ============================================================================
# 视频生成 API
# ============================================================================

# AI-WX 视频生成
AIWX_API_KEY = os.getenv('AIWX_API_KEY', 'sk-0dDn3ajqtCc0PTMmD045Ff7902774431Ad0304E396C856E7')
AIWX_BASE_URL = 'https://jyapi.ai-wx.cn'
AIWX_VIDEO_CREATE_URL = f'{AIWX_BASE_URL}/v1/video/create'
AIWX_VIDEO_QUERY_URL = f'{AIWX_BASE_URL}/v1/video/query'

# ============================================================================
# 音频合成 API
# ============================================================================

# MiniMax TTS
MINIMAX_TTS_API_KEY = os.getenv('MINIMAX_TTS_API_KEY', 'sk-api-aomH3HEEi6b-QcE_ZdQHJJ2gHqKmuoI_0MLPls7bBhKusdA3ief8Zar6x2IHOj7Cjuv7vvGVFnnwYL1czCY7iKOguMt0YAV-2JPoxjPXShcUL8u1zQLa8eo')
MINIMAX_TTS_GROUP_ID = '2017772342268141667'

# ============================================================================
# 豆包 API
# ============================================================================

ARK_API_KEY = os.getenv('ARK_API_KEY', '')
ARK_BASE_URL = os.getenv('ARK_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')
ARK_MODEL_ID = os.getenv('ARK_MODEL_ID', '')

# ============================================================================
# 模型配置
# ============================================================================

MODELS = {
    'gemini': 'gemini-3-pro-preview',
    'deepseek': 'deepseek-reasoner',
    'yuanbao': 'deepseek-reasoner',
}

# ============================================================================
# 验证函数
# ============================================================================

def validate_api_keys():
    """验证必要的 API 密钥是否已配置"""
    required_keys = {
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY,
    }

    missing_keys = [key for key, value in required_keys.items() if not value]

    if missing_keys:
        return False, f"缺少必要的 API 密钥: {', '.join(missing_keys)}"

    return True, "所有必要的 API 密钥已配置"
