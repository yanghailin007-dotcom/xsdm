"""
NovelCraft API 路由
提供模型列表、对话、自定义模型管理、项目文件同步等功能
"""
import json
import os
import re
import time
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, session, stream_with_context

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.managers.novelcraft_model_manager import novelcraft_model_manager
from web.utils.path_utils import get_current_username, get_user_novel_dir, _safe_filename

novelcraft_api = Blueprint('novelcraft_api', __name__, url_prefix='/api/novelcraft')

# 已知只支持 temperature=1.0 的模型（避免先报错再重试）
_FIXED_TEMP_MODELS = {
    "kimi-k2.5", "kimi-k2", "kimi-k2-5",
    "deepseek-reasoner", "deepseek-r1",
}

def _normalize_temp(model_name: str, temp):
    """根据模型特性调整 temperature"""
    if not model_name:
        return temp
    m = model_name.lower()
    for fixed in _FIXED_TEMP_MODELS:
        if fixed in m:
            return 1.0
    return temp


def _get_project_dir(username: str, project_name: str, create: bool = False) -> Path:
    """获取 NovelCraft 项目在服务器上的存储目录"""
    safe_name = _safe_filename(project_name)
    user_dir = get_user_novel_dir(username, create=create)
    project_dir = user_dir / f"NovelCraft_{safe_name}"
    if create and not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def _get_system_models():
    """获取系统预设模型列表"""
    try:
        import importlib.util
        config_path = BASE_DIR / "config" / "config.py"
        spec = importlib.util.spec_from_file_location("config_module", config_path)
        if spec and spec.loader:
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            CONFIG = config_module.CONFIG
        else:
            CONFIG = {"api_endpoints": {}}
    except Exception as e:
        logger.warning(f"[NovelCraft] 加载系统配置失败: {e}")
        CONFIG = {"api_endpoints": {}}
    
    models = []
    api_endpoints = CONFIG.get("api_endpoints", {})
    
    # 从 api_endpoints 提取可用模型
    for provider, endpoints in api_endpoints.items():
        for ep in endpoints:
            if not ep.get("enabled", True):
                continue
            model_name = ep.get("model", "unknown")
            models.append({
                "id": f"system:{provider}:{ep.get('name', 'default')}",
                "name": f"{provider.upper()} - {model_name}",
                "provider": provider,
                "model": model_name,
                "api_url": ep.get("api_url", ""),
                "is_system": True,
                "endpoint_name": ep.get("name", "default")
            })
    
    return models


@novelcraft_api.route('/models', methods=['GET'])
@login_required
def list_models():
    """获取可用模型列表（系统预设 + 用户自定义）"""
    try:
        user_id = session.get('user_id')
        system_models = _get_system_models()
        user_models = novelcraft_model_manager.list_models(user_id)
        
        # 标记用户自定义模型
        for m in user_models:
            m["is_custom"] = True
        
        return jsonify({
            "success": True,
            "data": {
                "system": system_models,
                "custom": user_models
            }
        })
    except Exception as e:
        logger.error(f"[NovelCraft] 获取模型列表失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/models', methods=['POST'])
@login_required
def add_custom_model():
    """添加用户自定义模型"""
    try:
        user_id = session.get('user_id')
        data = request.json or {}
        
        model = {
            "id": data.get("id", "").strip(),
            "name": data.get("name", "").strip(),
            "api_url": data.get("api_url", "").strip(),
            "api_key": data.get("api_key", "").strip(),
            "model": data.get("model", "").strip(),
            "base_url": data.get("base_url", "").strip(),
        }
        
        if not model["id"]:
            model["id"] = f"custom_{int(time.time() * 1000)}"
        
        # 如果提供了 base_url 但没有 api_url，自动补全
        if model["base_url"] and not model["api_url"]:
            model["api_url"] = model["base_url"].rstrip("/") + "/chat/completions"
        
        # 如果提供了 api_url 但没有 base_url，自动补全
        if model["api_url"] and not model["base_url"]:
            model["base_url"] = model["api_url"].replace("/chat/completions", "").rstrip("/")
        
        success, message = novelcraft_model_manager.add_model(user_id, model)
        if success:
            return jsonify({"success": True, "message": message, "id": model["id"]})
        return jsonify({"success": False, "error": message}), 400
    except Exception as e:
        logger.error(f"[NovelCraft] 添加自定义模型失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/models/<model_id>', methods=['DELETE'])
@login_required
def delete_custom_model(model_id):
    """删除用户自定义模型"""
    try:
        user_id = session.get('user_id')
        success, message = novelcraft_model_manager.delete_model(user_id, model_id)
        if success:
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "error": message}), 400
    except Exception as e:
        logger.error(f"[NovelCraft] 删除自定义模型失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/models/<model_id>', methods=['PUT'])
@login_required
def update_custom_model(model_id):
    """更新用户自定义模型"""
    try:
        user_id = session.get('user_id')
        data = request.json or {}
        
        updates = {}
        for key in ["name", "api_url", "api_key", "model", "base_url"]:
            if key in data:
                updates[key] = data[key].strip()
        
        # 同步 base_url 和 api_url
        if "api_url" in updates and "base_url" not in updates:
            updates["base_url"] = updates["api_url"].replace("/chat/completions", "").rstrip("/")
        if "base_url" in updates and "api_url" not in updates:
            updates["api_url"] = updates["base_url"].rstrip("/") + "/chat/completions"
        
        success, message = novelcraft_model_manager.update_model(user_id, model_id, updates)
        if success:
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "error": message}), 400
    except Exception as e:
        logger.error(f"[NovelCraft] 更新自定义模型失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _resolve_model_config(user_id, model_id: str):
    """解析模型配置"""
    if model_id.startswith("system:"):
        parts = model_id.split(":", 2)
        if len(parts) >= 3:
            provider = parts[1]
            endpoint_name = parts[2]
            
            try:
                import importlib.util
                config_path = BASE_DIR / "config" / "config.py"
                spec = importlib.util.spec_from_file_location("config_module", config_path)
                if spec and spec.loader:
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    CONFIG = config_module.CONFIG
                else:
                    CONFIG = {"api_endpoints": {}}
            except Exception:
                CONFIG = {"api_endpoints": {}}
            
            endpoints = CONFIG.get("api_endpoints", {}).get(provider, [])
            for ep in endpoints:
                if ep.get("name") == endpoint_name and ep.get("enabled", True):
                    return {
                        "api_key": ep.get("api_key", ""),
                        "api_url": ep.get("api_url", ""),
                        "model": ep.get("model", "unknown"),
                        "provider": provider,
                    }
        return None
    else:
        # 用户自定义模型
        model = novelcraft_model_manager.get_model(user_id, model_id)
        if model:
            return {
                "api_key": model.get("api_key", ""),
                "api_url": model.get("api_url", ""),
                "model": model.get("model", "unknown"),
                "provider": "custom",
            }
        return None


@novelcraft_api.route('/chat', methods=['POST'])
@login_required
def chat():
    """标准对话 API（非流式）"""
    try:
        user_id = session.get('user_id')
        data = request.json or {}
        
        messages = data.get("messages", [])
        model_id = data.get("model_id", "")
        temperature = data.get("temperature", 0.7)
        
        if not messages:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400
        
        config = _resolve_model_config(user_id, model_id)
        if not config:
            return jsonify({"success": False, "error": "模型配置不存在"}), 404
        
        if not config.get("api_key"):
            return jsonify({"success": False, "error": "该模型未配置 API Key"}), 400
        
        # 针对特定模型强制 temperature=1.0
        temperature = _normalize_temp(config.get("model"), temperature)
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        
        def _make_request(temp):
            p = {"model": config["model"], "messages": messages}
            if temp is not None:
                p["temperature"] = temp
            return requests.post(config["api_url"], headers=headers, json=p, timeout=300)
        
        resp = _make_request(temperature)
        
        # fallback: 某些模型只支持 temperature=1.0
        if not resp.ok:
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", str(err_data))
            except Exception:
                err_msg = resp.text or f"HTTP {resp.status_code}"
            
            if "temperature" in err_msg.lower() and temperature != 1.0:
                logger.info(f"[NovelCraft] temperature 受限，自动 fallback 到 1.0 重试: {config['model']}")
                resp = _make_request(1.0)
                if not resp.ok:
                    try:
                        err_data = resp.json()
                        err_msg = err_data.get("error", {}).get("message", str(err_data))
                    except Exception:
                        err_msg = resp.text or f"HTTP {resp.status_code}"
                    return jsonify({"success": False, "error": err_msg}), 502
            else:
                return jsonify({"success": False, "error": err_msg}), 502
        
        result = resp.json()
        choices = result.get("choices") or [{}]
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        return jsonify({
            "success": True,
            "data": {
                "content": content,
                "model": config["model"],
            }
        })
    except Exception as e:
        logger.error(f"[NovelCraft] 对话 API 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """流式对话 API（SSE）"""
    try:
        user_id = session.get('user_id')
        data = request.json or {}
        
        messages = data.get("messages", [])
        model_id = data.get("model_id", "")
        temperature = data.get("temperature", 0.7)
        
        if not messages:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400
        
        config = _resolve_model_config(user_id, model_id)
        if not config:
            return jsonify({"success": False, "error": "模型配置不存在"}), 404
        
        if not config.get("api_key"):
            return jsonify({"success": False, "error": "该模型未配置 API Key"}), 400
        
        # 针对特定模型强制 temperature=1.0
        temperature = _normalize_temp(config.get("model"), temperature)
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }
        
        def generate():
            def _make_request(temp):
                p = {"model": config["model"], "messages": messages, "stream": True}
                if temp is not None:
                    p["temperature"] = temp
                return requests.post(config["api_url"], headers=headers, json=p, stream=True, timeout=300)
            
            resp = _make_request(temperature)
            
            # fallback: 某些模型只支持 temperature=1.0
            if not resp.ok:
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("error", {}).get("message", str(err_data))
                except Exception:
                    err_msg = resp.text or f"HTTP {resp.status_code}"
                
                if "temperature" in err_msg.lower() and temperature != 1.0:
                    logger.info(f"[NovelCraft] 流式 temperature 受限，自动 fallback 到 1.0 重试: {config['model']}")
                    resp = _make_request(1.0)
                    if not resp.ok:
                        try:
                            err_data = resp.json()
                            err_msg = err_data.get("error", {}).get("message", str(err_data))
                        except Exception:
                            err_msg = resp.text or f"HTTP {resp.status_code}"
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        return
                else:
                    yield f"data: {json.dumps({'error': err_msg})}\n\n"
                    return
            
            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_content = line_text[6:]
                        if data_content == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data_content)
                            choices = chunk.get("choices") or [{}]
                            delta = choices[0].get("delta", {}) if choices else {}
                            content_piece = delta.get("content", "")
                            if content_piece:
                                yield f"data: {json.dumps({'content': content_piece})}\n\n"
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
            except Exception as e:
                logger.error(f"[NovelCraft] 流式对话异常: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )
    except Exception as e:
        logger.error(f"[NovelCraft] 流式对话 API 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _extract_synopsis(core_setting_text: str) -> str:
    """从 core-setting.md 中智能提取简介"""
    if not core_setting_text:
        return ''
    
    import re
    
    # 策略1：匹配 ## 书籍简介 / ## 简介 / ### 简介 等标题后的内容
    patterns = [
        r'##\s*书籍简介[\s\S]*?\n\n(.*?)(?=\n##|\n###|\Z)',
        r'##\s*简介[\s\S]*?\n\n(.*?)(?=\n##|\n###|\Z)',
        r'###\s*书籍简介[\s\S]*?\n\n(.*?)(?=\n##|\n###|\Z)',
        r'###\s*简介[\s\S]*?\n\n(.*?)(?=\n##|\n###|\Z)',
        r'\*\*书籍简介\*\*[\s\S]*?\n(.*?)(?=\n##|\n###|\Z)',
    ]
    for pattern in patterns:
        match = re.search(pattern, core_setting_text, re.MULTILINE)
        if match:
            synopsis = match.group(1).strip()
            # 去掉可能的引用符号 >
            synopsis = re.sub(r'^>\s*', '', synopsis, flags=re.MULTILINE).strip()
            if len(synopsis) > 10:
                # 限制长度
                if len(synopsis) > 300:
                    synopsis = synopsis[:297] + '...'
                return synopsis
    
    # 策略2：匹配 "书名：《xxx》" 后面紧跟的简短描述
    book_match = re.search(r'书名[：:]\s*《[^》]+》[\s\S]*?\n([^\n#]{10,150})', core_setting_text)
    if book_match:
        return book_match.group(1).strip()
    
    # 策略3：匹配 "核心爽点/看点" 后的内容
    hook_match = re.search(r'核心爽点[：/]([^\n]{5,150})', core_setting_text)
    if hook_match:
        return hook_match.group(1).strip()
    
    # 兜底：取前200字符，但跳过 YAML front matter 和 markdown 标记
    lines = core_setting_text.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('---') or stripped.startswith('#') or stripped.startswith('>'):
            continue
        if stripped:
            clean_lines.append(stripped)
    fallback = ' '.join(clean_lines)[:200]
    return fallback


# ==================== 项目文件同步 API ====================

@novelcraft_api.route('/sync', methods=['POST'])
@login_required
def sync_project():
    """
    同步 NovelCraft 项目到后端文件系统
    会在 小说项目/{username}/NovelCraft_{project_name}/ 下创建真实文件
    """
    try:
        data = request.json or {}
        project = data.get("project")
        if not project or not project.get("name"):
            return jsonify({"success": False, "error": "缺少项目数据"}), 400
        
        username = get_current_username()
        if not username or username == 'anonymous':
            return jsonify({"success": False, "error": "未登录，无法同步项目"}), 401
        project_name = project["name"]
        project_dir = _get_project_dir(username, project_name, create=True)
        
        # 保存 markdown 文件
        files = project.get("files", {})
        for filename, file_data in files.items():
            filepath = project_dir / filename
            content = file_data.get("content", "") if isinstance(file_data, dict) else str(file_data)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 保存完整项目元数据
        meta_path = project_dir / "novelcraft.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(project, f, ensure_ascii=False, indent=2)
        
        # 创建系统可识别的 项目信息.json，让它出现在作品列表中
        info_path = project_dir / "项目信息.json"
        project_info = {}
        if info_path.exists():
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
            except Exception:
                pass
        
        # 智能提取简介
        core_setting = files.get('core-setting.md', {}).get('content', '') if isinstance(files.get('core-setting.md'), dict) else ''
        synopsis = _extract_synopsis(core_setting)
        
        # 更新项目信息
        project_info.update({
            "novel_title": project_name,
            "title": project_name,
            "novel_synopsis": synopsis,
            "total_chapters": len(project.get("chapters", {})),
            "completed_chapters": len(project.get("chapters", {})),
            "word_count": sum(
                len(f.get("content", "")) for f in files.values() if isinstance(f, dict)
            ) + sum(
                len(c.get("content", "")) for c in project.get("chapters", {}).values() if isinstance(c, dict)
            ),
            "source": "novelcraft",
            "updated_at": time.time(),
        })
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[NovelCraft] 项目已同步到服务器: {project_dir}")
        return jsonify({
            "success": True,
            "message": "项目已同步到服务器",
            "path": str(project_dir)
        })
    except Exception as e:
        logger.error(f"[NovelCraft] 同步项目失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/projects', methods=['GET'])
@login_required
def list_server_projects():
    """列出服务器上已同步的 NovelCraft 项目"""
    try:
        username = get_current_username()
        user_dir = get_user_novel_dir(username, create=False)
        projects = []
        
        if user_dir.exists():
            for item in user_dir.iterdir():
                if item.is_dir() and item.name.startswith("NovelCraft_"):
                    meta_path = item / "novelcraft.json"
                    project_data = None
                    if meta_path.exists():
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                        except Exception:
                            pass
                    
                    # 从实际文件读取最新内容，覆盖 novelcraft.json 中的缓存
                    if project_data:
                        files = project_data.get("files", {})
                        for filename in ["core-setting.md", "rough-outline.md", "detailed-outline.md"]:
                            filepath = item / filename
                            if filepath.exists():
                                try:
                                    with open(filepath, 'r', encoding='utf-8') as f:
                                        actual_content = f.read()
                                    if filename in files:
                                        if isinstance(files[filename], dict):
                                            files[filename]["content"] = actual_content
                                        else:
                                            files[filename] = {"content": actual_content, "updatedAt": int(time.time() * 1000)}
                                    else:
                                        files[filename] = {"content": actual_content, "updatedAt": int(time.time() * 1000)}
                                except Exception:
                                    pass
                        project_data["files"] = files
                    
                    projects.append({
                        "name": item.name.replace("NovelCraft_", ""),
                        "path": str(item),
                        "has_meta": meta_path.exists(),
                        "project": project_data,
                    })
        
        return jsonify({"success": True, "data": projects})
    except Exception as e:
        logger.error(f"[NovelCraft] 列出项目失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/publish-info', methods=['POST'])
@login_required
def generate_publish_info():
    """
    调用 AI 从 core-setting.md 中提取发布信息（简介、标签、分类等）
    结果会保存到项目目录的 项目信息.json 中，供番茄上传直接使用
    """
    try:
        data = request.json or {}
        project_name = data.get("project_name", "").strip()
        if not project_name:
            return jsonify({"success": False, "error": "缺少项目名称"}), 400
        
        username = get_current_username()
        project_dir = _get_project_dir(username, project_name, create=False)
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        # 读取 core-setting.md
        core_setting_path = project_dir / "core-setting.md"
        core_setting = ""
        if core_setting_path.exists():
            with open(core_setting_path, 'r', encoding='utf-8') as f:
                core_setting = f.read()
        
        if not core_setting.strip():
            return jsonify({"success": False, "error": "请先完成核心设定"}), 400
        
        # 选择一个便宜的系统模型（优先 gemini）
        system_models = _get_system_models()
        preferred = None
        for m in system_models:
            if "gemini" in m["provider"].lower() or "flash" in m["model"].lower():
                preferred = m["id"]
                break
        if not preferred and system_models:
            preferred = system_models[0]["id"]
        
        if not preferred:
            return jsonify({"success": False, "error": "没有可用的 AI 模型"}), 500
        
        config = _resolve_model_config(session.get("user_id"), preferred)
        if not config or not config.get("api_key"):
            return jsonify({"success": False, "error": "模型配置不可用"}), 500
        
        prompt = f"""你是一位资深网文编辑，擅长从小说核心设定中提取作品信息用于平台发布。

请仔细阅读以下「核心设定」文档，提取并生成以下信息：
1. 书名（如果文档中有多个候选书名，选最抓眼球、最适合番茄小说平台的一个）
2. 简介（200-300字，突出核心爽点，适合作为平台作品简介）
3. 分类（番茄小说的主分类，如：都市、玄幻、仙侠、科幻、历史、悬疑、游戏、体育、轻小说等）
4. 标签（JSON格式，包含：主题标签、角色标签、情节标签、目标读者）

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "title": "确定的书名",
  "synopsis": "作品简介",
  "category": "主分类",
  "tags": {{
    "main_category": "主分类",
    "themes": ["主题标签1", "主题标签2"],
    "roles": ["角色标签1", "角色标签2"],
    "plots": ["情节标签1", "情节标签2"],
    "target_audience": ["目标读者1", "目标读者2"]
  }}
}}

---

核心设定文档：
{core_setting}
"""
        
        import requests
        resp = requests.post(
            config["api_url"],
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config['api_key']}"
            },
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": _normalize_temp(config.get("model"), 0.7),
            },
            timeout=120
        )
        
        if not resp.ok:
            return jsonify({"success": False, "error": f"AI 请求失败: {resp.status_code}"}), 502
        
        result = resp.json()
        ai_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 清理可能的 markdown 代码块
        if ai_content.startswith("```json"):
            ai_content = ai_content[7:]
        if ai_content.startswith("```"):
            ai_content = ai_content[3:]
        if ai_content.endswith("```"):
            ai_content = ai_content[:-3]
        ai_content = ai_content.strip()
        
        try:
            publish_data = json.loads(ai_content)
        except json.JSONDecodeError as e:
            logger.error(f"[NovelCraft] AI 返回的 JSON 解析失败: {e}\n内容: {ai_content[:500]}")
            return jsonify({"success": False, "error": "AI 返回格式不正确，请重试"}), 500
        
        # 保存到项目信息.json
        info_path = project_dir / "项目信息.json"
        project_info = {}
        if info_path.exists():
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
            except Exception:
                pass
        
        # 计算字数
        word_count = 0
        for filename in ["core-setting.md", "rough-outline.md", "detailed-outline.md"]:
            fp = project_dir / filename
            if fp.exists():
                word_count += len(fp.read_text(encoding='utf-8'))
        
        project_info.update({
            "novel_title": publish_data.get("title", project_name),
            "title": publish_data.get("title", project_name),
            "novel_synopsis": publish_data.get("synopsis", ""),
            "category": publish_data.get("category", ""),
            "fanqie_upload_data": {
                "title": publish_data.get("title", project_name),
                "synopsis": publish_data.get("synopsis", ""),
                "tags": publish_data.get("tags", {})
            },
            "total_chapters": 0,
            "completed_chapters": 0,
            "word_count": word_count,
            "source": "novelcraft",
            "updated_at": time.time(),
        })
        
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        # 同时保存 publish_info.json 方便前端读取
        publish_path = project_dir / "publish_info.json"
        with open(publish_path, 'w', encoding='utf-8') as f:
            json.dump(publish_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": publish_data,
            "message": "发布信息已生成并保存"
        })
    
    except Exception as e:
        logger.error(f"[NovelCraft] 生成发布信息失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@novelcraft_api.route('/load/<path:project_name>', methods=['GET'])
@login_required
def load_server_project(project_name):
    """从服务器加载 NovelCraft 项目"""
    try:
        username = get_current_username()
        project_dir = _get_project_dir(username, project_name, create=False)
        
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        meta_path = project_dir / "novelcraft.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    project = json.load(f)
                return jsonify({"success": True, "data": project})
            except Exception as e:
                return jsonify({"success": False, "error": f"读取项目失败: {e}"}), 500
        
        # 如果没有 novelcraft.json，尝试从 markdown 文件重建
        project = {
            "id": f"proj_{int(time.time() * 1000)}",
            "name": project_name,
            "createdAt": int(time.time() * 1000),
            "updatedAt": int(time.time() * 1000),
            "files": {},
            "chapters": {},
            "aiConfig": {},
            "prompts": {},
            "characters": [],
            "relations": [],
            "foreshadows": [],
            "timeline": [],
        }
        for filename in ["core-setting.md", "rough-outline.md", "detailed-outline.md"]:
            filepath = project_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    project["files"][filename] = {"content": f.read(), "updatedAt": int(time.time() * 1000)}
        
        return jsonify({"success": True, "data": project})
    except Exception as e:
        logger.error(f"[NovelCraft] 加载项目失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _extract_protagonist_name(core_setting: str) -> str:
    """从 core-setting.md 提取主角姓名"""
    import re
    patterns = [
        r'[\s*]*姓名[\s*]*[：:]\s*([^\n（(]+)',
        r'主角[\s*]*[：:]\s*([^\n（(]+)',
        r'- \*\*姓名\*\*：\s*([^\n（(]+)',
        r'\*\*姓名\*\*[：:]\s*([^\n（(]+)',
    ]
    for p in patterns:
        m = re.search(p, core_setting)
        if m:
            return m.group(1).strip()
    return "主角"


def _infer_genre_from_core_setting(core_setting: str) -> str:
    """从核心设定推断题材 genre"""
    text = core_setting.lower()
    if any(k in text for k in ["返利", "神豪", "签到", "百倍", "花钱", "返现", "万倍", "消费", "首富", "提现", "无限提现"]):
        return "god-tier-spending"
    if any(k in text for k in ["国运", "禁地", "扮演", "直播", "国战", "怪谈", "诡异"]):
        return "nation-live"
    if any(k in text for k in ["修仙", "修真", "境界", "灵根", "渡劫"]):
        return "cultivation"
    if any(k in text for k in ["重生", "穿越", "回到", "前世"]):
        return "rebirth"
    return "urban"


def _parse_detailed_outline_to_v2_chapters(detailed_outline: str, start_chapter: int, end_chapter: int, protagonist_name: str = "主角") -> list:
    """将 detailed-outline.md 解析为 V2 BatchChapterGenerator 需要的 tactical_plan 格式"""
    import re
    chapters = []
    lines = detailed_outline.split('\n')
    current = None
    current_mode = None

    for line in lines:
        trimmed = line.strip()
        m = re.match(r'^#{1,3}\s*第(\d+)章[\s:：]*(.+)$', trimmed)
        if m:
            if current:
                chapters.append(current)
            num = int(m.group(1))
            title = m.group(2).strip()
            current = {
                "chapter_number": num,
                "chapter_title": title,
                "title": title,
                "event": "",
                "emotion": "期待",
                "intensity": 7,
                "hook_content": "",
                "satisfaction_point": "",
                "face_slapping": "",
                "assigned_characters": {"core": [], "major": [], "minor": []},
                "beat_type": "普通章",
                "system_prompt_moment": "",
            }
            current_mode = None
            continue

        if not current:
            continue

        if re.match(r'^#{2,4}\s*本?章目的', trimmed):
            current_mode = 'purpose'; continue
        if re.match(r'^#{2,4}\s*关键情节', trimmed):
            current_mode = 'events'; continue
        if re.match(r'^#{2,4}\s*出场人物', trimmed):
            current_mode = 'characters'; continue
        if re.match(r'^#{2,4}\s*伏[^\n]*', trimmed):
            current_mode = 'foreshadows'; continue
        if re.match(r'^#{2,4}\s*章节钩子', trimmed):
            current_mode = 'hook'; continue

        if not current_mode or not trimmed:
            continue

        clean = re.sub(r'^[-*]\s*', '', trimmed)

        if current_mode == 'purpose':
            current["event"] += (current["event"] and " | " or "") + clean
            lower = clean.lower()
            if any(k in lower for k in ["打脸", "碾压", "碾压", "碾压"]):
                current["emotion"] = "爽"; current["intensity"] = 9; current["beat_type"] = "打脸章"
            elif any(k in lower for k in ["压抑", "羞辱", "困境", "绝境", "被嘲讽"]):
                current["emotion"] = "虐"; current["intensity"] = 4; current["beat_type"] = "铺垫章"
            elif any(k in lower for k in ["危机", "危险", "追杀", "暴露"]):
                current["emotion"] = "紧张"; current["intensity"] = 8; current["beat_type"] = "危机章"
            elif any(k in lower for k in ["收获", "升级", "突破", "获得"]):
                current["emotion"] = "满足"; current["intensity"] = 8; current["beat_type"] = "收获章"
            elif any(k in lower for k in ["爆发", "全力", "巅峰"]):
                current["emotion"] = "爽"; current["intensity"] = 10; current["beat_type"] = "爆发章"

        elif current_mode == 'events':
            current["event"] += (current["event"] and "；" or "") + clean
            if any(k in clean for k in ["打脸", "碾压", "碾压", "碾压", "碾压", "碾压", "碾压", "碾压"]):
                current["satisfaction_point"] = clean
                current["face_slapping"] = {"target": "", "method": clean, "shock_level": "高"}
            if any(k in clean for k in ["系统", "提示音", "返利", "奖励", "激活"]):
                current["system_prompt_moment"] = clean

        elif current_mode == 'characters':
            for name in re.split(r'[、,，；;]', clean):
                name = name.strip()
                if not name:
                    continue
                name = re.sub(r'[（(].*?[）)]', '', name).strip()
                if not name:
                    continue
                if name == protagonist_name or "主角" in name:
                    if name not in current["assigned_characters"]["core"]:
                        current["assigned_characters"]["core"].append(name)
                elif any(k in name for k in ["反派", "前女友", "富二代"]):
                    if name not in current["assigned_characters"]["major"]:
                        current["assigned_characters"]["major"].append(name)
                else:
                    if name not in current["assigned_characters"]["minor"]:
                        current["assigned_characters"]["minor"].append(name)

        elif current_mode == 'hook':
            current["hook_content"] += (current["hook_content"] and " " or "") + trimmed

    if current:
        chapters.append(current)

    return [c for c in chapters if start_chapter <= c["chapter_number"] <= end_chapter]


def _update_project_progress_v2(project_dir: Path, saved_chapters: list, generated_map: dict = None):
    """更新项目信息.json（兼容 V2 返回格式）"""
    import json
    info_path = project_dir / "项目信息.json"
    info = {}
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding='utf-8'))
        except Exception:
            pass
    info["completed_chapters"] = info.get("completed_chapters", 0) + len(saved_chapters)
    info["word_count"] = info.get("word_count", 0) + sum(c.get("word_count", 0) for c in saved_chapters)
    info["last_generated_at"] = time.time()
    if generated_map:
        if "generated_chapters" not in info:
            info["generated_chapters"] = {}
        info["generated_chapters"].update(generated_map)
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')


@novelcraft_api.route('/generate-chapters', methods=['POST'])
@login_required
def generate_chapters():
    """为 NovelCraft 项目生成章节正文（优先使用 V2 引擎）"""
    try:
        data = request.json or {}
        project_name = data.get("project_name")
        start_chapter = int(data.get("start_chapter", 1))
        end_chapter = int(data.get("end_chapter", 6))
        use_v2 = data.get("use_v2", True)

        if not project_name:
            return jsonify({"success": False, "error": "project_name 不能为空"}), 400

        username = get_current_username()
        if not username or username == 'anonymous':
            return jsonify({"success": False, "error": "未登录，无法生成章节"}), 401

        project_dir = _get_project_dir(username, project_name, create=False)
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404

        def _read_md(name):
            p = project_dir / name
            return p.read_text(encoding='utf-8') if p.exists() else ""

        core_setting = _read_md("core-setting.md")
        worldview = _read_md("worldview.md")
        characters = _read_md("characters.md")
        detailed_outline = _read_md("detailed-outline.md")

        if not detailed_outline.strip():
            return jsonify({"success": False, "error": "缺少细纲文件 detailed-outline.md，无法生成章节"}), 400

        # ========== V2 引擎 ==========
        if use_v2:
            try:
                from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
                from src.core.APIClient import APIClient
                from config.config import CONFIG
                from datetime import datetime

                api_client = APIClient(CONFIG)
                api_client.set_username(username)

                protagonist_name = _extract_protagonist_name(core_setting)
                genre = _infer_genre_from_core_setting(core_setting)
                v2_chapters = _parse_detailed_outline_to_v2_chapters(
                    detailed_outline, start_chapter, end_chapter, protagonist_name
                )

                if not v2_chapters:
                    return jsonify({"success": False, "error": f"未能从细纲中解析出第{start_chapter}-{end_chapter}章"}), 400

                novel_data = {
                    "title": project_name,
                    "genre": genre,
                    "plan": {
                        "synopsis": "",
                        "protagonist": {"name": protagonist_name},
                    },
                }
                import re
                synopsis_match = re.search(r'[\s*]*简介[\s*]*[：:]\s*(.+?)(?=\n##|\n#{1,2}\s|$)', core_setting, re.DOTALL)
                if not synopsis_match:
                    synopsis_match = re.search(r'[\s*]*一句话简介[\s*]*[：:]\s*(.+?)(?=\n)', core_setting)
                if synopsis_match:
                    novel_data["plan"]["synopsis"] = synopsis_match.group(1).strip()

                blueprint = {"chapters": v2_chapters}

                batch_gen = BatchChapterGenerator(
                    api_client=api_client,
                    project_path=str(project_dir)
                )

                logger.info(f"[NovelCraft] V2 生成 {project_name} 第{start_chapter}-{end_chapter}章 | 题材:{genre} | 主角:{protagonist_name}")

                results = batch_gen.generate_batch(
                    novel_title=project_name,
                    start_chapter=start_chapter,
                    end_chapter=end_chapter,
                    blueprint=blueprint,
                    tropes={},
                    novel_data=novel_data,
                    use_conversation=True
                )

                chapter_dir = project_dir / "chapters"
                chapter_dir.mkdir(exist_ok=True)
                saved = []
                generated_map = {}

                for ch in results.get("generated", []):
                    num = ch["chapter_number"]
                    title = ch.get("title", f"第{num}章")
                    content = ch.get("content", "")
                    word_count = ch.get("word_count", len(content))
                    quality_score = ch.get("quality_score", 8.0)

                    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                    filename = f"第{num:03d}章_{safe_title}.json"
                    filepath = chapter_dir / filename

                    chapter_json = {
                        "chapter_number": num,
                        "chapter_title": title,
                        "content": content,
                        "word_count": word_count,
                        "quality_assessment": {"overall_score": quality_score},
                        "quality_score": quality_score,
                        "generation_time": datetime.now().isoformat(),
                        "generation_mode": "v2",
                        "key_events": [],
                        "next_chapter_hook": "",
                        "connection_to_previous": "",
                        "plot_advancement": "",
                        "character_development": "",
                        "optimization_info": {},
                        "chapter_design": {},
                        "design_followed": True,
                        "base_settings_used": {},
                    }
                    filepath.write_text(json.dumps(chapter_json, ensure_ascii=False, indent=2), encoding='utf-8')
                    saved.append({
                        "chapter_number": num,
                        "title": title,
                        "word_count": word_count,
                        "quality_score": quality_score
                    })
                    generated_map[str(num)] = chapter_json

                _update_project_progress_v2(project_dir, saved, generated_map)

                avg_score = sum(c["quality_score"] for c in saved) / len(saved) if saved else 0
                return jsonify({
                    "success": True,
                    "data": {
                        "generation_mode": "v2",
                        "overall_score": avg_score,
                        "chapters": saved,
                        "project_dir": str(project_dir)
                    }
                })

            except Exception as v2_err:
                logger.warning(f"[NovelCraft] V2 引擎失败，回退旧引擎: {v2_err}", exc_info=True)

        # ========== 旧引擎 fallback ==========
        import re
        chapters = []
        pattern = re.compile(r'^#{1,2}\s*第(\d+)章[\s:：]*(.+?)$', re.MULTILINE)
        matches = pattern.findall(detailed_outline)
        for num_str, title in matches:
            num = int(num_str)
            if start_chapter <= num <= end_chapter:
                chapters.append({"number": num, "title": title.strip()})

        if not chapters:
            lines = [l for l in detailed_outline.split('\n')
                     if l.strip().startswith('# 第') or l.strip().startswith('## 第')]
            idx = 0
            for line in lines:
                m = re.match(r'^#{1,2}\s*第[\d一二三四五六七八九十百千]+章[\s:：]*(.+?)$', line.strip())
                if m:
                    idx += 1
                    if start_chapter <= idx <= end_chapter:
                        chapters.append({"number": idx, "title": m.group(1).strip()})

        if not chapters:
            return jsonify({"success": False, "error": "未能从细纲中解析出有效章节"}), 400

        from src.core.chapter_engine import ChapterContext, ChapterSpec, ChapterGenerationEngine, Callbacks
        from src.core.APIClient import APIClient
        from config.config import CONFIG

        api_client = APIClient(CONFIG)

        context = ChapterContext(
            novel_title=project_name,
            core_setting=core_setting,
            worldview=worldview,
            characters=characters,
            writing_style="番茄小说爽文风格，快节奏，打脸要狠，注重情绪调动"
        )

        chapter_dir = project_dir / "chapters"
        prev_summary = ""
        if chapter_dir.exists():
            existing = []
            for f in chapter_dir.glob("*.json"):
                m = re.search(r'第(\d+)章', f.name)
                if m:
                    existing.append(int(m.group(1)))
            if existing:
                last_num = max(existing)
                last_file = None
                for f in chapter_dir.glob("*.json"):
                    if f"第{last_num:03d}章" in f.name:
                        last_file = f
                        break
                if last_file:
                    try:
                        last_data = json.loads(last_file.read_text(encoding='utf-8'))
                        content = last_data.get("content", "")
                        prev_summary = content[-500:] if len(content) > 500 else content
                    except Exception:
                        pass
        context.previous_summary = prev_summary

        specs = []
        for ch in chapters:
            outline_snippet = _extract_chapter_outline(detailed_outline, ch["number"]) or ""
            specs.append(ChapterSpec(
                chapter_number=ch["number"],
                title=ch["title"],
                outline=outline_snippet,
                is_golden_chapter=(ch["number"] <= 3)
            ))

        engine = ChapterGenerationEngine(api_client, batch_size=6)

        saved = []
        generated_chapters_map = {}

        def on_chapter_done(ch):
            from datetime import datetime
            chapter_dir.mkdir(exist_ok=True)
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", ch.title)
            filename = f"第{ch.chapter_number:03d}章_{safe_title}.json"
            filepath = chapter_dir / filename
            chapter_json_data = {
                "chapter_number": ch.chapter_number,
                "chapter_title": ch.title,
                "content": ch.content,
                "word_count": ch.word_count,
                "quality_assessment": {"overall_score": ch.quality_score},
                "quality_score": ch.quality_score,
                "generation_time": datetime.now().isoformat(),
                "key_events": [],
                "next_chapter_hook": "",
                "connection_to_previous": "",
                "plot_advancement": "",
                "character_development": "",
                "previous_chapter_summary": context.previous_summary,
                "optimization_info": {},
                "chapter_design": {},
                "design_followed": True,
                "base_settings_used": {},
            }
            filepath.write_text(json.dumps(chapter_json_data, ensure_ascii=False, indent=2), encoding='utf-8')
            saved.append({
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "word_count": ch.word_count,
                "quality_score": ch.quality_score
            })
            generated_chapters_map[str(ch.chapter_number)] = chapter_json_data

        callbacks = Callbacks(on_chapter_done=on_chapter_done)
        result = engine.generate_batch(context, specs, callbacks=callbacks)
        _update_project_progress(project_dir, result, generated_chapters_map)

        return jsonify({
            "success": True,
            "data": {
                "overall_score": result.overall_score,
                "chapters": saved,
                "project_dir": str(project_dir)
            }
        })
    except Exception as e:
        logger.error(f"[NovelCraft] 生成章节失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _extract_chapter_outline(md: str, chapter_number: int) -> str:
    """从 detailed-outline.md 中提取指定章节的文本片段"""
    import re
    lines = md.split('\n')
    start = -1
    for i, line in enumerate(lines):
        m = re.match(r'^#{1,2}\s*第(\d+)章', line.strip())
        if m and int(m.group(1)) == chapter_number:
            start = i
            break
    if start == -1:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        m = re.match(r'^#{1,2}\s*第\d+章', lines[i].strip())
        if m:
            end = i
            break
    return '\n'.join(lines[start:end]).strip()


def _update_project_progress(project_dir: Path, result, generated_chapters_map=None):
    """更新项目信息.json 的进度统计与 generated_chapters"""
    import json
    info_path = project_dir / "项目信息.json"
    info = {}
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding='utf-8'))
        except Exception:
            pass
    info["completed_chapters"] = info.get("completed_chapters", 0) + len(result.chapters)
    info["word_count"] = info.get("word_count", 0) + sum(ch.word_count for ch in result.chapters)
    info["last_generated_at"] = time.time()
    if generated_chapters_map:
        if "generated_chapters" not in info:
            info["generated_chapters"] = {}
        info["generated_chapters"].update(generated_chapters_map)
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')

