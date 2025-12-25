#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化浏览器管理器
集成Chrome启动、连接诊断、自动重试等功能
"""

import os
import sys
import time
import subprocess
import requests
import socket
import psutil
from typing import Optional, Tuple, List
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class AutoBrowserManager:
    """自动化浏览器管理器 - 一键解决所有连接问题"""
    
    def __init__(self, debug_port: int = 9988, auto_start_chrome: bool = True):
        self.debug_port = debug_port
        self.auto_start_chrome = auto_start_chrome
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_process = None
        
    def find_chrome_executable(self) -> Optional[str]:
        """查找Chrome可执行文件"""
        possible_paths = [
            # 您项目中的Chrome（优先）
            r"D:\work6.05\Chrome\Chrome\App\chrome.exe",
            
            # 标准安装路径
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            
            # 用户安装路径
            os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result != 0
        except:
            return False
    
    def test_chrome_debug_connection(self, port: int) -> bool:
        """测试Chrome调试连接"""
        try:
            response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def kill_existing_chrome_processes(self) -> bool:
        """关闭现有的Chrome进程"""
        print("🧹 检查并关闭现有Chrome进程...")
        
        chrome_killed = False
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    process_info = proc.info
                    if process_info['name'] and 'chrome' in process_info['name'].lower():
                        cmdline = process_info.get('cmdline', [])
                        
                        # 检查是否是我们项目相关的Chrome（包含调试端口或用户数据目录）
                        is_project_chrome = False
                        if cmdline:
                            cmdline_str = ' '.join(cmdline)
                            if f'--remote-debugging-port={self.debug_port}' in cmdline_str or 'chrome_debug_user_data' in cmdline_str:
                                is_project_chrome = True
                        
                        if is_project_chrome:
                            print(f"  🔍 发现项目Chrome进程 (PID: {process_info['pid']})，正在关闭...")
                            proc.terminate()
                            chrome_killed = True
                            
                            # 等待进程结束
                            try:
                                proc.wait(timeout=5)
                                print(f"  ✓ Chrome进程 {process_info['pid']} 已关闭")
                            except psutil.TimeoutExpired:
                                print(f"  ⚠️ 强制关闭Chrome进程 {process_info['pid']}")
                                proc.kill()
                                proc.wait(timeout=2)
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except ImportError:
            print("⚠️ psutil未安装，跳过进程检查")
            return False
        except Exception as e:
            print(f"❌ 关闭Chrome进程时出错: {e}")
            return False
        
        if chrome_killed:
            print("✓ 已关闭现有的项目Chrome进程")
            # 等待一段时间确保进程完全关闭
            time.sleep(2)
        else:
            print("✓ 未发现需要关闭的项目Chrome进程")
            
        return True

    def start_chrome_with_debug(self) -> bool:
        """启动Chrome调试模式"""
        print("🔍 查找Chrome可执行文件...")
        chrome_path = self.find_chrome_executable()
        
        if not chrome_path:
            print("❌ 未找到Chrome可执行文件")
            print("请安装Chrome或手动指定路径")
            return False
        
        print(f"✓ 找到Chrome: {chrome_path}")
        
        # 首先关闭现有的项目Chrome进程
        if not self.kill_existing_chrome_processes():
            print("⚠️ 关闭现有Chrome进程时出现问题，但继续启动...")
        
        # 检查端口是否已被Chrome占用
        if not self.is_port_available(self.debug_port):
            if self.test_chrome_debug_connection(self.debug_port):
                print("✓ Chrome已在运行，无需重复启动")
                return True
            else:
                print(f"❌ 端口 {self.debug_port} 被其他程序占用")
                return False
        
        # 设置用户数据目录
        user_data_dir = os.path.join(os.getcwd(), "chrome_debug_user_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # 构建启动参数
        args = [
            chrome_path,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={user_data_dir}",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-hang-monitor",
            "--disable-client-side-phishing-detection",
            "--disable-component-extensions-with-background-pages",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--start-maximized",
            "about:blank"
        ]
        
        print(f"🚀 启动Chrome (端口: {self.debug_port})...")
        
        try:
            # 启动Chrome
            self.chrome_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            print(f"✓ Chrome进程已启动 (PID: {self.chrome_process.pid})")
            
            # 等待Chrome启动
            return self.wait_for_chrome_ready()
            
        except Exception as e:
            print(f"❌ 启动Chrome失败: {e}")
            return False
    
    def wait_for_chrome_ready(self, timeout: int = 30) -> bool:
        """等待Chrome启动完成"""
        print(f"⏳ 等待Chrome启动完成...")
        
        for i in range(timeout):
            if self.test_chrome_debug_connection(self.debug_port):
                try:
                    response = requests.get(f"http://127.0.0.1:{self.debug_port}/json/version", timeout=2)
                    if response.status_code == 200:
                        info = response.json()
                        print(f"✓ Chrome已就绪 (版本: {info.get('Browser', 'Unknown')})")
                        return True
                except:
                    pass
            
            if i % 5 == 0 and i > 0:
                print(f"  继续等待... ({i}/{timeout}秒)")
            time.sleep(1)
        
        print("❌ Chrome启动超时")
        return False
    
    def connect_to_browser(self, max_retries: int = 5) -> bool:
        """连接到浏览器"""
        print(f"🔗 连接到浏览器 (端口: {self.debug_port})...")
        
        # 启动Playwright
        if not self.playwright:
            self.playwright = sync_playwright().start()
        
        # 尝试连接
        for attempt in range(max_retries):
            try:
                print(f"  连接尝试 {attempt + 1}/{max_retries}...")
                
                self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.debug_port}")
                
                # 获取或创建上下文和页面
                contexts = self.browser.contexts
                if contexts:
                    self.context = contexts[0]
                    pages = self.context.pages
                    if pages:
                        self.page = pages[0]
                    else:
                        self.page = self.context.new_page()
                else:
                    self.context = self.browser.new_context()
                    self.page = self.context.new_page()
                
                print("✓ 成功连接到浏览器!")
                return True
                
            except Exception as e:
                print(f"  连接失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print("❌ 所有连接尝试都失败了")
                    return False
        
        # 确保函数总是返回值
        return False
    
    def ensure_browser_ready(self) -> bool:
        """确保浏览器准备就绪 - 主入口方法"""
        print("=" * 60)
        print("🤖 自动化浏览器管理器")
        print("=" * 60)
        
        # 步骤1: 检查现有连接
        print("\n📋 步骤1: 检查浏览器状态")
        if self.test_chrome_debug_connection(self.debug_port):
            print("✓ 检测到Chrome已在运行")
        else:
            print("❌ 未检测到运行的Chrome")
            if not self.auto_start_chrome:
                print("⚠️ 自动启动已禁用，请手动启动Chrome")
                return False
            
            # 步骤2: 启动Chrome
            print("\n📋 步骤2: 自动启动Chrome")
            if not self.start_chrome_with_debug():
                print("❌ Chrome启动失败")
                return False
        
        # 步骤3: 连接浏览器
        print("\n📋 步骤3: 建立连接")
        if not self.connect_to_browser():
            print("❌ 连接建立失败")
            return False
        
        # 步骤4: 测试连接
        print("\n📋 步骤4: 验证连接功能")
        if not self.test_connection():
            print("❌ 连接测试失败")
            return False
        
        print("\n🎉 浏览器准备就绪!")
        return True
    
    def test_connection(self) -> bool:
        """测试连接功能 - 简化版本，只测试基本功能"""
        try:
            # 检查页面对象是否可用
            if not self.page:
                print("  ❌ 页面对象不可用")
                return False
            
            # 测试基本页面操作 - 访问简单页面
            print("  📍 测试页面基本功能...")
            self.page.goto("about:blank", timeout=5000)
            
            # 测试JavaScript执行
            print("  📍 测试JavaScript执行...")
            result = self.page.evaluate("() => { return {status: 'ok', ready: true} }")
            
            if result.get('status') == 'ok':
                print("  ✓ 浏览器连接验证通过")
                return True
            else:
                print("  ⚠️ JavaScript执行异常")
                return False
            
        except Exception as e:
            print(f"  ❌ 连接测试失败: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """获取连接信息"""
        return {
            "debug_port": self.debug_port,
            "chrome_running": self.test_chrome_debug_connection(self.debug_port),
            "browser_connected": self.browser is not None,
            "page_ready": self.page is not None,
            "chrome_process_id": self.chrome_process.pid if self.chrome_process else None
        }
    
    def cleanup(self):
        """清理资源"""
        print("🧹 清理资源...")
        
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            if self.chrome_process:
                self.chrome_process.terminate()
        except:
            pass
        
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.chrome_process = None
    
    def __enter__(self):
        """上下文管理器入口"""
        if self.ensure_browser_ready():
            return self
        else:
            raise Exception("浏览器初始化失败")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


# 便捷函数，直接替换原有的connect_to_browser
def auto_connect_to_browser(debug_port: int = 9988, auto_start_chrome: bool = True, max_retries: int = 3):
    """
    自动连接浏览器 - 一键解决方案
    直接替换原有的connect_to_browser函数调用
    
    用法:
    playwright, browser, page, context = auto_connect_to_browser()
    """
    manager = AutoBrowserManager(debug_port, auto_start_chrome)
    
    # 尝试多次连接
    for attempt in range(max_retries):
        try:
            print(f"  尝试自动连接 (第 {attempt + 1} 次)...")
            
            if manager.ensure_browser_ready():
                return manager.playwright, manager.browser, manager.page, manager.context
            else:
                print(f"  第 {attempt + 1} 次自动连接失败")
                if attempt < max_retries - 1:
                    print("  等待 5 秒后重试...")
                    time.sleep(5)
                    # 重置管理器状态
                    manager.cleanup()
                    manager = AutoBrowserManager(debug_port, auto_start_chrome)
                else:
                    print("❌ 所有自动连接尝试都失败")
                    return None, None, None, None
                    
        except Exception as e:
            print(f"  第 {attempt + 1} 次自动连接异常: {e}")
            if attempt < max_retries - 1:
                print("  等待 5 秒后重试...")
                time.sleep(5)
                # 重置管理器状态
                try:
                    manager.cleanup()
                except:
                    pass
                manager = AutoBrowserManager(debug_port, auto_start_chrome)
    
    return None, None, None, None


# 示例用法
if __name__ == "__main__":
    print("测试自动化浏览器管理器...")
    
    # 使用上下文管理器（推荐）
    try:
        with AutoBrowserManager() as manager:
            print("\n🎯 连接信息:")
            info = manager.get_connection_info()
            for key, value in info.items():
                print(f"  {key}: {value}")
            
            print("\n📍 现在可以执行自动化操作了...")
            # 在这里添加您的自动化代码
            if manager.page:
                manager.page.goto("https://fanqienovel.com/")
                print(f"✓ 已导航到: {manager.page.title()}")
            else:
                print("❌ 页面对象不可用")
            
            # 保持连接用于测试
            input("\n按回车键退出...")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("测试完成")