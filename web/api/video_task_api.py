"""
视频生成任务管理API

功能：
- 创建和管理视频生成任务
- 支持任务提交、启动、暂停、恢复、取消
- 支持批量生成和单个生成
- 任务优先级管理
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import asyncio
from typing import Dict, List
from datetime import datetime

# 创建蓝图
video_task_api = Blueprint('video_task_api', __name__)

# 导入日志
from src.utils.logger import get_logger
logger = get_logger(__name__)

# 全局调度器实例
_scheduler = None
_workers = []


def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_scheduler():
    """获取或创建调度器"""
    global _scheduler
    if _scheduler is None:
        from src.schedulers.video_task_scheduler import VideoTaskScheduler
        _scheduler = VideoTaskScheduler(max_concurrent=3)
        logger.info("✅ 创建任务调度器")
    return _scheduler


def get_workers(count: int = 3):
    """获取或创建Worker"""
    global _workers
    if not _workers:
        from src.workers.video_worker import VideoWorker
        scheduler = get_scheduler()
        for i in range(count):
            worker = VideoWorker(worker_id=f"worker_{i}", scheduler=scheduler)
            _workers.append(worker)
            # 在后台启动Worker
            asyncio.create_task(worker.start())
        logger.info(f"✅ 创建 {count} 个Worker")
    return _workers


def run_async(coro):
    """在同步环境中运行异步函数"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@video_task_api.route('/video/tasks', methods=['POST'])
@login_required
def create_task():
    """
    创建视频生成任务
    
    请求参数：
    {
        "project_id": "项目ID",
        "shots": [
            {
                "shot_index": 0,
                "shot_type": "中景",
                "camera_movement": "固定",
                "duration_seconds": 10.0,
                "description": "场景描述",
                "generation_prompt": "生成提示词",
                "audio_prompt": "音频提示词"
            }
        ],
        "config": {
            "max_concurrent": 3,
            "auto_start": true
        }
    }
    """
    try:
        data = request.json or {}
        project_id = data.get('project_id')
        shots = data.get('shots', [])
        config = data.get('config', {})
        
        if not project_id:
            return jsonify({"success": False, "error": "项目ID不能为空"}), 400
        
        if not shots:
            return jsonify({"success": False, "error": "镜头列表不能为空"}), 400
        
        logger.info(f"📋 创建任务: project_id={project_id}, shots={len(shots)}")
        
        # 获取调度器
        scheduler = get_scheduler()
        
        # 提交任务
        task_id = run_async(scheduler.submit_task(shots, project_id, config))
        
        # 如果配置了自动启动，则启动任务
        if config.get('auto_start', False):
            run_async(_start_task_internal(scheduler, task_id))
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"任务创建成功，包含 {len(shots)} 个镜头"
        })
        
    except Exception as e:
        logger.error(f"❌ 创建任务失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


async def _start_task_internal(scheduler, task_id: str):
    """内部启动任务函数"""
    task = await scheduler.load_task(task_id)
    if task:
        from src.models.video_task_models import TaskStatus
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        await scheduler.task_queue.put(task_id)


@video_task_api.route('/video/tasks/<task_id>/start', methods=['POST'])
@login_required
def start_task(task_id: str):
    """启动任务"""
    try:
        logger.info(f"🚀 启动任务: {task_id}")
        
        # 获取调度器和Worker
        scheduler = get_scheduler()
        workers = get_workers()
        
        run_async(_start_task_internal(scheduler, task_id))
        
        return jsonify({
            "success": True,
            "message": "任务已启动"
        })
        
    except Exception as e:
        logger.error(f"❌ 启动任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks/<task_id>/pause', methods=['POST'])
@login_required
def pause_task(task_id: str):
    """暂停任务"""
    try:
        logger.info(f"⏸️  暂停任务: {task_id}")
        
        scheduler = get_scheduler()
        success = run_async(scheduler.pause_task(task_id))
        
        if not success:
            return jsonify({"success": False, "error": "无法暂停任务"}), 400
        
        return jsonify({
            "success": True,
            "message": "任务已暂停"
        })
        
    except Exception as e:
        logger.error(f"❌ 暂停任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks/<task_id>/resume', methods=['POST'])
@login_required
def resume_task(task_id: str):
    """恢复任务"""
    try:
        logger.info(f"▶️  恢复任务: {task_id}")
        
        scheduler = get_scheduler()
        success = run_async(scheduler.resume_task(task_id))
        
        if not success:
            return jsonify({"success": False, "error": "无法恢复任务"}), 400
        
        return jsonify({
            "success": True,
            "message": "任务已恢复"
        })
        
    except Exception as e:
        logger.error(f"❌ 恢复任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks/<task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id: str):
    """取消任务"""
    try:
        logger.info(f"🚫 取消任务: {task_id}")
        
        scheduler = get_scheduler()
        success = run_async(scheduler.cancel_task(task_id))
        
        if not success:
            return jsonify({"success": False, "error": "无法取消任务"}), 400
        
        return jsonify({
            "success": True,
            "message": "任务已取消"
        })
        
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks/<task_id>/status', methods=['GET'])
@login_required
def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        scheduler = get_scheduler()
        status = run_async(scheduler.get_task_status(task_id))
        
        if not status:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks', methods=['GET'])
@login_required
def list_tasks():
    """列出所有任务"""
    try:
        scheduler = get_scheduler()
        tasks = run_async(scheduler.get_all_tasks())
        
        return jsonify({
            "success": True,
            "tasks": tasks,
            "total": len(tasks)
        })
        
    except Exception as e:
        logger.error(f"❌ 列出任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_task_api.route('/video/tasks/<task_id>/retry', methods=['POST'])
@login_required
def retry_failed_shots(task_id: str):
    """重试失败的镜头"""
    try:
        logger.info(f"🔄 重试失败的镜头: {task_id}")
        
        scheduler = get_scheduler()
        task = run_async(scheduler.load_task(task_id))
        
        if not task:
            return jsonify({"success": False, "error": "任务不存在"}), 404
        
        # 导入ShotStatus
        from src.models.video_task_models import ShotStatus
        
        # 找出所有失败的镜头
        failed_shots = task.get_failed_shots()
        
        if not failed_shots:
            return jsonify({"success": False, "error": "没有失败的镜头"}), 400
        
        # 重置失败镜头的状态
        retry_count = 0
        for shot in failed_shots:
            if shot.retry_count < 3:  # 最多重试3次
                shot.status = ShotStatus.PENDING
                shot.error_message = None
                retry_count += 1
        
        # 将任务重新加入队列
        run_async(scheduler.task_queue.put(task_id))
        
        run_async(scheduler._save_task(task))
        
        return jsonify({
            "success": True,
            "message": f"已重置 {retry_count} 个失败的镜头",
            "retry_count": retry_count
        })
        
    except Exception as e:
        logger.error(f"❌ 重试失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def register_video_task_routes(app):
    """注册视频任务API路由"""
    app.register_blueprint(video_task_api, url_prefix='/api')
    
    logger.info("=" * 60)
    logger.info("📋 已注册的视频任务管理API路由:")
    for rule in app.url_map.iter_rules():
        if 'video/tasks' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    logger.info("视频任务管理API路由注册完成")