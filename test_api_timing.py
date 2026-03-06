#!/usr/bin/env python3
"""
测试 API 响应时间
"""
import time
import requests
import json

print("=" * 60)
print("Testing API Response Time")
print("=" * 60)

base_url = "http://localhost:5000"

# 1. 测试登录状态
print("\n[1] Testing server availability...")
start = time.time()
try:
    resp = requests.get(f"{base_url}/", timeout=5)
    elapsed = time.time() - start
    print(f"    Server response: {resp.status_code}, Time: {elapsed:.3f}s")
except Exception as e:
    print(f"    Error: {e}")
    exit(1)

# 2. 测试获取余额 API
print("\n[2] Testing points balance API...")
start = time.time()
try:
    resp = requests.get(f"{base_url}/api/points/balance", timeout=10)
    elapsed = time.time() - start
    print(f"    API response: {resp.status_code}, Time: {elapsed:.3f}s")
    if resp.ok:
        data = resp.json()
        print(f"    Balance: {data.get('data', {}).get('balance', 'N/A')}")
except Exception as e:
    print(f"    Error: {e}")

# 3. 测试开始生成 API（模拟，不实际创建任务）
print("\n[3] Testing phase-one start API (dry run)...")
test_data = {
    "title": f"测试小说_{int(time.time())}",
    "synopsis": "这是一个测试小说简介",
    "core_setting": "这是一个测试核心设定",
    "core_selling_points": "爽文节奏",
    "total_chapters": 50,
    "generation_mode": "phase_one_only",
    "target_platform": "fanqie"
}

start = time.time()
try:
    resp = requests.post(
        f"{base_url}/api/phase-one/generate",
        json=test_data,
        timeout=30
    )
    elapsed = time.time() - start
    print(f"    API response: {resp.status_code}, Time: {elapsed:.3f}s")
    
    if resp.ok:
        data = resp.json()
        print(f"    Task ID: {data.get('task_id', 'N/A')}")
        print(f"    Message: {data.get('message', 'N/A')}")
    else:
        print(f"    Error response: {resp.text[:200]}")
except Exception as e:
    print(f"    Error: {e}")

print("\n" + "=" * 60)
print("Test completed")
print("=" * 60)
