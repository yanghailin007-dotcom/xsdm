"""
测试 VeO 视频生成功能
支持 AI-WX 的 VeO 3.1 模型
"""
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.models.veo_models import (
    VeOVideoRequest,
    VeOGenerationConfig,
    VideoStatus
)
from src.managers.VeOVideoManager import get_veo_video_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_openai_format_request():
    """测试 OpenAI 格式的视频生成请求"""
    print("\n" + "="*60)
    print("测试 OpenAI 格式的视频生成请求")
    print("="*60)
    
    # 创建 OpenAI 格式请求（文本生成视频）
    request = VeOVideoRequest(
        model="veo_3_1",
        stream=True,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "一只可爱的橘猫在阳光下打盹"
                    }
                ]
            }
        ]
    )
    
    print(f"✓ 创建请求: {request.model}")
    print(f"✓ 提示词: {request.messages[0]['content'][0]['text']}")
    
    # 获取管理器
    manager = get_veo_video_manager()
    
    # 创建生成任务
    print("\n📝 创建生成任务...")
    response = manager.create_generation(request)
    
    print(f"✓ 任务ID: {response.id}")
    print(f"✓ 状态: {response.status}")
    print(f"✓ 创建时间: {response.created}")
    
    # 等待任务完成
    print("\n⏳ 等待任务完成...")
    max_wait = 60  # 最多等待60秒
    waited = 0
    
    while waited < max_wait:
        time.sleep(2)
        waited += 2
        
        # 查询任务状态
        status_response = manager.retrieve_generation(response.id)
        if status_response:
            print(f"  状态: {status_response.status} ({waited}s)")
            
            if status_response.status == VideoStatus.COMPLETED:
                print("\n✅ 任务完成!")
                if status_response.result and status_response.result.videos:
                    for video in status_response.result.videos:
                        print(f"  📹 视频: {video.url}")
                        print(f"  ⏱️  时长: {video.duration_seconds}s")
                        print(f"  📐 分辨率: {video.resolution}")
                break
            
            elif status_response.status == VideoStatus.FAILED:
                print(f"\n❌ 任务失败: {status_response.error}")
                break
    
    if waited >= max_wait:
        print(f"\n⚠️  任务超时（等待了 {max_wait}s）")
    
    return response


def test_image_to_video():
    """测试图片生成视频（图生视频）"""
    print("\n" + "="*60)
    print("测试图片生成视频")
    print("="*60)
    
    # 创建图片生成视频请求
    image_url = "http://cdn-picstyle.duomiao.pro/666.jpg"
    
    request = VeOVideoRequest(
        model="veo_3_1",
        stream=True,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "根据图片生成动态视频"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]
    )
    
    print(f"✓ 创建请求: {request.model}")
    print(f"✓ 提示词: {request.messages[0]['content'][0]['text']}")
    print(f"✓ 图片URL: {image_url}")
    
    # 获取管理器
    manager = get_veo_video_manager()
    
    # 创建生成任务
    print("\n📝 创建生成任务...")
    response = manager.create_generation(request)
    
    print(f"✓ 任务ID: {response.id}")
    print(f"✓ 状态: {response.status}")
    
    return response


def test_landscape_video():
    """测试横屏视频生成"""
    print("\n" + "="*60)
    print("测试横屏视频生成")
    print("="*60)
    
    # 创建横屏视频请求
    request = VeOVideoRequest(
        model="veo_3_1-landscape",
        stream=True,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "美丽的日落风景"
                    }
                ]
            }
        ]
    )
    
    print(f"✓ 创建请求: {request.model}")
    print(f"✓ 模式: 横屏 (landscape)")
    
    # 获取管理器
    manager = get_veo_video_manager()
    
    # 创建生成任务
    print("\n📝 创建生成任务...")
    response = manager.create_generation(request)
    
    print(f"✓ 任务ID: {response.id}")
    print(f"✓ 状态: {response.status}")
    
    # 检查配置
    if response.generation_config:
        print(f"✓ 方向: {response.generation_config.orientation}")
        print(f"✓ 宽高比: {response.generation_config.aspect_ratio}")
    
    return response


def test_list_generations():
    """测试列出生成任务"""
    print("\n" + "="*60)
    print("测试列出生成任务")
    print("="*60)
    
    manager = get_veo_video_manager()
    
    # 列出所有任务
    print("\n📋 所有生成任务:")
    generations = manager.list_generations(limit=10)
    
    for i, gen in enumerate(generations, 1):
        print(f"\n{i}. {gen.id}")
        print(f"   状态: {gen.status}")
        print(f"   模型: {gen.model}")
        print(f"   提示词: {gen.prompt[:50]}...")
        if gen.completed:
            print(f"   完成时间: {gen.completed}")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("VeO 视频生成功能测试")
    print("="*60)
    
    # 检查配置
    try:
        from config.aiwx_video_config import validate_config
        is_valid, message = validate_config()
        if not is_valid:
            print(f"❌ {message}")
            print("\n⚠️  请设置环境变量 AIWX_API_KEY")
            print("   示例: export AIWX_API_KEY='your_api_key'")
            return
        print(f"✅ {message}")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return
    
    # 运行测试
    try:
        # 测试1: 文本生成视频
        test_openai_format_request()
        
        # 测试2: 图片生成视频
        # test_image_to_video()
        
        # 测试3: 横屏视频
        # test_landscape_video()
        
        # 测试4: 列出任务
        time.sleep(1)
        test_list_generations()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()