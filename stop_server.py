"""
快速停止端口5000的进程
"""

import os
import subprocess
import sys

def stop_port_5000():
    try:
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
            print("没有找到占用端口5000的进程")
            return

        print(f"找到占用端口5000的进程: {pids}")

        # 杀死进程
        for pid in pids:
            print(f"终止进程 {pid}...")
            subprocess.run(['taskkill', '/F', '/PID', pid])
            print(f"进程 {pid} 已终止")

    except Exception as e:
        print(f"停止进程时出错: {e}")

if __name__ == "__main__":
    stop_port_5000()
    print("端口5000清理完成")