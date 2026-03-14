import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # 1. 访问登录页面
        print("访问登录页面...")
        await page.goto('http://localhost:5000/login', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        # 2. 填写登录信息
        print("填写登录信息...")
        await page.fill('#username', 'yanghailin')
        await page.fill('#password', 'yanghailin')
        
        # 3. 点击登录并等待跳转
        print("点击登录...")
        await page.click('#login-btn')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        current_url = page.url
        print(f"当前URL: {current_url}")
        
        # 如果还在登录页，说明登录失败
        if '/login' in current_url:
            print("登录可能失败，截图查看...")
            await page.screenshot(path='screenshot_login_failed.png')
        else:
            print("登录成功！")
            await page.screenshot(path='screenshot_after_login.png')
            
            # 4. 访问第二阶段页面
            print("访问第二阶段页面...")
            await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle')
            await page.wait_for_timeout(5000)
            await page.screenshot(path='screenshot_phase2_full.png', full_page=True)
            print("已截图第二阶段页面")
            
            # 5. 滚动到产物卡片区域
            print("滚动到产物卡片...")
            await page.evaluate('window.scrollTo(0, 600)')
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshot_products.png', full_page=False)
            print("已截图产物卡片")
        
        print("\n截图完成！")
        await browser.close()

asyncio.run(main())
