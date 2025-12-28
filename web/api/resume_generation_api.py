"""
恢复生成API - 支持中断后恢复
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from pathlib import Path
import sys
import os

# 创建蓝图
resume_api = Blueprint('resume_api', __name__)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger
from web.managers.resumable_novel_manager import ResumableNovelGenerationManager

logger = get_logger(__name__)

# 初始化管理器
try:
    manager = ResumableNovelGenerationManager()
except Exception as e:
    logger.error(f"无法初始化ResumableNovelGenerationManager: {e}")
    manager = None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


@resume_api.route('/resumable-tasks', methods=['GET'])
@login_required
def get_resumable_tasks():
    """获取所有可恢复的任务列表"""
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        tasks = manager.get_resumable_tasks()
        
        logger.info(f"✅ 获取可恢复任务列表: {len(tasks)} 个任务")
        
        return jsonify({
            "success": True,
            "tasks": tasks,
            "total": len(tasks)
        })
        
    except Exception as e:
        logger.error(f"❌ 获取可恢复任务列表失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@resume_api.route('/resumable-tasks/<title>', methods=['GET'])
@login_required
def get_resume_info(title):
    """获取特定任务的恢复信息"""
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        resume_info = manager.get_resume_info(title)
        
        if not resume_info:
            return jsonify({
                "success": False,
                "error": "任务不存在或没有可用的检查点"
            }), 404
        
        logger.info(f"✅ 获取恢复信息: {title}")
        
        return jsonify({
            "success": True,
            "resume_info": resume_info
        })
        
    except Exception as e:
        logger.error(f"❌ 获取恢复信息失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@resume_api.route('/generation/resume', methods=['POST'])
@login_required
def resume_generation():
    """从检查点恢复生成"""
    try:
        data = request.json or {}
        
        title = data.get('title')
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        logger.info(f"🔄 恢复生成任务: {title}")
        
        # 启动恢复模式
        def progress_callback(progress_info):
            """进度回调函数"""
            logger.info(f"  进度: {progress_info['progress']}% - {progress_info['current_step']}")
        
        # 构建生成参数（从检查点恢复）
        generation_params = {
            'title': title,
            'resume_mode': True
        }
        
        task_id = manager.start_generation_with_resume(
            generation_params=generation_params,
            resume_mode=True,
            progress_callback=progress_callback
        )
        
        logger.info(f"✅ 恢复任务已启动: {task_id}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "生成任务已恢复",
            "resume_info": manager.get_resume_info(title)
        })
        
    except Exception as e:
        logger.error(f"❌ 恢复生成失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@resume_api.route('/generation/checkpoint/delete', methods=['POST'])
@login_required
def delete_checkpoint():
    """删除检查点（完成任务后调用）"""
    try:
        data = request.json or {}
        
        title = data.get('title')
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        success = manager.delete_checkpoint(title)
        
        if success:
            logger.info(f"✅ 检查点已删除: {title}")
            return jsonify({
                "success": True,
                "message": "检查点已删除"
            })
        else:
            return jsonify({
                "success": False,
                "error": "删除检查点失败"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ 删除检查点失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@resume_api.route('/generation/start-with-resume-option', methods=['POST'])
@login_required
def start_generation_with_resume_option():
    """启动生成任务（带恢复选项）"""
    try:
        data = request.json or {}
        
        title = data.get('title')
        resume_if_available = data.get('resume_if_available', False)
        
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 检查是否有可用的检查点
        has_checkpoint = manager.get_resume_info(title) is not None
        
        if has_checkpoint and resume_if_available:
            # 恢复模式
            logger.info(f"🔄 检测到检查点，使用恢复模式: {title}")
            generation_params = {
                'title': title,
                'resume_mode': True
            }
            resume_mode = True
        else:
            # 新任务
            if has_checkpoint and not resume_if_available:
                logger.info(f"⚠️ 检测到检查点但用户选择重新开始: {title}")
            else:
                logger.info(f"🚀 启动新任务: {title}")
            
            # 获取完整的生成参数
            generation_params = {
                'title': title,
                'synopsis': data.get('synopsis', ''),
                'core_setting': data.get('core_setting', ''),
                'core_selling_points': data.get('core_selling_points', []),
                'total_chapters': data.get('total_chapters', 200),
                'generation_mode': data.get('generation_mode', 'phase_one_only'),
                'creative_seed': data.get('creative_seed')
            }
            resume_mode = False
        
        # 启动任务
        task_id = manager.start_generation_with_resume(
            generation_params=generation_params,
            resume_mode=resume_mode
        )
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "resume_mode": resume_mode,
            "message": "恢复模式启动" if resume_mode else "新任务启动"
        })
        
    except Exception as e:
        logger.error(f"❌ 启动生成失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def register_resume_routes(app):
    """注册恢复生成API路由"""
    app.register_blueprint(resume_api, url_prefix='/api')
    
    logger.info("=" * 60)
    logger.info("📋 已注册的恢复生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'resumable' in rule.rule or 'resume' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    logger.info("恢复生成API路由注册完成")