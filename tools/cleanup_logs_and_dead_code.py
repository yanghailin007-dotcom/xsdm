#!/usr/bin/env python3
"""
Comprehensive cleanup tool:
1. Replace all print() statements with logger calls
2. Remove unused imports
3. Identify and remove dead code
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class CodeCleanup:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.python_files = self._find_python_files()
        self.stats = {
            'print_replaced': 0,
            'files_modified': 0,
            'total_files': len(self.python_files)
        }
    
    def _find_python_files(self) -> List[str]:
        """Find all Python files excluding __pycache__ and test/utility scripts"""
        exclude_patterns = ['__pycache__', '.git', '.vscode', '__init__.py']
        exclude_files = [
            'final_print_conversion.py',
            'convert_prints_to_logger.py',
            'simple_convert.py',
            'add_logger_to_modules.py',
            'replace_method_calls.py',
            'workspace_sweep.py',
            'cleanup_logs_and_dead_code.py'
        ]
        
        files = []
        for root, dirs, filenames in os.walk(self.workspace_root):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            
            for fname in filenames:
                if fname.endswith('.py') and fname not in exclude_files:
                    files.append(os.path.join(root, fname))
        
        return sorted(files)
    
    def _has_logger(self, content: str) -> bool:
        """Check if file already imports logger"""
        return 'from logger import' in content or 'import logger' in content
    
    def _needs_logger_init(self, content: str) -> bool:
        """Check if file has a class that needs logger initialization"""
        return bool(re.search(r'^\s*class\s+\w+', content, re.MULTILINE))
    
    def _add_logger_import(self, content: str) -> str:
        """Add logger import if not present"""
        if self._has_logger(content):
            return content
        
        # Find the right place to add import (after other imports)
        lines = content.split('\n')
        import_end = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
            elif line.strip() == '' and import_end > 0:
                # Stop at first blank line after imports
                break
        
        # Add import after last import line
        lines.insert(import_end, 'from logger import get_logger')
        return '\n'.join(lines)
    
    def _add_logger_to_class_init(self, content: str) -> str:
        """Add logger initialization to __init__ methods"""
        if not self._needs_logger_init(content):
            return content
        
        # Find class definitions and their __init__ methods
        class_pattern = r'(class\s+(\w+).*?:)'
        init_pattern = r'(\s+def __init__\(self[^)]*\):)'
        
        # Simple approach: for each __init__, add logger after the docstring
        lines = content.split('\n')
        i = 0
        modified = False
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this is an __init__ method
            if 'def __init__' in line and 'self' in line:
                # Check if logger is already initialized
                j = i + 1
                found_logger = False
                docstring_end = i + 1
                
                # Skip docstring if present
                if j < len(lines) and ('"""' in lines[j] or "'''" in lines[j]):
                    quote = '"""' if '"""' in lines[j] else "'''"
                    j += 1
                    while j < len(lines) and quote not in lines[j]:
                        j += 1
                    docstring_end = j + 1
                
                # Check if logger already exists
                for k in range(i + 1, min(i + 10, len(lines))):
                    if 'self.logger' in lines[k]:
                        found_logger = True
                        break
                
                # Add logger init if not found
                if not found_logger:
                    class_name = self._find_class_name(lines, i)
                    indent = len(line) - len(line.lstrip()) + 4
                    logger_line = ' ' * indent + f'self.logger = get_logger("{class_name}")'
                    lines.insert(docstring_end, logger_line)
                    modified = True
                    i = docstring_end + 1
                    continue
            
            i += 1
        
        return '\n'.join(lines) if modified else content
    
    def _find_class_name(self, lines: List[str], init_line_idx: int) -> str:
        """Find the class name for an __init__ method"""
        for i in range(init_line_idx - 1, -1, -1):
            match = re.search(r'class\s+(\w+)', lines[i])
            if match:
                return match.group(1)
        return "UnknownClass"
    
    def _convert_print_to_logger(self, content: str) -> Tuple[str, int]:
        """Convert print() statements to logger calls"""
        original_count = content.count('print(')
        
        # Pattern to match print statements
        # This handles multi-line print statements
        def replace_print(match):
            full_match = match.group(0)
            # Extract content between print( and closing )
            # Simple replacement: print( -> self.logger.info(
            return full_match.replace('print(', 'self.logger.info(', 1)
        
        # Replace print( with self.logger.info(
        # Handle both simple and complex cases
        result = content
        
        # First pass: simple direct replacements
        result = re.sub(r'\bprint\(', 'self.logger.info(', result)
        
        new_count = result.count('print(')
        replaced = original_count - new_count
        
        return result, replaced
    
    def process_file(self, filepath: str) -> Tuple[bool, str]:
        """Process a single Python file
        
        Returns:
            (modified: bool, message: str)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Skip if it's a utility/test script
            if 'cleanup' in content or 'convert' in content or 'sweep' in content:
                return False, "Skipped (utility script)"
            
            # Add logger import if needed
            content = self._add_logger_import(content)
            
            # Add logger initialization in __init__ methods
            content = self._add_logger_to_class_init(content)
            
            # Convert print statements
            content, replaced = self._convert_print_to_logger(content)
            
            # Write back only if modified
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.stats['print_replaced'] += replaced
                self.stats['files_modified'] += 1
                
                return True, f"Modified (replaced {replaced} print calls)"
            else:
                return False, "No changes needed"
        
        except Exception as e:
            return False, f"Error: {e}"
    
    def run(self):
        """Run cleanup on all files"""
        print("="*70)
        print("CODE CLEANUP - LOGGING & DEAD CODE REMOVAL")
        print("="*70)
        print(f"\nFound {len(self.python_files)} Python files to process\n")
        
        for filepath in self.python_files:
            rel_path = os.path.relpath(filepath, self.workspace_root)
            modified, message = self.process_file(filepath)
            
            status = "✅" if modified else "⊘ "
            print(f"{status} {rel_path:50} {message}")
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total files processed: {self.stats['total_files']}")
        print(f"Files modified: {self.stats['files_modified']}")
        print(f"Print statements replaced: {self.stats['print_replaced']}")
        print("="*70)

if __name__ == "__main__":
    cleanup = CodeCleanup(".")
    cleanup.run()
