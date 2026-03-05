"""
点数系统API
提供用户点数查询、签到、消费等功能
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from web.models.point_model import point_model
from web.web_config import logger

points_api = Blueprint('points_api', __name__, url_prefix='/api/points')


def login_required_api(f):
    """API登录验证装饰器 - 检查 logged_in 或 user_id"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查登录状态 - 兼容两种方式
        if not session.get('logged_in') and 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required_api(f):
    """API管理员验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') and 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== 用户端API ====================

@points_api.route('/balance', methods=['GET'])
@login_required_api
def get_balance():
    """获取当前点数余额"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整，请重新登录'}), 401
    
    points = point_model.get_user_points(user_id)
    
    return jsonify({
        'success': True,
        'data': {
            'balance': points['balance'],
            'total_earned': points['total_earned'],
            'total_spent': points['total_spent']
        }
    })


@points_api.route('/transactions', methods=['GET'])
@login_required_api
def get_transactions():
    """获取交易记录"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整，请重新登录'}), 401
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    result = point_model.get_transactions(user_id, page, limit)
    
    return jsonify({
        'success': True,
        'data': result
    })


@points_api.route('/checkin', methods=['POST'])
@login_required_api
def daily_checkin():
    """每日签到"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整，请重新登录'}), 401
    
    result = point_model.daily_checkin(user_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': {
                'earned': result['earned'],
                'balance': result['balance'],
                'streak': result['streak'],
                'message': result['message']
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', '签到失败'),
            'already_checked': result.get('already_checked', False)
        }), 400


@points_api.route('/checkin/status', methods=['GET'])
@login_required_api
def get_checkin_status():
    """获取签到状态"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整，请重新登录'}), 401
    
    status = point_model.get_checkin_status(user_id)
    
    return jsonify({
        'success': True,
        'data': status
    })


@points_api.route('/estimate', methods=['POST'])
@login_required_api
def estimate_cost():
    """预估消耗"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'action' not in data:
        return jsonify({'success': False, 'error': '缺少action参数'}), 400
    
    action = data['action']
    params = data.get('params', {})
    
    # 获取当前余额
    points = point_model.get_user_points(user_id)
    
    if action == 'phase1':
        total_chapters = params.get('total_chapters', 200)
        estimated_characters = params.get('estimated_characters', 4)
        estimate = point_model.calculate_phase1_cost(total_chapters, estimated_characters)
        
        return jsonify({
            'success': True,
            'data': {
                'action': 'phase1',
                'estimated_cost': estimate['total'],
                'breakdown': estimate['breakdown'],
                'current_balance': points['balance'],
                'sufficient': points['balance'] >= estimate['total']
            }
        })
    
    elif action == 'phase2':
        chapter_count = params.get('chapter_count', 5)
        mode = params.get('mode', 'batch')
        estimate = point_model.calculate_phase2_cost(chapter_count, mode)
        
        return jsonify({
            'success': True,
            'data': {
                'action': 'phase2',
                'estimated_cost': estimate['total'],
                'chapter_count': estimate['chapter_count'],
                'mode': estimate['mode'],
                'cost_per_chapter': estimate['cost_per_chapter'],
                'current_balance': points['balance'],
                'sufficient': points['balance'] >= estimate['total']
            }
        })
    
    else:
        return jsonify({'success': False, 'error': '未知的action类型'}), 400


# ==================== 服务端内部调用API（无需登录验证） ====================

@points_api.route('/internal/spend', methods=['POST'])
def internal_spend_points():
    """
    内部API：扣除点数
    由其他服务调用，需要API密钥验证
    """
    # 验证API密钥
    api_key = request.headers.get('X-API-Key')
    if api_key != 'your-internal-api-key':  # 应该放在配置中
        return jsonify({'success': False, 'error': '无效的API密钥'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    source = data.get('source')
    description = data.get('description', '')
    related_id = data.get('related_id')
    
    if not all([user_id, amount, source]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = point_model.spend_points(user_id, amount, source, description, related_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': {
                'transaction_id': result['transaction_id'],
                'balance': result['balance'],
                'amount': result['amount']
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', '扣点失败'),
            'required': result.get('required'),
            'current': result.get('current')
        }), 400


@points_api.route('/internal/rollback', methods=['POST'])
def internal_rollback_points():
    """
    内部API：回滚点数
    AI调用失败时使用
    """
    api_key = request.headers.get('X-API-Key')
    if api_key != 'your-internal-api-key':
        return jsonify({'success': False, 'error': '无效的API密钥'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    related_id = data.get('related_id')
    reason = data.get('reason', '')
    
    if not all([user_id, related_id]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = point_model.rollback_points(user_id, related_id, reason)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': {
                'balance': result['balance'],
                'amount': result['amount']
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', '回滚失败')
        }), 400


@points_api.route('/internal/grant', methods=['POST'])
def internal_grant_points():
    """
    内部API：发放点数
    用于注册奖励等场景
    """
    api_key = request.headers.get('X-API-Key')
    if api_key != 'your-internal-api-key':
        return jsonify({'success': False, 'error': '无效的API密钥'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    source = data.get('source')
    description = data.get('description', '')
    
    if not all([user_id, amount, source]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = point_model.add_points(user_id, amount, source, description)
    
    if result['success']:
        return jsonify({
            'success': True,
            'data': {
                'balance': result['balance'],
                'amount': result['amount']
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', '发放失败')
        }), 400


# ==================== 公共配置API（无需登录） ====================

@points_api.route('/config', methods=['GET'])
def get_public_config():
    """
    获取点数配置（公开）
    返回消耗配置信息，用于前端估算
    """
    try:
        # 获取第二阶段相关配置
        phase2_batch = point_model.get_config('phase2_chapter_batch', 1)
        phase2_refined = point_model.get_config('phase2_chapter_refined', 2)
        
        return jsonify({
            'success': True,
            'config': {
                'phase2_chapter_batch': phase2_batch,
                'phase2_chapter_refined': phase2_refined
            }
        })
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        # 返回默认配置
        return jsonify({
            'success': True,
            'config': {
                'phase2_chapter_batch': 1,
                'phase2_chapter_refined': 2
            }
        })


# ==================== 管理员API ====================

@points_api.route('/admin/config', methods=['GET'])
@admin_required_api
def get_admin_config():
    """获取点数配置（管理员）"""
    configs = point_model.get_all_config()
    
    return jsonify({
        'success': True,
        'data': configs
    })


@points_api.route('/admin/config', methods=['PUT'])
@admin_required_api
def update_admin_config():
    """更新点数配置（管理员）"""
    data = request.get_json()
    
    if not data or 'config_key' not in data or 'config_value' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    config_key = data['config_key']
    config_value = data['config_value']
    
    if not isinstance(config_value, int) or config_value < 0:
        return jsonify({'success': False, 'error': '配置值必须是非负整数'}), 400
    
    result = point_model.update_config(config_key, config_value, session['user_id'])
    
    if result:
        return jsonify({
            'success': True,
            'message': f'配置 {config_key} 已更新为 {config_value}'
        })
    else:
        return jsonify({'success': False, 'error': '更新失败'}), 500


@points_api.route('/admin/user/<int:user_id>', methods=['GET'])
@admin_required_api
def get_user_points_admin(user_id):
    """获取指定用户的点数信息（管理员）"""
    points = point_model.get_user_points(user_id)
    transactions = point_model.get_transactions(user_id, page=1, limit=10)
    
    return jsonify({
        'success': True,
        'data': {
            'points': points,
            'recent_transactions': transactions['transactions']
        }
    })


@points_api.route('/admin/grant', methods=['POST'])
@admin_required_api
def admin_grant_points():
    """管理员手动发放点数"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    amount = data.get('amount')
    reason = data.get('reason', '管理员发放')
    
    if not user_id or not amount:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({'success': False, 'error': '点数必须是正整数'}), 400
    
    result = point_model.add_points(
        user_id, amount, 'admin_grant',
        f'管理员发放: {reason}'
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': f'已向用户{user_id}发放{amount}点',
            'data': {
                'balance': result['balance']
            }
        })
    else:
        return jsonify({'success': False, 'error': result.get('error', '发放失败')}), 500


@points_api.route('/admin/deduct', methods=['POST'])
@admin_required_api
def admin_deduct_points():
    """管理员手动扣除点数"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    amount = data.get('amount')
    reason = data.get('reason', '管理员扣除')
    
    if not user_id or not amount:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({'success': False, 'error': '点数必须是正整数'}), 400
    
    result = point_model.spend_points(
        user_id, amount, 'admin_deduct',
        f'管理员扣除: {reason}'
    )
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': f'已从用户{user_id}扣除{amount}点',
            'data': {
                'balance': result['balance']
            }
        })
    else:
        return jsonify({'success': False, 'error': result.get('error', '扣除失败')}), 500
