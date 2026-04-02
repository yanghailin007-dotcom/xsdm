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
        print(f'Text: {repr(e.text)}')
        print(f'Offset: {e.offset}')
        
        # Print the actual line
        lines = source.split('\n')
        if e.lineno <= len(lines):
            print(f'\nActual line {e.lineno}: {repr(lines[e.lineno-1])}')
            
        # Check if there's a try block without except
        # by looking at the structure
        print('\n--- Checking try/except structure ---')
        for i, line in enumerate(lines[836:920], 837):
            if line.strip().startswith(('try:', 'except')):
                print(f'{i}: {line.rstrip()}')

if __name__ == '__main__':
    main()
