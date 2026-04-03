#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 生成独立EXE文件

使用方法:
1. 安装依赖: pip install -r requirements.txt
2. 运行打包: python build.py
3. 输出目录: dist/小说自动上传工具.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """清理构建目录"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name}...")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
        for dir in dirs:
            if dir == '__pycache__':
                shutil.rmtree(os.path.join(root, dir))

def build_exe():
    """构建EXE"""
    print("=" * 60)
    print("开始打包 小说自动上传工具")
    print("=" * 60)
    
    # 清理旧构建
    clean_build()
    
    # PyInstaller 参数
    args = [
        'pyinstaller',
        '--name=小说自动上传工具',
        '--windowed',  # GUI模式，不显示控制台
        '--onefile',   # 单文件模式
        '--clean',     # 清理缓存
        '--noconfirm', # 不确认覆盖
        
        # 图标
        '--icon=NONE',
        
        # 添加数据文件
        '--add-data=../src/integration;integration',
        '--add-data=../Chrome/automation/legacy;Chrome/automation/legacy',
        
        # 隐藏导入
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.sip',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        
        # 排除不必要的模块以减小体积
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=pytest',
        
        # 主文件
        'main.py'
    ]
    
    print("执行命令:")
    print(' '.join(args))
    print()
    
    # 执行打包
    result = subprocess.run(args, capture_output=False)
    
    if result.returncode != 0:
        print("\n❌ 打包失败！")
        return False
    
    print("\n✅ 打包成功！")
    
    # 复制额外文件到dist目录
    print("\n复制配置文件...")
    
    # 创建配置模板
    config_template = {
        "delay_min": 3,
        "delay_max": 8,
        "stop_on_error": False,
        "platform": "fanqie",
        "browser": "chrome"
    }
    
    with open('dist/config.json', 'w', encoding='utf-8') as f:
        json.dump(config_template, f, indent=2, ensure_ascii=False)
    
    # 创建使用说明
    readme = """小说自动上传工具 v1.0
====================

使用方法:
1. 双击运行 "小说自动上传工具.exe"
2. 在左侧选择要上传的小说项目
3. 勾选要上传的章节
4. 设置上传参数（延迟、错误处理等）
5. 点击"开始上传"按钮
6. 上传过程中可以最小化到系统托盘

注意事项:
- 首次使用需要配置Chrome浏览器路径
- 请确保已登录番茄小说官网
- 建议设置合理的延迟时间以避免风控
- 上传过程中请勿关闭浏览器窗口

配置文件:
- config.json - 程序配置
- upload_config.json - 上传任务配置（由程序生成）

技术支持:
如有问题请联系技术支持
"""
    
    with open('dist/使用说明.txt', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print("✅ 文件复制完成！")
    
    # 输出信息
    exe_path = Path('dist') / '小说自动上传工具.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n📦 输出文件: {exe_path}")
        print(f"📊 文件大小: {size_mb:.1f} MB")
        print(f"\n✨ 打包完成！可以直接运行 dist/小说自动上传工具.exe")
    
    return True

def create_installer():
    """创建安装包（可选）"""
    print("\n" + "=" * 60)
    print("创建便携版压缩包")
    print("=" * 60)
    
    import zipfile
    
    zip_name = f'小说自动上传工具_v1.0_便携版.zip'
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in Path('dist').iterdir():
            if file.is_file():
                zf.write(file, file.name)
                print(f"添加: {file.name}")
    
    zip_path = Path(zip_name)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n📦 便携版: {zip_name}")
    print(f"📊 压缩后大小: {size_mb:.1f} MB")

if __name__ == "__main__":
    import json
    
    print("小说自动上传工具 - 打包脚本\n")
    
    # 检查依赖
    try:
        import PyQt5
        print("✅ PyQt5 已安装")
    except ImportError:
        print("❌ PyQt5 未安装，请先运行: pip install -r requirements.txt")
        sys.exit(1)
    
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装，请先运行: pip install -r requirements.txt")
        sys.exit(1)
    
    print()
    
    # 构建
    if build_exe():
        # 询问是否创建便携版
        response = input("\n是否创建便携版压缩包? (y/n): ")
        if response.lower() == 'y':
            create_installer()
        
        print("\n✨ 全部完成！")
    else:
        print("\n❌ 构建失败，请检查错误信息")
        sys.exit(1)
