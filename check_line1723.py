#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    with open('web/services/market_driven/chapter_conversation_generator.py', 'rb') as f:
        lines = f.readlines()
    print(f'Line 1722: {repr(lines[1721])}')
    print(f'Line 1723: {repr(lines[1722])}')
    print(f'Line 1724: {repr(lines[1723])}')
    # Check if line 1723 has correct content
    if b'"""' in lines[1722]:
        print('Line 1723 contains triple quotes')
    else:
        print('Line 1723 does NOT contain triple quotes')

if __name__ == '__main__':
    main()
