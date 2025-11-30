"""工具函数模块 - 全局时间戳版本"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import time
from datetime import datetime
import builtins
from src.utils.logger import get_logger

# 保存原始的 print 函数
_original_print = builtins.print

def timestamp_print(*args, **kwargs):
    """带时间戳的全局 print 函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 处理第一个参数，确保时间戳在最前面
    if args:
        new_args = (f"[{timestamp}]",) + args
    else:
        new_args = (f"[{timestamp}]",)
    
    # 调用原始 print 函数
    _original_print(*new_args, **kwargs)

# 全局替换 print 函数
builtins.print = _original_print

# 可选：提供一个恢复原始 print 的函数
def restore_original_print():
    """恢复原始的 print 函数"""
    builtins.print = _original_print
    self.logger.info("已恢复原始 print 函数")

# 可选：提供一个临时禁用时间戳的函数
def disable_timestamp():
    """临时禁用时间戳"""
    builtins.print = _original_print

def enable_timestamp():
    """启用时间戳"""
    builtins.print = timestamp_print

# utils.py
def parse_chapter_range(range_str: str) -> tuple:
    """
    解析章节范围字符串，返回(start, end)元组。
    例如："1-100" -> (1, 100)
    如果解析失败，返回默认值(1, 100)。
    """
    try:
        if "-" in range_str:
            start, end = map(int, range_str.split("-"))
            return start, end
        else:
            # 如果只有单个数字，比如"100"，则start和end相同
            chapter = int(range_str)
            return chapter, chapter
    except (ValueError, AttributeError):
        return 1, 100

def is_chapter_in_range(chapter: int, range_str: str) -> bool:
    try:
        if "-" in range_str:
            start, end = map(int, range_str.split("-"))
            return start <= chapter <= end
        else:
            return chapter == int(range_str)
    except:
        return False