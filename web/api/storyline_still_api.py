"""
故事线剧照生成API
在故事线概览中一键生成角色/场景剧照，合并"生成图片+入库"为单接口
使用 DouBaoImageGenerator（与封面生成共用配置）
"""

import os
import re
import traceback
from datetime import datetime

from flask import jsonify, request

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.utils.path_utils import get_current_username
from src.utils.DouBaoImageGenerator import DouBaoImageGenerator
from src.managers.StillImageManager import get_still_image_manager
from src.models.still_image_models import StillImageType


def register_storyline_still_routes(app):
    """注册故事线剧照生成API路由"""

    generator = DouBaoImageGenerator()

    @app.route('/api/storyline/generate-still', methods=['POST'])
    @login_required
    def generate_storyline_still():
        """
        生成故事线剧照（合并接口：生成图片 + 自动入库）
        图片保存到 generated_images/{username}/{novel_title}/stills/ 目录

        请求体:
        {
            "project_id": "项目ID（小说标题）",
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
                "image_url": "/generated_images/username/title/stills/xxx.jpg",
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

            project_id = (data.get('project_id') or '').strip()
            prompt = (data.get('prompt') or '').strip()
            image_type_str = (data.get('image_type') or '').strip()

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

            character_name = (data.get('character_name') or '').strip() or None
            aspect_ratio = data.get('aspect_ratio') or ('16:9' if image_type_str == 'scene' else '9:16')
            novel_title = (data.get('novel_title') or '').strip() or project_id

            # 获取当前用户名
            try:
                username = get_current_username()
            except Exception:
                username = 'anonymous'

            # 清理小说标题中的特殊字符，用于路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)

            # 构建保存目录: generated_images/username/safe_title/stills/
            stills_dir = os.path.join(BASE_DIR, 'generated_images', username, safe_title, 'stills')
            os.makedirs(stills_dir, exist_ok=True)

            # 构造文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = character_name or f"scene_ch{chapter_num}"
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in '_-').rstrip('_')
            filename = f"storyline_{safe_name}_{timestamp}.jpg"
            save_path = os.path.join(stills_dir, filename)

            logger.info(f"🎬 故事线剧照生成请求: project={project_id}, ch={chapter_num}, type={image_type_str}, user={username}")
            logger.info(f"   prompt: {prompt[:80]}...")

            # 1. 生成图片（使用豆包，与封面生成共用配置）
            # 豆包只支持 OpenAI 标准尺寸，根据比例选择
            size_mapping = {
                '16:9': '1792x1024',
                '9:16': '1024x1792',
                '1:1': '1024x1024',
                '4:3': '1024x1024'
            }
            # 映射到豆包支持的 1K/2K 尺寸
            openai_size = size_mapping.get(aspect_ratio, '1024x1792')
            doubao_size = '2K' if openai_size in ('1792x1024', '1024x1792') else '1K'

            result = generator.generate_image(
                prompt=prompt,
                size=doubao_size,
                save_path=save_path
            )

            if not result or 'local_path' not in result:
                return jsonify({"success": False, "error": "图片生成失败或无返回路径"}), 500

            local_path = result['local_path']

            if not os.path.exists(local_path):
                return jsonify({"success": False, "error": "图片生成成功但文件未找到"}), 500

            # 构建 image_url（相对于 generated_images 的相对路径）
            rel_path = os.path.relpath(local_path, os.path.join(BASE_DIR, 'generated_images')).replace('\\', '/')
            image_url = f"/generated_images/{rel_path}"

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
                image_size=doubao_size,
                metadata={
                    "project_id": project_id,
                    "chapter_num": chapter_num,
                    "source": "storyline",
                    "username": username
                }
            )

            logger.info(f"✅ 故事线剧照生成并入库成功: {image.image_id}")
            logger.info(f"   文件: {local_path}")

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
