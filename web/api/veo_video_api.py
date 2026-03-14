"""
VeO 视频生成 API 路由
支持两种图片输入模式：
1. 图片 URL（本地文件路径）：如 /project-files/xxx.png，会自动读取并转换为 base64
2. Base64 图片：传递 base64 编码的图片数据（会自动压缩）
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
import traceback
import os
import base64
from pathlib import Path
from urllib.parse import unquote

from web.auth import login_required
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
        "private": true,
        "metadata": {  // 🔥 新增：元数据，用于按项目/分集组织视频
            "novel_title": "小说名",
            "episode_title": "第一集",
            "shot_number": "1",
            "shot_type": "全景"
        }
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
                    logger.warning(f"⚠️  图片 {i} 数据无效")
                    continue
                
                # 检查是否是 URL
                if img.startswith(('http://', 'https://')):
                    logger.info(f"  - 图片 {i+1}: {img[:100]}... (URL)")
                elif len(img) > 100:
                    logger.info(f"  - 图片 {i+1}: base64 长度 {len(img)} 字符")
                else:
                    logger.warning(f"  - 图片 {i+1}: 数据太短，可能无效")
        
        # 创建 VeO 原生请求
        # 🔥 根据是否有参考图自动选择模型（强制覆盖用户配置）
        # - 有参考图：强制使用 veo_3_1-fast-components（参考图模式）
        # - 无参考图：强制使用 veo_3_1-fast（首尾帧模式）
        user_provided_model = data.get('model')

        # 自动选择模型：根据是否有图片强制设置正确的模型
        if images:
            # 有参考图：强制使用 veo_3_1-fast-components
            auto_model = 'veo_3_1-fast-components'
            if user_provided_model and user_provided_model != auto_model:
                logger.info(f"⚠️  用户指定模型 {user_provided_model}，但检测到参考图，自动切换为: {auto_model}")
            else:
                logger.info(f"🖼️  检测到参考图，使用模型: {auto_model}")
        else:
            # 无参考图：强制使用 veo_3_1-fast
            auto_model = 'veo_3_1-fast'
            if user_provided_model and user_provided_model != auto_model:
                logger.info(f"⚠️  用户指定模型 {user_provided_model}，但无参考图，自动切换为: {auto_model}")
            else:
                logger.info(f"📝 无参考图，使用模型: {auto_model}")

        # 🔥 提取元数据（用于按项目/分集组织视频）
        metadata = data.get('metadata', {})
        if metadata:
            logger.info(f"📁 视频元数据: {metadata}")

        # 🔥 质量检查已禁用 - 用户点击生成视频时不需要质量检查
        # 前端已移除自动质量检查，如需检查可手动点击"剧本质量检查"按钮
        skip_quality_check = data.get('skip_quality_check', True)  # 默认跳过

        if not skip_quality_check and metadata.get('novel_title'):
            try:
                from web.api.script_quality_check import ScriptQualityChecker, load_all_novel_data

                novel_title = metadata.get('novel_title', '')
                episode_title = metadata.get('episode_title', '')

                # 构建待检查的镜头数据
                check_shots = [{
                    "description": data.get('prompt', ''),
                    "veo_prompt": data.get('prompt', ''),
                    "shot_type": metadata.get('shot_type', '中景'),
                    "generation_prompt": data.get('prompt', '')
                }]

                # 使用新的API加载所有小说数据
                novel_data = load_all_novel_data(novel_title)
                checker = ScriptQualityChecker(novel_data, novel_title)
                result = checker.check(check_shots, episode_title)

                logger.info(f"📋 剧本质量检查结果: 评分={result.get('score', 'N/A')}, 通过={result.get('passed', 'N/A')}")

                # 如果有严重问题，记录警告但仍然允许生成（前端已做拦截）
                if not result.get('passed', True):
                    critical_issues = [i for i in result.get('issues', []) if i.get('severity') == 'critical']
                    if critical_issues:
                        for issue in critical_issues:
                            logger.warning(f"  - {issue.get('message')}: {issue.get('suggestion', '')}")

            except Exception as e:
                logger.warning(f"⚠️ 质量检查失败，继续生成: {e}")
        else:
            logger.info(f"⏭️ 跳过质量检查，直接生成视频")

        veo_request = VeOCreateVideoRequest(
            images=images,
            model=auto_model,
            orientation=data.get('orientation', 'portrait'),
            prompt=data.get('prompt', ''),
            size=data.get('size', 'large'),
            duration=10,  # VeO只支持10秒
            watermark=data.get('watermark', False),
            private=data.get('private', True),
            metadata=metadata  # 🔥 传递元数据
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

        # 🔥 收集处理好的 base64 图片数据（不含前缀，用于 VeOManager）
        processed_base64_images = []

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
        for img_data in veo_request.images:
            image_url_value = None

            # 🔥 检查是否是本地文件路径（/project-files/ 或 /generated_images/ 或 /static/ 或 /api/short-drama/projects/）
            if img_data.startswith('/project-files/') or img_data.startswith('/generated_images/') or img_data.startswith('/static/') or img_data.startswith('/api/short-drama/projects/'):
                # 本地文件模式：读取文件并转换为 base64
                try:
                    from urllib.parse import unquote

                    # 提取路径部分
                    if img_data.startswith('/project-files/'):
                        decoded_path = unquote(img_data.replace('/project-files/', ''))
                        base_path = Path('视频项目').resolve()
                    elif img_data.startswith('/generated_images/'):
                        decoded_path = unquote(img_data.replace('/generated_images/', ''))
                        base_path = Path('generated_images').resolve()
                    elif img_data.startswith('/static/generated_images/'):
                        decoded_path = unquote(img_data.replace('/static/generated_images/', ''))
                        base_path = Path('static/generated_images').resolve()
                    elif img_data.startswith('/api/short-drama/projects/'):
                        # 处理角色图片URL: /api/short-drama/projects/{小说名}/{集数名}/{文件名}
                        decoded_path = unquote(img_data.replace('/api/short-drama/projects/', ''))
                        base_path = Path('视频项目').resolve()
                    else:
                        decoded_path = unquote(img_data)
                        base_path = Path('.').resolve()

                    logger.info(f"📂 本地文件路径: {decoded_path}")
                    logger.info(f"📂 基础路径: {base_path}")

                    # 构建完整文件路径
                    full_path = (base_path / decoded_path).resolve()

                    logger.info(f"📂 完整文件路径: {full_path}")

                    # 安全检查
                    if not str(full_path).startswith(str(base_path)):
                        logger.error(f"❌ 非法路径访问: {img_data}")
                        continue

                    if not full_path.exists():
                        logger.error(f"❌ 文件不存在: {full_path}")
                        # 尝试列出父目录的内容，帮助调试
                        if full_path.parent.exists():
                            existing_files = list(full_path.parent.glob('*.png')) + list(full_path.parent.glob('*.jpg'))
                            logger.info(f"📂 父目录中的图片文件: {[f.name for f in existing_files]}")
                        continue

                    # 读取文件并转换为 base64
                    with open(full_path, 'rb') as f:
                        file_data = f.read()
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    image_url_value = f"data:image/jpeg;base64,{base64_data}"
                    # 🔥 收集纯 base64 数据（不含前缀），用于 VeOManager
                    processed_base64_images.append(base64_data)
                    logger.info(f"✅ 文件已转换为 base64，大小: {len(file_data)} 字节")

                except Exception as e:
                    logger.error(f"❌ 读取本地文件失败 {img_data}: {e}")
                    continue

            elif img_data.startswith(('http://', 'https://')):
                # 外部 URL 模式：直接使用
                image_url_value = img_data
                # 外部 URL 需要由 VeOManager 下载，暂时保留原值
                processed_base64_images.append(img_data)
            else:
                # Base64 模式：需要添加 data URI 前缀
                image_url_value = f"data:image/jpeg;base64,{img_data}"
                # 收集纯 base64 数据
                processed_base64_images.append(img_data)

            if image_url_value:
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url_value
                    }
                })

        # 🔥 更新 veo_request.images 为处理好的图片数据
        # 这样 VeOManager 就可以直接使用，不需要再次处理
        veo_request.images = processed_base64_images
        
        openai_request = VeOVideoRequest(
            model=veo_request.model,
            messages=messages,
            stream=True,
            metadata=metadata  # 传递 metadata
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


@veo_video_api.route('/api/video/reference-image/upload', methods=['POST'])
@login_required
def upload_reference_image():
    """
    上传本地参考图片到项目目录

    请求体：multipart/form-data
    - image: 图片文件
    - novel_title: 小说标题
    - episode_title: 分集标题
    - shot_number: 镜头编号（可选）

    响应：
    {
        "success": true,
        "url": "/api/short-drama/projects/...",
        "name": "文件名"
    }
    """
    try:
        from flask import send_from_directory
        import uuid
        from pathlib import Path

        # 获取表单数据
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "缺少图片文件"
            }), 400

        file = request.files['image']
        novel_title = request.form.get('novel_title', '')
        episode_title = request.form.get('episode_title', '')
        shot_number = request.form.get('shot_number', '')

        if not novel_title:
            return jsonify({
                "success": False,
                "error": "缺少小说标题"
            }), 400

        logger.info(f"📤 上传参考图片: {file.filename}, 项目: {novel_title}, 分集: {episode_title}")

        # 构建保存路径：视频项目/小说标题/分集标题/reference_images/
        # 使用URL安全的文件名
        import re
        safe_novel_title = re.sub(r'[\\/*?"<>|]', '_', novel_title)
        safe_episode_title = re.sub(r'[\\/*?"<>|]', '_', episode_title)

        # 创建目录
        base_dir = Path("视频项目") / safe_novel_title / safe_episode_title / "reference_images"
        base_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        file_ext = Path(file.filename).suffix or '.png'
        unique_id = str(uuid.uuid4())[:8]
        filename = f"ref_{unique_id}{file_ext}"
        file_path = base_dir / filename

        # 保存文件
        file.save(str(file_path))
        logger.info(f"✅ 图片已保存: {file_path}")

        # 返回访问URL
        url_path = f"/api/short-drama/projects/{safe_novel_title}/{safe_episode_title}/reference_images/{filename}"

        return jsonify({
            "success": True,
            "url": url_path,
            "name": filename,
            "full_path": str(file_path)
        })

    except Exception as e:
        logger.error(f"❌ 上传参考图片失败: {e}")
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


@veo_video_api.route('/api/video/check-exists', methods=['POST'])
def check_video_exists():
    """
    检查指定镜头的视频文件是否已存在

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "1集_黄金开局：退婚流当场变'舔狗流'",
        "event_name": "事件名",
        "shot_number": "1",
        "shot_type": "全景"
    }

    响应：
    {
        "success": true,
        "exists": true,
        "video_url": "/project-files/...",
        "file_path": "视频项目/..."
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')
        episode_title = data.get('episode_title', '')
        event_name = data.get('event_name', '')
        shot_number = data.get('shot_number', '')
        shot_type = data.get('shot_type', 'shot')

        logger.info(f"🔍 检查视频是否存在: {novel_title}/{episode_title}/{event_name}_{shot_number}_{shot_type}")

        # 导入路径构造函数
        from src.managers.VeOVideoManager import get_video_save_path, sanitize_path, VIDEO_PROJECT_BASE_DIR

        # 构造元数据
        metadata = {
            'novel_title': novel_title,
            'episode_title': episode_title,
            'event_name': event_name,
            'shot_number': shot_number,
            'shot_type': shot_type
        }

        # 获取视频保存路径
        video_path = get_video_save_path(metadata, 'check')

        # 检查文件是否存在
        if video_path.exists():
            # 构造HTTP URL路径
            relative_path = video_path.relative_to(VIDEO_PROJECT_BASE_DIR)
            path_str = str(relative_path).replace('\\', '/')
            video_url = f"/project-files/{path_str}"

            logger.info(f"✅ 视频文件已存在: {video_path}")

            return jsonify({
                "success": True,
                "exists": True,
                "video_url": video_url,
                "file_path": str(video_path)
            }), 200
        else:
            logger.info(f"❌ 视频文件不存在: {video_path}")

            return jsonify({
                "success": True,
                "exists": False,
                "video_url": None,
                "file_path": str(video_path)
            }), 200

    except Exception as e:
        logger.error(f"❌ 检查视频是否存在失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def register_veo_video_routes(app):
    """注册 VeO 视频生成 API 路由"""
    app.register_blueprint(veo_video_api)
    
    # 🔥 精简：只保留一行关键日志，详细路由使用 DEBUG 级别
    logger.info("✅ VeO 视频 API 已注册 (AI-WX VeO 3.1)")
    logger.debug("📋 VeO 视频 API 路由详情:")
    for rule in app.url_map.iter_rules():
        if 'api/veo' in rule.rule or 'api/video/studio' in rule.rule:
            logger.debug(f"  - {rule.methods} {rule.rule}")