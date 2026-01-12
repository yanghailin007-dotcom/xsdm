"""
视频生成配置测试脚本

用于验证 Google AI Platform API 配置是否正确
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config.videoconfig import (
    get_api_endpoint,
    validate_config,
    get_request_headers,
    DEFAULT_VIDEO_CONFIG,
    GOOGLE_AI_API_KEY,
    DEFAULT_GOOGLE_MODEL
)


def test_config_validation():
    """测试配置验证"""
    print("=" * 60)
    print("🔍 测试 1: 配置验证")
    print("=" * 60)
    
    is_valid, message = validate_config()
    
    if is_valid:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        print("\n⚠️  请按照以下步骤配置:")
        print("1. 访问 https://makersuite.google.com/app/apikey")
        print("2. 创建 API 密钥")
        print("3. 在 .env 文件中设置: GOOGLE_AI_API_KEY=your_key")
        print("4. 或直接在 config/videoconfig.py 中设置")
        return False
    
    return True


def test_api_endpoint():
    """测试 API 端点生成"""
    print("\n" + "=" * 60)
    print("🔍 测试 2: API 端点生成")
    print("=" * 60)
    
    try:
        # 测试流式端点
        stream_url = get_api_endpoint(stream=True)
        print(f"✅ 流式端点:")
        print(f"   {stream_url[:100]}...")
        
        # 测试非流式端点
        non_stream_url = get_api_endpoint(stream=False)
        print(f"\n✅ 非流式端点:")
        print(f"   {non_stream_url[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ 端点生成失败: {e}")
        return False


def test_request_headers():
    """测试请求头"""
    print("\n" + "=" * 60)
    print("🔍 测试 3: 请求头配置")
    print("=" * 60)
    
    try:
        headers = get_request_headers()
        print(f"✅ 请求头:")
        for key, value in headers.items():
            print(f"   {key}: {value}")
        return True
    except Exception as e:
        print(f"❌ 请求头获取失败: {e}")
        return False


def test_default_config():
    """测试默认配置"""
    print("\n" + "=" * 60)
    print("🔍 测试 4: 默认视频配置")
    print("=" * 60)
    
    try:
        print(f"✅ 默认配置:")
        for key, value in DEFAULT_VIDEO_CONFIG.items():
            print(f"   {key}: {value}")
        return True
    except Exception as e:
        print(f"❌ 配置读取失败: {e}")
        return False


def test_api_connection():
    """测试 API 连接（可选，需要有效的 API key）"""
    print("\n" + "=" * 60)
    print("🔍 测试 5: API 连接测试")
    print("=" * 60)
    
    if not GOOGLE_AI_API_KEY:
        print("⚠️  跳过: API 密钥未设置")
        return True
    
    import requests
    
    # 准备测试请求
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Hello, please respond with 'OK'"
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 10
        }
    }
    
    try:
        endpoint = get_api_endpoint(model=DEFAULT_GOOGLE_MODEL, stream=False)
        headers = get_request_headers()
        
        print(f"📡 发送测试请求到 {DEFAULT_GOOGLE_MODEL}...")
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"📊 响应状态: HTTP {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ API 连接成功!")
            data = response.json()
            
            # 尝试解析响应
            candidates = data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts and 'text' in parts[0]:
                    print(f"📝 响应内容: {parts[0]['text'][:100]}")
            
            return True
        elif response.status_code == 401:
            print(f"❌ 认证失败: API 密钥无效")
            return False
        elif response.status_code == 403:
            print(f"❌ 权限不足: 请检查 API 密钥权限")
            return False
        else:
            print(f"⚠️  意外响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时: 请检查网络连接")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接错误: 请检查网络连接")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Google AI Platform 视频生成配置测试" + " " * 10 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = []
    
    # 运行所有测试
    results.append(("配置验证", test_config_validation()))
    results.append(("API 端点", test_api_endpoint()))
    results.append(("请求头", test_request_headers()))
    results.append(("默认配置", test_default_config()))
    results.append(("API 连接", test_api_connection()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! 配置完成，可以开始使用视频生成功能。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    exit(main())