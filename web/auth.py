"""
用户认证和授权模块
"""
from functools import wraps
from flask import session, redirect, url_for
from web.web_config import logger

class UserAuth:
    """用户认证类"""
    
    def __init__(self):
        # 默认账户配置（用于初始化数据库）
        self.default_users = {
            "admin": {"password": "yanghailin", "is_admin": True, "phone": None},
            "test": {"password": "", "is_admin": False, "phone": None}  # 空密码表示任意密码
        }
        # 初始化默认用户到数据库
        self._init_default_users()
    
    def _init_default_users(self):
        """将默认用户初始化到数据库（如果不存在）"""
        try:
            from web.models.user_model import user_model
            
            for username, config in self.default_users.items():
                # 检查用户是否已存在
                existing = user_model.get_user_by_username(username)
                if not existing:
                    # 创建默认用户
                    result = user_model.create_user(
                        username=username,
                        password=config["password"] if config["password"] else "test123",  # test用户给一个默认密码
                        phone=config["phone"],
                        email=None,
                        is_admin=config.get("is_admin", False)
                    )
                    if result.get("success"):
                        logger.info(f"✅ 初始化默认用户: {username}")
                    else:
                        logger.warning(f"⚠️ 初始化用户失败: {username} - {result.get('error')}")
                else:
                    # 更新现有默认用户的密码和管理员状态
                    if username == "admin":
                        user_model.update_password(username, config["password"])
                        # 确保 admin 用户有管理员权限
                        user_model.set_admin_status(username, True)
                        logger.info(f"✅ 已同步默认用户密码和管理员权限: {username}")
                    else:
                        logger.info(f"✅ 默认用户已存在: {username}")
                    
        except Exception as e:
            logger.error(f"❌ 初始化默认用户失败: {e}")
    
    def verify_user(self, username: str, password: str) -> bool:
        """验证用户身份"""
        if not username:
            return False
        
        # [安全修复] 已删除 test 用户任意密码登录后门
        # 所有用户（包括test）必须通过数据库验证
        
        # 从数据库验证所有用户（包括admin和新注册用户）
        try:
            from web.models.user_model import user_model
            user = user_model.verify_user(username, password)
            if user:
                logger.info(f"✅ 用户登录成功: {username}")
                return True
        except Exception as e:
            logger.error(f"❌ 数据库验证失败: {e}")
        
        logger.info(f"❌ 登录失败: {username}")
        return False
    
    def add_user(self, username: str, password: str, phone: str = None, email: str = None) -> bool:
        """添加用户（使用数据库）"""
        try:
            from web.models.user_model import user_model
            result = user_model.create_user(username, password, phone, email)
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
        """获取用户列表（仅返回内存中的默认用户列表）"""
        return list(self.default_users.keys())
    
    def update_password(self, username: str, new_password: str) -> bool:
        """更新用户密码（需要在user_model中实现）"""
        # test用户不允许修改密码
        if username.lower() == 'test':
            logger.warning(f"⚠️ 尝试修改测试用户密码被拒绝: {username}")
            return False
        
        # TODO: 需要在user_model中实现update_password方法
        # 目前暂时返回失败，提示用户通过其他方式修改
        logger.warning(f"⚠️ 密码修改功能需要在user_model中实现: {username}")
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