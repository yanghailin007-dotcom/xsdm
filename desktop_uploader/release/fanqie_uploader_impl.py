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
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        self.novel_title = novel_title
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
            
            # 等待页面加载
            time.sleep(2)
            page_content = self.page.content()
            
            # 尝试多种方式查找书籍
            if self.novel_title[:10] in page_content:
                self._log("找到已有书籍")
                book_ids = re.findall(r'long-article-table-item-(\d+)', page_content)
                if book_ids:
                    self.book_id = book_ids[0]
                    self._progress(40, f"书籍ID: {self.book_id}")
                    return True
            
            # 尝试从URL中提取
            if '/book/' in self.page.url:
                match = re.search(r'/book/(\d+)', self.page.url)
                if match:
                    self.book_id = match.group(1)
                    self._progress(40, f"从URL获取书籍ID: {self.book_id}")
                    return True
            
            # 未找到书籍，自动创建
            self._log("未找到书籍，准备自动创建...", "warning")
            return self.create_book()
            
        except Exception as e:
            self._log(f"查找书籍失败: {e}", "error")
            return False
    
    def create_book(self) -> bool:
        """自动创建新书 - 从书籍管理页面点击创建"""
        try:
            self._progress(36, "正在创建新书...")
            self._log(f"开始创建书籍: {self.novel_title}")
            
            # 步骤0: 访问书籍管理页面
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            # 检查是否在登录页
            if "login" in self.page.url:
                self._log("需要登录，等待登录...", "warning")
                return False
            
            # 步骤1: 点击"创建新书"打开下拉菜单
            menu_opened = False
            try:
                locator = self.page.locator('div.hoverup:has-text("创建新书"), div.font-4:has-text("创建新书"), button:has-text("创建新书")')
                if locator.count() > 0:
                    self._log("找到创建新书按钮，点击打开下拉菜单...")
                    locator.first.click(timeout=5000)
                    menu_opened = True
                    time.sleep(1)
            except Exception as e:
                self._log(f"点击创建新书按钮失败: {e}", "warning")
            
            if not menu_opened:
                self._log("无法打开创建新书菜单，尝试直接访问创建页面...", "warning")
                self.page.goto("https://fanqienovel.com/main/writer/create?enter_from=home", timeout=30000)
                time.sleep(3)
            else:
                # 步骤2: 点击下拉菜单中的"创建书本"选项
                clicked = False
                try:
                    locator = self.page.get_by_text("创建书本", exact=True)
                    if locator.count() > 0:
                        locator.first.click(timeout=5000)
                        clicked = True
                except Exception as e:
                    self._log(f"精确查找创建书本失败: {e}", "warning")
                
                if not clicked:
                    try:
                        locator = self.page.locator('text=书本信息已准备好')
                        if locator.count() > 0:
                            parent = locator.locator('xpath=ancestor::*[contains(., "创建书本")][1]')
                            if parent.count() > 0:
                                parent.first.click(timeout=5000)
                                clicked = True
                    except Exception as e:
                        self._log(f"通过描述查找创建书本失败: {e}", "warning")
                
                if not clicked:
                    try:
                        elements = self.page.locator(':text("创建书本")').all()
                        for el in elements:
                            text = el.text_content()
                            if text and ("书本信息已准备好" in text or text.strip() == "创建书本"):
                                el.click(timeout=5000)
                                clicked = True
                                break
                    except Exception as e:
                        self._log(f"遍历创建书本元素失败: {e}", "warning")
                
                if not clicked:
                    self._log("未找到创建书本选项，尝试直接访问创建页面...", "warning")
                    self.page.goto("https://fanqienovel.com/main/writer/create?enter_from=home", timeout=30000)
                    time.sleep(3)
                else:
                    self._log("✓ 点击创建书本选项成功")
                    time.sleep(3)
            
            # 步骤3: 填写书名
            try:
                title_short = self.novel_title[:14] if len(self.novel_title) > 14 else self.novel_title
                title_input = self.page.locator('input[placeholder="请输入作品名称"]').first
                if title_input.count() > 0:
                    title_input.wait_for(state='visible', timeout=5000)
                    title_input.fill(title_short)
                    self._log(f"✓ 填写书名: {title_short}")
                else:
                    # 备用选择器
                    for selector in ['input[placeholder*="书名"]', 'input[name="title"]', 'input[type="text"]']:
                        try:
                            elem = self.page.locator(selector).first
                            if elem.count() > 0 and elem.is_visible():
                                elem.fill(title_short)
                                self._log(f"✓ 填写书名: {title_short}")
                                break
                        except:
                            continue
            except Exception as e:
                self._log(f"填写书名失败: {e}", "error")
                return False
            
            # 步骤4: 填写简介（可选）
            try:
                intro_text = f"{self.novel_title}，精彩小说，敬请期待！"
                for selector in ['textarea[placeholder*="简介"]', 'textarea', 'textarea[name="intro"]']:
                    try:
                        textarea = self.page.locator(selector).first
                        if textarea.count() > 0 and textarea.is_visible():
                            textarea.fill(intro_text)
                            self._log("✓ 填写简介")
                            break
                    except:
                        continue
            except:
                pass
            
            # 步骤5: 选择分类（点击第一个选项）
            try:
                for selector in ['.category-select', '.book-category', '[class*="category"]']:
                    try:
                        select_elem = self.page.locator(selector).first
                        if select_elem.count() > 0 and select_elem.is_visible():
                            select_elem.click()
                            time.sleep(1)
                            first_option = self.page.locator('.option-item, .select-option, [class*="option"]').first
                            if first_option.count() > 0:
                                first_option.click()
                                self._log("✓ 选择分类")
                                break
                    except:
                        continue
            except:
                pass
            
            time.sleep(2)
            
            # 步骤6: 点击创建按钮
            try:
                btn_clicked = False
                for selector in ['button:has-text("创建")', 'button:has-text("提交")', 'button:has-text("确定")', 'button[class*="primary"]', 'button[type="submit"]']:
                    try:
                        btn = self.page.locator(selector).first
                        if btn.count() > 0 and btn.is_visible():
                            btn.click()
                            self._log("✓ 点击创建按钮")
                            btn_clicked = True
                            break
                    except:
                        continue
                
                if not btn_clicked:
                    self._log("⚠️ 未能找到创建按钮", "warning")
                    return False
            except Exception as e:
                self._log(f"点击创建按钮失败: {e}", "error")
                return False
            
            # 等待创建结果
            time.sleep(5)
            
            # 检查是否创建成功
            page_content = self.page.content()
            success_indicators = ['创建成功', '书籍创建', 'book-manage', '/book/']
            if any(ind in page_content for ind in success_indicators) or '/book/' in self.page.url:
                book_ids = re.findall(r'/book/(\d+)', self.page.url)
                if book_ids:
                    self.book_id = book_ids[0]
                else:
                    book_ids = re.findall(r'long-article-table-item-(\d+)', page_content)
                    if book_ids:
                        self.book_id = book_ids[0]
                
                if self.book_id:
                    self.book_created = True
                    self._progress(40, f"✅ 书籍创建成功！ID: {self.book_id}")
                    self._log(f"✅ 书籍《{self.novel_title}》创建成功！")
                    return True
            
            # 检查是否已有同名书籍
            if '已存在' in page_content or '重复' in page_content:
                self._log("⚠️ 检测到同名书籍，尝试查找...", "warning")
                self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
                time.sleep(3)
                return self.find_book_in_list()
            
            self._log("⚠️ 书籍创建结果未知，请检查页面", "warning")
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
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        if not self.is_running:
            return False
            
        chapter_number = chapter.get('chapter_number', chapter.get('number', 0))
        chapter_title = chapter.get('chapter_title', chapter.get('title', f'第{chapter_number}章'))
        content = chapter.get('content', '')
        
        self._log(f"正在上传第 {chapter_number} 章: {chapter_title[:30]}...")
        
        try:
            # 访问发布页面
            publish_url = f"https://fanqienovel.com/main/writer/publish/{self.book_id}"
            self.page.goto(publish_url, timeout=30000)
            time.sleep(3)
            
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
            if '/chapter-manage/' in self.page.url or 'publish' not in self.page.url:
                self._log(f"  ✓ 第{chapter_number}章上传成功", "success")
                return True
            
            self._log(f"  ✓ 第{chapter_number}章上传完成", "success")
            return True
            
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
