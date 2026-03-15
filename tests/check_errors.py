#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    # 收集控制台日志
    console_logs = []
    page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))
    
    # 收集页面错误
    page_errors = []
    page.on('pageerror', lambda err: page_errors.append(str(err)))
    
    # 登录
    page.goto('http://localhost:5000/login', wait_until='domcontentloaded')
    page.fill('#username', 'yanghailin')
    page.fill('#password', 'yanghailin')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    # 访问第二阶段页面
    url = 'http://localhost:5000/phase-two-generation?title=诡异模拟：开局让护士姐姐试口红'
    page.goto(url, wait_until='domcontentloaded')
    
    # 等待几秒让JavaScript执行
    page.wait_for_timeout(5000)
    
    print('=== Console Logs ===')
    for log in console_logs:
        print(log)
    
    print('\n=== Page Errors ===')
    for err in page_errors:
        print(err)
    
    # 检查产物状态
    print('\n=== Product Status ===')
    cards = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
    for card in cards:
        text_el = page.query_selector(f'#{card}-status-text')
        if text_el:
            text = text_el.text_content()
            print(f'{card}: {text}')
        else:
            print(f'{card}: ELEMENT NOT FOUND')
    
    browser.close()
