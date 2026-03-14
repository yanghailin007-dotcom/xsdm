"""
全局停止标志模块
避免循环导入问题
"""
import threading
import time

# 🔥 全局停止标志（用于跨线程通信）
_global_stop_requested = False
_global_sigint_count = 0
_global_sigint_time = 0
_lock = threading.Lock()


def global_signal_handler(signum, frame):
    """全局信号处理器 - 在主线程中设置"""
    global _global_stop_requested, _global_sigint_count, _global_sigint_time
    
    current_time = time.time()
    
    # 如果超过 3 秒，重置计数器
    with _lock:
        if current_time - _global_sigint_time > 3:
            _global_sigint_count = 0
        
        _global_sigint_count += 1
        _global_sigint_time = current_time
        
        try:
            print(f"\n\n{'='*60}")
            print(f"[WARN] 收到中断信号 (Ctrl+C) - 第 {_global_sigint_count} 次")
            print(f"{'='*60}")
            
            if _global_sigint_count == 1:
                print("[INFO] 正在请求停止生成...")
                _global_stop_requested = True
                print("[OK] 停止标志已设置")
                print("\n[HINT] 3 秒内再按一次 Ctrl+C 强制退出服务器")
                print("       不按则等待当前生成完成...\n")
            else:
                print("[EXIT] 收到第二次中断信号，强制退出...")
                import sys
                sys.exit(0)
        except:
            # 忽略任何编码错误
            _global_stop_requested = True
            if _global_sigint_count >= 2:
                import sys
                sys.exit(0)


def is_stop_requested():
    """检查是否请求停止"""
    global _global_stop_requested
    return _global_stop_requested


def reset_stop_flag():
    """重置停止标志"""
    global _global_stop_requested
    with _lock:
        _global_stop_requested = False


def set_stop_flag():
    """设置停止标志"""
    global _global_stop_requested
    with _lock:
        _global_stop_requested = True
