# -*- coding: utf-8 -*-
"""
V2 架构集成测试

测试六层架构的完整集成流程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import logging
logging.basicConfig(level=logging.INFO)

def test_layered_system_prompt():
    """测试分层 System Prompt"""
    print("\n" + "="*60)
    print("测试 LayeredSystemPrompt")
    print("="*60)
    
    from web.services.market_driven.v2_architecture import LayeredSystemPrompt
    
    # 创建分层 System Prompt
    system = LayeredSystemPrompt(
        layer1_core_setting="主角绑定酒剑仙模板，可召唤酒剑仙作战",
        layer3_genre_techniques="国运文技法：弹幕反应、国运值变化、全球排名",
        layer4_writing_style="快节奏、震惊流、每章3-5个爽点"
    )
    
    # 测试组合
    full = system.combine()
    layer3_only = system.combine([3])
    layer34 = system.combine([3, 4])
    
    print(f"完整 System Prompt: {len(full)} 字符")
    print(f"仅 Layer 3: {len(layer3_only)} 字符")
    print(f"Layer 3+4: {len(layer34)} 字符")
    
    # 验证 Layer 3+4 应该是最常用的 System Prompt
    assert len(layer3_only) > 0, "Layer 3 应该包含内容"
    assert "国运文技法" in layer3_only, "Layer 3 应该包含题材技法"
    assert "快节奏" in layer34, "Layer 4 应该包含文风"
    
    print("[OK] LayeredSystemPrompt 测试通过")
    return system


def test_layered_user_prompt():
    """测试分层 User Prompt"""
    print("\n" + "="*60)
    print("测试 LayeredUserPrompt")
    print("="*60)
    
    from web.services.market_driven.v2_architecture import LayeredUserPrompt
    
    # 创建分层 User Prompt
    user = LayeredUserPrompt(
        layer5_ai_constraints="字数: 2000-2500字\n格式: 标准网文章节",
        layer6_self_check="□ 确认弹幕数量≥8条\n□ 确认国运值变化已展示",
        task_instruction="生成第7章：主角击败禁地BOSS，获得S级评价"
    )
    
    # 测试组合
    full = user.combine()
    layer5_only = user.combine([5])
    
    print(f"完整 User Prompt: {len(full)} 字符")
    print(f"仅 Layer 5: {len(layer5_only)} 字符")
    
    assert "字数" in full, "应该包含 AI 约束"
    assert "自检" in full or "确认" in full, "应该包含自检清单"
    assert "生成第7章" in full, "应该包含任务指令"
    
    print("[OK] LayeredUserPrompt 测试通过")
    return user


def test_conversation_session():
    """测试分层对话会话"""
    print("\n" + "="*60)
    print("测试 LayeredConversationSession")
    print("="*60)
    
    from web.services.market_driven.v2_architecture import (
        LayeredConversationSession,
        LayeredSystemPrompt
    )
    
    # 模拟 APIClient
    class MockAPIClient:
        default_provider = "kimi"
        
        def _call_with_messages(self, messages, **kwargs):
            # 记录调用信息
            print(f"  调用API | messages数量: {len(messages)}")
            print(f"  最后user消息长度: {len(messages[-1]['content'])} 字符")
            return "这是生成的章节内容..."
    
    api_client = MockAPIClient()
    
    # 创建 System Prompt
    system = LayeredSystemPrompt(
        layer3_genre_techniques="国运文技法...",
        layer4_writing_style="快节奏写法..."
    )
    
    # 创建会话
    session = LayeredConversationSession(
        api_client=api_client,
        system_prompt=system,
        purpose_prefix="test_v2"
    )
    
    print(f"创建会话成功 | System Prompt: {len(session.system_prompt.combine())} 字符")
    
    # 测试发送消息
    response = session.send_message("生成第1章...")
    print(f"第1轮响应: {len(response) if response else 0} 字符")
    
    # 测试更新 System Prompt
    session.update_system_layer(3, "新的国运文技法...")
    print(f"更新 Layer 3 后 System Prompt: {len(session.system_prompt.combine())} 字符")
    
    # 获取统计
    stats = session.get_stats()
    print(f"会话统计: 轮数={stats['turn_count']}, 消息数={stats['message_count']}")
    
    print("[OK] LayeredConversationSession 测试通过")


def test_chapter_conversation():
    """测试章节对话生成器"""
    print("\n" + "="*60)
    print("测试 ChapterConversationV2")
    print("="*60)
    
    from web.services.market_driven.v2_architecture import ChapterConversationV2
    
    # 模拟 APIClient
    class MockAPIClient:
        default_provider = "kimi"
        
        def _call_with_messages(self, messages, **kwargs):
            return "【模拟章节】主角踏入禁地，弹幕爆炸..."
    
    api_client = MockAPIClient()
    
    # 创建对话生成器
    conversation = ChapterConversationV2(
        api_client=api_client,
        genre="国运文-直播类",
        core_setting="主角绑定酒剑仙模板",
        tactical_planning="第一阶段：初入禁地"
    )
    
    print(f"创建对话生成器成功 | 题材: {conversation.genre}")
    print(f"Layer 3 长度: {len(conversation.layer3_content)} 字符")
    print(f"Layer 4 长度: {len(conversation.layer4_content)} 字符")
    
    # 测试生成章节
    result = conversation.generate_chapter(
        chapter_number=1,
        chapter_title="初入禁地",
        outline_summary="主角觉醒酒剑仙模板，进入国运禁地",
        chapter_type="爆发章"
    )
    
    print(f"生成第1章: {len(result) if result else 0} 字符")
    
    # 查看统计
    stats = conversation.get_session_stats()
    print(f"生成章节数: {stats['generated_chapters']}")
    
    print("[OK] ChapterConversationV2 测试通过")


def test_system_user_separation():
    """测试 System/User Prompt 分离"""
    print("\n" + "="*60)
    print("测试 System/User Prompt 分离")
    print("="*60)
    
    from web.services.market_driven.v2_architecture import (
        LayeredSystemPrompt,
        LayeredUserPrompt,
        ChapterConversationV2
    )
    
    # System Prompt (Layer 3-4): 长期保持
    system = LayeredSystemPrompt(
        layer3_genre_techniques="国运文技法...",
        layer4_writing_style="快节奏写法..."
    )
    system_prompt = system.combine([3, 4])
    
    # User Prompt (Layer 5-6 + 任务): 每章变化
    user = LayeredUserPrompt(
        layer5_ai_constraints="字数2000-2500...",
        layer6_self_check="检查弹幕...",
        task_instruction="生成第7章..."
    )
    user_prompt = user.combine()
    
    print(f"System Prompt: {len(system_prompt)} 字符")
    print(f"User Prompt: {len(user_prompt)} 字符")
    print(f"总长度: {len(system_prompt) + len(user_prompt)} 字符")
    
    # 验证分离效果
    assert "国运文技法" in system_prompt, "System Prompt 应包含题材技法"
    assert "快节奏" in system_prompt, "System Prompt 应包含文风"
    assert "字数" in user_prompt, "User Prompt 应包含AI约束"
    assert "生成第7章" in user_prompt, "User Prompt 应包含任务"
    
    # 下一章：System Prompt 不变，User Prompt 变化
    user2 = LayeredUserPrompt(
        layer5_ai_constraints="字数2000-2500...",
        layer6_self_check="检查弹幕...",
        task_instruction="生成第8章..."  # 变化的部分
    )
    user_prompt2 = user2.combine()
    
    print(f"\n第8章 User Prompt: {len(user_prompt2)} 字符")
    print("System Prompt 保持不变，只有 User Prompt 的任务部分变化")
    
    print("[OK] System/User Prompt 分离测试通过")


def main():
    """主测试函数"""
    print("="*60)
    print("V2 六层架构集成测试")
    print("="*60)
    
    try:
        test_layered_system_prompt()
        test_layered_user_prompt()
        test_conversation_session()
        test_chapter_conversation()
        test_system_user_separation()
        
        print("\n" + "="*60)
        print("所有测试通过!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
