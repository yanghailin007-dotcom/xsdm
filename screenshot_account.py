#!/usr/bin/env python3
"""使用Playwright截图检查账户设置页面"""

import asyncio
from playwright.async_api import async_playwright

async def capture_account_page():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("访问登录页面...")
            await page.goto('http://localhost:5000/login', wait_until='networkidle')
            await page.wait_for_timeout(1000)
            
            # 2. 填写登录表单
            print("填写登录信息...")
            await page.fill('input[name="username"], input#username, input[type="text"]', 'admin')
            await page.fill('input[name="password"], input#password, input[type="password"]', 'yanghailin')
            
            # 3. 点击登录按钮
            print("点击登录...")
            await page.click('button[type="submit"], input[type="submit"], button:has-text("登录")')
            
            # 等待登录完成并跳转
            await page.wait_for_timeout(2000)
            
            # 4. 导航到账户设置页面
            print("导航到账户设置页面...")
            await page.goto('http://localhost:5000/account', wait_until='networkidle')
            await page.wait_for_timeout(1500)
            
            # 5. 截图保存
            screenshot_path = r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_v3.png'
            print(f"正在截图保存到: {screenshot_path}")
            await page.screenshot(path=screenshot_path, full_page=True)
            print("截图成功！")
            
            # 检查页面元素
            print("\n=== 页面检查结果 ===")
            
            # 检查基本信息卡片
            basic_info = await page.locator('.info-card, .basic-info-card, [class*="info"]').count()
            print(f"- 信息卡片数量: {basic_info}")
            
            # 检查表单元素
            form_inputs = await page.locator('input[type="password"]').count()
            print(f"- 密码输入框数量: {form_inputs}")
            
            # 检查标题
            title = await page.title()
            print(f"- 页面标题: {title}")
            
            return True
            
        except Exception as e:
            print(f"错误: {e}")
            # 出错时也截图
            try:
                screenshot_path = r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_v3.png'
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"已保存错误截图到: {screenshot_path}")
            except:
                pass
            return False
            
        finally:
            await browser.close()

if __name__ == '__main__':
    result = asyncio.run(capture_account_page())
    exit(0 if result else 1)
