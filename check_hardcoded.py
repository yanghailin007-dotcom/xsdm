# -*- coding: utf-8 -*-
import os
import re

files_to_check = [
    'web/services/market_driven/chapter_prompt_optimizer_v3.py',
    'web/services/market_driven/prompt_templates.py',
    'web/services/market_driven/tactical_planner.py',
    'web/services/market_driven/stage_chapter_generator.py',
    'web/services/market_driven/stage_review_optimizer.py',
    'web/services/market_driven/chapter_conversation_generator.py',
    'web/services/market_driven/market_driven_conversation.py',
]

pattern = re.compile(r'(?:return\s+)?f?"""#', re.MULTILINE)

print("=" * 80)
print("Hardcoded Prompt Statistics Report")
print("=" * 80)

total = 0
for filepath in files_to_check:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = pattern.findall(content)
        total += len(matches)
        status = "NEEDS MIGRATION" if matches else "MIGRATED"
        print(f"{filepath}: {len(matches)} hardcoded prompts - {status}")

print("=" * 80)
print(f"TOTAL: {total} hardcoded prompts remaining")
print("=" * 80)
