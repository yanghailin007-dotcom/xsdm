"""
账户设置页面截图脚本
用于检查修复效果
"""

import asyncio
from playwright.async_api import async_playwright

async def screenshot_account_page():
    """截图账户设置页面"""
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("正在访问登录页面...")
            await page.goto('http://localhost:5000/login', wait_until='networkidle')
            
            # 2. 等待登录表单加载 - 使用更通用的选择器
            await page.wait_for_selector('input', timeout=10000)
            
            # 3. 填写登录信息 - 使用 placeholder 定位
            print("正在登录...")
            await page.fill('input[placeholder="请输入用户名"]', 'admin')
            await page.fill('input[placeholder="请输入密码"]', 'yanghailin')
            
            # 4. 点击登录按钮
            await page.click('button:has-text("登录")')
            
            # 5. 等待页面跳转
            await page.wait_for_timeout(3000)
            print(f"当前URL: {page.url}")
            
            # 6. 导航到账户设置页面
            print("正在访问账户设置页面...")
            await page.goto('http://localhost:5000/account', wait_until='networkidle')
            
            # 7. 等待页面内容加载
            await page.wait_for_timeout(2000)
            
            # 8. 截图保存
            screenshot_path = r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_v2.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"截图已保存到: {screenshot_path}")
            
            return True
            
        except Exception as e:
            print(f"发生错误: {e}")
            # 出错时也尝试截图
            try:
                error_path = r'C:\Users\yangh\Documents\GitHub\xsdm\screenshot_error.png'
                await page.screenshot(path=error_path, full_page=True)
                print(f"错误截图已保存到: {error_path}")
            except:
                pass
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(screenshot_account_page())
    exit(0 if success else 1)
