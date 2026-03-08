#!/usr/bin/env python3
"""
=================================================================
大文娱系统 - 启动脚本 (支持后台运行和日志输出)
=================================================================

使用方法:
    前台运行:   python start.py
    后台运行:   python start.py --daemon
    停止服务:   python start.py --stop
    查看状态:   python start.py --status
    查看日志:   python start.py --logs
    查看帮助:   python start.py --help

日志文件位置:
    logs/server_YYYY-MM-DD.log
=================================================================
"""

import sys
import os
import subprocess
import webbrowser
import time
import argparse
import datetime
import signal
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

# 配置
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR  # 日志直接放在项目根目录，方便查看
PID_FILE = PROJECT_DIR / ".server.pid"
PORT = 5000

def ensure_logs_dir():
    """确保日志目录存在（现在直接放在根目录，无需创建）"""
    pass  # 日志文件直接放在项目根目录，方便查看

def get_log_file():
    """获取今天的日志文件路径"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return LOGS_DIR / f"server_{today}.log"  # 直接放在项目根目录

def get_python_executable():
    """获取 Python 可执行文件路径"""
    if sys.executable and "python" in sys.executable.lower():
        return sys.executable
    
    for cmd in ["python", "py", "python3"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return cmd
        except:
            pass
    
    return None

def is_service_running(port=PORT):
    """检测服务是否已经在运行"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def check_service_status():
    """检查服务状态，返回 (是否运行, 是否可访问)"""
    if not is_service_running(PORT):
        return False, False
    
    try:
        import urllib.request
        response = urllib.request.urlopen(f'http://127.0.0.1:{PORT}/', timeout=3)
        return True, True
    except:
        return True, False

def get_pid_from_file():
    """从文件读取 PID"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except:
            pass
    return None

def save_pid(pid):
    """保存 PID 到文件"""
    PID_FILE.write_text(str(pid))

def remove_pid_file():
    """删除 PID 文件"""
    if PID_FILE.exists():
        PID_FILE.unlink()

def stop_service():
    """停止服务"""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} 正在停止服务...")
    
    # 尝试从 PID 文件停止
    pid = get_pid_from_file()
    if pid:
        try:
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                             capture_output=True, timeout=5)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
            print(f"  {Colors.GREEN}[OK]{Colors.RESET} 已停止进程 {pid}")
            remove_pid_file()
            return True
        except Exception as e:
            print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} 停止 PID {pid} 失败: {e}")
    
    # 尝试通过端口查找并停止
    if sys.platform == 'win32':
        try:
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            pids = []
            for line in lines:
                if f':{PORT}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit() and pid not in pids:
                            pids.append(pid)
            
            for pid in pids:
                try:
                    subprocess.run(['taskkill', '/F', '/PID', pid], 
                                 capture_output=True, timeout=5)
                    print(f"  {Colors.GREEN}[OK]{Colors.RESET} 已停止进程 {pid}")
                except:
                    pass
            
            remove_pid_file()
            return len(pids) > 0
        except Exception as e:
            print(f"  {Colors.RED}[ERR]{Colors.RESET} 停止失败: {e}")
    else:
        # Linux/Mac
        try:
            result = subprocess.run(['lsof', '-t', f'-i:{PORT}'], 
                                  capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], capture_output=True)
                    print(f"  {Colors.GREEN}[OK]{Colors.RESET} 已停止进程 {pid}")
            remove_pid_file()
            return len(pids) > 0
        except:
            pass
    
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} 未找到运行中的服务")
    return False

def show_status():
    """显示服务状态"""
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  大文娱系统 - 服务状态{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    is_running, is_accessible = check_service_status()
    pid = get_pid_from_file()
    log_file = get_log_file()
    
    if is_running and is_accessible:
        print(f"  {Colors.GREEN}● 服务运行中{Colors.RESET}")
        if pid:
            print(f"    PID: {pid}")
    elif is_running:
        print(f"  {Colors.YELLOW}● 端口被占用但服务不可访问{Colors.RESET}")
    else:
        print(f"  {Colors.RED}● 服务未运行{Colors.RESET}")
    
    print(f"\n  {Colors.CYAN}访问地址:{Colors.RESET}")
    print(f"    • 首页: http://localhost:{PORT}/landing")
    print(f"    • 创作: http://localhost:{PORT}/")
    
    print(f"\n  {Colors.CYAN}日志文件:{Colors.RESET}")
    print(f"    {log_file}")
    if log_file.exists():
        size = log_file.stat().st_size
        print(f"    大小: {size / 1024:.1f} KB")
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")

def show_logs(lines=50, follow=False):
    """显示日志"""
    log_file = get_log_file()
    
    if not log_file.exists():
        # 查找最近的日志文件
        log_files = sorted(LOGS_DIR.glob("server_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if log_files:
            log_file = log_files[0]
        else:
            print(f"{Colors.YELLOW}[WARN]{Colors.RESET} 未找到日志文件")
            return
    
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  日志文件: {log_file.name}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        if follow:
            # 实时跟踪日志（类似 tail -f）
            print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 正在跟踪日志，按 Ctrl+C 退出...\n")
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # 先显示最后几行
                f.seek(0, 2)  # 跳到文件末尾
                file_size = f.tell()
                
                # 读取最后 N 字节
                buffer_size = 10240  # 10KB
                if file_size > buffer_size:
                    f.seek(file_size - buffer_size)
                else:
                    f.seek(0)
                
                # 跳过第一行（可能不完整）
                if file_size > buffer_size:
                    f.readline()
                
                print(f.read(), end='')
                
                # 实时跟踪新内容
                while True:
                    where = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        f.seek(where)
                    else:
                        print(line, end='')
        else:
            # 显示最后 N 行
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                print(''.join(last_lines))
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[INFO]{Colors.RESET} 已退出日志查看")
    except Exception as e:
        print(f"{Colors.RED}[ERR]{Colors.RESET} 读取日志失败: {e}")

def run_foreground(open_browser_flag=True):
    """前台运行服务"""
    ensure_logs_dir()
    
    # 如果服务已在运行，先停止旧服务
    is_running, is_accessible = check_service_status()
    if is_running:
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET} 检测到已有服务在运行，正在停止...")
        stop_service()
        time.sleep(2)  # 等待进程完全停止
    
    # 获取 Python
    python_exe = get_python_executable()
    if not python_exe:
        print(f"{Colors.RED}✗ 错误: 未找到 Python 环境{Colors.RESET}")
        return
    
    # 获取 web_server 路径
    web_server_path = PROJECT_DIR / "web" / "web_server_refactored.py"
    if not web_server_path.exists():
        web_server_path = PROJECT_DIR / "web" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"{Colors.RED}✗ 错误: 找不到 Web 服务器文件{Colors.RESET}")
        return
    
    log_file = get_log_file()
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"  {Colors.BOLD}启动 Web 服务 (前台运行){Colors.RESET}")
    print(f"  {Colors.CYAN}• 首页:{Colors.RESET} http://localhost:{PORT}/landing")
    print(f"  {Colors.CYAN}• 日志:{Colors.RESET} {log_file}")
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
    
    # 打开浏览器
    if open_browser_flag:
        def open_browser():
            time.sleep(3)
            try:
                webbrowser.open(f'http://localhost:{PORT}/landing')
                print(f"\n{Colors.GREEN}[OK]{Colors.RESET} 浏览器已自动打开首页")
            except:
                pass
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    # 启动 Flask，输出到日志文件同时也显示在控制台
    os.chdir(PROJECT_DIR)
    
    try:
        # 使用 tee 命令同时输出到控制台和文件（Windows 需要安装 tee）
        # 这里使用 Python 方式实现
        process = subprocess.Popen(
            [python_exe, str(web_server_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='ignore'
        )
        
        # 保存 PID
        save_pid(process.pid)
        
        # 同时输出到控制台和日志文件
        with open(log_file, 'a', encoding='utf-8') as log_f:
            log_f.write(f"\n{'='*60}\n")
            log_f.write(f"[{datetime.datetime.now()}] 服务启动 (PID: {process.pid})\n")
            log_f.write(f"{'='*60}\n")
            
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} 服务启动中... (PID: {process.pid})")
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} 按 Ctrl+C 停止服务\n")
            
            # 🔥 双击 Ctrl+C 检测变量
            _sigint_count = 0
            _sigint_time = 0
            
            def handle_sigint():
                """处理 Ctrl+C，返回 True 表示继续运行，False 表示退出"""
                nonlocal _sigint_count, _sigint_time
                current_time = time.time()
                
                # 如果超过 3 秒，重置计数器
                if current_time - _sigint_time > 3:
                    _sigint_count = 0
                
                _sigint_count += 1
                _sigint_time = current_time
                
                if _sigint_count == 1:
                    # 第一次 Ctrl+C：请求停止，但不终止进程
                    print(f"\n{Colors.YELLOW}[INFO]{Colors.RESET} ========================================")
                    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 收到第一次 Ctrl+C，正在请求停止生成...")
                    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} ========================================")
                    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 3 秒内再按一次 Ctrl+C 强制退出服务器")
                    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} 不按则等待当前生成完成...\n")
                    
                    # 🔥 不再向子进程发送信号（避免误判为第二次 Ctrl+C）
                    # 全局停止标志会在 web_server_refactored.py 中自动处理
                    return True  # 继续运行
                else:
                    # 第二次 Ctrl+C：强制退出
                    print(f"\n{Colors.RED}[INFO]{Colors.RESET} 收到第二次 Ctrl+C，强制退出...")
                    return False  # 退出
            
            # 主循环读取输出
            while True:
                try:
                    line = process.stdout.readline()
                    if not line:
                        # 子进程结束
                        break
                    print(line, end='')
                    log_f.write(line)
                    log_f.flush()
                except KeyboardInterrupt:
                    if not handle_sigint():
                        break
            
            # 终止进程
            print(f"\n{Colors.YELLOW}[INFO]{Colors.RESET} 正在停止服务...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
            remove_pid_file()
            print(f"{Colors.GREEN}[OK]{Colors.RESET} 服务已停止")
    except Exception as e:
        print(f"{Colors.RED}[ERR]{Colors.RESET} 启动失败: {e}")
        remove_pid_file()

def run_daemon():
    """后台运行服务"""
    ensure_logs_dir()
    
    # 如果服务已在运行，先停止旧服务
    is_running, is_accessible = check_service_status()
    if is_running:
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET} 检测到已有服务在运行，正在停止...")
        stop_service()
        time.sleep(2)  # 等待进程完全停止
    
    # 获取 Python
    python_exe = get_python_executable()
    if not python_exe:
        print(f"{Colors.RED}✗ 错误: 未找到 Python 环境{Colors.RESET}")
        return
    
    # 获取 web_server 路径
    web_server_path = PROJECT_DIR / "web" / "web_server_refactored.py"
    if not web_server_path.exists():
        web_server_path = PROJECT_DIR / "web" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"{Colors.RED}✗ 错误: 找不到 Web 服务器文件{Colors.RESET}")
        return
    
    log_file = get_log_file()
    
    # 写入启动标记到日志
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{datetime.datetime.now()}] 启动后台服务\n")
        f.write(f"{'='*60}\n")
    
    os.chdir(PROJECT_DIR)
    
    try:
        if sys.platform == 'win32':
            # Windows 后台运行
            # 使用 CREATE_NEW_CONSOLE 创建新窗口，或者使用 CREATE_NO_WINDOW 无窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            process = subprocess.Popen(
                [python_exe, str(web_server_path)],
                stdout=open(log_file, 'a', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            # Linux/Mac 后台运行
            process = subprocess.Popen(
                [python_exe, str(web_server_path)],
                stdout=open(log_file, 'a', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True
            )
        
        # 保存 PID
        save_pid(process.pid)
        
        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}")
        print(f"  {Colors.BOLD}服务已在后台启动{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
        print(f"  {Colors.GREEN}● PID:{Colors.RESET} {process.pid}")
        print(f"  {Colors.CYAN}• 首页:{Colors.RESET} http://localhost:{PORT}/landing")
        print(f"  {Colors.CYAN}• 日志:{Colors.RESET} {log_file}")
        print(f"\n  {Colors.YELLOW}命令:{Colors.RESET}")
        print(f"    查看状态: python start.py --status")
        print(f"    查看日志: python start.py --logs")
        print(f"    停止服务: python start.py --stop")
        print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
        
        # 等待服务启动
        time.sleep(2)
        if check_service_status()[0]:
            print(f"{Colors.GREEN}[OK]{Colors.RESET} 服务启动成功!")
        else:
            print(f"{Colors.YELLOW}[WARN]{Colors.RESET} 服务启动中，请稍后检查状态")
            
    except Exception as e:
        print(f"{Colors.RED}[ERR]{Colors.RESET} 启动失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='大文娱系统启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
    python start.py              # 前台运行（带日志）
    python start.py --daemon     # 后台运行
    python start.py --stop       # 停止服务
    python start.py --status     # 查看状态
    python start.py --logs       # 查看日志（最后50行）
    python start.py --logs -n 100    # 查看最后100行
    python start.py --logs -f    # 实时跟踪日志
        '''
    )
    
    parser.add_argument('--daemon', '-d', action='store_true', 
                       help='后台运行服务')
    parser.add_argument('--stop', '-s', action='store_true', 
                       help='停止服务')
    parser.add_argument('--status', action='store_true', 
                       help='查看服务状态')
    parser.add_argument('--logs', '-l', action='store_true', 
                       help='查看日志')
    parser.add_argument('-n', '--lines', type=int, default=50, 
                       help='查看日志的行数（默认50）')
    parser.add_argument('-f', '--follow', action='store_true', 
                       help='实时跟踪日志输出')
    parser.add_argument('--no-browser', action='store_true', 
                       help='前台运行时不自动打开浏览器')
    
    args = parser.parse_args()
    
    # 处理各种命令
    if args.stop:
        stop_service()
    elif args.status:
        show_status()
    elif args.logs:
        show_logs(lines=args.lines, follow=args.follow)
    elif args.follow:
        # 单独使用 -f 也显示日志
        show_logs(lines=args.lines, follow=True)
    elif args.daemon:
        run_daemon()
    else:
        # 默认前台运行
        run_foreground(open_browser_flag=not args.no_browser)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"{Colors.RED}[ERR]{Colors.RESET} 错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")
