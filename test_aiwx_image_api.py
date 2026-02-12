#!/usr/bin/env python3
"""
测试 AI-WX 图像生成 API - 所有模型变体
"""
import requests

API_URL = "https://jyapi.ai-wx.cn/v1/images/generations"
API_KEY = "sk-zO9XLgXnznOLwFEM2cE7543942F94dFa92EcBe4a8bF483C8"

models_to_test = [
    "gemini-3-pro-image-preview",
    "gemini-3-pro-image-preview-1K",
    "gemini-3-pro-preview",
]

def test_model(model):
    """测试单个模型"""
    print(f"\n测试模型: {model}")
    print("-" * 50)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": model,
        "prompt": "a cute cat",
        "size": "1024x1024",
        "n": 1
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"异常: {e}")
        return False

print("=" * 60)
print("AI-WX API 模型测试")
print("=" * 60)

results = {}
for model in models_to_test:
    results[model] = test_model(model)

print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
for model, success in results.items():
    status = "✅ 可用" if success else "❌ 不可用"
    print(f"{model}: {status}")
