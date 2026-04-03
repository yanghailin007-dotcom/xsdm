#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版上传工具 - 验证一次，启动多个浏览器
"""

import json
import time
import random
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class SimpleUploader:
    """简化版上传器"""
    
    DEBUG_PORT_START = 10000
    
    def __init__(self):
        self.browser_instances = {}  # port -> browser info
        self.next_port = self.DEBUG_PORT_START
        
    def start_browser(self, chrome_path: str = None, headless: bool = False) -> dict:
        """启动一个浏览器实例"""
        import subprocess
        import os
        
        port = self.next_port
        self.next_port += 1
        
        # 创建用户数据目录
        data_dir = Path(__file__).parent / f"browser_data_{port}"
        data_dir.mkdir(exist_ok=True)
        
        # 构建 Chrome 启动命令
        if chrome_path and Path(chrome_path).exists():
            exe_path = chrome_path
        else:
            # 查找 Chrome
            exe_path = self._find_chrome()
        
        if not exe_path:
            return {"success": False, "error": "未找到 Chrome"}
        
        cmd = [
            exe_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "https://fanqienovel.com/main/writer/book-manage"
        ]
        
        try:
            process = subprocess.Popen(cmd)
            time.sleep(3)  # 等待启动
            
            self.browser_instances[port] = {
                "port": port,
                "process": process,
                "data_dir": data_dir,
                "started_at": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "port": port,
                "message": f"浏览器已启动 (端口: {port})"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_chrome(self) -> str:
        """查找 Chrome"""
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            Path(__file__).parent / "chrome" / "chrome-win64" / "chrome.exe",
        ]
        for p in paths:
            if Path(p).exists():
                return str(p)
        return None
    
    def stop_browser(self, port: int):
        """停止浏览器"""
        if port in self.browser_instances:
            info = self.browser_instances[port]
            if info["process"]:
                info["process"].terminate()
            del self.browser_instances[port]
    
    def stop_all(self):
        """停止所有浏览器"""
        for port in list(self.browser_instances.keys()):
            self.stop_browser(port)
    
    def get_running_count(self) -> int:
        """获取运行中的浏览器数"""
        return len(self.browser_instances)


class WebsiteAuthSimple:
    """简化的官网认证"""
    
    def __init__(self, base_url: str = "https://novel-ai.online"):
        self.base_url = base_url
        self.session_file = Path(__file__).parent / "session.json"
        self.token = None
        self.username = None
        
    def login(self, username: str, password: str) -> bool:
        """登录官网"""
        import requests
        
        try:
            response = requests.post(
                f"{self.base_url}/login",
                json={"username": username, "password": password},
                timeout=30
            )
            
            data = response.json()
            if data.get("success"):
                self.token = data.get("access_token")
                self.username = username
                self._save_session()
                print(f"✅ 登录成功: {username}")
                return True
            else:
                print(f"❌ 登录失败: {data.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False
    
    def _save_session(self):
        """保存会话"""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "username": self.username,
                    "token": self.token,
                    "saved_at": datetime.now().isoformat()
                }, f)
        except Exception as e:
            print(f"⚠️ 保存会话失败: {e}")
    
    def load_session(self) -> bool:
        """加载会话"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.username = data.get("username")
                    self.token = data.get("token")
                    print(f"✅ 已加载会话: {self.username}")
                    return True
        except Exception as e:
            print(f"⚠️ 加载会话失败: {e}")
        return False
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.token is not None
    
    def logout(self):
        """登出"""
        self.token = None
        self.username = None
        if self.session_file.exists():
            self.session_file.unlink()


if __name__ == "__main__":
    print("简化版上传工具")
