#!/usr/bin/env python3
"""
使用Playwright截图账户设置页面，强制刷新浏览器缓存
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("Step 1: Visit login page...")
            await page.goto("http://localhost:5000/login", wait_until="networkidle")
            await asyncio.sleep(2)
            
            print("Step 2: Fill login credentials...")
            # 使用更通用的选择器
            await page.fill("input#username", "admin")
            await page.fill("input#password", "yanghailin")
            
            print("Step 3: Click login button...")
            await page.click("button[type='submit']")
            
            # 等待登录完成
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            print("Step 4: Navigate to account page with cache buster...")
            await page.goto("http://localhost:5000/account?v=999", wait_until="networkidle")
            
            print("Step 5: Wait for page to fully load...")
            await asyncio.sleep(3)
            
            # 等待关键元素
            try:
                await page.wait_for_selector("body", timeout=5000)
                print("   - Body loaded")
            except:
                print("   - Warning: body timeout")
            
            print("Step 6: Take screenshot...")
            screenshot_path = r"C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_cache.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   Screenshot saved: {screenshot_path}")
            
            # 获取页面信息
            title = await page.title()
            url = page.url
            print(f"\nPage Info:")
            print(f"   - Title: {title}")
            print(f"   - URL: {url}")
            
            # 检查页面内容
            body_text = await page.inner_text("body")
            content_length = len(body_text)
            print(f"   - Content length: {content_length} chars")
            
            # 检查错误
            error_count = await page.eval_on_selector_all(".error, .alert-error, .text-danger", "els => els.length")
            if error_count > 0:
                print(f"   - Warning: {error_count} error elements found")
            else:
                print("   - No error elements found")
                
            print("\nTask completed successfully!")
            
        except Exception as e:
            print(f"\nError: {e}")
            # Error screenshot
            try:
                error_path = r"C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_error.png"
                await page.screenshot(path=error_path, full_page=True)
                print(f"   Error screenshot saved: {error_path}")
            except:
                pass
        finally:
            await asyncio.sleep(1)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
