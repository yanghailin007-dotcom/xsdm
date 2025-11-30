#!/usr/bin/env python3
"""
安全的文件移动脚本 - 分批次移动文件
执行前会显示要移动的文件列表，需要用户确认
"""

import shutil
import os
from pathlib import Path

# 核心代码文件
CORE_FILES = [
    ("NovelGenerator.py", "src/core/"),
    ("APIClient.py", "src/core/"),
    ("ContentGenerator.py", "src/core/"),
    ("QualityAssessor.py", "src/core/"),
    ("ProjectManager.py", "src/core/"),
    ("Contexts.py", "src/core/"),
    ("EventBus.py", "src/core/"),
]

# 管理器文件
MANAGER_FILES = [
    ("EventDrivenManager.py", "src/managers/"),
    ("EventManager.py", "src/managers/"),
    ("EmotionalBlueprintManager.py", "src/managers/"),
    ("EmotionalPlanManager.py", "src/managers/"),
    ("ForeshadowingManager.py", "src/managers/"),
    ("GlobalGrowthPlanner.py", "src/managers/"),
    ("RomancePatternManager.py", "src/managers/"),
    ("StagePlanManager.py", "src/managers/"),
    ("WorldStateManager.py", "src/managers/"),
    ("WritingGuidanceManager.py", "src/managers/"),
    ("ElementTimingPlanner.py", "src/managers/"),
    ("StagePlanUtils.py", "src/managers/"),
]

# Prompt 文件
PROMPT_FILES = [
    ("Prompts.py", "src/prompts/"),
    ("BasePrompts.py", "src/prompts/"),
    ("AnalysisPrompts.py", "src/prompts/"),
    ("OptimizationPrompts.py", "src/prompts/"),
    ("PlanningPrompts.py", "src/prompts/"),
    ("WorldviewPrompts.py", "src/prompts/"),
    ("WritingPrompts.py", "src/prompts/"),
]

# 工具文件
UTIL_FILES = [
    ("logger.py", "src/utils/"),
    ("utils.py", "src/utils/"),
    ("DouBaoImageGenerator.py", "src/utils/"),
]

# 配置文件
CONFIG_FILES = [
    ("config.py", "config/"),
    ("doubaoconfig.py", "config/"),
]

# 脚本文件
SCRIPT_FILES = [
    ("main.py", "scripts/"),
    ("automain.py", "scripts/"),
    ("start_web_server.py", "scripts/"),
]

# Web 文件
WEB_FILES = [
    ("web_server.py", "web/"),
]

# 测试文件
TEST_FILES = [
    ("test_e2e_with_mock_data.py", "tests/"),
    ("test_helper_classes.py", "tests/"),
    ("test_integration.py", "tests/"),
    ("test_quick.py", "tests/"),
    ("test_web_api.py", "tests/"),
    ("test_web_api_request.py", "tests/"),
    ("run_all_tests.py", "tests/"),
]

# 工具脚本
TOOL_FILES = [
    ("analyze_architecture.py", "tools/"),
    ("batch_delete_deprecated.py", "tools/"),
    ("cleanup_deprecated_methods.py", "tools/"),
    ("cleanup_logs_and_dead_code.py", "tools/"),
    ("delete_deprecated_methods.py", "tools/"),
    ("generate_cleanup_report.py", "tools/"),
    ("generate_final_architecture_report.py", "tools/"),
    ("remove_unused_imports.py", "tools/"),
    ("workspace_sweep.py", "tools/"),
    ("web_api_demo.py", "tools/"),
]

# 文档文件 - 指南类
GUIDE_DOCS = [
    ("WEB_GENERATION_GUIDE.md", "docs/guides/"),
    ("WEB_ENHANCEMENT_SUMMARY.md", "docs/guides/"),
    ("WEB_COMPLETE_GUIDE.md", "docs/guides/"),
    ("WEB_QUICK_REFERENCE.md", "docs/guides/"),
    ("WEB_SYSTEM_README.md", "docs/guides/"),
    ("WEB_SERVICE_TROUBLESHOOTING.md", "docs/guides/"),
    ("SETUP_GUIDE.md", "docs/guides/"),
    ("QUICK_START.md", "docs/guides/"),
    ("E2E_TEST_GUIDE.md", "docs/guides/"),
]

# 文档文件 - 报告类
REPORT_DOCS = [
    ("PROJECT_COMPLETION_REPORT.md", "docs/reports/"),
    ("WEB_SYSTEM_COMPLETION.md", "docs/reports/"),
    ("FINAL_ARCHITECTURE_REPORT.md", "docs/reports/"),
    ("FINAL_ARCHITECTURE_REPORT.txt", "docs/reports/"),
    ("CLEANUP_COMPLETION_SUMMARY.md", "docs/reports/"),
    ("CLEANUP_FINAL_SUMMARY.txt", "docs/reports/"),
    ("FINAL_CLEANUP_REPORT.md", "docs/reports/"),
    ("AUTOMAIN_BUG_FIX_REPORT.md", "docs/reports/"),
    ("AUTOMAIN_COMPLETE_FIX_SUMMARY.txt", "docs/reports/"),
    ("AUTOMAIN_FINAL_REPORT.md", "docs/reports/"),
    ("AUTOMAIN_QUICK_REFERENCE.md", "docs/reports/"),
    ("RUNTIME_FIXES_SUMMARY.md", "docs/reports/"),
    ("FILE_MANIFEST.md", "docs/reports/"),
    ("EXECUTION_STEPS.md", "docs/reports/"),
]

# 文档文件 - 测试类
TEST_DOCS = [
    ("TEST_COMPLETION_SUMMARY.md", "docs/tests/"),
    ("TEST_FLOW_DIAGRAM.md", "docs/tests/"),
    ("TEST_README.md", "docs/tests/"),
    ("TEST_SUITE_SUMMARY.md", "docs/tests/"),
    ("TEST_SYSTEM_INVENTORY.md", "docs/tests/"),
]

# 文档文件 - 功能类
FEATURE_DOCS = [
    ("FEATURE_CHAPTER_NAVIGATION.md", "docs/features/"),
    ("LAYOUT_OPTIMIZATION.md", "docs/features/"),
    ("NAVIGATION_QUICK_START.md", "docs/features/"),
]

# 创意文件
CREATIVE_FILES = [
    ("novel_ideas.txt", "data/creative_ideas/"),
    ("novel_ideas copy.txt", "data/creative_ideas/"),
]

# 目录移动
DIRECTORY_MOVES = [
    ("templates", "web/templates"),
    ("static", "web/static"),
    ("quality_data", "data/quality_data"),
    ("generated_images", "data/generated_images"),
    ("debug_responses", "data/debug_responses"),
    ("models", "resources/models"),
    ("optimized_prompts", "resources/prompts"),
    ("Driver_Notes", "resources/driver_notes"),
    ("小说项目", "data/projects"),
]


def move_files(file_list, base_path: Path, dry_run=True):
    """移动文件列表"""
    success_count = 0
    fail_count = 0

    for src_file, dest_dir in file_list:
        src_path = base_path / src_file
        dest_path = base_path / dest_dir / src_file

        if not src_path.exists():
            print(f"  ⚠️  源文件不存在: {src_file}")
            continue

        if dry_run:
            print(f"  [预览] {src_file} -> {dest_dir}")
        else:
            try:
                # 确保目标目录存在
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # 移动文件
                shutil.move(str(src_path), str(dest_path))
                print(f"  ✅ {src_file} -> {dest_dir}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ 失败: {src_file} - {e}")
                fail_count += 1

    return success_count, fail_count


def move_directories(dir_list, base_path: Path, dry_run=True):
    """移动目录列表"""
    success_count = 0
    fail_count = 0

    for src_dir, dest_dir in dir_list:
        src_path = base_path / src_dir
        dest_path = base_path / dest_dir

        if not src_path.exists():
            print(f"  ⚠️  源目录不存在: {src_dir}")
            continue

        if dry_run:
            print(f"  [预览] {src_dir}/ -> {dest_dir}/")
        else:
            try:
                # 如果目标已存在，先删除
                if dest_path.exists():
                    shutil.rmtree(dest_path)

                # 移动目录
                shutil.move(str(src_path), str(dest_path))
                print(f"  ✅ {src_dir}/ -> {dest_dir}/")
                success_count += 1
            except Exception as e:
                print(f"  ❌ 失败: {src_dir}/ - {e}")
                fail_count += 1

    return success_count, fail_count


def main():
    """主函数"""
    print("=" * 70)
    print("📦 文件移动脚本")
    print("=" * 70)

    base_path = Path.cwd()
    print(f"\n📂 当前目录: {base_path}")

    # 首先显示预览
    print("\n🔍 预览模式 - 将要移动的文件:\n")

    categories = [
        ("核心代码", CORE_FILES),
        ("管理器", MANAGER_FILES),
        ("提示词", PROMPT_FILES),
        ("工具类", UTIL_FILES),
        ("配置", CONFIG_FILES),
        ("脚本", SCRIPT_FILES),
        ("Web服务", WEB_FILES),
        ("测试", TEST_FILES),
        ("工具脚本", TOOL_FILES),
        ("指南文档", GUIDE_DOCS),
        ("报告文档", REPORT_DOCS),
        ("测试文档", TEST_DOCS),
        ("功能文档", FEATURE_DOCS),
        ("创意文件", CREATIVE_FILES),
    ]

    total_files = 0
    for category_name, file_list in categories:
        print(f"\n📁 {category_name} ({len(file_list)} 个文件)")
        move_files(file_list, base_path, dry_run=True)
        total_files += len(file_list)

    print(f"\n📁 目录移动 ({len(DIRECTORY_MOVES)} 个)")
    move_directories(DIRECTORY_MOVES, base_path, dry_run=True)

    print("\n" + "=" * 70)
    print(f"📊 总计: {total_files} 个文件 + {len(DIRECTORY_MOVES)} 个目录")
    print("=" * 70)

    # 询问是否执行
    print("\n⚠️  确认要执行移动操作吗？")
    confirm = input("输入 'yes' 确认，其他任何输入取消: ").lower().strip()

    if confirm != 'yes':
        print("\n❌ 操作已取消")
        return

    # 执行移动
    print("\n" + "=" * 70)
    print("🚀 开始移动文件...")
    print("=" * 70)

    total_success = 0
    total_fail = 0

    for category_name, file_list in categories:
        print(f"\n📁 移动 {category_name}...")
        success, fail = move_files(file_list, base_path, dry_run=False)
        total_success += success
        total_fail += fail

    print(f"\n📁 移动目录...")
    dir_success, dir_fail = move_directories(DIRECTORY_MOVES, base_path, dry_run=False)

    print("\n" + "=" * 70)
    print("✅ 移动完成!")
    print("=" * 70)
    print(f"  成功: {total_success} 个文件 + {dir_success} 个目录")
    if total_fail > 0 or dir_fail > 0:
        print(f"  失败: {total_fail} 个文件 + {dir_fail} 个目录")
    print("=" * 70)

    print("\n📋 下一步:")
    print("  1. 运行 update_imports.py 更新导入路径")
    print("  2. 创建 __init__.py 文件")
    print("  3. 测试所有功能")


if __name__ == "__main__":
    main()
