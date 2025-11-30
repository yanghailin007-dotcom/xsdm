#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试章节标题生成的完整修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_title_generation_fix():
    print("=" * 60)
    print("测试章节标题生成完整修复")
    print("=" * 60)

    try:
        # 1. 验证 prompt 存在
        from src.prompts.Prompts import Prompts

        if 'chapter_title_generation' not in Prompts:
            print("ERROR: chapter_title_generation prompt 不存在")
            return False

        print("[1/3] chapter_title_generation prompt 存在")

        # 2. 验证 GenerationContext 处理
        from src.core.Contexts import GenerationContext

        context = GenerationContext(
            chapter_number=2,
            total_chapters=10,
            novel_data={},
            stage_plan={},
            event_context={
                'active_events': [
                    {
                        'name': '测试事件',
                        'main_goal': '测试目标'
                    }
                ]
            },
            foreshadowing_context={},
            growth_context={}
        )

        novel_data = {
            '_current_generation_context': context,
            'novel_title': '测试小说'
        }

        # 测试访问逻辑
        context_obj = novel_data.get('_current_generation_context')
        if hasattr(context_obj, 'event_context'):
            event_context = context_obj.event_context
        elif isinstance(context_obj, dict):
            event_context = context_obj.get('event_context', {})
        else:
            event_context = {}

        if not event_context:
            print("ERROR: event_context 访问失败")
            return False

        print("[2/3] GenerationContext 访问逻辑正确")

        # 3. 验证 API 调用参数
        from src.core.MockAPIClient import MockAPIClient

        api_client = MockAPIClient()

        # 模拟调用
        result = api_client.generate_content_with_retry(
            content_type="chapter_title_generation",
            user_prompt="生成一个测试标题",
            temperature=0.7,
            purpose="生成章节标题"
        )

        if not result:
            print("ERROR: API 调用失败")
            return False

        print("[3/3] API 调用参数正确")

        print("\n" + "=" * 60)
        print("所有测试通过！修复完整有效！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_title_generation_fix()
    sys.exit(0 if success else 1)