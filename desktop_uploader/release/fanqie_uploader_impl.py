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
    
    def connect_chrome(self) -> bool:
        """连接 Chrome"""
        try:
            from playwright.sync_api import sync_playwright
            
            self._progress(10, "正在连接 Chrome...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            self._progress(20, "已连接到 Chrome")
            return True
        except Exception as e:
            self._log(f"连接 Chrome 失败: {e}", "error")
            self._log("请确保：1. 已运行 Chrome 启动 2. Chrome 窗口保持打开", "warning")
            return False
    
    def check_login(self) -> bool:
        """检查登录状态"""
        try:
            self._progress(25, "检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            if self.page.url.startswith("https://fanqienovel.com/login"):
                self._log("未登录番茄小说，请在 Chrome 中登录", "warning")
                return False
            
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
        """查找书籍"""
        try:
            self._progress(35, f"查找书籍: {self.novel_title}")
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
            
            self._log("未找到书籍，请先手动创建", "warning")
            return False
        except Exception as e:
            self._log(f"查找书籍失败: {e}", "error")
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
