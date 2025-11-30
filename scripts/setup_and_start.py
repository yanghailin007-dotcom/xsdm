"""
设置并启动Web服务

功能：
1. 确保所有必要的目录存在
2. 检查配置文件
3. 清理旧的重复进程
4. 启动Web服务
"""

import os
import sys
import psutil
import subprocess
from pathlib import Path

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def ensure_directories():
    """确保所有必要的目录存在"""
    print_header("检查和创建必要目录")

    directories = [
        "data",
        "data/projects",
        "output",
        "resources",
        "static",
        "config",
        "logs",
        "小说项目"
    ]

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  [CREATE] {directory}/")
        else:
            print(f"  [OK] {directory}/")

def check_config_files():
    """检查配置文件"""
    print_header("检查配置文件")

    config_files = {
        "config/config.json": "config/config.json.example",
        ".env": ".env.example"
    }

    for config_file, example_file in config_files.items():
        config_path = Path(config_file)
        example_path = Path(example_file)

        if config_path.exists():
            print(f"  [OK] {config_file} 存在")
        else:
            if example_path.exists():
                print(f"  [WARN] {config_file} 不存在")
                print(f"         请复制 {example_file} 为 {config_file} 并填写配置")
            else:
                print(f"  [ERROR] {config_file} 和示例文件都不存在")

def kill_processes_on_port(port=5000):
    """杀死占用指定端口的所有进程"""
    print_header(f"清理占用端口 {port} 的进程")

    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            # 检查进程的所有连接
            for conn in proc.connections():
                if conn.laddr.port == port:
                    print(f"  [KILL] PID={proc.pid}, Name={proc.name()}")
                    proc.kill()
                    killed_count += 1
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if killed_count > 0:
        print(f"  已清理 {killed_count} 个进程")
        import time
        print("  等待2秒让进程完全关闭...")
        time.sleep(2)
    else:
        print(f"  没有进程占用端口 {port}")

def start_web_server():
    """启动Web服务器"""
    print_header("启动Web服务器")

    print("  启动命令: python run_web.py")
    print("  访问地址: http://localhost:5000")
    print("\n  按 Ctrl+C 停止服务\n")

    try:
        subprocess.run([sys.executable, "run_web.py"])
    except KeyboardInterrupt:
        print("\n\n  服务已停止")

def main():
    """主函数"""
    print_header("小说生成Web服务 - 设置和启动脚本")

    # 1. 确保目录存在
    ensure_directories()

    # 2. 检查配置文件
    check_config_files()

    # 3. 清理重复进程
    kill_processes_on_port(5000)

    # 4. 启动服务
    start_web_server()

if __name__ == "__main__":
    main()
