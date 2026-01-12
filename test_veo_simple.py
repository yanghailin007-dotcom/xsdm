"""
简单测试 VeO 视频生成功能
"""
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.models.veo_models import (
    VeOVideoRequest,
    VeOGenerationConfig,
    VideoStatus
)
from src.managers.VeOVideoManager import get_veo_video_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_config():
    """测试配置"""
    print("\n" + "="*60)
    print("测试配置验证")
    print("="*60)
    
    try:
        from config.aiwx_video_config import validate_config, get_api_key
        is_valid, message = validate_config()
        
        print(f"配置验证: {is_valid}")
        print(f"消息: {message}")
        
        if is_valid:
            api_key = get_api_key()
            print(f"API密钥: {api_key[:20]}...{api_key[-10:]}")
            print("配置验证通过!")
            return True
        else:
            print(f"配置验证失败: {message}")
            return False
            
    except Exception as e:
        print(f"配置验证异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_text_to_video():
    """测试文本生成视频"""
    print("\n" + "="*60)
    print("测试文本生成视频")
    print("="*60)
    
    try:
        # 创建请求
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
        
        print(f"模型: {request.model}")
        print(f"提示词: {request.messages[0]['content'][0]['text']}")
        
        # 获取管理器
        manager = get_veo_video_manager()
        
        # 创建任务
        print("\n创建生成任务...")
        response = manager.create_generation(request)
        
        print(f"任务ID: {response.id}")
        print(f"状态: {response.status}")
        print(f"创建时间: {response.created}")
        
        if response.generation_config:
            print(f"配置:")
            print(f"  - 方向: {response.generation_config.orientation}")
            print(f"  - 尺寸: {response.generation_config.size}")
            print(f"  - 宽高比: {response.generation_config.aspect_ratio}")
        
        return response
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_manager():
    """测试管理器功能"""
    print("\n" + "="*60)
    print("测试管理器功能")
    print("="*60)
    
    try:
        manager = get_veo_video_manager()
        
        # 列出任务
        print("\n列出所有任务:")
        generations = manager.list_generations(limit=10)
        
        if generations:
            for i, gen in enumerate(generations, 1):
                print(f"{i}. {gen.id}")
                print(f"   状态: {gen.status}")
                print(f"   模型: {gen.model}")
                if gen.prompt:
                    print(f"   提示词: {gen.prompt[:50]}...")
        else:
            print("没有找到任务")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("VeO 视频生成功能测试")
    print("="*60)
    
    # 测试1: 配置验证
    config_ok = test_config()
    if not config_ok:
        print("\n配置验证失败，无法继续测试")
        return
    
    # 测试2: 文本生成视频
    response = test_text_to_video()
    if response:
        print("\n任务创建成功!")
        
        # 等待一段时间
        print("\n等待任务处理...")
        time.sleep(3)
        
        # 查询状态
        manager = get_veo_video_manager()
        status_response = manager.retrieve_generation(response.id)
        if status_response:
            print(f"\n当前状态: {status_response.status}")
    
    # 测试3: 管理器功能
    test_manager()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()