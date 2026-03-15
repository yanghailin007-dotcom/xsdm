#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 收集网络请求
    network_logs = []
    page.on('response', lambda response: 
        network_logs.append(f"{response.status} {response.url}") if '/phase-one/products/' in response.url else None
    )
    
    # 收集控制台日志
    console_logs = []
    page.on('console', lambda msg: console_logs.append(f'{msg.type}: {msg.text}'))
    
    page.goto('http://localhost:5000/login', wait_until='domcontentloaded')
    page.fill('#username', 'yanghailin')
    page.fill('#password', 'yanghailin')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    url = 'http://localhost:5000/phase-two-generation?title=诡异模拟：开局让护士姐姐试口红'
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    
    print('Network logs:')
    for log in network_logs:
        print(log)
    
    print('\nConsole logs:')
    for log in console_logs:
        print(log)
    
    # 尝试直接调用API
    print('\nDirect API call:')
    try:
        response = page.evaluate("""
            async () => {
                const r = await fetch('/phase-one/products/%E8%AF%A1%E5%BC%82%E6%A8%A1%E6%8B%9F%EF%BC%9A%E5%BC%80%E5%B1%80%E8%AE%A9%E6%8A%A4%E5%A3%AB%E5%A7%90%E5%A7%90%E8%AF%95%E5%8F%A3%E7%BA%A2');
                return await r.json();
            }
        """)
        print(json.dumps(response, indent=2, ensure_ascii=False)[:500])
    except Exception as e:
        print(f'API call failed: {e}')
    
    browser.close()
