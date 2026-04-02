#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print('Lines 1664-1702 (checking for triple quotes):')
    for i in range(1663, 1702):
        line = lines[i]
        if '"""' in line:
            count = line.count('"""')
            print(f'{i+1}: count={count}, line={repr(line)}')

if __name__ == '__main__':
    main()
