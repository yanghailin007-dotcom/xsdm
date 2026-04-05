#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说上传实现
复用原有的 upload_script.py 逻辑
"""

import os
import sys
import json
import time
import random
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime, timedelta

# 调试端口
DEBUG_PORT = 9988
MAX_RETRY = 3


class FanqieUploaderImpl:
    """番茄小说上传实现类"""
    
    def __init__(self, 
                 novel_title: str = "",
                 novel_config: Optional[Dict[str, Any]] = None,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None,
                 pause_check_callback: Optional[Callable] = None):
        self.novel_title = novel_title
        self.novel_config = novel_config or {}
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.pause_check_callback = pause_check_callback  # 暂停检查回调
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = []
        self.book_id = None
        self.is_running = True
        self.book_created = False  # 标记是否自动创建了书籍
        
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _check_pause(self):
        """检查是否暂停，如果暂停则等待"""
        if self.pause_check_callback:
            self.pause_check_callback()
    
    def _random_sleep(self, min_sec: float = 0.3, max_sec: float = 1.2):
        """随机延迟，模拟人类操作"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay
    
    def _human_type(self, element, text: str, min_delay: float = 0.01, max_delay: float = 0.05):
        """模拟人类打字，逐个字符输入"""
        element.fill("")
        self._random_sleep(0.1, 0.3)
        
        # 对于短文本直接填充，长文本使用逐字输入
        if len(text) <= 20:
            element.fill(text)
        else:
            # 分段输入，模拟真实打字
            chunk_size = random.randint(3, 8)
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i+chunk_size]
                element.type(chunk, delay=random.uniform(min_delay, max_delay))
                self._random_sleep(0.05, 0.15)
    
    def _progress(self, percent: int, message: str):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        self._log(f"[{percent}%] {message}")
    
    def connect_chrome(self, port: int = None) -> bool:
        """连接 Chrome（优先复用现有页面，不创建新页面）
        
        Args:
            port: Chrome 调试端口，默认使用 DEBUG_PORT
        """
        try:
            from playwright.sync_api import sync_playwright
            
            target_port = port if port else DEBUG_PORT
            
            self._progress(10, f"正在连接 Chrome (端口: {target_port})...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{target_port}")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                all_pages = contexts[0].pages
                
                # 🔥 优先查找已打开的番茄相关页面（发布页、章节管理页）
                target_page = None
                book_id = self.book_id
                
                for page in all_pages:
                    url = page.url
                    # 优先顺序：发布页 > 章节管理页 > 番茄其他页
                    if book_id and f"/{book_id}/publish/" in url:
                        target_page = page
                        self._log(f"  复用已打开的发布页")
                        break
                    elif book_id and f"/chapter-manage/{book_id}" in url:
                        target_page = page
                        self._log(f"  复用已打开的章节管理页")
                        break
                    elif "fanqienovel.com/main/writer" in url:
                        # 如果URL包含书籍ID，记录下来
                        if not book_id:
                            import re
                            match = re.search(r'/writer/\d+/publish/', url)
                            if match:
                                extracted_id = match.group(0).split('/')[3]
                                self.book_id = extracted_id
                                target_page = page
                                self._log(f"  从页面URL提取book_id: {extracted_id}")
                                break
                            match = re.search(r'/chapter-manage/(\d+)', url)
                            if match:
                                self.book_id = match.group(1)
                                target_page = page
                                break
                        target_page = page
                        self._log(f"  复用已打开的作者后台")
                        break
                
                # 如果没有找到番茄页面，使用第一个非空白页面
                if not target_page:
                    for page in all_pages:
                        if page.url not in ["about:blank", "chrome://newtab/"]:
                            target_page = page
                            break
                    if not target_page:
                        target_page = all_pages[0]
                
                self.page = target_page
            else:
                self.page = self.browser.new_page()
            
            self._progress(20, "已连接到 Chrome")
            return True
        except Exception as e:
            self._log(f"连接 Chrome 失败: {e}", "error")
            self._log("请确保：1. 已启动对应账户的浏览器 2. 浏览器窗口保持打开", "warning")
            return False
    
    def check_login(self) -> bool:
        """检查登录状态（避免重复导航）"""
        try:
            self._progress(25, "检查登录状态...")
            
            current_url = self.page.url
            
            # 如果当前已经在番茄作者后台页面，直接认为已登录
            if "/main/writer" in current_url:
                self._log("  当前已在作者后台，已登录")
                return True
            
            # 如果当前在 fanqienovel.com 域名下，检查是否跳转到了登录页
            if "fanqienovel.com" in current_url:
                if "login" in current_url.lower():
                    self._log("未登录番茄小说（跳转到登录页），请在 Chrome 中登录", "warning")
                    return False
                # 已经在番茄页面但不是登录页，可能已登录
                self._log("  当前在番茄页面，检查登录状态...")
            else:
                # 先访问首页检查登录状态
                self.page.goto("https://fanqienovel.com", timeout=30000)
                time.sleep(2)
                current_url = self.page.url
            
            # 检查是否有登录按钮或用户头像
            # 方法1: 检查URL是否跳转到登录页
            if "login" in current_url.lower():
                self._log("未登录番茄小说（跳转到登录页），请在 Chrome 中登录", "warning")
                return False
            
            # 方法2: 检查页面中是否有登录按钮
            try:
                login_button = self.page.locator('a[href*="login"], .login-btn, [data-e2e="login-button"]').first
                if login_button.is_visible(timeout=3000):
                    self._log("未登录番茄小说（发现登录按钮），请在 Chrome 中登录", "warning")
                    return False
            except:
                pass
            
            # 方法3: 检查是否有用户头像或用户名
            try:
                user_avatar = self.page.locator('.avatar, .user-avatar, [data-e2e="user-avatar"]').first
                if not user_avatar.is_visible(timeout=3000):
                    # 没有头像，可能未登录，再尝试访问作者后台确认
                    pass
            except:
                pass
            
            # 方法4: 尝试访问作者后台确认（如果当前不在番茄页面）
            current_url = self.page.url
            if "/main/writer" not in current_url:
                self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
                time.sleep(2)
                current_url = self.page.url
            
            if "login" in current_url.lower():
                self._log("未登录番茄小说（访问后台被拦截），请在 Chrome 中登录", "warning")
                return False
            
            # 检查是否有"创建作品"或"书籍管理"等元素
            try:
                writer_elements = self.page.locator('.writer-page, .book-manage, [data-e2e="writer-page"]').first
                if not writer_elements.is_visible(timeout=3000):
                    self._log("可能未登录或页面加载异常，请在 Chrome 中确认登录状态", "warning")
                    # 不直接返回False，让上层决定是否需要等待登录
            except:
                pass
            
            self._progress(30, "已登录番茄小说")
            return True
        except Exception as e:
            self._log(f"检查登录失败: {e}", "error")
            return False
    
    def wait_for_login(self, timeout: int = 120) -> bool:
        """等待用户登录（减少导航频率）"""
        self._log(f"等待登录，请在 {timeout} 秒内完成登录...")
        
        start_time = time.time()
        last_check_time = 0
        
        while time.time() - start_time < timeout:
            if not self.is_running:
                return False
            
            try:
                # 每5秒检查一次，减少导航频率
                if time.time() - last_check_time < 5:
                    time.sleep(0.5)
                    continue
                last_check_time = time.time()
                
                # 如果已经在番茄后台，说明已登录
                current_url = self.page.url
                if "/main/writer" in current_url:
                    self._progress(30, "登录成功！")
                    return True
                
                # 不在番茄后台，才需要导航
                if not current_url.startswith("https://fanqienovel.com/login"):
                    self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=10000)
                    time.sleep(2)
                    current_url = self.page.url
                
                if not current_url.startswith("https://fanqienovel.com/login"):
                    self._progress(30, "登录成功！")
                    return True
            except:
                pass
            time.sleep(1)
        
        self._log("登录超时", "error")
        return False
    
    def find_book(self) -> bool:
        """查找书籍，找不到则自动创建"""
        try:
            self._progress(35, f"查找书籍: {self.novel_title}")
            
            # 先检查番茄平台上是否已有该书
            existing_url = self._check_book_exists_on_fanqie()
            if existing_url:
                self._progress(40, "找到已有书籍")
                return True
            
            # 未找到书籍，自动创建
            self._log("未找到书籍，准备自动创建...", "warning")
            return self.create_book()
            
        except Exception as e:
            self._log(f"查找书籍失败: {e}", "error")
            return False
    
    def create_book(self) -> bool:
        """自动创建新书 - 复用 web 端完整逻辑"""
        try:
            self._progress(36, "正在创建新书...")
            self._log(f"开始创建书籍: {self.novel_title}")
            
            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self._log(f"访问创建作品页面... (尝试 {attempt + 1}/{max_retries})")
                    self.page.goto(
                        "https://fanqienovel.com/main/writer/create?enter_from=home",
                        timeout=30000, wait_until="domcontentloaded"
                    )
                    time.sleep(2)
                    
                    current_url = self.page.url
                    if "fanqienovel.com" not in current_url:
                        self._log(f"⚠️ 页面可能未正确加载，当前URL: {current_url}")
                        if attempt < max_retries - 1:
                            continue
                    
                    # 检查是否进入新手引导/实名认证页
                    if self._check_for_guide_page():
                        self._log("⚠️ 检测到番茄新手引导或实名认证页面，自动创建被中断", "warning")
                        self._log("👉 请手动在浏览器中完成新手引导/实名认证/作者签约流程，然后再尝试自动上传", "warning")
                        return False
                    
                    break
                except Exception as e:
                    self._log(f"⚠️ 导航失败 (尝试 {attempt + 1}): {str(e)[:200]}")
                    if attempt == max_retries - 1:
                        self._log("✗ 所有重试都失败")
                        return False
                    time.sleep(3)
            
            # ===== 1. 填写书名 =====
            title_short = self.novel_title[:14] if len(self.novel_title) > 14 else self.novel_title
            try:
                title_input = self.page.locator('input[placeholder="请输入作品名称"]').first
                title_input.wait_for(state='visible', timeout=5000)
                title_input.fill(title_short)
                self._log(f"✓ 填写书名: {title_short}")
            except Exception as e:
                self._log(f"✗ 填写书名失败: {e}")
                return False
            
            # 准备配置数据
            tags_info = self.novel_config.get("tags_info", {})
            gender = tags_info.get("target_audience", "男频")
            main_character = self.novel_config.get("main_character", "未知主角")
            synopsis = self.novel_config.get("synopsis", "")
            formatted_synopsis = self._format_synopsis(synopsis)
            
            # ===== 2. 选择男女频 =====
            try:
                if gender == "女频":
                    self.page.locator('label:has-text("女频")').first.click()
                    self._log("✓ 选择女频")
                else:
                    self.page.locator('label:has-text("男频")').first.click()
                    self._log("✓ 选择男频")
                time.sleep(0.5)
            except Exception as e:
                self._log(f"⚠ 选择男/女频失败: {e}")
            
            # ===== 3. 选择作品标签 =====
            self._log("准备选择作品标签...")
            try:
                self._select_book_tags_v2(tags_info)
            except Exception as e:
                self._log(f"⚠ 选择作品标签失败: {e}")
            
            # ===== 4. 处理封面 =====
            self._log("准备处理封面...")
            try:
                cover_result = self._handle_cover_upload()
                if not cover_result:
                    self._log("⚠ 封面处理未完成，继续创建...")
            except Exception as e:
                self._log(f"⚠ 封面上传失败: {e}")
            
            # ===== 5. 填写主角名 =====
            character_short = main_character[:5] if len(main_character) >= 5 else main_character
            try:
                character_input = self.page.locator('input[placeholder="请输入主角名1"]').first
                character_input.fill(character_short)
                self._log(f"✓ 填写主角名: {character_short}")
            except Exception as e:
                self._log(f"⚠ 填写主角名失败: {e}")
            
            # ===== 6. 填写作品简介 =====
            synopsis_short = formatted_synopsis[:500] if len(formatted_synopsis) >= 500 else formatted_synopsis
            try:
                synopsis_input = self.page.locator('textarea').first
                synopsis_input.fill(synopsis_short)
                self._log("✓ 填写作品简介")
            except Exception as e:
                self._log(f"⚠ 填写简介失败: {e}")
            
            # ===== 7. 点击立即创建 =====
            self._log("点击立即创建...")
            try:
                create_button = self.page.locator('button:has-text("立即创建")').first
                create_button.wait_for(state='visible', timeout=5000)
                create_button.click()
                self._log("✓ 点击立即创建")
            except Exception as e:
                self._log(f"✗ 点击立即创建失败: {e}")
                return False
            
            # 等待创建完成
            self._log("等待创建完成...")
            time.sleep(3)
            
            create_success = False
            # 检查是否有错误/成功提示
            try:
                error_msg = self.page.locator('.arco-message-content, .error-message, [class*="error"]').first
                if error_msg.count() > 0 and error_msg.is_visible():
                    error_text = error_msg.text_content() or ""
                    if "成功" in error_text or "success" in error_text.lower():
                        self._log(f"✓ 操作成功提示: {error_text}")
                        create_success = True
                    else:
                        self._log(f"✗ 创建失败，错误信息: {error_text}")
                        return False
            except:
                pass
            
            # 等待跳转到书籍详情页
            for i in range(15):
                time.sleep(1)
                current_url = self.page.url
                if "/main/writer/book/" in current_url or "/main/writer/novel/" in current_url:
                    self._log(f"✓ 书籍创建成功，已跳转到详情页: {current_url}")
                    # 提取 book_id
                    match = re.search(r'/book/(\d+)', current_url)
                    if match:
                        self.book_id = match.group(1)
                    self.book_created = True
                    self._progress(40, f"✅ 书籍创建成功！ID: {self.book_id or 'unknown'}")
                    return True
                if "/main/writer/chapter-manage/" in current_url:
                    book_id = current_url.split("/chapter-manage/")[-1].split("/")[0]
                    if book_id and book_id.isdigit():
                        self.book_id = book_id
                        self.book_created = True
                        self._log(f"✓ 书籍创建成功，已跳转到章节管理页: {current_url}")
                        self._progress(40, f"✅ 书籍创建成功！ID: {self.book_id}")
                        return True
                if "/main/writer/create" in current_url:
                    self._log(f"仍在创建页面，等待中... ({i+1}/15)")
            
            # 如果提示成功但还没跳转，主动到书籍管理页查找
            if create_success:
                self._log("检测到创建成功提示但页面未跳转，主动查找书籍...")
                # 只有在非番茄页面才导航
                if "/main/writer" not in self.page.url:
                    self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
                    time.sleep(3)
                found = self.find_book_in_list()
                if found:
                    self.book_created = True
                    self._progress(40, f"✅ 书籍创建成功！ID: {self.book_id or 'unknown'}")
                return found
            
            # 检查是否已有同名书籍
            page_content = self.page.content()
            if '已存在' in page_content or '重复' in page_content:
                self._log("⚠️ 检测到同名书籍，尝试查找...", "warning")
                if "/main/writer" not in self.page.url:
                    self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
                    time.sleep(3)
                return self.find_book_in_list()
            
            self._log("✗ 等待超时，无法确认创建是否成功")
            return False
            
        except Exception as e:
            self._log(f"创建书籍失败: {e}", "error")
            return False
    
    def find_book_in_list(self) -> bool:
        """在书籍列表中查找"""
        try:
            page_content = self.page.content()
            
            if self.novel_title[:10] in page_content:
                book_ids = re.findall(r'long-article-table-item-(\d+)', page_content)
                if book_ids:
                    self.book_id = book_ids[0]
                    self._progress(40, f"找到书籍ID: {self.book_id}")
                    return True
            
            return False
        except Exception as e:
            self._log(f"查找书籍列表失败: {e}", "error")
            return False
    
    def _check_book_exists_on_fanqie(self) -> Optional[str]:
        """检查番茄平台上是否已有该书（修复URL解析）"""
        import re  # 确保re模块在整个函数中可用
        
        try:
            current_url = self.page.url
            self._log(f"当前页面URL: {current_url}")
            
            if "/chapter-manage/" in current_url:
                # 修复：提取纯数字ID，忽略&后面的参数
                match = re.search(r'/chapter-manage/(\d+)', current_url)
                if match:
                    book_id = match.group(1)
                    if book_id and book_id.isdigit():
                        self.book_id = book_id
                        self._log(f"从章节管理页提取到book_id: {book_id}")
                        return current_url
            
            if "/book-info/" in current_url:
                match = re.search(r'/book-info/(\d+)', current_url)
                if match:
                    book_id = match.group(1)
                    if book_id and book_id.isdigit():
                        self.book_id = book_id
                        self._log(f"从书籍详情页提取到book_id: {book_id}")
                        return f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
            
            # 判断是否需要导航到书籍管理页面
            # 注意：/main/writer/create 也包含 /main/writer，需要排除
            is_on_book_manage = "/book-manage" in current_url
            is_on_chapter_manage = "/chapter-manage/" in current_url
            is_on_book_info = "/book-info/" in current_url
            is_on_writer_pages = "/main/writer" in current_url
            
            if is_on_chapter_manage:
                # 已在章节管理页，直接提取book_id处理
                pass
            elif is_on_book_manage:
                # 已经在书籍管理页面，刷新确保内容最新
                self._log("已在书籍管理页面，刷新页面确保数据最新...")
                self.page.reload(wait_until="networkidle", timeout=15000)
                time.sleep(3)
            elif is_on_book_info:
                # 在书籍详情页，稍后处理
                pass
            elif is_on_writer_pages:
                # 在其他作家后台页面（如创建页），需要导航到书籍管理
                self._log(f"当前在作家后台其他页面({current_url})，导航到书籍管理...")
                self.page.goto("https://fanqienovel.com/main/writer/book-manage",
                             wait_until="networkidle", timeout=15000)
                time.sleep(3)
            else:
                # 完全不在番茄后台页面，需要导航
                self._log("导航到书籍管理页面...")
                self.page.goto("https://fanqienovel.com/main/writer/book-manage",
                             wait_until="networkidle", timeout=15000)
                time.sleep(3)
            
            try:
                title_short = self.novel_title[:10] if self.novel_title else ""
                if not title_short:
                    self._log("错误: 书名为空", "error")
                    return None
                    
                self._log(f"在书籍管理页面查找书名(前10字): {title_short}")
                self._log(f"完整书名: {self.novel_title}")
                
                # 等待页面加载 - 最多重试3次
                for attempt in range(3):
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                        # 等待书籍列表元素出现（即使已存在也继续）
                        self.page.wait_for_selector('.long-article-table-item', state='attached', timeout=10000)
                        break
                    except Exception as e:
                        self._log(f"等待页面加载，尝试 {attempt+1}/3... ({e})")
                        time.sleep(2)
                
                time.sleep(2)
                
                # 获取页面内容
                page_text = self.page.content()
                
                # 调试：显示页面中的一部分文本帮助诊断
                # 查找包含书名的上下文
                title_idx = page_text.find(title_short) if title_short else -1
                if title_idx > 0:
                    context_start = max(0, title_idx - 50)
                    context_end = min(len(page_text), title_idx + 100)
                    self._log(f"DEBUG: 找到书名上下文: ...{page_text[context_start:context_end]}...")
                else:
                    # 尝试查找部分书名
                    for i in range(min(8, len(self.novel_title) if self.novel_title else 0), 0, -1):
                        partial = self.novel_title[:i]
                        if partial in page_text:
                            self._log(f"DEBUG: 找到部分书名 '{partial}'")
                            break
                    self._log(f"DEBUG: 书名前10字'{title_short}'不在页面内容中")
                
                # 首先检查书名是否在页面中
                if title_short not in page_text and self.novel_title[:8] not in page_text:
                    self._log(f"书名'{title_short}'不在当前页面，可能需要翻页或书籍不存在")
                    return None
                
                # 提取所有书籍ID
                book_ids = re.findall(r'long-article-table-item-(\d+)', page_text)
                self._log(f"找到 {len(book_ids)} 本书籍，ID列表: {book_ids[:5]}...")  # 只显示前5个
                
                if book_ids:
                    # 清理书名用于比较（去除多余空格）
                    novel_title_clean = self.novel_title.strip() if self.novel_title else ""
                    novel_title_lower = novel_title_clean.lower()
                    
                    # 优先精确匹配
                    for book_id in book_ids:
                        try:
                            book_elem = self.page.locator(f'#long-article-table-item-{book_id}').first
                            if book_elem.count() > 0:
                                # 获取书名 - 可能在 .hoverup 或直接在 .info-content-title 中
                                title_elem = book_elem.locator('.info-content-title .hoverup, .info-content-title').first
                                if title_elem.count() > 0:
                                    title_text = title_elem.text_content().strip()
                                    title_text_clean = ' '.join(title_text.split())  # 规范化空格
                                    title_lower = title_text_clean.lower()
                                    self._log(f"检查书籍ID {book_id}: {title_text[:25]}...")
                                    
                                    # 多种匹配策略（从精确到宽松）
                                    matched = False
                                    
                                    # 策略1: 完整包含
                                    if novel_title_clean in title_text_clean or title_text_clean in novel_title_clean:
                                        matched = True
                                        self._log(f"  -> 策略1匹配: 完整包含")
                                    # 策略2: 前10字符匹配
                                    elif (novel_title_clean[:10] in title_text_clean or 
                                          title_text_clean[:10] in novel_title_clean):
                                        matched = True
                                        self._log(f"  -> 策略2匹配: 前10字符")
                                    # 策略3: 前8字符匹配
                                    elif (len(novel_title_clean) >= 8 and 
                                          novel_title_clean[:8] in title_text_clean):
                                        matched = True
                                        self._log(f"  -> 策略3匹配: 前8字符")
                                    # 策略4: 忽略大小写匹配（对于英文书名）
                                    elif novel_title_lower == title_lower:
                                        matched = True
                                        self._log(f"  -> 策略4匹配: 忽略大小写")
                                    
                                    if matched:
                                        url = f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
                                        self.book_id = book_id
                                        self._log(f"✓ 成功匹配书籍ID {book_id}: {title_text}")
                                        return url
                        except Exception as e:
                            self._log(f"检查书籍ID {book_id} 时出错: {e}")
                            continue
                    
                    # 如果没找到匹配，记录警告
                    self._log(f"⚠ 在页面找到 {len(book_ids)} 本书，但没有匹配'{novel_title_clean}'的书")
                    
            except Exception as e:
                self._log(f"页面检查失败: {e}")
            
            return None
        except Exception as e:
            self._log(f"检查书籍存在性时出错: {e}")
            return None
    
    def _format_synopsis(self, text: str, max_length: int = 500) -> str:
        """针对番茄小说优化简介排版"""
        if not text or len(text.strip()) == 0:
            return ""
        
        text = re.sub(r'\s+', ' ', text.strip())
        
        tag_line = ""
        tag_match = re.search(r'^(\[[^\]]+\])', text)
        if tag_match:
            tag_line = tag_match.group(1)
            text = text.replace(tag_line, "").strip()
        
        if not tag_line:
            tag_line = "[系统+爽文]"
        
        original_synopsis = text
        sentences = re.split(r'([。！？])', original_synopsis)
        processed_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                if sentence.strip():
                    processed_sentences.append(sentence.strip())
        
        if not processed_sentences:
            processed_sentences = [s.strip() for s in original_synopsis.split('。') if s.strip()]
            processed_sentences = [s + '。' for s in processed_sentences]
        
        formatted_lines = [tag_line, ""]
        formatted_lines.extend(processed_sentences)
        formatted_text = '\n'.join(formatted_lines)
        
        if len(formatted_text) > max_length:
            formatted_text = formatted_text[:max_length]
        
        return formatted_text
    
    def _select_book_tags_v2(self, tags_info: Dict[str, Any]) -> bool:
        """选择作品标签 - V2版本（适配番茄最新界面）"""
        self._log("[Tags] 开始选择作品标签...")
        
        try:
            tag_selector = self.page.locator('.select-row, .select-view, [placeholder*="请选择作品标签"]').first
            if tag_selector.count() == 0:
                self._log("[Tags] 未找到标签选择器")
                return False
            
            tag_selector.click()
            self._log("[Tags] 已点击标签选择器")
            time.sleep(2)
            
            main_category = tags_info.get("main_category", "")
            themes = tags_info.get("themes", [])
            roles = tags_info.get("roles", [])
            plots = tags_info.get("plots", [])
            
            self._log(f"[Tags] 需要选择的标签: 主分类={main_category}, 主题={themes}, 角色={roles}, 情节={plots}")
            
            if main_category:
                if self._click_tag_in_modal("主分类", main_category):
                    self._log(f"[Tags] ✓ 选择主分类: {main_category}")
                else:
                    self._log(f"[Tags] ⚠ 未找到主分类: {main_category}")
            
            selected_themes = 0
            for theme in themes[:3]:
                if self._click_tag_in_modal("主题", theme):
                    self._log(f"[Tags] ✓ 选择主题: {theme}")
                    selected_themes += 1
                    time.sleep(0.3)
                else:
                    self._log(f"[Tags] ⚠ 未找到主题: {theme}")
            
            selected_roles = 0
            for role in roles[:3]:
                if self._click_tag_in_modal("角色", role):
                    self._log(f"[Tags] ✓ 选择角色: {role}")
                    selected_roles += 1
                    time.sleep(0.3)
                else:
                    self._log(f"[Tags] ⚠ 未找到角色: {role}")
            
            selected_plots = 0
            for plot in plots[:3]:
                if self._click_tag_in_modal("情节", plot):
                    self._log(f"[Tags] ✓ 选择情节: {plot}")
                    selected_plots += 1
                    time.sleep(0.3)
                else:
                    self._log(f"[Tags] ⚠ 未找到情节: {plot}")
            
            try:
                confirm_btn = self.page.locator('button:has-text("确认"), button:has-text("确定"), .arco-btn-primary').filter(
                    has_text=re.compile(r'(确认|确定)')
                ).first
                if confirm_btn.count() > 0:
                    confirm_btn.click(timeout=5000, force=True)
                    self._log("[Tags] ✓ 点击确认按钮")
                    time.sleep(1)
                else:
                    self.page.keyboard.press("Escape")
                    self._log("[Tags] 按ESC关闭标签弹窗")
            except Exception as e:
                self._log(f"[Tags] 关闭标签弹窗时出错: {e}")
            
            return True
            
        except Exception as e:
            self._log(f"[Tags] 选择标签时出错: {e}")
            return False
    
    def _click_tag_in_modal(self, category: str, tag_name: str) -> bool:
        """在标签弹窗中点击指定标签"""
        self._log(f"[Tags] 正在切换分类到: {category}，准备点击标签: {tag_name}")
        try:
            tab_selectors = [
                f'.arco-tabs-header-title:has-text("{category}")',
                f'[role="tab"]:has-text("{category}")',
                f'text="{category}" >> xpath=ancestor::*[@role="tab" or contains(@class, "arco-tabs-header-title")]',
            ]
            
            tab_clicked = False
            for selector in tab_selectors:
                try:
                    tab = self.page.locator(selector).first
                    if tab.count() > 0 and tab.is_visible():
                        tab.click(timeout=5000, force=True)
                        tab_clicked = True
                        self._log(f"[Tags] 已点击分类 tab: {category}")
                        time.sleep(0.5)
                        break
                except Exception as e:
                    self._log(f"[Tags] tab 选择器 {selector} 失败: {e}")
                    continue
            
            if not tab_clicked:
                self._log(f"[Tags] ⚠ 未能点击分类 tab: {category}，尝试直接查找标签")
            
            selectors = [
                f'.category-choose-item:has-text("{tag_name}")',
                f'.tag-item:has-text("{tag_name}")',
                f'text="{tag_name}"',
                f'[role="tabpanel"] >> text="{tag_name}"',
            ]
            
            for selector in selectors:
                try:
                    tag = self.page.locator(selector).first
                    if tag.count() > 0 and tag.is_visible():
                        tag.click(timeout=5000, force=True)
                        self._log(f"[Tags] 直接点击标签成功: {tag_name} (selector={selector})")
                        time.sleep(0.3)
                        return True
                except Exception as e:
                    self._log(f"[Tags] 直接选择器 {selector} 失败: {e}")
                    continue
            
            # 滚动查找
            self._log(f"[Tags] 尝试滚动查找标签: {tag_name}")
            for scroll_attempt in range(10):
                try:
                    scroll_container = self.page.locator('.category-choose-scroll-parent, .arco-tabs-content-item-active').first
                    if scroll_container.count() == 0:
                        self._log("[Tags] 未找到滚动容器")
                        break
                    tag = scroll_container.locator(f'.category-choose-item:has-text("{tag_name}")').first
                    if tag.count() > 0 and tag.is_visible():
                        tag.click(timeout=5000, force=True)
                        self._log(f"[Tags] 滚动后点击标签成功: {tag_name}")
                        time.sleep(0.3)
                        return True
                    # 短超时滚动，防止卡死 30 秒
                    scroll_container.evaluate('el => el.scrollTop += 200', timeout=3000)
                    time.sleep(0.3)
                except Exception as e:
                    self._log(f"[Tags] 滚动查找第 {scroll_attempt+1} 次失败: {e}")
                    time.sleep(0.3)
            
            self._log(f"[Tags] 尝试通过 page.evaluate 直接点击标签: {tag_name}")
            try:
                clicked = self.page.evaluate(f'''(tagName) => {{
                    const titles = document.querySelectorAll('.category-choose-item-title');
                    for (const title of titles) {{
                        if (title.textContent.trim() === tagName) {{
                            const item = title.closest('.category-choose-item');
                            if (item) {{
                                item.click();
                                return true;
                            }}
                        }}
                    }}
                    const items = document.querySelectorAll('.category-choose-item, .tag-item');
                    for (const item of items) {{
                        const titleEl = item.querySelector('.category-choose-item-title');
                        if (titleEl && titleEl.textContent.trim() === tagName) {{
                            item.click();
                            return true;
                        }}
                        if (item.textContent.trim().startsWith(tagName)) {{
                            item.click();
                            return true;
                        }}
                    }}
                    const xpath = `//div[contains(@class, 'category-choose-item-title') and text()='${{tagName}}']`;
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    const node = result.singleNodeValue;
                    if (node) {{
                        const item = node.closest('.category-choose-item');
                        if (item) {{
                            item.click();
                            return true;
                        }}
                    }}
                    return false;
                }}''', tag_name)
                if clicked:
                    self._log(f"[Tags] evaluate 点击标签成功: {tag_name}")
                else:
                    self._log(f"[Tags] evaluate 未找到标签: {tag_name}")
                return clicked
            except Exception as e:
                self._log(f"[Tags] evaluate 点击标签 '{tag_name}' 失败: {e}")
                return False
            
        except Exception as e:
            self._log(f"[Tags] 点击标签 '{tag_name}' 外层失败: {e}")
            return False
    
    def _handle_cover_upload(self) -> bool:
        """处理封面上传"""
        self._log("[Cover] 开始处理封面...")
        
        project_dir = Path(self.novel_config.get("project_dir", "."))
        novel_title = self.novel_title
        
        cover_paths = [
            project_dir / "cover.png",
            project_dir / "cover.jpg",
            project_dir / "cover.jpeg",
            project_dir / f"{novel_title}_封面.png",
            project_dir / f"{novel_title}_封面.jpg",
            project_dir / "images" / "cover.png",
            project_dir / "images" / "cover.jpg",
        ]
        
        cover_file = None
        for path in cover_paths:
            if path.exists():
                cover_file = path
                break
        
        if not cover_file:
            self._log("[Cover] 在项目目录未找到封面，检查 generated_images 目录...")
            
            username = ""
            try:
                parts = project_dir.parts
                if "小说项目" in parts or "novel_projects" in parts:
                    for i, part in enumerate(parts):
                        if part in ["小说项目", "novel_projects"] and i + 1 < len(parts):
                            username = parts[i + 1]
                            break
            except:
                pass
            
            base_dir = project_dir.parent.parent.parent
            generated_images_dir = base_dir / "generated_images" / username / novel_title
            
            self._log(f"[Cover] 检查目录: {generated_images_dir}")
            
            if generated_images_dir.exists():
                image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
                cover_files = []
                
                for ext in image_extensions:
                    cover_files.extend(generated_images_dir.glob(f'*{ext}'))
                
                if cover_files:
                    cover_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    cover_file = cover_files[0]
                    self._log(f"[Cover] 在 generated_images 找到封面: {cover_file.name}")
        
        if not cover_file:
            self._log("[Cover] ⚠ 未找到封面文件，跳过封面上传")
            return False
        
        self._log(f"[Cover] 找到封面文件: {cover_file}")
        
        try:
            cover_btn = self.page.locator('button:has-text("选择封面"), .left-cover-container button').first
            if cover_btn.count() == 0:
                self._log("[Cover] 未找到'选择封面'按钮")
                return False
            
            cover_btn.click()
            self._log("[Cover] 已点击选择封面按钮")
            time.sleep(2)
            
            self.page.wait_for_selector('.arco-modal, [class*="modal"], [class*="upload"]', timeout=5000)
            
            file_input = self.page.locator('input[type="file"]').first
            if file_input.count() == 0:
                self._log("[Cover] 未找到文件输入框，尝试点击上传区域...")
                upload_area = self.page.locator('.upload-area, .cover-upload, [class*="upload"]').first
                if upload_area.count() > 0:
                    upload_area.click()
                    time.sleep(1)
                    file_input = self.page.locator('input[type="file"]').first
            
            if file_input.count() > 0:
                file_input.set_input_files(str(cover_file))
                self._log(f"[Cover] 已选择文件: {cover_file}")
                time.sleep(3)
                
                confirm_btn = self.page.locator('button:has-text("确认"), button:has-text("确定"), button:has-text("保存")').last
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    self._log("[Cover] 已点击确认")
                    time.sleep(1)
                
                self._log("[Cover] ✓ 封面上传完成")
                return True
            else:
                self._log("[Cover] 无法找到文件输入框")
                self.page.keyboard.press("Escape")
                return False
                
        except Exception as e:
            self._log(f"[Cover] 封面上传失败: {e}")
            try:
                self.page.keyboard.press("Escape")
            except:
                pass
            return False
    
    def _check_for_guide_page(self) -> bool:
        """检查是否进入了番茄新手引导/实名认证/作者签约页面"""
        try:
            url = self.page.url
            content = self.page.content()[:1500]
            content_lower = content.lower()
            
            guide_keywords = [
                '新手引导', '作者引导', '实名认证', '完善信息', '作者认证',
                '签约', '合同', '引导流程', '入驻引导', '开始创作',
                '请完成实名认证', '请完善作者信息', '新人作者',
                'guide', 'tutorial', 'rookie', 'verify identity',
                'author certification', 'contract', 'agreement'
            ]
            
            if any(kw in content for kw in guide_keywords):
                return True
            
            # 如果 URL 里包含 author/certification/guide 等路径
            if any(k in url.lower() for k in ['/author-guide', '/certification', '/contract', '/tutorial']):
                return True
                
        except:
            pass
        return False
    
    def _close_extra_pages(self, keep_chapter_manage=True):
        """关闭多余的标签页，只保留当前页面和章节管理页（可选）"""
        try:
            if not self.browser:
                return
            
            # 获取所有上下文和页面
            contexts = self.browser.contexts
            for context in contexts:
                pages = context.pages
                if len(pages) <= 1:
                    continue
                
                # 找到当前页面和章节管理页
                current_page_idx = -1
                chapter_manage_idx = -1
                for idx, page in enumerate(pages):
                    if page == self.page:
                        current_page_idx = idx
                    url = page.url
                    if '/chapter-manage/' in url and '/publish/' not in url:
                        chapter_manage_idx = idx
                
                # 关闭除当前页面和章节管理页外的其他页面
                closed_count = 0
                for idx, page in enumerate(pages):
                    # 保留当前页面
                    if idx == current_page_idx:
                        continue
                    # 保留章节管理页（如果keep_chapter_manage为True）
                    if keep_chapter_manage and idx == chapter_manage_idx:
                        continue
                    
                    try:
                        page.close()
                        closed_count += 1
                    except:
                        pass
                
                if closed_count > 0:
                    self._log(f"  已关闭 {closed_count} 个多余标签页")
                    
        except Exception as e:
            self._log(f"  关闭标签页时出错: {e}", "debug")
    
    def _navigate_to_publish_page(self) -> bool:
        """导航到章节发布页面（避免重复导航，优先复用当前页面）"""
        try:
            current_url = self.page.url
            
            # ✅ 检查1: 如果当前已在正确的发布页面，直接返回
            if "/publish/" in current_url and self.book_id and self.book_id in current_url:
                self._log("  已在发布页面")
                return True
            
            if not self.book_id:
                self._log("  ✗ 缺少书籍ID")
                return False
            
            # ✅ 检查2: 如果当前已经在章节管理页，直接点击"新建章节"
            if "/chapter-manage/" in current_url and self.book_id in current_url:
                self._log("  当前在章节管理页，点击'新建章节'...")
                try:
                    # 先关闭多余的标签页，避免累积
                    self._close_extra_pages()
                    
                    new_chapter_btn = self.page.locator(
                        '.btns.right-btns a[href*="/publish/"] button.arco-btn-primary, '
                        'button:has-text("新建章节"), '
                        f'a[href*="{self.book_id}/publish/"]'
                    ).first
                    
                    if new_chapter_btn.count() > 0 and new_chapter_btn.is_visible():
                        with self.page.expect_popup() as popup_info:
                            new_chapter_btn.click()
                        new_page = popup_info.value
                        
                        if new_page:
                            self.page = new_page
                            time.sleep(2)
                            # 🔥 关闭其他发布页标签，只保留当前和章节管理页
                            self._close_extra_pages()
                        
                        if "/publish/" in self.page.url:
                            return True
                except Exception as e:
                    self._log(f"  点击失败: {e}", "debug")
            
            # ✅ 检查3: 如果当前在番茄其他页面，直接goto章节管理页（只导航一次）
            self._log("  导航到章节管理页...")
            chapter_manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.book_id}"
            self.page.goto(chapter_manage_url, timeout=30000)
            time.sleep(2)
            
            # 点击"新建章节"
            current_url = self.page.url
            if "/chapter-manage/" in current_url:
                try:
                    btn = self.page.locator(
                        f'a[href*="{self.book_id}/publish/"], '
                        'button:has-text("新建章节")'
                    ).first
                    
                    if btn.count() > 0 and btn.is_visible():
                        with self.page.expect_popup() as popup_info:
                            btn.click()
                        new_page = popup_info.value
                        
                        if new_page:
                            self.page = new_page
                            time.sleep(2)
                            # 🔥 关闭其他发布页标签，只保留当前和章节管理页
                            self._close_extra_pages()
                        
                        if "/publish/" in self.page.url:
                            return True
                except Exception as e:
                    self._log(f"  点击失败: {e}", "debug")
            
            self._log(f"  ⚠ 导航失败，当前URL: {self.page.url}")
            return False
            
        except Exception as e:
            self._log(f"  导航失败: {e}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        if not self.is_running:
            return False
            
        chapter_number = chapter.get('chapter_number', chapter.get('number', 0))
        chapter_title = chapter.get('chapter_title', chapter.get('title', f'第{chapter_number}章'))
        content = chapter.get('content', '')
        
        self._log(f"正在上传第 {chapter_number} 章: {chapter_title[:30]}...")
        
        # 🔥 先关闭多余的发布页标签，避免累积
        self._close_extra_pages(keep_chapter_manage=True)
        
        try:
            # 确保在发布页面
            if not self._navigate_to_publish_page():
                self._log("  ✗ 无法进入章节发布页面", "error")
                return False
            
            # 🔥 关键：等待页面完全加载，元素渲染需要时间
            self._log("  等待页面元素加载...")
            self._random_sleep(2.5, 4.0)  # 随机延迟，防风控
            
            # 填写章节号 - 先点击激活区域
            chapter_num_input = None
            chapter_title_input = None
            
            # 🔥 尝试多种方式激活章节号输入框
            # 方式1: 点击 "第 X 章" 文本区域
            try:
                chapter_label = self.page.locator('.serial-editor-title-left, .left-input').first
                if chapter_label.count() > 0:
                    chapter_label.click()
                    self._log("  点击激活章节号输入区域(方式1)")
                    self._random_sleep(0.5, 1.0)
            except Exception as e:
                self._log(f"  方式1跳过: {e}", "debug")
            
            # 方式2: 使用 JavaScript 直接移除 none 类
            try:
                self.page.evaluate('''() => {
                    const left = document.querySelector('.serial-editor-title-left');
                    if (left && left.classList.contains('none')) {
                        left.classList.remove('none');
                        return 'removed none class';
                    }
                    return 'no none class found';
                }''')
                self._log("  尝试JS移除none类(方式2)")
                self._random_sleep(0.2, 0.5)
            except Exception as e:
                self._log(f"  方式2跳过: {e}", "debug")
            
            # 方式3: 点击输入框本身（即使隐藏）
            try:
                hidden_input = self.page.locator('.serial-editor-title-left input.serial-input, .left-input input').first
                if hidden_input.count() > 0:
                    hidden_input.click(force=True)
                    self._log("  强制点击输入框(方式3)")
                    self._random_sleep(0.3, 0.6)
            except Exception as e:
                self._log(f"  方式3跳过: {e}", "debug")
            
            # 查找章节号输入框 - 直接查找不等待，避免超时卡住
            try:
                chapter_num_input = self.page.locator('.serial-editor-title-left input').first
                if chapter_num_input.count() == 0:
                    chapter_num_input = self.page.locator('.left-input input').first
                if chapter_num_input.count() > 0:
                    self._log("  ✓ 找到章节号输入框")
                else:
                    chapter_num_input = None
            except Exception as e:
                self._log(f"  查找章节号输入框失败: {e}", "warning")
                chapter_num_input = None
            
            # 查找标题输入框
            try:
                chapter_title_input = self.page.locator('.serial-editor-title-right input').first
                if chapter_title_input.count() == 0:
                    chapter_title_input = self.page.locator('.right-input input').first
                if chapter_title_input.count() > 0:
                    self._log("  ✓ 找到标题输入框")
                else:
                    chapter_title_input = None
            except Exception as e:
                self._log(f"  查找标题输入框失败: {e}", "warning")
                chapter_title_input = None
            
            # 备选：使用更通用的选择器
            if not chapter_num_input:
                try:
                    all_inputs = self.page.locator('input.serial-input').all()
                    self._log(f"  找到 {len(all_inputs)} 个 serial-input 输入框")
                    if len(all_inputs) >= 2:
                        chapter_num_input = all_inputs[0]
                        chapter_title_input = all_inputs[1]
                except Exception as e:
                    self._log(f"  备选查找失败: {e}", "warning")
            
            # 填写章节号 - 直接使用 fill（像测试脚本一样）
            if chapter_num_input:
                try:
                    chapter_num_input.fill("")
                    self._random_sleep(0.1, 0.3)
                    chapter_num_input.fill(str(chapter_number))
                    self._log(f"  填写章节号: {chapter_number}")
                except Exception as e:
                    self._log(f"  章节号填写失败: {e}", "warning")
            else:
                self._log("  ✗ 未找到章节号输入框", "error")
                return False
            
            # 填写标题
            if chapter_title_input:
                try:
                    chapter_title_input.fill("")
                    self._random_sleep(0.1, 0.3)
                    chapter_title_input.fill(chapter_title)
                    self._log(f"  填写标题: {chapter_title[:20]}...")
                except Exception as e:
                    self._log(f"  标题填写失败: {e}", "warning")
            else:
                self._log("  ✗ 未找到标题输入框", "error")
                return False
            
            # 填写内容（直接填充，快速粘贴）
            try:
                # 等待编辑器加载
                self.page.wait_for_selector('.ProseMirror[contenteditable]', timeout=10000)
                content_editor = self.page.locator('.ProseMirror[contenteditable]').first
                
                # 清理内容格式
                lines = content.split('\n')
                if lines and ('第' in lines[0] and '章' in lines[0]):
                    lines = lines[1:]
                processed = '\n'.join(lines).strip()
                
                # 直接填充内容（复制粘贴模式，比逐字输入快几十倍）
                content_editor.fill(processed)
                self._log(f"  填写内容: {len(processed)} 字")
                self._random_sleep(0.5, 1.0)  # 稍等片刻确保内容写入
            except Exception as e:
                self._log(f"  内容填写失败: {e}", "warning")
            
            # 检查暂停
            self._check_pause()
            if not self.is_running:
                return False
            
            time.sleep(1)
            
            # 点击下一步
            try:
                next_btn = self.page.locator('button:has-text("下一步")').first
                if next_btn.count() > 0 and next_btn.is_visible():
                    next_btn.click()
                    self._log("  点击下一步")
                    # 增加等待时间，让模态框有足够时间出现
                    self._random_sleep(2.5, 4.0)
            except Exception as e:
                self._log(f"  下一步按钮跳过: {e}", "debug")
            
            # 处理可能的弹窗（如"继续编辑本地"等）
            for _ in range(3):
                try:
                    for btn_text in ["提交", "继续编辑本地", "确定", "确认"]:
                        try:
                            btn = self.page.locator(f'button:has-text("{btn_text}")').first
                            if btn.count() > 0 and btn.is_visible():
                                btn_text_content = btn.text_content() or ""
                                if "发布" not in btn_text_content:
                                    btn.click()
                                    self._random_sleep(0.3, 0.8)
                        except:
                            pass
                except:
                    pass
            
            # 检查暂停
            self._check_pause()
            if not self.is_running:
                return False
            
            # 处理"发布设置"模态框（等待并处理）
            try:
                # 等待模态框出现（最多等10秒）
                modal = None
                for i in range(20):
                    modal = self.page.locator('.publish-confirm-container-new, .arco-modal:has(.publish-confirm-card)').first
                    if modal.count() > 0 and modal.is_visible():
                        self._log("  检测到发布设置模态框")
                        break
                    time.sleep(0.5)
                else:
                    self._log("  未检测到发布设置模态框，跳过")
                    modal = None
                
                if modal and modal.count() > 0 and modal.is_visible():
                    # 等待模态框完全渲染
                    self._random_sleep(1.0, 1.5)
                    
                    # 获取所有cards
                    cards = self.page.locator('.publish-confirm-card').all()
                    self._log(f"  找到 {len(cards)} 个设置卡片")
                    
                    # 5.1 选择 AI "是"（在第一个card中）
                    if len(cards) >= 1:
                        try:
                            ai_card = cards[0]
                            
                            # 等待AI选项加载
                            self._random_sleep(0.5, 1.0)
                            
                            # 尝试多种方式选择AI选项
                            ai_selected = False
                            
                            # 方式1: 通过 label.arco-radio
                            try:
                                radios = ai_card.locator('label.arco-radio').all()
                                if len(radios) >= 1:
                                    radios[0].scroll_into_view_if_needed()
                                    self._random_sleep(0.3, 0.5)
                                    radios[0].click()
                                    self._log("  选择 AI: 是 (方式1)")
                                    ai_selected = True
                            except Exception as e1:
                                self._log(f"  AI方式1失败: {e1}", "debug")
                            
                            # 方式2: 通过 input[type="radio"] + 点击关联label
                            if not ai_selected:
                                try:
                                    radio_inputs = ai_card.locator('input[type="radio"]').all()
                                    if len(radio_inputs) >= 1:
                                        # 点击第一个radio
                                        radio_inputs[0].scroll_into_view_if_needed()
                                        self._random_sleep(0.2, 0.4)
                                        radio_inputs[0].click()
                                        self._log("  选择 AI: 是 (方式2)")
                                        ai_selected = True
                                except Exception as e2:
                                    self._log(f"  AI方式2失败: {e2}", "debug")
                            
                            # 方式3: 通过JavaScript点击
                            if not ai_selected:
                                try:
                                    # 在card内找到第一个radio并点击
                                    ai_card.evaluate('''(card) => {
                                        const radio = card.querySelector('input[type="radio"], .arco-radio');
                                        if (radio) {
                                            radio.click();
                                            return true;
                                        }
                                        return false;
                                    }''')
                                    self._random_sleep(0.3, 0.5)
                                    self._log("  选择 AI: 是 (方式3 JS)")
                                    ai_selected = True
                                except Exception as e3:
                                    self._log(f"  AI方式3失败: {e3}", "debug")
                            
                            if not ai_selected:
                                self._log("  AI选项未能选择，继续执行", "warning")
                                
                        except Exception as e:
                            self._log(f"  AI选项跳过: {e}", "debug")
                    
                    self._random_sleep(0.5, 1.0)
                    
                    # 检查暂停
                    self._check_pause()
                    if not self.is_running:
                        return False
                    
                    # 5.2 开启定时发布（在第二个card中）
                    scheduled_time = chapter.get('scheduled_time')  # 格式: "2026-04-05 07:00"
                    if len(cards) >= 2 and scheduled_time:
                        try:
                            time_card = cards[1]
                            switch = time_card.locator('button[role="switch"]').first
                            if switch.count() > 0:
                                is_on = switch.get_attribute('aria-checked') == 'true'
                                if not is_on:
                                    self._random_sleep(0.3, 0.6)
                                    switch.click()
                                    self._log("  开启定时发布")
                                    self._random_sleep(2.0, 3.0)  # 等待时间选择器出现
                                
                                # 解析 scheduled_time
                                try:
                                    from datetime import datetime
                                    dt = datetime.strptime(scheduled_time, '%Y-%m-%d %H:%M')
                                    target_date = dt.strftime('%Y-%m-%d')
                                    target_hour = dt.hour
                                    target_minute = dt.minute
                                    
                                    # 选择日期时间
                                    picker = self.page.locator('.arco-picker-input input').first
                                    if picker.count() > 0:
                                        picker.click()
                                        self._random_sleep(2.0, 3.0)  # 等待日期选择器弹出
                                        
                                        # 获取目标年月日
                                        target_year = dt.year
                                        target_month = dt.month
                                        target_day = dt.day
                                        
                                        # 导航到正确的年月（带错误处理）
                                        try:
                                            max_nav_attempts = 12
                                            for nav_i in range(max_nav_attempts):
                                                # 等待并获取当前显示的年月
                                                try:
                                                    header_year_elem = self.page.locator('.arco-picker-header-label').nth(0)
                                                    header_month_elem = self.page.locator('.arco-picker-header-label').nth(1)
                                                    
                                                    # 等待元素可见
                                                    header_year_elem.wait_for(state='visible', timeout=5000)
                                                    header_month_elem.wait_for(state='visible', timeout=5000)
                                                    
                                                    header_year = header_year_elem.text_content().strip()
                                                    header_month = header_month_elem.text_content().strip()
                                                    
                                                    current_year = int(header_year.replace('年', ''))
                                                    current_month = int(header_month.replace('月', ''))
                                                    
                                                    if current_year == target_year and current_month == target_month:
                                                        break
                                                    
                                                    # 计算月份差
                                                    year_diff = target_year - current_year
                                                    month_diff = target_month - current_month + year_diff * 12
                                                    
                                                    if month_diff > 0:
                                                        next_btn = self.page.locator('.arco-icon-right').first
                                                        if next_btn.count() > 0:
                                                            next_btn.click()
                                                            self._random_sleep(0.5, 0.8)
                                                    else:
                                                        prev_btn = self.page.locator('.arco-icon-left').first
                                                        if prev_btn.count() > 0:
                                                            prev_btn.click()
                                                            self._random_sleep(0.5, 0.8)
                                                except Exception as nav_e:
                                                    self._log(f"  导航年月时出错: {nav_e}", "warning")
                                                    break
                                        except Exception as e:
                                            self._log(f"  年月导航失败: {e}", "warning")
                                        
                                        self._random_sleep(1.0, 1.5)
                                        
                                        # 选择日期
                                        try:
                                            day_str = str(target_day)
                                            # 尝试点击可见的日期
                                            date_selectors = [
                                                f'.arco-picker-cell-in-view .arco-picker-date-value:has-text("{day_str}")',
                                                f'.arco-picker-cell:not(.arco-picker-cell-disabled) .arco-picker-date-value:has-text("{day_str}")',
                                                f'.arco-picker-date-value:has-text("{day_str}")'
                                            ]
                                            
                                            date_clicked = False
                                            for date_sel in date_selectors:
                                                try:
                                                    date_cell = self.page.locator(date_sel).first
                                                    date_cell.wait_for(state='visible', timeout=3000)
                                                    if date_cell.count() > 0:
                                                        date_cell.click()
                                                        self._log(f"  选择日期: {target_year}年{target_month}月{target_day}日")
                                                        date_clicked = True
                                                        self._random_sleep(1.0, 1.5)
                                                        break
                                                except:
                                                    continue
                                            
                                            if not date_clicked:
                                                self._log(f"  未找到日期单元格: {day_str}", "warning")
                                        except Exception as e:
                                            self._log(f"  选择日期失败: {e}", "warning")
                                        
                                        # 选择时间 - 先点击时间输入框
                                        time_input = self.page.locator('.arco-picker-input input').nth(1)
                                        if time_input.count() > 0:
                                            time_input.click()
                                            self._random_sleep(0.5, 1.0)
                                            
                                            # 选择具体时间
                                            time_str = f"{target_hour:02d}:{target_minute:02d}"
                                            time_cell = self.page.locator(f'.arco-timepicker-cell:has-text("{time_str}")').first
                                            if time_cell.count() > 0:
                                                time_cell.click()
                                                self._log(f"  选择时间: {time_str}")
                                            else:
                                                # 备选：直接输入时间
                                                time_input.fill(time_str)
                                                self._random_sleep(0.3, 0.5)
                                                time_input.press("Enter")
                                        
                                        # 等待日期选择器自动关闭，不要按ESC（会关闭整个模态框）
                                        self._random_sleep(1.0, 1.5)
                                        
                                        self._log(f"  设置定时: {scheduled_time}")
                                except Exception as e:
                                    self._log(f"  设置定时时间失败: {e}", "warning")
                                    # 尝试关闭可能打开的日期选择器
                                    try:
                                        self.page.keyboard.press("Escape")
                                    except:
                                        pass
                            else:
                                self._log("  定时发布已开启")
                        except Exception as e:
                            self._log(f"  定时发布设置跳过: {e}", "debug")
                    elif len(cards) >= 2 and not scheduled_time:
                        # 不需要定时发布，确保开关是关闭的
                        try:
                            time_card = cards[1]
                            switch = time_card.locator('button[role="switch"]').first
                            if switch.count() > 0:
                                is_on = switch.get_attribute('aria-checked') == 'true'
                                if is_on:
                                    switch.click()
                                    self._log("  关闭定时发布（前N章直接发布）")
                                    self._random_sleep(0.5, 1.0)
                        except Exception as e:
                            self._log(f"  关闭定时发布跳过: {e}", "debug")
                    
                    self._random_sleep(0.5, 1.0)
                    
                    # 5.3 点击确认发布
                    try:
                        # 先检查模态框是否还在
                        modal_check = self.page.locator('.arco-modal:has(.publish-confirm-card), .publish-confirm-container-new').first
                        if modal_check.count() == 0:
                            self._log("  ⚠ 模态框已关闭，尝试重新打开...", "warning")
                            # 尝试点击下一步重新打开模态框
                            try:
                                next_btn = self.page.locator('button:has-text("下一步")').first
                                if next_btn.count() > 0:
                                    next_btn.click()
                                    self._random_sleep(2.0, 3.0)
                            except:
                                pass
                        
                        # 等待并点击确认发布按钮（多种选择器尝试）
                        confirm_btn = None
                        confirm_selectors = [
                            '.arco-modal-footer button.arco-btn-primary:has-text("确认")',
                            '.arco-modal-footer button.arco-btn-primary:has-text("发布")',
                            '.arco-modal-footer button.arco-btn-primary',
                            'button:has-text("确认发布")',
                            '.publish-confirm-container-new button.arco-btn-primary',
                            '.arco-modal:has(.publish-confirm-card) button.arco-btn-primary'
                        ]
                        
                        # 等待按钮出现
                        for _ in range(5):
                            for selector in confirm_selectors:
                                try:
                                    btn = self.page.locator(selector).first
                                    if btn.count() > 0 and btn.is_visible():
                                        confirm_btn = btn
                                        self._log(f"  找到确认发布按钮: {selector}")
                                        break
                                except:
                                    continue
                            if confirm_btn:
                                break
                            self._random_sleep(0.5, 1.0)
                        
                        if confirm_btn:
                            self._random_sleep(0.5, 1.0)
                            confirm_btn.click()
                            self._log("  点击确认发布")
                            self._random_sleep(3.0, 5.0)  # 等待发布完成
                        else:
                            self._log("  未找到确认发布按钮，尝试备用方案", "warning")
                            # 备用：尝试点击任何包含"发布"或"确认"的主按钮
                            fallback_btn = self.page.locator('button.arco-btn-primary:has-text("确认"), button.arco-btn-primary:has-text("发布")').first
                            if fallback_btn.count() > 0:
                                fallback_btn.click()
                                self._log("  使用备用按钮点击")
                                self._random_sleep(3.0, 5.0)
                    except Exception as e:
                        self._log(f"  确认发布失败: {e}", "warning")
            except Exception as e:
                self._log(f"  模态框处理跳过: {e}", "debug")
            
            # 处理风险检测弹窗
            try:
                for _ in range(5):
                    risk_modal = self.page.locator('.arco-modal:has-text("风险检测")').first
                    if risk_modal.count() > 0 and risk_modal.is_visible():
                        self._log("  检测到风险检测弹窗")
                        risk_modal.locator('button.arco-btn-primary').first.click()
                        self._log("  点击确定")
                        self._random_sleep(1.5, 2.5)
                        break
                    self._random_sleep(0.3, 0.6)
            except Exception as e:
                self._log(f"  风险检测处理跳过: {e}", "debug")
            
            # 检查暂停
            self._check_pause()
            if not self.is_running:
                return False
            
            # 确认发布（普通按钮 - 兼容旧版）
            try:
                confirm_selectors = [
                    'button:has-text("确认发布")',
                    'button:has-text("立即发布")',
                    'button:has-text("发布")'
                ]
                for selector in confirm_selectors:
                    try:
                        confirm_btn = self.page.locator(selector).first
                        if confirm_btn.count() > 0 and confirm_btn.is_visible():
                            confirm_btn.click()
                            self._log(f"  点击发布按钮 ({selector})")
                            self._random_sleep(2.5, 4.0)
                            break
                    except:
                        continue
            except Exception as e:
                self._log(f"  发布按钮跳过: {e}", "debug")
            
            # 检查结果
            self._random_sleep(2.0, 3.5)
            current_url = self.page.url
            
            # 获取更多页面内容用于判断
            try:
                page_text = self.page.content()[:1000]
            except:
                page_text = ""
            
            # 判断是否成功
            has_success_hint = any(kw in page_text for kw in ['发布成功', '操作成功', 'success', '创建成功', '提交成功'])
            is_chapter_manage = '/chapter-manage/' in current_url
            is_publish_page = '/publish/' in current_url
            is_book_page = '/book/' in current_url
            
            self._log(f"  当前URL: {current_url}")
            
            # 🔥 成功上传后关闭发布页标签，避免累积
            success_result = None
            
            if has_success_hint:
                self._log(f"  ✓ 第{chapter_number}章上传成功 (检测到成功提示)", "success")
                success_result = True
            
            elif is_chapter_manage:
                self._log(f"  ✓ 第{chapter_number}章上传成功 (已返回章节管理页)", "success")
                success_result = True
            
            elif is_book_page and not is_publish_page:
                self._log(f"  ✓ 第{chapter_number}章上传成功 (已跳转到书籍页)", "success")
                success_result = True
            
            # 检查是否有明确的错误提示
            has_error = any(kw in page_text.lower() for kw in ['error', '报错', '失败', '错误', 'cannot', 'unable'])
            
            elif not is_publish_page and not has_error:
                self._log(f"  ⚠ 页面已跳转，无错误提示，视为成功", "warning")
                success_result = True
            
            elif is_publish_page and not has_error:
                # 仍在发布页，但可能没有错误，可能是网络慢
                self._log(f"  ⚠ 仍在发布页，等待后重试检查...", "warning")
                time.sleep(3)
                # 再次检查URL
                if '/publish/' not in self.page.url:
                    self._log(f"  ✓ 第{chapter_number}章上传成功 (页面已跳转)", "success")
                    success_result = True
            
            # 🔥 如果上传成功，关闭多余的发布页标签
            if success_result:
                self._close_extra_pages(keep_chapter_manage=True)
                return True
            
            self._log(f"  ✗ 第{chapter_number}章上传可能失败", "error")
            if has_error:
                self._log(f"  检测到错误提示", "error")
            return False
            
        except Exception as e:
            error_msg = str(e)
            self._log(f"  ✗ 上传失败: {error_msg[:50]}", "error")
            
            if retry_count < MAX_RETRY:
                self._log(f"  🔄 重试 ({retry_count + 1}/{MAX_RETRY})...", "warning")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            
            return False
    
    def upload_chapters(self, chapters: List[Dict], 
                        delay_min: float = 3.0, 
                        delay_max: float = 8.0,
                        stop_on_error: bool = False) -> Dict[str, Any]:
        """批量上传章节，支持项目配置的定时发布设置"""
        self.chapters = chapters
        total = len(chapters)
        success_count = 0
        failed_chapters = []
        
        # 读取项目配置中的 publish_config
        publish_config = self.novel_config.get('publish_config', {})
        self._log(f"DEBUG: novel_config = {self.novel_config}")
        self._log(f"DEBUG: publish_config = {publish_config}")
        
        first_publish_count = publish_config.get('first_publish_count', 20)  # 前N章直接发布
        daily_count = publish_config.get('daily_count', 8)  # 每日发布数量
        publish_time = publish_config.get('publish_time', '07:00')  # 发布时间
        interval_minutes = publish_config.get('interval_minutes', 10)  # 章节间隔分钟
        
        # 获取本次上传章节的实际章节号列表
        chapter_numbers = [ch.get('chapter_number', i+1) for i, ch in enumerate(chapters)]
        max_chapter = max(chapter_numbers) if chapter_numbers else total
        min_chapter = min(chapter_numbers) if chapter_numbers else 1
        
        self._log(f"开始上传 {total} 个章节 (章节号范围: {min_chapter}-{max_chapter})...")
        self._log(f"发布配置: 前{first_publish_count}章直接发布, 之后{daily_count}章/日, 时间{publish_time}, 间隔{interval_minutes}分钟")
        
        # 判断是否需要计算定时计划（如果所有章节都<=first_publish_count，则不需要）
        needs_schedule = any(ch_num > first_publish_count for ch_num in chapter_numbers)
        
        schedule = {}
        if needs_schedule:
            # 计算定时发布计划（从第N+1章开始，同步平台数据）
            schedule = self._calculate_publish_schedule_with_sync(
                chapter_numbers, first_publish_count, daily_count, publish_time, interval_minutes
            )
        else:
            self._log(f"所有章节({min_chapter}-{max_chapter})均≤{first_publish_count}，全部立即发布")
        
        for i, chapter in enumerate(chapters):
            if not self.is_running:
                self._log("用户取消上传", "warning")
                break
            
            progress = 40 + int((i / total) * 60)
            ch_num = chapter.get('chapter_number', i + 1)
            
            # 检查是否需要定时发布（按实际章节号）
            scheduled_time = schedule.get(ch_num)
            if scheduled_time:
                self._progress(progress, f"正在上传第{ch_num}章 (定时: {scheduled_time})")
                chapter['scheduled_time'] = scheduled_time
            else:
                self._progress(progress, f"正在上传第{ch_num}章")
            
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
                if stop_on_error:
                    self._log("出错停止", "error")
                    break
            
            # 延迟
            if i < total - 1 and self.is_running:
                delay = random.uniform(delay_min, delay_max)
                self._log(f"  等待 {delay:.1f}s...")
                time.sleep(delay)
        
        result = {
            "total": total,
            "success": success_count,
            "failed": len(failed_chapters),
            "failed_chapters": failed_chapters
        }
        
        self._progress(100, f"上传完成：成功 {success_count}/{total}")
        return result
    
    def _calculate_publish_schedule(self, total_chapters: int, first_count: int, 
                                     daily_count: int, publish_time: str, 
                                     interval: int) -> Dict[int, str]:
        """
        计算章节定时发布计划
        
        Returns:
            Dict[章节号, 发布时间字符串]  格式: "2026-04-05 07:00"
        """
        schedule = {}
        
        if total_chapters <= first_count:
            return schedule  # 全部直接发布，不需要定时
        
        # 解析发布时间 (HH:MM)
        try:
            hour, minute = map(int, publish_time.split(':'))
        except:
            hour, minute = 7, 0
        
        # 从明天开始计算定时发布
        from datetime import datetime, timedelta
        base_date = datetime.now() + timedelta(days=1)
        base_date = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 需要定时发布的章节
        scheduled_chapters = list(range(first_count + 1, total_chapters + 1))
        
        # 按 daily_count 分组，每天发布指定数量
        for idx, chap_num in enumerate(scheduled_chapters):
            day_offset = idx // daily_count  # 第几天
            slot_in_day = idx % daily_count   # 当天第几个
            
            publish_dt = base_date + timedelta(days=day_offset, minutes=slot_in_day * interval)
            schedule[chap_num] = publish_dt.strftime('%Y-%m-%d %H:%M')
        
        self._log(f"定时发布计划: 共{len(schedule)}章需要定时, 从第{first_count+1}章开始")
        if schedule:
            first_scheduled = min(schedule.items(), key=lambda x: x[0])
            last_scheduled = max(schedule.items(), key=lambda x: x[0])
            self._log(f"  首章定时: 第{first_scheduled[0]}章 @ {first_scheduled[1]}")
            self._log(f"  末章定时: 第{last_scheduled[0]}章 @ {last_scheduled[1]}")
        
        return schedule
    
    def _get_last_published_time_from_page(self) -> Tuple[Optional[datetime], int]:
        """
        从章节管理页面抓取最后发布的章节时间和今天发布数量
        
        Returns:
            tuple: (最后发布时间, 今天已发布数量)
        """
        try:
            if not self.book_id:
                self._log("无法获取发布时间: book_id为空", "warning")
                return None, 0
            
            # 访问章节管理页
            chapter_manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.book_id}"
            self._log(f"访问章节管理页获取发布时间...")
            
            self.page.goto(chapter_manage_url, wait_until="networkidle", timeout=15000)
            time.sleep(2)
            
            # 等待表格加载
            self.page.wait_for_selector(".arco-table-tbody tr", timeout=10000)
            
            # 获取所有行的发布时间和状态
            rows = self.page.locator(".arco-table-tbody tr").all()
            
            last_published_time = None
            today_published_count = 0
            today = datetime.now().date()
            
            for row in rows:
                try:
                    # 获取状态单元格
                    status_cell = row.locator("td:nth-child(4)").first
                    if status_cell.count() == 0:
                        continue
                    
                    status = status_cell.text_content().strip()
                    
                    if status == "已发布":
                        # 获取发布时间单元格
                        time_cell = row.locator("td:nth-child(5)").first
                        if time_cell.count() == 0:
                            continue
                        
                        time_text = time_cell.text_content().strip()
                        if not time_text or time_text == "-":
                            continue
                        
                        # 解析时间 "2026-04-05 11:18"
                        try:
                            publish_dt = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
                            
                            # 记录最后发布时间
                            if last_published_time is None or publish_dt > last_published_time:
                                last_published_time = publish_dt
                            
                            # 统计今天发布的数量
                            if publish_dt.date() == today:
                                today_published_count += 1
                                
                        except ValueError:
                            continue
                            
                except Exception as e:
                    continue
            
            if last_published_time:
                self._log(f"最后发布时间: {last_published_time.strftime('%Y-%m-%d %H:%M')}")
                self._log(f"今天已发布: {today_published_count} 章")
            else:
                self._log("未找到已发布章节的时间信息")
            
            return last_published_time, today_published_count
            
        except Exception as e:
            self._log(f"获取发布时间失败: {e}", "warning")
            return None, 0
    
    def _get_next_publish_time(self, last_time: Optional[datetime] = None, 
                                today_count: int = 0) -> datetime:
        """
        计算下一个发布时间
        
        Args:
            last_time: 最后发布时间（从页面抓取）
            today_count: 今天已发布的数量
            
        Returns:
            datetime: 下一个章节的发布时间
        """
        config = self.novel_config.get('publish_config', {})
        daily_count = config.get('daily_count', 8)
        interval_mins = config.get('interval_minutes', 10)
        publish_time_str = config.get('publish_time', '07:00')
        
        hour, minute = map(int, publish_time_str.split(':'))
        now = datetime.now()
        today = now.date()
        
        # 如果今天已满，从明天开始
        if today_count >= daily_count:
            next_date = today + timedelta(days=1)
            next_time = datetime(next_date.year, next_date.month, next_date.day, hour, minute)
            self._log(f"今天已发布{daily_count}章，下一天从 {next_time.strftime('%Y-%m-%d %H:%M')} 开始")
            return next_time
        
        # 如果有最后发布时间，从最后时间+间隔开始
        if last_time:
            next_time = last_time + timedelta(minutes=interval_mins)
            
            # 确保不早于今天publish_time
            today_start = datetime(today.year, today.month, today.day, hour, minute)
            if next_time < today_start:
                next_time = today_start
            
            # 如果已经超过今天，检查是否跨天
            if next_time.date() > today:
                # 已经跨天了，从新一天的publish_time开始
                next_time = datetime(next_time.year, next_time.month, next_time.day, hour, minute)
            
            self._log(f"基于最后发布时间推算，下一章: {next_time.strftime('%Y-%m-%d %H:%M')}")
            return next_time
        else:
            # 没有最后发布时间，从今天开始
            today_start = datetime(today.year, today.month, today.day, hour, minute)
            
            # 如果今天publish_time已过，从下一个间隔开始
            if now > today_start:
                # 计算从publish_time开始，已经过了几个interval
                elapsed_minutes = (now - today_start).total_seconds() / 60
                intervals_passed = int(elapsed_minutes / interval_mins) + 1
                next_time = today_start + timedelta(minutes=intervals_passed * interval_mins)
            else:
                next_time = today_start
            
            self._log(f"无历史发布时间，下一章: {next_time.strftime('%Y-%m-%d %H:%M')}")
            return next_time
    
    def _calculate_publish_schedule_with_sync(self, chapter_numbers: List[int], 
                                               first_count: int,
                                               daily_count: int, 
                                               publish_time: str, 
                                               interval: int) -> Dict[int, str]:
        """
        计算章节定时发布计划（基于平台同步的数据）
        
        先从章节管理页抓取最后发布时间，然后推算后续时间
        
        Args:
            chapter_numbers: 本次要上传的章节号列表
            
        Returns:
            Dict[章节号, 发布时间字符串]  格式: "2026-04-05 07:00"
        """
        schedule = {}
        
        # 过滤出需要定时发布的章节（章节号 > first_count）
        scheduled_chapters = sorted([ch for ch in chapter_numbers if ch > first_count])
        
        if not scheduled_chapters:
            return schedule  # 没有需要定时的章节
        
        # 🔥 优先检查手动设置的基准时间
        publish_config = self.novel_config.get('publish_config', {})
        manual_date = publish_config.get('manual_publish_date')
        manual_time = publish_config.get('manual_publish_time')
        manual_count = publish_config.get('manual_chapter_count', 1)
        
        if manual_date and manual_time:
            self._log("=" * 50)
            self._log(f"使用手动设置的基准时间: {manual_date} {manual_time}")
            
            # 解析基准时间
            base_time = datetime.strptime(f"{manual_date} {manual_time}", "%Y-%m-%d %H:%M")
            
            # 分配给章节（基于基准时间递增）
            today_chapters = 0
            next_time = base_time
            
            for i, chap_num in enumerate(scheduled_chapters):
                # 检查是否跨天（超过 daily_count 章）
                if today_chapters >= daily_count:
                    # 跳到明天同一时间
                    next_day = next_time.date() + timedelta(days=1)
                    hour, minute = map(int, manual_time.split(':'))
                    next_time = datetime(next_day.year, next_day.month, next_day.day, hour, minute)
                    today_chapters = 0
                
                schedule[chap_num] = next_time.strftime('%Y-%m-%d %H:%M')
                
                # 准备下一个时间（+间隔分钟）
                next_time = next_time + timedelta(minutes=interval)
                today_chapters += 1
            
            self._log(f"手动设置计划: 已安排 {len(schedule)} 章 (从第{scheduled_chapters[0]}章开始)")
            return schedule
        
        # 从页面获取最后发布时间和今天发布数量
        self._log("=" * 50)
        self._log("同步平台发布时间数据...")
        last_published_time, today_published_count = self._get_last_published_time_from_page()
        
        # 获取下一个可用时间
        next_time = self._get_next_publish_time(last_published_time, today_published_count)
        
        # 生成发布计划
        hour, minute = map(int, publish_time.split(':'))
        today_chapters = 0
        
        for chap_num in scheduled_chapters:
            # 检查是否跨天
            if today_chapters >= daily_count:
                # 跳到明天
                next_day = next_time.date() + timedelta(days=1)
                next_time = datetime(next_day.year, next_day.month, next_day.day, hour, minute)
                today_chapters = 0
            
            schedule[chap_num] = next_time.strftime('%Y-%m-%d %H:%M')
            
            # 准备下一个时间
            next_time = next_time + timedelta(minutes=interval)
            today_chapters += 1
        
        self._log(f"=" * 50)
        self._log(f"定时发布计划: 共{len(schedule)}章需要定时")
        if schedule:
            first_scheduled = min(schedule.items(), key=lambda x: x[0])
            last_scheduled = max(schedule.items(), key=lambda x: x[0])
            self._log(f"  首章定时: 第{first_scheduled[0]}章 @ {first_scheduled[1]}")
            self._log(f"  末章定时: 第{last_scheduled[0]}章 @ {last_scheduled[1]}")
        self._log(f"=" * 50)
        
        return schedule
    
    def close(self):
        """关闭连接"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self._log("已断开 Chrome 连接")
        except Exception as e:
            self._log(f"关闭连接失败: {e}", "warning")
    
    def stop(self):
        """停止上传"""
        self.is_running = False
        self._log("正在停止上传...", "warning")
