"""
详细调试 VeO API 请求
查看实际发送的 HTTP 请求内容
"""
import sys
import io
from pathlib import Path

# 修复 Windows 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
from config.aiwx_video_config import (
    AIWX_VIDEO_CREATE_URL,
    get_request_headers
)

print("=" * 80)
print("详细调试 VeO API 请求")
print("=" * 80)

# 获取请求头
headers = get_request_headers()

print("\n1️⃣ 配置的请求头:")
for key, value in headers.items():
    if key == 'Authorization':
        print(f"   {key}: {value[:30]}...")
    else:
        print(f"   {key}: {value}")

# 准备测试请求
payload = {
    "model": "veo_3_1-fast",
    "prompt": "test",
    "orientation": "portrait",
    "size": "large",
    "duration": 10
}

print("\n2️⃣ 准备发送的请求体:")
import json
print(json.dumps(payload, indent=2, ensure_ascii=False))

# 使用 requests 的 session 来捕获实际发送的请求
print("\n3️⃣ 实际发送的 HTTP 请求:")

# 创建一个自定义的适配器来记录请求详情
class DebugAdapter(requests.adapters.HTTPAdapter):
    def send(self, request, **kwargs):
        print("\n   📤 请求行:")
        print(f"   {request.method} {request.url}")
        print("\n   📋 请求头:")
        for key, value in request.headers.items():
            if 'auth' in key.lower() or 'token' in key.lower():
                print(f"   {key}: {value[:30]}...")
            else:
                print(f"   {key}: {value}")
        print("\n   📦 请求体:")
        if request.body:
            try:
                body_json = json.loads(request.body)
                print(f"   {json.dumps(body_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"   {request.body[:500]}")
        
        # 实际发送请求
        response = super().send(request, **kwargs)
        
        print(f"\n   📥 响应状态: {response.status_code}")
        print(f"   📄 响应头:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        return response

# 创建 session 并添加调试适配器
session = requests.Session()
adapter = DebugAdapter()
session.mount('https://', adapter)
session.mount('http://', adapter)

print("\n4️⃣ 发送测试请求:")
try:
    response = session.post(
        AIWX_VIDEO_CREATE_URL,
        json=payload,
        headers=headers,
        timeout=30
    )
    
    print(f"\n5️⃣ 响应内容:")
    print(response.text[:1000])
    
except Exception as e:
    print(f"\n❌ 请求失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
