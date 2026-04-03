#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome 浏览器管理器
复用原有的 start_browser.py 逻辑
"""

import subprocess
import os
import sys
import time
import json
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# 配置
DEBUG_PORT = 9988
CHROME_DOWNLOAD_URLS = {
    "windows": "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/win64/chrome-win64.zip",
    "macos": "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/mac-x64/chrome-mac-x64.zip",
    "linux": "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/linux64/chrome-linux64.zip"
}


class ChromeManager:
    """Chrome 浏览器管理器"""
    
    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir or Path(__file__).parent
        self.chrome_dir = self.work_dir / "chrome"
        self.userdata_dir = self.work_dir / "userdata"
        
    def detect_platform(self) -> str:
        """检测操作系统平台"""
        if sys.platform == "win32":
            return "windows"
        elif sys.platform == "darwin":
            return "macos"
        else:
            return "linux"
    
    def get_chrome_executable(self) -> Tuple[bool, Path]:
        """获取 Chrome 可执行文件路径"""
        platform = self.detect_platform()
        possible_paths = []
        
        if platform == "windows":
            possible_paths = [
                self.chrome_dir / "chrome-win64" / "chrome.exe",
                self.chrome_dir / "chrome" / "chrome.exe",
                self.chrome_dir / "chrome.exe",
                # 系统 Chrome
                Path(os.environ.get('LOCALAPPDATA', '')) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            ]
        elif platform == "macos":
            possible_paths = [
                self.chrome_dir / "chrome-mac-x64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing",
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        else:
            possible_paths = [
                self.chrome_dir / "chrome-linux64" / "chrome",
                self.chrome_dir / "chrome",
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/chromium"),
            ]
        
        for chrome_exe in possible_paths:
            if chrome_exe.exists():
                return True, chrome_exe
        
        return False, possible_paths[0] if possible_paths else self.chrome_dir / "chrome"
    
    def check_chrome_running(self) -> bool:
        """检查 Chrome 是否已在运行（通过调试端口）"""
        try:
            url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                return True
        except:
            return False
    
    def download_chrome(self, progress_callback=None, confirm_callback=None) -> bool:
        """下载 Chrome 绿色版
        
        Args:
            progress_callback: 进度回调函数 (percent, message)
            confirm_callback: 确认回调函数 (message) -> bool，返回是否继续
        """
        import zipfile
        
        download_url = CHROME_DOWNLOAD_URLS.get(self.detect_platform(), CHROME_DOWNLOAD_URLS["windows"])
        
        # 首次下载提示
        confirm_msg = (
            "首次使用需要下载 Chrome 浏览器（约 150MB）\n\n"
            "下载完成后即可使用，下次无需重复下载。\n\n"
            "是否立即下载？"
        )
        
        if confirm_callback:
            if not confirm_callback(confirm_msg):
                if progress_callback:
                    progress_callback(0, "用户取消下载 Chrome")
                return False
        else:
            print(confirm_msg)
            choice = input("是否下载? (Y/n): ").strip().lower()
            if choice not in ('', 'y', 'yes'):
                return False
        
        if progress_callback:
            progress_callback(0, "正在下载 Chrome for Testing（约 150MB）...")
        else:
            print("📥 正在下载 Chrome for Testing（约 150MB）...")
        
        zip_path = self.work_dir / "chrome-download.zip"
        
        try:
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                if progress_callback:
                    progress_callback(int(percent), f"下载中... {percent:.1f}%")
            
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            
            urllib.request.urlretrieve(download_url, zip_path, download_progress)
            
            if progress_callback:
                progress_callback(100, "下载完成，正在解压...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.chrome_dir)
            
            zip_path.unlink()
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"下载失败: {e}")
            return False
    
    def start_chrome(self, headless: bool = False, progress_callback=None, confirm_callback=None) -> bool:
        """启动 Chrome 浏览器
        
        Args:
            headless: 是否无头模式
            progress_callback: 进度回调 (percent, message)
            confirm_callback: 确认回调 (message) -> bool
        """
        # 检查是否已运行
        if self.check_chrome_running():
            if progress_callback:
                progress_callback(100, "Chrome 已在运行")
            return True
        
        # 检查 Chrome 是否存在
        exists, chrome_exe = self.get_chrome_executable()
        
        if not exists:
            # 首次下载，需要用户确认
            if not self.download_chrome(progress_callback, confirm_callback):
                return False
            exists, chrome_exe = self.get_chrome_executable()
        
        if not exists:
            if progress_callback:
                progress_callback(0, "Chrome 启动失败：找不到浏览器")
            return False
        
        self.userdata_dir.mkdir(exist_ok=True)
        
        if progress_callback:
            progress_callback(50, "正在启动 Chrome...")
        
        args = [
            str(chrome_exe),
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={self.userdata_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--window-size=1920,1080",
            "https://fanqienovel.com/",
        ]
        
        try:
            if sys.platform == "win32":
                subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # 等待 Chrome 启动
            for i in range(30):
                if self.check_chrome_running():
                    if progress_callback:
                        progress_callback(100, "Chrome 启动成功")
                    return True
                time.sleep(1)
                if progress_callback:
                    progress_callback(50 + int(i/30*50), f"等待 Chrome 启动... ({i+1}/30)")
            
            return False
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"启动失败: {e}")
            return False
    
    def get_debug_port(self) -> int:
        """获取调试端口"""
        return DEBUG_PORT
