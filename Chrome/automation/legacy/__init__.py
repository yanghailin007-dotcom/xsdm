# Legacy automation module
"""
番茄小说自动发布程序 - Legacy版本

这个模块包含旧版本的自动发布功能，包括：
- 自动发布章节
- 合同管理（已禁用）
- 浏览器自动化
"""

from .main_controller import main as refactored_main

# 为了保持向后兼容性，同时提供 main 和 refactored_main
main = refactored_main

# ContractManager 导入已禁用 - 签约管理功能暂时不需要
# try:
#     from .contract_manager_legacy import ContractManager
#     __all__ = ['main', 'refactored_main', 'ContractManager']
# except ImportError:
#     ContractManager = None
#     __all__ = ['main', 'refactored_main']

__all__ = ['main', 'refactored_main']
__version__ = '1.0.0'