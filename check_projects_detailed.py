#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""详细检查小说项目"""
from pathlib import Path
import os

workspace = Path('d:/work6.05')
projects_dir = workspace / '小说项目'

print('=== 详细检查小说项目 ===')
print()

for item in projects_dir.iterdir():
    print(f'名称: {item.name}')
    print(f'完整路径: {item}')
    print(f'是目录: {item.is_dir()}')
    print(f'是文件: {item.is_file()}')
    
    # 如果是目录，列出内容
    if item.is_dir():
        print('目录内容:')
        try:
            for sub_item in item.iterdir():
                print(f'  - {sub_item.name}')
        except Exception as e:
            print(f'  [无法列出: {e}]')
    
    print('-' * 60)