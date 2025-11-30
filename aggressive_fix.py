"""Advanced encoding and syntax fixer for Python files"""
import re
import sys
from pathlib import Path

# Set UTF-8 output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def fix_python_file(file_path):
    """Comprehensively fix encoding and syntax issues"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Remove corruption character
            line = line.replace('\ufffd', '')

            # Fix incomplete docstrings at end of function definitions
            if 'def ' in line and i + 1 < len(lines):
                # Ensure function has proper body
                next_line = lines[i + 1] if i + 1 < len(lines) else ''
                if next_line.strip().startswith('"""'):
                    # Next line is a docstring
                    docstring_line = next_line.replace('\ufffd', '')
                    # Check if docstring is complete
                    if docstring_line.count('"""') == 1:
                        # Incomplete docstring - close it
                        docstring_line = docstring_line.rstrip() + '"""' + '\n'
                    new_lines.append(line)
                    new_lines.append(docstring_line)
                    i += 2
                    continue

            # Fix incomplete string literals ending with f"
            if line.rstrip().endswith(('f"', 'f"', 'r"', '"')) and '"""' not in line:
                # Check if this is supposed to be a complete statement
                if not re.search(r'[=\(\[]', line) or not re.search(r'[)\]]', line):
                    # Likely incomplete, try to fix
                    if line.rstrip().endswith(('f"', 'r"', '"')):
                        # Add closing quote if missing
                        if line.count('"') % 2 == 1:
                            line = line.rstrip() + '"' + '\n'

            # Fix broken f-strings in log statements
            if 'self.logger.info(f"' in line and not line.rstrip().endswith(('"', ')')):
                # This line is likely broken, try to fix
                line = re.sub(r'f"[^"]*$', '', line)
                if line.strip() and not line.strip().endswith(('#', '(')):
                    new_lines.append(line)
                    i += 1
                    continue

            # Skip lines that are just closing quotes or corrupted
            if line.strip() in ('"', '"""', "'''", '?', '??'):
                i += 1
                continue

            # Add the line
            if line.strip():  # Only add non-empty lines after cleaning
                new_lines.append(line)

            i += 1

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

# List of problem files
problem_files = [
    "src/core/NovelGenerator.py",
    "src/core/APIClient.py",
    "src/core/ContentGenerator.py",
    "src/core/MockAPIClient.py",
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

for file_path in problem_files:
    full_path = Path(file_path)
    if full_path.exists():
        if fix_python_file(full_path):
            print(f"Fixed: {file_path}")
        else:
            print(f"Error fixing: {file_path}")
    else:
        print(f"Not found: {file_path}")

print("\nDone!")
