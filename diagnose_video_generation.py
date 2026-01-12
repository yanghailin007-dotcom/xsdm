"""
视频生成配置诊断工具
"""
import os
import sys
import io
from pathlib import Path

# 设置UTF-8输出以支持emoji
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config.videoconfig import (
    GOOGLE_AI_API_KEY,
    DEFAULT_GOOGLE_MODEL,
    get_api_endpoint,
    validate_config
)

def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_api_key():
    """检查API Key配置"""
    print_section("1. API Key 检查")
    
    print(f"📝 API Key 长度: {len(GOOGLE_AI_API_KEY)}")
    print(f"🔑 API Key 前缀: {GOOGLE_AI_API_KEY[:10]}...")
    
    # 检查格式
    if GOOGLE_AI_API_KEY.startswith("AIza"):
        print("✅ API Key 格式正确（以 AIza 开头）")
    elif GOOGLE_AI_API_KEY.startswith("AQ."):
        print("❌ API Key 格式异常（以 AQ. 开头）")
        print("   这看起来像是一个访问令牌，不是API密钥")
        print("   请使用以 'AIza' 开头的标准 Google AI API Key")
    else:
        print("⚠️  API Key 格式未知")
    
    print(f"\n📌 完整 API Key: {GOOGLE_AI_API_KEY[:20]}...{GOOGLE_AI_API_KEY[-10:]}")

def check_model():
    """检查模型配置"""
    print_section("2. 模型配置检查")
    
    print(f"🎬 默认模型: {DEFAULT_GOOGLE_MODEL}")
    
    valid_models = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-pro",
        "gemini-pro-vision"
    ]
    
    if DEFAULT_GOOGLE_MODEL in valid_models:
        print("✅ 模型名称有效")
    else:
        print("⚠️  模型名称可能无效")
        print(f"   有效模型列表: {', '.join(valid_models)}")

def check_endpoint():
    """检查API端点"""
    print_section("3. API 端点检查")
    
    try:
        endpoint = get_api_endpoint()
        print(f"🌐 API 端点: {endpoint}")
        
        # 检查端点格式
        if "aiplatform.googleapis.com" in endpoint:
            print("✅ 使用 Google AI Platform 端点")
        elif "generativelanguage.googleapis.com" in endpoint:
            print("✅ 使用 Generative Language API 端点")
        else:
            print("⚠️  未知的API端点")
    except Exception as e:
        print(f"❌ 获取端点失败: {e}")

def check_video_support():
    """检查视频生成支持"""
    print_section("4. 视频生成支持检查")
    
    print("⚠️  重要提示：")
    print("   Google Gemini API 主要用于文本生成")
    print("   目前不直接支持视频生成功能")
    print()
    print("📋 可用的AI视频生成选项：")
    print("   1. OpenAI Sora API（需申请访问权限）")
    print("   2. Runway Gen-2 API")
    print("   3. Stability AI Video API")
    print("   4. Replicate Video APIs")

def main():
    """主函数"""
    print("🔍 Google AI 视频生成配置诊断")
    print("="*60)
    
    # 检查配置
    is_valid, message = validate_config()
    print(f"\n配置验证结果: {message}")
    
    # 详细检查
    check_api_key()
    check_model()
    check_endpoint()
    check_video_support()
    
    # 建议
    print_section("💡 建议和解决方案")
    
    print("1. 获取正确的 API Key：")
    print("   访问: https://makersuite.google.com/app/apikey")
    print("   创建新的 API Key（应以 'AIza' 开头）")
    print()
    
    print("2. 使用支持视频生成的服务：")
    print("   - OpenAI: https://platform.openai.com/")
    print("   - Runway: https://runwayml.com/")
    print("   - Replicate: https://replicate.com/")
    print()
    
    print("3. 如果坚持使用 Google：")
    print("   - 使用 Gemini API 生成文本描述")
    print("   - 将描述传递给专业的视频生成API")
    print("   - 或使用 Google Cloud Video Intelligence API（分析而非生成）")

if __name__ == "__main__":
    main()