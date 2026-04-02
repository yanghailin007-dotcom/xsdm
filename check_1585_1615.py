#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print('Lines 1585-1615:')
    for i in range(1584, 1615):
        if '"""' in lines[i]:
            print(f'{i+1}: {repr(lines[i])}')

if __name__ == '__main__':
    main()
