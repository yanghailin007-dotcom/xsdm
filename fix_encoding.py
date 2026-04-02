#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 chapter_conversation_generator.py 中的中文标点符号
"""

def main():
    # Read file
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all Chinese punctuation with English equivalents
    # 中文标点 -> 英文标点
    content = content.replace('（', '(')
    content = content.replace('）', ')')
    content = content.replace('：', ':')
    content = content.replace('，', ',')
    content = content.replace('。', '.')
    content = content.replace('；', ';')
    content = content.replace('！', '!')
    content = content.replace('？', '?')
    content = content.replace('、', ',')
    content = content.replace('"', '"')
    content = content.replace('"', '"')
    content = content.replace(''', "'")
    content = content.replace(''', "'")
    content = content.replace('【', '[')
    content = content.replace('】', ']')
    content = content.replace('《', '<')
    content = content.replace('》', '>')
    content = content.replace('·', '-')
    content = content.replace('……', '...')
    content = content.replace('—', '-')
    content = content.replace('～', '~')
    
    # Write back
    with open('web/services/market_driven/chapter_conversation_generator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('Done! Fixed all Chinese punctuation.')

if __name__ == '__main__':
    main()
