#!/usr/bin/env python3
"""
验证右侧详情面板显示
"""
import asyncio
from playwright.async_api import async_playwright

async def test_right_panel():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()
        
        print("[TEST] 验证右侧详情面板...")
        
        # 登录
        await page.goto('http://localhost:5000/login', timeout=60000)
        await page.fill('input[placeholder="请输入用户名"]', 'yanghailin')
        await page.fill('input[placeholder="请输入密码"]', 'yanghailin')
        await page.click('button[type="submit"]')
        await asyncio.sleep(2)
        
        # 进入页面
        await page.goto('http://localhost:5000/phase-two-generation?v=6', timeout=60000)
        await asyncio.sleep(3)
        
        # 选择项目
        cards = await page.query_selector_all('.creative-idea-card')
        if cards:
            print(f"[CLICK] 选择项目: {await cards[0].get_attribute('data-title')}")
            await cards[0].click()
            await asyncio.sleep(3)
        
        # 截图
        await page.screenshot(path='right_panel_test.png', full_page=False)
        
        # 检查右侧详情面板内容
        project_details = await page.query_selector('#project-details')
        if project_details:
            text = await project_details.text_content()
            print(f"[CHECK] 项目详情内容: {text[:200]}...")
            
            if '项目信息' in text or '标题:' in text:
                print("[PASS] 右侧详情面板显示正确!")
            else:
                print("[FAIL] 右侧详情面板未显示项目信息")
        else:
            print("[FAIL] 未找到 project-details 元素")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_right_panel())
