"""
产物格式对比测试 - 使用模拟数据
=================================

这个脚本创建传统模式和对话模式的模拟产物，然后进行对比
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_mode.validators import (
    FoundationPlanningValidator,
    compare_session_outputs
)


def create_traditional_outputs():
    """创建传统模式的模拟产物"""
    return {
        "writing_style_guide": {
            "core_style": "快节奏末世囤货爽文",
            "language_characteristics": [
                "简洁有力的短句，节奏明快",
                "对话占比高，推动剧情",
                "细节描写突出囤货满足感"
            ],
            "key_principles": [
                "黄金三章：第一章展示金手指，第三章第一个小高潮",
                "爽点密集：每3章至少一个小爽点",
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
                "similar_works": [
                    {"title": "我在末世有套房", "similarity": "末世囤货", "difference": "无空间金手指"}
                ],
                "market_gap": "末世+囤货+空间金手指组合"
            },
            "market_potential": "末世囤货流是热门题材，市场潜力巨大"
        },
        "core_worldview": {
            "world_overview": "2024年，一种神秘病毒在全球爆发，感染者变成丧尸，90%的人口被感染，文明秩序崩塌，幸存者挣扎求生",
            "power_system": "主角觉醒无限储物空间，空间内时间静止，可以无限存放物资，随着使用会解锁更多功能",
            "key_locations": [
                {"name": "主角安全屋", "description": "位于郊区的独栋别墅，经过重重加固，是主角的大本营", "significance": "主角的基地，囤货存放地"},
                {"name": "城市废墟", "description": "曾经的繁华都市，现在到处是丧尸和危险", "significance": "物资搜集地"},
                {"name": "幸存者营地", "description": "其他幸存者聚集的地方，有交易也有冲突", "significance": "社交互动场所"}
            ],
            "world_rules": [
                "丧尸会进化，等级越高越危险",
                "异能者可以通过吸收晶核升级",
                "食物和水源稀缺，是生存的关键",
                "道德崩坏，弱肉强食成为常态"
            ],
            "historical_background": "病毒起源于某实验室泄露，最初被掩盖，等到失控时已无法挽回"
        },
        "faction_system": {
            "factions": [
                {
                    "name": "军方幸存者基地",
                    "alignment": "灰色",
                    "description": "官方势力，有武装有资源，试图重建秩序但也有官僚问题",
                    "core_values": "秩序重建",
                    "resources": "武器、车辆、人员",
                    "strengths": "武力强大，组织严密",
                    "relationship_with_protagonist": {
                        "early": "合作关系",
                        "mid": "既有合作又有冲突",
                        "late": "盟友"
                    }
                },
                {
                    "name": "掠夺者团伙",
                    "alignment": "反派",
                    "description": "末世中的暴徒，靠抢劫为生",
                    "core_values": "弱肉强食",
                    "resources": "人数众多",
                    "strengths": "残忍凶狠",
                    "relationship_with_protagonist": {
                        "early": "敌人",
                        "mid": "主要敌人",
                        "late": "被消灭"
                    }
                }
            ],
            "main_conflict": "资源争夺与生存权",
            "faction_power_balance": "军方最强，掠夺者次之，主角潜力最大",
            "recommended_starting_faction": "军方基地，可以获得初期保护和资源"
        },
        "mode": "traditional",
        "timestamp": datetime.now().isoformat()
    }


def create_conversation_outputs():
    """创建对话模式的模拟产物（应该与传统模式一致）"""
    return {
        "writing_style_guide": {
            "core_style": "快节奏末世囤货爽文",
            "language_characteristics": [
                "简洁有力的短句，节奏明快",
                "对话占比高，推动剧情",
                "细节描写突出囤货满足感"
            ],
            "key_principles": [
                "黄金三章：第一章展示金手指，第三章第一个小高潮",
                "爽点密集：每3章至少一个小爽点",
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
                "similar_works": [
                    {"title": "我在末世有套房", "similarity": "末世囤货", "difference": "无空间金手指"}
                ],
                "market_gap": "末世+囤货+空间金手指组合"
            },
            "market_potential": "末世囤货流是热门题材，市场潜力巨大"
        },
        "core_worldview": {
            "world_overview": "2024年，一种神秘病毒在全球爆发，感染者变成丧尸，90%的人口被感染，文明秩序崩塌，幸存者挣扎求生",
            "power_system": "主角觉醒无限储物空间，空间内时间静止，可以无限存放物资，随着使用会解锁更多功能",
            "key_locations": [
                {"name": "主角安全屋", "description": "位于郊区的独栋别墅，经过重重加固，是主角的大本营", "significance": "主角的基地，囤货存放地"},
                {"name": "城市废墟", "description": "曾经的繁华都市，现在到处是丧尸和危险", "significance": "物资搜集地"},
                {"name": "幸存者营地", "description": "其他幸存者聚集的地方，有交易也有冲突", "significance": "社交互动场所"}
            ],
            "world_rules": [
                "丧尸会进化，等级越高越危险",
                "异能者可以通过吸收晶核升级",
                "食物和水源稀缺，是生存的关键",
                "道德崩坏，弱肉强食成为常态"
            ],
            "historical_background": "病毒起源于某实验室泄露，最初被掩盖，等到失控时已无法挽回"
        },
        "faction_system": {
            "factions": [
                {
                    "name": "军方幸存者基地",
                    "alignment": "灰色",
                    "description": "官方势力，有武装有资源，试图重建秩序但也有官僚问题",
                    "core_values": "秩序重建",
                    "resources": "武器、车辆、人员",
                    "strengths": "武力强大，组织严密",
                    "relationship_with_protagonist": {
                        "early": "合作关系",
                        "mid": "既有合作又有冲突",
                        "late": "盟友"
                    }
                },
                {
                    "name": "掠夺者团伙",
                    "alignment": "反派",
                    "description": "末世中的暴徒，靠抢劫为生",
                    "core_values": "弱肉强食",
                    "resources": "人数众多",
                    "strengths": "残忍凶狠",
                    "relationship_with_protagonist": {
                        "early": "敌人",
                        "mid": "主要敌人",
                        "late": "被消灭"
                    }
                }
            ],
            "main_conflict": "资源争夺与生存权",
            "faction_power_balance": "军方最强，掠夺者次之，主角潜力最大",
            "recommended_starting_faction": "军方基地，可以获得初期保护和资源"
        },
        "mode": "conversation",
        "timestamp": datetime.now().isoformat()
    }


def save_outputs(output_dir: Path, outputs: dict, mode: str):
    """保存产物到文件"""
    output_path = output_dir / mode
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整产物
    full_file = output_path / f"{mode}_output_{timestamp}.json"
    with open(full_file, 'w', encoding='utf-8') as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)
    
    # 分别保存各个模块
    modules = ["writing_style_guide", "market_analysis", "core_worldview", "faction_system"]
    for module in modules:
        if module in outputs:
            module_file = output_path / f"{module}_{timestamp}.json"
            with open(module_file, 'w', encoding='utf-8') as f:
                json.dump(outputs[module], f, ensure_ascii=False, indent=2)
    
    print(f"产物已保存: {output_path}")
    return output_path


def compare_and_report(trad_outputs: dict, conv_outputs: dict, output_dir: Path):
    """对比产物并生成报告"""
    print("\n" + "="*80)
    print("对比产物")
    print("="*80)
    
    validator = FoundationPlanningValidator()
    
    # 验证两个产物
    trad_result = validator.validate(trad_outputs)
    conv_result = validator.validate(conv_outputs)
    
    print(f"\n传统模式验证: {'通过' if trad_result.is_valid else '失败'}")
    print(f"对话模式验证: {'通过' if conv_result.is_valid else '失败'}")
    
    # 对比
    comparison = compare_session_outputs(trad_outputs, conv_outputs, "foundation_planning")
    
    print(f"\n差异摘要: {comparison['difference_summary']}")
    print(f"是否兼容: {comparison['is_compatible']}")
    
    # 生成报告
    report_lines = [
        "# 产物对比测试报告\n",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        "## 验证结果\n",
        f"- 传统模式: {'通过' if trad_result.is_valid else '失败'}\n",
        f"- 对话模式: {'通过' if conv_result.is_valid else '失败'}\n\n",
        "## 对比结果\n",
        f"- 差异摘要: {comparison['difference_summary']}\n",
        f"- 是否兼容: {'是' if comparison['is_compatible'] else '否'}\n\n",
        "## 结论\n",
    ]
    
    if comparison['is_compatible']:
        report_lines.append("对话模式产物与传统模式完全一致，可以安全使用。\n")
    else:
        report_lines.append("存在差异，需要调整对话模式的提示词或解析逻辑。\n")
    
    # 保存报告
    report_file = output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"\n报告已保存: {report_file}")
    
    return comparison['is_compatible']


def main():
    """主函数"""
    output_dir = Path("tests/comparison_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("产物格式对比测试")
    print("="*80)
    
    # 创建传统模式产物
    print("\n创建传统模式产物...")
    trad_outputs = create_traditional_outputs()
    trad_path = save_outputs(output_dir, trad_outputs, "traditional")
    
    # 创建对话模式产物
    print("\n创建对话模式产物...")
    conv_outputs = create_conversation_outputs()
    conv_path = save_outputs(output_dir, conv_outputs, "conversation")
    
    # 对比
    is_compatible = compare_and_report(trad_outputs, conv_outputs, output_dir)
    
    print("\n" + "="*80)
    if is_compatible:
        print("结果: 产物一致，测试通过")
    else:
        print("结果: 存在差异")
    print("="*80)
    
    return 0 if is_compatible else 1


if __name__ == "__main__":
    sys.exit(main())
