"""
UI操作辅助模块
提供安全的页面操作、点击、填充等功能
"""

import time
import threading
from typing import Optional
from playwright.sync_api import Locator, Page


class UIHelper:
    """UI操作辅助类"""
    
    def __init__(self, config_loader=None):
        """
        初始化UI辅助器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
    
    def wait_for_enter(self, prompt: str = "按回车键继续...", timeout: Optional[int] = None) -> None:
        """
        等待用户按回车继续，超时后自动继续
        
        Args:
            prompt: 提示信息
            timeout: 超时时间（秒）
        """
        if timeout is None and self.config_loader:
            timeout = self.config_loader.get('basic.auto_continue_delay', 10)
        elif timeout is None:
            timeout = 10
        
        print(f"\n>>> {prompt} ({timeout}秒后自动继续)")
        
        input_received = threading.Event()
        
        def wait_for_input():
            try:
                input()
                input_received.set()
            except:
                pass
        
        input_thread = threading.Thread(target=wait_for_input)
        input_thread.daemon = True
        input_thread.start()
        
        input_received.wait(timeout)
        
        if input_received.is_set():
            print(">>> 用户按回车，继续执行...")
        else:
            print(f">>> 等待超时，自动继续执行...")
    
    def safe_click(self, element: Locator, desc: str = "元素", timeout: Optional[int] = None, retries: int = 3) -> bool:
        """
        安全的点击操作，带有重试和遮挡处理
        
        Args:
            element: 要点击的元素
            desc: 元素描述
            timeout: 超时时间
            retries: 重试次数
            
        Returns:
            是否点击成功
        """
        if timeout is None and self.config_loader:
            timeout = self.config_loader.get_click_timeout()
        elif timeout is None:
            timeout = 15000
        
        for attempt in range(retries):
            try:
                # 滚动元素到视图中
                element.scroll_into_view_if_needed(timeout=5000)
                
                # 等待元素可交互
                element.wait_for(state="visible", timeout=5000)
                
                try:
                    element.click(timeout=timeout)
                    print(f"✓ 成功点击: {desc}")
                    time.sleep(0.3)
                    return True
                except Exception as e:
                    if "intercepts pointer events" in str(e) and attempt < retries - 1:
                        print(f"第{attempt + 1}次点击被遮挡，尝试强制点击...")
                        element.click(force=True, timeout=timeout)
                        print(f"✓ 强制点击成功: {desc}")
                        time.sleep(0.3)
                        return True
                    else:
                        raise e
                        
            except Exception as e:
                print(f"✗ 点击失败 {desc} (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    return False
        return False
    
    def safe_fill(self, element: Locator, text: str, desc: str = "元素", timeout: Optional[int] = None) -> bool:
        """
        安全的填充文本操作
        
        Args:
            element: 要填充的元素
            text: 要填充的文本
            desc: 元素描述
            timeout: 超时时间
            
        Returns:
            是否填充成功
        """
        if timeout is None and self.config_loader:
            timeout = self.config_loader.get_fill_timeout()
        elif timeout is None:
            timeout = 12000
        
        try:
            element.scroll_into_view_if_needed()
            element.click()
            time.sleep(0.3)
            element.fill(text, timeout=timeout)
            print(f"✓ 成功填充: {desc}")
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"✗ 填充失败 {desc}: {e}")
            return False
    
    def scroll_and_click_enhanced(self, page: Page, tab_name: str, target_text: str, max_scrolls: int = 30, scroll_step: int = 300) -> bool:
        """
        增强版：在分类选择模态框中查找目标文本并点击
        
        Args:
            page: 页面对象
            tab_name: 标签页名称
            target_text: 目标文本
            max_scrolls: 最大滚动次数
            scroll_step: 滚动步长
            
        Returns:
            是否点击成功
        """
        try:
            # 首先点击对应的标签页
            tab_locator = page.locator(f".arco-tabs-header-title:has-text('{tab_name}')")
            if tab_locator.count() > 0:
                tab_locator.first.click()
                page.wait_for_timeout(500)
            
            # 定位到当前活动标签页的滚动容器
            active_tab_content = page.locator(".arco-tabs-content-item-active .category-choose-scroll-parent")
            
            if active_tab_content.count() == 0:
                print(f"❌ 未找到活动标签页的滚动容器，标签页: {tab_name}")
                return False
            
            scrollable = active_tab_content.first
            
            # 将鼠标悬停在滚动区域上
            scrollable.hover(timeout=3000)
            
            # 循环查找和滚动
            for i in range(max_scrolls):
                # 在滚动容器内部查找目标
                target = scrollable.locator(f".category-choose-item:has-text('{target_text}')")
                
                if target.count() > 0:
                    print(f"✅ 在'{tab_name}'标签页找到目标: {target_text}")
                    target.first.click()
                    page.wait_for_timeout(300)
                    return True
                
                # 使用鼠标滚轮滚动
                page.mouse.wheel(0, scroll_step)
                page.wait_for_timeout(300)
                
                # 检查是否到达底部
                if i % 5 == 0:
                    current_scroll_pos = page.evaluate("() => window.scrollY")
                    if i > 0 and current_scroll_pos <= 10:
                        print(f"🟡 可能已滚动到底部，停止滚动")
                        break
            
            print(f"🟡 在'{tab_name}'标签页滚动{max_scrolls}次后未找到: '{target_text}'")
            return False
            
        except Exception as e:
            print(f"✗ 在'{tab_name}'标签页操作'{target_text}'时发生错误: {e}")
            return False
    
    def scroll_list_container(self, page: Page) -> None:
        """
        针对列表容器的滚动方法
        
        Args:
            page: 页面对象
        """
        print("使用列表容器进行滚动...")
        
        try:
            # 定位列表容器
            list_container = page.locator('//*[@id="arco-tabs-3-panel-0"]')
            
            if list_container.count() > 0:
                # 获取容器的高度和滚动信息
                container_info = list_container.evaluate('''
                    (element) => {
                        return {
                            scrollHeight: element.scrollHeight,
                            clientHeight: element.clientHeight,
                            scrollTop: element.scrollTop
                        };
                    }
                ''')
                
                scroll_height = container_info['scrollHeight']
                client_height = container_info['clientHeight']
                current_scroll = container_info['scrollTop']
                
                print(f"列表容器 - 总高度: {scroll_height}px, 可视高度: {client_height}px, 当前滚动: {current_scroll}px")
                
                # 如果内容高度大于可视高度，则需要滚动
                if scroll_height > client_height:
                    scroll_steps = 5
                    scroll_step = (scroll_height - client_height) // scroll_steps
                    
                    print(f"将分 {scroll_steps} 步滚动，每步 {scroll_step}px")
                    
                    for step in range(1, scroll_steps + 1):
                        target_scroll = scroll_step * step
                        list_container.evaluate(f'(element, position) => {{ element.scrollTop = position; }}', target_scroll)
                        print(f"滚动到: {target_scroll}px")
                        time.sleep(0.2)
                    
                    # 最后滚动回顶部
                    list_container.evaluate('(element) => { element.scrollTop = 0; }')
                    print("已滚动回顶部")
                else:
                    print("列表容器内容无需滚动")
            else:
                print("未找到列表容器，使用备选滚动方法")
                self.fallback_scroll_method(page)
                
        except Exception as e:
            print(f"列表容器滚动失败: {e}")
            self.fallback_scroll_method(page)
    
    def fallback_scroll_method(self, page: Page) -> None:
        """
        备选滚动方法
        
        Args:
            page: 页面对象
        """
        print("使用备选滚动方法...")
        
        try:
            # 获取视口高度
            viewport_height = page.evaluate('() => window.innerHeight')
            
            # 小幅滚动：每次滚动视口高度的1/8
            scroll_step = viewport_height // 8
            print(f"备选滚动 - 视口高度: {viewport_height}px, 每步滚动: {scroll_step}px")
            
            # 分8次小幅滚动
            for i in range(1, 9):
                scroll_position = scroll_step * i
                page.evaluate(f'(position) => {{ window.scrollTo(0, position); }}', scroll_position)
                time.sleep(0.1)
            
            # 最后回到顶部
            page.evaluate('() => { window.scrollTo(0, 0); }')
            time.sleep(0.3)
            
        except Exception as e:
            print(f"备选滚动方法失败: {e}")
    
    def navigate_to_next_page(self, page: Page, direction: str = "next") -> bool:
        """
        导航到下一页或上一页
        
        Args:
            page: 页面对象
            direction: 方向，"next"或"prev"
            
        Returns:
            是否翻页成功
        """
        try:
            if direction == "next":
                # 下一页选择器
                selectors = [
                    '//*[@id="arco-tabs-6-panel-0"]/div/div/div/div[2]/ul/li[7]/svg',
                    'button:has-text("下一页")',
                    '.arco-pagination-next',
                    '[class*="next"]',
                    'button[aria-label="下一页"]',
                    '//button[contains(text(), "下一页")]',
                    '//span[contains(text(), "下一页")]'
                ]
                button_desc = "下一页按钮"
                disabled_desc = "下一页按钮不可点击，已到达最后一页"
            else:
                # 上一页选择器
                selectors = [
                    '//*[@id="arco-tabs-6-panel-0"]/div/div/div/div[2]/ul/li[1]/svg',
                    'button:has-text("上一页")',
                    '.arco-pagination-prev',
                    '[class*="prev"]',
                    'button[aria-label="上一页"]',
                    '//button[contains(text(), "上一页")]',
                    '//span[contains(text(), "上一页")]'
                ]
                button_desc = "上一页按钮"
                disabled_desc = "上一页按钮不可点击，已到达第一页"
            
            for selector in selectors:
                try:
                    if selector.startswith('//'):
                        button = page.locator(f'xpath={selector}')
                    else:
                        button = page.locator(selector).first
                    
                    if button.count() > 0:
                        # 检查按钮是否被禁用
                        is_disabled = button.get_attribute('disabled') is not None or \
                                      'disabled' in button.get_attribute('class') or \
                                      not button.is_enabled()
                        
                        if is_disabled:
                            print(disabled_desc)
                            return False
                        
                        # 检查按钮是否可见
                        if button.is_visible():
                            if self.safe_click(button, button_desc):
                                time.sleep(1)
                                return True
                        else:
                            print(f"{button_desc}不可见，滑动页面...")
                            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                            time.sleep(0.5)
                            
                            if button.is_visible() and button.is_enabled():
                                if self.safe_click(button, f"{button_desc}(滑动后)"):
                                    time.sleep(1)
                                    return True
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            print(f"未找到可用的{button_desc}")
            return False
            
        except Exception as e:
            print(f"翻页时出错: {e}")
            return False
    
    def check_and_recover_page(self, page: Page) -> bool:
        """
        检查页面状态并尝试恢复
        
        Args:
            page: 页面对象
            
        Returns:
            页面是否可用
        """
        try:
            page.title()
            return True
        except:
            print("页面可能已关闭或失效，尝试重新连接...")
            return False