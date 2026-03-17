"""
番茄小说上传 API
使用 Playwright 连接本地 Chrome 进行自动化上传
"""
import os
import sys
import json
import asyncio
from flask import Blueprint, request, jsonify, session
from functools import wraps
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 添加上传逻辑到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'fanqie_uploader'))

fanqie_upload_api = Blueprint('fanqie_upload_api', __name__, url_prefix='/api/fanqie')

DEBUG_PORT = 9988


def login_required_api(f):
    """API登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g
        from web.jwt_auth import get_token_from_request, decode_token
        
        token = get_token_from_request()
        
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


def check_chrome_status() -> dict:
    """检查本地 Chrome 状态"""
    import requests
    try:
        response = requests.get(
            f'http://127.0.0.1:{DEBUG_PORT}/json/version',
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            return {'running': True, 'version': data.get('Browser', 'Unknown')}
    except:
        pass
    return {'running': False, 'error': 'Chrome not running'}


@fanqie_upload_api.route('/upload/start', methods=['POST'])
@login_required_api
def start_upload():
    """开始上传小说到番茄平台"""
    user_id = request.user_info.get('user_id') if hasattr(request, 'user_info') else session.get('user_id')
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': '请求参数错误'}), 400
    
    novel_title = data.get('novel_title')
    upload_config = data.get('upload_config', {})
    
    if not novel_title:
        return jsonify({'success': False, 'error': '缺少小说标题'}), 400
    
    # 检查 Chrome 连接
    chrome_status = check_chrome_status()
    if not chrome_status['running']:
        return jsonify({
            'success': False, 
            'error': 'Chrome 未连接',
            'message': '请先启动 Chrome 浏览器'
        }), 400
    
    try:
        # 导入上传核心逻辑
        from novel_publisher import NovelPublisher
        from config_loader import ConfigLoader
        from playwright.sync_api import sync_playwright
        
        # 连接 Chrome
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{DEBUG_PORT}')
        
        # 获取页面
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            page = browser.new_page()
        
        # 创建上传器实例
        config_loader = ConfigLoader()
        publisher = NovelPublisher(config_loader)
        
        # 查找小说项目文件
        novel_file = find_novel_file(novel_title, user_id)
        if not novel_file:
            return jsonify({
                'success': False,
                'error': '未找到小说项目文件'
            }), 404
        
        # 执行上传（在后台线程中运行）
        # TODO: 使用异步任务队列处理长时间运行的上传
        result = publisher.publish_novel(page, novel_file)
        
        browser.close()
        playwright.stop()
        
        return jsonify({
            'success': result,
            'message': '上传完成' if result else '上传失败'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'上传过程出错: {str(e)}'
        }), 500


def find_novel_file(novel_title: str, user_id: int) -> Optional[str]:
    """查找小说项目文件路径"""
    from web.utils.path_utils import get_user_novel_dir
    
    user_dir = get_user_novel_dir(user_id)
    project_dir = user_dir / novel_title
    
    # 查找项目信息文件
    info_file = project_dir / "项目信息.json"
    if info_file.exists():
        return str(info_file)
    
    # 备选：查找其他 JSON 文件
    json_files = list(project_dir.glob("*.json"))
    if json_files:
        return str(json_files[0])
    
    return None
