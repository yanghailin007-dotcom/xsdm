"""
小说生成相关API路由
"""
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
        """获取所有小说项目"""
        try:
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
            if not novel_detail:
                return jsonify({"error": "小说不存在"}), 404
            
            # 标准化数据结构，确保前端能够正确获取核心设定信息
            standardized_detail = standardize_novel_data_structure(novel_detail)
            
            return jsonify(standardized_detail)
        except Exception as e:
            logger.error(f"❌ 获取小说详情失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/project/<title>/chapter/<int:chapter_num>', methods=['GET'])
    def get_chapter_detail(title, chapter_num):
        """获取章节详情"""
        try:
            chapter_detail = manager.get_chapter_detail(title, chapter_num)
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
            # 获取最新项目的章节
            projects = manager.get_novel_projects()
            if projects:
                latest_project = projects[0]
                novel_detail = manager.get_novel_detail(latest_project["title"])
                if novel_detail:
                    chapters = []
                    generated_chapters = novel_detail.get("generated_chapters", {})
                    for chapter_num in sorted(generated_chapters.keys()):
                        chapter_data = generated_chapters[chapter_num]
                        chapters.append({
                            "chapter_number": chapter_num,
                            "title": chapter_data.get("outline", {}).get("章节标题", f"第{chapter_num}章"),
                            "word_count": len(chapter_data.get("content", "")),
                            "score": chapter_data.get("assessment", {}).get("整体评分", 0),
                            "status": "completed",
                            "generated_at": chapter_data.get("generation_time", "")
                        })
                    return jsonify(chapters)
            return jsonify([])
        except Exception as e:
            logger.error(f"❌ 获取章节列表失败: {e}")
            return jsonify([])

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