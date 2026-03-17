#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱 Chrome 浏览器启动器
用于启动本地 Chrome 浏览器并开启远程调试端口
供番茄上传等功能使用
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
CHROME_DOWNLOAD_URL = "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/1097615/chrome-win.zip"

class ChromeLauncher:
    """Chrome 浏览器启动器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.chrome_dir = self.script_dir / "chrome"
        self.userdata_dir = self.script_dir / "userdata"
        self.config_file = self.script_dir / "config.json"
        
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
        
        if platform == "windows":
            chrome_exe = self.chrome_dir / "chrome.exe"
            # 也尝试 chromium
            if not chrome_exe.exists():
                chrome_exe = self.chrome_dir / "chrome-win" / "chrome.exe"
        elif platform == "macos":
            chrome_exe = self.chrome_dir / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"
        else:
            chrome_exe = self.chrome_dir / "chrome"
            if not chrome_exe.exists():
                chrome_exe = self.chrome_dir / "chromium"
        
        return chrome_exe.exists(), chrome_exe
    
    def check_chrome_running(self) -> bool:
        """检查 Chrome 是否已在运行（通过调试端口）"""
        try:
            url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                return True
        except:
            return False
    
    def download_chrome(self) -> bool:
        """下载 Chrome 绿色版"""
        import zipfile
        
        print("📥 Chrome 浏览器未找到")
        print("   正在下载 Chromium 绿色版（约 150MB）...")
        print(f"   下载地址: {CHROME_DOWNLOAD_URL}")
        
        zip_path = self.script_dir / "chrome-download.zip"
        
        try:
            # 显示下载进度
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                print(f"\r   进度: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)", end="", flush=True)
            
            urllib.request.urlretrieve(CHROME_DOWNLOAD_URL, zip_path, download_progress)
            print("\n✅ 下载完成")
            
            # 解压
            print("📦 正在解压...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.chrome_dir)
            
            # 清理
            zip_path.unlink()
            print("✅ 解压完成")
            return True
            
        except Exception as e:
            print(f"\n❌ 下载失败: {e}")
            print("   请手动下载 Chrome 并放到 chrome/ 目录")
            return False
    
    def start_chrome(self) -> bool:
        """启动 Chrome 浏览器"""
        # 检查是否已运行
        if self.check_chrome_running():
            print("✅ Chrome 已在运行（调试端口已开启）")
            self._show_success_info()
            return True
        
        # 检查 Chrome 是否存在
        exists, chrome_exe = self.get_chrome_executable()
        
        if not exists:
            print("🔍 Chrome 浏览器未找到")
            choice = input("   是否下载 Chromium 绿色版？(Y/n): ").strip().lower()
            if choice in ('', 'y', 'yes'):
                if not self.download_chrome():
                    return False
                exists, chrome_exe = self.get_chrome_executable()
        
        if not exists:
            print("❌ Chrome 启动失败：找不到浏览器")
            print(f"   请将 Chrome 放置在: {self.chrome_dir}")
            return False
        
        # 确保用户数据目录存在
        self.userdata_dir.mkdir(exist_ok=True)
        
        # 构建启动参数
        args = [
            str(chrome_exe),
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={self.userdata_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-translate",
            "--disable-features=TranslateUI",
            "--disable-sync",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            # 窗口大小
            "--window-size=1920,1080",
            # 启动页面
            "https://fanqienovel.com/",
        ]
        
        print()
        print("=" * 50)
        print("🚀 正在启动 Chrome...")
        print("=" * 50)
        print(f"   浏览器: {chrome_exe}")
        print(f"   调试端口: {DEBUG_PORT}")
        print(f"   用户数据: {self.userdata_dir}")
        print()
        
        try:
            # 后台启动 Chrome
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
            print("⏳ 等待 Chrome 启动...")
            for i in range(30):
                if self.check_chrome_running():
                    print()
                    print("✅ Chrome 启动成功！")
                    self._show_success_info()
                    return True
                time.sleep(1)
                print(f"   等待中... ({i+1}/30)", end="\r")
            
            print()
            print("❌ Chrome 启动超时")
            return False
            
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            return False
    
    def _show_success_info(self):
        """显示成功信息"""
        print()
        print("=" * 50)
        print("✨ Chrome 已就绪")
        print("=" * 50)
        print()
        print("📋 使用步骤：")
        print("   1. 在打开的 Chrome 中登录番茄账号")
        print("   2. 进入「作家专区」")
        print("   3. 回到大文娱 Web 界面")
        print("   4. 点击「开始上传」")
        print()
        print(f"🔗 调试端口: http://127.0.0.1:{DEBUG_PORT}")
        print()
        print("⚠️  请勿关闭此窗口，保持 Chrome 运行")
        print()
    
    def run(self):
        """运行启动器"""
        # 设置控制台标题
        if sys.platform == "win32":
            os.system(f"title 大文娱 Chrome 启动器")
        
        print()
        print("╔" + "═" * 48 + "╗")
        print("║" + " " * 12 + "大文娱 Chrome 启动器" + " " * 15 + "║")
        print("╚" + "═" * 48 + "╝")
        print()
        
        # 尝试启动
        if self.start_chrome():
            print()
            input("按回车键关闭此窗口（Chrome 会继续运行）...")
        else:
            print()
            input("启动失败，按回车键退出...")


def main():
    """主入口"""
    launcher = ChromeLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
