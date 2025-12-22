"""
用户认证和授权模块
"""
from functools import wraps
from flask import session, redirect, url_for
from web.web_config import logger

class UserAuth:
    """用户认证类"""
    
    def __init__(self):
        self.users = {
            "admin": "admin",  # 默认管理员账户
            "test": ""         # 测试账户（空密码）
        }
    
    def verify_user(self, username: str, password: str) -> bool:
        """验证用户身份"""
        if not username:
            return False
            
        # 特殊处理：测试用户
        if username.lower() == 'test':
            logger.info(f"✅ 测试用户登录成功: {username}")
            return True
        
        # 正常验证流程
        stored_password = self.users.get(username)
        if stored_password is not None and password == stored_password:
            logger.info(f"✅ 用户登录成功: {username}")
            return True
        
        logger.info(f"❌ 登录失败: {username}")
        return False
    
    def add_user(self, username: str, password: str) -> bool:
        """添加用户（仅用于开发环境）"""
        if username in self.users:
            return False
        self.users[username] = password
        logger.info(f"✅ 添加用户: {username}")
        return True
    
    def get_user_list(self) -> list:
        """获取用户列表（仅用于开发环境）"""
        return list(self.users.keys())

# 创建全局认证实例
user_auth = UserAuth()

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        if session.get('username') != 'admin':
            return {"error": "需要管理员权限"}, 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """获取当前登录用户"""
    return session.get('username', 'anonymous')

def is_logged_in():
    """检查是否已登录"""
    return 'logged_in' in session and session['logged_in']

def is_admin():
    """检查是否为管理员"""
    return is_logged_in() and session.get('username') == 'admin'