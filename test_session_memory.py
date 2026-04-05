"""
测试 ConversationSession 的历史记忆能力
验证：1. 记忆能力 2. 历史维护 3. 不同场景调用
"""

import sys
sys.path.insert(0, r'c:\work\xsdm')

from src.core.APIClient import APIClient, ConversationSession
from config.config import CONFIG


def test_memory_capability():
    """测试记忆能力 - 短篇风格调用"""
    print("=" * 60)
    print("[测试1] 短篇风格 ConversationSession - 记忆能力")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    
    # 短篇风格：max_history=20
    session = ConversationSession(
        api_client=api_client,
        system_prompt="你是一位专业小说作家。要求：1.记住前文 2.保持一致性",
        provider=api_client.default_provider,
        purpose_prefix="TestShort"
    )
    session.max_history = 20
    
    print(f"[OK] 会话创建成功 | Provider: {api_client.default_provider}")
    print(f"     Max History: {session.max_history}")
    print()
    
    # 多轮对话测试
    print("[多轮对话测试]")
    
    # 第1轮：设定
    print("第1轮: 设定主角名字为'张三'")
    r1 = session.send_message(
        "设定主角名字为'张三'，背景是修仙世界。只回复确认。",
        purpose="设定主角"
    )
    print(f"  响应: {r1[:60]}...")
    print(f"  历史消息数: {len(session.messages)} (system + 第1轮)")
    
    # 第2轮：测试记忆
    print("\n第2轮: 询问主角名字(测试记忆)")
    r2 = session.send_message(
        "刚才设定的主角叫什么名字？只回答名字。",
        purpose="记忆测试"
    )
    print(f"  响应: {r2}")
    print(f"  历史消息数: {len(session.messages)}")
    has_memory = "张三" in r2 or "张" in r2
    print(f"  [记忆测试] {'通过' if has_memory else '失败'}")
    
    # 第3轮：继续故事
    print("\n第3轮: 继续故事发展")
    r3 = session.send_message(
        "主角在山上遇到了什么？简述情节(30字以内)。",
        purpose="故事发展"
    )
    print(f"  响应: {r3[:60]}...")
    print(f"  历史消息数: {len(session.messages)}")
    
    print(f"\n[统计] 对话轮数: {session.turn_count}, 总消息数: {len(session.messages)}")
    return has_memory


def test_long_form_session():
    """测试长篇风格 - 大历史容量"""
    print("\n" + "=" * 60)
    print("[测试2] 长篇风格 ConversationSession - 大历史容量")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    
    # 长篇风格：max_history=50
    session = ConversationSession(
        api_client=api_client,
        system_prompt="你是一位专业小说作家。要求：1.记住前文 2.保持一致性 3.留悬念",
        provider=api_client.default_provider,
        purpose_prefix="TestLong"
    )
    session.max_history = 50
    
    print(f"[OK] 会话创建成功 | Max History: {session.max_history}")
    print()
    
    # 模拟多章节生成
    print("[模拟多章节生成]")
    for i in range(1, 6):
        r = session.send_message(
            f"生成第{i}章内容(50字以内)。",
            purpose=f"第{i}章"
        )
        print(f"第{i}章: {r[:50]}... | 消息数: {len(session.messages)}")
    
    print(f"\n[统计] 对话轮数: {session.turn_count}, 总消息数: {len(session.messages)}")
    return session.turn_count == 5


def test_history_structure():
    """测试历史消息结构"""
    print("\n" + "=" * 60)
    print("[测试3] 验证历史消息结构")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    
    session = ConversationSession(
        api_client=api_client,
        system_prompt="你是作家",
        provider=api_client.default_provider,
        purpose_prefix="TestStruct"
    )
    
    # 发送2轮消息
    session.send_message("设定主角为李四", purpose="设定")
    session.send_message("李四遇到了谁？", purpose="发展")
    
    print(f"总消息数: {len(session.messages)}")
    print("消息结构:")
    for i, msg in enumerate(session.messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:40]
        print(f"  {i}. [{role}] {content}...")
    
    # 验证结构
    is_valid = (
        len(session.messages) >= 5 and  # system + 2轮(user+assistant)
        session.messages[0].get('role') == 'system' and
        session.messages[1].get('role') == 'user' and
        session.messages[2].get('role') == 'assistant'
    )
    print(f"\n[结构验证] {'通过' if is_valid else '失败'}")
    return is_valid


def show_usage_example():
    """展示实际使用示例"""
    print("\n" + "=" * 60)
    print("[使用示例] ConversationSession 正确调用方式")
    print("=" * 60)
    print("""
# 方式1: 直接使用 ConversationSession (短篇/测试)
from src.core.APIClient import APIClient, ConversationSession
from config.config import CONFIG

api_client = APIClient(config=CONFIG)
session = ConversationSession(
    api_client=api_client,
    system_prompt="你是一位小说作家...",
    provider=api_client.default_provider,  # 或 "kimi", "gemini"
    purpose_prefix="MyNovel"  # 日志和扣费标识
)
session.max_history = 20  # 短篇20条

# 多轮对话(自动维护历史)
chapter1 = session.send_message("写第1章...", purpose="第1章")
chapter2 = session.send_message("继续写第2章...", purpose="第2章")

# 查看状态
print(f"对话轮数: {session.turn_count}")
print(f"消息数量: {len(session.messages)}")


# 方式2: 长篇生成(大历史容量)
session = ConversationSession(...)
session.max_history = 50  # 长篇50条

for i in range(1, 101):
    chapter = session.send_message(f"写第{i}章...", purpose=f"第{i}章")
    # 历史自动裁剪，保持最近50条
""")


if __name__ == "__main__":
    print("开始测试 ConversationSession 记忆能力...\n")
    
    results = []
    
    try:
        results.append(("短篇记忆测试", test_memory_capability()))
        results.append(("长篇容量测试", test_long_form_session()))
        results.append(("历史结构验证", test_history_structure()))
        show_usage_example()
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print("[测试总结]")
    print("=" * 60)
    for name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print(f"\n总体结果: {'全部通过 [OK]' if all_passed else '有失败项 [FAIL]'}")
