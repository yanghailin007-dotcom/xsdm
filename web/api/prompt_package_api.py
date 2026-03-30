"""
提示词包管理 API
提供提示词包的 CRUD、导入导出功能
"""

import json
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file, session
from functools import wraps

# 导入提示词包管理器
try:
    from web.services.prompt_package import PromptPackageManager, PromptPackage
    HAS_PROMPT_PACKAGE = True
except ImportError as e:
    logging.error(f"[PromptPackageAPI] 导入失败: {e}")
    HAS_PROMPT_PACKAGE = False

logger = logging.getLogger(__name__)

# 创建蓝图
prompt_package_api = Blueprint('prompt_package_api', __name__, url_prefix='/api/v2')


def require_login(f):
    """验证登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_manager():
    """获取提示词包管理器实例"""
    if not HAS_PROMPT_PACKAGE:
        raise RuntimeError("提示词包模块未加载")
    return PromptPackageManager()


def get_user_id():
    """获取当前用户ID"""
    return session.get('user', session.get('user_id', 'anonymous'))


# ==================== API 路由 ====================

@prompt_package_api.route('/prompt-packages', methods=['GET'])
@require_login
def list_packages():
    """
    列出所有提示词包
    
    Query参数:
        mode: 可选，过滤特定模式
    
    Returns:
        {
            "packages": [
                {
                    "id": "包ID",
                    "name": "包名称",
                    "description": "描述",
                    "mode": "生成模式",
                    "is_default": true/false,
                    "is_editable": true/false,
                    "total_steps": 7
                }
            ]
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        mode = request.args.get('mode')
        
        packages = manager.list_packages(user_id=user_id, mode=mode)
        return jsonify({"packages": packages})
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 列出包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>', methods=['GET'])
@require_login
def get_package(package_id):
    """
    获取提示词包详情
    
    Returns:
        {
            "package": {
                "id": "...",
                "name": "...",
                "steps": [...]
            }
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        
        package = manager.get_package(package_id, user_id)
        if not package:
            return jsonify({"error": "包不存在"}), 404
        
        # 转换为字典（包含步骤详情）
        package_data = {
            "id": package.id,
            "name": package.name,
            "description": package.description,
            "mode": package.mode,
            "version": package.info.get("version", "1.0.0"),
            "is_default": package.is_default,
            "is_editable": package.is_editable,
            "tags": package.info.get("tags", []),
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_name": step.step_name,
                    "step_order": step.step_order,
                    "enabled": step.enabled,
                    "description": step.description,
                    "prompt_template": step.prompt_template,
                    "parameters": step.parameters,
                    "output_schema": step.output_schema
                }
                for step in package.get_all_steps()
            ]
        }
        
        return jsonify({"package": package_data})
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 获取包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages', methods=['POST'])
@require_login
def create_package():
    """
    创建新的提示词包
    
    Request Body:
        {
            "name": "包名称",
            "description": "描述",
            "base_package_id": "基础包ID（可选）",
            "mode": "生成模式"
        }
    
    Returns:
        {
            "package": {"id": "...", "name": "..."}
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        data = request.json
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        base_package_id = data.get('base_package_id')
        mode = data.get('mode', 'market_driven')
        
        if not name:
            return jsonify({"error": "名称不能为空"}), 400
        
        package = manager.create_package(
            user_id=user_id,
            name=name,
            base_package_id=base_package_id,
            mode=mode,
            description=description
        )
        
        return jsonify({
            "package": {
                "id": package.id,
                "name": package.name
            }
        }), 201
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 创建包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>', methods=['PUT'])
@require_login
def update_package(package_id):
    """
    更新提示词包基本信息
    
    Request Body:
        {
            "name": "新名称",
            "description": "新描述"
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        data = request.json
        
        package = manager.get_package(package_id, user_id)
        if not package:
            return jsonify({"error": "包不存在"}), 404
        
        if package.is_default:
            return jsonify({"error": "系统默认包不能修改"}), 403
        
        # 更新信息
        if 'name' in data:
            package.info['name'] = data['name'].strip()
        if 'description' in data:
            package.info['description'] = data['description'].strip()
        if 'tags' in data:
            package.info['tags'] = data['tags']
        
        package.info['updated_at'] = __import__('datetime').datetime.now().isoformat()
        package.save()
        
        return jsonify({"message": "更新成功"})
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 更新包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>', methods=['DELETE'])
@require_login
def delete_package(package_id):
    """
    删除提示词包
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        
        success = manager.delete_package(package_id, user_id)
        if not success:
            return jsonify({"error": "包不存在或是系统默认包"}), 400
        
        return jsonify({"message": "删除成功"})
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 删除包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>/steps/<step_id>', methods=['PUT'])
@require_login
def update_step(package_id, step_id):
    """
    更新步骤配置
    
    Request Body:
        {
            "step_name": "步骤名称",
            "description": "描述",
            "enabled": true/false,
            "prompt_template": {...},
            "parameters": {...}
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        data = request.json
        
        package = manager.get_package(package_id, user_id)
        if not package:
            return jsonify({"error": "包不存在"}), 404
        
        if package.is_default:
            return jsonify({"error": "系统默认包不能修改，请复制后再编辑"}), 403
        
        step = package.get_step(step_id)
        if not step:
            return jsonify({"error": "步骤不存在"}), 404
        
        # 更新步骤配置
        if 'step_name' in data:
            step.step_name = data['step_name'].strip()
        if 'description' in data:
            step.description = data['description'].strip()
        if 'enabled' in data:
            step.enabled = bool(data['enabled'])
        if 'prompt_template' in data:
            step.prompt_template = data['prompt_template']
        if 'parameters' in data:
            step.parameters = data['parameters']
        
        # 保存
        step_data = {
            "step_id": step.step_id,
            "step_name": step.step_name,
            "step_order": step.step_order,
            "enabled": step.enabled,
            "description": step.description,
            "prompt_template": step.prompt_template,
            "parameters": step.parameters,
            "output_schema": step.output_schema
        }
        
        step_file = package.package_path / f"{step_id}.json"
        with open(step_file, 'w', encoding='utf-8') as f:
            json.dump(step_data, f, ensure_ascii=False, indent=2)
        
        # 更新包信息
        package.info['updated_at'] = __import__('datetime').datetime.now().isoformat()
        package.save()
        
        return jsonify({"message": "步骤更新成功"})
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 更新步骤失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>/duplicate', methods=['POST'])
@require_login
def duplicate_package(package_id):
    """
    复制提示词包
    
    Request Body:
        {
            "name": "新名称（可选）"
        }
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        data = request.json or {}
        
        source_package = manager.get_package(package_id)
        if not source_package:
            return jsonify({"error": "源包不存在"}), 404
        
        new_name = data.get('name') or f"{source_package.name} - 副本"
        
        new_package = manager.duplicate_package(package_id, user_id, new_name)
        if not new_package:
            return jsonify({"error": "复制失败"}), 500
        
        return jsonify({
            "package": {
                "id": new_package.id,
                "name": new_package.name
            }
        }), 201
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 复制包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/<package_id>/export', methods=['GET'])
@require_login
def export_package(package_id):
    """
    导出提示词包为 ZIP 文件
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        
        # 验证包存在且用户有权限
        package = manager.get_package(package_id, user_id)
        if not package:
            return jsonify({"error": "包不存在"}), 404
        
        # 导出为 ZIP
        zip_data = manager.export_package(package_id, user_id)
        
        # 创建临时文件
        import io
        buffer = io.BytesIO(zip_data)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{package.name}_v{package.info.get('version', '1.0.0')}.zip"
        )
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 导出包失败: {e}")
        return jsonify({"error": str(e)}), 500


@prompt_package_api.route('/prompt-packages/import', methods=['POST'])
@require_login
def import_package():
    """
    导入提示词包
    
    Form Data:
        file: ZIP 文件
        name: 可选，重命名
    """
    try:
        manager = get_manager()
        user_id = get_user_id()
        
        if 'file' not in request.files:
            return jsonify({"error": "请上传文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "请选择文件"}), 400
        
        if not file.filename.endswith('.zip'):
            return jsonify({"error": "只支持 ZIP 文件"}), 400
        
        zip_data = file.read()
        name = request.form.get('name')
        
        package = manager.import_package(user_id, zip_data, name)
        
        return jsonify({
            "package": {
                "id": package.id,
                "name": package.name
            }
        }), 201
        
    except Exception as e:
        logger.error(f"[PromptPackageAPI] 导入包失败: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== 注册蓝图 ====================

def init_app(app):
    """初始化 Flask 应用"""
    app.register_blueprint(prompt_package_api)
    logger.info("[PromptPackageAPI] 已注册 API 蓝图")
