"""
测试 VeO API 格式修复
验证是否与用户提供的原始 API 调用格式一致
"""
import json
import sys
import io
from pathlib import Path

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.models.veo_models import VeOCreateVideoRequest, VeOVideoRequest
from config.aiwx_video_config import get_request_headers


def test_api_format():
    """测试 API 格式是否与用户的原始代码一致"""
    
    print("=" * 80)
    print("🧪 测试 VeO API 格式修复")
    print("=" * 80)
    
    # 1. 测试请求头
    print("\n1️⃣ 测试请求头格式:")
    print("-" * 80)
    headers = get_request_headers()
    
    print(f"✅ Authorization: {headers.get('Authorization', 'N/A')}")
    print(f"✅ Content-Type: {headers.get('Content-Type', 'N/A')}")
    print(f"✅ User-Agent: {headers.get('User-Agent', 'N/A')}")
    print(f"✅ Accept: {headers.get('Accept', 'N/A')}")
    print(f"✅ Host: {headers.get('Host', 'N/A')}")
    print(f"✅ Connection: {headers.get('Connection', 'N/A')}")
    
    # 验证 Authorization 格式（应该没有 Bearer 前缀）
    auth = headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        print("❌ 错误: Authorization 包含 Bearer 前缀")
    elif auth.startswith('sk-'):
        print("✅ 正确: Authorization 直接使用 API Key（无 Bearer 前缀）")
    else:
        print(f"⚠️  警告: Authorization 格式异常: {auth}")
    
    # 2. 测试 payload 格式
    print("\n2️⃣ 测试 Payload 格式:")
    print("-" * 80)
    
    # 创建一个测试请求
    request = VeOVideoRequest(
        model="veo_3_1-fast",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "make animate"}
            ]
        }]
    )
    
    # 转换为原生格式
    native_request = VeOCreateVideoRequest.from_openai_format(request)
    payload = native_request.to_dict()
    
    print("\n📦 生成的 Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # 3. 对比用户的原始 payload
    print("\n3️⃣ 对比用户的原始 Payload:")
    print("-" * 80)
    
    original_payload = {
        "images": [],
        "model": "veo_3_1-fast",
        "orientation": "portrait",
        "prompt": "make animate",
        "size": "large",
        "duration": 15,
        "watermark": False,
        "private": True
    }
    
    print("\n📦 用户的原始 Payload:")
    print(json.dumps(original_payload, indent=2, ensure_ascii=False))
    
    # 4. 验证关键字段
    print("\n4️⃣ 验证关键字段:")
    print("-" * 80)
    
    checks = [
        ("model", payload.get("model") == "veo_3_1-fast", "模型名称应为 veo_3_1-fast"),
        ("orientation", payload.get("orientation") == "portrait", "方向应为 portrait"),
        ("size", payload.get("size") == "large", "尺寸应为 large"),
        ("duration", payload.get("duration") == 15, "时长应为 15 秒"),
        ("watermark", "watermark" in payload, "应包含 watermark 字段"),
        ("watermark_value", payload.get("watermark") == False, "watermark 应为 False"),
        ("private", "private" in payload, "应包含 private 字段"),
        ("private_value", payload.get("private") == True, "private 应为 True"),
    ]
    
    all_passed = True
    for key, passed, description in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {key}: {description}")
        if not passed:
            all_passed = False
    
    # 5. 检查不应该存在的字段
    print("\n5️⃣ 检查不应存在的字段:")
    print("-" * 80)
    
    unwanted_fields = ["aspect_ratio", "enable_upsample"]
    for field in unwanted_fields:
        if field in payload:
            print(f"❌ 错误: payload 包含不应存在的字段 '{field}'")
            all_passed = False
        else:
            print(f"✅ 正确: payload 不包含字段 '{field}'")
    
    # 6. 最终结果
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有测试通过！API 格式修复成功！")
    else:
        print("❌ 部分测试失败，需要进一步修复")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = test_api_format()
    sys.exit(0 if success else 1)