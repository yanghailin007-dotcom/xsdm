#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix PhaseGenerator.py thread pool issues
"""
import sys

def fix_phase_generator():
    file_path = 'src/core/PhaseGenerator.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the ThreadPoolExecutor usage
    old_code = 'with ThreadPoolExecutor(max_workers=4) as executor:'
    new_code = '''with ManagedThreadPool(
                    max_workers=4, 
                    thread_name_prefix="StagePlan",
                    timeout=300,
                    task_timeout=60
                ) as executor:'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("[OK] Replaced ThreadPoolExecutor with ManagedThreadPool")
    else:
        print("[ERROR] Target code not found")
        idx = content.find('ThreadPoolExecutor')
        if idx != -1:
            print(f"Found ThreadPoolExecutor at position {idx}")
            print("Context:", repr(content[idx-100:idx+150]))
        return False
    
    # Update imports
    old_import = 'from concurrent.futures import ThreadPoolExecutor, as_completed'
    new_import = 'from concurrent.futures import as_completed, TimeoutError\nfrom src.utils.thread_pool_manager import ManagedThreadPool'
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("[OK] Updated imports")
    
    # Add timeout to as_completed
    old_as_completed = 'for future in as_completed(future_to_stage):'
    new_as_completed = 'for future in as_completed(future_to_stage, timeout=300):'
    
    if old_as_completed in content:
        content = content.replace(old_as_completed, new_as_completed)
        print("[OK] Added timeout to as_completed")
    
    # Add timeout to future.result()
    old_result = 'stage_name, stage_plan = future.result()'
    new_result = 'stage_name, stage_plan = future.result(timeout=60)'
    
    if old_result in content:
        content = content.replace(old_result, new_result)
        print("[OK] Added timeout to future.result()")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[DONE] File saved: {file_path}")
    return True

if __name__ == '__main__':
    fix_phase_generator()
