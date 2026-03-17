#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 Chrome 启动器分发包
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path

# 配置
VERSION = "1.0.0"
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")

def clean_build():
    """清理构建目录"""
    print("🧹 清理构建目录...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)

def copy_files():
    """复制必要文件"""
    print("📋 复制文件...")
    
    # 创建目录结构
    (BUILD_DIR / "chrome").mkdir(exist_ok=True)
    (BUILD_DIR / "userdata").mkdir(exist_ok=True)
    
    # 复制启动脚本
    shutil.copy("start_browser.py", BUILD_DIR)
    
    # 创建 README
    readme = BUILD_DIR / "README.txt"
    readme.write_text("""大文娱 Chrome 启动器
===================

使用说明：
1. 双击运行 start_browser.exe（或 python start_browser.py）
2. 首次使用会自动下载 Chrome（约 150MB）
3. 在打开的 Chrome 中登录番茄账号
4. 回到大文娱 Web 界面使用上传功能

系统要求：
- Windows 10/11 / macOS / Linux
- 网络连接（首次下载 Chrome）
- 500MB 磁盘空间

调试端口：9988
""", encoding="utf-8")

def build_executable():
    """构建可执行文件"""
    print("🔨 构建可执行文件...")
    
    try:
        import PyInstaller.__main__
        
        PyInstaller.__main__.run([
            'start_browser.py',
            '--onefile',
            '--windowed',
            '--name', 'start_browser',
            '--distpath', str(BUILD_DIR),
            '--workpath', str(BUILD_DIR / 'work'),
            '--specpath', str(BUILD_DIR),
            '--icon', 'NONE',
            '--clean',
        ])
        print("✅ 可执行文件构建完成")
        return True
        
    except ImportError:
        print("⚠️  PyInstaller 未安装，跳过构建可执行文件")
        print("   用户将需要使用 Python 运行: python start_browser.py")
        return False

def create_zip():
    """创建分发包"""
    print("📦 创建分发包...")
    
    # 固定包名：chrome_launcher.zip
    # 解压后自动得到 chrome_launcher/ 目录，无需重命名
    zip_name = "chrome_launcher.zip"
    zip_path = DIST_DIR / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in BUILD_DIR.rglob('*'):
            if file_path.is_file():
                # 排除 work 目录
                if 'work' in str(file_path):
                    continue
                # 在 zip 中添加顶层 chrome_launcher/ 目录
                arcname = Path('chrome_launcher') / file_path.relative_to(BUILD_DIR)
                zf.write(file_path, arcname)
    
    print(f"✅ 分发包已创建: {zip_path}")
    
    # 显示文件大小
    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   提示: 解压后自动得到 chrome_launcher/ 目录")

def main():
    """主函数"""
    print("=" * 50)
    print("大文娱 Chrome 启动器构建脚本")
    print("=" * 50)
    print()
    
    clean_build()
    copy_files()
    build_executable()
    create_zip()
    
    print()
    print("=" * 50)
    print("构建完成！")
    print("=" * 50)
    print(f"分发包位置: {DIST_DIR}")

if __name__ == "__main__":
    main()
