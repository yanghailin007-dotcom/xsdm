"""
多账号管理系统
支持同时管理多个番茄小说账号，每个账号独立浏览器实例
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Account:
    """账号信息"""
    id: str
    name: str  # 账号名称（如：主账号、小号1）
    platform: str  # 平台：fanqie（番茄）、qidian（起点）等
    username: str = ""  # 登录用户名/手机号
    is_logged_in: bool = False
    last_used: str = ""
    created_at: str = ""
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class AccountManager:
    """
    多账号管理器
    - 每个账号独立的数据目录
    - 支持同时运行多个浏览器实例
    - 账号切换不掉线
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent / "accounts"
        self.base_dir.mkdir(exist_ok=True)
        
        self.accounts_file = self.base_dir / "accounts.json"
        self.accounts: Dict[str, Account] = {}
        self.active_accounts: Dict[str, any] = {}  # 正在运行的浏览器实例
        
        self._load_accounts()
    
    def _load_accounts(self):
        """加载账号列表"""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for acc_id, acc_data in data.items():
                        self.accounts[acc_id] = Account.from_dict(acc_data)
            except Exception as e:
                print(f"加载账号列表失败: {e}")
    
    def _save_accounts(self):
        """保存账号列表"""
        try:
            data = {acc_id: acc.to_dict() for acc_id, acc in self.accounts.items()}
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存账号列表失败: {e}")
    
    def create_account(self, name: str, platform: str = "fanqie") -> Account:
        """
        创建新账号
        
        Args:
            name: 账号名称（如：主账号、小号1）
            platform: 平台类型
            
        Returns:
            Account 对象
        """
        import uuid
        account_id = str(uuid.uuid4())[:8]
        
        # 创建账号数据目录
        account_dir = self.base_dir / account_id
        account_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        (account_dir / "chrome_data").mkdir(exist_ok=True)  # Chrome 用户数据
        (account_dir / "cookies").mkdir(exist_ok=True)      # Cookie 备份
        (account_dir / "downloads").mkdir(exist_ok=True)    # 下载文件
        
        account = Account(
            id=account_id,
            name=name,
            platform=platform,
            created_at=datetime.now().isoformat()
        )
        
        self.accounts[account_id] = account
        self._save_accounts()
        
        print(f"✅ 创建账号成功: {name} ({account_id})")
        return account
    
    def delete_account(self, account_id: str) -> bool:
        """删除账号"""
        if account_id not in self.accounts:
            return False
        
        # 先停止该账号的浏览器
        self.stop_browser(account_id)
        
        # 删除数据目录
        account_dir = self.base_dir / account_id
        if account_dir.exists():
            shutil.rmtree(account_dir)
        
        del self.accounts[account_id]
        self._save_accounts()
        
        print(f"✅ 删除账号成功: {account_id}")
        return True
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账号信息"""
        return self.accounts.get(account_id)
    
    def list_accounts(self, platform: str = None) -> List[Account]:
        """
        列出所有账号
        
        Args:
            platform: 筛选指定平台，None 表示全部
        """
        accounts = list(self.accounts.values())
        if platform:
            accounts = [acc for acc in accounts if acc.platform == platform]
        return accounts
    
    def get_account_data_dir(self, account_id: str) -> Path:
        """获取账号的 Chrome 数据目录"""
        return self.base_dir / account_id / "chrome_data"
    
    def launch_browser(self, account_id: str, headless: bool = False, proxy: str = None):
        """
        为指定账号启动浏览器
        
        Args:
            account_id: 账号ID
            headless: 是否无头模式
            proxy: 代理服务器（如：http://127.0.0.1:7890）
            
        Returns:
            (browser, context, page) 元组
        """
        from playwright.sync_api import sync_playwright
        
        if account_id not in self.accounts:
            raise ValueError(f"账号不存在: {account_id}")
        
        # 如果该账号已有运行中的浏览器，先关闭
        if account_id in self.active_accounts:
            self.stop_browser(account_id)
        
        account = self.accounts[account_id]
        data_dir = self.get_account_data_dir(account_id)
        
        # 启动 Playwright
        p = sync_playwright().start()
        
        # 启动浏览器（每个账号独立的数据目录）
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(data_dir),
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
            proxy={"server": proxy} if proxy else None
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        # 保存活跃实例
        self.active_accounts[account_id] = {
            'playwright': p,
            'browser': browser,
            'page': page
        }
        
        # 更新账号状态
        account.last_used = datetime.now().isoformat()
        self._save_accounts()
        
        print(f"✅ 启动浏览器成功: {account.name}")
        return browser, page
    
    def stop_browser(self, account_id: str):
        """停止指定账号的浏览器"""
        if account_id not in self.active_accounts:
            return
        
        try:
            instance = self.active_accounts[account_id]
            instance['browser'].close()
            instance['playwright'].stop()
            del self.active_accounts[account_id]
            print(f"✅ 关闭浏览器: {account_id}")
        except Exception as e:
            print(f"关闭浏览器失败: {e}")
    
    def stop_all_browsers(self):
        """停止所有浏览器"""
        for account_id in list(self.active_accounts.keys()):
            self.stop_browser(account_id)
    
    def is_browser_running(self, account_id: str) -> bool:
        """检查账号的浏览器是否正在运行"""
        return account_id in self.active_accounts
    
    def get_active_account_count(self) -> int:
        """获取正在运行的账号数量"""
        return len(self.active_accounts)
    
    def backup_cookies(self, account_id: str):
        """
        备份账号的 Cookies
        用于防止登录状态丢失
        """
        if account_id not in self.active_accounts:
            print(f"账号 {account_id} 没有运行中的浏览器")
            return
        
        try:
            page = self.active_accounts[account_id]['page']
            cookies = page.context.cookies()
            
            cookie_file = self.base_dir / account_id / "cookies" / "backup.json"
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Cookie 备份成功: {account_id}")
        except Exception as e:
            print(f"备份 Cookie 失败: {e}")
    
    def restore_cookies(self, account_id: str, page):
        """恢复账号的 Cookies"""
        cookie_file = self.base_dir / account_id / "cookies" / "backup.json"
        if not cookie_file.exists():
            return
        
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            page.context.add_cookies(cookies)
            print(f"✅ Cookie 恢复成功: {account_id}")
        except Exception as e:
            print(f"恢复 Cookie 失败: {e}")


# 全局账号管理器实例
_account_manager = None

def get_account_manager() -> AccountManager:
    """获取全局账号管理器实例"""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
    return _account_manager


if __name__ == "__main__":
    # 测试代码
    manager = get_account_manager()
    
    # 创建测试账号
    acc1 = manager.create_account("主账号", "fanqie")
    acc2 = manager.create_account("小号1", "fanqie")
    
    print(f"\n所有账号:")
    for acc in manager.list_accounts():
        print(f"  - {acc.name} ({acc.id})")
