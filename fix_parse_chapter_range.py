#!/usr/bin/env python3
"""修复parse_chapter_range导入"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


import re
from pathlib import Path

files_to_fix = [
    'src/managers/EventManager.py',
    'src/managers/ForeshadowingManager.py',
    'src/managers/GlobalGrowthPlanner.py',
    'src/managers/WritingGuidanceManager.py',
]

for file_path in files_to_fix:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复导入
        content = re.sub(
            r'from src\.utils import parse_chapter_range(?:, is_chapter_in_range)?',
            'from src.managers.StagePlanUtils import parse_chapter_range, is_chapter_in_range',
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'✅ {file_path}')
    except Exception as e:
        print(f'❌ {file_path}: {e}')

print('\n✨ Done!')
