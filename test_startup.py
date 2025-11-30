#!/usr/bin/env python3
"""
启动测试脚本 - 测试所有组件是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加根目录到路径
root_path = Path(__file__).parent
sys.path.insert(0, str(root_path))

def test_imports():
    """测试关键导入"""
    print("Testing imports...")

    tests = [
        ("Config", lambda: import_module("config.config")),
        ("Logger", lambda: import_module("src.utils.logger")),
        ("Contexts", lambda: import_module("src.core.Contexts")),
        ("NovelGenerator", lambda: import_module("src.core.NovelGenerator")),
        ("APIClient", lambda: import_module("src.core.APIClient")),
        ("QualityAssessor", lambda: import_module("src.core.QualityAssessor")),
        ("ProjectManager", lambda: import_module("src.core.ProjectManager")),
    ]

    failed = []
    passed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed.append((name, str(e)))

    return passed, len(tests), failed

def import_module(module_name):
    """导入模块的辅助函数"""
    __import__(module_name)

def test_web_server():
    """测试Web服务器导入"""
    print("\nTesting web server...")
    try:
        import web.web_server as ws
        print("  ✓ Web server imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Web server import failed: {e}")
        return False

def test_scripts():
    """测试脚本导入"""
    print("\nTesting scripts...")

    scripts = [
        "scripts.main",
        "scripts.automain",
    ]

    passed = 0
    for script in scripts:
        try:
            __import__(script)
            print(f"  ✓ {script}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {script}: {e}")

    return passed, len(scripts)

def test_data_directories():
    """测试数据目录"""
    print("\nTesting data directories...")

    required_dirs = [
        "data/projects",
        "data/creative_ideas",
        "data/quality_data",
        "data/generated_images",
        "data/debug_responses",
        "web/templates",
        "web/static"
    ]

    passed = 0
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}")
            passed += 1
        else:
            print(f"  ✗ {dir_path} (missing)")

    return passed, len(required_dirs)

def main():
    """主函数"""
    print("=" * 50)
    print("Startup Test Script")
    print("=" * 50)

    # 测试基本导入
    passed, total, failed_imports = test_imports()
    print(f"\nBasic imports: {passed}/{total}")

    if failed_imports:
        print("\nFailed imports:")
        for name, error in failed_imports:
            print(f"  - {name}: {error}")

    # 测试Web服务器
    web_ok = test_web_server()

    # 测试脚本
    script_passed, script_total = test_scripts()
    print(f"\nScripts: {script_passed}/{script_total}")

    # 测试目录
    dir_passed, dir_total = test_data_directories()
    print(f"\nDirectories: {dir_passed}/{dir_total}")

    # 总结
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Basic imports: {passed}/{total} ✓")
    print(f"  Web server: {'✓' if web_ok else '✗'}")
    print(f"  Scripts: {script_passed}/{script_total}")
    print(f"  Directories: {dir_passed}/{dir_total}")

    if failed_imports or not web_ok:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return False
    else:
        print("\n✅ All tests passed! System should be ready to start.")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)