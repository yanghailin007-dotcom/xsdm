#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace Sweep Tool

Performs three operations on the entire workspace:
1. Replace remaining print() with self.logger calls
2. Detect unused methods (lists candidates only, doesn't auto-delete)
3. Delete all task-generated .md files

Usage:
    python workspace_sweep.py              # Dry-run mode (show what would change)
    python workspace_sweep.py --apply      # Actually make changes
    python workspace_sweep.py --verbose    # Show detailed analysis
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple
import argparse

class WorkspaceSweep:
    def __init__(self, workspace_path: str = "."):
        self.workspace = Path(workspace_path)
        self.py_files = list(self.workspace.glob("**/*.py"))
        self.md_files = list(self.workspace.glob("*.md"))
        
        # Config
        self.md_to_delete = {
            "OPTIMIZATION_", "COMPREHENSIVE_", "DEAD_CODE_",
            "QUICK_REFERENCE", "PHASE7_", "EXECUTION_SUMMARY"
        }
        
        self.stats = {
            "prints_found": 0,
            "prints_replaced": 0,
            "unused_methods": 0,
            "md_files_deleted": 0,
            "files_processed": 0
        }

    def should_delete_md(self, filename: str) -> bool:
        """Check if markdown file should be deleted based on task prefixes"""
        for prefix in self.md_to_delete:
            if prefix in filename:
                return True
        return False

    def find_unused_methods(self) -> Dict[str, List[Tuple[str, int]]]:
        """Analyze Python files to find potentially unused methods
        
        Returns dict of {filepath: [(method_name, line_num), ...]}
        """
        unused_methods = {}
        
        for py_file in self.py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                classes = {}
                
                # Find all classes and their methods
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes[node.name] = {}
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                # Skip magic methods, public methods called often
                                if not item.name.startswith('__'):
                                    classes[node.name][item.name] = item.lineno
                
                # Find method calls
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        # Track which methods are called
                        for class_name in classes:
                            if node.attr in classes[class_name]:
                                classes[class_name][node.attr] = None
                
                # Methods with None value are called, others might be unused
                candidates = []
                for class_name, methods in classes.items():
                    for method_name, line_num in methods.items():
                        if line_num is not None and method_name not in ['__init__', 'main']:
                            # Additional filtering: skip if it's in a test file
                            if 'test' not in py_file.name.lower():
                                candidates.append((method_name, line_num))
                
                if candidates:
                    unused_methods[str(py_file)] = candidates
            
            except Exception as e:
                pass  # Silently skip files that can't be parsed
        
        return unused_methods

    def replace_prints_in_file(self, py_file: Path) -> int:
        """Replace print() with self.logger.info() in a Python file
        
        Returns count of replacements made
        """
        with open(py_file, 'r', encoding='utf-8') as f:
            original = f.read()
        
        # Replace print() calls with self.logger.info()
        modified = re.sub(
            r'\bprint\s*\(',
            r'self.logger.info(',
            original
        )
        
        count = original.count('print(') - modified.count('print(')
        
        if count > 0 and '--apply' in sys.argv:
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(modified)
        
        return count

    def process_all_prints(self) -> int:
        """Process all Python files for print replacements"""
        total = 0
        for py_file in self.py_files:
            count = self.replace_prints_in_file(py_file)
            if count > 0:
                action = "Would replace" if '--apply' not in sys.argv else "Replaced"
                print(f"  {action} {count} print() calls in {py_file.name}")
                total += count
                self.stats['files_processed'] += 1
        
        self.stats['prints_replaced'] = total
        return total

    def list_unused_methods(self) -> int:
        """Find and list potentially unused methods"""
        candidates = self.find_unused_methods()
        count = 0
        
        if candidates:
            print("\n  Potentially unused methods (review before deletion):")
            print("  (Note: These are candidates only - manual review recommended)")
            for filepath, methods in candidates.items():
                # Only show if there are candidates
                if methods:
                    print(f"\n    {Path(filepath).name}:")
                    for method_name, line_num in methods[:5]:  # Show first 5
                        print(f"      Line {line_num}: {method_name}()")
                    if len(methods) > 5:
                        print(f"      ... and {len(methods)-5} more")
                    count += len(methods)
        
        self.stats['unused_methods'] = count
        return count

    def delete_generated_md_files(self) -> int:
        """Delete markdown files that were generated during optimization tasks"""
        count = 0
        for md_file in self.md_files:
            if self.should_delete_md(md_file.name):
                if '--apply' in sys.argv:
                    md_file.unlink()
                    print(f"  Deleted: {md_file.name}")
                else:
                    print(f"  Would delete: {md_file.name}")
                count += 1
        
        self.stats['md_files_deleted'] = count
        return count

    def run(self):
        """Execute the full workspace sweep"""
        print("="*70)
        print("WORKSPACE SWEEP TOOL")
        print("="*70)
        
        if '--apply' not in sys.argv:
            print("\n⚠️  DRY-RUN MODE (no changes will be made)")
            print("    Run with --apply to make actual changes\n")
        else:
            print("\n✅ APPLY MODE - Changes will be made\n")
        
        # Step 1: Replace prints
        print("Step 1: Replacing print() with logger...")
        print_count = self.process_all_prints()
        print(f"  Total: {print_count} print() calls to replace")
        
        # Step 2: Detect unused methods
        print("\nStep 2: Detecting potentially unused methods...")
        unused_count = self.list_unused_methods()
        print(f"  Total: {unused_count} potential candidates found")
        
        # Step 3: Delete markdown files
        print("\nStep 3: Deleting generated markdown files...")
        md_count = self.delete_generated_md_files()
        print(f"  Total: {md_count} markdown files to delete")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Print() calls:     {print_count} {'(replaced)' if '--apply' in sys.argv else '(would replace)'}")
        print(f"Unused methods:    {unused_count} (candidates for review)")
        print(f"MD files:          {md_count} {'(deleted)' if '--apply' in sys.argv else '(would delete)'}")
        print(f"Files processed:   {self.stats['files_processed']}")
        
        if '--apply' not in sys.argv:
            print("\n💡 Run with --apply to execute these changes")
        else:
            print("\n✅ All changes applied successfully!")

def main():
    parser = argparse.ArgumentParser(description="Workspace sweep tool")
    parser.add_argument('--apply', action='store_true', help='Actually make changes (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    sweep = WorkspaceSweep(".")
    sweep.run()

if __name__ == "__main__":
    main()
