"""
视频生成API配置
支持 Google Gemini 2.5 Flash Lite 等模型
"""
import os
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# Google AI Platform API 配置
# ============================================================================

# API密钥配置
# 直接在配置文件中设置API密钥
GOOGLE_AI_API_KEY = 'AQ.Ab8RN6I5dQ7J9KUmxSILiedrL8tFXMl7py6TtXS4WBpHqHzlVw'

# 也可以使用环境变量（可选）
# GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', GOOGLE_AI_API_KEY)

# API基础地址
GOOGLE_AI_BASE_URL = "https://aiplatform.googleapis.com/v1"

# 模型配置
# Gemini 2.5 Flash Lite - 轻量级快速模型
GOOGLE_MODEL_GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

# Gemini 2.5 Pro - 专业模型
GOOGLE_MODEL_GEMINI_2_5_PRO = "gemini-2.5-pro"

# Gemini 2.0 Flash - Flash模型
GOOGLE_MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"

# 默认使用的模型
DEFAULT_GOOGLE_MODEL = GOOGLE_MODEL_GEMINI_2_5_FLASH_LITE

# ============================================================================
# 视频生成端点配置
# ============================================================================

# 完整的API端点URL模板
# 使用方法: GOOGLE_VIDEO_GENERATION_URL.format(model=MODEL_NAME, api_key=API_KEY)
GOOGLE_VIDEO_GENERATION_URL = (
    GOOGLE_AI_BASE_URL + 
    "/publishers/google/models/{model}:streamGenerateContent?key={api_key}"
)

# 或者使用非流式端点
GOOGLE_VIDEO_GENERATION_URL_NON_STREAM = (
    GOOGLE_AI_BASE_URL +
    "/publishers/google/models/{model}:generateContent?key={api_key}"
)

# ============================================================================
# 视频生成参数配置
# ============================================================================

# 支持的视频分辨率
SUPPORTED_RESOLUTIONS = [
    "1920x1080",  # Full HD
    "1280x720",   # HD
    "1080x1920",  # Portrait
    "720x1280",   # Portrait HD
    "1080x1080",  # Square
]

# 支持的视频时长（秒）
SUPPORTED_DURATIONS = [5, 10, 15, 20, 30]

# 默认视频生成配置
DEFAULT_VIDEO_CONFIG = {
    "duration_seconds": 10,
    "resolution": "1920x1080",
    "aspect_ratio": "16:9",
    "fps": 24,
    "style": "realistic",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_videos": 1,
}

# ============================================================================
# 请求配置
# ============================================================================

REQUEST_CONFIG = {
    'timeout': 300,  # 5分钟超时
    'max_retries': 3,
    'retry_delay': 2,  # 重试延迟（秒）
    'default_headers': {
        "Content-Type": "application/json",
    }
}

# ============================================================================
# 文件保存配置
# ============================================================================

FILE_CONFIG = {
    'default_output_dir': 'generated_videos',
    'auto_create_dir': True,
    'filename_prefix': 'google_video_',
    'default_format': 'mp4',
    'thumbnail_format': 'jpg',
}

# ============================================================================
# 进度轮询配置
# ============================================================================

POLLING_CONFIG = {
    'enabled': True,           # 是否启用轮询
    'max_attempts': 60,        # 最大轮询次数
    'poll_interval': 2,        # 轮询间隔（秒）
    'progress_update_interval': 5,  # 进度更新间隔（秒）
}

# ============================================================================
# 辅助函数
# ============================================================================

def get_api_endpoint(model: Optional[str] = None, api_key: Optional[str] = None, stream: bool = True) -> str:
    """
    获取完整的API端点URL
    
    Args:
        model: 模型名称，默认使用 DEFAULT_GOOGLE_MODEL
        api_key: API密钥，默认使用 GOOGLE_AI_API_KEY
        stream: 是否使用流式端点
    
    Returns:
        完整的API URL
    """
    if model is None:
        model = DEFAULT_GOOGLE_MODEL
    if api_key is None:
        api_key = GOOGLE_AI_API_KEY
    
    if not api_key:
        raise ValueError("API密钥未设置！请在环境变量中设置 GOOGLE_AI_API_KEY 或在配置文件中直接设置")
    
    url_template = GOOGLE_VIDEO_GENERATION_URL if stream else GOOGLE_VIDEO_GENERATION_URL_NON_STREAM
    return url_template.format(model=model, api_key=api_key)


def validate_config() -> tuple[bool, str]:
    """
    验证配置是否完整
    
    Returns:
        (是否有效, 错误消息)
    """
    if not GOOGLE_AI_API_KEY:
        return False, "Google AI API Key 未设置"
    
    return True, "配置验证通过"


def get_request_headers() -> dict:
    """
    获取请求头
    
    Returns:
        请求头字典
    """
    headers = REQUEST_CONFIG['default_headers'].copy()
    return headers


# ============================================================================
# 配置初始化检查
# ============================================================================

if __name__ == "__main__":
    # 验证配置
    is_valid, message = validate_config()
    if is_valid:
        print(f"✅ {message}")
        print(f"📡 API端点: {get_api_endpoint()}")
        print(f"🎬 默认模型: {DEFAULT_GOOGLE_MODEL}")
    else:
        print(f"❌ {message}")
        print("⚠️  请在环境变量中设置 GOOGLE_AI_API_KEY")
        print("⚠️  或在此配置文件中直接设置 GOOGLE_AI_API_KEY")