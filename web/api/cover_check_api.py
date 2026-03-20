"""
封面检查 API
提供项目封面存在性检查接口
"""

from flask import Blueprint, jsonify, current_app
from pathlib import Path
import logging
import os

from web.utils.path_utils import get_novel_project_dir, get_current_username

logger = logging.getLogger(__name__)
cover_check_api = Blueprint('cover_check_api', __name__)


@cover_check_api.route('/api/project/<title>/check-cover', methods=['GET'])
def check_project_cover(title):
    """
    检查项目封面是否存在
    
    检查以下路径：
    1. {project_dir}/cover.png
    2. {project_dir}/cover.jpg
    3. {project_dir}/images/cover.png
    4. {project_dir}/images/cover.jpg
    5. generated_images/{username}/{title}/ 目录下的图片
    
    Returns:
        {
            "has_cover": bool,
            "cover_path": str or None,  # 相对路径
            "checked_paths": [str]  # 检查过的路径列表
        }
    """
    try:
        from urllib.parse import unquote
        title = unquote(title)
        
        # 获取当前用户名
        username = get_current_username()
        
        # 获取项目目录
        project_dir = get_novel_project_dir(title, username, create=False)
        
        checked_paths = []
        
        # 1. 首先检查项目目录下的标准封面路径
        if project_dir and project_dir.exists():
            cover_paths = [
                project_dir / 'cover.png',
                project_dir / 'cover.jpg',
                project_dir / 'images' / 'cover.png',
                project_dir / 'images' / 'cover.jpg',
            ]
            
            checked_paths = [str(p.relative_to(project_dir.parent.parent.parent)) for p in cover_paths]
            
            for cover_path in cover_paths:
                if cover_path.exists():
                    logger.info(f"[CoverCheck] ✅ 找到封面(项目目录): {cover_path}")
                    return jsonify({
                        "has_cover": True,
                        "cover_path": str(cover_path.relative_to(project_dir.parent.parent.parent)),
                        "checked_paths": checked_paths
                    })
        
        # 2. 检查 generated_images/{username}/{title}/ 目录
        base_dir = Path(current_app.root_path).parent
        
        # 尝试多种目录名变体（原始标题、清理后的标题）
        possible_dirs = [
            base_dir / 'generated_images' / username / title,  # 原始标题
            base_dir / 'generated_images' / username / "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip(),  # 清理后的标题
        ]
        
        generated_cover_dir = None
        for d in possible_dirs:
            checked_paths.append(str(d.relative_to(base_dir)))
            if d.exists():
                generated_cover_dir = d
                break
        
        logger.info(f"[CoverCheck] 检查 generated_images 目录: {possible_dirs}")
        
        if generated_cover_dir:
            # 查找目录下的图片文件
            image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
            cover_files = []
            
            for ext in image_extensions:
                cover_files.extend(generated_cover_dir.glob(f'*{ext}'))
            
            if cover_files:
                # 按修改时间排序，取最新的
                cover_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_cover = cover_files[0]
                
                # 构建相对路径
                rel_path = f"generated_images/{username}/{generated_cover_dir.name}/{latest_cover.name}"
                
                logger.info(f"[CoverCheck] ✅ 找到封面(generated_images): {rel_path}")
                
                # 如果有多张封面，返回所有封面供选择
                if len(cover_files) > 1:
                    all_covers = [f"generated_images/{username}/{generated_cover_dir.name}/{f.name}" for f in cover_files]
                    return jsonify({
                        "has_cover": True,
                        "cover_path": rel_path,
                        "all_covers": all_covers,
                        "cover_count": len(cover_files),
                        "checked_paths": checked_paths
                    })
                
                return jsonify({
                    "has_cover": True,
                    "cover_path": rel_path,
                    "checked_paths": checked_paths
                })
        
        # 3. 还检查旧的 generated_images/{title}/ 目录（兼容旧数据）
        old_generated_dir = base_dir / 'generated_images' / title
        if not old_generated_dir.exists():
            old_generated_dir = base_dir / 'generated_images' / "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        if old_generated_dir.exists():
            image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
            cover_files = []
            
            for ext in image_extensions:
                cover_files.extend(old_generated_dir.glob(f'*{ext}'))
            
            if cover_files:
                cover_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_cover = cover_files[0]
                
                rel_path = f"generated_images/{safe_title}/{latest_cover.name}"
                checked_paths.append(rel_path)
                
                logger.info(f"[CoverCheck] ✅ 找到封面(旧目录): {rel_path}")
                return jsonify({
                    "has_cover": True,
                    "cover_path": rel_path,
                    "checked_paths": checked_paths
                })
        
        logger.info(f"[CoverCheck] ⚠️ 项目缺少封面: {title}")
        return jsonify({
            "has_cover": False,
            "cover_path": None,
            "checked_paths": checked_paths,
            "suggested_paths": [
                f"{project_dir}/cover.png" if project_dir else None,
                f"{project_dir}/images/cover.png" if project_dir else None,
                f"generated_images/{username}/{safe_title}/"
            ]
        })
        
    except Exception as e:
        logger.error(f"[CoverCheck] 检查封面失败: {e}")
        return jsonify({
            "has_cover": False,
            "cover_path": None,
            "error": str(e)
        }), 500
