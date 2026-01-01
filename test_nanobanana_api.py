"""
Nano Banana API测试脚本
测试角色生成的文生图功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
from src.utils.logger import get_logger

logger = get_logger("NanoBananaTest")


def test_service_status():
    """测试服务状态"""
    print("\n" + "="*60)
    print("🔍 测试1: 检查服务状态")
    print("="*60)
    
    try:
        generator = NanoBananaImageGenerator()
        
        print(f"✅ Nano Banana客户端初始化成功")
        print(f"   - 启用状态: {generator.enabled}")
        print(f"   - API可用: {generator.is_available()}")
        print(f"   - Base URL: {generator.base_url}")
        print(f"   - 有API密钥: {bool(generator.api_key)}")
        print(f"   - 超时设置: {generator.timeout}秒")
        print(f"   - 最大重试: {generator.max_retries}次")
        
        if not generator.is_available():
            print("\n⚠️  警告: Nano Banana服务不可用")
            print("   请在config.py中配置API密钥:")
            print("   CONFIG['nanobanana']['api_key'] = 'your_api_key_here'")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 服务状态检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_image_generation():
    """测试单张图像生成"""
    print("\n" + "="*60)
    print("🎨 测试2: 生成单张图像（角色生成）")
    print("="*60)
    
    try:
        generator = NanoBananaImageGenerator()
        
        if not generator.is_available():
            print("⚠️  跳过测试: 服务不可用")
            return False
        
        # 测试提示词 - 用于角色生成
        test_prompt = "draw a cute cat"
        
        print(f"📝 提示词: {test_prompt}")
        print(f"⏳ 开始生成...")
        
        result = generator.generate_image(
            prompt=test_prompt,
            aspect_ratio="16:9",
            image_size="2K"  # 使用2K以加快测试
        )
        
        if result.get("success"):
            print(f"✅ 图像生成成功!")
            print(f"   - 本地路径: {result['local_path']}")
            print(f"   - 访问URL: {result['url']}")
            print(f"   - 文件大小: {result.get('file_size', 0)} 字节")
            if result.get('text_response'):
                print(f"   - 文本响应: {result['text_response']}")
            return True
        else:
            print(f"❌ 图像生成失败: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 单张图像生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_image_generation():
    """测试批量图像生成"""
    print("\n" + "="*60)
    print("🎨 测试3: 批量生成图像")
    print("="*60)
    
    try:
        generator = NanoBananaImageGenerator()
        
        if not generator.is_available():
            print("⚠️  跳过测试: 服务不可用")
            return False
        
        # 测试提示词列表
        test_prompts = [
            "draw a cat",
            "draw a dog"
        ]
        
        print(f"📝 提示词数量: {len(test_prompts)}")
        print(f"⏳ 开始批量生成...")
        
        results = generator.batch_generate(
            prompts=test_prompts,
            aspect_ratio="16:9",
            image_size="2K",
            delay=1.0
        )
        
        success_count = len([r for r in results if r.get('success')])
        
        print(f"\n📊 批量生成结果:")
        print(f"   - 总数: {len(results)}")
        print(f"   - 成功: {success_count}")
        print(f"   - 失败: {len(results) - success_count}")
        
        for i, result in enumerate(results):
            status = "✅" if result.get('success') else "❌"
            print(f"   {status} 图像{i+1}: {result.get('prompt', 'N/A')[:30]}...")
            if result.get('success'):
                print(f"      路径: {result['local_path']}")
            else:
                print(f"      错误: {result.get('error', 'Unknown')}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 批量图像生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_via_requests():
    """通过HTTP请求测试API"""
    print("\n" + "="*60)
    print("🌐 测试4: 通过HTTP API测试")
    print("="*60)
    
    try:
        import requests
        
        # 检查服务是否运行
        base_url = "http://localhost:5000"
        
        # 测试状态接口
        print("📡 检查Nano Banana服务状态...")
        try:
            response = requests.get(f"{base_url}/api/nanobanana/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ 服务状态API正常")
                print(f"   - 启用: {status_data.get('enabled')}")
                print(f"   - 可用: {status_data.get('available')}")
                print(f"   - 有密钥: {status_data.get('has_api_key')}")
            else:
                print(f"⚠️  服务状态API返回: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("⚠️  无法连接到Web服务器")
            print("   提示: 请先启动Web服务器 (python web/web_server_refactored.py)")
            return False
        except Exception as e:
            print(f"⚠️  状态检查失败: {e}")
            return False
        
        # 测试生成接口
        print("\n📡 测试图像生成API...")
        try:
            payload = {
                "prompt": "draw a cute cat",
                "aspect_ratio": "16:9",
                "image_size": "2K"
            }
            
            response = requests.post(
                f"{base_url}/api/nanobanana/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ API生成成功")
                    print(f"   - 路径: {result.get('local_path')}")
                    print(f"   - URL: {result.get('url')}")
                    return True
                else:
                    print(f"❌ API生成失败: {result.get('error')}")
                    return False
            else:
                print(f"❌ API返回错误: {response.status_code}")
                print(f"   响应: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时")
            return False
        except Exception as e:
            print(f"❌ API测试失败: {e}")
            return False
            
    except ImportError:
        print("⚠️  未安装requests库，跳过HTTP API测试")
        return None


def print_usage_guide():
    """打印使用指南"""
    print("\n" + "="*60)
    print("📖 Nano Banana API使用指南")
    print("="*60)
    print("""
1. 配置API密钥:
   在 config.py 中已设置:
   CONFIG['nanobanana']['api_key'] = 'sk-mDqCm1AByrVbtN6EGmN638SSyNFOsGUdjzVZrdjNz1xGq8TC'
   CONFIG['nanobanana']['base_url'] = 'https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent'
   
   或设置环境变量:
   export NANOBANANA_API_KEY='your_api_key_here'

2. 直接使用Python:
   ```python
   from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
   
   generator = NanoBananaImageGenerator()
   result = generator.generate_image(
       prompt="draw a character",
       aspect_ratio="16:9",
       image_size="4K"
   )
   print(result)
   ```

3. 通过HTTP API使用:
   ```bash
   # 检查服务状态
   curl http://localhost:5000/api/nanobanana/status
   
   # 生成图像
   curl -X POST http://localhost:5000/api/nanobanana/generate \\
     -H "Content-Type: application/json" \\
     -d '{"prompt": "draw a character", "aspect_ratio": "16:9", "image_size": "4K"}'
   
   # 批量生成
   curl -X POST http://localhost:5000/api/nanobanana/batch-generate \\
     -H "Content-Type: application/json" \\
     -d '{"prompts": ["draw a cat", "draw a dog"], "aspect_ratio": "16:9"}'
   ```

4. 支持的参数:
   - aspect_ratio: 16:9, 4:3, 1:1, 9:16
   - image_size: 1K, 2K, 4K
   - prompt: 文本描述（用于角色生成）
   
5. 主要用途:
   - 小说角色图像生成
   - 角色设计可视化
   - 角色配图生成
    """)


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 Nano Banana API测试套件")
    print("   (用于角色生成的文生图API)")
    print("="*60)
    
    results = {}
    
    # 运行测试
    results['service_status'] = test_service_status()
    results['single_generation'] = test_single_image_generation() if results['service_status'] else None
    results['batch_generation'] = test_batch_image_generation() if results['service_status'] else None
    results['http_api'] = test_api_via_requests()
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⏭️  跳过"
        
        test_display = {
            'service_status': '服务状态检查',
            'single_generation': '单张图像生成',
            'batch_generation': '批量图像生成',
            'http_api': 'HTTP API测试'
        }
        
        print(f"{status} - {test_display.get(test_name, test_name)}")
    
    # 打印使用指南
    print_usage_guide()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    main()