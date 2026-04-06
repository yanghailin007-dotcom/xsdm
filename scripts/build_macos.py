#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 打包脚本
打包 NovelPublisher 为 .app 应用程序

使用方式:
    python scripts/build_macos.py

输出:
    dist/NovelPublisher.app
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_platform():
    """检查是否在 macOS 上运行"""
    if sys.platform != 'darwin':
        print("⚠️  警告: 当前不是 macOS 系统，打包可能失败")
        print(f"当前系统: {sys.platform}")
        return False
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

def create_icns_icon():
    """创建 macOS 图标（如果存在 png 图标）"""
    icon_path = Path('resources/icon.png')
    icns_path = Path('resources/icon.icns')
    
    if not icon_path.exists():
        print("⚠️  未找到图标文件，跳过图标设置")
        return None
    
    if icns_path.exists():
        print("✅ 图标已存在")
        return str(icns_path)
    
    # 尝试使用 sips 和 iconutil 创建 icns
    try:
        print("🎨 创建 macOS 图标...")
        temp_dir = Path('temp_icon.iconset')
        temp_dir.mkdir(exist_ok=True)
        
        # 生成不同尺寸的图标
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for size in sizes:
            output_file = temp_dir / f'icon_{size}x{size}.png'
            subprocess.run([
                'sips', '-z', str(size), str(size), 
                str(icon_path), '--out', str(output_file)
            ], check=True, capture_output=True)
            
            # 视网膜屏 @2x
            if size <= 512:
                output_file2x = temp_dir / f'icon_{size}x{size}@2x.png'
                subprocess.run([
                    'sips', '-z', str(size*2), str(size*2),
                    str(icon_path), '--out', str(output_file2x)
                ], check=True, capture_output=True)
        
        # 转换为 icns
        subprocess.run(['iconutil', '-c', 'icns', str(temp_dir), '-o', str(icns_path)], check=True)
        
        # 清理临时文件
        shutil.rmtree(temp_dir)
        
        print(f"✅ 图标创建完成: {icns_path}")
        return str(icns_path)
        
    except Exception as e:
        print(f"⚠️  创建图标失败: {e}")
        return None

def build_macos():
    """打包 macOS 应用"""
    print("=" * 60)
    print("🍎 NovelPublisher macOS 打包工具")
    print("=" * 60)
    
    # 检查平台
    check_platform()
    
    # 安装依赖
    install_pyinstaller()
    
    # 创建图标
    icon_path = create_icns_icon()
    
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
        '--windowed',                    # GUI 模式，不显示终端
        '--clean',
        '--noconfirm',
        
        # macOS Bundle 标识符
        '--osx-bundle-identifier=com.xsdm.novelpublisher',
        
        # 添加数据文件
        '--add-data=web:web',
        '--add-data=prompt_packages:prompt_packages',
        '--add-data=config:config',
        '--add-data=小说项目:小说项目',
        '--add-data=README.md:.',
        '--add-data=LICENSE:.',
        
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
    
    # 添加图标（如果有）
    if icon_path:
        cmd.extend(['--icon', icon_path])
    
    # 执行打包
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ 打包完成!")
        print("=" * 60)
        
        # 创建压缩包（方便下载）
        app_path = Path('dist/NovelPublisher.app')
        zip_path = Path('dist/NovelPublisher-macos.zip')
        
        if app_path.exists():
            print(f"\n📱 应用位置: {app_path.absolute()}")
            
            # 创建 zip 压缩包
            print("\n📦 创建压缩包...")
            shutil.make_archive(
                'dist/NovelPublisher-macos',
                'zip',
                'dist',
                'NovelPublisher.app'
            )
            
            if zip_path.exists():
                print(f"✅ 压缩包位置: {zip_path.absolute()}")
                
                # 计算文件大小
                size_mb = zip_path.stat().st_size / (1024 * 1024)
                print(f"📊 文件大小: {size_mb:.1f} MB")
                
                # 复制到 desktop_uploader/release/ 目录供 Web 下载
                release_dir = Path('desktop_uploader/release')
                release_dir.mkdir(parents=True, exist_ok=True)
                
                # 检测平台架构
                import platform
                machine = platform.machine()
                if machine == 'arm64':
                    release_name = 'NovelPublisher-macos-arm64.zip'
                else:
                    release_name = 'NovelPublisher-macos.zip'
                
                release_path = release_dir / release_name
                shutil.copy(zip_path, release_path)
                print(f"📤 已复制到 Web 下载目录: {release_path}")
        
        print("\n" + "=" * 60)
        print("📋 使用说明:")
        print("=" * 60)
        print("1. 首次运行时，在 Finder 中找到 NovelPublisher.app")
        print("2. 按住 Control 键点击应用图标")
        print("3. 选择'打开'")
        print("4. 在弹出的对话框中点击'打开'")
        print("")
        print("或者:")
        print("1. 打开'系统偏好设置' → '安全性与隐私'")
        print("2. 点击下方的'仍要打开'按钮")
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
    success = build_macos()
    sys.exit(0 if success else 1)
