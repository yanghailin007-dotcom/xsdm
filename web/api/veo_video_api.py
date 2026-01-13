"""
VeO 视频生成 API 路由
支持两种图片输入模式：
1. 图片 URL（推荐）：直接传递图片 URL，无需 base64 编码
2. Base64 图片：传递 base64 编码的图片数据（会自动压缩）
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
import traceback

from src.utils.logger import get_logger
from src.models.veo_models import (
    VeOCreateVideoRequest,
    VeOGenerationResponse,
    VeOGenerationResult,
    VeOVideoResult,
    VideoStatus,
    VeOUsageMetadata,
    VeOGenerationConfig
)
from src.managers.VeOVideoManager import get_veo_video_manager

# 创建蓝图
veo_video_api = Blueprint('veo_video_api', __name__)

# 初始化日志
logger = get_logger(__name__)


@veo_video_api.route('/api/veo/generate', methods=['POST'])
def create_video_generation():
    """
    创建视频生成任务（使用 VeO 原生格式）
    
    请求体：
    {
        "model": "veo_3_1-fast",
        "prompt": "视频生成的文本描述",
        "image_urls": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],  // 推荐：图片 URL
        "images": ["base64_image_data1", "base64_image_data2"],  // 可选：base64 图片
        "orientation": "portrait" | "landscape",
        "size": "small" | "large",
        "duration": 10 | 15,
        "watermark": false,
        "private": true
    }
    
    响应：
    {
        "id": "veo_abc123",
        "status": "processing",
        ...
    }
    """
    try:
        data = request.json or {}
        
        logger.info("📥 收到视频生成请求")
        
        # 验证必需参数
        if not data.get('prompt'):
            return jsonify({
                "error": {
                    "message": "Missing required parameter: prompt",
                    "type": "invalid_request_error"
                }
            }), 400
        
        # 提取图片数据 - 支持两种模式
        # 1. image_urls: 图片 URL 列表（推荐）
        # 2. images: base64 编码的图片数据（会自动压缩）
        image_urls: List[str] = data.get('image_urls', [])
        images: List[str] = data.get('images', [])
        
        # 优先使用 image_urls
        if image_urls:
            logger.info(f"🔗 使用图片 URL 模式: {len(image_urls)} 个 URL")
            for i, url in enumerate(image_urls):
                logger.info(f"  - 图片 {i+1}: {url}")
            images = image_urls
        elif images:
            logger.info(f"📦 使用 base64 图片模式: {len(images)} 张图片")
            for i, img in enumerate(images):
                if not img or not isinstance(img, str):
                    logger.warn(f"⚠️  图片 {i} 数据无效")
                    continue
                
                # 检查是否是 URL
                if img.startswith(('http://', 'https://')):
                    logger.info(f"  - 图片 {i+1}: {img[:100]}... (URL)")
                elif len(img) > 100:
                    logger.info(f"  - 图片 {i+1}: base64 长度 {len(img)} 字符")
                else:
                    logger.warn(f"  - 图片 {i+1}: 数据太短，可能无效")
        
        # 创建 VeO 原生请求
        # 根据前端选择的模式自动选择正确的模型
        # - mode='frame'（首尾帧模式）: veo_3_1-fast-fl
        # - mode='reference'（参考图模式）: veo_3_1-fast
        user_provided_model = data.get('model')
        upload_mode = data.get('mode', 'reference')  # 默认为参考图模式
        
        # 如果用户没有指定模型，根据上传模式自动选择
        if user_provided_model is None:
            if upload_mode == 'frame':
                # 首尾帧模式（可能只有1张或2张图片）
                # 🔥 修复：帧模式模型名称是 veo_3_1-fl（不是 veo_3_1-fast-fl）
                auto_model = 'veo_3_1-fl'
            else:
                # 参考图模式
                auto_model = 'veo_3_1-fast'
        else:
            # 使用用户指定的模型
            auto_model = user_provided_model
        
        veo_request = VeOCreateVideoRequest(
            images=images,
            model=auto_model,
            orientation=data.get('orientation', 'portrait'),
            prompt=data.get('prompt', ''),
            size=data.get('size', 'large'),
            duration=10,  # VeO只支持10秒
            watermark=data.get('watermark', False),
            private=data.get('private', True)
        )
        
        logger.info(f"🎨 上传模式: {upload_mode}")
        logger.info(f"🎨 图片数量: {len(images)}")
        if upload_mode == 'frame':
            logger.info(f"🎬 模式: 首尾帧模式 (使用 veo_3_1-fast-fl)")
        else:
            logger.info(f"🎬 模式: 参考图模式 (使用 veo_3_1-fast)")
        
        logger.info(f"📝 提示词长度: {len(veo_request.prompt)} 字符")
        logger.info(f"🎬 模型: {veo_request.model}")
        logger.info(f"📐 方向: {veo_request.orientation}")
        logger.info(f"📐 尺寸: {veo_request.size}")
        logger.info(f"⏱️  时长: {veo_request.duration}秒")
        logger.info(f"💧 水印: {veo_request.watermark}")
        logger.info(f"🔒 私有: {veo_request.private}")
        
        # 转换为 OpenAI 格式请求（用于内部处理）
        from src.models.veo_models import VeOVideoRequest
        
        # 构建消息格式
        messages = [{
            "role": "user",
            "content": []
        }]
        
        # 添加文本内容
        messages[0]["content"].append({
            "type": "text",
            "text": veo_request.prompt
        })
        
        # 添加图片内容
        for img_base64 in veo_request.images:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}"
                }
            })
        
        openai_request = VeOVideoRequest(
            model=veo_request.model,
            messages=messages,
            stream=True
        )
        
        # 获取管理器并创建任务（传递原生请求对象以保留配置参数）
        manager = get_veo_video_manager()
        response = manager.create_generation(openai_request, veo_request)
        
        logger.info(f"✅ 创建 VeO 视频生成任务: {response.id}")
        
        return jsonify(response.to_dict()), 202
    
    except Exception as e:
        logger.error(f"❌ 创建生成任务失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@veo_video_api.route('/api/veo/status/<generation_id>', methods=['GET'])
def get_generation_status(generation_id: str):
    """
    查询生成状态
    
    参数：
    - generation_id: 生成任务ID
    
    响应：
    {
        "id": "veo_abc123",
        "status": "completed",
        "result": {...}
    }
    """
    try:
        manager = get_veo_video_manager()
        response = manager.retrieve_generation(generation_id)
        
        if not response:
            return jsonify({
                "error": {
                    "message": f"Generation not found: {generation_id}",
                    "type": "invalid_request_error"
                }
            }), 404
        
        return jsonify(response.to_dict()), 200
    
    except Exception as e:
        logger.error(f"❌ 查询生成状态失败: {e}")
        logger.error(f"❌ 错误详情: {traceback.format_exc()}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@veo_video_api.route('/api/veo/cancel/<generation_id>', methods=['POST'])
def cancel_generation(generation_id: str):
    """
    取消生成任务
    
    参数：
    - generation_id: 生成任务ID
    
    响应：
    {
        "success": true,
        "message": "Generation cancelled"
    }
    """
    try:
        manager = get_veo_video_manager()
        success = manager.cancel_generation(generation_id)
        
        if not success:
            return jsonify({
                "error": {
                    "message": f"Failed to cancel generation: {generation_id}",
                    "type": "invalid_request_error"
                }
            }), 400
        
        return jsonify({
            "success": True,
            "message": "Generation cancelled"
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 取消生成任务失败: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@veo_video_api.route('/api/veo/tasks', methods=['GET'])
def list_generations():
    """
    列出生成任务
    
    查询参数：
    - limit: 返回数量限制（默认20）
    - status: 状态过滤
    - order: 排序方式（desc/asc）
    
    响应：
    {
        "data": [...],
        "total": 100
    }
    """
    try:
        limit = int(request.args.get('limit', 20))
        status_str = request.args.get('status')
        order = request.args.get('order', 'desc')
        
        # 将字符串状态转换为 VideoStatus 枚举
        status = None
        if status_str:
            try:
                status = VideoStatus(status_str)
            except ValueError:
                return jsonify({
                    "error": {
                        "message": f"Invalid status: {status_str}",
                        "type": "invalid_request_error"
                    }
                }), 400
        
        manager = get_veo_video_manager()
        generations = manager.list_generations(
            limit=limit,
            status=status,
            order=order
        )
        
        return jsonify({
            "data": [g.to_dict() for g in generations],
            "total": len(generations)
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 列出生成任务失败: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


def register_veo_video_routes(app):
    """注册 VeO 视频生成 API 路由"""
    app.register_blueprint(veo_video_api)
    
    logger.info("=" * 60)
    logger.info("📋 已注册的 VeO 视频生成 API 路由:")
    for rule in app.url_map.iter_rules():
        if 'api/veo' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("📡 API 提供商: AI-WX VeO 3.1")
    logger.info("🔗 支持图片 URL 输入（推荐）")
    logger.info("📦 支持 base64 图片输入（自动压缩）")
    logger.info("=" * 60)