#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一键修复和验证脚本
清除缓存 + 验证所有修复 + 运行测试
"""

import sys
import os
import shutil
import pathlib

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def cleanup_cache():
    """清除所有 Python 缓存"""
    print_header("步骤 1: 清除 Python 缓存")

    cache_count = 0
    pyc_count = 0

    try:
        cache_dirs = list(pathlib.Path('.').rglob('__pycache__'))
        for cache_dir in cache_dirs:
            try:
                shutil.rmtree(cache_dir)
                cache_count += 1
            except Exception as e:
                print(f"  警告: 无法删除 {cache_dir} - {e}")

        pyc_files = list(pathlib.Path('.').rglob('*.pyc'))
        for pyc_file in pyc_files:
            try:
                pyc_file.unlink()
                pyc_count += 1
            except Exception as e:
                print(f"  警告: 无法删除 {pyc_file} - {e}")

        print(f"[OK] 缓存清理完成 (删除了 {cache_count} 个目录和 {pyc_count} 个文件)")
        return True
    except Exception as e:
        print(f"[FAIL] 缓存清理失败: {e}")
        return False

def verify_fixes():
    """验证所有修复"""
    print_header("步骤 2: 验证所有修复")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # 验证 GenerationContext 修复
        print("\n验证 GenerationContext 修复...")
        from test_all_context_fixes import test_all_context_fixes
        if not test_all_context_fixes():
            print("[FAIL] GenerationContext 修复验证失败")
            return False
        print("[OK] GenerationContext 修复已验证")

        # 验证字典键一致性修复
        print("\n验证字典键一致性修复...")
        from verify_dict_key_fixes import test_dict_key_consistency
        if not test_dict_key_consistency():
            print("[FAIL] 字典键一致性修复验证失败")
            return False
        print("[OK] 字典键一致性修复已验证")

        return True
    except Exception as e:
        print(f"[FAIL] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_header("完整修复工具")
    print("\n本工具将执行以下操作:")
    print("1. 清除所有 Python 缓存")
    print("2. 验证 GenerationContext 修复")
    print("3. 验证字典键一致性修复")
    print("4. 显示修复完成状态")

    # 步骤 1: 清理缓存
    if not cleanup_cache():
        print("\n[FAIL] 缓存清理失败，请手动清理后重试")
        return 1

    # 步骤 2: 验证修复
    if not verify_fixes():
        print("\n[FAIL] 修复验证失败")
        return 1

    # 成功
    print_header("修复完成")
    print("""
[OK] 所有修复已完成并验证通过!

下一步:
1. 重启您的应用程序
2. 测试章节生成功能
3. 如需进一步验证，运行:
   - python verify_all_fixes.py         (完整验证)
   - python verify_dict_key_fixes.py    (字典键验证)
   - python test_all_context_fixes.py   (GenerationContext 验证)

修复文档:
- COMPLETE_FIX_SUMMARY.md    (完整修复说明)
- FIX_INSTRUCTIONS.md         (使用说明)
- FINAL_FIX_SUMMARY.md        (快速参考)
    """)

    return 0

if __name__ == "__main__":
    sys.exit(main())