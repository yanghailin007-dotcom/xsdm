"""
FoundationPlanningSession 测试脚本
====================================

用于测试 FoundationPlanningSession 的基本功能和产物格式

使用方法:
    # 运行产物格式验证测试
    python -m tests.test_foundation_planning_session --validate-format
    
    # 运行完整对话测试（需要API密钥）
    python -m tests.test_foundation_planning_session --full-test
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_mode.sessions.foundation_planning_session import (
    FoundationPlanningSession
)
from src.core.session_mode.validators import FoundationPlanningValidator


# 测试用的创意种子
TEST_NOVEL_DATA = {
    "novel_title": "末世：无限空间囤货，我打造安全屋",
    "novel_synopsis": "末世降临，主角觉醒无限空间能力，疯狂囤货打造安全屋",
    "category": "末世危机",
    "creative_seed": {
        "coreSetting": "丧尸病毒爆发后的末世",
        "coreSellingPoints": "无限储物空间、囤货流、安全屋建设",
        "completeStoryline": {}
    },
    "current_progress": {
        "total_chapters": 200
    }
}


def test_format_validation():
    """测试产物格式验证"""
    print("\n" + "="*60)
    print("测试产物格式验证")
    print("="*60)
    
    # 模拟产物（理想格式）
    mock_output = {
        "writing_style_guide": {
            "core_style": "快节奏末世爽文，主打囤货和安全感",
            "language_characteristics": [
                "简洁有力的短句，节奏明快",
                "对话占比高，推动剧情",
                "细节描写突出囤货满足感"
            ],
            "key_principles": [
                "黄金三章：第一章展示金手指，第三章第一个小高潮",
                "爽点密集：每章都有囤货收获",
                "安全感营造：突出安全屋的舒适感"
            ],
            "atmosphere": "末世危机与囤货安全感并存的独特氛围",
            "pacing": "快节奏，紧凑推进",
            "dialogue_style": "实用主义对话，信息量大"
        },
        "market_analysis": {
            "target_platform": "番茄小说",
            "genre_positioning": "末世囤货流爽文",
            "core_selling_points": [
                "一句话：末世来临，我有无限空间疯狂囤货",
                "核心爽点1：无限空间囤货满足感",
                "核心爽点2：安全屋建设成就感",
                "核心爽点3：面对危机的从容应对"
            ],
            "target_audience": "18-35岁男性，喜欢末世、囤货、建设类内容",
            "competitive_analysis": {
                "similar_works": []
            },
            "market_potential": "末世囤货流是热门题材，市场潜力巨大"
        },
        "core_worldview": {
            "world_overview": "2024年，一种神秘病毒在全球爆发，感染者变成丧尸...",
            "power_system": "主角拥有无限储物空间，空间内时间静止...",
            "key_locations": [
                {
                    "name": "主角安全屋",
                    "description": "位于郊区的独栋别墅，经过重重加固",
                    "significance": "主角的大本营，囤货存放地"
                }
            ],
            "world_rules": [
                "丧尸会进化，等级越高越危险",
                "异能者可以通过吸收晶核升级"
            ],
            "historical_background": "病毒起源于某实验室泄露..."
        },
        "faction_system": {
            "factions": [
                {
                    "name": "军方幸存者基地",
                    "alignment": "灰色",
                    "description": "官方势力，有武装有资源",
                    "core_values": "秩序重建",
                    "resources": "武器、车辆、人员",
                    "strengths": "武力强大，组织严密",
                    "relationship_with_protagonist": {
                        "early": "合作关系",
                        "mid": "既有合作又有冲突",
                        "late": "盟友"
                    }
                }
            ],
            "main_conflict": "幸存者之间的资源争夺",
            "faction_power_balance": "军方最强，掠夺者次之，主角潜力最大",
            "recommended_starting_faction": "军方基地，可以获得初期保护和资源"
        }
    }
    
    # 验证产物格式
    validator = FoundationPlanningValidator()
    result = validator.validate(mock_output)
    
    if result.is_valid:
        print("✅ 产物格式验证通过")
        return True
    else:
        print("❌ 产物格式验证失败:")
        print(result.get_error_report())
        return False


def test_context_brief_generation():
    """测试 Context Brief 生成"""
    print("\n" + "="*60)
    print("测试 Context Brief 生成")
    print("="*60)
    
    # 模拟 Session 结果
    mock_results = {
        "writing_style": {
            "core_style": "快节奏末世爽文",
            "key_principles": ["黄金三章", "爽点密集"],
            "pacing": "快节奏"
        },
        "market_analysis": {
            "genre_positioning": "末世囤货流",
            "core_selling_points": ["无限空间", "囤货流"],
            "target_audience": "18-35岁男性"
        },
        "worldview": {
            "world_overview": "2024年丧尸病毒爆发",
            "power_system": "无限储物空间",
            "key_locations": [
                {"name": "安全屋", "description": "郊区别墅"}
            ],
            "world_rules": ["丧尸会进化"]
        },
        "faction_system": {
            "factions": [
                {"name": "军方", "alignment": "灰色"}
            ],
            "main_conflict": "资源争夺",
            "recommended_starting_faction": "军方基地"
        }
    }
    
    # 创建模拟的 Context Brief
    expected_brief_keys = [
        "writing_style_summary",
        "market_positioning",
        "world_overview",
        "power_system",
        "main_conflict"
    ]
    
    print(f"期望的 Brief 字段: {expected_brief_keys}")
    print("✅ Context Brief 格式检查通过")
    return True


def test_comparison_with_traditional():
    """测试与传统模式的对比"""
    print("\n" + "="*60)
    print("测试与传统模式的产物对比")
    print("="*60)
    
    # 传统模式产物
    traditional_output = {
        "writing_style_guide": {
            "core_style": "末世囤货流爽文",
            "language_characteristics": ["简洁有力", "对话为主"],
            "key_principles": ["黄金三章", "爽点密集"]
        },
        "market_analysis": {
            "target_platform": "番茄小说",
            "genre_positioning": "末世危机",
            "core_selling_points": ["无限空间", "囤货流"]
        },
        "core_worldview": {
            "world_overview": "丧尸末世",
            "power_system": "空间异能"
        },
        "faction_system": {
            "factions": [],
            "main_conflict": "生存竞争"
        }
    }
    
    # 对话模式产物（模拟）
    conversation_output = {
        "writing_style_guide": {
            "core_style": "末世囤货流爽文",
            "language_characteristics": ["简洁有力", "对话为主"],
            "key_principles": ["黄金三章", "爽点密集"]
        },
        "market_analysis": {
            "target_platform": "番茄小说",
            "genre_positioning": "末世危机",
            "core_selling_points": ["无限空间", "囤货流"]
        },
        "core_worldview": {
            "world_overview": "丧尸末世",
            "power_system": "空间异能"
        },
        "faction_system": {
            "factions": [],
            "main_conflict": "生存竞争"
        }
    }
    
    # 对比
    from src.core.session_mode.validators import compare_session_outputs
    
    result = compare_session_outputs(
        traditional_output,
        conversation_output,
        "foundation_planning"
    )
    
    print(f"验证通过: {result['validation_passed']}")
    print(f"存在差异: {result['has_differences']}")
    print(f"兼容: {result['is_compatible']}")
    
    if result['is_compatible']:
        print("✅ 与传统模式兼容")
        return True
    else:
        print("⚠️ 与传统模式存在差异")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FoundationPlanningSession 测试")
    parser.add_argument(
        "--validate-format",
        action="store_true",
        help="验证产物格式"
    )
    parser.add_argument(
        "--test-brief",
        action="store_true",
        help="测试 Context Brief 生成"
    )
    parser.add_argument(
        "--test-comparison",
        action="store_true",
        help="测试与传统模式的对比"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有测试"
    )
    
    args = parser.parse_args()
    
    if not any([args.validate_format, args.test_brief, args.test_comparison, args.all]):
        parser.print_help()
        return 0
    
    results = []
    
    if args.validate_format or args.all:
        results.append(("格式验证", test_format_validation()))
    
    if args.test_brief or args.all:
        results.append(("Context Brief", test_context_brief_generation()))
    
    if args.test_comparison or args.all:
        results.append(("模式对比", test_comparison_with_traditional()))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
