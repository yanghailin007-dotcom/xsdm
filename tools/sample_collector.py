#!/usr/bin/env python3
"""
头部作品样本收集工具

使用方法:
1. 直接运行进行交互式录入
   python tools/sample_collector.py

2. 从JSON文件批量导入
   python tools/sample_collector.py --import samples.json

3. 导出数据库到JSON
   python tools/sample_collector.py --export output.json
"""

import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.human_touch import SampleDatabase, NovelSample, ChapterSample, HumanTouchAnalyzer


def interactive_add_novel(db: SampleDatabase):
    """交互式添加小说样本"""
    print("\n" + "="*50)
    print("添加头部作品样本")
    print("="*50)
    
    # 基本信息
    title = input("书名: ").strip()
    if not title:
        print("书名不能为空")
        return
    
    # 检查是否已存在
    existing = db.get_novel_by_title(title)
    if existing:
        print(f"警告: '{title}' 已存在(ID={existing.id})，继续将添加新记录")
    
    author = input("作者: ").strip()
    genre = input("题材类型(如:赘婿/玄幻/都市): ").strip()
    
    print("\n表现数据(可选，直接回车跳过):")
    total_chapters = input("总章节数: ").strip()
    total_words = input("总字数: ").strip()
    rating = input("评分(如9.2): ").strip()
    
    sample_reason = input("\n为什么选择这本作为样本(人味特征): ").strip()
    
    style_tags = input("风格标签(用逗号分隔，如:热血,幽默,快节奏): ").strip()
    style_tags = [t.strip() for t in style_tags.split(",") if t.strip()]
    
    novel = NovelSample(
        title=title,
        author=author,
        genre=genre,
        total_chapters=int(total_chapters) if total_chapters else 0,
        total_words=int(total_words) if total_words else 0,
        rating=float(rating) if rating else 0.0,
        sample_reason=sample_reason,
        style_tags=style_tags
    )
    
    novel_id = db.add_novel(novel)
    print(f"\n✅ 小说已添加，ID: {novel_id}")
    
    # 添加章节样本
    add_chapters = input("\n是否添加章节样本?(y/n): ").strip().lower()
    if add_chapters == 'y':
        add_chapters_interactive(db, novel_id)


def add_chapters_interactive(db: SampleDatabase, novel_id: int):
    """交互式添加章节"""
    analyzer = HumanTouchAnalyzer()
    
    print("\n" + "-"*50)
    print("添加章节样本")
    print("提示: 建议选取开头、中间、结尾各1-2章")
    print("-"*50)
    
    while True:
        print(f"\n当前小说ID: {novel_id}")
        chapter_num = input("章节号(如1, 50, 100，输入q退出): ").strip()
        if chapter_num.lower() == 'q':
            break
        
        if not chapter_num.isdigit():
            print("请输入数字")
            continue
        
        title = input("章节标题: ").strip()
        
        print("章节内容(输入END结束，支持多行):")
        lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        
        content = '\n'.join(lines)
        
        if len(content) < 100:
            print("内容太短，跳过")
            continue
        
        # 自动分析
        print("正在分析人味特征...")
        metrics = analyzer.analyze(content)
        
        chapter = ChapterSample(
            novel_id=novel_id,
            chapter_number=int(chapter_num),
            title=title,
            content=content,
            word_count=len(content),
            metrics=metrics.to_dict(),
            sentence_count=metrics.sentence_count,
            avg_sentence_length=metrics.avg_sentence_length,
            sentence_variance=metrics.sentence_variance
        )
        
        chapter_id = db.add_chapter(chapter)
        print(f"✅ 章节已添加，ID: {chapter_id}")
        print(f"   人味分数: {metrics.overall_score:.1f}")
        print(f"   句长方差: {metrics.sentence_variance:.2f}")


def list_novels(db: SampleDatabase):
    """列出所有小说样本"""
    novels = db.get_all_novels()
    
    if not novels:
        print("数据库为空")
        return
    
    print("\n" + "="*80)
    print(f"{'ID':<5} {'书名':<20} {'作者':<12} {'题材':<10} {'章节数':<8} {'评分':<6}")
    print("="*80)
    
    for novel in novels:
        chapters = db.get_chapters(novel.id)
        print(f"{novel.id:<5} {novel.title[:18]:<20} {novel.author[:10]:<12} "
              f"{novel.genre[:8]:<10} {len(chapters):<8} {novel.rating:<6}")
    
    print(f"\n总计: {len(novels)} 本小说")


def analyze_novel(db: SampleDatabase):
    """分析指定小说"""
    novel_id = input("请输入小说ID: ").strip()
    if not novel_id.isdigit():
        print("无效ID")
        return
    
    novel = db.get_novel(int(novel_id))
    if not novel:
        print("小说不存在")
        return
    
    chapters = db.get_chapters(novel.id)
    
    print("\n" + "="*50)
    print(f"《{novel.title}》分析报告")
    print("="*50)
    print(f"作者: {novel.author}")
    print(f"题材: {novel.genre}")
    print(f"样本章节数: {len(chapters)}")
    
    if chapters:
        # 计算平均指标
        avg_variance = sum(c.sentence_variance for c in chapters) / len(chapters)
        avg_score = sum(c.metrics.get('overall_score', 0) for c in chapters) / len(chapters)
        
        print(f"\n平均人味分数: {avg_score:.1f}")
        print(f"平均句长方差: {avg_variance:.2f}")
        
        print("\n各章节详情:")
        for ch in chapters:
            score = ch.metrics.get('overall_score', 0)
            print(f"  第{ch.chapter_number}章 {ch.title[:15]:<15} - 人味分:{score:.1f}")


def main():
    parser = argparse.ArgumentParser(description='头部作品样本收集工具')
    parser.add_argument('--import', dest='import_file', help='从JSON文件导入')
    parser.add_argument('--export', help='导出到JSON文件')
    parser.add_argument('--db', help='数据库文件路径')
    
    args = parser.parse_args()
    
    # 初始化数据库
    db = SampleDatabase(args.db)
    
    if args.import_file:
        print(f"正在从 {args.import_file} 导入...")
        db.import_from_json(args.import_file)
        return
    
    if args.export:
        print(f"正在导出到 {args.export}...")
        db.export_to_json(args.export)
        return
    
    # 交互式菜单
    while True:
        print("\n" + "="*50)
        print("头部作品样本收集工具")
        print("="*50)
        print("1. 添加小说样本")
        print("2. 查看所有样本")
        print("3. 分析小说样本")
        print("4. 导出数据库")
        print("0. 退出")
        
        choice = input("\n请选择: ").strip()
        
        if choice == '1':
            interactive_add_novel(db)
        elif choice == '2':
            list_novels(db)
        elif choice == '3':
            analyze_novel(db)
        elif choice == '4':
            path = input("导出文件路径: ").strip()
            if path:
                db.export_to_json(path)
        elif choice == '0':
            print("再见!")
            break
        else:
            print("无效选择")


if __name__ == '__main__':
    main()
