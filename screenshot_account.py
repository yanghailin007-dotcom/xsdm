# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright

async def capture_account_page():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("访问登录页面...")
            await page.goto('http://localhost:5000/login', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(1)
            
            # 2. 填写登录信息 - 使用多种选择器尝试
            print("填写登录信息...")
            
            # 尝试多种方式填写用户名
            try:
                await page.fill('input#username', 'admin', timeout=5000)
            except:
                try:
                    await page.fill('input[name="username"]', 'admin', timeout=5000)
                except:
                    await page.fill('input[type="text"]', 'admin', timeout=5000)
            
            # 尝试多种方式填写密码
            try:
                await page.fill('input#password', 'yanghailin', timeout=5000)
            except:
                try:
                    await page.fill('input[name="password"]', 'yanghailin', timeout=5000)
                except:
                    await page.fill('input[type="password"]', 'yanghailin', timeout=5000)
            
            # 3. 点击登录按钮
            print("点击登录...")
            try:
                await page.click('button[type="submit"]', timeout=5000)
            except:
                await page.click('button:has-text("登录")', timeout=5000)
            
            # 等待登录完成
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 4. 导航到账户设置页面
            print("导航到账户设置页面...")
            await page.goto('http://localhost:5000/account', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(2)
            
            # 5. 截图
            screenshot_path = r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_final.png'
            print(f"截图保存到: {screenshot_path}")
            await page.screenshot(path=screenshot_path, full_page=True)
            
            print("截图完成!")
            
            # 获取页面信息用于验证
            cards = await page.query_selector_all('.card')
            card_headers = await page.query_selector_all('.card-header')
            card_bodies = await page.query_selector_all('.card-body')
            
            print(f"\n页面统计信息:")
            print(f"- 卡片数量 (.card): {len(cards)}")
            print(f"- 卡片头部数量 (.card-header): {len(card_headers)}")
            print(f"- 卡片内容数量 (.card-body): {len(card_bodies)}")
            
            # 获取页面HTML用于分析
            html_content = await page.content()
            has_vertical_layout = 'flex-col' in html_content or 'flex-direction: column' in html_content
            print(f"- 是否使用垂直布局: {has_vertical_layout}")
            
            return True
            
        except Exception as e:
            print(f"错误: {e}")
            # 出错时也截图
            try:
                await page.screenshot(path=r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_error.png')
                print("错误截图已保存")
            except:
                pass
            return False
        finally:
            await browser.close()

if __name__ == '__main__':
    result = asyncio.run(capture_account_page())
    exit(0 if result else 1)
