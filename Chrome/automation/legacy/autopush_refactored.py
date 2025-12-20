"""
番茄小说自动发布系统 - 重构后的主入口文件
替代原有的超过4000行的 autopush_legacy.py 文件
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from main_controller import main

if __name__ == "__main__":
    main()