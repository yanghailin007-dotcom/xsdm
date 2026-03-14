import asyncio
from playwright.async_api import async_playwright

async def screenshot_account():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            # 1. 访问登录页面
            print("访问登录页面...")
            await page.goto('http://localhost:5000/login')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            # 2. 填写登录表单 - 使用ID选择器
            print("填写登录信息...")
            await page.fill('#username', 'admin')
            await page.fill('#password', 'yanghailin')
            
            # 3. 点击登录按钮
            print("点击登录...")
            await page.click('#loginBtn')
            
            # 等待登录完成并跳转
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 4. 导航到账户设置页面
            print("导航到账户设置页面...")
            await page.goto('http://localhost:5000/account')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 5. 截图
            print("正在截图...")
            screenshot_path = 'C:\\Users\\yangh\\Documents\\GitHub\\xsdm\\screenshot_account_fixed.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"截图已保存到: {screenshot_path}")
            
            return True
            
        except Exception as e:
            print(f"错误: {e}")
            # 错误时也要截图
            try:
                await page.screenshot(path='C:\\Users\\yangh\\Documents\\GitHub\\xsdm\\screenshot_error.png')
                print("错误截图已保存到 screenshot_error.png")
            except:
                pass
            return False
            
        finally:
            await browser.close()

if __name__ == '__main__':
    result = asyncio.run(screenshot_account())
    print(f"截图结果: {'成功' if result else '失败'}")
