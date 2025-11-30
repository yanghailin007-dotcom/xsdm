#!/usr/bin/env python3
"""
删除已识别的5个废弃方法
"""
import re

def delete_deprecated_methods():
    """删除所有5个废弃方法"""
    
    # 方法1: ContentGenerator._get_golden_chapter_design_variant
    print("删除方法1: ContentGenerator._get_golden_chapter_design_variant...")
    with open('ContentGenerator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到方法并删除（从def开始到下一个def或类结尾）
    pattern1 = r'\n    def _get_golden_chapter_design_variant\(self.*?\n        return ""\n        \n'
    content = re.sub(pattern1, '\n', content, flags=re.DOTALL)
    
    with open('ContentGenerator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ ContentGenerator._get_golden_chapter_design_variant 已删除")
    
    # 方法2-4: QualityAssessor 的三个方法
    print("删除方法2-4: QualityAssessor 的三个方法...")
    with open('QualityAssessor.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到这些方法并删除
    methods_to_remove = [
        '_apply_golden_chapters_standards',
        '_get_golden_chapters_quality_tier',
        '_generate_golden_chapters_suggestions'
    ]
    
    for method_name in methods_to_remove:
        # 使用文件搜索定位方法
        for i, line in enumerate(lines):
            if f'def {method_name}(' in line:
                # 找到方法的开始和结束
                indent_level = len(line) - len(line.lstrip())
                start_idx = i
                end_idx = i + 1
                
                # 找到下一个同级别的def或类定义
                while end_idx < len(lines):
                    next_line = lines[end_idx]
                    if next_line.strip() and not next_line.startswith(' ' * (indent_level + 4)):
                        if next_line.startswith(' ' * indent_level + 'def '):
                            break
                    end_idx += 1
                
                # 删除这个方法（包括前后空行）
                del lines[start_idx:end_idx]
                print(f"  ✅ {method_name} 已删除")
                break
    
    with open('QualityAssessor.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # 方法5: StagePlanManager._decompose_golden_arc_from_seed
    print("删除方法5: StagePlanManager._decompose_golden_arc_from_seed...")
    with open('StagePlanManager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 删除这个方法
    pattern5 = r'\n    def _decompose_golden_arc_from_seed\(self.*?\n(?=    def |\Z)'
    content = re.sub(pattern5, '\n', content, flags=re.DOTALL)
    
    with open('StagePlanManager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ StagePlanManager._decompose_golden_arc_from_seed 已删除")
    
    print("\n" + "="*60)
    print("✅ 全部5个废弃方法已成功删除!")
    print("="*60)

if __name__ == "__main__":
    delete_deprecated_methods()
