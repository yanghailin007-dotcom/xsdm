#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'rb') as f:
        content = f.read()
        
    # Check line endings
    if b'\r\n' in content:
        print('File uses CRLF line endings')
    elif b'\n' in content:
        print('File uses LF line endings')

    # Check for null bytes
    if b'\x00' in content:
        print('File contains null bytes')

    # Count triple quotes
    triple_quotes = content.count(b'"""')
    print(f'Number of triple quotes: {triple_quotes}')
    
    # Check line 1723
    lines = content.split(b'\n')
    if len(lines) > 1722:
        print(f'Line 1723: {lines[1722]}')
    if len(lines) > 1744:
        print(f'Line 1745: {lines[1744]}')
    print(f'Total lines: {len(lines)}')

if __name__ == '__main__':
    main()
