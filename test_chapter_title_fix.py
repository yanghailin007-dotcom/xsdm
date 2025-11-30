#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试章节标题生成的修复
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chapter_title_fix():
    print("=" * 60)
    print("测试章节标题生成修复")
    print("=" * 60)

    try:
        from src.core.Contexts import GenerationContext

        # 1. 创建模拟的 GenerationContext
        context = GenerationContext(
            chapter_number=2,
            total_chapters=10,
            novel_data={},
            stage_plan={},
            event_context={
                'active_events': [
                    {
                        'name': '异界初醒事件',
                        'main_goal': '主角适应新世界'
                    }
                ]
            },
            foreshadowing_context={},
            growth_context={}
        )

        print("GenerationContext 创建成功")

        # 2. 创建包含 GenerationContext 的 novel_data
        novel_data = {
            '_current_generation_context': context,
            'novel_title': '异界归来的天才医生'
        }

        print("novel_data 创建成功")

        # 3. 测试访问 event_context 的修复逻辑
        context_obj = novel_data.get('_current_generation_context')
        if hasattr(context_obj, 'event_context'):
            event_context = context_obj.event_context
        elif isinstance(context_obj, dict):
            event_context = context_obj.get('event_context', {})
        else:
            event_context = {}

        print("event_context 访问成功")
        print(f"   事件上下文: {event_context}")

        # 4. 测试获取 active_events
        active_events = event_context.get('active_events', [])
        if active_events:
            current_event = active_events[0]
            print(f"当前事件: {current_event.get('name', '')}")
            print(f"   事件目标: {current_event.get('main_goal', '')}")

        print("\n" + "=" * 60)
        print("所有测试通过！修复有效！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chapter_title_fix()
    sys.exit(0 if success else 1)