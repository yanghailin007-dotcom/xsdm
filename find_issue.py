#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find all triple quotes and track nesting
    stack = []
    issues = []
    
    for i, line in enumerate(lines):
        if '"""' in line:
            # Count occurrences (could be both open and close on same line)
            count = line.count('"""')
            for _ in range(count):
                if len(stack) == 0:
                    stack.append(i+1)
                else:
                    # Check if this is a closing quote
                    start_line = stack[-1]
                    # Simple check: if it's a continuation, pop
                    if i+1 != start_line:
                        stack.pop()
                    else:
                        # Same line, treat as open+close
                        stack.pop()
                        stack.append(i+1)
                        
    if stack:
        print(f'Unclosed triple quotes at lines: {stack}')
    else:
        print('All triple quotes are balanced')

if __name__ == '__main__':
    main()
