"""测试 MediumEventSceneManager 和场景共享机制

运行测试：
    python -m tests.test_medium_event_scene_manager
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.MediumEventSceneManager import MediumEventSceneManager, parse_chapter_range


def test_parse_chapter_range():
    """测试章节范围解析"""
    print("\n=== 测试 parse_chapter_range ===")

    test_cases = [
        ("1-1", (1, 1)),
        ("3-5", (3, 5)),
        ("10", (10, 10)),
        ("2-10", (2, 10)),
    ]

    for input_str, expected in test_cases:
        result = parse_chapter_range(input_str)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} parse_chapter_range('{input_str}') = {result}, 期望 {expected}")

    print("=== 测试完成 ===\n")


def test_medium_event_manager():
    """测试 MediumEventSceneManager 基本功能"""
    print("\n=== 测试 MediumEventSceneManager ===")

    # 创建管理器
    manager = MediumEventSceneManager()
    print("[OK] MediumEventSceneManager 初始化成功")

    # 测试 get_event_id
    medium_event = {
        "name": "天命之子的逆袭：从退婚到跪舔",
        "chapter_range": "3-4"
    }
    stage_name = "opening_stage"

    event_id = manager.get_event_id(medium_event, stage_name)
    print(f"[OK] get_event_id: {event_id}")

    # 测试缓存文件路径
    cache_path = manager.get_cache_file_path(event_id)
    print(f"[OK] 缓存文件路径: {cache_path}")

    # 测试保存和加载
    event_data = {
        "medium_event_id": event_id,
        "event_name": medium_event["name"],
        "chapter_range": "3-4",
        "total_chapters": 2,
        "status": "completed",
        "scenes": {
            "3": [
                {"position": "opening", "name": "苏清月登门", "purpose": "引入冲突"},
                {"position": "climax", "name": "老祖宗显灵", "purpose": "镇压全场"}
            ],
            "4": [
                {"position": "opening", "name": "事件余波", "purpose": "后续发展"},
                {"position": "development1", "name": "资源盘点", "purpose": "盘点收获"}
            ]
        },
        "global_scene_summary": "苏清月上门退婚被老祖宗镇压，赔偿灵石后逃离"
    }

    manager.save_event_scenes(event_id, event_data)
    print("[OK] 保存事件数据成功")

    # 测试加载
    loaded_scenes = manager.get_scenes_for_chapter(event_id, 3)
    print(f"[OK] 获取第3章场景: {len(loaded_scenes)}个场景")

    # 测试继承数据
    cached_data = manager.get_cached_scenes(event_id, 4)
    if cached_data:
        print(f"[OK] 获取继承数据: 之前章节={cached_data['previous_chapters']}")
    else:
        print("[FAIL] 获取继承数据失败")

    # 测试完成状态
    is_completed = manager.is_event_completed(event_id)
    print(f"[OK] 事件完成状态: {is_completed}")

    # 清理测试数据
    manager.clear_cache(event_id)
    print("[OK] 清理缓存成功")

    print("=== 测试完成 ===\n")


def test_scenario_division():
    """测试场景分派逻辑"""
    print("\n=== 测试场景分派逻辑 ===")

    # 模拟不同跨度的场景
    scenarios = [
        ("1-1", 1, "单章生成"),
        ("2-3", 2, "一次性生成+分配"),
        ("3-5", 3, "逐章生成+继承"),
        ("1-4", 4, "逐章生成+继承"),
    ]

    for chapter_range, expected_strategy_name, strategy_desc in scenarios:
        start, end = parse_chapter_range(chapter_range)
        span = end - start + 1

        if span == 1:
            strategy = "单章生成"
        elif span <= 3:
            strategy = "一次性生成+分配"
        else:
            strategy = "逐章生成+继承"

        status = "[OK]" if strategy == expected_strategy_name else "[FAIL]"
        print(f"  {status} 章节{chapter_range} (跨度{span}): {strategy}")

    print("=== 测试完成 ===\n")


def test_integration():
    """集成测试 - 模拟完整的场景共享流程"""
    print("\n=== 集成测试：完整场景共享流程 ===")

    manager = MediumEventSceneManager()

    # 模拟场景数据
    event_id = "test_event_退婚逆袭"
    medium_event = {
        "name": "退婚逆袭",
        "chapter_range": "3-4",
        "main_goal": "退婚冲突与反转"
    }

    # 第3章生成场景
    print("\n[第3章] 生成场景...")
    chapter3_scenes = [
        {"position": "opening", "name": "苏清月登门", "purpose": "引入冲突"},
        {"position": "climax", "name": "老祖宗显灵", "purpose": "镇压全场"}
    ]

    manager.save_event_scenes(event_id, {
        "medium_event_id": event_id,
        "event_name": medium_event["name"],
        "chapter_range": medium_event["chapter_range"],
        "total_chapters": 2,
        "status": "in_progress",
        "scenes": {
            "3": chapter3_scenes
        },
        "global_scene_summary": "第3章：苏清月登门被镇压"
    })
    print(f"[OK] 第3章保存了 {len(chapter3_scenes)} 个场景")

    # 第4章生成时，获取第3章的场景
    print("\n[第4章] 获取继承场景...")
    cached_data = manager.get_cached_scenes(event_id, 4)
    if cached_data:
        print(f"[OK] 获取到第{cached_data['previous_chapters']}章的场景")
        print(f"  场景: {[s['name'] for s in cached_data['all_previous_scenes']]}")
    else:
        print("[FAIL] 未获取到继承场景")

    # 第4章生成场景后，更新缓存
    print("\n[第4章] 生成并保存场景...")
    chapter4_scenes = [
        {"position": "opening", "name": "事件余波", "purpose": "后续发展"},
        {"position": "climax", "name": "资源盘点", "purpose": "盘点收获"}
    ]

    manager.save_event_scenes(event_id, {
        "medium_event_id": event_id,
        "event_name": medium_event["name"],
        "chapter_range": medium_event["chapter_range"],
        "total_chapters": 2,
        "status": "completed",
        "scenes": {
            "3": chapter3_scenes,
            "4": chapter4_scenes
        },
        "global_scene_summary": "苏清月上门退婚被老祖宗镇压，赔偿灵石后逃离"
    })
    print(f"[OK] 第4章保存了 {len(chapter4_scenes)} 个场景")

    # 验证两章的场景都可以获取
    ch3_retrieved = manager.get_scenes_for_chapter(event_id, 3)
    ch4_retrieved = manager.get_scenes_for_chapter(event_id, 4)
    print(f"\n[OK] 验证: 第3章 {len(ch3_retrieved)}个场景, 第4章 {len(ch4_retrieved)}个场景")

    # 清理
    manager.clear_cache(event_id)
    print("\n[OK] 清理测试数据")

    print("=== 集成测试完成 ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("MediumEventSceneManager 功能测试")
    print("=" * 60)

    try:
        test_parse_chapter_range()
        test_medium_event_manager()
        test_scenario_division()
        test_integration()

        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
