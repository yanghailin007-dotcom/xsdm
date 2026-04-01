# -*- coding: utf-8 -*-
import json
import os
import sys
import re

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

base_path = "小说项目/yanghailin/国运：扮演瞎子，队友白月魁/chapters"

# 读取前6章
chapters = []
for i in range(1, 7):
    fname = os.path.join(base_path, f'chapter_{i:03d}.json')
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as f:
            ch = json.load(f)
            content = ch.get('content', '')
            chapters.append({
                'num': i,
                'title': ch.get('title', 'N/A'),
                'word_count': len(content),
                'content': content
            })

print("=" * 60)
print("章节质量深度分析")
print("=" * 60)

# 1. 基础数据
print("\n【一、章节基础数据】")
print("-" * 40)
for ch in chapters:
    print(f"C{ch['num']}: {ch['title'][:40]}...")
    print(f"    字数: {ch['word_count']}")

# 2. 番茄算法检查
print("\n【二、番茄算法合规性检查】")
print("-" * 40)

def check_chapter(content, num):
    issues = []
    
    # 段落长度检查
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    long_paras = [p for p in paragraphs if len(p) > 100]
    if len(long_paras) > len(paragraphs) * 0.3:
        issues.append(f"长段落过多({len(long_paras)}/{len(paragraphs)})")
    
    # 对话比例
    dialogue = re.findall(r'["""][^"""]+["""]', content)
    dialogue_len = sum(len(d) for d in dialogue)
    dialogue_ratio = dialogue_len / len(content) if content else 0
    if dialogue_ratio < 0.3:
        issues.append(f"对话比例偏低({dialogue_ratio:.1%})")
    
    # 结尾钩子检查
    last_100 = content[-100:] if len(content) >= 100 else content
    hook_keywords = ['?', '！', '...', '……', '但是', '然而', '突然', '没想到', '危机', '危险']
    has_hook = any(k in last_100 for k in hook_keywords)
    if not has_hook:
        issues.append("结尾缺乏钩子")
    
    # 爽点关键词
    shuang_keywords = ['震惊', '不可能', '秒杀', '碾压', '逆天', '恐怖', '妖孽', '怪物']
    shuang_count = sum(content.count(k) for k in shuang_keywords)
    shuang_density = shuang_count / (len(content) / 1000)
    
    return {
        'paragraphs': len(paragraphs),
        'long_paras': len(long_paras),
        'dialogue_ratio': dialogue_ratio,
        'shuang_density': shuang_density,
        'issues': issues,
        'has_hook': has_hook
    }

for ch in chapters:
    result = check_chapter(ch['content'], ch['num'])
    print(f"\n第{ch['num']}章:")
    print(f"  段落数: {result['paragraphs']}, 长段落: {result['long_paras']}")
    print(f"  对话比例: {result['dialogue_ratio']:.1%}")
    print(f"  爽点密度: {result['shuang_density']:.1f}/千字")
    print(f"  结尾钩子: {'有' if result['has_hook'] else '无'}")
    if result['issues']:
        print(f"  问题: {', '.join(result['issues'])}")

# 3. 情绪词分析
print("\n【三、情绪词频分析】")
print("-" * 40)

emotion_words = {
    '震惊类': ['震惊', '骇然', '不可思议', '目瞪口呆', '哗然'],
    '恐惧类': ['恐惧', '害怕', '颤栗', '惊悚', '恐怖'],
    '兴奋类': ['激动', '兴奋', '热血沸腾', '期待', '振奋'],
    '压抑类': ['压抑', '绝望', '沉重', '灰暗', '窒息'],
    '爽感类': ['爽', '畅快', '解气', '打脸', '碾压']
}

for ch in chapters:
    print(f"\n第{ch['num']}章:")
    content = ch['content']
    for cat, words in emotion_words.items():
        count = sum(content.count(w) for w in words)
        if count > 0:
            print(f"  {cat}: {count}次")
