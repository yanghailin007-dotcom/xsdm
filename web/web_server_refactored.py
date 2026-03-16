"""
重构后的Web服务器主文件
按功能模块拆分，提高代码可维护性
"""
import os
import sys
import logging

# 🔥 第一步：在任何其他模块导入之前，立即禁用所有可能打印base64的日志
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests.packages").setLevel(logging.CRITICAL)
logging.getLogger("requests.packages.urllib3").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.util").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.util.retry").setLevel(logging.CRITICAL)

# 清除所有handlers，阻止传播
for logger_name in ['requests', 'urllib3', 'requests.packages.urllib3', 'urllib3.connectionpool']:
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.propagate = False

import threading
import signal
import atexit
import time
from flask import Flask, request, jsonify
from datetime import datetime

# 🔥 确保项目根目录在 Python 路径中（支持直接运行此文件）
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 🔥 从独立模块导入停止标志功能（避免循环导入）
from web.stop_flag import (
    global_signal_handler, 
    is_stop_requested, 
    reset_stop_flag,
    set_stop_flag
)

# 🔥 在主线程中设置信号处理器
try:
    signal.signal(signal.SIGINT, global_signal_handler)
    try:
        print("OK: 全局信号处理器已设置（双击 Ctrl+C 退出）")
    except:
        pass
except ValueError as e:
    try:
        print(f"WARN: 无法设置信号处理器: {e}")
    except:
        pass

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 修复：补全缺失的括号

# 导入配置和工具
from web.web_config import (
    logger, FlaskConfig, APP_INFO, MODULE_STATUS,
    BASE_DIR, CREATIVE_IDEAS_FILE
)

# 初始化日志系统 - 按日期生成日志文件
from src.utils.logger import Logger
log_dir = os.path.join(BASE_DIR, 'logs')
try:
    # 检查现有日志文件
    from datetime import datetime
    today_log = os.path.join(log_dir, f"server_{datetime.now().strftime('%Y-%m-%d')}.log")
    existing_size = os.path.getsize(today_log) if os.path.exists(today_log) else 0
    
    Logger.enable_file_logging(log_file='logs/server_%Y-%m-%d.log', log_dir=log_dir)
    
    # 🔥 关键：记录启动信息到日志，方便诊断
    logger.info(f"="*60)
    logger.info(f"🚀 服务器启动 - PID: {os.getpid()}, Time: {datetime.now().isoformat()}")
    logger.info(f"📁 工作目录: {BASE_DIR}")
    logger.info(f"👤 启动用户: {os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))}")
    logger.info(f"📝 今日日志文件: {today_log}, 追加前大小: {existing_size} bytes")
    logger.info(f"✅ 日志系统已初始化 (追加模式)")
    logger.info(f"="*60)
except Exception as e:
    # 如果文件日志初始化失败，至少打印到控制台
    print(f"❌ 文件日志初始化失败: {e}")
    import traceback
    traceback.print_exc()
from web.auth import user_auth
from web.managers.novel_manager import NovelGenerationManager

# 导入番茄上传相关
try:
    from src.integration.fanqie_uploader import FanqieUploader
    fanqie_uploader = FanqieUploader()
    logger.info("✅ 番茄上传器加载成功")
except ImportError as e:
    logger.error(f"❌ 番茄上传器加载失败: {e}")
    fanqie_uploader = None

# 导入API路由模块
from web.api.novel_api import register_novel_routes
from web.api.creative_api import register_creative_routes
from web.api.creative_workshop_api import register_creative_workshop_routes
from web.api.cover_api import register_cover_routes
from web.api.phase_generation_api import register_phase_routes
from web.api.resume_generation_api import register_resume_routes
from web.api.worldview_api import register_worldview_routes
from web.api.video_generation_api import register_video_routes
from web.api.openai_video_api import register_openai_video_routes
from web.api.nanobanana_api import register_nanobanana_routes
from web.api.character_api import register_character_routes
from web.api.veo_video_api import register_veo_video_routes
from web.api.still_image_api import register_still_image_routes
from web.api.short_drama_api import register_short_drama_routes
from web.api.script_quality_check import register_script_quality_routes
from web.api.tts_api import register_tts_routes
from web.api.points_api import points_api
from web.api.export_api import export_api

# 导入页面路由模块
from web.routes.auth_routes import register_auth_routes, register_page_routes
from web.routes.custom_endpoint_routes import register_custom_endpoint_routes

# 导入注册API模块
from web.api.register_api import register_register_routes


def create_app():
    """创建Flask应用实例"""
    # 配置静态文件路径 - static文件夹在项目根目录下，而不是web目录下
    static_folder = os.path.join(BASE_DIR, 'static')
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(FlaskConfig)
    
    # 🔥 配置服务器端 session（支持多用户同时登录）
    try:
        from flask_session import Session
        # 使用文件系统存储 session（比客户端 cookie 更安全，支持多会话）
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = os.path.join(BASE_DIR, 'flask_session')
        app.config['SESSION_PERMANENT'] = False
        app.config['SESSION_USE_SIGNER'] = True
        app.config['SESSION_KEY_PREFIX'] = 'novel_session:'
        # 确保 session 目录存在
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        Session(app)
        logger.info("✅ 服务器端 session 已启用（支持多用户同时登录）")
    except ImportError as e:
        logger.warning(f"⚠️ flask-session 未安装或导入失败: {e}，使用默认客户端 session（同一浏览器窗口共享会话）")
    except Exception as e:
        logger.error(f"⚠️ 服务器端 session 初始化失败: {e}，使用默认客户端 session")

    # 🔑 初始化 JWT 认证（支持多账号切换）
    try:
        from web.jwt_auth import init_jwt
        init_jwt(app)
        logger.info("✅ JWT 认证已初始化（支持多账号切换）")
    except Exception as e:
        logger.error(f"⚠️ JWT 初始化失败: {e}")

    # 🔥 禁用静态文件缓存（开发环境）
    @app.after_request
    def add_header(response):
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # 🔥 禁用Flask的请求日志，避免打印base64图片数据
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    # 同时禁用Flask的请求日志记录器
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # 🔥 修复：先创建全局管理器实例，再注册依赖它的蓝图
    manager = NovelGenerationManager()
    # 🔥 关键：将manager存入app.config，供admin_api等模块使用
    app.config['MANAGER'] = manager
    logger.info(f"✅ 全局管理器已创建并注册: {id(manager)}")
    import sys
    sys.stdout.flush()
    
    # 🔥 注册 phase_api 蓝图（包含质量评估API）
    logger.info("🔄 开始注册 phase_api 蓝图...")
    sys.stdout.flush()
    try:
        logger.info("  正在导入 phase_generation_api...")
        from web.api import phase_generation_api
        logger.info("  ✅ phase_generation_api 导入成功")
        # 🔥 修复：先设置app，再设置config
        logger.info("  正在设置 phase_generation_api.app...")
        phase_generation_api.app = app  # 设置app引用
        logger.info("  正在设置 phase_generation_api.app.config...")
        phase_generation_api.app.config = app.config  # 共享配置
        logger.info("  正在设置 phase_generation_api.manager...")
        phase_generation_api.manager = manager  # 使用已创建的管理器
        # 注册蓝图中的所有路由
        logger.info("  ✅ phase_api 设置完成，将由 register_phase_routes 注册")
    except Exception as e:
        logger.error(f"⚠️ phase_api 蓝图注册失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")

    # 🔥 修复：在应用创建时初始化contract_api，确保单例
    try:
        from Chrome.automation.api.contract_api import ContractAPI
        app.config['CONTRACT_API'] = ContractAPI()
        logger.info(f"✅ 签约API已初始化: {id(app.config['CONTRACT_API'])}")
        logger.info(f"✅ 队列ID: task_queue={id(app.config['CONTRACT_API'].client.task_queue)}, result_queue={id(app.config['CONTRACT_API'].client.result_queue)}")
    except Exception as e:
        logger.error(f"❌ 签约API初始化失败: {e}")
        app.config['CONTRACT_API'] = None
    
    # 注册生成的图片访问路由
    @app.route('/generated_images/<path:filename>')
    def serve_generated_image(filename):
        """提供生成的图片文件访问"""
        from flask import send_from_directory
        generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
        return send_from_directory(generated_images_dir, filename)
    
    logger.info(f"✅ 配置图片访问路由: /generated_images/<filename>")
    
    # 🔥 代理访问生成的视频（支持VeO本地视频和远程视频）
    @app.route('/static/generated_videos/<path:filename>')
    def serve_generated_video(filename):
        """智能代理访问生成的视频文件
        
        优先级：
        1. VeO本地视频：从本地文件系统提供（优先）
        2. VeO远程视频：重定向到远程URL（备用）
        3. 其他本地视频：从本地文件系统提供
        """
        from flask import send_from_directory, redirect
        import re
        
        logger.info(f"📹 请求视频: {filename}")
        
        # 检查是否是VeO视频（格式：veo_xxxxxxxxx.mp4）
        if filename.startswith('veo_') and filename.endswith('.mp4'):
            # 提取任务ID（去掉veo_前缀和.mp4后缀）
            task_id = filename.replace('.mp4', '')
            logger.info(f"🔍 检测到VeO视频，任务ID: {task_id}")
            
            try:
                # 🔥 优先尝试本地文件
                local_video_dir = os.path.join(BASE_DIR, 'static', 'generated_videos')
                local_video_path = os.path.join(local_video_dir, filename)
                
                if os.path.exists(local_video_path):
                    logger.info(f"✅ 找到本地VeO视频: {local_video_path}")
                    return send_from_directory(local_video_dir, filename)
                
                logger.info(f"📥 本地文件不存在，尝试远程URL")
                
                # 如果本地不存在，从VeO管理器获取任务
                from src.managers.VeOVideoManager import get_veo_video_manager
                manager = get_veo_video_manager()
                task = manager.retrieve_generation(task_id)
                
                if task and task.result and task.result.videos:
                    video_url = task.result.videos[0].url
                    
                    # 检查URL是否是本地路径（已经下载）
                    if video_url.startswith('/static/'):
                        # 🔥 修复：检查本地文件是否真的存在
                        local_filename = video_url.split('/')[-1]
                        local_file_check = os.path.join(local_video_dir, local_filename)
                        
                        if os.path.exists(local_file_check):
                            logger.info(f"✅ 使用本地路径: {video_url}")
                            return send_from_directory(local_video_dir, local_filename)
                        else:
                            # 本地路径指向的文件不存在，可能是旧任务
                            logger.warning(f"⚠️ JSON中的本地路径不存在: {local_file_check}")
                            # 尝试从元数据中获取原始远程URL
                            if hasattr(task, 'metadata') and task.metadata:
                                original_url = task.metadata.get('original_url')
                                if original_url and (original_url.startswith('http://') or original_url.startswith('https://')):
                                    logger.info(f"🌐 重定向到原始远程URL: {original_url}")
                                    return redirect(original_url)
                            
                            # 没有远程URL可用，返回404
                            return jsonify({
                                "error": "Video file not found",
                                "message": f"Local video file not found and no remote URL available"
                            }), 404
                    else:
                        logger.info(f"🌐 重定向到远程URL: {video_url}")
                        # 重定向到真实的视频URL
                        return redirect(video_url)
                else:
                    logger.warning(f"⚠️ 未找到任务或视频结果: {task_id}")
                    return jsonify({
                        "error": "Video not found",
                        "message": f"VeO task {task_id} not found or not completed"
                    }), 404
                    
            except Exception as e:
                logger.error(f"❌ 获取VeO视频失败: {e}")
                return jsonify({
                    "error": "Internal error",
                    "message": str(e)
                }), 500
        
        # 如果不是VeO视频，尝试本地文件
        try:
            generated_videos_dir = os.path.join(BASE_DIR, 'generated_videos')
            
            # 检查是否是子目录格式（如：novel_name/shot_0.mp4）
            if '/' in filename or '\\' in filename:
                # 支持子目录
                return send_from_directory(generated_videos_dir, filename)
            else:
                # 直接在generated_videos目录下查找
                return send_from_directory(generated_videos_dir, filename)
                
        except FileNotFoundError:
            logger.warning(f"⚠️ 本地视频文件不存在: {filename}")
            return jsonify({
                "error": "File not found",
                "message": f"Video file {filename} not found"
            }), 404
    
    @app.route('/generated_videos/<path:filename>')
    def serve_generated_video_alt(filename):
        """备用的视频访问路由（不带static前缀）"""
        # 🔥 修复重定向循环：直接处理，不再调用 serve_generated_video
        from flask import send_from_directory
        import os
        
        # 先尝试从 static/generated_videos 目录读取
        static_video_path = os.path.join(BASE_DIR, 'static', 'generated_videos', filename)
        if os.path.exists(static_video_path):
            logger.info(f"✅ 从static目录提供视频: {filename}")
            return send_from_directory(os.path.join(BASE_DIR, 'static', 'generated_videos'), filename)
        
        # 再尝试从根目录的 generated_videos 读取
        root_video_path = os.path.join(BASE_DIR, 'generated_videos', filename)
        if os.path.exists(root_video_path):
            logger.info(f"✅ 从根目录提供视频: {filename}")
            return send_from_directory(os.path.join(BASE_DIR, 'generated_videos'), filename)
        
        # 如果都不存在，返回404
        logger.warning(f"⚠️ 视频文件不存在: {filename}")
        return jsonify({
            "error": "File not found",
            "message": f"Video file {filename} not found"
        }), 404
    
    logger.info(f"✅ 配置视频访问路由: /static/generated_videos/<filename>")
    logger.info(f"✅ 配置视频访问路由: /generated_videos/<filename>")
    
    # 注册路由
    # 1. 认证和页面路由
    register_auth_routes(app)
    register_page_routes(app)
    
    # 2. 用户注册API路由
    register_register_routes(app)
    
    # 2. 小说相关API路由
    register_novel_routes(app, manager)
    
    # 3. 创意文件API路由
    register_creative_routes(app, manager)
    
    # 3.5 创意工坊API路由（用户隔离的创意管理）
    register_creative_workshop_routes(app, manager)
    
    # 4. 封面生成API路由
    register_cover_routes(app)
    
    # 5. 番茄上传API路由（内联实现，因为相对较简单）
    register_fanqie_routes(app)
    
    # 6. 签约上传API路由（内联实现）
    register_contract_routes(app)
    
    # 7. 服务监控API路由（内联实现）
    register_monitoring_routes(app)
    
    # 8. 两阶段生成API路由
    register_phase_routes(app, manager)
    
    # 9. 恢复生成API路由
    register_resume_routes(app)
    
    # 10. 世界观可视化API路由
    register_worldview_routes(app)
    
    # 11. 视频生成API路由
    register_video_routes(app)
    
    # 12. Nano Banana文生图API路由（用于角色生成）
    register_nanobanana_routes(app)
    
    # 13. 角色管理API路由
    register_character_routes(app)
    
    # 14. OpenAI 标准视频生成 API 路由
    register_openai_video_routes(app)
    
    # 15. VeO 原生视频生成 API 路由（支持 base64 图片）
    register_veo_video_routes(app)
    
    # 16. 剧照图片素材库 API 路由
    register_still_image_routes(app)

    # 17. 短剧工作台 API 路由
    register_short_drama_routes(app)

    # 18. 剧本质量检查 API 路由
    register_script_quality_routes(app)

    # 19. TTS配音制作 API 路由
    register_tts_routes(app)

    # 20. 点数系统 API 路由
    app.register_blueprint(points_api)

    # 21. 支付系统 API 路由
    from web.api.payment_api import payment_api
    app.register_blueprint(payment_api)

    # 22. 导出功能 API 路由
    app.register_blueprint(export_api)
    logger.info("✅ export_api 导出功能已注册")

    # 23. 自定义端点 API 路由
    register_custom_endpoint_routes(app)
    logger.info("✅ custom_endpoint 自定义端点已注册")

    # 23.5. 优先级管理 API 路由
    from web.routes.priority_routes import register_priority_routes
    register_priority_routes(app)
    logger.info("✅ priority_routes 优先级管理已注册")

    # 24. 管理员 API 路由
    from web.api.admin_api import admin_api
    app.register_blueprint(admin_api)
    logger.info("✅ admin_api 管理员功能已注册")

    # 🔥 同步预初始化 NovelGenerator（确保服务器启动时完成）
    logger.info("🔄 开始预初始化 NovelGenerator...")
    try:
        import time
        import sys
        from pathlib import Path
        
        # 导入配置
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        try:
            import importlib.util
            config_path = project_root / "config" / "config.py"
            spec = importlib.util.spec_from_file_location("config_module", config_path)
            if spec is not None and spec.loader is not None:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                CONFIG = config_module.CONFIG
            else:
                raise ImportError("无法创建config模块规格")
        except Exception as e:
            logger.error(f"无法导入配置文件: {e}")
            CONFIG = {"defaults": {"total_chapters": 200, "chapters_per_batch": 3}}
        
        # 同步初始化 NovelGenerator
        start_time = time.time()
        from web.managers.novel_manager import get_novel_generator
        get_novel_generator(CONFIG)
        elapsed = time.time() - start_time
        logger.info(f"✅ NovelGenerator 预初始化完成，耗时: {elapsed:.2f}秒")
        
    except Exception as e:
        logger.error(f"❌ 预初始化 NovelGenerator 失败: {e}")
        import traceback
        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")

    return app, manager


def register_fanqie_routes(app):
    """注册番茄上传相关API路由"""
    
    @app.route('/api/fanqie/upload/check-prerequisites', methods=['GET'])
    def check_fanqie_upload_prerequisites():
        """检查番茄上传前提条件 - 手动浏览器模式"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            checks = fanqie_uploader.check_upload_prerequisites()
            
            # 手动浏览器模式：只检查系统环境，不检查浏览器状态
            system_ready = checks.get("temp_dir_writable", False) and checks.get("autopush_available", False)
            
            return jsonify({
                "success": True,
                "checks": checks,
                "ready": system_ready,
                "message": "系统环境检查通过。请手动启动浏览器并登录番茄小说网站。" if system_ready else "系统环境检查未通过，请检查失败项目",
                "manual_browser_required": True,
                "instructions": {
                    "step1": "1. 手动启动Chrome浏览器",
                    "step2": "2. 访问 https://fanqienovel.com 并登录账号",
                    "step3": "3. 进入作家专区",
                    "step4": "4. 选择小说开始上传（会从上次进度继续）"
                }
            })
        except Exception as e:
            logger.error(f"❌ 检查番茄上传前提条件失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/fanqie/upload/validate-novel/<title>', methods=['GET'])
    def validate_novel_for_fanqie_upload(title):
        """验证小说是否可以上传到番茄"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            validation_result = fanqie_uploader.validate_novel_for_upload(title)
            return jsonify({
                "success": True,
                "validation": validation_result
            })
        except Exception as e:
            logger.error(f"❌ 验证小说上传失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/fanqie/upload/start', methods=['POST'])
    def start_fanqie_upload():
        """启动番茄上传任务"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            data = request.json or {}
            novel_title = data.get('novel_title')
            
            logger.info(f"📝 收到上传请求，小说标题: {novel_title}")
            logger.info(f"📦 请求数据: {data}")
            
            if not novel_title:
                logger.error("❌ 400错误: 缺少小说标题")
                return jsonify({"success": False, "error": "缺少小说标题"}), 400
            
            # 验证小说是否可以上传
            logger.info(f"🔍 开始验证小说: {novel_title}")
            validation_result = fanqie_uploader.validate_novel_for_upload(novel_title)
            # 只打印摘要信息，不打印完整数据
            if validation_result.get("valid"):
                logger.info(f"✅ 验证通过，章节数: {validation_result.get('chapter_count', 0)}")
            else:
                logger.warning(f"⚠️ 验证失败: {validation_result.get('error', '未知错误')}")
            
            if not validation_result["valid"]:
                error_msg = validation_result.get("error", "验证失败")
                logger.error(f"❌ 400错误: 小说验证失败 - {error_msg}")
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 400
            
            # 启动上传任务
            upload_result = fanqie_uploader.start_upload_task(novel_title, data.get('upload_config', {}))
            
            if upload_result["success"]:
                return jsonify({
                    "success": True,
                    "task_id": upload_result["task_id"],
                    "message": upload_result["message"],
                    "chapter_count": upload_result["chapter_count"]
                })
            else:
                return jsonify({
                    "success": False,
                    "error": upload_result["error"]
                }), 500
                
        except Exception as e:
            logger.error(f"❌ 启动番茄上传任务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/fanqie/upload/tasks', methods=['GET'])
    def get_upload_tasks():
        """获取所有上传任务"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            tasks = fanqie_uploader.get_all_upload_tasks()
            
            return jsonify({
                "success": True,
                "tasks": tasks
            })
            
        except Exception as e:
            logger.error(f"❌ 获取上传任务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/fanqie/upload/status/<path:task_id>', methods=['GET'])
    def get_upload_status(task_id):
        """获取指定上传任务的状态"""
        try:
            from web.auth import login_required
            import urllib.parse
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            # Flask会自动解码路径参数，但为了确保中文字符正确处理，我们显式解码一次
            # 注意：Flask已经解码过一次，所以这里直接使用task_id即可
            status = fanqie_uploader.get_upload_status(task_id)
            
            if "error" in status:
                return jsonify({"success": False, "error": status["error"]}), 404
            
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"❌ 获取上传状态失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/fanqie/upload/trigger-scan', methods=['POST'])
    def trigger_fanqie_scan():
        """手动触发番茄上传扫描"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            # 这个功能暂时不实现，返回提示信息
            return jsonify({
                "success": False,
                "error": "手动触发扫描功能暂未实现，请使用单个小说上传功能"
            }), 501
            
        except Exception as e:
            logger.error(f"❌ 触发扫描失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/fanqie/upload/progress/<novel_title>', methods=['GET'])
    def get_fanqie_upload_progress(novel_title):
        """获取指定小说的上传进度"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            progress = fanqie_uploader.get_upload_progress(novel_title)
            
            if "error" in progress:
                return jsonify({"success": False, "error": progress["error"]}), 500
            
            return jsonify({
                "success": True,
                "progress": progress
            })

        except Exception as e:
            logger.error(f"❌ 获取上传进度失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


def register_quality_assessment_routes(app):
    """注册质量评估API路由"""

    @app.route('/api/quality-assessment/<path:novel_title>', methods=['GET'])
    def get_quality_assessment(novel_title):
        """获取小说的质量评估报告"""
        try:
            from web.auth import login_required
            from flask import session
            if 'logged_in' not in session:
                return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401

            from pathlib import Path
            import re
            import json

            # URL解码
            novel_title = re.sub(r'_|\+', ' ', novel_title)

            logger.info(f"[QUALITY_ASSESSMENT] 获取质量评估: {novel_title}")

            # 构建评估报告路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            report_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan_quality_report.json")

            if not report_path.exists():
                # 尝试从materials目录查找
                alt_report_path = Path(f"小说项目/{safe_title}/materials/phase_one_products/{safe_title}_quality_assessment.json")
                if alt_report_path.exists():
                    report_path = alt_report_path
                else:
                    return jsonify({
                        "success": False,
                        "error": "评估报告不存在",
                        "hint": "请先生成第一阶段设定"
                    }), 404

            # 读取评估报告
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            logger.info(f"[QUALITY_ASSESSMENT] 返回评估报告: {report.get('overall_score', 0)}/100")

            return jsonify({
                "success": True,
                "report": report
            })

        except Exception as e:
            logger.error(f"[QUALITY_ASSESSMENT] 获取评估报告失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/quality-assessment/trigger/<path:novel_title>', methods=['POST'])
    def trigger_quality_assessment(novel_title):
        """手动触发质量评估"""
        try:
            from web.auth import login_required
            from flask import session, request
            if 'logged_in' not in session:
                return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401

            from pathlib import Path
            import re
            from src.core.PlanQualityAssessor import PlanQualityAssessor
            from datetime import datetime

            # URL解码
            novel_title = re.sub(r'_|\+', ' ', novel_title)

            logger.info(f"[QUALITY_ASSESSMENT] 触发质量评估: {novel_title}")

            # 构建写作计划路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            plan_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan.json")

            if not plan_path.exists():
                return jsonify({
                    "success": False,
                    "error": "写作计划文件不存在"
                }), 404

            # 获取API密钥（用于AI评估）
            request_data = request.get_json() or {}
            use_deep_analysis = request_data.get('deep_analysis', True)

            # 🔥 使用APIClient进行AI评估（统一使用系统配置的API）
            from src.core.APIClient import APIClient
            from config.config import CONFIG
            api_client = APIClient(CONFIG)
            
            # 创建评估器并执行评估
            assessor = PlanQualityAssessor(api_client=api_client)
            result = assessor.assess(plan_path, use_deep_analysis=use_deep_analysis)

            # 转换为字典格式
            report = {
                "overall_score": result.overall_score,
                "readiness": result.readiness,
                "strengths": result.strengths,
                "issues": [
                    {
                        "category": i.category,
                        "severity": i.severity.value,
                        "location": i.location,
                        "description": i.description,
                        "suggestion": i.suggestion,
                        "auto_fixable": i.auto_fixable
                    }
                    for i in result.issues
                ],
                "summary": result.summary,
                "token_saved": result.token_saved,
                "assessment_time": datetime.now().isoformat()
            }

            logger.info(f"[QUALITY_ASSESSMENT] 评估完成: {report['overall_score']}/100")

            return jsonify({
                "success": True,
                "report": report
            })

        except Exception as e:
            logger.error(f"[QUALITY_ASSESSMENT] 触发评估失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


def register_contract_routes(app):
    """注册签约上传相关API路由"""
    
    # 🔥 修复：从app.config获取已初始化的API实例
    contract_api = app.config.get('CONTRACT_API')
    
    if contract_api is not None:
        contract_api_available = True
        logger.info("✅ 签约上传API加载成功")
        logger.info(f"✅ 使用API实例: {id(contract_api)}")
        logger.info(f"✅ 客户端队列ID: task_queue={id(contract_api.client.task_queue)}, result_queue={id(contract_api.client.result_queue)}")
    else:
        contract_api_available = False
        logger.warning("⚠️ 签约上传API未初始化")

    @app.route('/contract')
    def contract_page():
        """签约管理页面"""
        try:
            from web.auth import login_required
            from flask import render_template
            return render_template('contract_management.html')
        except Exception as e:
            logger.error(f"❌ 加载签约页面失败: {e}")
            return f"签约页面加载失败: {str(e)}", 500

    @app.route('/contract-test')
    def contract_test_page():
        """签约系统测试页面（简化版）"""
        try:
            from flask import render_template
            return render_template('contract_test.html')
        except Exception as e:
            logger.error(f"❌ 加载测试页面失败: {e}")
            return f"测试页面加载失败: {str(e)}", 500

    @app.route('/admin/users')
    def admin_users_page():
        """管理员用户管理页面"""
        try:
            from flask import render_template, session, redirect, url_for
            # 检查是否为管理员
            if not session.get('is_admin'):
                return redirect('/login')
            return render_template('pages/v2/admin-users.html')
        except Exception as e:
            logger.error(f"❌ 加载管理员页面失败: {e}")
            return f"管理员页面加载失败: {str(e)}", 500

    @app.route('/admin/logs')
    def admin_logs_page():
        """日志管理页面"""
        try:
            from flask import render_template, session, redirect, url_for
            # 检查是否为管理员
            if not session.get('is_admin'):
                return redirect('/login')
            return render_template('pages/v2/admin-logs.html')
        except Exception as e:
            logger.error(f"❌ 加载日志管理页面失败: {e}")
            return f"日志管理页面加载失败: {str(e)}", 500

    @app.route('/admin/tasks')
    def admin_tasks_page():
        """生成任务监控页面"""
        try:
            from flask import render_template, session, redirect, url_for
            # 检查是否为管理员
            if not session.get('is_admin'):
                return redirect('/login')
            return render_template('pages/v2/admin-tasks.html')
        except Exception as e:
            logger.error(f"❌ 加载任务监控页面失败: {e}")
            return f"任务监控页面加载失败: {str(e)}", 500

    @app.route('/api/contract/users/enabled', methods=['GET'])
    def get_contract_enabled_users():
        """获取所有启用的用户配置"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.get_enabled_users()
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 获取启用用户失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/novels/contractable', methods=['GET'])
    def get_contractable_novels_list():
        """获取可签约的小说列表"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.get_contractable_novels()
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 获取可签约小说失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/sign/auto', methods=['POST'])
    def auto_sign_contract_novel():
        """自动签约小说"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            data = request.json or {}
            novel_title = data.get('novel_title')
            user_id = data.get('user_id')
            
            if not novel_title or not user_id:
                return jsonify({
                    "success": False,
                    "error": "缺少必要参数"
                }), 400
                
            result = contract_api.submit_auto_sign_task(novel_title, user_id)
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 自动签约失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/service/start', methods=['POST'])
    def start_contract_signing_service():
        """启动签约服务"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.start_service()
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 启动签约服务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/service/stop', methods=['POST'])
    def stop_contract_signing_service():
        """停止签约服务"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.stop_service()
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 停止签约服务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/service/status', methods=['GET'])
    def get_contract_signing_service_status():
        """获取签约服务状态"""
        try:
            if not contract_api_available:
                return jsonify({
                    "running": False,
                    "api_active": False,
                    "error": "签约上传API不可用"
                })
            
            status = contract_api.get_service_status()
            return jsonify(status)
        except Exception as e:
            logger.error(f"❌ 获取签约服务状态失败: {e}")
            return jsonify({
                "running": False,
                "error": str(e)
            }), 500

    @app.route('/api/contract/service/reset', methods=['POST'])
    def reset_contract_signing_service():
        """重置签约服务状态（清理僵尸状态）"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
            
            # 停止服务
            contract_api.client.stop_service()
            
            # 删除状态文件
            import os
            status_file = "logs/enhanced_contract_service_status.json"
            if os.path.exists(status_file):
                try:
                    os.remove(status_file)
                    logger.info(f"✅ 已删除状态文件: {status_file}")
                except Exception as e:
                    logger.warning(f"⚠️ 删除状态文件失败: {e}")
            
            return jsonify({
                "success": True,
                "message": "服务状态已重置，请重新启动服务"
            })
        except Exception as e:
            logger.error(f"❌ 重置签约服务状态失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/contract/service/ready', methods=['GET'])
    def check_service_ready():
        """检查服务是否准备就绪"""
        try:
            if not contract_api_available:
                return jsonify({
                    "ready": False,
                    "error": "签约上传API不可用"
                }), 503
            
            # 检查服务状态和队列匹配
            status = contract_api.get_service_status()
            is_ready = (
                status.get("running", False) and
                status.get("process_running", False)
            )
            
            # 🔥 添加：检查队列是否可用
            try:
                queue_size = contract_api.client.task_queue.qsize()
                logger.info(f"✅ 服务就绪检查: running={status.get('running')}, process_running={status.get('process_running')}, queue_size={queue_size}")
            except:
                queue_size = -1
            
            return jsonify({
                "ready": is_ready,
                "queue_size": queue_size,
                "status": status,
                "message": "服务已准备就绪" if is_ready else "服务未就绪"
            })
        except Exception as e:
            logger.error(f"❌ 检查服务就绪状态失败: {e}")
            return jsonify({
                "ready": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/contract/tasks/<task_id>', methods=['GET'])
    def get_contract_task_status(task_id):
        """获取签约任务状态"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.get_task_status(task_id)
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 获取任务状态失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/contract/tasks', methods=['GET'])
    def get_all_contract_tasks():
        """获取所有签约任务"""
        try:
            if not contract_api_available:
                return jsonify({
                    "success": False,
                    "error": "签约上传API不可用"
                }), 503
                
            result = contract_api.get_all_tasks()
            return jsonify(result)
        except Exception as e:
            logger.error(f"❌ 获取所有任务失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


def register_monitoring_routes(app):
    """注册服务监控相关API路由（已禁用以降低CPU占用）"""
    
    # 禁用服务监控模块以降低CPU占用
    service_monitor = None
    service_monitor_available = False
    logger.info("ℹ️ 服务监控模块已禁用以降低CPU占用")

    @app.route('/api/monitoring/status', methods=['GET'])
    def get_monitoring_status():
        """获取当前监控状态"""
        try:
            from web.auth import login_required
            
            if not service_monitor_available:
                return jsonify({
                    "success": False,
                    "error": "服务监控模块不可用"
                }), 503
                
            status = service_monitor.get_current_status()
            return jsonify({
                "success": True,
                "status": status,
                "monitoring_active": service_monitor.monitoring
            })
        except Exception as e:
            logger.error(f"❌ 获取监控状态失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/monitoring/dashboard', methods=['GET'])
    def get_monitoring_dashboard():
        """获取监控仪表板数据"""
        try:
            from web.auth import login_required
            
            if not service_monitor_available:
                return jsonify({
                    "success": False,
                    "error": "服务监控模块不可用"
                }), 503
                
            # 获取综合监控数据
            current_status = service_monitor.get_current_status()
            recent_alerts = service_monitor.get_alerts(hours=1)
            performance_summary = service_monitor.get_performance_summary(hours=24)
            
            dashboard_data = {
                "current_status": current_status,
                "recent_alerts": recent_alerts[-10:],  # 最近10个告警
                "performance_summary": performance_summary,
                "monitoring_active": service_monitor.monitoring,
                "timestamp": datetime.now().isoformat()
            }
            
            return jsonify({
                "success": True,
                "dashboard": dashboard_data
            })
        except Exception as e:
            logger.error(f"❌ 获取监控仪表板数据失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查端点 - 用于负载均衡和监控"""
        try:
            # 基础健康检查
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": APP_INFO.get('version', 'unknown'),
                "checks": {
                    "api": "ok",
                    "static_files": os.path.exists(os.path.join(BASE_DIR, 'static'))
                }
            }
            
            # 检查关键目录可写
            critical_dirs = ['logs', 'generated_images', '小说项目']
            dir_status = {}
            for dir_name in critical_dirs:
                dir_path = os.path.join(BASE_DIR, dir_name)
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    # 测试写入
                    test_file = os.path.join(dir_path, '.health_check')
                    with open(test_file, 'w') as f:
                        f.write('ok')
                    os.remove(test_file)
                    dir_status[dir_name] = "ok"
                except Exception as e:
                    dir_status[dir_name] = f"error: {str(e)}"
                    health_data["status"] = "degraded"
            
            health_data["checks"]["directories"] = dir_status
            
            # 如果所有检查都通过，返回 200，否则返回 503
            status_code = 200 if health_data["status"] == "healthy" else 503
            return jsonify(health_data), status_code
            
        except Exception as e:
            logger.error(f"❌ 健康检查失败: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 503
        
    @app.route('/api/task-status/<task_id>', methods=['GET'])
    def get_task_status_simple(task_id):
        """获取任务状态 - 简化版API供前端轮询使用"""
        try:
            from web.managers.novel_manager import novel_manager
            
            # 获取任务状态
            task_status = novel_manager.get_task_status(task_id)
            if "error" in task_status:
                return jsonify({"error": task_status["error"]}), 404
            
            # 获取任务进度
            task_progress = novel_manager.get_task_progress(task_id)
            
            # 构建响应
            response = {
                "task_id": task_id,
                "status": task_status.get("status", "unknown"),
                "progress": task_status.get("progress", 0),
                "current_step": task_status.get("current_step", ""),
                "step_status": task_progress.get("step_status", {}),
                "points_consumed": task_progress.get("points_consumed", 0),
                "points_total": task_progress.get("points_total", 400)
            }
            
            # 如果任务失败，包含错误信息
            if task_status.get("status") == "failed" and "error" in task_status:
                response["error"] = task_status["error"]
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"❌ 获取任务状态失败: {e}")
            return jsonify({"error": str(e)}), 500


def print_startup_info():
    """打印启动信息"""
    logger.info("=" * 60)
    logger.info("🚀 Web 服务启动")
    logger.info("=" * 60)
    logger.info(f"📱 应用名称: {APP_INFO['name']}")
    logger.info(f"📋 版本: {APP_INFO['version']}")
    logger.info(f"🌐 前端地址: http://localhost:{FlaskConfig.PORT}")
    logger.info(f"🔧 API 地址: http://localhost:{FlaskConfig.PORT}/api")
    logger.info("🍅 番茄上传功能已集成")
    
    if MODULE_STATUS["contract_api_available"]:
        logger.info("✅ 签约上传独立进程服务已集成")
    else:
        logger.warning("⚠️ 签约上传独立进程服务不可用")
    
    if MODULE_STATUS["service_monitor_available"]:
        logger.info("✅ 服务监控模块已集成")
    else:
        logger.warning("⚠️ 服务监控模块不可用")
    
    logger.info("=" * 60)


def cleanup_on_exit():
    """退出清理函数"""
    logger.info("🧹 正在清理资源...")
    
    # 停止服务监控
    try:
        from Chrome.automation.monitoring.service_monitor import service_monitor
        if service_monitor.monitoring:
            service_monitor.stop_monitoring()
    except:
        pass
    
    # 🔥 停止所有生成任务和线程
    try:
        if manager:
            logger.info("⏹️ 停止所有生成任务...")
            # 停止所有活跃任务
            for task_id in list(manager.active_tasks.keys()):
                logger.info(f"  停止任务: {task_id}")
                manager.stop_task(task_id)
            
            # 等待线程结束
            for task_id, thread in list(manager.task_threads.items()):
                if thread.is_alive():
                    logger.info(f"  等待线程: {task_id}")
                    manager._stop_flags[task_id] = True
                    thread.join(timeout=2)
    except Exception as e:
        logger.error(f"❌ 停止生成任务时出错: {e}")
    
    logger.info("✅ 清理完成")


import time

# 全局变量用于跟踪信号
_last_signal_time = 0
_signal_count = 0
_EXIT_SIGNALS_REQUIRED = 2  # 需要连续两次 Ctrl+C 才退出
_SIGNAL_TIMEOUT = 3.0  # 两次信号之间的时间间隔（秒）


def signal_handler(signum, frame):
    """智能信号处理器 - 需要连续两次信号才退出"""
    global _last_signal_time, _signal_count
    
    current_time = time.time()
    time_since_last = current_time - _last_signal_time
    
    # 如果距离上次信号太久，重置计数
    if time_since_last > _SIGNAL_TIMEOUT:
        _signal_count = 0
    
    _signal_count += 1
    _last_signal_time = current_time
    
    logger.info(f"📝 收到信号 {signum} (第 {_signal_count}/{_EXIT_SIGNALS_REQUIRED} 次)")
    
    if signum == signal.SIGTERM:
        # SIGTERM 立即退出
        logger.info("⚠️ 收到终止信号，立即退出...")
        cleanup_on_exit()
        os._exit(0)
    elif _signal_count >= _EXIT_SIGNALS_REQUIRED:
        # 需要连续多次 Ctrl+C 才退出（防止误触）
        logger.info("✅ 检测到连续中断信号，准备退出...")
        logger.info("💡 提示：在 PowerShell/CMD 中复制文本请使用：")
        logger.info("   - 右键菜单 -> 标记 -> 选择文本 -> 右键复制")
        logger.info("   - 或者使用 Ctrl+Shift+C（如果支持）")
        cleanup_on_exit()
        os._exit(0)
    else:
        # 第一次 Ctrl+C，只警告不退出
        remaining = _EXIT_SIGNALS_REQUIRED - _signal_count
        logger.warning(f"⚠️  检测到中断信号！如需退出请再次按下 Ctrl+C ({remaining}/{_EXIT_SIGNALS_REQUIRED})")
        logger.warning("💡 如果是想复制日志，请使用：右键 -> 标记 -> 选择文本 -> Enter")


def main():
    """主函数"""
    print_startup_info()
    
    # 注册信号处理器（智能模式）
    # 注意：在Windows后台模式（无控制台）下，信号注册可能会失败
    try:
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C（需要两次才退出）
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号（立即退出）
    except ValueError as e:
        logger.warning(f"⚠️ 无法注册信号处理器（可能处于后台模式）: {e}")
    
    # 注册退出清理函数
    atexit.register(cleanup_on_exit)

    # 打印操作提示
    logger.info("=" * 60)
    logger.info("💡 使用提示：")
    logger.info("   • 服务器需要连续 2 次 Ctrl+C 才会退出（防止误触）")
    logger.info("   • 复制日志内容请使用：右键 -> 标记 -> 选择文本 -> Enter")
    logger.info("   • 或者使用 Ctrl+Shift+C（部分终端支持）")
    logger.info("=" * 60)

    # 创建应用实例
    app, manager = create_app()

    # 🔥 过滤werkzeug的视频文件请求日志
    class VideoRequestFilter(logging.Filter):
        def filter(self, record):
            # 只记录非200的响应或非视频文件的请求
            msg = record.getMessage()
            if '.mp4' in msg and '206' in msg:
                return False  # 不记录视频文件的部分内容请求
            if '.mp4' in msg and '200' in msg:
                return False  # 不记录视频文件的完整请求
            return True

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(VideoRequestFilter())
    # 禁用werkzeug的请求日志，避免打印base64图片数据
    werkzeug_logger.setLevel(logging.WARNING)

    # 🔥 修复：禁用热重载，避免多进程队列问题
    app.run(
        host=FlaskConfig.HOST,
        port=FlaskConfig.PORT,
        debug=FlaskConfig.DEBUG,
        use_reloader=False  # 禁用热重载，避免队列ID不匹配
    )


if __name__ == '__main__':
    main()