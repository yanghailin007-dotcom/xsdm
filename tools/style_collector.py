#!/usr/bin/env python3
"""
文风库录入工具

使用方式:
1. 用户提供截图，大模型识别文字后
2. 运行此工具录入风格

python tools/style_collector.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.style_library import StyleDatabase, StyleProfile, ChapterSample, StyleExtractor


def interactive_add_style():
    """交互式添加风格"""
    print("\n" + "="*60)
    print("添加头部作品风格到文风库")
    print("="*60)
    
    db = StyleDatabase()
    extractor = StyleExtractor()
    
    # 1. 基本信息
    title = input("\n书名: ").strip()
    if not title:
        print("书名不能为空")
        return
    
    # 检查是否已存在
    existing = db.get_profile_by_title(title)
    if existing:
        print(f"\n⚠️  '{title}' 已存在 (ID={existing.id})")
        choice = input("是否添加更多章节样本?(y/n): ").strip().lower()
        if choice == 'y':
            add_chapters_to_existing(db, extractor, existing.id)
        return
    
    author = input("作者: ").strip()
    genre = input("题材(如:赘婿/玄幻/都市): ").strip()
    sub_genre = input("子题材(可选): ").strip()
    
    print("\n风格标签(用逗号分隔):")
    print("  可选:热血,幽默,悬疑,甜宠,压抑,快节奏,慢节奏...")
    tone_input = input("标签: ").strip()
    tone_tags = [t.strip() for t in tone_input.split(",") if t.strip()]
    
    pace = ""
    if any(t in tone_tags for t in ['快节奏', '爽文']):
        pace = '快节奏'
    elif any(t in tone_tags for t in ['慢节奏', '种田', '温馨']):
        pace = '慢节奏'
    
    description = input("\n风格描述(可选): ").strip()
    
    # 创建风格档案
    profile = StyleProfile(
        title=title,
        author=author,
        genre=genre,
        sub_genre=sub_genre,
        tone_tags=tone_tags,
        pace=pace,
        description=description
    )
    
    profile_id = db.add_profile(profile)
    print(f"\n✅ 风格档案已创建，ID: {profile_id}")
    
    # 2. 添加章节样本
    add_chapters_interactive(db, extractor, profile_id)
    
    # 3. 更新风格指纹
    print("\n正在计算综合风格指纹...")
    db.update_profile_fingerprint(profile_id)
    
    updated = db.get_profile(profile_id)
    print(f"✅ 风格录入完成！")
    print(f"   样本章节数: {updated.chapter_count}")
    print(f"   句长方差: {updated.fingerprint.sentence_variance:.2f}")
    print(f"   对话占比: {updated.fingerprint.dialogue_ratio:.1%}")


def add_chapters_interactive(db, extractor, profile_id):
    """交互式添加章节"""
    print("\n" + "-"*60)
    print("添加章节样本（建议开头、中间、结尾各1-2章）")
    print("-"*60)
    
    while True:
        print(f"\n当前风格ID: {profile_id}")
        chapter_num = input("章节号(如1, 50, 100，输入q完成): ").strip()
        if chapter_num.lower() == 'q':
            break
        
        if not chapter_num.isdigit():
            print("请输入数字")
            continue
        
        title = input("章节标题: ").strip()
        
        print("章节内容（识别后的文字，输入END结束）:")
        lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        
        content = '\n'.join(lines)
        
        if len(content) < 200:
            print("⚠️  内容太短（<200字），跳过")
            continue
        
        # 提取风格特征
        print("正在分析风格特征...")
        fingerprint = extractor.extract(content)
        
        chapter = ChapterSample(
            profile_id=profile_id,
            chapter_number=int(chapter_num),
            title=title,
            content=content,  # 存储原文（可选）
            word_count=len(content),
            fingerprint=fingerprint
        )
        
        chapter_id = db.add_chapter(chapter)
        print(f"✅ 章节已添加，ID: {chapter_id}")
        print(f"   字数: {chapter.word_count}")
        print(f"   句长方差: {fingerprint.sentence_variance:.2f}")
        print(f"   短句比例: {fingerprint.short_sentence_ratio:.1%}")
        print(f"   对话占比: {fingerprint.dialogue_ratio:.1%}")


def add_chapters_to_existing(db, extractor, profile_id):
    """为已有风格添加章节"""
    profile = db.get_profile(profile_id)
    print(f"\n为《{profile.title}》添加章节")
    add_chapters_interactive(db, extractor, profile_id)
    
    # 更新指纹
    db.update_profile_fingerprint(profile_id)
    print("\n✅ 风格指纹已更新")


def list_styles():
    """列出所有风格"""
    db = StyleDatabase()
    profiles = db.list_profiles()
    
    if not profiles:
        print("\n文风库为空")
        return
    
    print("\n" + "="*80)
    print(f"{'ID':<5} {'书名':<20} {'题材':<10} {'标签':<20} {'样本数':<8}")
    print("="*80)
    
    for p in profiles:
        tags = ','.join(p.tone_tags[:3])
        print(f"{p.id:<5} {p.title[:18]:<20} {p.genre[:8]:<10} "
              f"{tags[:18]:<20} {p.chapter_count:<8}")
    
    print(f"\n总计: {len(profiles)} 种风格")


def view_style_detail():
    """查看风格详情"""
    db = StyleDatabase()
    
    style_id = input("\n风格ID: ").strip()
    if not style_id.isdigit():
        print("无效ID")
        return
    
    profile = db.get_profile(int(style_id))
    if not profile:
        print("风格不存在")
        return
    
    print("\n" + "="*60)
    print(f"《{profile.title}》风格档案")
    print("="*60)
    print(f"作者: {profile.author}")
    print(f"题材: {profile.genre} / {profile.sub_genre}")
    print(f"标签: {', '.join(profile.tone_tags)}")
    print(f"节奏: {profile.pace}")
    print(f"描述: {profile.description}")
    print(f"\n样本数: {profile.chapter_count}")
    
    fp = profile.fingerprint
    print("\n【风格特征指标】")
    print(f"  平均句长: {fp.avg_sentence_length:.1f}字")
    print(f"  句长方差: {fp.sentence_variance:.2f} (越高变化越大)")
    print(f"  短句比例: {fp.short_sentence_ratio:.1%}")
    print(f"  破碎句比例: {fp.fragment_ratio:.1%}")
    print(f"  对话占比: {fp.dialogue_ratio:.1%}")
    print(f"  口语化密度: {fp.colloquialism_density:.3f}")
    print(f"  感官密度: {fp.sensory_density:.3f}")


def main():
    while True:
        print("\n" + "="*60)
        print("文风库管理系统")
        print("="*60)
        print("1. 添加新风格")
        print("2. 查看所有风格")
        print("3. 查看风格详情")
        print("0. 退出")
        
        choice = input("\n请选择: ").strip()
        
        if choice == '1':
            interactive_add_style()
        elif choice == '2':
            list_styles()
        elif choice == '3':
            view_style_detail()
        elif choice == '0':
            print("再见!")
            break
        else:
            print("无效选择")


if __name__ == '__main__':
    main()
