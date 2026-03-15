#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 收集控制台日志
    logs = []
    page.on('console', lambda msg: logs.append(f'{msg.type}: {msg.text}'))
    
    page.goto('http://localhost:5000/login', wait_until='domcontentloaded')
    page.fill('#username', 'yanghailin')
    page.fill('#password', 'yanghailin')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    url = 'http://localhost:5000/phase-two-generation?title=诡异模拟：开局让护士姐姐试口红'
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    
    print('Console logs:')
    for log in logs:
        print(log)
    
    browser.close()
