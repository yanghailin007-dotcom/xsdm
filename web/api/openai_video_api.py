"""
OpenAI 标准视频生成 API 路由

符合 OpenAI API 规范的视频生成接口
使用 AI-WX API (https://jyapi.ai-wx.cn)
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
from typing import Dict, Any
import json

from src.utils.logger import get_logger
from src.models.video_openai_models import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoInput,
    GenerationConfig,
    OutputConfig,
    SafetySetting,
    VideoMetadata,
    HarmCategory,
    HarmBlockThreshold,
    HarmBlockMethod
)
from src.managers.AiWxVideoManager import get_aiwx_video_manager

# 创建蓝图
openai_video_api = Blueprint('openai_video_api', __name__)

# 初始化日志
logger = get_logger(__name__)


def parse_request(data: Dict[str, Any]) -> VideoGenerationRequest:
    """解析请求数据"""
    # 解析 input
    input_data = None
    if data.get('input'):
        input_dict = data['input']
        input_data = VideoInput(
            type=input_dict.get('type', 'multimodal'),
            text=input_dict.get('text')
        )
        # 图片、视频、音频可以后续扩展
    
    # 解析 generation_config
    gen_config = None
    if data.get('generation_config'):
        config_dict = data['generation_config']
        gen_config = GenerationConfig(
            duration_seconds=config_dict.get('duration_seconds', 5),
            resolution=config_dict.get('resolution', '1080p'),
            aspect_ratio=config_dict.get('aspect_ratio', '16:9'),
            fps=config_dict.get('fps', 24),
            style=config_dict.get('style', 'cinematic'),
            temperature=config_dict.get('temperature', 1.0),
            top_p=config_dict.get('top_p', 0.95),
            top_k=config_dict.get('top_k', 40),
            seed=config_dict.get('seed'),
            num_videos=config_dict.get('num_videos', 1)
        )
    
    # 解析 output_config
    output_config = None
    if data.get('output_config'):
        output_dict = data['output_config']
        output_config = OutputConfig(
            format=output_dict.get('format', 'mp4'),
            codec=output_dict.get('codec', 'h264'),
            quality=output_dict.get('quality', 'high'),
            include_audio=output_dict.get('include_audio', True)
        )
    
    # 解析 safety_settings
    safety_settings = []
    for setting in data.get('safety_settings', []):
        safety_settings.append(SafetySetting(
            category=HarmCategory(setting['category']),
            threshold=HarmBlockThreshold(setting['threshold']),
            method=HarmBlockMethod(setting.get('method', 'PROBABILITY'))
        ))
    
    # 解析 metadata
    metadata = None
    if data.get('metadata'):
        metadata_dict = data['metadata']
        metadata = VideoMetadata(
            user_id=metadata_dict.get('user_id'),
            project_id=metadata_dict.get('project_id'),
            labels=metadata_dict.get('labels', {})
        )
    
    # 创建请求对象
    return VideoGenerationRequest(
        model=data['model'],
        prompt=data['prompt'],
        input=input_data,
        generation_config=gen_config,
        output_config=output_config,
        safety_settings=safety_settings,
        system_instruction=data.get('system_instruction'),
        metadata=metadata
    )


@openai_video_api.route('/v1/videos/generations', methods=['POST'])
def create_generation():
    """
    创建视频生成任务
    
    请求体：
    {
        "model": "video-model-name",
        "prompt": "视频生成的文本描述",
        "generation_config": {
            "duration_seconds": 5,
            "resolution": "1080p",
            ...
        }
    }
    
    响应：
    {
        "id": "gen_abc123",
        "object": "video.generation",
        "created": 1699874567,
        "status": "processing",
        ...
    }
    """
    try:
        data = request.json or {}
        
        # 验证必需参数
        if not data.get('model'):
            return jsonify({
                "error": {
                    "message": "Missing required parameter: model",
                    "type": "invalid_request_error"
                }
            }), 400
        
        if not data.get('prompt'):
            return jsonify({
                "error": {
                    "message": "Missing required parameter: prompt",
                    "type": "invalid_request_error"
                }
            }), 400
        
        # 解析请求
        req = parse_request(data)
        
        # 获取 AI-WX 管理器
        manager = get_aiwx_video_manager()
        
        # 创建生成任务
        response = manager.create_generation(req)
        
        logger.info(f"✅ 创建 AI-WX 视频生成任务: {response.id}")
        
        return jsonify(response.to_dict()), 202
    
    except Exception as e:
        logger.error(f"❌ 创建生成任务失败: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@openai_video_api.route('/v1/videos/generations/<generation_id>', methods=['GET'])
def retrieve_generation(generation_id: str):
    """
    查询生成状态
    
    参数：
    - generation_id: 生成任务ID
    
    响应：
    {
        "id": "gen_abc123",
        "status": "completed",
        "result": {...}
    }
    """
    try:
        manager = get_aiwx_video_manager()
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
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500


@openai_video_api.route('/v1/videos/generations', methods=['GET'])
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
        "object": "list",
        "total": 100
    }
    """
    try:
        limit = int(request.args.get('limit', 20))
        status_str = request.args.get('status')
        order = request.args.get('order', 'desc')
        
        # 将字符串状态转换为 GenerationStatus 枚举
        from src.models.video_openai_models import GenerationStatus
        status = GenerationStatus(status_str) if status_str else None
        
        manager = get_aiwx_video_manager()
        generations = manager.list_generations(
            limit=limit,
            status=status,
            order=order
        )
        
        return jsonify({
            "data": [g.to_dict() for g in generations],
            "object": "list",
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


@openai_video_api.route('/v1/videos/generations/<generation_id>/cancel', methods=['POST'])
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
        manager = get_aiwx_video_manager()
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


@openai_video_api.route('/v1/videos/generations/stream', methods=['POST'])
def stream_generation():
    """
    流式生成视频（Server-Sent Events）
    
    注意：AI-WX API 目前不支持流式生成，此端点返回错误
    
    响应：错误信息
    """
    return jsonify({
        "error": {
            "message": "Streaming is not supported by AI-WX API. Please use the standard POST /v1/videos/generations endpoint and poll for results using GET /v1/videos/generations/{id}",
            "type": "invalid_request_error"
        }
    }), 400


def register_openai_video_routes(app):
    """注册 OpenAI 标准视频生成 API 路由"""
    app.register_blueprint(openai_video_api)
    
    logger.info("=" * 60)
    logger.info("📋 已注册的 OpenAI 标准视频生成 API 路由 (使用 AI-WX):")
    for rule in app.url_map.iter_rules():
        if 'v1/videos' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("📡 API 提供商: AI-WX (https://jyapi.ai-wx.cn)")
    logger.info("=" * 60)