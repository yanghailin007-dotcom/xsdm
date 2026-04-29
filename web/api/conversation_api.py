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

_REALITY_AVOIDANCE_RULES = """【现实规避铁律 — 平行时空设定】
1. 国名代称：中国→龙国/华夏/九州，美国→星条国/合众国，日本→樱花国/东瀛，英国→雾都国
2. 一线城市：北京→B市/京城/燕京，上海→S市/沪市/申城，深圳→S市/深市/鹏城，广州→G市/羊城
3. 省份：广东→粤州/南粤，浙江→浙州/钱塘，江苏→苏州/江南，四川→蜀州/天府
4. 机构：省政府→省署/省府，县政府→县衙/县署，公安局→警署/治安司，法院→裁判司，高铁→磁悬浮/城际快线
5. 品牌/APP：iPhone→智能机，微信→某社交软件，支付宝→某支付软件，抖音→某短视频平台，微博→某社交平台，淘宝→某购物平台
6. 真实名人：禁止出现真实存在的名人、明星、政客姓名
7. 敏感事件：禁止影射、映射、暗示任何现实敏感事件
8. 货币：人民币→龙币/华夏币；身份证→身份卡；驾驶证→驾驶许可
9. 本故事发生在平行时空，所有地名、机构、事件均为虚构"""

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

    # 3. 获取该 provider 下与 model_name 匹配的 endpoint
    if provider:
        endpoints = api_endpoints.get(provider, [])
        # 优先匹配 model_name 完全一致的 endpoint
        for ep in endpoints:
            if ep.get("model") == model_name and ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": provider,
                    "model":    ep.get("model", model_name),
                }
        # fallback：返回第一个启用的 endpoint，但保留用户请求的 model 名用于 API 调用
        for ep in endpoints:
            if ep.get("enabled", True):
                return {
                    "api_key":  ep.get("api_key", ""),
                    "api_url":  ep.get("api_url", ""),
                    "provider": provider,
                    "model":    model_name,
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

_GENERATE_SETTINGS_PROMPT = """根据以上对话内容，生成一份小说项目设定文档（Markdown格式）。

要求：
1. 输出格式必须是 **Markdown**，不要包含任何 markdown 代码块标记（```）或其他说明文字
2. 文档结构必须严格按以下模板：

# 项目信息

- **书名**：《书名》（严格控制在15个字以内，超过15字的书名读者记忆成本过高，直接影响点击率）
- **一句话简介**：20-50字，必须抓住眼球
- **番茄风格简介**：100-200字。要求：
  - 第1章就有爽点或强悬念
  - 突出金手指/系统的核心卖点（让读者一眼知道"这书爽在哪"）
  - 有打脸/反转的预期，情绪强烈
  - 短促有力，不要叙事体，不要抒情，像番茄推荐位文案
  - 示例风格："35岁被大厂优化，回到连高铁都没有的贫困县。所有人都当他废了，直到手机里弹出一个倒计时：【太空电梯奠基仪式：29年364天】"
- **题材**：例如 都市·科幻·系统
- **标签**：标签1、标签2、标签3
- **目标字数**：40万字
- **预估章节**：200章

# 世界观设定

## 背景
（世界观背景，100-300字）

## 核心规则/金手指
（金手指机制，必须具体、有代价、有成长空间）

## 时代设定
（时代/背景设定）

# 角色设定

## 主角：xxx
- **性格**：...
- **背景**：...
- **核心目标**：...

## 核心反派/对手：xxx
- **性格**：...
- **与主角的矛盾**：...

## 女主/重要配角：xxx
- **性格**：...
- **与主角的关系**：...

# 核心爽点设计
1. 爽点1（说明为什么爽）
2. 爽点2
3. 爽点3

# 全书故事节奏规划（网文结构）
按网文"爽点循环"划分为若干节奏阶段，每个阶段是一个完整的"压抑→反击→收获→钩子"情绪周期。

| 阶段 | 预计章数 | 核心功能 | 核心爽点 | 情绪走向 | 衔接钩子 |
|------|---------|---------|---------|---------|---------|
| ... | ... | ... | ... | ... | ... |

阶段数量不限，但必须连续覆盖全书，不能有遗漏。阶段是故事节奏单位，不是出版分卷单位。

3. 角色至少包含主角、核心反派/对手、女主/重要配角
4. 爽点设计要贴合番茄读者偏好：即时反馈、打脸反转、升级收获

""" + _REALITY_AVOIDANCE_RULES + """
5. 直接返回 Markdown 文本，不要加 ``` 代码块"""

_CUSTOM_PROMPTS_FILENAME = "prompts.json"

def _get_default_prompts():
    return {"settings": _GENERATE_SETTINGS_PROMPT, "outline": _GENERATE_OUTLINE_PROMPT, "detailed": _GENERATE_DETAILED_PROMPT}

def _read_custom_prompts(project_dir: Path):
    defaults = _get_default_prompts()
    custom_file = project_dir / _CUSTOM_PROMPTS_FILENAME
    if not custom_file.exists():
        return defaults, {k: False for k in defaults}
    try:
        data = json.loads(custom_file.read_text(encoding='utf-8'))
        prompts, is_custom = {}, {}
        for key in defaults:
            val = data.get(key)
            if val and isinstance(val, str) and val.strip():
                prompts[key] = val
                is_custom[key] = True
            else:
                prompts[key] = defaults[key]
                is_custom[key] = False
        return prompts, is_custom
    except Exception:
        return defaults, {k: False for k in defaults}

def _save_custom_prompts(project_dir: Path, prompts: dict):
    custom_file = project_dir / _CUSTOM_PROMPTS_FILENAME
    try:
        custom_file.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error(f"保存自定义prompt失败: {e}")
        raise


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
        custom_prompts = data.get("custom_prompts", {})
        settings_prompt = custom_prompts.get("settings", "") or _GENERATE_SETTINGS_PROMPT
        gen_messages = messages.copy()
        gen_messages.append({
            "role": "user",
            "content": settings_prompt
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

        # 直接返回原始 Markdown 文本
        if not raw_content or len(raw_content) < 100:
            logger.warning(f"[Conversation] /generate-settings 返回内容过短: {len(raw_content)} 字符")
            return jsonify({
                "success": False,
                "error": "AI 返回内容异常过短",
                "raw": raw_content[:2000]
            }), 422

        logger.info(f"[Conversation] /generate-settings 成功: {len(raw_content)} 字符")
        return jsonify({
            "success": True,
            "content": raw_content,
            "model": actual_model,
        })

    except Exception as e:
        logger.error(f"[Conversation] /generate-settings 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



_GENERATE_OUTLINE_PROMPT = """请根据以下小说设定，生成完整的卷级大纲（Markdown格式）。

你不是在写每章的摘要。你是在设计读者的"追读心理契约"——回答"读者为什么停不下来"。

要求：
1. 输出格式必须是 **Markdown**，不要包含任何 markdown 代码块标记（```）或其他说明文字
2. 文档结构：

# 全书大纲

## 核心卖点
[主角身份] + [金手指/核心能力] + [核心冲突/目标]，一句话抓住读者

## 追读预期链（分阶段设计）
读者点开第1章时，心里种下了一个核心问题：________
这个问题分几个阶段回答，每个阶段都是新的钩子。

| 阶段 | 章节区间 | 核心问题 | 延迟策略 | 兑现方式 |
|------|---------|---------|---------|---------|
| 阶段1 | 第1-X章 | ... | ... | ... |
| 阶段2 | 第X-Y章 | ... | ... | ... |

## 爽点排布表
| 位置 | 爽点类型 | 具体设计 | 作用 |
|------|---------|---------|------|
| 卷首 | 代入爽 | ... | 建立情感连接 |
| 1/4处 | 希望爽 | ... | 建立信心 |
| 中点 | 打脸爽 | ... | 第一次情绪释放 |
| 3/4处 | 危机爽 | ... | 升级紧张感 |
| 卷尾 | 爆发爽 | ... | 大满足+新钩子 |

## 第一卷：卷标题

**卷核心卖点**：本卷给读者的核心满足是什么？
**卷情绪走向**：例如 压抑→希望→小爽→挫折→大爽→钩子
**卷目标**：主角这卷要达成什么？留下什么新问题？

### 关键里程碑（战略节点，不是每章流水账）
- M1 开局锚定（第1-3章）：让读者"站主角这边"
- M2 第一个小成果（第5-7章）：让读者觉得"有点意思"
- M3 第一次打脸/反转（第10-12章）：让读者"爽到了"
- M4 卷高潮（第20-22章）：让读者"尖叫/转发"
- M5 卷尾钩子（最后一章）：新的悬念，迫不及待下一卷

### 第1章 章节标题
**追读功能**：这章在追读链中承担什么任务？
**核心看点**：一句话，删掉这章读者会错过什么？
**章节钩子**：看完这章，读者最想知道什么？

### 第2章 章节标题
...

（每卷章节数由分卷规划中的"章节数"决定，必须完整列出该卷所有章节。每章只写"追读功能+看点+钩子"三要素，不要写流水账）

3. 卷数由项目规模决定，必须严格按照分卷规划输出
4. 每卷必须有清晰的追读预期链和爽点排布
5. 直接返回 Markdown 文本，不要加 ``` 代码块

""" + _REALITY_AVOIDANCE_RULES


_GENERATE_DETAILED_PROMPT = """请根据以下小说设定和粗纲，生成详细章节细纲（Markdown格式）。

你不是在扩写粗纲。你是在设计"这章怎么让读者爽"。

要求：
1. 输出格式必须是 **Markdown**，不要包含任何 markdown 代码块标记（```）或其他说明文字
2. 每章必须服务于粗纲中的追读预期链，禁止偏离主线的"过渡章节"
3. 每章结构：

### 第X章 [抓眼球标题]

**叙事任务**：这章要完成什么心理效果？（不是"发生了什么"）

**情绪设计**：
- 开头：____（承接上一章钩子，建立情绪基调）
- 中段：____（推进剧情，制造张力或期待）
- 结尾：____（释放或升级，抛出下一章钩子）

**核心看点**：删掉这章，读者会错过什么最精彩的东西？

**场景与动作**（怎么把看点写出来）：
1. ________（开场，建立情境）
2. ________（推进，制造冲突/悬念）
3. ________（转折/高潮，核心看点释放）
4. ________（收尾，抛钩子）

**关键对话**（可选，标志性台词）：
"________"

**章节钩子**：为什么必须点下一章？
→ 不是"悬念"，而是"承诺"——下一章会给读者什么？

**预计字数**：2500字

4. 优先保证当前卷的完整细纲，每章充实具体，不能敷衍
5. 直接返回 Markdown 文本，不要加 ``` 代码块

""" + _REALITY_AVOIDANCE_RULES


@conversation_api.route('/generate-outline', methods=['POST'])
@login_required
def generate_outline():
    """基于设定生成大纲"""
    try:
        data = request.json or {}
        messages = data.get("messages", [])
        settings = data.get("settings", {})
        model = data.get("model", "deepseek-v4-pro")

        if not settings:
            return jsonify({"success": False, "error": "settings 不能为空，请先生成设定"}), 400

        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        actual_model = endpoint.get("model", model)
        temperature = _normalize_temp(actual_model, 0.7)
        logger.info(f"[Conversation] /generate-outline 请求: model={actual_model}")

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        # 构建消息：对话历史 + 设定 + 大纲生成指令
        custom_prompts = data.get("custom_prompts", {})
        outline_prompt = custom_prompts.get("outline", "") or _GENERATE_OUTLINE_PROMPT
        gen_messages = messages.copy()
        gen_messages.append({
            "role": "user",
            "content": f"以下是已确定的小说设定：\n\n{json.dumps(settings, ensure_ascii=False, indent=2)}\n\n{outline_prompt}"
        })

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
            logger.error(f"[Conversation] /generate-outline API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502

        result = resp.json()
        _deduct_by_usage(result, endpoint, actual_model, 'generate-outline')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        logger.info(f"[Conversation] /generate-outline 响应长度: {len(raw_content)} 字符")

        if not raw_content or len(raw_content) < 100:
            logger.warning(f"[Conversation] /generate-outline 返回内容过短: {len(raw_content)} 字符")
            return jsonify({
                "success": False,
                "error": "AI 返回内容异常过短",
                "raw": raw_content[:2000]
            }), 422

        logger.info(f"[Conversation] /generate-outline 成功: {len(raw_content)} 字符")
        return jsonify({
            "success": True,
            "content": raw_content,
            "model": actual_model,
        })

    except Exception as e:
        logger.error(f"[Conversation] /generate-outline 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@conversation_api.route('/generate-detailed', methods=['POST'])
@login_required
def generate_detailed():
    """基于设定+大纲生成细纲"""
    try:
        data = request.json or {}
        messages = data.get("messages", [])
        settings = data.get("settings", {})
        outline = data.get("outline", {})
        model = data.get("model", "deepseek-v4-pro")

        if not settings:
            return jsonify({"success": False, "error": "settings 不能为空"}), 400
        if not outline:
            return jsonify({"success": False, "error": "outline 不能为空，请先生成大纲"}), 400

        endpoint = _resolve_endpoint(model)
        if not endpoint:
            return jsonify({"success": False, "error": f"模型 '{model}' 无可用端点"}), 404
        if not endpoint.get("api_key"):
            return jsonify({"success": False, "error": "API Key 未配置"}), 400

        actual_model = endpoint.get("model", model)
        temperature = _normalize_temp(actual_model, 0.7)
        logger.info(f"[Conversation] /generate-detailed 请求: model={actual_model}")

        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }

        # 构建消息：对话历史 + 设定 + 大纲 + 细纲生成指令
        gen_messages = messages.copy()
        gen_messages.append({
            "role": "user",
            "content": f"以下是已确定的小说设定：\n\n{json.dumps(settings, ensure_ascii=False, indent=2)}\n\n以下是已确定的大纲：\n\n{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n{_GENERATE_DETAILED_PROMPT}"
        })

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
            logger.error(f"[Conversation] /generate-detailed API 错误: {err}")
            return jsonify({"success": False, "error": err}), 502

        result = resp.json()
        _deduct_by_usage(result, endpoint, actual_model, 'generate-detailed')
        choices = result.get("choices") or [{}]
        raw_content = choices[0].get("message", {}).get("content", "") if choices else ""
        logger.info(f"[Conversation] /generate-detailed 响应长度: {len(raw_content)} 字符")

        if not raw_content or len(raw_content) < 100:
            logger.warning(f"[Conversation] /generate-detailed 返回内容过短: {len(raw_content)} 字符")
            return jsonify({
                "success": False,
                "error": "AI 返回内容异常过短",
                "raw": raw_content[:2000]
            }), 422

        logger.info(f"[Conversation] /generate-detailed 成功: {len(raw_content)} 字符")
        return jsonify({
            "success": True,
            "content": raw_content,
            "model": actual_model,
        })

    except Exception as e:
        logger.error(f"[Conversation] /generate-detailed 失败: {e}")
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
    现在直接接收 Markdown 文本保存
    """
    try:
        from pathlib import Path
        import datetime
        
        data = request.json or {}
        title = data.get("title", "未命名项目").strip()
        settings_md = data.get("settings", "")
        outline_md = data.get("outline", "")
        detailed_md = data.get("detailed_outline", "")
        
        if not title:
            return jsonify({"success": False, "error": "书名不能为空"}), 400
        
        username = session.get('username', 'anonymous')
        user_dir = Path("小说项目") / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = _safe_filename(title)
        project_dir = user_dir / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存设定为 Markdown
        settings_file = project_dir / "settings.md"
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(settings_md)
        
        # 2. 保存大纲为 Markdown
        outline_file = project_dir / "outline.md"
        with open(outline_file, 'w', encoding='utf-8') as f:
            f.write(outline_md)
        
        # 3. 保存细纲为 Markdown
        detailed_file = project_dir / "detailed_outline.md"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write(detailed_md)
        
        # 3.5 保存框架为 Markdown（如有）
        framework_md = data.get("framework", "")
        if framework_md:
            framework_file = project_dir / "framework.md"
            with open(framework_file, 'w', encoding='utf-8') as f:
                f.write(framework_md)
        
        # 4. 保存 core-setting.md（兼容旧流程）
        core_file = project_dir / "core-setting.md"
        with open(core_file, 'w', encoding='utf-8') as f:
            f.write(settings_md)
        
        # 5. 从 Markdown 提取 project_info
        project_info = _extract_project_info_from_markdown(settings_md, outline_md)
        info_file = project_dir / "project_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        # 6. 生成 project_config.json
        config_file = project_dir / "project_config.json"
        config = {
            "novel_title": title,
            "proj_name": safe_name,
            "username": username,
            "total_chapters": project_info.get("total_chapters", 0),
            "total_words": project_info.get("total_words", 0),
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
    # 先去掉常见的 Markdown 标题符号、书名号和前后空格
    cleaned = re.sub(r'^[#\s《\[]+', '', name).strip()
    cleaned = re.sub(r'[》\]]+$', '', cleaned).strip()
    # 保留中文、英文、数字，替换非法文件名字符
    safe = re.sub(r'[\\/:*?"<>|#]', '_', cleaned).strip()
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



def _extract_project_info_from_markdown(settings_md: str, outline_md: str = "") -> dict:
    """从 Markdown 设定文本中提取 project_info 所需字段"""
    import re
    import datetime
    
    info = {
        "novel_title": "未命名项目",
        "novel_synopsis": "",
        "novel_description": "",
        "genre": "",
        "sub_genre": "",
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
            "main_category": "都市",
            "sub_category": "都市生活",
            "tags": [],
            "target_audience": "男频",
            "content_rating": "全年龄"
        },
        "generation_metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_chapters": 0,
            "total_words": 0,
            "ai_model": "deepseek-v4",
            "mode_specific": {"info": {"generation_mode": "conversation", "has_outline": bool(outline_md), "has_detailed_outline": False}}
        }
    }
    
    # 提取书名
    book_match = re.search(r'\*\*书名\*\*[\s:：]*[《\[]?([^》\]]+)[》\]]?', settings_md)
    if book_match:
        info["novel_title"] = book_match.group(1).strip()
    else:
        h1_match = re.search(r'^#\s*[《\[]?([^《》]+)[》\]]?', settings_md, re.MULTILINE)
        if h1_match:
            info["novel_title"] = h1_match.group(1).strip()
    
    # 提取一句话简介
    synopsis_match = re.search(r'\*\*一句话简介\*\*[\s:：]*(.+?)(?=\n|$)', settings_md)
    if synopsis_match:
        info["novel_synopsis"] = synopsis_match.group(1).strip()
    
    # 提取番茄风格简介（作为详细简介）
    desc_match = re.search(r'\*\*番茄风格简介\*\*[\s:：]*(.+?)(?=\n#|\n\*\*|$)', settings_md, re.DOTALL)
    if desc_match:
        info["novel_description"] = desc_match.group(1).strip()
    
    # 提取题材
    genre_match = re.search(r'\*\*题材\*\*[\s:：]*(.+?)(?=\n|$)', settings_md)
    if genre_match:
        info["genre"] = genre_match.group(1).strip()
        info["category_tags"]["main_category"] = genre_match.group(1).strip().split('·')[0].strip()
    
    # 提取标签
    tags_match = re.search(r'\*\*标签\*\*[\s:：]*(.+?)(?=\n|$)', settings_md)
    if tags_match:
        tags_text = tags_match.group(1).strip()
        info["category_tags"]["tags"] = [t.strip() for t in tags_text.replace('、', ',').split(',') if t.strip()]
    
    # 统计章节数
    total_chapters = 0
    if outline_md:
        chapters = re.findall(r'###\s*第\s*\d+\s*章', outline_md)
        total_chapters = len(chapters)
    info["generation_metadata"]["total_chapters"] = total_chapters
    info["generation_metadata"]["total_words"] = total_chapters * 3000 if total_chapters > 0 else 0
    
    return info


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

_QUALITY_CHECK_PROMPT = """请作为番茄小说网的资深编辑，对以上小说项目方案进行严格质检。

【目标平台】番茄小说网（免费阅读、算法推荐驱动、下沉市场为主）
【目标读者】碎片化阅读的移动端用户，追求即时情绪释放，前3章留不住就会划走

重点检查以下维度：

## 1. 设定矛盾
- 世界观背景、金手指规则、角色设定是否存在自相矛盾
- 力量体系/经济体系是否自洽

## 2. 毒点排查（番茄读者雷区）
- 主角圣母、降智、双标
- 绿帽、背叛、虐主（让主角长期受辱无反击）——番茄读者零容忍
- 反派过于强大导致长期压抑、无解
- 逻辑硬伤（钱/实力来得太轻易、无代价）
- 后宫关系处理不当（女配脸谱化、无成长）
- 开篇压抑过长、先抑后扬的"抑"超过1章——番茄读者会直接划走

## 3. 爽点密度与节奏（番茄核心指标）
- 前3章是否出现核心爽点或强悬念（番茄算法留存的关键）
- 打脸节奏是否紧凑（建议每3-5章一个小爽点，每卷一个大高潮）
- 期待感构建是否到位（铺垫→爆发→收获，铺垫不宜超过2章）
- 金手指使用是否有新意，还是老套路重复
- 是否存在"长篇大论解释设定"的劝退段落

## 4. 开局与卷节奏
- 开局是否拖沓（第1章前500字必须抓住眼球）
- 第1卷结束前是否有第一个大高潮
- 每章结尾是否有钩子（促使读者点击下一章）

## 5. 番茄市场契合度
- 题材是否符合当前番茄热门趋势（都市脑洞、玄幻脑洞、神豪、种田、奶爸等）
- 书名+简介是否具有点击吸引力（算法推荐场景下的标题竞争力）
- 前三章是否具备"算法推荐友好"的强钩子

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


def _read_volume_outline(project_dir: Path, volume_number: int) -> str:
    """读取指定卷的粗纲（从 outline_vol{N}.md）。
    如果分卷文件不存在，回退到从 outline.md 提取。
    """
    # 1. 优先读分卷粗纲文件
    vol_file = project_dir / f"outline_vol{volume_number}.md"
    if vol_file.exists():
        return vol_file.read_text(encoding='utf-8')
    
    # 2. 回退：从 outline.md 提取该卷粗纲（兼容旧格式）
    for outline_name in ["outline.md", "rough-outline.md"]:
        outline_path = project_dir / outline_name
        if outline_path.exists():
            text = outline_path.read_text(encoding='utf-8')
            return _extract_volume_rough_outline(text, volume_number)
    
    return ""


def _read_volume_detailed(project_dir: Path, volume_number: int):
    """【已废弃】原读取细纲接口，保留兼容。"""
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


def _extract_volume_rough_outline(outline_text: str, volume_number: int) -> str:
    """从 outline.md 中提取某卷的粗纲内容。
    支持两种格式：
    1. 旧格式：## 第N卷 ... ### 第X章
    2. 新格式：--- 分隔后 # 各卷粗纲 / # 第N卷粗纲
    返回该卷的粗纲文本，找不到则返回空字符串。
    """
    import re
    if not outline_text or volume_number < 1:
        return ""
    
    # 模式1：新格式，按 "# 第N卷粗纲" 或 "## 第N卷粗纲" 匹配
    new_patterns = [
        rf'^#+\s*第{volume_number}卷粗纲.*?\n(.*?)(?=^#+\s*第{volume_number + 1}卷粗纲|\Z)',
        rf'^#+\s*第{volume_number}卷.*?\n(.*?)(?=^#+\s*第{volume_number + 1}卷|\Z)',
    ]
    for p in new_patterns:
        m = re.search(p, outline_text, re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
    
    # 模式2：旧格式，按 "## 第N卷" 匹配
    old_patterns = [
        rf'##\s*第{volume_number}卷[：:\s][^\n]*\n(.*?)(?=##\s*第{volume_number + 1}卷|\Z)',
        rf'##\s*第{volume_number}卷\n(.*?)(?=##\s*第|\Z)',
    ]
    for p in old_patterns:
        m = re.search(p, outline_text, re.DOTALL)
        if m:
            return m.group(1).strip()
    
    return ""


def _extract_single_chapter_rough(volume_rough_text: str, chapter_number: int) -> str:
    """从单卷粗纲文本中提取某一章的粗纲内容。
    粗纲格式：### 第X章：标题 ... 下一个 ### 第X+1章
    """
    import re
    if not volume_rough_text or chapter_number < 1:
        return ""
    
    # 匹配该章及后续内容，直到下一章或结束
    # 注意：使用 {{3,4}} 转义 f-string 中的花括号，使其成为正则量词
    pattern = re.compile(
        rf'^(#{{3,4}})\s*第{chapter_number}章[：:\s](.*?)\n(.*?)(?=^\1\s*第\d+章|\Z)',
        re.MULTILINE | re.DOTALL
    )
    m = pattern.search(volume_rough_text)
    if m:
        title = m.group(2).strip()
        content = m.group(3).strip()
        return f"### 第{chapter_number}章：{title}\n{content}"
    
    # 回退：简单匹配 "第X章" 开头行
    lines = volume_rough_text.split('\n')
    start = None
    for i, line in enumerate(lines):
        if re.match(rf'^(#{{3,4}})\s*第{chapter_number}章', line):
            start = i
            break
    if start is not None:
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if re.match(r'^(#{3,4})\s*第\d+章', lines[i]):
                end = i
                break
        return '\n'.join(lines[start:end]).strip()
    
    return ""


def _extract_volume_chapter_plan(outline_text: str, volume_number: int, chapters_per_volume: int = 30) -> tuple:
    """从 outline Markdown 文本中提取某卷的章节规划。
    支持新旧两种格式：
      - 新格式(绝对编号): ### 第X章：标题 [情绪标签]
      - 旧格式(相对编号): - 第X章：标题 — summary
    返回 (章节数, 章节列表文本, 全书起始章, 全书结束章)
    """
    import re
    
    default_start = (volume_number - 1) * chapters_per_volume + 1
    default_end = volume_number * chapters_per_volume
    
    if not outline_text or volume_number < 1:
        return chapters_per_volume, "", default_start, default_end
    
    # 先尝试用新函数提取卷文本
    vol_text = _extract_volume_rough_outline(outline_text, volume_number)
    
    # 如果没找到，回退到旧格式匹配
    if not vol_text:
        old_patterns = [
            rf'##\s*第{volume_number}卷[：:\s][^\n]*\n(.*?)(?=##\s*第{volume_number + 1}卷|\Z)',
            rf'##\s*第{volume_number}卷\n(.*?)(?=##\s*第|\Z)',
        ]
        for p in old_patterns:
            m = re.search(p, outline_text, re.DOTALL)
            if m:
                vol_text = m.group(1)
                break
    
    if not vol_text:
        return chapters_per_volume, "", default_start, default_end
    
    # === 模式A：新格式 — 绝对编号（### 第X章 或 ## 第X章）===
    # 匹配如：### 第1章：雷劫之兆 [主线推进][爽][金手指]
    abs_pattern = r'^#{2,3}\s*第(\d+)章[：:\s]+(.+?)$'
    abs_chapters = re.findall(abs_pattern, vol_text, re.MULTILINE)
    
    if abs_chapters:
        plan_lines = ["【本卷章节规划（按粗纲逐章列表，绝对不可增减）】"]
        ch_numbers = []
        for ch_num_str, ch_title in abs_chapters:
            ch_num = int(ch_num_str)
            ch_numbers.append(ch_num)
            plan_lines.append(f"- 全书第{ch_num}章（必须生成）：{ch_title.strip()}")
        if ch_numbers:
            return len(ch_numbers), "\n".join(plan_lines), min(ch_numbers), max(ch_numbers)
    
    # === 模式B：旧格式 — 相对编号（- 第X章：标题 — summary）===
    rel_pattern = r'^-\s*第(\d+)章[：:\s]+([^—\n]+?)(?:\s*—\s*(.+?))?$'
    rel_chapters = re.findall(rel_pattern, vol_text, re.MULTILINE)
    
    if rel_chapters:
        plan_lines = ["【本卷章节规划（按粗纲逐章列表，绝对不可增减）】"]
        for ch_num_str, ch_title, ch_summary in rel_chapters:
            ch_num = int(ch_num_str)
            g_num = ch_num + (volume_number - 1) * chapters_per_volume
            line = f"- 全书第{g_num}章（必须生成）：{ch_title.strip()}"
            if ch_summary:
                line += f" — {ch_summary.strip()}"
            plan_lines.append(line)
        return len(rel_chapters), "\n".join(plan_lines), default_start, default_end
    
    # === 兜底：从 vol_text 中暴力统计任何 "第X章" 出现 ===
    fallback_nums = re.findall(r'第(\d+)章', vol_text)
    if fallback_nums:
        nums = sorted([int(n) for n in fallback_nums])
        return len(nums), "", nums[0], nums[-1]
    
    return chapters_per_volume, "", default_start, default_end


def _extract_batch_detailed(detailed_text: str, start_chapter: int, end_chapter: int) -> str:
    """从整卷细纲中提取指定批次章节的细纲内容。
    细纲格式：每章以 '### 第X章' 或 '## 第X章' 开头。
    返回提取的细纲文本，找不到则返回空字符串。
    """
    import re
    if not detailed_text:
        return ""
    
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
    
    # 找到所有章节标题位置
    pattern = re.compile(r'^(#{2,3}\s+第)([一二三四五六七八九十百\d]+)(章)', re.MULTILINE)
    matches = list(pattern.finditer(detailed_text))
    
    if not matches:
        return ""
    
    # 构建 (章节号, 起始位置, 结束位置) 列表
    chapters = []
    for i, m in enumerate(matches):
        ch_num = _cn_to_int(m.group(2))
        start_pos = m.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(detailed_text)
        chapters.append((ch_num, start_pos, end_pos))
    
    # 提取指定范围的章节
    result_parts = []
    for ch_num, start_pos, end_pos in chapters:
        if start_chapter <= ch_num <= end_chapter:
            result_parts.append(detailed_text[start_pos:end_pos])
    
    return '\n'.join(result_parts)


def _build_writing_prompt(settings_text: str, volume_rough_outline: str, vol_num: int) -> str:
    """构建初始写作设定 prompt（全局上下文，只传一次）。
    包含核心设定+本卷粗纲+现实规避，作为全卷写作上下文。
    """
    return f"""你是番茄小说顶级签约作家。

【核心设定】
{settings_text}

【本卷粗纲】
{volume_rough_outline}

---

【现实规避铁律】
1. 国名：中国→龙国/华夏，美国→星条国，日本→樱花国
2. 城市：北京→B市/京城，上海→S市/沪市，深圳→S市/深市
3. 机构：省政府→省署/省府，县政府→县衙/县署，公安局→警署
4. 品牌：微信→某社交软件，支付宝→某支付软件，抖音→某短视频平台
5. 货币：人民币→龙币/华夏币；本故事发生在平行时空，所有地名、机构、事件均为虚构"""


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
        
        # 读取本卷粗纲（从 outline_vol{N}.md 读取）
        volume_rough = _read_volume_outline(project_dir, volume_number)
        
        end_chapter = start_chapter + batch_size - 1
        
        # 如果 messages 为空，构建初始设定消息（全局上下文，只传一次）
        if not messages:
            prompt = _build_writing_prompt(files.get('settings', ''), volume_rough, volume_number)
            messages = [{"role": "user", "content": prompt}]
        
        import requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint['api_key']}"
        }
        
        logger.info(f"[Conversation] /generate-batch: project={project_id}, vol={volume_number}, chapters={start_chapter}-{end_chapter}, model={actual_model}")
        
        def _cn_to_int(cn: str) -> int:
            """简单中文数字转阿拉伯数字"""
            if cn.isdigit():
                return int(cn)
            CN_NUMS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000,'万':10000,'亿':100000000}
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
        
        def generate():
            # 对话上下文，从初始设定开始
            req_messages = messages.copy()
            all_chapters_text = ""
            total_prompt_tokens = 0
            
            for ch in range(start_chapter, end_chapter + 1):
                # 提取单章粗纲
                single_rough = _extract_single_chapter_rough(volume_rough, ch)
                if not single_rough:
                    err_msg = f"当前第{volume_number}卷粗纲未覆盖第{ch}章。"
                    logger.warning(f"[Conversation] {err_msg}")
                    yield f"data: {json.dumps({'error': err_msg})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                single_prompt = f"""请生成第{ch}章的正文。

【本章粗纲】
{single_rough}

【本章要求】
- 字数2000字以上
- 以 ### 第{ch}章 [抓眼球标题] 开头
- 口语化、精简化、网文化。少用长句和复杂修辞，多用短句、对话、梗。不要传统文学腔
- 对话占比超过40%，用对话推动剧情，不要大段叙述和心理描写
- 参考番茄的黄金三章写作要求（开局即钩子、情绪快节奏、每章结尾必留悬念）
- 直接输出正文，不要插入分隔线或说明文字
- 禁止输出任何说明文字、总结、分析、字数统计、写作思路、本章完、待续等标记"""
                
                # 当前轮的完整消息
                current_messages = req_messages + [{"role": "user", "content": single_prompt}]
                
                payload = {
                    "model": actual_model,
                    "messages": current_messages,
                    "stream": True,
                }
                if "deepseek" in actual_model.lower():
                    payload["thinking"] = {"type": "enabled"}
                
                try:
                    resp = requests.post(
                        endpoint["api_url"],
                        headers=headers,
                        json=payload,
                        stream=True,
                        timeout=600
                    )
                except Exception as e:
                    yield f"data: {json.dumps({'error': f'第{ch}章请求异常: {str(e)}'})}\n\n"
                    return
                
                if not resp.ok:
                    try:
                        err = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err = resp.text or f"HTTP {resp.status_code}"
                    logger.error(f"[Conversation] 第{ch}章 API 错误: {err}")
                    yield f"data: {json.dumps({'error': f'第{ch}章生成失败: {err}'})}\n\n"
                    return
                
                chapter_text = ""
                try:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        line_text = line.decode('utf-8')
                        if not line_text.startswith('data: '):
                            continue
                        
                        data_content = line_text[6:]
                        if data_content == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_content)
                            choices = chunk.get("choices") or [{}]
                            delta = choices[0].get("delta", {}) if choices else {}
                            content_piece = delta.get("content", "")
                            reasoning_piece = delta.get("reasoning_content", "")
                            if content_piece:
                                chapter_text += content_piece
                                yield f"data: {json.dumps({'content': content_piece})}\n\n"
                            if reasoning_piece:
                                yield f"data: {json.dumps({'reasoning': reasoning_piece})}\n\n"
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
                except Exception as e:
                    logger.error(f"[Conversation] 第{ch}章流式异常: {e}")
                    yield f"data: {json.dumps({'error': f'第{ch}章流式异常: {str(e)}'})}\n\n"
                    return
                
                # 把这章的对话历史追加到上下文
                req_messages.append({"role": "user", "content": single_prompt})
                req_messages.append({"role": "assistant", "content": chapter_text})
                all_chapters_text += chapter_text + "\n\n"
                
                # 累加 prompt token（用于计费）
                total_prompt_tokens += sum(len(m.get("content", "")) for m in current_messages)
                
                logger.info(f"[Conversation] 第{ch}章生成完成，长度: {len(chapter_text)} 字符")
            
            # 所有章节生成完毕
            _save_chapters_from_text(project_dir, all_chapters_text.strip())
            
            # 返回完整对话历史
            yield f"data: {json.dumps({'session_messages': req_messages})}\n\n"
            yield "data: [DONE]\n\n"
            
            # 计费
            _deduct_by_estimate(endpoint, actual_model, " " * total_prompt_tokens, all_chapters_text, 'generate-batch')
        
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
        volume_outline = _read_volume_outline(project_dir, volume_number)
        
        # 读取所有分卷粗纲文件
        outline_volumes = {}
        for vol_file in sorted(project_dir.glob("outline_vol*.md"), key=lambda p: p.name):
            vol_match = re.search(r'vol(\d+)', vol_file.name)
            if vol_match:
                vnum = int(vol_match.group(1))
                outline_volumes[vnum] = vol_file.read_text(encoding='utf-8')
        
        import re as _re
        
        # 统计各卷章节数，提取最大章节号
        chapters_dir = project_dir / "chapters"
        chapter_files = list(chapters_dir.glob("第*.md")) if chapters_dir.exists() else []
        latest_chapter = 0
        for cf in chapter_files:
            m = _re.search(r'第(\d+)章', cf.name)
            if m:
                latest_chapter = max(latest_chapter, int(m.group(1)))
        
        # 读取各章节标题和内容
        chapters_data = {}
        for cf in chapter_files:
            m = _re.search(r'第(\d+)章', cf.name)
            if m:
                ch_num = int(m.group(1))
                try:
                    content = cf.read_text(encoding='utf-8').strip()
                    title_match = _re.search(r'^#\s*第\s*\d+\s*章\s*[：:：]?\s*(.*?)$', content, _re.MULTILINE)
                    title = title_match.group(1).strip() if title_match else f'第{ch_num}章'
                    chapters_data[str(ch_num)] = {
                        "title": title,
                        "content": content
                    }
                except Exception:
                    pass
        
        logger.info(f"[Conversation] /project-files: project={project_id}, vol={volume_number}, latest_chapter={latest_chapter}")
        return jsonify({
            "success": True,
            "settings": files.get('settings', '')[:10000],
            "outline": files.get('outline', '')[:10000],
            "volume_outline": volume_outline,
            "outline_volumes": outline_volumes,
            "chapter_count": len(chapter_files),
            "latest_chapter": latest_chapter,
            "chapters": chapters_data,
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
6. 不要输出任何说明文字、总结、分析

""" + _REALITY_AVOIDANCE_RULES


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

{_REALITY_AVOIDANCE_RULES}

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

【绝对铁律 — 违反即失败】
1. **章节数量铁律**：粗纲中列出了多少章，你就必须输出多少章，一章都不能少，一章都不能多。
2. **严禁合并章节**：不能把两章或多章粗纲合并成一章细纲，必须严格 1:1 对应。
3. **严禁跳过章节**：粗纲中的每一章都必须有对应的细纲，禁止以"与上一章类似"等理由跳过。
4. **章节编号铁律**：必须从第 {global_start} 章开始，连续编号到第 {global_end} 章，中间不能断号、跳号、重号。
5. **如果粗纲有51章，你的输出必须有51章细纲**，这是不可妥协的要求。

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
        
        # 提取本卷粗纲
        outline_text = files.get('outline', '')
        volume_rough = _extract_volume_rough_outline(outline_text, volume_number)
        
        logger.info(f"[Conversation] /volume-outline-context: project={project_id}, vol={volume_number}, has_prev={has_prev}, has_rough={bool(volume_rough)}")
        return jsonify({
            "success": True,
            "settings": files.get('settings', '')[:8000],
            "outline": outline_text[:3000],  # 全书框架/大纲前3000字，供AI了解整体脉络
            "volume_outline": volume_rough[:15000] if volume_rough else "",  # 本卷粗纲（主体）
            "prev_volume_outline": prev_outline[:15000],
            "has_prev": has_prev,
            "has_volume_outline": bool(volume_rough),
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
        
        import re
        
        # 读取上下文
        files = _read_project_files(project_dir)
        settings = files.get('settings', '')
        outline = files.get('outline', '')
        
        # 提取本卷粗纲（新格式：框架+各卷粗纲）
        volume_rough = _extract_volume_rough_outline(outline, volume_number)
        
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
        logger.info(f"[Conversation] /generate-volume-outline-v2: project={project_id}, vol={volume_number}, model={actual_model}, has_rough={bool(volume_rough)}")
        
        # 从全书大纲中提取本卷章节规划（旧格式兼容）
        chapter_count, chapter_plan_text, global_start, global_end = _extract_volume_chapter_plan(
            outline, volume_number
        )
        
        # 构建 prompt
        custom_prompts = data.get("custom_prompts", {})
        if custom_prompts.get("detailed", "").strip():
            outline_prompt = custom_prompts["detailed"] \
                .replace("{volume_number}", str(volume_number)) \
                .replace("{chapter_count}", str(chapter_count)) \
                .replace("{global_start}", str(global_start)) \
                .replace("{global_end}", str(global_end)) \
                .replace("{plan_section}", chapter_plan_text or "") \
                .replace("{_REALITY_AVOIDANCE_RULES}", _REALITY_AVOIDANCE_RULES)
        else:
            outline_prompt = _build_volume_outline_v2_prompt(
                volume_number, chapter_count, global_start, global_end, chapter_plan_text
            )
        
        prompt_parts = [
            f"【核心设定】\n{settings[:5000]}",
        ]
        # 主体：本卷粗纲（如果有）
        if volume_rough:
            prompt_parts.append(f"【本卷粗纲】\n{volume_rough[:8000]}")
        else:
            # fallback：旧格式的全书大纲
            prompt_parts.append(f"【全书大纲】\n{outline[:6000]}")
        # 辅助：全书框架（让AI了解整体脉络，不超1000字）
        framework_hint = outline[:1000] if outline else ""
        if framework_hint:
            prompt_parts.append(f"【全书框架（供参考）】\n{framework_hint}")
        if prev_outline:
            # 只取上一卷最后3章（承上启下），避免全文传递浪费token
            prev_sections = re.split(r'\n(?=##\s*第\d+章|###\s*第\d+章)', prev_outline)
            if len(prev_sections) > 3:
                prev_tail = '\n'.join(prev_sections[-3:])
            else:
                prev_tail = prev_outline
            prompt_parts.append(f"【上一卷结尾（承上）】\n{prev_tail[:2500]}")
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


@conversation_api.route('/custom-prompts', methods=['GET'])
@login_required
def get_custom_prompts():
    project_id = request.args.get("project_id", "").strip()
    if not project_id:
        return jsonify({"success": False, "error": "project_id 不能为空"}), 400
    username = session.get('username', 'anonymous')
    project_dir = Path("小说项目") / username / project_id
    if not project_dir.exists():
        return jsonify({"success": False, "error": "项目不存在"}), 404
    prompts, is_custom = _read_custom_prompts(project_dir)
    return jsonify({"success": True, "prompts": prompts, "is_custom": is_custom})


@conversation_api.route('/custom-prompts', methods=['POST'])
@login_required
def save_custom_prompts():
    data = request.json or {}
    project_id = data.get("project_id", "").strip()
    prompts = data.get("prompts", {})
    if not project_id:
        return jsonify({"success": False, "error": "project_id 不能为空"}), 400
    username = session.get('username', 'anonymous')
    project_dir = Path("小说项目") / username / project_id
    if not project_dir.exists():
        return jsonify({"success": False, "error": "项目不存在"}), 404
    existing, _ = _read_custom_prompts(project_dir)
    for key in ["settings", "outline", "detailed"]:
        if key in prompts and isinstance(prompts[key], str):
            existing[key] = prompts[key]
    _save_custom_prompts(project_dir, existing)
    return jsonify({"success": True})
