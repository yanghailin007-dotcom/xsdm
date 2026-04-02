#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

# 读取文件
with open('prompt_packages/default/market_driven/components/chapter_expansion_prompts.json', 'r', encoding='utf-8') as f:
    content = f.read()

# 尝试解析
lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# 找到包含 force_expansion_prompt_template 的行
for i, line in enumerate(lines):
    if 'force_expansion_prompt_template' in line:
        print(f"Line {i}: {line[:100]}")
        # 检查下一行
        if i + 1 < len(lines):
            print(f"Line {i+1}: {lines[i+1][:100]}")
