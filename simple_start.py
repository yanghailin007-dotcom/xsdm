#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说生成系统 - 简单启动脚本（自动打开浏览器）
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path

def open_browser():
    """等待服务器启动后自动打开浏览器"""
    # 等待3秒让服务器启动
    time.sleep(3)
    
    try:
        # 尝试打开浏览器
        url = "http://localhost:5000"
        print(f"正在自动打开浏览器: {url}")
        
        # Windows系统使用start命令
        if os.name == 'nt':
            subprocess.run(['start', url], shell=True)
        else:
            # macOS和Linux系统
            subprocess.run(['open', url] if sys.platform == 'darwin' else ['xdg-open', url])
            
    except Exception as e:
        print(f"自动打开浏览器失败: {e}")
        print("请手动访问: http://localhost:5000")

def main():
    print("=" * 50)
    print("小说生成系统 - 启动服务")
    print("=" * 50)
    
    # 获取项目根目录
    project_root = Path(__file__).parent.absolute()
    print(f"项目目录: {project_root}")
    
    # 切换到项目根目录
    os.chdir(project_root)
    print(f"当前工作目录: {os.getcwd()}")
    
    # 设置环境变量
    os.environ['USE_MOCK_API'] = 'false'
    
    # 启动服务器
    print("\n正在启动Web服务器...")
    print("前端地址: http://localhost:5000")
    print("API 地址: http://localhost:5000/api")
    print("登录账号: admin / admin")
    print("按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    web_server_path = project_root / "web" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"错误: 找不到服务器文件 {web_server_path}")
        input("按回车键退出...")
        return
    
    # 启动浏览器打开线程
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        print("服务器启动中，即将自动打开浏览器...")
        # 直接运行服务器
        subprocess.run([sys.executable, str(web_server_path)])
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        input("按回车键退出...")

if __name__ == '__main__':
    main()