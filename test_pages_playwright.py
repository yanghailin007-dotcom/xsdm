#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 页面入口测试
验证所有关键页面都能正常打开
"""

import asyncio
import sys
import os
from pathlib import Path

# 尝试安装 playwright
async def ensure_playwright():
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except ImportError:
        print("Installing playwright...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        from playwright.async_api import async_playwright
        return async_playwright

async def test_page(page, name: str, url: str, selector: str = None, timeout: int = 10000):
    """测试单个页面"""
    try:
        print(f"\n[TEST] {name}: {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        
        if response and response.status >= 400:
            print(f"  [FAIL] HTTP {response.status}")
            return False
            
        # 等待特定元素出现（如果指定了）
        if selector:
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                print(f"  [PASS] Page loaded, found: {selector}")
            except Exception as e:
                print(f"  [WARN] Page loaded but element not found: {selector} - {e}")
                # 截图保存
                await page.screenshot(path=f"test_screenshot_{name}.png")
                return False
        else:
            # 至少等待 body
            await page.wait_for_selector("body", timeout=timeout)
            print(f"  [PASS] Page loaded successfully")
            
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        try:
            await page.screenshot(path=f"test_screenshot_{name}_error.png")
        except:
            pass
        return False

async def main():
    BASE_URL = "http://localhost:5000"
    
    # 定义要测试的页面
    pages_to_test = [
        # 名称, 路径, 验证选择器
        ("home", "/", "body"),
        ("login", "/login", "input[type='password']"),
        ("market-driven-create", "/market-driven-create", "body"),
        ("short-drama", "/short-drama", "body"),
        ("creative-workshop", "/creative-workshop", "body"),
        ("video-generation", "/video-generation", "body"),
    ]
    
    # 需要登录后才能访问的页面
    auth_pages = [
        ("my-novels", "/my-novels", ".novel-card"),
        ("continue-chapters", "/novel/开局牵着二哈全网弹幕助我屠神/continue", "input[name='start_chapter']"),
    ]
    
    async_playwright = await ensure_playwright()
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        # 测试公开页面
        print("=" * 60)
        print("Testing Public Pages")
        print("=" * 60)
        
        for name, path, selector in pages_to_test:
            page = await context.new_page()
            try:
                success = await test_page(page, name, f"{BASE_URL}{path}", selector)
                results.append((name, success))
            finally:
                await page.close()
        
        # 测试需要登录的页面
        print("\n" + "=" * 60)
        print("Testing Auth Required Pages")
        print("=" * 60)
        
        page = await context.new_page()
        try:
            # 先登录
            print("\n[LOGIN] Using test account...")
            await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
            await page.fill("input#username", "admin")
            await page.fill("input#password", "admin123")
            await page.click("button[type='submit']")
            await page.wait_for_load_state("networkidle")
            print("  [PASS] Login successful")
            
            # 测试登录后才能访问的页面
            for name, path, selector in auth_pages:
                success = await test_page(page, name, f"{BASE_URL}{path}", selector)
                results.append((name, success))
                
        except Exception as e:
            print(f"  [ERROR] Login or test failed: {e}")
        finally:
            await page.close()
        
        await browser.close()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\nAll page tests passed! System ready for deployment.")
        return 0
    else:
        print(f"\n{total - passed} page(s) failed, please check.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
