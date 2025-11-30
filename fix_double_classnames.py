#!/usr/bin/env python3
"""修复所有双重类名引用（如 APIClient.APIClient -> APIClient）"""

import re
from pathlib import Path

BASE_DIR = Path('.')
count = 0

# 需要修复的模式
replacements = [
    (r'APIClient\.APIClient', 'APIClient'),
    (r'NovelGenerator\.NovelGenerator', 'NovelGenerator'),
    (r'QualityAssessor\.QualityAssessor', 'QualityAssessor'),
    (r'ContentGenerator\.ContentGenerator', 'ContentGenerator'),
    (r'GenerationContext\.GenerationContext', 'GenerationContext'),
]

for py_file in BASE_DIR.rglob('src/**/*.py'):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(content)
            rel_path = py_file.relative_to(BASE_DIR)
            print(f'✅ {rel_path}')
            count += 1
    except Exception as e:
        print(f'❌ {py_file}: {e}')

print(f'\n✨ Total fixed: {count} files')
