#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace special characters
    content = content.replace('\u2192', '->')  # →
    content = content.replace('\u201c', '"')  # "
    content = content.replace('\u201d', '"')  # "
    content = content.replace('\u2018', "'")  # '
    content = content.replace('\u2019', "'")  # '
    
    with open('web/services/market_driven/chapter_conversation_generator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed special characters')

if __name__ == '__main__':
    main()
