#!/usr/bin/env python3
"""修复上传脚本方法"""

# 读取原文件
with open('web/services/upload_package_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要替换的行范围
start_line = None
end_line = None

for i, line in enumerate(lines):
    if 'def _create_upload_script(self, output_dir: Path, task_id: str,' in line:
        start_line = i
    if start_line is not None and 'def _create_chapters_json' in line:
        end_line = i
        break

if start_line is None or end_line is None:
    print(f"未找到方法: start={start_line}, end={end_line}")
    exit(1)

print(f"找到方法在第 {start_line+1} 到 {end_line} 行")

# 构建新方法 - 注意顺序：先定义变量，再使用
new_method = '''    def _create_upload_script(self, output_dir: Path, task_id: str, 
                             user_token: str, novel_info: Dict, 
                             chapters: List[Dict]):
        """创建完整的上传脚本（包含真正的上传逻辑）"""
        
        # 准备数据
        chapters_json = json.dumps(chapters, ensure_ascii=False, indent=2)
        novel_title = novel_info.get('title', '').replace('"', '\\"')
        novel_id = novel_info.get('id', '')
        api_url = self.api_base_url
        
        # 构建脚本内容
        script_parts = []
        script_parts.append("#!/usr/bin/env python3")
        script_parts.append("# -*- coding: utf-8 -*-")
        script_parts.append('"""')
        script_parts.append(f"大文娱创作平台 - 番茄小说上传脚本")
        script_parts.append(f"任务ID: {task_id}")
        script_parts.append(f"小说: {novel_info.get('title', 'Unknown')}")
        script_parts.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        script_parts.append('"""')
        script_parts.append("")
        script_parts.append("import os")
        script_parts.append("import sys")
        script_parts.append("import json")
        script_parts.append("import time")
        script_parts.append("import random")
        script_parts.append("import re")
        script_parts.append("import requests")
        script_parts.append("from pathlib import Path")
        script_parts.append("from datetime import datetime")
        script_parts.append("")
        script_parts.append(f'API_BASE_URL = "{api_url}"')
        script_parts.append(f'TASK_ID = "{task_id}"')
        script_parts.append(f'USER_TOKEN = "{user_token}"')
        script_parts.append(f'NOVEL_TITLE = """{novel_title}"""')
        script_parts.append(f'NOVEL_ID = "{novel_id}"')
        script_parts.append(f'CHAPTERS_DATA = {chapters_json}')
        script_parts.append("")
        
        # 添加核心类代码
        script_parts.append('''
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
    def __init__(self, reporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = CHAPTERS_DATA
    
    def connect_chrome(self):
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
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ 连接 Chrome 失败: {e}{Colors.RESET}")
            print("\\n💡 请确保已运行 'start.bat' 启动 Chrome")
            return False
    
    def check_login(self):
        try:
            print("\\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            if "login" in self.page.url:
                print(f"{Colors.RED}✗ 未登录番茄小说{Colors.RESET}")
                print("\\n💡 请在 Chrome 中登录 https://fanqienovel.com")
                return False
            print(f"{Colors.GREEN}✓ 已登录番茄小说{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ 检查登录失败: {e}{Colors.RESET}")
            return False
    
    def find_book_id(self):
        try:
            print(f"\\n📚 查找书籍: {NOVEL_TITLE[:20]}...")
            self.page.reload()
            time.sleep(3)
            
            # 从URL提取
            import re
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
                    if NOVEL_TITLE[:10] in title or title[:10] in NOVEL_TITLE:
                        links = item.locator('a[href*="/chapter-manage/"]').all()
                        for link in links:
                            href = link.get_attribute('href')
                            id_match = re.search(r'/chapter-manage/(\\d+)', href)
                            if id_match:
                                print(f"{Colors.GREEN}✓ 找到书籍: {title}{Colors.RESET}")
                                return id_match.group(1)
                except:
                    continue
            print(f"{Colors.YELLOW}⚠️ 未找到书籍{Colors.RESET}")
            return None
        except Exception as e:
            print(f"{Colors.RED}✗ 查找书籍失败: {e}{Colors.RESET}")
            return None
    
    def upload_chapter(self, chapter, retry_count=0):
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        chapter_content = chapter.get('content', '')
        
        print(f"\\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"📖 第 {chapter_number} 章: {chapter_title[:40]}")
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            book_id = self.find_book_id()
            if not book_id:
                raise Exception("未找到书籍ID")
            
            # 导航到发布页面
            publish_url = f"https://fanqienovel.com/publish/{book_id}"
            print(f"  打开发布页面...")
            self.page.goto(publish_url, timeout=30000)
            time.sleep(5)
            
            # 填写章节号
            print("  填写章节号...")
            num_inputs = self.page.locator('input[placeholder*="章节"], .serial-editor-title-left input').all()
            for inp in num_inputs:
                if inp.is_visible():
                    inp.fill(str(chapter_number))
                    break
            
            # 填写标题
            print("  填写标题...")
            title_inputs = self.page.locator('input[placeholder*="标题"], .serial-editor-title-right input').all()
            for inp in title_inputs:
                if inp.is_visible():
                    inp.fill(chapter_title)
                    break
            
            # 填写内容
            print("  填写内容...")
            content_area = self.page.locator('.ProseMirror, .editor-content').first
            if content_area.count() > 0 and content_area.is_visible():
                content_area.click()
                content_area.fill(chapter_content)
                print(f"    ✓ {len(chapter_content)} 字")
            
            # 提交
            print("  点击发布...")
            submit_btn = self.page.locator('button:has-text("发布"), button[type="submit"]').first
            if submit_btn.count() > 0 and submit_btn.is_visible():
                submit_btn.click()
                time.sleep(3)
            
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            print(f"{Colors.GREEN}✓ 第 {chapter_number} 章上传成功{Colors.RESET}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{Colors.RED}✗ 上传失败: {error_msg}{Colors.RESET}")
            self.reporter.report(chapter_number, 'failed', chapter_title=chapter_title, error_message=error_msg)
            
            if retry_count < MAX_RETRY:
                print(f"{Colors.YELLOW}🔄 重试 ({retry_count + 1}/{MAX_RETRY})...{Colors.RESET}")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            return False
    
    def run(self):
        print("\\n" + "="*60)
        print(f"{Colors.BLUE}📚 大文娱 - 番茄小说上传{Colors.RESET}")
        print(f"小说: {NOVEL_TITLE}")
        print(f"章节: {len(self.chapters)} 章")
        print("="*60)
        
        if not self.connect_chrome():
            return False
        if not self.check_login():
            return False
        
        success_count = 0
        failed_chapters = []
        
        for i, chapter in enumerate(self.chapters, 1):
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            if i < len(self.chapters):
                delay = random.uniform(3, 6)
                print(f"\\n⏱️ 等待 {delay:.1f} 秒...")
                time.sleep(delay)
        
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        print("\\n" + "="*60)
        print(f"{Colors.GREEN}✓ 上传完成{Colors.RESET}")
        print(f"成功: {success_count}/{len(self.chapters)} 章")
        if failed_chapters:
            print(f"{Colors.RED}失败: {len(failed_chapters)} 章{Colors.RESET}")
        print(f"\\n查看详情: {API_BASE_URL}/pages/v2/fanqie-upload-v2?task={TASK_ID}")
        print("="*60)
        return len(failed_chapters) == 0

def main():
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
        print("\\n用户取消")
    except Exception as e:
        print(f"\\n{Colors.RED}❌ 错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        input("\\n按回车键退出...")

if __name__ == "__main__":
    main()
'''
        
        script_content = "\\n".join(script_parts) + script_core
        
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
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [✓] Python 已安装
echo.
echo 使用步骤:
echo 1. 确保 Chrome 已启动 (端口 9988)
echo 2. 确保已在 Chrome 登录番茄小说
echo 3. 按任意键开始上传
echo.
pause
python upload_script.py
pause
"""
        with open(output_dir / '开始上传.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)

'''

# 替换
new_lines = lines[:start_line] + [new_method] + lines[end_line:]

with open('web/services/upload_package_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✓ 已替换第 {start_line+1} 到 {end_line} 行")
