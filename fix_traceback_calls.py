#!/usr/bin/env python3
"""
Fix traceback.print_exc() calls in Python files to use safe logger method
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


import re
import os
from pathlib import Path

def fix_traceback_in_file(file_path: str) -> bool:
    """Fix traceback.print_exc() calls in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if file has logger imports
        if 'from src.utils.logger import get_logger' not in content and 'get_logger' not in content:
            return False  # Skip files without logger

        # Find logger instance (common patterns)
        logger_patterns = [
            r'self\.logger\s*=\s*get_logger\(["\'][^"\']*["\']\)',
            r'logger\s*=\s*get_logger\(["\'][^"\']*["\']\)',
            r'self\.logger\s*=.*Logger\(.*\)',
            r'logger\s*=.*Logger\(.*\)'
        ]

        has_logger = any(re.search(pattern, content) for pattern in logger_patterns)
        if not has_logger:
            return False

        # Replace traceback.print_exc() with appropriate logger method
        # First, try to determine logger variable name
        logger_var = 'logger'  # default

        # Try to find specific logger variable
        for pattern in logger_patterns:
            match = re.search(pattern, content)
            if match:
                # Extract variable name from match
                match_str = match.group()
                if '.' in match_str:
                    parts = match_str.split('.')
                    if len(parts) >= 2:
                        logger_var = parts[0]
                break

        # Replace the calls
        original_count = content.count('traceback.print_exc()')
        if original_count == 0:
            return False

        # Simple replacement
        content = content.replace('traceback.print_exc()', f'{logger_var}.safe_print_traceback()')

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Fixed {original_count} traceback.print_exc() calls in {file_path} using logger variable '{logger_var}'")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all Python files"""
    base_dir = Path("D:\\work6.03\\src")

    # Find all Python files
    python_files = list(base_dir.rglob("*.py"))

    fixed_count = 0
    for py_file in python_files:
        if fix_traceback_in_file(str(py_file)):
            fixed_count += 1

    print(f"\nDone! Fixed traceback.print_exc() in {fixed_count} files.")

if __name__ == "__main__":
    main()