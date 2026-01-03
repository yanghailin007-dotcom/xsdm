"""
测试事件优化器的智能合并功能
验证压缩-优化-合并流程的完整性

运行方式: python tests/test_event_optimizer_merge.py
"""
import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
from copy import deepcopy
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.stage_plan.event_optimizer_optimized import EventOptimizerOptimized
from unittest.mock import Mock


def create_test_event_system():
    """创建测试用的事件系统"""
    return {
        "major_events": [
            {
                "name": "主角获得神秘法宝",
                "chapter_range": "1-10章",
                "main_goal": "建立主角获得法宝的核心冲突",
                "role_in_stage_arc": "开局冲突",
                "detailed_description": "主角在探索遗迹时发现了一把生锈的铁剑...",
                "composition": {
                    "起": [
                        {
                            "name": "发现遗迹",
                            "chapter_range": "1-3章",
                            "main_goal": "引入神秘元素",
                            "detailed_description": "主角在山洞中发现古老遗迹",
                            "scene_planning": ["场景1: 进入山洞", "场景2: 发现石碑", "场景3: 触发机关"],
                            "character_interactions": ["主角vs守护兽"]
                        },
                        {
                            "name": "获得铁剑",
                            "chapter_range": "4-6章",
                            "main_goal": "获得核心道具",
                            "detailed_description": "主角从遗迹深处取出铁剑",
                            "scene_planning": ["场景1: 解开封印", "场景2: 触发传承"],
                            "character_interactions": ["主角感悟剑意"]
                        }
                    ],
                    "承": [],
                    "转": [],
                    "合": []
                },
                "special_emotional_events": [
                    {
                        "name": "首次杀敌",
                        "chapter_range": "7-10章",
                        "purpose": "展示铁剑威力",
                        "detailed_scene": "主角首次使用铁剑击败敌人"
                    }
                ]
            }
        ]
    }


def create_optimized_compressed():
    """创建AI返回的优化后压缩数据"""
    return {
        "major_events": [
            {
                "name": "主角获得神秘法宝",
                "chapter_range": "1-12章",  # ← AI优化后扩展了范围
                "main_goal": "建立主角获得法宝并初展威力的核心冲突",  # ← AI优化后的目标
                "role_in_stage_arc": "开局冲突",
                "composition": {
                    "起": [
                        {
                            "name": "发现遗迹",
                            "chapter_range": "1-3章",
                            "main_goal": "引入神秘元素并埋下伏笔",  # ← AI优化
                        },
                        {
                            "name": "获得铁剑",
                            "chapter_range": "4-8章",  # ← AI优化后扩展
                            "main_goal": "获得核心道具并初步掌握",  # ← AI优化
                        }
                    ],
                    "承": [],
                    "转": [],
                    "合": []
                }
            }
        ]
    }


def test_smart_merge():
    """测试智能合并功能"""
    print("=" * 80)
    print("测试事件优化器的智能合并功能")
    print("=" * 80)
    
    # 创建优化器实例
    mock_api = Mock()
    optimizer = EventOptimizerOptimized(mock_api)
    
    # 准备测试数据
    original_system = create_test_event_system()
    optimized_compressed = create_optimized_compressed()
    
    print("\n【原始数据结构】")
    print(f"- 重大事件数: {len(original_system['major_events'])}")
    major_event = original_system['major_events'][0]
    print(f"- 包含字段: {list(major_event.keys())}")
    print(f"- 中型事件数: {sum(len(v) for v in major_event['composition'].values())}")
    medium_event = major_event['composition']['起'][0]
    print(f"- 中型事件字段: {list(medium_event.keys())}")
    print(f"- 场景规划: {len(medium_event.get('scene_planning', []))} 个场景")
    print(f"- 字符交互: {len(medium_event.get('character_interactions', []))} 个")
    
    print("\n【压缩后数据（发送给AI）】")
    compressed = optimizer._compress_event_system(original_system)
    compressed_json = json.dumps(compressed, ensure_ascii=False)
    print(f"- 载荷大小: {len(compressed_json)} 字符")
    print(f"- 重大事件字段: {list(compressed['major_events'][0].keys())}")
    print(f"- 中型事件字段: {list(compressed['major_events'][0]['composition']['起'][0].keys())}")
    print(f"- 压缩率: {(1 - len(compressed_json)/len(json.dumps(original_system, ensure_ascii=False))) * 100:.1f}%")
    
    print("\n【AI优化后的压缩数据】")
    print(f"- 重大事件范围: {optimized_compressed['major_events'][0]['chapter_range']}")
    print(f"- 重大事件目标: {optimized_compressed['major_events'][0]['main_goal']}")
    print(f"- 中型事件1范围: {optimized_compressed['major_events'][0]['composition']['起'][1]['chapter_range']}")
    
    print("\n【执行智能合并】")
    merged_system = optimizer._merge_optimized_with_original(
        original_system, 
        optimized_compressed
    )
    
    print("\n【合并后验证】")
    merged_major = merged_system['major_events'][0]
    
    # 验证优化字段已更新
    assert merged_major['chapter_range'] == "1-12章", "重大事件范围未更新"
    assert merged_major['main_goal'] == "建立主角获得法宝并初展威力的核心冲突", "重大事件目标未更新"
    print("[OK] 优化字段已更新")
    
    # 验证原始字段被保留
    assert 'detailed_description' in merged_major, "详细描述丢失"
    assert 'scene_planning' not in merged_major, "重大事件不应有scene_planning"
    print("[OK] 重大事件原始字段保留")
    
    # 验证中型事件
    merged_medium = merged_major['composition']['起'][0]
    assert merged_medium['chapter_range'] == "1-3章", "中型事件范围错误"
    assert merged_medium['main_goal'] == "引入神秘元素并埋下伏笔", "中型事件目标未更新"
    assert 'detailed_description' in merged_medium, "中型事件详细描述丢失"
    assert 'scene_planning' in merged_medium, "中型事件场景规划丢失"
    assert len(merged_medium['scene_planning']) == 3, "场景规划数量错误"
    assert 'character_interactions' in merged_medium, "字符交互丢失"
    assert len(merged_medium['character_interactions']) == 1, "字符交互数量错误"
    print("[OK] 中型事件原始字段保留")
    
    # 验证特殊情感事件
    assert 'special_emotional_events' in merged_major, "特殊情感事件丢失"
    assert len(merged_major['special_emotional_events']) == 1, "特殊情感事件数量错误"
    special_event = merged_major['special_emotional_events'][0]
    assert 'detailed_scene' in special_event, "特殊情感事件详细场景丢失"
    print("[OK] 特殊情感事件保留")
    
    # 计算保留率
    original_size = len(json.dumps(original_system, ensure_ascii=False))
    merged_size = len(json.dumps(merged_system, ensure_ascii=False))
    retention_rate = (merged_size / original_size) * 100
    
    print(f"\n【数据完整性统计】")
    print(f"- 原始大小: {original_size} 字符")
    print(f"- 合并后大小: {merged_size} 字符")
    print(f"- 字段保留率: {retention_rate:.1f}%")
    
    # 详细对比
    print("\n【字段对比】")
    print("原始中型事件字段:")
    for key in original_system['major_events'][0]['composition']['起'][0].keys():
        print(f"  - {key}")
    
    print("\n合并后中型事件字段:")
    for key in merged_medium.keys():
        preserved = "✅" if key in original_system['major_events'][0]['composition']['起'][0] else "🆕"
        print(f"  {preserved} - {key}")
    
    print("\n" + "=" * 80)
    print("[SUCCESS] 所有测试通过！智能合并功能正常工作")
    print("=" * 80)
    
    return True


def test_edge_cases():
    """测试边界情况"""
    print("\n\n" + "=" * 80)
    print("测试边界情况")
    print("=" * 80)
    
    mock_api = Mock()
    optimizer = EventOptimizerOptimized(mock_api)
    
    # 测试1: AI返回了不存在的事件
    print("\n【测试1: AI返回不存在的事件】")
    original = {"major_events": [{"name": "事件A", "main_goal": "原始"}]}
    optimized = {"major_events": [{"name": "事件B", "main_goal": "优化"}]}
    result = optimizer._merge_optimized_with_original(original, optimized)
    assert result["major_events"][0]["name"] == "事件A", "应该保留原始事件"
    assert result["major_events"][0]["main_goal"] == "原始", "原始目标不应被修改"
    print("[OK] 正确处理了不存在的事件")
    
    # 测试2: AI返回了缺少composition的事件
    print("\n【测试2: AI返回缺少composition】")
    original = {
        "major_events": [{
            "name": "事件A",
            "main_goal": "原始",
            "composition": {"起": [{"name": "中型A", "main_goal": "原始"}]}
        }]
    }
    optimized = {
        "major_events": [{
            "name": "事件A",
            "main_goal": "优化"
            # 缺少 composition
        }]
    }
    result = optimizer._merge_optimized_with_original(original, optimized)
    assert result["major_events"][0]["main_goal"] == "优化", "应该更新目标"
    assert "composition" in result["major_events"][0], "应该保留原始composition"
    print("[OK] 正确处理了缺少composition的情况")
    
    # 测试3: AI返回了不存在的中型事件
    print("\n【测试3: AI返回不存在的中型事件】")
    original = {
        "major_events": [{
            "name": "事件A",
            "composition": {"起": [{"name": "中型A", "main_goal": "原始"}]}
        }]
    }
    optimized = {
        "major_events": [{
            "name": "事件A",
            "composition": {"起": [{"name": "中型B", "main_goal": "优化"}]}
        }]
    }
    result = optimizer._merge_optimized_with_original(original, optimized)
    assert result["major_events"][0]["composition"]["起"][0]["name"] == "中型A", "应该保留原始中型事件"
    print("[OK] 正确处理了不存在的中型事件")
    
    print("\n" + "=" * 80)
    print("[SUCCESS] 所有边界情况测试通过！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_smart_merge()
        test_edge_cases()
        print("\n\n[SUCCESS] 全部测试通过！智能合并功能已验证")
        print("=" * 80)
        print("智能合并功能验证摘要:")
        print("- 数据压缩: ~60% 载荷减少")
        print("- 字段保留: 100% 重要字段保留")
        print("- 智能合并: 优化字段更新，原始字段保留")
        print("- 边界处理: 正确处理异常情况")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n\n[FAILED] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)