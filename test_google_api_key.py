"""
测试 Google AI Platform API Key 是否正常工作
"""
import sys
import io
import requests
import json
from config.videoconfig import GOOGLE_AI_API_KEY

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_api_key():
    """测试 API Key 是否有效"""
    
    if not GOOGLE_AI_API_KEY:
        print("❌ API Key 未设置！")
        print("请在 config/videoconfig.py 中设置 GOOGLE_AI_API_KEY")
        return False
    
    print("=" * 60)
    print("测试 Google AI Platform API Key")
    print("=" * 60)
    print(f"API Key: {GOOGLE_AI_API_KEY[:20]}...")
    print()
    
    # 构建请求
    url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:streamGenerateContent?key={GOOGLE_AI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Explain how AI works in a few words"
                    }
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"发送请求到: {url[:80]}...")
    print(f"请求数据: {json.dumps(payload, ensure_ascii=False)}")
    print()
    
    try:
        print("等待响应...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"响应状态码: HTTP {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("[SUCCESS] API Key 验证成功！")
            print()
            print("响应内容:")
            print("-" * 60)
            
            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        try:
                            json_str = line_text[6:]
                            data = json.loads(json_str)
                            
                            # 提取候选结果
                            candidates = data.get('candidates', [])
                            if candidates:
                                candidate = candidates[0]
                                content = candidate.get('content', {})
                                parts = content.get('parts', [])
                                
                                for part in parts:
                                    if 'text' in part:
                                        print(part['text'], end='', flush=True)
                        except json.JSONDecodeError:
                            pass
            
            print()
            print("-" * 60)
            print()
            print("[SUCCESS] API 工作正常！可以开始使用视频生成功能。")
            return True
            
        elif response.status_code == 401:
            print("[ERROR] 认证失败：API Key 无效或已过期")
            print(f"错误详情: {response.text[:200]}")
            return False
            
        elif response.status_code == 403:
            print("[ERROR] 权限不足：请检查 API Key 权限")
            print(f"错误详情: {response.text[:200]}")
            return False
            
        elif response.status_code == 400:
            print("[ERROR] 请求错误：请检查请求参数")
            print(f"错误详情: {response.text[:200]}")
            return False
            
        else:
            print(f"[ERROR] 未知错误：HTTP {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("[ERROR] 请求超时：请检查网络连接")
        return False
        
    except requests.exceptions.ConnectionError:
        print("[ERROR] 连接错误：请检查网络连接或防火墙设置")
        return False
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False


def main():
    """主函数"""
    success = test_api_key()
    
    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if success:
        print("[SUCCESS] API Key 验证通过")
        print("[INFO] 您可以开始使用视频生成功能了！")
        return 0
    else:
        print("[ERROR] API Key 验证失败")
        print("[WARNING] 请检查以下内容：")
        print("   1. API Key 是否正确复制")
        print("   2. API Key 是否已激活")
        print("   3. 网络连接是否正常")
        print("   4. 是否有访问 Google AI Platform 的权限")
        return 1


if __name__ == "__main__":
    exit(main())