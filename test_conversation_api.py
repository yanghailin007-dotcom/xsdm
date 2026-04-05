"""
测试长篇和短篇的 ConversationSession API 调用
验证：1. 记忆能力 2. 正常返回 3. 格式差异
"""

import sys
sys.path.insert(0, 'c:\\work\\xsdm')

from src.core.APIClient import APIClient, ConversationSession
from config.config import CONFIG

def test_long_form_conversation():
    """测试长篇市场导向模式的 ConversationSession"""
    print("=" * 60)
    print("【测试】长篇 ConversationSession")
    print("=" * 60)
    
    # 初始化 APIClient（与长篇相同）
    api_client = APIClient(config=CONFIG)
    
    # 创建 ConversationSession（与 chapter_conversation_generator.py 相同）
    system_prompt = """你是一位专业的小说写作助手。
要求：
1. 记住前文内容
2. 保持角色一致性
3. 每章结尾留悬念"""
    
    session = ConversationSession(
        api_client=api_client,
        system_prompt=system_prompt,
        provider=api_client.default_provider,
        purpose_prefix="TestLongForm"
    )
    session.max_history = 50
    
    print(f"[OK] 会话创建成功")
    print(f"  - Provider: {api_client.default_provider}")
    print(f"  - Max History: {session.max_history}")
    print()
    
    # 测试多轮对话（记忆能力）
    print("【多轮对话测试 - 记忆能力】")
    
    # 第1轮：设定主角名字
    response1 = session.send_message(
        user_prompt="设定主角名字为'张三'，背景是一个修仙世界。只回复确认信息。",
        purpose="第1轮-设定"
    )
    print(f"第1轮响应: {response1[:100]}...")
    print(f"  历史消息数: {len(session.messages)}")
    
    # 第2轮：询问主角名字（测试记忆）
    response2 = session.send_message(
        user_prompt="刚才设定的主角叫什么名字？只回答名字。",
        purpose="第2轮-记忆测试"
    )
    print(f"第2轮响应: {response2}")
    print(f"  历史消息数: {len(session.messages)}")
    print(f"  [记忆测试] 结果: {'通过' if '张三' in response2 or '张' in response2 else '失败'}")
    print()
    
    return session, response1, response2

def test_short_story_conversation():
    """测试短篇的 ConversationSession"""
    print("=" * 60)
    print("【测试】短篇 ConversationSession")
    print("=" * 60)
    
    # 初始化 APIClient（与短篇相同）
    api_client = APIClient(config=CONFIG)
    
    # 创建 ConversationSession（与 short_story/generator.py 相同）
    system_prompt = """你是一位专业的小说写作助手。
要求：
1. 记住前文内容
2. 保持角色一致性
3. 每章结尾留悬念"""
    
    session = ConversationSession(
        api_client=api_client,
        system_prompt=system_prompt,
        provider=getattr(api_client, 'default_provider', None),
        purpose_prefix="TestShortStory"
    )
    session.max_history = 20
    
    print(f"[OK] 会话创建成功")
    print(f"  - Provider: {getattr(api_client, 'default_provider', None)}")
    print(f"  - Max History: {session.max_history}")
    print()
    
    # 测试多轮对话（记忆能力）
    print("【多轮对话测试 - 记忆能力】")
    
    # 第1轮：设定主角名字
    response1 = session.send_message(
        user_prompt="设定主角名字为'李四'，背景是一个科幻世界。只回复确认信息。",
        purpose="第1轮-设定"
    )
    print(f"第1轮响应: {response1[:100]}...")
    print(f"  历史消息数: {len(session.messages)}")
    
    # 第2轮：询问主角名字（测试记忆）
    response2 = session.send_message(
        user_prompt="刚才设定的主角叫什么名字？只回答名字。",
        purpose="第2轮-记忆测试"
    )
    print(f"第2轮响应: {response2}")
    print(f"  历史消息数: {len(session.messages)}")
    print(f"  [记忆测试] 结果: {'通过' if '李四' in response2 or '李' in response2 else '失败'}")
    print()
    
    return session, response1, response2

def compare_implementations():
    """对比长篇和短篇的实现差异"""
    print("=" * 60)
    print("【对比】长篇 vs 短篇 实现差异")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    
    # 长篇方式
    long_provider = api_client.default_provider
    
    # 短篇方式  
    short_provider = getattr(api_client, 'default_provider', None)
    
    print(f"长篇 provider: {long_provider} (类型: {type(long_provider)})")
    print(f"短篇 provider: {short_provider} (类型: {type(short_provider)})")
    print(f"两者相同: {long_provider == short_provider}")
    print()
    
    # 检查端点池
    print("可用端点池:")
    for provider, pool in api_client.endpoint_pools.items():
        available = pool.get_available_endpoints()
        print(f"  {provider}: {len(available)} 个可用端点")
        for ep in available[:3]:  # 只显示前3个
            print(f"    - {ep.name}: {ep.model}")
    print()

if __name__ == "__main__":
    try:
        # 先对比实现
        compare_implementations()
        
        # 测试长篇
        long_session, long_r1, long_r2 = test_long_form_conversation()
        
        # 测试短篇
        short_session, short_r1, short_r2 = test_short_story_conversation()
        
        print("=" * 60)
        print("【总结】")
        print("=" * 60)
        print(f"长篇测试: {'通过 [OK]' if long_r1 and long_r2 else '失败 [FAIL]'}")
        print(f"短篇测试: {'通过 [OK]' if short_r1 and short_r2 else '失败 [FAIL]'}")
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
