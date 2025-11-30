"""测试分层上下文管理器"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.LayeredContextManager import LayeredContextManager
from src.utils.logger import get_logger

def print_safe(text):
    """安全打印，避免编码错误"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 移除所有非ASCII字符的emoji
        clean_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(clean_text)

def test_layered_context():
    """测试分层上下文管理器"""
    logger = get_logger("test_layered_context")

    print("=" * 60)
    print("测试分层上下文管理器 (优化版)")
    print("=" * 60)

    # 初始化管理器
    manager = LayeredContextManager()

    # 创建测试数据
    test_context = {
        "title": "测试小说标题",
        "characters": [
            {"name": "主角A", "description": "详细的角色描述A" * 20},
            {"name": "角色B", "description": "详细的角色描述B" * 20},
            {"name": "角色C", "description": "详细的角色描述C" * 20},
            {"name": "角色D", "description": "详细的角色描述D" * 20},
            {"name": "角色E", "description": "详细的角色描述E" * 20},
            {"name": "角色F", "description": "详细的角色描述F" * 20}
        ],
        "events": [
            {"chapter": 1, "name": "事件1", "description": "事件描述" * 10},
            {"chapter": 5, "name": "事件2", "description": "事件描述" * 10},
            {"chapter": 15, "name": "事件3", "description": "事件描述" * 10},
            {"chapter": 25, "name": "事件4", "description": "事件描述" * 10}
        ],
        "long_description": "这是一个很长的描述" * 100,
        "summary": "这是一个很长的摘要" * 50
    }

    print("\n[1] 原始上下文大小:")
    original_size = manager.get_context_size_info(test_context)
    print(f"  字符数: {original_size['character_count']}")
    print(f"  估算tokens: {original_size['estimated_tokens']}")
    print(f"  是否较大: {original_size['is_large']}")
    print(f"  压缩建议: {original_size.get('compression_level', '未知')}")

    # 测试不同章节的上下文压缩（新的5层架构）
    test_scenarios = [
        (1, 1, "immediate - 同章节"),
        (2, 1, "immediate - 1章前"),
        (3, 1, "close - 2章前"),
        (6, 1, "close - 5章前"),
        (7, 1, "medium - 6章前"),
        (11, 1, "medium - 10章前"),
        (12, 1, "far - 11章前"),
        (21, 1, "far - 20章前"),
        (22, 1, "distant - 21章前"),
        (50, 1, "distant - 49章前")
    ]

    print("\n[2] 测试不同距离的上下文压缩 (5层架构):")
    for current_chapter, target_chapter, description in test_scenarios:
        layer = manager.get_context_layer(current_chapter, target_chapter)

        # 测试通用上下文压缩
        compressed_general = manager.compress_context(
            test_context, current_chapter, target_chapter, "general"
        )

        general_size = manager.get_context_size_info(compressed_general)
        compression_ratio = (1 - general_size['estimated_tokens'] / original_size['estimated_tokens']) * 100

        print(f"  {description}:")
        print(f"    层级: {layer}")
        print(f"    压缩后tokens: {general_size['estimated_tokens']} (压缩率: {compression_ratio:.1f}%)")
        print()

    # 测试不同类型的上下文压缩
    print("[3] 测试不同类型的上下文压缩 (第30章视角):")

    # 事件上下文
    event_context = {
        "major_events": [
            {"chapter": 1, "name": "重大事件1", "type": "plot", "description": "详细描述" * 20},
            {"chapter": 10, "name": "重大事件2", "type": "battle", "description": "详细描述" * 20},
            {"chapter": 20, "name": "重大事件3", "type": "romance", "description": "详细描述" * 20}
        ],
        "active_events": [
            {"chapter": 25, "name": "活跃事件1", "type": "daily"},
            {"chapter": 28, "name": "活跃事件2", "type": "plot"},
            {"chapter": 29, "name": "活跃事件3", "type": "emotional"}
        ],
        "summary": "这是事件摘要" * 50
    }

    # 角色上下文
    character_context = {
        "main_characters": {
            "主角": {
                "name": "测试主角",
                "role": "protagonist",
                "description": "主角详细描述" * 30,
                "current_status": "主角当前状态" * 10,
                "abilities": ["能力1", "能力2", "能力3"] * 5
            },
            "配角": {
                "name": "测试配角",
                "role": "supporting",
                "description": "配角详细描述" * 20
            }
        },
        "key_relationships": {
            "主角-配角": ["关系描述1", "关系描述2", "关系描述3"] * 3,
            "主角-反派": ["敌对关系描述"] * 5
        },
        "character_development_summary": "角色发展摘要" * 40
    }

    # 情节上下文
    plot_context = {
        "plot_progression": "故事处于发展阶段，主角正在历练成长中" * 20,
        "key_plot_points": [
            {"chapter": 5, "point": "关键情节1"},
            {"chapter": 10, "point": "关键情节2"},
            {"chapter": 20, "point": "关键情节3"}
        ] * 3,
        "current_conflicts": [
            "主角与反派的冲突",
            "内心的矛盾与成长",
            "势力之间的斗争"
        ]
    }

    contexts_to_test = [
        ("事件上下文", event_context, "event"),
        ("角色上下文", character_context, "character"),
        ("情节上下文", plot_context, "plot"),
        ("通用上下文", test_context, "general")
    ]

    for context_name, context_data, context_type in contexts_to_test:
        original = manager.get_context_size_info(context_data)
        compressed = manager.compress_context(context_data, 30, 1, context_type)
        compressed_size = manager.get_context_size_info(compressed)
        compression_ratio = (1 - compressed_size['estimated_tokens'] / original['estimated_tokens']) * 100

        print(f"  {context_name}:")
        print(f"    原始tokens: {original['estimated_tokens']}")
        print(f"    压缩后tokens: {compressed_size['estimated_tokens']}")
        print(f"    压缩率: {compression_ratio:.1f}%")
        print()

    # 测试缓存功能
    print("[4] 测试缓存功能:")
    manager.reset_stats()

    # 第一次压缩
    for i in range(3):
        manager.compress_context(test_context, 30, 1, "general")

    # 第二次压缩（应该使用缓存）
    for i in range(3):
        manager.compress_context(test_context, 30, 1, "general")

    stats = manager.get_compression_stats()
    print(f"  总压缩次数: {stats['total_compressions']}")
    print(f"  缓存命中次数: {stats['cache_hits']}")
    print(f"  缓存命中率: {stats['cache_hit_rate']}")
    print(f"  整体压缩率: {stats['overall_compression_ratio']}")

    # 测试token估算准确性
    print("\n[5] 测试token估算准确性:")
    test_strings = [
        ("纯中文字符串测试" * 10, "中文字符串"),
        ("Pure English string test" * 10, "英文字符串"),
        ("混合字符串test测试mixed" * 10, "混合字符串"),
        ({"key": "value", "nested": {"data": "test"}}, "字典对象"),
        (["item1", "item2", "item3"] * 10, "列表对象")
    ]

    for test_data, description in test_strings:
        tokens = manager.estimate_token_count(test_data)
        print(f"  {description}: {tokens} tokens")

    # 测试极端场景
    print("\n[6] 测试极端场景:")

    # 空数据
    empty_context = {}
    empty_compressed = manager.compress_context(empty_context, 30, 1, "general")
    print(f"  空数据压缩: {manager.get_context_size_info(empty_compressed)['estimated_tokens']} tokens")

    # 超大数据
    huge_context = {
        "huge_text": "超长文本" * 1000,
        "huge_list": [{"item": f"数据{i}"} for i in range(100)]
    }
    huge_size = manager.get_context_size_info(huge_context)
    huge_compressed = manager.compress_context(huge_context, 100, 1, "general")
    huge_compressed_size = manager.get_context_size_info(huge_compressed)
    huge_ratio = (1 - huge_compressed_size['estimated_tokens'] / huge_size['estimated_tokens']) * 100
    print(f"  超大数据压缩: {huge_size['estimated_tokens']} -> {huge_compressed_size['estimated_tokens']} tokens (压缩率: {huge_ratio:.1f}%)")

    print("\n" + "=" * 60)
    print_safe("✅ 分层上下文管理器测试完成")
    print("=" * 60)

    # 打印最终统计
    print("\n[最终性能统计]")
    final_stats = manager.get_compression_stats()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_layered_context()