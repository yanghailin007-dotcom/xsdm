#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄账户管理模块
单官网账户 + 多番茄账户架构
每个番茄账户对应独立 Chrome 数据目录和端口
"""

import json
import shutil
import subprocess
import socket
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TomatoAccount:
    """番茄账户信息"""
    id: str           # 唯一ID (tomato_001)
    name: str         # 显示名称 (作者张三)
    port: int         # 调试端口 (10001)
    status: str = "stopped"  # stopped/running/error
    created_at: str = ""


def get_app_dir() -> Path:
    """获取应用程序目录（兼容开发和打包环境）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


class TomatoAccountManager:
    """番茄账户管理器"""
    
    PORT_START = 10001
    PORT_END = 10100
    
    def __init__(self, base_dir: str = "browser_data/tomato_accounts", app_dir: Path = None):
        # 支持传入应用目录（兼容打包环境）
        self.app_dir = app_dir or get_app_dir()
        self.base_dir = self.app_dir / base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.base_dir / "accounts.json"
        self.accounts: Dict[str, TomatoAccount] = {}
        
        self._load_accounts()
    
    def _load_accounts(self):
        """加载账户列表"""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding='utf-8'))
                for acc_data in data.get('accounts', []):
                    acc = TomatoAccount(**acc_data)
                    self.accounts[acc.id] = acc
            except Exception as e:
                print(f"加载账户失败: {e}")
    
    def _save_accounts(self):
        """保存账户列表"""
        try:
            data = {
                'accounts': [asdict(acc) for acc in self.accounts.values()]
            }
            self.config_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"保存账户失败: {e}")
    
    def _find_available_port(self) -> int:
        """查找可用端口"""
        used_ports = {acc.port for acc in self.accounts.values()}
        for port in range(self.PORT_START, self.PORT_END):
            if port not in used_ports and not self._is_port_in_use(port):
                return port
        raise RuntimeError("没有可用端口")
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex(('localhost', port)) == 0
        except:
            return False
    
    def add_account(self, name: str) -> Optional[TomatoAccount]:
        """添加新账户"""
        # 生成ID
        idx = len(self.accounts) + 1
        while f"tomato_{idx:03d}" in self.accounts:
            idx += 1
        
        account_id = f"tomato_{idx:03d}"
        
        try:
            port = self._find_available_port()
        except RuntimeError:
            return None
        
        acc = TomatoAccount(
            id=account_id,
            name=name,
            port=port,
            created_at=datetime.now().isoformat()
        )
        
        # 创建数据目录
        data_dir = self.base_dir / account_id
        data_dir.mkdir(exist_ok=True)
        
        self.accounts[account_id] = acc
        self._save_accounts()
        
        return acc
    
    def remove_account(self, account_id: str) -> bool:
        """删除账户"""
        if account_id not in self.accounts:
            return False
        
        acc = self.accounts[account_id]
        
        # 删除数据目录
        data_dir = self.base_dir / account_id
        if data_dir.exists():
            shutil.rmtree(data_dir, ignore_errors=True)
        
        del self.accounts[account_id]
        self._save_accounts()
        
        return True
    
    def rename_account(self, account_id: str, new_name: str) -> bool:
        """重命名账户"""
        if account_id not in self.accounts:
            return False
        
        self.accounts[account_id].name = new_name
        self._save_accounts()
        return True
    
    def get_all_accounts(self) -> List[TomatoAccount]:
        """获取所有账户"""
        return list(self.accounts.values())
    
    def get_account(self, account_id: str) -> Optional[TomatoAccount]:
        """获取指定账户"""
        return self.accounts.get(account_id)
    
    def get_data_dir(self, account_id: str) -> Path:
        """获取账户数据目录"""
        return self.base_dir / account_id


class ChromeLauncher:
    """Chrome 启动器 - 使用 subprocess"""
    
    # Chrome 下载链接 (Chrome for Testing)
    CHROME_URL = "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/win64/chrome-win64.zip"
    
    def __init__(self, app_dir: Path = None):
        self.app_dir = app_dir or get_app_dir()
        self.work_dir = self.app_dir
        self.chrome_path = self._find_chrome()
        self.is_downloading = False
    
    def _find_chrome(self) -> Optional[str]:
        """查找 Chrome"""
        # 检查下载目录
        chrome_exe = self.work_dir / "chrome" / "chrome-win64" / "chrome.exe"
        if chrome_exe.exists():
            return str(chrome_exe)
        
        # 检查系统目录
        system_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for path in system_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def is_available(self) -> bool:
        """Chrome 是否可用"""
        return self.chrome_path is not None
    
    def download_chrome_blocking(self, progress_callback=None):
        """同步下载 Chrome（在主线程中执行，用于后台线程）"""
        import urllib.request
        import zipfile
        
        self.is_downloading = True
        try:
            chrome_dir = self.work_dir / "chrome"
            chrome_dir.mkdir(exist_ok=True)
            zip_path = chrome_dir / "chrome.zip"
            
            # 下载
            if progress_callback:
                progress_callback(10, "开始下载 Chrome...")
            
            def download_progress(block_num, block_size, total_size):
                if total_size > 0 and progress_callback:
                    percent = min(90, int(block_num * block_size / total_size * 80) + 10)
                    progress_callback(percent, f"下载中... {percent}%")
            
            urllib.request.urlretrieve(
                self.CHROME_URL, 
                zip_path,
                reporthook=download_progress
            )
            
            if progress_callback:
                progress_callback(90, "下载完成，正在解压...")
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(chrome_dir)
            
            # 删除zip
            zip_path.unlink(missing_ok=True)
            
            # 更新路径
            self.chrome_path = self._find_chrome()
            
            if progress_callback:
                progress_callback(100, "Chrome 安装完成")
            
            return True, "Chrome 安装成功"
                
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"下载失败: {e}")
            return False, str(e)
        finally:
            self.is_downloading = False
    
    def launch(self, port: int, data_dir: Path, url: str = "https://fanqienovel.com") -> bool:
        """启动 Chrome"""
        if not self.chrome_path:
            return False
        
        try:
            cmd = [
                self.chrome_path,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-sandbox",
                url
            ]
            
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True
            
        except Exception as e:
            print(f"启动 Chrome 失败: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    mgr = TomatoAccountManager()
    
    # 添加测试账户
    acc = mgr.add_account("作者张三")
    if acc:
        print(f"添加账户: {acc.name} (ID: {acc.id}, Port: {acc.port})")
    
    # 列出所有账户
    print("\n所有账户:")
    for a in mgr.get_all_accounts():
        print(f"  - {a.name} ({a.id}): port={a.port}, status={a.status}")
