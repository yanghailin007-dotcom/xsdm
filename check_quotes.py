#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Count triple quotes in lines 1702-1723
    count = 0
    for i in range(1701, 1723):
        if '"""' in lines[i]:
            count += 1
            print(f'{i+1}: {repr(lines[i][:60])}')
    print(f'Total triple quotes: {count}')

if __name__ == '__main__':
    main()
