import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 等待页面加载
        await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle')
        
        # 登录
        await page.fill('input[name="username"]', 'yanghailin')
        await page.fill('input[name="password"]', 'yanghailin')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # 截图 - 产物卡片区域
        await page.screenshot(path='screenshot_factions.png', full_page=False)
        print('截图已保存: screenshot_factions.png')
        
        await browser.close()

asyncio.run(main())
