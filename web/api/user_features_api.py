"""
用户功能订阅API
管理用户Pro会员状态和功能订阅
"""
import os
import sqlite3
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
from datetime import datetime, timedelta
from pathlib import Path
from web.web_config import logger, BASE_DIR
from web.models.point_model import point_model

user_features_api = Blueprint('user_features_api', __name__, url_prefix='/api/user/features')

# 数据库路径
DB_PATH = BASE_DIR / "data" / "users.db"


def login_required_api(f):
    """API登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from web.jwt_auth import get_token_from_request, decode_token
        
        token = get_token_from_request()
        
        # JWT Token 验证
        if token and token != '__session__':
            payload, error = decode_token(token, 'access')
            if not error:
                g.current_user = {
                    'user_id': payload['user_id'],
                    'username': payload['username'],
                    'is_admin': payload.get('is_admin', False)
                }
                return f(*args, **kwargs)
            else:
                return jsonify({'success': False, 'error': error['message'], 'code': error['code']}), 401
        
        # Session 兼容模式
        if token == '__session__' or session.get('logged_in') or session.get('user_id'):
            if session.get('user_id'):
                g.current_user = {
                    'user_id': session.get('user_id'),
                    'username': session.get('username'),
                    'is_admin': session.get('is_admin', False)
                }
                return f(*args, **kwargs)
        
        return jsonify({'success': False, 'error': '请先登录', 'code': 'AUTH_REQUIRED'}), 401
    return decorated_function


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_user_features_table():
    """初始化用户功能订阅表"""
    try:
        with get_db_connection() as conn:
            # 用户功能订阅表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    feature_key TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    auto_renew INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, feature_key),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 功能订阅历史记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feature_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    feature_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    points_spent INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
            logger.info("✅ 用户功能订阅表初始化完成")
    except Exception as e:
        logger.error(f"❌ 初始化用户功能订阅表失败: {e}")


# 功能配置
FEATURES_CONFIG = {
    'fanqie_upload': {
        'name': '番茄小说上传 Pro',
        'description': '一键上传小说到番茄作家平台',
        'price_monthly': 88,  # 创造点/月
        'features': [
            '自动创建书籍并设置信息',
            '批量上传章节（支持定时发布）',
            '智能检测发布状态',
            '每日自动发布设置'
        ]
    }
}


@user_features_api.route('/status/<feature_key>', methods=['GET'])
@login_required_api
def get_feature_status(feature_key):
    """获取用户功能订阅状态"""
    user_id = g.current_user.get('user_id')
    
    try:
        with get_db_connection() as conn:
            # 查询功能订阅状态
            feature = conn.execute(
                """
                SELECT * FROM user_features 
                WHERE user_id = ? AND feature_key = ?
                """,
                (user_id, feature_key)
            ).fetchone()
            
            if not feature:
                return jsonify({
                    'success': True,
                    'data': {
                        'feature_key': feature_key,
                        'is_active': False,
                        'is_expired': True,
                        'expires_at': None,
                        'days_remaining': 0
                    }
                })
            
            # 检查是否过期
            now = datetime.now()
            expires_at = datetime.fromisoformat(feature['expires_at']) if feature['expires_at'] else now
            is_expired = now > expires_at
            days_remaining = max(0, (expires_at - now).days)
            
            # 如果已过期但状态仍为active，更新状态
            if is_expired and feature['is_active']:
                conn.execute(
                    """
                    UPDATE user_features 
                    SET is_active = 0, updated_at = ?
                    WHERE user_id = ? AND feature_key = ?
                    """,
                    (now.isoformat(), user_id, feature_key)
                )
                conn.commit()
            
            return jsonify({
                'success': True,
                'data': {
                    'feature_key': feature_key,
                    'is_active': feature['is_active'] and not is_expired,
                    'is_expired': is_expired,
                    'expires_at': feature['expires_at'],
                    'days_remaining': days_remaining,
                    'auto_renew': bool(feature['auto_renew'])
                }
            })
            
    except Exception as e:
        logger.error(f"❌ 获取功能状态失败: {e}")
        return jsonify({'success': False, 'error': '获取状态失败'}), 500


@user_features_api.route('/subscribe', methods=['POST'])
@login_required_api
def subscribe_feature():
    """订阅功能（使用创造点支付）"""
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': '请求参数错误'}), 400
    
    feature_key = data.get('feature_key')
    months = data.get('months', 1)
    
    if not feature_key:
        return jsonify({'success': False, 'error': '缺少功能标识'}), 400
    
    if feature_key not in FEATURES_CONFIG:
        return jsonify({'success': False, 'error': '未知的功能类型'}), 400
    
    if not isinstance(months, int) or months < 1 or months > 12:
        return jsonify({'success': False, 'error': '订阅时长必须在1-12个月之间'}), 400
    
    config = FEATURES_CONFIG[feature_key]
    total_cost = config['price_monthly'] * months
    
    try:
        # 检查用户余额
        points_info = point_model.get_user_points(user_id)
        if points_info['balance'] < total_cost:
            return jsonify({
                'success': False, 
                'error': '创造点余额不足',
                'required': total_cost,
                'current': points_info['balance']
            }), 400
        
        # 计算订阅时间
        now = datetime.now()
        
        with get_db_connection() as conn:
            # 查询现有订阅
            existing = conn.execute(
                """
                SELECT * FROM user_features 
                WHERE user_id = ? AND feature_key = ?
                """,
                (user_id, feature_key)
            ).fetchone()
            
            if existing and existing['expires_at']:
                # 如果有未过期的订阅，从过期时间续期
                expires_at = datetime.fromisoformat(existing['expires_at'])
                if expires_at > now:
                    new_expires_at = expires_at + timedelta(days=30*months)
                else:
                    new_expires_at = now + timedelta(days=30*months)
            else:
                new_expires_at = now + timedelta(days=30*months)
            
            # 扣除创造点
            spend_result = point_model.spend_points(
                user_id=user_id,
                amount=total_cost,
                source=f'{feature_key}_subscribe',
                description=f"订阅 {config['name']} {months}个月",
                related_id=None
            )
            
            if not spend_result['success']:
                return jsonify({
                    'success': False,
                    'error': spend_result.get('error', '扣点失败')
                }), 400
            
            # 更新或插入订阅记录
            if existing:
                conn.execute(
                    """
                    UPDATE user_features 
                    SET is_active = 1, 
                        started_at = ?,
                        expires_at = ?,
                        updated_at = ?
                    WHERE user_id = ? AND feature_key = ?
                    """,
                    (now.isoformat(), new_expires_at.isoformat(), now.isoformat(),
                     user_id, feature_key)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_features 
                    (user_id, feature_key, is_active, started_at, expires_at)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (user_id, feature_key, now.isoformat(), new_expires_at.isoformat())
                )
            
            # 记录历史
            conn.execute(
                """
                INSERT INTO user_feature_history 
                (user_id, feature_key, action, points_spent, started_at, expires_at)
                VALUES (?, ?, 'subscribe', ?, ?, ?)
                """,
                (user_id, feature_key, total_cost, now.isoformat(), new_expires_at.isoformat())
            )
            
            conn.commit()
            
            logger.info(f"✅ 用户 {user_id} 订阅 {feature_key} 成功，时长 {months}个月")
            
            return jsonify({
                'success': True,
                'data': {
                    'feature_key': feature_key,
                    'feature_name': config['name'],
                    'months': months,
                    'cost': total_cost,
                    'expires_at': new_expires_at.isoformat(),
                    'balance': spend_result['balance']
                }
            })
            
    except Exception as e:
        logger.error(f"❌ 订阅功能失败: {e}")
        return jsonify({'success': False, 'error': '订阅失败，请稍后重试'}), 500


@user_features_api.route('/list', methods=['GET'])
@login_required_api
def get_user_features():
    """获取用户所有功能订阅列表"""
    user_id = g.current_user.get('user_id')
    
    try:
        with get_db_connection() as conn:
            features = conn.execute(
                """
                SELECT * FROM user_features 
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,)
            ).fetchall()
            
            now = datetime.now()
            result = []
            
            for feature in features:
                expires_at = datetime.fromisoformat(feature['expires_at']) if feature['expires_at'] else now
                is_expired = now > expires_at
                days_remaining = max(0, (expires_at - now).days)
                
                config = FEATURES_CONFIG.get(feature['feature_key'], {})
                
                result.append({
                    'feature_key': feature['feature_key'],
                    'feature_name': config.get('name', feature['feature_key']),
                    'is_active': feature['is_active'] and not is_expired,
                    'is_expired': is_expired,
                    'expires_at': feature['expires_at'],
                    'days_remaining': days_remaining,
                    'price_monthly': config.get('price_monthly', 0)
                })
            
            return jsonify({
                'success': True,
                'data': result
            })
            
    except Exception as e:
        logger.error(f"❌ 获取功能列表失败: {e}")
        return jsonify({'success': False, 'error': '获取列表失败'}), 500


@user_features_api.route('/config', methods=['GET'])
def get_features_config():
    """获取功能配置（公开API）"""
    return jsonify({
        'success': True,
        'data': FEATURES_CONFIG
    })


# 初始化数据库表
init_user_features_table()
