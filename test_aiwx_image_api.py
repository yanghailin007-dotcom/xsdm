#!/usr/bin/env python3
"""
测试 AI-WX 图像生成 API
"""
import requests
import json
import time

# API 配置
API_URL = "https://jyapi.ai-wx.cn/v1/images/generations"
API_KEY = "sk-zO9XLgXnznOLwFEM2cE7543942F94dFa92EcBe4a8bF483C8"
MODEL = "gemini-3-pro-image-preview-1K"

def test_api():
    """测试 API 是否可用"""
    print("=" * 60)
    print("AI-WX 图像生成 API 测试")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print(f"Model: {MODEL}")
    print()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": MODEL,
        "prompt": "a cute cat sitting on a table, photorealistic",
        "size": "1024x1024",
        "n": 1
    }
    
    try:
        print("发送请求...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        
        print(f"\n状态码: {response.status_code}")
        print(f"响应:\n{response.text}")
        
        if response.status_code == 200:
            print("\n[PASS] API 可用!")
            return True
        elif response.status_code == 403:
            data = response.json()
            error_msg = data.get('error', {}).get('message', '')
            if 'suspended' in error_msg.lower():
                print("\n[FAIL] API Key 已被暂停/封禁!")
                print(f"错误: {error_msg}")
                return False
            else:
                print(f"\n[FAIL] 403 权限拒绝: {error_msg}")
                return False
        elif response.status_code == 500:
            print("\n[FAIL] 服务器内部错误 (500)")
            return False
        else:
            print(f"\n[FAIL] 未知错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] 请求异常: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)
