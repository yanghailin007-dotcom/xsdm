import time
import requests
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple


def test_debug_connection(port: int = 9988) -> bool:
    """测试调试端口连接"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=5)
        return response.status_code == 200
    except:
        return False


def connect_to_existing_browser(port: int = 9988, max_retries: int = 5) -> Tuple[Optional[object], Optional[object], Optional[object], Optional[object]]:
    """连接到已存在的浏览器 - 简化版"""
    print(f"尝试连接到端口 {port} 的浏览器...")
    
    # 首先测试调试端口
    if not test_debug_connection(port):
        print(f"❌ 端口 {port} 无法访问")
        print("请确保:")
        print("1. Chrome已启动")
        print("2. 使用了 --remote-debugging-port=9988 参数")
        print("3. 防火墙没有阻止连接")
        return None, None, None, None
    
    print("✓ 调试端口可访问")
    
    # 启动Playwright并连接
    playwright = sync_playwright().start()
    
    for attempt in range(max_retries):
        try:
            print(f"连接尝试 {attempt + 1}/{max_retries}...")
            
            browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            
            # 获取或创建上下文和页面
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = context.new_page()
            else:
                context = browser.new_context()
                page = context.new_page()
            
            print("✓ 成功连接到浏览器!")
            return playwright, browser, context, page
            
        except Exception as e:
            print(f"连接失败: {e}")
            if attempt < max_retries - 1:
                print("等待 3 秒后重试...")
                time.sleep(3)
            else:
                print("❌ 所有连接尝试都失败了")
                playwright.stop()
                return None, None, None, None


def quick_connect_and_test():
    """快速连接测试"""
    print("=== 快速连接测试 ===")
    
    # 测试端口
    if not test_debug_connection(9988):
        print("❌ 端口 9988 不可访问")
        print("\n解决方案:")
        print("1. 重新启动Chrome并添加参数:")
        print('   chrome.exe --remote-debugging-port=9988 --user-data-dir="C:\\temp\\chrome_debug"')
        print("2. 或者使用项目中的启动脚本")
        return False
    
    print("✓ 端口测试通过")
    
    # 尝试连接
    playwright, browser, context, page = connect_to_existing_browser(9988)
    
    if browser:
        try:
            # 测试导航
            page.goto("https://www.baidu.com")
            title = page.title()
            print(f"✓ 页面导航成功: {title}")
            
            # 保持连接
            print("\n连接已建立，您可以继续使用自动化脚本")
            print("按 Ctrl+C 退出")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n用户中断，关闭连接...")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False
        finally:
            try:
                browser.close()
                playwright.stop()
            except:
                pass
    else:
        return False


def enhanced_connect_with_fallback():
    """增强版连接，支持端口回退"""
    ports = [9988, 9222, 9223, 9224, 9225]  # 常用的调试端口
    
    print("=== 增强版连接测试 ===")
    
    for port in ports:
        print(f"\n尝试端口 {port}...")
        
        if test_debug_connection(port):
            print(f"✓ 端口 {port} 可访问")
            
            playwright, browser, context, page = connect_to_existing_browser(port, max_retries=3)
            
            if browser:
                print(f"✓ 成功连接到端口 {port}")
                return playwright, browser, context, page, port
            else:
                print(f"❌ 端口 {port} 连接失败")
        else:
            print(f"❌ 端口 {port} 不可访问")
    
    print("\n❌ 所有端口都无法连接")
    print("请确保Chrome已启动并开启调试端口")
    return None, None, None, None, None


if __name__ == "__main__":
    # 选择测试模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "enhanced":
        enhanced_connect_with_fallback()
    else:
        quick_connect_and_test()