#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time

def main():
    screenshot_path = r"C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_result.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            print("1. 访问登录页面...")
            page.goto("http://localhost:5000/login", wait_until="networkidle")
            time.sleep(1)
            
            # 检查页面上的输入框
            html = page.content()
            print(f"页面内容长度: {len(html)}")
            
            # 尝试不同的选择器
            username_selectors = ['input[name="username"]', 'input#username', 'input[type="text"]', '#username']
            password_selectors = ['input[name="password"]', 'input#password', 'input[type="password"]', '#password']
            
            username_filled = False
            for sel in username_selectors:
                try:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, 'admin')
                        print(f"用户名已填写使用: {sel}")
                        username_filled = True
                        break
                except Exception as e:
                    pass
            
            password_filled = False
            for sel in password_selectors:
                try:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, 'yanghailin')
                        print(f"密码已填写使用: {sel}")
                        password_filled = True
                        break
                except Exception as e:
                    pass
            
            if not username_filled or not password_filled:
                print("未找到输入框，保存页面源码调试")
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(html)
            
            # 点击登录按钮
            button_selectors = ['button[type="submit"]', 'button:has-text("登录")', '.login-btn', 'input[type="submit"]']
            for sel in button_selectors:
                try:
                    if page.locator(sel).count() > 0:
                        page.click(sel)
                        print(f"点击登录按钮: {sel}")
                        break
                except Exception as e:
                    pass
            
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print(f"登录后页面: {page.url}")
            
            print("2. 导航到账户设置页面...")
            page.goto("http://localhost:5000/account?v=final", wait_until="networkidle")
            time.sleep(2)
            print(f"当前页面: {page.url}")
            
            print("3. 截图保存...")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"截图已保存到: {screenshot_path}")
            
            # 分析页面元素
            print("\n=== 页面布局分析 ===")
            
            # 检查是否有 grid 布局
            grid_count = page.locator("[class*='grid']").count()
            col_count = page.locator("[class*='col-']").count()
            row_count = page.locator("[class*='row']").count()
            
            print(f"grid 类元素: {grid_count}")
            print(f"col- 类元素: {col_count}")
            print(f"row 类元素: {row_count}")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            try:
                page.screenshot(path=screenshot_path.replace(".png", "_error.png"), full_page=True)
            except:
                pass
        finally:
            browser.close()

if __name__ == "__main__":
    main()
