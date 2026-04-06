#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复项目状态文件
"""
import sys
sys.path.insert(0, 'C:/work/xsdm')

from web.services.market_driven.project_state_initializer import initialize_project_state, check_project_state_health
from pathlib import Path

project_path = Path('C:/work/xsdm/小说项目/yanghailin/开局带只二哈，我直播气哭邪神')

print('=' * 60)
print('修复项目状态文件')
print('=' * 60)

print('\n1. 检查当前状态健康度...')
health = check_project_state_health(project_path)
print(f'健康状态: {"✅ 健康" if health["healthy"] else "❌ 不健康"}')
if health['issues']:
    print(f'问题: {health["issues"]}')

print('\n2. 执行强制初始化...')
result = initialize_project_state(project_path, force=True)
print(f'初始化结果: {"✅ 成功" if result else "❌ 失败"}')

print('\n3. 再次检查健康度...')
health = check_project_state_health(project_path)
print(f'健康状态: {"✅ 健康" if health["healthy"] else "❌ 不健康"}')
if not health['healthy']:
    print(f'问题: {health["issues"]}')

print('\n' + '=' * 60)
print('完成!')
print('=' * 60)
