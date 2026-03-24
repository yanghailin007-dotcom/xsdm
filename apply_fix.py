#!/usr/bin/env python3
"""应用修复 - 替换 _create_upload_script 方法"""

# 读取文件
with open('web/services/upload_package_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到方法的开始和结束
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'def _create_upload_script(self, output_dir: Path, task_id: str,' in line:
        start_idx = i
    if start_idx is not None and 'def _create_chapters_json' in line:
        end_idx = i
        break

print(f"Found method at lines {start_idx+1} to {end_idx}")

# 新的方法内容
new_method = '''    def _create_upload_script(self, output_dir: Path, task_id: str, 
                             user_token: str, novel_info: Dict, 
                             chapters: List[Dict]):
        """创建完整的上传脚本（包含真正的番茄小说上传逻辑）"""
        
        import json as json_mod
        chapters_json_str = json_mod.dumps(chapters, ensure_ascii=False, indent=2)
        novel_title_str = novel_info.get('title', '').replace('"', '\\"')
        api_url = self.api_base_url
        
        # 使用 % 格式化避免嵌套 f-string 问题
        script_template = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"""
大文娱创作平台 - 番茄小说上传脚本
任务ID: %%task_id%%
小说: %%novel_title%%
生成时间: %%datetime%%

使用说明:
1. 确保已安装 Python 3.8+ 和 Playwright
2. 运行前请先启动 Chrome（端口9988）
3. 在 Chrome 中登录番茄小说作者账号
4. 运行: python upload_script.py
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

# ==================== 配置 ====================
API_BASE_URL = "%%api_url%%"
TASK_ID = "%%task_id%%"
USER_TOKEN = "%%user_token%%"
NOVEL_TITLE = """%%novel_title_escaped%%"""
NOVEL_ID = "%%novel_id%%"
CHAPTERS_DATA = %%chapters_json%%
# =============================================

REPORT_INTERVAL = 3
MAX_RETRY = 3


class Colors:
    GREEN = '\\033[92m'
    RED = '\\033[91m'
    YELLOW = '\\033[93m'
    BLUE = '\\033[94m'
    CYAN = '\\033[96m'
    RESET = '\\033[0m'


class UploadReporter:
    \"\"\"上传进度上报器\"\"\"
    
    def __init__(self):
        self.last_report_time = 0
    
    def report(self, chapter_number, status, **kwargs):
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
            
            response = requests.post(
                f"{API_BASE_URL}/api/local-upload/report",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"  ⚠️ 上报失败: {e}")
            return False


class FanqieUploader:
    \"\"\"番茄小说上传器\"\"\"
    
    def __init__(self, reporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = CHAPTERS_DATA
    
    def connect_chrome(self):
        \"\"\"连接Chrome（端口9988）\"\"\"
        try:
            from playwright.sync_api import sync_playwright
            
            print("\\n🔌 正在连接 Chrome (端口 9988)...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9988")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            print(f"{Colors.GREEN}✓ 已连接到 Chrome{Colors.RESET}")
            print(f"  当前页面: {self.page.url[:60]}...")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 连接 Chrome 失败: {e}{Colors.RESET}")
            print("\\n💡 请确保:")
            print("   1. 已运行 'start.bat' 启动 Chrome")
            print("   2. Chrome 窗口保持打开")
            print("   3. Chrome 启动参数: --remote-debugging-port=9988")
            return False
    
    def check_login(self):
        \"\"\"检查番茄小说登录状态\"\"\"
        try:
            print("\\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            current_url = self.page.url
            
            # 检查是否跳转到登录页
            if "login" in current_url or "auth" in current_url:
                print(f"{Colors.RED}✗ 未登录番茄小说{Colors.RESET}")
                print("\\n💡 请在 Chrome 中:")
                print("   1. 访问 https://fanqienovel.com")
                print("   2. 点击右上角登录")
                print("   3. 使用抖音/手机号登录")
                print("   4. 重新运行此脚本")
                return False
            
            print(f"{Colors.GREEN}✓ 已登录番茄小说{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 检查登录失败: {e}{Colors.RESET}")
            return False
    
    def find_book_id(self):
        \"\"\"查找书籍ID\"\"\"
        try:
            print(f"\\n📚 查找书籍: {NOVEL_TITLE[:20]}...")
            self.page.reload()
            time.sleep(3)
            
            # 从URL提取
            url_match = re.search(r'/chapter-manage/(\\d+)', self.page.url)
            if url_match:
                return url_match.group(1)
            
            # 从页面查找
            book_items = self.page.locator('.long-article-table-item').all()
            
            for item in book_items:
                try:
                    title_elem = item.locator('.info-content-title').first
                    if title_elem.count() == 0:
                        continue
                    
                    title = title_elem.text_content().strip()
                    
                    # 匹配书名（支持部分匹配）
                    if NOVEL_TITLE[:10] in title or title[:10] in NOVEL_TITLE:
                        # 从链接提取ID
                        links = item.locator('a[href*=\"/chapter-manage/\"]').all()
                        for link in links:
                            href = link.get_attribute('href')
                            id_match = re.search(r'/chapter-manage/(\\d+)', href)
                            if id_match:
                                print(f"{Colors.GREEN}✓ 找到书籍: {title}{Colors.RESET}")
                                return id_match.group(1)
                except:
                    continue
            
            print(f"{Colors.YELLOW}⚠️ 未找到书籍，请手动创建{Colors.RESET}")
            return None
            
        except Exception as e:
            print(f"{Colors.RED}✗ 查找书籍失败: {e}{Colors.RESET}")
            return None
    
    def upload_chapter(self, chapter, retry_count=0):
        \"\"\"上传单个章节\"\"\"
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        chapter_content = chapter.get('content', '')
        
        print(f"\\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"📖 第 {chapter_number} 章: {chapter_title[:40]}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        # 上报开始
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            # 获取书籍ID
            book_id = self.find_book_id()
            if not book_id:
                raise Exception("未找到书籍ID，请先在番茄小说创建书籍")
            
            # 导航到发布页面
            publish_url = f"https://fanqienovel.com/publish/{book_id}"
            print(f"  打开发布页面...")
            self.page.goto(publish_url, timeout=30000)
            time.sleep(5)
            
            # 填写章节号
            print("  填写章节号...")
            num_inputs = self.page.locator('input[placeholder*=\"章节\"], .serial-editor-title-left input').all()
            for inp in num_inputs:
                if inp.is_visible():
                    inp.fill(str(chapter_number))
                    print(f"    ✓ 章节号: {chapter_number}")
                    break
            
            # 填写标题
            print("  填写章节标题...")
            title_inputs = self.page.locator('input[placeholder*=\"标题\"], .serial-editor-title-right input').all()
            for inp in title_inputs:
                if inp.is_visible():
                    inp.fill(chapter_title)
                    print(f"    ✓ 标题: {chapter_title[:30]}")
                    break
            
            # 填写内容
            print("  填写章节内容...")
            content_area = self.page.locator('.ProseMirror, .editor-content').first
            if content_area.count() > 0 and content_area.is_visible():
                content_area.click()
                content_area.fill(chapter_content)
                word_count = len(chapter_content)
                print(f"    ✓ 内容: {word_count} 字")
            else:
                print(f"    {Colors.YELLOW}⚠️ 未找到内容输入框{Colors.RESET}")
            
            # 提交
            print("  点击发布...")
            submit_btn = self.page.locator('button:has-text(\"发布\"), button[type=\"submit\"]').first
            
            if submit_btn.count() > 0 and submit_btn.is_visible():
                submit_btn.click()
                time.sleep(3)
            
            # 上报成功
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            print(f"{Colors.GREEN}✓ 第 {chapter_number} 章上传成功{Colors.RESET}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{Colors.RED}✗ 上传失败: {error_msg}{Colors.RESET}")
            
            # 上报失败
            self.reporter.report(
                chapter_number, 'failed',
                chapter_title=chapter_title,
                error_message=error_msg
            )
            
            # 重试
            if retry_count < MAX_RETRY:
                print(f"{Colors.YELLOW}🔄 重试 ({retry_count + 1}/{MAX_RETRY})...{Colors.RESET}")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            
            return False
    
    def run(self):
        \"\"\"运行上传流程\"\"\"
        print("\\n" + "="*60)
        print(f"{Colors.BLUE}📚 大文娱创作平台 - 番茄小说上传{Colors.RESET}")
        print("="*60)
        print(f"小说标题: {NOVEL_TITLE}")
        print(f"章节数量: {len(self.chapters)} 章")
        print(f"任务ID: {TASK_ID}")
        print("="*60)
        
        # 连接Chrome
        if not self.connect_chrome():
            return False
        
        # 检查登录
        if not self.check_login():
            return False
        
        # 上传章节
        print("\\n" + "-"*60)
        success_count = 0
        failed_chapters = []
        
        for i, chapter in enumerate(self.chapters, 1):
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            # 章节间隔
            if i < len(self.chapters):
                delay = random.uniform(3, 6)
                print(f"\\n⏱️ 等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)
        
        # 关闭浏览器
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        # 结果统计
        print("\\n" + "="*60)
        print(f"{Colors.GREEN}✓ 上传完成{Colors.RESET}")
        print("-"*60)
        print(f"成功: {success_count}/{len(self.chapters)} 章")
        
        if failed_chapters:
            print(f"{Colors.RED}失败: {len(failed_chapters)} 章{Colors.RESET}")
            for ch in failed_chapters:
                print(f"  - 第 {ch['number']} 章: {ch['title'][:30]}")
        
        print(f"\\n查看详情: {API_BASE_URL}/pages/v2/fanqie-upload-v2?task={TASK_ID}")
        print("="*60)
        
        return len(failed_chapters) == 0


def main():
    \"\"\"主函数\"\"\"
    reporter = UploadReporter()
    uploader = FanqieUploader(reporter)
    
    try:
        success = uploader.run()
        
        if success:
            print(f"\\n{Colors.GREEN}🎉 全部上传成功！{Colors.RESET}")
        else:
            print(f"\\n{Colors.YELLOW}⚠️ 部分章节上传失败{Colors.RESET}")
        
        input("\\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\\n\\n用户取消上传")
        sys.exit(1)
    except Exception as e:
        print(f"\\n{Colors.RED}❌ 发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        input("\\n按回车键退出...")


if __name__ == "__main__":
    main()
"""
        
        # 替换变量
        script_content = script_template.replace('%%task_id%%', task_id)
        script_content = script_content.replace('%%novel_title%%', novel_info.get('title', 'Unknown'))
        script_content = script_content.replace('%%datetime%%', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        script_content = script_content.replace('%%api_url%%', api_url)
        script_content = script_content.replace('%%user_token%%', user_token)
        script_content = script_content.replace('%%novel_title_escaped%%', novel_title_str)
        script_content = script_content.replace('%%novel_id%%', novel_info.get('id', ''))
        script_content = script_content.replace('%%chapters_json%%', chapters_json_str)
        
        with open(output_dir / 'upload_script.py', 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 创建启动批处理
        bat_content = """@echo off
chcp 65001 >nul
title 大文娱 - 番茄小说上传
echo ============================================
echo  大文娱创作平台 - 番茄小说上传工具
echo ============================================
echo.
echo 正在检查环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [✓] Python 已安装
playwright --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 Playwright...
    pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
    playwright install chromium
)
echo [✓] Playwright 已安装
echo.
echo ============================================
echo  使用步骤:
echo  1. 确保 Chrome 已启动 (端口 9988)
echo  2. 确保已在 Chrome 登录番茄小说
echo  3. 按任意键开始上传
echo ============================================
echo.
pause

python upload_script.py

pause
"""
        with open(output_dir / '开始上传.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)

'''

# 替换
new_lines = lines[:start_idx] + [new_method] + lines[end_idx:]

with open('web/services/upload_package_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"OK: Replaced method at lines {start_idx+1} - {end_idx}")
