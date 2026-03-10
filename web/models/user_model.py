"""
用户数据库模型
使用SQLite存储用户信息
"""
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Union
from web.web_config import logger, BASE_DIR

# 尝试导入bcrypt，如果不存在则使用fallback
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not installed, using SHA256 fallback (not recommended for production)")


class UserModel:
    """用户数据库模型"""
    
    def __init__(self, db_path: Union[str, Path, None] = None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = BASE_DIR / "data" / "users.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)
        
        # 确保数据目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = str(db_path)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            # 用户表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    phone TEXT UNIQUE,
                    email TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP
                )
            """)
            
            # 验证码表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    code TEXT NOT NULL,
                    type TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT
                )
            """)
            
            # 登录日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
            logger.info(f"✅ 数据库初始化完成: {self.db_path}")
    
    def _hash_password(self, password: str) -> str:
        """哈希密码 - 优先使用bcrypt，降级到SHA256（用于兼容旧数据）"""
        if BCRYPT_AVAILABLE:
            # bcrypt 自动处理盐值，推荐用于生产环境
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        else:
            # 兼容旧数据，但会记录警告
            return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码 - 支持bcrypt和SHA256（兼容旧数据）"""
        if BCRYPT_AVAILABLE and hashed.startswith('$2'):
            # bcrypt 格式: $2b$10$...
            return bcrypt.checkpw(password.encode(), hashed.encode())
        else:
            # 兼容旧版 SHA256
            return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    def create_user(self, username: str, password: str, phone: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            phone: 手机号（可选）
            email: 邮箱（可选）
            
        Returns:
            包含success和message或error的字典
        """
        try:
            # 验证用户名长度
            if len(username) < 3 or len(username) > 20:
                return {"success": False, "error": "用户名长度必须在3-20个字符之间"}
            
            # 验证密码强度
            if len(password) < 6:
                return {"success": False, "error": "密码长度至少6个字符"}
            
            # 验证手机号格式（如果提供了手机号）
            if phone and not self._validate_phone(phone):
                return {"success": False, "error": "手机号格式不正确"}
            
            # 检查用户名是否已存在
            with self._get_connection() as conn:
                # 检查用户名
                existing_user = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                ).fetchone()
                if existing_user:
                    return {"success": False, "error": "用户名已存在"}
                
                # 如果提供了手机号，检查手机号是否已存在
                if phone:
                    existing_phone = conn.execute(
                        "SELECT id FROM users WHERE phone = ?",
                        (phone,)
                    ).fetchone()
                    if existing_phone:
                        return {"success": False, "error": "该手机号已注册"}
                
                # 创建用户（phone 为 None 时使用唯一占位符避免 NOT NULL + UNIQUE 冲突）
                import time
                actual_phone = phone if phone else f'NULL_{username}_{int(time.time())}'
                password_hash = self._hash_password(password)
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, phone, email)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, actual_phone, email)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ 创建用户成功: {username} (ID: {user_id})")
                return {
                    "success": True,
                    "message": "注册成功",
                    "user_id": user_id
                }
                
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ 用户创建失败（完整性错误）: {e}")
            return {"success": False, "error": "用户名或手机号已存在"}
        except Exception as e:
            logger.error(f"❌ 用户创建失败: {e}")
            return {"success": False, "error": "注册失败，请稍后重试"}
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户登录
        
        Args:
            username: 用户名或手机号
            password: 密码
            
        Returns:
            用户信息字典，验证失败返回None
        """
        try:
            with self._get_connection() as conn:
                # 先查询用户信息
                user = conn.execute(
                    """
                    SELECT id, username, password_hash, phone, email, 
                           is_active, is_admin, last_login_at
                    FROM users 
                    WHERE username = ? OR phone = ?
                    """,
                    (username, username)
                ).fetchone()
                
                # 验证密码
                if user and self._verify_password(password, user['password_hash']):
                    # [安全升级] 如果是旧版SHA256哈希，自动升级到bcrypt
                    if BCRYPT_AVAILABLE and not user['password_hash'].startswith('$2'):
                        new_hash = self._hash_password(password)
                        conn.execute(
                            "UPDATE users SET password_hash = ? WHERE id = ?",
                            (new_hash, user['id'])
                        )
                        conn.commit()
                        logger.info(f"用户 {username} 密码哈希已自动升级到bcrypt")
                    
                    # 更新最后登录时间
                    conn.execute(
                        "UPDATE users SET last_login_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), user['id'])
                    )
                    conn.commit()
                    
                    return dict(user)
                return None
                
        except Exception as e:
            logger.error(f"❌ 用户验证失败: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        try:
            with self._get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                ).fetchone()
                
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"❌ 获取用户失败: {e}")
            return None
    
    def mark_welcome_shown(self, user_id: int) -> bool:
        """标记用户已显示欢迎弹窗"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE users SET welcome_shown_at = ? WHERE id = ?",
                    (datetime.now(), user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 标记欢迎弹窗状态失败: {e}")
            return False
    
    def has_seen_welcome(self, user_id: int) -> bool:
        """检查用户是否已看过欢迎弹窗"""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT welcome_shown_at FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                return result and result['welcome_shown_at'] is not None
        except Exception as e:
            logger.error(f"❌ 检查欢迎弹窗状态失败: {e}")
            return False
    
    def _validate_phone(self, phone: str) -> bool:
        """验证手机号格式（中国手机号）"""
        import re
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    def log_login(self, user_id: int, username: str, action: str,
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None, success: bool = True):
        """记录登录日志"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO login_logs (user_id, username, action, ip_address, user_agent, success)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, action, ip_address, user_agent, 1 if success else 0)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 记录登录日志失败: {e}")
    
    # ==================== 管理员方法 ====================
    
    def get_all_users(self) -> list:
        """获取所有用户列表（用于管理员）"""
        try:
            with self._get_connection() as conn:
                users = conn.execute(
                    """
                    SELECT id, username, phone, email, is_active, is_admin, 
                           created_at, last_login_at
                    FROM users
                    ORDER BY id DESC
                    """
                ).fetchall()
                return [dict(user) for user in users]
        except Exception as e:
            logger.error(f"❌ 获取用户列表失败: {e}")
            return []
    
    def update_user_status(self, user_id: int, is_active: bool) -> dict:
        """更新用户状态（禁用/启用）"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                    (1 if is_active else 0, datetime.now().isoformat(), user_id)
                )
                conn.commit()
                status = "启用" if is_active else "禁用"
                logger.info(f"✅ 用户 {user_id} 已{status}")
                return {"success": True, "message": f"用户已{status}"}
        except Exception as e:
            logger.error(f"❌ 更新用户状态失败: {e}")
            return {"success": False, "error": str(e)}
    
    def reset_password(self, user_id: int, new_password: str = "123456") -> dict:
        """重置用户密码"""
        try:
            password_hash = self._hash_password(new_password)
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                    (password_hash, datetime.now().isoformat(), user_id)
                )
                conn.commit()
                logger.info(f"✅ 用户 {user_id} 密码已重置")
                return {"success": True, "message": "密码已重置", "new_password": new_password}
        except Exception as e:
            logger.error(f"❌ 重置密码失败: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_user(self, user_id: int) -> dict:
        """删除用户"""
        try:
            with self._get_connection() as conn:
                # 先删除关联的登录日志
                conn.execute("DELETE FROM login_logs WHERE user_id = ?", (user_id,))
                # 删除用户
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                logger.info(f"✅ 用户 {user_id} 已删除")
                return {"success": True, "message": "用户已删除"}
        except Exception as e:
            logger.error(f"❌ 删除用户失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        try:
            with self._get_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,)
                ).fetchone()
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"❌ 获取用户失败: {e}")
            return None


class VerificationCodeModel:
    """验证码模型"""
    
    def __init__(self, db_path: Union[str, Path, None] = None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = BASE_DIR / "data" / "users.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_code(self, length: int = 6) -> str:
        """生成随机验证码"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def create_code(self, phone: str, code_type: str = "register",
                    expiry_minutes: int = 5, ip_address: Optional[str] = None) -> str:
        """
        创建验证码
        
        Args:
            phone: 手机号
            code_type: 验证码类型 (register, login, reset_password)
            expiry_minutes: 过期时间（分钟）
            ip_address: 请求IP地址
            
        Returns:
            生成的验证码
        """
        # 清理该手机号旧的未使用验证码
        with self._get_connection() as conn:
            conn.execute(
                """
                DELETE FROM verification_codes 
                WHERE phone = ? AND type = ? AND used = 0 AND expires_at > ?
                """,
                (phone, code_type, datetime.now().isoformat())
            )
            conn.commit()
        
        # 生成新验证码
        code = self.generate_code()
        expires_at = (datetime.now() + timedelta(minutes=expiry_minutes)).isoformat()
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO verification_codes (phone, code, type, expires_at, ip_address)
                VALUES (?, ?, ?, ?, ?)
                """,
                (phone, code, code_type, expires_at, ip_address)
            )
            conn.commit()
        
        logger.info(f"📱 生成验证码: {phone} - {code_type}")
        return code
    
    def verify_code(self, phone: str, code: str, code_type: str = "register") -> bool:
        """
        验证验证码
        
        Args:
            phone: 手机号
            code: 验证码
            code_type: 验证码类型
            
        Returns:
            验证成功返回True，否则返回False
        """
        try:
            with self._get_connection() as conn:
                # 查找有效的验证码
                record = conn.execute(
                    """
                    SELECT id, code, used, expires_at
                    FROM verification_codes
                    WHERE phone = ? AND code = ? AND type = ? AND used = 0
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (phone, code, code_type)
                ).fetchone()
                
                if not record:
                    logger.warning(f"⚠️ 验证码不存在或已使用: {phone}")
                    return False
                
                # 检查是否过期
                expires_at = datetime.fromisoformat(record['expires_at'])
                if datetime.now() > expires_at:
                    logger.warning(f"⚠️ 验证码已过期: {phone}")
                    return False
                
                # 标记为已使用
                conn.execute(
                    "UPDATE verification_codes SET used = 1 WHERE id = ?",
                    (record['id'],)
                )
                conn.commit()
                
                logger.info(f"✅ 验证码验证成功: {phone}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 验证码验证失败: {e}")
            return False
    
    def check_rate_limit(self, phone: str, code_type: str = "register", 
                        max_attempts: int = 3, time_window_minutes: int = 60) -> bool:
        """
        检查请求频率限制
        
        Args:
            phone: 手机号
            code_type: 验证码类型
            max_attempts: 最大尝试次数
            time_window_minutes: 时间窗口（分钟）
            
        Returns:
            未超过限制返回True，否则返回False
        """
        try:
            time_window = datetime.now() - timedelta(minutes=time_window_minutes)
            
            with self._get_connection() as conn:
                count = conn.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM verification_codes
                    WHERE phone = ? AND type = ? AND created_at > ?
                    """,
                    (phone, code_type, time_window.isoformat())
                ).fetchone()['count']
                
                if count >= max_attempts:
                    logger.warning(f"⚠️ 超过验证码请求限制: {phone} ({count}次)")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 检查频率限制失败: {e}")
            return True  # 出错时允许通过


# 创建全局模型实例
user_model = UserModel()
verification_model = VerificationCodeModel()