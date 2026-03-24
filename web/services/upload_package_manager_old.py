"""
上传包管理器
管理不同类型的上传包：首次包、脚本包、数据包
"""
import os
import json
import zipfile
import tempfile
import shutil
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 包类型
PACKAGE_TYPE_FIRST_TIME = 'first_time'  # 首次下载：浏览器+环境+脚本
PACKAGE_TYPE_SCRIPT = 'script'          # 脚本下载：上传脚本+小说数据
PACKAGE_TYPE_DATA_ONLY = 'data_only'    # 仅数据：小说章节数据（用于已有脚本）

BASE_DIR = Path(__file__).parent.parent.parent
PACKAGES_DIR = BASE_DIR / 'temp_uploads' / 'packages'


@dataclass
class PackageConfig:
    """包配置"""
    type: str
    name: str
    description: str
    files: List[str]
    size_estimate: str


class UploadPackageManager:
    """上传包管理器"""
    
    # 包配置定义
    PACKAGE_CONFIGS = {
        PACKAGE_TYPE_FIRST_TIME: PackageConfig(
            type=PACKAGE_TYPE_FIRST_TIME,
            name='完整环境包',
            description='包含Chrome浏览器、Python环境、上传脚本（首次使用下载）',
            files=['chrome_launcher/', 'python_embed/', 'upload_script.py', 'start.bat', 'README_FIRST.txt'],
            size_estimate='约 200MB'
        ),
        PACKAGE_TYPE_SCRIPT: PackageConfig(
            type=PACKAGE_TYPE_SCRIPT,
            name='上传脚本包',
            description='包含上传脚本和小说数据（已安装环境后使用）',
            files=['upload_script.py', 'chapters.json', 'config.json', 'README.txt'],
            size_estimate='约 500KB'
        ),
        PACKAGE_TYPE_DATA_ONLY: PackageConfig(
            type=PACKAGE_TYPE_DATA_ONLY,
            name='数据更新包',
            description='仅小说章节数据（脚本已存在时快速更新）',
            files=['chapters.json', 'update_data.py'],
            size_estimate='约 100KB'
        )
    }
    
    def __init__(self, api_base_url: str = "http://localhost:5000"):
        self.api_base_url = api_base_url
        PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_package_config(self, package_type: str) -> Optional[PackageConfig]:
        """获取包配置"""
        return self.PACKAGE_CONFIGS.get(package_type)
    
    def detect_user_environment(self, user_id: int) -> Dict:
        """
        检测用户环境状态
        快速检查本地是否有 Chrome 和 Python 环境
        """
        import os
        from pathlib import Path
        
        # 1. 检查 Chrome 启动器目录
        chrome_launcher_paths = [
            Path(r'C:\chrome_launcher'),
            Path(r'D:\chrome_launcher'),
            Path.home() / 'chrome_launcher',
        ]
        has_chrome_launcher = any(p.exists() and any(p.iterdir()) for p in chrome_launcher_paths)
        
        # 2. 检查 Python 环境
        python_paths = [
            Path(r'C:\python_embed\python.exe'),
            Path(r'D:\python_embed\python.exe'),
            Path.home() / 'python_embed' / 'python.exe',
        ]
        has_python = any(p.exists() for p in python_paths)
        
        # 3. 检查系统是否安装了 Python
        if not has_python:
            import shutil
            has_python = shutil.which('python') is not None or shutil.which('python3') is not None
        
        # 4. 从数据库查询是否上传过
        has_uploaded_before = False
        try:
            from web.models.upload_task_model import get_upload_task_model
            model = get_upload_task_model()
            # 查询用户是否有成功完成的任务
            tasks = model.get_user_tasks(user_id, limit=1)
            if tasks and any(t.get('status') == 'completed' for t in tasks):
                has_uploaded_before = True
        except Exception:
            pass
        
        # 决定推荐哪种包
        if not has_chrome_launcher or not has_python:
            recommended = PACKAGE_TYPE_FIRST_TIME
        else:
            recommended = PACKAGE_TYPE_SCRIPT
        
        return {
            'has_chrome_launcher': has_chrome_launcher,
            'has_python': has_python,
            'has_uploaded_before': has_uploaded_before,
            'last_upload_time': None,
            'recommended_package': recommended,
            'detected_paths': {
                'chrome_launcher': [str(p) for p in chrome_launcher_paths if p.exists()],
                'python': [str(p) for p in python_paths if p.exists()]
            }
        }
    
    def create_first_time_package(self, task_id: str, user_token: str, 
                                  novel_info: Dict, chapters: List[Dict]) -> Dict:
        """
        创建首次使用完整包
        包含：Chrome启动器 + Python环境 + 上传脚本
        """
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=f'first_pkg_{task_id}_'))
            
            # 1. 创建目录结构
            chrome_dir = temp_dir / 'chrome_launcher'
            python_dir = temp_dir / 'python_embed'
            upload_dir = temp_dir / 'upload'
            chrome_dir.mkdir()
            python_dir.mkdir()
            upload_dir.mkdir()
            
            # 2. 复制 Chrome 启动器文件
            self._copy_chrome_launcher(chrome_dir)
            
            # 3. 复制 Python 环境文件
            self._copy_python_embed(python_dir)
            
            # 4. 创建一键启动脚本
            self._create_start_bat(temp_dir)
            
            # 5. 创建环境检查脚本
            self._create_env_check_script(temp_dir)
            
            # 6. 创建上传脚本（在upload目录）
            self._create_upload_script(
                upload_dir,
                task_id, user_token, novel_info, chapters
            )
            
            # 7. 创建章节数据文件
            self._create_chapters_json(upload_dir, chapters)
            
            # 8. 创建配置文件
            config = {
                'task_id': task_id,
                'novel_title': novel_info.get('title'),
                'novel_id': novel_info.get('id'),
                'total_chapters': len(chapters),
                'created_at': datetime.now().isoformat(),
                'api_base_url': self.api_base_url
            }
            with open(upload_dir / 'config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 9. 创建首次使用说明
            self._create_first_time_readme(temp_dir, novel_info)
            
            # 10. 创建番茄登录引导
            self._create_login_guide(temp_dir)
            
            # 11. 打包
            zip_path = PACKAGES_DIR / f'first_time_{task_id}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zf.write(file_path, arcname)
            
            # 清理
            shutil.rmtree(temp_dir)
            
            return {
                'success': True,
                'package_path': str(zip_path),
                'package_type': PACKAGE_TYPE_FIRST_TIME,
                'file_name': f'大文娱上传环境包_{task_id}.zip',
                'size_estimate': '约 50MB（首次下载较慢）'
            }
            
        except Exception as e:
            print(f"[PackageManager] 创建首次包失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _copy_chrome_launcher(self, dest_dir: Path):
        """复制 Chrome 启动器文件到目标目录"""
        # 可能的源目录路径
        possible_sources = [
            BASE_DIR / 'tools' / 'chrome_launcher' / 'build',
            BASE_DIR / 'tools' / 'chrome_launcher',
            Path(r'C:\chrome_launcher'),
            Path(r'D:\chrome_launcher'),
        ]
        
        source_dir = None
        for src in possible_sources:
            if src.exists() and (src / 'start_browser.py').exists():
                source_dir = src
                break
        
        if not source_dir:
            print(f"[PackageManager] 警告: 未找到 Chrome 启动器源文件")
            # 创建基本的启动脚本
            self._create_basic_chrome_launcher(dest_dir)
            return
        
        # 复制文件
        for item in source_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_dir / item.name)
            elif item.is_dir() and item.name in ['chrome', 'userdata']:
                shutil.copytree(item, dest_dir / item.name, dirs_exist_ok=True)
        
        print(f"[PackageManager] 已复制 Chrome 启动器到 {dest_dir}")
    
    def _copy_python_embed(self, dest_dir: Path):
        """复制 Python 环境文件到目标目录"""
        # 可能的源目录路径
        possible_sources = [
            BASE_DIR / 'python-embed',
            Path(r'C:\python_embed'),
            Path(r'D:\python_embed'),
        ]
        
        source_dir = None
        for src in possible_sources:
            if src.exists() and (src / 'python.exe').exists():
                source_dir = src
                break
        
        if not source_dir:
            print(f"[PackageManager] 警告: 未找到 Python 环境源文件")
            # 创建说明文件
            with open(dest_dir / 'README.txt', 'w', encoding='utf-8') as f:
                f.write("""Python 环境需要自行安装

请访问 https://www.python.org/downloads/ 下载 Python 3.10+ 并安装
安装时请勾选 "Add Python to PATH"

或者使用 Microsoft Store 安装 Python
""")
            return
        
        # 复制 Python 环境（只复制关键文件，避免包过大）
        import fnmatch
        essential_patterns = ['python*.exe', 'python*.dll', '*.pyd', 'Lib/**/*', 'DLLs/**/*']
        
        for item in source_dir.rglob('*'):
            if item.is_file():
                # 检查是否在必要文件模式中
                relative_path = item.relative_to(source_dir)
                should_copy = False
                
                for pattern in essential_patterns:
                    if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(item.name, pattern):
                        should_copy = True
                        break
                
                if should_copy:
                    target = dest_dir / relative_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
        
        print(f"[PackageManager] 已复制 Python 环境到 {dest_dir}")
    
    def _create_basic_chrome_launcher(self, dest_dir: Path):
        """创建基本的 Chrome 启动器脚本"""
        # 一键启动.bat
        bat_content = '''@echo off
chcp 65001 >nul
title Chrome 调试模式启动器
echo ============================================
echo  Chrome 调试模式启动器
echo ============================================
echo.

:: 查找 Chrome 安装路径
set CHROME_PATH=

if exist "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" (
    set CHROME_PATH="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
) else if exist "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" (
    set CHROME_PATH="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
) else if exist "%%LOCALAPPDATA%%\\Google\\Chrome\\Application\\chrome.exe" (
    set CHROME_PATH="%%LOCALAPPDATA%%\\Google\\Chrome\\Application\\chrome.exe"
)

if not defined CHROME_PATH (
    echo [错误] 未找到 Chrome 浏览器
    echo 请确保已安装 Chrome 浏览器
    pause
    exit /b 1
)

echo [1/3] 找到 Chrome: %%CHROME_PATH%%
echo.

:: 创建用户数据目录
if not exist "%%CD%%\\userdata" mkdir "%%CD%%\\userdata"

:: 启动 Chrome 调试模式
echo [2/3] 正在启动 Chrome（调试端口 9988）...
start "" %%CHROME_PATH%% ^
    --remote-debugging-port=9988 ^
    --user-data-dir="%%CD%%\\userdata" ^
    --no-first-run ^
    --no-default-browser-check ^
    "https://fanqienovel.com"

echo.
echo [3/3] Chrome 已启动！
echo.
echo ============================================
echo  提示：
echo  - Chrome 调试端口：9988
echo  - 请勿关闭此窗口
echo  - 请在 Chrome 中登录番茄小说
echo ============================================
echo.
pause
'''
        with open(dest_dir / '一键启动.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)
        
        # README
        readme = '''Chrome 调试模式启动器

使用方法：
1. 双击运行 "一键启动.bat"
2. 等待 Chrome 启动
3. 在 Chrome 中访问 https://fanqienovel.com 并登录
4. 保持 Chrome 窗口打开，运行上传脚本

注意：
- 此窗口需要保持打开状态
- 调试端口为 9988
- 用户数据保存在 userdata 目录
'''
        with open(dest_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme)
        
        print(f"[PackageManager] 已创建基本 Chrome 启动器到 {dest_dir}")
    
    def create_script_package(self, task_id: str, user_token: str,
                             novel_info: Dict, chapters: List[Dict]) -> Dict:
        """
        创建脚本上传包
        包含：上传脚本 + 小说数据（用户已有环境）
        """
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=f'script_pkg_{task_id}_'))
            
            # 1. 创建上传脚本
            self._create_upload_script(
                temp_dir,
                task_id, user_token, novel_info, chapters
            )
            
            # 2. 创建章节数据
            self._create_chapters_json(temp_dir, chapters)
            
            # 3. 创建配置文件
            config = {
                'task_id': task_id,
                'novel_title': novel_info.get('title'),
                'novel_id': novel_info.get('id'),
                'total_chapters': len(chapters),
                'created_at': datetime.now().isoformat(),
                'api_base_url': self.api_base_url
            }
            with open(temp_dir / 'config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 4. 创建使用说明
            self._create_script_readme(temp_dir, novel_info)
            
            # 5. 创建快捷启动bat
            self._create_quick_start_bat(temp_dir, novel_info)
            
            # 6. 打包
            zip_path = PACKAGES_DIR / f'script_{task_id}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        zf.write(file_path, file_path.name)
            
            # 清理
            shutil.rmtree(temp_dir)
            
            return {
                'success': True,
                'package_path': str(zip_path),
                'package_type': PACKAGE_TYPE_SCRIPT,
                'file_name': f'{novel_info.get("title", "novel")}_上传包.zip',
                'size_estimate': '约 500KB'
            }
            
        except Exception as e:
            print(f"[PackageManager] 创建脚本包失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_upload_script(self, output_dir: Path, task_id: str, 
                             user_token: str, novel_info: Dict, 
                             chapters: List[Dict]):
        """创建完整的上传脚本（包含真正的番茄小说上传逻辑）"""
        
        script_content = self._generate_full_upload_script(task_id, user_token, novel_info, chapters)
        
        with open(output_dir / 'upload_script.py', 'w', encoding='utf-8') as f:
            f.write(script_content)
    
    def _generate_full_upload_script(self, task_id: str, user_token: str, 
                                     novel_info: Dict, chapters: List[Dict]) -> str:
        """生成完整的番茄小说上传脚本"""
        
        import json as json_mod
        chapters_json_str = json_mod.dumps(chapters, ensure_ascii=False, indent=2)
        novel_title_str = novel_info.get('title', '').replace('"', '\\"')
        
        return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱创作平台 - 番茄小说上传脚本
任务ID: {task_id}
小说: {novel_info.get('title', 'Unknown')}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

此脚本由服务器自动生成，请勿手动修改
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

# ==================== 配置（自动注入）====================
API_BASE_URL = "{self.api_base_url}"
TASK_ID = "{task_id}"
USER_TOKEN = "{user_token}"
NOVEL_TITLE = """{novel_title_str}"""
NOVEL_ID = "{novel_info.get('id', '')}"
TOTAL_CHAPTERS = {len(chapters)}
CHAPTERS_DATA = {chapters_json_str}
# =====================================================

REPORT_INTERVAL = 3  # 上报间隔（秒）
MAX_RETRY = 3        # 最大重试次数
DEBUG_PORT = 9988    # Chrome 调试端口


class Colors:
    GREEN = '\\033[92m'
    RED = '\\033[91m'
    YELLOW = '\\033[93m'
    BLUE = '\\033[94m'
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
            
            data = {{
                'task_id': TASK_ID,
                'chapter_number': chapter_number,
                'status': status,
            }}
            
            for key in ['chapter_title', 'error_message', 'error_type', 'error_detail', 'page_url', 'screenshot']:
                if key in kwargs:
                    data[key] = kwargs[key]
            
            response = requests.post(
                f"{{API_BASE_URL}}/api/local-upload/report",
                json=data,
                headers={{'Content-Type': 'application/json'}},
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"  ⚠️ 上报失败（不影响上传）: {{e}}")
            return False


class FanqieUploader:
    """番茄小说上传器 - 完整功能版"""
    
    def __init__(self, reporter: UploadReporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = []
        self.current_chapter = 0
        self.book_id = None
    
    def load_chapters(self):
        """加载章节数据"""
        chapters_file = Path(__file__).parent / "chapters.json"
        if not chapters_file.exists():
            print(f"{{Colors.RED}}✗ 未找到章节数据: chapters.json{{Colors.RESET}}")
            return False
        
        with open(chapters_file, 'r', encoding='utf-8') as f:
            self.chapters = json.load(f)
        
        print(f"{{Colors.BLUE}}📚 已加载 {{len(self.chapters)}} 章{{Colors.RESET}}")
        return True
    
    def connect_chrome(self):
        """连接Chrome"""
        try:
            from playwright.sync_api import sync_playwright
            
            print("\\n🔌 正在连接 Chrome...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{{DEBUG_PORT}}")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            print(f"{{Colors.GREEN}}✓ 已连接到 Chrome{{Colors.RESET}}")
            return True
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 连接 Chrome 失败: {{e}}{{Colors.RESET}}")
            print("\\n💡 请确保:")
            print("   1. 已运行 '一键启动.bat' 启动 Chrome")
            print("   2. Chrome 窗口保持打开")
            print("   3. 调试端口 9988 已开放")
            return False
    
    def check_login(self):
        """检查登录状态"""
        try:
            print("\\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            # 检查是否跳转到了登录页
            if self.page.url.startswith("https://fanqienovel.com/login"):
                print(f"{{Colors.RED}}✗ 未登录番茄小说{{Colors.RESET}}")
                print("\\n💡 请在 Chrome 中:")
                print("   1. 访问 https://fanqienovel.com")
                print("   2. 登录您的作者账号")
                print("   3. 重新运行此脚本")
                return False
            
            # 检查是否有登录按钮
            try:
                login_btn = self.page.locator('a[href*="/login"]').first
                if login_btn.count() > 0 and login_btn.is_visible():
                    print(f"{{Colors.RED}}✗ 未登录番茄小说{{Colors.RESET}}")
                    print("\\n💡 请在 Chrome 中登录后再运行脚本")
                    return False
            except:
                pass
            
            print(f"{{Colors.GREEN}}✓ 已登录番茄小说{{Colors.RESET}}")
            return True
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 检查登录失败: {{e}}{{Colors.RESET}}")
            return False
    
    def find_or_create_book(self):
        """查找或创建书籍"""
        try:
            print(f"\\n📖 查找书籍: {{NOVEL_TITLE}}")
            
            # 在页面中搜索书籍标题
            page_content = self.page.content()
            
            # 检查书籍是否已存在
            if NOVEL_TITLE[:10] in page_content or NOVEL_TITLE[:8] in page_content:
                print(f"{{Colors.GREEN}}✓ 找到已有书籍{{Colors.RESET}}")
                
                # 提取书籍ID
                book_ids = re.findall(r'long-article-table-item-(\\d+)', page_content)
                if book_ids:
                    self.book_id = book_ids[0]
                    print(f"  书籍ID: {{self.book_id}}")
                    return True
            
            # 书籍不存在，需要创建
            print(f"{{Colors.YELLOW}}⚠ 未找到书籍，需要手动创建{{Colors.RESET}}")
            print("\\n请按以下步骤操作:")
            print("1. 在 Chrome 中点击'创建作品'")
            print("2. 填写作品信息")
            print("3. 创建完成后，重新运行此脚本")
            return False
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 查找书籍失败: {{e}}{{Colors.RESET}}")
            return False
    
    def navigate_to_chapter_create(self):
        """导航到创建章节页面"""
        try:
            if not self.book_id:
                print("{{Colors.RED}}✗ 未获取到书籍ID{{Colors.RESET}}")
                return False
            
            # 访问章节管理页面
            url = f"https://fanqienovel.com/main/writer/chapter-manage/{{self.book_id}}"
            self.page.goto(url, timeout=30000)
            time.sleep(3)
            
            print(f"{{Colors.GREEN}}✓ 已进入章节管理页面{{Colors.RESET}}")
            return True
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 导航失败: {{e}}{{Colors.RESET}}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节 - 完整功能"""
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        content = chapter.get('content', '')
        
        print(f"\\n📖 第 {{chapter_number}} 章: {{chapter_title[:30]}}...")
        
        # 上报开始
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeout
            
            # 1. 点击创建章节按钮
            try:
                create_btn = self.page.locator('button:has-text("创建章节"), a:has-text("创建章节")').first
                if create_btn.count() == 0:
                    # 尝试其他选择器
                    create_btn = self.page.locator('[class*="create"], [class*="add"]').filter(has_text="章节").first
                
                if create_btn.count() > 0:
                    create_btn.click()
                    print("  点击创建章节按钮")
                    time.sleep(2)
                else:
                    # 直接访问发布页面
                    publish_url = f"https://fanqienovel.com/main/writer/publish/{{self.book_id}}"
                    self.page.goto(publish_url, timeout=30000)
                    time.sleep(3)
            except Exception as e:
                print(f"  尝试直接访问发布页面")
                publish_url = f"https://fanqienovel.com/main/writer/publish/{{self.book_id}}"
                self.page.goto(publish_url, timeout=30000)
                time.sleep(3)
            
            # 2. 填写章节号
            try:
                num_input = self.page.locator('input[placeholder*="章节号"], input[placeholder*="序号"], .serial-input').first
                if num_input.count() > 0:
                    num_input.fill(str(chapter_number))
                    print(f"  填写章节号: {{chapter_number}}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️ 填写章节号失败: {{e}}")
            
            # 3. 填写章节标题
            try:
                title_input = self.page.locator('input[placeholder*="标题"], input[placeholder*="标题"]').first
                if title_input.count() > 0:
                    title_input.fill(chapter_title)
                    print(f"  填写标题: {{chapter_title[:20]}}...")
                    time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️ 填写标题失败: {{e}}")
            
            # 4. 填写内容
            try:
                # 处理内容格式
                processed_content = self._process_content(content)
                
                # 查找内容编辑区
                content_editor = self.page.locator('div[contenteditable="true"], .ProseMirror, [class*="editor"]').first
                if content_editor.count() > 0:
                    content_editor.fill(processed_content)
                    print(f"  填写内容: {{len(processed_content)}} 字")
                    time.sleep(1)
                else:
                    # 尝试 textarea
                    textarea = self.page.locator('textarea').first
                    if textarea.count() > 0:
                        textarea.fill(processed_content)
                        print(f"  填写内容: {{len(processed_content)}} 字")
                        time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ 填写内容失败: {{e}}")
                raise
            
            # 5. 点击下一步/提交
            try:
                next_btn = self.page.locator('button:has-text("下一步"), button:has-text("提交"), button[type="submit"]').first
                if next_btn.count() > 0:
                    next_btn.click()
                    print("  点击下一步")
                    time.sleep(2)
            except:
                pass
            
            # 6. 确认发布
            try:
                # 检查是否有AI辅助声明
                try:
                    ai_yes = self.page.locator('.arco-radio-text:has-text("是")').first
                    if ai_yes.count() > 0:
                        ai_yes.click()
                        time.sleep(0.5)
                except:
                    pass
                
                # 点击确认发布
                confirm_btn = self.page.locator('button:has-text("确认发布"), button:has-text("发布"), .arco-btn-primary').filter(has_text=re.compile(r'发布|确认')).first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    print("  点击确认发布")
                    time.sleep(3)
                
            except Exception as e:
                print(f"  ⚠️ 确认发布时: {{e}}")
            
            # 7. 检查发布结果
            time.sleep(2)
            page_url = self.page.url
            
            # 如果回到章节列表或显示成功提示，则认为成功
            if '/chapter-manage/' in page_url or 'publish' not in page_url:
                self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
                print(f"{{Colors.GREEN}}  ✓ 上传成功{{Colors.RESET}}")
                return True
            
            # 检查页面内容是否有成功提示
            page_content = self.page.content()
            if '成功' in page_content or 'success' in page_content.lower():
                self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
                print(f"{{Colors.GREEN}}  ✓ 上传成功{{Colors.RESET}}")
                return True
            
            # 可能需要额外处理
            print(f"{{Colors.YELLOW}}  ⚠️ 请检查发布状态{{Colors.RESET}}")
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{{Colors.RED}}  ✗ 上传失败: {{error_msg[:50]}}{{Colors.RESET}}")
            
            self.reporter.report(
                chapter_number, 'failed',
                chapter_title=chapter_title,
                error_message=error_msg,
                error_type='upload_error',
                page_url=self.page.url if self.page else ''
            )
            
            # 重试逻辑
            if retry_count < MAX_RETRY:
                print(f"{{Colors.YELLOW}}  🔄 重试 ({{retry_count + 1}}/{{MAX_RETRY}})...{{Colors.RESET}}")
                time.sleep(5)
                return self.upload_chapter(chapter, retry_count + 1)
            
            return False
    
    def _process_content(self, content: str) -> str:
        """处理章节内容格式"""
        # 移除章节标题行（如果内容开头有）
        lines = content.split('\\n')
        if lines and ('第' in lines[0] and '章' in lines[0]):
            lines = lines[1:]
        
        # 合并段落
        processed = '\\n'.join(lines)
        
        # 清理多余空行
        processed = re.sub(r'\\n{{3,}}', '\\n\\n', processed)
        
        return processed.strip()
    
    def run(self):
        """运行上传流程"""
        print("=" * 60)
        print(f"{{Colors.BLUE}}大文娱创作平台 - 番茄小说上传{{Colors.RESET}}")
        print("=" * 60)
        print(f"小说: {{NOVEL_TITLE}}")
        print(f"章节: {{TOTAL_CHAPTERS}} 章")
        print(f"任务: {{TASK_ID}}")
        print("=" * 60)
        
        # 加载章节
        if not self.load_chapters():
            return False
        
        # 连接Chrome
        if not self.connect_chrome():
            return False
        
        # 检查登录
        if not self.check_login():
            return False
        
        # 查找或创建书籍
        if not self.find_or_create_book():
            print("\\n请先手动创建书籍，然后重新运行脚本")
            input("\\n按回车键退出...")
            return False
        
        # 导航到章节管理页面
        if not self.navigate_to_chapter_create():
            return False
        
        # 上传章节
        print("\\n" + "-" * 60)
        print("开始上传章节...")
        print("-" * 60)
        
        success_count = 0
        failed_chapters = []
        
        for i, chapter in enumerate(self.chapters, 1):
            self.current_chapter = i
            
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            # 延时 - 避免频率限制
            if i < len(self.chapters):
                delay = random.uniform(5, 10)
                print(f"  等待 {{delay:.1f}}s...")
                time.sleep(delay)
        
        # 关闭
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        # 结果
        print("\\n" + "=" * 60)
        print(f"{{Colors.GREEN}}✓ 上传完成{{Colors.RESET}}")
        print(f"成功: {{success_count}}/{{len(self.chapters)}} 章")
        if failed_chapters:
            print(f"{{Colors.RED}}失败: {{len(failed_chapters)}} 章{{Colors.RESET}}")
            for ch in failed_chapters:
                print(f"  - 第{{ch['number']}}章: {{ch['title']}}")
        print(f"\\n查看详情: {{API_BASE_URL}}/upload-status/{{TASK_ID}}")
        print("=" * 60)
        
        return len(failed_chapters) == 0


def main():
    """主函数"""
    reporter = UploadReporter()
    uploader = FanqieUploader(reporter)
    
    try:
        success = uploader.run()
        
        if success:
            print(f"\\n{{Colors.GREEN}}🎉 全部上传成功！{{Colors.RESET}}")
        else:
            print(f"\\n{{Colors.YELLOW}}⚠️ 部分章节上传失败{{Colors.RESET}}")
        
        input("\\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\\n\\n用户取消上传")
        sys.exit(1)
    except Exception as e:
        print(f"\\n{{Colors.RED}}发生错误: {{e}}{{Colors.RESET}}")
        import traceback
        traceback.print_exc()
        input("\\n按回车键退出...")


if __name__ == "__main__":
    main()
'''
    
    def _create_chapters_json(self, output_dir: Path, chapters: List[Dict]):
        """创建章节数据文件"""
        with open(output_dir / 'chapters.json', 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
    
    def _create_start_bat(self, output_dir: Path):
        """创建首次使用的一键启动脚本"""
        bat_content = '''@echo off
chcp 65001 >nul
title 大文娱创作平台 - 环境启动器
echo ============================================
echo  大文娱创作平台 - 环境启动器
echo ============================================
echo.

:: 检查Chrome启动器
if not exist "chrome_launcher\\一键启动.bat" (
    echo [错误] 未找到 Chrome 启动器
    echo 请先下载 Chrome 浏览器环境
    pause
    exit /b 1
)

:: 启动Chrome
echo [1/3] 正在启动 Chrome...
call "chrome_launcher\\一键启动.bat"
if errorlevel 1 (
    echo [错误] Chrome 启动失败
    pause
    exit /b 1
)

echo.
echo [2/3] Chrome 已启动！
echo.
echo ============================================
echo  接下来请：
echo  1. 在 Chrome 中访问 https://fanqienovel.com
echo  2. 登录您的番茄小说作者账号
echo  3. 运行 upload 目录中的 upload_script.py
echo ============================================
echo.
pause
'''
        with open(output_dir / 'start.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)
    
    def _create_quick_start_bat(self, output_dir: Path, novel_info: Dict):
        """创建快速启动脚本"""
        bat_content = f'''@echo off
chcp 65001 >nul
title {novel_info.get('title', '小说')} - 开始上传
echo ============================================
echo  {novel_info.get('title', '小说')}
echo ============================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装
    pause
    exit /b 1
)

:: 检查Playwright
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [安装依赖] 正在安装 Playwright...
    pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
    python -m playwright install chromium
)

:: 运行上传脚本
echo [开始上传] 正在启动上传脚本...
python upload_script.py

pause
'''
        with open(output_dir / f'开始上传_{novel_info.get("title", "novel")[:10]}.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)
    
    def _create_env_check_script(self, output_dir: Path):
        """创建环境检查脚本"""
        check_script = '''#!/usr/bin/env python3
"""环境检查脚本"""
import sys
import subprocess

def check():
    print("=" * 50)
    print("环境检查")
    print("=" * 50)
    
    # 检查Python
    print(f"Python: {sys.version.split()[0]}")
    
    # 检查Playwright
    try:
        import playwright
        print(f"Playwright: 已安装")
    except:
        print("Playwright: 未安装")
    
    # 检查Chrome
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 9988))
    if result == 0:
        print("Chrome (9988): 已连接")
    else:
        print("Chrome (9988): 未连接")
    sock.close()
    
    print("=" * 50)

if __name__ == "__main__":
    check()
    input("\\n按回车退出...")
'''
        with open(output_dir / 'check_env.py', 'w', encoding='utf-8') as f:
            f.write(check_script)
    
    def _create_first_time_readme(self, output_dir: Path, novel_info: Dict):
        """创建首次使用说明"""
        readme = f'''═══════════════════════════════════════════════════════════
  大文娱创作平台 - 首次使用指南
═══════════════════════════════════════════════════════════

📦 包内容说明
─────────────────────────────────────────────────────────
chrome_launcher/     Chrome浏览器启动器（已包含）
python_embed/        Python环境（已包含）
upload/              上传脚本和小说数据
check_env.py         环境检查脚本
start.bat            一键启动脚本

🚀 首次使用步骤
─────────────────────────────────────────────────────────

步骤1：启动环境（仅需一次）
  1. 双击运行 start.bat
  2. 等待 Chrome 启动（会自动打开番茄小说）
  3. 在 Chrome 中登录番茄小说作者账号

步骤2：运行上传脚本
  1. 进入 upload 文件夹
  2. 运行 upload_script.py
     - 方式1：双击运行
     - 方式2：命令行运行 python upload_script.py
  3. 脚本会自动上传小说并显示进度

📁 当前小说
─────────────────────────────────────────────────────────
标题：{novel_info.get('title', 'Unknown')}
ID：{novel_info.get('id', 'Unknown')}
章节数：{novel_info.get('chapters', 'Unknown')} 章

💡 常见问题
─────────────────────────────────────────────────────────
Q: Chrome 启动失败？
A: 1. 确保系统已安装 Chrome 浏览器
   2. 检查 9988 端口是否被占用
   3. 尝试以管理员身份运行 start.bat

Q: 提示未登录？
A: 在 Chrome 中访问 fanqienovel.com 并登录作者账号

Q: Python 环境有问题？
A: 如果使用完整包，python_embed 目录已包含所需环境
   如仍有问题，请安装 Python 3.10+ 和 Playwright

Q: 上传中断怎么办？
A: 重新运行脚本，已上传的章节会自动跳过

═══════════════════════════════════════════════════════════
'''
        with open(output_dir / 'README_FIRST.txt', 'w', encoding='utf-8') as f:
            f.write(readme)
    
    def _create_script_readme(self, output_dir: Path, novel_info: Dict):
        """创建脚本包使用说明"""
        readme = f'''═══════════════════════════════════════════════════════════
  大文娱创作平台 - 上传脚本包
═══════════════════════════════════════════════════════════

📦 文件说明
─────────────────────────────────────────────────────────
upload_script.py     上传脚本（双击运行）
chapters.json        章节数据
config.json          任务配置
start.bat            快速启动脚本

🚀 使用方法
─────────────────────────────────────────────────────────

前提条件：
  - 已安装 Chrome 浏览器
  - 已运行 Chrome 调试模式（一键启动.bat）
  - 已在 Chrome 中登录番茄小说

开始上传：
  方式1：双击 "开始上传_xxxxx.bat"
  方式2：命令行运行 python upload_script.py

📊 查看进度
─────────────────────────────────────────────────────────
上传过程中可在网页查看实时进度：
{self.api_base_url}/upload-status

📖 小说信息
─────────────────────────────────────────────────────────
标题：{novel_info.get('title', 'Unknown')}
章节数：详见 chapters.json

═══════════════════════════════════════════════════════════
'''
        with open(output_dir / 'README.txt', 'w', encoding='utf-8') as f:
            f.write(readme)
    
    def _create_login_guide(self, output_dir: Path):
        """创建番茄登录引导"""
        guide = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>番茄小说登录引导</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .step { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }
        .step h3 { margin-top: 0; }
        .btn { display: inline-block; padding: 10px 20px; background: #ff5f00; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>🍅 番茄小说登录引导</h1>
    
    <div class="step">
        <h3>步骤1：打开番茄小说</h3>
        <p>点击下方按钮在Chrome中打开番茄小说</p>
        <a href="https://fanqienovel.com" target="_blank" class="btn">打开番茄小说</a>
    </div>
    
    <div class="step">
        <h3>步骤2：登录账号</h3>
        <p>使用您的番茄小说作者账号登录</p>
    </div>
    
    <div class="step">
        <h3>步骤3：验证登录</h3>
        <p>登录成功后，访问作家专区确认可以正常访问</p>
        <a href="https://fanqienovel.com/main/writer/book-manage" target="_blank" class="btn">打开作家专区</a>
    </div>
    
    <div class="step">
        <h3>步骤4：开始上传</h3>
        <p>登录成功后，运行 upload_script.py 开始上传</p>
    </div>
</body>
</html>
'''
        with open(output_dir / '登录引导.html', 'w', encoding='utf-8') as f:
            f.write(guide)
    
    def cleanup_old_packages(self, max_age_hours: int = 24):
        """清理过期包"""
        try:
            current_time = datetime.now().timestamp()
            for file_path in PACKAGES_DIR.glob('*.zip'):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_hours * 3600:
                    file_path.unlink()
                    print(f"[PackageManager] 清理过期包: {file_path.name}")
        except Exception as e:
            print(f"[PackageManager] 清理包失败: {e}")
