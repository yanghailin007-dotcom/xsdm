#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合修复 chapter_conversation_generator.py 中的所有编码问题
"""

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'rb') as f:
        content = f.read()

    # 1. Fix standalone \r (not part of \r\n)
    content = content.replace(b'\r\n', b'<<CRLF>>')
    content = content.replace(b'\r', b'\n')
    content = content.replace(b'<<CRLF>>', b'\r\n')

    # Decode as UTF-8 for text replacements
    text = content.decode('utf-8')

    # 2. Replace Chinese punctuation with English equivalents
    text = text.replace('（', '(')
    text = text.replace('）', ')')
    text = text.replace('：', ':')
    text = text.replace('，', ',')
    text = text.replace('。', '.')
    text = text.replace('；', ';')
    text = text.replace('！', '!')
    text = text.replace('？', '?')
    text = text.replace('、', ',')
    text = text.replace('"', '"')
    text = text.replace('"', '"')
    text = text.replace(''', "'")
    text = text.replace(''', "'")
    text = text.replace('【', '[')
    text = text.replace('】', ']')
    text = text.replace('《', '<')
    text = text.replace('》', '>')
    text = text.replace('·', '-')
    text = text.replace('……', '...')
    text = text.replace('—', '-')
    text = text.replace('～', '~')

    # 3. Remove fire emoji
    text = text.replace('\U0001f525', '')

    # 4. Replace special characters
    text = text.replace('\u2192', '->')  # →
    text = text.replace('\u201c', '"')  # "
    text = text.replace('\u201d', '"')  # "
    text = text.replace('\u2018', "'")  # '
    text = text.replace('\u2019', "'")  # '

    with open('web/services/market_driven/chapter_conversation_generator.py', 'w', encoding='utf-8') as f:
        f.write(text)

    print('All fixes applied!')

if __name__ == '__main__':
    main()
