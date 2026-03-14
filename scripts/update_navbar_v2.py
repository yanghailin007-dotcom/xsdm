#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量替换旧版导航栏为V2版本
"""
import os
import re

# 需要替换的文件列表
files_to_update = [
    'web/templates/account.html',
    'web/templates/base.html',
    'web/templates/chapter-view.html',
    'web/templates/contract_management.html',
    'web/templates/character-portrait.html',
    'web/templates/cover_maker.html',
    'web/templates/dashboard.html',
    'web/templates/fanqie_upload.html',
    'web/templates/layouts/base.html',
    'web/templates/novels.html',
    'web/templates/phase-one-setup.html',
    'web/templates/novel_view.html',
    'web/templates/project-management.html',
    'web/templates/worldview-viewer.html',
    'web/templates/storyline.html',
    'web/templates/phase-two-generation-v2.html',
    'web/templates/pages/v2/phase-two-generation-new.html',
]

old_pattern = r"{% include 'components/navbar.html' %}"
new_pattern = "{% include 'components/v2/navbar.html' %}"

updated = []
failed = []

for filepath in files_to_update:
    full_path = os.path.join('c:/Users/yangh/Documents/GitHub/xsdm', filepath)
    if not os.path.exists(full_path):
        failed.append(filepath)
        continue
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_pattern not in content:
            continue
        
        new_content = content.replace(old_pattern, new_pattern)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        updated.append(filepath)
        print(f"[OK] {filepath}")
    except Exception as e:
        failed.append(filepath)
        print(f"[ERROR] {filepath}: {e}")

print(f"\n✅ 成功更新: {len(updated)} 个文件")
if failed:
    print(f"❌ 失败: {len(failed)} 个文件")
    for f in failed:
        print(f"  - {f}")
