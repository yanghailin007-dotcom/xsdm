"""
Creative Planning API - 交互式创意策划会话 API

提供交互式对话能力，让用户与 AI 共同打磨爆款创作方案。
"""

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import Blueprint, request, jsonify, session as flask_session
from functools import wraps

from src.core.session_mode.sessions.creative_planning_session import (
    CreativePlanningSession,
    PlanningMode,
    CreativePlanningState,
)
from src.core.session_mode.sessions.fanfiction_background_session import FanfictionBackgroundSession
from src.utils.logger import get_logger

logger = get_logger("CreativePlanningAPI")

# 内存中的 session 缓存（单进程 Flask 下有效）
creative_planning_sessions: Dict[str, CreativePlanningSession] = {}

# Session 持久化目录
SESSION_DIR = Path("data") / "creative_planning_sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


creative_planning_api = Blueprint("creative_planning_api", __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in flask_session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


def _get_api_client():
    """获取全局 API 客户端"""
    try:
        from flask import current_app
        manager = current_app.config.get('MANAGER')
        if manager and hasattr(manager, "api_client"):
            return manager.api_client
    except Exception as e:
        logger.warning(f"获取 manager api_client 失败: {e}")
    
    # 回退：直接创建
    try:
        from src.core.APIClient import APIClient
        from config.config import CONFIG
        return APIClient(CONFIG)
    except Exception as e:
        logger.error(f"创建 APIClient 失败: {e}")
        return None


def _save_session_state(session_id: str, cps: CreativePlanningSession):
    """将会话状态保存到文件"""
    try:
        state_dict = asdict(cps.state)
        # 移除不可序列化的字段（如果 dataclass 里加了的话，但目前没有）
        file_path = SESSION_DIR / f"{session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存会话状态失败: {e}")


def _load_session_state(session_id: str) -> Optional[CreativePlanningState]:
    """从文件加载会话状态"""
    try:
        file_path = SESSION_DIR / f"{session_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CreativePlanningState(**data)
    except Exception as e:
        logger.warning(f"加载会话状态失败: {e}")
        return None


def _build_novel_data_from_request(data: dict) -> dict:
    """从请求构建 novel_data"""
    title = data.get("title", "")
    synopsis = data.get("synopsis", "")
    core_setting = data.get("core_setting", "")
    core_selling_points = data.get("core_selling_points", "")
    total_chapters = data.get("total_chapters", 200)
    target_platform = data.get("target_platform", "fanqie")
    creative_seed = data.get("creative_seed", {})
    
    if not creative_seed:
        creative_seed = {
            "novelTitle": title,
            "storySynopsis": synopsis,
            "coreSetting": core_setting,
            "coreSellingPoints": core_selling_points if isinstance(core_selling_points, list) else [core_selling_points] if core_selling_points else []
        }
    
    return {
        "novel_title": title,
        "novel_synopsis": synopsis,
        "core_setting": core_setting,
        "core_selling_points": core_selling_points,
        "category": data.get("category", "未分类"),
        "creative_seed": creative_seed,
        "target_platform": target_platform,
        "current_progress": {
            "total_chapters": total_chapters,
            "start_time": datetime.now().isoformat(),
        },
    }


@creative_planning_api.route("/api/creative-planning/start", methods=["POST"])
@login_required
def api_creative_planning_start():
    """启动交互式创意策划会话"""
    try:
        data = request.json or {}
        
        title = data.get("title")
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        api_client = _get_api_client()
        if not api_client:
            return jsonify({"success": False, "error": "API 客户端不可用"}), 500
        
        provider = getattr(api_client, "default_provider", "kimi")
        model_name = None
        if hasattr(api_client, "config"):
            model_name = api_client.config.get("models", {}).get(provider)
        
        novel_data = _build_novel_data_from_request(data)
        
        session_id = str(uuid.uuid4())
        cps = CreativePlanningSession(
            api_client=api_client,
            mode=PlanningMode.INTERACTIVE,
            max_auto_iterations=3,
            context_briefs=[],
            novel_data=novel_data,
            provider=provider,
            model_name=model_name,
            temperature=0.7,
        )
        
        # 执行第一步（创意诊断）
        result = cps.execute_interactive_step()
        
        # 保存到内存和文件
        creative_planning_sessions[session_id] = cps
        _save_session_state(session_id, cps)
        
        logger.info(f"[CreativePlanningAPI] 会话已启动: {session_id}, 状态: {result.get('status')}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "status": result.get("status"),
            "data": result.get("data"),
            "message": result.get("message"),
        })
        
    except Exception as e:
        logger.error(f"启动创意策划会话失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@creative_planning_api.route("/api/creative-planning/step", methods=["POST"])
@login_required
def api_creative_planning_step():
    """执行交互式创意策划的下一步"""
    try:
        data = request.json or {}
        session_id = data.get("session_id")
        user_input = data.get("user_input", "")
        
        if not session_id:
            return jsonify({"success": False, "error": "缺少 session_id"}), 400
        
        cps = creative_planning_sessions.get(session_id)
        
        # 如果内存中没有，尝试从文件恢复（需要重建 api_client）
        if cps is None:
            loaded_state = _load_session_state(session_id)
            if loaded_state is None:
                return jsonify({"success": False, "error": "会话已过期或不存在"}), 404
            
            api_client = _get_api_client()
            if not api_client:
                return jsonify({"success": False, "error": "API 客户端不可用"}), 500
            
            provider = getattr(api_client, "default_provider", "kimi")
            model_name = None
            if hasattr(api_client, "config"):
                model_name = api_client.config.get("models", {}).get(provider)
            
            cps = CreativePlanningSession(
                api_client=api_client,
                mode=PlanningMode.INTERACTIVE,
                max_auto_iterations=3,
                context_briefs=[],
                novel_data=loaded_state.novel_seed,
                provider=provider,
                model_name=model_name,
                temperature=0.7,
            )
            cps.state = loaded_state
            
            # 恢复 fanfiction session 状态（如果有）
            if loaded_state.fanfiction_work_name:
                ffs = FanfictionBackgroundSession(
                    api_client=api_client,
                    work_name=loaded_state.fanfiction_work_name,
                    mode=PlanningMode.INTERACTIVE,
                )
                # 从 cps 的结果中恢复草稿状态
                ffs.current_draft = loaded_state.diagnosis.get("_fanfiction_draft", {})
                ffs.is_locked = loaded_state.fanfiction_background_locked
                ffs.background_brief = loaded_state.fanfiction_background_brief
                cps._fanfiction_session = ffs
            
            creative_planning_sessions[session_id] = cps
        
        result = cps.execute_interactive_step(user_input)
        _save_session_state(session_id, cps)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "status": result.get("status"),
            "data": _sanitize_data(result.get("data")),
            "message": result.get("message"),
            "next_actions": result.get("next_actions", []),
        })
        
    except Exception as e:
        logger.error(f"创意策划步骤执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@creative_planning_api.route("/api/creative-planning/finalize", methods=["POST"])
@login_required
def api_creative_planning_finalize():
    """最终定型并保存结果"""
    try:
        data = request.json or {}
        session_id = data.get("session_id")
        
        if not session_id:
            return jsonify({"success": False, "error": "缺少 session_id"}), 400
        
        cps = creative_planning_sessions.get(session_id)
        if cps is None:
            loaded_state = _load_session_state(session_id)
            if loaded_state is None:
                return jsonify({"success": False, "error": "会话已过期或不存在"}), 404
            
            api_client = _get_api_client()
            provider = getattr(api_client, "default_provider", "kimi")
            model_name = None
            if hasattr(api_client, "config"):
                model_name = api_client.config.get("models", {}).get(provider)
            
            cps = CreativePlanningSession(
                api_client=api_client,
                mode=PlanningMode.INTERACTIVE,
                max_auto_iterations=3,
                context_briefs=[],
                novel_data=loaded_state.novel_seed,
                provider=provider,
                model_name=model_name,
                temperature=0.7,
            )
            cps.state = loaded_state
        
        # 显式触发最终定型
        result = cps.transition_to_finalization()
        
        if result.get("status") != "completed":
            return jsonify({
                "success": False,
                "error": result.get("message", "定型失败"),
                "status": result.get("status"),
            }), 400
        
        final_plan_brief = cps.state.final_plan_brief
        title = cps.state.novel_seed.get("novel_title", "未命名")
        
        # 保存结果到项目目录（供后续生成使用）
        try:
            from web.utils.path_utils import get_user_novel_dir
            project_dir = get_user_novel_dir(create=True)
            safe_title = "".join(c if c.isalnum() or c in "_ -" else "_" for c in title)
            novel_dir = project_dir / safe_title
            novel_dir.mkdir(parents=True, exist_ok=True)
            
            plan_path = novel_dir / "creative_planning_result.json"
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(cps.export_results(), f, ensure_ascii=False, indent=2)
            
            # 同时保存基础 novel_data
            novel_data_path = novel_dir / "novel_data.json"
            novel_data = dict(cps.state.novel_seed)
            novel_data["final_plan_brief"] = final_plan_brief
            with open(novel_data_path, "w", encoding="utf-8") as f:
                json.dump(novel_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"保存项目文件失败: {e}")
        
        # 清理会话
        creative_planning_sessions.pop(session_id, None)
        try:
            (SESSION_DIR / f"{session_id}.json").unlink(missing_ok=True)
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "final_plan_brief": final_plan_brief,
            "title": title,
            "message": "方案已定型",
            "redirect_url": f"/phase-one-setup?from_planning=1&title={title}",
        })
        
    except Exception as e:
        logger.error(f"创意策划定型失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@creative_planning_api.route("/api/creative-planning/state/<session_id>", methods=["GET"])
@login_required
def api_creative_planning_state(session_id: str):
    """获取当前会话状态（用于页面刷新恢复）"""
    try:
        cps = creative_planning_sessions.get(session_id)
        if cps is None:
            loaded_state = _load_session_state(session_id)
            if loaded_state is None:
                return jsonify({"success": False, "error": "会话已过期或不存在"}), 404
            return jsonify({
                "success": True,
                "session_id": session_id,
                "status": loaded_state.current_phase,
                "data": _sanitize_data(asdict(loaded_state)),
            })
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "status": cps.state.current_phase,
            "data": _sanitize_data(asdict(cps.state)),
        })
        
    except Exception as e:
        logger.error(f"获取会话状态失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _sanitize_data(data):
    """清理数据，确保可 JSON 序列化"""
    if data is None:
        return None
    try:
        return json.loads(json.dumps(data, default=str))
    except Exception:
        return {}
