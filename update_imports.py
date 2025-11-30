"""
自动更新导入路径脚本
根据新的目录结构更新所有 Python 文件中的导入语句
"""

import re
from pathlib import Path
from typing import List, Tuple

# 定义导入映射规则
IMPORT_MAPPINGS = [
    # (原始正则表达式, 替换为)
    (r'^from\s+NovelGenerator\s+import', 'from src.core.NovelGenerator import'),
    (r'^from\s+APIClient\s+import', 'from src.core.APIClient import'),
    (r'^from\s+ContentGenerator\s+import', 'from src.core.ContentGenerator import'),
    (r'^from\s+QualityAssessor\s+import', 'from src.core.QualityAssessor import'),
    (r'^from\s+ProjectManager\s+import', 'from src.core.ProjectManager import'),
    (r'^from\s+Contexts\s+import', 'from src.core.Contexts import'),
    (r'^from\s+EventBus\s+import', 'from src.core.EventBus import'),

    (r'^import\s+EventDrivenManager', 'from src.managers import EventDrivenManager'),
    (r'^import\s+EventManager', 'from src.managers import EventManager'),
    (r'^import\s+EmotionalBlueprintManager', 'from src.managers import EmotionalBlueprintManager'),
    (r'^import\s+EmotionalPlanManager', 'from src.managers import EmotionalPlanManager'),
    (r'^import\s+ForeshadowingManager', 'from src.managers import ForeshadowingManager'),
    (r'^import\s+GlobalGrowthPlanner', 'from src.managers import GlobalGrowthPlanner'),
    (r'^import\s+RomancePatternManager', 'from src.managers import RomancePatternManager'),
    (r'^import\s+StagePlanManager', 'from src.managers import StagePlanManager'),
    (r'^import\s+WorldStateManager', 'from src.managers import WorldStateManager'),
    (r'^import\s+WritingGuidanceManager', 'from src.managers import WritingGuidanceManager'),
    (r'^import\s+ElementTimingPlanner', 'from src.managers import ElementTimingPlanner'),

    (r'^from\s+Prompts\s+import', 'from src.prompts.Prompts import'),
    (r'^from\s+BasePrompts\s+import', 'from src.prompts.BasePrompts import'),
    (r'^from\s+AnalysisPrompts\s+import', 'from src.prompts.AnalysisPrompts import'),
    (r'^from\s+OptimizationPrompts\s+import', 'from src.prompts.OptimizationPrompts import'),
    (r'^from\s+PlanningPrompts\s+import', 'from src.prompts.PlanningPrompts import'),
    (r'^from\s+WorldviewPrompts\s+import', 'from src.prompts.WorldviewPrompts import'),
    (r'^from\s+WritingPrompts\s+import', 'from src.prompts.WritingPrompts import'),

    (r'^from\s+logger\s+import', 'from src.utils.logger import'),
    (r'^from\s+utils\s+import', 'from src.utils.utils import'),
    (r'^from\s+config\s+import', 'from config.config import'),
    (r'^import\s+utils\s+$', 'import src.utils.utils as utils'),
]

# 路径配置映射
PATH_MAPPINGS = [
    (r'"小说项目"', '"data/projects"'),
    (r"'小说项目'", "'data/projects'"),
    (r'"novel_ideas\.txt"', '"data/creative_ideas/novel_ideas.txt"'),
    (r"'novel_ideas\.txt'", "'data/creative_ideas/novel_ideas.txt'"),
    (r'"quality_data"', '"data/quality_data"'),
    (r"'quality_data'", "'data/quality_data'"),
    (r'"generated_images"', '"data/generated_images"'),
    (r"'generated_images'", "'data/generated_images'"),
    (r'"debug_responses"', '"data/debug_responses"'),
    (r"'debug_responses'", "'data/debug_responses'"),
    (r'"template_folder=\'templates\'"', '"template_folder=\'web/templates\'"'),
    (r'"static_folder=\'static\'"', '"static_folder=\'web/static\'"'),
    (r"template_folder='templates'", "template_folder='web/templates'"),
    (r"static_folder='static'", "static_folder='web/static'"),
]


def update_imports_in_file(file_path: Path) -> Tuple[bool, int]:
    """
    更新单个文件中的导入语句
    返回: (是否修改, 修改数量)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        changes_count = 0

        # 应用导入映射
        for pattern, replacement in IMPORT_MAPPINGS:
            new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            if count > 0:
                content = new_content
                changes_count += count

        # 应用路径映射
        for pattern, replacement in PATH_MAPPINGS:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changes_count += count

        # 如果有变更，写回文件
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, changes_count
        return False, 0

    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        return False, 0


def find_python_files(root_path: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """找到所有 Python 文件"""
    if exclude_dirs is None:
        exclude_dirs = ['.git', '.vscode', '__pycache__', '.claude']

    py_files = []
    for py_file in root_path.rglob('*.py'):
        # 跳过排除的目录
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        py_files.append(py_file)

    return sorted(py_files)


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 自动更新导入路径")
    print("=" * 60)

    base_path = Path(__file__).parent
    print(f"\n📂 项目目录: {base_path}")

    # 找到所有 Python 文件
    py_files = find_python_files(base_path)
    print(f"\n📝 找到 {len(py_files)} 个 Python 文件")

    # 需要更新的文件夹
    update_dirs = [
        "src",
        "web",
        "scripts",
        "tests",
        "tools",
        "config",
    ]

    total_changes = 0
    updated_files = 0

    print("\n🔄 开始更新导入路径...")
    for py_file in py_files:
        # 检查文件是否在需要更新的目录中
        if not any(update_dir in str(py_file) for update_dir in update_dirs):
            continue

        is_modified, changes = update_imports_in_file(py_file)
        if is_modified:
            rel_path = py_file.relative_to(base_path)
            print(f"  ✅ {rel_path} (+{changes} 处修改)")
            updated_files += 1
            total_changes += changes

    print("\n" + "=" * 60)
    print(f"✅ 更新完成!")
    print(f"   文件数: {updated_files}")
    print(f"   总修改数: {total_changes}")
    print("=" * 60)

    if total_changes > 0:
        print("\n⚠️  建议:")
        print("  1. 运行测试确保代码正常")
        print("  2. 手动检查关键文件确保修改正确")
        print("  3. 测试 Web 服务和命令行脚本")


if __name__ == "__main__":
    main()
