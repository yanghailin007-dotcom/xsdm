#!/usr/bin/env python3
"""
清理所有缓存文件 - 确保服务器使用最新代码
用法: python clear_cache.py
"""
import os
import shutil
import sys
from pathlib import Path

def clear_python_cache():
    """清理 Python 缓存文件"""
    print("🔍 清理 Python 缓存...")
    count = 0
    
    # 清理 __pycache__ 目录
    for pycache_dir in Path('.').rglob('__pycache__'):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                count += 1
                print(f"  ✓ 删除: {pycache_dir}")
            except Exception as e:
                print(f"  ✗ 删除失败 {pycache_dir}: {e}")
    
    # 清理 .pyc 和 .pyo 文件
    for ext in ['*.pyc', '*.pyo', '*.pyd']:
        for file in Path('.').rglob(ext):
            try:
                file.unlink()
                count += 1
            except Exception as e:
                pass
    
    print(f"✅ Python 缓存清理完成: {count} 个项目\n")
    return count

def clear_flask_cache():
    """清理 Flask 相关缓存"""
    print("🔍 清理 Flask 缓存...")
    
    # 清理 .flask_session 或其他会话缓存
    cache_dirs = ['.flask_session', 'flask_cache', 'cache', '.cache']
    count = 0
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                if os.path.isdir(cache_dir):
                    shutil.rmtree(cache_dir)
                else:
                    os.remove(cache_dir)
                count += 1
                print(f"  ✓ 删除: {cache_dir}")
            except Exception as e:
                print(f"  ✗ 删除失败 {cache_dir}: {e}")
    
    print(f"✅ Flask 缓存清理完成: {count} 个项目\n")
    return count

def clear_logs():
    """清理旧日志文件"""
    print("🔍 清理日志文件...")
    count = 0
    
    log_dirs = ['logs']
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            for log_file in Path(log_dir).glob('*.log'):
                try:
                    log_file.unlink()
                    count += 1
                    print(f"  ✓ 删除: {log_file}")
                except Exception as e:
                    pass
    
    print(f"✅ 日志清理完成: {count} 个文件\n")
    return count

def clear_temp_files():
    """清理临时文件"""
    print("🔍 清理临时文件...")
    count = 0
    
    # 清理各种临时文件
    temp_patterns = ['*.tmp', '*.temp', '.DS_Store', 'Thumbs.db', '.server.pid']
    
    for pattern in temp_patterns:
        for file in Path('.').rglob(pattern):
            try:
                if file.is_file():
                    file.unlink()
                    count += 1
                    print(f"  ✓ 删除: {file}")
            except Exception as e:
                pass
    
    print(f"✅ 临时文件清理完成: {count} 个文件\n")
    return count

def restart_server():
    """重启服务器"""
    print("🚀 重启服务器...")
    
    # 尝试使用不同的方式重启
    if os.path.exists('restart.sh'):
        os.system('sh restart.sh')
    elif os.path.exists('start.sh') and os.path.exists('stop.sh'):
        os.system('sh stop.sh && sleep 2 && sh start.sh')
    else:
        print("⚠️ 未找到 restart.sh，请手动重启服务器")

def main():
    """主函数"""
    print("="*60)
    print("🧹 服务器缓存清理工具")
    print("="*60)
    print()
    
    # 确认操作
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        confirm = 'y'
    else:
        confirm = input("⚠️  这将清理所有缓存并重启服务器，是否继续? (y/n): ")
    
    if confirm.lower() != 'y':
        print("已取消")
        return
    
    print()
    
    # 执行清理
    total = 0
    total += clear_python_cache()
    total += clear_flask_cache()
    total += clear_logs()
    total += clear_temp_files()
    
    print("="*60)
    print(f"✅ 总计清理: {total} 个项目")
    print("="*60)
    print()
    
    # 询问是否重启
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        restart = 'y'
    else:
        restart = input("🚀 是否立即重启服务器? (y/n): ")
    
    if restart.lower() == 'y':
        restart_server()
    else:
        print("💡 请手动重启服务器以应用更改")

if __name__ == '__main__':
    main()
