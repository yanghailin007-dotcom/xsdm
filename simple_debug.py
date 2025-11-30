"""
简单的Web请求测试脚本
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# 模拟Flask请求
print("Testing request data parsing...")

# 模拟前端发送的正常数据
test_data = {
    "title": "test novel",
    "synopsis": "test synopsis",
    "core_setting": "test setting",
    "core_selling_points": ["point1", "point2"],
    "total_chapters": 50
}

print(f"Test data: {test_data}")
print(f"Type: {type(test_data)}")

# 模拟Flask的 request.json or {} 逻辑
config = test_data or {}
print(f"Parsed config: {config}")
print(f"Config type: {type(config)}")

# 测试 .get() 调用
title = config.get("title", "default")
print(f"Title from .get(): {title}")

# 测试可能导致问题的场景
print("\nTesting problematic scenarios:")

# 场景1: 如果request.json返回字符串而不是字典
try:
    config_str = '{"title": "test"}'  # 字符串形式
    config_from_str = json.loads(config_str) if isinstance(config_str, str) else config_str
    print(f"String to dict: {config_from_str}")
    print(f"Can call .get(): {hasattr(config_from_str, 'get')}")
except Exception as e:
    print(f"Error parsing string: {e}")

# 场景2: 如果数据结构错误
bad_data = "this is a string, not a dict"
print(f"Bad data: {bad_data}")
print(f"Type: {type(bad_data)}")
print(f"Can call .get(): {hasattr(bad_data, 'get')}")

try:
    result = bad_data.get("title")  # 这会失败
    print(f"Result: {result}")
except AttributeError as e:
    print(f"AttributeError: {e}")

print("\nConclusion: The error occurs when code expects a dict but gets a string.")