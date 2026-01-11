#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台Web服务启动脚本
支持Windows和Linux系统
"""

import sys
import os
import time
import signal
import platform
import subprocess
import socket
from pathlib import Path

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def check_python_version():
    """检查Python版本"""
    print_header("检查Python版本")
    version = sys.version_info
    print(f"  Python版本: {version.major}.{version.minor}.{version.micro}")
    print(f"  平台: {platform.system()} {platform.release()}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  [ERROR] 需要Python 3.8或更高版本")
        return False
    print("  [OK] Python版本符合要求")
    return True

def check_dependencies():
    """检查依赖包"""
    print_header("检查依赖包")
    
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS'
    }
    
    missing = []
    for package, display_name in required_packages.items():
        try:
            __import__(package)
            print(f"  [OK] {display_name}")
        except ImportError:
            print(f"  [X] {display_name} (缺失)")
            missing.append(display_name)
    
    if missing:
        print(f"\n  [INFO] 需要安装: {', '.join(missing)}")
        print(f"  [CMD] pip install {' '.join(missing)}")
        response = input("\n  是否现在安装? (y/n): ").lower()
        if response == 'y':
            for pkg in missing:
                print(f"  正在安装 {pkg}...")
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"  [ERROR] 安装失败: {e}")
                    print(f"  [INFO] 如果在Ubuntu/Debian系统上，请先创建虚拟环境:")
                    print(f"        python3 -m venv venv")
                    print(f"        source venv/bin/activate  # Linux/Mac")
                    print(f"        venv\\Scripts\\activate     # Windows")
                    print(f"        pip install {' '.join(missing)}")
                    return False
            print("  [OK] 依赖安装完成")
        else:
            print("  [WARN] 跳过依赖安装，服务可能无法正常启动")
            return False
    
    return True

def kill_port_process(port=5000):
    """清理占用指定端口的进程（跨平台）"""
    print_header(f"清理端口 {port}")
    
    system = platform.system()
    killed = False
    
    if system == "Windows":
        # Windows: 使用netstat和taskkill
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = result.stdout.split('\n')
            pids = set()
            
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.add(pid)
            
            if pids:
                print(f"  [INFO] 找到占用端口的进程: {pids}")
                for pid in pids:
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/PID', pid],
                            capture_output=True,
                            timeout=5
                        )
                        print(f"  [KILL] 进程 {pid} 已终止")
                        killed = True
                    except Exception as e:
                        print(f"  [WARN] 终止进程 {pid} 失败: {e}")
            else:
                print(f"  [OK] 没有进程占用端口 {port}")
                
        except Exception as e:
            print(f"  [WARN] 清理端口时出错: {e}")
    
    else:
        # Linux/Mac: 多种方法尝试清理端口
        # 方法1: 使用fuser (最可靠)
        try:
            result = subprocess.run(
                ['fuser', '-k', f'{port}/tcp'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"  [OK] 使用fuser清理端口 {port}")
                killed = True
            # 即使returncode不为0，也可能清理成功
            elif 'killed' in result.stderr.lower() or 'killed' in result.stdout.lower():
                print(f"  [OK] 端口 {port} 已清理")
                killed = True
        except FileNotFoundError:
            print(f"  [INFO] fuser未安装，尝试其他方法...")
        except Exception as e:
            print(f"  [INFO] fuser执行失败: {e}，尝试其他方法...")
        
        # 方法2: 如果fuser失败或不可用，尝试lsof
        if not killed:
            try:
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    pids = [pid for pid in pids if pid.isdigit()]
                    
                    if pids:
                        print(f"  [INFO] 找到占用端口的进程: {pids}")
                        for pid in pids:
                            try:
                                subprocess.run(
                                    ['kill', '-9', pid],
                                    capture_output=True,
                                    timeout=5
                                )
                                print(f"  [KILL] 进程 {pid} 已终止")
                                killed = True
                            except Exception as e:
                                print(f"  [WARN] 终止进程 {pid} 失败: {e}")
                    else:
                        print(f"  [OK] 没有进程占用端口 {port}")
                else:
                    print(f"  [OK] 没有进程占用端口 {port}")
                    
            except FileNotFoundError:
                print(f"  [INFO] lsof未安装")
            except Exception as e:
                print(f"  [INFO] lsof执行失败: {e}")
        
        # 方法3: 如果前两种方法都失败，尝试ss命令
        if not killed:
            try:
                result = subprocess.run(
                    ['ss', '-tlnp'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    pids = set()
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line:
                            # 解析ss输出获取pid
                            parts = line.split()
                            for part in parts:
                                if 'pid=' in part:
                                    pid = part.split('=')[1].split(',')[0]
                                    if pid.isdigit():
                                        pids.add(pid)
                    
                    if pids:
                        print(f"  [INFO] 找到占用端口的进程: {pids}")
                        for pid in pids:
                            try:
                                subprocess.run(
                                    ['kill', '-9', pid],
                                    capture_output=True,
                                    timeout=5
                                )
                                print(f"  [KILL] 进程 {pid} 已终止")
                                killed = True
                            except Exception as e:
                                print(f"  [WARN] 终止进程 {pid} 失败: {e}")
                    else:
                        print(f"  [OK] 没有进程占用端口 {port}")
            except FileNotFoundError:
                print(f"  [INFO] ss命令未安装")
            except Exception as e:
                print(f"  [INFO] ss命令执行失败: {e}")
        
        # 如果所有方法都失败，给用户提示
        if not killed:
            print(f"  [WARN] 无法自动清理端口 {port}")
            print(f"  [INFO] 请手动执行以下命令:")
            print(f"        sudo lsof -ti :{port} | xargs kill -9")
            print(f"        或")
            print(f"        sudo fuser -k {port}/tcp")
    
    if killed:
        print("  [OK] 等待端口释放...")
        time.sleep(2)
        # 再次检查端口是否已释放
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            result = test_socket.connect_ex(('127.0.0.1', port))
            test_socket.close()
            if result == 0:
                print(f"  [WARN] 端口 {port} 仍被占用，请手动检查")
            else:
                print(f"  [OK] 端口 {port} 已释放")
        except:
            pass

def ensure_directories():
    """确保必要的目录存在"""
    print_header("检查目录结构")
    
    directories = [
        "data",
        "logs",
        "generated_images",
        "temp_fanqie_upload",
        "小说项目"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  [CREATE] {directory}/")
        else:
            print(f"  [OK] {directory}/")

def start_web_server():
    """启动Web服务器"""
    print_header("启动Web服务器")
    
    # 获取项目根目录
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    web_server_path = project_root / "web" / "web_server_refactored.py"
    
    if not web_server_path.exists():
        print(f"  [ERROR] 找不到Web服务器文件: {web_server_path}")
        return False
    
    print(f"  [INFO] 服务器路径: {web_server_path}")
    print(f"  [INFO] 访问地址: http://localhost:8080")
    print(f"  [INFO] 按Ctrl+C停止服务（需要连续两次）")
    print("\n" + "=" * 70)
    print("服务启动中...")
    print("=" * 70 + "\n")
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 启动Flask服务器
    try:
        subprocess.run([sys.executable, str(web_server_path)])
    except KeyboardInterrupt:
        print("\n\n  [INFO] 服务已停止")
        return True
    
    return True

def main():
    """主函数"""
    print_header("小说生成系统 - Web服务启动")
    
    # 1. 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 2. 检查依赖
    if not check_dependencies():
        print("\n  [WARN] 依赖检查未通过，尝试继续启动...")
    
    # 3. 确保目录存在
    ensure_directories()
    
    # 4. 清理端口
    kill_port_process(8080)
    
    # 5. 启动服务器
    start_web_server()

if __name__ == '__main__':
    main()