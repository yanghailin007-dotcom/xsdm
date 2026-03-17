"""
番茄上传页面截图测试
"""
from playwright.sync_api import sync_playwright
import time

def test_fanqie_upload_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = context.new_page()
        
        # 登录
        page.goto('http://localhost:5000/login')
        page.fill('#username', 'yanghailin')
        page.fill('#password', 'yanghailin')
        page.click('button[type="submit"]')
        page.wait_for_url(lambda url: '/login' not in url, timeout=10000)
        time.sleep(2)
        
        # 访问番茄上传页面
        page.goto('http://localhost:5000/pages/v2/fanqie-upload-v2')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # 截图：初始状态
        page.screenshot(path='screenshots/fanqie_upload_01_initial.png', full_page=False)
        print("Screenshot: initial state")
        
        # 尝试选择第一个项目
        try:
            cards = page.locator('.project-card')
            if cards.count() > 0:
                cards.first.click()
                time.sleep(1)
                page.screenshot(path='screenshots/fanqie_upload_02_selected.png', full_page=True)
                print("Screenshot: project selected (full page)")
        except Exception as e:
            print(f"Click failed: {e}")
        
        browser.close()
        print("Screenshots completed!")

if __name__ == '__main__':
    test_fanqie_upload_screenshot()
