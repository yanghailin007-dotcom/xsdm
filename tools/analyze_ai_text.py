#!/usr/bin/env python3
"""
AI生成文本人味分析工具

分析当前AI生成的文本，与头部作品样本对比

使用方法:
1. 分析单个章节文件
   python tools/analyze_ai_text.py --file chapter_001.txt

2. 分析整个项目
   python tools/analyze_ai_text.py --project "小说项目/我的小说"

3. 对比样本
   python tools/analyze_ai_text.py --file chapter.txt --compare
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.human_touch import HumanTouchAnalyzer, SampleDatabase


def analyze_file(filepath: str, db: SampleDatabase = None):
    """分析单个文件"""
    path = Path(filepath)
    if not path.exists():
        print(f"文件不存在: {filepath}")
        return
    
    content = path.read_text(encoding='utf-8')
    
    analyzer = HumanTouchAnalyzer()
    metrics = analyzer.analyze(content)
    
    print("\n" + "="*60)
    print(f"文件: {path.name}")
    print("="*60)
    print(f"字数: {len(content)}")
    print(f"\n📊 人味指标:")
    print(f"  整体人味分数: {metrics.overall_score:.1f}/100")
    print(f"  句长方差: {metrics.sentence_variance:.2f} (头部作品通常15-40)")
    print(f"  破碎句比例: {metrics.fragment_ratio:.2%} (头部作品通常10-20%)")
    
    print(f"\n📝 句式特征:")
    print(f"  句子数: {metrics.sentence_count}")
    print(f"  平均句长: {metrics.avg_sentence_length:.1f}字")
    print(f"  短句比例: {metrics.short_sentence_ratio:.1%}")
    
    print(f"\n👁 感官描写密度:")
    print(f"  视觉: {metrics.visual_density:.3f}")
    print(f"  听觉: {metrics.auditory_density:.3f}")
    print(f"  触觉: {metrics.tactile_density:.3f}")
    print(f"  嗅觉: {metrics.olfactory_density:.3f}")
    print(f"  味觉: {metrics.gustatory_density:.3f}")
    
    print(f"\n💬 对话特征:")
    print(f"  对话占比: {metrics.dialogue_ratio:.1%}")
    print(f"  口语化程度: {metrics.colloquialism_ratio:.3f}")
    
    # 与样本对比
    if db:
        compare_with_samples(metrics, db)
    
    return metrics


def compare_with_samples(metrics, db: SampleDatabase):
    """与样本对比"""
    print("\n📈 与头部作品对比:")
    
    # 获取所有样本的平均值
    novels = db.get_all_novels()
    if not novels:
        print("  (暂无样本数据，请先收集头部作品样本)")
        return
    
    sample_scores = []
    sample_variances = []
    
    for novel in novels:
        chapters = db.get_chapters(novel.id)
        for ch in chapters:
            sample_scores.append(ch.metrics.get('overall_score', 0))
            sample_variances.append(ch.sentence_variance)
    
    if not sample_scores:
        return
    
    avg_score = sum(sample_scores) / len(sample_scores)
    avg_variance = sum(sample_variances) / len(sample_variances)
    
    score_diff = metrics.overall_score - avg_score
    variance_diff = metrics.sentence_variance - avg_variance
    
    print(f"  样本平均人味分数: {avg_score:.1f}")
    print(f"  你的文本人味分数: {metrics.overall_score:.1f}")
    print(f"  差距: {score_diff:+.1f} {'✓' if score_diff > -10 else '✗'}")
    
    print(f"\n  样本平均句长方差: {avg_variance:.2f}")
    print(f"  你的文本句长方差: {metrics.sentence_variance:.2f}")
    print(f"  差距: {variance_diff:+.2f} {'✓' if variance_diff > -5 else '✗'}")
    
    # 建议
    print("\n💡 改进建议:")
    if metrics.sentence_variance < 10:
        print("  - 句式太整齐，尝试长短句交替使用")
        print("  - 在情绪高潮处使用短句/破碎句")
    if metrics.fragment_ratio < 0.05:
        print("  - 缺少破碎句，适当加入'他愣住了。''怎么可能？'等短句")
    if metrics.sensory_density < 0.02:
        print("  - 感官描写不足，加入更多视觉/听觉/触觉细节")
    if metrics.colloquialism_ratio < 0.02:
        print("  - 对话太书面化，加入口语化表达和语气词")


def analyze_project(project_path: str):
    """分析整个项目"""
    path = Path(project_path)
    if not path.exists():
        print(f"项目不存在: {project_path}")
        return
    
    # 查找所有章节文件
    chapters_dir = path / 'chapters'
    if not chapters_dir.exists():
        print("未找到chapters目录")
        return
    
    chapter_files = list(chapters_dir.glob('*.txt')) + list(chapters_dir.glob('*.json'))
    
    if not chapter_files:
        print("未找到章节文件")
        return
    
    print(f"\n发现 {len(chapter_files)} 个章节文件")
    
    db = SampleDatabase()
    analyzer = HumanTouchAnalyzer()
    
    all_metrics = []
    
    for chapter_file in sorted(chapter_files)[:10]:  # 最多分析前10章
        if chapter_file.suffix == '.json':
            import json
            try:
                data = json.loads(chapter_file.read_text(encoding='utf-8'))
                content = data.get('content', '')
            except:
                continue
        else:
            content = chapter_file.read_text(encoding='utf-8')
        
        if len(content) < 100:
            continue
        
        metrics = analyzer.analyze(content)
        all_metrics.append(metrics)
        
        print(f"\n{chapter_file.name}: 人味分={metrics.overall_score:.1f}, 方差={metrics.sentence_variance:.2f}")
    
    # 整体统计
    if all_metrics:
        avg_score = sum(m.overall_score for m in all_metrics) / len(all_metrics)
        avg_variance = sum(m.sentence_variance for m in all_metrics) / len(all_metrics)
        
        print("\n" + "="*60)
        print("整体统计:")
        print(f"  平均人味分数: {avg_score:.1f}")
        print(f"  平均句长方差: {avg_variance:.2f}")
        print(f"  分析章节数: {len(all_metrics)}")
        
        compare_with_samples(all_metrics[0], db)  # 用第一章对比


def main():
    parser = argparse.ArgumentParser(description='AI文本人味分析工具')
    parser.add_argument('--file', help='分析单个文件')
    parser.add_argument('--project', help='分析整个项目')
    parser.add_argument('--compare', action='store_true', help='与样本对比')
    
    args = parser.parse_args()
    
    db = SampleDatabase() if args.compare else None
    
    if args.file:
        analyze_file(args.file, db)
    elif args.project:
        analyze_project(args.project)
    else:
        parser.print_help()
        print("\n示例:")
        print("  python tools/analyze_ai_text.py --file chapter_001.txt --compare")
        print("  python tools/analyze_ai_text.py --project \"小说项目/我的小说\"")


if __name__ == '__main__':
    main()
