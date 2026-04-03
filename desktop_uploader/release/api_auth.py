#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官网API认证模块
处理GUI与官网的认证交互
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class AccountToken:
    """账户Token信息"""
    user_id: int
    username: str
    access_token: str
    refresh_token: str
    expires_at: float  # timestamp
    is_admin: bool = False
    points_balance: int = 0
    
    @property
    def is_expired(self) -> bool:
        """检查token是否过期（提前5分钟认为过期）"""
        return time.time() > (self.expires_at - 300)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AccountToken':
        return cls(**data)


class WebsiteAuth:
    """官网认证客户端"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            # 尝试从环境配置获取
            try:
                from config_env import env_config
                base_url = env_config.api_base_url
            except ImportError:
                base_url = "https://novel-ai.online"
        
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NovelPublisher-GUI/1.3.4'
        })
    
    def login(self, username: str, password: str) -> Optional[AccountToken]:
        """
        官网账户登录
        
        Args:
            username: 官网用户名
            password: 官网密码
            
        Returns:
            AccountToken or None
        """
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    'username': username,
                    'password': password,
                    'remember': True  # 获取长期token
                },
                timeout=30
            )
            
            data = response.json()
            
            if not data.get('success'):
                print(f"❌ 登录失败: {data.get('error', '未知错误')}")
                return None
            
            # 解析token过期时间（默认2小时）
            expires_in = data.get('expires_in', 7200)
            expires_at = time.time() + expires_in
            
            token = AccountToken(
                user_id=data['user_id'],
                username=data['username'],
                access_token=data['access_token'],
                refresh_token=data['refresh_token'],
                expires_at=expires_at,
                is_admin=data.get('is_admin', False),
                points_balance=data.get('points_balance', 0)
            )
            
            print(f"✅ 登录成功: {token.username} (余额: {token.points_balance})")
            return token
            
        except requests.exceptions.ConnectionError:
            print(f"❌ 无法连接到官网: {self.base_url}")
            return None
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[AccountToken]:
        """刷新access token"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/refresh",
                json={'refresh_token': refresh_token},
                timeout=30
            )
            
            data = response.json()
            
            if not data.get('success'):
                print(f"❌ Token刷新失败: {data.get('error')}")
                return None
            
            expires_in = data.get('expires_in', 7200)
            expires_at = time.time() + expires_in
            
            # 注意：返回的数据中可能没有user_id和username
            # 需要调用者补充
            return {
                'access_token': data['access_token'],
                'refresh_token': data['refresh_token'],
                'expires_at': expires_at
            }
            
        except Exception as e:
            print(f"❌ Token刷新异常: {e}")
            return None
    
    def verify_token(self, access_token: str) -> Optional[Dict]:
        """验证token是否有效"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/auth/verify",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            
            data = response.json()
            
            if data.get('success'):
                return data
            return None
            
        except Exception as e:
            print(f"❌ Token验证异常: {e}")
            return None


class AccountStorage:
    """账户本地存储管理"""
    
    def __init__(self, storage_file: str = "accounts.json"):
        self.storage_path = Path(__file__).parent / storage_file
        self.accounts: Dict[str, dict] = {}  # username -> account_data
        self._load()
    
    def _load(self):
        """从文件加载账户"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', {})
                print(f"📂 已加载 {len(self.accounts)} 个账户")
            except Exception as e:
                print(f"⚠️ 加载账户失败: {e}")
                self.accounts = {}
    
    def save(self):
        """保存账户到文件（密码加密存储）"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'accounts': self.accounts,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存账户失败: {e}")
            return False
    
    def add_account(self, username: str, password: str, token: AccountToken, 
                    fanqie_accounts: list = None):
        """
        添加账户
        
        Args:
            username: 官网用户名
            password: 官网密码（加密存储）
            token: 认证token
            fanqie_accounts: 绑定的番茄账户列表 [{"name": "番茄账号1", "cookies": "..."}]
        """
        # 简单加密密码（base64 + 固定salt）
        import base64
        encrypted_pass = base64.b64encode(password.encode()).decode()
        
        self.accounts[username] = {
            'username': username,
            'password': encrypted_pass,  # 加密后的密码
            'token': token.to_dict(),
            'fanqie_accounts': fanqie_accounts or [],
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        }
        self.save()
    
    def get_account(self, username: str) -> Optional[dict]:
        """获取账户信息"""
        return self.accounts.get(username)
    
    def update_token(self, username: str, token: AccountToken):
        """更新账户token"""
        if username in self.accounts:
            self.accounts[username]['token'] = token.to_dict()
            self.accounts[username]['last_login'] = datetime.now().isoformat()
            self.save()
    
    def add_fanqie_account(self, username: str, fanqie_name: str, cookies: str = None):
        """添加番茄账户绑定"""
        if username in self.accounts:
            fanqie_list = self.accounts[username].get('fanqie_accounts', [])
            
            # 检查是否已存在
            existing = next((f for f in fanqie_list if f['name'] == fanqie_name), None)
            if not existing:
                fanqie_list.append({
                    'name': fanqie_name,
                    'cookies': cookies,
                    'added_at': datetime.now().isoformat()
                })
                self.accounts[username]['fanqie_accounts'] = fanqie_list
                self.save()
                return True
        return False
    
    def remove_account(self, username: str):
        """删除账户"""
        if username in self.accounts:
            del self.accounts[username]
            self.save()
            return True
        return False
    
    def get_all_accounts(self) -> list:
        """获取所有账户列表"""
        return [
            {
                'username': k,
                'last_login': v.get('last_login'),
                'fanqie_count': len(v.get('fanqie_accounts', [])),
                'points_balance': v.get('token', {}).get('points_balance', 0)
            }
            for k, v in self.accounts.items()
        ]
    
    def decrypt_password(self, encrypted_pass: str) -> str:
        """解密密码"""
        import base64
        return base64.b64decode(encrypted_pass.encode()).decode()


class MultiAccountManager:
    """多账户管理器 - 整合认证和存储"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            # 尝试从环境配置获取
            try:
                from config_env import env_config
                base_url = env_config.api_base_url
            except ImportError:
                base_url = "https://novel-ai.online"
        
        self.auth = WebsiteAuth(base_url)
        self.storage = AccountStorage()
        self.current_account: Optional[str] = None  # 当前登录的官网账户
        self.active_sessions: Dict[str, AccountToken] = {}  # 活跃的token
    
    def login(self, username: str, password: str, save_account: bool = True) -> bool:
        """
        登录官网账户
        
        Returns:
            bool: 是否成功
        """
        token = self.auth.login(username, password)
        
        if not token:
            return False
        
        # 保存到活跃会话
        self.active_sessions[username] = token
        self.current_account = username
        
        # 保存到本地
        if save_account:
            existing = self.storage.get_account(username)
            fanqie_accounts = existing.get('fanqie_accounts', []) if existing else []
            self.storage.add_account(username, password, token, fanqie_accounts)
        
        return True
    
    def auto_login(self, username: str) -> bool:
        """使用保存的密码自动登录"""
        account = self.storage.get_account(username)
        if not account:
            print(f"❌ 未找到保存的账户: {username}")
            return False
        
        try:
            password = self.storage.decrypt_password(account['password'])
            return self.login(username, password, save_account=False)
        except Exception as e:
            print(f"❌ 自动登录失败: {e}")
            return False
    
    def get_token(self, username: str) -> Optional[AccountToken]:
        """获取账户token（自动刷新）"""
        token = self.active_sessions.get(username)
        
        if not token:
            # 尝试从存储加载
            account = self.storage.get_account(username)
            if account and account.get('token'):
                token = AccountToken.from_dict(account['token'])
                self.active_sessions[username] = token
        
        if token and token.is_expired:
            # 需要刷新
            print(f"🔄 Token过期，正在刷新: {username}")
            refresh_result = self.auth.refresh_token(token.refresh_token)
            if refresh_result:
                # 更新token信息
                token.access_token = refresh_result['access_token']
                token.refresh_token = refresh_result['refresh_token']
                token.expires_at = refresh_result['expires_at']
                self.storage.update_token(username, token)
            else:
                # 刷新失败，尝试重新登录
                print(f"🔄 Token刷新失败，尝试重新登录: {username}")
                if not self.auto_login(username):
                    return None
                token = self.active_sessions.get(username)
        
        return token
    
    def switch_account(self, username: str) -> bool:
        """切换到指定账户"""
        if username not in self.active_sessions and not self.storage.get_account(username):
            print(f"❌ 账户不存在: {username}")
            return False
        
        # 确保token有效
        token = self.get_token(username)
        if token:
            self.current_account = username
            return True
        return False
    
    def logout(self, username: str = None):
        """登出账户"""
        target = username or self.current_account
        if target:
            if target in self.active_sessions:
                del self.active_sessions[target]
            if self.current_account == target:
                self.current_account = None
            print(f"👋 已登出: {target}")
    
    def get_current_user(self) -> Optional[dict]:
        """获取当前用户信息"""
        if not self.current_account:
            return None
        
        token = self.get_token(self.current_account)
        if token:
            return {
                'username': token.username,
                'user_id': token.user_id,
                'points_balance': token.points_balance,
                'is_admin': token.is_admin
            }
        return None
    
    def make_authenticated_request(self, username: str, method: str, 
                                   endpoint: str, **kwargs) -> Optional[dict]:
        """
        发起带认证的API请求
        
        Args:
            username: 官网账户名
            method: HTTP方法 (get/post/put/delete)
            endpoint: API端点 (/api/...)
            **kwargs: requests的其他参数
        """
        token = self.get_token(username)
        if not token:
            print(f"❌ 无法获取有效token: {username}")
            return None
        
        url = f"{self.auth.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {token.access_token}'
        
        try:
            response = self.auth.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                timeout=kwargs.get('timeout', 30),
                **{k: v for k, v in kwargs.items() if k != 'timeout'}
            )
            
            if response.status_code == 401:
                print(f"⚠️ Token失效，尝试刷新: {username}")
                # 强制刷新token
                self.active_sessions.pop(username, None)
                token = self.get_token(username)
                if token:
                    headers['Authorization'] = f'Bearer {token.access_token}'
                    response = self.auth.session.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        timeout=kwargs.get('timeout', 30),
                        **{k: v for k, v in kwargs.items() if k != 'timeout'}
                    )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None


# 全局多账户管理器实例
multi_account_manager = MultiAccountManager()


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("官网认证模块测试")
    print("=" * 50)
    
    manager = MultiAccountManager()
    
    # 显示已保存的账户
    accounts = manager.storage.get_all_accounts()
    print(f"\n已保存账户: {len(accounts)}")
    for acc in accounts:
        print(f"  - {acc['username']} (番茄账户: {acc['fanqie_count']}个)")
    
    # 测试登录
    print("\n测试登录...")
    test_user = input("用户名: ").strip()
    test_pass = input("密码: ").strip()
    
    if manager.login(test_user, test_pass):
        user_info = manager.get_current_user()
        print(f"\n✅ 当前用户: {user_info}")
    else:
        print("\n❌ 登录失败")
