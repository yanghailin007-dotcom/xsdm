#!/usr/bin/env python3
"""
Delete 5 deprecated methods from the codebase
"""
import re

def delete_all_deprecated_methods():
    """Delete all 5 identified deprecated methods"""
    
    print("开始删除5个废弃方法...")
    print("="*60)
    
    # Method 1: ContentGenerator._get_golden_chapter_design_variant
    print("\n[1/5] 删除 ContentGenerator._get_golden_chapter_design_variant...")
    try:
        with open('ContentGenerator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and remove the method
        pattern = r'\n    def _get_golden_chapter_design_variant\(self.*?\n        return ""\n        \n'
        new_content = re.sub(pattern, '\n', content, flags=re.DOTALL)
        
        if new_content != content:
            with open('ContentGenerator.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("      ✅ 已删除")
        else:
            print("      ❌ 未找到该方法")
    except Exception as e:
        print(f"      ❌ 出错: {e}")
    
    # Methods 2-4: QualityAssessor methods
    qa_methods = [
        '_apply_golden_chapters_standards',
        '_get_golden_chapters_quality_tier',
        '_generate_golden_chapters_suggestions'
    ]
    
    try:
        with open('QualityAssessor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        for i, method_name in enumerate(qa_methods, start=2):
            print(f"\n[{i}/5] 删除 QualityAssessor.{method_name}...")
            # Find the method pattern
            pattern = r'\n    def ' + method_name + r'\(self.*?\n        .*?(?=\n    def |\Z)'
            matches = list(re.finditer(pattern, content, flags=re.DOTALL))
            
            if matches:
                match = matches[0]
                # Get the method and related whitespace
                start = match.start()
                end = match.end()
                
                # Remove from first newline to preserve formatting
                if start > 0 and content[start-1] == '\n':
                    # content = content[:start] + content[end:]
                    pattern2 = r'\n    def ' + method_name + r'\(self[^}]*?\n    def |\n    def ' + method_name + r'\(self[^}]*?\Z'
                    content = re.sub(pattern2, '\n    def ', content, flags=re.DOTALL, count=1)
                
                print(f"      ✅ 已删除")
            else:
                print(f"      ❌ 未找到该方法")
        
        with open('QualityAssessor.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
    except Exception as e:
        print(f"      ❌ 出错: {e}")
    
    # Method 5: StagePlanManager._decompose_golden_arc_from_seed
    print(f"\n[5/5] 删除 StagePlanManager._decompose_golden_arc_from_seed...")
    try:
        with open('StagePlanManager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'\n    def _decompose_golden_arc_from_seed\(self.*?\n(?=    def |\Z)'
        new_content = re.sub(pattern, '\n', content, flags=re.DOTALL)
        
        if new_content != content:
            with open('StagePlanManager.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("      ✅ 已删除")
        else:
            print("      ❌ 未找到该方法")
    except Exception as e:
        print(f"      ❌ 出错: {e}")
    
    print("\n" + "="*60)
    print("✅ 废弃方法删除完成!")
    print("="*60)

if __name__ == "__main__":
    delete_all_deprecated_methods()
