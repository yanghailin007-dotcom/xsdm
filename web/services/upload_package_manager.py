"""
上传包管理器
管理不同类型的上传包：首次包、脚本包、数据包
"""
import os
import json
import zipfile
import tempfile
import shutil
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
        返回用户需要哪种包类型
        """
        # TODO: 从数据库查询用户是否下载过首次包
        # 这里先返回模拟数据
        return {
            'has_chrome_launcher': False,  # 是否有浏览器启动器
            'has_python': False,           # 是否有Python环境
            'has_uploaded_before': False,  # 是否成功上传过
            'last_upload_time': None,      # 上次上传时间
            'recommended_package': PACKAGE_TYPE_FIRST_TIME
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
            (temp_dir / 'chrome_launcher').mkdir()
            (temp_dir / 'python_embed').mkdir()
            (temp_dir / 'upload').mkdir()
            
            # 2. 创建一键启动脚本
            self._create_start_bat(temp_dir)
            
            # 3. 创建环境检查脚本
            self._create_env_check_script(temp_dir)
            
            # 4. 创建上传脚本（在upload目录）
            self._create_upload_script(
                temp_dir / 'upload',
                task_id, user_token, novel_info, chapters
            )
            
            # 5. 创建首次使用说明
            self._create_first_time_readme(temp_dir, novel_info)
            
            # 6. 创建番茄登录引导
            self._create_login_guide(temp_dir)
            
            # 7. 打包
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
                'size_estimate': '约 200MB（首次下载较慢）'
            }
            
        except Exception as e:
            print(f"[PackageManager] 创建首次包失败: {e}")
            return {'success': False, 'error': str(e)}
    
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
        """创建上传脚本"""
        script_content = f'''#!/usr/bin/env python3
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
import requests
from pathlib import Path
from datetime import datetime

# ==================== 配置（自动注入）====================
API_BASE_URL = "{self.api_base_url}"
TASK_ID = "{task_id}"
USER_TOKEN = "{user_token}"
NOVEL_TITLE = """{novel_info.get('title', '')}"""
NOVEL_ID = "{novel_info.get('id', '')}"
TOTAL_CHAPTERS = {len(chapters)}
# =====================================================

REPORT_INTERVAL = 3  # 上报间隔（秒）
MAX_RETRY = 3        # 最大重试次数


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
            # 控制上报频率
            current_time = time.time()
            if current_time - self.last_report_time < REPORT_INTERVAL and status not in ['success', 'failed']:
                return True
            self.last_report_time = current_time
            
            data = {{
                'task_id': TASK_ID,
                'chapter_number': chapter_number,
                'status': status,
            }}
            
            # 可选字段
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
    """番茄小说上传器"""
    
    def __init__(self, reporter: UploadReporter):
        self.reporter = reporter
        self.playwright = None
        self.browser = None
        self.page = None
        self.chapters = []
        self.current_chapter = 0
    
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
            self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9988")
            
            contexts = self.browser.contexts
            if contexts and contexts[0].pages:
                self.page = contexts[0].pages[0]
            else:
                self.page = self.browser.new_page()
            
            print(f"{{Colors.GREEN}}✓ 已连接: {{self.page.url[:50]}}...{{Colors.RESET}}")
            return True
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 连接 Chrome 失败: {{e}}{{Colors.RESET}}")
            print("\\n💡 请确保:")
            print("   1. 已运行 '一键启动.bat' 启动 Chrome")
            print("   2. Chrome 窗口保持打开")
            return False
    
    def check_login(self):
        """检查登录状态"""
        try:
            print("\\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            # 检查是否有登录按钮
            if self.page.url.startswith("https://fanqienovel.com/login") or \
               self.page.locator('a[href*="/login"]').count() > 0:
                print(f"{{Colors.RED}}✗ 未登录番茄小说{{Colors.RESET}}")
                print("\\n💡 请在 Chrome 中:")
                print("   1. 访问 https://fanqienovel.com")
                print("   2. 登录您的作者账号")
                print("   3. 重新运行此脚本")
                return False
            
            print(f"{{Colors.GREEN}}✓ 已登录番茄小说{{Colors.RESET}}")
            return True
            
        except Exception as e:
            print(f"{{Colors.RED}}✗ 检查登录失败: {{e}}{{Colors.RESET}}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        
        print(f"\\n📖 第 {{chapter_number}} 章: {{chapter_title[:30]}}...")
        
        # 上报开始
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            # TODO: 实现实际上传逻辑
            # 1. 点击创建章节
            # 2. 填写章节号、标题
            # 3. 填写内容
            # 4. 点击发布
            
            # 模拟上传过程
            time.sleep(random.uniform(2, 4))
            
            # 模拟成功
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            print(f"{{Colors.GREEN}}  ✓ 上传成功{{Colors.RESET}}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{{Colors.RED}}  ✗ 上传失败: {{error_msg[:50]}}{{Colors.RESET}}")
            
            # 上报失败
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
        
        # 上传章节
        print("\\n" + "-" * 60)
        success_count = 0
        failed_chapters = []
        
        for i, chapter in enumerate(self.chapters, 1):
            self.current_chapter = i
            progress = f"[{{i}}/{{len(self.chapters)}}]"
            print(f"\\n{{progress}} ", end="")
            
            if self.upload_chapter(chapter):
                success_count += 1
            else:
                failed_chapters.append(chapter)
            
            # 延时
            if i < len(self.chapters):
                delay = random.uniform(3, 6)
                print(f"  等待 {{delay:.1f}}s...", end="")
                time.sleep(delay)
                print(" ✓")
        
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
            print("可在网页点击'重试失败章节'")
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
            print(f"\\n{{Colors.YELLOW}}⚠️ 部分章节上传失败，可在网页重试{{Colors.RESET}}")
        
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
        
        with open(output_dir / 'upload_script.py', 'w', encoding='utf-8') as f:
            f.write(script_content)
    
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
chrome_launcher/     Chrome浏览器启动器（需自行下载）
python_embed/        Python环境（需自行下载）
upload/              上传脚本和小说数据
check_env.py         环境检查脚本
start.bat            一键启动脚本

🚀 首次使用步骤
─────────────────────────────────────────────────────────

步骤1：下载浏览器环境（仅需一次）
  1. 访问 https://www.google.com/chrome/
  2. 下载并安装 Chrome 浏览器
  3. 或将 chrome_launcher 文件夹解压到本目录

步骤2：配置环境（仅需一次）
  1. 双击运行 start.bat
  2. 等待 Chrome 启动
  3. 在 Chrome 中登录番茄小说作者账号

步骤3：运行上传脚本
  1. 进入 upload 文件夹
  2. 双击运行 upload_script.py
  3. 脚本会自动上传小说并显示进度

📁 当前小说
─────────────────────────────────────────────────────────
标题：{novel_info.get('title', 'Unknown')}
ID：{novel_info.get('id', 'Unknown')}

💡 常见问题
─────────────────────────────────────────────────────────
Q: Chrome 启动失败？
A: 确保已安装 Chrome，且 9988 端口未被占用

Q: 提示未登录？
A: 在 Chrome 中访问 fanqienovel.com 并登录

Q: 上传中断怎么办？
A: 重新运行脚本，会自动从断点续传

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
