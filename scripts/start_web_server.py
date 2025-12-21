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

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import locale
    import codecs
    # 尝试设置控制台编码
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except:
        pass

# 获取当前目录
current_dir = Path(__file__).parent

def check_dependencies():
    """检查依赖"""
    print("检查依赖...")
    
    required_packages = ['flask', 'flask_cors']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [X] {package} (缺失)")
            missing.append(package)
    
    if missing:
        print("\n安装缺失的依赖...")
        for package in missing:
            os.system(f'pip install {package}')
    
    print("依赖检查完成")

def stop_port_5000():
    """清理端口5000的进程"""
    try:
        print("\n清理端口5000...")
        
        # 查找占用端口5000的进程
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')

        pids = []
        for line in lines:
            if ':5000' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid not in pids:
                        pids.append(pid)

        if not pids:
            print("  [OK] 没有找到占用端口5000的进程")
            return

        print(f"  [INFO] 找到占用端口5000的进程: {pids}")

        # 杀死进程
        for pid in pids:
            print(f"  [KILL] 终止进程 {pid}...")
            subprocess.run(['taskkill', '/F', '/PID', pid])
            print(f"  [OK] 进程 {pid} 已终止")

        print("  [OK] 端口5000清理完成")

    except Exception as e:
        print(f"  [WARNING] 清理端口时出错: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("小说生成系统 - Web 服务启动")
    print("=" * 60)
    # 设置环境变量
    os.environ['USE_MOCK_API'] = 'false'  # 使用真实API进行测试
    # 检查依赖
    check_dependencies()
    
    # 清理端口5000
    stop_port_5000()
    
    # 等待端口释放
    time.sleep(1)
    
    # 获取web_server的正确路径（使用重构后的版本）
    web_server_path = current_dir.parent / "web" / "web_server_refactored.py"
    
    if not web_server_path.exists():
        print(f"\n❌ 错误: 找不到 {web_server_path}")
        # 如果重构版本不存在，尝试使用原版本
        web_server_path = current_dir.parent / "web" / "web_server.py"
        if not web_server_path.exists():
            print(f"\n❌ 错误: 找不到 {web_server_path}")
            return
        else:
            print(f"\n📋 使用原版本: {web_server_path}")
    else:
        print(f"\n📋 使用重构版本: {web_server_path}")
    
    # 启动 Web 服务
    print("\n启动 Web 服务...")
    print("  • 前端地址: http://localhost:5000")
    print("  • API 地址: http://localhost:5000/api")
    print("\n⏳ 等待服务启动...")
    
    # 等待 Flask 启动
    time.sleep(2)
    
    # 在浏览器中打开
    try:
        webbrowser.open('http://localhost:5000')
        print("[OK] 浏览器已打开\n")
    except Exception as e:
        print(f"[WARNING] 无法打开浏览器: {e}")
        print("请手动访问: http://localhost:5000\n")
    
    # 启动 Flask - 切换到项目根目录
    os.chdir(current_dir.parent)
    os.system(f'{sys.executable} {web_server_path}')

if __name__ == '__main__':
    main()
