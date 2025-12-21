"""
Web应用配置和基础工具
"""
import os
import sys

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
class FlaskConfig:
    """Flask应用配置"""
    SECRET_KEY = 'your-secret-key-here'  # 应该从配置文件读取
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    
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
    
    # 检查番茄自动上传模块
    try:
        import Chrome.automation.legacy.main_controller as autopush
        MODULE_STATUS["autopush_available"] = True
        logger.info("✅ 番茄自动上传模块(main_controller)加载成功")
    except ImportError as e:
        logger.warn(f"⚠️ 无法导入番茄自动上传模块(main_controller): {e}")
        try:
            # 备用：尝试导入autopush_legacy
            import Chrome.automation.legacy.autopush_legacy as autopush
            MODULE_STATUS["autopush_available"] = True
            logger.info("✅ 番茄自动上传模块(autopush_legacy)加载成功")
        except ImportError as e2:
            logger.warn(f"⚠️ 无法导入番茄自动上传模块(autopush_legacy): {e2}")
            MODULE_STATUS["autopush_available"] = False

    # 检查签约上传API
    try:
        from Chrome.automation.api.contract_api import contract_api
        MODULE_STATUS["contract_api_available"] = True
        logger.info("✅ 签约上传API加载成功")
    except ImportError as e:
        logger.warn(f"⚠️ 无法导入签约上传API: {e}")
        MODULE_STATUS["contract_api_available"] = False

    # 检查服务监控模块
    try:
        from Chrome.automation.monitoring.service_monitor import service_monitor
        MODULE_STATUS["service_monitor_available"] = True
        logger.info("✅ 服务监控模块加载成功")
    except ImportError as e:
        logger.warn(f"⚠️ 无法导入服务监控模块: {e}")
        MODULE_STATUS["service_monitor_available"] = False

# 初始化模块状态
check_module_availability()