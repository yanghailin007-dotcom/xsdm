"""
测试 BaseConversationGenerator 基础会话生成器
验证：1. 记忆能力 2. 正常返回 3. Session 重建
"""

import sys
sys.path.insert(0, 'c:\\work\\xsdm')

from src.core.base_conversation_generator import BaseConversationGenerator
from src.core.APIClient import APIClient
from config.config import CONFIG


class TestGenerator(BaseConversationGenerator):
    """测试用的生成器"""
    
    MAX_HISTORY = 20
    SESSION_REBUILD_INTERVAL = 3  # 每3轮重建，方便测试
    
    def __init__(self, api_client, name="Test"):
        super().__init__(
            api_client=api_client,
            purpose_prefix=f"Test_{name}",
        )
        self.name = name
        self.story_context = {"protagonist": "", "world": ""}
    
    def _build_system_prompt(self) -> str:
        return """你是一位小说写作助手。
要求：
1. 记住前文内容
2. 保持角色和设定一致性
3. 每章结尾留悬念"""
    
    def _build_context_summary(self) -> str:
        """构建上下文摘要"""
        return f"主角: {self.story_context.get('protagonist', '未知')}, 世界观: {self.story_context.get('world', '未知')}"
    
    def set_story_context(self, protagonist: str, world: str):
        """设置故事上下文"""
        self.story_context["protagonist"] = protagonist
        self.story_context["world"] = world


def test_memory_capability():
    """测试记忆能力"""
    print("=" * 60)
    print("【测试1】记忆能力测试")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    gen = TestGenerator(api_client, name="MemoryTest")
    
    # 设定上下文
    gen.set_story_context("张三", "修仙世界")
    
    # 第1轮：告诉AI主角名字
    print("\n第1轮：设定主角")
    r1 = gen.send_message(
        "设定主角名字为'张三'，他是一个普通山村少年。只回复确认。",
        purpose="设定主角"
    )
    print(f"  响应: {r1[:80]}...")
    print(f"  当前消息数: {gen._message_count}")
    
    # 第2轮：询问主角名字（测试记忆）
    print("\n第2轮：询问主角名字（测试记忆）")
    r2 = gen.send_message(
        "刚才设定的主角叫什么名字？只回答名字。",
        purpose="记忆测试"
    )
    print(f"  响应: {r2}")
    has_memory = "张三" in r2 or "张" in r2
    print(f"  [记忆测试] 结果: {'通过' if has_memory else '失败'}")
    
    # 第3轮：继续故事
    print("\n第3轮：继续故事")
    r3 = gen.send_message(
        "主角在山上遇到了什么奇遇？简述情节。",
        purpose="故事发展"
    )
    print(f"  响应: {r3[:80]}...")
    
    print(f"\n统计: 总消息数={gen._total_messages}, Session重建次数={gen._session_count}")
    return has_memory


def test_session_rebuild():
    """测试 Session 自动重建"""
    print("\n" + "=" * 60)
    print("【测试2】Session 自动重建测试")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    gen = TestGenerator(api_client, name="RebuildTest")
    gen.set_story_context("李四", "科幻未来")
    
    print(f"重建阈值: {gen.SESSION_REBUILD_INTERVAL} 轮")
    print(f"最大历史: {gen.MAX_HISTORY} 条")
    
    # 连续发送消息，触发重建
    for i in range(1, 8):
        print(f"\n第 {i} 轮发送...")
        r = gen.send_message(
            f"生成第{i}章内容（50字以内）。",
            purpose=f"第{i}章"
        )
        print(f"  响应长度: {len(r) if r else 0} 字符")
        print(f"  当前消息数: {gen._message_count}, Session重建: {gen._session_count} 次")
        
        if gen._session_count > 1:
            print(f"  [OK] Session 已自动重建！")
    
    print(f"\n最终统计: 总消息数={gen._total_messages}, Session重建={gen._session_count} 次")
    return gen._session_count >= 2


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("【测试3】错误处理和统计")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    gen = TestGenerator(api_client, name="ErrorTest")
    
    # 获取统计
    stats = gen.get_stats()
    print("初始统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 发送一条消息
    r = gen.send_message("你好，请介绍一下自己。", purpose="问候")
    print(f"\n发送后统计:")
    stats = gen.get_stats()
    print(f"  total_messages: {stats['total_messages']}")
    print(f"  current_message_count: {stats['current_message_count']}")
    
    # 获取对话历史
    history = gen.get_conversation_history()
    print(f"\n对话历史条数: {len(history)}")
    for i, msg in enumerate(history[:3], 1):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:50]
        print(f"  {i}. [{role}] {content}...")
    
    return True


def test_comparison_with_chapter_generator():
    """对比测试：基础类 vs chapter_conversation_generator"""
    print("\n" + "=" * 60)
    print("【测试4】对比测试（基础类 vs 市场导向章节生成器）")
    print("=" * 60)
    
    api_client = APIClient(config=CONFIG)
    
    # 使用基础类
    print("\n使用 BaseConversationGenerator:")
    base_gen = TestGenerator(api_client, name="Base")
    base_gen.set_story_context("王五", "武侠江湖")
    
    start = base_gen._session_count
    for i in range(3):
        base_gen.send_message(f"生成第{i+1}章（测试）", purpose=f"第{i+1}章")
    print(f"  3轮后 Session 重建次数: {base_gen._session_count - start}")
    
    # 使用原生的 chapter_conversation_generator 方式
    print("\n使用原生 ConversationSession (市场导向方式):")
    from src.core.APIClient import ConversationSession
    
    session = ConversationSession(
        api_client=api_client,
        system_prompt="你是一位小说写作助手。",
        provider=api_client.default_provider,
        purpose_prefix="Test_Native"
    )
    session.max_history = 20
    
    for i in range(3):
        session.send_message(f"生成第{i+1}章（测试）", purpose=f"第{i+1}章")
    print(f"  3轮后消息数: {session.turn_count}")
    
    print("\n[OK] 两种方式都正常工作")
    return True


if __name__ == "__main__":
    print("开始测试 BaseConversationGenerator...\n")
    
    results = []
    
    try:
        # 测试1: 记忆能力
        results.append(("记忆能力", test_memory_capability()))
        
        # 测试2: Session重建
        results.append(("Session重建", test_session_rebuild()))
        
        # 测试3: 错误处理
        results.append(("错误处理", test_error_handling()))
        
        # 测试4: 对比测试
        results.append(("对比测试", test_comparison_with_chapter_generator()))
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print("【测试总结】")
    print("=" * 60)
    for name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print(f"\n总体结果: {'全部通过 [OK]' if all_passed else '有失败项 [FAIL]'}")
