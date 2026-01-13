"""
AI-WX 视频生成API配置
https://jyapi.ai-wx.cn
"""
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# AI-WX API 配置
# ============================================================================

# API基础地址
AIWX_BASE_URL = "https://jyapi.ai-wx.cn"

# 视频生成端点 - 官方格式
AIWX_VIDEO_CREATE_URL = f"{AIWX_BASE_URL}/v1/video/create"

# 视频查询端点 - 标准查询接口
AIWX_VIDEO_QUERY_URL = f"{AIWX_BASE_URL}/v1/video/query"

# API密钥配置 - 使用官方提供的密钥
AIWX_API_KEY = 'sk-0dDn3ajqtCc0PTMmD045Ff7902774431Ad0304E396C856E7'

# 模型配置 - Veo 3.1 系列
AIWX_MODEL_VEO_3_1 = "veo_3_1"
AIWX_MODEL_VEO_3_1_FAST = "veo_3_1-fast"

# 默认使用的模型
DEFAULT_AIWX_MODEL = AIWX_MODEL_VEO_3_1_FAST

# ============================================================================
# 视频参数配置
# ============================================================================

# 支持的方向
SUPPORTED_ORIENTATIONS = {
    "portrait": "竖屏",
    "landscape": "横屏"
}

# 支持的尺寸
SUPPORTED_SIZES = {
    "small": "720p",  # 一般720p
    "large": "1080p"  # 高清
}

# 支持的宽高比
SUPPORTED_ASPECT_RATIOS = ["16:9", "9:16"]

# 支持的时长（秒）
SUPPORTED_DURATIONS = [10]  # 目前仅支持10秒

# 默认视频生成配置（官方格式）
DEFAULT_AIWX_VIDEO_CONFIG = {
    "model": DEFAULT_AIWX_MODEL,
    "orientation": "portrait",  # portrait 竖屏, landscape 横屏
    "size": "large",  # small 720p, large 1080p
    "duration": 15,  # 视频时长（秒）
    "watermark": False,  # 是否添加水印
    "private": True  # 是否私有
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
# 轮询配置
# ============================================================================

POLLING_CONFIG = {
    'enabled': True,
    'max_attempts': 60,  # 最大轮询次数
    'poll_interval': 5,  # 轮询间隔（秒）
    'progress_update_interval': 5,  # 进度更新间隔（秒）
}

# ============================================================================
# 文件保存配置
# ============================================================================

FILE_CONFIG = {
    'default_output_dir': 'generated_videos',
    'auto_create_dir': True,
    'filename_prefix': 'aiwx_video_',
    'default_format': 'mp4',
    'thumbnail_format': 'jpg',
}

# ============================================================================
# 辅助函数
# ============================================================================

def get_api_key() -> str:
    """
    获取API密钥
    
    Returns:
        API密钥字符串
        
    Raises:
        ValueError: 如果API密钥未设置
    """
    api_key = AIWX_API_KEY
    if not api_key:
        raise ValueError(
            "AI-WX API Key 未设置！\n"
            "请设置环境变量 AIWX_API_KEY\n"
            "示例: export AIWX_API_KEY='your_api_key'"
        )
    return api_key


def get_request_headers() -> dict:
    """
    获取请求头
    
    Returns:
        请求头字典，包含Authorization
    """
    headers = REQUEST_CONFIG['default_headers'].copy()
    api_key = get_api_key()
    # 直接使用 API Key，不加 Bearer 前缀
    headers['Authorization'] = api_key
    headers['User-Agent'] = 'Apifox/1.0.0 (https://apifox.com)'
    headers['Accept'] = '*/*'
    headers['Host'] = 'jyapi.ai-wx.cn'
    headers['Connection'] = 'keep-alive'
    return headers


def validate_config() -> tuple[bool, str]:
    """
    验证配置是否完整
    
    Returns:
        (是否有效, 错误消息)
    """
    try:
        get_api_key()
        return True, "配置验证通过"
    except ValueError as e:
        return False, str(e)


def get_video_url(task_id: str) -> str:
    """
    获取视频下载URL（如果API提供）
    
    Args:
        task_id: 任务ID
        
    Returns:
        视频URL
    """
    # 根据实际API文档调整
    return f"{AIWX_BASE_URL}/v1/video/result/{task_id}"


# ============================================================================
# 配置初始化检查
# ============================================================================

if __name__ == "__main__":
    # 验证配置
    is_valid, message = validate_config()
    if is_valid:
        print(f"✅ {message}")
        print(f"📡 API端点: {AIWX_VIDEO_CREATE_URL}")
        print(f"🎬 默认模型: {DEFAULT_AIWX_MODEL}")
        print(f"⚙️  默认配置: {DEFAULT_AIWX_VIDEO_CONFIG}")
    else:
        print(f"❌ {message}")
        print("⚠️  请在环境变量中设置 AIWX_API_KEY")