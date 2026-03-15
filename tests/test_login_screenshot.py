#!/usr/bin/env python3
"""登录并截图验证UI数据显示"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("Step 1: Visiting login page...")
            await page.goto('http://localhost:5000/login', wait_until='networkidle')
            await page.wait_for_selector('#username', timeout=10000)
            await page.screenshot(path='screenshots/01_login.png')
            print("[OK] Screenshot 01_login.png saved")
            
            # 2. 填写登录信息
            print("Step 2: Filling login info...")
            await page.fill('#username', 'yanghailin')
            await page.fill('#password', 'yanghailin')
            await page.screenshot(path='screenshots/02_filled.png')
            print("[OK] Screenshot 02_filled.png saved")
            
            # 3. 点击登录按钮
            print("Step 3: Clicking login button...")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            await page.screenshot(path='screenshots/03_after_login.png')
            print("[OK] Screenshot 03_after_login.png saved")
            
            # 4. 访问第二阶段页面
            print("Step 4: Visiting phase 2 page...")
            url = 'http://localhost:5000/phase-two-generation?title=%E8%AF%A1%E5%BC%82%E6%A8%A1%E6%8B%9F%EF%BC%9A%E5%BC%80%E5%B1%80%E8%AE%A9%E6%8A%A4%E5%A3%AB%E5%A7%90%E5%A7%90%E8%AF%95%E5%8F%A3%E7%BA%A2'
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(5)
            await page.screenshot(path='screenshots/04_phase2_full.png', full_page=True)
            print("[OK] Screenshot 04_phase2_full.png saved")
            
            # 5. 检查产物状态
            print("Step 5: Checking product status...")
            cards = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
            for card in cards:
                dot = await page.query_selector(f'#{card}-status-dot')
                text = await page.query_selector(f'#{card}-status-text')
                if dot and text:
                    dot_class = await dot.get_attribute('class')
                    text_content = await text.text_content()
                    print(f"  {card}: {text_content} ({dot_class})")
                else:
                    print(f"  {card}: NOT FOUND")
            
            # 6. 截图产物区域
            product_grid = await page.query_selector('#products-grid')
            if product_grid:
                await product_grid.screenshot(path='screenshots/05_products_grid.png')
                print("[OK] Screenshot 05_products_grid.png saved")
            
            print("\n[OK] All tests completed!")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='screenshots/error.png')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
