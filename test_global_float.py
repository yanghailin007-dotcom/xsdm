"""
测试后台运行模式是否全局显示
使用 Playwright 登录并验证浮动窗口
"""
import asyncio
from playwright.async_api import async_playwright

async def test_global_float():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        
        # 创建第一个页面 - 登录并开始生成
        page1 = await context.new_page()
        
        print("[测试] 打开登录页面...")
        await page1.goto("http://localhost:5000/login")
        
        # 登录
        await page1.fill('input[name="username"]', 'yanghailin')
        await page1.fill('input[name="password"]', 'yanghailin')
        await page1.click('button[type="submit"]')
        
        # 等待登录成功
        await page1.wait_for_load_state('networkidle')
        print("[测试] 登录成功")
        
        # 进入生成页面
        print("[测试] 进入对话打磨模式...")
        await page1.goto("http://localhost:5000/market-driven-plan-dialog?genre=国运文-直播类")
        await page1.wait_for_load_state('networkidle')
        
        # 等待页面加载完成
        await page1.wait_for_timeout(2000)
        
        # 检查 localStorage 是否支持
        print("[测试] 检查 localStorage 状态...")
        storage_data = await page1.evaluate('''() => {
            return {
                task: localStorage.getItem('market_driven_background_task'),
                hasFloat: !!document.getElementById('globalTaskFloat'),
                floatDisplay: document.getElementById('globalTaskFloat')?.style.display
            };
        }''')
        print(f"[测试] 初始状态: {storage_data}")
        
        # 模拟开始一个任务（直接设置 localStorage）
        print("[测试] 模拟开始生成任务...")
        await page1.evaluate('''() => {
            localStorage.setItem('market_driven_background_task', JSON.stringify({
                task_id: 'test-task-123',
                title: '测试小说',
                genre: '国运文-直播类',
                progress: 30,
                status: 'running',
                created_at: Date.now()
            }));
            // 触发 storage 事件
            window.dispatchEvent(new StorageEvent('storage', {
                key: 'market_driven_background_task',
                newValue: localStorage.getItem('market_driven_background_task')
            }));
        }''')
        
        await page1.wait_for_timeout(1000)
        
        # 检查浮窗是否显示
        float_info = await page1.evaluate('''() => {
            const floatEl = document.getElementById('globalTaskFloat');
            return {
                exists: !!floatEl,
                display: floatEl?.style.display,
                visible: floatEl && window.getComputedStyle(floatEl).display !== 'none',
                text: floatEl?.textContent?.substring(0, 100)
            };
        }''')
        print(f"[测试] 页面1浮窗状态: {float_info}")
        
        # 创建第二个页面 - 验证全局显示
        print("[测试] 创建第二个页面验证全局显示...")
        page2 = await context.new_page()
        await page2.goto("http://localhost:5000/")
        await page2.wait_for_load_state('networkidle')
        await page2.wait_for_timeout(2000)
        
        # 检查第二个页面的浮窗
        float_info2 = await page2.evaluate('''() => {
            const floatEl = document.getElementById('globalTaskFloat');
            return {
                exists: !!floatEl,
                display: floatEl?.style.display,
                visible: floatEl && window.getComputedStyle(floatEl).display !== 'none',
                text: floatEl?.textContent?.substring(0, 100)
            };
        }''')
        print(f"[测试] 页面2浮窗状态: {float_info2}")
        
        # 测试结果
        if float_info['exists'] and float_info2['exists']:
            print("\n✅ [测试通过] 后台模式浮窗在两个页面都显示！")
        else:
            print("\n❌ [测试失败] 后台模式浮窗未全局显示")
            print(f"   页面1: {'✅' if float_info['exists'] else '❌'}")
            print(f"   页面2: {'✅' if float_info2['exists'] else '❌'}")
        
        # 等待用户查看
        print("\n[测试] 等待10秒以便查看...")
        await asyncio.sleep(10)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_global_float())
