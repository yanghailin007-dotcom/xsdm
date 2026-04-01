# -*- coding: utf-8 -*-
"""
测试报告生成功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, 'c:\\work\\xsdm')

from web.services.chapter_analytics_service import ChapterAnalyticsService
from web.services.report_generator import BatchReportGenerator

# 测试路径
novel_path = "小说项目/yanghailin/国运：扮演瞎子，队友白月魁"
novel_title = "国运：扮演瞎子，队友白月魁"

print("=" * 60)
print("测试批次质量报告生成")
print("=" * 60)

# 1. 测试章节分析服务
print("\n[1/3] 测试章节分析服务...")
analytics = ChapterAnalyticsService(novel_path)

# 分析前6章
metrics_list = analytics.analyze_batch(1, 6)
print(f"✓ 成功分析 {len(metrics_list)} 章")

for m in metrics_list:
    print(f"  C{m.chapter_num}: {m.word_count}字 | 对话{m.dialogue_ratio:.1f}% | 得分{m.tomato_score:.1f}")

# 2. 测试汇总数据生成
print("\n[2/3] 测试汇总数据生成...")
summary = analytics.get_batch_summary(metrics_list)
print(f"✓ 批次范围: {summary['chapter_range']}")
print(f"✓ 总字数: {summary['total_words']}")
print(f"✓ 平均番茄得分: {summary['avg_tomato_score']}")
print(f"✓ 对话比例: {summary['avg_dialogue_ratio']}%")
print(f"✓ 爽点密度: {summary['avg_shuang_density']}/千字")

# 3. 测试完整报告生成
print("\n[3/3] 测试完整报告生成...")
generator = BatchReportGenerator(novel_path, novel_title)
result = generator.generate_batch_report(1, 6)

if result:
    print(f"✓ 报告生成成功!")
    print(f"  报告路径: {result['report_path']}")
    print(f"  图表数量: {len(result['chart_paths'])}")
    for chart_type, path in result['chart_paths'].items():
        print(f"    - {chart_type}: {path}")
else:
    print("✗ 报告生成失败")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
