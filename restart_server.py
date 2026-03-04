#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import subprocess
import sys

os.chdir(r'C:\Users\yangh\Documents\GitHub\xsdm')

# 读取 PID
try:
    with open('.server.pid', 'r') as f:
        pid = f.read().strip()
    print(f"停止服务 PID: {pid}")
    os.system(f'taskkill /F /PID {pid} 2>nul')
    time.sleep(2)
except Exception as e:
    print(f"停止服务失败: {e}")

# 启动服务
print("启动服务...")
subprocess.Popen([r'.venv\Scripts\python.exe', 'start.py'])
print("服务已重启")
time.sleep(3)
