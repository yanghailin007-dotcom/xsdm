"""
浏览器管理核心模块
负责浏览器连接、导航和基础操作
"""

import time
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from ..utils.ui_helper import UIHelper
from ..utils.config_loader import ConfigLoader


class BrowserManager:
    """浏览器管理器类"""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        初始化浏览器管理器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.ui_helper = UIHelper(config_loader)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def connect_to_browser(self) -> Tuple[Optional[sync_playwright], Optional[Browser], Optional[Page], Optional[BrowserContext]]:
        """
        连接浏览器
        
        Returns:
            (playwright, browser, page, context) 元组
        """
        debug_port = self.config_loader.get_debug_port() if self.config_loader else 9988
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
            else:
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
            
            print(f"✓ 成功连接到浏览器，调试端口: {debug_port}")
            return self.playwright, self.browser, self.page, self.context
            
        except Exception as e:
            print(f"✗ 连接浏览器失败: {e}")
            return None, None, None, None
    
    def navigate_to_fanqie_homepage(self, page: Page) -> bool:
        """
        导航到番茄小说首页
        
        Args:
            page: 页面对象
            
        Returns:
            是否导航成功
        """
        try:
            page.goto("https://fanqienovel.com/")
            
            # 检查是否在番茄小说页面
            page_title = page.title()
            if '番茄小说' not in page_title:
                print(f"当前页面不是番茄小说: {page_title}")
                print("请确保已打开番茄小说网站")
                page.goto("https://fanqienovel.com/")
                return False
            
            print("✓ 已导航到番茄小说首页")
            return True
            
        except Exception as e:
            print(f"导航到番茄小说首页失败: {e}")
            return False
    
    def navigate_to_writer_platform(self, page: Page, context: BrowserContext) -> Optional[Page]:
        """
        导航到作家专区
        
        Args:
            page: 主页面对象
            context: 浏览器上下文
            
        Returns:
            作家专区页面对象
        """
        print("尝试打开作家专区...")
        try:
            with page.expect_popup() as page2_info:
                # 尝试多种选择器定位作家专区链接
                selectors = [
                    'xpath=//*[@id="app"]/div/div[1]/div/div[2]/div[5]/a',
                    'a:has-text("作家专区")',
                    'text=作家专区'
                ]
                
                for selector in selectors:
                    try:
                        page.locator(selector).first.click(timeout=3000)
                        break
                    except:
                        continue
                else:
                    print("未找到作家专区链接，请手动打开作家专区页面")
                    self.ui_helper.wait_for_enter("请手动打开作家专区页面后按回车继续...", timeout=15)
                    # 假设用户已手动打开，尝试获取当前标签页
                    if len(context.pages) > 1:
                        return context.pages[1]
                    else:
                        print("无法获取作家专区页面")
                        return None
            
            writer_page = page2_info.value
            
        except:
            print("打开作家专区失败，尝试使用现有页面")
            if len(context.pages) > 1:
                writer_page = context.pages[1]
            else:
                writer_page = page
        
        # 导航到工作台和小说页面
        print("导航到工作台和小说页面...")
        try:
            writer_page.wait_for_load_state("domcontentloaded")
            
            # 尝试点击工作台
            workbench_selectors = [
                'xpath=//*[@id="root"]/div[2]/div/div[3]/div[1]/div[1]/div[2]/button[1]',
                'button:has-text("工作台")',
                'text=工作台'
            ]
            
            for selector in workbench_selectors:
                if self.ui_helper.safe_click(writer_page.locator(selector).first, "工作台"):
                    break
            else:
                print("未找到工作台按钮")
            
            time.sleep(2)
            
            # 尝试点击小说
            novel_selectors = [
                'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
                'text=小说',
                'span:has-text("小说")'
            ]
            
            for selector in novel_selectors:
                if self.ui_helper.safe_click(writer_page.locator(selector).first, "小说"):
                    break
            else:
                print("未找到小说按钮")
            
            print("✓ 已导航到作家专区小说管理页面")
            return writer_page
            
        except Exception as e:
            print(f"导航失败: {e}")
            self.ui_helper.wait_for_enter("请手动导航到小说管理页面后按回车继续...", timeout=15)
            return writer_page
    
    def ensure_novel_management_page(self, page: Page) -> bool:
        """
        确保在小说管理页面
        
        Args:
            page: 页面对象
            
        Returns:
            是否成功导航到小说管理页面
        """
        try:
            # 检查是否已经在小说管理页面
            novel_tab_indicators = [
                '//span[text()="小说"]',
                'text=小说',
                '[class*="novel"]',
            ]
            
            for indicator in novel_tab_indicators:
                if page.locator(indicator).count() > 0:
                    return True
            
            # 如果不在，点击小说标签
            novel_selectors = [
                'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
                'text=小说',
                'span:has-text("小说")'
            ]
            
            for selector in novel_selectors:
                if self.ui_helper.safe_click(page.locator(selector).first, "小说标签"):
                    time.sleep(3)
                    return True
            
            return False
            
        except Exception as e:
            print(f"确保小说管理页面时出错: {e}")
            return False
    
    def cleanup_extra_pages(self, context: BrowserContext) -> None:
        """
        清理多余的页面，只保留番茄小说首页
        
        Args:
            context: 浏览器上下文
        """
        pages = context.pages
        pages_count = len(pages)
        
        for idx, page in enumerate(pages):
            try:
                url = page.url
                if page.url != 'https://fanqienovel.com/':
                    if pages_count != 1:
                        print(f"正在关闭第 {idx + 1} 个页面：{url}")
                        page.close()
                else:
                    print(f"保留 第 {idx + 1} 个页面：{url}")
            except Exception as e:
                print(f"关闭第 {idx + 1} 个页面时出错：{e}")
    
    def verify_current_book_by_header(self, page: Page, expected_book_title: str) -> bool:
        """
        通过发布页面的头部元素验证当前书籍
        
        Args:
            page: 页面对象
            expected_book_title: 期望的书籍标题
            
        Returns:
            是否验证成功
        """
        try:
            # 等待页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 查找发布页面的书籍名称元素
            book_name_elements = page.locator('.publish-header-book-name')
            if book_name_elements.count() > 0:
                actual_title = book_name_elements.first.text_content().strip()
                if expected_book_title in actual_title:
                    print(f"✓ 通过头部元素验证成功: 当前在书籍《{actual_title}》页面")
                    return True
                else:
                    print(f"✗ 书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                    return False
            else:
                print("⚠ 未找到发布页面头部书籍名称元素")
                return False
                
        except Exception as e:
            print(f"通过头部元素验证当前书籍时出错: {e}")
            return False
    
    def verify_current_book(self, page: Page, expected_book_title: str) -> bool:
        """
        验证当前页面是否在正确的书籍详情页
        
        Args:
            page: 页面对象
            expected_book_title: 期望的书籍标题
            
        Returns:
            是否验证成功
        """
        try:
            # 等待页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 尝试多种选择器查找书籍标题
            title_selectors = [
                'h1',
                '.book-title',
                '.title',
                '[class*="title"]',
                '[class*="book"] h1',
                '[class*="book"] [class*="title"]'
            ]
            
            for selector in title_selectors:
                try:
                    title_elements = page.locator(selector)
                    if title_elements.count() > 0:
                        for i in range(title_elements.count()):
                            actual_title = title_elements.nth(i).text_content().strip()
                            if actual_title and expected_book_title in actual_title:
                                print(f"✓ 验证成功: 当前在书籍《{actual_title}》详情页")
                                return True
                except:
                    continue
            
            print(f"⚠ 无法验证当前书籍，期望: {expected_book_title}")
            return False
            
        except Exception as e:
            print(f"验证当前书籍时出错: {e}")
            return False
    
    def close_browser(self) -> None:
        """关闭浏览器连接"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("✓ 浏览器连接已关闭")
        except Exception as e:
            print(f"关闭浏览器连接时出错: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
    
    def get_browser_config(self) -> dict:
        """
        获取浏览器配置
        
        Returns:
            浏览器配置字典
        """
        if self.config_loader:
            return self.config_loader.get_browser_config()
        return {
            "headless": False,
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }