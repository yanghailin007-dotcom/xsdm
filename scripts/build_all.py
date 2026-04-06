#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双平台统一打包脚本
自动检测平台并执行对应的打包流程

使用方式:
    python scripts/build_all.py

输出:
    Windows: dist/NovelPublisher.exe
    macOS:   dist/NovelPublisher-macos.zip
"""

import os
import sys
import platform

def main():
    """主函数"""
    system = platform.system()
    
    print("=" * 60)
    print("🚀 NovelPublisher 自动打包工具")
    print(f"检测到的平台: {system}")
    print("=" * 60)
    
    if system == 'Windows':
        print("\n🪟 开始 Windows 打包...\n")
        import build_windows
        return build_windows.build_windows()
        
    elif system == 'Darwin':  # macOS
        print("\n🍎 开始 macOS 打包...\n")
        import build_macos
        return build_macos.build_macos()
        
    else:
        print(f"\n❌ 不支持的平台: {system}")
        print("支持的平台: Windows, macOS")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
