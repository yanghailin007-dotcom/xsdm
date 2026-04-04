"""
番茄短篇小说创作 API
支持创意模式和仿写模式
"""

import threading
import time
import logging
from typing import Dict, Optional
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# 创建蓝图
short_story_api = Blueprint('short_story_api', __name__, url_prefix='/api/short-story')


class ShortStoryTaskManager:
    """短篇任务管理器（轻量级内存存储）"""
    
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()
        self._counter = 0
    
    def create_task(self, mode: str, params: Dict) -> str:
        with self.lock:
            self._counter += 1
            task_id = f"ss-{int(time.time())}-{self._counter}"
            self.tasks[task_id] = {
                "task_id": task_id,
                "mode": mode,
                "params": params,
                "status": "pending",
                "progress": 0,
                "current_stage": "initialization",
                "message": "任务创建成功，等待开始...",
                "result": None,
                "error": None,
                "points_consumed": 0.0,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)
                self.tasks[task_id]["updated_at"] = time.time()
    
    def delete_task(self, task_id: str):
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]


# 全局任务管理器
task_manager = ShortStoryTaskManager()


def _get_current_username() -> str:
    """获取当前用户名"""
    try:
        from flask import session
        return session.get('user') or session.get('username') or 'anonymous'
    except:
        return 'anonymous'


def _get_current_user_id() -> Optional[int]:
    """获取当前用户ID"""
    try:
        from flask import session
        return session.get('user_id')
    except:
        return None


def _init_api_client_with_deduction(task_id: str, user_id: int):
    """初始化 APIClient 并设置扣费回调"""
    from src.core.APIClient import APIClient
    from config.config import CONFIG
    from web.models.point_model import point_model
    
    api_client = APIClient(CONFIG)
    
    def _on_api_call_deduct_points(purpose: str, attempt: int = 1, endpoint_name: str = None, discount_rate: int = 100):
        try:
            actual_cost = discount_rate / 100.0
            
            # 检查余额
            user_points = point_model.get_user_points(user_id)
            balance = user_points.get('balance', 0)
            if isinstance(balance, str):
                balance = float(balance)
            elif not isinstance(balance, (int, float)):
                balance = 0
            
            if balance < actual_cost:
                task_manager.update_task(
                    task_id,
                    status="paused_insufficient_points",
                    current_stage="paused",
                    message=f"创造点不足，生成已暂停。当前余额: {balance:.1f}点",
                    error="创造点不足，请充值后继续"
                )
                raise Exception(f"创造点不足: 当前余额 {balance:.1f} 点")
            
            result = point_model.spend_points(
                user_id=user_id,
                amount=actual_cost,
                source='api_call',
                description=f'短篇API调用: {purpose} (端点:{endpoint_name}, 折扣:{discount_rate}%)',
                related_id=task_id
            )
            
            if result['success']:
                task = task_manager.get_task(task_id)
                current_consumed = task.get('points_consumed', 0) if task else 0
                if isinstance(current_consumed, str):
                    current_consumed = float(current_consumed)
                elif not isinstance(current_consumed, (int, float)):
                    current_consumed = 0
                task_manager.update_task(
                    task_id,
                    points_consumed=current_consumed + actual_cost
                )
                logger.info(f"💰 [ShortStory Task {task_id}] 扣费成功: {purpose} (消耗:{actual_cost}点)")
            else:
                raise Exception(f"扣费失败: {result.get('error')}")
        except Exception as e:
            if "创造点不足" in str(e) or "扣费失败" in str(e):
                raise
            logger.error(f"❌ [ShortStory Task {task_id}] 扣费回调出错: {e}")
    
    api_client.set_api_call_callback(_on_api_call_deduct_points)
    return api_client


def _run_generation(task_id: str, config, api_client):
    """后台执行短篇生成"""
    from src.core.short_story import ShortStoryGenerator
    
    def progress_callback(chapter_num: int, total: int, status: str):
        progress = int((chapter_num / total) * 80) if status == "generating" else int((chapter_num / total) * 80) + 5
        task_manager.update_task(
            task_id,
            status="running",
            progress=min(progress, 90),
            current_stage=f"chapter_{chapter_num}",
            message=f"正在生成第 {chapter_num}/{total} 章..."
        )
    
    try:
        task_manager.update_task(
            task_id,
            status="running",
            progress=5,
            current_stage="blueprint",
            message="正在生成短篇蓝图..."
        )
        
        generator = ShortStoryGenerator(config)
        result = generator.generate(progress_callback=progress_callback)
        
        if result.success:
            task_manager.update_task(
                task_id,
                status="completed",
                progress=100,
                current_stage="finished",
                message="短篇生成完成！",
                result={
                    "title": result.title,
                    "synopsis": result.synopsis,
                    "chapters": result.chapters,
                    "total_word_count": result.total_word_count,
                    "api_calls_used": result.api_calls_used,
                    "quality_score": result.quality_score,
                }
            )
        else:
            task_manager.update_task(
                task_id,
                status="failed",
                progress=0,
                current_stage="error",
                message=f"生成失败: {result.error_message}",
                error=result.error_message
            )
    except Exception as e:
        logger.error(f"[ShortStory Task {task_id}] 生成异常: {e}", exc_info=True)
        task_manager.update_task(
            task_id,
            status="failed",
            current_stage="error",
            message=f"生成失败: {str(e)}",
            error=str(e)
        )


@short_story_api.route('/create', methods=['POST'])
def create_short_story():
    """创意模式：创建短篇生成任务"""
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        user_id = _get_current_user_id()
        
        # 参数校验
        creative_seed = data.get('creative_seed', '').strip()
        if not creative_seed:
            return jsonify({"error": "创意种子不能为空"}), 400
        
        from src.core.short_story.models import ShortStoryConfig, StoryMode, StoryGenre
        
        config = ShortStoryConfig(
            mode=StoryMode.CREATIVE,
            title=data.get('title', creative_seed[:20]),
            genre=StoryGenre(data.get('genre', 'revenge_romance')),
            target_word_count=int(data.get('target_word_count', 15000)),
            chapter_count=int(data.get('chapter_count', 8)),
            ending_type=data.get('ending_type', 'open'),
            creative_seed=creative_seed,
            username=username,
            project_path="."
        )
        
        task_id = task_manager.create_task("creative", {
            "title": config.title,
            "genre": config.genre.value,
            "target_word_count": config.target_word_count
        })
        
        # 启动后台线程
        def run():
            api_client = _init_api_client_with_deduction(task_id, user_id) if user_id else None
            if not api_client:
                # 无用户ID时不扣费，仅初始化
                from src.core.APIClient import APIClient
                from config.config import CONFIG
                api_client = APIClient(CONFIG)
            config.api_client = api_client
            _run_generation(task_id, config, api_client)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "短篇创意生成任务已创建",
            "estimated_time": "10-20分钟",
            "estimated_points": config.target_word_count // 3000 * 0.85
        }), 202
        
    except Exception as e:
        logger.error(f"创建短篇创意任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/imitate', methods=['POST'])
def imitate_short_story():
    """仿写模式：创建短篇生成任务"""
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        user_id = _get_current_user_id()
        
        reference_text = data.get('reference_text', '').strip()
        if not reference_text:
            return jsonify({"error": "参考文本不能为空"}), 400
        
        from src.core.short_story.models import ShortStoryConfig, StoryMode, StoryGenre
        
        config = ShortStoryConfig(
            mode=StoryMode.IMITATE,
            title=data.get('title', reference_text[:20]),
            genre=StoryGenre(data.get('genre', 'revenge_romance')),
            target_word_count=int(data.get('target_word_count', 15000)),
            chapter_count=int(data.get('chapter_count', 8)),
            ending_type=data.get('ending_type', 'open'),
            reference_text=reference_text,
            protagonist_replacement=data.get('protagonist_replacement', ''),
            era_replacement=data.get('era_replacement', ''),
            username=username,
            project_path="."
        )
        
        task_id = task_manager.create_task("imitate", {
            "title": config.title,
            "genre": config.genre.value,
            "target_word_count": config.target_word_count
        })
        
        def run():
            api_client = _init_api_client_with_deduction(task_id, user_id) if user_id else None
            if not api_client:
                from src.core.APIClient import APIClient
                from config.config import CONFIG
                api_client = APIClient(CONFIG)
            config.api_client = api_client
            _run_generation(task_id, config, api_client)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "短篇仿写生成任务已创建",
            "estimated_time": "10-20分钟",
            "estimated_points": config.target_word_count // 3000 * 0.85
        }), 202
        
    except Exception as e:
        logger.error(f"创建短篇仿写任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """查询任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    return jsonify({
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task["progress"],
        "current_stage": task["current_stage"],
        "message": task["message"],
        "points_consumed": task.get("points_consumed", 0),
        "error": task.get("error")
    })


@short_story_api.route('/result/<task_id>', methods=['GET'])
def get_task_result(task_id: str):
    """获取任务结果"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    if task["status"] != "completed":
        return jsonify({
            "task_id": task_id,
            "status": task["status"],
            "message": "任务尚未完成"
        }), 202
    
    return jsonify({
        "task_id": task_id,
        "status": "completed",
        "result": task.get("result")
    })


@short_story_api.route('/regenerate-chapter', methods=['POST'])
def regenerate_chapter():
    """重生成指定章节"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        chapter_num = int(data.get('chapter_num', 0))
        
        if not task_id or not chapter_num:
            return jsonify({"error": "缺少 task_id 或 chapter_num"}), 400
        
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        # TODO: 从 checkpoint 恢复并重生成指定章节
        # 当前版本先返回提示
        return jsonify({
            "task_id": task_id,
            "chapter_num": chapter_num,
            "message": "重生成功能将在后续版本开放",
            "status": "not_implemented"
        })
        
    except Exception as e:
        logger.error(f"重生成章节失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def register_short_story_routes(app):
    """注册短篇 API 路由"""
    app.register_blueprint(short_story_api)
    logger.info("✅ short_story_api 番茄短篇 API 已注册")
