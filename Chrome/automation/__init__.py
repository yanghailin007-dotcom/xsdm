"""
自动化模块
提供小说自动发布、签约管理等功能
"""

__version__ = "1.0.0"
__author__ = "自动化系统"

from .core.browser_manager import BrowserManager
from .core.novel_publisher import NovelPublisher
from .managers.contract_manager import ContractManager
from .utils.config_loader import ConfigLoader, get_config_loader, reload_config
from .utils.file_handler import FileHandler
from .utils.ui_helper import UIHelper

__all__ = [
    "BrowserManager",
    "NovelPublisher", 
    "ContractManager",
    "ConfigLoader",
    "get_config_loader",
    "reload_config",
    "FileHandler",
    "UIHelper"
]