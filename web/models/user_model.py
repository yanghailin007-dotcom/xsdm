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
                    phone TEXT UNIQUE NOT NULL,
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
        """使用SHA256哈希密码（生产环境建议使用bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, phone: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            phone: 手机号
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
            
            # 验证手机号格式
            if not self._validate_phone(phone):
                return {"success": False, "error": "手机号格式不正确"}
            
            # 检查用户名是否已存在
            with self._get_connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM users WHERE username = ? OR phone = ?",
                    (username, phone)
                ).fetchone()
                
                if existing:
                    if existing['username'] == username:
                        return {"success": False, "error": "用户名已存在"}
                    else:
                        return {"success": False, "error": "该手机号已注册"}
                
                # 创建用户
                password_hash = self._hash_password(password)
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, phone, email)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, phone, email)
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
            password_hash = self._hash_password(password)
            
            with self._get_connection() as conn:
                user = conn.execute(
                    """
                    SELECT id, username, password_hash, phone, email, 
                           is_active, is_admin, last_login_at
                    FROM users 
                    WHERE (username = ? OR phone = ?) AND password_hash = ?
                    """,
                    (username, username, password_hash)
                ).fetchone()
                
                if user:
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
                    logger.warn(f"⚠️ 验证码不存在或已使用: {phone}")
                    return False
                
                # 检查是否过期
                expires_at = datetime.fromisoformat(record['expires_at'])
                if datetime.now() > expires_at:
                    logger.warn(f"⚠️ 验证码已过期: {phone}")
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
                    logger.warn(f"⚠️ 超过验证码请求限制: {phone} ({count}次)")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 检查频率限制失败: {e}")
            return True  # 出错时允许通过


# 创建全局模型实例
user_model = UserModel()
verification_model = VerificationCodeModel()