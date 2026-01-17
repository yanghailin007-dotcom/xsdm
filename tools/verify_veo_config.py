"""
快速验证 VeO API 配置
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 重新导入配置（避免缓存）
import importlib
if 'config.aiwx_video_config' in sys.modules:
    del sys.modules['config.aiwx_video_config']

from config.aiwx_video_config import get_request_headers

print("=" * 60)
print("验证 VeO API 请求头配置")
print("=" * 60)

headers = get_request_headers()

print("\n当前请求头配置:")
for key, value in headers.items():
    if key == 'Authorization':
        print(f"  {key}: {value[:30]}...")
    else:
        print(f"  {key}: {value}")

print("\n检查结果:")
issues = []

# 检查是否有 Host 头（不应该有）
if 'Host' in headers:
    issues.append("❌ 发现手动设置的 Host 头（应该移除）")
else:
    print("✅ 没有手动设置 Host 头")

# 检查是否有 Connection 头（不应该有）
if 'Connection' in headers:
    issues.append("❌ 发现手动设置的 Connection 头（应该移除）")
else:
    print("✅ 没有手动设置 Connection 头")

# 检查必需的请求头
required_headers = ['Content-Type', 'Authorization', 'User-Agent']
for header in required_headers:
    if header in headers:
        print(f"✅ 包含必需的 {header} 头")
    else:
        issues.append(f"❌ 缺少必需的 {header} 头")

# 检查 User-Agent 是否正确
if headers.get('User-Agent') == 'Apifox/1.0.0 (https://apifox.com)':
    print("✅ User-Agent 设置正确")
else:
    issues.append(f"❌ User-Agent 设置不正确: {headers.get('User-Agent')}")

print("\n" + "=" * 60)
if issues:
    print("配置问题:")
    for issue in issues:
        print(f"  {issue}")
    print("\n⚠️ 配置存在问题，请检查 config/aiwx_video_config.py")
else:
    print("✅ 配置完全正确！")
    print("\n📝 下一步：重启 Web 服务器以加载新配置")
    print("   方法 1: 在 VS Code 中按 Ctrl+Shift+P，输入 'Reload Window'")
    print("   方法 2: 停止服务器后重新启动")
print("=" * 60)
