#!/usr/bin/env python3
"""
大文娱创作平台 - 本地上传脚本
由服务器自动生成，包含用户认证信息和上传配置

使用方法:
1. 确保 Chrome 已启动（运行一键启动.bat）
2. 在 Chrome 中登录番茄小说作者账号
3. 双击运行此脚本
4. 脚本会自动上传小说并上报进度到服务器
"""

import os
import sys
import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime

# ==================== 配置信息（由服务器生成时注入）====================
API_BASE_URL = "{{API_BASE_URL}}"  # 如: https://novel-ai.online
TASK_ID = "{{TASK_ID}}"
USER_TOKEN = "{{USER_TOKEN}}"
NOVEL_TITLE = "{{NOVEL_TITLE}}"
NOVEL_ID = "{{NOVEL_ID}}"
PLATFORM = "{{PLATFORM}}"  # fanqie
# =====================================================================

# 上报间隔（秒）
REPORT_INTERVAL = 5


class UploadReporter:
    """上传进度上报器"""
    
    def __init__(self, api_base: str, task_id: str, token: str):
        self.api_base = api_base
        self.task_id = task_id
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    
    def report(self, chapter_number: int, status: str, **kwargs):
        """上报进度"""
        try:
            data = {
                'task_id': self.task_id,
                'chapter_number': chapter_number,
                'status': status,  # uploading, success, failed
            }
            
            # 可选字段
            if 'chapter_title' in kwargs:
                data['chapter_title'] = kwargs['chapter_title']
            if 'error_message' in kwargs:
                data['error_message'] = kwargs['error_message']
            if 'error_type' in kwargs:
                data['error_type'] = kwargs['error_type']
            if 'error_detail' in kwargs:
                data['error_detail'] = kwargs['error_detail']
            if 'page_url' in kwargs:
                data['page_url'] = kwargs['page_url']
            
            response = requests.post(
                f"{self.api_base}/api/local-upload/report",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"  ✓ 上报成功: 第{chapter_number}章 {status}")
                return True
            else:
                print(f"  ✗ 上报失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ✗ 上报异常: {e}")
            return False


class FanqieUploader:
    """番茄小说上传器"""
    
    def __init__(self, reporter: UploadReporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
    
    def connect_chrome(self):
        """连接本地 Chrome"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9988")
            
            # 获取或创建页面
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            print(f"✓ 已连接到 Chrome: {self.page.url}")
            return True
            
        except Exception as e:
            print(f"✗ 连接 Chrome 失败: {e}")
            print("  请确保:")
            print("  1. 已运行 '一键启动.bat' 启动 Chrome")
            print("  2. Chrome 调试端口 9988 已开放")
            return False
    
    def check_login(self):
        """检查是否已登录番茄"""
        try:
            self.page.goto("https://fanqienovel.com/main/writer/book-manage")
            time.sleep(3)
            
            # 检查是否有登录按钮
            login_btn = self.page.locator('a[href*="/login"]').first
            if login_btn.count() > 0 and login_btn.is_visible():
                print("✗ 未检测到登录状态，请在 Chrome 中登录番茄小说")
                return False
            
            print("✓ 已登录番茄小说")
            return True
            
        except Exception as e:
            print(f"✗ 检查登录状态失败: {e}")
            return False
    
    def upload_chapter(self, chapter_data: dict) -> bool:
        """上传单个章节"""
        chapter_number = chapter_data['number']
        chapter_title = chapter_data['title']
        
        print(f"\n📖 正在上传第 {chapter_number} 章: {chapter_title}")
        
        # 上报开始上传
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            # TODO: 实现实际上传逻辑
            # 这里先模拟上传
            time.sleep(random.uniform(2, 5))
            
            # 模拟成功
            success = True
            
            if success:
                self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
                print(f"  ✓ 上传成功")
                return True
            else:
                raise Exception("上传失败")
                
        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ 上传失败: {error_msg}")
            
            # 上报失败
            self.reporter.report(
                chapter_number, 
                'failed',
                chapter_title=chapter_title,
                error_message=error_msg,
                error_type='upload_error',
                error_detail={
                    'traceback': '',
                    'page_url': self.page.url if self.page else ''
                },
                page_url=self.page.url if self.page else ''
            )
            return False
    
    def close(self):
        """关闭连接"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def main():
    """主函数"""
    print("=" * 60)
    print("大文娱创作平台 - 本地一键上传")
    print("=" * 60)
    print(f"小说: {NOVEL_TITLE}")
    print(f"平台: {PLATFORM}")
    print(f"任务: {TASK_ID}")
    print("=" * 60)
    
    # 创建上报器
    reporter = UploadReporter(API_BASE_URL, TASK_ID, USER_TOKEN)
    
    # 创建上传器
    uploader = FanqieUploader(reporter)
    
    # 连接 Chrome
    if not uploader.connect_chrome():
        print("\n请按回车键退出...")
        input()
        sys.exit(1)
    
    # 检查登录
    if not uploader.check_login():
        print("\n请按回车键退出...")
        input()
        sys.exit(1)
    
    # 加载章节数据
    chapters_file = Path(__file__).parent / "chapters.json"
    if not chapters_file.exists():
        print(f"✗ 未找到章节数据文件: {chapters_file}")
        print("\n请按回车键退出...")
        input()
        sys.exit(1)
    
    with open(chapters_file, 'r', encoding='utf-8') as f:
        chapters = json.load(f)
    
    print(f"\n共 {len(chapters)} 章待上传")
    print("-" * 60)
    
    # 上传章节
    success_count = 0
    failed_count = 0
    
    for i, chapter in enumerate(chapters, 1):
        print(f"\n[{i}/{len(chapters)}] ", end="")
        
        if uploader.upload_chapter(chapter):
            success_count += 1
        else:
            failed_count += 1
        
        # 随机延时，避免频率限制
        if i < len(chapters):
            delay = random.uniform(3, 8)
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 关闭连接
    uploader.close()
    
    # 显示结果
    print("\n" + "=" * 60)
    print("上传完成!")
    print(f"成功: {success_count} 章")
    print(f"失败: {failed_count} 章")
    print(f"\n可在网页查看详情: {API_BASE_URL}/upload-tasks/{TASK_ID}")
    print("=" * 60)
    
    print("\n请按回车键退出...")
    input()


if __name__ == "__main__":
    main()
