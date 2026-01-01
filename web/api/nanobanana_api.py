"""
Nano Banana文生图API路由
用于角色生成的图像生成API
"""
from flask import jsonify, request

from web.auth import login_required
from web.web_config import logger
from web.services.nanobanana_service import NanoBananaService


def register_nanobanana_routes(app):
    """注册Nano Banana相关API路由"""
    
    nanobanana_service = NanoBananaService()
    
    @app.route('/api/nanobanana/generate', methods=['POST'])
    @login_required
    def generate_nanobanana_image():
        """
        生成Nano Banana图像（用于角色生成）
        
        请求体:
        {
            "prompt": "a cute cat",  // 必需
            "aspect_ratio": "16:9",  // 可选，默认16:9
            "image_size": "4K",      // 可选，默认4K
            "save_filename": "cat"   // 可选
        }
        """
        try:
            data = request.json or {}
            result = nanobanana_service.generate_image(data)
            
            if result.get("success"):
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 生成Nano Banana图像API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/nanobanana/batch-generate', methods=['POST'])
    @login_required
    def batch_generate_nanobanana_images():
        """
        批量生成Nano Banana图像
        
        请求体:
        {
            "prompts": ["a cat", "a dog"],  // 必需
            "aspect_ratio": "16:9",          // 可选，默认16:9
            "image_size": "4K",              // 可选，默认4K
            "delay": 1.0                     // 可选，默认1.0秒
        }
        """
        try:
            data = request.json or {}
            result = nanobanana_service.batch_generate_images(data)
            
            if result.get("success"):
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 批量生成Nano Banana图像API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/nanobanana/status', methods=['GET'])
    @login_required
    def get_nanobanana_status():
        """获取Nano Banana服务状态"""
        try:
            result = nanobanana_service.get_service_status()
            
            if result.get("success"):
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"❌ 获取Nano Banana状态API失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500