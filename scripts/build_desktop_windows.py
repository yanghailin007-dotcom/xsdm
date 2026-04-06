#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 桌面程序打包脚本
打包 NovelPublisher 桌面上传程序

使用方式:
    python scripts/build_desktop_windows.py

输出:
    desktop_uploader/release/NovelPublisher.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_platform():
    """检查是否在 Windows 上运行"""
    if sys.platform != 'win32':
        print("[WARN] 警告: 当前不是 Windows 系统")
        print(f"当前系统: {sys.platform}")
    return True

def install_dependencies():
    """安装打包依赖"""
    print("[INFO] 检查依赖...")
    
    # 安装 PyInstaller
    try:
        import PyInstaller
        print("[OK] PyInstaller 已安装")
    except ImportError:
        print("[INFO] 安装 PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    
    # 安装 PyQt5
    try:
        import PyQt5
        print("[OK] PyQt5 已安装")
    except ImportError:
        print("[INFO] 安装 PyQt5...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'PyQt5'], check=True)
    
    # 安装 playwright
    try:
        import playwright
        print("[OK] playwright 已安装")
    except ImportError:
        print("[INFO] 安装 playwright...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
        print("[INFO] 安装 Chromium...")
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)

def build_windows():
    """打包 Windows 桌面程序"""
    print("=" * 60)
    print("NovelPublisher Windows 桌面程序打包工具")
    print("=" * 60)
    
    check_platform()
    install_dependencies()
    
    # 获取仓库根目录（脚本在 scripts/ 目录下）
    repo_root = Path(__file__).parent.parent
    release_dir = repo_root / 'desktop_uploader' / 'release'
    
    print(f"[INFO] 工作目录: {repo_root.absolute()}")
    print(f"[INFO] Release 目录: {release_dir.absolute()}")
    
    if not release_dir.exists():
        print(f"[ERROR] 目录不存在: {release_dir}")
        print(f"[INFO] 当前目录: {Path.cwd()}")
        return False
    
    # 清理旧的构建文件
    print("[INFO] 清理旧的构建文件...")
    dirs_to_clean = [release_dir / 'build', release_dir / 'dist']
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  删除 {dir_path}")
    
    # 使用 spec 文件打包
    spec_file = release_dir / 'NovelPublisher_onefile.spec'
    if not spec_file.exists():
        print(f"[ERROR] Spec 文件不存在: {spec_file}")
        return False
    
    print("[INFO] 开始打包...")
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        str(spec_file),
        '--noconfirm',
        '--clean',
        '--workpath', str(release_dir / 'build'),
        '--distpath', str(release_dir / 'dist'),
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=str(release_dir))
        
        exe_path = release_dir / 'dist' / 'NovelPublisher.exe'
        if exe_path.exists():
            # 复制到 release 根目录
            target_exe = release_dir / 'NovelPublisher.exe'
            shutil.copy(str(exe_path), str(target_exe))
            
            size_mb = target_exe.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print("[OK] 打包完成!")
            print("=" * 60)
            print(f"[INFO] 可执行文件: {target_exe}")
            print(f"[INFO] 文件大小: {size_mb:.1f} MB")
            
            # 复制到 Web 下载目录
            web_release_dir = Path('desktop_uploader/release')
            web_release_dir.mkdir(parents=True, exist_ok=True)
            web_exe = web_release_dir / 'NovelPublisher.exe'
            shutil.copy(str(target_exe), str(web_exe))
            print(f"[OK] 已复制到: {web_exe}")
            
            return True
        else:
            print(f"[ERROR] 未找到构建输出: {exe_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] 打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = build_windows()
    sys.exit(0 if success else 1)
