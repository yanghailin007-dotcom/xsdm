"""
测试系统功率密度监控机制

对比分析：
- 旧版本（前20章）：密度不足的问题
- 新版本（应用监控后）：改善效果
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from managers.SystemPowerDensityMonitor import LootSystemMonitor, DensityConstraint
import json


def simulate_old_version():
    """
    模拟旧版本（实际生成的前20章）
    
    根据诊断报告，前20章的掠夺记录：
    - 第2章：温天仁（六极真魔体）
    - 第20章：罗刹鬼王（万魂统御）
    - 仅此2次掠夺
    """
    print("=" * 60)
    print("旧版本模拟（实际生成的前20章）")
    print("=" * 60)
    
    monitor = LootSystemMonitor()
    
    # 记录前20章的实际生成情况
    chapters = [
        (1, False, None, None, None, None, "plot"),        # 第1章：观战
        (2, True, "温天仁", "六极真魔体", "紫", "体质类", "combat"),  # 第2章：掠夺
        (3, True, "温天仁", "魔道少主", "蓝", "身份类", "combat"),   # 第3章：掠夺
        (4, False, None, None, None, None, "combat"),      # 第4章：战斗
        (5, False, None, None, None, None, "combat"),      # 第5章：战斗
        (6, False, None, None, None, None, "combat"),      # 第6章：战斗
        (7, False, None, None, None, None, "combat"),      # 第7章：战斗
        (8, False, None, None, None, None, "combat"),      # 第8章：战斗
        (9, False, None, None, None, None, "plot"),        # 第9章：剧情
        (10, False, None, None, None, None, "combat"),     # 第10章：战斗
        (11, False, None, None, None, None, "combat"),     # 第11章：战斗
        (12, False, None, None, None, None, "plot"),       # 第12章：剧情
        (13, False, None, None, None, None, "combat"),     # 第13章：战斗
        (14, False, None, None, None, None, "combat"),     # 第14章：战斗
        (15, False, None, None, None, None, "combat"),     # 第15章：战斗
        (16, False, None, None, None, None, "combat"),     # 第16章：战斗
        (17, False, None, None, None, None, "combat"),     # 第17章：战斗
        (18, False, None, None, None, None, "combat"),     # 第18章：战斗
        (19, False, None, None, None, None, "plot"),       # 第19章：剧情
        (20, True, "罗刹鬼王", "万魂统御", "紫", "技能类", "combat"),  # 第20章：掠夺
    ]
    
    for chapter_num, triggered, target, reward, quality, rtype, ctype in chapters:
        monitor.post_generation_validate(
            chapter_num=chapter_num,
            triggered=triggered,
            target_name=target,
            reward_name=reward,
            reward_quality=quality,
            reward_type=rtype,
            chapter_type=ctype
        )
    
    # 生成报告
    report = monitor.generate_density_report(1, 20)
    
    print(f"\n【密度统计】")
    print(f"  触发次数：{report['trigger_count']}/20章")
    print(f"  密度：{report['density_per_10_chapters']}/10章（期望{report['expected_density']}/10章）")
    print(f"  密度得分：{report['density_score']}/100")
    print(f"  最大间隔：{report['max_gap_without_trigger']}章（允许{report['acceptable_gap']}章）")
    
    if report['issues']:
        print(f"\n【发现问题】")
        for issue in report['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['message']}")
    
    if report['recommendations']:
        print(f"\n【改进建议】")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    # 检查第21章的约束
    print(f"\n【第21章生成前检查】")
    constraints = monitor.pre_generation_check(21)
    if constraints:
        for constraint in constraints:
            print(f"  [{constraint.urgency.upper()}] {constraint.message}")
    else:
        print(f"  无约束")
    
    return report


def simulate_new_version():
    """
    模拟新版本（应用密度监控后）
    
    按照"每3章至少掠夺1次"的规则重新规划
    """
    print("\n\n")
    print("=" * 60)
    print("新版本模拟（应用密度监控后的规划）")
    print("=" * 60)
    
    monitor = LootSystemMonitor()
    
    # 按照"每3章至少掠夺1次"的规则规划
    chapters = [
        (1, False, None, None, None, None, "plot"),        # 第1章：观战
        (2, True, "温天仁", "六极真魔体", "紫", "体质类", "combat"),  # 第2章：掠夺
        (3, True, "温天仁", "魔道少主", "蓝", "身份类", "combat"),   # 第3章：掠夺
        
        (4, False, None, None, None, None, "plot"),        # 第4章：进入阴冥之地
        (5, True, "阴冥兽群", "阴冥之气", "蓝", "能量类", "combat"),  # 第5章：掠夺
        (6, False, None, None, None, None, "combat"),      # 第6章：展示战力
        (7, False, None, None, None, None, "plot"),        # 第7章：梅凝剧情
        
        (8, True, "变异阴兽", "铜皮铁骨", "蓝", "体质类", "combat"),  # 第8章：掠夺
        (9, False, None, None, None, None, "plot"),        # 第9章：篝火夜话
        (10, False, None, None, None, None, "combat"),     # 第10章：兽王之战
        
        (11, True, "阴冥兽王", "兽王精血", "紫", "体质类", "combat"),  # 第11章：掠夺
        (12, False, None, None, None, None, "plot"),       # 第12章：整顿队伍
        (13, False, None, None, None, None, "combat"),     # 第13章：攀登暴风山
        
        (14, True, "鬼雾怨灵", "神魂护体", "蓝", "防御类", "combat"),  # 第14章：掠夺
        (15, False, None, None, None, None, "combat"),     # 第15章：啼魂受挫
        (16, False, None, None, None, None, "plot"),       # 第16章：风暴前夕
        
        (17, True, "变异鬼兵", "鬼道亲和", "蓝", "亲和类", "combat"),  # 第17章：掠夺
        (18, False, None, None, None, None, "plot"),       # 第18章：依偎取暖
        (19, False, None, None, None, None, "combat"),     # 第19章：鬼王降临
        
        (20, True, "罗刹鬼王", "万魂统御", "紫", "技能类", "combat"),  # 第20章：掠夺
    ]
    
    for chapter_num, triggered, target, reward, quality, rtype, ctype in chapters:
        monitor.post_generation_validate(
            chapter_num=chapter_num,
            triggered=triggered,
            target_name=target,
            reward_name=reward,
            reward_quality=quality,
            reward_type=rtype,
            chapter_type=ctype
        )
    
    # 生成报告
    report = monitor.generate_density_report(1, 20)
    
    print(f"\n【密度统计】")
    print(f"  触发次数：{report['trigger_count']}/20章")
    print(f"  密度：{report['density_per_10_chapters']}/10章（期望{report['expected_density']}/10章）")
    print(f"  密度得分：{report['density_score']}/100")
    print(f"  最大间隔：{report['max_gap_without_trigger']}章（允许{report['acceptable_gap']}章）")
    
    if report['issues']:
        print(f"\n【发现问题】")
        for issue in report['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['message']}")
    else:
        print(f"\n【发现问题】无")
    
    if report['recommendations']:
        print(f"\n【改进建议】")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    else:
        print(f"\n【改进建议】无")
    
    # 检查第21章的约束
    print(f"\n【第21章生成前检查】")
    constraints = monitor.pre_generation_check(21)
    if constraints:
        for constraint in constraints:
            print(f"  [{constraint.urgency.upper()}] {constraint.message}")
    else:
        print(f"  无约束（密度正常）")
    
    return report


def generate_comparison_report(old_report, new_report):
    """生成对比报告"""
    print("\n\n")
    print("=" * 60)
    print("【对比分析】")
    print("=" * 60)
    
    print(f"\n指标对比：")
    print(f"  触发次数：{old_report['trigger_count']} → {new_report['trigger_count']}（提升{((new_report['trigger_count'] - old_report['trigger_count']) / old_report['trigger_count'] * 100):.1f}%）")
    print(f"  密度：{old_report['density_per_10_chapters']}/10章 → {new_report['density_per_10_chapters']}/10章（提升{((new_report['density_per_10_chapters'] - old_report['density_per_10_chapters']) / old_report['density_per_10_chapters'] * 100):.1f}%）")
    print(f"  密度得分：{old_report['density_score']}/100 → {new_report['density_score']}/100（提升{new_report['density_score'] - old_report['density_score']}分）")
    print(f"  最大间隔：{old_report['max_gap_without_trigger']}章 → {new_report['max_gap_without_trigger']}章（改善{old_report['max_gap_without_trigger'] - new_report['max_gap_without_trigger']}章）")
    print(f"  问题数量：{len(old_report['issues'])} → {len(new_report['issues'])}")
    
    print(f"\n【结论】")
    if new_report['density_score'] >= 90:
        print("  [OK] 新版本密度达标，符合预期！")
    elif new_report['density_score'] >= 70:
        print("  [WARN] 新版本密度基本达标，仍有优化空间")
    else:
        print("  [FAIL] 新版本密度仍不足，需要进一步优化")
    
    improvement_rate = (new_report['density_score'] - old_report['density_score']) / old_report['density_score'] * 100
    print(f"\n  整体改善：{improvement_rate:.1f}%")


if __name__ == "__main__":
    # 运行对比测试
    old_report = simulate_old_version()
    new_report = simulate_new_version()
    generate_comparison_report(old_report, new_report)
    
    # 保存报告
    report_data = {
        "old_version": old_report,
        "new_version": new_report,
        "timestamp": "2025-12-27"
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "docs", "novel_analysis", "density_monitor_test_report.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已保存至：{output_path}")