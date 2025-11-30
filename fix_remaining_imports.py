#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自动修复所有剩余文件的导入路径问题"""
import os
import re
from pathlib import Path
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 需要修复的文件列表
files_to_fix = [
    "D:/work6.03/config/config.py",
    "D:/work6.03/config/doubaoconfig.py",
    "D:/work6.03/scripts/main.py",
    "D:/work6.03/web/web_server.py",
]

# sys.path 代码
sys_path_code = '''import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

'''

def has_sys_path_insert(file_path):
    """检查文件是否已经有 sys.path.insert"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return 'sys.path.insert' in content

def get_docstring_and_imports_end(content):
    """找到文档字符串和第一个真实导入语句的位置"""
    lines = content.split('\n')
    insert_position = 0
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 检查文档字符串
        if (stripped.startswith('"""') or stripped.startswith("'''")):
            if not in_docstring:
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
                in_docstring = True
                if docstring_char in stripped[3:]:
                    in_docstring = False
            else:
                in_docstring = False
        
        # 如果不在文档字符串中，检查导入
        if not in_docstring and stripped and not stripped.startswith('#'):
            if stripped.startswith(('import ', 'from ')):
                insert_position = i
                break
    
    # 如果找到导入，就在导入之前插入
    if insert_position > 0:
        # 插入在导入前，且要保留之前的空行和注释
        while insert_position > 0 and (not lines[insert_position - 1].strip() or lines[insert_position - 1].strip().startswith('#')):
            insert_position -= 1
    
    return insert_position

def fix_file(file_path):
    """修复单个文件"""
    if not os.path.exists(file_path):
        print(f"WARNING: File not found: {file_path}")
        return False
    
    if has_sys_path_insert(file_path):
        print(f"OK: Already fixed: {file_path}")
        return True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    insert_pos = get_docstring_and_imports_end(content)
    
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
    for file_path in files_to_fix:
        fix_file(file_path)
    print("\nDone!")
