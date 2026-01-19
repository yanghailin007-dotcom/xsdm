"""
VeO 视频生成 API 路由
支持两种图片输入模式：
1. 图片 URL（推荐）：直接传递图片 URL，无需 base64 编码
2. Base64 图片：传递 base64 编码的图片数据（会自动压缩）
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
import traceback
import os

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
from config.aiwx_video_config import DEFAULT_AIWX_MODEL

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
        # 🔥 统一使用 veo_3_1-fast 模型，首尾帧模式和参考图模式调用方式完全一致
        # 唯一的区别只是图片数量不同
        user_provided_model = data.get('model')
        
        # 使用用户指定的模型，如果没有则使用默认的 fast 模型
        auto_model = user_provided_model if user_provided_model else DEFAULT_AIWX_MODEL
        
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
        
        logger.info(f"🎨 图片数量: {len(images)}")
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


@veo_video_api.route('/api/veo/tasks/<generation_id>', methods=['DELETE'])
def delete_generation(generation_id: str):
    """
    删除生成任务
    
    参数：
    - generation_id: 生成任务ID
    
    响应：
    {
        "success": true,
        "message": "Generation deleted"
    }
    """
    try:
        manager = get_veo_video_manager()
        success = manager.delete_generation(generation_id)
        
        if not success:
            return jsonify({
                "error": {
                    "message": f"Failed to delete generation: {generation_id}",
                    "type": "invalid_request_error"
                }
            }), 400
        
        return jsonify({
            "success": True,
            "message": "Generation deleted"
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 删除生成任务失败: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@veo_video_api.route('/api/video/studio/library', methods=['GET'])
def get_video_library():
    """
    获取视频素材库列表
    
    查询参数：
    - status: 状态过滤 (all | completed | processing | failed)
    
    响应：
    {
        "success": true,
        "videos": [
            {
                "id": "veo_abc123",
                "prompt": "视频生成提示词",
                "status": "completed",
                "progress": 100,
                "url": "/static/generated_videos/veo_abc123.mp4",
                "date": "2026-01-17 13:38:25"
            }
        ]
    }
    """
    try:
        from datetime import datetime
        
        status_filter = request.args.get('status', 'all')
        
        logger.info(f"📋 获取视频素材库: status={status_filter}")
        
        manager = get_veo_video_manager()
        generations = manager.list_generations(
            limit=100,  # 获取最近100个任务
            status=None if status_filter == 'all' else VideoStatus(status_filter) if status_filter != 'all' else None,
            order='desc'
        )
        
        # 格式化为前端需要的格式
        videos = []
        for gen in generations:
            # 🔥 修复：使用 gen.prompt 直接获取提示词
            prompt = gen.prompt if hasattr(gen, 'prompt') else ""
            
            # 获取视频URL
            url = None
            if gen.result and gen.result.videos:
                video_url = gen.result.videos[0].url
                # 如果是本地路径，转换为HTTP URL
                if video_url.startswith('/static/'):
                    url = video_url
                elif video_url.startswith('http://') or video_url.startswith('https://'):
                    url = video_url
                else:
                    # 本地文件路径，转换为HTTP URL
                    url = f"/static/generated_videos/{os.path.basename(video_url)}"
            
            # 🔥 修复：使用 gen.created 而不是 gen.created_at
            created_at = ""
            if hasattr(gen, 'created') and gen.created:
                if isinstance(gen.created, str):
                    created_at = gen.created
                elif isinstance(gen.created, int):
                    # timestamp转换为日期字符串
                    created_at = datetime.fromtimestamp(gen.created).strftime("%Y-%m-%d %H:%M:%S")
            
            # 🔥 修复：状态映射，使用正确的枚举值
            status_map = {
                VideoStatus.PENDING: 'processing',
                VideoStatus.PROCESSING: 'processing',
                VideoStatus.COMPLETED: 'completed',
                VideoStatus.FAILED: 'failed',
                VideoStatus.CANCELLED: 'failed'
            }
            status = status_map.get(gen.status, 'processing')
            
            # 进度
            progress = 100 if status == 'completed' else (50 if status == 'processing' else 0)
            
            videos.append({
                "id": gen.id,
                "prompt": prompt or "无提示词",
                "status": status,
                "progress": progress,
                "url": url,
                "date": created_at
            })
        
        logger.info(f"✅ 返回 {len(videos)} 个视频")
        
        return jsonify({
            "success": True,
            "videos": videos
        }), 200
    
    except Exception as e:
        logger.error(f"❌ 获取视频素材库失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@veo_video_api.route('/api/video/studio/delete/<video_id>', methods=['DELETE'])
def delete_video_from_library(video_id: str):
    """
    从素材库删除视频
    
    参数：
    - video_id: 视频ID
    
    响应：
    {
        "success": true,
        "message": "视频已删除"
    }
    """
    try:
        logger.info(f"🗑️ 删除视频: {video_id}")
        
        manager = get_veo_video_manager()
        success = manager.delete_generation(video_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "视频已删除"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "删除失败"
            }), 400
    
    except Exception as e:
        logger.error(f"❌ 删除视频失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def register_veo_video_routes(app):
    """注册 VeO 视频生成 API 路由"""
    app.register_blueprint(veo_video_api)
    
    logger.info("=" * 60)
    logger.info("📋 已注册的 VeO 视频生成 API 路由:")
    for rule in app.url_map.iter_rules():
        if 'api/veo' in rule.rule or 'api/video/studio' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("📡 API 提供商: AI-WX VeO 3.1")
    logger.info("🔗 支持图片 URL 输入（推荐）")
    logger.info("📦 支持 base64 图片输入（自动压缩）")
    logger.info("📋 视频素材库接口已启用")
    logger.info("=" * 60)