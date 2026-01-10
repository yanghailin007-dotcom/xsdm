#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的Web服务启动脚本
本地和服务器都使用相同的启动方式
"""

import os
import sys
import signal
import time
import platform
from pathlib import Path

# 添加项目根目录到系统路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("🚀 小说生成系统 - Web服务")
    print("=" * 70)
    print()
    print(f"📂 项目目录: {PROJECT_ROOT}")
    print(f"🐍 Python版本: {sys.version.split()[0]}")
    print(f"💻 操作系统: {platform.system()} {platform.release()}")
    print()

def check_dependencies():
    """检查依赖"""
    print("📦 检查依赖...")
    
    required = ['flask', 'gunicorn', 'eventlet']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} (缺失)")
            missing.append(pkg)
    
    if missing:
        print()
        print(f"⚠️  缺少依赖: {', '.join(missing)}")
        print("正在安装...")
        os.system(f"pip install {' '.join(missing)}")
    
    print()

def stop_existing_service(port=5000):
    """停止占用端口的进程"""
    print(f"🔍 检查端口 {port}...")
    
    try:
        if platform.system() == "Windows":
            # Windows
            import subprocess
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.split('\n')
            pids = set()
            
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5 and parts[-1].isdigit():
                        pids.add(parts[-1])
            
            if pids:
                print(f"  找到占用端口的进程: {pids}")
                for pid in pids:
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=3)
                        print(f"  ✓ 已终止进程 {pid}")
                    except:
                        print(f"  ✗ 终止进程 {pid} 失败")
            else:
                print("  ✓ 端口未被占用")
        else:
            # Linux/Mac
            import subprocess
            try:
                # 首先尝试使用fuser，如果不可用再用lsof
                result = subprocess.run(['fuser', '-k', f'{port}/tcp'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print("  ✓ 已使用fuser清理端口")
                    # 等待端口释放
                    time.sleep(2)
                else:
                    # fuser不可用，使用lsof
                    result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        print(f"  找到占用端口的进程: {pids}")
                        for pid in pids:
                            if pid.strip():
                                subprocess.run(['kill', '-9', pid.strip()], capture_output=True)
                                print(f"  ✓ 已终止进程 {pid}")
                        # 等待端口释放
                        time.sleep(2)
                    else:
                        print("  ✓ 端口未被占用")
            except:
                print("  ✓ 跳过端口检查")
    except Exception as e:
        print(f"  ⚠️  检查端口时出错: {e}")
    
    print()

def start_service():
    """启动服务"""
    print("🚀 启动Web服务...")
    print()
    
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    # 使用WSGI入口启动
    if platform.system() == "Windows":
        # Windows: 使用Python直接启动
        print("启动模式: 开发模式 (Windows)")
        print()
        exec(open('web/web_server_refactored.py').read())
    else:
        # Linux: 使用Gunicorn
        print("启动模式: 生产模式 (Linux)")
        print()
        print("执行命令:")
        print("  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app")
        print()
        
        os.system("gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app")

def signal_handler(signum, frame):
    """信号处理器"""
    print()
    print("🛑 收到停止信号，正在关闭服务...")
    print("=" * 70)
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 打印横幅
    print_banner()
    
    # 检查依赖
    check_dependencies()
    
    # 停止现有服务
    stop_existing_service()
    
    # 启动服务
    start_service()

if __name__ == '__main__':
    main()