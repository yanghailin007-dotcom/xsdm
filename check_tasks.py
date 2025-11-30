#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查任务列表格式"""

import requests
import time

# 等待服务启动
print('⏳ 等待 Web 服务...')
time.sleep(2)

try:
    response = requests.get('http://localhost:5000/api/tasks', timeout=5)
    print(f'✅ 状态码: {response.status_code}')
    
    data = response.json()
    print(f'📌 响应类型: {type(data)}')
    print(f'📌 响应内容:')
    print(f'{data}')
    
except Exception as e:
    print(f'❌ 错误: {e}')
