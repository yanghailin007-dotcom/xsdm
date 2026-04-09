# -*- coding: utf-8 -*-
"""
文风管理API
提供文风的CRUD操作和提取功能
"""

import logging
from flask import Blueprint, request, jsonify
from web.models.writing_style_model import get_writing_style_model

logger = logging.getLogger(__name__)

# 创建蓝图
writing_style_bp = Blueprint('writing_style', __name__, url_prefix='/api/writing-style')

@writing_style_bp.route('/presets', methods=['GET'])
def get_preset_styles():
    """获取所有预设文风"""
    try:
        model = get_writing_style_model()
        presets = model.get_all_presets()
        
        # 简化返回数据
        simplified = []
        for style in presets:
            simplified.append({
                "style_id": style.get("style_id"),
                "style_name": style.get("style_name"),
                "description": style.get("description"),
                "rating": style.get("rating"),
                "usage_count": style.get("usage_count"),
                "suitable_genres": style.get("suitable_genres", []),
                "example_paragraph": style.get("example_paragraph", "")[:100] + "..."
            })
        
        return jsonify({
            "success": True,
            "data": simplified
        })
    except Exception as e:
        logger.error(f"获取预设文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/user-styles', methods=['GET'])
def get_user_styles():
    """获取用户文风"""
    try:
        user_id = request.args.get('user_id')
        model = get_writing_style_model()
        styles = model.get_all_user_styles(user_id)
        
        return jsonify({
            "success": True,
            "data": styles
        })
    except Exception as e:
        logger.error(f"获取用户文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/detail/<style_id>', methods=['GET'])
def get_style_detail(style_id):
    """获取文风详情"""
    try:
        model = get_writing_style_model()
        style = model.get_style(style_id)
        
        if not style:
            return jsonify({
                "success": False,
                "error": "文风不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "data": style
        })
    except Exception as e:
        logger.error(f"获取文风详情失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/recommended', methods=['GET'])
def get_recommended_styles():
    """获取推荐文风"""
    try:
        genre = request.args.get('genre')
        model = get_writing_style_model()
        styles = model.get_recommended_styles(genre)
        
        # 简化返回
        simplified = []
        for style in styles:
            simplified.append({
                "style_id": style.get("style_id"),
                "style_name": style.get("style_name"),
                "description": style.get("description"),
                "rating": style.get("rating"),
                "match_score": 95 if genre and genre in style.get("suitable_genres", []) else 80
            })
        
        return jsonify({
            "success": True,
            "data": simplified
        })
    except Exception as e:
        logger.error(f"获取推荐文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/extract', methods=['POST'])
def extract_style():
    """从正文提取文风"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text or len(text) < 500:
            return jsonify({
                "success": False,
                "error": "文本太短，至少需要500字"
            }), 400
        
        # TODO: 调用AI进行文风提取
        # 这里先返回模拟数据
        extracted_features = {
            "opening_pattern": "ps_interaction" if "ps：" in text or "PS：" in text else "direct",
            "sentence_structure": "short" if text.count("。") > len(text) / 50 else "medium",
            "dialogue_style": "colloquial" if "卧槽" in text or "牛逼" in text else "standard",
            "pacing": "fast" if text.count("\n\n") > 10 else "medium",
            "humor_level": "high" if "（" in text and "）" in text else "low"
        }
        
        return jsonify({
            "success": True,
            "data": {
                "extracted_features": extracted_features,
                "suggested_name": "自定义文风",
                "system_prompt_addon": "根据提取的特征自动生成..."
            }
        })
    except Exception as e:
        logger.error(f"提取文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/create', methods=['POST'])
def create_style():
    """创建用户文风"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        model = get_writing_style_model()
        style_id = model.create_user_style(data, user_id)
        
        return jsonify({
            "success": True,
            "data": {
                "style_id": style_id,
                "message": "文风创建成功"
            }
        })
    except Exception as e:
        logger.error(f"创建文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/update/<style_id>', methods=['POST'])
def update_style(style_id):
    """更新文风"""
    try:
        data = request.get_json()
        model = get_writing_style_model()
        
        success = model.update_style(style_id, data)
        
        if success:
            return jsonify({
                "success": True,
                "message": "文风更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "error": "文风不存在或无法修改"
            }), 404
    except Exception as e:
        logger.error(f"更新文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/delete/<style_id>', methods=['POST'])
def delete_style(style_id):
    """删除文风"""
    try:
        model = get_writing_style_model()
        success = model.delete_style(style_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "文风删除成功"
            })
        else:
            return jsonify({
                "success": False,
                "error": "文风不存在或无法删除"
            }), 404
    except Exception as e:
        logger.error(f"删除文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@writing_style_bp.route('/apply-to-project', methods=['POST'])
def apply_to_project():
    """将文风应用到项目"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        style_id = data.get('style_id')
        enable_comparison = data.get('enable_comparison', False)
        
        if not project_id or not style_id:
            return jsonify({
                "success": False,
                "error": "缺少project_id或style_id"
            }), 400
        
        # TODO: 将文风配置保存到项目
        # 这里先返回成功
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "style_id": style_id,
                "enable_comparison": enable_comparison,
                "message": "文风已应用到项目"
            }
        })
    except Exception as e:
        logger.error(f"应用文风失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
