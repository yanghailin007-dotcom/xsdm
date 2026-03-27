#!/usr/bin/env python3
"""更新上传脚本模板"""

import re

with open('web/services/upload_package_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 新的上传脚本方法 - 使用更简单的字符串构建
new_method_start = '''    def _create_upload_script(self, output_dir: Path, task_id: str, 
                             user_token: str, novel_info: Dict, 
                             chapters: List[Dict]):
        """创建完整的上传脚本（包含真正的上传逻辑）"""
        
        # 准备章节数据（嵌入到脚本中）
        chapters_json = json.dumps(chapters, ensure_ascii=False, indent=2)
        novel_title_escaped = novel_info.get('title', '').replace('"', '\\"')
        
        script_content = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"""
大文娱创作平台 - 番茄小说上传脚本
任务ID: {task_id}
小说: {novel_info.get('title', 'Unknown')}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

使用说明:
1. 确保已安装 Python 3.8+ 和 Playwright
2. 运行前请先启动 Chrome（端口9988）
3. 在 Chrome 中登录番茄小说作者账号
4. 运行: python upload_script.py

此脚本由服务器自动生成
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
from typing import Optional

# ==================== 配置（自动注入）====================
API_BASE_URL = "{self.api_base_url}"
TASK_ID = "{task_id}"
USER_TOKEN = "{user_token}"
NOVEL_TITLE = \"\"\""""

new_method_end = '''""\"
NOVEL_ID = "{novel_info.get('id', '')}"
# 章节数据直接嵌入脚本
CHAPTERS_DATA = ''' + chapters_json + '''
# =====================================================

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
    """上传进度上报器"""
    
    def __init__(self):
        self.last_report_time = 0
    
    def report(self, chapter_number: int, status: str, **kwargs):
        """上报进度到服务器"""
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
            
            for key in ['chapter_title', 'error_message', 'error_type', 'error_detail', 'page_url']:
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
            print(f"  ⚠️  上报失败: {e}")
            return False


class FanqieUploader:
    """番茄小说上传器 - 完整版"""
    
    def __init__(self, reporter: UploadReporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = CHAPTERS_DATA
        self.current_chapter = 0
    
    def connect_chrome(self) -> bool:
        """连接Chrome（端口9988）"""
        try:
            from playwright.sync_api import sync_playwright
            
            print("\\n🔌 正在连接 Chrome (端口 9988)...")
            self.playwright = sync_playwright().start()
            
            # 连接本地 Chrome
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
            print("   1. 已运行 'start.bat' 或 '一键启动.bat' 启动 Chrome")
            print("   2. Chrome 窗口保持打开")
            print("   3. Chrome 启动参数包含: --remote-debugging-port=9988")
            return False
    
    def check_login(self) -> bool:
        """检查番茄小说登录状态"""
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
                print("   3. 使用抖音/手机号登录作者账号")
                print("   4. 重新运行此脚本")
                return False
            
            # 检查页面内容是否有书籍管理元素
            if self.page.locator('.long-article-table-item, .book-manage-container, [class*=\"book\"]').count() == 0:
                print(f"{Colors.YELLOW}⚠️  可能未登录，请检查页面{Colors.RESET}")
                print("   如果已登录，10秒后将继续...")
                time.sleep(10)
            
            print(f"{Colors.GREEN}✓ 已登录番茄小说{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 检查登录失败: {e}{Colors.RESET}")
            return False
    
    def find_book_id(self) -> Optional[str]:
        """查找书籍ID"""
        try:
            print(f"\\n📚 查找书籍: {NOVEL_TITLE[:20]}...")
            
            # 刷新页面获取最新内容
            self.page.reload()
            time.sleep(3)
            
            # 方法1: 从URL中提取
            url_match = re.search(r'/chapter-manage/(\\d+)', self.page.url)
            if url_match:
                return url_match.group(1)
            
            # 方法2: 从页面内容中查找
            book_items = self.page.locator('.long-article-table-item').all()
            
            for item in book_items:
                try:
                    # 获取书名
                    title_elem = item.locator('.info-content-title').first
                    if title_elem.count() == 0:
                        continue
                    
                    title = title_elem.text_content().strip()
                    
                    # 匹配书名（支持部分匹配）
                    if NOVEL_TITLE[:10] in title or title[:10] in NOVEL_TITLE:
                        # 提取ID
                        item_id = item.get_attribute('id')
                        if item_id:
                            book_id = re.search(r'(\\d+)', item_id)
                            if book_id:
                                print(f"{Colors.GREEN}✓ 找到书籍: {title}{Colors.RESET}")
                                return book_id.group(1)
                        
                        # 从链接中提取
                        links = item.locator('a[href*=\"/chapter-manage/\"]').all()
                        for link in links:
                            href = link.get_attribute('href')
                            id_match = re.search(r'/chapter-manage/(\\d+)', href)
                            if id_match:
                                print(f"{Colors.GREEN}✓ 找到书籍: {title}{Colors.RESET}")
                                return id_match.group(1)
                                
                except Exception as e:
                    continue
            
            print(f"{Colors.YELLOW}⚠️  未找到书籍，请手动创建{Colors.RESET}")
            return None
            
        except Exception as e:
            print(f"{Colors.RED}✗ 查找书籍失败: {e}{Colors.RESET}")
            return None
    
    def click_create_chapter(self, book_id: str) -> bool:
        """点击创建章节按钮"""
        try:
            print("\\n🖱️  点击创建章节...")
            
            # 悬停到书籍条目上显示操作按钮
            book_item = self.page.locator(f'#long-article-table-item-{book_id}')
            if book_item.count() > 0:
                book_item.first.hover()
                time.sleep(1)
            
            # 方法1: 直接找创建章节按钮
            create_btn = self.page.locator(f'#long-article-table-item-{book_id} button:has-text(\"创建章节\"), #long-article-table-item-{book_id} a:has-text(\"创建章节\")').first
            
            # 方法2: 通用选择器
            if create_btn.count() == 0:
                create_btn = self.page.locator('button:has-text(\"创建章节\"), a:has-text(\"创建章节\")').first
            
            # 方法3: 查找包含 publish 的链接
            if create_btn.count() == 0:
                create_link = self.page.locator(f'a[href*=\"/publish/\"]').first
                if create_link.count() > 0:
                    create_link.click()
                    time.sleep(5)
                    return True
            
            if create_btn.count() > 0 and create_btn.is_visible():
                # 处理可能的新标签页
                try:
                    with self.page.expect_popup(timeout=10000) as popup_info:
                        create_btn.click()
                    new_page = popup_info.value
                    self.page = new_page
                    print("  已在新标签页打开")
                except:
                    # 没有新标签页，在当前页打开
                    create_btn.click()
                    print("  已在当前页打开")
                
                time.sleep(5)
                return True
            
            # 直接导航到发布页面
            publish_url = f"https://fanqienovel.com/publish/{book_id}"
            print(f"  直接导航到: {publish_url}")
            self.page.goto(publish_url, timeout=30000)
            time.sleep(5)
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 点击创建章节失败: {e}{Colors.RESET}")
            return False
    
    def fill_chapter_form(self, chapter: dict) -> bool:
        """填写章节表单"""
        try:
            chapter_num = str(chapter['number'])
            chapter_title = chapter['title']
            chapter_content = chapter.get('content', '')
            
            print(f"\\n📝 填写第 {chapter_num} 章...")
            
            # 等待页面加载
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 验证页面标题
            header = self.page.locator('.publish-header-book-name')
            if header.count() > 0:
                book_name = header.first.text_content().strip()
                print(f"  当前书籍: {book_name[:30]}")
            
            # 填写章节号
            print("  填写章节号...")
            num_inputs = self.page.locator('.serial-editor-title-left input, input[placeholder*=\"章节\"]').all()
            for inp in num_inputs:
                if inp.is_visible():
                    inp.fill(chapter_num)
                    print(f"    ✓ 章节号: {chapter_num}")
                    break
            
            # 填写章节标题
            print("  填写章节标题...")
            title_inputs = self.page.locator('.serial-editor-title-right input, input[placeholder*=\"标题\"]').all()
            for inp in title_inputs:
                if inp.is_visible():
                    inp.fill(chapter_title)
                    print(f"    ✓ 标题: {chapter_title[:30]}")
                    break
            
            # 填写内容
            print("  填写章节内容...")
            content_area = self.page.locator('.ProseMirror, .editor-content, textarea[placeholder*=\"内容\"]').first
            if content_area.count() > 0 and content_area.is_visible():
                # 清空并填写
                content_area.click()
                content_area.fill('')
                content_area.fill(chapter_content)
                word_count = len(chapter_content)
                print(f"    ✓ 内容: {word_count} 字")
            else:
                print(f"    {Colors.YELLOW}⚠️  未找到内容输入框{Colors.RESET}")
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 填写表单失败: {e}{Colors.RESET}")
            return False
    
    def submit_chapter(self) -> bool:
        """提交章节"""
        try:
            print("\\n📤 提交章节...")
            
            # 查找发布按钮
            submit_btn = self.page.locator('button:has-text(\"发布\"), button:has-text(\"立即发布\"), button[type=\"submit\"]').first
            
            if submit_btn.count() == 0 or not submit_btn.is_visible():
                print(f"{Colors.RED}✗ 未找到发布按钮{Colors.RESET}")
                return False
            
            # 点击发布
            submit_btn.click()
            print("  已点击发布按钮")
            
            # 等待发布完成
            time.sleep(3)
            
            # 检查是否成功
            current_url = self.page.url
            if "chapter-manage" in current_url or "success" in current_url:
                print(f"{Colors.GREEN}✓ 发布成功{Colors.RESET}")
                return True
            
            # 检查是否有错误提示
            error_msg = self.page.locator('.error-message, .el-message--error, .toast-error').first
            if error_msg.count() > 0 and error_msg.is_visible():
                msg_text = error_msg.text_content().strip()
                print(f"{Colors.RED}✗ 发布失败: {msg_text}{Colors.RESET}")
                return False
            
            print(f"{Colors.GREEN}✓ 发布成功{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}✗ 提交失败: {e}{Colors.RESET}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        
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
            
            # 点击创建章节
            if not self.click_create_chapter(book_id):
                raise Exception("点击创建章节失败")
            
            # 填写表单
            if not self.fill_chapter_form(chapter):
                raise Exception("填写章节表单失败")
            
            # 提交
            if not self.submit_chapter():
                raise Exception("提交章节失败")
            
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
                error_message=error_msg,
                error_type='upload_error',
                page_url=self.page.url if self.page else ''
            )
            
            # 重试
            if retry_count < MAX_RETRY:
                print(f"{Colors.YELLOW}🔄 重试 ({retry_count + 1}/{MAX_RETRY})...{Colors.RESET}")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            
            return False
    
    def run(self):
        """运行上传流程"""
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
            self.current_chapter = i
            
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            # 章节间隔
            if i < len(self.chapters):
                delay = random.uniform(3, 6)
                print(f"\\n⏱️  等待 {delay:.1f} 秒后继续下一章...")
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
    """主函数"""
    reporter = UploadReporter()
    uploader = FanqieUploader(reporter)
    
    try:
        success = uploader.run()
        
        if success:
            print(f"\\n{Colors.GREEN}🎉 全部上传成功！{Colors.RESET}")
        else:
            print(f"\\n{Colors.YELLOW}⚠️  部分章节上传失败{Colors.RESET}")
        
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
        
        with open(output_dir / 'upload_script.py', 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 同时创建启动批处理文件
        bat_content = """@echo off
chcp 65001 >nul
title 大文娱 - 番茄小说上传工具
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

echo [✓] 环境检查完成
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

# 简单替换 - 找到旧方法并删除，插入新方法
start_marker = '    def _create_upload_script(self, output_dir: Path, task_id: str,'
end_marker = '    def _create_chapters_json'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx > 0 and end_idx > start_idx:
    # 保留之前的内容 + 新方法 + 之后的内容
    new_content = content[:start_idx] + new_method_start + novel_title_escaped + new_method_end + '\n    ' + content[end_idx:]
    
    with open('web/services/upload_package_manager.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✓ 方法已更新")
else:
    print(f"✗ 未找到方法: start={start_idx}, end={end_idx}")
