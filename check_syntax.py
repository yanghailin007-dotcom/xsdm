#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import sys

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        ast.parse(source)
        print('Syntax OK!')
    except SyntaxError as e:
        print(f'Syntax error at line {e.lineno}: {e.msg}')
        print(f'Text: {e.text}')
        print(f'Offset: {e.offset}')
        
        # Print surrounding lines
        lines = source.split('\n')
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        print(f'\nContext (lines {start+1} to {end}):')
        for i in range(start, end):
            marker = '>>> ' if i == e.lineno - 1 else '    '
            print(f'{marker}{i+1}: {lines[i]}')

if __name__ == '__main__':
    main()
