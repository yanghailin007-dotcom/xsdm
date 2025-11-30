#!/usr/bin/env python3
"""
Remove unused imports from Python files using Pylance refactoring
"""

import os
import subprocess
from pathlib import Path

def remove_unused_imports(workspace_root: str = "."):
    """Remove unused imports from all Python files"""
    
    python_files = []
    exclude_patterns = ['__pycache__', '.git', '.vscode', '__init__.py']
    exclude_files = ['cleanup_logs_and_dead_code.py', 'workspace_sweep.py', 'test_helper_classes.py']
    
    # Find all Python files
    for root, dirs, filenames in os.walk(workspace_root):
        dirs[:] = [d for d in dirs if d not in exclude_patterns]
        for fname in filenames:
            if fname.endswith('.py') and fname not in exclude_files:
                python_files.append(os.path.join(root, fname))
    
    print("="*70)
    print("REMOVING UNUSED IMPORTS")
    print("="*70)
    print(f"\nFound {len(python_files)} Python files\n")
    
    modified_count = 0
    
    for filepath in sorted(python_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()
            
            # Use Pylance refactoring to remove unused imports
            # This is done via simple analysis
            lines = original.split('\n')
            imports_to_check = {}
            
            # Collect all imports
            for i, line in enumerate(lines):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    imports_to_check[i] = line
            
            # Check which imports are actually used
            content_without_imports = '\n'.join(
                [lines[i] for i in range(len(lines)) if i not in imports_to_check]
            )
            
            modified = False
            new_lines = []
            
            for i, line in enumerate(lines):
                if i not in imports_to_check:
                    new_lines.append(line)
                else:
                    # Parse import
                    import_match = None
                    if line.strip().startswith('from '):
                        # from X import Y
                        parts = line.split()
                        if len(parts) >= 4:
                            imported_name = parts[-1]
                            import_match = imported_name
                    elif line.strip().startswith('import '):
                        # import X [as Y]
                        parts = line.split()
                        if len(parts) >= 2:
                            import_match = parts[1].split('.')[-1]
                    
                    # Check if import is used
                    if import_match and import_match in content_without_imports:
                        new_lines.append(line)
                    elif import_match == 'logger' or 'get_logger' in line:
                        # Keep logger imports
                        new_lines.append(line)
                    else:
                        modified = True
                        # Skip this line (unused import)
            
            result = '\n'.join(new_lines)
            
            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result)
                modified_count += 1
                rel_path = os.path.relpath(filepath, workspace_root)
                print(f"✅ {rel_path:50} Cleaned unused imports")
        
        except Exception as e:
            rel_path = os.path.relpath(filepath, workspace_root)
            print(f"⊘  {rel_path:50} Error: {str(e)[:30]}")
    
    print("\n" + "="*70)
    print(f"Files cleaned: {modified_count}")
    print("="*70)

if __name__ == "__main__":
    remove_unused_imports(".")
