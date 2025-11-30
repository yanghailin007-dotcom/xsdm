#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复所有剩余文件的导入路径问题"""
import os
import re
from pathlib import Path
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 所有需要修复的文件（从 grep 结果的71个文件，排除已经有 sys.path 的35个）
files_to_fix = [
    "D:/work6.03/fix_traceback_calls.py",
    "D:/work6.03/verify_all_fixes.py",
    "D:/work6.03/test_all_context_fixes.py",
    "D:/work6.03/test_title_generation_fix.py",
    "D:/work6.03/test_chapter_title_fix.py",
    "D:/work6.03/test_intelligent_compression_comparison.py",
    "D:/work6.03/test_generation_pipeline.py",
    "D:/work6.03/test_mock.py",
    "D:/work6.03/reorganize_project.py",
    "D:/work6.03/mock_test.py",
    "D:/work6.03/fix_imports.py",
    "D:/work6.03/update_imports.py",
    "D:/work6.03/update_paths.py",
    "D:/work6.03/fix_parse_chapter_range.py",
    "D:/work6.03/validate_fixes.py",
]

# sys.path 代码
sys_path_code = '''import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

'''

def has_sys_path_insert(file_path):
    """检查文件是否已经有 sys.path.insert"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return 'sys.path.insert' in content
    except:
        return False

def get_insert_position(content):
    """找到第一个 from src. 或 import 语句的位置"""
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(('from src.', 'import ')):
            # 回退找到非空行和非注释行
            while i > 0 and (not lines[i-1].strip() or lines[i-1].strip().startswith('#')):
                i -= 1
            return i
    return 0

def fix_file(file_path):
    """修复单个文件"""
    if not os.path.exists(file_path):
        return False
    
    if has_sys_path_insert(file_path):
        return True
    
    # 检查文件是否含有 from src
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from src.' not in content:
        return True  # 不需要修复
    
    lines = content.split('\n')
    insert_pos = get_insert_position(content)
    
    # 在找到的位置插入 sys.path 代码
    sys_path_lines = sys_path_code.rstrip('\n').split('\n')
    
    # 在插入位置之前插入代码
    for i in range(len(sys_path_lines)):
        lines.insert(insert_pos + i, sys_path_lines[i])
    
    # 在 sys.path 代码后添加一个空行
    lines.insert(insert_pos + len(sys_path_lines), '')
    
    new_content = '\n'.join(lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"FIXED: {file_path}")
    return True

if __name__ == "__main__":
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_file(file_path):
            fixed_count += 1
    print(f"\nDone! Fixed {fixed_count} files")
