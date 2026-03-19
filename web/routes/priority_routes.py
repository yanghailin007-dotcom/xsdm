"""
端点优先级管理路由
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from pathlib import Path
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.endpoint_utils import (
    get_enabled_endpoints, 
    get_enabled_providers,
    get_enabled_provider_priority,
    get_default_provider
)

priority_api = Blueprint('priority_api', __name__)

def register_priority_routes(app):
    """注册优先级管理路由"""
    app.register_blueprint(priority_api)
    print("✅ 优先级管理路由已注册")

DATA_DIR = Path("data")
PRIORITY_DIR = DATA_DIR / "endpoint_priorities"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_user_priority_file(user_id):
    """获取用户优先级配置文件路径"""
    PRIORITY_DIR.mkdir(parents=True, exist_ok=True)
    return PRIORITY_DIR / f"{user_id}.json"


@priority_api.route('/api/endpoint-priority', methods=['POST'])
@login_required
def save_endpoint_priority():
    """保存端点优先级"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        priority = data.get('priority')
        
        if not endpoint or priority is None:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        user_id = session.get('user_id', 'default')
        priority_file = get_user_priority_file(user_id)
        
        # 读取现有配置
        priorities = {}
        if priority_file.exists():
            with open(priority_file, 'r', encoding='utf-8') as f:
                priorities = json.load(f)
        
        # 更新优先级
        priorities[endpoint] = int(priority)
        
        # 保存
        with open(priority_file, 'w', encoding='utf-8') as f:
            json.dump(priorities, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True, 
            'message': f'端点 {endpoint} 优先级已设置为 {priority}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@priority_api.route('/api/endpoint-priority', methods=['GET'])
@login_required
def get_endpoint_priorities():
    """获取所有端点优先级"""
    try:
        user_id = session.get('user_id', 'default')
        priority_file = get_user_priority_file(user_id)
        
        priorities = {}
        if priority_file.exists():
            with open(priority_file, 'r', encoding='utf-8') as f:
                priorities = json.load(f)
        
        # 默认值（数字越小优先级越高：1=最高，5=最低）
        defaults = {
            'lemon-api': 3,        # 低优先级
            'aiberm': 1,           # 最高优先级
            'xiaochuang-backup': 2, # 中等优先级
            'deepseek-official': 1,  # 最高优先级
            'kimi-k2.5-primary': 1   # 最高优先级（但受 enabled 字段控制）
        }
        
        # 合并默认值和用户设置
        for ep, default_priority in defaults.items():
            if ep not in priorities:
                priorities[ep] = default_priority
        
        return jsonify({'success': True, 'priorities': priorities})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@priority_api.route('/api/endpoints/enabled', methods=['GET'])
def get_enabled_endpoints_api():
    """获取启用的端点配置（供前端 UI 使用）"""
    try:
        # 获取启用的端点
        endpoints = get_enabled_endpoints()
        providers = get_enabled_providers()
        priority = get_enabled_provider_priority()
        default_provider = get_default_provider()
        
        return jsonify({
            'success': True,
            'endpoints': endpoints,
            'providers': providers,
            'provider_priority': priority,
            'default_provider': default_provider
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
