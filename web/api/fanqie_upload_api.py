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
        logger.warning(f"[番茄上传] Chrome 未连接，无法上传")
        return jsonify({
            'success': False, 
            'error': 'Chrome 未连接',
            'message': '请先启动 Chrome 浏览器，并确保已点击"检测连接"'
        }), 400
    
    try:
        from web.web_config import logger
        logger.info(f"[番茄上传] 开始上传小说: {novel_title}, 用户: {user_id}")
        
        # 导入上传核心逻辑
        try:
            from novel_publisher import NovelPublisher
            from config_loader import ConfigLoader
            logger.info("[番茄上传] 导入上传模块成功")
        except Exception as import_err:
            logger.error(f"[番茄上传] 导入模块失败: {import_err}")
            return jsonify({
                'success': False,
                'error': f'导入上传模块失败: {str(import_err)}'
            }), 500
        
        from playwright.sync_api import sync_playwright
        
        # 连接 Chrome
        logger.info("[番茄上传] 连接 Chrome...")
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{DEBUG_PORT}')
        
        # 获取页面
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
            logger.info(f"[番茄上传] 使用现有页面: {page.url}")
        else:
            page = browser.new_page()
            logger.info("[番茄上传] 创建新页面")
        
        # 创建上传器实例
        config_loader = ConfigLoader()
        publisher = NovelPublisher(config_loader)
        
        # 查找小说项目文件
        novel_file = find_novel_file(novel_title, user_id)
        if not novel_file:
            logger.error(f"[番茄上传] 未找到小说文件: {novel_title}")
            browser.close()
            playwright.stop()
            return jsonify({
                'success': False,
                'error': '未找到小说项目文件',
                'message': f'在目录中未找到 {novel_title} 的项目文件'
            }), 404
        
        logger.info(f"[番茄上传] 找到小说文件: {novel_file}")
        
        # 执行上传
        logger.info("[番茄上传] 开始执行 publish_novel...")
        result = publisher.publish_novel(page, novel_file)
        logger.info(f"[番茄上传] 上传结果: {result}")
        
        browser.close()
        playwright.stop()
        
        return jsonify({
            'success': result,
            'message': '上传完成' if result else '上传失败，请检查 Chrome 页面状态'
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        from web.web_config import logger
        logger.error(f"[番茄上传] 上传过程出错: {e}\n{error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'上传过程出错: {str(e)}'
        }), 500


def find_novel_file(novel_title: str, user_id: int) -> Optional[str]:
    """查找小说项目文件路径"""
    from web.utils.path_utils import get_user_novel_dir, find_novel_project, NOVEL_PROJECTS_ROOT
    from web.database import get_db_connection
    
    # 先获取用户名
    username = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            username = row[0]
        conn.close()
    except Exception as e:
        from web.web_config import logger
        logger.warning(f"[查找小说] 获取用户名失败: {e}")
    
    # 使用通用查找函数（优先用户名，后备 user_id）
    search_names = [n for n in [username, str(user_id)] if n]
    
    for name in search_names:
        project_dir = find_novel_project(novel_title, name)
        if project_dir and project_dir.exists():
            # 查找项目信息文件
            info_file = project_dir / "项目信息.json"
            if info_file.exists():
                return str(info_file)
            # 备选：查找其他 JSON 文件
            json_files = list(project_dir.glob("*.json"))
            if json_files:
                return str(json_files[0])
    
    # 兜底：尝试在项目根目录查找（兼容旧路径）
    safe_title = novel_title.replace('/', '_').replace('\\', '_')
    legacy_project = NOVEL_PROJECTS_ROOT / safe_title
    if legacy_project.exists():
        info_file = legacy_project / "项目信息.json"
        if info_file.exists():
            return str(info_file)
        json_files = list(legacy_project.glob("*.json"))
        if json_files:
            return str(json_files[0])
    
    return None


def find_novel_file_legacy(novel_title: str, user_id: int) -> Optional[str]:
    """查找小说项目文件路径（旧方法，用于调试）"""
    from web.utils.path_utils import get_user_novel_dir
    
    # 尝试用户名或 user_id 作为目录名
    for username in [str(user_id)]:
        user_dir = get_user_novel_dir(username)
        project_dir = user_dir / novel_title
        
        if project_dir.exists():
            info_file = project_dir / "项目信息.json"
            if info_file.exists():
                return str(info_file)
            json_files = list(project_dir.glob("*.json"))
            if json_files:
                return str(json_files[0])
    
    return None
