"""
管理员API - 用户管理等功能
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from web.models.user_model import user_model
from web.models.point_model import point_model
from web.web_config import logger

admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_api.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """获取所有用户列表"""
    try:
        users = user_model.get_all_users()
        return jsonify({
            'success': True,
            'data': users
        })
    except Exception as e:
        logger.error(f"❌ 获取用户列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/users/recharge', methods=['POST'])
@admin_required
def recharge_user():
    """为用户充值"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount', 0)
        
        if not user_id or not amount:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        if amount <= 0:
            return jsonify({'success': False, 'error': '充值点数必须大于0'}), 400
        
        # 检查用户是否存在
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        # 执行充值
        result = point_model.add_points(
            user_id=user_id,
            amount=amount,
            source='admin_grant',
            description='管理员充值'
        )
        
        if result['success']:
            logger.info(f"✅ 管理员为用户 {user_id} 充值 {amount} 点")
            return jsonify({
                'success': True,
                'message': f'成功充值 {amount} 点',
                'data': {'balance': result['balance']}
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', '充值失败')}), 500
            
    except Exception as e:
        logger.error(f"❌ 充值失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/users/reset-password', methods=['POST'])
@admin_required
def reset_user_password():
    """重置用户密码"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': '缺少用户ID'}), 400
        
        # 检查用户是否存在
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        # 重置密码为123456
        result = user_model.reset_password(user_id, '123456')
        
        if result['success']:
            logger.info(f"✅ 管理员重置用户 {user_id} 密码")
            return jsonify({
                'success': True,
                'message': '密码已重置为 123456'
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', '重置失败')}), 500
            
    except Exception as e:
        logger.error(f"❌ 重置密码失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/users/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status():
    """切换用户状态（启用/禁用）"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        is_active = data.get('is_active')
        
        if not user_id or is_active is None:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        # 检查用户是否存在
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        # 不能禁用管理员
        if user.get('is_admin') and not is_active:
            return jsonify({'success': False, 'error': '不能禁用管理员账户'}), 403
        
        # 更新状态
        result = user_model.update_user_status(user_id, is_active)
        
        if result['success']:
            status_text = "启用" if is_active else "禁用"
            logger.info(f"✅ 管理员{status_text}用户 {user_id}")
            return jsonify({
                'success': True,
                'message': f'用户已{status_text}'
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', '操作失败')}), 500
            
    except Exception as e:
        logger.error(f"❌ 切换用户状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/users/delete', methods=['POST'])
@admin_required
def delete_user():
    """删除用户"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': '缺少用户ID'}), 400
        
        # 检查用户是否存在
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        # 不能删除管理员
        if user.get('is_admin'):
            return jsonify({'success': False, 'error': '不能删除管理员账户'}), 403
        
        # 删除用户
        result = user_model.delete_user(user_id)
        
        if result['success']:
            logger.info(f"✅ 管理员删除用户 {user_id}")
            return jsonify({
                'success': True,
                'message': '用户已删除'
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', '删除失败')}), 500
            
    except Exception as e:
        logger.error(f"❌ 删除用户失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
