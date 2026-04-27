"""
故事线剧照生成API
在故事线概览中一键生成角色/场景剧照，合并"生成图片+入库"为单接口
"""

import os
import traceback
from datetime import datetime

from flask import jsonify, request

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.services.nanobanana_service import NanoBananaService
from src.managers.StillImageManager import get_still_image_manager
from src.models.still_image_models import StillImageType


def register_storyline_still_routes(app):
    """注册故事线剧照生成API路由"""

    nanobanana_service = NanoBananaService()

    @app.route('/api/storyline/generate-still', methods=['POST'])
    @login_required
    def generate_storyline_still():
        """
        生成故事线剧照（合并接口：生成图片 + 自动入库）

        请求体:
        {
            "project_id": "项目ID",
            "chapter_num": 1,
            "image_type": "scene" | "character",
            "prompt": "生成提示词（用户可编辑）",
            "character_name": "角色名",      // character类型时可选
            "aspect_ratio": "16:9" | "9:16", // 可选，场景默认16:9，角色默认9:16
            "novel_title": "小说标题"        // 可选，默认用project_id
        }

        响应:
        {
            "success": true,
            "data": {
                "image_id": "still_xxx",
                "image_url": "/generated_images/xxx.png",
                "local_path": "...",
                "prompt": "...",
                "aspect_ratio": "16:9",
                "character_name": "...",
                "metadata": { "project_id": "...", "chapter_num": 1, "source": "storyline" }
            }
        }
        """
        try:
            data = request.json or {}

            project_id = data.get('project_id', '').strip()
            prompt = data.get('prompt', '').strip()
            image_type_str = data.get('image_type', '').strip()

            if not project_id:
                return jsonify({"success": False, "error": "缺少 project_id"}), 400
            if not prompt:
                return jsonify({"success": False, "error": "缺少 prompt"}), 400
            if image_type_str not in ('scene', 'character'):
                return jsonify({"success": False, "error": "image_type 必须是 scene 或 character"}), 400

            chapter_num = data.get('chapter_num')
            if not isinstance(chapter_num, int):
                return jsonify({"success": False, "error": "chapter_num 必须是整数"}), 400

            image_type = StillImageType.SCENE if image_type_str == 'scene' else StillImageType.CHARACTER

            character_name = data.get('character_name', '').strip() or None
            default_ratio = '16:9' if image_type_str == 'scene' else '9:16'
            aspect_ratio = data.get('aspect_ratio', default_ratio)
            novel_title = data.get('novel_title', '').strip() or project_id

            # 校验比例
            if aspect_ratio not in ('16:9', '9:16', '1:1', '4:3'):
                aspect_ratio = default_ratio

            # 构造保存文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = character_name or f"scene_ch{chapter_num}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in '_-').rstrip('_')
            save_filename = f"storyline_{project_id}_{safe_name}_{timestamp}"

            logger.info(f"🎬 故事线剧照生成请求: project={project_id}, ch={chapter_num}, type={image_type_str}")
            logger.info(f"   prompt: {prompt[:80]}...")

            # 1. 生成图片
            gen_result = nanobanana_service.generate_image({
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": "2K",
                "save_filename": save_filename
            })

            if not gen_result.get('success'):
                err = gen_result.get('error', '图片生成失败')
                logger.error(f"❌ 故事线剧照生成失败: {err}")
                return jsonify({"success": False, "error": err}), 500

            local_path = gen_result.get('local_path')
            image_url = gen_result.get('url')

            if not local_path or not os.path.exists(local_path):
                return jsonify({"success": False, "error": "图片生成成功但文件未找到"}), 500

            # 2. 自动入库
            manager = get_still_image_manager()
            image = manager.add_image(
                image_type=image_type,
                prompt=prompt,
                local_path=local_path,
                image_url=image_url,
                novel_title=novel_title,
                character_name=character_name,
                event_name=f"第{chapter_num}章" if image_type_str == 'scene' else None,
                aspect_ratio=aspect_ratio,
                image_size="2K",
                metadata={
                    "project_id": project_id,
                    "chapter_num": chapter_num,
                    "source": "storyline"
                }
            )

            logger.info(f"✅ 故事线剧照生成并入库成功: {image.image_id}")

            return jsonify({
                "success": True,
                "data": image.to_dict()
            }), 201

        except Exception as e:
            logger.error(f"❌ 生成故事线剧照失败: {e}")
            logger.error(f"❌ 错误详情: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/storyline/stills', methods=['GET'])
    @login_required
    def list_storyline_stills():
        """
        查询故事线剧照（按 project_id + chapter_num 过滤）

        查询参数:
        - project_id: 项目ID（必需）
        - chapter_num: 章节号（可选）
        - image_type: scene | character（可选）
        - limit: 数量限制（默认50）
        """
        try:
            project_id = request.args.get('project_id', '').strip()
            if not project_id:
                return jsonify({"success": False, "error": "缺少 project_id"}), 400

            chapter_num = request.args.get('chapter_num', type=int)
            image_type_str = request.args.get('image_type')
            limit = request.args.get('limit', 50, type=int)

            manager = get_still_image_manager()
            all_images = manager.list_images(limit=500, order='desc')

            filtered = []
            for img in all_images:
                meta = img.metadata or {}
                if meta.get('project_id') != project_id:
                    continue
                if chapter_num is not None and meta.get('chapter_num') != chapter_num:
                    continue
                if image_type_str and img.image_type.value != image_type_str:
                    continue
                filtered.append(img)

            filtered = filtered[:limit]

            return jsonify({
                "success": True,
                "data": [img.to_dict() for img in filtered],
                "total": len(filtered)
            }), 200

        except Exception as e:
            logger.error(f"❌ 查询故事线剧照失败: {e}")
            logger.error(f"❌ 错误详情: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
