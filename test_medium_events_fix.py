"""
测试中级事件提取修复

验证 LongSeriesStrategy 和 video_generation_api 能正确提取中级事件
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import get_logger
from src.managers.EventExtractor import get_event_extractor
from src.managers.VideoAdapterManager import VideoAdapterManager

logger = get_logger("test_medium_events_fix")


def create_test_major_event_old_format():
    """创建旧格式(起承转合)的测试数据"""
    return {
        "name": "测试重大事件-旧格式",
        "chapter_range": "1-10",
        "composition": {
            "起": [
                {
                    "name": "起-事件1",
                    "description": "起始阶段",
                    "main_goal": "建立冲突"
                }
            ],
            "承": [
                {
                    "name": "承-事件1",
                    "description": "发展阶段",
                    "main_goal": "深化冲突"
                }
            ],
            "转": [
                {
                    "name": "转-事件1",
                    "description": "转折阶段",
                    "main_goal": "高潮转折"
                }
            ],
            "合": [
                {
                    "name": "合-事件1",
                    "description": "结局阶段",
                    "main_goal": "收束剧情"
                }
            ]
        }
    }


def create_test_major_event_new_format():
    """创建新格式(起因发展高潮结局)的测试数据"""
    return {
        "name": "测试重大事件-新格式",
        "chapter_range": "11-20",
        "composition": {
            "起因": [
                {
                    "name": "起因-事件1",
                    "description": "起始阶段",
                    "main_goal": "建立冲突"
                }
            ],
            "发展": [
                {
                    "name": "发展-事件1",
                    "description": "发展阶段",
                    "main_goal": "深化冲突"
                },
                {
                    "name": "发展-事件2",
                    "description": "发展阶段2",
                    "main_goal": "继续发展"
                }
            ],
            "高潮": [
                {
                    "name": "高潮-事件1",
                    "description": "高潮阶段",
                    "main_goal": "爆发冲突"
                }
            ],
            "结局": [
                {
                    "name": "结局-事件1",
                    "description": "结局阶段",
                    "main_goal": "解决冲突"
                }
            ]
        }
    }


def test_event_extractor():
    """测试 EventExtractor 的中级事件提取"""
    print("\n" + "="*80)
    print("测试 EventExtractor.extract_medium_events()")
    print("="*80)
    
    extractor = get_event_extractor(logger)
    
    # 测试旧格式
    print("\n[测试1] 旧格式 (起承转合)")
    old_event = create_test_major_event_old_format()
    old_medium_events = extractor.extract_medium_events(old_event)
    print(f"[OK] 提取到 {len(old_medium_events)} 个中级事件")
    for event in old_medium_events:
        print(f"  - [{event['stage']}] {event['name']}")
    
    # 测试新格式
    print("\n[测试2] 新格式 (起因发展高潮结局)")
    new_event = create_test_major_event_new_format()
    new_medium_events = extractor.extract_medium_events(new_event)
    print(f"[OK] 提取到 {len(new_medium_events)} 个中级事件")
    for event in new_medium_events:
        print(f"  - [{event['stage']}] {event['name']}")
    
    return len(old_medium_events) == 4 and len(new_medium_events) == 5


def test_long_series_strategy():
    """测试 LongSeriesStrategy 的中级事件提取"""
    print("\n" + "="*80)
    print("测试 LongSeriesStrategy._extract_medium_events()")
    print("="*80)
    
    from src.managers.VideoAdapterManager import LongSeriesStrategy
    strategy = LongSeriesStrategy()
    
    # 测试旧格式
    print("\n[测试1] 旧格式 (起承转合)")
    old_event = create_test_major_event_old_format()
    old_medium_events = strategy._extract_medium_events(old_event)
    print(f"[OK] 提取到 {len(old_medium_events)} 个中级事件")
    for event in old_medium_events:
        print(f"  - [{event['stage']}] {event['name']}")
    
    # 测试新格式
    print("\n[测试2] 新格式 (起因发展高潮结局)")
    new_event = create_test_major_event_new_format()
    new_medium_events = strategy._extract_medium_events(new_event)
    print(f"[OK] 提取到 {len(new_medium_events)} 个中级事件")
    for event in new_medium_events:
        print(f"  - [{event['stage']}] {event['name']}")
    
    return len(old_medium_events) == 4 and len(new_medium_events) == 5


def test_video_adapter_manager():
    """测试 VideoAdapterManager 的完整流程"""
    print("\n" + "="*80)
    print("测试 VideoAdapterManager.convert_to_video() - long_series 模式")
    print("="*80)
    
    # 创建测试数据
    test_novel_data = {
        "novel_title": "测试小说",
        "stage_writing_plans": {
            "opening_stage": {
                "stage_writing_plan": {
                    "event_system": {
                        "major_events": [
                            create_test_major_event_old_format(),
                            create_test_major_event_new_format()
                        ]
                    }
                }
            }
        }
    }
    
    # 创建适配器
    class MockGenerator:
        def __init__(self, novel_data):
            self.novel_data = novel_data
            self.api_client = None
    
    mock_generator = MockGenerator(test_novel_data)
    adapter = VideoAdapterManager(mock_generator)
    
    # 转换为长剧集
    print("\n[转换] 开始转换...")
    result = adapter.convert_to_video(
        novel_data=test_novel_data,
        video_type="long_series"
    )
    
    units = result.get("units", [])
    print(f"\n[OK] 转换完成！生成了 {len(units)} 个分集")
    
    for unit in units:
        print(f"\n  [分集 {unit['unit_number']}]")
        print(f"     - 重大事件: {unit.get('major_event_name')}")
        print(f"     - 中级事件: {unit.get('medium_event_name')}")
        print(f"     - 阶段: {unit.get('stage')}")
        print(f"     - 预计时长: {unit.get('estimated_duration_minutes')} 分钟")
    
    return len(units) == 9  # 4个旧格式 + 5个新格式 = 9个中级事件


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("开始测试中级事件提取修复")
    print("="*80)
    
    results = {}
    
    # 测试1: EventExtractor
    results["EventExtractor"] = test_event_extractor()
    
    # 测试2: LongSeriesStrategy
    results["LongSeriesStrategy"] = test_long_series_strategy()
    
    # 测试3: VideoAdapterManager
    results["VideoAdapterManager"] = test_video_adapter_manager()
    
    # 总结
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS] 通过" if passed else "[FAIL] 失败"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] 所有测试通过！中级事件提取修复成功！")
    else:
        print("[WARNING] 部分测试失败，请检查修复代码")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())