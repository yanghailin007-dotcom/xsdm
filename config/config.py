import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 尝试加载环境变量（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except:
    pass

# 创意文件路径
CREATIVE_IDEAS_FILE = BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt"

from src.utils.logger import get_logger
"""AI 模型配置文件 - 仅包含模型相关配置"""

CONFIG = {
    # ============================================================
    # 🔥 API 端点池配置（支持故障转移和优先级调度）
    # ============================================================
    "api_endpoints": {
        "gemini": [
            {
                "name": "lemon-api",
                "api_url": "https://new.lemonapi.site/v1/chat/completions",
                "api_key": os.getenv('LEMON_API_KEY', 'sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg'),
                "model": "[L]gemini-3.1-pro-preview",
                "model1": "[L]gemini-3-flash-preview", 
                "assessment": "[L]gemini-2.5-flash",
                "priority": 3,
                "enabled": True,
                "timeout": 300,
                "max_retries": 3,
                "discount_rate": 80,
                "stream": False
            },
            {
                "name": "aiberm",
                "api_url": "https://aiberm.com/v1/chat/completions",
                "api_key": os.getenv('AIBERM_API_KEY', 'sk-dWu7JFD69zTYeSLZiWV8OQYBjQ2IoJlQCmSo3f963ArGEAju'),
                "model": "google/gemini-3-flash",
                "assessment": "google/gemini-2.5-flash",
                "priority": 1,
                "enabled": True,
                "timeout": 300,
                "max_retries": 3,
                "discount_rate": 150,
                "stream": True
            },
            {
                "name": "aiapi-world",
                "api_url": "https://aiapi.world/v1/chat/completions",
                "api_key": os.getenv('AIAPI_WORLD_KEY', 'sk-h0obXbJ7NRUmu9ic9mgOYuFiK7vmTSENhDEGk3mJIPHlLm0L'),
                "model": "gemini-3-flash-preview-thinking",
                "assessment": "gemini-2.5-flash",
                "priority": 1,
                "enabled": True,
                "timeout": 300,
                "max_retries": 3,
                "discount_rate": 100,
                "stream": False
            },
            {
                "name": "xiaochuang-backup",
                "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
                "api_key": os.getenv('GEMINI_API_KEY', 'sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw'),
                "model": "gemini-3-pro-preview",
                "assessment": "gemini-2.5-flash",
                "priority": 2,
                "enabled": True,
                "timeout": 300,
                "max_retries": 3,
                "discount_rate": 100,
                "stream": False
            }
        ],
        "deepseek": [
            {
                "name": "deepseek-official",
                "api_url": "https://api.deepseek.com/v1/chat/completions",
                "api_key": os.getenv('DEEPSEEK_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b'),
                "model": "deepseek-reasoner",
                "priority": 1,
                "enabled": True,
                "timeout": 120,
                "max_retries": 3,
                "discount_rate": 100,
                "stream": False
            }
        ],
        "kimi": [
            {
                "name": "kimi-k2.5-primary",
                "api_url": "https://api.moonshot.cn/v1/chat/completions",
                "api_key": os.getenv('KIMI_API_KEY', 'sk-uVuGTs0D7Oz8UlSfFO6k8TJDw8Ag6EiTvaqu0lG8TyU3nhyk'),
                "model": "kimi-k2.5",
                "priority": 1,
                "enabled": True,  # 🔥 设置为 False 禁用此端点
                "timeout": 300,
                "max_retries": 3,
                "discount_rate": 85,
                "stream": True
            }
        ]
    },
    # 🔥 Provider 优先级配置（自动选择 + 故障转移）
    # 1. 当 default_provider=None 时，按此列表自动选择第一个可用的 provider
    # 2. 当高优先级 provider 的所有端点都失败时，自动切换到低优先级
    "provider_priority": ["gemini", "kimi", "deepseek"],  # 优先级: kimi > gemini > deepseek
    
    # 🔥 Provider 故障转移配置
    "provider_failover": {
        "enabled": True,           # 启用跨 provider 故障转移
        "max_failures": 2,         # 一个 provider 连续失败多少次后切换（降低阈值更快切换）
        "failure_window": 300,     # 失败计数时间窗口（秒）
        "cooldown": 30             # 切换后冷却时间（秒）
    },
    
    # 保底模型配置（向后兼容）
    "fallback": {
        "enabled": False,
        "primary_provider": "gemini",
        "fallback_provider": "deepseek"
    },
    
    # 多轮对话优化（仅 Kimi 支持）
    "use_conversation_mode_for_kimi": True,
    
    # 默认生成参数
    "defaults": {
        "temperature": 0.9,  # 提高温度以增加内容多样性
        "max_tokens": 60000,
        "total_chapters": 200,
        "max_retries": 3,
        "chapters_per_batch": 3,
        "max_optimization_attempts": 1,
        "json_retries": 3
    }
}
