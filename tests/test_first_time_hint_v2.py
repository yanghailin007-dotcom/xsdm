# -*- coding: utf-8 -*-
"""
Test: First Time Hint Display (True First Visit)
Clears localStorage to simulate actual first visit
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_first_time_hint():
    """Test that first-time hint shows on true first visit"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Clear localStorage before loading page
        await page.goto('http://localhost:5000/login')
        await page.evaluate('''() => {
            localStorage.clear();
            sessionStorage.clear();
        }''')
        print("[INFO] Cleared localStorage and sessionStorage")
        
        # Navigate to target page
        print("[INFO] Navigating to phase-two-generation...")
        try:
            await page.goto('http://localhost:5000/phase-two-generation', timeout=10000)
        except Exception as e:
            print(f"[WARN] Navigation timeout (expected if requires auth): {e}")
        
        current_url = page.url
        print(f"[INFO] Current URL: {current_url}")
        
        # If redirected to login, handle it
        if 'login' in current_url:
            print("[INFO] Login required, attempting...")
            try:
                await page.wait_for_selector('input', timeout=5000)
                inputs = await page.query_selector_all('input')
                print(f"[INFO] Found {len(inputs)} input fields")
                
                # Fill login form
                await page.fill('input[type="text"]', 'test')
                await page.fill('input[type="password"]', 'test123')
                
                # Find login button
                buttons = await page.query_selector_all('button, .v2-btn--primary')
                for btn in buttons:
                    text = await btn.inner_text()
                    print(f"[DEBUG] Button text: {text}")
                    if '登录' in text:
                        await btn.click()
                        break
                
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[WARN] Login attempt failed: {e}")
        
        # Try to navigate to target page again
        print("[INFO] Re-navigating to phase-two-generation...")
        await page.goto('http://localhost:5000/phase-two-generation', wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Create screenshot dir
        screenshot_dir = Path(__file__).parent / 'screenshots'
        screenshot_dir.mkdir(exist_ok=True)
        
        current_url = page.url
        print(f"[INFO] Final URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path=str(screenshot_dir / '01_first_visit.png'), full_page=True)
        print("[OK] Screenshot: 01_first_visit.png")
        
        # Check if on correct page
        if 'phase-two' not in current_url:
            print("[FAIL] Not on phase-two-generation page")
            await browser.close()
            return False
        
        # Check for first-time hint
        print("[INFO] Checking for first-time hint...")
        
        hint = await page.query_selector('#first-time-hint')
        if not hint:
            print("[FAIL] #first-time-hint not found")
            # Debug: print all IDs
            ids = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('[id]')).map(el => el.id);
            }''')
            print(f"[DEBUG] All IDs on page: {ids[:30]}")
        else:
            is_visible = await hint.is_visible()
            text = await hint.inner_text()
            print(f"[INFO] Hint found, visible={is_visible}")
            print(f"[INFO] Hint text: {text[:80]}...")
            
            if is_visible:
                print("[PASS] First-time hint is VISIBLE")
                await hint.screenshot(path=str(screenshot_dir / '02_hint_visible.png'))
                result = True
            else:
                print("[FAIL] Hint found but NOT visible")
                result = False
        
        # Check project-details content
        details_html = await page.inner_html('#project-details')
        if 'first-time-hint' in details_html:
            print("[PASS] first-time-hint is inside project-details")
        else:
            print("[INFO] first-time-hint not in project-details (may have been replaced)")
            print(f"[DEBUG] project-details content preview: {details_html[:300]}")
        
        await browser.close()
        return result if 'result' in dir() else False

if __name__ == '__main__':
    result = asyncio.run(test_first_time_hint())
    print(f"\n[RESULT] {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)
