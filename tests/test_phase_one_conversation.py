"""
第一阶段对话化改造 - 对比测试脚本
==================================

用于对比传统模式和对话模式的产物差异

使用方法:
    # 运行单个Session对比测试
    python -m tests.test_phase_one_conversation --session foundation_planning
    
    # 运行全部对比测试
    python -m tests.test_phase_one_conversation --all
    
    # 生成参考产物（用于后续对比）
    python -m tests.test_phase_one_conversation --generate-reference
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_mode.validators import (
    ValidatorFactory,
    compare_session_outputs,
    generate_comparison_report
)


# 测试用的创意种子样本
TEST_CREATIVE_SEEDS = [
    {
        "name": "末世囤货",
        "title": "末世：无限空间囤货，我打造安全屋",
        "category": "末世危机",
        "synopsis": "末世降临，主角觉醒无限空间能力，疯狂囤货打造安全屋",
        "core_setting": {
            "world_background": "丧尸病毒爆发后的末世",
            "golden_finger": "无限储物空间",
            "core_conflict": "在资源匮乏的末世中生存并建立势力"
        }
    },
    {
        "name": "国运扮演",
        "title": "国运：扮演酒剑仙，我一人镇守国门",
        "category": "国运直播",
        "synopsis": "国运游戏降临，主角扮演酒剑仙守护国家",
        "core_setting": {
            "world_background": "国运游戏与现实融合",
            "golden_finger": "酒剑仙扮演系统",
            "core_conflict": "代表国家参与国运游戏对抗"
        }
    },
    {
        "name": "修仙模拟器",
        "title": "修仙：人生模拟器，我逆天改命",
        "category": "仙侠修真",
        "synopsis": "主角获得人生模拟器，在修仙世界逆天改命",
        "core_setting": {
            "world_background": "弱肉强食的修仙世界",
            "golden_finger": "人生模拟器",
            "core_conflict": "从凡人一步步走向长生"
        }
    }
]


class PhaseOneComparisonTest:
    """第一阶段对比测试"""
    
    def __init__(self, output_dir: str = "tests/reference_outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list = []
    
    def generate_reference_outputs(self, creative_seed: Dict) -> Dict[str, Any]:
        """
        使用传统模式生成参考产物
        
        Args:
            creative_seed: 创意种子
            
        Returns:
            各Session的产物
        """
        print(f"\n生成参考产物: {creative_seed['title']}")
        print("=" * 60)
        
        # TODO: 实际调用传统模式生成
        # 这里先用模拟数据作为示例
        
        reference_outputs = {
            "foundation_planning": {
                "writing_style_guide": {
                    "core_style": "快节奏爽文",
                    "language_characteristics": ["简洁有力", "对话为主"],
                    "key_principles": ["黄金三章", "情绪曲线", "爽点密集"]
                },
                "market_analysis": {
                    "target_platform": "番茄小说",
                    "genre_positioning": "末世生存",
                    "core_selling_points": ["无限空间", "囤货流", "安全屋"]
                },
                "core_worldview": {
                    "world_overview": "丧尸病毒爆发后的末世",
                    "power_system": "异能觉醒系统",
                    "key_locations": ["主角安全屋", "城市废墟", "幸存者营地"],
                    "world_rules": ["丧尸会进化", "异能可以升级"]
                },
                "faction_system": {
                    "factions": [
                        {"name": "主角团队", "type": "主角势力"},
                        {"name": "军方", "type": "官方势力"},
                        {"name": "掠夺者", "type": "反派势力"}
                    ],
                    "main_conflict": "资源争夺与生存权",
                    "faction_power_balance": "军方最强，主角潜力最大"
                }
            },
            "character_narrative": {
                "character_design": {
                    "protagonist": {
                        "basic_info": {"name": "林默", "age": 25},
                        "goals": "在末世建立安全据点，保护重要的人",
                        "abilities": "无限储物空间，空间内时间静止"
                    },
                    "supporting_characters": [
                        {"name": "苏晴", "role": "女主", "relationship": "幸存者"}
                    ]
                },
                "emotional_blueprint": {
                    "emotional_arcs": ["绝望→希望→绝望→大爽点"],
                    "key_emotional_beats": ["觉醒异能", "第一次囤货", "救下女主"]
                },
                "global_growth_plan": {
                    "protagonist_growth": ["普通白领→异能者→势力领袖"],
                    "milestone_events": ["建立安全屋", "收编团队", "对抗军方"]
                }
            },
            "structure_planning": {
                "overall_stage_plans": {
                    "stages": [
                        {"stage_name": "第一阶段：觉醒囤货", "chapter_range": "1-50"},
                        {"stage_name": "第二阶段：建立势力", "chapter_range": "51-150"},
                        {"stage_name": "第三阶段：争霸末世", "chapter_range": "151-300"}
                    ]
                },
                "stage_writing_plans": {
                    "第一阶段：觉醒囤货": {
                        "chapter_breakdown": [
                            {"chapter_number": 1, "title": "末世降临", "key_events": "病毒爆发"}
                        ]
                    }
                },
                "supplementary_characters": [
                    {"name": "张叔", "role": "仓库管理员", "importance": "中等"}
                ]
            },
            "expectation_system": {
                "expectation_mapping": {
                    "expectation_elements": ["无限空间升级", "女主身世揭秘", "末世真相"],
                    "element_schedule": {"空间升级": "第30章", "女主揭秘": "第100章"}
                },
                "system_init": {"status": "completed"}
            }
        }
        
        # 保存参考产物
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"reference_{creative_seed['name']}_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reference_outputs, f, ensure_ascii=False, indent=2)
        
        print(f"参考产物已保存: {output_file}")
        return reference_outputs
    
    def run_comparison(
        self,
        session_name: str,
        traditional_output: Dict,
        conversation_output: Dict
    ) -> Dict:
        """
        运行单个Session的对比测试
        
        Args:
            session_name: Session名称
            traditional_output: 传统模式产物
            conversation_output: 对话模式产物
            
        Returns:
            对比结果
        """
        print(f"\n对比测试: {session_name}")
        print("-" * 40)
        
        result = compare_session_outputs(
            traditional_output,
            conversation_output,
            session_name
        )
        
        # 打印结果
        print(f"验证通过: {result['validation_passed']}")
        print(f"存在差异: {result['has_differences']}")
        print(f"差异摘要: {result['difference_summary']}")
        print(f"兼容: {result['is_compatible']}")
        
        if result['validation_errors']:
            print("\n验证错误:")
            for error in result['validation_errors']:
                print(f"  - {error}")
        
        return result
    
    def run_all_comparisons(
        self,
        creative_seed: Dict,
        conversation_outputs: Dict[str, Dict]
    ) -> list:
        """
        运行所有Session的对比测试
        
        Args:
            creative_seed: 创意种子
            conversation_outputs: 对话模式各Session产物
            
        Returns:
            所有对比结果
        """
        print(f"\n{'='*80}")
        print(f"开始全量对比测试: {creative_seed['title']}")
        print(f"{'='*80}")
        
        # 生成传统模式参考产物
        traditional_outputs = self.generate_reference_outputs(creative_seed)
        
        # 对比每个Session
        results = []
        for session_name in conversation_outputs.keys():
            if session_name in traditional_outputs:
                result = self.run_comparison(
                    session_name,
                    traditional_outputs[session_name],
                    conversation_outputs[session_name]
                )
                results.append(result)
        
        # 生成完整报告
        report = generate_comparison_report(results)
        print("\n" + report)
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"comparison_report_{creative_seed['name']}_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存: {report_file}")
        
        return results
    
    def validate_conversation_output(
        self,
        session_name: str,
        output: Dict
    ) -> bool:
        """
        验证对话模式产物格式
        
        Args:
            session_name: Session名称
            output: 产物字典
            
        Returns:
            是否通过验证
        """
        from src.core.session_mode.validators import quick_validate
        
        is_valid = quick_validate(session_name, output)
        
        if is_valid:
            print(f"✅ {session_name} 格式验证通过")
        else:
            print(f"❌ {session_name} 格式验证失败")
        
        return is_valid


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="第一阶段对话化对比测试")
    parser.add_argument(
        "--generate-reference",
        action="store_true",
        help="生成传统模式参考产物"
    )
    parser.add_argument(
        "--session",
        type=str,
        choices=["foundation_planning", "character_narrative", 
                 "structure_planning", "expectation_system"],
        help="测试单个Session"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="测试所有Session"
    )
    parser.add_argument(
        "--seed-index",
        type=int,
        default=0,
        help=f"使用第几个创意种子 (0-{len(TEST_CREATIVE_SEEDS)-1})"
    )
    
    args = parser.parse_args()
    
    # 获取测试用的创意种子
    if args.seed_index < 0 or args.seed_index >= len(TEST_CREATIVE_SEEDS):
        print(f"错误的seed_index，可用范围: 0-{len(TEST_CREATIVE_SEEDS)-1}")
        return 1
    
    creative_seed = TEST_CREATIVE_SEEDS[args.seed_index]
    
    # 创建测试实例
    tester = PhaseOneComparisonTest()
    
    if args.generate_reference:
        # 生成参考产物
        tester.generate_reference_outputs(creative_seed)
        print("\n✅ 参考产物生成完成")
        
    elif args.session:
        # 单个Session测试
        print(f"测试Session: {args.session}")
        # TODO: 实际调用对话模式生成产物进行对比
        
    elif args.all:
        # 全量测试
        # TODO: 实际调用对话模式生成所有产物
        print("全量对比测试 - 需要实现对话模式后运行")
        
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
