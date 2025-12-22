"""
重构后的Web服务器主文件
按功能模块拆分，提高代码可维护性
"""
import os
import sys
import threading
from flask import Flask, request, jsonify
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# 导入页面路由模块
from web.routes.auth_routes import register_auth_routes, register_page_routes


def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(FlaskConfig)
    
    # 创建全局管理器实例
    manager = NovelGenerationManager()
    
    # 注册路由
    # 1. 认证和页面路由
    register_auth_routes(app)
    register_page_routes(app)
    
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
    
    return app, manager


def register_fanqie_routes(app):
    """注册番茄上传相关API路由"""
    
    @app.route('/api/fanqie/upload/check-prerequisites', methods=['GET'])
    def check_fanqie_upload_prerequisites():
        """检查番茄上传前提条件 - 手动环境准备模式"""
        try:
            from web.auth import login_required
            
            if not fanqie_uploader:
                return jsonify({"success": False, "error": "番茄上传器不可用"}), 503
                
            checks = fanqie_uploader.check_upload_prerequisites()
            
            # 在手动环境准备模式下，主要检查系统环境
            # 浏览器和登录状态由用户手动确认
            system_ready = checks.get("temp_dir_writable", False) and checks.get("autopush_available", False)
            
            return jsonify({
                "success": True,
                "checks": checks,
                "ready": system_ready,
                "message": "系统环境检查通过，请确认手动环境准备完成" if system_ready else "系统环境检查未通过，请检查失败项目",
                "manual_preparation_required": True,
                "manual_items": {
                    "browser_available": "请手动准备浏览器并确保可以访问网络",
                    "fanqie_logged_in": "请手动登录番茄小说网站并进入作家专区"
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
            
            if not novel_title:
                return jsonify({"success": False, "error": "缺少小说标题"}), 400
            
            # 验证小说是否可以上传
            validation_result = fanqie_uploader.validate_novel_for_upload(novel_title)
            if not validation_result["valid"]:
                return jsonify({
                    "success": False,
                    "error": validation_result["error"]
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

    @app.route('/api/contract/service/start', methods=['POST'])
    def start_contract_service():
        """启动签约服务"""
        try:
            from web.auth import login_required
            
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

    @app.route('/api/contract/service/status', methods=['GET'])
    def get_contract_service_status():
        """获取签约服务状态"""
        try:
            from web.auth import login_required
            
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


def register_monitoring_routes(app):
    """注册服务监控相关API路由"""
    
    # 尝试导入服务监控
    try:
        from Chrome.automation.monitoring.service_monitor import service_monitor
        service_monitor_available = True
        logger.info("✅ 服务监控模块加载成功")
    except ImportError as e:
        logger.warn(f"⚠️ 无法导入服务监控模块: {e}")
        service_monitor = None
        service_monitor_available = False

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


def main():
    """主函数"""
    print_startup_info()
    
    # 创建应用实例
    app, manager = create_app()
    
    # 开发模式运行
    app.run(
        host=FlaskConfig.HOST,
        port=FlaskConfig.PORT,
        debug=FlaskConfig.DEBUG,
        use_reloader=False
    )


if __name__ == '__main__':
    main()