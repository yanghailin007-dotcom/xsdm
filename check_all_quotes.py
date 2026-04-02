#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Count all triple quotes
    count = 0
    for i, line in enumerate(lines):
        if '"""' in line:
            count += 1
            if count % 2 == 1:  # Opening
                print(f'{i+1}: OPEN  {repr(line[:60])}')
            else:  # Closing
                print(f'{i+1}: CLOSE {repr(line[:60])}')
    
    print(f'\nTotal triple quotes: {count}')
    if count % 2 != 0:
        print('WARNING: Odd number of triple quotes!')

if __name__ == '__main__':
    main()
