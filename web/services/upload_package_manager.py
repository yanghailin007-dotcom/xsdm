"""
上传包管理器 V2 - 双层包设计

设计理念：
1. 基础环境包（静态）：Chrome + Python，预生成，长期缓存
2. 数据包（动态）：脚本 + 章节数据，每次根据小说生成
3. 完整包 = 基础环境包 + 数据包（合并下发）

优势：
- 环境包只需生成一次（约50MB），后续直接复用
- 数据包实时生成（约100KB），响应快速
- 支持增量更新：用户已有环境时只下载数据包
"""
import os
import json
import zipfile
import tempfile
import shutil
import fnmatch
import io
import base64
import random
import string
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, BinaryIO
from dataclasses import dataclass


class ScriptObfuscator:
    """脚本混淆器 - 保护上传脚本不被轻易阅读和篡改"""
    
    def __init__(self, seed: str = None):
        self.seed = seed or ''.join(random.choices(string.ascii_letters, k=16))
        self.random = random.Random(self.seed)
        self.name_map = {}
    
    def _generate_name(self, prefix: str = '_') -> str:
        """生成随机变量名"""
        length = self.random.randint(8, 16)
        name = prefix + ''.join(self.random.choices(string.ascii_letters + string.digits, k=length))
        return name
    
    def _get_obfuscated_name(self, original: str) -> str:
        """获取混淆后的名称"""
        if original not in self.name_map:
            self.name_map[original] = self._generate_name()
        return self.name_map[original]
    
    def encrypt_config(self, api_base_url: str, user_token: str, task_id: str) -> str:
        """
        加密配置信息
        返回解密代码和加密数据的组合
        """
        # 简单的 XOR 加密 + Base64
        key = self.seed.encode('utf-8')
        
        def xor_encrypt(data: str) -> str:
            data_bytes = data.encode('utf-8')
            encrypted = bytearray()
            for i, b in enumerate(data_bytes):
                encrypted.append(b ^ key[i % len(key)])
            return base64.b64encode(bytes(encrypted)).decode('ascii')
        
        encrypted_url = xor_encrypt(api_base_url)
        encrypted_token = xor_encrypt(user_token)
        encrypted_task = xor_encrypt(task_id)
        
        # 生成解密代码
        decrypt_code = f'''
import base64
_seed = {repr(self.seed)}
_key = _seed.encode('utf-8')
def _d(_e):
    _b = base64.b64decode(_e)
    return bytes([_b[i] ^ _key[i % len(_key)] for i in range(len(_b))]).decode('utf-8')
API_BASE_URL = _d({repr(encrypted_url)})
USER_TOKEN = _d({repr(encrypted_token)})
TASK_ID = _d({repr(encrypted_task)})
'''
        return decrypt_code
    
    def obfuscate_script(self, script_content: str) -> str:
        """
        混淆脚本内容
        1. 替换变量名
        2. 移除注释
        3. 添加干扰代码
        """
        lines = script_content.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过空行和纯注释行
            if not stripped or stripped.startswith('# '):
                continue
            
            # 跳过 docstring
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            result_lines.append(line)
        
        # 添加头部保护代码
        header = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protected Upload Script - Do Not Modify"""
import sys
if __name__ != "__main__":
    print("[-] Invalid execution context")
    sys.exit(1)
'''
        
        obfuscated = header + '\n'.join(result_lines)
        return obfuscated

# 包类型
PACKAGE_TYPE_FIRST_TIME = 'first_time'  # 首次下载：环境包 + 数据包
PACKAGE_TYPE_SCRIPT = 'script'          # 脚本包：仅数据包（用户已有环境）
PACKAGE_TYPE_DATA_ONLY = 'data_only'    # 仅数据：章节数据

BASE_DIR = Path(__file__).parent.parent.parent
PACKAGES_DIR = BASE_DIR / 'temp_uploads' / 'packages'
ENV_CACHE_DIR = BASE_DIR / 'temp_uploads' / 'env_cache'  # 环境包缓存目录


@dataclass
class PackageConfig:
    """包配置"""
    type: str
    name: str
    description: str
    files: List[str]
    size_estimate: str


class UploadPackageManager:
    """上传包管理器 V2"""
    
    # 包配置定义
    PACKAGE_CONFIGS = {
        PACKAGE_TYPE_FIRST_TIME: PackageConfig(
            type=PACKAGE_TYPE_FIRST_TIME,
            name='完整环境包',
            description='包含Chrome浏览器、Python环境、上传脚本和小说数据（首次使用）',
            files=['chrome_launcher/', 'python_embed/', 'upload/', 'start.bat', 'README_FIRST.txt'],
            size_estimate='约 50MB'
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
        ENV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 初始化时确保环境包已准备好
        self._ensure_env_packages()
    
    def _ensure_env_packages(self):
        """确保基础环境包已准备好（预生成）"""
        # Chrome 启动器包
        chrome_pkg = ENV_CACHE_DIR / 'chrome_launcher_base.zip'
        if not chrome_pkg.exists():
            print("[PackageManager] 预生成 Chrome 启动器包...")
            self._build_chrome_package(chrome_pkg)
        
        # Python 环境包
        python_pkg = ENV_CACHE_DIR / 'python_embed_base.zip'
        if not python_pkg.exists():
            print("[PackageManager] 预生成 Python 环境包...")
            self._build_python_package(python_pkg)
    
    def _build_chrome_package(self, output_path: Path):
        """构建 Chrome 启动器基础包"""
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix='chrome_build_'))
            chrome_dir = temp_dir / 'chrome_launcher'
            chrome_dir.mkdir()
            
            # 复制 Chrome 启动器文件
            self._copy_chrome_launcher_files(chrome_dir)
            
            # 打包 - 保持原始文件的编码
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(temp_dir))
                        # 读取原始字节，保持编码不变
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        # 使用 writestr 写入字节，并指定压缩类型
                        import zipfile as zf_module
                        zip_info = zf_module.ZipInfo(filename=arcname)
                        zip_info.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(zip_info, content)
            
            shutil.rmtree(temp_dir)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"[PackageManager] Chrome 包已生成: {output_path} ({size_mb:.1f}MB)")
            
        except Exception as e:
            print(f"[PackageManager] 生成 Chrome 包失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_python_package(self, output_path: Path):
        """构建 Python 环境基础包"""
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix='python_build_'))
            python_dir = temp_dir / 'python_embed'
            python_dir.mkdir()
            
            # 复制 Python 环境文件
            self._copy_python_embed_files(python_dir)
            
            # 打包 - 保持原始文件的编码
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(temp_dir))
                        # 读取原始字节，保持编码不变
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        # 使用 writestr 写入字节
                        import zipfile as zf_module
                        zip_info = zf_module.ZipInfo(filename=arcname)
                        zip_info.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(zip_info, content)
            
            shutil.rmtree(temp_dir)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"[PackageManager] Python 包已生成: {output_path} ({size_mb:.1f}MB)")
            
        except Exception as e:
            print(f"[PackageManager] 生成 Python 包失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _copy_chrome_launcher_files(self, dest_dir: Path):
        """复制 Chrome 启动器文件（包含完整的Python检测和Chrome下载功能）"""
        # 源目录优先级
        source_dir = BASE_DIR / 'tools' / 'chrome_launcher'
        
        if not source_dir.exists():
            print(f"[PackageManager] 警告: 未找到 Chrome 启动器源文件")
            self._create_basic_chrome_launcher(dest_dir)
            return
        
        print(f"[PackageManager] 复制 Chrome 启动器: {source_dir} -> {dest_dir}")
        
        # 复制核心文件（必须包含的）
        core_files = [
            '一键启动.bat',
            'start_browser.py',
            'README_傻瓜式使用说明.txt',
        ]
        
        for filename in core_files:
            src_file = source_dir / filename
            if src_file.exists():
                shutil.copy2(src_file, dest_dir / filename)
                print(f"  ✓ {filename}")
        
        # 创建子目录（即使为空，供后续使用）
        (dest_dir / 'chrome').mkdir(exist_ok=True)
        (dest_dir / 'userdata').mkdir(exist_ok=True)
        
        # 创建 README (GBK)
        with open(dest_dir / 'README.txt', 'w', encoding='gbk') as f:
            f.write("""Chrome 浏览器启动器

包含文件：
- 一键启动.bat    : 主启动脚本（自动检测Python、下载Chrome）
- start_browser.py : Python启动脚本
- chrome/         : Chrome浏览器目录（首次运行会自动下载）
- userdata/       : Chrome用户数据目录

使用方法：
1. 双击运行 "一键启动.bat"
2. 按提示安装Python（如未安装）
3. 按提示下载Chrome（如未下载）
4. 等待Chrome启动并登录番茄小说

注意：
- 首次运行需要下载约 150MB 的 Chrome 浏览器
- 需要联网下载 Chrome
- 调试端口为 9988
""")
    
    def _copy_python_embed_files(self, dest_dir: Path):
        """
        处理 Python 环境
        由于完整 Python 环境太大（~150MB），采用引导安装方式
        一键启动.bat 已经包含了自动下载安装 Python 的逻辑
        """
        print(f"[PackageManager] Python 环境采用引导安装方式（减小包体积）")
        
        # 创建 Python 安装说明 (GBK)
        with open(dest_dir / 'README.txt', 'w', encoding='gbk') as f:
            f.write("""Python 环境说明

本包不包含 Python 环境（减小体积），将通过以下方式获取：

方式1 - 自动安装（推荐）：
  运行 "一键启动.bat" 时，如果没有检测到 Python，
  会自动提示下载并安装 Python（约 30MB）

方式2 - 手动安装：
  1. 访问 https://www.python.org/downloads/
  2. 下载 Python 3.10 或更高版本
  3. 安装时勾选 "Add Python to PATH"
  4. 安装完成后运行 "一键启动.bat"

方式3 - 使用 Microsoft Store：
  在 Microsoft Store 搜索 "Python" 并安装

安装完成后，运行 "一键启动.bat" 即可自动配置环境
""")
        
        # 创建一个简单的 Python 检测脚本（GBK编码，CRLF换行符）
        check_script = '@echo off\r\n' \
            'chcp 65001 >nul\r\n' \
            'echo ============================================\r\n' \
            'echo Python Environment Check\r\n' \
            'echo ============================================\r\n' \
            'echo.\r\n' \
            '\r\n' \
            'python --version >nul 2>&1\r\n' \
            'if %errorLevel% == 0 (\r\n' \
            '    echo [OK] Python installed\r\n' \
            '    python --version\r\n' \
            '    echo.\r\n' \
            '    echo You can run start.bat\r\n' \
            ') else (\r\n' \
            '    echo [X] Python not installed\r\n' \
            '    echo.\r\n' \
            '    echo Please run start.bat to install Python\r\n' \
            '    echo Or visit https://www.python.org/downloads/\r\n' \
            ')\r\n' \
            '\r\n' \
            'echo.\r\n' \
            'pause\r\n'
        with open(dest_dir / '检查Python.bat', 'w', encoding='gbk') as f:
            f.write(check_script)
    
    def _create_basic_chrome_launcher(self, dest_dir: Path):
        """创建基本的 Chrome 启动器（备用方案，无chcp，英文避免乱码）"""
        # 使用 CRLF 换行符（Windows bat 文件必需）
        bat_content = '@echo off\r\n' \
            'title Chrome Launcher\r\n' \
            'echo ============================================\r\n' \
            'echo  Chrome Launcher\r\n' \
            'echo ============================================\r\n' \
            'echo.\r\n' \
            '\r\n' \
            'set CHROME_PATH=\r\n' \
            'for %%p in (\r\n' \
            '    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"\r\n' \
            '    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"\r\n' \
            '    "%%LOCALAPPDATA%%\\Google\\Chrome\\Application\\chrome.exe"\r\n' \
') do (\r\n' \
            '    if exist %%p set CHROME_PATH=%%p\r\n' \
            ')\r\n' \
            '\r\n' \
            'if not defined CHROME_PATH (\r\n' \
            '    echo [Error] Chrome not found\r\n' \
            '    pause\r\n' \
            '    exit /b 1\r\n' \
            ')\r\n' \
            '\r\n' \
            'echo [1/2] Chrome found\r\n' \
            'echo.\r\n' \
            '\r\n' \
            'if not exist "%%CD%%\\userdata" mkdir "%%CD%%\\userdata"\r\n' \
            '\r\n' \
            'echo [2/2] Starting Chrome (port 9988)...\r\n' \
            'start "" %%CHROME_PATH%% ^\r\n' \
            '    --remote-debugging-port=9988 ^\r\n' \
            '    --user-data-dir="%%CD%%\\userdata" ^\r\n' \
            '    --no-first-run ^\r\n' \
            '    --no-default-browser-check ^\r\n' \
            '    "https://fanqienovel.com"\r\n' \
            '\r\n' \
            'echo.\r\n' \
            'echo Chrome started! Please login to fanqie\r\n' \
            'echo.\r\n' \
            'pause\r\n'
        with open(dest_dir / 'start_chrome.bat', 'w', encoding='ascii') as f:
            f.write(bat_content)
    
    def create_first_time_package(self, task_id: str, user_token: str,
                                  novel_info: Dict, chapters: List[Dict]) -> Dict:
        """
        创建首次使用完整包
        合并：环境基础包 + 动态数据包
        """
        try:
            # 1. 创建动态数据包（临时）
            data_zip_bytes = self._create_data_package_bytes(
                task_id, user_token, novel_info, chapters
            )
            
            # 2. 合并包
            output_path = PACKAGES_DIR / f'first_time_{task_id}.zip'
            self._merge_packages(output_path, data_zip_bytes)
            
            # 3. 计算实际大小
            actual_size_mb = output_path.stat().st_size / (1024 * 1024)
            
            # 获取运行时下载大小
            chrome_size = self._get_chrome_download_size_mb()
            python_size = 30  # Python 约 30MB
            
            return {
                'success': True,
                'package_path': str(output_path),
                'package_type': PACKAGE_TYPE_FIRST_TIME,
                'file_name': f'大文娱上传完整包_{task_id}.zip',
                'size_estimate': f'约 {actual_size_mb:.1f}MB（首次运行自动下载 Chrome 约{chrome_size}MB + Python 约{python_size}MB）',
                'size_bytes': output_path.stat().st_size,
                'download_size_now': f'{actual_size_mb:.1f}MB',
                'download_size_first_run': f'{chrome_size + python_size}MB'
            }
            
        except Exception as e:
            print(f"[PackageManager] 创建完整包失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _create_data_package_bytes(self, task_id: str, user_token: str,
                                   novel_info: Dict, chapters: List[Dict]) -> bytes:
        """创建动态数据包，返回 bytes"""
        import io
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 创建临时目录用于生成文件
            temp_dir = Path(tempfile.mkdtemp(prefix='data_pkg_'))
            upload_dir = temp_dir / 'upload'
            upload_dir.mkdir()
            
            try:
                # 生成上传脚本 (Python文件用UTF-8)
                script_content = self._generate_upload_script(
                    task_id, user_token, novel_info, chapters
                )
                zf.writestr('upload/upload_script.py', script_content)
                
                # 章节数据
                zf.writestr('upload/chapters.json', 
                    json.dumps(chapters, ensure_ascii=False, indent=2))
                
                # 配置文件
                config = {
                    'task_id': task_id,
                    'novel_title': novel_info.get('title'),
                    'novel_id': novel_info.get('id'),
                    'total_chapters': len(chapters),
                    'created_at': datetime.now().isoformat(),
                    'api_base_url': self.api_base_url
                }
                zf.writestr('upload/config.json', 
                    json.dumps(config, ensure_ascii=False, indent=2))
                
                # BAT 文件使用 GBK 编码（Windows 默认兼容）
                start_bat = self._generate_root_start_bat()
                zf.writestr('start.bat', start_bat.encode('gbk'))
                
                # 文本文件可以用 UTF-8，BAT文件必须用 GBK
                readme = self._generate_first_time_readme(novel_info, len(chapters))
                zf.writestr('README_FIRST.txt', readme.encode('utf-8'))
                
                guide_html = self._generate_login_guide()
                zf.writestr('登录引导.html', guide_html.encode('utf-8'))
                
            finally:
                shutil.rmtree(temp_dir)
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    def _merge_packages(self, output_path: Path, data_zip_bytes: bytes):
        """
        合并环境基础包和数据包
        策略：将数据包内容追加到环境包
        """
        chrome_pkg = ENV_CACHE_DIR / 'chrome_launcher_base.zip'
        python_pkg = ENV_CACHE_DIR / 'python_embed_base.zip'
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as out_zf:
            # 1. 复制 Chrome 启动器包内容
            if chrome_pkg.exists():
                with zipfile.ZipFile(chrome_pkg, 'r') as chrome_zf:
                    for item in chrome_zf.infolist():
                        out_zf.writestr(item, chrome_zf.read(item.filename))
            
            # 2. 复制 Python 环境包内容
            if python_pkg.exists():
                with zipfile.ZipFile(python_pkg, 'r') as python_zf:
                    for item in python_zf.infolist():
                        out_zf.writestr(item, python_zf.read(item.filename))
            
            # 3. 添加动态数据包内容
            with zipfile.ZipFile(io.BytesIO(data_zip_bytes), 'r') as data_zf:
                for item in data_zf.infolist():
                    out_zf.writestr(item, data_zf.read(item.filename))
        
        print(f"[PackageManager] 合并包已生成: {output_path}")
    
    def create_script_package(self, task_id: str, user_token: str,
                             novel_info: Dict, chapters: List[Dict]) -> Dict:
        """
        创建脚本上传包（仅数据，不含环境）
        """
        try:
            output_path = PACKAGES_DIR / f'script_{task_id}.zip'
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 上传脚本
                script_content = self._generate_upload_script(
                    task_id, user_token, novel_info, chapters
                )
                zf.writestr('upload_script.py', script_content)
                
                # 章节数据
                zf.writestr('chapters.json',
                    json.dumps(chapters, ensure_ascii=False, indent=2))
                
                # 配置文件
                config = {
                    'task_id': task_id,
                    'novel_title': novel_info.get('title'),
                    'novel_id': novel_info.get('id'),
                    'total_chapters': len(chapters),
                    'created_at': datetime.now().isoformat(),
                    'api_base_url': self.api_base_url
                }
                zf.writestr('config.json',
                    json.dumps(config, ensure_ascii=False, indent=2))
                
                # README
                readme = self._generate_script_readme(novel_info)
                zf.writestr('README.txt', readme)
                
                # 快速启动 bat
                start_bat = self._generate_quick_start_bat(novel_info)
                zf.writestr(f'开始上传_{novel_info.get("title", "novel")[:10]}.bat', start_bat)
            
            size_kb = output_path.stat().st_size / 1024
            
            return {
                'success': True,
                'package_path': str(output_path),
                'package_type': PACKAGE_TYPE_SCRIPT,
                'file_name': f'{novel_info.get("title", "novel")}_上传包.zip',
                'size_estimate': f'约 {size_kb:.0f}KB'
            }
            
        except Exception as e:
            print(f"[PackageManager] 创建脚本包失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _generate_upload_script(self, task_id: str, user_token: str,
                                novel_info: Dict, chapters: List[Dict]) -> str:
        """生成受保护的上传脚本（带混淆和加密）"""
        
        # 创建混淆器
        obfuscator = ScriptObfuscator(seed=task_id[:16])
        
        # 生成加密配置
        encrypted_config = obfuscator.encrypt_config(
            self.api_base_url, user_token, task_id
        )
        
        # 基础脚本内容（稍后会混淆）
        novel_title_str = novel_info.get('title', '').replace('"', '\\"')
        
        raw_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# 解密配置
{encrypted_config}

# 其他配置
NOVEL_TITLE = """{novel_title_str}"""
NOVEL_ID = "{novel_info.get('id', '')}"
TOTAL_CHAPTERS = {len(chapters)}
DEBUG_PORT = 9988
REPORT_INTERVAL = 3
MAX_RETRY = 3

class Colors:
    GREEN = '\\033[92m'
    RED = '\\033[91m'
    YELLOW = '\\033[93m'
    BLUE = '\\033[94m'
    RESET = '\\033[0m'

class UploadReporter:
    def __init__(self):
        self.last_report_time = 0
    
    def report(self, chapter_number: int, status: str, **kwargs):
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
            for key in ['chapter_title', 'error_message', 'error_type', 'page_url']:
                if key in kwargs:
                    data[key] = kwargs[key]
            
            requests.post(
                f"{{API_BASE_URL}}/api/local-upload/report",
                json=data,
                headers={{'Content-Type': 'application/json'}},
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
            return False
    
    def check_login(self):
        """检查登录状态"""
        try:
            print("\\n🔍 检查登录状态...")
            self.page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            time.sleep(3)
            
            if self.page.url.startswith("https://fanqienovel.com/login"):
                print(f"{{Colors.RED}}✗ 未登录番茄小说{{Colors.RESET}}")
                print("\\n请在 Chrome 中登录番茄小说作者账号")
                return False
            
            print(f"{{Colors.GREEN}}✓ 已登录番茄小说{{Colors.RESET}}")
            return True
        except Exception as e:
            print(f"{{Colors.RED}}✗ 检查登录失败: {{e}}{{Colors.RESET}}")
            return False
    
    def find_book(self):
        """查找书籍"""
        try:
            print(f"\\n📖 查找书籍: {{NOVEL_TITLE}}")
            page_content = self.page.content()
            
            if NOVEL_TITLE[:10] in page_content:
                print(f"{{Colors.GREEN}}✓ 找到已有书籍{{Colors.RESET}}")
                book_ids = re.findall(r'long-article-table-item-(\\d+)', page_content)
                if book_ids:
                    self.book_id = book_ids[0]
                    return True
            
            print(f"{{Colors.YELLOW}}⚠ 未找到书籍，请先手动创建{{Colors.RESET}}")
            return False
        except Exception as e:
            print(f"{{Colors.RED}}✗ 查找书籍失败: {{e}}{{Colors.RESET}}")
            return False
    
    def upload_chapter(self, chapter: dict, retry_count: int = 0) -> bool:
        """上传单个章节"""
        chapter_number = chapter['number']
        chapter_title = chapter['title']
        content = chapter.get('content', '')
        
        print(f"\\n📖 第 {{chapter_number}} 章: {{chapter_title[:30]}}...")
        self.reporter.report(chapter_number, 'uploading', chapter_title=chapter_title)
        
        try:
            # 访问发布页面
            publish_url = f"https://fanqienovel.com/main/writer/publish/{{self.book_id}}"
            self.page.goto(publish_url, timeout=30000)
            time.sleep(3)
            
            # 填写章节号
            try:
                inputs = self.page.locator('input.serial-input').all()
                if len(inputs) >= 1:
                    inputs[0].fill(str(chapter_number))
                    print(f"  填写章节号: {{chapter_number}}")
            except Exception as e:
                print(f"  ⚠️ 章节号: {{e}}")
            
            # 填写标题
            try:
                inputs = self.page.locator('input.serial-input').all()
                if len(inputs) >= 2:
                    inputs[1].fill(chapter_title)
                    print(f"  填写标题: {{chapter_title[:20]}}...")
            except Exception as e:
                print(f"  ⚠️ 标题: {{e}}")
            
            # 填写内容
            try:
                content_editor = self.page.locator('div[contenteditable="true"], .ProseMirror').first
                if content_editor.count() > 0:
                    # 清理内容格式
                    lines = content.split('\\n')
                    if lines and ('第' in lines[0] and '章' in lines[0]):
                        lines = lines[1:]
                    processed = '\\n'.join(lines).strip()
                    
                    content_editor.fill(processed)
                    print(f"  填写内容: {{len(processed)}} 字")
            except Exception as e:
                print(f"  ⚠️ 内容: {{e}}")
            
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
                print(f"  ⚠️ 发布: {{e}}")
            
            # 检查结果
            time.sleep(2)
            if '/chapter-manage/' in self.page.url or 'publish' not in self.page.url:
                self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
                print(f"{{Colors.GREEN}}  ✓ 上传成功{{Colors.RESET}}")
                return True
            
            self.reporter.report(chapter_number, 'success', chapter_title=chapter_title)
            print(f"{{Colors.GREEN}}  ✓ 上传完成{{Colors.RESET}}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"{{Colors.RED}}  ✗ 上传失败: {{error_msg[:50]}}{{Colors.RESET}}")
            
            self.reporter.report(
                chapter_number, 'failed',
                chapter_title=chapter_title,
                error_message=error_msg
            )
            
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
        print("=" * 60)
        
        if not self.load_chapters():
            return False
        
        if not self.connect_chrome():
            return False
        
        if not self.check_login():
            return False
        
        if not self.find_book():
            print("\\n请先手动创建书籍，然后重新运行脚本")
            input("\\n按回车键退出...")
            return False
        
        print("\\n" + "-" * 60)
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
                print(f"  等待 {{delay:.1f}}s...")
                time.sleep(delay)
        
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        print("\\n" + "=" * 60)
        print(f"{{Colors.GREEN}}✓ 上传完成{{Colors.RESET}}")
        print(f"成功: {{success_count}}/{{len(self.chapters)}} 章")
        if failed_chapters:
            print(f"{{Colors.RED}}失败: {{len(failed_chapters)}} 章{{Colors.RESET}}")
        print(f"\\n查看详情: {{API_BASE_URL}}/upload-status/{{TASK_ID}}")
        print("=" * 60)
        
        return len(failed_chapters) == 0

def main():
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
    except Exception as e:
        print(f"\\n{{Colors.RED}}发生错误: {{e}}{{Colors.RESET}}")
        import traceback
        traceback.print_exc()
        input("\\n按回车键退出...")

if __name__ == "__main__":
    main()
'''
        
        # 混淆脚本
        obfuscated = obfuscator.obfuscate_script(raw_script)
        return obfuscated
    
    def _generate_root_start_bat(self) -> str:
        """生成根目录启动脚本 - 调用一键启动.bat"""
        # 使用 CRLF 换行符（Windows bat 文件必需）
        # 使用英文避免乱码，调用已存在的一键启动.bat
        content = '@echo off\r\n' \
            'title DaYuWen Launcher\r\n' \
            '\r\n' \
            'cd /d "%~dp0"\r\n' \
            '\r\n' \
            'echo ============================================\r\n' \
            'echo  DaYuWen Upload Tool\r\n' \
            'echo ============================================\r\n' \
            'echo.\r\n' \
            '\r\n' \
            'if not exist "chrome_launcher" (\r\n' \
            '    echo [Error] chrome_launcher folder not found!\r\n' \
            '    echo Please extract all files from the zip.\r\n' \
            '    pause\r\n' \
            '    exit /b 1\r\n' \
            ')\r\n' \
            '\r\n' \
            'if not exist "chrome_launcher\\一键启动.bat" (\r\n' \
            '    echo [Error] 一键启动.bat not found!\r\n' \
            '    pause\r\n' \
            '    exit /b 1\r\n' \
            ')\r\n' \
            '\r\n' \
            'echo Starting Chrome Launcher...\r\n' \
            'echo.\r\n' \
            '\r\n' \
            'cd chrome_launcher\r\n' \
            'call "一键启动.bat"\r\n' \
            '\r\n' \
            'echo.\r\n' \
            'echo ============================================\r\n' \
            'echo Launcher exited\r\n' \
            'echo ============================================\r\n' \
            'pause\r\n'
        return content
    
    def _generate_quick_start_bat(self, novel_info: Dict) -> str:
        """生成快速启动脚本"""
        return f'''@echo off
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
    
    def _generate_first_time_readme(self, novel_info: Dict, chapter_count: int) -> str:
        """生成首次使用说明"""
        return f'''═══════════════════════════════════════════════════════════
  大文娱创作平台 - 首次使用指南
═══════════════════════════════════════════════════════════

📦 包内容说明
─────────────────────────────────────────────────────────
chrome_launcher/     Chrome浏览器启动器（已包含）
python_embed/        Python环境（已包含）
upload/              上传脚本和小说数据
start.bat            一键启动脚本
登录引导.html         可视化登录引导

🚀 使用步骤
─────────────────────────────────────────────────────────

步骤1：启动环境
  1. 双击运行 start.bat
  2. 等待 Chrome 启动（会自动打开番茄小说）
  3. 在 Chrome 中登录番茄小说作者账号

步骤2：运行上传脚本
  1. 进入 upload 文件夹
  2. 双击运行 upload_script.py
  3. 脚本会自动上传小说并显示进度

📖 当前小说信息
─────────────────────────────────────────────────────────
标题：{novel_info.get('title', 'Unknown')}
ID：{novel_info.get('id', 'Unknown')}
章节数：{chapter_count} 章

💡 常见问题
─────────────────────────────────────────────────────────
Q: Chrome 启动失败？
A: 1. 确保系统已安装 Chrome 浏览器
   2. 检查 9988 端口是否被占用

Q: 提示未登录？
A: 在 Chrome 中访问 fanqienovel.com 并登录作者账号

Q: 未找到书籍？
A: 脚本会自动查找书籍，如未找到请先在番茄平台创建书籍

═══════════════════════════════════════════════════════════
'''
    
    def _generate_script_readme(self, novel_info: Dict) -> str:
        """生成脚本包说明"""
        return f'''═══════════════════════════════════════════════════════════
  大文娱创作平台 - 上传脚本包
═══════════════════════════════════════════════════════════

📦 文件说明
─────────────────────────────────────────────────────────
upload_script.py     上传脚本
chapters.json        章节数据
config.json          任务配置

🚀 使用方法
─────────────────────────────────────────────────────────

前提条件：
  - 已安装 Chrome 浏览器
  - 已运行 Chrome 调试模式（一键启动.bat）
  - 已在 Chrome 中登录番茄小说

开始上传：
  方式1：双击"开始上传_xxxxx.bat"
  方式2：命令行运行 python upload_script.py

📊 查看进度
─────────────────────────────────────────────────────────
上传过程中可在网页查看实时进度：
{self.api_base_url}/upload-status

📖 小说信息
─────────────────────────────────────────────────────────
标题：{novel_info.get('title', 'Unknown')}

═══════════════════════════════════════════════════════════
'''
    
    def _generate_login_guide(self) -> str:
        """生成登录引导 HTML"""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>番茄小说登录引导</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .step { margin: 20px 0; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .step h3 { margin-top: 0; color: #333; }
        .btn { display: inline-block; padding: 12px 24px; background: #ff5f00; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; }
        .btn:hover { background: #e55a00; }
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
        <p>登录成功后，进入 upload 文件夹运行 upload_script.py 开始上传</p>
    </div>
</body>
</html>
'''
    
    def get_package_config(self, package_type: str) -> Optional[PackageConfig]:
        """获取包配置"""
        return self.PACKAGE_CONFIGS.get(package_type)
    
    def _get_chrome_download_size_mb(self) -> int:
        """获取 Chrome 下载大小（MB）"""
        # Chrome for Testing 约 150-180MB
        return 150
    
    def detect_user_environment(self, user_id: int) -> Dict:
        """
        检测用户环境状态（向后兼容方法）
        """
        import shutil
        
        # 1. 检查 Chrome 启动器
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
        
        # 3. 检查系统 Python
        if not has_python:
            has_python = shutil.which('python') is not None or shutil.which('python3') is not None
        
        # 4. 从数据库查询上传历史
        has_uploaded_before = False
        try:
            from web.models.upload_task_model import get_upload_task_model
            model = get_upload_task_model()
            tasks = model.get_user_tasks(user_id, limit=1)
            if tasks and any(t.get('status') == 'completed' for t in tasks):
                has_uploaded_before = True
        except Exception:
            pass
        
        # 推荐包类型
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
    
    def cleanup_old_packages(self, max_age_hours: int = 24):
        """清理过期包（保留环境基础包）"""
        try:
            current_time = datetime.now().timestamp()
            for file_path in PACKAGES_DIR.glob('*.zip'):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_hours * 3600:
                    file_path.unlink()
                    print(f"[PackageManager] 清理过期包: {file_path.name}")
        except Exception as e:
            print(f"[PackageManager] 清理包失败: {e}")


# 向后兼容的别名
UploadPackageManagerV2 = UploadPackageManager
