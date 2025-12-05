"""
启动 Web 服务脚本
Start Web Server Script
"""

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

# 获取当前目录
current_dir = Path(__file__).parent

def check_dependencies():
    """检查依赖"""
    print("🔍 检查依赖...")
    
    required_packages = ['flask', 'flask_cors']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (缺失)")
            missing.append(package)
    
    if missing:
        print("\n📦 安装缺失的依赖...")
        for package in missing:
            os.system(f'pip install {package}')
    
    print("✅ 依赖检查完成")

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 小说生成系统 - Web 服务启动")
    print("=" * 60)
    # 设置环境变量
    os.environ['USE_MOCK_API'] = 'false'  # 使用真实API进行测试
    # 检查依赖
    check_dependencies()
    
    # 获取web_server的正确路径
    web_server_path = current_dir.parent / "web" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"\n❌ 错误: 找不到 {web_server_path}")
        return
    
    # 启动 Web 服务
    print("\n📱 启动 Web 服务...")
    print("  • 前端地址: http://localhost:5000")
    print("  • API 地址: http://localhost:5000/api")
    print("\n⏳ 等待服务启动...")
    
    # 等待 Flask 启动
    time.sleep(2)
    
    # 在浏览器中打开
    try:
        webbrowser.open('http://localhost:5000')
        print("✓ 浏览器已打开\n")
    except Exception as e:
        print(f"⚠ 无法打开浏览器: {e}")
        print("请手动访问: http://localhost:5000\n")
    
    # 启动 Flask - 切换到项目根目录
    os.chdir(current_dir.parent)
    os.system(f'{sys.executable} {web_server_path}')

if __name__ == '__main__':
    main()
