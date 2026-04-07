"""
第一阶段对比测试 - 同时运行传统模式和对话模式
================================================

用法:
    python -m tests.run_phase_one_comparison --mode traditional --output-dir tests/comparison_outputs
    python -m tests.run_phase_one_comparison --mode conversation --output-dir tests/comparison_outputs
    
    # 对比产物
    python -m tests.run_phase_one_comparison --compare \
        --traditional-dir tests/comparison_outputs/traditional \
        --conversation-dir tests/comparison_outputs/conversation
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# 测试用的创意种子
TEST_CREATIVE_SEED = {
    "novel_title": "末世：无限空间囤货，我打造安全屋",
    "novel_synopsis": "末世降临，主角觉醒无限空间能力，疯狂囤货打造安全屋，收编幸存者建立势力",
    "category": "末世危机",
    "core_setting": {
        "world_background": "2024年丧尸病毒爆发，文明秩序崩塌",
        "golden_finger": "无限储物空间，时间静止",
        "core_selling_points": "囤货满足感、安全屋建设、势力发展"
    },
    "total_chapters": 200,
    "target_platform": "fanqie"
}


def save_outputs(output_dir: Path, outputs: Dict[str, Any], mode: str):
    """保存产物到文件"""
    output_dir = Path(output_dir) / mode
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整产物
    output_file = output_dir / f"phase_one_output_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)
    
    # 分别保存各个模块（便于对比）
    modules = [
        "writing_style_guide",
        "market_analysis", 
        "core_worldview",
        "faction_system",
        "character_design",
        "emotional_blueprint",
        "global_growth_plan",
        "overall_stage_plans",
        "stage_writing_plans"
    ]
    
    for module in modules:
        if module in outputs:
            module_file = output_dir / f"{module}_{timestamp}.json"
            with open(module_file, 'w', encoding='utf-8') as f:
                json.dump(outputs[module], f, ensure_ascii=False, indent=2)
    
    print(f"产物已保存到: {output_dir}")
    return output_dir


def run_traditional_mode(output_dir: Path) -> Dict[str, Any]:
    """运行传统模式"""
    print("\n" + "="*80)
    print("运行传统模式")
    print("="*80)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        
        # 创建配置
        config = {
            'use_creative_conversation_mode': False,
            'use_phase_one_conversation_mode': False,
            'llm': {
                'provider': 'gemini',
                'model': 'models/gemini-1.5-flash',
                'temperature': 0.7
            }
        }
        
        # 创建 NovelGenerator 实例
        generator = NovelGenerator(config=config)
        
        # 运行第一阶段
        print("开始运行传统模式第一阶段...")
        success = generator.phase_one_generation(
            creative_seed=TEST_CREATIVE_SEED,
            total_chapters=TEST_CREATIVE_SEED['total_chapters']
        )
        
        if not success:
            print("传统模式运行失败")
            return {}
        
        # 收集产物
        outputs = {
            "writing_style_guide": generator.novel_data.get("writing_style_guide", {}),
            "market_analysis": generator.novel_data.get("market_analysis", {}),
            "core_worldview": generator.novel_data.get("core_worldview", {}),
            "faction_system": generator.novel_data.get("faction_system", {}),
            "character_design": generator.novel_data.get("character_design", {}),
            "emotional_blueprint": generator.novel_data.get("emotional_blueprint", {}),
            "global_growth_plan": generator.novel_data.get("global_growth_plan", {}),
            "overall_stage_plans": generator.novel_data.get("overall_stage_plans", {}),
            "stage_writing_plans": generator.novel_data.get("stage_writing_plans", {}),
            "mode": "traditional",
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存产物
        save_outputs(output_dir, outputs, "traditional")
        
        print("传统模式运行完成")
        return outputs
        
    except Exception as e:
        print(f"传统模式运行出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def run_conversation_mode(output_dir: Path) -> Dict[str, Any]:
    """运行对话模式（使用新的FoundationPlanningSession）"""
    print("\n" + "="*80)
    print("运行对话模式（含FoundationPlanningSession）")
    print("="*80)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        
        # 创建配置
        config = {
            'use_creative_conversation_mode': True,
            'use_phase_one_conversation_mode': True,
            'session_fallback': {
                'foundation_planning': {'mode': 'conversation'},
                'character_narrative': {'mode': 'traditional'},
                'structure_planning': {'mode': 'traditional'}
            },
            'llm': {
                'provider': 'gemini',
                'model': 'models/gemini-1.5-flash',
                'temperature': 0.7
            }
        }
        
        # 创建 NovelGenerator 实例
        generator = NovelGenerator(config=config)
        
        # 运行第一阶段
        print("开始运行对话模式第一阶段...")
        success = generator.phase_one_generation(
            creative_seed=TEST_CREATIVE_SEED,
            total_chapters=TEST_CREATIVE_SEED['total_chapters']
        )
        
        if not success:
            print("对话模式运行失败")
            return {}
        
        # 收集产物
        outputs = {
            "writing_style_guide": generator.novel_data.get("writing_style_guide", {}),
            "market_analysis": generator.novel_data.get("market_analysis", {}),
            "core_worldview": generator.novel_data.get("core_worldview", {}),
            "faction_system": generator.novel_data.get("faction_system", {}),
            "character_design": generator.novel_data.get("character_design", {}),
            "emotional_blueprint": generator.novel_data.get("emotional_blueprint", {}),
            "global_growth_plan": generator.novel_data.get("global_growth_plan", {}),
            "overall_stage_plans": generator.novel_data.get("overall_stage_plans", {}),
            "stage_writing_plans": generator.novel_data.get("stage_writing_plans", {}),
            "mode": "conversation",
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存产物
        save_outputs(output_dir, outputs, "conversation")
        
        print("对话模式运行完成")
        return outputs
        
    except Exception as e:
        print(f"对话模式运行出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def compare_outputs(traditional_dir: Path, conversation_dir: Path):
    """对比传统模式和对话模式的产物"""
    print("\n" + "="*80)
    print("对比产物")
    print("="*80)
    
    from src.core.session_mode.validators import (
        FoundationPlanningValidator,
        CharacterNarrativeValidator,
        StructurePlanningValidator,
        compare_session_outputs
    )
    
    modules = [
        ("foundation_planning", FoundationPlanningValidator(), [
            "writing_style_guide",
            "market_analysis",
            "core_worldview",
            "faction_system"
        ]),
        ("character_narrative", CharacterNarrativeValidator(), [
            "character_design",
            "emotional_blueprint",
            "global_growth_plan"
        ]),
        ("structure_planning", StructurePlanningValidator(), [
            "overall_stage_plans",
            "stage_writing_plans"
        ])
    ]
    
    results = []
    
    for session_name, validator, files in modules:
        print(f"\n【{session_name}】")
        print("-" * 40)
        
        for file_name in files:
            trad_file = Path(traditional_dir) / f"{file_name}_*.json"
            conv_file = Path(conversation_dir) / f"{file_name}_*.json"
            
            # 找到最新的文件
            trad_files = list(Path(traditional_dir).glob(f"{file_name}_*.json"))
            conv_files = list(Path(conversation_dir).glob(f"{file_name}_*.json"))
            
            if not trad_files or not conv_files:
                print(f"  {file_name}: 文件不存在，跳过")
                continue
            
            # 读取最新的文件
            trad_latest = max(trad_files, key=lambda p: p.stat().st_mtime)
            conv_latest = max(conv_files, key=lambda p: p.stat().st_mtime)
            
            with open(trad_latest, 'r', encoding='utf-8') as f:
                trad_data = json.load(f)
            with open(conv_latest, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            # 对比
            comparison = compare_session_outputs(trad_data, conv_data, session_name)
            
            print(f"  {file_name}:")
            print(f"    验证通过: {comparison['validation_passed']}")
            print(f"    存在差异: {comparison['has_differences']}")
            print(f"    差异摘要: {comparison['difference_summary']}")
            
            results.append({
                "module": file_name,
                "comparison": comparison
            })
    
    # 生成对比报告
    generate_comparison_report(results, traditional_dir, conversation_dir)


def generate_comparison_report(results: list, trad_dir: Path, conv_dir: Path):
    """生成对比报告"""
    print("\n" + "="*80)
    print("对比报告")
    print("="*80)
    
    report_lines = [
        "# 第一阶段产物对比报告\n",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"传统模式产物: {trad_dir}\n",
        f"对话模式产物: {conv_dir}\n",
        "\n## 对比结果\n"
    ]
    
    compatible_count = 0
    incompatible_count = 0
    
    for result in results:
        module = result['module']
        comparison = result['comparison']
        
        is_compatible = comparison.get('is_compatible', False)
        if is_compatible:
            compatible_count += 1
            status = "✅ 兼容"
        else:
            incompatible_count += 1
            status = "⚠️ 存在差异"
        
        report_lines.append(f"\n### {module}\n")
        report_lines.append(f"- 状态: {status}\n")
        report_lines.append(f"- 验证通过: {comparison['validation_passed']}\n")
        report_lines.append(f"- 差异摘要: {comparison['difference_summary']}\n")
        
        if comparison.get('validation_errors'):
            report_lines.append("- 验证错误:\n")
            for error in comparison['validation_errors']:
                report_lines.append(f"  - {error}\n")
    
    report_lines.append(f"\n## 总结\n")
    report_lines.append(f"- 兼容模块: {compatible_count}/{len(results)}\n")
    report_lines.append(f"- 存在差异: {incompatible_count}/{len(results)}\n")
    
    # 保存报告
    report_dir = Path(trad_dir).parent
    report_file = report_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"\n报告已保存: {report_file}")
    
    # 打印总结
    print(f"\n兼容模块: {compatible_count}/{len(results)}")
    print(f"存在差异: {incompatible_count}/{len(results)}")


def main():
    parser = argparse.ArgumentParser(description="第一阶段对比测试")
    parser.add_argument("--mode", choices=["traditional", "conversation"], help="运行模式")
    parser.add_argument("--output-dir", default="tests/comparison_outputs", help="输出目录")
    parser.add_argument("--compare", action="store_true", help="对比模式")
    parser.add_argument("--traditional-dir", help="传统模式产物目录")
    parser.add_argument("--conversation-dir", help="对话模式产物目录")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.compare:
        if not args.traditional_dir or not args.conversation_dir:
            print("对比模式需要提供 --traditional-dir 和 --conversation-dir")
            return 1
        compare_outputs(args.traditional_dir, args.conversation_dir)
    elif args.mode == "traditional":
        outputs = run_traditional_mode(output_dir)
        return 0 if outputs else 1
    elif args.mode == "conversation":
        outputs = run_conversation_mode(output_dir)
        return 0 if outputs else 1
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
