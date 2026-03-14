"""
JWT 认证模块 - 支持多账号切换
基于 Token 的无状态认证
"""
import jwt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app

# JWT 配置
JWT_SECRET_KEY = None  # 从配置文件加载
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)      # Access Token 2小时过期
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)     # Refresh Token 30天过期


def init_jwt(app):
    """初始化 JWT 配置"""
    global JWT_SECRET_KEY
    JWT_SECRET_KEY = app.config.get('SECRET_KEY') or secrets.token_hex(32)
    
    # 从配置读取过期时间
    global JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES
    access_hours = app.config.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 2)
    refresh_days = app.config.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=access_hours)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=refresh_days)


def generate_tokens(user_id, username, is_admin=False, extra_data=None):
    """
    生成访问令牌和刷新令牌
    
    Args:
        user_id: 用户ID
        username: 用户名
        is_admin: 是否管理员
        extra_data: 额外数据（如 points_balance）
    
    Returns:
        dict: {access_token, refresh_token, expires_in, token_type}
    """
    global JWT_SECRET_KEY
    # 如果未初始化，使用默认密钥（仅用于测试）
    if JWT_SECRET_KEY is None:
        JWT_SECRET_KEY = secrets.token_hex(32)
    
    now = datetime.utcnow()
    
    # Access Token - 短期有效
    access_payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'type': 'access',
        'iat': now,
        'exp': now + JWT_ACCESS_TOKEN_EXPIRES,
        'jti': secrets.token_hex(16)  # 唯一标识，用于撤销
    }
    
    if extra_data:
        access_payload['extra'] = extra_data
    
    # Refresh Token - 长期有效
    refresh_payload = {
        'user_id': user_id,
        'username': username,
        'type': 'refresh',
        'iat': now,
        'exp': now + JWT_REFRESH_TOKEN_EXPIRES,
        'jti': secrets.token_hex(16)
    }
    
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm='HS256')
    
    # 🔥 修复：Python 3 中 jwt.encode 返回 bytes，需要解码为字符串
    if isinstance(access_token, bytes):
        access_token = access_token.decode('utf-8')
    if isinstance(refresh_token, bytes):
        refresh_token = refresh_token.decode('utf-8')
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': int(JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        'token_type': 'Bearer'
    }


def decode_token(token, token_type=None):
    """
    解码并验证 Token
    
    Args:
        token: JWT Token
        token_type: 期望的 token 类型 ('access' 或 'refresh')
    
    Returns:
        tuple: (payload, error)
        - 成功: (payload, None)
        - 失败: (None, error_info)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        
        # 验证 token 类型
        if token_type and payload.get('type') != token_type:
            return None, {'code': 'WRONG_TOKEN_TYPE', 'message': f'Expected {token_type} token'}
        
        return payload, None
        
    except jwt.ExpiredSignatureError:
        return None, {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired'}
    except jwt.InvalidTokenError as e:
        return None, {'code': 'INVALID_TOKEN', 'message': str(e)}


def get_token_from_request():
    """
    从请求中提取 Token
    支持: Authorization Header 或 Cookie
    
    Returns:
        str or None: Token 字符串
    """
    # 1. 优先从 Header 获取
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # 2. 从 Cookie 获取（兼容旧版 Session）
    from flask import session
    if session.get('logged_in') and session.get('user_id'):
        # 为兼容旧版，如果 Session 有效，视为已登录
        # 返回一个特殊的标记，让 jwt_required 识别
        return '__session__'
    
    return None


def jwt_required(optional=False):
    """
    JWT 认证装饰器
    
    Args:
        optional: 如果为 True，未登录也能访问，但 g.current_user 可能为 None
    
    Usage:
        @app.route('/api/protected')
        @jwt_required()
        def protected():
            user_id = g.current_user['user_id']
            return jsonify({'user_id': user_id})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = get_token_from_request()
            
            # 处理 Session 兼容模式
            if token == '__session__':
                from flask import session
                g.current_user = {
                    'user_id': session.get('user_id'),
                    'username': session.get('username'),
                    'is_admin': session.get('is_admin', False),
                    'source': 'session'  # 标记来源
                }
                return f(*args, **kwargs)
            
            if not token:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            
            payload, error = decode_token(token, 'access')
            
            if error:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'error': error['message'],
                    'code': error['code']
                }), 401
            
            # 将用户信息存入 g
            g.current_user = {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'is_admin': payload.get('is_admin', False),
                'extra': payload.get('extra', {}),
                'source': 'jwt'
            }
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def jwt_optional(f):
    """可选认证装饰器（快捷方式）"""
    return jwt_required(optional=True)(f)


# 兼容旧版装饰器
def login_required_api(f):
    """API 登录验证装饰器（兼容 JWT 和 Session）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        # Session 兼容
        if token == '__session__':
            from flask import session
            if session.get('logged_in') or session.get('user_id'):
                g.current_user = {
                    'user_id': session.get('user_id'),
                    'username': session.get('username'),
                    'is_admin': session.get('is_admin', False)
                }
                return f(*args, **kwargs)
        
        # JWT 验证
        if token:
            payload, error = decode_token(token, 'access')
            if not error:
                g.current_user = {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'is_admin': payload.get('is_admin', False)
                }
                return f(*args, **kwargs)
        
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    return decorated_function
