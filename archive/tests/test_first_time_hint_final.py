# -*- coding: utf-8 -*-
"""
Test: First Time Hint Display (Final)
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_first_time_hint():
    """Test that first-time hint shows on first visit"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Clear storage
        await page.goto('http://localhost:5000/login')
        await page.evaluate('() => { localStorage.clear(); sessionStorage.clear(); }')
        print("[INFO] Storage cleared")
        
        # Login
        await page.fill('input[type="text"]', 'test')
        await page.fill('input[type="password"]', 'test123')
        buttons = await page.query_selector_all('button')
        for btn in buttons:
            text = await btn.inner_text()
            if '登录' in text:
                await btn.click()
                break
        await asyncio.sleep(2)
        
        # Go to phase two page
        await page.goto('http://localhost:5000/phase-two-generation', wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        screenshot_dir = Path(__file__).parent / 'screenshots'
        screenshot_dir.mkdir(exist_ok=True)
        
        print(f"[INFO] URL: {page.url}")
        await page.screenshot(path=str(screenshot_dir / '01_first_visit.png'), full_page=True)
        print("[OK] Screenshot saved")
        
        # Check hint
        hint = await page.query_selector('#first-time-hint')
        if hint:
            visible = await hint.is_visible()
            text = await hint.inner_text()
            # Remove emoji for console output
            clean_text = text.encode('ascii', 'ignore').decode()[:80]
            
            print(f"[INFO] Hint visible: {visible}")
            print(f"[INFO] Hint text: {clean_text}...")
            
            if visible:
                print("[PASS] First-time hint IS VISIBLE")
                await hint.screenshot(path=str(screenshot_dir / '02_hint.png'))
                result = True
            else:
                print("[FAIL] Hint found but not visible")
                result = False
        else:
            print("[FAIL] Hint element not found")
            result = False
        
        await browser.close()
        return result

if __name__ == '__main__':
    result = asyncio.run(test_first_time_hint())
    print(f"[RESULT] {'PASS' if result else 'FAIL'}")
    exit(0 if result else 1)
