"""
本地上传任务 API
用于接收用户本地脚本上传进度的上报
"""
import os
import sys
import uuid
import json
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 添加模型到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

local_upload_api = Blueprint('local_upload_api', __name__, url_prefix='/api/local-upload')


def get_upload_task_model():
    """获取上传任务模型实例（延迟导入）"""
    from web.models.upload_task_model import UploadTaskModel
    return UploadTaskModel()


@local_upload_api.route('/tasks', methods=['POST'])
def create_task():
    """创建上传任务"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        if not data.get('novel_title'):
            return jsonify({'success': False, 'error': '小说标题不能为空'}), 400
        
        # 生成任务ID
        task_id = f"UL{uuid.uuid4().hex[:16].upper()}"  # UL = Upload Local
        
        # 获取用户信息（从 token 或 session）
        user_id = data.get('user_id')
        if not user_id and 'user_id' in session:
            user_id = session['user_id']
        
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        # 创建任务
        model = get_upload_task_model()
        success = model.create_task(
            task_id=task_id,
            user_id=user_id,
            novel_title=data['novel_title'],
            novel_id=data.get('novel_id'),
            total_chapters=data.get('total_chapters', 0),
            platform=data.get('platform', 'fanqie'),
            client_info=json.dumps(data.get('client_info', {}), ensure_ascii=False)
        )
        
        if not success:
            return jsonify({'success': False, 'error': '创建任务失败'}), 500
        
        # 如果有章节信息，批量创建章节
        if data.get('chapters'):
            model.create_chapters(task_id, data['chapters'])
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '任务创建成功'
        })
        
    except Exception as e:
        print(f"[LocalUploadAPI] 创建任务错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/report', methods=['POST'])
def report_progress():
    """接收上传进度上报"""
    try:
        data = request.get_json()
        
        task_id = data.get('task_id')
        chapter_number = data.get('chapter_number')
        status = data.get('status')  # uploading, success, failed
        
        if not task_id or chapter_number is None or not status:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        model = get_upload_task_model()
        
        # 更新章节状态
        error_message = data.get('error_message')
        success = model.update_chapter_status(
            task_id=task_id,
            chapter_number=chapter_number,
            status=status,
            error_message=error_message
        )
        
        if not success:
            return jsonify({'success': False, 'error': '更新状态失败'}), 500
        
        # 如果是失败状态，记录详细错误信息
        if status == 'failed' and data.get('error_detail'):
            model.add_error_log(task_id, {
                'chapter_number': chapter_number,
                'chapter_title': data.get('chapter_title', ''),
                'error_type': data.get('error_type', 'unknown'),
                'error_message': error_message,
                'error_detail': data.get('error_detail'),
                'screenshot_path': data.get('screenshot_path'),
                'page_url': data.get('page_url'),
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({'success': True, 'message': '上报成功'})
        
    except Exception as e:
        print(f"[LocalUploadAPI] 上报进度错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """获取任务详情和进度"""
    try:
        model = get_upload_task_model()
        
        # 获取任务信息
        task = model.get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 权限检查
        user_id = session.get('user_id')
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'error': '无权访问'}), 403
        
        # 获取章节详情
        chapters = model.get_task_chapters(task_id)
        
        return jsonify({
            'success': True,
            'task': task,
            'chapters': chapters
        })
        
    except Exception as e:
        print(f"[LocalUploadAPI] 获取任务错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/tasks', methods=['GET'])
def get_user_tasks():
    """获取当前用户的任务列表"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        limit = request.args.get('limit', 20, type=int)
        
        model = get_upload_task_model()
        tasks = model.get_user_tasks(user_id, limit)
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
        
    except Exception as e:
        print(f"[LocalUploadAPI] 获取任务列表错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/tasks/<task_id>/retry', methods=['POST'])
def get_retry_chapters(task_id: str):
    """获取需要重试的章节（失败且重试次数<3）"""
    try:
        model = get_upload_task_model()
        
        # 验证任务归属
        task = model.get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        user_id = session.get('user_id')
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'error': '无权访问'}), 403
        
        # 获取失败章节
        failed_chapters = model.get_failed_chapters(task_id)
        
        # 过滤重试次数过多的
        retry_chapters = [
            ch for ch in failed_chapters 
            if ch['retry_count'] < 3
        ]
        
        return jsonify({
            'success': True,
            'chapters': retry_chapters,
            'total_failed': len(failed_chapters),
            'can_retry': len(retry_chapters)
        })
        
    except Exception as e:
        print(f"[LocalUploadAPI] 获取重试章节错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/generate-script', methods=['POST'])
def generate_upload_script():
    """
    生成上传脚本包
    返回包含脚本和小说数据的打包下载
    """
    try:
        data = request.get_json()
        
        novel_title = data.get('novel_title')
        if not novel_title:
            return jsonify({'success': False, 'error': '小说标题不能为空'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        # 获取小说章节数据（这里简化，实际应从数据库或文件读取）
        chapters = data.get('chapters', [])
        if not chapters:
            return jsonify({'success': False, 'error': '没有章节数据'}), 400
        
        # 创建任务
        task_id = f"UL{uuid.uuid4().hex[:16].upper()}"
        
        model = get_upload_task_model()
        model.create_task(
            task_id=task_id,
            user_id=user_id,
            novel_title=novel_title,
            novel_id=data.get('novel_id'),
            total_chapters=len(chapters),
            platform=data.get('platform', 'fanqie')
        )
        
        # 创建章节记录
        model.create_chapters(task_id, chapters)
        
        # 生成脚本包
        from web.services.script_generator import ScriptGenerator
        
        # 获取用户token（这里简化处理，实际应生成临时token）
        from web.jwt_auth import generate_token
        user_token = generate_token({'user_id': user_id}, token_type='upload')
        
        generator = ScriptGenerator(api_base_url=request.host_url.rstrip('/'))
        
        novel_info = {
            'title': novel_title,
            'id': data.get('novel_id', '')
        }
        
        result = generator.create_upload_package(
            task_id=task_id,
            user_token=user_token,
            novel_info=novel_info,
            chapters=chapters,
            platform=data.get('platform', 'fanqie')
        )
        
        if not result['success']:
            return jsonify({'success': False, 'error': result.get('error', '生成失败')}), 500
        
        # 返回下载链接（临时文件，需要定期清理）
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '脚本生成成功',
            'download_url': f'/api/local-upload/download-script/{task_id}'
        })
        
    except Exception as e:
        print(f"[LocalUploadAPI] 生成脚本错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@local_upload_api.route('/download-script/<task_id>', methods=['GET'])
def download_script(task_id: str):
    """下载上传脚本包"""
    try:
        # 查找生成的包（这里简化，实际应从存储中获取）
        # TODO: 实现安全的文件下载
        return jsonify({'success': False, 'error': '开发中'}), 501
        
    except Exception as e:
        print(f"[LocalUploadAPI] 下载脚本错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
