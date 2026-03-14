#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Playwright 截图账户设置页面
"""

from playwright.sync_api import sync_playwright
import time

def main():
    screenshot_path = r"C:\Users\yangh\Documents\GitHub\xsdm\screenshot_account_result.png"
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)  # headless=False 以便观察
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            print("1. 访问登录页面...")
            page.goto("http://localhost:5000/login", wait_until="networkidle")
            time.sleep(1)
            
            print("2. 填写登录信息...")
            # 填写用户名和密码
            page.fill('input[name="username"]', 'admin')
            page.fill('input[name="password"]', 'yanghailin')
            
            print("3. 点击登录按钮...")
            page.click('button[type="submit"]')
            
            # 等待登录完成，跳转到首页
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print(f"   当前页面: {page.url}")
            
            print("4. 导航到账户设置页面...")
            page.goto("http://localhost:5000/account?v=final", wait_until="networkidle")
            time.sleep(2)
            print(f"   当前页面: {page.url}")
            
            print("5. 等待页面完全加载...")
            # 等待页面关键元素加载
            page.wait_for_selector(".account-container, .account-page, main, body", state="visible", timeout=10000)
            time.sleep(2)
            
            print("6. 截图保存...")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"   截图已保存到: {screenshot_path}")
            
            # 获取页面基本信息
            title = page.title()
            print(f"\n页面标题: {title}")
            
            # 检查关键元素
            print("\n=== 页面元素检查结果 ===")
            
            # 检查基本信息卡片布局
            info_cards = page.locator(".info-card, .basic-info-card, [class*='info']").count()
            print(f"找到 {info_cards} 个信息卡片元素")
            
            # 检查表单布局
            forms = page.locator("form").count()
            print(f"找到 {forms} 个表单")
            
            # 检查是否有 grid 或两列布局
            grid_elements = page.locator("[class*='grid'], [class*='col-'], [class*='two-column']").count()
            print(f"找到 {grid_elements} 个可能的两列/grid布局元素")
            
            print("\n截图成功完成！")
            
        except Exception as e:
            print(f"发生错误: {e}")
            # 错误时也尝试截图
            try:
                page.screenshot(path=screenshot_path.replace(".png", "_error.png"), full_page=True)
                print(f"错误截图已保存")
            except:
                pass
        finally:
            browser.close()

if __name__ == "__main__":
    main()
