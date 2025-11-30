"""清理占用5000端口的所有进程"""

import psutil
import sys

def kill_processes_on_port(port=5000):
    """杀死占用指定端口的所有进程"""
    print(f"查找占用端口 {port} 的进程...")

    killed_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    print(f"  发现进程: PID={proc.pid}, Name={proc.name()}")
                    try:
                        proc.kill()
                        killed_pids.append(proc.pid)
                        print(f"  ✓ 已杀死进程 PID={proc.pid}")
                    except Exception as e:
                        print(f"  × 无法杀死进程 PID={proc.pid}: {e}")
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if killed_pids:
        print(f"\n总计清理了 {len(killed_pids)} 个进程")
        print(f"已清理的PIDs: {killed_pids}")
    else:
        print(f"\n没有进程占用端口 {port}")

    return len(killed_pids)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    count = kill_processes_on_port(port)
    sys.exit(0 if count > 0 else 1)
