"""
自定义API端点管理路由
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps

# 导入自定义端点管理器
try:
    from web.managers.custom_endpoint_manager import custom_endpoint_manager, DEMO_ENDPOINT
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from web.managers.custom_endpoint_manager import custom_endpoint_manager, DEMO_ENDPOINT

# 创建蓝图
custom_endpoint_bp = Blueprint('custom_endpoint', __name__, url_prefix='/api/custom-endpoints')


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


@custom_endpoint_bp.route('', methods=['GET'])
@login_required
def get_endpoints():
    """获取所有自定义端点"""
    try:
        endpoints = custom_endpoint_manager.get_formatted_endpoints()
        return jsonify({
            'success': True,
            'data': endpoints
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('/demo', methods=['GET'])
@login_required
def get_demo():
    """获取Demo格式示例"""
    return jsonify({
        'success': True,
        'data': DEMO_ENDPOINT
    })


@custom_endpoint_bp.route('/status', methods=['GET'])
@login_required
def get_custom_endpoint_status():
    """获取用户自定义端点状态（用于前端提示）"""
    try:
        endpoints = custom_endpoint_manager.get_formatted_endpoints()
        enabled_endpoints = [ep for ep in endpoints if ep.get('enabled', True)]
        
        if enabled_endpoints:
            endpoint_names = [ep.get('name', 'unnamed') for ep in enabled_endpoints]
            discount_rates = [ep.get('discount', 50) for ep in enabled_endpoints]
            avg_discount = sum(discount_rates) / len(discount_rates)
            
            return jsonify({
                'success': True,
                'data': {
                    'has_custom_endpoints': True,
                    'endpoint_count': len(enabled_endpoints),
                    'endpoint_names': endpoint_names,
                    'avg_discount_rate': avg_discount,
                    'message': f"检测到您配置了自己的模型({', '.join(endpoint_names)})，系统将只使用您的模型进行生成",
                    'note': "如需使用系统模型，请删除或禁用您的自定义端点"
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'has_custom_endpoints': False,
                    'message': "未配置自定义模型，将使用系统默认模型"
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('', methods=['POST'])
@login_required
def add_endpoint():
    """添加自定义端点"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        success, message = custom_endpoint_manager.add_endpoint(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('/<name>', methods=['PUT'])
@login_required
def update_endpoint(name):
    """更新自定义端点"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        success, message = custom_endpoint_manager.update_endpoint(name, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('/<name>', methods=['DELETE'])
@login_required
def delete_endpoint(name):
    """删除自定义端点"""
    try:
        success, message = custom_endpoint_manager.delete_endpoint(name)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('/<name>/toggle', methods=['POST'])
@login_required
def toggle_endpoint(name):
    """切换端点启用状态"""
    try:
        success, message = custom_endpoint_manager.toggle_endpoint(name)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@custom_endpoint_bp.route('/<name>/priority', methods=['PUT'])
@login_required
def update_custom_endpoint_priority(name):
    """更新自定义端点优先级"""
    try:
        data = request.get_json()
        priority = data.get('priority')
        
        if priority is None:
            return jsonify({'success': False, 'error': '缺少优先级参数'}), 400
        
        # 限制范围 1-5
        priority = max(1, min(5, int(priority)))
        
        success, message = custom_endpoint_manager.update_endpoint(name, {'priority': priority})
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'端点 {name} 优先级已设置为 {priority}'
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def register_custom_endpoint_routes(app):
    """注册自定义端点路由"""
    app.register_blueprint(custom_endpoint_bp)
    print("✅ 自定义端点路由已注册")
