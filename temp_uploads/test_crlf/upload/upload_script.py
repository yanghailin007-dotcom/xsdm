#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱创作平台 - 番茄小说上传脚本
任务ID: test_crlf
小说: CRLF测试
生成时间: 2026-03-21 11:41:59
"""

import os
import sys
import json
import time
import random
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# ==================== 配置 ====================
API_BASE_URL = "http://localhost:5000"
TASK_ID = "test_crlf"
USER_TOKEN = "test"
NOVEL_TITLE = """CRLF测试"""
NOVEL_ID = "1"
TOTAL_CHAPTERS = 1
DEBUG_PORT = 9988
REPORT_INTERVAL = 3
MAX_RETRY = 3

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class UploadReporter:
    def __init__(self):
        self.last_report_time = 0
    
    def report(self, chapter_number: int, status: str, **kwargs):
        try:
            current_time = time.time()
            if current_time - self.last_report_time < REPORT_INTERVAL and status not in ['success', 'failed']:
                return True
            self.last_report_time = current_time
            
            data = {
                'task_id': TASK_ID,
                'chapter_number': chapter_number,
                'status': status,
            }
            for key in ['chapter_title', 'error_message', 'error_type', 'page_url']:
                if key in kwargs:
                    data[key] = kwargs[key]
            
            requests.post(
                f"{API_BASE_URL}/api/local-upload/report",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return True
        except:
            return False

class FanqieUploader:
    """番茄小说上传器"""
    
    def __init__(self, reporter: UploadReporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = []
        self.book_id = None
    
    def load_chapters(self):
        """加载章节数据"""
        chapters_file = Path(__file__).parent / "chapters.json"
        if not chapters_file.exists():
            print(f"{Colors.RED}✗ 未找到章节数据: chapters.json{Colors.RESET}")
            return False
        
        with open(chapters_file, 'r', encoding='utf-8') as f:
            self.chapters = json.load(f)
        
        print(f"{Colors.BLUE}📚 已加载 {len(self.chapters)} 章{Colors.RESET}")
        return True
    
    def connect_chrome(self):
        """连接Chrome"""
        try:
            from playwright.sync_api import sync_playwright
            
            print("\n🔌 正在连接 Chrome...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            print(f"{Colors.GREEN}✓ 已连接到 Chrome{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ 连接 Chrome 失败: {e}{Colors.RESET}")
            print("\n💡 请确保:")
            print("   1. 已运行 '一键启动.bat' 启动 Chrome")
            print("   2. Chrome 窗口保持打开")
            return False
    
    def check_login(self):
        """检查登录状态"""
        try:
            print("\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            if self.page.url.startswith("https://fanqienovel.com/login"):
                print(f"{Colors.RED}✗ 未登录番茄小说{Colors.RESET}")
                print("\n请在 Chrome 中登录番茄小说作者账号")
                return False
            
            print(f"{Colors.GREEN}✓ 已登录番茄小说{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ 检查登录失败: {e}{Colors.RESET}")
            return False
    
    def find_book(self):
        """查找书籍"""
        try:
            print(f"\n📖 查找书籍: {NOVEL_TITLE}")
            page_content = self.page.content()
            
            if NOVEL_TITLE[:10] in page_content:
                print(f"{Colors.GREEN}✓ 找到已有书籍{Colors.RESET}")
                book_ids = re.findall(r'long-article-table-item-(\d+)', page_content)
                if book_ids:
                    self.book_id = book_ids[0]
                    return True
            
            print(f"{Colors.YELLOW}⚠ 未找到书籍，请先手动创建{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ 查找书籍失败: {e}{Colors.RESET}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        content = chapter.get('content', '')
        
        print(f"\n📖 第 {chapter_number} 章: {chapter_title[:30]}...")
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
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
                    print(f"  填写章节号: {chapter_number}")
            except Exception as e:
                print(f"  ⚠️ 章节号: {e}")
            
            # 填写标题
            try:
                inputs = self.page.locator('input.serial-input').all()
                if len(inputs) >= 2:
                    inputs[1].fill(chapter_title)
                    print(f"  填写标题: {chapter_title[:20]}...")
            except Exception as e:
                print(f"  ⚠️ 标题: {e}")
            
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
                    print(f"  填写内容: {len(processed)} 字")
            except Exception as e:
                print(f"  ⚠️ 内容: {e}")
            
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
                confirm_btn = self.page.locator('button:has-text("确认发布"), button:has-text("发布")').filter(has_text=re.compile(r'发布|确认')).first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    print("  点击确认发布")
                    time.sleep(3)
            except Exception as e:
                print(f"  ⚠️ 发布: {e}")
            
            # 检查结果
            time.sleep(2)
            if '/chapter-manage/' in self.page.url or 'publish' not in self.page.url:
                self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
                print(f"{Colors.GREEN}  ✓ 上传成功{Colors.RESET}")
                return True
            
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            print(f"{Colors.GREEN}  ✓ 上传完成{Colors.RESET}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{Colors.RED}  ✗ 上传失败: {error_msg[:50]}{Colors.RESET}")
            
            self.reporter.report(
                chapter_number, 'failed',
                chapter_title=chapter_title,
                error_message=error_msg
            )
            
            if retry_count < MAX_RETRY:
                print(f"{Colors.YELLOW}  🔄 重试 ({retry_count + 1}/{MAX_RETRY})...{Colors.RESET}")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            
            return False
    
    def run(self):
        """运行上传流程"""
        print("=" * 60)
        print(f"{Colors.BLUE}大文娱创作平台 - 番茄小说上传{Colors.RESET}")
        print("=" * 60)
        print(f"小说: {NOVEL_TITLE}")
        print(f"章节: {TOTAL_CHAPTERS} 章")
        print("=" * 60)
        
        if not self.load_chapters():
            return False
        
        if not self.connect_chrome():
            return False
        
        if not self.check_login():
            return False
        
        if not self.find_book():
            print("\n请先手动创建书籍，然后重新运行脚本")
            input("\n按回车键退出...")
            return False
        
        print("\n" + "-" * 60)
        print("开始上传章节...")
        print("-" * 60)
        
        success_count = 0
        failed_chapters = []
        
        for i, chapter in enumerate(self.chapters, 1):
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            if i < len(self.chapters):
                delay = random.uniform(5, 10)
                print(f"  等待 {delay:.1f}s...")
                time.sleep(delay)
        
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        print("\n" + "=" * 60)
        print(f"{Colors.GREEN}✓ 上传完成{Colors.RESET}")
        print(f"成功: {success_count}/{len(self.chapters)} 章")
        if failed_chapters:
            print(f"{Colors.RED}失败: {len(failed_chapters)} 章{Colors.RESET}")
        print(f"\n查看详情: {API_BASE_URL}/upload-status/{TASK_ID}")
        print("=" * 60)
        
        return len(failed_chapters) == 0

def main():
    reporter = UploadReporter()
    uploader = FanqieUploader(reporter)
    
    try:
        success = uploader.run()
        
        if success:
            print(f"\n{Colors.GREEN}🎉 全部上传成功！{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️ 部分章节上传失败{Colors.RESET}")
        
        input("\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\n\n用户取消上传")
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()
