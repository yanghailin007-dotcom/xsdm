#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清理缓存并验证所有修复
"""

import sys
import os
import shutil
import pathlib

def cleanup_cache():
    """清除所有 Python 缓存"""
    print("清除 Python 缓存...")
    cache_dirs = list(pathlib.Path('.').rglob('__pycache__'))
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"  已删除: {cache_dir}")
        except Exception as e:
            print(f"  失败: {cache_dir} - {e}")

    # 删除 .pyc 文件
    pyc_files = list(pathlib.Path('.').rglob('*.pyc'))
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            print(f"  已删除: {pyc_file}")
        except Exception as e:
            print(f"  失败: {pyc_file} - {e}")

    print(f"缓存清理完成 (删除了 {len(cache_dirs)} 个目录和 {len(pyc_files)} 个文件)")

def verify_fixes():
    """验证所有修复"""
    print("\n验证修复...")

    # 导入验证脚本
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from verify_all_fixes import verify_all_fixes
        return verify_all_fixes()
    except Exception as e:
        print(f"验证失败: {e}")
        return False

def main():
    print("=" * 70)
    print("清理缓存并验证修复")
    print("=" * 70)

    # 清理缓存
    cleanup_cache()

    # 验证修复
    success = verify_fixes()

    print("\n" + "=" * 70)
    if success:
        print("成功: 所有修复已验证，可以重启应用程序")
    else:
        print("警告: 某些验证失败，请检查日志")
    print("=" * 70)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())