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
    """获取特定任务的恢复信息 - 支持通过创意标题或实际书名查找"""
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        logger.info(f"🔍 查找检查点: {title}")
        
        # 首先尝试直接查找
        resume_info = manager.get_resume_info(title)
        
        if not resume_info:
            # 如果直接查找失败，尝试通过 creative_title 查找
            logger.info(f"📋 直接查找失败，尝试通过 creative_title 映射查找...")
            all_tasks = manager.get_resumable_tasks()
            
            for task in all_tasks:
                if task.get('creative_title') == title:
                    logger.info(f"✅ 找到映射: {title} -> {task.get('novel_title')}")
                    # 使用实际书名获取信息
                    actual_title = task.get('novel_title')
                    resume_info = manager.get_resume_info(actual_title)
                    if resume_info:
                        # 添加映射信息到响应中
                        resume_info['original_request_title'] = title
                        resume_info['actual_novel_title'] = actual_title
                        break
            
        if not resume_info:
            # 检查项目目录和文件状态，提供更详细的信息
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
             
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
             
            response_data = {
                "success": False,
                "error": "任务不存在或没有可用的检查点",
                "title": title,
                "checkpoint_dir": str(checkpoint_mgr.checkpoint_dir),
                "checkpoint_file": str(checkpoint_mgr.checkpoint_file),
                "dir_exists": checkpoint_mgr.checkpoint_dir.exists(),
                "file_exists": checkpoint_mgr.checkpoint_file.exists()
            }
             
            logger.warn(f"⚠️ 未找到检查点: {title}")
            logger.warn(f"  检查点目录: {response_data['checkpoint_dir']} (存在: {response_data['dir_exists']})")
            logger.warn(f"  检查点文件: {response_data['checkpoint_file']} (存在: {response_data['file_exists']})")
             
            # 如果目录存在但文件不存在，提供额外提示
            if response_data['dir_exists'] and not response_data['file_exists']:
                response_data['hint'] = "项目目录存在，但没有检查点文件。这可能是因为生成过程在创建检查点之前就失败了。"
             
            return jsonify(response_data), 404
        
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
    
    logger.debug("=" * 60)
    logger.debug("📋 已注册的恢复生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'resumable' in rule.rule or 'resume' in rule.rule:
            logger.debug(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.debug("=" * 60)
    logger.debug("恢复生成API路由注册完成")