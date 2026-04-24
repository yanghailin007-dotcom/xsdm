"""
对话式设定生成 API
提供零提示词干预的自由对话 + 一键生成结构化设定的能力
"""
import json
import os
import time
from flask import Blueprint, request, jsonify, Response, session, stream_with_context

from web.auth import login_required
from web.web_config import logger, BASE_DIR

conversation_api = Blueprint('conversation_api', __name__, url_prefix='/api/conversation')

# 已知只支持 temperature=1.0 的模型
_FIXED_TEMP_MODELS = {
    "kimi-k2.5", "kimi-k2", "kimi-k2-5",
    "deepseek-reasoner", "deepseek-r1",
}

# 模型 → provider 映射（选择第一个可用的 endpoint）
_MODEL_PROVIDER_MAP = {
    "deepseek-v4-flash": "deepseek",
    "deepseek-v4-pro":   "deepseek",
    "deepseek-reasoner": "deepseek",
    "kimi-k2.5":         "kimi",
    "gemini-3-flash":    "gemini",
    "gemini-3-pro":      "gemini",
    "doubao-seed-2-0-pro": "doubao",
}


def _load_config():
    """加载系统 config"""
    try:
        import importlib.util
        config_path = BASE_DIR / "config" / "config.py"
        spec = importlib.util.spec_from_file_location("config_module", config_path)
        if spec and spec.loader:
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            return getattr(config_module, "CONFIG", {})
    except Exception as e:
        logger.warning(f"[Conversation] 加载配置失败: {e}")
    return {}


def _resolve_endpoint(model_name: str):
    """
    根据前端传来的 model 名称，解析出实际可用的 endpoint 配置。
    返回: {"api_key": str, "api_url": str, "provider": str} 或 None
    """
    if not model_name:
        return None

    CONFIG = _load_config()
    api_endpoints = CONFIG.get("api_endpoints", {})

    # 1. 尝试通过映射表定位 provider
    provider = _MODEL_PROVIDER_MAP.get(model_name)

    # 2. 如果没有映射，尝试直接在 endpoint model 字段匹配
    if not provider:
        for prov, endpoints in api_endpoints.items():
            for ep in endpoints:
                if ep.get("model") == model_name and ep.get("enabled", True):
                    provider = prov
                    break
            if provider:
                break

    # 3. 获取该 provider 下第一个启用的 endpoint
    if provider:
        endpoints = api_endpoints.get(provider, [])
        for ep in endpoints:
            if ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": provider,
                }

    # 4. 兜底：遍历所有 provider 找匹配 model 的 endpoint
    for prov, endpoints in api_endpoints.items():
        for ep in endpoints:
            if ep.get("model") == model_name and ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": prov,
                }

    return None


def _normalize_temp(model_name: str, temp):
    """根据模型特性调整 temperature"""
    if not model_name:
        return temp
    m = model_name.lower()
    for fixed in _FIXED_TEMP_MODELS:
        if fixed in m:
            return 1.0
    return temp


# ───────────────────────────────
#  1. 自由对话（流式透传）
# ───────────────────────────────

@conversation_api.route('/chat', methods=['POST'])
@login_required
def chat_stream():
    """
    对话式自由聊天 —— 零提示词干预，完全透传用户消息。
    返回 SSE 流式响应。
    """
    try:
        data = request.json or {}
        messages = data.get("messages", [])
        model = data.get("model", "deepseek-v4-flash")
        temperature = data.get("temperature", 0.7)

        if not messages:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400

        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        temperature = _normalize_temp(model, temperature)

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        def generate():
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if temperature is not None:
                payload["temperature"] = temperature

            try:
                resp = requests.post(
                    endpoint["api_url"],
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=300
                )
            except Exception as e:
                yield f"data: {json.dumps({'error': f'请求异常: {str(e)}'})}\n\n"
                return

            if not resp.ok:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err = resp.text or f"HTTP {resp.status_code}"
                yield f"data: {json.dumps({'error': err})}\n\n"
                return

            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_text = line.decode('utf-8')
                    if not line_text.startswith('data: '):
                        continue

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
                logger.error(f"[Conversation] 流式异常: {e}")
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
        logger.error(f"[Conversation] /chat 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  2. 生成设定（非流式 JSON）
# ───────────────────────────────

_GENERATE_SETTINGS_PROMPT = """根据以上对话内容，生成一份完整的小说项目设定文件。要求：

1. 输出格式必须是 **JSON**，不要包含任何 markdown 代码块标记或其他说明文字
2. JSON 结构如下：
{
  "title": "书名",
  "synopsis": "一句话简介（20-50字）",
  "description": "详细简介（200-500字）",
  "genre": "题材/类型",
  "tags": ["标签1", "标签2", "标签3"],
  "worldview": {
    "background": "世界观背景",
    "rules": "核心规则/金手指机制",
    "era": "时代/背景设定"
  },
  "characters": [
    {
      "name": "角色名",
      "role": "主角/反派/女主等",
      "personality": "性格特征",
      "background": "角色背景",
      "goal": "核心目标"
    }
  ],
  "plot_outline": {
    "opening": "开局设计",
    "rising": "发展脉络",
    "climax": "高潮设计",
    "ending": "结局走向"
  },
  "key_hooks": ["爽点1", "爽点2", "爽点3"],
  "target_words": 400000,
  "chapters_estimate": 200
}

3. 内容要充实、有创意，不能敷衍
4. 直接返回 JSON 字符串，不要加 ```json 这样的代码块"""


@conversation_api.route('/generate-settings', methods=['POST'])
@login_required
def generate_settings():
    """
    根据对话历史，追加设定生成指令，让 AI 输出结构化 JSON。
    非流式，等待完整返回后解析 JSON。
    """
    try:
        data = request.json or {}
        messages = data.get("messages", [])
        model = data.get("model", "deepseek-v4-pro")
        temperature = data.get("temperature", 0.5)

        if not messages:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400

        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        temperature = _normalize_temp(model, temperature)

        # 复制消息并追加设定生成指令
        gen_messages = messages.copy()
        gen_messages.append({
            "role": "user",
            "content": _GENERATE_SETTINGS_PROMPT
        })

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        payload = {
            "model": model,
            "messages": gen_messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        resp = requests.post(
            endpoint["api_url"],
            headers=headers,
            json=payload,
            timeout=300
        )

        if not resp.ok:
            try:
                err = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err = resp.text or f"HTTP {resp.status_code}"
            return jsonify({"success": False, "error": err}), 502

        result = resp.json()
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""

        # 尝试解析 JSON
        settings = _extract_json(raw_content)
        if not settings:
            return jsonify({
                "success": False,
                "error": "AI 返回内容无法解析为有效 JSON",
                "raw": raw_content[:2000]
            }), 422

        return jsonify({
            "success": True,
            "settings": settings,
            "model": model,
        })

    except Exception as e:
        logger.error(f"[Conversation] /generate-settings 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _extract_json(text: str):
    """从文本中提取 JSON 对象，支持代码块和普通文本"""
    if not text:
        return None

    text = text.strip()

    # 1. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 代码块
    import re
    block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text, re.IGNORECASE)
    if block_match:
        try:
            return json.loads(block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. 查找最外层 { ... }
    brace_match = re.search(r'(\{[\s\S]*\})', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    return None
