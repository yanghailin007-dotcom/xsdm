#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查检查点文件是否存在"""
from pathlib import Path
import json

workspace = Path('d:/work6.05')
title = '修仙：我是一柄魔剑，专治各种不服'

print(f'工作目录: {workspace}')
print(f'小说标题: {title}')
print()

# 检查小说项目目录
projects_dir = workspace / '小说项目'
print(f'小说项目目录: {projects_dir}')
print(f'存在: {projects_dir.exists()}')
print()

# 检查具体项目目录
project_dir = projects_dir / title
print(f'具体项目目录: {project_dir}')
print(f'存在: {project_dir.exists()}')
print()

# 检查 .generation 目录
generation_dir = project_dir / '.generation'
print(f'.generation 目录: {generation_dir}')
print(f'存在: {generation_dir.exists()}')
print()

# 检查检查点文件
checkpoint_file = generation_dir / 'checkpoint.json'
print(f'检查点文件: {checkpoint_file}')
print(f'存在: {checkpoint_file.exists()}')
print()

# 列出小说项目目录下的所有项目
print('=== 所有小说项目 ===')
if projects_dir.exists():
    for item in projects_dir.iterdir():
        if item.is_dir():
            # 检查是否有 .generation 目录
            gen_dir = item / '.generation'
            has_checkpoint = (gen_dir / 'checkpoint.json').exists()
            print(f'  - {item.name} {"[有检查点]" if has_checkpoint else "[无检查点]"}')