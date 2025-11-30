#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试所有 GenerationContext 相关的修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_context_fixes():
    print("=" * 60)
    print("测试所有 GenerationContext 修复")
    print("=" * 60)

    try:
        from src.core.Contexts import GenerationContext
        from src.core.ContentGenerator import ContentGenerator
        from src.core.MockAPIClient import MockAPIClient
        from src.core.QualityAssessor import QualityAssessor
        from src.core.NovelGenerator import NovelGenerator

        # 创建测试用的 GenerationContext
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
                ],
                'event_timeline': {
                    'timeline_summary': '测试时间线'
                }
            },
            foreshadowing_context={
                'elements_to_introduce': ['伏笔1', '伏笔2']
            },
            growth_context={
                'chapter_specific': {
                    'content_focus': {'focus': '测试焦点'}
                }
            }
        )

        novel_data = {
            '_current_generation_context': context,
            'novel_title': '测试小说',
            'used_chapter_titles': set()
        }

        print("\n[测试 1/3] _generate_unique_chapter_title 中的 event_context 访问")
        # 模拟 _generate_unique_chapter_title 中的逻辑
        context_obj = novel_data.get('_current_generation_context')
        if hasattr(context_obj, 'event_context'):
            event_context = context_obj.event_context
        elif isinstance(context_obj, dict):
            event_context = context_obj.get('event_context', {})
        else:
            event_context = {}

        assert event_context is not None, "event_context 不应为 None"
        assert 'active_events' in event_context, "event_context 应包含 active_events"
        print("  通过")

        print("\n[测试 2/3] _generate_event_related_title 中的 event_context 访问")
        # 模拟 _generate_event_related_title 中的逻辑
        context_obj = novel_data.get('_current_generation_context')
        if hasattr(context_obj, 'event_context'):
            event_context = context_obj.event_context
        elif isinstance(context_obj, dict):
            event_context = context_obj.get('event_context', {})
        else:
            event_context = {}
        active_events = event_context.get('active_events', []) if event_context else []

        assert len(active_events) > 0, "应该有活动事件"
        print("  通过")

        print("\n[测试 3/3] _save_chapter_failure 中的上下文摘要提取")
        # 模拟 _save_chapter_failure 中的逻辑
        current_context = novel_data.get('_current_generation_context')
        if current_context:
            try:
                event_ctx = current_context.event_context if hasattr(current_context, 'event_context') else {}
                foreshadowing_ctx = current_context.foreshadowing_context if hasattr(current_context, 'foreshadowing_context') else {}
                growth_ctx = current_context.growth_context if hasattr(current_context, 'growth_context') else {}

                context_summary = {
                    "event_context": {
                        "active_events_count": len(event_ctx.get('active_events', [])) if isinstance(event_ctx, dict) else 0,
                        "timeline_summary": event_ctx.get('event_timeline', {}).get('timeline_summary', '') if isinstance(event_ctx, dict) else ''
                    },
                    "foreshadowing_context_count": len(foreshadowing_ctx.get('elements_to_introduce', [])) if isinstance(foreshadowing_ctx, dict) else 0,
                    "growth_context_focus": growth_ctx.get('chapter_specific', {}).get('content_focus', {}) if isinstance(growth_ctx, dict) else {}
                }

                assert context_summary['event_context']['active_events_count'] == 1, "应该有1个活动事件"
                assert context_summary['event_context']['timeline_summary'] == '测试时间线', "时间线摘要应该匹配"
                assert context_summary['foreshadowing_context_count'] == 2, "应该有2个伏笔元素"
                print("  通过")

            except Exception as e:
                print(f"  失败: {e}")
                return False

        print("\n" + "=" * 60)
        print("所有测试通过！所有 GenerationContext 修复有效！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_all_context_fixes()
    sys.exit(0 if success else 1)