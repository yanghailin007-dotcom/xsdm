#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
静态文件目录检查工具
防止 web/static 和 static 目录混淆
"""

import os
import sys
from pathlib import Path

def check_static_directories():
    """检查静态文件目录配置是否正确"""
    
    # 项目根目录
    project_root = Path(__file__).parent.parent
    
    # 正确的 static 目录（根目录下）
    correct_static = project_root / "static"
    
    # 错误的 static 目录（web 目录下）
    wrong_static = project_root / "web" / "static"
    
    issues = []
    
    # 检查正确的目录是否存在
    if not correct_static.exists():
        issues.append(f"❌ 错误: 正确的 static 目录不存在: {correct_static}")
    else:
        print(f"✅ 正确的 static 目录存在: {correct_static}")
    
    # 检查错误的目录是否存在
    if wrong_static.exists():
        issues.append(f"❌ 错误: 发现了错误的 static 目录: {wrong_static}")
        issues.append("   请将其内容移动到根目录的 static/ 文件夹，然后删除 web/static")
    else:
        print(f"✅ 没有发现错误的 static 目录")
    
    # 检查关键文件是否存在
    key_files = [
        "js/dialog.js",
        "css/confirm-dialog.css",
    ]
    
    for file in key_files:
        file_path = correct_static / file
        if file_path.exists():
            print(f"✅ 关键文件存在: {file}")
        else:
            issues.append(f"⚠️ 警告: 关键文件不存在: {file}")
    
    if issues:
        print("\n" + "="*60)
        print("发现以下问题：")
        print("="*60)
        for issue in issues:
            print(issue)
        print("="*60)
        return False
    else:
        print("\n✅ 所有检查通过！静态文件目录配置正确。")
        return True

if __name__ == "__main__":
    success = check_static_directories()
    sys.exit(0 if success else 1)
