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
        from web.utils.path_utils import get_user_short_stories_dir
        
        # 使用短篇作品专用路径（与长篇分离）
        project_path = str(get_user_short_stories_dir(username=username, create=True))
        
        config = ShortStoryConfig(
            mode=StoryMode.CREATIVE,
            title=data.get('title', creative_seed[:20]),
            genre=StoryGenre(data.get('genre', 'revenge_romance')),
            target_word_count=int(data.get('target_word_count', 15000)),
            chapter_count=int(data.get('chapter_count', 8)),
            ending_type=data.get('ending_type', 'open'),
            creative_seed=creative_seed,
            username=username,
            project_path=project_path
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
        from web.utils.path_utils import get_user_novel_dir
        
        # 使用短篇作品专用路径（与长篇分离）
        project_path = str(get_user_short_stories_dir(username=username, create=True))
        
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
            project_path=project_path
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
        username = _get_current_username()
        user_id = _get_current_user_id()
        
        outline = data.get('outline')
        chapters = data.get('chapters', [])
        chapter_num = int(data.get('chapter_num', 0))
        blueprint = data.get('blueprint', {})
        
        if not outline or not chapter_num:
            return jsonify({"error": "缺少 outline 或 chapter_num"}), 400
        
        from src.core.short_story.models import ShortStoryConfig, StoryMode, StoryGenre
        from web.utils.path_utils import get_user_novel_dir
        
        project_path = str(get_user_novel_dir(username=username, create=True))
        
        config_data = data.get('config', {})
        config = ShortStoryConfig(
            mode=StoryMode.CREATIVE,
            title=config_data.get('title', '未命名短篇'),
            genre=StoryGenre(config_data.get('genre', 'revenge_romance')),
            target_word_count=int(config_data.get('target_word_count', 15000)),
            chapter_count=int(config_data.get('chapter_count', 12)),
            username=username,
            project_path=project_path
        )
        
        task_id = task_manager.create_task("regenerate_chapter", {
            "title": config.title,
            "phase": "regenerate_chapter",
            "chapter_num": chapter_num
        })
        
        def run():
            try:
                api_client = _init_api_client_with_deduction(task_id, user_id) if user_id else None
                if not api_client:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                
                config.api_client = api_client
                
                from src.core.short_story import ShortStoryGenerator
                generator = ShortStoryGenerator(config)
                
                # 恢复上下文
                generator.blueprint = blueprint
                generator.result.title = outline.get('title', '')
                generator.result.synopsis = outline.get('synopsis', '')
                
                # 恢复已生成章节的状态
                for ch in chapters:
                    if ch['chapter_number'] < chapter_num:
                        generator.generated_chapters[ch['chapter_number']] = {
                            'content': ch.get('content', ''),
                            'summary': ch.get('content', '')[:200] + '...' if ch.get('content') else ''
                        }
                        # 更新前文摘要
                        generator.prev_summary = ch.get('content', '')[:300] + '...' if ch.get('content') else ''
                
                task_manager.update_task(
                    task_id,
                    status="running",
                    progress=10,
                    current_stage=f"regenerating_chapter_{chapter_num}",
                    message=f"正在重新生成第 {chapter_num} 章..."
                )
                
                # 找到对应章节的blueprint
                chapter_blueprint = None
                for bp in blueprint.get('chapters', []):
                    if bp.get('chapter_number') == chapter_num:
                        chapter_blueprint = bp
                        break
                
                if not chapter_blueprint:
                    chapter_blueprint = {
                        'chapter_number': chapter_num,
                        'purpose': f'第{chapter_num}章',
                        'word_count': 2000
                    }
                
                # 重新生成指定章节
                chapter_content = generator._generate_single_chapter(
                    chapter_number=chapter_num,
                    total_chapters=config.chapter_count,
                    blueprint=chapter_blueprint
                )
                
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="regenerate_completed",
                    message=f"第 {chapter_num} 章重新生成完成",
                    result={
                        "chapter": {
                            "chapter_number": chapter_num,
                            "title": chapter_content.get('title', f'第{chapter_num}章'),
                            "content": chapter_content.get('content', ''),
                            "word_count": chapter_content.get('word_count', 0)
                        }
                    }
                )
                
            except Exception as e:
                logger.error(f"重新生成章节失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"重新生成失败: {str(e)}"
                )
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": f"第 {chapter_num} 章重新生成任务已创建"
        }), 202
        
    except Exception as e:
        logger.error(f"创建重新生成任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ==================== 分阶段生成 API (新) ====================

@short_story_api.route('/outline', methods=['POST'])
def generate_outline():
    """
    第一阶段：生成大纲
    
    输入：创意描述、题材、章节数等
    输出：大纲（书名、简介、章节列表）
    """
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        user_id = _get_current_user_id()
        
        creative_seed = data.get('creative_seed', '').strip()
        if not creative_seed:
            return jsonify({"error": "创意描述不能为空"}), 400
        
        from src.core.short_story.models import ShortStoryConfig, StoryMode, StoryGenre
        from web.utils.path_utils import get_user_novel_dir
        
        project_path = str(get_user_novel_dir(username=username, create=True))
        
        config = ShortStoryConfig(
            mode=StoryMode.CREATIVE,
            title=data.get('title', creative_seed[:20]),
            genre=StoryGenre(data.get('genre', 'revenge_romance')),
            target_word_count=int(data.get('target_word_count', 15000)),
            chapter_count=int(data.get('chapter_count', 12)),
            ending_type=data.get('ending_type', 'open'),
            creative_seed=creative_seed,
            username=username,
            project_path=project_path
        )
        
        task_id = task_manager.create_task("outline", {
            "title": config.title,
            "phase": "outline"
        })
        
        def run():
            try:
                api_client = _init_api_client_with_deduction(task_id, user_id) if user_id else None
                if not api_client:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                
                config.api_client = api_client
                
                # 只生成大纲
                from src.core.short_story import ShortStoryGenerator
                generator = ShortStoryGenerator(config)
                
                task_manager.update_task(
                    task_id,
                    status="running",
                    progress=10,
                    current_stage="outline_generating",
                    message="正在生成大纲..."
                )
                
                # 生成大纲（使用conversation session）
                blueprint = generator._create_blueprint_from_seed()
                
                outline = {
                    "title": blueprint.get('title_candidates', [config.title])[0],
                    "synopsis": blueprint.get('synopsis', ''),
                    "chapters": [
                        {
                            "chapter_number": ch.get('chapter_number', i+1),
                            "title": ch.get('purpose', f"第{i+1}章"),
                            "synopsis": f"{ch.get('crisis_hook', '')} {ch.get('payoff_hook', '')}".strip()
                        }
                        for i, ch in enumerate(blueprint.get('chapters', []))
                    ]
                }
                
                # 保存到任务结果
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="outline_completed",
                    message="大纲生成完成",
                    result={
                        "outline": outline,
                        "blueprint": blueprint,
                        "config": {
                            "title": config.title,
                            "genre": config.genre.value,
                            "chapter_count": config.chapter_count,
                            "target_word_count": config.target_word_count
                        }
                    }
                )
                
            except Exception as e:
                logger.error(f"大纲生成失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"生成失败: {str(e)}"
                )
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "大纲生成任务已创建"
        }), 202
        
    except Exception as e:
        logger.error(f"创建大纲任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/content', methods=['POST'])
def generate_content():
    """
    第二阶段：生成正文
    
    输入：大纲、起始章节
    输出：章节内容
    """
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        user_id = _get_current_user_id()
        
        outline = data.get('outline')
        if not outline:
            return jsonify({"error": "缺少大纲数据"}), 400
        
        from src.core.short_story.models import ShortStoryConfig, StoryMode, StoryGenre
        from web.utils.path_utils import get_user_novel_dir
        
        project_path = str(get_user_novel_dir(username=username, create=True))
        
        config_data = data.get('config', {})
        config = ShortStoryConfig(
            mode=StoryMode.CREATIVE,
            title=config_data.get('title', '未命名短篇'),
            genre=StoryGenre(config_data.get('genre', 'revenge_romance')),
            target_word_count=int(config_data.get('target_word_count', 15000)),
            chapter_count=int(config_data.get('chapter_count', 12)),
            username=username,
            project_path=project_path
        )
        
        task_id = task_manager.create_task("content", {
            "title": config.title,
            "phase": "content"
        })
        
        def run():
            try:
                api_client = _init_api_client_with_deduction(task_id, user_id) if user_id else None
                if not api_client:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                
                config.api_client = api_client
                
                from src.core.short_story import ShortStoryGenerator
                generator = ShortStoryGenerator(config)
                
                # 从outline恢复blueprint
                generator.blueprint = data.get('blueprint', {})
                generator.result.title = outline.get('title', '')
                generator.result.synopsis = outline.get('synopsis', '')
                
                chapters_data = outline.get('chapters', [])
                total = len(chapters_data)
                generated_chapters = []
                
                for i, ch_outline in enumerate(chapters_data):
                    progress = int((i / total) * 100)
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        current_stage=f"chapter_{i+1}",
                        message=f"正在生成第 {i+1}/{total} 章..."
                    )
                    
                    # 逐章生成（使用conversation session保持上下文）
                    chapter_content = generator._generate_single_chapter(
                        chapter_number=ch_outline['chapter_number'],
                        total_chapters=total,
                        blueprint=generator.blueprint.get('chapters', [])[i] if i < len(generator.blueprint.get('chapters', [])) else {}
                    )
                    
                    generated_chapters.append({
                        "chapter_number": ch_outline['chapter_number'],
                        "title": ch_outline.get('title', f"第{ch_outline['chapter_number']}章"),
                        "content": chapter_content.get('content', ''),
                        "word_count": chapter_content.get('word_count', 0)
                    })
                
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="content_completed",
                    message="正文生成完成",
                    result={
                        "chapters": generated_chapters,
                        "outline": outline,
                        "total_word_count": sum(ch['word_count'] for ch in generated_chapters)
                    }
                )
                
            except Exception as e:
                logger.error(f"正文生成失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"生成失败: {str(e)}"
                )
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "正文生成任务已创建"
        }), 202
        
    except Exception as e:
        logger.error(f"创建正文任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/finalize', methods=['POST'])
def finalize_story():
    """
    第三阶段：保存完成
    
    输入：大纲、正文、封面（可选）
    输出：保存到项目
    """
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        
        outline = data.get('outline')
        chapters = data.get('chapters')
        
        if not outline or not chapters:
            return jsonify({"error": "缺少大纲或正文数据"}), 400
        
        # 保存到短篇作品目录
        from web.utils.path_utils import get_user_short_stories_dir
        import json
        
        project_dir = get_user_short_stories_dir(username=username, create=True) / outline.get('title', '未命名短篇')
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存大纲
        with open(project_dir / 'outline.json', 'w', encoding='utf-8') as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        
        # 保存章节
        chapters_dir = project_dir / 'chapters'
        chapters_dir.mkdir(exist_ok=True)
        
        for ch in chapters:
            with open(chapters_dir / f"chapter_{ch['chapter_number']:03d}.json", 'w', encoding='utf-8') as f:
                json.dump(ch, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "保存成功",
            "project_path": str(project_dir),
            "title": outline.get('title'),
            "chapter_count": len(chapters),
            "total_word_count": sum(ch.get('word_count', 0) for ch in chapters)
        })
        
    except Exception as e:
        logger.error(f"保存失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/save-draft', methods=['POST'])
def save_draft():
    """保存草稿"""
    try:
        data = request.get_json() or {}
        username = _get_current_username()
        
        from web.utils.path_utils import get_user_short_stories_dir
        import json
        
        title = data.get('title', '未命名短篇')
        project_dir = get_user_short_stories_dir(username=username, create=True) / title
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存草稿文件
        draft_data = {
            "title": title,
            "outline": data.get('outline'),
            "chapters": data.get('chapters', []),
            "config": data.get('config', {}),
            "cover_image": data.get('cover_image'),
            "saved_at": time.time()
        }
        
        with open(project_dir / 'draft.json', 'w', encoding='utf-8') as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "草稿已保存",
            "project_path": str(project_dir)
        })
        
    except Exception as e:
        logger.error(f"保存草稿失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@short_story_api.route('/load-draft', methods=['GET'])
def load_draft():
    """加载草稿"""
    try:
        username = _get_current_username()
        title = request.args.get('title')
        
        if not title:
            return jsonify({"error": "缺少 title 参数"}), 400
        
        from web.utils.path_utils import get_user_novel_dir
        import json
        
        project_dir = get_user_novel_dir(username=username) / title
        draft_file = project_dir / 'draft.json'
        
        if not draft_file.exists():
            return jsonify({"error": "草稿不存在"}), 404
        
        with open(draft_file, 'r', encoding='utf-8') as f:
            draft_data = json.load(f)
        
        return jsonify({
            "success": True,
            "draft": draft_data
        })
        
    except Exception as e:
        logger.error(f"加载草稿失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def register_short_story_routes(app):
    """注册短篇 API 路由"""
    app.register_blueprint(short_story_api)
    logger.info("✅ short_story_api 番茄短篇 API 已注册")
