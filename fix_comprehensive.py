"""Comprehensive fix for encoding corruption and syntax errors"""
import os
import re
import sys
from pathlib import Path

# Set UTF-8 output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def fix_encoding_and_syntax(file_path):
    """Fix encoding issues and broken syntax in Python files"""
    try:
        # Read file with error replacement
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Remove corrupted characters
        content = content.replace('\ufffd', '')

        # Fix incomplete docstrings (common issue from corruption)
        # Pattern for incomplete docstrings
        docstring_pattern = r'"""[^"]*$'
        matches = re.finditer(docstring_pattern, content, re.MULTILINE)

        for match in matches:
            start_pos = match.start()
            end_line_end = content.find('\n', match.end())
            if end_line_end == -1:
                end_line_end = len(content)

            # Find the start of this line
            line_start = content.rfind('\n', 0, start_pos) + 1

            # Get the problematic line
            problematic_line = content[line_start:end_line_end]

            # Check if it's an incomplete docstring
            if '"""' in problematic_line and not problematic_line.rstrip().endswith('"""'):
                # Find the previous non-empty line to see if we should complete the docstring
                prev_line_start = line_start - 1
                while prev_line_start > 0 and content[prev_line_start-1:prev_line_start] == '\n':
                    prev_line_start = content.rfind('\n', 0, prev_line_start-1)

                # Complete or fix the docstring
                if prev_line_start >= 0:
                    prev_line_end = content.find('\n', prev_line_start)
                    prev_line = content[prev_line_start:prev_line_end]

                    # If previous line is a method definition, we need to complete the docstring
                    if 'def ' in prev_line and ('"""' in problematic_line):
                        # Complete the docstring with proper closing
                        content = content[:line_start] + prev_line + content[line_start:end_line_end].replace('"""', '"""', 1) + '"""' + content[end_line_end:]
                    else:
                        # Remove the broken docstring line
                        content = content[:line_start] + content[end_line_end:]

        # Additional syntax fixes for common patterns
        # Fix broken string concatenations
        content = re.sub(r'f"[^"]*$', '', content, flags=re.MULTILINE)

        # Remove any lines with just quotes
        content = re.sub(r'^[ \t]*"[^"]*$\n?', '', content, flags=re.MULTILINE)

        # Save the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

# Files to fix
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
    if full_path.exists():
        if fix_encoding_and_syntax(full_path):
            print(f"Fixed: {file_path}")
            fixed_count += 1
        else:
            print(f"Skipped: {file_path}")
    else:
        print(f"Not found: {file_path}")

print(f"\nTotal files processed: {fixed_count}")
