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
            # DeepSeek 思考模式：添加 thinking 参数，并移除 temperature
            is_deepseek = "deepseek" in model.lower()
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
                        reasoning_piece = delta.get("reasoning_content", "")
                        if reasoning_piece:
                            yield f"data: {json.dumps({'reasoning': reasoning_piece})}\n\n"
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
    "chapters": [
      {
        "chapter_number": 1,
        "chapter_title": "第一章标题",
        "summary": "本章详细内容规划（200-300字），包含出场人物、关键对话、情绪转折",
        "key_scenes": ["场景1", "场景2"],
        "emotional_arc": "情绪走向，如：压抑→爆发→爽",
        "word_count_estimate": 3000
      }
    ]
  }
}

3. 大纲部分至少规划 3-5 卷，每卷 20-60 章
4. 细纲部分至少输出前 30 章的详细规划，后续章节可简略但要覆盖全书
5. 内容要充实、有创意，不能敷衍
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
        
        # 3. 保存 detailed_outline.md
        detailed_md = _detailed_outline_to_markdown(detailed_outline)
        detailed_file = project_dir / "detailed_outline.md"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write(detailed_md)
        
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
        
        logger.info(f"[Conversation] 项目已保存: {project_dir}")
        
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


def _detailed_outline_to_markdown(detailed: dict) -> str:
    """将 detailed_outline JSON 转为 Markdown"""
    lines = ["# 章节细纲", ""]
    chapters = detailed.get('chapters', [])
    for ch in chapters:
        lines.append(f"## 第{ch.get('chapter_number', '?')}章：{ch.get('chapter_title', '')}")
        if ch.get('summary'):
            lines.extend(["", ch['summary'], ""])
        if ch.get('key_scenes'):
            lines.extend(["**关键场景**：", ""])
            for s in ch['key_scenes']:
                lines.append(f"- {s}")
            lines.append("")
        if ch.get('emotional_arc'):
            lines.append(f"**情绪曲线**：{ch['emotional_arc']}")
        if ch.get('word_count_estimate'):
            lines.append(f"**预计字数**：{ch['word_count_estimate']}")
        lines.append("")
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
