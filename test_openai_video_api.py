"""
OpenAI 标准视频生成 API 测试脚本

测试所有 API 端点功能
"""
import requests
import json
import time

# API 基础 URL
BASE_URL = "http://localhost:5000"


def test_create_generation():
    """测试创建视频生成任务"""
    print("\n" + "=" * 60)
    print("测试 1: 创建视频生成任务")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/videos/generations"
    
    payload = {
        "model": "video-model-v1",
        "prompt": "一位仙风道骨的剑仙，白发如雪，身穿白色仙袍，手持发光的长剑，在云端御剑飞行",
        "generation_config": {
            "duration_seconds": 5,
            "resolution": "1080p",
            "aspect_ratio": "16:9",
            "fps": 24,
            "style": "cinematic",
            "temperature": 1.0
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 202:
            data = response.json()
            print(f"✅ 任务创建成功")
            print(f"   任务 ID: {data.get('id')}")
            print(f"   状态: {data.get('status')}")
            print(f"   创建时间: {data.get('created')}")
            return data.get('id')
        else:
            print(f"❌ 请求失败: {response.text}")
            return None
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def test_retrieve_generation(generation_id):
    """测试查询生成状态"""
    print("\n" + "=" * 60)
    print("测试 2: 查询生成状态")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/videos/generations/{generation_id}"
    
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 查询成功")
            print(f"   任务 ID: {data.get('id')}")
            print(f"   状态: {data.get('status')}")
            print(f"   模型: {data.get('model')}")
            
            if data.get('result'):
                print(f"   生成视频数: {len(data['result'].get('videos', []))}")
            
            return True
        else:
            print(f"❌ 查询失败: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_list_generations():
    """测试列出生成任务"""
    print("\n" + "=" * 60)
    print("测试 3: 列出生成任务")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/videos/generations"
    params = {
        "limit": 10,
        "order": "desc"
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 列表获取成功")
            print(f"   总数: {data.get('total')}")
            print(f"   任务数: {len(data.get('data', []))}")
            
            for task in data.get('data', [])[:3]:
                print(f"   - {task.get('id')}: {task.get('status')}")
            
            return True
        else:
            print(f"❌ 获取失败: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_cancel_generation(generation_id):
    """测试取消生成任务"""
    print("\n" + "=" * 60)
    print("测试 4: 取消生成任务")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/videos/generations/{generation_id}/cancel"
    
    try:
        response = requests.post(url)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 取消成功")
            print(f"   消息: {data.get('message')}")
            return True
        else:
            print(f"❌ 取消失败: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_stream_generation():
    """测试流式生成"""
    print("\n" + "=" * 60)
    print("测试 5: 流式生成（Server-Sent Events）")
    print("=" * 60)
    
    url = f"{BASE_URL}/v1/videos/generations/stream"
    
    payload = {
        "model": "video-model-v1",
        "prompt": "赛博朋克风格的未来城市夜景，霓虹灯闪烁",
        "generation_config": {
            "duration_seconds": 3,
            "resolution": "720p"
        }
    }
    
    try:
        response = requests.post(url, json=payload, stream=True)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 流式连接成功")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
            # 读取前几个事件
            event_count = 0
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    print(f"   {line}")
                    event_count += 1
                    if event_count >= 10:
                        print(f"   ... (省略后续事件)")
                        break
            
            return True
        else:
            print(f"❌ 流式连接失败: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 6: 错误处理")
    print("=" * 60)
    
    # 测试缺少必需参数
    print("\n6.1 测试缺少 model 参数:")
    url = f"{BASE_URL}/v1/videos/generations"
    payload = {
        "prompt": "测试提示词"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 400:
            print(f"   ✅ 正确返回 400 错误")
            data = response.json()
            print(f"   错误信息: {data.get('error', {}).get('message')}")
        else:
            print(f"   ❌ 应该返回 400 错误")
    
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试查询不存在的任务
    print("\n6.2 测试查询不存在的任务:")
    url = f"{BASE_URL}/v1/videos/generations/nonexistent_id"
    
    try:
        response = requests.get(url)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print(f"   ✅ 正确返回 404 错误")
        else:
            print(f"   ❌ 应该返回 404 错误")
    
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("OpenAI 标准视频生成 API 测试")
    print("=" * 60)
    print(f"API 基础 URL: {BASE_URL}")
    print("=" * 60)
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/api/video/types", timeout=5)
        print(f"\n✅ 服务器运行正常")
    except Exception as e:
        print(f"\n❌ 无法连接到服务器: {e}")
        print(f"   请确保服务器正在运行: python web/wsgi.py")
        return
    
    # 运行测试
    generation_id = test_create_generation()
    
    if generation_id:
        time.sleep(1)
        test_retrieve_generation(generation_id)
    
    test_list_generations()
    
    # 流式生成测试
    # test_stream_generation()  # 可选，耗时较长
    
    # 错误处理测试
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()