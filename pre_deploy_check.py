#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上线前检查清单
验证所有关键组件是否就绪
"""

import sys
import os
from pathlib import Path
import json

def check_file(path: str, description: str) -> bool:
    """检查文件是否存在"""
    if Path(path).exists():
        print(f"  [OK] {description}: {path}")
        return True
    else:
        print(f"  [MISSING] {description}: {path}")
        return False

def check_dir(path: str, description: str) -> bool:
    """检查目录是否存在"""
    if Path(path).is_dir():
        print(f"  [OK] {description}: {path}")
        return True
    else:
        print(f"  [MISSING] {description}: {path}")
        return False

def main():
    print("=" * 60)
    print("Pre-Deployment Checklist")
    print("=" * 60)
    
    checks = []
    
    # 1. 检查关键配置文件
    print("\n[1] Checking configuration files...")
    checks.append(check_file("config/config.py", "Main config"))
    checks.append(check_file(".env", "Environment variables"))
    checks.append(check_file("requirements.txt", "Python dependencies"))
    
    # 2. 检查关键目录
    print("\n[2] Checking directories...")
    checks.append(check_dir("web/templates", "Templates directory"))
    checks.append(check_dir("static", "Static files directory"))
    checks.append(check_dir("prompt_packages", "Prompt packages directory"))
    checks.append(check_dir("小说项目", "Novels directory"))
    checks.append(check_dir("data", "Data directory"))
    
    # 🔥 检查是否存在错误的 web/static 目录
    if os.path.exists("web/static"):
        print("\n⚠️  WARNING: Found incorrect directory 'web/static/'")
        print("   Static files should be in 'static/' (project root), not 'web/static/'")
        checks.append((False, "Directory check", "web/static should not exist"))
    
    # 3. 检查关键代码文件
    print("\n[3] Checking critical code files...")
    checks.append(check_file("start.py", "Main entry point"))
    checks.append(check_file("web/web_server_refactored.py", "Web server"))
    checks.append(check_file("src/core/APIClient.py", "API Client"))
    
    # 4. 检查市场驱动模式相关
    print("\n[4] Checking market-driven mode...")
    checks.append(check_file("web/api/market_driven_api.py", "Market driven API"))
    checks.append(check_file("web/services/market_driven/world_state_manager.py", "World state manager"))
    checks.append(check_file("web/services/market_driven/chapter_conversation_generator.py", "Chapter generator"))
    
    # 5. 检查数据库
    print("\n[5] Checking database...")
    checks.append(check_file("data/users.db", "Users database"))
    
    # 6. 检查日志目录
    print("\n[6] Checking log directories...")
    checks.append(check_dir("logs", "Logs directory"))
    
    # 7. 检查测试脚本
    print("\n[7] Checking test/monitor scripts...")
    checks.append(check_file("test_pages_playwright.py", "Page test script"))
    checks.append(check_file("monitor_pages.py", "Page monitor script"))
    
    # 汇总
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n[READY] All checks passed! System is ready for deployment.")
        print("\nNext steps:")
        print("  1. Run: python start.py")
        print("  2. Run: python test_pages_playwright.py")
        print("  3. Start monitor: start_monitor.bat")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} check(s) failed!")
        print("Please fix the missing items before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
