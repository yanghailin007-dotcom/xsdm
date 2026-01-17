"""
剧照图片素材库 API 路由

提供剧照图片的增删查查接口
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
import traceback
import os
from pathlib import Path

from src.utils.logger import get_logger
from src.models.still_image_models import StillImage, StillImageType, StillImageStatus
from src.managers.StillImageManager import get_still_image_manager

# 创建蓝图
still_image_api = Blueprint('still_image_api', __name__)

# 初始化日志
logger = get_logger(__name__)

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent.parent


@still_image_api.route('/api/still-images', methods=['GET'])
def list_still_images():
    """
    列出剧照图片
    
    查询参数：
    - limit: 返回数量限制（默认50）
    - image_type: 图片类型过滤（character/scene/custom）
    - novel_title: 小说标题过滤
    - status: 状态过滤（pending/generating/completed/failed/cancelled）
    - order: 排序方式（desc/asc）
    
    响应：
    {
        "success": true,
        "data": [...],
        "total": 100
    }
    """
    try:
        limit = int(request.args.get('limit', 50))
        image_type_str = request.args.get('image_type')
        novel_title = request.args.get('novel_title')
        status_str = request.args.get('status')
        order = request.args.get('order', 'desc')
        
        # 转换类型
        image_type = None
        if image_type_str:
            try:
                image_type = StillImageType(image_type_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"Invalid image_type: {image_type_str}"
                }), 400
        
        # 转换状态
        status = None
        if status_str:
            try:
                status = StillImageStatus(status_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": f"Invalid status: {status_str}"
                }), 400
        
        # 获取管理器并查询
        manager = get_still_image_manager()
        images = manager.list_images(
            limit=limit,
            image_type=image_type,
            novel_title=novel_title,
            status=status,
            order=order
        )
        
        return jsonify({
            "success": True,
            "data": [img.to_dict() for img in images],
            "total": len(images)
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 列出剧照图片失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@still_image_api.route('/api/still-images/<image_id>', methods=['GET'])
def get_still_image(image_id: str):
    """
    获取指定剧照图片
    
    参数：
    - image_id: 图片ID
    
    响应：
    {
        "success": true,
        "data": {...}
    }
    """
    try:
        manager = get_still_image_manager()
        image = manager.get_image(image_id)
        
        if not image:
            return jsonify({
                "success": False,
                "error": f"Image not found: {image_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": image.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 获取剧照图片失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@still_image_api.route('/api/still-images/<image_id>', methods=['DELETE'])
def delete_still_image(image_id: str):
    """
    删除剧照图片
    
    参数：
    - image_id: 图片ID
    
    响应：
    {
        "success": true,
        "message": "Image deleted"
    }
    """
    try:
        manager = get_still_image_manager()
        success = manager.delete_image(image_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": f"Failed to delete image: {image_id}"
            }), 400
        
        return jsonify({
            "success": True,
            "message": "Image deleted"
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 删除剧照图片失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@still_image_api.route('/api/still-images/statistics', methods=['GET'])
def get_statistics():
    """
    获取素材库统计信息
    
    响应：
    {
        "success": true,
        "data": {
            "total_count": 100,
            "type_counts": {...},
            "status_counts": {...},
            "novel_counts": {...},
            "total_size_bytes": 12345678,
            "total_size_mb": 12.34
        }
    }
    """
    try:
        manager = get_still_image_manager()
        stats = manager.get_statistics()
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 获取统计信息失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@still_image_api.route('/api/still-images/add', methods=['POST'])
def add_still_image():
    """
    添加剧照图片到素材库
    
    请求体：
    {
        "image_type": "character" | "scene" | "custom",
        "prompt": "生成提示词",
        "local_path": "本地文件路径",
        "image_url": "HTTP访问URL",
        "novel_title": "小说标题（可选）",
        "character_name": "角色名称（可选，character类型）",
        "event_name": "事件名称（可选，scene类型）",
        "aspect_ratio": "9:16"（可选，默认9:16）,
        "image_size": "4K"（可选，默认4K）,
        "used_reference_images": 0（可选，默认0）,
        "file_size": 123456（可选，默认0）,
        "metadata": {}（可选）
    }
    
    响应：
    {
        "success": true,
        "data": {...},
        "message": "Image added to library"
    }
    """
    try:
        data = request.json or {}
        
        # 验证必需参数
        if not data.get('image_type'):
            return jsonify({
                "success": False,
                "error": "Missing required parameter: image_type"
            }), 400
        
        if not data.get('prompt'):
            return jsonify({
                "success": False,
                "error": "Missing required parameter: prompt"
            }), 400
        
        if not data.get('local_path'):
            return jsonify({
                "success": False,
                "error": "Missing required parameter: local_path"
            }), 400
        
        if not data.get('image_url'):
            return jsonify({
                "success": False,
                "error": "Missing required parameter: image_url"
            }), 400
        
        # 转换类型
        try:
            image_type = StillImageType(data['image_type'])
        except ValueError:
            return jsonify({
                "success": False,
                "error": f"Invalid image_type: {data['image_type']}"
            }), 400
        
        # 获取管理器并添加图片
        manager = get_still_image_manager()
        image = manager.add_image(
            image_type=image_type,
            prompt=data['prompt'],
            local_path=data['local_path'],
            image_url=data['image_url'],
            novel_title=data.get('novel_title'),
            character_name=data.get('character_name'),
            event_name=data.get('event_name'),
            aspect_ratio=data.get('aspect_ratio', '9:16'),
            image_size=data.get('image_size', '4K'),
            used_reference_images=data.get('used_reference_images', 0),
            file_size=data.get('file_size', 0),
            metadata=data.get('metadata', {})
        )
        
        logger.info(f"✅ 添加剧照图片到素材库: {image.image_id}")
        
        return jsonify({
            "success": True,
            "data": image.to_dict(),
            "message": "Image added to library"
        }), 201
    
    except Exception as e:
        logger.error(f"❌ 添加剧照图片失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@still_image_api.route('/api/still-images/export', methods=['POST'])
def export_metadata():
    """
    导出所有图片元数据
    
    请求体：
    {
        "output_file": "输出文件路径（可选，默认still_images_export.json）"
    }
    
    响应：
    {
        "success": true,
        "output_file": "/path/to/export.json",
        "message": "Metadata exported successfully"
    }
    """
    try:
        data = request.json or {}
        output_file = data.get('output_file', 'still_images_export.json')
        
        manager = get_still_image_manager()
        success = manager.export_metadata(output_file)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to export metadata"
            }), 500
        
        return jsonify({
            "success": True,
            "output_file": output_file,
            "message": "Metadata exported successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 导出元数据失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def register_still_image_routes(app):
    """注册剧照图片素材库API路由"""
    app.register_blueprint(still_image_api)
    
    logger.info("=" * 60)
    logger.info("📋 已注册的剧照图片素材库API路由:")
    for rule in app.url_map.iter_rules():
        if 'still-images' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    logger.info("🎨 剧照图片素材库API已启用")
    logger.info("💾 支持本地存储和元数据管理")
    logger.info("📊 提供统计和导出功能")
    logger.info("=" * 60)
