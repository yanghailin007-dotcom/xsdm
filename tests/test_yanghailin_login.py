# -*- coding: utf-8 -*-
"""
Test: Login as yanghailin and check first-time hint
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_yanghailin_login():
    """Test first-time hint for yanghailin user"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Clear all storage to simulate true first visit
        await page.goto('http://localhost:5000/login')
        await page.evaluate('''() => {
            localStorage.clear();
            sessionStorage.clear();
            // Clear cookies
            document.cookie.split(";").forEach(function(c) {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
        }''')
        print("[INFO] All storage cleared for fresh start")
        
        # Login as yanghailin
        print("[INFO] Logging in as yanghailin...")
        await page.goto('http://localhost:5000/login', wait_until='networkidle')
        
        # Fill login form
        await page.fill('input[type="text"]', 'yanghailin')
        await page.fill('input[type="password"]', '123456')  # Use actual password
        
        # Click login button
        buttons = await page.query_selector_all('button')
        for btn in buttons:
            text = await btn.inner_text()
            if '登录' in text or 'Login' in text:
                await btn.click()
                break
        
        await asyncio.sleep(3)  # Wait for login and redirect
        
        # Navigate to phase-two-generation
        print("[INFO] Navigating to phase-two-generation...")
        await page.goto('http://localhost:5000/phase-two-generation', wait_until='domcontentloaded')
        await asyncio.sleep(5)  # Wait for full page load
        
        # Create screenshot directory
        screenshot_dir = Path(__file__).parent / 'screenshots'
        screenshot_dir.mkdir(exist_ok=True)
        
        # Get current state
        current_url = page.url
        title = await page.title()
        print(f"[INFO] URL: {current_url}")
        print(f"[INFO] Title: {title}")
        
        # Screenshot 1: Full page
        await page.screenshot(path=str(screenshot_dir / 'yanghailin_full_page.png'), full_page=True)
        print("[OK] Screenshot: yanghailin_full_page.png")
        
        # Check for first-time hint
        print("[INFO] Checking for first-time hint...")
        hint = await page.query_selector('#first-time-hint')
        
        if hint:
            is_visible = await hint.is_visible()
            text = await hint.inner_text()
            print(f"[INFO] Hint found, visible={is_visible}")
            
            # Save hint screenshot
            await hint.screenshot(path=str(screenshot_dir / 'yanghailin_hint.png'))
            print("[OK] Screenshot: yanghailin_hint.png")
            
            if is_visible:
                print("[PASS] First-time hint IS VISIBLE")
                result = True
            else:
                print("[FAIL] Hint found but NOT visible")
                result = False
        else:
            print("[FAIL] First-time hint NOT found")
            
            # Debug: check project-details content
            details = await page.query_selector('#project-details')
            if details:
                html = await details.inner_html()
                # Save to file for inspection
                debug_file = screenshot_dir / 'yanghailin_project_details.html'
                debug_file.write_text(html, encoding='utf-8')
                print(f"[DEBUG] project-details HTML saved to: {debug_file}")
            
            result = False
        
        # Screenshot 2: Right panel only
        right_panel = await page.query_selector('#right-panel')
        if right_panel:
            await right_panel.screenshot(path=str(screenshot_dir / 'yanghailin_right_panel.png'))
            print("[OK] Screenshot: yanghailin_right_panel.png")
        
        print(f"[INFO] All screenshots saved to: {screenshot_dir}")
        
        await browser.close()
        return result

if __name__ == '__main__':
    result = asyncio.run(test_yanghailin_login())
    print(f"\n[RESULT] {'PASS' if result else 'FAIL'}")
    exit(0 if result else 1)
