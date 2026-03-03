"""
用户认证和授权模块
"""
from functools import wraps
from flask import session, redirect, url_for
from web.web_config import logger

class UserAuth:
    """用户认证类"""
    
    def __init__(self):
        # 保留内存中的默认账户（向后兼容）
        self.default_users = {
            "admin": "admin",  # 默认管理员账户
            "test": ""         # 测试账户（空密码）
        }
    
    def verify_user(self, username: str, password: str) -> bool:
        """验证用户身份"""
        if not username:
            return False
        
        # 特殊处理：测试用户（向后兼容）
        if username.lower() == 'test':
            logger.info(f"✅ 测试用户登录成功: {username}")
            return True
        
        # 优先检查内存中的默认账户（向后兼容）
        stored_password = self.default_users.get(username)
        if stored_password is not None and password == stored_password:
            logger.info(f"✅ 用户登录成功: {username}")
            return True
        
        # 从数据库验证用户
        try:
            from web.models.user_model import user_model
            user = user_model.verify_user(username, password)
            if user:
                logger.info(f"✅ 数据库用户登录成功: {username}")
                return True
        except Exception as e:
            logger.error(f"❌ 数据库验证失败: {e}")
        
        logger.info(f"❌ 登录失败: {username}")
        return False
    
    def add_user(self, username: str, password: str) -> bool:
        """添加用户（使用数据库）"""
        try:
            from web.models.user_model import user_model
            result = user_model.create_user(username, password)
            if result.get('success'):
                logger.info(f"✅ 添加用户: {username}")
                return True
            else:
                logger.warning(f"⚠️ 添加用户失败: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"❌ 添加用户失败: {e}")
            return False
    
    def get_user_list(self) -> list:
        """获取用户列表（仅返回默认用户，数据库用户请直接查询）"""
        return list(self.default_users.keys())
    
    def update_password(self, username: str, new_password: str) -> bool:
        """更新用户密码"""
        # 特殊用户不允许修改密码
        if username.lower() == 'test':
            logger.warning(f"⚠️ 尝试修改测试用户密码被拒绝: {username}")
            return False
        
        # 默认账户在内存中修改
        if username in self.default_users:
            self.default_users[username] = new_password
            logger.info(f"🔐 默认用户密码已更新: {username}")
            return True
        
        # 数据库用户在数据库中修改（需要额外实现）
        logger.warning(f"⚠️ 数据库用户密码修改未实现: {username}")
        return False

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