"""
AI-WX 视频生成 API 测试脚本
测试 https://jyapi.ai-wx.cn API 集成
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.AiWxVideoManager import AiWxVideoManager
from src.models.video_openai_models import (
    VideoGenerationRequest,
    GenerationConfig
)


def test_aiwx_video_generation():
    """测试 AI-WX 视频生成"""
    print("=" * 60)
    print("AI-WX 视频生成 API 测试")
    print("=" * 60)
    
    # 创建管理器
    print("\n1️⃣ 初始化 AI-WX 视频生成管理器...")
    manager = AiWxVideoManager()
    manager.start()
    print("✅ 管理器已启动")
    
    # 创建生成请求
    print("\n2️⃣ 创建视频生成请求...")
    
    # 定义进度回调
    def progress_callback(task_id, progress, stage):
        print(f"📊 进度: {progress}% - {stage}")
    
    # 创建请求
    request = VideoGenerationRequest(
        model="sora-2",
        prompt="一只可爱的橘猫在阳光下打哈欠，镜头缓慢推进",
        generation_config=GenerationConfig(
            duration_seconds=10,
            resolution="1280x720",  # 横屏720p
            fps=24
        )
    )
    
    print(f"📝 提示词: {request.prompt}")
    print(f"🎬 模型: {request.model}")
    if request.generation_config:
        print(f"⏱️  时长: {request.generation_config.duration_seconds}秒")
        print(f"📐 分辨率: {request.generation_config.resolution}")
    
    # 提交生成任务
    print("\n3️⃣ 提交生成任务...")
    response = manager.create_generation(request, progress_callback=progress_callback)
    
    print(f"✅ 任务已创建")
    print(f"🆔 任务ID: {response.id}")
    print(f"📊 状态: {response.status}")
    
    # 轮询任务状态
    print("\n4️⃣ 等待生成完成...")
    max_wait_time = 300  # 最多等待5分钟
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        # 查询任务状态
        current_response = manager.retrieve_generation(response.id)
        
        if current_response:
            status = current_response.status
            print(f"📊 当前状态: {status}")
            
            if status == "completed":
                print("\n✅ 生成完成!")
                print(f"🆔 任务ID: {current_response.id}")
                print(f"⏱️  创建时间: {current_response.created}")
                print(f"⏱️  完成时间: {current_response.completed}")
                
                if current_response.result and current_response.result.videos:
                    print(f"\n🎬 生成的视频:")
                    for video in current_response.result.videos:
                        print(f"  - ID: {video.id}")
                        print(f"  - URL: {video.url}")
                        print(f"  - 时长: {video.duration_seconds}秒")
                        print(f"  - 分辨率: {video.resolution}")
                        print(f"  - 格式: {video.format}")
                    
                    if current_response.usage:
                        print(f"\n📊 使用统计:")
                        print(f"  - 提示词tokens: {current_response.usage.prompt_tokens}")
                        print(f"  - 总tokens: {current_response.usage.total_tokens}")
                        print(f"  - 视频时长: {current_response.usage.video_seconds}秒")
                
                manager.stop()
                return True
            
            elif status == "failed":
                print(f"\n❌ 生成失败!")
                print(f"错误信息: {current_response.error}")
                manager.stop()
                return False
            
            elif status == "cancelled":
                print(f"\n🚫 任务已取消")
                manager.stop()
                return False
        
        # 等待一段时间后再查询
        time.sleep(5)
    
    print(f"\n⏰ 等待超时 ({max_wait_time}秒)")
    manager.stop()
    return False


def test_config_validation():
    """测试配置验证"""
    print("\n" + "=" * 60)
    print("配置验证测试")
    print("=" * 60)
    
    from config.aiwx_video_config import validate_config, get_api_key, AIWX_VIDEO_CREATE_URL
    
    is_valid, message = validate_config()
    
    if is_valid:
        print(f"✅ {message}")
        print(f"📡 API端点: {AIWX_VIDEO_CREATE_URL}")
        
        try:
            api_key = get_api_key()
            print(f"🔑 API密钥: {api_key[:10]}...{api_key[-4:]}")
        except Exception as e:
            print(f"❌ {e}")
    else:
        print(f"❌ {message}")
    
    return is_valid


if __name__ == "__main__":
    # 首先验证配置
    if not test_config_validation():
        print("\n❌ 配置验证失败，请检查 API 密钥设置")
        sys.exit(1)
    
    # 测试视频生成
    try:
        success = test_aiwx_video_generation()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 测试成功完成!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 测试失败")
            print("=" * 60)
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)