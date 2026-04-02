#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Trace all triple quotes up to line 1723
    stack = []
    for i in range(1723):
        line = lines[i]
        if '"""' in line:
            count = line.count('"""')
            for _ in range(count):
                if len(stack) == 0:
                    stack.append(i+1)
                    print(f'{i+1}: OPEN (stack: {stack})')
                else:
                    start = stack.pop()
                    print(f'{i+1}: CLOSE (opened at {start}, stack: {stack})')
    
    print(f'\nFinal stack: {stack}')

if __name__ == '__main__':
    main()
