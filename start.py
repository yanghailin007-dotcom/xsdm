#!/usr/bin/env python3
"""
=================================================================
大文娱系统 - 日常启动脚本 (Daily Start Script)
=================================================================
快速启动服务，用于日常开发使用

使用方法:
    日常启动:  python start.py
    或直接双击运行 start.py

注意:
    如果环境未配置，请先运行 setup.py 进行初始化
=================================================================
"""

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except:
        pass

# 颜色定义
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def get_python_executable():
    """获取 Python 可执行文件路径"""
    # 优先使用当前运行的 Python（确保一致性）
    if sys.executable and "python" in sys.executable.lower():
        return sys.executable
    
    # 尝试系统 Python
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "python"
    except:
        pass
    
    # 尝试 py 启动器
    try:
        result = subprocess.run(["py", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "py"
    except:
        pass
    
    return None

def is_service_running(port=5000):
    """检测服务是否已经在运行"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0  # 如果连接成功，说明服务在运行
    except:
        return False

def check_service_status():
    """检查服务状态，返回 (是否运行, 是否可访问)"""
    if not is_service_running(5000):
        return False, False
    
    # 进一步检查 HTTP 服务是否可用
    try:
        import urllib.request
        response = urllib.request.urlopen('http://127.0.0.1:5000/', timeout=3)
        return True, True
    except:
        return True, False  # 端口被占用但可能不是我们的服务

def stop_port_5000():
    """清理端口5000的进程"""
    try:
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} 检查端口 5000...")
        
        # 查找占用端口5000的进程
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
        lines = result.stdout.split('\n')

        pids = []
        for line in lines:
            if ':5000' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and pid not in pids:
                        pids.append(pid)

        if not pids:
            print(f"  {Colors.GREEN}[OK]{Colors.RESET} 端口 5000 空闲")
            return

        print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} 发现占用进程: {', '.join(pids)}")

        # 杀死进程
        killed = 0
        for pid in pids:
            try:
                subprocess.run(['taskkill', '/F', '/PID', pid], 
                             capture_output=True, timeout=5)
                killed += 1
            except:
                pass

        if killed > 0:
            print(f"  {Colors.GREEN}[OK]{Colors.RESET} 已清理 {killed} 个进程")
        
    except Exception as e:
        pass  # 静默处理错误

def check_quick():
    """快速检查环境"""
    try:
        import flask
        import flask_cors
        from PIL import Image
        return True
    except ImportError:
        return False

def main():
    """主函数"""
    # 打印标题
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  大文娱系统 - 日常启动{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    project_dir = Path(__file__).parent
    
    # 获取 Python
    python_exe = get_python_executable()
    if not python_exe:
        print(f"{Colors.RED}✗ 错误: 未找到 Python 环境{Colors.RESET}")
        print(f"\n请先运行 {Colors.YELLOW}setup.py{Colors.RESET} 进行初始化安装:")
        print(f"  python setup.py\n")
        input("按 Enter 键退出...")
        return
    
    # 快速检查依赖
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} 检查依赖...")
    if not check_quick():
        print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} 依赖未安装，尝试安装...")
        req_file = project_dir / "requirements.txt"
        if req_file.exists():
            subprocess.run([python_exe, "-m", "pip", "install", "-r", str(req_file), 
                          "--no-warn-script-location", "-q"], capture_output=True)
            if not check_quick():
                print(f"{Colors.RED}[ERR]{Colors.RESET} 依赖安装失败，请运行 setup.py")
                input("按 Enter 键退出...")
                return
        else:
            print(f"{Colors.RED}[ERR]{Colors.RESET} 找不到 requirements.txt")
            input("按 Enter 键退出...")
            return
    
    print(f"  {Colors.GREEN}[OK]{Colors.RESET} 依赖检查通过")
    
    # 检查服务是否已在运行
    print(f"\n{Colors.BLUE}[INFO]{Colors.RESET} 检查服务状态...")
    is_running, is_accessible = check_service_status()
    
    if is_running and is_accessible:
        print(f"  {Colors.GREEN}[OK]{Colors.RESET} 服务已在运行!")
        print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
        print(f"  {Colors.BOLD}Web 服务运行中{Colors.RESET}")
        print(f"  {Colors.CYAN}• 首页:{Colors.RESET} http://localhost:5000/landing")
        print(f"  {Colors.CYAN}• 创作:{Colors.RESET} http://localhost:5000/")
        print(f"  {Colors.CYAN}• API:{Colors.RESET}  http://localhost:5000/api")
        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
        
        # 直接打开浏览器
        try:
            webbrowser.open('http://localhost:5000/landing')
            print(f"{Colors.GREEN}[OK]{Colors.RESET} 浏览器已打开\n")
        except Exception as e:
            print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 请手动访问: http://localhost:5000/landing\n")
        
        input("按 Enter 键退出...")
        return
    elif is_running:
        print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} 端口被占用但服务不可访问，尝试清理...")
        stop_port_5000()
    else:
        print(f"  {Colors.GREEN}[OK]{Colors.RESET} 服务未启动，准备启动...")
    
    time.sleep(0.5)
    
    # 获取 web_server 路径
    web_server_path = project_dir / "web" / "web_server_refactored.py"
    if not web_server_path.exists():
        web_server_path = project_dir / "web" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"{Colors.RED}✗ 错误: 找不到 Web 服务器文件{Colors.RESET}")
        input("按 Enter 键退出...")
        return
    
    # 启动信息
    print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"  {Colors.BOLD}启动 Web 服务...{Colors.RESET}")
    print(f"  {Colors.CYAN}• 首页:{Colors.RESET} http://localhost:5000/landing")
    print(f"  {Colors.CYAN}• 创作:{Colors.RESET} http://localhost:5000/")
    print(f"  {Colors.CYAN}• API:{Colors.RESET}  http://localhost:5000/api")
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
    
    # 等待服务启动后打开浏览器
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open('http://localhost:5000/landing')
            print(f"{Colors.GREEN}[OK]{Colors.RESET} 浏览器已自动打开首页")
        except:
            print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 请手动访问: http://localhost:5000/landing")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动 Flask
    os.chdir(project_dir)
    try:
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} 正在启动 Flask 服务...")
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} 按 Ctrl+C 两次可停止服务\n")
        # 使用 subprocess.run 代替 os.system，更好地处理中断
        subprocess.run([python_exe, str(web_server_path)], check=False)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[INFO]{Colors.RESET} 服务已停止")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"{Colors.RED}[ERR]{Colors.RESET} 错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")
