#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix indentation issue"""

def fix_indent():
    file_path = 'src/core/PhaseGenerator.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the broken import line
    old = '''            from concurrent.futures import as_completed, TimeoutError
from src.utils.thread_pool_manager import ManagedThreadPool
            
            import threading'''
    
    new = '''            from concurrent.futures import as_completed, TimeoutError
            from src.utils.thread_pool_manager import ManagedThreadPool
            import threading'''
    
    if old in content:
        content = content.replace(old, new)
        print("[OK] Fixed indentation")
    else:
        print("[WARN] Pattern not found, checking...")
        # Check if already fixed
        if 'from src.utils.thread_pool_manager import ManagedThreadPool' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from src.utils.thread_pool_manager' in line:
                    print(f"Line {i+1}: {repr(line)}")
        return
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[DONE] File saved")

if __name__ == '__main__':
    fix_indent()
