#!/usr/bin/env python3
"""快速截图第二阶段页面"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 登录
            print("Logging in...")
            await page.goto('http://localhost:5000/login', wait_until='domcontentloaded')
            await page.fill('#username', 'yanghailin')
            await page.fill('#password', 'yanghailin')
            await page.click('button[type="submit"]')
            await asyncio.sleep(3)
            
            # 2. 访问第二阶段页面（不等待networkidle，避免超时）
            print("Loading phase 2 page...")
            url = 'http://localhost:5000/phase-two-generation?title=%E8%AF%A1%E5%BC%82%E6%A8%A1%E6%8B%9F%EF%BC%9A%E5%BC%80%E5%B1%80%E8%AE%A9%E6%8A%A4%E5%A3%AB%E5%A7%90%E5%A7%90%E8%AF%95%E5%8F%A3%E7%BA%A2'
            await page.goto(url, wait_until='domcontentloaded')
            await asyncio.sleep(5)
            await page.screenshot(path='screenshots/phase2_result.png', full_page=True)
            print("[OK] Screenshot saved: screenshots/phase2_result.png")
            
            # 3. 检查产物状态
            print("Checking product status...")
            cards = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
            for card in cards:
                dot = await page.query_selector(f'#{card}-status-dot')
                text = await page.query_selector(f'#{card}-status-text')
                if dot and text:
                    dot_class = await dot.get_attribute('class') or 'N/A'
                    text_content = await text.text_content() or 'N/A'
                    print(f"  {card}: {text_content.strip()}")
                else:
                    print(f"  {card}: ELEMENT NOT FOUND")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path='screenshots/error.png')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
