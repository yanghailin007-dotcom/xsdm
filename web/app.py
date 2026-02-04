"""
Electron桌面应用的Flask启动入口
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入并启动Flask应用
from web.web_server_refactored import main

if __name__ == '__main__':
    main()
