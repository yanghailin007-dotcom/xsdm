#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    # Read file with CRLF
    with open('web/services/market_driven/chapter_conversation_generator.py', 'rb') as f:
        content = f.read()
    
    # Convert CRLF to LF
    content = content.replace(b'\r\n', b'\n')
    
    # Write back
    with open('web/services/market_driven/chapter_conversation_generator.py', 'wb') as f:
        f.write(content)
    
    print('Converted CRLF to LF')

if __name__ == '__main__':
    main()
