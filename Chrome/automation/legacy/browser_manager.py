"""
番茄小说自动发布系统 - 浏览器管理模块
处理浏览器连接、导航和页面管理
"""

import os
import sys
import time
import threading
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple

from .config import CONFIG
from .utils import safe_click


def connect_to_browser():
    """连接浏览器 - 全自动集成版本（同步执行，避免线程安全问题）"""
    print(f"🔗 尝试连接浏览器 (调试端口: {CONFIG['debug_port']})...")
    
    try:
        from ..utils.auto_browser_manager import auto_connect_to_browser
        
        debug_port = CONFIG['debug_port']
        print(f"🤖 启动自动化浏览器管理器 (端口: {debug_port})...")
        
        # 使用自动化连接管理器，增加重试次数
        # 直接同步调用，避免跨线程传递Playwright对象
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
        
    except Exception as e:
        print(f"❌ 连接时发生异常: {e}")
        import traceback
        traceback.print_exc()
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
        # 使用更宽松的等待策略：只等待 domcontentloaded，不等待 load 事件
        for attempt in range(3):
            try:
                print(f"  尝试导航到番茄网站 (第 {attempt + 1} 次)...")
                # 使用 commit 策略：只要开始加载 DOM 就认为成功
                # 避免等待 load 事件导致的超时问题
                page1.goto("https://fanqienovel.com/", wait_until="domcontentloaded", timeout=30000)
                
                # 验证页面是否真的加载成功（检查 URL）
                current_url = page1.url
                if "fanqienovel.com" in current_url:
                    print(f"✅ 已打开番茄小说首页 (URL: {current_url})")
                    break
                else:
                    print(f"⚠️ URL 不符合预期: {current_url}")
                    if attempt == 2:
                        raise Exception(f"导航失败，当前 URL: {current_url}")
            except Exception as nav_error:
                print(f"  第 {attempt + 1} 次导航失败: {nav_error}")
                
                # 检查页面是否实际上已经加载成功
                try:
                    if "fanqienovel.com" in page1.url:
                        print(f"✅ 检测到页面实际已加载成功，继续执行")
                        print(f"   当前 URL: {page1.url}")
                        break
                except:
                    pass
                
                if attempt == 2:  # 最后一次尝试
                    print("❌ 所有导航尝试都失败")
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
                
                # 定义应该保留的页面模式
                should_keep = False
                
                # 保留所有番茄小说相关的页面
                if 'fanqienovel.com' in url:
                    should_keep = True
                    print(f"  ✅ 保留番茄页面: {url}")
                    # 如果是首页，设为主页
                    if url == 'https://fanqienovel.com/' or url.startswith('https://fanqienovel.com/?'):
                        main_page = page
                
                # 关闭完全无关的页面（about:blank, devtools, 其他网站等）
                if not should_keep and pages_count > 1:
                    print(f"  🔒 关闭非番茄页面: {url}")
                    page.close()
                    pages_count -= 1
                    
            except Exception as e:
                print(f"  ❌ 处理页面 {idx + 1} 时出错: {e}")
        
        # 如果没有找到主页，使用第一个番茄页面
        if 'main_page' not in locals():
            for page in default_context.pages:
                try:
                    if 'fanqienovel.com' in page.url:
                        main_page = page
                        print(f"  📍 使用主页: {page.url}")
                        break
                except:
                    continue
        
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
            # 使用 domcontentloaded 策略避免超时
            page1.goto("https://fanqienovel.com/", wait_until="domcontentloaded", timeout=30000)
            
            # 验证导航是否成功
            if "fanqienovel.com" not in page1.url:
                print(f"⚠️ 导航后 URL 不符合预期: {page1.url}")
        
        # 检查页面标题
        page_title = page1.title()
        print(f"📄 页面标题: {page_title}")
        
        if '番茄小说' not in page_title:
            print("⚠️ 当前页面可能不是番茄小说，但继续尝试...")
            print("🔄 强制导航到番茄小说...")
            page1.goto("https://fanqienovel.com/", wait_until="domcontentloaded", timeout=30000)
            
            # 再次验证
            if "fanqienovel.com" not in page1.url:
                print(f"⚠️ 强制导航后仍不符合预期: {page1.url}")
        
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