#!/usr/bin/env python3
"""
使用 Playwright 登录并查看小说页面
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("访问登录页面...")
            await page.goto('http://localhost:5000/login', wait_until='networkidle')
            await page.screenshot(path='screenshots/01_login_page.png', full_page=True)
            
            # 2. 填写登录表单
            print("填写登录表单...")
            await page.fill('input[name="username"]', 'yanghailin')
            await page.fill('input[name="password"]', 'yanghailin')
            await page.screenshot(path='screenshots/02_login_filled.png', full_page=True)
            
            # 3. 点击登录按钮
            print("点击登录...")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # 等待页面加载完成
            await page.screenshot(path='screenshots/03_after_login.png', full_page=True)
            
            # 4. 访问小说页面
            novel_url = 'http://localhost:5000/novel?title=%E8%AF%A1%E5%BC%82%E7%9B%B4%E6%92%AD%EF%BC%9A%E6%88%91%E6%8A%8A%E6%81%90%E6%80%96%E5%89%AF%E6%9C%AC%E7%8E%A9%E6%88%90%E4%BA%86%E5%85%BB%E6%88%90'
            print(f"访问小说页面: {novel_url}")
            await page.goto(novel_url, wait_until='networkidle')
            await asyncio.sleep(3)  # 等待内容加载
            
            # 5. 截图 - 完整页面
            await page.screenshot(path='screenshots/04_novel_page_full.png', full_page=True)
            print("已保存完整页面截图: screenshots/04_novel_page_full.png")
            
            # 6. 截图 - 首屏
            await page.screenshot(path='screenshots/05_novel_page_viewport.png')
            print("已保存首屏截图: screenshots/05_novel_page_viewport.png")
            
            # 7. 获取页面信息
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 获取页面结构信息
            html_structure = await page.evaluate('''() => {
                const body = document.body;
                return {
                    bodyClasses: body.className,
                    hasV2Class: body.classList.contains('v2-body'),
                    mainContent: document.querySelector('main') ? document.querySelector('main').className : 'no main',
                    navbarExists: !!document.querySelector('.v2-navbar'),
                    footerExists: !!document.querySelector('.v2-footer'),
                    containerExists: !!document.querySelector('.container, .v2-container')
                };
            }''')
            print(f"页面结构: {html_structure}")
            
        except Exception as e:
            print(f"错误: {e}")
            await page.screenshot(path='screenshots/error.png', full_page=True)
        
        finally:
            await browser.close()
            print("浏览器已关闭")

if __name__ == '__main__':
    asyncio.run(main())
