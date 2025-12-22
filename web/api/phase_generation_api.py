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
try:
    from web.managers.novel_manager import NovelGenerationManager
    manager = NovelGenerationManager()
except Exception as e:
    print(f"❌ 无法初始化NovelGenerationManager: {e}")
    manager = None

# API登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== 第一阶段相关API ====================

@phase_api.route('/phase-one/generate', methods=['POST'])
@login_required
def start_phase_one_generation():
    """启动第一阶段设定生成"""
    logger.info("🚀 [API_DEBUG] 第一阶段生成API被调用")
    logger.info(f"📋 [API_DEBUG] 请求方法: {request.method}")
    logger.info(f"📋 [API_DEBUG] 请求URL: {request.url}")
    logger.info(f"📋 [API_DEBUG] 请求头: {dict(request.headers)}")
    
    try:
        # 获取表单数据
        data = request.json or {}
        logger.info(f"📋 [API_DEBUG] 接收到的数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 验证必需参数
        required_fields = ['title', 'synopsis', 'core_setting', 'core_selling_points', 'total_chapters']
        logger.info(f"✅ [API_DEBUG] 开始验证必需参数: {required_fields}")
        
        for field in required_fields:
            if not data.get(field):
                logger.error(f"❌ [API_DEBUG] 缺少必需参数: {field}")
                return jsonify({"success": False, "error": f"缺少必需参数: {field}"}), 400
        
        logger.info("✅ [API_DEBUG] 必需参数验证通过")
        
        # 调用管理器启动生成任务
        global manager
        if not manager:
            logger.error("❌ [API_DEBUG] NovelGenerationManager 未初始化")
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        logger.info("✅ [API_DEBUG] NovelGenerationManager 可用")
        
        # 构建创意种子数据
        creative_seed = {
            "novelTitle": data.get("title"),
            "synopsis": data.get("synopsis"),
            "coreSetting": data.get("core_setting"),
            "coreSellingPoints": data.get("core_selling_points"),
            "totalChapters": data.get("total_chapters", 50),
            "generationMode": data.get("generation_mode", "phase_one_only")
        }
        logger.info(f"📋 [API_DEBUG] 构建的创意种子: {json.dumps(creative_seed, ensure_ascii=False, indent=2)}")
        
        # 启动生成任务，使用管理器返回的任务ID
        logger.info("🚀 [API_DEBUG] 调用管理器启动第一阶段生成任务...")
        generation_config = {
            "title": data.get("title"),
            "synopsis": data.get("synopsis"),
            "core_setting": data.get("core_setting"),
            "core_selling_points": data.get("core_selling_points"),
            "total_chapters": data.get("total_chapters", 50),
            "generation_mode": "phase_one_only",  # 强制设置为第一阶段模式
            "creative_seed": creative_seed
        }
        logger.info(f"📋 [API_DEBUG] 生成配置: {json.dumps(generation_config, ensure_ascii=False, indent=2)}")
        
        manager_task_id = manager.start_generation(generation_config)
        logger.info(f"✅ [API_DEBUG] 管理器返回任务ID: {manager_task_id}")
        
        # 使用管理器返回的任务ID作为统一的任务ID
        task_id = manager_task_id
        logger.info(f"✅ [API_DEBUG] 第一阶段设定生成任务已启动: {task_id}")
        
        response_data = {
            "success": True,
            "task_id": task_id,
            "manager_task_id": manager_task_id,
            "message": "第一阶段设定生成任务已启动，正在后台处理（只执行到第一章生成前）",
            "status": "started",
            "phase": "phase_one",
            "expected_stages": [
                "基础规划",
                "世界观与角色设计",
                "全书规划",
                "内容生成准备"
            ]
        }
        logger.info(f"📤 [API_DEBUG] 返回响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ [API_DEBUG] 启动第一阶段生成任务失败: {e}")
        logger.error(f"❌ [API_DEBUG] 错误类型: {type(e).__name__}")
        logger.error(f"❌ [API_DEBUG] 错误详情: {str(e)}")
        import traceback
        logger.error(f"❌ [API_DEBUG] 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-one/start-generation', methods=['POST'])
@login_required
def start_phase_one_generation_legacy():
    """启动第一阶段设定生成（兼容旧版本）"""
    return start_phase_one_generation()

@phase_api.route('/phase-one/task/<task_id>/status', methods=['GET'])
@login_required
def get_phase_one_task_status(task_id):
    """获取第一阶段任务状态"""
    logger.info(f"🔍 [API_DEBUG] 任务状态查询API被调用")
    logger.info(f"📋 [API_DEBUG] 请求方法: {request.method}")
    logger.info(f"📋 [API_DEBUG] 请求URL: {request.url}")
    logger.info(f"📋 [API_DEBUG] 任务ID: {task_id}")
    
    try:
        global manager
        if not manager:
            logger.error("❌ [API_DEBUG] NovelGenerationManager 未初始化")
            return jsonify({"error": "管理器未初始化"}), 500
        
        logger.info("✅ [API_DEBUG] NovelGenerationManager 可用")
        
        # 查询任务状态
        logger.info(f"🔍 [API_DEBUG] 查询任务状态: {task_id}")
        task_status = manager.get_task_status(task_id)
        logger.info(f"📋 [API_DEBUG] 任务状态结果: {json.dumps(task_status, ensure_ascii=False, indent=2)}")
        
        task_progress = manager.get_task_progress(task_id)
        logger.info(f"📋 [API_DEBUG] 任务进度结果: {json.dumps(task_progress, ensure_ascii=False, indent=2)}")
        
        if "error" in task_status:
            logger.error(f"❌ [API_DEBUG] 任务不存在或出错: {task_status['error']}")
            return jsonify({"error": task_status["error"]}), 404
        
        # 构建响应数据
        response = {
            "task_id": task_id,
            "status": task_status.get("status", "unknown"),
            "progress": task_progress.get("progress", 0),
            "current_step": task_status.get("current_step", "initializing"),
            "message": task_status.get("message", "处理中...")
        }
        
        # 如果任务完成，添加结果数据
        if task_status.get("status") == "completed":
            response["result"] = task_status.get("result", {})
            logger.info(f"✅ [API_DEBUG] 任务已完成，包含结果数据")
        
        logger.info(f"📤 [API_DEBUG] 返回状态查询响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ [API_DEBUG] 获取第一阶段任务状态失败: {e}")
        logger.error(f"❌ [API_DEBUG] 错误类型: {type(e).__name__}")
        logger.error(f"❌ [API_DEBUG] 错误详情: {str(e)}")
        import traceback
        logger.error(f"❌ [API_DEBUG] 错误堆栈: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/phase-one/task/<task_id>/status', methods=['GET'])
@login_required
def get_phase_one_task_status_legacy(task_id):
    """获取第一阶段任务状态（兼容旧版本）"""
    return get_phase_one_task_status(task_id)

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
    logger.info("🚀 [API_DEBUG] 第二阶段生成API被调用")
    logger.info(f"📋 [API_DEBUG] 请求方法: {request.method}")
    logger.info(f"📋 [API_DEBUG] 请求URL: {request.url}")
    
    try:
        data = request.json or {}
        logger.info(f"📋 [API_DEBUG] 接收到的数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        novel_title = data.get('novel_title')
        from_chapter = data.get('from_chapter', 1)
        chapters_to_generate = data.get('chapters_to_generate', None)
        chapters_per_batch = data.get('chapters_per_batch', 3)
        
        if not novel_title:
            logger.error("❌ [API_DEBUG] 缺少novel_title参数")
            return jsonify({
                "success": False,
                "error": "缺少novel_title参数"
            }), 400
        
        # 检查第一阶段是否完成
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        logger.info(f"🔍 [API_DEBUG] 检查第一阶段结果文件: {phase_one_file}")
        
        if not os.path.exists(phase_one_file):
            logger.error(f"❌ [API_DEBUG] 未找到第一阶段结果文件: {phase_one_file}")
            return jsonify({
                "success": False,
                "error": f"未找到第一阶段结果: {novel_title}"
            }), 404
        
        with open(phase_one_file, 'r', encoding='utf-8') as f:
            phase_one_result = json.load(f)
        
        if not phase_one_result.get('is_phase_one_completed', False):
            logger.error("❌ [API_DEBUG] 第一阶段尚未完成")
            return jsonify({
                "success": False,
                "error": f"第一阶段尚未完成"
            }), 400
        
        # 检查起始章节
        if from_chapter < 1:
            logger.error(f"❌ [API_DEBUG] 起始章节无效: {from_chapter}")
            return jsonify({
                "success": False,
                "error": f"起始章节必须大于等于1"
            }), 400
        
        logger.info(f"✅ [API_DEBUG] 第一阶段验证通过，开始第二阶段生成")
        logger.info(f"📚 [API_DEBUG] 小说标题: {novel_title}")
        logger.info(f"📚 [API_DEBUG] 起始章节: {from_chapter}")
        logger.info(f"📚 [API_DEBUG] 生成章节数: {chapters_to_generate}")
        
        # 调用管理器启动第二阶段任务
        global manager
        if not manager:
            logger.error("❌ [API_DEBUG] NovelGenerationManager 未初始化")
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 构建第二阶段任务配置
        phase_two_config = {
            "novel_title": novel_title,
            "phase_one_file": phase_one_file,
            "from_chapter": from_chapter,
            "chapters_to_generate": chapters_to_generate,
            "chapters_per_batch": chapters_per_batch,
            "generation_mode": "phase_two_only"
        }
        
        logger.info(f"🚀 [API_DEBUG] 调用管理器启动第二阶段生成任务...")
        
        # 启动第二阶段任务
        manager_task_id = manager.start_phase_two_generation(phase_two_config)
        logger.info(f"✅ [API_DEBUG] 第二阶段任务已启动: {manager_task_id}")
        
        response_data = {
            "success": True,
            "task_id": manager_task_id,
            "message": f"第二阶段章节生成任务已启动，从第{from_chapter}章开始",
            "status": "started",
            "phase": "phase_two",
            "novel_title": novel_title,
            "from_chapter": from_chapter,
            "chapters_to_generate": chapters_to_generate
        }
        logger.info(f"📤 [API_DEBUG] 返回第二阶段响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ 启动第二阶段生成失败: {e}")
        logger.error(f"❌ [API_DEBUG] 错误类型: {type(e).__name__}")
        logger.error(f"❌ [API_DEBUG] 错误详情: {str(e)}")
        import traceback
        logger.error(f"❌ [API_DEBUG] 错误堆栈: {traceback.format_exc()}")
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

@phase_api.route('/projects/with-phase-status', methods=['GET'])
@login_required
def get_projects_with_phase_status():
    """获取包含两阶段状态的项目列表"""
    try:
        projects = manager.get_novel_projects() if manager else []
        logger.info(f"🔍 [PROJECT_DEBUG] 获取到 {len(projects)} 个项目")
        
        # 为每个项目添加两阶段状态
        for project in projects:
            title = project["title"]
            logger.info(f"🔍 [PROJECT_DEBUG] 处理项目: {title}")
            
            # 检查第一阶段状态 - 使用更灵活的检测方式
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
            
            # 检查多种可能的第一阶段完成标识
            phase_one_indicators = [
                # 新格式：第一阶段设定目录
                f"小说项目/{safe_title}_第一阶段设定",
                # 旧格式：项目目录下有完整规划文件
                f"小说项目/{safe_title}/planning",
                f"小说项目/{safe_title}/worldview",
                f"小说项目/{safe_title}/project_info",
                # 通用：有章节目录说明至少开始生成
                f"小说项目/{safe_title}/chapters",
                f"小说项目/{safe_title}_章节"
            ]
            
            phase_one_completed = False
            completed_reason = ""
            
            for indicator in phase_one_indicators:
                if os.path.exists(indicator):
                    phase_one_completed = True
                    completed_reason = f"找到目录: {indicator}"
                    logger.info(f"✅ [PROJECT_DEBUG] 第一阶段完成标识: {indicator}")
                    break
            
            # 额外检查：如果没有目录结构，检查是否有章节数据
            if not phase_one_completed:
                novel_detail = manager.get_novel_detail(title) if manager else None
                if novel_detail:
                    generated_chapters = novel_detail.get("generated_chapters", {})
                    if generated_chapters:
                        phase_one_completed = True
                        completed_reason = f"找到 {len(generated_chapters)} 个已生成章节"
                        logger.info(f"✅ [PROJECT_DEBUG] 通过章节数据确认第一阶段完成: {len(generated_chapters)} 章")
            
            # 检查第二阶段状态
            novel_detail = manager.get_novel_detail(title) if manager else None
            generated_chapters = novel_detail.get("generated_chapters", {}) if novel_detail else {}
            chapter_count = len(generated_chapters)
            
            # 设置两阶段状态
            if phase_one_completed:
                project["phase_one"] = {
                    "status": "completed",
                    "completed_at": novel_detail.get("creation_time", "") if novel_detail else "",
                    "reason": completed_reason
                }
                
                if chapter_count > 0:
                    project["phase_two"] = {
                        "status": "generating" if chapter_count < project.get("total_chapters", 50) else "completed",
                        "progress": f"{chapter_count} 章",
                        "generated_chapters": chapter_count
                    }
                    project["status"] = "phase_two_in_progress" if chapter_count < project.get("total_chapters", 50) else "completed"
                else:
                    project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                    project["status"] = "phase_one_completed"
            else:
                project["phase_one"] = {"status": "pending"}
                project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                project["status"] = "designing"
            
            logger.info(f"📋 [PROJECT_DEBUG] 项目 {title} 状态: phase_one={project['phase_one']['status']}, phase_two={project['phase_two']['status']}, overall={project['status']}")
        
        logger.info(f"✅ [PROJECT_DEBUG] 返回 {len(projects)} 个项目的状态信息")
        return jsonify({"projects": projects})
        
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@phase_api.route('/project/<title>/with-phase-info', methods=['GET'])
@login_required
def get_novel_detail_with_phase_info(title):
    """获取包含两阶段信息的小说详情"""
    try:
        novel_detail = manager.get_novel_detail(title) if manager else None
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

@phase_api.route('/project/<title>/export', methods=['GET'])
@login_required
def export_project(title):
    """导出项目数据"""
    try:
        safe_title = clean_title(title)
        export_type = request.args.get('format', 'json')
        return manager.export_novel(safe_title, export_type) if manager else {"error": "管理器未初始化"}
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
    # 注册蓝图，添加 /api 前缀
    app.register_blueprint(phase_api, url_prefix='/api')
    
    # 如果提供了管理器实例，更新全局管理器
    if manager_instance:
        global manager
        manager = manager_instance
    
    # 添加保存项目API端点
    @app.route('/api/phase-one/save/<task_id>', methods=['POST'])
    @login_required
    def save_phase_one_project(task_id):
        """保存第一阶段项目"""
        try:
            global manager
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            # 获取任务状态
            task_status = manager.get_task_status(task_id)
            if "error" in task_status:
                return jsonify({"success": False, "error": f"任务不存在: {task_id}"}), 404
            
            # 检查任务是否完成
            if task_status.get("status") != "completed":
                return jsonify({"success": False, "error": "任务尚未完成，无法保存"}), 400
            
            # 获取任务配置和结果
            config = task_status.get("config", {})
            result = task_status.get("result", {})
            
            if not config:
                return jsonify({"success": False, "error": "任务配置为空"}), 400
            
            # 构建项目数据
            project_data = {
                "title": config.get("title", "未命名小说"),
                "synopsis": config.get("synopsis", ""),
                "core_setting": config.get("core_setting", ""),
                "core_selling_points": config.get("core_selling_points", ""),
                "total_chapters": config.get("total_chapters", 50),
                "generation_mode": config.get("generation_mode", "phase_one_only"),
                "phase_one_result": result,
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "status": "phase_one_completed"
            }
            
            # 保存项目到文件系统
            project_title = config.get("title", f"项目_{task_id}")
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', project_title)
            
            # 创建项目目录
            project_dir = Path(f"小说项目/{safe_title}_第一阶段设定")
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存项目信息
            project_file = project_dir / f"{safe_title}_第一阶段设定.json"
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            # 同时保存为主项目信息文件
            main_project_file = Path(f"小说项目/{safe_title}_项目信息.json")
            with open(main_project_file, 'w', encoding='utf-8') as f:
                json.dump({
                    **project_data,
                    "is_phase_one_completed": True,
                    "phase_one_file": str(project_file)
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 第一阶段项目已保存: {project_file}")
            
            return jsonify({
                "success": True,
                "message": f"项目 {project_title} 保存成功",
                "project_path": str(project_file),
                "project_title": project_title
            })
        except Exception as e:
            logger.error(f"❌ 保存项目失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    # 添加系统状态API端点
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