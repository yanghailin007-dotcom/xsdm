"""
对话式设定生成 API
提供零提示词干预的自由对话 + 一键生成结构化设定的能力
"""
import json
import os
import time
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, session, stream_with_context

from web.auth import login_required
from web.web_config import logger, BASE_DIR
from web.models.point_model import point_model

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


def _deduct_by_estimate(endpoint: dict, actual_model: str, prompt_text: str, 
                         completion_text: str, purpose: str):
    """基于字符数估算Token并扣费（用于流式响应）"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return
        provider = endpoint.get('provider', 'unknown')
        # 粗略估算：1个中文字符 ≈ 1.5 tokens
        prompt_tokens = int(len(prompt_text) * 1.5)
        completion_tokens = int(len(completion_text) * 1.5)
        result = point_model.deduct_by_tokens(
            user_id=user_id,
            provider=provider,
            model_name=actual_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            purpose=purpose,
            source='conversation_api_stream',
            related_id=None
        )
        if result and result.get('success'):
            logger.info(f"[Conversation] Token估算计费成功: {provider}/{actual_model} | "
                      f"估算 输入:{prompt_tokens} 输出:{completion_tokens} | 扣除:{result.get('amount', 0)}点")
        elif result is None:
            logger.info(f"[Conversation] {provider}/{actual_model} 未配置token价格，跳过按token计费")
    except Exception as e:
        logger.error(f"[Conversation] Token估算计费失败: {e}")


def _deduct_by_usage(resp_json: dict, endpoint: dict, actual_model: str, purpose: str):
    """根据API响应中的usage信息进行Token扣费"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return
        provider = endpoint.get('provider', 'unknown')
        usage = resp_json.get('usage') if resp_json else None
        if usage:
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            result = point_model.deduct_by_tokens(
                user_id=user_id,
                provider=provider,
                model_name=actual_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                purpose=purpose,
                source='conversation_api',
                related_id=None
            )
            if result and result.get('success'):
                logger.info(f"[Conversation] Token计费成功: {provider}/{actual_model} | "
                          f"输入:{prompt_tokens} 输出:{completion_tokens} | 扣除:{result.get('amount', 0)}点")
            elif result is None:
                logger.info(f"[Conversation] {provider}/{actual_model} 未配置token价格，跳过按token计费")
        else:
            logger.debug(f"[Conversation] 响应中无usage信息，跳过token计费")
    except Exception as e:
        logger.error(f"[Conversation] Token计费失败: {e}")


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

    # 3. 获取该 provider 下第一个启用的 endpoint，使用配置中的实际 model 名
    if provider:
        endpoints = api_endpoints.get(provider, [])
        for ep in endpoints:
            if ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": provider,
                    "model":    ep.get("model", model_name),
                }

    # 4. 兜底：遍历所有 provider 找匹配 model 的 endpoint
    for prov, endpoints in api_endpoints.items():
        for ep in endpoints:
            if ep.get("model") == model_name and ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": prov,
                    "model":    ep.get("model", model_name),
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
            logger.warning(f"[Conversation] /chat 模型 '{model}' 无可用端点")
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        # 使用 endpoint 配置中实际可用的 model 名
        actual_model = endpoint.get("model", model)
        temperature = _normalize_temp(actual_model, temperature)
        logger.info(f"[Conversation] /chat 请求: provider={endpoint['provider']}, model={actual_model}, messages={len(messages)}")

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        # 提取 system prompt 和 user message，用于流式结束后估算计费
        system_prompt = ""
        user_message = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                user_message = content

        def generate():
            payload = {
                "model": actual_model,
                "messages": messages,
                "stream": True,
            }
            # DeepSeek 思考模式：添加 thinking 参数，并移除 temperature
            is_deepseek = "deepseek" in actual_model.lower()
            if is_deepseek:
                payload["thinking"] = {"type": "enabled"}
            elif temperature is not None:
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
                logger.error(f"[Conversation] /chat API 请求异常: {e}")
                yield f"data: {json.dumps({'error': f'请求异常: {str(e)}'})}\n\n"
                return

            if not resp.ok:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err = resp.text or f"HTTP {resp.status_code}"
                logger.error(f"[Conversation] /chat API 返回错误: {err}")
                yield f"data: {json.dumps({'error': err})}\n\n"
                return
            
            logger.info(f"[Conversation] /chat 流式响应开始: provider={endpoint['provider']}, model={actual_model}")

            full_content = ""
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
                        reasoning_piece = delta.get("reasoning_content", "")
                        if reasoning_piece:
                            yield f"data: {json.dumps({'reasoning': reasoning_piece})}\n\n"
                        if content_piece:
                            full_content += content_piece
                            yield f"data: {json.dumps({'content': content_piece})}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
                # 🔥 流式响应结束后进行Token估算计费
                prompt_text = user_message + (system_prompt or "")
                _deduct_by_estimate(endpoint, actual_model, prompt_text, full_content, 'chat')
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

_GENERATE_SETTINGS_PROMPT = """根据以上对话内容，生成一份完整的小说项目方案，包含三大部分：设定、大纲、细纲。

要求：
1. 输出格式必须是 **JSON**，不要包含任何 markdown 代码块标记或其他说明文字
2. JSON 顶层结构如下：

{
  "settings": {
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
    "key_hooks": ["爽点1", "爽点2", "爽点3"],
    "target_words": 400000,
    "chapters_estimate": 200
  },
  "outline": {
    "volumes": [
      {
        "volume_number": 1,
        "volume_title": "第一卷标题",
        "summary": "本卷核心剧情概要（100-200字）",
        "chapters": [
          {
            "chapter_number": 1,
            "chapter_title": "第一章标题",
            "summary": "本章剧情概要（50-100字）"
          }
        ]
      }
    ]
  },
  "detailed_outline": {
    "volumes": [
      {
        "volume_number": 1,
        "volume_title": "第一卷标题",
        "chapters": [
          {
            "chapter_number": 1,
            "chapter_title": "第一章标题",
            "scene_setting": "时间、地点、氛围",
            "characters": "涉及角色1、角色2",
            "hook_point": "核心爽点/猎奇点（一句话）",
            "plot_steps": ["情节步骤1", "情节步骤2", "情节步骤3"],
            "dialogue_samples": ["关键对话示例1", "关键对话示例2"],
            "climax_design": "爽点设计说明：为什么这章能打动番茄读者",
            "ending_hook": "章节结尾钩子：下一章的悬念预告",
            "emotional_arc": "情绪走向，如：压抑→爆发→爽",
            "word_count_estimate": 3000
          }
        ]
      }
    ]
  }
}

3. 大纲部分（outline）必须规划 3-6 卷，每卷固定 30 章。outline.volumes[].chapters 中每卷都必须列出完整的 30 章列表，每章包含 chapter_number + chapter_title + summary（50-100字）。这是全书的"骨架"，必须完整、不能省略任何一章。
4. 细纲部分（detailed_outline）由于输出长度限制，优先保证前 1-2 卷的完整详细细纲（每章 200-400 字）。如果长度允许，尽量覆盖更多卷。但 outline 的章节列表必须完整覆盖全书所有卷。
5. 细纲字段必须严格按上述 JSON 结构填写，每个字段都要充实具体，不能敷衍
6. 直接返回 JSON 字符串，不要加 ```json 这样的代码块"""


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
            logger.warning(f"[Conversation] /generate-settings 模型 '{model}' 无可用端点")
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        actual_model = endpoint.get("model", model)
        temperature = _normalize_temp(actual_model, temperature)
        logger.info(f"[Conversation] /generate-settings 请求: provider={endpoint['provider']}, model={actual_model}, messages={len(messages)}")

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
            "model": actual_model,
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
            logger.error(f"[Conversation] /generate-settings API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502

        result = resp.json()
        # 🔥 Token用量计费
        _deduct_by_usage(result, endpoint, actual_model, 'generate-settings')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        logger.info(f"[Conversation] /generate-settings 响应长度: {len(raw_content)} 字符")

        # 尝试解析 JSON
        settings = _extract_json(raw_content)
        if not settings:
            logger.warning(f"[Conversation] /generate-settings JSON 解析失败，原始内容前 500 字: {raw_content[:500]}")
            return jsonify({
                "success": False,
                "error": "AI 返回内容无法解析为有效 JSON",
                "raw": raw_content[:2000]
            }), 422

        logger.info(f"[Conversation] /generate-settings 解析成功: settings_keys={list(settings.keys()) if isinstance(settings, dict) else 'not dict'}")
        return jsonify({
            "success": True,
            "settings": settings,
            "model": actual_model,
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


# ───────────────────────────────
#  3. 保存项目方案到文件系统
# ───────────────────────────────

@conversation_api.route('/save-project', methods=['POST'])
@login_required
def save_project():
    """
    保存设定+大纲+细纲到项目目录，同时生成番茄上传所需的 project_info.json
    """
    try:
        from pathlib import Path
        import datetime
        
        data = request.json or {}
        title = data.get("title", "未命名项目").strip()
        settings = data.get("settings", {})
        outline = data.get("outline", {})
        detailed_outline = data.get("detailed_outline", {})
        
        if not title:
            return jsonify({"success": False, "error": "书名不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 安全目录名
        safe_name = _safe_filename(title)
        project_dir = user_dir / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存设定为 Markdown（人类可读）
        settings_md = _settings_to_markdown(settings)
        settings_file = project_dir / "settings.md"
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(settings_md)
        
        # 2. 保存 outline.md
        outline_md = _outline_to_markdown(outline)
        outline_file = project_dir / "outline.md"
        with open(outline_file, 'w', encoding='utf-8') as f:
            f.write(outline_md)
        
        # 3. 保存细纲（总览 + 按卷拆分）
        detailed_md = _detailed_outline_to_markdown(detailed_outline)
        detailed_file = project_dir / "detailed_outline.md"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write(detailed_md)
        
        # 按卷保存单独文件
        volumes = detailed_outline.get('volumes', [])
        for vol in volumes:
            vol_num = vol.get('volume_number', 1)
            vol_md = _volume_to_markdown(vol)
            vol_file = project_dir / f"detailed_outline_vol{vol_num}.md"
            with open(vol_file, 'w', encoding='utf-8') as f:
                f.write(vol_md)
        
        # 4. 保存 core-setting.md（兼容旧流程，内容同 settings.md）
        core_file = project_dir / "core-setting.md"
        with open(core_file, 'w', encoding='utf-8') as f:
            f.write(settings_md)
        
        # 5. 生成 project_info.json（给番茄上传用）
        project_info = _build_project_info(title, settings, outline)
        info_file = project_dir / "project_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        # 6. 生成 project_config.json（兼容旧流程）
        config_file = project_dir / "project_config.json"
        config = {
            "novel_title": title,
            "proj_name": safe_name,
            "username": username,
            "total_chapters": project_info.get("generation_metadata", {}).get("total_chapters", 0),
            "total_words": project_info.get("generation_metadata", {}).get("total_words", 0),
            "created_at": datetime.datetime.now().isoformat(),
            "chapters_dir": "chapters",
            "format": "md"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[Conversation] /save-project 项目已保存: {project_dir} (title={title})")
        
        return jsonify({
            "success": True,
            "project_path": str(project_dir),
            "title": title,
            "message": "项目方案已保存"
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /save-project 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _safe_filename(name: str) -> str:
    """生成安全的目录名"""
    import re
    # 保留中文、英文、数字
    safe = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    if not safe:
        safe = "untitled"
    return safe


def _settings_to_markdown(settings: dict) -> str:
    """将 settings JSON 转为 Markdown 格式的核心设定文档"""
    lines = [f"# 《{settings.get('title', '未命名')}》核心设定", ""]
    
    if settings.get('synopsis'):
        lines.extend(["## 书籍简介", settings['synopsis'], ""])
    if settings.get('description'):
        lines.extend(["## 详细简介", settings['description'], ""])
    if settings.get('genre'):
        lines.extend([f"**题材**：{settings['genre']}", ""])
    if settings.get('tags'):
        lines.extend([f"**标签**：{', '.join(settings['tags'])}", ""])
    
    worldview = settings.get('worldview', {})
    if worldview:
        lines.extend(["## 世界观设定", ""])
        for k, v in worldview.items():
            lines.append(f"- **{k}**：{v}")
        lines.append("")
    
    characters = settings.get('characters', [])
    if characters:
        lines.extend(["## 角色设定", ""])
        for ch in characters:
            lines.append(f"### {ch.get('name', '未知')}")
            for k, v in ch.items():
                if k != 'name' and v:
                    lines.append(f"- **{k}**：{v}")
            lines.append("")
    
    hooks = settings.get('key_hooks', [])
    if hooks:
        lines.extend(["## 核心爽点", ""])
        for h in hooks:
            lines.append(f"- {h}")
        lines.append("")
    
    return "\n".join(lines)


def _outline_to_markdown(outline: dict) -> str:
    """将 outline JSON 转为 Markdown"""
    lines = ["# 全书大纲", ""]
    volumes = outline.get('volumes', [])
    for vol in volumes:
        lines.append(f"## 第{vol.get('volume_number', '?')}卷：{vol.get('volume_title', '')}")
        if vol.get('summary'):
            lines.extend(["", vol['summary'], ""])
        for ch in vol.get('chapters', []):
            lines.append(f"- 第{ch.get('chapter_number', '?')}章：{ch.get('chapter_title', '')} — {ch.get('summary', '')}")
        lines.append("")
    return "\n".join(lines)


def _chapter_to_markdown_lines(ch: dict) -> list:
    """将单个 chapter JSON 转为 Markdown 行列表（统一番茄网文细纲格式）"""
    lines = []
    ch_num = ch.get('chapter_number', '?')
    ch_title = ch.get('chapter_title', '')
    lines.append(f"## 第{ch_num}章 {ch_title}")
    lines.append("")
    
    # 场景设定
    if ch.get('scene_setting'):
        lines.append(f"**场景设定**：{ch['scene_setting']}")
    # 涉及角色
    if ch.get('characters'):
        chars = ch['characters']
        if isinstance(chars, list):
            chars = '、'.join(str(c) for c in chars)
        lines.append(f"**涉及角色**：{chars}")
    # 核心爽点
    if ch.get('hook_point'):
        lines.append(f"**核心爽点/猎奇点**：{ch['hook_point']}")
    # 具体情节步骤
    if ch.get('plot_steps'):
        lines.append("**具体情节步骤**：")
        for i, step in enumerate(ch['plot_steps'], 1):
            lines.append(f"{i}. {step}")
    # 关键对话示例
    if ch.get('dialogue_samples'):
        lines.append("**关键对话示例**：")
        for dlg in ch['dialogue_samples']:
            lines.append(f"- {dlg}")
    # 爽点设计
    if ch.get('climax_design'):
        lines.append(f"**爽点设计说明**：{ch['climax_design']}")
    # 章节结尾钩子
    if ch.get('ending_hook'):
        lines.append(f"**章节结尾钩子**：{ch['ending_hook']}")
    
    # 兼容旧字段
    if ch.get('summary') and not ch.get('scene_setting'):
        lines.append(f"**剧情概要**：{ch['summary']}")
    if ch.get('key_scenes'):
        lines.append("**关键场景**：")
        for s in ch['key_scenes']:
            lines.append(f"- {s}")
    if ch.get('emotional_arc'):
        lines.append(f"**情绪曲线**：{ch['emotional_arc']}")
    if ch.get('word_count_estimate'):
        lines.append(f"**预计字数**：{ch['word_count_estimate']}")
    
    lines.append("")
    return lines


def _detailed_outline_to_markdown(detailed: dict) -> str:
    """将 detailed_outline JSON 转为 Markdown（统一番茄网文细纲格式，兼容旧结构）"""
    lines = ["# 章节细纲", ""]
    volumes = detailed.get('volumes', [])
    if volumes:
        for vol in volumes:
            vol_title = vol.get('volume_title') or f"第{vol.get('volume_number', '?')}卷"
            lines.append(f"## {vol_title}")
            lines.append("")
            for ch in vol.get('chapters', []):
                lines.extend(_chapter_to_markdown_lines(ch))
    else:
        # 兼容旧结构：扁平 chapters
        for ch in detailed.get('chapters', []):
            lines.extend(_chapter_to_markdown_lines(ch))
    return "\n".join(lines)


def _volume_to_markdown(vol: dict) -> str:
    """将单卷细纲转为 Markdown（统一番茄网文细纲格式）"""
    vol_title = vol.get('volume_title') or f"第{vol.get('volume_number', '?')}卷"
    lines = [f"# {vol_title} 细纲", ""]
    for ch in vol.get('chapters', []):
        lines.extend(_chapter_to_markdown_lines(ch))
    return "\n".join(lines)


def _build_project_info(title: str, settings: dict, outline: dict) -> dict:
    """构建番茄上传用的 project_info.json"""
    import datetime
    
    # 统计章节数和字数
    total_chapters = 0
    total_words = 0
    volumes = outline.get('volumes', [])
    for vol in volumes:
        total_chapters += len(vol.get('chapters', []))
    
    detailed = settings.get('detailed_outline', {})
    for ch in detailed.get('chapters', []):
        total_words += ch.get('word_count_estimate', 0)
    
    # 如果没有细纲字数，用章节数 * 3000 估算
    if total_words == 0 and total_chapters > 0:
        total_words = total_chapters * 3000
    
    return {
        "novel_title": title,
        "novel_synopsis": settings.get('synopsis', ''),
        "genre": settings.get('genre', ''),
        "sub_genre": settings.get('sub_genre', ''),
        "target_platform": "番茄小说",
        "generation_mode": "conversation",
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "author_info": {
            "author_name": session.get('username', ''),
            "author_id": "",
            "author_statement": ""
        },
        "category_tags": {
            "main_category": settings.get('category', '都市'),
            "sub_category": settings.get('sub_category', '都市生活'),
            "tags": settings.get('tags', []),
            "target_audience": "男频",
            "content_rating": "全年龄"
        },
        "generation_metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_chapters": total_chapters,
            "total_words": total_words,
            "ai_model": "deepseek-v4",
            "mode_specific": {
                "info": {
                    "generation_mode": "conversation",
                    "has_outline": True,
                    "has_detailed_outline": True
                }
            }
        }
    }


# ───────────────────────────────
#  4. 自动质检（生成设定后自动调用）
# ───────────────────────────────

_QUALITY_CHECK_PROMPT = """请作为资深网文编辑，对以上小说项目方案进行严格质检。重点检查以下维度：

## 1. 设定矛盾
- 世界观背景、金手指规则、角色设定是否存在自相矛盾
- 力量体系/经济体系是否自洽

## 2. 毒点排查（读者雷区）
- 主角圣母、降智、双标
- 绿帽、背叛、虐主（让主角长期受辱无反击）
- 反派过于强大导致长期压抑、无解
- 逻辑硬伤（钱/实力来得太轻易、无代价）
- 后宫关系处理不当（女配脸谱化、无成长）

## 3. 爽点密度与节奏
- 打脸节奏是否紧凑（建议每3-5章一个小爽点，每卷一个大高潮）
- 期待感构建是否到位（铺垫→爆发→收获）
- 金手指使用是否有新意，还是老套路重复

## 4. 开局与节奏
- 开局是否拖沓（前3章必须出现核心爽点或悬念）
- 高潮来得是否太晚（第1卷结束前应有第一个大高潮）

## 5. 市场契合度
- 题材是否符合当前番茄/起点热门趋势
- 书名+简介是否具有点击吸引力

请输出 JSON（不要加代码块标记）：
{
  "passed": false,
  "overall_score": 72,
  "summary": "总体评价（100字以内）",
  "issues": [
    {
      "severity": "critical/warning/suggestion",
      "category": "设定矛盾/毒点/爽点/节奏/市场",
      "description": "具体问题描述",
      "location": "第X卷第Y章/全局/设定",
      "fix_suggestion": "具体修改建议"
    }
  ],
  "highlights": ["值得保留的亮点1", "亮点2"]
}

注意：
- severity: critical=必须改，warning=建议改，suggestion=可优化
- 至少找出3个问题，不能敷衍
- 同时指出2-3个亮点，保持建设性"""


@conversation_api.route('/quality-check', methods=['POST'])
@login_required
def quality_check():
    """
    对生成的项目方案进行自动质检。
    接收 settings + outline + detailed_outline，返回质检报告。
    """
    try:
        data = request.json or {}
        settings = data.get("settings", {})
        outline = data.get("outline", {})
        detailed_outline = data.get("detailed_outline", {})
        model = data.get("model", "deepseek-v4-pro")

        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        actual_model = endpoint.get("model", model)
        logger.info(f"[Conversation] /quality-check 请求: model={actual_model}")

        # 构建质检消息：把方案作为 user message，追加质检指令
        plan_text = json.dumps({
            "settings": settings,
            "outline": outline,
            "detailed_outline": detailed_outline
        }, ensure_ascii=False, indent=2)

        check_messages = [
            {"role": "user", "content": f"请对以下小说项目方案进行质检：\n\n{plan_text}"},
            {"role": "user", "content": _QUALITY_CHECK_PROMPT}
        ]

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        payload = {
            "model": actual_model,
            "messages": check_messages,
            "stream": False,
        }
        # DeepSeek 思考模式
        if "deepseek" in actual_model.lower():
            payload["thinking"] = {"type": "enabled"}

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
            logger.error(f"[Conversation] /quality-check API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502

        result = resp.json()
        # 🔥 Token用量计费
        _deduct_by_usage(result, endpoint, actual_model, 'quality-check')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        logger.info(f"[Conversation] /quality-check 响应长度: {len(raw_content)} 字符")

        report = _extract_json(raw_content)
        if not report:
            logger.warning(f"[Conversation] /quality-check JSON 解析失败")
            return jsonify({
                "success": False,
                "error": "质检结果无法解析为有效 JSON",
                "raw": raw_content[:2000]
            }), 422

        logger.info(f"[Conversation] /quality-check 完成: score={report.get('overall_score', 'N/A')}, issues={len(report.get('issues', []))}")
        return jsonify({
            "success": True,
            "report": report,
            "model": actual_model,
        })

    except Exception as e:
        logger.error(f"[Conversation] /quality-check 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  5. 正文生成（每卷一个会话）
# ───────────────────────────────

def _read_project_files(project_dir: Path):
    """读取项目目录下的设定、大纲、细纲文件"""
    files = {}
    
    # settings - 兼容新旧命名
    for settings_name in ["settings.md", "core-setting.md", "project_config.json"]:
        settings_path = project_dir / settings_name
        if settings_path.exists():
            if settings_name.endswith('.json'):
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    files['settings'] = _settings_to_markdown(data)
                except:
                    files['settings'] = settings_path.read_text(encoding='utf-8')
            else:
                files['settings'] = settings_path.read_text(encoding='utf-8')
            break
    if 'settings' not in files:
        files['settings'] = ""
    
    # outline - 兼容新旧命名
    for outline_name in ["outline.md", "rough-outline.md"]:
        outline_path = project_dir / outline_name
        if outline_path.exists():
            files['outline'] = outline_path.read_text(encoding='utf-8')
            break
    if 'outline' not in files:
        files['outline'] = ""
    
    return files


def _read_volume_detailed(project_dir: Path, volume_number: int):
    """读取指定卷的细纲"""
    # 先尝试按卷文件
    vol_file = project_dir / f"detailed_outline_vol{volume_number}.md"
    if vol_file.exists():
        return vol_file.read_text(encoding='utf-8')
    
    # 回退到总览文件（兼容连字符和下划线命名）
    for total_name in ["detailed_outline.md", "detailed-outline.md"]:
        total_file = project_dir / total_name
        if total_file.exists():
            text = total_file.read_text(encoding='utf-8')
            # 尝试提取该卷部分
            import re
            patterns = [
                rf'## 第{volume_number}卷.*?(?=## 第{volume_number + 1}卷|\Z)',
                rf'## .*?第{volume_number}卷.*?(?=## .*?第{volume_number + 1}卷|\Z)',
            ]
            for p in patterns:
                m = re.search(p, text, re.DOTALL)
                if m:
                    return m.group(0)
            return text
    
    return ""


def _offset_chapter_numbers(text: str, volume_number: int, chapters_per_volume: int = 30) -> str:
    """将分卷细纲中的章节号偏移为全书连续章节号。
    例如：第2卷的第1章 → 第31章
    只处理 Markdown 标题格式（##/### 开头行），不处理正文中的引用。
    """
    import re
    
    if volume_number <= 1 or not text:
        return text
    
    offset = (volume_number - 1) * chapters_per_volume
    
    CN_NUMS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000,'万':10000,'亿':100000000}
    
    def _cn_to_int(cn: str) -> int:
        if cn.isdigit():
            return int(cn)
        total = 0
        temp = 0
        for c in cn:
            if c in CN_NUMS:
                n = CN_NUMS[c]
                if n >= 10:
                    if temp == 0:
                        temp = 1
                    total += temp * n
                    temp = 0
                else:
                    temp = temp * 10 + n if temp else n
        return total + temp
    
    def _replacer(match):
        prefix = match.group(1)      # ## 或 ### 等（已包含"第"）
        num_raw = match.group(2)     # 中文或阿拉伯数字
        suffix = match.group(3)      # 章（已包含"章"）
        num = _cn_to_int(num_raw)
        new_num = num + offset
        return f"{prefix}{new_num}{suffix}"
    
    # 匹配 Markdown 章节标题行：## 第X章 或 ### 第X章
    pattern = r'^(#{2,3}\s+第)([一二三四五六七八九十百\d]+)(章\b)'
    return re.sub(pattern, _replacer, text, flags=re.MULTILINE)


def _extract_volume_chapter_plan(outline_text: str, volume_number: int, chapters_per_volume: int = 30) -> tuple:
    """从 outline Markdown 文本中提取某卷的章节规划。
    返回 (章节数, 章节列表文本, 全书起始章, 全书结束章)
    """
    import re
    
    global_start = (volume_number - 1) * chapters_per_volume + 1
    global_end = volume_number * chapters_per_volume
    
    if not outline_text or volume_number < 1:
        return chapters_per_volume, "", global_start, global_end
    
    # 尝试匹配 "第N卷" 区块：从 ## 第N卷 到下一个 ## 第N+1卷 或文件结束
    # 先尝试包含卷标题的格式：## 第N卷：标题
    vol_patterns = [
        rf'##\s*第{volume_number}卷[：:\s][^\n]*\n(.*?)(?=##\s*第{volume_number + 1}卷|\Z)',
        rf'##\s*第{volume_number}卷\n(.*?)(?=##\s*第|\Z)',
    ]
    
    vol_text = ""
    for p in vol_patterns:
        m = re.search(p, outline_text, re.DOTALL)
        if m:
            vol_text = m.group(1)
            break
    
    if not vol_text:
        return chapters_per_volume, "", global_start, global_end
    
    # 提取 "- 第X章：标题 — summary" 或 "- 第X章 标题" 格式的章节
    ch_pattern = r'^-\s*第(\d+)章[：:\s]+([^—\n]+?)(?:\s*—\s*(.+?))?$'
    chapters = re.findall(ch_pattern, vol_text, re.MULTILINE)
    
    if chapters:
        plan_lines = ["【本卷章节规划（按全书大纲）】"]
        for ch_num_str, ch_title, ch_summary in chapters:
            ch_num = int(ch_num_str)
            g_num = ch_num + (volume_number - 1) * chapters_per_volume
            line = f"- 全书第{g_num}章（本卷第{ch_num}章）：{ch_title.strip()}"
            if ch_summary:
                line += f" — {ch_summary.strip()}"
            plan_lines.append(line)
        return len(chapters), "\n".join(plan_lines), global_start, global_end
    
    return chapters_per_volume, "", global_start, global_end


def _build_writing_prompt(settings_text: str, outline_text: str, detailed_text: str, vol_num: int) -> str:
    """构建初始写作设定 prompt"""
    # 将分卷章节号偏移为全书连续章节号，确保 AI 生成正确的全书章节标题
    detailed_offset = _offset_chapter_numbers(detailed_text, vol_num)
    
    return f"""你是番茄小说（fanqienovel.com）签约级别的专业网文作家。请严格根据以下设定创作正文。

【核心设定】
{settings_text}

【全书大纲】
{outline_text}

【本卷细纲】
{detailed_offset}

---

## 平台风格（番茄小说读者偏好）

你的目标平台是番茄小说（fanqienovel.com），读者群体喜欢快节奏、强情绪、强反转的阅读体验。你只需要把握一个原则：**适合番茄读者**。

1. **不要长段落**：拒绝大段旁白和景物描写。叙述、对话、动作、心理各自成段，段落之间用空行分隔。

2. **防风格漂移**：
   - 每章开头用 1-2 句话回顾上一章的钩子，保持情绪连贯
   - 始终保持同一主角视角，禁止中途切换视角
   - 主角性格、行事逻辑在全卷中保持一致

## 格式铁律（违反视为失败）

1. **章节标题决定点击率——必须抓眼球**：
   - 标题公式：[核心事件/遭遇] + [冲突/悬念/反转] + [情绪词/感叹词]
   - 标题必须通过"读者测试"：读者只看标题，是否会产生"这章到底发生了什么？"的好奇心想点进来？
   - 以下标题会被番茄读者直接划走，**绝对禁止出现**：
     ❌ "省道上的四个小时"（没有事件，没有冲突，像日记）
     ❌ "老房子里的相册"（没有悬念，没有情绪，像散文）
     ❌ "系统不对话"（太平淡，像说明文）
     ❌ "数据包装"（没有人物，没有情节）
     ❌ "老书记的沉默"（没有反转，没有爽点）
     ❌ "全省第一个试点"（像公文报告）
   - 正确示范：
     ✅ "### 第1章 省道堵车四小时，系统突然弹出百亿蓝图！"
     ✅ "### 第2章 老房子里翻出神秘相册，系统竟要求他造太空电梯？"
     ✅ "### 第3章 系统装死不说话，林远一怒点了确认，全县炸了！"
   - 每章用 "### 第X章 【抓眼球标题】" 作为分隔标记

2. **第三人称**：全文使用第三人称（他/她），锁定主角视角，禁止切换视角。

3. **段落格式**：
   - 段落之间用一个空行分隔，顶格写（不要首行缩进）
   - 对话单独成段，用中文引号 "" 包裹
   - 拒绝大段旁白，叙述/对话/动作各自成段

4. **每章 2000 字左右**（1800-2200 字），严格按照细纲写作
5. 主角不能圣母、不能降智、不能受辱不还手
6. 每章结尾必须留钩子
7. **禁止输出任何说明文字、总结、分析、字数统计、写作思路、本章完、待续等标记**
8. 章节之间直接连续输出，不要插入空行或分隔线
9. 标题中的"第X章"用中文数字或阿拉伯数字均可"""


@conversation_api.route('/generate-batch', methods=['POST'])
@login_required
def generate_batch():
    """
    按批次生成正文。每卷一个会话。
    如果 messages 为空，自动构建初始设定消息。
    返回 SSE 流式响应。
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        start_chapter = data.get("start_chapter", 1)
        batch_size = data.get("batch_size", 6)
        model = data.get("model", "deepseek-v4-pro")
        messages = data.get("messages", [])
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400
        
        actual_model = endpoint.get("model", model)
        
        # 如果 messages 为空，构建初始设定消息
        if not messages:
            files = _read_project_files(project_dir)
            detailed = _read_volume_detailed(project_dir, volume_number)
            prompt = _build_writing_prompt(files.get('settings', ''), files.get('outline', ''), detailed, volume_number)
            messages = [{"role": "user", "content": prompt}]
        
        end_chapter = start_chapter + batch_size - 1
        
        # 计算全书实际章节号（分卷章节号 → 全书连续章节号）
        chapters_per_volume = 30
        actual_start = start_chapter + (volume_number - 1) * chapters_per_volume
        actual_end = end_chapter + (volume_number - 1) * chapters_per_volume
        
        gen_prompt = f"""请生成全书第{actual_start}章到第{actual_end}章的正文。

记住：每章标题必须是抓眼球的悬念/冲突型，以下类型标题会直接导致读者划走，绝对禁止：
- ❌ "省道上的四个小时" / "老房子里的相册" / "系统不对话" / "数据包装" / "老书记的沉默" / "全省第一个试点"
- 正确公式：[核心事件] + [冲突/悬念/反转] + [情绪词/感叹词]
- 正确示例："第{actual_start}章 省道堵车四小时，系统突然弹出百亿蓝图！"

严格按照细纲写作，每章2000字左右。"""
        
        # 追加到 messages
        req_messages = messages.copy()
        req_messages.append({"role": "user", "content": gen_prompt})
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }
        
        payload = {
            "model": actual_model,
            "messages": req_messages,
            "stream": True,
        }
        if "deepseek" in actual_model.lower():
            payload["thinking"] = {"type": "enabled"}
        
        logger.info(f"[Conversation] /generate-batch: project={project_id}, vol={volume_number}, chapters={start_chapter}-{end_chapter}, model={actual_model}")
        
        def generate():
            try:
                resp = requests.post(
                    endpoint["api_url"],
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=600
                )
            except Exception as e:
                yield f"data: {json.dumps({'error': f'请求异常: {str(e)}'})}\n\n"
                return
            
            if not resp.ok:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err = resp.text or f"HTTP {resp.status_code}"
                logger.error(f"[Conversation] /generate-batch API 错误: {err}")
                yield f"data: {json.dumps({'error': err})}\n\n"
                return
            
            full_text = ""
            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_text = line.decode('utf-8')
                    if not line_text.startswith('data: '):
                        continue
                    
                    data_content = line_text[6:]
                    if data_content == '[DONE]':
                        # 保存章节文件
                        _save_chapters_from_text(project_dir, full_text)
                        yield "data: [DONE]\n\n"
                        break
                    
                    try:
                        chunk = json.loads(data_content)
                        choices = chunk.get("choices") or [{}]
                        delta = choices[0].get("delta", {}) if choices else {}
                        content_piece = delta.get("content", "")
                        reasoning_piece = delta.get("reasoning_content", "")
                        if content_piece:
                            full_text += content_piece
                            yield f"data: {json.dumps({'content': content_piece})}\n\n"
                        if reasoning_piece:
                            yield f"data: {json.dumps({'reasoning': reasoning_piece})}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
                # 🔥 流式响应结束后进行Token估算计费
                prompt_text = "\n".join(m.get("content", "") for m in req_messages)
                _deduct_by_estimate(endpoint, actual_model, prompt_text, full_text, 'generate-batch')
            except Exception as e:
                logger.error(f"[Conversation] /generate-batch 流式异常: {e}")
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
        logger.error(f"[Conversation] /generate-batch 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _save_chapters_from_text(project_dir: Path, text: str):
    """从 AI 返回的文本中提取章节并保存为 .md 文件"""
    import re
    
    chapters_dir = project_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # 按 "### 第X章 标题" 分割，支持阿拉伯数字和中文数字
    pattern = r'### 第([一二三四五六七八九十百千万亿\d]+)章\s*(.*?)\n'
    matches = list(re.finditer(pattern, text))
    
    if not matches:
        logger.warning(f"[Conversation] 未找到章节标记，尝试保存为单文件")
        # 兜底：保存为临时文件
        temp_file = chapters_dir / "_generated_temp.md"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(text)
        return
    
    # 中文数字转阿拉伯数字映射
    CN_NUMS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000,'万':10000,'亿':100000000}
    
    def cn_to_int(cn: str) -> int:
        """简单中文数字转阿拉伯数字"""
        if cn.isdigit():
            return int(cn)
        total = 0
        temp = 0
        for c in cn:
            if c in CN_NUMS:
                n = CN_NUMS[c]
                if n >= 10:
                    if temp == 0:
                        temp = 1
                    total += temp * n
                    temp = 0
                else:
                    temp = temp * 10 + n if temp else n
        return total + temp
    
    for i, match in enumerate(matches):
        ch_num_raw = match.group(1)
        ch_title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        
        # 转换章节号为阿拉伯数字
        ch_num = cn_to_int(ch_num_raw)
        
        # 构建文件名
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', ch_title).strip() or "untitled"
        filename = f"第{ch_num}章_{safe_title}.md"
        filepath = chapters_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 第{ch_num}章 {ch_title}\n\n{content}\n")
        
        logger.info(f"[Conversation] 章节已保存: {filepath}")


# ───────────────────────────────
#  6. 对齐质检（正文 vs 细纲）
# ───────────────────────────────

_ALIGN_CHECK_PROMPT = """你是番茄小说资深编辑。请对生成的正文进行全维度质检，严格对标原始大纲、细纲和核心设定。

## 质检维度

1. **大纲一致性**：正文剧情走向是否与全书大纲一致？是否有擅自改变主线、跳过关键节点、添加大纲外的支线？
2. **细纲一致性**：正文是否严格按细纲中的场景、情绪曲线、关键对话写作？场景是否遗漏或擅自添加？
3. **设定一致性**：
   - 人设：主角性格、说话方式、行事逻辑是否与设定一致？是否圣母/降智/双标/人设崩塌？
   - 世界观：金手指规则、力量体系、势力关系是否与设定一致？是否出现设定外的能力或规则？
   - 物品/状态：关键道具、角色状态（修为/资产/伤势）是否前后一致？是否出现状态突变无解释？
4. **逻辑一致性**：时间线是否合理？因果关系是否通顺？角色行为动机是否充分？是否存在明显的逻辑漏洞？
5. **网文毒点分析**（必须逐项排查，发现即报）：
   - 主角圣母心泛滥、以德报怨
   - 主角智商掉线、被反派戏耍不还手
   - 反派过强且长期无解，读者看不到希望
   - 身份暴露/打脸节奏拖沓，爽点被水掉
   - 突然新增设定解释之前漏洞（机械降神）
   - 感情线突兀、暧昧对象工具人化
   - 系统/金手指规则前后矛盾
   - 严重水字数、大段无意义景物描写
   - 章节结尾无钩子，读者没有翻页动力
   - 视角漂移、突然切换到配角内心独白
6. **爽点密度**：打脸是否有力？期待感是否拉满？钩子是否到位？情绪峰值是否足够？
7. **节奏**：是否有拖沓？水字数？信息密度是否够？
8. **字数**：每章是否在 1800-2200 字范围内？

## 输出 JSON（不要加代码块标记）

```json
{
  "passed": false,
  "overall_score": 78,
  "issues": [
    {
      "chapter": 1,
      "severity": "critical/warning/suggestion",
      "category": "大纲偏离/细纲偏离/设定矛盾/逻辑漏洞/毒点/爽点不足/节奏/字数/风格漂移",
      "description": "具体问题描述，指出哪里错了、怎么错的",
      "fix_suggestion": "具体的修改建议",
      "highlights": ["正文中需要高亮的具体文字片段1", "片段2"]
    }
  ],
  "chapter_scores": {"1": 80, "2": 75},
  "summary": "总体评价，指出最严重的问题和最大亮点"
}
```

## 输出要求
- severity: critical=必须改，warning=建议改，suggestion=可优化
- 每章至少找出1个问题，整批至少3个问题
- 每章给分（0-100）
- **highlights 字段必须填写**：从正文中摘录出具体的问题文字片段，供前端高亮显示。如果没有具体文字可摘录，填 []
- summary 字段给出 50-100 字的总体评价"""


@conversation_api.route('/align-check', methods=['POST'])
@login_required
def align_check():
    """
    对齐质检：对比生成的正文与原始细纲。
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        start_chapter = data.get("start_chapter", 1)
        end_chapter = data.get("end_chapter", 6)
        model = data.get("model", "deepseek-v4-pro")
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        # 读取生成的正文
        chapters_dir = project_dir / "chapters"
        generated_texts = []
        for ch_num in range(start_chapter, end_chapter + 1):
            # 查找文件
            pattern = f"第{ch_num}章_*.md"
            files = list(chapters_dir.glob(pattern))
            if files:
                text = files[0].read_text(encoding='utf-8')
                generated_texts.append(f"=== 第{ch_num}章 ===\n{text}\n")
        
        if not generated_texts:
            return jsonify({"success": False, "error": "未找到生成的章节文件"}), 404
        
        generated_combined = "\n".join(generated_texts)
        
        # 读取大纲、细纲、设定
        files = _read_project_files(project_dir)
        outline = files.get('outline', '')
        settings = files.get('settings', '')
        detailed = _read_volume_detailed(project_dir, volume_number)
        
        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400
        
        actual_model = endpoint.get("model", model)
        logger.info(f"[Conversation] /align-check: project={project_id}, vol={volume_number}, chapters={start_chapter}-{end_chapter}")
        
        # 构建质检消息，包含大纲、设定、细纲、正文
        check_prompt = f"""【全书大纲】
{outline[:5000]}

【核心设定】
{settings[:5000]}

【本卷细纲】
{detailed[:8000]}

【生成的正文】
{generated_combined}

{_ALIGN_CHECK_PROMPT}"""
        
        check_messages = [
            {"role": "user", "content": check_prompt}
        ]
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }
        
        payload = {
            "model": actual_model,
            "messages": check_messages,
            "stream": False,
        }
        if "deepseek" in actual_model.lower():
            payload["thinking"] = {"type": "enabled"}
        
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
            logger.error(f"[Conversation] /align-check API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502
        
        result = resp.json()
        # 🔥 Token用量计费
        _deduct_by_usage(result, endpoint, actual_model, 'align-check')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        report = _extract_json(raw_content)
        if not report:
            logger.warning(f"[Conversation] /align-check JSON 解析失败")
            return jsonify({
                "success": False,
                "error": "质检结果无法解析为有效 JSON",
                "raw": raw_content[:2000]
            }), 422
        
        logger.info(f"[Conversation] /align-check 完成: score={report.get('overall_score', 'N/A')}")
        return jsonify({
            "success": True,
            "report": report,
            "model": actual_model,
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /align-check 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  7. 读取项目文件（细纲/设定/大纲）
# ───────────────────────────────

@conversation_api.route('/project-files', methods=['POST'])
@login_required
def get_project_files():
    """
    读取项目目录下的设定、大纲、细纲文件内容
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        files = _read_project_files(project_dir)
        detailed = _read_volume_detailed(project_dir, volume_number)
        
        # 统计各卷章节数
        chapters_dir = project_dir / "chapters"
        chapter_files = list(chapters_dir.glob("第*.md")) if chapters_dir.exists() else []
        
        logger.info(f"[Conversation] /project-files: project={project_id}, vol={volume_number}")
        return jsonify({
            "success": True,
            "settings": files.get('settings', '')[:10000],
            "outline": files.get('outline', '')[:10000],
            "detailed_outline": detailed[:20000],
            "chapter_count": len(chapter_files),
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /project-files 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  8. 保存项目文件（设定/大纲/细纲）
# ───────────────────────────────

def _detect_file_path(project_dir: Path, candidates: list) -> Path:
    """检测项目中已存在的文件，返回第一个存在的，都不存在则返回第一个候选"""
    for name in candidates:
        p = project_dir / name
        if p.exists():
            return p
    return project_dir / candidates[0]


@conversation_api.route('/save-project-files', methods=['POST'])
@login_required
def save_project_files():
    """
    保存项目文件（设定/大纲/细纲）。只保存提供的非空字段。
    兼容新旧命名方式，保存前自动备份原文件。
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        settings_text = data.get("settings")
        outline_text = data.get("outline")
        detailed_text = data.get("detailed_outline")
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        saved = []
        
        # 保存设定
        if settings_text is not None:
            settings_path = _detect_file_path(project_dir, ["settings.md", "core-setting.md"])
            # 备份
            if settings_path.exists():
                backup_path = settings_path.with_suffix('.md.bak')
                try:
                    backup_path.write_text(settings_path.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
            settings_path.write_text(settings_text, encoding='utf-8')
            saved.append(str(settings_path.name))
            logger.info(f"[Conversation] 设定已保存: {settings_path}")
        
        # 保存大纲
        if outline_text is not None:
            outline_path = _detect_file_path(project_dir, ["outline.md", "rough-outline.md"])
            if outline_path.exists():
                backup_path = outline_path.with_suffix('.md.bak')
                try:
                    backup_path.write_text(outline_path.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
            outline_path.write_text(outline_text, encoding='utf-8')
            saved.append(str(outline_path.name))
            logger.info(f"[Conversation] 大纲已保存: {outline_path}")
        
        # 保存细纲
        if detailed_text is not None:
            # 优先按卷文件，没有则按总览文件
            vol_path = project_dir / f"detailed_outline_vol{volume_number}.md"
            if vol_path.exists():
                detailed_path = vol_path
            else:
                detailed_path = _detect_file_path(project_dir, ["detailed-outline.md", "detailed_outline.md"])
            
            if detailed_path.exists():
                backup_path = detailed_path.with_suffix('.md.bak')
                try:
                    backup_path.write_text(detailed_path.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
            detailed_path.write_text(detailed_text, encoding='utf-8')
            saved.append(str(detailed_path.name))
            logger.info(f"[Conversation] 细纲已保存: {detailed_path}")
        
        return jsonify({
            "success": True,
            "saved": saved,
            "message": f"已保存 {len(saved)} 个文件",
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /save-project-files 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  9. 生成分卷细纲
# ───────────────────────────────

_VOLUME_OUTLINE_PROMPT = """你是专业网文策划。请根据以下设定和大纲，生成指定卷的详细细纲。

要求：
1. 本卷细纲必须严格围绕大纲中该卷的内容展开，不能偏离主线
2. 每章包含：场景设定、涉及角色、核心爽点/猎奇点、具体情节步骤、关键对话示例、爽点设计
3. 每章细纲字数 200-400 字
4. 章节之间要有清晰的情绪曲线和钩子衔接
5. 用 Markdown 格式输出，每章用 "## 第X章 标题" 开头
6. 不要输出任何说明文字、总结、分析"""


@conversation_api.route('/generate-volume-outline', methods=['POST'])
@login_required
def generate_volume_outline():
    """
    根据设定和大纲，生成指定卷的细纲并保存。
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        model = data.get("model", "deepseek-v4-pro")
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        # 读取设定和大纲
        files = _read_project_files(project_dir)
        settings = files.get('settings', '')
        outline = files.get('outline', '')
        
        if not outline:
            return jsonify({"success": False, "error": "项目暂无大纲，无法生成分卷细纲"}), 400
        
        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400
        
        actual_model = endpoint.get("model", model)
        logger.info(f"[Conversation] /generate-volume-outline: project={project_id}, vol={volume_number}, model={actual_model}")
        
        prompt = f"""【核心设定】
{settings[:5000]}

【全书大纲】
{outline[:8000]}

【任务】
请生成第{volume_number}卷的详细细纲。

{_VOLUME_OUTLINE_PROMPT}"""
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }
        
        payload = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if "deepseek" in actual_model.lower():
            payload["thinking"] = {"type": "enabled"}
        
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
            logger.error(f"[Conversation] /generate-volume-outline API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502
        
        result = resp.json()
        # 🔥 Token用量计费
        _deduct_by_usage(result, endpoint, actual_model, 'generate-volume-outline')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        
        # 保存到文件
        vol_file = project_dir / f"detailed_outline_vol{volume_number}.md"
        vol_file.write_text(raw_content, encoding='utf-8')
        logger.info(f"[Conversation] 第{volume_number}卷细纲已保存: {vol_file}")
        
        return jsonify({
            "success": True,
            "content": raw_content,
            "file": str(vol_file.name),
            "model": actual_model,
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /generate-volume-outline 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ───────────────────────────────
#  10. 分卷细纲生成页面 API
# ───────────────────────────────

def _build_volume_outline_v2_prompt(volume_number: int, chapter_count: int,
                                     global_start: int, global_end: int,
                                     chapter_plan_text: str = "") -> str:
    """构建分卷细纲生成 prompt（统一番茄网文细纲格式，含章节范围约束）"""
    plan_section = chapter_plan_text if chapter_plan_text else ""
    
    return f"""你是番茄小说签约级别的专业网文策划。请根据以下信息生成本卷细纲。

【卷次与章节范围】
- 本卷为第{volume_number}卷
- 本卷共 {chapter_count} 章
- 对应全书第 {global_start} 章 到 第 {global_end} 章
{plan_section}

【细纲格式要求（必须严格遵守）】
每章必须按以下固定格式输出，不得遗漏任何字段：

## 第X章 【抓眼球标题】

**场景设定**：时间、地点、氛围
**涉及角色**：角色1、角色2
**核心爽点/猎奇点**：一句话概括本章最吸引读者的点
**具体情节步骤**：
1. 步骤一
2. 步骤二
3. 步骤三
**关键对话示例**：
- "对话内容1"
- "对话内容2"
**爽点设计说明**：为什么这个设计能打动番茄读者
**章节结尾钩子**：下一章的悬念预告

【内容要求】
1. 本卷细纲必须严格围绕大纲中该卷的内容展开，不能偏离主线
2. 每章细纲 200-400 字
3. 章节之间要有清晰的情绪曲线和钩子衔接
4. 标题必须是悬念型/冲突型/情绪型，禁止平淡陈述句
5. 不要输出任何说明文字、总结、分析、字数统计"""


@conversation_api.route('/volume-outline-context', methods=['GET'])
@login_required
def volume_outline_context():
    """
    获取分卷细纲生成所需的上下文：设定 + 大纲 + 上一卷细纲
    """
    try:
        project_id = request.args.get("project_id", "").strip()
        volume_number = int(request.args.get("volume_number", 1))
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        files = _read_project_files(project_dir)
        
        # 读取上一卷细纲（如果 volume > 1）
        prev_outline = ""
        has_prev = False
        if volume_number > 1:
            prev_vol_file = project_dir / f"detailed_outline_vol{volume_number - 1}.md"
            if prev_vol_file.exists():
                prev_outline = prev_vol_file.read_text(encoding='utf-8')
                has_prev = True
            else:
                # 尝试从总览文件中提取上一卷
                total_file = _detect_file_path(project_dir, ["detailed-outline.md", "detailed_outline.md"])
                if total_file.exists():
                    total_text = total_file.read_text(encoding='utf-8')
                    import re
                    # 尝试匹配 "第N卷" 或 "第{N}卷"
                    patterns = [
                        rf'## 第{volume_number - 1}卷.*?(?=## 第{volume_number}卷|\Z)',
                        rf'## .*?第{volume_number - 1}卷.*?(?=## .*?第{volume_number}卷|\Z)',
                    ]
                    for p in patterns:
                        m = re.search(p, total_text, re.DOTALL)
                        if m:
                            prev_outline = m.group(0)
                            has_prev = True
                            break
        
        logger.info(f"[Conversation] /volume-outline-context: project={project_id}, vol={volume_number}, has_prev={has_prev}")
        return jsonify({
            "success": True,
            "settings": files.get('settings', '')[:8000],
            "outline": files.get('outline', '')[:8000],
            "prev_volume_outline": prev_outline[:15000],
            "has_prev": has_prev,
            "volume_number": volume_number,
        })
        
    except Exception as e:
        logger.error(f"[Conversation] /volume-outline-context 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@conversation_api.route('/generate-volume-outline-v2', methods=['POST'])
@login_required
def generate_volume_outline_v2():
    """
    流式生成分卷细纲（SSE）。
    接收设定 + 大纲 + 上一卷细纲 + 用户补充要求。
    """
    try:
        data = request.json or {}
        project_id = data.get("project_id", "").strip()
        volume_number = data.get("volume_number", 1)
        model = data.get("model", "deepseek-v4-pro")
        user_notes = data.get("user_notes", "").strip()
        
        if not project_id:
            return jsonify({"success": False, "error": "project_id 不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        project_dir = user_dir / project_id
        if not project_dir.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        # 读取上下文
        files = _read_project_files(project_dir)
        settings = files.get('settings', '')
        outline = files.get('outline', '')
        
        prev_outline = ""
        if volume_number > 1:
            prev_vol_file = project_dir / f"detailed_outline_vol{volume_number - 1}.md"
            if prev_vol_file.exists():
                prev_outline = prev_vol_file.read_text(encoding='utf-8')
        
        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400
        
        actual_model = endpoint.get("model", model)
        logger.info(f"[Conversation] /generate-volume-outline-v2: project={project_id}, vol={volume_number}, model={actual_model}")
        
        # 从全书大纲中提取本卷章节规划
        chapter_count, chapter_plan_text, global_start, global_end = _extract_volume_chapter_plan(
            outline, volume_number
        )
        
        # 构建 prompt
        outline_prompt = _build_volume_outline_v2_prompt(
            volume_number, chapter_count, global_start, global_end, chapter_plan_text
        )
        
        prompt_parts = [
            f"【核心设定】\n{settings[:5000]}",
            f"【全书大纲】\n{outline[:6000]}",
        ]
        if prev_outline:
            prompt_parts.append(f"【上一卷细纲】\n{prev_outline[:4000]}")
        if user_notes:
            prompt_parts.append(f"【作者补充要求】\n{user_notes}")
        prompt_parts.append(outline_prompt)
        
        full_prompt = "\n\n".join(prompt_parts)
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }
        
        payload = {
            "model": actual_model,
            "messages": [{"role": "user", "content": full_prompt}],
            "stream": True,
        }
        if "deepseek" in actual_model.lower():
            payload["thinking"] = {"type": "enabled"}
        
        def generate():
            try:
                resp = requests.post(
                    endpoint["api_url"],
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=600
                )
            except Exception as e:
                yield f"data: {json.dumps({'error': f'请求异常: {str(e)}'})}\n\n"
                return
            
            if not resp.ok:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err = resp.text or f"HTTP {resp.status_code}"
                logger.error(f"[Conversation] /generate-volume-outline-v2 API 错误: {err}")
                yield f"data: {json.dumps({'error': err})}\n\n"
                return
            
            full_text = ""
            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_text = line.decode('utf-8')
                    if not line_text.startswith('data: '):
                        continue
                    
                    data_content = line_text[6:]
                    if data_content == '[DONE]':
                        # 保存到文件
                        vol_file = project_dir / f"detailed_outline_vol{volume_number}.md"
                        vol_file.write_text(full_text, encoding='utf-8')
                        logger.info(f"[Conversation] 第{volume_number}卷细纲已保存: {vol_file}")
                        yield "data: [DONE]\n\n"
                        break
                    
                    try:
                        chunk = json.loads(data_content)
                        choices = chunk.get("choices") or [{}]
                        delta = choices[0].get("delta", {}) if choices else {}
                        content_piece = delta.get("content", "")
                        reasoning_piece = delta.get("reasoning_content", "")
                        if content_piece:
                            full_text += content_piece
                            yield f"data: {json.dumps({'content': content_piece})}\n\n"
                        if reasoning_piece:
                            yield f"data: {json.dumps({'reasoning': reasoning_piece})}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
                # 🔥 流式响应结束后进行Token估算计费
                _deduct_by_estimate(endpoint, actual_model, full_prompt, full_text, 'generate-volume-outline-v2')
            except Exception as e:
                logger.error(f"[Conversation] /generate-volume-outline-v2 流式异常: {e}")
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
        logger.error(f"[Conversation] /generate-volume-outline-v2 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
