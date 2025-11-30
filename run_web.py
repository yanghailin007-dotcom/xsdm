"""
Web 服务启动脚本 - 正确版本
Correct Web Server Startup Script
"""

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    """启动Web服务器"""
    print("=" * 60)
    print("🚀 小说生成系统 - Web 服务启动")
    print("=" * 60)
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    # Web服务器路径
    web_server_path = project_root / "web" / "web_server.py"
    
    print(f"\n📁 项目根目录: {project_root}")
    print(f"📄 Web服务器: {web_server_path}")
    
    # 检查文件是否存在
    if not web_server_path.exists():
        print(f"\n❌ 错误: 找不到 {web_server_path}")
        print("请确保你在正确的目录中运行此脚本")
        sys.exit(1)
    
    # 检查依赖
    print("\n🔍 检查依赖...")
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'requests': 'requests'
    }
    
    missing = []
    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (缺失)")
            missing.append(package)
    
    if missing:
        print(f"\n📦 安装缺失的依赖: {', '.join(missing)}")
        for package in missing:
            print(f"  安装 {package}...")
            os.system(f'{sys.executable} -m pip install {package} -q')
        print("✅ 依赖安装完成")
    else:
        print("✅ 所有依赖已安装")
    
    # 启动Flask服务
    print("\n📱 启动 Web 服务...")
    print("  • 前端地址: http://localhost:5000")
    print("  • API 地址: http://localhost:5000/api")
    print("\n💡 按 Ctrl+C 停止服务\n")
    
    # 等待1秒后尝试打开浏览器
    time.sleep(1)
    try:
        webbrowser.open('http://localhost:5000')
        print("✓ 浏览器已打开\n")
    except Exception as e:
        print(f"⚠ 无法打开浏览器: {e}")
        print("请手动访问: http://localhost:5000\n")
    
    # 启动Flask应用 - 在项目根目录运行
    os.chdir(project_root)
    subprocess.run([sys.executable, str(web_server_path)])

if __name__ == '__main__':
    main()
