#!/usr/bin/env python3
"""
诊断 start.py 启动问题
"""
import sys
import os
import subprocess
import time
import socket
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
PID_FILE = PROJECT_DIR / ".server.pid"
PORT = 5000

def check_port(port=PORT):
    """检测端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"检查端口时出错: {e}")
        return False

def test_web_server_direct():
    """直接测试 web_server_refactored.py"""
    print("=" * 60)
    print("测试1: 直接启动 web_server_refactored.py")
    print("=" * 60)
    
    web_server_path = PROJECT_DIR / "web" / "web_server_refactored.py"
    
    # 启动进程
    print(f"启动: {web_server_path}")
    proc = subprocess.Popen(
        [sys.executable, str(web_server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='ignore',
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    print(f"进程已启动，PID: {proc.pid}")
    
    # 读取输出（最多30秒）
    print("\n读取输出（最多30秒）...")
    start_time = time.time()
    lines = []
    
    try:
        while time.time() - start_time < 30:
            # 检查进程是否还在运行
            if proc.poll() is not None:
                print(f"进程已退出，返回码: {proc.returncode}")
                break
            
            # 尝试读取一行（非阻塞）
            import select
            if hasattr(proc.stdout, 'readable') and proc.stdout.readable():
                line = proc.stdout.readline()
                if line:
                    lines.append(line.rstrip())
                    print(f"  > {line.rstrip()[:100]}")
            
            # 检查端口
            if check_port():
                print(f"\n[成功] 端口 {PORT} 已开放！")
                break
            
            time.sleep(0.5)
    except Exception as e:
        print(f"读取输出时出错: {e}")
    
    # 检查结果
    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  进程状态: {'运行中' if proc.poll() is None else '已退出'}")
    print(f"  端口状态: {'开放' if check_port() else '未开放'}")
    print(f"  输出行数: {len(lines)}")
    
    # 终止进程
    if proc.poll() is None:
        print("\n终止测试进程...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
    
    return check_port()

def test_import():
    """测试导入 web_server_refactored 模块"""
    print("\n" + "=" * 60)
    print("测试2: 导入 web_server_refactored 模块")
    print("=" * 60)
    
    start_time = time.time()
    try:
        # 导入模块
        print("正在导入模块...")
        from web import web_server_refactored
        print(f"模块导入成功，耗时: {time.time() - start_time:.2f}秒")
        
        # 检查 create_app 是否存在
        if hasattr(web_server_refactored, 'create_app'):
            print("create_app 函数存在")
        else:
            print("警告: create_app 函数不存在")
        
        return True
    except Exception as e:
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("大文娱系统 - 启动诊断工具")
    print(f"Python: {sys.executable}")
    print(f"工作目录: {PROJECT_DIR}")
    print()
    
    # 测试导入
    import_success = test_import()
    
    # 测试直接启动
    start_success = test_web_server_direct()
    
    print("\n" + "=" * 60)
    print("诊断总结:")
    print("=" * 60)
    print(f"  模块导入: {'成功' if import_success else '失败'}")
    print(f"  服务启动: {'成功' if start_success else '失败'}")
    
    if not import_success:
        print("\n建议: 检查 web_server_refactored.py 是否有语法错误或缺少依赖")
    elif not start_success:
        print("\n建议: 服务启动后端口未开放，可能是启动过程中卡住")
        print("      检查日志文件: server_YYYY-MM-DD.log")
    else:
        print("\n服务可以正常启动，问题可能出在 start.py 本身")

if __name__ == '__main__':
    main()
    input("\n按 Enter 键退出...")
