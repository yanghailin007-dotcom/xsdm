"""
Web应用配置和基础工具
"""
import os
import sys
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装，跳过

def fix_console_encoding():
    """修复控制台编码问题"""
    try:
        # 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # 重新配置标准输出
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        if hasattr(sys.stdin, 'reconfigure'):
            sys.stdin.reconfigure(encoding='utf-8')
            
        # Windows 系统特殊处理
        if sys.platform == 'win32':
            import subprocess
            try:
                subprocess.run(['chcp', '65001'], shell=True, check=False, capture_output=True)
            except:
                pass
                
    except Exception:
        pass

# 在导入其他模块之前先修复编码
fix_console_encoding()

# 添加项目根目录到系统路径
def setup_project_path():
    """设置项目路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.append(project_root)

setup_project_path()

# 导入日志记录器
from src.utils.logger import get_logger
logger = get_logger("WebConfig")

# 导入项目配置
try:
    from config.config import BASE_DIR, CREATIVE_IDEAS_FILE
    logger.info("✅ 项目配置加载成功")
except ImportError as e:
    logger.error(f"❌ 项目配置加载失败: {e}")
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CREATIVE_IDEAS_FILE = os.path.join(BASE_DIR, "data", "creative_ideas", "novel_ideas.txt")

# Flask应用配置
import secrets

class FlaskConfig:
    """Flask应用配置"""
    # 优先从环境变量读取，否则生成随机密钥（每次重启会失效会话）
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = '0.0.0.0'
    PORT = 5000  #
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = 86400  # 默认1天（秒），记住我功能可延长至30天 
    
# 应用信息
APP_INFO = {
    "name": "小说生成Web服务",
    "version": "1.0.0",
    "description": "基于AI的小说生成和管理系统"
}

# 功能模块状态
MODULE_STATUS = {
    "autopush_available": False,
    "contract_api_available": False,
    "service_monitor_available": False
}

# 检查可选模块的可用性
def check_module_availability():
    """检查可选模块的可用性"""
    global MODULE_STATUS
    
    # 注：Chrome/ 目录已移除，相关功能迁移到 web/fanqie_uploader/
    # 以下旧模块标记为不可用，使用新架构替代
    
    MODULE_STATUS["autopush_available"] = False
    MODULE_STATUS["contract_api_available"] = False
    MODULE_STATUS["service_monitor_available"] = False
    
    logger.info("ℹ️ 旧版 Chrome 模块已移除，使用 web/fanqie_uploader/ 新架构")

# 初始化模块状态
check_module_availability()