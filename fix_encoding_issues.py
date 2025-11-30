"""Fix encoding corruption in Python files"""
import os
import sys
from pathlib import Path

# Set UTF-8 output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# List of files with encoding issues
problem_files = [
    "src/core/APIClient.py",
    "src/core/ContentGenerator.py",
    "src/core/MockAPIClient.py",
    "src/core/NovelGenerator.py",
    "src/core/ProjectManager.py",
    "src/core/QualityAssessor.py",
    "src/managers/ElementTimingPlanner.py",
    "src/managers/EventDrivenManager.py",
    "src/managers/StagePlanManager.py",
    "src/managers/StagePlanUtils.py",
    "src/managers/WorldStateManager.py",
    "src/prompts/AnalysisPrompts.py",
    "src/prompts/BasePrompts.py",
    "src/prompts/PlanningPrompts.py",
    "src/prompts/WorldviewPrompts.py",
    "src/prompts/WritingPrompts.py",
]

fixed_count = 0
for file_path in problem_files:
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"File not found: {file_path}")
        continue

    try:
        # Read file with error replacement
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Replace corrupted characters (U+FFFD) with empty string
        clean_content = content.replace('\ufffd', '')

        # Save if content changed
        if clean_content != content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            print(f"Fixed: {file_path}")
            fixed_count += 1
        else:
            print(f"OK: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print(f"\nTotal files fixed: {fixed_count}")
