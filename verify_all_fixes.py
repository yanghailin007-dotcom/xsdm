#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证所有 GenerationContext 修复的最终检查清单
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_all_fixes():
    print("=" * 70)
    print("最终修复验证清单")
    print("=" * 70)

    checks_passed = 0
    checks_total = 0

    # 检查 1: 验证 Prompts 中有 chapter_title_generation
    checks_total += 1
    print("\n[检查 1] 验证 chapter_title_generation prompt 存在")
    try:
        from src.prompts.Prompts import Prompts
        if 'chapter_title_generation' in Prompts:
            print("  通过: prompt 已添加")
            checks_passed += 1
        else:
            print("  失败: prompt 未找到")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 2: 验证 GenerationContext 可以正常访问
    checks_total += 1
    print("\n[检查 2] 验证 GenerationContext 属性访问")
    try:
        from src.core.Contexts import GenerationContext
        context = GenerationContext(
            chapter_number=3,
            total_chapters=10,
            novel_data={},
            stage_plan={},
            event_context={'active_events': [{'name': '测试', 'main_goal': '测试'}]},
            foreshadowing_context={},
            growth_context={}
        )
        assert hasattr(context, 'event_context'), "缺少 event_context 属性"
        assert isinstance(context.event_context, dict), "event_context 应该是字典"
        print("  通过: GenerationContext 属性正常")
        checks_passed += 1
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 3: 验证 _generate_unique_chapter_title 修复
    checks_total += 1
    print("\n[检查 3] 验证 _generate_unique_chapter_title 修复")
    try:
        with open('src/core/ContentGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查是否有类型检查
            if 'hasattr(context_obj, \'event_context\')' in content and \
               'isinstance(context_obj, dict)' in content:
                print("  通过: 修复逻辑已应用")
                checks_passed += 1
            else:
                print("  失败: 修复逻辑未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 4: 验证 _generate_event_related_title 修复
    checks_total += 1
    print("\n[检查 4] 验证 _generate_event_related_title 修复")
    try:
        with open('src/core/ContentGenerator.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 查找方法
            found = False
            for i, line in enumerate(lines):
                if 'def _generate_event_related_title' in line:
                    # 检查接下来的 20 行
                    for j in range(i, min(i+25, len(lines))):
                        if 'if not isinstance(event_context, dict):' in lines[j]:
                            print("  通过: 修复逻辑已应用")
                            checks_passed += 1
                            found = True
                            break
                    if found:
                        break
            if not found:
                print("  失败: 修复逻辑未应用")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 5: 验证 API 调用修复
    checks_total += 1
    print("\n[检查 5] 验证 API 调用参数修复")
    try:
        with open('src/core/ContentGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查是否使用了正确的参数
            if 'content_type="chapter_title_generation"' in content and \
               'user_prompt=title_prompt' in content:
                print("  通过: API 调用参数已修复")
                checks_passed += 1
            else:
                print("  失败: API 调用参数未修复")
    except Exception as e:
        print(f"  失败: {e}")

    # 检查 6: 验证 _save_chapter_failure 修复
    checks_total += 1
    print("\n[检查 6] 验证 _save_chapter_failure 修复")
    try:
        with open('src/core/ContentGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'event_ctx = current_context.event_context if hasattr' in content and \
               'isinstance(event_ctx, dict)' in content:
                print("  通过: 修复逻辑已应用")
                checks_passed += 1
            else:
                print("  失败: 修复逻辑未应用")
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
    success = verify_all_fixes()
    sys.exit(0 if success else 1)