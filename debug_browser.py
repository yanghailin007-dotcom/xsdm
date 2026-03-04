from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    # 启动浏览器
    browser = p.chromium.launch(headless=False, args=['--start-maximized'])
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    
    # 监听控制台日志
    def handle_console(msg):
        print(f'[Console {msg.type}] {msg.text}')
    page.on('console', handle_console)
    
    # 打开首页
    print('正在打开首页...')
    page.goto('http://localhost:5000/')
    time.sleep(3)
    
    # 检查余额显示
    print('检查余额元素...')
    try:
        nav_points = page.locator('#nav-points-value').text_content()
        print(f'导航栏余额显示: "{nav_points}"')
    except Exception as e:
        print(f'获取导航栏余额失败: {e}')
    
    try:
        dropdown_points = page.locator('#dropdown-points-value').text_content()
        print(f'下拉框余额显示: "{dropdown_points}"')
    except Exception as e:
        print(f'获取下拉框余额失败: {e}')
    
    # 检查页面 HTML
    print('\n检查余额元素是否存在...')
    has_nav = page.locator('#nav-points-value').count() > 0
    has_dropdown = page.locator('#dropdown-points-value').count() > 0
    print(f'导航栏余额元素存在: {has_nav}')
    print(f'下拉框余额元素存在: {has_dropdown}')
    
    # 执行JS获取余额
    print('\n通过JS获取余额...')
    balance_js = page.evaluate("""
        async () => {
            const response = await fetch('/api/points/balance');
            const data = await response.json();
            return data;
        }
    """)
    print(f'API返回: {balance_js}')
    
    # 等待用户查看
    print('\n浏览器已打开，请查看。按 Enter 键关闭...')
    input()
    
    browser.close()
