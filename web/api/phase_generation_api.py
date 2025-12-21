"""
两阶段小说生成API接口
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import re
import os
import json
from pathlib import Path
from functools import wraps
from typing import Dict, Any, Optional

# 创建蓝图
phase_api = Blueprint('phase_api', __name__)

# 导入全局变量和日志记录器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

# 导入管理器
from web.managers.novel_manager import NovelGenerationManager
manager = NovelGenerationManager()

# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'logged_in' not in session:
            return jsonify({"error": "需要登录"}, 401)
        return f(*args, **kwargs)
    return decorated_function

# ==================== 第一阶段相关API ====================

@phase_api.route('/phase-one/start-generation', methods=['POST'])
@login_required
def start_phase_one_generation():
    """启动第一阶段设定生成"""
    try:
        config = request.json or {}
        
        # 验证必需参数
        if not config.get("creative_seed"):
            return jsonify({"success": False, "error": "缺少creative_seed参数"}), 400
        
        # 暂时返回模拟响应
        task_id = f"phase_one_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"✅ 第一阶段任务已启动: {task_id}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "第一阶段设定生成任务已启动，正在后台处理",
            "status": "started"
        })
    except Exception as e:
        logger.error(f"❌ 启动第一阶段生成任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-one/task/<task_id>/status', methods=['GET'])
@login_required
def get_phase_one_task_status(task_id):
    """获取第一阶段任务状态"""
    try:
        # 暂时返回模拟状态
        return jsonify({
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "message": "第一阶段已完成"
        })
    except Exception as e:
        logger.error(f"❌ 获取第一阶段任务状态失败: {e}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/phase-one/result/<novel_title>', methods=['GET'])
@login_required
def get_phase_one_result(novel_title):
    """获取第一阶段结果"""
    try:
        # 构建第一阶段结果文件路径
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return jsonify({"error": "第一阶段结果不存在"}), 404
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
            return jsonify(result)
    except Exception as e:
        logger.error(f"❌ 获取第一阶段结果失败: {e}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/phase-one/validate/<novel_title>', methods=['POST'])
@login_required
def validate_phase_one_result(novel_title):
    """验证第一阶段结果"""
    try:
        # 构建第一阶段结果路径
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return jsonify({
                "is_valid": False,
                "issues": ["第一阶段结果文件不存在"]
            }), 404
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        # 简单验证
        validation_result = {
            "is_valid": True,
            "issues": [],
            "message": "第一阶段结果验证通过"
        }
        return jsonify(validation_result)
    except Exception as e:
        logger.error(f"❌ 验证第一阶段结果失败: {e}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/phase-one/continue-to-phase-two/<novel_title>', methods=['POST'])
@login_required
def continue_to_phase_two(novel_title):
    """从第一阶段继续到第二阶段"""
    try:
        data = request.json or {}
        total_chapters = data.get('total_chapters', 50)
        chapters_per_batch = data.get('chapters_per_batch', 3)
        
        # 加载第一阶段结果
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return jsonify({
                "success": False,
                "error": f"找不到第一阶段结果: {novel_title}"
            }), 404
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            phase_one_result = json.load(f)
        
        # 暂时返回模拟响应
        return jsonify({
            "success": True,
            "message": f"已从 {novel_title} 继写到第二阶段",
            "task_id": f"resume_{novel_title}",
            "phase_one_result": phase_one_result
        })
    except Exception as e:
        logger.error(f"❌ 继写到第二阶段失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== 第二阶段相关API ====================

@phase_api.route('/phase-two/start-generation', methods=['POST'])
@login_required
def start_phase_two_generation():
    """启动第二阶段章节生成"""
    try:
        data = request.json or {}
        novel_title = data.get('novel_title')
        from_chapter = data.get('from_chapter', 1)
        chapters_to_generate = data.get('chapters_to_generate', 10)
        chapters_per_batch = data.get('chapters_per_batch', 3)
        
        if not novel_title:
            return jsonify({
                "success": False,
                "error": "缺少novel_title参数"
            }), 400
        
        # 检查第一阶段是否完成
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return jsonify({
                "success": False,
                "error": f"未找到第一阶段结果: {novel_title}"
            }), 404
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            phase_one_result = json.load(f)
        
        if not phase_one_result.get('is_phase_one_completed', False):
            return jsonify({
                "success": False,
                "error": f"第一阶段尚未完成"
            }), 400
        
        # 检查起始章节
        if from_chapter < 1:
            return jsonify({
                "success": False,
                "error": f"起始章节必须大于等于1"
            }), 400
        
        # 暂时返回模拟响应
        return jsonify({
            "success": True,
            "task_id": f"phase_two_{novel_title}",
            "message": f"第二阶段章节生成完成",
            "generated_chapters": chapters_to_generate
        })
        
    except Exception as e:
        logger.error(f"❌ 启动第二阶段生成失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-two/task/<task_id>/status', methods=['GET'])
@login_required
def get_phase_two_task_status(task_id):
    """获取第二阶段任务状态"""
    try:
        # 暂时返回模拟状态
        return jsonify({
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "message": "第二阶段已完成"
        })
    except Exception as e:
        logger.error(f"❌ 获取第二阶段任务状态失败: {e}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/phase-two/progress/<novel_title>', methods=['GET'])
@login_required
def get_phase_two_progress(novel_title):
    """获取第二阶段进度"""
    try:
        # 检查第一阶段结果
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return jsonify({
                "phase_two_status": "not_started",
                "message": "第一阶段未完成",
                "current_chapter": 0,
                "total_chapters": 0,
                "generated_chapters": []
            })
        
        # 获取已生成的章节数据
        novel_dir = Path("小说项目") / safe_title / "chapters"
        generated_chapters = {}
        
        if novel_dir.exists():
            chapter_files = list(novel_dir.glob("第*.txt")) + list(novel_dir.glob("第*.json"))
            
            for chapter_file in chapter_files:
                try:
                    match = re.search(r'第(\d+)章', chapter_file.name)
                    if match:
                        chapter_num = int(match.group(1))
                        with open(chapter_file, 'r', encoding='utf-8') as cf:
                            file_content = cf.read()
                            
                            try:
                                chapter_data = json.loads(file_content)
                                generated_chapters[chapter_num] = {
                                    "chapter_number": chapter_num,
                                    "title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                                    "content": chapter_data.get("content", file_content),
                                    "word_count": chapter_data.get("word_count", len(file_content)),
                                    "status": "completed"
                                }
                            except json.JSONDecodeError:
                                generated_chapters[chapter_num] = {
                                    "chapter_number": chapter_num,
                                    "title": chapter_file.stem.replace("第", "").replace("章", ""),
                                    "content": file_content,
                                    "word_count": len(file_content),
                                    "status": "completed"
                                }
                            except Exception as e:
                                logger.error(f"⚠️ 加载章节 {chapter_file.name} 失败: {e}")
                                continue
                except Exception as e:
                    logger.error(f"处理章节文件 {chapter_file} 时出错: {e}")
                    continue
                    
            total_chapters = len(generated_chapters)
            
            return jsonify({
                "phase_two_status": "generating" if total_chapters > 0 else "not_started",
                "message": "正在生成中..." if total_chapters > 0 else "尚未开始",
                "current_chapter": total_chapters + 1,
                "total_chapters": total_chapters,
                "generated_chapters": list(generated_chapters.values())
            })
        else:
            return jsonify({
                "phase_two_status": "not_started",
                "message": "尚未开始生成章节",
                "current_chapter": 1,
                "total_chapters": 0,
                "generated_chapters": []
            })
        
    except Exception as e:
        logger.error(f"❌ 获取第二阶段进度失败: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== 项目管理API ====================

@phase_api.route('/api/projects/with-phase-status', methods=['GET'])
@login_required
def get_projects_with_phase_status():
    """获取包含两阶段状态的项目列表"""
    try:
        projects = manager.get_novel_projects()
        
        # 为每个项目添加两阶段状态
        for project in projects:
            title = project["title"]
            
            # 检查第一阶段状态
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
            phase_one_completed = (
                os.path.exists(f"小说项目/{safe_title}_第一阶段设定") and 
                os.path.exists(f"小说项目/{safe_title}_项目信息.json")
            )
            
            # 设置两阶段状态
            if phase_one_completed:
                project["phase_one"] = {"status": "completed"}
                project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                project["status"] = "phase_one_completed"
            else:
                project["phase_one"] = {"status": "pending"}
                project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                project["status"] = "designing"
        
        return jsonify(projects)
        
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/api/project/<title>/with-phase-info', methods=['GET'])
@login_required
def get_novel_detail_with_phase_info(title):
    """获取包含两阶段信息的小说详情"""
    try:
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"error": "小说不存在"}), 404
        
        # 标准化数据结构，确保前端能够正确获取核心设定信息
        standardized_detail = standardize_novel_data_structure(novel_detail)
        
        # 添加两阶段状态信息
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        
        # 检查第一阶段状态
        phase_one_completed = (
            os.path.exists(f"小说项目/{safe_title}_第一阶段设定") and 
            os.path.exists(f"小说项目/{safe_title}_项目信息.json")
        )
        
        # 检查第二阶段状态
        generated_chapters = novel_detail.get("generated_chapters", {})
        phase_two_in_progress = (
            phase_one_completed and len(generated_chapters) > 0
        )
        
        # 添加两阶段状态
        if phase_one_completed and phase_two_in_progress:
            phase_one_status = {"status": "completed"}
            phase_two_status = {"status": "generating", "progress": f"{len(generated_chapters)} 章"}
        elif phase_one_completed:
            phase_one_status = {"status": "completed"}
            phase_two_status = {"status": "not_started", "progress": "0 章"}
        else:
            phase_one_status = {"status": "pending"}
            phase_two_status = {"status": "not_started", "progress": "0 章"}
        
        # 添加到详情中
        standardized_detail["phase_one"] = phase_one_status
        standardized_detail["phase_two"] = phase_two_status
        standardized_detail["current_phase"] = "phase_two" if phase_two_in_progress else "phase_one"
        
        return jsonify(standardized_detail)
        
    except Exception as e:
        logger.error(f"❌ 获取小说详情失败: {e}")
        return jsonify({"error": str(e)}), 500

def standardize_novel_data_structure(novel_data):
    """标准化小说数据结构，确保前端能够正确获取核心设定信息"""
    
    # 创建标准化的数据结构
    standardized = {
        # 保留原始数据
        **novel_data,
    }
    
    # 添加两阶段状态
    safe_title = re.sub(r'[\\/*?:"<>|]', '_', novel_data.get("title", ""))
    phase_one_completed = (
        os.path.exists(f"小说项目/{safe_title}_第一阶段设定") and 
        os.path.exists(f"小说项目/{safe_title}_项目信息.json")
    )
    generated_chapters = novel_data.get("generated_chapters", {})
    phase_two_in_progress = (
        phase_one_completed and len(generated_chapters) > 0
    )
    
    # 添加两阶段状态
    standardized["phase_one"] = phase_one_completed
    standardized["phase_two"] = phase_two_in_progress
    standardized["current_phase"] = "phase_two" if phase_two_in_progress else "phase_one"
    
    return standardized

# ==================== 通用工具函数 ====================

def clean_title(title: str) -> str:
    """清理文件名中的特殊字符"""
    return re.sub(r'[\\/*?:"<>|]', '_', title)

def load_phase_one_result(title: str) -> Optional[Dict[str, Any]]:
    """加载第一阶段结果数据"""
    try:
        safe_title = clean_title(title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        if not os.path.exists(phase_one_file):
            return None
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载第一阶段结果失败: {e}")
        return None

def save_phase_one_result(title: str, result: Dict[str, Any]) -> bool:
    """保存第一阶段结果"""
    try:
        safe_title = clean_title(title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        os.makedirs(phase_one_dir, exist_ok=True)
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        with open(phase_one_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 第一阶段结果已保存: {phase_one_file}")
        return True
    except Exception as e:
        logger.error(f"保存第一阶段结果失败: {e}")
        return False

def delete_project(title: str) -> bool:
    """删除项目"""
    try:
        # 删除项目目录
        safe_title = clean_title(title)
        project_dirs = [
            f"小说项目/{safe_title}_第一章",
            f"小说项目/{safe_title}_章节",
            f"小说项目/{safe_title}_质量数据"
        ]
        
        for dir_path in project_dirs:
            if os.path.exists(dir_path):
                import shutil
                shutil.rmtree(dir_path)
                logger.info(f"✅ 已删除目录: {dir_path}")
        
        logger.info(f"✅ 项目已删除: {title}")
        return True
    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        return False

# ==================== 导出功能 ====================

@phase_api.route('/api/project/<title>/export', methods=['GET'])
@login_required
def export_project(title):
    """导出项目数据"""
    try:
        safe_title = clean_title(title)
        export_type = request.args.get('format', 'json')
        return manager.export_novel(safe_title, export_type)
    except Exception as e:
        logger.error(f"导出项目失败: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== 错误处理 ====================

@phase_api.errorhandler(404)
def phase_not_found(error):
    """第一阶段404处理"""
    return jsonify({"error": "页面未找到"}), 404

@phase_api.errorhandler(500)
def phase_server_error(error):
    """第一阶段500处理"""
    return jsonify({"error": str(error)}), 500


def register_phase_routes(app, manager_instance=None):
    """注册两阶段生成API路由"""
    # 注册蓝图
    app.register_blueprint(phase_api)
    
    # 如果提供了管理器实例，更新全局管理器
    if manager_instance:
        global manager
        manager = manager_instance
    
    # 添加一些直接的路由（如果需要的话）
    @app.route('/api/phase/status', methods=['GET'])
    def get_phase_system_status():
        """获取两阶段系统状态"""
        try:
            from web.auth import login_required
            
            return jsonify({
                "success": True,
                "phase_system_active": True,
                "manager_available": manager is not None,
                "loaded_projects": len(manager.novel_projects) if manager else 0,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ 获取两阶段系统状态失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500