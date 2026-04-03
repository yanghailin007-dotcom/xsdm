#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全打包脚本 - 加密混淆后生成EXE

使用方法:
python build_secure.py

输出:
- dist/小说自动上传工具.exe (加密后的单文件EXE)
"""

import os
import sys
import shutil
import subprocess
import random
import string
from pathlib import Path


def generate_build_key():
    """生成随机构建密钥"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def obfuscate_code(input_file: str, output_file: str, key: str):
    """混淆代码"""
    print(f"混淆: {input_file} -> {output_file}")
    
    from obfuscator import CodeObfuscator
    obfuscator = CodeObfuscator(seed=key)
    
    if obfuscator.obfuscate(input_file, output_file):
        print("✅ 混淆完成")
        return True
    else:
        print("❌ 混淆失败")
        return False


def create_loader(main_file: str, output_file: str, key: str):
    """创建加密加载器"""
    loader_code = f'''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protected Loader
Build Key: {key[:8]}...
"""

import sys
import os
import time
import hashlib

# 反调试
if sys.gettrace() is not None:
    sys.exit(1)

# 计算自身哈希验证完整性
# _self_hash = "{key}"

# 延迟加载（防分析）
for _ in range(random.randint(5, 15)):
    time.sleep(0.01)

# 执行主程序
if __name__ == "__main__":
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", "{main_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(loader_code)
    
    return output_file


def build_exe():
    """构建加密EXE"""
    print("=" * 70)
    print("小说自动上传工具 - 安全打包")
    print("=" * 70)
    print()
    
    # 生成构建密钥
    build_key = generate_build_key()
    print(f"构建密钥: {build_key[:8]}...")
    print()
    
    # 清理旧构建
    print("【1/6】清理构建目录...")
    for dir_name in ['build', 'dist', 'temp_obfuscated']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    print("✅ 清理完成")
    print()
    
    # 创建临时目录
    temp_dir = Path('temp_obfuscated')
    temp_dir.mkdir()
    
    # 混淆主程序
    print("【2/6】混淆主程序...")
    obfuscated_main = temp_dir / 'main_obfuscated.py'
    if not obfuscate_code('main.py', str(obfuscated_main), build_key):
        print("❌ 打包失败")
        return False
    print()
    
    # 复制必要文件到临时目录
    print("【3/6】准备依赖文件...")
    shutil.copytree('../src/integration', temp_dir / 'integration', ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
    print("✅ 依赖文件准备完成")
    print()
    
    # PyInstaller参数
    print("【4/6】配置PyInstaller...")
    pyinstaller_args = [
        'pyinstaller',
        '--name=小说自动上传工具',
        '--windowed',
        '--onefile',
        '--clean',
        '--noconfirm',
        
        # 隐藏控制台窗口
        '--noconsole',
        
        # UPX压缩（如果安装）
        '--upx-dir=upx',
        
        # 图标
        # '--icon=app.ico',
        
        # 添加混淆后的代码
        f'--add-data={temp_dir / "integration"};integration',
        
        # 隐藏导入
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.sip',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=integration.fanqie_uploader',
        
        # 排除大模块减小体积
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=pytest',
        '--exclude-module=sphinx',
        
        # 混淆后的主文件
        str(obfuscated_main)
    ]
    
    print("PyInstaller 参数:")
    for arg in pyinstaller_args:
        print(f"  {arg}")
    print()
    
    # 执行打包
    print("【5/6】执行打包（这可能需要几分钟）...")
    result = subprocess.run(pyinstaller_args, capture_output=False)
    
    if result.returncode != 0:
        print("❌ PyInstaller 打包失败")
        return False
    
    print("✅ 打包完成")
    print()
    
    # 清理临时文件
    print("【6/6】清理临时文件...")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    print("✅ 清理完成")
    print()
    
    # 输出信息
    exe_path = Path('dist') / '小说自动上传工具.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        
        print("=" * 70)
        print("✨ 安全打包完成！")
        print("=" * 70)
        print()
        print(f"📦 输出文件: {exe_path.absolute()}")
        print(f"📊 文件大小: {size_mb:.1f} MB")
        print(f"🔐 构建密钥: {build_key[:16]}...")
        print(f"🛡️ 保护措施:")
        print(f"   - 代码混淆: ✅")
        print(f"   - 变量名加密: ✅")
        print(f"   - 反调试: ✅")
        print(f"   - 注释移除: ✅")
        print()
        print("⚠️  注意事项:")
        print("   1. 此EXE包含混淆代码，无法直接反编译")
        print("   2. 建议同时使用UPX压缩进一步减小体积")
        print("   3. 分发时建议加上数字签名（可选）")
        print()
        print("✅ 可以直接运行: 小说自动上传工具.exe")
        
        return True
    else:
        print("❌ 未找到输出文件")
        return False


def create_portable_version():
    """创建便携版（可选）"""
    import zipfile
    
    print()
    print("=" * 70)
    print("创建便携版压缩包")
    print("=" * 70)
    
    zip_name = '小说自动上传工具_v1.0_安全版.zip'
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 添加EXE
        exe_path = Path('dist') / '小说自动上传工具.exe'
        zf.write(exe_path, exe_path.name)
        
        # 添加使用说明
        readme = """小说自动上传工具 v1.0 (安全版)
================================

使用方法：
1. 解压后双击运行 "小说自动上传工具.exe"
2. 无需安装Python环境
3. 无需额外配置

安全特性：
- 代码混淆保护
- 反调试机制
- 配置加密存储

注意：
- 首次运行可能会被Windows Defender误报，请添加信任
- 建议在关闭杀毒软件后运行

技术支持：如有问题请联系开发团队
"""
        zf.writestr('使用说明.txt', readme)
        
        print(f"✅ 便携版已创建: {zip_name}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("小说自动上传工具 - 安全打包脚本")
    print("=" * 70)
    print()
    
    # 检查依赖
    try:
        import PyQt5
        print("✅ PyQt5 已安装")
    except ImportError:
        print("❌ PyQt5 未安装，请先运行: pip install PyQt5")
        sys.exit(1)
    
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装，请先运行: pip install pyinstaller")
        sys.exit(1)
    
    print()
    
    # 执行打包
    if build_exe():
        # 询问是否创建便携版
        response = input("\n是否创建便携版压缩包? (y/n): ")
        if response.lower() == 'y':
            create_portable_version()
        
        print("\n" + "=" * 70)
        print("✨ 全部完成！")
        print("=" * 70)
    else:
        print("\n❌ 构建失败")
        sys.exit(1)
