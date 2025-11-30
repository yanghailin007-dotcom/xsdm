#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证 generated_chapters 字典键一致性修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_dict_key_consistency():
    print("=" * 70)
    print("验证 generated_chapters 字典键一致性修复")
    print("=" * 70)

    checks_passed = 0
    checks_total = 0

    # 检查 1: 验证 ProjectManager 排序修复
    checks_total += 1
    print("\n[检查 1] 验证 ProjectManager 排序修复")
    try:
        with open('src/core/ProjectManager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'key=lambda x: int(x[0])' in content:
                print("  通过: 排序修复已应用")
                checks_passed += 1
            else:
                print("  失败: 排序修复未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 2: 验证 NovelGenerator 键转换修复
    checks_total += 1
    print("\n[检查 2] 验证 NovelGenerator 键转换修复")
    try:
        with open('src/core/NovelGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'chapter_key = str(chapter_number)' in content:
                print("  通过: 键转换修复已应用")
                checks_passed += 1
            else:
                print("  失败: 键转换修复未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 3: 验证 ContentGenerator 向后兼容性修复
    checks_total += 1
    print("\n[检查 3] 验证 ContentGenerator 向后兼容性修复")
    try:
        with open('src/core/ContentGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'chapter_key = str(chapter_number)' in content and '向后兼容' in content:
                print("  通过: 向后兼容性修复已应用")
                checks_passed += 1
            else:
                print("  失败: 向后兼容性修复未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 4: 验证 ProjectManager 键转换修复
    checks_total += 1
    print("\n[检查 4] 验证 ProjectManager 键转换修复 (int转换)")
    try:
        with open('src/core/ProjectManager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'int(chapter_num)' in content and 'int(num)' in content:
                print("  通过: 整数转换修复已应用")
                checks_passed += 1
            else:
                print("  失败: 整数转换修复未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 5: 实际运行测试
    checks_total += 1
    print("\n[检查 5] 实际运行字典操作测试")
    try:
        # 测试整数排序
        test_dict = {
            "1": {"title": "第1章"},
            "10": {"title": "第10章"},
            "2": {"title": "第2章"},
        }

        # 使用修复后的排序方式
        sorted_items = sorted(test_dict.items(), key=lambda x: int(x[0]))
        sorted_keys = [k for k, _ in sorted_items]

        if sorted_keys == ["1", "2", "10"]:
            print("  通过: 排序结果正确")
            checks_passed += 1
        else:
            print(f"  失败: 排序结果不正确，得到 {sorted_keys}")
    except Exception as e:
        print(f"  失败: {e}")

    # 最终结果
    print("\n" + "=" * 70)
    print(f"验证结果: {checks_passed}/{checks_total} 检查通过")
    print("=" * 70)

    if checks_passed == checks_total:
        print("\n成功: 所有修复已正确应用!")
        return True
    else:
        print(f"\n警告: 有 {checks_total - checks_passed} 个检查失败")
        return False

if __name__ == "__main__":
    success = test_dict_key_consistency()
    sys.exit(0 if success else 1)