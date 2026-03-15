#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    # 登录
    print("Logging in...")
    page.goto('http://localhost:5000/login', wait_until='domcontentloaded')
    page.fill('#username', 'yanghailin')
    page.fill('#password', 'yanghailin')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    # 访问第二阶段页面
    print("Loading phase 2...")
    url = 'http://localhost:5000/phase-two-generation?title=诡异模拟：开局让护士姐姐试口红'
    page.goto(url, wait_until='domcontentloaded')
    
    # 等待JavaScript执行
    page.wait_for_timeout(5000)
    
    # 截图
    page.screenshot(path='screenshots/final_test.png', full_page=True)
    print("Screenshot saved: screenshots/final_test.png")
    
    # 获取页面HTML看看元素是否存在
    html = page.content()
    if 'worldview-status-dot' in html:
        print("✅ worldview-status-dot FOUND in HTML")
    else:
        print("❌ worldview-status-dot NOT FOUND in HTML")
    
    # 尝试用JavaScript获取元素
    result = page.evaluate("""
        () => {
            const el = document.getElementById('worldview-status-dot');
            return el ? 'Found: ' + el.className : 'Not found';
        }
    """)
    print(f"JavaScript check: {result}")
    
    browser.close()
