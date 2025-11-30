"""统一日志系统 - Unified Logging System

标准化所有模块的日志输出，支持日志级别、时间戳、模块名称标识
支持本地文件持久化和控制台输出
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional


class LogLevel:
    """日志级别常量"""
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3
    
    NAMES = {
        0: "DEBUG",
        1: "INFO",
        2: "WARN",
        3: "ERROR"
    }
    
    ICONS = {
        0: "[D]",
        1: "[I]",
        2: "[W]",
        3: "[E]"
    }

class Logger:
    """统一日志记录器
    
    使用示例:
        logger = Logger("NovelGenerator")
        logger.info("开始生成章节")
        logger.debug("详细的调试信息")
        logger.warn("可能有问题的情况")
        logger.error("发生了错误")
    """
    
    # 类级别配置 - 所有实例共享
    _global_level = LogLevel.INFO
    _log_file: Optional[Path] = None
    _use_console = True
    _use_file = False
    
    def __init__(self, module_name: str, level: int = None):
        """初始化日志记录器
        
        Args:
            module_name: 模块名称 (用于标识日志来源)
            level: 日志级别 (0=DEBUG, 1=INFO, 2=WARN, 3=ERROR)
                  如果为 None，使用全局日志级别
        """
        self.module = module_name
        self._level = level if level is not None else self._global_level
    
    @classmethod
    def set_global_level(cls, level: int):
        """设置全局日志级别
        
        Args:
            level: 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR
        """
        if 0 <= level <= 3:
            cls._global_level = level
    
    @classmethod
    def enable_file_logging(cls, log_file: str = "logs/novel_generation.log"):
        """启用文件日志
        
        Args:
            log_file: 日志文件路径
        """
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cls._log_file = log_path
        cls._use_file = True
    
    @classmethod
    def disable_file_logging(cls):
        """禁用文件日志"""
        cls._use_file = False
    
    @classmethod
    def set_console_output(cls, enabled: bool):
        """设置是否输出到控制台
        
        Args:
            enabled: True 为启用，False 为禁用
        """
        cls._use_console = enabled
    
    def _should_log(self, level: int) -> bool:
        """判断是否应该记录此日志
        
        Args:
            level: 要记录的日志级别
            
        Returns:
            True 如果应该记录，False 否则
        """
        effective_level = self._level if self._level != self._global_level else self._global_level
        return level >= effective_level
    
    def _format_message(self, level: int, message: str) -> str:
        """格式化日志消息
        
        格式: [TIMESTAMP] [MODULE] [LEVEL] [ICON] message
        示例: 2025-01-15 14:32:45 [NovelGenerator] [INFO] ℹ️  章节生成完成
        
        Args:
            level: 日志级别
            message: 日志消息
            
        Returns:
            格式化后的日志字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_name = LogLevel.NAMES.get(level, "UNKNOWN")
        icon = LogLevel.ICONS.get(level, "")
        
        # 构建日志格式
        log_line = f"[{timestamp}] [{self.module:20}] [{level_name:5}] {icon} {message}"
        return log_line
    
    def _safe_print(self, message: str, output_stream):
        """安全的打印方法，处理编码问题"""
        try:
            # 直接打印到输出流
            print(message, file=output_stream)
            return True
        except (UnicodeEncodeError, OSError):
            # 回退: 移除特殊字符后打印
            try:
                # 使用更安全的编码方式
                safe_line = message.encode('utf-8', errors='ignore').decode('utf-8')
                if safe_line.strip():  # 只有当清理后还有内容时才打印
                    print(safe_line, file=output_stream)
                    return True
            except (UnicodeEncodeError, OSError):
                # 进一步回退: 使用ASCII
                try:
                    safe_line = message.encode('ascii', 'ignore').decode('ascii')
                    if safe_line.strip():
                        print(safe_line, file=output_stream)
                        return True
                except OSError:
                    # 如果仍然失败，尝试最基本的输出
                    try:
                        print(f"[{self.module}] LOG: Output failed", file=output_stream)
                        return True
                    except OSError:
                        pass  # 静默忽略
        return False

    def _output(self, log_line: str, error: bool = False):
        """输出日志到控制台和文件

        Args:
            log_line: 格式化的日志行
            error: 是否输出到 stderr (错误日志)
        """
        if self._use_console:
            output_stream = sys.stderr if error else sys.stdout
            self._safe_print(log_line, output_stream)

        if self._use_file and self._log_file:
            try:
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line + '\n')
            except Exception as e:
                # 文件写入失败，不中断主流程，仅输出到控制台
                if self._use_console:
                    try:
                        print(f"[WARNING] 无法写入日志文件: {e}", file=sys.stderr)
                    except UnicodeEncodeError:
                        # 如果警告也无法输出，则忽略
                        pass
    
    def debug(self, message: str):
        """记录调试信息
        
        Args:
            message: 日志消息
        """
        if self._should_log(LogLevel.DEBUG):
            log_line = self._format_message(LogLevel.DEBUG, message)
            self._output(log_line)
    
    def info(self, message: str):
        """记录普通信息
        
        Args:
            message: 日志消息
        """
        if self._should_log(LogLevel.INFO):
            log_line = self._format_message(LogLevel.INFO, message)
            self._output(log_line)
    
    def warn(self, message: str):
        """记录警告信息
        
        Args:
            message: 日志消息
        """
        if self._should_log(LogLevel.WARN):
            log_line = self._format_message(LogLevel.WARN, message)
            self._output(log_line, error=True)
    
    def safe_print_traceback(self):
        """安全地打印traceback，处理编码问题"""
        try:
            # 获取traceback信息为字符串
            tb_str = traceback.format_exc()

            # 尝试安全打印
            if not self._safe_print(tb_str, sys.stderr):
                # 如果直接打印失败，尝试逐行清理后打印
                lines = tb_str.split('\n')
                for line in lines:
                    if line.strip():  # 只处理非空行
                        try:
                            safe_line = line.encode('ascii', 'ignore').decode('ascii')
                            if safe_line.strip():
                                print(safe_line, file=sys.stderr)
                        except (UnicodeEncodeError, OSError):
                            pass  # 静默忽略无法打印的行
        except Exception:
            # 如果连格式化都失败了，打印简单错误信息
            try:
                print(f"[{self.module}] ERROR: Exception occurred (traceback output failed)", file=sys.stderr)
            except (UnicodeEncodeError, OSError):
                pass  # 彻底静默

    def error(self, message: str, exception: Exception = None):
        """记录错误信息

        Args:
            message: 日志消息
            exception: 可选的异常对象，会在日志中打印堆栈跟踪
        """
        if self._should_log(LogLevel.ERROR):
            if exception:
                message = f"{message} | 异常: {type(exception).__name__}: {str(exception)}"
            log_line = self._format_message(LogLevel.ERROR, message)
            self._output(log_line, error=True)
    
    @classmethod
    def get_log_file_path(cls) -> Optional[Path]:
        """获取当前日志文件路径
        
        Returns:
            日志文件路径，如果未启用文件日志则返回 None
        """
        return cls._log_file if cls._use_file else None


# ============================================================================
# 便利函数 - 不需要创建 Logger 实例时可直接使用
# ============================================================================

def get_logger(module_name: str, level: int = None) -> Logger:
    """获取指定模块的日志记录器
    
    Args:
        module_name: 模块名称
        level: 日志级别 (可选)
        
    Returns:
        Logger 实例
    """
    return Logger(module_name, level)


# ============================================================================
# 初始化示例配置
# ============================================================================

def setup_logging(level: int = LogLevel.INFO, enable_file: bool = False, 
                  log_file: str = "logs/novel_generation.log"):
    """一次性设置所有日志配置
    
    Args:
        level: 全局日志级别
        enable_file: 是否启用文件日志
        log_file: 日志文件路径
        
    示例:
        setup_logging(level=LogLevel.INFO, enable_file=True)
        logger = get_logger("MyModule")
        logger.info("开始处理")
    """
    Logger.set_global_level(level)
    Logger.set_console_output(True)
    
    if enable_file:
        Logger.enable_file_logging(log_file)
    else:
        Logger.disable_file_logging()


# ============================================================================
# 模块级别的便利日志记录器 (用于未重构的模块)
# ============================================================================

# 默认模块记录器
_default_logger = Logger("DEFAULT")

def log_debug(msg: str):
    """全局调试日志"""
    _default_logger.debug(msg)

def log_info(msg: str):
    """全局普通日志"""
    _default_logger.info(msg)

def log_warn(msg: str):
    """全局警告日志"""
    _default_logger.warn(msg)

def log_error(msg: str, exception: Exception = None):
    """全局错误日志"""
    _default_logger.error(msg, exception)
