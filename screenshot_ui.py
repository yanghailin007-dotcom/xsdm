#!/usr/bin/env python3
"""
UI整改效果截图脚本
"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()
        
        print("[1/3] Accessing login page...")
        await page.goto('http://127.0.0.1:5000/login')
        await asyncio.sleep(3)
        
        print("[2/3] Filling login form...")
        # Use placeholder to find inputs
        await page.fill('input[placeholder="请输入用户名"]', 'yanghailin')
        await page.fill('input[placeholder="请输入密码"]', 'yanghailin')
        
        # Click login button
        await page.click('button:has-text("登录")')
        await asyncio.sleep(3)
        
        print("[3/3] Accessing phase two generation page...")
        # Access the page without waiting for networkidle
        await page.goto('http://127.0.0.1:5000/phase-two-generation')
        await asyncio.sleep(5)
        
        print("Taking screenshot...")
        # Take screenshot
        await page.screenshot(path='screenshots/ui_redesign_v1.png', full_page=True)
        print("[OK] Screenshot saved to screenshots/ui_redesign_v1.png")
        
        # Close browser
        await browser.close()
        print("[Done] Complete!")

if __name__ == '__main__':
    asyncio.run(main())
