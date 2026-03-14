#!/usr/bin/env python
"""
使用Playwright登录并截图验证UI
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto('http://localhost:5000/login', wait_until='networkidle', timeout=30000)
        
        # 尝试使用测试账户登录
        print("Trying to login with test account...")
        try:
            await page.fill('input[name="username"]', 'test')
            await page.fill('input[name="password"]', 'test')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(3000)
            
            # 现在访问二阶段页面
            print("Navigating to phase two generation page...")
            await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 截图
            await page.screenshot(path='screenshots/phase_two_logged_in.png', full_page=True)
            print("[OK] Saved screenshots/phase_two_logged_in.png")
            
            # 检查项目列表
            projects_list = await page.query_selector('#projects-list')
            if projects_list:
                print("[OK] Projects list found")
                await projects_list.screenshot(path='screenshots/projects_list.png')
                print("[OK] Saved screenshots/projects_list.png")
            else:
                print("[WARN] Projects list not found")
            
            # 检查章节队列（可能是隐藏状态）
            chapter_queue = await page.query_selector('#chapterQueueContainer')
            if chapter_queue:
                is_visible = await chapter_queue.is_visible()
                print(f"Chapter queue visible: {is_visible}")
                
            # 统计UI元素
            all_elements = await page.query_selector_all('.chapter-queue-container, .v2-chapter-section, #generation-form, #progress-section')
            print(f"\nFound {len(all_elements)} main UI sections")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path='screenshots/error.png', full_page=True)
            print("[OK] Saved error screenshot to screenshots/error.png")
        
        await browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('screenshots', exist_ok=True)
    asyncio.run(capture_screenshots())
