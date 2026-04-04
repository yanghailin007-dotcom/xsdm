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
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

# 调试端口
DEBUG_PORT = 9988
MAX_RETRY = 3


class FanqieUploaderImpl:
    """番茄小说上传实现类"""
    
    def __init__(self, 
                 novel_title: str = "",
                 novel_config: Optional[Dict[str, Any]] = None,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        self.novel_title = novel_title
        self.novel_config = novel_config or {}
        self.progress_callback = progress_callback
        self.log_callback = log_callback
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
    
    def _progress(self, percent: int, message: str):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        self._log(f"[{percent}%] {message}")
    
    def connect_chrome(self, port: int = None) -> bool:
        """连接 Chrome
        
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
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            self._progress(20, "已连接到 Chrome")
            return True
        except Exception as e:
            self._log(f"连接 Chrome 失败: {e}", "error")
            self._log("请确保：1. 已启动对应账户的浏览器 2. 浏览器窗口保持打开", "warning")
            return False
    
    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            self._progress(25, "检查登录状态...")
            
            # 先访问首页检查登录状态
            self.page.goto("https://fanqienovel.com", timeout=30000)
            time.sleep(2)
            
            # 检查是否有登录按钮或用户头像
            # 方法1: 检查URL是否跳转到登录页
            current_url = self.page.url
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
            
            # 方法4: 尝试访问作者后台确认
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
        """等待用户登录"""
        self._log(f"等待登录，请在 {timeout} 秒内完成登录...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                return False
            try:
                self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=10000)
                time.sleep(2)
                if not self.page.url.startswith("https://fanqienovel.com/login"):
                    self._progress(30, "登录成功！")
                    return True
            except:
                pass
            time.sleep(2)
        
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
        """检查番茄平台上是否已有该书"""
        try:
            current_url = self.page.url
            self._log(f"当前页面URL: {current_url}")
            
            if "/chapter-manage/" in current_url:
                book_id = current_url.split("/chapter-manage/")[-1].split("/")[0]
                if book_id and book_id.isdigit():
                    self.book_id = book_id
                    return current_url
            
            if "/book-info/" in current_url:
                book_id = current_url.split("/book-info/")[-1].split("/")[0]
                if book_id and book_id.isdigit():
                    self.book_id = book_id
                    return f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
            
            if "/main/writer" not in current_url:
                self.page.goto("https://fanqienovel.com/main/writer/book-manage",
                             wait_until="networkidle", timeout=15000)
                time.sleep(3)
            
            try:
                title_short = self.novel_title[:10]
                self._log(f"在书籍管理页面查找书名: {title_short}...")
                self.page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                page_text = self.page.content()
                if title_short in page_text or self.novel_title[:8] in page_text:
                    book_ids = re.findall(r'long-article-table-item-(\d+)', page_text)
                    if book_ids:
                        for book_id in book_ids:
                            book_elem = self.page.locator(f'#long-article-table-item-{book_id}')
                            if book_elem.count() > 0:
                                title_elem = book_elem.locator('.info-content-title').first
                                if title_elem.count() > 0:
                                    title_text = title_elem.text_content().strip()
                                    if self.novel_title[:10] in title_text or title_text[:10] in self.novel_title:
                                        url = f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
                                        self.book_id = book_id
                                        return url
                        book_id = book_ids[0]
                        self.book_id = book_id
                        return f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
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
    
    def _navigate_to_publish_page(self) -> bool:
        """导航到章节发布页面（通过章节管理页点击创建章节）"""
        try:
            current_url = self.page.url
            if "/publish/" in current_url:
                self._log("  当前已在发布页面")
                return True
            
            if not self.book_id:
                self._log("  ✗ 缺少书籍ID，无法进入发布页")
                return False
            
            # 先访问章节管理页
            manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.book_id}"
            self.page.goto(manage_url, timeout=30000)
            time.sleep(3)
            
            # 点击"创建章节"按钮
            create_btn = self.page.locator(
                f'#long-article-table-item-{self.book_id} a[href*="/publish/"] button, '
                f'#long-article-table-item-{self.book_id} button:has-text("创建章节"), '
                'a[href*="/publish/"] button:has-text("创建章节"), '
                'button:has-text("创建章节")'
            ).first
            
            if create_btn.count() > 0 and create_btn.is_visible():
                create_btn.click()
                self._log("  点击'创建章节'按钮")
                time.sleep(4)
                
                # 检查是否弹出了新标签页
                # Playwright 的 popup 处理较复杂，这里简化：检查当前页面 URL
                if "/publish/" in self.page.url:
                    return True
            
            # 尝试点击链接
            create_link = self.page.locator(
                f'#long-article-table-item-{self.book_id} a[href*="/publish/"], '
                'a[href*="/publish/"]'
            ).first
            if create_link.count() > 0 and create_link.is_visible():
                create_link.click()
                self._log("  点击'创建章节'链接")
                time.sleep(4)
                if "/publish/" in self.page.url:
                    return True
            
            # 最后尝试直接访问发布页（旧版兼容）
            publish_url = f"https://fanqienovel.com/main/writer/publish/{self.book_id}"
            self.page.goto(publish_url, timeout=30000)
            time.sleep(3)
            if "/publish/" in self.page.url:
                return True
            
            self._log(f"  ⚠ 无法确认是否进入发布页，当前URL: {self.page.url}")
            return False
            
        except Exception as e:
            self._log(f"  导航到发布页失败: {e}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        if not self.is_running:
            return False
            
        chapter_number = chapter.get('chapter_number', chapter.get('number', 0))
        chapter_title = chapter.get('chapter_title', chapter.get('title', f'第{chapter_number}章'))
        content = chapter.get('content', '')
        
        self._log(f"正在上传第 {chapter_number} 章: {chapter_title[:30]}...")
        
        try:
            # 确保在发布页面
            if not self._navigate_to_publish_page():
                self._log("  ✗ 无法进入章节发布页面", "error")
                return False
            
            # 填写章节号
            try:
                inputs = self.page.locator('input.serial-input').all()
                if len(inputs) >= 1:
                    inputs[0].fill(str(chapter_number))
                    self._log(f"  填写章节号: {chapter_number}")
            except Exception as e:
                self._log(f"  章节号填写跳过: {e}", "warning")
            
            # 填写标题
            try:
                inputs = self.page.locator('input.serial-input').all()
                if len(inputs) >= 2:
                    inputs[1].fill(chapter_title)
                    self._log(f"  填写标题: {chapter_title[:20]}...")
            except Exception as e:
                self._log(f"  标题填写跳过: {e}", "warning")
            
            # 填写内容
            try:
                content_editor = self.page.locator('div[contenteditable="true"], .ProseMirror').first
                if content_editor.count() > 0:
                    # 清理内容格式
                    lines = content.split('\n')
                    if lines and ('第' in lines[0] and '章' in lines[0]):
                        lines = lines[1:]
                    processed = '\n'.join(lines).strip()
                    
                    content_editor.fill(processed)
                    self._log(f"  填写内容: {len(processed)} 字")
            except Exception as e:
                self._log(f"  内容填写跳过: {e}", "warning")
            
            time.sleep(1)
            
            # 点击下一步
            try:
                next_btn = self.page.locator('button:has-text("下一步")').first
                if next_btn.count() > 0:
                    next_btn.click()
                    time.sleep(2)
            except:
                pass
            
            # 确认发布
            try:
                confirm_btn = self.page.locator('button:has-text("确认发布"), button:has-text("发布")').first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    self._log("  点击确认发布")
                    time.sleep(3)
            except Exception as e:
                self._log(f"  发布按钮跳过: {e}", "warning")
            
            # 检查结果
            time.sleep(2)
            current_url = self.page.url
            page_text = self.page.content()[:500]
            
            # 判断是否成功
            has_success_hint = any(kw in page_text for kw in ['发布成功', '操作成功', 'success', '创建成功'])
            is_chapter_manage = '/chapter-manage/' in current_url
            is_publish_page = '/publish/' in current_url
            
            if has_success_hint or is_chapter_manage:
                self._log(f"  ✓ 第{chapter_number}章上传成功", "success")
                return True
            
            if not is_publish_page and not is_chapter_manage:
                self._log(f"  ⚠ 发布后页面异常，当前URL: {current_url}", "warning")
                # 如果页面异常但看起来没有明确报错，也尝试返回成功（因为番茄有时会跳转）
                if 'error' not in page_text.lower() and '报错' not in page_text:
                    return True
            
            self._log(f"  ✗ 第{chapter_number}章上传可能失败，仍在发布页且无成功提示", "error")
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
        """批量上传章节"""
        self.chapters = chapters
        total = len(chapters)
        success_count = 0
        failed_chapters = []
        
        self._log(f"开始上传 {total} 个章节...")
        
        for i, chapter in enumerate(chapters):
            if not self.is_running:
                self._log("用户取消上传", "warning")
                break
            
            progress = 40 + int((i / total) * 60)
            self._progress(progress, f"正在上传第{i+1}/{total}章")
            
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
