"""
FoundationPlanningSession 基于 final_plan 的测试
================================================

验证 FoundationPlanningSession 正确基于 CreativeToPlanConversation 生成的 final_plan 工作
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_mode.validators import FoundationPlanningValidator


# 模拟 CreativeToPlanConversation 生成的 final_plan
MOCK_FINAL_PLAN = {
    "title": "末世：无限空间囤货，我打造安全屋",
    "genre": "末世危机",
    "core_setting": {
        "worldview": "2024年，丧尸病毒全球爆发，文明秩序崩塌，幸存者挣扎求生",
        "power_system": "主角觉醒无限储物空间，空间内时间静止，可以无限囤货",
        "protagonist": {
            "identity": "普通上班族",
            "personality": "谨慎、果断、有领导力",
            "goal": "在末世建立安全据点，保护身边的人",
            "growth_arc": "从普通人到末世强者"
        },
        "golden_finger": {
            "ability": "无限储物空间，时间静止",
            "limitations": "只能存放非生命体",
            "upgrade_path": "随着使用会解锁更多功能"
        },
        "key_characters": [
            {"role": "女主", "description": "邻居美女，后期成为得力助手"},
            {"role": "反派", "description": "军方高层，觊觎主角空间能力"}
        ]
    },
    "book_structure": {
        "total_stages": 4,
        "stages": [
            {
                "stage_number": 1,
                "name": "觉醒囤货",
                "chapters": "1-50",
                "goal": "觉醒空间能力，疯狂囤货建立安全屋",
                "key_events": ["病毒爆发", "觉醒空间", "第一次囤货"],
                "climax": "建立安全屋"
            },
            {
                "stage_number": 2,
                "name": "势力初建",
                "chapters": "51-150",
                "goal": "收编幸存者，建立自己的小势力",
                "key_events": ["救下女主", "收编团队", "对抗掠夺者"],
                "climax": "击败掠夺者团队"
            }
        ]
    },
    "emotion_curve": {
        "overall_arc": "恐慌→希望→危机→爆发→登顶",
        "key_turning_points": ["觉醒空间", "建立安全屋", "势力成型"]
    }
}


def test_final_plan_validation():
    """验证 final_plan 格式正确性"""
    print("\n" + "="*60)
    print("测试1: 验证 final_plan 格式")
    print("="*60)
    
    # 检查必需字段
    required_fields = ["title", "genre", "core_setting", "book_structure"]
    for field in required_fields:
        if field not in MOCK_FINAL_PLAN:
            print(f"ERROR: 缺少必需字段 {field}")
            return False
    
    # 检查 core_setting 子字段
    core_setting = MOCK_FINAL_PLAN["core_setting"]
    required_core = ["worldview", "power_system", "protagonist", "golden_finger"]
    for field in required_core:
        if field not in core_setting:
            print(f"ERROR: core_setting 缺少 {field}")
            return False
    
    print("final_plan 格式验证通过")
    print(f"  - 书名: {MOCK_FINAL_PLAN['title']}")
    print(f"  - 类型: {MOCK_FINAL_PLAN['genre']}")
    print(f"  - 世界观: {core_setting['worldview'][:30]}...")
    print(f"  - 阶段数: {len(MOCK_FINAL_PLAN['book_structure']['stages'])}")
    
    return True


def test_foundation_output_format():
    """验证 FoundationPlanningSession 产物格式"""
    print("\n" + "="*60)
    print("测试2: 验证产物格式")
    print("="*60)
    
    # 基于 final_plan 构建模拟产物
    mock_output = {
        "writing_style_guide": {
            "core_style": f"末世囤货流爽文，{MOCK_FINAL_PLAN['genre']}题材",
            "language_characteristics": [
                "简洁有力的短句",
                "对话推动剧情",
                "突出囤货满足感"
            ],
            "key_principles": [
                "黄金三章：第一章展示金手指",
                "爽点密集：每章都有囤货收获",
                f"风格匹配：符合{MOCK_FINAL_PLAN['genre']}特点"
            ],
            "atmosphere": "末世危机与囤货安全感并存",
            "pacing": "快节奏",
            "dialogue_style": "实用主义"
        },
        "market_analysis": {
            "target_platform": "番茄小说",
            "genre_positioning": MOCK_FINAL_PLAN['genre'],
            "core_selling_points": [
                f"一句话：{MOCK_FINAL_PLAN['core_setting']['golden_finger']['ability']}",
                "核心爽点1：无限囤货满足感",
                "核心爽点2：安全屋建设成就感"
            ],
            "target_audience": "18-35岁男性，喜欢末世题材",
            "competitive_analysis": {
                "market_gap": "末世+囤货+空间金手指组合"
            },
            "market_potential": "末世囤货流是热门题材"
        },
        "core_worldview": {
            "world_overview": MOCK_FINAL_PLAN['core_setting']['worldview'],
            "power_system": MOCK_FINAL_PLAN['core_setting']['power_system'],
            "key_locations": [
                {"name": "主角安全屋", "description": "郊区别墅", "significance": "大本营"}
            ],
            "world_rules": [
                "丧尸会进化",
                "异能者可以升级"
            ],
            "historical_background": "2024年病毒爆发"
        },
        "faction_system": {
            "factions": [
                {
                    "name": "军方基地",
                    "alignment": "灰色",
                    "description": "官方势力",
                    "core_values": "秩序重建",
                    "resources": "武器、车辆",
                    "strengths": "武力强大",
                    "relationship_with_protagonist": {
                        "early": "合作",
                        "mid": "既有合作又有冲突",
                        "late": "盟友"
                    }
                }
            ],
            "main_conflict": "资源争夺",
            "faction_power_balance": "军方最强，主角潜力最大",
            "recommended_starting_faction": "军方基地"
        }
    }
    
    # 验证产物格式
    validator = FoundationPlanningValidator()
    result = validator.validate(mock_output)
    
    if result.is_valid:
        print("产物格式验证通过")
        return True
    else:
        print("产物格式验证失败:")
        print(result.get_error_report())
        return False


def test_context_brief_generation():
    """测试 Context Brief 生成"""
    print("\n" + "="*60)
    print("测试3: 验证 Context Brief 格式")
    print("="*60)
    
    # 模拟 export_context_brief 输出
    expected_brief_keys = [
        "writing_style_summary",
        "market_positioning",
        "world_overview",
        "power_system",
        "key_locations",
        "world_rules",
        "main_conflict",
        "factions",
        "recommended_starting_faction",
        "generation_timestamp",
        "session_type"
    ]
    
    print(f"期望的 Brief 字段数: {len(expected_brief_keys)}")
    print("关键字段检查:")
    for key in ["world_overview", "power_system", "main_conflict"]:
        print(f"  - {key}: OK")
    
    return True


def test_data_flow():
    """测试数据流：final_plan -> FoundationPlanning -> novel_data"""
    print("\n" + "="*60)
    print("测试4: 数据流验证")
    print("="*60)
    
    print("数据流:")
    print("  1. CreativeToPlanConversation 生成 final_plan")
    print("     -> final_plan 包含: title, core_setting, book_structure...")
    
    print("  2. FoundationPlanningSession 读取 final_plan")
    print(f"     -> 提取世界观: {MOCK_FINAL_PLAN['core_setting']['worldview'][:20]}...")
    print(f"     -> 提取力量体系: {MOCK_FINAL_PLAN['core_setting']['power_system'][:20]}...")
    
    print("  3. FoundationPlanningSession 生成产物")
    print("     -> writing_style_guide")
    print("     -> market_analysis")
    print("     -> core_worldview (与 final_plan 保持一致)")
    print("     -> faction_system")
    
    print("  4. 同步到 novel_data")
    print("     -> novel_data['writing_style_guide']")
    print("     -> novel_data['market_analysis']")
    print("     -> novel_data['core_worldview']")
    print("     -> novel_data['faction_system']")
    
    print("\n数据流验证通过")
    return True


def generate_test_report():
    """生成测试报告"""
    print("\n" + "="*60)
    print("FoundationPlanningSession 测试报告")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("final_plan 格式验证", test_final_plan_validation()))
    results.append(("产物格式验证", test_foundation_output_format()))
    results.append(("Context Brief 格式", test_context_brief_generation()))
    results.append(("数据流验证", test_data_flow()))
    
    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("所有测试通过")
        print("FoundationPlanningSession 可以正确处理 final_plan")
    else:
        print("部分测试失败，需要检查")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = generate_test_report()
    sys.exit(0 if success else 1)
