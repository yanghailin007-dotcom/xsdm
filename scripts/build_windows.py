#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 打包脚本
打包 NovelPublisher 为 .exe 可执行文件

使用方式:
    python scripts/build_windows.py

输出:
    dist/NovelPublisher.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_platform():
    """检查是否在 Windows 上运行"""
    if sys.platform != 'win32':
        print("⚠️  警告: 当前不是 Windows 系统")
        print(f"当前系统: {sys.platform}")
    return True

def install_pyinstaller():
    """确保 PyInstaller 已安装"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("📦 安装 PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        return True

def build_windows():
    """打包 Windows 应用"""
    print("=" * 60)
    print("🪟 NovelPublisher Windows 打包工具")
    print("=" * 60)
    
    check_platform()
    install_pyinstaller()
    
    # 清理旧的构建文件
    print("🧹 清理旧的构建文件...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  删除 {dir_name}/")
    
    # 准备 PyInstaller 参数
    print("📦 开始打包...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=NovelPublisher',
        '--windowed',                    # GUI 模式，不显示控制台
        '--onefile',                     # 单文件
        '--clean',
        '--noconfirm',
        
        # 添加数据文件（Windows 使用 ; 分隔）
        '--add-data=web;web',
        '--add-data=prompt_packages;prompt_packages',
        '--add-data=config;config',
        '--add-data=小说项目;小说项目',
        '--add-data=README.md;.',
        '--add-data=LICENSE;.',
        
        # 隐藏导入
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=flask',
        '--hidden-import=flask_socketio',
        '--hidden-import=flask_cors',
        '--hidden-import=requests',
        '--hidden-import=openai',
        '--hidden-import=anthropic',
        '--hidden-import=selenium',
        '--hidden-import=bs4',
        '--hidden-import=lxml',
        
        # 入口文件
        'start.py'
    ]
    
    # 如果有图标文件
    icon_path = Path('resources/icon.ico')
    if icon_path.exists():
        cmd.extend(['--icon', str(icon_path)])
    
    # 执行打包
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ 打包完成!")
        print("=" * 60)
        
        exe_path = Path('dist/NovelPublisher.exe')
        
        if exe_path.exists():
            # 计算文件大小
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n📦 可执行文件: {exe_path.absolute()}")
            print(f"📊 文件大小: {size_mb:.1f} MB")
            
            # 复制到 desktop_uploader/release/ 目录供 Web 下载
            release_dir = Path('desktop_uploader/release')
            release_dir.mkdir(parents=True, exist_ok=True)
            release_path = release_dir / 'NovelPublisher.exe'
            shutil.copy(exe_path, release_path)
            print(f"📤 已复制到 Web 下载目录: {release_path}")
        
        print("\n" + "=" * 60)
        print("📋 使用说明:")
        print("=" * 60)
        print("双击 NovelPublisher.exe 即可运行")
        print("首次运行可能需要允许 Windows Defender 访问")
        print("=" * 60)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = build_windows()
    sys.exit(0 if success else 1)
