#!/usr/bin/env python3
"""全局修复所有导入错误"""

import os
import re
from pathlib import Path

BASE_DIR = Path('.')
count = 0

# 定义所有需要修复的相对导入
fixes = [
    (r'^import WorldStateManager$', 'from src.managers.WorldStateManager import WorldStateManager'),
    (r'^from WorldStateManager import', 'from src.managers.WorldStateManager import'),
    (r'^import GlobalGrowthPlanner$', 'from src.managers.GlobalGrowthPlanner import GlobalGrowthPlanner'),
    (r'^from GlobalGrowthPlanner import', 'from src.managers.GlobalGrowthPlanner import'),
    (r'^import ElementTimingPlanner$', 'from src.managers.ElementTimingPlanner import ElementTimingPlanner'),
    (r'^from ElementTimingPlanner import', 'from src.managers.ElementTimingPlanner import'),
    (r'^import ForeshadowingManager$', 'from src.managers.ForeshadowingManager import ForeshadowingManager'),
    (r'^from ForeshadowingManager import', 'from src.managers.ForeshadowingManager import'),
    (r'^import ProjectManager$', 'from src.core.ProjectManager import ProjectManager'),
    (r'^from ProjectManager import', 'from src.core.ProjectManager import'),
    (r'^import EventManager$', 'from src.managers.EventManager import EventManager'),
    (r'^from EventManager import', 'from src.managers.EventManager import'),
    (r'^import StagePlanManager$', 'from src.managers.StagePlanManager import StagePlanManager'),
    (r'^from StagePlanManager import', 'from src.managers.StagePlanManager import'),
    (r'^import QualityAssessor$', 'from src.core.QualityAssessor import QualityAssessor'),
    (r'^from QualityAssessor import', 'from src.core.QualityAssessor import'),
    (r'^import WritingGuidanceManager$', 'from src.managers.WritingGuidanceManager import WritingGuidanceManager'),
    (r'^from WritingGuidanceManager import', 'from src.managers.WritingGuidanceManager import'),
    (r'^import EmotionalBlueprintManager$', 'from src.managers.EmotionalBlueprintManager import EmotionalBlueprintManager'),
    (r'^from EmotionalBlueprintManager import', 'from src.managers.EmotionalBlueprintManager import'),
    (r'^import NovelGenerator$', 'from src.core.NovelGenerator import NovelGenerator'),
    (r'^from NovelGenerator import', 'from src.core.NovelGenerator import'),
    (r'^import ContentGenerator$', 'from src.core.ContentGenerator import ContentGenerator'),
    (r'^from ContentGenerator import', 'from src.core.ContentGenerator import'),
    (r'^import EmotionalPlanManager$', 'from src.managers.EmotionalPlanManager import EmotionalPlanManager'),
    (r'^from EmotionalPlanManager import', 'from src.managers.EmotionalPlanManager import'),
    (r'^import EventBus$', 'from src.managers.EventBus import EventBus'),
    (r'^from EventBus import', 'from src.managers.EventBus import'),
    (r'^import RomancePatternManager$', 'from src.managers.RomancePatternManager import RomancePatternManager'),
    (r'^from RomancePatternManager import', 'from src.managers.RomancePatternManager import'),
]

for py_file in BASE_DIR.rglob('src/**/*.py'):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if content != original:
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(content)
            rel_path = py_file.relative_to(BASE_DIR)
            print(f'✅ {rel_path}')
            count += 1
    except Exception as e:
        print(f'❌ {py_file}: {e}')

print(f'\n✨ Total fixed: {count} files')

