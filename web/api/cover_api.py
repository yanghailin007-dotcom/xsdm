"""
封面生成相关API路由
"""
from flask import jsonify, request, send_from_directory
from urllib.parse import unquote

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.services.cover_service import CoverService


def register_cover_routes(app):
    """注册封面相关API路由"""
    
    cover_service = CoverService()
    
    @app.route('/api/generate-cover', methods=['POST'])
    @login_required
    def generate_cover():
        """生成小说封面"""
        try:
            data = request.json or {}
            result = cover_service.generate_cover(data)
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 生成封面API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/novel/<title>/covers', methods=['GET'])
    @login_required
    def get_novel_covers(title):
        """获取指定小说的封面列表"""
        try:
            result = cover_service.get_novel_covers(title)
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 获取小说封面API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/covers/list', methods=['GET'])
    @login_required
    def get_all_covers():
        """获取所有封面列表"""
        try:
            result = cover_service.get_all_covers()
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 获取所有封面API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/cover/copy-to-novel-directory', methods=['POST'])
    @login_required
    def copy_cover_to_novel_directory():
        """将选中的封面拷贝到小说目录，覆盖原图片"""
        try:
            data = request.json or {}
            cover_url = data.get('cover_url')
            novel_title = data.get('novel_title')
            
            if not cover_url or not novel_title:
                return jsonify({
                    "success": False,
                    "error": "缺少必需参数: cover_url 和 novel_title"
                }), 400
            
            result = cover_service.copy_cover_to_novel_directory(cover_url, novel_title)
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 拷贝封面API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/cover/batch-copy-to-novel-directories', methods=['POST'])
    @login_required
    def batch_copy_covers_to_novel_directories():
        """批量将选中的封面拷贝到对应的小说目录"""
        try:
            data = request.json or {}
            covers = data.get('covers', [])  # [{"cover_url": "...", "novel_title": "..."}]
            
            if not covers:
                return jsonify({
                    "success": False,
                    "error": "没有提供要拷贝的封面列表"
                }), 400
            
            result = cover_service.batch_copy_covers_to_novel_directories(covers)
            
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 批量拷贝封面API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # 静态文件服务
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """提供静态文件"""
        return send_from_directory('static', filename)

    @app.route('/generated_images/<path:filename>')
    def serve_generated_images(filename):
        """提供生成的图片文件"""
        try:
            result = cover_service.serve_generated_image(filename)
            
            # 如果返回的是字典，说明是错误响应
            if isinstance(result, dict):
                return jsonify(result), result.get("status_code", 500)
            
            # 否则是Flask的send_file响应
            return result
            
        except Exception as e:
            logger.error(f"❌ 静态文件服务失败: {e}")
            return jsonify({"error": f"访问文件失败: {str(e)}"}), 500