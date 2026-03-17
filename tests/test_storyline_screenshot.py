"""
Storyline page screenshot test
Login and visit storyline page for screenshot
"""
from playwright.sync_api import sync_playwright
import time

def test_storyline_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = context.new_page()
        
        # Visit login page
        page.goto('http://localhost:5000/login')
        page.wait_for_selector('#loginForm', timeout=10000)
        
        # Screenshot: before login
        page.screenshot(path='screenshots/storyline_test_01_login_page.png', full_page=False)
        print("Screenshot: login page saved")
        
        # Fill login info
        page.fill('#username', 'yanghailin')
        page.fill('#password', 'yanghailin')
        
        # Click login button
        page.click('button[type="submit"]')
        
        # Wait for navigation
        try:
            page.wait_for_url(lambda url: '/login' not in url, timeout=10000)
            print(f"Login success, current page: {page.url}")
        except:
            print("Login failed or timeout")
            page.screenshot(path='screenshots/storyline_test_01b_login_error.png', full_page=False)
            browser.close()
            return
        
        # Wait for page to load
        time.sleep(2)
        
        # Visit storyline page with project parameter
        test_title = "诡异直播：我把恐怖副本玩成了养成"
        page.goto(f'http://localhost:5000/storyline?title={test_title}')
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        
        # Screenshot: storyline page
        page.screenshot(path='screenshots/storyline_test_02_main.png', full_page=False)
        print("Screenshot: storyline main page saved")
        
        # Try to click first major event
        try:
            cards = page.locator('.timeline-card')
            count = cards.count()
            print(f"Found {count} timeline cards")
            if count > 0:
                cards.first.click()
                time.sleep(1)
                page.screenshot(path='screenshots/storyline_test_03_detail.png', full_page=False)
                print("Screenshot: detail view saved")
        except Exception as e:
            print(f"Click event failed: {e}")
        
        browser.close()
        print("Screenshots completed!")

if __name__ == '__main__':
    test_storyline_screenshot()
