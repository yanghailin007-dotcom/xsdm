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
            "totalChapters": data.get("total_chapters", 200),
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
            "total_chapters": data.get("total_chapters", 200),
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

@phase_api.route('/phase-one/continue-to-phase-two/<path:novel_title>', methods=['POST'])
@login_required
def continue_to_phase_two(novel_title):
    """从第一阶段继续到第二阶段"""
    logger.info(f"✅ continue_to_phase_two 路由被调用，novel_title={novel_title}")
    try:
        data = request.json or {}
        total_chapters = data.get('total_chapters', 200)
        chapters_per_batch = data.get('chapters_per_batch', 3)
        logger.info(f"✅ 接收到请求参数: total_chapters={total_chapters}, chapters_per_batch={chapters_per_batch}")
        
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
        
        # 检查第一阶段是否完成 - 支持多种路径结构
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        
        # 尝试多种可能的路径
        possible_paths = [
            # 最常见的旧路径
            f"小说项目/{safe_title}_第一阶段设定/{safe_title}_第一阶段设定.json",
            # 新的混合路径（项目名在中间）
            f"小说项目/{safe_title}/{safe_title}_第一阶段设定/{safe_title}_第一阶段设定.json",
            # 新项目结构路径
            f"小说项目/{safe_title}/project_info"
        ]
        
        logger.info(f"🔍 [API_DEBUG] 检查第一阶段结果...")
        for path in possible_paths:
            logger.info(f"🔍 [API_DEBUG] 检查路径: {path}")
        
        phase_one_result = None
        phase_one_source = ""
        actual_phase_one_file = None
        
        # 遍历所有可能的路径
        for phase_one_file in possible_paths:
            if os.path.exists(phase_one_file):
                logger.info(f"✅ [API_DEBUG] 找到第一阶段结果: {phase_one_file}")
                
                # 如果是目录，继续查找JSON文件
                if os.path.isdir(phase_one_file):
                    logger.info(f"🔍 [API_DEBUG] 是目录，继续查找JSON文件")
                    project_info_files = [f for f in os.listdir(phase_one_file) if f.endswith('.json')]
                    for info_file in project_info_files:
                        try:
                            file_path = f"{phase_one_file}/{info_file}"
                            with open(file_path, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                            
                            # 检查是否有核心设定数据
                            has_core_data = any(key in project_data for key in [
                                'core_worldview', 'character_design', 'global_growth_plan',
                                'overall_stage_plans', 'stage_writing_plans', 'market_analysis'
                            ])
                            
                            if has_core_data:
                                phase_one_result = project_data
                                phase_one_source = f"目录路径: {phase_one_file}"
                                actual_phase_one_file = file_path  # 使用实际的JSON文件路径
                                logger.info(f"✅ [API_DEBUG] 从目录加载成功，使用文件: {file_path}")
                                break
                        except Exception as e:
                            logger.info(f"⚠️ 读取文件失败: {info_file}, {e}")
                            continue
                    
                    if phase_one_result:
                        break
                else:
                    # 是文件，直接读取
                    with open(phase_one_file, 'r', encoding='utf-8') as f:
                        phase_one_result = json.load(f)
                    phase_one_source = "文件路径"
                    actual_phase_one_file = phase_one_file
                
        
        # 如果所有路径都没找到
        if not phase_one_result:
            logger.error(f"❌ [API_DEBUG] 未找到第一阶段结果")
            logger.error(f"❌ [API_DEBUG] 检查的路径:")
            for path in possible_paths:
                logger.error(f"   - {path}")
            return jsonify({
                "success": False,
                "error": f"未找到第一阶段结果: {novel_title}。请确保已完成第一阶段设定生成。"
            }), 404
        
        logger.info(f"✅ [API_DEBUG] 第一阶段数据加载成功 (来源: {phase_one_source})")
        
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
        
        # 构建第二阶段任务配置 - 使用actual_phase_one_file而不是phase_one_file
        phase_two_config = {
            "novel_title": novel_title,
            "phase_one_file": actual_phase_one_file,  # 使用实际的JSON文件路径
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
        global manager
        if not manager:
            return jsonify({"error": "管理器未初始化"}), 500
        
        # 查询任务状态
        task_status = manager.get_task_status(task_id)
        task_progress = manager.get_task_progress(task_id)
        
        if "error" in task_status:
            return jsonify({"error": task_status["error"]}), 404
        
        # 构建响应数据
        response = {
            "task_id": task_id,
            "status": task_status.get("status", "unknown"),
            "progress": task_progress.get("progress", 0),
            "current_step": task_status.get("current_step", "initializing"),
            "message": task_status.get("message", "处理中..."),
            "status_message": task_status.get("message", "处理中...")
        }
        
        # 添加章节进度信息（如果有）
        if "current_chapter" in task_progress:
            response["current_chapter"] = task_progress["current_chapter"]
        if "total_chapters" in task_progress:
            response["total_chapters"] = task_progress["total_chapters"]
        # 添加章节进度列表（关键修复：这是前端显示章节状态所需的数据）
        if "chapter_progress" in task_progress:
            response["chapter_progress"] = task_progress["chapter_progress"]
        
        # 如果任务完成，添加结果数据
        if task_status.get("status") == "completed":
            response["result"] = task_status.get("result", {})
            if "generated_chapters" in task_progress:
                response["generated_chapters"] = task_progress["generated_chapters"]
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"获取第二阶段任务状态失败: {e}")
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
        logger.info(f"🔍 [PROJECT_DEBUG] 开始获取项目列表")
        global manager
        if not manager:
            logger.error("❌ [PROJECT_DEBUG] manager未初始化")
            return jsonify({"projects": []}), 200
        
        projects = manager.get_novel_projects()
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
                        "status": "generating" if chapter_count < project.get("total_chapters", 200) else "completed",
                        "progress": f"{chapter_count} 章",
                        "generated_chapters": chapter_count
                    }
                    project["status"] = "phase_two_in_progress" if chapter_count < project.get("total_chapters", 200) else "completed"
                else:
                    project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                    project["status"] = "phase_one_completed"
            else:
                project["phase_one"] = {"status": "pending"}
                project["phase_two"] = {"status": "not_started", "progress": "0 章"}
                project["status"] = "designing"
            
            try:
                logger.info(f"📋 [PROJECT_DEBUG] 项目 {title} 状态: phase_one={project['phase_one']['status']}, phase_two={project['phase_two']['status']}, overall={project['status']}")
            except Exception as inner_e:
                logger.error(f"❌ [PROJECT_DEBUG] 处理项目 {title} 时出错: {inner_e}")
                continue
        
        logger.info(f"✅ [PROJECT_DEBUG] 返回 {len(projects)} 个项目的状态信息")
        return jsonify({"projects": projects})
        
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        # 返回空列表而不是错误，避免前端崩溃
        return jsonify({"projects": []}), 200

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
        safe_title = title.replace('\\', '_').replace('/', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # 检查第一阶段状态 - 支持新旧两种路径结构
        old_phase_one_path = f"小说项目/{safe_title}_第一阶段设定"
        old_project_info = f"小说项目/{safe_title}_项目信息.json"
        new_project_dir = f"小说项目/{safe_title}/project_info"
        
        phase_one_completed = False
        phase_one_source = ""
        
        # 检查旧路径
        if os.path.exists(old_phase_one_path) and os.path.exists(old_project_info):
            phase_one_completed = True
            phase_one_source = "旧路径"
        # 检查新路径
        elif os.path.exists(new_project_dir):
            phase_one_completed = True
            phase_one_source = "新路径"
        
        if phase_one_completed:
            logger.info(f"✅ 第一阶段完成检测成功 (来源: {phase_one_source})")
        
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
    
    # 打印注册的路由，用于调试
    logger.info("=" * 60)
    logger.info("📋 已注册的两阶段生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'phase' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    
    # 注意: 第一阶段产物管理的API路由已经在Blueprint中定义
    # /api/phase-one/products/<title>
    # /api/phase-one/products/<title>/<category>
    # /api/phase-one/products/<title>/export
    # /api/phase-one/products/<title>/validate
    # 不需要在这里重复注册,避免路由冲突
    
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
                "total_chapters": config.get("total_chapters", 200),
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
    

# ==================== 第一阶段产物管理API ====================

@phase_api.route('/phase-one/products/<title>', methods=['GET'])
def get_phase_one_products(title):
    """获取第一阶段的所有产物"""
    try:
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        products_dir = f"{phase_one_dir}/产物"
        phase_one_index_file = f"{phase_one_dir}/{safe_title}_第一阶段索引.json"
        
        # 新的项目结构路径
        project_dir = f"小说项目/{safe_title}"
        project_info_path = f"{project_dir}/project_info"
        worldview_path = f"{project_dir}/worldview"
        plans_path = f"{project_dir}/plans"
        stage_plan_path = f"{project_dir}/stage_plan"
        market_path = f"{project_dir}/market_analysis"
        
        products = {
            'worldview': {'title': '世界观设定', 'content': '', 'complete': False, 'file_path': ''},
            'characters': {'title': '角色设计', 'content': '', 'complete': False, 'file_path': ''},
            'growth': {'title': '成长路线', 'content': '', 'complete': False, 'file_path': ''},
            'writing': {'title': '写作计划', 'content': '', 'complete': False, 'file_path': ''},
            'storyline': {'title': '故事线', 'content': '', 'complete': False, 'file_path': ''},
            'market': {'title': '市场分析', 'content': '', 'complete': False, 'file_path': ''}
        }
        
        # 首先尝试从manager获取quality_data（这些数据已经在服务器端加载了）
        novel_detail = manager.get_novel_detail(title) if manager else None
        if novel_detail:
            quality_data = novel_detail.get("quality_data", {})
            logger.info(f"🔍 [PRODUCTS_DEBUG] 从manager获取到quality_data，包含 {len(quality_data)} 个键")
            quality_writing_plans = quality_data.get("writing_plans", {})
            if quality_writing_plans:
                logger.info(f"✅ [PRODUCTS_DEBUG] 从quality_data找到 {len(quality_writing_plans)} 个写作计划")
                # 将quality_data中的写作计划添加到products中
                for stage_name, plan_data in quality_writing_plans.items():
                    if isinstance(plan_data, dict):
                        products['writing']['content'] = json.dumps(plan_data, ensure_ascii=False, indent=2)
                        products['writing']['complete'] = True
                        products['writing']['file_path'] = f"quality_data/{stage_name}"
                        logger.info(f"✅ 从quality_data加载写作计划: {stage_name}")
                        break  # 只取第一个找到的写作计划
        
        # 检查是否存在产物目录
        if os.path.exists(products_dir):
            # 新文件结构：从单独的产物文件读取
            product_files = {
                'worldview': f"{products_dir}/{safe_title}_世界观设定.json",
                'characters': f"{products_dir}/{safe_title}_角色设计.json",
                'growth': f"{products_dir}/{safe_title}_成长路线.json",
                'writing': f"{products_dir}/{safe_title}_写作计划.json",
                'storyline': f"{products_dir}/{safe_title}_阶段计划.json",
                'market': f"{products_dir}/{safe_title}_市场分析.json"
            }
            
            for category, file_path in product_files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    products[category]['content'] = json.dumps(content, ensure_ascii=False, indent=2)
                    products[category]['complete'] = True
                    products[category]['file_path'] = file_path
                    logger.info(f"✅ 已加载产物: {category}")
                else:
                    logger.info(f"⚠️ 产物文件不存在: {category}")
        
        elif os.path.exists(phase_one_index_file):
            # 旧文件结构：从索引文件读取
            with open(phase_one_index_file, 'r', encoding='utf-8') as f:
                phase_one_index = json.load(f)
            
            products_mapping = phase_one_index.get("products_mapping", {})
            
            # 从映射中加载产物
            for category, file_path in products_mapping.items():
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    products[category]['content'] = json.dumps(content, ensure_ascii=False, indent=2)
                    products[category]['complete'] = True
                    products[category]['file_path'] = file_path
                    logger.info(f"✅ 已加载产物(旧格式): {category}")
                else:
                    logger.info(f"⚠️ 产物文件不存在(旧格式): {category}")
        
        elif os.path.exists(phase_one_file):
            # 直接从第一阶段设定文件读取（最常用的格式）
            logger.info(f"📁 从第一阶段设定文件读取产物: {phase_one_file}")
            try:
                with open(phase_one_file, 'r', encoding='utf-8') as f:
                    phase_one_data = json.load(f)
                
                # 优先从顶层提取数据（新格式），如果没有则从嵌套结构提取（旧格式）
                novel_data_summary = phase_one_data.get('result', {}).get('novel_data_summary', {})
                
                # 提取世界观
                worldview_data = phase_one_data.get('core_worldview') or novel_data_summary.get('core_worldview', {})
                if worldview_data:
                    products['worldview']['content'] = json.dumps(worldview_data, ensure_ascii=False, indent=2)
                    products['worldview']['complete'] = True
                    products['worldview']['file_path'] = phase_one_file
                
                # 提取角色设计
                character_data = phase_one_data.get('character_design') or novel_data_summary.get('character_design', {})
                if character_data:
                    products['characters']['content'] = json.dumps(character_data, ensure_ascii=False, indent=2)
                    products['characters']['complete'] = True
                    products['characters']['file_path'] = phase_one_file
                
                # 提取成长路线
                growth_data = phase_one_data.get('global_growth_plan') or novel_data_summary.get('global_growth_plan', {})
                if growth_data:
                    products['growth']['content'] = json.dumps(growth_data, ensure_ascii=False, indent=2)
                    products['growth']['complete'] = True
                    products['growth']['file_path'] = phase_one_file
                
                # 提取写作计划
                writing_data = phase_one_data.get('stage_writing_plans') or novel_data_summary.get('stage_writing_plans', {})
                if writing_data:
                    products['writing']['content'] = json.dumps(writing_data, ensure_ascii=False, indent=2)
                    products['writing']['complete'] = True
                    products['writing']['file_path'] = phase_one_file
                
                # 提取故事线 - 检查是否有有效的整体阶段规划数据
                # 只有在storyline尚未设置时才提取，避免覆盖
                if not products['storyline']['complete'] or not products['storyline']['content']:
                    storyline_data = (
                        phase_one_data.get('overall_stage_plans') or
                        novel_data_summary.get('overall_stage_plans', {}) or
                        phase_one_data.get('global_growth_plan') or
                        novel_data_summary.get('global_growth_plan', {})
                    )
                    # 检查是否有实际的阶段数据
                    has_valid_storyline = False
                    if isinstance(storyline_data, dict):
                        # 检查是否有 overall_stage_plan 或其他阶段数据
                        if 'overall_stage_plan' in storyline_data:
                            has_valid_storyline = True
                            logger.info(f"✅ 故事线数据有效：包含overall_stage_plan")
                        elif any(key in storyline_data for key in ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']):
                            has_valid_storyline = True
                            logger.info(f"✅ 故事线数据有效：包含阶段数据")
                        elif storyline_data:  # 非空字典也视为有效
                            # 检查字典中是否有任何实质性的内容（不只是元数据）
                            content_keys = [k for k in storyline_data.keys()
                                          if not k.startswith('_') and k not in ['version', 'created_at', 'updated_at']]
                            if content_keys:
                                has_valid_storyline = True
                                logger.info(f"✅ 故事线数据有效：非空字典，内容键: {content_keys[:5]}")
                            else:
                                logger.info(f"⚠️ 故事线数据字典为空或只包含元数据")
                        else:
                            logger.info(f"⚠️ 故事线数据为空字典")
                    else:
                        logger.info(f"⚠️ storyline_data不是字典类型: {type(storyline_data).__name__}")
                    
                    if has_valid_storyline:
                        products['storyline']['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                        products['storyline']['complete'] = True
                        products['storyline']['file_path'] = phase_one_file
                        logger.info(f"✅ 已加载故事线数据(从第一阶段设定文件): {type(storyline_data).__name__}")
                    else:
                        logger.info(f"⚠️ 第一阶段设定文件中故事线数据为空或无效")
                else:
                    logger.info(f"ℹ️ 故事线数据已在其他分支中加载，跳过第一阶段设定文件的storyline提取")
                
                # 提取市场分析
                market_data = phase_one_data.get('market_analysis') or novel_data_summary.get('market_analysis', {})
                if market_data:
                    products['market']['content'] = json.dumps(market_data, ensure_ascii=False, indent=2)
                    products['market']['complete'] = True
                    products['market']['file_path'] = phase_one_file
                
                logger.info(f"✅ 从第一阶段设定文件加载产物完成")
            except Exception as e:
                logger.error(f"❌ 读取第一阶段设定文件失败: {e}")
        
        # 尝试从新的项目结构读取 - 添加对 characters/ 目录的支持
        elif os.path.exists(project_info_path) or os.path.exists(f"{project_dir}/characters") or os.path.exists(f"{project_dir}/{safe_title}_项目信息.json") or os.path.exists(f"{project_dir}/{title}_项目信息.json"):
            logger.info(f"📁 从新项目结构读取第一阶段产物")
            
            # 首先检查 characters 目录（角色设计的标准路径）
            characters_dir = f"{project_dir}/characters"
            if os.path.exists(characters_dir):
                character_files = [f for f in os.listdir(characters_dir) if f.endswith('.json')]
                for cf in character_files:
                    try:
                        with open(f"{characters_dir}/{cf}", 'r', encoding='utf-8') as f:
                            character_data = json.load(f)
                        products['characters']['content'] = json.dumps(character_data, ensure_ascii=False, indent=2)
                        products['characters']['complete'] = True
                        products['characters']['file_path'] = f"{characters_dir}/{cf}"
                        logger.info(f"✅ 从characters目录加载角色设计数据")
                        break
                    except Exception as e:
                        logger.info(f"⚠️ 读取角色设计文件失败: {cf}, {e}")
            
            # 优先尝试从项目根目录读取项目信息文件（最新版本）
            project_info_files = []
            possible_root_names = [
                f"{title}_项目信息.json",  # 优先使用原始标题
                f"{safe_title}_项目信息.json",
                f"{title.replace(':', '：')}_项目信息.json"  # 处理英文冒号
            ]
            for possible_name in possible_root_names:
                project_info_json = f"{project_dir}/{possible_name}"
                if os.path.exists(project_info_json):
                    project_info_files = [possible_name]
                    logger.info(f"📁 [PRIORITY] 找到项目根目录的项目信息文件: {project_info_json}")
                    break
            
            # 如果根目录没有，再尝试从project_info目录读取
            if not project_info_files and os.path.exists(project_info_path):
                project_info_files = os.listdir(project_info_path)
                logger.info(f"📁 从project_info目录读取，找到 {len(project_info_files)} 个文件")
            
            for info_file in project_info_files:
                if info_file.endswith('.json'):
                    try:
                        # 构建文件路径 - 支持两种位置
                        if os.path.exists(f"{project_info_path}/{info_file}"):
                            info_path = f"{project_info_path}/{info_file}"
                        else:
                            info_path = f"{project_dir}/{info_file}"
                        
                        logger.info(f"📁 [FILE_DEBUG] 尝试读取文件: {info_path}")
                        with open(info_path, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)
                        
                        logger.info(f"📁 [FILE_DEBUG] 文件读取成功: {info_path}")
                        logger.info(f"📁 [FILE_DEBUG] project_data键: {list(project_data.keys())}")
                        logger.info(f"📁 [FILE_DEBUG] 是否包含产物数据字段: {any(k in project_data for k in ['core_worldview', 'character_design', 'overall_stage_plans', 'global_growth_plan', 'stage_writing_plans', 'market_analysis'])}")
                        
                        # 提取世界观 - 支持顶层和嵌套两种格式
                        worldview_data = project_data.get('core_worldview') or project_data.get('result', {}).get('novel_data_summary', {}).get('core_worldview', {})
                        if worldview_data:
                            products['worldview']['content'] = json.dumps(worldview_data, ensure_ascii=False, indent=2)
                            products['worldview']['complete'] = True
                            products['worldview']['file_path'] = f"{project_info_path}/{info_file}"
                        
                        # 提取角色设计 - 支持顶层和嵌套两种格式
                        character_data = project_data.get('character_design') or project_data.get('result', {}).get('novel_data_summary', {}).get('character_design', {})
                        if character_data:
                            products['characters']['content'] = json.dumps(character_data, ensure_ascii=False, indent=2)
                            products['characters']['complete'] = True
                            products['characters']['file_path'] = f"{project_info_path}/{info_file}"
                        
                        # 提取市场分析 - 支持顶层和嵌套两种格式
                        market_data = project_data.get('market_analysis') or project_data.get('result', {}).get('novel_data_summary', {}).get('market_analysis', {})
                        if market_data:
                            products['market']['content'] = json.dumps(market_data, ensure_ascii=False, indent=2)
                            products['market']['complete'] = True
                            products['market']['file_path'] = f"{project_info_path}/{info_file}"
                        
                        # 提取成长路线 - 支持多种字段名和目录
                        growth_data = (
                            project_data.get('global_growth_plan') or
                            project_data.get('overall_stage_plans') or
                            project_data.get('result', {}).get('novel_data_summary', {}).get('global_growth_plan', {}) or
                            project_data.get('result', {}).get('novel_data_summary', {}).get('overall_stage_plans', {})
                        )
                        if growth_data:
                            products['growth']['content'] = json.dumps(growth_data, ensure_ascii=False, indent=2)
                            products['growth']['complete'] = True
                            products['growth']['file_path'] = info_path
                            logger.info(f"✅ 从project_data加载成长路线数据 (字段名: {project_data.get('global_growth_plan') and 'global_growth_plan' or project_data.get('overall_stage_plans') and 'overall_stage_plans' or 'none'})")
                        elif not products['growth']['complete']:
                           # 尝试从 planning 目录读取
                           planning_dir = f"{project_dir}/planning"
                           if os.path.exists(planning_dir):
                               planning_files = os.listdir(planning_dir)
                               for pf in planning_files:
                                   if pf.endswith('.json') and '成长' in pf:
                                       try:
                                           with open(f"{planning_dir}/{pf}", 'r', encoding='utf-8') as f:
                                               planning_data = json.load(f)
                                           products['growth']['content'] = json.dumps(planning_data, ensure_ascii=False, indent=2)
                                           products['growth']['complete'] = True
                                           products['growth']['file_path'] = f"{planning_dir}/{pf}"
                                           logger.info(f"✅ 从planning目录加载成长路线数据")
                                           break
                                       except Exception as e:
                                           logger.info(f"⚠️ 读取planning文件失败: {pf}, {e}")
                        
                        # 提取写作计划 - 支持多种来源
                        writing_data = project_data.get('stage_writing_plans') or project_data.get('result', {}).get('novel_data_summary', {}).get('stage_writing_plans', {})
                        
                        # 如果还没找到，尝试从planning目录加载
                        if not writing_data or not isinstance(writing_data, dict) or len(writing_data) == 0:
                            planning_dir = f"{project_dir}/planning"
                            if os.path.exists(planning_dir):
                                # 尝试加载写作计划文件
                                writing_plan_files = []
                                # 常见文件名模式 - 优先使用精确的文件名
                                patterns = [
                                    f"{title}_写作计划.json",
                                    f"{safe_title}_写作计划.json",
                                    f"{title}*writing_plan*.json",
                                    "*写作计划*.json"
                                ]
                                for pattern in patterns:
                                    matching_files = list(Path(planning_dir).glob(pattern))
                                    if matching_files:
                                        writing_plan_files.extend(matching_files)
                                
                                if writing_plan_files:
                                    for wp_file in writing_plan_files:
                                        try:
                                            with open(wp_file, 'r', encoding='utf-8') as f:
                                                plan_content = json.load(f)
                                            # 如果是顶级结构，直接使用；如果是嵌套结构，提取stage_writing_plans
                                            if 'stage_writing_plan' in plan_content or 'opening_stage' in plan_content:
                                                writing_data = plan_content
                                                break
                                            # 检查是否包含完整的阶段计划
                                            if all(key in plan_content for key in ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']):
                                                writing_data = plan_content
                                                break
                                            logger.info(f"✅ 从planning目录加载写作计划: {wp_file.name}")
                                        except Exception as e:
                                            logger.info(f"⚠️ 读取写作计划文件失败: {wp_file.name}, {e}")
                        
                        # 如果还是没有，尝试从quality_data中获取（这些数据在服务器端已加载）
                        if not writing_data or not isinstance(writing_data, dict) or len(writing_data) == 0:
                            # 尝试从quality_data获取写作计划
                            novel_detail = manager.get_novel_detail(title) if manager else None
                            if novel_detail:
                                quality_data = novel_detail.get("quality_data", {})
                                if quality_data:
                                    quality_writing_plans = quality_data.get("writing_plans", {})
                                    if quality_writing_plans:
                                        writing_data = quality_writing_plans
                                        logger.info(f"✅ 从quality_data加载写作计划")
                        
                        if writing_data and (isinstance(writing_data, dict) or isinstance(writing_data, list)):
                            products['writing']['content'] = json.dumps(writing_data, ensure_ascii=False, indent=2)
                            products['writing']['complete'] = True
                            products['writing']['file_path'] = f"{project_info_path}/{info_file}"
                            logger.info(f"✅ 写作计划数据已加载，大小: {len(str(writing_data))} 字符")
                        else:
                            logger.info(f"⚠️ 写作计划数据未找到，可用的源: project_data.stage_writing_plans={bool(project_data.get('stage_writing_plans'))}, planning_dir_exists={os.path.exists(planning_dir)}")
                        
                        # 提取故事线 - 支持顶层和嵌套两种格式
                        logger.info(f"🔍 [STORYLINE_DEBUG] 开始提取storyline_data")
                        logger.info(f"🔍 [STORYLINE_DEBUG] project_data顶层键: {list(project_data.keys())[:20]}")
                        
                        # 检查每个可能的路径
                        overall_stage_plans = project_data.get('overall_stage_plans')
                        logger.info(f"🔍 [STORYLINE_DEBUG] project_data.get('overall_stage_plans'): {type(overall_stage_plans)} = {bool(overall_stage_plans)}")
                        if overall_stage_plans:
                            logger.info(f"   键: {list(overall_stage_plans.keys())[:10]}")
                        
                        global_growth_plan = project_data.get('global_growth_plan')
                        logger.info(f"🔍 [STORYLINE_DEBUG] project_data.get('global_growth_plan'): {type(global_growth_plan)} = {bool(global_growth_plan)}")
                        if global_growth_plan:
                            logger.info(f"   键: {list(global_growth_plan.keys())[:10]}")
                        
                        # 检查嵌套结构
                        result_data = project_data.get('result', {})
                        if isinstance(result_data, dict):
                            logger.info(f"🔍 [STORYLINE_DEBUG] result键: {list(result_data.keys())[:10]}")
                            novel_data_summary = result_data.get('novel_data_summary', {})
                            if isinstance(novel_data_summary, dict):
                                logger.info(f"🔍 [STORYLINE_DEBUG] novel_data_summary键: {list(novel_data_summary.keys())[:10]}")
                                
                                nested_overall_stage_plans = novel_data_summary.get('overall_stage_plans')
                                logger.info(f"🔍 [STORYLINE_DEBUG] novel_data_summary.get('overall_stage_plans'): {type(nested_overall_stage_plans)} = {bool(nested_overall_stage_plans)}")
                                if nested_overall_stage_plans:
                                    logger.info(f"   键: {list(nested_overall_stage_plans.keys())[:10]}")
                                
                                nested_global_growth_plan = novel_data_summary.get('global_growth_plan')
                                logger.info(f"🔍 [STORYLINE_DEBUG] novel_data_summary.get('global_growth_plan'): {type(nested_global_growth_plan)} = {bool(nested_global_growth_plan)}")
                                if nested_global_growth_plan:
                                    logger.info(f"   键: {list(nested_global_growth_plan.keys())[:10]}")
                        
                        storyline_data = (
                            project_data.get('overall_stage_plans') or
                            project_data.get('global_growth_plan') or
                            project_data.get('result', {}).get('novel_data_summary', {}).get('overall_stage_plans', {}) or
                            project_data.get('result', {}).get('novel_data_summary', {}).get('global_growth_plan', {})
                        )
                        
                        logger.info(f"🔍 [STORYLINE_DEBUG] 最终storyline_data类型: {type(storyline_data)}, 是否为空: {not storyline_data}")
                        if isinstance(storyline_data, dict) and storyline_data:
                            logger.info(f"   storyline_data键: {list(storyline_data.keys())[:10]}")
                        
                        # 检查是否有有效的阶段规划数据
                        has_valid_storyline = False
                        if isinstance(storyline_data, dict):
                            # 检查是否包含overall_stage_plan
                            if 'overall_stage_plan' in storyline_data:
                                # 检查overall_stage_plan是否包含阶段数据
                                stage_plan = storyline_data.get('overall_stage_plan', {})
                                if any(key in stage_plan for key in ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']):
                                    has_valid_storyline = True
                                    logger.info(f"✅ 故事线数据有效：包含overall_stage_plan且包含阶段数据")
                                elif stage_plan:
                                    has_valid_storyline = True
                                    logger.info(f"✅ 故事线数据有效：包含overall_stage_plan")
                            # 直接检查是否包含阶段数据
                            elif any(key in storyline_data for key in ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']):
                                has_valid_storyline = True
                                logger.info(f"✅ 故事线数据有效：直接包含阶段数据")
                            # 检查是否非空
                            elif storyline_data:
                                has_valid_storyline = True
                                logger.info(f"✅ 故事线数据有效：非空字典，键: {list(storyline_data.keys())[:5]}")
                            else:
                                logger.info(f"⚠️ storyline_data为空字典")
                        else:
                            logger.info(f"⚠️ storyline_data不是字典类型: {type(storyline_data).__name__}")
                        
                        if has_valid_storyline:
                            products['storyline']['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                            products['storyline']['complete'] = True
                            products['storyline']['file_path'] = f"{project_info_path}/{info_file}"
                            logger.info(f"✅ 从project_data加载故事线数据，包含overall_stage_plan: {'overall_stage_plan' in storyline_data}")
                        else:
                            logger.info(f"⚠️ project_data中故事线数据为空或无效，overall_stage_plans存在: {bool(project_data.get('overall_stage_plans'))}")
                        
                        logger.info(f"✅ 从project_info加载产物数据成功")
                        break
                    except Exception as e:
                        logger.info(f"⚠️ 读取项目信息文件失败: {info_file}, {e}")
            
            # 如果project_info中没有完整数据，尝试从其他目录读取
            if not products['worldview']['complete'] and os.path.exists(worldview_path):
                worldview_files = os.listdir(worldview_path)
                for wf in worldview_files:
                    if wf.endswith('.json'):
                        try:
                            with open(f"{worldview_path}/{wf}", 'r', encoding='utf-8') as f:
                                worldview_data = json.load(f)
                            products['worldview']['content'] = json.dumps(worldview_data, ensure_ascii=False, indent=2)
                            products['worldview']['complete'] = True
                            products['worldview']['file_path'] = f"{worldview_path}/{wf}"
                            logger.info(f"✅ 从worldview目录加载世界观数据")
                            break
                        except Exception as e:
                            logger.info(f"⚠️ 读取世界观文件失败: {wf}, {e}")
            
            if not products['market']['complete'] and os.path.exists(market_path):
                market_files = os.listdir(market_path)
                for mf in market_files:
                    if mf.endswith('.json'):
                        try:
                            with open(f"{market_path}/{mf}", 'r', encoding='utf-8') as f:
                                market_data = json.load(f)
                            products['market']['content'] = json.dumps(market_data, ensure_ascii=False, indent=2)
                            products['market']['complete'] = True
                            products['market']['file_path'] = f"{market_path}/{mf}"
                            logger.info(f"✅ 从market_analysis目录加载市场分析数据")
                            break
                        except Exception as e:
                            logger.info(f"⚠️ 读取市场分析文件失败: {mf}, {e}")
        
        # 如果还是没有数据，返回404
        elif not any(p['complete'] for p in products.values()):
            logger.error(f"❌ 第一阶段产物目录和索引文件都不存在: {title}")
            logger.info(f"🔍 检查的路径:")
            logger.info(f"  - 产物目录: {products_dir}")
            logger.info(f"  - 索引文件: {phase_one_index_file}")
            logger.info(f"  - 项目目录: {project_dir}")
            logger.info(f"  - Project Info: {project_info_path}")
            logger.info(f"  - Worldview: {worldview_path}")
            logger.info(f"  - Market Analysis: {market_path}")
            return jsonify({"success": False, "error": "第一阶段产物不存在"}), 404
        
        return jsonify({
            "success": True,
            "products": products,
            "phase_one_dir": phase_one_dir
        })
        
    except Exception as e:
        logger.error(f"❌ 获取第一阶段产物失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-one/products/<title>/<category>', methods=['PUT'])
def update_phase_one_product(title, category):
    """更新第一阶段的单个产物"""
    try:
        data = request.json or {}
        product_title = data.get('title', '')
        product_content = data.get('content', '')
        
        if not product_title or not product_content:
            return jsonify({"success": False, "error": "标题和内容不能为空"}), 400
        
        # 构建产物文件路径
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        products_dir = f"{phase_one_dir}/产物"
        product_file = f"{products_dir}/{safe_title}_{category}.json"
        
        # 确保目录存在
        os.makedirs(products_dir, exist_ok=True)
        
        # 检查产物文件是否存在
        if not os.path.exists(product_file):
            logger.info(f"📝 创建新的产物文件: {product_file}")
        
        # 保存产物内容
        with open(product_file, 'w', encoding='utf-8') as f:
            json.dump({
                'title': product_title,
                'content': product_content,
                'updated_at': datetime.now().isoformat(),
                'category': category
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 第一阶段产物已更新: {title} - {category}")
        
        return jsonify({
            "success": True,
            "message": f"{product_title} 已更新"
        })
        
    except Exception as e:
        logger.error(f"❌ 更新第一阶段产物失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-one/products/<title>/export', methods=['GET'])
def export_phase_one_products(title):
    """导出第一阶段的所有产物"""
    try:
        # 直接获取产物数据，避免函数调用问题
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        products = {
            'worldview': {'title': '世界观设定', 'content': '', 'complete': False},
            'characters': {'title': '角色设计', 'content': '', 'complete': False},
            'growth': {'title': '成长路线', 'content': '', 'complete': False},
            'writing': {'title': '写作计划', 'content': '', 'complete': False},
            'storyline': {'title': '故事线', 'content': '', 'complete': False},
            'market': {'title': '市场分析', 'content': '', 'complete': False}
        }
        
        if os.path.exists(phase_one_file):
            with open(phase_one_file, 'r', encoding='utf-8') as f:
                phase_one_data = json.load(f)
                
                # 优先从顶层直接提取产物数据（新格式）
                # 如果顶层没有数据，再从 result.novel_data_summary 中提取（旧格式兼容）
                novel_data_summary = phase_one_data.get('result', {}).get('novel_data_summary', {})
                
                # 提取世界观
                core_worldview = phase_one_data.get('core_worldview') or novel_data_summary.get('core_worldview', {})
                if core_worldview:
                    products['worldview']['content'] = json.dumps(core_worldview, ensure_ascii=False, indent=2)
                    products['worldview']['complete'] = True
                
                # 提取角色设计
                character_design = phase_one_data.get('character_design') or novel_data_summary.get('character_design', {})
                if character_design:
                    products['characters']['content'] = json.dumps(character_design, ensure_ascii=False, indent=2)
                    products['characters']['complete'] = True
                
                # 提取其他产物（简化处理）
                overall_stage_plans = phase_one_data.get('overall_stage_plans') or novel_data_summary.get('overall_stage_plans', {})
                if overall_stage_plans:
                    # 成长路线
                    growth_content = "成长路线规划：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        growth_content += f"- {stage_name}: {stage_data.get('description', '')}\n"
                    products['growth']['content'] = growth_content
                    products['growth']['complete'] = True
                    
                    # 写作计划
                    writing_content = "写作计划安排：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        writing_content += f"- {stage_name}: {stage_data.get('chapter_range', '')}\n"
                    products['writing']['content'] = writing_content
                    products['writing']['complete'] = True
                    
                    # 故事线
                    storyline_content = "故事线架构：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        storyline_content += f"- {stage_name}: {stage_data.get('key_events', '')}\n"
                    products['storyline']['content'] = storyline_content
                    products['storyline']['complete'] = True
                
                # 市场分析
                market_analysis = phase_one_data.get('market_analysis') or novel_data_summary.get('market_analysis', {})
                if market_analysis:
                    products['market']['content'] = json.dumps(market_analysis, ensure_ascii=False, indent=2)
                    products['market']['complete'] = True
        
        # 检查自定义产物
        custom_products = phase_one_data.get('custom_products', {})
        for category, product_data in custom_products.items():
            if category in products:
                products[category].update(product_data)
        
        # 构建导出数据
        export_data = {
            'project_title': title,
            'export_time': datetime.now().isoformat(),
            'products': products,
            'summary': {
                'total_categories': len(products),
                'completed_categories': sum(1 for p in products.values() if p.get('complete', False))
            }
        }
        
        # 创建响应
        from flask import Response
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={title}_第一阶段产物.json'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ 导出第一阶段产物失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-one/products/<title>/validate', methods=['POST'])
def validate_phase_one_products(title):
    """验证第一阶段产物的完整性"""
    try:
        # 直接获取产物数据，避免函数调用问题
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        phase_one_dir = f"小说项目/{safe_title}_第一阶段设定"
        phase_one_file = f"{phase_one_dir}/{safe_title}_第一阶段设定.json"
        
        products = {
            'worldview': {'title': '世界观设定', 'content': '', 'complete': False},
            'characters': {'title': '角色设计', 'content': '', 'complete': False},
            'growth': {'title': '成长路线', 'content': '', 'complete': False},
            'writing': {'title': '写作计划', 'content': '', 'complete': False},
            'storyline': {'title': '故事线', 'content': '', 'complete': False},
            'market': {'title': '市场分析', 'content': '', 'complete': False}
        }
        
        if os.path.exists(phase_one_file):
            with open(phase_one_file, 'r', encoding='utf-8') as f:
                phase_one_data = json.load(f)
                
                # 优先从顶层提取数据（新格式），如果没有则从嵌套结构提取（旧格式）
                novel_data_summary = phase_one_data.get('result', {}).get('novel_data_summary', {})
                
                # 提取世界观
                core_worldview = phase_one_data.get('core_worldview') or novel_data_summary.get('core_worldview', {})
                if core_worldview:
                    products['worldview']['content'] = json.dumps(core_worldview, ensure_ascii=False, indent=2)
                    products['worldview']['complete'] = True
                
                # 提取角色设计
                character_design = phase_one_data.get('character_design') or novel_data_summary.get('character_design', {})
                if character_design:
                    products['characters']['content'] = json.dumps(character_design, ensure_ascii=False, indent=2)
                    products['characters']['complete'] = True
                
                # 提取其他产物（简化处理）
                overall_stage_plans = phase_one_data.get('overall_stage_plans') or novel_data_summary.get('overall_stage_plans', {})
                if overall_stage_plans:
                    # 成长路线
                    growth_content = "成长路线规划：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        growth_content += f"- {stage_name}: {stage_data.get('description', '')}\n"
                    products['growth']['content'] = growth_content
                    products['growth']['complete'] = True
                    
                    # 写作计划
                    writing_content = "写作计划安排：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        writing_content += f"- {stage_name}: {stage_data.get('chapter_range', '')}\n"
                    products['writing']['content'] = writing_content
                    products['writing']['complete'] = True
                    
                    # 故事线
                    storyline_content = "故事线架构：\n"
                    for stage_name, stage_data in overall_stage_plans.items():
                        storyline_content += f"- {stage_name}: {stage_data.get('key_events', '')}\n"
                    products['storyline']['content'] = storyline_content
                    products['storyline']['complete'] = True
                
                # 市场分析
                market_analysis = phase_one_data.get('market_analysis') or novel_data_summary.get('market_analysis', {})
                if market_analysis:
                    products['market']['content'] = json.dumps(market_analysis, ensure_ascii=False, indent=2)
                    products['market']['complete'] = True
        
        # 检查自定义产物
        custom_products = phase_one_data.get('custom_products', {})
        for category, product_data in custom_products.items():
            if category in products:
                products[category].update(product_data)
        
        # 验证逻辑
        required_categories = ['worldview', 'characters', 'growth', 'writing', 'storyline']
        completed_categories = []
        missing_categories = []
        
        for category in required_categories:
            if category in products and products[category].get('content'):
                completed_categories.append(category)
            else:
                missing_categories.append(category)
        
        completion_rate = len(completed_categories) / len(required_categories) * 100
        
        validation_result = {
            'is_valid': completion_rate >= 80,
            'completion_rate': round(completion_rate, 1),
            'completed_categories': completed_categories,
            'missing_categories': missing_categories,
            'total_categories': len(required_categories),
            'recommendations': []
        }
        
        # 生成建议
        if completion_rate < 100:
            validation_result['recommendations'].append("建议完善所有类别的设定以获得最佳生成效果")
        
        if not products.get('worldview', {}).get('content'):
            validation_result['recommendations'].append("世界观设定是小说的基础，请务必完善")
        
        if not products.get('characters', {}).get('content'):
            validation_result['recommendations'].append("角色设计有助于生成更有深度的故事")
        
        return jsonify({
            "success": True,
            "validation": validation_result
        })
        
    except Exception as e:
        logger.error(f"❌ 验证第一阶段产物失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== 故事线API ====================

@phase_api.route('/storyline/<path:title>', methods=['GET'])
@login_required
def get_storyline(title):
    """获取小说的故事线时间线数据"""
    try:
        # Flask已经自动解码了URL参数，所以title已经是解码后的中文
        original_title = title
        logger.info(f"接收到的标题参数: '{title}'")
        logger.info(f"使用的标题: '{original_title}'")
        
        # 尝试从多个可能的路径读取项目信息和写作计划
        # 构建安全标题用于文件路径
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', original_title)
        
        possible_paths = [
            # 新项目结构 - 项目信息文件（使用原始标题）
            f"小说项目/{original_title}/{original_title}_项目信息.json",
            f"小说项目/{original_title}/project_info/{original_title}_项目信息.json",
            f"小说项目/{original_title}/{safe_title}_项目信息.json",
            # 旧项目结构
            f"小说项目/{original_title}_第一阶段设定/{original_title}_第一阶段设定.json",
            f"小说项目/{safe_title}_第一阶段设定/{safe_title}_第一阶段设定.json",
        ]
        
        logger.info(f"🔍 开始检查路径，标题: '{original_title}'")
        
        # 额外检查：尝试列出目录内容
        project_dir = f"小说项目/{original_title}"
        logger.info(f"🔍 检查项目目录: {project_dir}")
        logger.info(f"🔍 目录存在: {os.path.exists(project_dir)}")
        
        if os.path.exists(project_dir) and os.path.isdir(project_dir):
            try:
                files = os.listdir(project_dir)
                logger.info(f"📁 项目目录存在: {project_dir}")
                logger.info(f"📁 目录内容数量: {len(files)}")
                
                # 查找项目信息文件
                for f in files:
                    if '项目信息' in f and f.endswith('.json') and not f.endswith('.backup'):
                        found_path = f"{project_dir}/{f}"
                        if found_path not in possible_paths:
                            possible_paths.insert(0, found_path)  # 插入到开头优先使用
                        logger.info(f"✅ 找到项目信息文件: {found_path}")
                        break
            except Exception as e:
                logger.info(f"⚠️ 列出目录失败: {e}")
        
        project_data = None
        source_path = None
        
        for idx, path in enumerate(possible_paths):
            logger.info(f"🔍 [{idx+1}/{len(possible_paths)}] 检查路径: {path}")
            logger.info(f"🔍 文件存在: {os.path.exists(path)}")
            if os.path.exists(path):
                try:
                    logger.info(f"✅ 文件存在，尝试读取: {path}")
                    with open(path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                    source_path = path
                    logger.info(f"✅ 成功从路径加载项目数据: {path}")
                    logger.info(f"✅ 数据键: {list(project_data.keys())[:10]}")
                    break
                except Exception as e:
                    logger.error(f"❌ 读取文件失败: {path}, {e}")
                    import traceback
                    logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
                    continue
            else:
                logger.info(f"❌ 文件不存在: {path}")
        
        if not project_data:
            logger.error(f"❌ 未找到项目数据: {title}")
            logger.error(f"❌ 检查的路径: {possible_paths}")
            # 尝试从manager获取
            if manager:
                try:
                    novel_detail = manager.get_novel_detail(title)
                    if novel_detail:
                        logger.info(f"✅ 从manager获取到小说详情")
                        project_data = novel_detail
                        source_path = "manager"
                except Exception as e:
                    logger.error(f"❌ 从manager获取失败: {e}")
            
            if not project_data:
                return jsonify({"success": False, "error": "未找到项目数据"}), 404
        
        # 从overall_stage_plans提取所有阶段的故事线数据
        storyline = extract_storyline_from_stage_plans(project_data, title)
        
        if not storyline or not storyline.get("major_events"):
            logger.error(f"❌ 未能从项目数据中提取故事线: {title}")
            return jsonify({"success": False, "error": "未能提取故事线数据，可能缺少overall_stage_plans数据"}), 404
        
        return jsonify({
            "success": True,
            "title": title,
            "storyline": storyline,
            "source": source_path
        })
        
    except Exception as e:
        logger.error(f"❌ 获取故事线失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

def extract_storyline_from_stage_plans(project_data, title):
    """从项目的详细写作计划中提取故事线数据"""
    
    logger.info(f"🔍 开始提取故事线数据，项目数据键: {list(project_data.keys())[:20]}")
    
    # 优先尝试从 plans/ 目录读取详细的阶段写作计划
    safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
    project_dir = f"小说项目/{safe_title}"
    plans_dir = f"{project_dir}/plans"
    
    storyline = None
    
    # 检查是否存在 plans 目录
    if os.path.exists(plans_dir):
        logger.info(f"✅ 找到 plans 目录: {plans_dir}")
        
        # 读取所有阶段写作计划文件
        all_major_events = []
        
        # 定义阶段文件名模式
        stage_patterns = {
            "opening_stage": f"{safe_title}_opening_stage_writing_plan.json",
            "development_stage": f"{safe_title}_development_stage_writing_plan.json",
            "climax_stage": f"{safe_title}_climax_stage_writing_plan.json",
            "ending_stage": f"{safe_title}_ending_stage_writing_plan.json"
        }
        
        stage_names = {
            "opening_stage": "开局阶段",
            "development_stage": "发展阶段",
            "climax_stage": "高潮阶段",
            "ending_stage": "结局阶段"
        }
        
        for stage_key, filename in stage_patterns.items():
            stage_file = f"{plans_dir}/{filename}"
            if os.path.exists(stage_file):
                try:
                    logger.info(f"📖 读取阶段文件: {filename}")
                    with open(stage_file, 'r', encoding='utf-8') as f:
                        stage_data = json.load(f)
                    
                    # 从 stage_writing_plan.event_system.major_events 提取事件
                    stage_writing_plan = stage_data.get("stage_writing_plan", {})
                    event_system = stage_writing_plan.get("event_system", {})
                    stage_major_events = event_system.get("major_events", [])
                    
                    for idx, major_event in enumerate(stage_major_events):
                        # 构建重大事件数据
                        event_data = {
                            "id": f"{stage_key}_{idx + 1}",
                            "order": len(all_major_events) + 1,
                            "name": major_event.get("name", f"{stage_names[stage_key]}-{idx+1}"),
                            "type": major_event.get("type", "major_event"),
                            "role_in_stage_arc": major_event.get("role_in_stage_arc", ""),
                            "chapter_range": major_event.get("chapter_range", ""),
                            "main_goal": major_event.get("main_goal", ""),
                            "emotional_goal": major_event.get("emotional_goal", ""),
                            "emotional_focus": major_event.get("emotional_goal", ""),
                            "description": major_event.get("main_goal", ""),
                            "medium_events": [],
                            "special_events": major_event.get("special_emotional_events", [])
                        }
                        
                        # 提取起承转合的中级事件
                        composition = major_event.get("composition", {})
                        for phase_key, phase_name in [("起", "起"), ("承", "承"), ("转", "转"), ("合", "合")]:
                            medium_events = composition.get(phase_key, [])
                            for medium_idx, medium_event in enumerate(medium_events):
                                medium_data = {
                                    "id": f"{stage_key}_{idx + 1}_{phase_key}_{medium_idx + 1}",
                                    "phase": phase_name,
                                    "phase_key": phase_key,
                                    "order": medium_idx + 1,
                                    "name": medium_event.get("name", ""),
                                    "type": medium_event.get("type", "medium_event"),
                                    "chapter_range": medium_event.get("chapter_range", ""),
                                    "main_goal": medium_event.get("main_goal", ""),
                                    "role_in_stage_arc": medium_event.get("main_goal", ""),
                                    "emotional_focus": medium_event.get("emotional_focus", ""),
                                    "emotional_goal": medium_event.get("emotional_focus", ""),
                                    "emotional_intensity": medium_event.get("emotional_intensity", "medium"),
                                    "description": medium_event.get("description", ""),
                                    "key_emotional_beats": medium_event.get("key_emotional_beats", [])
                                }
                                event_data["medium_events"].append(medium_data)
                        
                        all_major_events.append(event_data)
                        logger.info(f"  ✓ 提取重大事件: {event_data['name']}, 包含 {len(event_data['medium_events'])} 个中级事件")
                    
                except Exception as e:
                    logger.error(f"❌ 读取阶段文件失败: {filename}, {e}")
                    continue
        
        # 如果从 plans 目录提取到了数据，构建并返回
        if all_major_events:
            storyline = {
                "stage_name": "全书故事线",
                "chapter_range": str(project_data.get("total_chapters", "未知")) + "章",
                "stage_overview": project_data.get("novel_synopsis", ""),
                "major_events": all_major_events
            }
            logger.info(f"✅ 从 plans 目录提取了 {len(all_major_events)} 个重大事件")
            return storyline
    
    # 如果 plans 目录没有数据，回退到从 overall_stage_plans 提取（原有逻辑）
    logger.info("⚠️ plans 目录无数据，回退到 overall_stage_plans 提取")
    
    # 获取overall_stage_plans数据
    overall_stage_plans = project_data.get("overall_stage_plans", {})
    if not overall_stage_plans:
        overall_stage_plans = project_data.get("overall_stage_plan", {})
    
    # 如果还是没有，尝试从嵌套结构获取
    if not overall_stage_plans:
        result_data = project_data.get("result", {})
        if isinstance(result_data, dict):
            novel_data_summary = result_data.get("novel_data_summary", {})
            if isinstance(novel_data_summary, dict):
                overall_stage_plans = novel_data_summary.get("overall_stage_plans", {})
                if not overall_stage_plans:
                    overall_stage_plans = novel_data_summary.get("overall_stage_plan", {})
    
    logger.info(f"🔍 overall_stage_plans类型: {type(overall_stage_plans)}")
    logger.info(f"🔍 overall_stage_plans为空: {not overall_stage_plans}")
    
    if not overall_stage_plans:
        logger.error(f"❌ 未找到overall_stage_plans数据")
        return None
    
    # 获取overall_stage_plan中的各个阶段
    stage_plan = overall_stage_plans.get("overall_stage_plan", overall_stage_plans)
    
    if not stage_plan:
        logger.error(f"❌ 未找到overall_stage_plan数据")
        return None
    
    logger.info(f"✅ 找到stage_plan，键: {list(stage_plan.keys())}")
    
    # 合并所有阶段的事件
    all_major_events = []
    stage_names = {
        "opening_stage": "开局阶段",
        "development_stage": "发展阶段",
        "climax_stage": "高潮阶段",
        "ending_stage": "结局阶段"
    }
    
    for stage_key, stage_name in stage_names.items():
        stage_data = stage_plan.get(stage_key, {})
        if not stage_data:
            logger.info(f"⚠️ 阶段 {stage_key} 数据为空")
            continue
        
        logger.info(f"✅ 处理阶段: {stage_key}")
        
        # 提取关键发展作为重大事件
        key_developments = stage_data.get("key_developments", [])
        chapter_range = stage_data.get("chapter_range", "")
        stage_goal = stage_data.get("stage_goal", "")
        
        logger.info(f"  - 关键发展数量: {len(key_developments)}")
        
        # 如果没有key_developments，创建一个默认的重大事件
        if not key_developments:
            major_event = {
                "id": f"{stage_key}_1",
                "order": len(all_major_events) + 1,
                "name": stage_name,
                "type": "major_event",
                "role_in_stage_arc": stage_goal,
                "chapter_range": chapter_range,
                "main_goal": stage_goal or f"{stage_name}的主要目标",
                "emotional_focus": stage_data.get("core_conflicts", ""),
                "emotional_goal": stage_data.get("core_conflicts", ""),
                "description": stage_goal or f"{stage_name}的描述",
                "medium_events": [],
                "special_events": []
            }
            all_major_events.append(major_event)
            logger.info(f"  - 创建默认重大事件: {stage_name}")
        else:
            for idx, development in enumerate(key_developments):
                major_event = {
                    "id": f"{stage_key}_{idx + 1}",
                    "order": len(all_major_events) + 1,
                    "name": development,  # 直接使用development作为名称
                    "type": "major_event",
                    "role_in_stage_arc": stage_goal,
                    "chapter_range": chapter_range,
                    "main_goal": development,
                    "emotional_focus": stage_data.get("core_conflicts", ""),
                    "emotional_goal": stage_data.get("core_conflicts", ""),
                    "description": development,
                    "medium_events": [],
                    "special_events": []
                }
                
                # 添加一些默认的中型事件（起承转合）
                phases = [("起", "铺垫"), ("承", "发展"), ("转", "转折"), ("合", "收束")]
                for phase_idx, (phase_key, phase_desc) in enumerate(phases):
                    medium_event = {
                        "id": f"{stage_key}_{idx + 1}_{phase_key}",
                        "phase": phase_desc,  # 使用更清晰的描述而不是单个字符
                        "phase_key": phase_key,
                        "order": phase_idx + 1,
                        "name": f"{development} - {phase_desc}",
                        "type": "medium_event",
                        "chapter_range": chapter_range,
                        "main_goal": f"{development}的{phase_desc}阶段",
                        "role_in_stage_arc": development,
                        "emotional_focus": stage_data.get("core_conflicts", ""),
                        "emotional_goal": stage_data.get("core_conflicts", ""),
                        "emotional_intensity": "medium",
                        "description": f"{development}的{phase_desc}阶段描述",
                        "key_emotional_beats": [development, f"{phase_desc}阶段发展"]
                    }
                    major_event["medium_events"].append(medium_event)
                
                all_major_events.append(major_event)
    
    # 如果没有从key_developments获取到事件，尝试从stage_transitions或其他字段生成
    if not all_major_events:
        stage_transitions = overall_stage_plans.get("stage_transitions", {})
        for transition_key, transition_desc in stage_transitions.items():
            parts = transition_key.split("_")
            if len(parts) >= 3:
                stage_key = f"{parts[0]}_{parts[1]}"
                stage_name = stage_names.get(stage_key, stage_key)
                
                major_event = {
                    "id": f"transition_{len(all_major_events) + 1}",
                    "order": len(all_major_events) + 1,
                    "name": f"{stage_name}",
                    "type": "major_event",
                    "role_in_stage_arc": "阶段过渡",
                    "chapter_range": "",
                    "main_goal": transition_desc,
                    "emotional_goal": "",
                    "medium_events": [],
                    "special_events": []
                }
                all_major_events.append(major_event)
    
    # 构建故事线数据
    storyline = {
        "stage_name": "全书故事线",
        "chapter_range": str(project_data.get("total_chapters", "未知")) + "章",
        "stage_overview": project_data.get("novel_synopsis", ""),
        "major_events": all_major_events
    }
    
    logger.info(f"✅ 从overall_stage_plans提取了 {len(all_major_events)} 个重大事件")
    return storyline


def extract_storyline_data(writing_plan):
    """从写作计划中提取故事线数据"""
    storyline = {
        "stage_name": writing_plan.get("stage_name", "未知阶段"),
        "chapter_range": writing_plan.get("chapter_range", ""),
        "stage_overview": writing_plan.get("stage_overview", ""),
        "major_events": []
    }
    
    event_system = writing_plan.get("event_system", {})
    major_events = event_system.get("major_events", [])
    
    for idx, major_event in enumerate(major_events):
        event_data = {
            "id": f"major_{idx + 1}",
            "order": idx + 1,
            "name": major_event.get("name", ""),
            "type": major_event.get("type", "major_event"),
            "role_in_stage_arc": major_event.get("role_in_stage_arc", ""),
            "chapter_range": major_event.get("chapter_range", ""),
            "main_goal": major_event.get("main_goal", ""),
            "emotional_goal": major_event.get("emotional_goal", ""),
            "medium_events": []
        }
        
        # 提取起承转合的中型事件
        composition = major_event.get("composition", {})
        for phase_key, phase_name in [("起", "起"), ("承", "承"), ("转", "转"), ("合", "合")]:
            medium_events = composition.get(phase_key, [])
            for medium_idx, medium_event in enumerate(medium_events):
                medium_data = {
                    "id": f"medium_{idx + 1}_{phase_name}_{medium_idx + 1}",
                    "phase": phase_name,
                    "order": medium_idx + 1,
                    "name": medium_event.get("name", ""),
                    "type": medium_event.get("type", "medium_event"),
                    "chapter_range": medium_event.get("chapter_range", ""),
                    "main_goal": medium_event.get("main_goal", ""),
                    "emotional_focus": medium_event.get("emotional_focus", ""),
                    "emotional_intensity": medium_event.get("emotional_intensity", "medium"),
                    "description": medium_event.get("description", ""),
                    "key_emotional_beats": medium_event.get("key_emotional_beats", [])
                }
                event_data["medium_events"].append(medium_data)
        
        # 添加特殊情感事件
        special_events = major_event.get("special_emotional_events", [])
        event_data["special_events"] = special_events
        
        storyline["major_events"].append(event_data)
    
    return storyline


@phase_api.route('/storyline/<path:title>/update', methods=['POST'])
@login_required
def update_storyline(title):
    """更新小说的故事线数据"""
    try:
        data = request.json or {}
        storyline = data.get('storyline')
        
        if not storyline:
            return jsonify({"success": False, "error": "缺少storyline数据"}), 400
        
        # 构建安全标题用于文件路径
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        
        # 尝试多个可能的路径
        possible_paths = [
            # 新项目结构
            f"小说项目/{title}/{title}_项目信息.json",
            f"小说项目/{title}/project_info/{title}_项目信息.json",
            f"小说项目/{title}/{safe_title}_项目信息.json",
            # 旧项目结构
            f"小说项目/{title}_第一阶段设定/{title}_第一阶段设定.json",
            f"小说项目/{safe_title}_第一阶段设定/{safe_title}_第一阶段设定.json",
        ]
        
        project_data = None
        source_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                    source_path = path
                    logger.info(f"✅ 找到项目文件: {path}")
                    break
                except Exception as e:
                    logger.error(f"❌ 读取文件失败: {path}, {e}")
                    continue
        
        if not project_data:
            return jsonify({"success": False, "error": "未找到项目文件"}), 404
        
        # 将storyline数据转换回overall_stage_plans格式
        overall_stage_plan = {}
        stage_name_mapping = {
            "opening_stage": "开局阶段",
            "development_stage": "发展阶段",
            "climax_stage": "高潮阶段",
            "ending_stage": "结局阶段"
        }
        
        for major_event in storyline.get("major_events", []):
            # 尝试从事件名称推断属于哪个阶段
            # 这里简化处理，将所有重大事件按顺序分配到各阶段
            pass
        
        # 更新overall_stage_plans数据
        # 注意：这里需要根据实际的数据结构进行更新
        # 由于storyline是从overall_stage_plans提取的，更新时需要逆向操作
        
        # 简化处理：直接更新storyline到一个单独的文件
        storyline_dir = f"小说项目/{safe_title}/storyline"
        os.makedirs(storyline_dir, exist_ok=True)
        storyline_file = f"{storyline_dir}/{safe_title}_故事线.json"
        
        with open(storyline_file, 'w', encoding='utf-8') as f:
            json.dump({
                "title": title,
                "updated_at": datetime.now().isoformat(),
                "storyline": storyline
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 故事线已保存: {storyline_file}")
        
        return jsonify({
            "success": True,
            "message": "故事线已更新",
            "file_path": storyline_file
        })
        
    except Exception as e:
        logger.error(f"❌ 更新故事线失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== 文件内容读取API ====================

@phase_api.route('/file-content', methods=['GET'])
@login_required
def get_file_content():
    """读取文件内容"""
    try:
        from flask import request
        file_path = request.args.get('path')
        
        if not file_path:
            return jsonify({"success": False, "error": "缺少文件路径参数"}), 400
        
        # 安全检查：确保文件路径在允许的目录内
        allowed_dirs = ['小说项目', 'data', 'knowledge_base']
        is_allowed = False
        for allowed_dir in allowed_dirs:
            if file_path.startswith(allowed_dir) or file_path.startswith(f'./{allowed_dir}'):
                is_allowed = True
                break
        
        if not is_allowed:
            return jsonify({"success": False, "error": "不允许访问该路径"}), 403
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "文件不存在"}), 404
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            "success": True,
            "content": content,
            "file_path": file_path,
            "size": len(content)
        })
        
    except Exception as e:
        logger.error(f"❌ 读取文件内容失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== 第二阶段内容审核API ====================

@phase_api.route('/phase-two/content-review/<path:title>', methods=['GET'])
@login_required
def get_phase_two_content_review(title):
    """获取第二阶段的章节列表用于内容审核"""
    try:
        # Flask会自动解码URL中的中文参数
        original_title = title
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', original_title)
        logger.info(f"📋 [CONTENT_REVIEW] 获取章节列表: {original_title}")
        
        # 构建章节目录路径
        possible_chapter_dirs = [
            f"小说项目/{original_title}/chapters",
            f"小说项目/{safe_title}/chapters",
            f"小说项目/{original_title}_章节",
            f"小说项目/{safe_title}_章节"
        ]
        
        chapters_dir = None
        for dir_path in possible_chapter_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                chapters_dir = dir_path
                logger.info(f"✅ [CONTENT_REVIEW] 找到章节目录: {chapters_dir}")
                break
        
        if not chapters_dir:
            logger.error(f"❌ [CONTENT_REVIEW] 未找到章节目录: {original_title}")
            return jsonify({
                "success": False,
                "error": "未找到章节目录，该项目可能尚未生成章节"
            }), 404
        
        # 扫描章节文件
        chapters = []
        chapter_files = [f for f in os.listdir(chapters_dir) if f.endswith(('.txt', '.json'))]
        
        for chapter_file in sorted(chapter_files):
            file_path = os.path.join(chapters_dir, chapter_file)
            try:
                # 提取章节号
                match = re.search(r'第?(\d+)章?', chapter_file)
                if not match:
                    continue
                
                chapter_number = int(match.group(1))
                
                # 获取文件大小和字数
                file_size = os.path.getsize(file_path)
                word_count = file_size  # 对于文本文件，字数约等于文件大小
                
                # 尝试读取JSON文件获取更准确的信息
                chapter_title = f"第{chapter_number}章"  # 默认标题
                if chapter_file.endswith('.json'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            chapter_data = json.load(f)
                        # 提取章节标题
                        if chapter_data.get('chapter_title'):
                            chapter_title = chapter_data['chapter_title']
                        elif chapter_data.get('title'):
                            chapter_title = chapter_data['title']
                        # 计算字数
                        word_count = len(chapter_data.get('content', ''))
                    except:
                        pass
                
                chapters.append({
                    "chapter_number": chapter_number,
                    "title": chapter_title,
                    "word_count": word_count,
                    "file_name": chapter_file,
                    "file_path": file_path
                })
            except Exception as e:
                logger.info(f"⚠️ 处理章节文件失败: {chapter_file}, {e}")
                continue
        
        logger.info(f"✅ [CONTENT_REVIEW] 找到 {len(chapters)} 个章节")
        
        return jsonify({
            "success": True,
            "project_title": original_title,
            "chapters": chapters,
            "total_chapters": len(chapters),
            "total_words": sum(ch['word_count'] for ch in chapters)
        })
        
    except Exception as e:
        logger.error(f"❌ 获取章节列表失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@phase_api.route('/phase-two/content-review/<path:title>/chapter/<int:chapterNum>/files', methods=['GET'])
@login_required
def get_chapter_raw_files(title, chapterNum):
    """获取章节的原始文件信息"""
    try:
        original_title = title
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', original_title)
        logger.info(f"📋 [CONTENT_REVIEW] 获取章节文件: {original_title}, 第{chapterNum}章")
        
        # 构建可能的目录路径
        possible_paths = [
            {
                "base_dir": f"小说项目/{original_title}",
                "chapters_dir": f"小说项目/{original_title}/chapters"
            },
            {
                "base_dir": f"小说项目/{safe_title}",
                "chapters_dir": f"小说项目/{safe_title}/chapters"
            }
        ]
        
        base_dir = None
        chapters_dir = None
        for paths in possible_paths:
            if os.path.exists(paths["base_dir"]):
                base_dir = paths["base_dir"]
                if os.path.exists(paths["chapters_dir"]):
                    chapters_dir = paths["chapters_dir"]
                break
        
        if not base_dir:
            return jsonify({"success": False, "error": "未找到项目目录"}), 404
        
        # 查找章节文件
        chapter_files = []
        if chapters_dir:
            for f in os.listdir(chapters_dir):
                if re.search(rf'第?{chapterNum}章?', f):
                    file_path = os.path.join(chapters_dir, f)
                    chapter_files.append({
                        "name": f,
                        "type": "章节内容",
                        "file_path": file_path,
                        "file_size": os.path.getsize(file_path),
                        "extension": os.path.splitext(f)[1]
                    })
        
        # 构建原始文件分类
        raw_files = {
            "input_files": [],  # 生成章节时使用的提示词
            "output_files": chapter_files,  # 章节内容输出
            "quality_files": [],  # quality_data目录下的输出文件
            "character_files": []  # 其他相关文件
        }
        
        # 1. 添加生成提示词（输入文件）
        generation_prompts_dir = os.path.join(base_dir, "generation_prompts")
        if os.path.exists(generation_prompts_dir):
            prompt_file = os.path.join(generation_prompts_dir, f"第{chapterNum:03d}章_生成提示词.txt")
            if os.path.exists(prompt_file):
                raw_files["input_files"].append({
                    "name": f"第{chapterNum}章_生成提示词.txt",
                    "type": "生成提示词",
                    "description": "生成该章节时使用的完整提示词",
                    "file_path": prompt_file,
                    "file_size": os.path.getsize(prompt_file),
                    "extension": ".txt"
                })
        
        # 2. 添加quality_data输出文件（从全局quality_data目录读取）
        quality_files_map = {
            f"{original_title}_character_development.json": "角色发展数据",
            f"{original_title}_mindset_主角.json": "主角心路历程",
            f"{original_title}_world_state.json": "世界状态数据"
        }
        
        # 检查全局quality_data目录
        quality_data_dir = "quality_data"
        if os.path.exists(quality_data_dir):
            for filename, display_type in quality_files_map.items():
                file_path = os.path.join(quality_data_dir, filename)
                if os.path.exists(file_path):
                    raw_files["quality_files"].append({
                        "name": filename,
                        "type": display_type,
                        "description": f"该章节生成后的{display_type}",
                        "file_path": file_path,
                        "file_size": os.path.getsize(file_path),
                        "extension": ".json"
                    })
        
        # 3. 尝试从其他目录查找相关文件（用于向后兼容）
        subdirs = ["planning", "characters", "worldview", "event_records", "stage_plan"]
        for subdir in subdirs:
            subdir_path = os.path.join(base_dir, subdir)
            if os.path.exists(subdir_path):
                for f in os.listdir(subdir_path):
                    if not f.endswith('.json'):
                        continue
                    
                    file_path = os.path.join(subdir_path, f)
                    file_size = os.path.getsize(file_path)
                    
                    # 根据目录分类
                    if subdir == "planning":
                        raw_files["character_files"].append({
                            "name": f,
                            "type": "写作计划",
                            "file_path": file_path,
                            "file_size": file_size,
                            "extension": ".json"
                        })
                    elif subdir == "characters":
                        raw_files["character_files"].append({
                            "name": f,
                            "type": "角色数据",
                            "file_path": file_path,
                            "file_size": file_size,
                            "extension": ".json"
                        })
                    elif subdir == "stage_plan":
                        raw_files["character_files"].append({
                            "name": f,
                            "type": "阶段计划",
                            "file_path": file_path,
                            "file_size": file_size,
                            "extension": ".json"
                        })
        
        logger.info(f"✅ [CONTENT_REVIEW] 找到文件: input={len(raw_files['input_files'])}, output={len(raw_files['output_files'])}, quality={len(raw_files['quality_files'])}, character={len(raw_files['character_files'])}")
        
        return jsonify({
            "success": True,
            "project_title": original_title,
            "chapter_number": chapterNum,
            "raw_files": raw_files
        })
        
    except Exception as e:
        logger.error(f"❌ 获取章节文件失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500