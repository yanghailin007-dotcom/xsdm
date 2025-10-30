import os

# API密钥配置（优先级：环境变量 > 配置文件）
ARK_API_KEY = os.getenv('ARK_API_KEY', '88117df2-5ce5-4d75-8224-01695231951f')  # 替换为您的实际API密钥

# API端点
API_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 默认模型配置
DEFAULT_MODEL = "doubao-seedream-4-0-250828"
DEFAULT_SIZE = "1K"

# 请求配置
REQUEST_CONFIG = {
    'timeout': 60,
    'max_retries': 3,
    'default_headers': {
        "Content-Type": "application/json"
    }
}

# 支持的图片尺寸
SUPPORTED_SIZES = ['1K', '2K']

# 图像质量设置
QUALITY_SETTINGS = {
    'high': {
        'sequential_image_generation': 'disabled',
        'watermark': True
    },
    'fast': {
        'sequential_image_generation': 'disabled', 
        'watermark': False
    }
}

# 文件保存配置
FILE_CONFIG = {
    'default_output_dir': 'generated_images',
    'auto_create_dir': True,
    'filename_prefix': 'doubao_',
    'default_format': 'jpg'
}