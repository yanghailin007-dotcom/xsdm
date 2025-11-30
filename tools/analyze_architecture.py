#!/usr/bin/env python3
"""
代码架构梳理和清理工具
分析小说生成流程，删除废弃的方法和类
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class NovelGenerationAnalyzer:
    """分析小说生成流程"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.py_files = list(self.workspace.glob("**/*.py"))
        self.deprecated_items = []
        self.unused_methods = defaultdict(list)
        self.class_hierarchy = {}
        
    def analyze_all_files(self):
        """分析所有文件"""
        print("=" * 80)
        print("小说生成流程架构分析")
        print("=" * 80)
        
        for py_file in sorted(self.py_files):
            if self._should_skip_file(py_file):
                continue
            
            self.analyze_file(py_file)
        
        self._print_analysis_results()
    
    def _should_skip_file(self, py_file: Path) -> bool:
        """检查是否应该跳过该文件"""
        skip_patterns = [
            '__pycache__', '.git', '.vscode', 'tests',
            'cleanup', 'sweep', 'generate_', 'remove_unused'
        ]
        path_str = str(py_file)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def analyze_file(self, py_file: Path):
        """分析单个文件"""
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # 寻找已弃用的方法/类
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    # 检查docstring中的deprecated标记
                    docstring = ast.get_docstring(node)
                    if docstring and ('deprecated' in docstring.lower() or '废弃' in docstring or '已弃用' in docstring):
                        self.deprecated_items.append({
                            'file': str(py_file),
                            'name': node.name,
                            'type': 'Class' if isinstance(node, ast.ClassDef) else 'Function',
                            'line': node.lineno,
                            'docstring': docstring[:100]
                        })
                    
                    # 检查名称中的deprecated标记
                    if 'deprecated' in node.name.lower() or 'old' in node.name.lower():
                        self.deprecated_items.append({
                            'file': str(py_file),
                            'name': node.name,
                            'type': 'Class' if isinstance(node, ast.ClassDef) else 'Function',
                            'line': node.lineno,
                            'docstring': '(名称标记为deprecated/old)'
                        })
            
            # 记录类和方法
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.class_hierarchy[node.name] = {
                        'file': str(py_file),
                        'methods': [],
                        'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
                    }
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            self.class_hierarchy[node.name]['methods'].append(item.name)
        
        except Exception as e:
            pass
    
    def _print_analysis_results(self):
        """打印分析结果"""
        print("\n" + "=" * 80)
        print("📋 已弃用项目清单")
        print("=" * 80)
        
        if self.deprecated_items:
            for item in self.deprecated_items:
                print(f"\n❌ {item['type']}: {item['name']}")
                print(f"   文件: {item['file']}")
                print(f"   行号: {item['line']}")
                print(f"   说明: {item['docstring']}")
        else:
            print("✅ 未发现明确标记为废弃的项目")
        
        print("\n" + "=" * 80)
        print("📊 主要类和方法统计")
        print("=" * 80)
        
        # 统计主要类
        main_classes = [
            'NovelGenerator', 'ContentGenerator', 'APIClient', 'QualityAssessor',
            'ProjectManager', 'StagePlanManager', 'EventManager', 'WorldStateManager',
            'ForeshadowingManager', 'GlobalGrowthPlanner', 'RomancePatternManager'
        ]
        
        for class_name in main_classes:
            if class_name in self.class_hierarchy:
                info = self.class_hierarchy[class_name]
                print(f"\n✅ {class_name}")
                print(f"   文件: {info['file']}")
                print(f"   方法数: {len(info['methods'])}")
                if len(info['methods']) <= 10:
                    for method in info['methods'][:5]:
                        print(f"      - {method}")
                    if len(info['methods']) > 5:
                        print(f"      ... 还有 {len(info['methods']) - 5} 个方法")

def identify_deprecated_patterns(workspace_root: str = "."):
    """识别废弃的代码模式"""
    workspace = Path(workspace_root)
    
    patterns = {
        'old_method': r'def\s+\w*old\w*\(',
        'unused_import': r'import.*#\s*(unused|废弃)',
        'dead_code': r'^\s*#\s*(old|废弃|已弃用)',
        'todo_cleanup': r'#\s*TODO.*cleanup|#\s*FIXME.*remove'
    }
    
    print("\n" + "=" * 80)
    print("🔍 寻找废弃代码模式")
    print("=" * 80)
    
    found_patterns = defaultdict(list)
    
    for py_file in workspace.glob("**/*.py"):
        if '__pycache__' in str(py_file) or '.git' in str(py_file):
            continue
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern_name, pattern in patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            found_patterns[pattern_name].append({
                                'file': py_file.name,
                                'line': line_num,
                                'content': line.strip()[:60]
                            })
        except:
            pass
    
    for pattern_name, matches in found_patterns.items():
        if matches:
            print(f"\n{pattern_name}:")
            for match in matches[:5]:
                print(f"  {match['file']}:{match['line']} - {match['content']}")
            if len(matches) > 5:
                print(f"  ... 还有 {len(matches) - 5} 个匹配")

def print_writing_pipeline(workspace_root: str = "."):
    """打印小说写作流程"""
    print("\n" + "=" * 80)
    print("📖 小说写作流程")
    print("=" * 80)
    
    pipeline = [
        ("1. 用户输入", "main.py", "获取创意种子"),
        ("2. 方案生成", "NovelGenerator.generate_novel_plan", "生成小说方案"),
        ("3. 阶段规划", "StagePlanManager", "规划各阶段情节"),
        ("4. 事件设计", "EventManager", "设计重大事件"),
        ("5. 成长规划", "GlobalGrowthPlanner", "规划主角成长"),
        ("6. 伏笔管理", "ForeshadowingManager", "管理伏笔和回应"),
        ("7. 内容生成", "ContentGenerator.generate_chapter_content", "生成章节内容"),
        ("8. 质量评估", "QualityAssessor.assess_quality", "评估章节质量"),
        ("9. 文本优化", "ContentGenerator.refine_chapter_content", "优化章节内容"),
        ("10. 项目保存", "ProjectManager.save_single_chapter", "保存章节文件"),
    ]
    
    for step, component, description in pipeline:
        print(f"\n{step}: {description}")
        print(f"   组件: {component}")

if __name__ == "__main__":
    analyzer = NovelGenerationAnalyzer(".")
    analyzer.analyze_all_files()
    
    identify_deprecated_patterns(".")
    
    print_writing_pipeline(".")
    
    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print("=" * 80)
