"""
小说生成相关API路由
"""
import json
from flask import jsonify, request
from datetime import datetime

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.managers.novel_manager import NovelGenerationManager


def register_novel_routes(app, manager: NovelGenerationManager):
    """注册小说相关API路由"""
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """健康检查"""
        return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

    @app.route('/api/start-generation', methods=['POST'])
    @login_required
    def start_generation():
        """开始生成小说"""
        try:
            config = request.json or {}
            # 🔥 添加当前用户名到 config，确保用户隔离路径正确
            from web.utils.path_utils import get_current_username
            config['username'] = get_current_username()
            config['user_id'] = session.get('user_id')
            task_id = manager.start_generation(config)
            logger.info(f"✅ 生成任务已启动: {task_id}")
            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": "小说生成任务已启动，正在后台处理",
                "status": "started"
            })
        except Exception as e:
            logger.error(f"❌ 启动生成任务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/task/<task_id>/status', methods=['GET'])
    def get_task_status(task_id):
        """获取任务状态"""
        try:
            status = manager.get_task_status(task_id)
            return jsonify(status)
        except Exception as e:
            logger.error(f"❌ 获取任务状态失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/task/<task_id>/progress', methods=['GET'])
    def get_task_progress(task_id):
        """获取任务进度"""
        try:
            progress = manager.get_task_progress(task_id)
            return jsonify(progress)
        except Exception as e:
            logger.error(f"❌ 获取任务进度失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/tasks', methods=['GET'])
    def get_all_tasks():
        """获取所有任务"""
        try:
            tasks = manager.get_all_tasks()
            return jsonify(tasks)
        except Exception as e:
            logger.error(f"❌ 获取任务列表失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/generate-chapters', methods=['POST'])
    def generate_chapters_legacy():
        """兼容性端点：生成章节（使用新的后台任务系统）"""
        try:
            data = request.json or {}
            
            # 🔥 添加当前用户名到 data，确保用户隔离路径正确
            from web.utils.path_utils import get_current_username
            data['username'] = get_current_username()
            data['user_id'] = session.get('user_id')

            # 使用新的启动系统
            task_id = manager.start_generation(data)

            logger.info(f"✅ 生成任务已启动: {task_id}")

            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": "小说生成已启动，使用新版本后台处理系统",
                "note": "请使用 /api/task/{task_id}/status 获取实时状态"
            })

        except Exception as e:
            logger.error(f"❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500

    # 小说项目管理 API
    @app.route('/api/projects', methods=['GET'])
    def get_novel_projects():
        """获取所有作品（长篇+短篇）"""
        try:
            # 1. 获取长篇项目
            projects = manager.get_novel_projects()
            # 为每个项目添加状态信息
            for project in projects:
                total_chapters = project.get("total_chapters", 0)
                completed_chapters = project.get("completed_chapters", 0)
                if completed_chapters >= total_chapters and total_chapters > 0:
                    project["status"] = "completed"
                elif completed_chapters > 0:
                    project["status"] = "generating"
                else:
                    project["status"] = "paused"
                # 标记为长篇
                project["is_short_story"] = False
                project["type"] = "novel"
            
            # 2. 获取短篇作品
            from web.utils.path_utils import list_user_short_stories, get_current_username
            username = get_current_username()
            short_stories = list_user_short_stories(username)
            
            # 转换短篇格式以兼容前端
            for story in short_stories:
                story_obj = {
                    "novel_title": story["title"],
                    "title": story["title"],
                    "synopsis": story.get("synopsis", ""),
                    "is_short_story": True,
                    "type": "short_story",
                    "status": "completed",  # 短篇默认已完成
                    "owner": story["owner"],
                    "completed_chapters": story.get("chapter_count", 0),
                    "total_chapters": story.get("chapter_count", 0),
                    "word_count": story.get("word_count", 0),
                    "average_score": None,
                    "project_type": "short_story",
                    "type_display": "短篇"
                }
                projects.append(story_obj)
            
            return jsonify(projects)
        except Exception as e:
            logger.error(f"❌ 获取项目列表失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/dashboard-stats', methods=['GET'])
    @login_required
    def get_dashboard_stats():
        """获取仪表板统计数据"""
        try:
            projects = manager.get_novel_projects()
            
            total_projects = len(projects)
            total_chapters = sum(p.get("completed_chapters", 0) for p in projects)
            total_words = 0
            completed_projects = 0
            active_tasks = 0
            
            # 计算总字数和完成项目数
            for project in projects:
                total_words += project.get("word_count", 0)
                project_total_chapters = project.get("total_chapters", 0)
                project_completed_chapters = project.get("completed_chapters", 0)
                
                if project_completed_chapters >= project_total_chapters and project_total_chapters > 0:
                    completed_projects += 1
            
            # 获取活动任务数
            active_tasks = len([task for task in manager.get_all_tasks()
                               if task.get("status") in ["initializing", "generating", "generator_ready", "creative_ready"]])
            
            return jsonify({
                "total_projects": total_projects,
                "total_chapters": total_chapters,
                "total_words": total_words,
                "completed_projects": completed_projects,
                "active_tasks": active_tasks
            })
        except Exception as e:
            logger.error(f"❌ 获取统计数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/stats', methods=['GET'])
    @login_required
    def get_stats():
        """获取首页统计数据（兼容接口）"""
        try:
            projects = manager.get_novel_projects()
            
            total_projects = len(projects)
            total_chapters = sum(p.get("completed_chapters", 0) for p in projects)
            
            # 获取活动任务数
            active_tasks = len([task for task in manager.get_all_tasks()
                               if task.get("status") in ["initializing", "generating", "generator_ready", "creative_ready"]])
            
            return jsonify({
                "total_projects": total_projects,
                "total_chapters": total_chapters,
                "active_tasks": active_tasks
            })
        except Exception as e:
            logger.error(f"❌ 获取统计数据失败: {e}")
            return jsonify({"total_projects": 0, "total_chapters": 0, "active_tasks": 0}), 500

    @app.route('/api/generation/<task_id>/stop', methods=['POST'])
    @login_required
    def stop_generation_task(task_id):
        """停止生成任务"""
        try:
            logger.info(f"🛑 请求停止生成任务: {task_id}")
            
            # 获取所有任务
            all_tasks = manager.get_all_tasks()
            task_found = False
            
            for task in all_tasks:
                if task.get('id') == task_id or task.get('task_id') == task_id:
                    task_found = True
                    # 将任务状态设置为 stopped
                    task['status'] = 'stopped'
                    task['stopped_at'] = datetime.now().isoformat()
                    logger.info(f"✅ 任务 {task_id} 已标记为停止")
                    break
            
            if task_found:
                return jsonify({
                    'success': True,
                    'message': '任务已停止',
                    'task_id': task_id
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '任务不存在或已完成'
                }), 404
                
        except Exception as e:
            logger.error(f"❌ 停止任务失败: {e}")
            return jsonify({
                'success': False,
                'message': f'停止任务失败: {str(e)}'
            }), 500

    @app.route('/api/project/<title>', methods=['GET'])
    def get_novel_detail(title):
        """获取小说详情"""
        try:
            novel_detail = manager.get_novel_detail(title)
            
            # 🔥 关键修复：检查缓存的项目是否有章节数据
            has_chapters = False
            if novel_detail:
                generated_chapters = novel_detail.get('generated_chapters', {})
                has_chapters = len(generated_chapters) > 0 if generated_chapters else False
            
            # 如果项目不在缓存中，或者没有章节数据，尝试重新加载
            if not novel_detail or not has_chapters:
                reason = "不在缓存中" if not novel_detail else "没有章节数据"
                logger.info(f"[NOVEL_API] 项目 {title} {reason}，尝试重新加载...")
                manager.load_existing_novels()
                novel_detail = manager.get_novel_detail(title)
            
            if not novel_detail:
                return jsonify({"error": "小说不存在"}), 404
            
            # 标准化数据结构，确保前端能够正确获取核心设定信息
            standardized_detail = standardize_novel_data_structure(novel_detail)
            
            return jsonify(standardized_detail)
        except Exception as e:
            logger.error(f"❌ 获取小说详情失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/novel-info', methods=['GET'])
    def get_novel_info():
        """获取小说信息（前端兼容性接口）"""
        try:
            title = request.args.get('title')
            if not title:
                return jsonify({"success": False, "error": "缺少title参数"}), 400
            
            novel_detail = manager.get_novel_detail(title)
            
            # 如果项目不在缓存中，尝试重新加载
            if not novel_detail:
                logger.info(f"[NOVEL_API] 项目 {title} 不在缓存中，尝试重新加载...")
                manager.load_existing_novels()
                novel_detail = manager.get_novel_detail(title)
            
            if not novel_detail:
                return jsonify({"success": False, "error": "小说不存在"}), 404
            
            # 构造前端期望的数据格式
            generated_chapters = novel_detail.get('generated_chapters', {})
            # 🔥 修复：支持简化结构（顶层 total_chapters）和旧结构（current_progress.total_chapters）
            total_chapters = (
                novel_detail.get('total_chapters', 0) or 
                novel_detail.get('current_progress', {}).get('total_chapters', 0) or
                novel_detail.get('progress', {}).get('total_chapters', 0) or
                0
            )
            completed_chapters = len(generated_chapters)
            
            return jsonify({
                "success": True,
                "novel": {
                    "title": novel_detail.get('novel_title', title),
                    "total_chapters": total_chapters,
                    "completed_chapters": completed_chapters,
                    "status": "completed" if completed_chapters >= total_chapters and total_chapters > 0 else "generating"
                }
            })
        except Exception as e:
            logger.error(f"❌ 获取小说信息失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/project/<title>/chapters', methods=['GET'])
    def get_project_chapters(title):
        """获取项目章节列表"""
        try:
            # 先尝试从内存读取
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                manager.load_existing_novels()
                novel_detail = manager.get_novel_detail(title)
            
            chapters = []
            if novel_detail and novel_detail.get("generated_chapters"):
                generated = novel_detail.get("generated_chapters", {})
                for num in sorted(generated.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                    ch = generated[num]
                    chapters.append({
                        "number": int(num) if str(num).isdigit() else num,
                        "title": ch.get("title") or ch.get("chapter_title") or "",
                        "word_count": ch.get("word_count", 0)
                    })
            
            # 如果内存中没有，从文件系统扫描
            if not chapters:
                try:
                    from pathlib import Path
                    import json, re
                    from flask import session
                    from web.utils.path_utils import find_novel_project
                    
                    username = session.get('username')
                    project_path = find_novel_project(title, username)
                    
                    if project_path:
                        chapters_dir = Path(project_path) / "chapters"
                    else:
                        # 回退到旧方式
                        from src.config.path_config import path_config
                        paths = path_config.get_project_paths(title, username=username)
                        chapters_dir = Path(paths.get("chapters_dir", ""))
                    
                    if chapters_dir.exists():
                        files = sorted(
                            list(chapters_dir.glob("chapter_*.json")) +
                            list(chapters_dir.glob("第*.json"))
                        )
                        for f in files:
                            try:
                                data = json.loads(f.read_text(encoding='utf-8'))
                                num = data.get("chapter_number", 0)
                                if not num:
                                    # 尝试从文件名解析
                                    m = re.search(r'chapter_(\d+)', f.name) or re.search(r'第(\d+)章', f.name)
                                    num = int(m.group(1)) if m else 0
                                chapters.append({
                                    "number": num,
                                    "title": data.get("title", data.get("chapter_title", f"第{num}章")),
                                    "word_count": data.get("word_count", 0)
                                })
                            except Exception:
                                continue
                        chapters.sort(key=lambda x: x["number"])
                except Exception as e:
                    logger.warning(f"从文件系统读取章节列表失败: {e}")
            
            return jsonify({
                "success": True,
                "title": title,
                "chapters": chapters
            })
        except Exception as e:
            logger.error(f"❌ 获取章节列表失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/project/<title>/chapter/<int:chapter_num>', methods=['GET'])
    def get_chapter_detail(title, chapter_num):
        """获取章节详情"""
        try:
            chapter_detail = manager.get_chapter_detail(title, chapter_num)
            # 🔥 如果内存中没有，尝试重新加载项目后再读取
            if not chapter_detail:
                manager.load_existing_novels()
                chapter_detail = manager.get_chapter_detail(title, chapter_num)
            
            # 巧灯修复：如果内存中还是没有，尝试从文件系统读取
            if not chapter_detail:
                try:
                    from pathlib import Path
                    from flask import session
                    from web.utils.path_utils import find_novel_project
                    
                    username = session.get('username')
                    project_path = find_novel_project(title, username)
                    
                    if project_path:
                        chapters_dir = Path(project_path) / "chapters"
                        possible_files = [
                            chapters_dir / f"chapter_{chapter_num}.json",
                            chapters_dir / f"chapter_{chapter_num:03d}.json",
                            chapters_dir / f"第{chapter_num}章.json",
                        ]
                        
                        chapter_file = None
                        for f in possible_files:
                            if f.exists():
                                chapter_file = f
                                break
                        
                        if not chapter_file and chapters_dir.exists():
                            import re
                            for f in chapters_dir.glob("*.json"):
                                match = re.search(r'chapter_(\d+)', f.name) or re.search(r'第(\d+)章', f.name)
                                if match and int(match.group(1)) == chapter_num:
                                    chapter_file = f
                                    break
                        
                        if chapter_file and chapter_file.exists():
                            with open(chapter_file, 'r', encoding='utf-8') as f:
                                chapter_data = json.load(f)
                            chapter_detail = {
                                "chapter_number": chapter_data.get("chapter_number", chapter_num),
                                "number": chapter_data.get("chapter_number", chapter_num),
                                "title": chapter_data.get("title") or chapter_data.get("chapter_title", f"第{chapter_num}章"),
                                "chapter_title": chapter_data.get("title") or chapter_data.get("chapter_title", f"第{chapter_num}章"),
                                "content": chapter_data.get("content") or chapter_data.get("chapter_content", ""),
                                "chapter_content": chapter_data.get("content") or chapter_data.get("chapter_content", ""),
                                "word_count": chapter_data.get("word_count", 0),
                            }
                            logger.info(f"[章节详情] 从文件系统读取章节 {chapter_num}: {chapter_file}")
                except Exception as e:
                    logger.warning(f"[章节详情] 从文件系统读取失败: {e}")
            
            if not chapter_detail:
                return jsonify({"error": "章节不存在"}), 404

            # 获取质量数据
            quality_data = manager.get_chapter_quality_data(title, chapter_num)
            chapter_detail["quality_data"] = quality_data

            return jsonify(chapter_detail)
        except Exception as e:
            logger.error(f"❌ 获取章节详情失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/project/<title>/chapter/<int:chapter_num>/quality', methods=['GET'])
    def get_chapter_quality_data(title, chapter_num):
        """获取章节质量数据"""
        try:
            quality_data = manager.get_chapter_quality_data(title, chapter_num)
            return jsonify(quality_data)
        except Exception as e:
            logger.error(f"❌ 获取章节质量数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/project/<title>/export', methods=['GET'])
    @login_required
    def export_novel(title):
        """导出小说"""
        try:
            format_type = request.args.get('format', 'json')
            
            # 🔥 修复：获取当前用户名用于用户隔离路径
            username = session.get('username')
            result = manager.export_novel(title, format_type, username=username)

            if "error" in result:
                return jsonify(result), 400

            if format_type == "text":
                # 下载文本文件
                response = app.response_class(
                    result["content"],
                    mimetype='text/plain',
                    headers={"Content-Disposition": f"attachment; filename={result['title']}.txt"}
                )
                return response
            else:
                return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 导出小说失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/project/<title>/resume-generation', methods=['POST'])
    @login_required
    def resume_novel_generation(title):
        """续写小说生成"""
        try:
            data = request.json or {}
            from_chapter = data.get('from_chapter', 1)
            additional_chapters = data.get('additional_chapters', 10)
            
            logger.info(f"📖 开始续写小说: {title}")
            logger.info(f"从第{from_chapter}章开始，计划再生成{additional_chapters}章")
            
            # 检查小说是否存在
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"error": "小说不存在"}), 404
            
            # 检查是否可以续写（至少有一章已生成）
            generated_chapters = novel_detail.get("generated_chapters", {})
            if not generated_chapters:
                return jsonify({"error": "该小说还没有生成任何章节，无法续写"}), 400
            
            # 检查起始章节是否有效
            if from_chapter < 1:
                return jsonify({"error": "起始章节必须大于等于1"}), 400
            
            # 检查是否有足够的上下文数据
            max_chapter = max(generated_chapters.keys()) if generated_chapters else 0
            if from_chapter > max_chapter + 1:
                return jsonify({"error": f"起始章节{from_chapter}超出已生成范围，最大章节为{max_chapter}"}), 400
            
            # 启动续写任务
            task_id = manager.start_resume_generation(title, from_chapter, additional_chapters)
            
            logger.info(f"✅ 续写任务已启动: {task_id}")
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": f"续写任务已启动，正在后台处理",
                "from_chapter": from_chapter,
                "additional_chapters": additional_chapters,
                "status": "started"
            })
            
        except Exception as e:
            logger.error(f"❌ 启动续写任务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/project/<title>/can-resume', methods=['GET'])
    def check_can_resume(title):
        """检查小说是否可以续写"""
        try:
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"can_resume": False, "reason": "小说不存在"})
            
            generated_chapters = novel_detail.get("generated_chapters", {})
            if not generated_chapters:
                return jsonify({"can_resume": False, "reason": "该小说还没有生成任何章节"})
            
            max_chapter = max(generated_chapters.keys()) if generated_chapters else 0
            completed_chapters = len(generated_chapters)
            
            # 检查是否有足够的数据用于续写
            has_context_data = (
                novel_detail.get("selected_plan") and
                novel_detail.get("creative_seed") and
                novel_detail.get("core_worldview") and
                novel_detail.get("character_design")
            )
            
            return jsonify({
                "can_resume": has_context_data,
                "max_chapter": max_chapter,
                "completed_chapters": completed_chapters,
                "total_target_chapters": novel_detail.get("current_progress", {}).get("total_chapters", 0),
                "has_context_data": has_context_data
            })
            
        except Exception as e:
            logger.error(f"❌ 检查续写能力失败: {e}")
            return jsonify({"can_resume": False, "reason": str(e)}), 500

    # 兼容性API - 为了保持现有前端功能
    @app.route('/api/novel/summary', methods=['GET'])
    def get_novel_summary():
        """获取当前小说摘要（兼容性）"""
        try:
            # 优先获取最新的项目
            projects = manager.get_novel_projects()
            if projects:
                latest_project = projects[0]
                novel_detail = manager.get_novel_detail(latest_project["title"])
                if novel_detail:
                    return jsonify({
                        "title": novel_detail.get("novel_title", ""),
                        "synopsis": novel_detail.get("story_synopsis", ""),
                        "chapters_count": len(novel_detail.get("generated_chapters", {})),
                        "total_chapters": novel_detail.get("current_progress", {}).get("total_chapters", 0),
                        "progress": f"{len(novel_detail.get('generated_chapters', {}))}/{novel_detail.get('current_progress', {}).get('total_chapters', 0)}"
                    })
            
            # 如果没有项目，检查是否有正在进行的任务
            all_tasks = manager.get_all_tasks()
            active_tasks = [task for task in all_tasks
                           if task.get("status") in ["initializing", "generating", "generator_ready", "creative_ready"]]
            
            if active_tasks:
                latest_active_task = max(active_tasks,
                    key=lambda x: x.get("updated_at", ""))
                return jsonify({
                    "title": latest_active_task.get("title", "正在生成中..."),
                    "synopsis": latest_active_task.get("synopsis", ""),
                    "chapters_count": 0,
                    "total_chapters": latest_active_task.get("total_chapters", 0),
                    "progress": f"{latest_active_task.get('progress', 0)}%",
                    "status": latest_active_task.get("status", "unknown"),
                    "task_id": latest_active_task.get("task_id", "")
                })
            
            return jsonify({})
        except Exception as e:
            logger.error(f"❌ 获取小说摘要失败: {e}")
            return jsonify({})

    @app.route('/api/chapters', methods=['GET'])
    def get_chapters_list():
        """获取章节列表（兼容性）"""
        try:
            # 获取title参数
            title = request.args.get('title')
            
            novel_detail = None
            if title:
                # 根据title获取指定小说
                novel_detail = manager.get_novel_detail(title)
                # 如果不在缓存中，尝试重新加载
                if not novel_detail:
                    manager.load_existing_novels()
                    novel_detail = manager.get_novel_detail(title)
            else:
                # 兼容旧逻辑：获取最新项目
                projects = manager.get_novel_projects()
                if projects:
                    latest_project = projects[0]
                    novel_detail = manager.get_novel_detail(latest_project["title"])
            
            if novel_detail:
                chapters = []
                generated_chapters = novel_detail.get("generated_chapters", {})
                for chapter_num in sorted(generated_chapters.keys(), key=lambda x: int(x) if str(x).isdigit() else x):
                    chapter_data = generated_chapters[chapter_num]
                    # 获取章节标题，尝试多个可能的字段（按优先级）
                    title = None
                    
                    # 1. 直接从 chapter_data 取 title（最常用）
                    if not title:
                        title = chapter_data.get("title")
                    
                    # 2. 从 chapter_title 取
                    if not title:
                        title = chapter_data.get("chapter_title")
                    
                    # 3. 从 outline 取
                    if not title:
                        outline = chapter_data.get("outline") or {}
                        if outline:
                            title = outline.get("章节标题") or outline.get("title")
                    
                    # 4. 从 chapter_plan 取
                    if not title:
                        chapter_plan = chapter_data.get("chapter_plan") or {}
                        if chapter_plan:
                            title = chapter_plan.get("章节标题") or chapter_plan.get("title")
                    
                    # 5. 默认标题
                    if not title:
                        title = f"第{chapter_num}章"
                    
                    chapters.append({
                        "number": chapter_num,
                        "title": title,
                        "word_count": chapter_data.get("word_count") or len(chapter_data.get("content", "")),
                        "score": chapter_data.get("assessment", {}).get("整体评分", 0),
                        "status": "completed",
                        "generated_at": chapter_data.get("generation_time") or chapter_data.get("generated_at", "")
                    })
                return jsonify({"success": True, "chapters": chapters})
            
            return jsonify({"success": False, "error": "小说不存在", "chapters": []})
        except Exception as e:
            logger.error(f"❌ 获取章节列表失败: {e}")
            return jsonify({"success": False, "error": str(e), "chapters": []})

    @app.route('/api/chapter', methods=['GET'])
    def get_chapter_by_query():
        """获取章节详情（支持查询参数）"""
        try:
            title = request.args.get('title')
            chapter_num = request.args.get('chapter', type=int)
            
            if not title or not chapter_num:
                return jsonify({"success": False, "error": "缺少title或chapter参数"}), 400
            
            # 获取小说详情
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                # 尝试重新加载
                manager.load_existing_novels()
                novel_detail = manager.get_novel_detail(title)
            
            if not novel_detail:
                return jsonify({"success": False, "error": "小说不存在"}), 404
            
            # 从generated_chapters获取章节数据
            generated_chapters = novel_detail.get("generated_chapters", {})
            chapter_data = generated_chapters.get(str(chapter_num)) or generated_chapters.get(chapter_num)
            
            # 🔥 如果内存缓存中没有，回退到 get_chapter_detail（支持文件系统读取）
            if not chapter_data:
                chapter_data = manager.get_chapter_detail(title, chapter_num)
            
            if not chapter_data:
                return jsonify({"success": False, "error": "章节不存在"}), 404
            
            # 构造前端期望的格式
            # 获取章节标题，尝试多个可能的字段（按优先级）
            title = None
            
            # 1. 直接从 chapter_data 取 title（最常用）
            if not title:
                title = chapter_data.get("title")
            
            # 2. 从 chapter_title 取（有些版本用这个字段）
            if not title:
                title = chapter_data.get("chapter_title")
            
            # 3. 从 outline 取
            outline = chapter_data.get("outline") or {}
            if not title and outline:
                title = outline.get("章节标题") or outline.get("title")
            
            # 4. 从 chapter_plan 取
            chapter_plan = chapter_data.get("chapter_plan") or {}
            if not title and chapter_plan:
                title = chapter_plan.get("章节标题") or chapter_plan.get("title")
            
            # 5. 默认标题
            if not title:
                title = f"第{chapter_num}章"
            
            chapter = {
                "number": chapter_num,
                "title": title,
                "outline": outline,
                "content": chapter_data.get("content", ""),
                "word_count": chapter_data.get("word_count") or len(chapter_data.get("content", "")),
                "created_at": chapter_data.get("generation_time") or chapter_data.get("generated_at", ""),
                "status": chapter_data.get("status", "completed"),
                "file_path": chapter_data.get("file_path", ""),
                "prompts": chapter_data.get("prompts", ""),
                "ai_response": chapter_data.get("ai_response", ""),
                "assessment": chapter_data.get("assessment", {})
            }
            
            return jsonify({"success": True, "chapter": chapter})
        except Exception as e:
            logger.error(f"❌ 获取章节详情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/chapter/<int:chapter_num>', methods=['GET'])
    def get_chapter(chapter_num):
        """获取章节详情（兼容性）"""
        try:
            # 获取最新项目的指定章节
            projects = manager.get_novel_projects()
            if projects:
                latest_project = projects[0]
                chapter_detail = manager.get_chapter_detail(latest_project["title"], chapter_num)
                if chapter_detail:
                    return jsonify({
                        "chapter_number": chapter_num,
                        "title": chapter_detail.get("outline", {}).get("章节标题", f"第{chapter_num}章"),
                        "outline": chapter_detail.get("outline", {}),
                        "content": chapter_detail.get("content", ""),
                        "assessment": chapter_detail.get("assessment", {})
                    })
            return jsonify({"error": "章节不存在"}), 404
        except Exception as e:
            logger.error(f"❌ 获取章节详情失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/export-json', methods=['GET'])
    def export_json():
        """导出为 JSON（兼容性）"""
        try:
            # 获取最新项目
            projects = manager.get_novel_projects()
            if projects:
                latest_project = projects[0]
                novel_detail = manager.get_novel_detail(latest_project["title"])
                if novel_detail:
                    return jsonify({
                        "novel": {
                            "title": novel_detail.get("novel_title", ""),
                            "synopsis": novel_detail.get("story_synopsis", ""),
                            "total_chapters": novel_detail.get("current_progress", {}).get("total_chapters", 0),
                            "chapters_generated": len(novel_detail.get("generated_chapters", {}))
                        },
                        "chapters": novel_detail.get("generated_chapters", {}),
                        "exported_at": datetime.now().isoformat()
                    })
            return jsonify({"error": "没有找到小说项目"}), 404
        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")
            return jsonify({"error": str(e)}), 500

    # 原始数据API
    @app.route('/api/raw-chapter-data', methods=['GET'])
    def get_raw_chapter_data():
        """获取原始章节数据"""
        try:
            file_path = request.args.get('file_path')
            if not file_path:
                return jsonify({"error": "缺少file_path参数"}), 400

            # 安全检查：确保文件路径在允许的范围内
            allowed_dirs = [
                str(BASE_DIR / "小说项目"),
                str(BASE_DIR / "chapter_failures"),
                str(BASE_DIR / "quality_data"),
                str(BASE_DIR / "generated_images"),
                str(BASE_DIR / "logs")
            ]
            
            file_path = file_path.lstrip('/\\')
            full_path = BASE_DIR / file_path
            
            # 检查路径安全性
            if not any(str(full_path).startswith(allowed_dir) for allowed_dir in allowed_dirs):
                return jsonify({"error": "文件路径不被允许访问"}), 403

            if not full_path.exists():
                return jsonify({"error": "文件不存在"}), 404

            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试解析为JSON
            try:
                json_data = json.loads(content)
                return jsonify({
                    "success": True,
                    "file_path": str(full_path),
                    "file_size": len(content.encode('utf-8')),
                    "content_type": "json",
                    "data": json_data
                })
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始文本
                return jsonify({
                    "success": True,
                    "file_path": str(full_path),
                    "file_size": len(content.encode('utf-8')),
                    "content_type": "text",
                    "data": content
                })

        except Exception as e:
            logger.error(f"❌ 获取原始章节数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/quality-data/<title>', methods=['GET'])
    def get_quality_data(title):
        """获取小说的质量数据"""
        try:
            quality_data = manager.get_chapter_quality_data(title, 0)  # 获取所有质量数据
            return jsonify({
                "success": True,
                "title": title,
                "quality_data": quality_data
            })
        except Exception as e:
            logger.error(f"❌ 获取质量数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/project-materials/<title>', methods=['GET'])
    def get_project_materials(title):
        """获取项目一阶段产物材料（供设定结果页预览）"""
        try:
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                manager.load_existing_novels()
                novel_detail = manager.get_novel_detail(title)
            
            if not novel_detail:
                return jsonify({"success": False, "error": "小说不存在"}), 404
            
            # ---- worldview ----
            core_worldview = novel_detail.get("core_worldview", {})
            if isinstance(core_worldview, dict):
                worldview_parts = []
                if core_worldview.get("world_overview"):
                    worldview_parts.append(f"【世界观概述】\n{core_worldview['world_overview']}")
                if core_worldview.get("power_system"):
                    worldview_parts.append(f"\n【力量体系】\n{core_worldview['power_system']}")
                if core_worldview.get("world_rules"):
                    rules = core_worldview['world_rules']
                    if isinstance(rules, list):
                        worldview_parts.append("\n【世界规则】\n" + "\n".join(f"- {r}" for r in rules))
                    else:
                        worldview_parts.append(f"\n【世界规则】\n{rules}")
                if core_worldview.get("key_locations"):
                    locs = core_worldview['key_locations']
                    if isinstance(locs, list):
                        loc_str = "\n".join(f"- {loc.get('name','')}: {loc.get('description','')}" for loc in locs)
                        worldview_parts.append(f"\n【关键地点】\n{loc_str}")
                worldview_str = "\n\n".join(worldview_parts) if worldview_parts else ""
            else:
                worldview_str = str(core_worldview)
            
            # ---- characters ----
            character_design = novel_detail.get("character_design", {})
            characters_list = []
            if isinstance(character_design, dict):
                for key, char_data in character_design.items():
                    if not isinstance(char_data, dict):
                        continue
                    basic = char_data.get("basic_info", {})
                    name = basic.get("name") or key
                    desc_parts = []
                    if basic.get("identity"):
                        desc_parts.append(f"身份: {basic['identity']}")
                    if basic.get("appearance"):
                        desc_parts.append(f"外貌: {basic['appearance']}")
                    if char_data.get("background", {}).get("origin"):
                        desc_parts.append(f"背景: {char_data['background']['origin']}")
                    if char_data.get("personality", {}).get("core_traits"):
                        traits = char_data['personality']['core_traits']
                        if isinstance(traits, list):
                            desc_parts.append(f"核心特质: {', '.join(traits)}")
                        else:
                            desc_parts.append(f"核心特质: {traits}")
                    if char_data.get("growth_arc", {}).get("arc_summary"):
                        desc_parts.append(f"成长: {char_data['growth_arc']['arc_summary']}")
                    description = " | ".join(desc_parts) if desc_parts else "暂无详细描述"
                    characters_list.append({"name": name, "description": description})
            elif isinstance(character_design, list):
                characters_list = [
                    {"name": c.get("name", "未命名"), "description": c.get("description", "")}
                    for c in character_design if isinstance(c, dict)
                ]
            
            # ---- outline ----
            outline = (
                novel_detail.get("story_synopsis", "")
                or novel_detail.get("novel_synopsis", "")
                or novel_detail.get("novel_info", {}).get("synopsis", "")
            )
            if not outline:
                selected_plan = novel_detail.get("selected_plan") or novel_detail.get("novel_info", {}).get("selected_plan", {})
                if isinstance(selected_plan, dict):
                    outline = selected_plan.get("synopsis", "") or selected_plan.get("plot_outline", "")
            
            # ---- stage_plans ----
            stage_plans = {}
            overall_stage_plans = novel_detail.get("overall_stage_plans", {})
            if isinstance(overall_stage_plans, dict):
                # 可能包装在 overall_stage_plan 下
                osp = overall_stage_plans.get("overall_stage_plan", overall_stage_plans)
                stages_data = osp.get("stages") if isinstance(osp, dict) else None
                if isinstance(stages_data, list):
                    for stage in stages_data:
                        if not isinstance(stage, dict):
                            continue
                        stage_name = stage.get("stage_name", f"阶段{stage.get('stage_number','')}")
                        stage_plans[stage_name] = {
                            "chapter_range": stage.get("chapter_range", ""),
                            "stage_overview": stage.get("core_conflict", "") or stage.get("stage_overview", "")
                        }
                elif isinstance(stages_data, dict):
                    for stage_name, stage in stages_data.items():
                        if not isinstance(stage, dict):
                            continue
                        stage_plans[stage_name] = {
                            "chapter_range": stage.get("chapter_range", ""),
                            "stage_overview": stage.get("stage_overview", "") or stage.get("core_conflict", "")
                        }
            
            # 若 overall_stage_plans 为空，尝试 stage_writing_plans
            if not stage_plans:
                stage_writing_plans = novel_detail.get("stage_writing_plans", {})
                if isinstance(stage_writing_plans, dict):
                    for stage_name, stage in stage_writing_plans.items():
                        if not isinstance(stage, dict):
                            continue
                        plan = stage.get("stage_writing_plan", stage)
                        stage_plans[stage_name] = {
                            "chapter_range": plan.get("chapter_range", ""),
                            "stage_overview": plan.get("stage_overview", "")
                        }
            
            return jsonify({
                "success": True,
                "materials": {
                    "worldview": worldview_str,
                    "characters": characters_list,
                    "outline": outline,
                    "stage_plans": stage_plans
                }
            })
        except Exception as e:
            logger.error(f"❌ 获取项目材料失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


def standardize_novel_data_structure(novel_data):
    """标准化小说数据结构，确保前端能够正确获取核心设定信息"""
    
    # 创建标准化的数据结构
    standardized = {
        # 保留原始数据
        **novel_data,
        
        # 添加标准化的核心字段
        "novel_title": (
            novel_data.get("novel_title") or
            novel_data.get("novel_info", {}).get("title") or
            novel_data.get("title", "未命名小说")
        ),
        
        "story_synopsis": (
            novel_data.get("story_synopsis") or
            novel_data.get("novel_info", {}).get("synopsis") or
            novel_data.get("synopsis", "")
        ),
        
        # 标准化创意种子数据
        "creative_seed": (
            novel_data.get("creative_seed") or
            novel_data.get("novel_info", {}).get("creative_seed") or
            {}
        ),
        
        # 标准化核心设定
        "core_setting": (
            novel_data.get("core_setting") or
            extract_core_setting_from_paths(novel_data)
        ),
        
        # 标准化核心卖点
        "core_selling_points": (
            novel_data.get("core_selling_points") or
            extract_selling_points_from_paths(novel_data)
        ),
        
        # 标准化元数据
        "novel_metadata": {
            "coreSetting": (
                novel_data.get("core_setting") or
                extract_core_setting_from_paths(novel_data)
            ),
            "coreSellingPoints": (
                novel_data.get("core_selling_points") or
                extract_selling_points_from_paths(novel_data)
            ),
            "worldview": extract_worldview_from_paths(novel_data),
            "growthPlan": extract_growth_plan_from_paths(novel_data),
            "generation_timestamp": novel_data.get("timestamp", ""),
            **novel_data.get("novel_metadata", {})
        },
        
        # 确保章节数据存在
        "generated_chapters": (
            novel_data.get("generated_chapters") or
            novel_data.get("chapters", {})
        ),
        
        # 确保进度数据存在
        "current_progress": (
            novel_data.get("current_progress") or
            novel_data.get("progress", {})
        ),
        
        # 章节索引
        "chapter_index": (
            novel_data.get("chapter_index") or
            extract_chapter_index_from_paths(novel_data)
        )
    }
    
    # 确保creative_seed包含必要字段
    if not standardized["creative_seed"]:
        standardized["creative_seed"] = {}
    
    # 从selected_plan中提取核心设定到creative_seed
    selected_plan = (
        novel_data.get("selected_plan") or
        novel_data.get("novel_info", {}).get("selected_plan")
    )
    
    if selected_plan:
        if "coreSetting" not in standardized["creative_seed"] and selected_plan.get("core_direction"):
            standardized["creative_seed"]["coreSetting"] = selected_plan["core_direction"]
        
        if "coreSellingPoints" not in standardized["creative_seed"] and selected_plan.get("competitive_advantage"):
            standardized["creative_seed"]["coreSellingPoints"] = selected_plan["competitive_advantage"]
        
        if "completeStoryline" not in standardized["creative_seed"] and selected_plan.get("plot_outline"):
            standardized["creative_seed"]["completeStoryline"] = selected_plan["plot_outline"]
    
    return standardized


def extract_core_setting_from_paths(novel_data):
    """从多个可能路径提取核心设定"""
    paths = [
        ["novel_info", "creative_seed", "coreSetting"],
        ["creative_seed", "coreSetting"],
        ["novel_metadata", "coreSetting"],
        ["core_setting"],
        ["selected_plan", "core_direction"],
        ["novel_info", "selected_plan", "core_direction"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, str) and current.strip():
            return current.strip()
    
    return ""


def extract_selling_points_from_paths(novel_data):
    """从多个可能路径提取核心卖点"""
    paths = [
        ["novel_info", "creative_seed", "coreSellingPoints"],
        ["creative_seed", "coreSellingPoints"],
        ["novel_metadata", "coreSellingPoints"],
        ["core_selling_points"],
        ["selected_plan", "competitive_advantage"],
        ["novel_info", "selected_plan", "competitive_advantage"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current:
            if isinstance(current, list):
                return current
            elif isinstance(current, str) and current.strip():
                return current.strip()
    
    return ""


def extract_worldview_from_paths(novel_data):
    """从多个可能路径提取世界观"""
    paths = [
        ["novel_info", "creative_seed", "worldview"],
        ["creative_seed", "worldview"],
        ["worldview"],
        ["core_worldview", "result"]  # 如果是模拟响应
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, str) and current.strip():
            return current.strip()
    
    return ""


def extract_growth_plan_from_paths(novel_data):
    """从多个可能路径提取成长规划"""
    paths = [
        ["global_growth_plan"],
        ["growth_plan"],
        ["creative_seed", "growthPlan"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current:
            return current
    
    return {}


def extract_chapter_index_from_paths(novel_data):
    """从多个可能路径提取章节索引"""
    paths = [
        ["chapter_index"],
        ["novel_info", "chapter_index"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, list):
            return current
    
    # 如果没有章节索引，尝试从generated_chapters生成
    generated_chapters = novel_data.get("generated_chapters", {})
    if generated_chapters and isinstance(generated_chapters, dict):
        chapter_index = []
        for chapter_num, chapter_data in generated_chapters.items():
            if isinstance(chapter_data, dict):
                chapter_index.append({
                    "chapter_number": str(chapter_num),
                    "chapter_title": chapter_data.get("title", f"第{chapter_num}章"),
                    "filename": chapter_data.get("file_path", ""),
                    "quality_score": chapter_data.get("quality_score", 0),
                    "word_count": chapter_data.get("word_count", len(chapter_data.get("content", "")))
                })
        return chapter_index
    
    return []