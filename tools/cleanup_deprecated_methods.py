#!/usr/bin/env python3
"""
清理废弃方法脚本
删除所有已标记为废弃的方法
"""

import os
import re
from pathlib import Path

def remove_deprecated_method(file_path: str, method_name: str, start_marker: str, end_marker: str) -> bool:
    """删除一个废弃的方法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到方法的开始和结束
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return False
        
        # 找到方法结束（下一个 def 或文件结尾）
        remaining = content[start_idx:]
        next_def = re.search(r'\n    def ', remaining[len(start_marker):])
        
        if next_def:
            end_idx = start_idx + len(start_marker) + next_def.start()
        else:
            end_idx = len(content)
        
        # 删除方法
        new_content = content[:start_idx] + content[end_idx:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 删除 {method_name} from {Path(file_path).name}")
        return True
    except Exception as e:
        print(f"❌ 删除 {method_name} 失败: {e}")
        return False

def cleanup_deprecated_methods():
    """清理所有废弃方法"""
    
    deprecated_methods = [
        {
            'file': 'd:\\work6.03\\ContentGenerator.py',
            'method': '_get_fallback_emotional_guidance',
            'reason': '已被新的 _get_emotional_guidance_for_chapter 替代'
        },
        {
            'file': 'd:\\work6.03\\ContentGenerator.py',
            'method': '_get_golden_chapter_design_variant',
            'reason': '黄金三章的硬编码指导，已由更灵活的系统替代'
        },
        {
            'file': 'd:\\work6.03\\QualityAssessor.py',
            'method': '_apply_golden_chapters_standards',
            'reason': '黄金三章的特殊评分标准已整合到主评估流程'
        },
        {
            'file': 'd:\\work6.03\\QualityAssessor.py',
            'method': '_get_golden_chapters_quality_tier',
            'reason': '已被新的质量分类系统替代'
        },
        {
            'file': 'd:\\work6.03\\QualityAssessor.py',
            'method': '_generate_golden_chapters_suggestions',
            'reason': '建议生成已集成到主流程'
        },
        {
            'file': 'd:\\work6.03\\StagePlanManager.py',
            'method': '_decompose_golden_arc_from_seed',
            'reason': '旧的弧形分解方法，已被新的事件分解策略替代'
        }
    ]
    
    print("=" * 80)
    print("清理废弃方法")
    print("=" * 80)
    print()
    
    removed_count = 0
    for item in deprecated_methods:
        file_path = item['file']
        method_name = item['method']
        reason = item['reason']
        
        print(f"处理: {Path(file_path).name}::{method_name}")
        print(f"原因: {reason}")
        
        # 验证文件中是否存在该方法
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if f"def {method_name}(" in content:
                print(f"  状态: 找到，准备删除...")
                removed_count += 1
            else:
                print(f"  状态: 未找到")
        except:
            print(f"  状态: 文件错误")
        
        print()
    
    print("=" * 80)
    print(f"✅ 发现 {removed_count} 个废弃方法，可以安全删除")
    print("=" * 80)
    print()
    print("这些方法已被更现代的实现替代:")
    print("  • 情绪指导: 使用 _get_emotional_guidance_for_chapter 和 EmotionalPlanManager")
    print("  • 黄金三章标准: 已整合到主评估流程中")
    print("  • 弧形分解: 使用新的 _EventDecomposer 策略模式")
    print()
    print("下一步:")
    print("  1. 验证没有代码调用这些方法")
    print("  2. 运行测试确保功能正常")
    print("  3. 手动删除这些方法")

if __name__ == "__main__":
    cleanup_deprecated_methods()
