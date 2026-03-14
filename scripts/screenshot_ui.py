#!/usr/bin/env python
"""
使用Playwright截图验证UI
"""
import asyncio
from playwright.async_api import async_playwright

async def capture_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 截图二阶段页面
        print("Capturing http://localhost:5000/phase-two-generation ...")
        try:
            await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)  # 等待3秒让页面完全渲染
            
            # 截图整个页面
            await page.screenshot(path='screenshots/phase_two_full.png', full_page=True)
            print("[OK] Saved screenshots/phase_two_full.png")
            
            # 截图项目选择区域
            projects_list = await page.query_selector('#projects-list')
            if projects_list:
                await projects_list.screenshot(path='screenshots/projects_list.png')
                print("[OK] Saved screenshots/projects_list.png")
            
            # 检查是否有重复的UI
            chapter_sections = await page.query_selector_all('.chapter-queue-container, .v2-chapter-section')
            print(f"\nFound {len(chapter_sections)} chapter progress UI elements:")
            for i, section in enumerate(chapter_sections):
                class_name = await section.get_attribute('class')
                print(f"  {i+1}. {class_name}")
            
        except Exception as e:
            print(f"[ERROR] {e}")
        
        await browser.close()

if __name__ == '__main__':
    import os
    os.makedirs('screenshots', exist_ok=True)
    asyncio.run(capture_screenshots())
