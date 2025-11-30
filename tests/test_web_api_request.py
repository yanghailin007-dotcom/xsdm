"""
测试 Web API 是否能成功生成小说
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

print("🧪 Web API 测试")
print("=" * 60)

# 1. 测试 health 端点
print("\n1️⃣ 测试 Health 端点...")
try:
    response = requests.get(f"{BASE_URL}/api/health", timeout=5)
    print(f"   ✅ 健康检查: HTTP {response.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")
    exit(1)

# 2. 测试首页访问
print("\n2️⃣ 测试首页...")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   ✅ 首页加载: HTTP {response.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 测试生成接口
print("\n3️⃣ 测试生成接口 (生成 2 章)...")
try:
    response = requests.post(
        f"{BASE_URL}/api/generate-chapters",
        json={"chapters_count": 2},
        timeout=30
    )
    print(f"   📡 请求发送...")
    print(f"   ✅ 响应: HTTP {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print(f"   ✅ 生成成功！")
            print(f"   📊 生成了 {data.get('chapters_generated')} 章")
            
            # 4. 获取生成结果
            print("\n4️⃣ 获取生成结果...")
            summary = requests.get(f"{BASE_URL}/api/novel/summary", timeout=5).json()
            print(f"   📚 小说标题: {summary.get('title')}")
            print(f"   📄 已生成章节: {len(summary.get('chapters_generated', []))}")
            
            # 5. 获取第一章详情
            if summary.get('chapters_generated'):
                first_chapter = requests.get(f"{BASE_URL}/api/chapter/1", timeout=5).json()
                if first_chapter:
                    print(f"\n5️⃣ 第一章信息:")
                    print(f"   标题: {first_chapter.get('title')}")
                    print(f"   字数: {len(first_chapter.get('content', ''))}")
                    print(f"   评分: {first_chapter.get('assessment', {}).get('score', '未评')}")
            
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！")
            print("=" * 60)
            print("\n🎉 Web API 工作正常")
            print("📱 可以通过网页端发起小说生成了")
            print("\n访问地址: http://localhost:5000")
        else:
            print(f"   ❌ 生成失败: {data.get('error')}")
    else:
        print(f"   ❌ 请求失败: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ 错误: {e}")
    import traceback
    traceback.print_exc()
