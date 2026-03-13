"""
管理员API - 用户管理等功能
"""
from flask import Blueprint, request, jsonify, session, send_file, current_app
from functools import wraps
from datetime import datetime
from web.models.user_model import user_model
from web.models.point_model import point_model
from web.web_config import logger
from src.utils.logger import Logger

admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


def verify_admin_password(password: str) -> bool:
    """验证管理员密码
    
    Args:
        password: 管理员输入的二次验证密码
    
    Returns:
        bool: 验证是否通过
    """
    logger.info(f"🔐 开始二次验证 - session: {dict(session)}")
    
    if not password:
        logger.warning("❌ 二次验证失败: 密码为空")
        return False
    
    # 获取当前登录的管理员用户名
    admin_username = session.get('username')
    if not admin_username:
        logger.warning("❌ 二次验证失败: session中没有username")
        return False
    
    logger.info(f"🔐 验证管理员: {admin_username}")
    
    # 验证密码
    try:
        admin_user = user_model.verify_user(admin_username, password)
        logger.info(f"🔐 verify_user结果: {admin_user is not None}")
        if admin_user:
            logger.info(f"🔐 用户is_admin: {admin_user.get('is_admin')}")
        return admin_user is not None and admin_user.get('is_admin')
    except Exception as e:
        logger.error(f"❌ 二次验证异常: {e}")
        return False


@admin_api.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """获取所有用户列表（包含点数信息）"""
    try:
        users = user_model.get_all_users()
        # 为每个用户添加点数信息
        for user in users:
            points_info = point_model.get_user_points(user['id'])
            user['points'] = points_info['balance']
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
        password = data.get('password')
        
        # 二次验证：验证管理员密码
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
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
        password = data.get('password')
        
        # 二次验证：验证管理员密码
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
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
        password = data.get('password')
        
        # 二次验证：验证管理员密码
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
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
        password = data.get('password')
        
        # 二次验证：验证管理员密码
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
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


# ==================== 日志管理 API ====================

@admin_api.route('/logs', methods=['GET'])
@admin_required
def list_logs():
    """获取日志文件列表"""
    try:
        log_files = Logger.list_log_files()
        return jsonify({
            'success': True,
            'data': log_files,
            'log_dir': str(Logger.get_log_dir()) if Logger.get_log_dir() else None
        })
    except Exception as e:
        logger.error(f"❌ 获取日志列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/logs/<filename>', methods=['GET'])
@admin_required
def get_log_content(filename):
    """获取日志文件内容"""
    try:
        # 获取分页参数
        limit = request.args.get('limit', 1000, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 读取日志内容
        lines, total_lines = Logger.read_log_file(filename, limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'lines': lines,
                'total_lines': total_lines,
                'offset': offset,
                'limit': limit,
                'has_more': (offset + len(lines)) < total_lines
            }
        })
    except Exception as e:
        logger.error(f"❌ 获取日志内容失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/logs/<filename>/search', methods=['GET'])
@admin_required
def search_log_content(filename):
    """搜索日志内容"""
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 100, type=int)
        
        if not keyword:
            return jsonify({'success': False, 'error': '请提供搜索关键词'}), 400
        
        results = Logger.search_log(filename, keyword, limit=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'keyword': keyword,
                'results': results,
                'count': len(results)
            }
        })
    except Exception as e:
        logger.error(f"❌ 搜索日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/logs/<filename>/download', methods=['GET'])
@admin_required
def download_log(filename):
    """下载日志文件"""
    try:
        log_dir = Logger.get_log_dir()
        if not log_dir:
            return jsonify({'success': False, 'error': '日志目录未配置'}), 500
        
        file_path = log_dir / filename
        
        # 安全检查：确保文件在日志目录内
        if not str(file_path.resolve()).startswith(str(log_dir.resolve())):
            return jsonify({'success': False, 'error': '非法的文件路径'}), 403
        
        if not file_path.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        return send_file(
            file_path,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"❌ 下载日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/logs/clean', methods=['POST'])
@admin_required
def clean_logs():
    """清理旧日志"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)  # 默认保留30天
        password = data.get('password')
        
        # 二次验证
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
        deleted_count = Logger.clean_old_logs(days=days)
        
        logger.info(f"✅ 管理员清理日志: 删除 {deleted_count} 个文件，保留 {days} 天")
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 个旧日志文件',
            'data': {
                'deleted_count': deleted_count,
                'keep_days': days
            }
        })
    except Exception as e:
        logger.error(f"❌ 清理日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/logs/current', methods=['GET'])
@admin_required
def get_current_log_info():
    """获取当前日志信息"""
    try:
        log_file = Logger.get_log_file_path()
        log_dir = Logger.get_log_dir()
        
        # 获取当前日志的统计信息
        stats = {
            'current_file': str(log_file) if log_file else None,
            'log_dir': str(log_dir) if log_dir else None,
            'file_logging_enabled': Logger._use_file
        }
        
        if log_file and log_file.exists():
            stat = log_file.stat()
            stats['size'] = stat.st_size
            stats['size_formatted'] = Logger._format_file_size(stat.st_size)
            stats['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"❌ 获取当前日志信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 生成任务监控 API ====================

@admin_api.route('/generation-tasks', methods=['GET'])
@admin_required
def get_generation_tasks():
    """获取所有生成任务状态"""
    try:
        # 🔥 修复：使用正在运行的全局管理器实例
        manager = current_app.config.get('MANAGER')
        if not manager:
            return jsonify({'success': False, 'error': '管理器未初始化'}), 500
        
        all_tasks = manager.get_all_tasks()
        logger.info(f"[ADMIN] 获取所有任务: {len(all_tasks)} 个")
        
        # 分类任务状态
        active_tasks = []
        completed_tasks = []
        failed_tasks = []
        
        for task in all_tasks:
            task_info = {
                'task_id': task.get('task_id', ''),
                'status': task.get('status', 'unknown'),
                'progress': task.get('progress', 0),
                'created_at': task.get('created_at', ''),
                'updated_at': task.get('updated_at', ''),
                'current_step': task.get('current_step', ''),
                'points_consumed': task.get('points_consumed', 0),
                'generation_mode': task.get('generation_mode', 'full'),
                'from_chapter': task.get('from_chapter'),
                'chapters_to_generate': task.get('chapters_to_generate'),
                'novel_title': task.get('novel_title', '未命名'),
                'error': task.get('error', '')
            }
            
            # 根据状态分类
            status = task.get('status', '').lower()
            if status in ['completed', 'success']:
                completed_tasks.append(task_info)
            elif status in ['failed', 'error', 'cancelled']:
                failed_tasks.append(task_info)
            else:
                # 进行中的任务
                active_tasks.append(task_info)
        
        # 按时间倒序排列
        active_tasks.sort(key=lambda x: x['updated_at'], reverse=True)
        completed_tasks.sort(key=lambda x: x['updated_at'], reverse=True)
        failed_tasks.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'active': active_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'summary': {
                    'total': len(all_tasks),
                    'active_count': len(active_tasks),
                    'completed_count': len(completed_tasks),
                    'failed_count': len(failed_tasks)
                }
            }
        })
    except Exception as e:
        logger.error(f"❌ 获取生成任务失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/generation-tasks/<task_id>/stop', methods=['POST'])
@admin_required
def stop_generation_task(task_id):
    """停止生成任务"""
    try:
        data = request.get_json() or {}
        password = data.get('password')
        
        # 二次验证
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
        # 🔥 修复：使用正在运行的全局管理器实例
        manager = current_app.config.get('MANAGER')
        if not manager:
            return jsonify({'success': False, 'error': '管理器未初始化'}), 500
        
        # 获取任务状态
        task = manager.get_task_status(task_id)
        if 'error' in task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 更新任务状态为已取消
        manager._update_task_status(task_id, 'cancelled', task.get('progress', 0), error='管理员手动停止')
        
        logger.info(f"✅ 管理员停止任务: {task_id}")
        
        return jsonify({
            'success': True,
            'message': '任务已停止'
        })
    except Exception as e:
        logger.error(f"❌ 停止任务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/generation-tasks/stop-all', methods=['POST'])
@admin_required
def stop_all_generation_tasks():
    """停止所有进行中的生成任务"""
    try:
        data = request.get_json() or {}
        password = data.get('password')
        
        # 二次验证
        if not verify_admin_password(password):
            return jsonify({'success': False, 'error': '管理员密码验证失败'}), 403
        
        # 🔥 修复：使用正在运行的全局管理器实例
        manager = current_app.config.get('MANAGER')
        if not manager:
            return jsonify({'success': False, 'error': '管理器未初始化'}), 500
        
        # 获取所有任务
        all_tasks = manager.get_all_tasks()
        stopped_count = 0
        
        for task in all_tasks:
            status = task.get('status', '').lower()
            if status not in ['completed', 'success', 'failed', 'error', 'cancelled']:
                task_id = task.get('task_id')
                manager._update_task_status(
                    task_id, 
                    'cancelled', 
                    task.get('progress', 0), 
                    error='管理员停止所有任务'
                )
                stopped_count += 1
        
        logger.info(f"✅ 管理员停止所有任务: {stopped_count} 个")
        
        return jsonify({
            'success': True,
            'message': f'已停止 {stopped_count} 个进行中的任务'
        })
    except Exception as e:
        logger.error(f"❌ 停止所有任务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api.route('/system-status', methods=['GET'])
@admin_required
def get_system_status():
    """获取系统运行状态"""
    try:
        import psutil
        import threading
        
        # 获取CPU和内存使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取线程信息
        thread_count = threading.active_count()
        
        # 🔥 修复：使用正在运行的全局管理器实例
        manager = current_app.config.get('MANAGER')
        if manager:
            all_tasks = manager.get_all_tasks()
        else:
            all_tasks = []
        
        active_generations = sum(1 for t in all_tasks 
                                if t.get('status', '').lower() 
                                not in ['completed', 'success', 'failed', 'error', 'cancelled'])
        
        return jsonify({
            'success': True,
            'data': {
                'cpu': {
                    'percent': cpu_percent,
                    'cores': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'threads': thread_count,
                'active_generations': active_generations
            }
        })
    except Exception as e:
        logger.error(f"❌ 获取系统状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
