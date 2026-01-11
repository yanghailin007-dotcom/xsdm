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
from flask import Flask, request, jsonify
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 修复：补全缺失的括号

# 导入配置和工具
from web.web_config import (
    logger, FlaskConfig, APP_INFO, MODULE_STATUS,
    BASE_DIR, CREATIVE_IDEAS_FILE
)
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
from web.api.cover_api import register_cover_routes
from web.api.phase_generation_api import register_phase_routes
from web.api.resume_generation_api import register_resume_routes
from web.api.worldview_api import register_worldview_routes
from web.api.video_generation_api import register_video_routes
from web.api.nanobanana_api import register_nanobanana_routes
from web.api.character_api import register_character_routes

# 导入页面路由模块
from web.routes.auth_routes import register_auth_routes, register_page_routes

# 导入注册API模块
from web.api.register_api import register_register_routes


def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(FlaskConfig)
    
    # 创建全局管理器实例
    manager = NovelGenerationManager()
    
    # 注册生成的图片访问路由
    @app.route('/generated_images/<path:filename>')
    def serve_generated_image(filename):
        """提供生成的图片文件访问"""
        from flask import send_from_directory
        generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
        return send_from_directory(generated_images_dir, filename)
    
    logger.info(f"✅ 配置图片访问路由: /generated_images/<filename>")
    
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
                logger.warn(f"⚠️ 验证失败: {validation_result.get('error', '未知错误')}")
            
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


def register_contract_routes(app):
    """注册签约上传相关API路由"""
    
    # 尝试导入签约API
    try:
        from Chrome.automation.api.contract_api import contract_api
        contract_api_available = True
        logger.info("✅ 签约上传API加载成功")
    except ImportError as e:
        logger.warn(f"⚠️ 无法导入签约上传API: {e}")
        contract_api = None
        contract_api_available = False

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

    @app.route('/api//service/stop', methods=['POST'])
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
        logger.warn("⚠️ 签约上传独立进程服务不可用")
    
    if MODULE_STATUS["service_monitor_available"]:
        logger.info("✅ 服务监控模块已集成")
    else:
        logger.warn("⚠️ 服务监控模块不可用")
    
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
        logger.warn(f"⚠️  检测到中断信号！如需退出请再次按下 Ctrl+C ({remaining}/{_EXIT_SIGNALS_REQUIRED})")
        logger.warn("💡 如果是想复制日志，请使用：右键 -> 标记 -> 选择文本 -> Enter")


def main():
    """主函数"""
    print_startup_info()
    
    # 注册信号处理器（智能模式）
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C（需要两次才退出）
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号（立即退出）
    
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
    
    # 开发模式运行 - 启用热重载但确保正确退出
    app.run(
        host=FlaskConfig.HOST,
        port=FlaskConfig.PORT,
        debug=FlaskConfig.DEBUG,
        use_reloader=True  # 恢复热重载功能
    )


if __name__ == '__main__':
    main()