"""
清理 Python 缓存并重启服务器
"""
import os
import shutil
import sys
from pathlib import Path

print("=" * 60)
print("清理 Python 缓存文件")
print("=" * 60)

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 清理所有 __pycache__ 目录
cache_count = 0
for cache_dir in BASE_DIR.rglob("__pycache__"):
    try:
        shutil.rmtree(cache_dir)
        print(f"✅ 已删除: {cache_dir.relative_to(BASE_DIR)}")
        cache_count += 1
    except Exception as e:
        print(f"❌ 删除失败: {cache_dir.relative_to(BASE_DIR)}: {e}")

# 清理所有 .pyc 文件
pyc_count = 0
for pyc_file in BASE_DIR.rglob("*.pyc"):
    try:
        pyc_file.unlink()
        print(f"✅ 已删除: {pyc_file.relative_to(BASE_DIR)}")
        pyc_count += 1
    except Exception as e:
        print(f"❌ 删除失败: {pyc_file.relative_to(BASE_DIR)}: {e}")

print("\n" + "=" * 60)
print(f"✅ 清理完成!")
print(f"   删除了 {cache_count} 个 __pycache__ 目录")
print(f"   删除了 {pyc_count} 个 .pyc 文件")
print("=" * 60)
print("\n💡 下一步：")
print("   1. 完全停止当前的 Web 服务器（Ctrl+C）")
print("   2. 重新启动: python web/web_server_refactored.py")
print("   3. 创建新的视频生成任务进行测试")
print("=" * 60)
