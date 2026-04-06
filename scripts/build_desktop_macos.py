#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 桌面程序打包脚本
打包 NovelPublisher 桌面上传程序

使用方式:
    python scripts/build_desktop_macos.py

输出:
    desktop_uploader/release/dist/NovelPublisher.app
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_platform():
    """检查是否在 macOS 上运行"""
    if sys.platform != 'darwin':
        print("[WARN] 警告: 当前不是 macOS 系统，打包可能失败")
        print(f"当前系统: {sys.platform}")
        return False
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

def build_macos():
    """打包 macOS 桌面程序"""
    print("=" * 60)
    print("NovelPublisher macOS 桌面程序打包工具")
    print("=" * 60)
    
    if not check_platform():
        return False
    
    install_dependencies()
    
    # 获取仓库根目录（脚本在 scripts/ 目录下）
    repo_root = Path(__file__).parent.parent
    release_dir = repo_root / 'desktop_uploader' / 'release'
    
    print(f"[INFO] 工作目录: {repo_root.absolute()}")
    print(f"[INFO] Release 目录: {release_dir.absolute()}")
    
    if not release_dir.exists():
        print(f"[ERROR] 目录不存在: {release_dir}")
        print(f"[INFO] 当前目录: {Path.cwd()}")
        # 列出当前目录内容帮助调试
        print(f"[INFO] 当前目录内容: {list(Path.cwd().iterdir())}")
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
    
    # 检测平台架构
    import platform
    machine = platform.machine()
    arch_flag = '--target-arch=arm64' if machine == 'arm64' else ''
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        str(spec_file),
        '--noconfirm',
        '--clean',
        '--workpath', str(release_dir / 'build'),
        '--distpath', str(release_dir / 'dist'),
    ]
    
    if arch_flag:
        cmd.append(arch_flag)
    
    try:
        subprocess.run(cmd, check=True, cwd=str(release_dir))
        
        # macOS 单文件版本
        app_path = release_dir / 'dist' / 'NovelPublisher'
        if app_path.exists():
            # 创建压缩包
            print("[INFO] 创建压缩包...")
            import platform
            machine = platform.machine()
            if machine == 'arm64':
                zip_name = 'NovelPublisher-macos-arm64'
            else:
                zip_name = 'NovelPublisher-macos'
            
            zip_path = release_dir / 'dist' / zip_name
            shutil.make_archive(
                str(zip_path),
                'zip',
                str(release_dir / 'dist'),
                'NovelPublisher'
            )
            
            final_zip = zip_path.with_suffix('.zip')
            if final_zip.exists():
                size_mb = final_zip.stat().st_size / (1024 * 1024)
                print("\n" + "=" * 60)
                print("[OK] 打包完成!")
                print("=" * 60)
                print(f"[INFO] 压缩包: {final_zip}")
                print(f"[INFO] 文件大小: {size_mb:.1f} MB")
                
                # 复制到 Web 下载目录
                web_release_dir = Path('desktop_uploader/release')
                web_release_dir.mkdir(parents=True, exist_ok=True)
                web_zip = web_release_dir / final_zip.name
                shutil.copy(str(final_zip), str(web_zip))
                print(f"[OK] 已复制到: {web_zip}")
                
                return True
        else:
            print(f"[ERROR] 未找到构建输出: {app_path}")
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
    success = build_macos()
    sys.exit(0 if success else 1)
