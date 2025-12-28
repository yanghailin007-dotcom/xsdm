#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查.generation目录内容"""
from pathlib import Path
import json

workspace = Path('d:/work6.05')
title = '修仙：我是一柄魔剑，专治各种不服'
project_dir = workspace / '小说项目' / title
generation_dir = project_dir / '.generation'

print(f'检查目录: {generation_dir}')
print(f'存在: {generation_dir.exists()}')
print()

if generation_dir.exists():
    print('=== .generation 目录内容 ===')
    for item in generation_dir.iterdir():
        print(f'  - {item.name}')
        
        # 如果是 JSON 文件，尝试读取
        if item.suffix == '.json':
            try:
                with open(item, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f'    内容预览: {str(data)[:200]}...')
            except Exception as e:
                print(f'    [读取失败: {e}]')
    
    # 检查是否有 checkpoint.json
    checkpoint_file = generation_dir / 'checkpoint.json'
    print()
    print(f'checkpoint.json 存在: {checkpoint_file.exists()}')
else:
    print('❌ .generation 目录不存在')