# -*- coding: utf-8 -*-
"""
Test: First Time Hint Display on phase-two-generation page
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_first_time_hint():
    """Test that first-time hint is displayed correctly"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Use API to login directly via session
        print("[INFO] Setting up auth via API...")
        
        # First try to access page directly (may already be authenticated via session cookie)
        print("[INFO] Navigating to phase-two-generation...")
        response = await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle')
        
        current_url = page.url
        print(f"[INFO] Current URL: {current_url}")
        
        # If redirected to login, we need to handle auth
        if 'login' in current_url:
            print("[INFO] Need to login, attempting...")
            await page.fill('input[type="text"]', 'test')
            await page.fill('input[type="password"]', 'test123')
            # Try to find and click the actual login button
            buttons = await page.query_selector_all('button')
            for btn in buttons:
                text = await btn.inner_text()
                if '登录' in text or 'login' in text.lower():
                    await btn.click()
                    break
            await asyncio.sleep(2)
            
            # Navigate to target page again
            await page.goto('http://localhost:5000/phase-two-generation', wait_until='networkidle')
        
        await asyncio.sleep(3)
        
        # Create screenshots directory
        screenshot_dir = Path(__file__).parent / 'screenshots'
        screenshot_dir.mkdir(exist_ok=True)
        
        # Check page loaded correctly
        current_url = page.url
        print(f"[INFO] Final URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path=str(screenshot_dir / '01_full_page.png'), full_page=True)
        print("[OK] Screenshot: 01_full_page.png")
        
        # Debug: Print page title
        title = await page.title()
        print(f"[INFO] Page title: {title}")
        
        # Check if we're on the right page
        if 'phase-two' not in current_url and 'phase-two' not in title:
            print("[FAIL] Not on phase-two-generation page!")
            print("[INFO] This might be because authentication is required")
            await browser.close()
            return False
        
        # Check for first-time hint with multiple attempts
        print("[INFO] Checking for first-time hint...")
        
        # Try multiple selectors
        selectors = [
            '#first-time-hint',
            '#project-details #first-time-hint',
            '[id="first-time-hint"]'
        ]
        
        hint = None
        for selector in selectors:
            hint = await page.query_selector(selector)
            if hint:
                print(f"[OK] Found hint with selector: {selector}")
                break
        
        if hint:
            is_visible = await hint.is_visible()
            print(f"[INFO] Hint visible: {is_visible}")
            
            # Get outer HTML
            outer_html = await hint.evaluate('el => el.outerHTML')
            print(f"[DEBUG] Hint HTML: {outer_html[:300]}...")
            
            # Get text content
            text = await hint.inner_text()
            print(f"[INFO] Hint text: {text[:100]}...")
            
            if is_visible:
                print("[PASS] First-time hint is VISIBLE and FOUND")
                await hint.screenshot(path=str(screenshot_dir / '02_hint_success.png'))
                result = True
            else:
                print("[FAIL] Hint found but not visible")
                await hint.screenshot(path=str(screenshot_dir / '02_hint_hidden.png'))
                result = False
        else:
            print("[FAIL] First-time hint element NOT found with any selector!")
            
            # Debug: Get project-details HTML
            details = await page.query_selector('#project-details')
            if details:
                html = await details.inner_html()
                print(f"[DEBUG] project-details content:")
                print(html)
                
                # Save debug screenshot
                await page.screenshot(path=str(screenshot_dir / '02_debug.png'), full_page=True)
            else:
                print("[DEBUG] project-details element not found either!")
                # Print all div IDs on page
                all_divs = await page.query_selector_all('div[id]')
                print(f"[DEBUG] Found {len(all_divs)} divs with IDs:")
                for i, div in enumerate(all_divs[:20]):  # Limit to first 20
                    div_id = await div.get_attribute('id')
                    print(f"  - {div_id}")
            
            result = False
        
        print(f"[INFO] Screenshots saved to: {screenshot_dir}")
        
        await browser.close()
        return result

if __name__ == '__main__':
    result = asyncio.run(test_first_time_hint())
    print(f"\n[RESULT] {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)
