#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""强制重新构建，确保版本正确"""

import os
import sys
import shutil
import subprocess

# 清理所有缓存
cache_dirs = [
    "release/build",
    "release/dist", 
    "release/__pycache__",
    os.path.expandvars("%LOCALAPPDATA%/pyinstaller")
]

for d in cache_dirs:
    if os.path.exists(d):
        shutil.rmtree(d)
        print(f"清理: {d}")

# 清理pyc文件
for root, dirs, files in os.walk("release"):
    for f in files:
        if f.endswith('.pyc'):
            os.remove(os.path.join(root, f))
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'))

print("\n验证 main.py 版本...")
with open('release/main.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'v1.3.10' in content:
        print("[OK] main.py 包含 v1.3.10")
    else:
        print("[ERR] main.py 版本不正确")
        sys.exit(1)

print("\n开始构建...")
os.chdir('release')
result = subprocess.run([
    sys.executable, '-m', 'PyInstaller',
    'NovelPublisher_onefile.spec',
    '--noconfirm',
    '--clean'
], capture_output=True, text=True)

if result.returncode != 0:
    print("构建失败:")
    print(result.stderr)
    sys.exit(1)

print("\n[OK] 构建完成")

# 验证
exe_path = 'dist/NovelPublisher.exe'
if os.path.exists(exe_path):
    data = open(exe_path, 'rb').read()
    text = data.decode('latin-1', errors='ignore')
    
    if 'v1.3.10' in text:
        print("[OK] EXE 包含 v1.3.10")
        # 复制到目标位置
        shutil.copy(exe_path, 'NovelPublisher.exe')
        shutil.copy(exe_path, '../NovelPublisher.exe')
        os.makedirs('../web/desktop_uploader/release', exist_ok=True)
        shutil.copy(exe_path, '../web/desktop_uploader/release/NovelPublisher.exe')
        print("[OK] 已复制到所有位置")
    else:
        print("[ERR] EXE 中未找到 v1.3.10")
        # 查找实际版本
        import re
        versions = re.findall(r'1\.3\.\d+', text)
        print(f"  实际版本: {set(versions)}")
        sys.exit(1)
