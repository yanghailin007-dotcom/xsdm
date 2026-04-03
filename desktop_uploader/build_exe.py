#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手 - 打包脚本
生成独立的可执行文件

官网: https://novel-ai.online/
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

APP_NAME = "NovelPublisher"

def build_exe():
    """使用 PyInstaller 构建 EXE"""
    print(f"[1/3] 构建 {APP_NAME}.exe...")
    
    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        f"--name={APP_NAME}",
        "--onefile",
        "--windowed",
        "--icon=NONE",
        # 添加数据文件
        "--add-data", "libs;libs",
        # 隐藏导入
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.sync_api",
        # 清理
        "--clean",
        "--noconfirm",
        # 主脚本
        "main.py"
    ]
    
    subprocess.run(cmd, check=True)

def create_release_package():
    """创建发布包"""
    print("[2/3] 创建发布包...")
    
    dist_dir = Path(__file__).parent / "dist"
    release_dir = Path(__file__).parent / "release"
    release_dir.mkdir(exist_ok=True)
    
    # 复制主 EXE
    exe_source = dist_dir / f"{APP_NAME}.exe"
    exe_dest = release_dir / f"{APP_NAME}.exe"
    
    if exe_source.exists():
        shutil.copy2(exe_source, exe_dest)
    else:
        print(f"警告: {exe_source} 未找到")
        return False
    
    # 复制源码模块（供参考）
    modules = ["chrome_manager.py", "fanqie_uploader_impl.py"]
    for module in modules:
        src = Path(__file__).parent / module
        if src.exists():
            shutil.copy2(src, release_dir / module)
    
    print("[3/3] 发布包创建完成!")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print(f"大文娱小说发布助手 - 打包工具")
    print(f"官网: https://novel-ai.online/")
    print("=" * 50)
    print()
    
    try:
        # 检查 PyInstaller
        try:
            import PyInstaller
        except ImportError:
            print("安装 PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        
        # 构建
        build_exe()
        
        # 创建发布包
        if create_release_package():
            print()
            print("=" * 50)
            print("✅ 构建完成!")
            print("=" * 50)
            print(f"输出: {Path(__file__).parent / 'release' / f'{APP_NAME}.exe'}")
            print(f"大小: {Path(__file__).parent / 'release' / f'{APP_NAME}.exe'}.stat().st_size / 1024 / 1024:.1f MB")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
