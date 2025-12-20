"""
番茄小说自动发布系统 - 浏览器管理模块
处理浏览器连接、导航和页面管理
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple

from .config import CONFIG
from .utils import safe_click


def connect_to_browser():
    """连接浏览器 - 全自动集成版本"""
    print(f"🔗 尝试连接浏览器 (调试端口: {CONFIG['debug_port']})...")
    
    try:
        from ..utils.auto_browser_manager import auto_connect_to_browser
        
        debug_port = CONFIG['debug_port']
        print(f"🤖 启动自动化浏览器管理器 (端口: {debug_port})...")
        
        # 使用自动化连接管理器，增加重试次数
        for attempt in range(3):
            try:
                print(f"  尝试自动连接 (第 {attempt + 1} 次)...")
                playwright, browser, page, context = auto_connect_to_browser(
                    debug_port=debug_port,
                    auto_start_chrome=True  # 自动启动Chrome
                )
                
                if browser:
                    print("✅ 浏览器连接已建立!")
                    return playwright, browser, page, context
                else:
                    print(f"  第 {attempt + 1} 次自动连接失败")
                    if attempt < 2:
                        print("  等待 5 秒后重试...")
                        time.sleep(5)
                        
            except Exception as auto_error:
                print(f"  第 {attempt + 1} 次自动连接异常: {auto_error}")
                if attempt < 2:
                    print("  等待 5 秒后重试...")
                    time.sleep(5)
        
        print("❌ 所有自动连接尝试都失败")
        return None, None, None, None
            
    except ImportError as e:
        print(f"❌ 导入自动化管理器失败: {e}")
        print("尝试使用简化连接方案...")
        
        # 回退到简化连接方案
        try:
            from ..utils.simple_connection_fix import connect_to_existing_browser, test_debug_connection
            
            debug_port = CONFIG['debug_port']
            print(f"尝试连接到端口 {debug_port} 的浏览器...")
            
            # 首先测试调试端口，增加重试
            for attempt in range(3):
                try:
                    print(f"  测试调试端口连接 (第 {attempt + 1} 次)...")
                    if test_debug_connection(debug_port):
                        print("✓ 调试端口连接成功")
                        break
                    else:
                        print(f"  第 {attempt + 1} 次端口测试失败")
                        if attempt < 2:
                            time.sleep(3)
                except Exception as port_error:
                    print(f"  第 {attempt + 1} 次端口测试异常: {port_error}")
                    if attempt < 2:
                        time.sleep(3)
            else:
                print(f"❌ 端口 {debug_port} 无法访问")
                print("请确保:")
                print("1. Chrome已启动")
                print(f"2. 使用了 --remote-debugging-port={debug_port} 参数")
                print("3. 防火墙没有阻止连接")
                print("\n💡 或者运行自动启动脚本:")
                print("   python fanqie_browser_launcher.py")
                return None, None, None, None
            
            # 尝试连接
            for attempt in range(3):
                try:
                    print(f"  尝试建立浏览器连接 (第 {attempt + 1} 次)...")
                    playwright, browser, context, page = connect_to_existing_browser(debug_port, max_retries=2)
                    
                    if browser:
                        print("✓ 成功连接到浏览器!")
                        return playwright, browser, page, context
                    else:
                        print(f"  第 {attempt + 1} 次连接失败")
                        if attempt < 2:
                            time.sleep(3)
                except Exception as conn_error:
                    print(f"  第 {attempt + 1} 次连接异常: {conn_error}")
                    if attempt < 2:
                        time.sleep(3)
            
            print("❌ 所有连接尝试都失败")
            return None, None, None, None
                
        except ImportError as e2:
            print(f"❌ 导入简化连接模块失败: {e2}")
            print("使用原有连接方式...")
            
            # 最后回退到原有方式
            playwright = sync_playwright().start()
            try:
                for attempt in range(3):
                    try:
                        print(f"  使用原有方式连接 (第 {attempt + 1} 次)...")
                        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{CONFIG['debug_port']}")
                        default_context = browser.contexts[0]
                        page1 = default_context.pages[0]
                        print("✓ 原有方式连接成功")
                        return playwright, browser, page1, default_context
                    except Exception as e3:
                        print(f"  第 {attempt + 1} 次原有方式连接失败: {e3}")
                        if attempt < 2:
                            time.sleep(3)
            except Exception as e3:
                print(f"❌ 原有连接方式也失败: {e3}")
                return None, None, None, None
        except Exception as e2:
            print(f"❌ 简化连接失败: {e2}")
            return None, None, None, None
    except Exception as e:
        print(f"❌ 自动连接失败: {e}")
        return None, None, None, None


def navigate_to_writer_platform(page1, default_context):
    """导航到作家专区 - 全自动版本"""
    print("=" * 60)
    print("🍅 自动导航到番茄小说作家专区")
    print("=" * 60)
    print("🚀 正在自动导航，无需手动操作...")
    print()
    
    # 自动导航到作家专区
    print("📍 步骤1: 导航到番茄小说首页...")
    try:
        # 增加超时时间并添加重试机制
        for attempt in range(3):
            try:
                print(f"  尝试导航到番茄网站 (第 {attempt + 1} 次)...")
                page1.goto("https://fanqienovel.com/", timeout=60000)  # 60秒超时
                page1.wait_for_load_state("domcontentloaded", timeout=30000)  # 30秒等待
                print("✅ 已打开番茄小说首页")
                break
            except Exception as nav_error:
                print(f"  第 {attempt + 1} 次导航失败: {nav_error}")
                if attempt == 2:  # 最后一次尝试
                    raise nav_error
                print("  等待 5 秒后重试...")
                time.sleep(5)
    except Exception as e:
        print(f"❌ 打开番茄小说首页失败: {e}")
        print("💡 可能的解决方案:")
        print("   1. 检查网络连接")
        print("   2. 确认防火墙设置")
        print("   3. 验证 Chrome 是否正确启动")
        print("   4. 尝试手动打开 https://fanqienovel.com")
        return None
    
    # 等待页面加载
    time.sleep(3)
    
    print("📍 步骤2: 查找并点击作家专区链接...")
    try:
        # 尝试多种选择器定位作家专区链接
        writer_zone_selectors = [
            'xpath=//*[@id="app"]/div/div[1]/div/div[2]/div[5]/a',
            'a:has-text("作家专区")',
            'text=作家专区',
            '[href*="writer"]',
            'a[href*="author"]',
            'a[href*="creator"]'
        ]
        
        link_found = False
        for selector in writer_zone_selectors:
            try:
                print(f"  尝试选择器: {selector}")
                element = page1.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    print("  ✓ 找到作家专区链接")
                    
                    # 使用expect_popup处理新窗口
                    with page1.expect_popup(timeout=10000) as page2_info:
                        element.click()
                    
                    page2 = page2_info.value
                    link_found = True
                    break
            except Exception as e:
                print(f"  选择器失败: {e}")
                continue
        
        if not link_found:
            print("❌ 未找到作家专区链接，尝试备用方案...")
            # 备用方案：直接导航到作家专区URL
            try:
                with page1.expect_popup(timeout=10000) as page2_info:
                    page1.goto("https://fanqienovel.com/writer", timeout=15000)
                page2 = page2_info.value
                print("✅ 通过直接导航打开作家专区")
            except Exception as e:
                print(f"❌ 备用方案也失败: {e}")
                return None
                
    except Exception as e:
        print(f"❌ 打开作家专区失败: {e}")
        return None
    
    print("📍 步骤3: 等待作家专区页面加载...")
    try:
        page2.wait_for_load_state("domcontentloaded")
        time.sleep(3)
        print("✅ 作家专区页面已加载")
    except Exception as e:
        print(f"⚠️ 页面加载检查失败: {e}")
    
    print("📍 步骤4: 导航到工作台...")
    try:
        # 尝试点击工作台
        workbench_selectors = [
            'xpath=//*[@id="root"]/div[2]/div/div[3]/div[1]/div[1]/div[2]/button[1]',
            'button:has-text("工作台")',
            'text=工作台',
            '[class*="workbench"]',
            '[class*="dashboard"]'
        ]
        
        workbench_found = False
        for selector in workbench_selectors:
            try:
                print(f"  尝试工作台选择器: {selector}")
                element = page2.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    if safe_click(element, "工作台"):
                        workbench_found = True
                        break
            except Exception as e:
                print(f"  工作台选择器失败: {e}")
                continue
        
        if workbench_found:
            print("✅ 已进入工作台")
            time.sleep(2)
        else:
            print("⚠️ 未找到工作台按钮，可能已在正确页面")
            
    except Exception as e:
        print(f"⚠️ 导航工作台失败: {e}")
    
    print("📍 步骤5: 导航到小说管理页面...")
    try:
        # 尝试点击小说
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")',
            '[class*="novel"]',
            'a[href*="novel"]'
        ]
        
        novel_found = False
        for selector in novel_selectors:
            try:
                print(f"  尝试小说选择器: {selector}")
                element = page2.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    if safe_click(element, "小说"):
                        novel_found = True
                        break
            except Exception as e:
                print(f"  小说选择器失败: {e}")
                continue
        
        if novel_found:
            print("✅ 已进入小说管理页面")
            time.sleep(2)
        else:
            print("⚠️ 未找到小说按钮，可能已在正确页面")
            
    except Exception as e:
        print(f"⚠️ 导航小说页面失败: {e}")
    
    print("=" * 60)
    print("✅ 自动导航完成！")
    print("📝 当前应该位于作家专区的小说管理页面")
    print("📍 如未登录，请在浏览器中手动登录番茄小说账号")
    print("=" * 60)
    
    return page2


def check_and_recover_page(page):
    """检查页面状态并尝试恢复"""
    try:
        # 检查页面是否仍然可用
        page.title()
        return True
    except:
        print("页面可能已关闭或失效，尝试重新连接...")
        return False


def manage_browser_pages(default_context):
    """管理浏览器页面，关闭非必要页面"""
    try:
        # 获取当前 context 下所有页面
        pages = default_context.pages
        pages_count = len(pages)
        print(f"📄 发现 {pages_count} 个浏览器页面")
        
        for idx, page in enumerate(pages):
            try:
                url = page.url
                print(f"  页面 {idx + 1}: {url}")
                if url != 'https://fanqienovel.com/':
                    if pages_count != 1:
                        print(f"  🔒 关闭非番茄页面: {url}")
                        page.close()
                else:
                    print(f"  ✅ 保留番茄页面: {url}")
                    main_page = page
            except Exception as e:
                print(f"  ❌ 关闭页面 {idx + 1} 时出错: {e}")
        
        return main_page if 'main_page' in locals() else None
    except Exception as e:
        print(f"❌ 页面管理失败: {e}")
        return None


def ensure_fanqie_page(page1):
    """确保在番茄小说页面"""
    try:
        current_url = page1.url
        print(f"📍 当前页面: {current_url}")
        
        if current_url != 'https://fanqienovel.com/':
            print("🔄 导航到番茄小说首页...")
            page1.goto("https://fanqienovel.com/", timeout=60000)
            page1.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # 检查页面标题
        page_title = page1.title()
        print(f"📄 页面标题: {page_title}")
        
        if '番茄小说' not in page_title:
            print("⚠️ 当前页面可能不是番茄小说，但继续尝试...")
            print("🔄 强制导航到番茄小说...")
            page1.goto("https://fanqienovel.com/", timeout=60000)
            page1.wait_for_load_state("domcontentloaded", timeout=30000)
            
        return True
    except Exception as e:
        print(f"❌ 页面导航失败: {e}")
        return False


def close_browser_connection(playwright, browser, page2):
    """关闭浏览器连接"""
    print("=" * 50)
    print("🧹 清理和退出")
    print("=" * 50)
    
    try:
        if page2:
            page2.close()
            print("✅ 作家专区页面已关闭")
    except Exception as e:
        print(f"⚠️ 关闭作家专区页面时出错: {e}")
        pass
    
    # 自动关闭浏览器连接
    try:
        print("🔄 自动关闭浏览器连接...")
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            print("✅ 浏览器连接已自动关闭")
        except Exception as e:
            print(f"⚠️ 关闭浏览器连接时出错: {e}")
    except Exception as e:
        print(f"⚠️ 关闭浏览器连接时发生异常: {e}")