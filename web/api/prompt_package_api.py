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


# ==================== 配置编辑 API (前端配置编辑器使用) ====================

# 配置路径定义
CONFIG_BASE_PATH = Path("prompt_packages")
COMPONENTS_PATHS = [
    CONFIG_BASE_PATH / "default" / "market_driven" / "components",
    CONFIG_BASE_PATH / "_base" / "system_components"
]
STEPS_PATH = CONFIG_BASE_PATH / "default" / "market_driven" / "steps"
BACKUP_PATH = Path("config/backups")


def _get_all_components():
    """获取所有可用组件（支持子目录递归）"""
    components = []
    for components_path in COMPONENTS_PATHS:
        if not components_path.exists():
            continue
        # 使用 rglob 递归查找所有子目录中的 JSON 文件
        for json_file in components_path.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    component_id = data.get('component_id') or json_file.stem
                    components.append({
                        "id": component_id,
                        "name": data.get('name', component_id),
                        "description": data.get('description', ''),
                        "version": data.get('version', '1.0.0'),
                        "editable": data.get('editable', True),
                        "source": str(json_file.relative_to(CONFIG_BASE_PATH)),
                        "file_path": str(json_file)
                    })
            except Exception as e:
                logger.warning(f"[PromptConfigAPI] 读取组件失败 {json_file}: {e}")
    return components


def _find_component_file(component_id):
    """查找组件文件路径（支持子目录递归）"""
    for components_path in COMPONENTS_PATHS:
        if not components_path.exists():
            continue
        # 使用 rglob 递归查找所有子目录中的 JSON 文件
        for json_file in components_path.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_component_id = data.get('component_id') or json_file.stem
                    if file_component_id == component_id:
                        return json_file, data
            except Exception:
                continue
    return None, None


def _backup_file(file_path):
    """备份配置文件"""
    try:
        if not BACKUP_PATH.exists():
            BACKUP_PATH.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}.json"
        backup_file = BACKUP_PATH / backup_filename
        
        import shutil
        shutil.copy2(file_path, backup_file)
        logger.info(f"[PromptConfigAPI] 已备份配置: {backup_file}")
        return str(backup_file)
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 备份失败: {e}")
        return None


def _get_all_steps():
    """获取所有步骤配置"""
    steps = []
    if not STEPS_PATH.exists():
        return steps
    
    for json_file in sorted(STEPS_PATH.glob("step_*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                steps.append({
                    "step_id": data.get('step_id', json_file.stem),
                    "step_name": data.get('step_name', ''),
                    "step_order": data.get('step_order', 0),
                    "enabled": data.get('enabled', True),
                    "description": data.get('description', ''),
                    "file_path": str(json_file)
                })
        except Exception as e:
            logger.warning(f"[PromptConfigAPI] 读取步骤失败 {json_file}: {e}")
    
    # 按 step_order 排序
    steps.sort(key=lambda x: x['step_order'])
    return steps


@prompt_package_api.route('/prompt-config/components', methods=['GET'])
@require_login
def list_components():
    """
    列出所有可用组件
    
    Returns:
        {
            "components": [
                {
                    "id": "组件ID",
                    "name": "组件名称",
                    "description": "描述",
                    "version": "版本",
                    "editable": true/false,
                    "source": "文件路径"
                }
            ]
        }
    """
    try:
        components = _get_all_components()
        return jsonify({"components": components})
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 列出组件失败: {e}")
        return jsonify({"error": f"获取组件列表失败: {str(e)}"}), 500


@prompt_package_api.route('/prompt-config/component/<component_id>', methods=['GET'])
@require_login
def get_component(component_id):
    """
    获取组件详情
    
    Args:
        component_id: 组件ID
    
    Returns:
        {
            "component": {组件完整数据}
        }
    """
    try:
        file_path, data = _find_component_file(component_id)
        if not file_path:
            return jsonify({"error": f"组件 '{component_id}' 不存在"}), 404
        
        return jsonify({"component": data})
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 获取组件失败: {e}")
        return jsonify({"error": f"获取组件失败: {str(e)}"}), 500


@prompt_package_api.route('/prompt-config/component/<component_id>', methods=['POST'])
@require_login
def update_component(component_id):
    """
    更新组件配置
    
    Request Body:
        完整的组件JSON数据
    
    Returns:
        {
            "message": "更新成功",
            "backup_path": "备份文件路径"
        }
    """
    try:
        file_path, existing_data = _find_component_file(component_id)
        if not file_path:
            return jsonify({"error": f"组件 '{component_id}' 不存在"}), 404
        
        # 检查组件是否可编辑
        if existing_data.get('editable') is False:
            return jsonify({"error": "该组件为系统组件，不允许编辑"}), 403
        
        # 获取请求数据
        data = request.get_json()
        if data is None:
            return jsonify({"error": "请求体必须是有效的JSON格式"}), 400
        
        # 验证JSON数据
        if not isinstance(data, dict):
            return jsonify({"error": "组件数据必须是JSON对象"}), 400
        
        # 确保组件ID一致
        if 'component_id' in data and data['component_id'] != component_id:
            return jsonify({"error": "组件ID不匹配"}), 400
        
        # 备份原始配置
        backup_path = _backup_file(file_path)
        if not backup_path:
            return jsonify({"error": "备份原始配置失败，取消更新"}), 500
        
        # 写入新配置
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "message": "组件更新成功",
            "backup_path": backup_path
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"[PromptConfigAPI] JSON解析失败: {e}")
        return jsonify({"error": f"JSON格式错误: {str(e)}"}), 400
    except PermissionError as e:
        logger.error(f"[PromptConfigAPI] 权限错误: {e}")
        return jsonify({"error": f"无权限写入文件: {str(e)}"}), 403
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 更新组件失败: {e}")
        return jsonify({"error": f"更新组件失败: {str(e)}"}), 500


@prompt_package_api.route('/prompt-config/steps', methods=['GET'])
@require_login
def list_steps():
    """
    列出所有步骤配置
    
    Returns:
        {
            "steps": [
                {
                    "step_id": "步骤ID",
                    "step_name": "步骤名称",
                    "step_order": 1,
                    "enabled": true,
                    "description": "描述"
                }
            ]
        }
    """
    try:
        steps = _get_all_steps()
        return jsonify({"steps": steps})
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 列出步骤失败: {e}")
        return jsonify({"error": f"获取步骤列表失败: {str(e)}"}), 500


@prompt_package_api.route('/prompt-config/reload', methods=['POST'])
@require_login
def reload_config():
    """
    重新加载配置
    
    这会清除缓存并重新加载所有配置
    
    Returns:
        {
            "message": "配置已重新加载",
            "stats": {
                "components_count": 10,
                "steps_count": 6
            }
        }
    """
    try:
        # 重新加载组件和步骤
        components = _get_all_components()
        steps = _get_all_steps()
        
        # 尝试重新加载 PromptPackageManager 缓存
        try:
            manager = get_manager()
            # 如果管理器有缓存刷新方法，调用它
            if hasattr(manager, 'refresh_cache'):
                manager.refresh_cache()
        except Exception as e:
            logger.warning(f"[PromptConfigAPI] 刷新管理器缓存失败: {e}")
        
        return jsonify({
            "message": "配置已重新加载",
            "stats": {
                "components_count": len(components),
                "steps_count": len(steps)
            }
        })
        
    except Exception as e:
        logger.error(f"[PromptConfigAPI] 重新加载配置失败: {e}")
        return jsonify({"error": f"重新加载配置失败: {str(e)}"}), 500


# ==================== 注册蓝图 ====================

def init_app(app):
    """初始化 Flask 应用"""
    app.register_blueprint(prompt_package_api)
    logger.info("[PromptPackageAPI] 已注册 API 蓝图")
