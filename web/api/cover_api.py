"""
封面生成相关API路由
"""
from flask import jsonify, request, send_from_directory, send_file
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

    # 🔥 新增：访问视频项目文件的路由
    @app.route('/project-files/<path:filepath>')
    def serve_project_files(filepath):
        """提供视频项目内的文件（如剧照）"""
        try:
            import os
            from pathlib import Path
            from urllib.parse import unquote

            logger.info(f"📂 [project-files] 请求的filepath: {filepath}")

            # URL解码
            decoded_filepath = unquote(filepath)
            logger.info(f"📂 [project-files] 解码后的filepath: {decoded_filepath}")

            # 构建完整路径
            base_path = Path('视频项目').resolve()
            full_path = (base_path / decoded_filepath).resolve()

            logger.info(f"📂 [project-files] base_path: {base_path}")
            logger.info(f"📂 [project-files] full_path: {full_path}")

            # 安全检查：防止路径遍历攻击
            if not str(full_path).startswith(str(base_path)):
                logger.error(f"❌ [project-files] 非法路径访问: {filepath}")
                return jsonify({"error": "非法路径访问"}), 403

            if not full_path.exists():
                logger.error(f"❌ [project-files] 文件不存在: {full_path}")
                # 列出目录下的文件用于调试
                if full_path.parent.exists():
                    logger.info(f"📂 [project-files] 父目录内容: {list(full_path.parent.iterdir())}")
                return jsonify({"error": f"文件不存在: {filepath}"}), 404

            logger.info(f"✅ [project-files] 提供视频项目文件: {full_path}")
            return send_file(str(full_path), as_attachment=False)

        except Exception as e:
            logger.error(f"❌ [project-files] 视频项目文件服务失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"error": f"访问文件失败: {str(e)}"}), 500