from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    # 连接到已打开的浏览器
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    
    # 获取所有页面
    contexts = browser.contexts
    print(f"找到 {len(contexts)} 个 context")
    
    for ctx_idx, context in enumerate(contexts):
        pages = context.pages
        print(f"\nContext {ctx_idx}: {len(pages)} 个页面")
        
        for page in pages:
            url = page.url
            print(f"\n=== 页面: {url} ===")
            
            # 如果页面不是我们的网站，跳过
            if "localhost:5001" not in url:
                print(f"  跳过非目标页面")
                continue
            
            # 等待页面加载完成
            page.wait_for_load_state("networkidle")
            
            # 1. 检查 API 调用结果 - 执行 JavaScript 获取 window 对象中的数据
            print("\n--- 1. 检查 API 调用 ---")
            
            # 重新加载页面以确保获取最新的数据
            page.reload()
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            
            # 获取控制台日志（如果有）
            print("\n--- 2. 检查点数显示元素 ---")
            
            # 检查导航栏点数
            nav_points = page.locator("#nav-points-value").first
            if nav_points.is_visible():
                text = nav_points.text_content()
                print(f"  导航栏点数显示: '{text}'")
            else:
                print("  导航栏点数元素未找到或不可见")
            
            # 检查下拉菜单点数
            # 先点击用户头像/菜单打开下拉框
            user_menu = page.locator(".user-menu").first
            if user_menu.is_visible():
                user_menu.click()
                time.sleep(0.5)
                
                dropdown_points = page.locator("#dropdown-points-value").first
                if dropdown_points.is_visible():
                    text = dropdown_points.text_content()
                    print(f"  下拉菜单点数显示: '{text}'")
                else:
                    print("  下拉菜单点数元素未找到")
            
            # 3. 直接调用 API 检查返回
            print("\n--- 3. 直接调用 API ---")
            api_response = page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('/api/points/balance');
                        const data = await response.json();
                        return data;
                    } catch (e) {
                        return { error: e.message };
                    }
                }
            """)
            print(f"  API 返回: {api_response}")
            
            # 4. 检查 localStorage 和 sessionStorage
            print("\n--- 4. 检查存储 ---")
            local_storage = page.evaluate("() => JSON.stringify(localStorage)")
            session_storage = page.evaluate("() => JSON.stringify(sessionStorage)")
            print(f"  localStorage: {local_storage[:500] if len(local_storage) > 500 else local_storage}")
            print(f"  sessionStorage: {session_storage[:500] if len(session_storage) > 500 else session_storage}")
            
            # 5. 截图
            print("\n--- 5. 截图 ---")
            page.screenshot(path="debug_screenshot.png", full_page=True)
            print("  已保存截图到 debug_screenshot.png")
    
    print("\n=== 调试完成 ===")
    browser.close()
