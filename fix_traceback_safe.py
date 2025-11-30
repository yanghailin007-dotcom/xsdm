#!/usr/bin/env python3
"""
Safely fix traceback.print_exc() calls in NovelGenerator.py
"""

import re

def fix_novel_generator():
    """Fix traceback calls in NovelGenerator.py"""

    file_path = "D:\\work6.03\\src\\core\\NovelGenerator.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count replacements
    count_before = content.count('traceback.print_exc()')
    print(f"Found {count_before} traceback.print_exc() calls")

    # Simple replacement - all use self.logger
    content = content.replace('traceback.print_exc()', 'self.logger.safe_print_traceback()')

    count_after = content.count('traceback.print_exc()')
    print(f"After replacement: {count_after} traceback.print_exc() calls remaining")
    print(f"Replaced: {count_before - count_after}")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Fixed {file_path}")

if __name__ == "__main__":
    fix_novel_generator()
