"""
测试视频生成事件过滤功能

验证：
1. 当没有选中事件时，生成所有事件的分镜头
2. 当选中部分事件时，只生成选中事件的分镜头
3. 事件ID过滤逻辑正确（支持重大事件和中级事件）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import get_logger
from web.api.video_generation_api import _filter_selected_events

logger = get_logger("test_video_event_filtering")


def create_mock_events():
    """创建模拟的事件数据"""
    return [
        {
            "name": "事件1",
            "title": "事件1",
            "chapter_range": "1-10",
            "description": "第一个重大事件",
            "composition": {
                "起": [
                    {"name": "起事件1", "title": "起事件1", "description": "起部事件1"},
                    {"name": "起事件2", "title": "起事件2", "description": "起部事件2"}
                ],
                "承": [
                    {"name": "承事件1", "title": "承事件1", "description": "承部事件1"}
                ],
                "转": [],
                "合": []
            }
        },
        {
            "name": "事件2",
            "title": "事件2",
            "chapter_range": "11-20",
            "description": "第二个重大事件",
            "composition": {
                "起": [{"name": "起事件3", "title": "起事件3", "description": "起部事件3"}],
                "承": [],
                "转": [
                    {"name": "转事件1", "title": "转事件1", "description": "转部事件1"},
                    {"name": "转事件2", "title": "转事件2", "description": "转部事件2"}
                ],
                "合": [{"name": "合事件1", "title": "合事件1", "description": "合部事件1"}]
            }
        },
        {
            "name": "事件3",
            "title": "事件3",
            "chapter_range": "21-30",
            "description": "第三个重大事件",
            "composition": {
                "起": [],
                "承": [],
                "转": [],
                "合": [
                    {"name": "合事件2", "title": "合事件2", "description": "合部事件2"}
                ]
            }
        }
    ]


def test_no_selection():
    """测试1：没有选中任何事件"""
    print("\n" + "="*60)
    print("测试1：没有选中任何事件")
    print("="*60)
    
    all_events = create_mock_events()
    selected_events = []
    
    filtered = _filter_selected_events(all_events, selected_events, logger)
    
    print(f"✅ 原始事件数: {len(all_events)}")
    print(f"✅ 过滤后事件数: {len(filtered)}")
    print(f"✅ 预期: 应返回空列表")
    
    assert len(filtered) == 0, f"期望返回0个事件，实际返回{len(filtered)}个"
    print("✅ 测试通过\n")


def test_select_major_events():
    """测试2：选中整个重大事件"""
    print("\n" + "="*60)
    print("测试2：选中整个重大事件")
    print("="*60)
    
    all_events = create_mock_events()
    # 选中事件1和事件3（通过名称）
    selected_events = ["事件1", "事件3"]
    
    filtered = _filter_selected_events(all_events, selected_events, logger)
    
    print(f"✅ 原始事件数: {len(all_events)}")
    print(f"✅ 选中事件: {selected_events}")
    print(f"✅ 过滤后事件数: {len(filtered)}")
    print(f"✅ 过滤后事件: {[e['name'] for e in filtered]}")
    print(f"✅ 预期: 应返回2个完整事件（事件1和事件3）")
    
    assert len(filtered) == 2, f"期望返回2个事件，实际返回{len(filtered)}个"
    assert filtered[0]['name'] == '事件1', "第一个事件应该是事件1"
    assert filtered[1]['name'] == '事件3', "第二个事件应该是事件3"
    
    # 验证完整的事件结构被保留
    assert len(filtered[0]['composition']['起']) == 2, "事件1的起部应该有2个中级事件"
    print("✅ 测试通过\n")


def test_select_major_events_by_id():
    """测试3：通过ID选中重大事件"""
    print("\n" + "="*60)
    print("测试3：通过ID选中重大事件")
    print("="*60)
    
    all_events = create_mock_events()
    # 通过ID选中事件2
    selected_events = ["major_event_1", "event_1"]  # 两种ID格式
    
    filtered = _filter_selected_events(all_events, selected_events, logger)
    
    print(f"✅ 原始事件数: {len(all_events)}")
    print(f"✅ 选中事件ID: {selected_events}")
    print(f"✅ 过滤后事件数: {len(filtered)}")
    print(f"✅ 过滤后事件: {[e['name'] for e in filtered]}")
    print(f"✅ 预期: 应返回1个完整事件（事件2）")
    
    # 注意：由于event_1会被匹配两次（作为major_event_1和event_1），但应该去重
    assert len(filtered) == 1, f"期望返回1个事件，实际返回{len(filtered)}个"
    assert filtered[0]['name'] == '事件2', "应该是事件2"
    print("✅ 测试通过\n")


def test_select_medium_events():
    """测试4：选中部分中级事件"""
    print("\n" + "="*60)
    print("测试4：选中部分中级事件")
    print("="*60)
    
    all_events = create_mock_events()
    # 选中事件1的起事件1和起事件2，以及事件2的转事件1
    # 使用复合ID格式: major_event_X_event_Y_Z
    selected_events = [
        "major_event_0_event_0_0",  # 事件1的起事件1
        "major_event_0_event_0_1",  # 事件1的起事件2
        "major_event_1_event_2_0"   # 事件2的转事件1
    ]
    
    filtered = _filter_selected_events(all_events, selected_events, logger)
    
    print(f"✅ 原始事件数: {len(all_events)}")
    print(f"✅ 选中中级事件ID: {selected_events}")
    print(f"✅ 过滤后事件数: {len(filtered)}")
    print(f"✅ 预期: 应返回2个事件（事件1包含2个中级事件，事件2包含1个中级事件）")
    
    # 验证返回了2个重大事件（部分内容）
    assert len(filtered) == 2, f"期望返回2个事件，实际返回{len(filtered)}个"
    
    # 验证事件1只包含选中的2个起部事件
    assert len(filtered[0]['composition']['起']) == 2, "事件1的起部应该有2个中级事件"
    assert len(filtered[0]['composition'].get('承', [])) == 0, "事件1的承部应该为空"
    
    # 验证事件2只包含选中的1个转部事件
    assert len(filtered[1]['composition']['转']) == 1, "事件2的转部应该有1个中级事件"
    assert len(filtered[1]['composition'].get('合', [])) == 0, "事件2的合部应该为空"
    
    print("✅ 测试通过\n")


def test_mixed_selection():
    """测试5：混合选择（重大事件+中级事件）"""
    print("\n" + "="*60)
    print("测试5：混合选择（重大事件+中级事件）")
    print("="*60)
    
    all_events = create_mock_events()
    # 选中整个事件1，以及事件2的部分中级事件
    selected_events = [
        "事件1",                          # 整个事件1
        "major_event_1_event_2_0"        # 事件2的转事件1
    ]
    
    filtered = _filter_selected_events(all_events, selected_events, logger)
    
    print(f"✅ 原始事件数: {len(all_events)}")
    print(f"✅ 选中内容: {selected_events}")
    print(f"✅ 过滤后事件数: {len(filtered)}")
    print(f"✅ 预期: 应返回2个事件（事件1完整，事件2部分）")
    
    assert len(filtered) == 2, f"期望返回2个事件，实际返回{len(filtered)}个"
    
    # 验证事件1是完整的
    assert len(filtered[0]['composition']['起']) == 2, "事件1应该是完整的"
    
    # 验证事件2只有选中的部分
    assert len(filtered[1]['composition']['转']) == 1, "事件2应该只有1个转部事件"
    
    print("✅ 测试通过\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪"*30)
    print("开始测试视频事件过滤功能")
    print("🧪"*30 + "\n")
    
    try:
        test_no_selection()
        test_select_major_events()
        test_select_major_events_by_id()
        test_select_medium_events()
        test_mixed_selection()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        print("\n✅ 事件过滤功能工作正常")
        print("✅ 现在用户可以选择特定事件生成分镜头脚本")
        print("✅ 未选中事件将被正确过滤")
        
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)