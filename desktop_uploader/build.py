#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手 - 构建脚本

本脚本会先使用 PyInstaller 构建 onedir 版本，
再使用 Inno Setup 打包成通用安装程序（Setup.exe）。

前置依赖:
  1. PyInstaller    : pip install pyinstaller
  2. Inno Setup 6   : https://jrsoftware.org/isdl.php

使用方法:
  python build.py

输出位置:
  desktop_uploader/release/installer_output/大文娱小说发布助手_Setup_v1.3.7.exe
"""

import sys
from pathlib import Path

# 导入新的构建逻辑
sys.path.insert(0, str(Path(__file__).parent))
from build_installer import main

if __name__ == "__main__":
    main()
