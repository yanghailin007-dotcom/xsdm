#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说自动上传核心模块
基于 Playwright 实现真实的浏览器自动化上传

使用方法:
    from uploader_core import FanqieUploaderCore
    
    uploader = FanqieUploaderCore()
    uploader.start_browser()
    uploader.login("username", "password")
    uploader.select_or_create_book("书名")
    uploader.upload_chapter(chapter_data)
"""

import os
import json
import time
import random
import re
from typing import Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime

# Playwright 浏览器控制
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright 未安装，请先运行: pip install playwright")
    print("   然后运行: playwright install chromium")


class FanqieUploaderCore:
    """番茄小说上传核心类"""
    
    def __init__(self, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None):
        """
        初始化上传器
        
        Args:
            progress_callback: 进度回调函数 (percent, message)
            log_callback: 日志回调函数 (message, level)
        """
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.book_id: Optional[str] = None
        self.is_logged_in = False
        
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level.upper()}] {message}")
    
    def _update_progress(self, percent: int, message: str):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        self._log(f"[{percent}%] {message}")
    
    def start_browser(self, headless: bool = False, user_data_dir: Optional[str] = None) -> bool:
        """
        启动浏览器
        
        Args:
            headless: 是否无头模式（建议False以便观察）
            user_data_dir: 用户数据目录（保存登录状态）
        """
        if not PLAYWRIGHT_AVAILABLE:
            self._log("Playwright 未安装，无法启动浏览器", "error")
            return False
        
        try:
            self._update_progress(5, "正在启动浏览器...")
            
            self.playwright = sync_playwright().start()
            
            # 浏览器启动参数
            args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
            
            # 如果有用户数据目录，使用它（保存登录状态）
            if user_data_dir and os.path.exists(user_data_dir):
                self._log(f"使用用户数据目录: {user_data_dir}")
                browser_context = self.playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=headless,
                    args=args,
                    viewport={'width': 1280, 'height': 800}
                )
                self.page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
            else:
                self.browser = self.playwright.chromium.launch(
                    headless=headless,
                    args=args
                )
                self.page = self.browser.new_page(viewport={'width': 1280, 'height': 800})
            
            # 隐藏自动化特征
            self.page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)
            
            self._update_progress(10, "浏览器启动成功")
            return True
            
        except Exception as e:
            self._log(f"启动浏览器失败: {e}", "error")
            return False
    
    def navigate_to_login(self) -> bool:
        """导航到登录页面"""
        try:
            self._update_progress(15, "正在打开番茄小说官网...")
            self.page.goto("https://fanqienovel.com", wait_until="networkidle", timeout=30000)
            
            # 检查是否已经登录
            if self._check_logged_in():
                self._update_progress(20, "检测到已登录状态")
                self.is_logged_in = True
                return True
            
            # 点击登录按钮
            login_btn = self.page.locator("text=登录").first
            if login_btn.is_visible():
                login_btn.click()
                self._update_progress(20, "请手动登录账号...")
                return True
            
            return False
            
        except Exception as e:
            self._log(f"导航失败: {e}", "error")
            return False
    
    def _check_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            # 检查是否有用户头像或用户名显示
            avatar = self.page.locator(".avatar, .user-name, [class*='user']").first
            return avatar.is_visible(timeout=3000)
        except:
            return False
    
    def wait_for_login(self, timeout: int = 120) -> bool:
        """
        等待用户手动登录
        
        Args:
            timeout: 超时时间（秒）
        """
        self._log(f"等待登录，请在 {timeout} 秒内完成登录...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_logged_in():
                self.is_logged_in = True
                self._update_progress(30, "登录成功！")
                return True
            time.sleep(1)
        
        self._log("登录超时", "error")
        return False
    
    def navigate_to_author_center(self) -> bool:
        """导航到作者中心"""
        try:
            self._update_progress(35, "正在进入作者中心...")
            
            # 点击作者专区或直接进入
            self.page.goto("https://fanqienovel.com/author", wait_until="networkidle", timeout=30000)
            
            # 等待页面加载
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self._log(f"进入作者中心失败: {e}", "error")
            return False
    
    def get_book_list(self) -> List[Dict]:
        """获取作品列表"""
        books = []
        try:
            # 等待作品列表加载
            self.page.wait_for_selector("[class*='book'], [class*='work'], .book-item, .work-item", timeout=10000)
            
            # 获取所有作品
            book_elements = self.page.locator("[class*='book'], [class*='work'], .book-item, .work-item").all()
            
            for elem in book_elements:
                try:
                    title = elem.locator("[class*='title'], .book-title, h3, h4").first.text_content(timeout=1000)
                    book_id = elem.get_attribute("data-id") or elem.get_attribute("data-book-id")
                    
                    books.append({
                        "title": title.strip() if title else "未知标题",
                        "id": book_id,
                        "element": elem
                    })
                except:
                    pass
            
        except Exception as e:
            self._log(f"获取作品列表失败: {e}", "warning")
        
        return books
    
    def select_or_create_book(self, book_title: str, synopsis: str = "", category: str = "") -> bool:
        """
        选择或创建书籍
        
        Args:
            book_title: 书籍标题
            synopsis: 简介（创建新书时使用）
            category: 分类（创建新书时使用）
        """
        try:
            self._update_progress(40, f"查找作品: {book_title}")
            
            # 获取作品列表
            books = self.get_book_list()
            
            # 查找匹配的作品
            for book in books:
                if book_title in book["title"] or book["title"] in book_title:
                    self.book_id = book["id"]
                    book["element"].click()
                    self._update_progress(45, f"已选择作品: {book['title']}")
                    time.sleep(2)
                    return True
            
            # 没有找到，创建新书
            self._update_progress(42, "未找到现有作品，准备创建新书...")
            return self._create_book(book_title, synopsis, category)
            
        except Exception as e:
            self._log(f"选择/创建作品失败: {e}", "error")
            return False
    
    def _create_book(self, title: str, synopsis: str, category: str) -> bool:
        """创建新书籍"""
        try:
            # 点击创建作品按钮
            create_btn = self.page.locator("text=创建作品, text=新建作品, .create-book, [class*='create']").first
            if create_btn.is_visible():
                create_btn.click()
                time.sleep(2)
            
            # 填写作品信息
            self._update_progress(43, "填写作品信息...")
            
            # 标题
            title_input = self.page.locator("input[placeholder*='标题'], input[name*='title'], #title").first
            if title_input.is_visible():
                title_input.fill(title)
                time.sleep(0.5)
            
            # 简介
            if synopsis:
                synopsis_input = self.page.locator("textarea[placeholder*='简介'], textarea[name*='synopsis'], #synopsis").first
                if synopsis_input.is_visible():
                    synopsis_input.fill(synopsis)
                    time.sleep(0.5)
            
            # 分类
            if category:
                # 点击分类选择器
                category_select = self.page.locator("[class*='category'], [class*='type'], text='选择分类'").first
                if category_select.is_visible():
                    category_select.click()
                    time.sleep(1)
                    # 选择分类
                    self.page.locator(f"text={category}").first.click()
                    time.sleep(0.5)
            
            # 提交创建
            submit_btn = self.page.locator("text=创建, text=确定, text=提交, button[type='submit']").first
            if submit_btn.is_visible():
                submit_btn.click()
                self._update_progress(45, "作品创建成功")
                time.sleep(3)
                return True
            
            return False
            
        except Exception as e:
            self._log(f"创建作品失败: {e}", "error")
            return False
    
    def upload_chapter(self, chapter_data: Dict) -> bool:
        """
        上传单章
        
        Args:
            chapter_data: {
                "chapter_number": int,
                "chapter_title": str,
                "content": str
            }
        """
        try:
            ch_num = chapter_data.get("chapter_number", 0)
            ch_title = chapter_data.get("chapter_title", f"第{ch_num}章")
            content = chapter_data.get("content", "")
            
            self._log(f"开始上传第{ch_num}章: {ch_title}")
            
            # 1. 点击新建章节
            new_chapter_btn = self.page.locator(
                "text=新建章节, text=添加章节, text=写新章节, "
                "[class*='new-chapter'], [class*='add-chapter'], "
                "button:has-text('章节'), a:has-text('章节')"
            ).first
            
            if new_chapter_btn.is_visible():
                new_chapter_btn.click()
                time.sleep(2)
            
            # 2. 填写章节标题
            title_input = self.page.locator(
                "input[placeholder*='标题'], input[name*='title'], "
                "input[name*='chapter'], #chapter-title"
            ).first
            
            if title_input.is_visible():
                # 清空并填写
                title_input.fill("")
                time.sleep(0.2)
                title_input.fill(ch_title)
                time.sleep(0.5)
            
            # 3. 填写正文
            content_editor = self.page.locator(
                "textarea[placeholder*='正文'], textarea[name*='content'], "
                "div[contenteditable='true'], .editor, #editor"
            ).first
            
            if content_editor.is_visible():
                # 处理内容格式
                formatted_content = self._format_content(content)
                
                # 逐段输入（模拟人工）
                paragraphs = formatted_content.split('\n')
                for i, para in enumerate(paragraphs):
                    if para.strip():
                        if i > 0:
                            content_editor.press("Enter")
                            time.sleep(0.1)
                        content_editor.type(para, delay=random.randint(20, 50))
                        time.sleep(random.uniform(0.1, 0.3))
            
            # 4. 保存草稿或直接发布
            # 先保存草稿
            save_btn = self.page.locator(
                "text=保存草稿, text=存草稿, .save-draft, [class*='save']"
            ).first
            
            if save_btn.is_visible():
                save_btn.click()
                time.sleep(2)
            
            # 5. 发布章节
            publish_btn = self.page.locator(
                "text=发布, text=立即发布, text=确认发布, "
                "button:has-text('发布'), .publish, [class*='publish']"
            ).first
            
            if publish_btn.is_visible():
                publish_btn.click()
                self._log(f"✅ 第{ch_num}章发布成功")
                time.sleep(3)
                return True
            else:
                self._log(f"⚠️ 未找到发布按钮，可能已自动保存", "warning")
                return True
            
        except Exception as e:
            self._log(f"上传第{ch_num}章失败: {e}", "error")
            return False
    
    def _format_content(self, content: str) -> str:
        """格式化正文内容"""
        # 移除多余的空白
        content = re.sub(r'\n{3,}', '\n\n', content)
        # 统一段落格式
        paragraphs = content.split('\n')
        formatted = []
        for para in paragraphs:
            para = para.strip()
            if para:
                formatted.append(para)
        return '\n'.join(formatted)
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self._log("浏览器已关闭")
        except Exception as e:
            self._log(f"关闭浏览器失败: {e}", "warning")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 兼容旧的 FanqieUploader 接口
class FanqieUploaderAdapter:
    """适配器类，兼容 fanqie_uploader.py 的接口"""
    
    def __init__(self, progress_callback=None, log_callback=None):
        self.core = FanqieUploaderCore(progress_callback, log_callback)
        self.novel_title = None
        
    def start_upload(self, novel_title: str, chapters: List[Dict], upload_config: Dict = None) -> bool:
        """
        开始上传（兼容旧接口）
        
        Args:
            novel_title: 小说标题
            chapters: 章节列表
            upload_config: 上传配置
        """
        self.novel_title = novel_title
        upload_config = upload_config or {}
        
        try:
            # 1. 启动浏览器
            headless = upload_config.get('headless', False)
            user_data_dir = upload_config.get('user_data_dir')
            
            if not self.core.start_browser(headless=headless, user_data_dir=user_data_dir):
                return False
            
            # 2. 导航到登录页面
            if not self.core.navigate_to_login():
                return False
            
            # 3. 等待登录（如果未登录）
            if not self.core.is_logged_in:
                if not self.core.wait_for_login(timeout=120):
                    return False
            
            # 4. 进入作者中心
            if not self.core.navigate_to_author_center():
                return False
            
            # 5. 选择或创建书籍
            # 从章节数据中获取简介（如果有）
            synopsis = upload_config.get('synopsis', '')
            category = upload_config.get('category', '')
            
            if not self.core.select_or_create_book(novel_title, synopsis, category):
                return False
            
            # 6. 上传章节
            total = len(chapters)
            for i, chapter in enumerate(chapters):
                progress = 50 + int((i / total) * 50)
                self.core._update_progress(progress, f"正在上传第{i+1}/{total}章")
                
                if not self.core.upload_chapter(chapter):
                    self.core._log(f"第{i+1}章上传失败", "error")
                    if upload_config.get('stop_on_error', True):
                        return False
                
                # 延迟
                if i < total - 1:
                    delay = random.uniform(
                        upload_config.get('delay_min', 3),
                        upload_config.get('delay_max', 8)
                    )
                    time.sleep(delay)
            
            self.core._update_progress(100, "上传完成！")
            return True
            
        except Exception as e:
            self.core._log(f"上传过程异常: {e}", "error")
            return False
        finally:
            # 保持浏览器打开，让用户可以看到结果
            # 如果需要自动关闭，取消下面的注释
            # self.core.close()
            pass
    
    def close(self):
        """关闭"""
        self.core.close()


if __name__ == "__main__":
    # 测试代码
    print("番茄小说上传核心模块")
    print("=" * 50)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("请先安装 Playwright:")
        print("  pip install playwright")
        print("  playwright install chromium")
        exit(1)
    
    # 简单测试
    uploader = FanqieUploaderCore()
    if uploader.start_browser(headless=False):
        print("✅ 浏览器启动成功")
        uploader.navigate_to_login()
        print("请手动登录...")
        time.sleep(30)  # 给用户30秒登录时间
        uploader.close()
    else:
        print("❌ 浏览器启动失败")
