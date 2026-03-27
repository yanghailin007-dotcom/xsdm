from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    try:
        # 连接到已打开的 Edge 浏览器
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        
        # 获取所有页面
        contexts = browser.contexts
        print(f"找到 {len(contexts)} 个 context")
        
        for context in contexts:
            # 清理缓存
            print("正在清理缓存...")
            context.clear_cookies()
            
            # 尝试清理 storage
            for page in context.pages:
                try:
                    page.evaluate("""
                        () => {
                            localStorage.clear();
                            sessionStorage.clear();
                            console.log('Storage cleared');
                        }
                    """)
                    print(f"已清理页面 storage: {page.url}")
                except:
                    pass
        
        # 找到 home 页面并刷新
        for context in contexts:
            for page in context.pages:
                if "localhost:5000/home" in page.url or "localhost:5000/" in page.url:
                    print(f"\n找到首页: {page.url}")
                    print("正在强制刷新...")
                    page.reload(wait_until="networkidle")
                    time.sleep(2)
                    print("✅ 刷新完成")
                    
                    # 检查显示值
                    try:
                        total_projects = page.locator("#total-projects").text_content()
                        print(f"创作项目显示: {total_projects}")
                    except:
                        print("无法读取创作项目数值")
        
        browser.close()
        print("\n✅ 缓存清理完成")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n尝试手动清理缓存...")
