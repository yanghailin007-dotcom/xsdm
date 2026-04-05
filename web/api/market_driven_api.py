# -*- coding: utf-8 -*-
"""
Market Driven Generation API
市场导向生成API

提供市场导向模式的完整流程：
1. 获取可选择的题材列表
2. 分析题材套路
3. 基于套路生成方案
4. 基于套路生成第一阶段产物
5. 批量生成章节
"""

import logging
import json
import threading
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify
from pathlib import Path
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

# 创建蓝图
market_driven_api = Blueprint('market_driven_api', __name__, url_prefix='/api/market-driven')

# 导入服务
try:
    from web.services.market_driven.trope_analyzer import TropeAnalyzer, TropeCache
    from web.services.market_driven.plan_generator import MarketDrivenPlanGenerator
    from web.services.market_driven.phase_one_generator import MarketDrivenPhaseOneGenerator
    from web.services.market_driven.market_driven_conversation import (
        MarketDrivenConversationSession, MarketDrivenConversationManager,
        generate_with_conversation
    )
    from web.services.market_driven.batch_chapter_generator import (
        BatchChapterGenerator, ChapterBluePrintGenerator, generate_300k_words
    )
    from web.services.market_driven.project_manager import (
        UnifiedProjectManager, FanqieUploadAdapter, ProjectDirectoryManager,
        create_unified_project, load_and_prepare_upload
    )
    logger.info("✅ MarketDriven services 导入成功")
except ImportError as e:
    logger.error(f"❌ MarketDriven services 导入失败: {e}")
    TropeAnalyzer = None
    TropeCache = None
    MarketDrivenPlanGenerator = None
    MarketDrivenPhaseOneGenerator = None
    BatchChapterGenerator = None
    ChapterBluePrintGenerator = None
    generate_300k_words = None
    UnifiedProjectManager = None
    FanqieUploadAdapter = None
    ProjectDirectoryManager = None
    create_unified_project = None
    load_and_prepare_upload = None

# 任务管理器（简单内存版）
class MarketGenerationTaskManager:
    """市场导向生成任务管理器"""
    
    def __init__(self):
        self.tasks = {}
    
    def create_task(self, genre: str, user_choices: Dict) -> str:
        """创建新任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "genre": genre,
            "user_choices": user_choices,
            "status": "pending",  # pending, analyzing, generating_plan, generating_products, generating_chapters, completed, failed
            "progress": 0,
            "current_stage": None,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
            self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
    
    def delete_task(self, task_id: str):
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]

# 全局任务管理器
task_manager = MarketGenerationTaskManager()


@market_driven_api.route('/genres', methods=['GET'])
def get_available_genres():
    """
    获取可选择的题材列表（支持自动更新）
    
    Query参数:
        - refresh: 是否强制刷新（传入任意值触发）
    
    响应：
    {
        "genres": [
            {
                "id": "神豪文-花钱返利类",
                "name": "神豪文-花钱返利类",
                "description": "主角获得花钱返利系统...",
                "expected_retention": "12-18%",
                "competition": "激烈",
                "market_status": "稳定"
            }
        ],
        "total": 20,
        "update_status": {
            "last_update": "2026-03-21T10:00:00",
            "days_since_update": 3,
            "next_update_due": false
        }
    }
    """
    try:
        if TropeAnalyzer is None:
            return jsonify({"error": "服务暂不可用"}), 503
        
        # 检查是否强制刷新
        force_refresh = request.args.get('refresh') is not None
        
        # 初始化API客户端（用于自动更新）
        api_client = None
        try:
            from src.core.APIClient import APIClient
            from config.config import CONFIG
            api_client = APIClient(CONFIG)
        except Exception as e:
            logger.warning(f"APIClient初始化失败，将使用缓存: {e}")
        
        # 获取GenreManager
        from web.services.market_driven.genre_manager import get_genre_manager
        genre_manager = get_genre_manager(api_client=api_client)
        
        # 获取类型列表（支持自动更新）
        genres = genre_manager.get_genres(force_refresh=force_refresh)
        
        # 格式化输出
        genre_list = []
        for genre_id, info in genres.items():
            genre_list.append({
                "id": genre_id,
                "name": genre_id,
                **info
            })
        
        # 获取更新状态
        update_status = genre_manager.get_update_status()
        
        return jsonify({
            "genres": genre_list,
            "total": len(genre_list),
            "update_status": {
                "last_update": update_status.get("last_update"),
                "days_since_update": update_status.get("days_since_update"),
                "next_update_due": update_status.get("next_update_due"),
                "base_genres": update_status.get("base_genres"),
                "ai_genres": update_status.get("ai_genres")
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取题材列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/genres/refresh', methods=['POST'])
def refresh_genres():
    """
    手动刷新类型列表（通过AI生成新类型）
    
    响应：
    {
        "success": true,
        "message": "类型列表已刷新",
        "total_genres": 23,
        "new_genres": 3
    }
    """
    try:
        from web.services.market_driven.genre_manager import get_genre_manager
        from src.core.APIClient import APIClient
        from config.config import CONFIG
        
        # 初始化API客户端
        api_client = APIClient(CONFIG)
        genre_manager = get_genre_manager(api_client=api_client)
        
        # 记录刷新前的数量
        before_count = len(genre_manager.get_genres())
        
        # 强制刷新
        genres = genre_manager.get_genres(force_refresh=True)
        after_count = len(genres)
        
        return jsonify({
            "success": True,
            "message": "类型列表已刷新",
            "total_genres": after_count,
            "new_genres": after_count - before_count,
            "genres_added": list(genres.keys())[before_count:] if after_count > before_count else []
        }), 200
        
    except Exception as e:
        logger.error(f"刷新类型列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/analyze-tropes', methods=['POST'])
def analyze_tropes():
    """
    分析指定题材的套路
    
    请求体：
    {
        "genre": "神豪文-花钱返利类",
        "use_cache": true
    }
    
    响应：
    {
        "task_id": "uuid",
        "status": "pending",
        "message": "套路分析任务已创建"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        use_cache = data.get('use_cache', True)
        
        if not genre:
            return jsonify({"error": "缺少必要参数: genre"}), 400
        
        if TropeAnalyzer is None:
            return jsonify({"error": "服务暂不可用"}), 503
        
        # 检查题材是否有效
        available_genres = TropeAnalyzer.get_available_genres()
        if genre not in available_genres:
            return jsonify({
                "error": "无效的题材",
                "available_genres": list(available_genres.keys())
            }), 400
        
        # 创建任务
        task_id = task_manager.create_task(genre, {})
        
        # 🔥 获取当前用户名并保存到任务中（后台线程无法访问session）
        username = _get_current_username()
        task_manager.update_task(task_id, username=username)
        logger.info(f"[Task {task_id}] 创建分析任务，用户名: {username}")
        
        # 在后台执行分析
        def run_analysis():
            try:
                task_manager.update_task(
                    task_id,
                    status="analyzing",
                    progress=10,
                    current_stage="analyzing_tropes",
                    message="正在分析题材套路..."
                )
                
                # 初始化分析器
                from src.core.APIClient import APIClient
                from config.config import CONFIG
                api_client = APIClient(CONFIG)
                analyzer = TropeAnalyzer(api_client=api_client)
                
                # 执行分析
                task_manager.update_task(task_id, progress=30)
                tropes = analyzer.analyze_genre(genre, use_cache=use_cache)
                
                # 更新完成
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="analysis_completed",
                    message="套路分析完成",
                    result={
                        "genre": genre,
                        "tropes": tropes
                    }
                )
                
                logger.info(f"套路分析任务完成: {task_id}")
                
            except Exception as e:
                logger.error(f"套路分析任务失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"分析失败: {str(e)}"
                )
        
        # 启动后台线程
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "套路分析任务已创建并开始运行"
        }), 202
        
    except Exception as e:
        logger.error(f"创建套路分析任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """
    获取任务状态
    
    响应：
    {
        "task_id": "uuid",
        "status": "completed",
        "progress": 100,
        "current_stage": "analysis_completed",
        "result": {...}
    }
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        # 构建响应
        response = {
            "task_id": task["id"],
            "genre": task.get("genre"),
            "status": task["status"],
            "progress": task["progress"],
            "current_stage": task["current_stage"],
            "message": task.get("message", ""),
            "created_at": task["created_at"],
            "updated_at": task["updated_at"]
        }
        
        # 如果完成，包含结果
        if task["status"] == "completed" and task["result"]:
            response["result"] = task["result"]
        
        # 如果失败，包含错误
        if task["status"] == "failed" and task["error"]:
            response["error"] = task["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/generate', methods=['POST'])
def start_market_driven_generation():
    """
    启动市场导向的完整生成流程
    
    请求体：
    {
        "genre": "神豪文-花钱返利类",
        "user_choices": {
            "opening_scenario": "送外卖被宝马男撞",
            "first_face_slap": "4S店买车",
            "protagonist_name": "夏天"
        },
        "target_words": 500000,  // 默认50万字（200章）
        "options": {
            "skip_phase_one": false,
            "generate_chapters": true
        }
    }
    
    响应：
    {
        "task_id": "uuid",
        "status": "pending",
        "message": "市场导向生成任务已创建"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        user_choices = data.get('user_choices', {})
        # 使用配置默认值50万字，如果用户指定则使用用户值
        from web.services.market_driven.config import get_target_words
        target_words = data.get('target_words') or get_target_words(genre)
        options = data.get('options', {})
        
        if not genre:
            return jsonify({"error": "缺少必要参数: genre"}), 400
        
        # 🔥 获取当前用户ID和用户名
        from flask import session
        user_id = session.get('user_id')
        username = _get_current_username()
        
        # 🔥 创造点预估和余额检查
        from web.models.point_model import point_model
        from web.services.market_driven.config import get_config, calculate_batches
        
        total_chapters = target_words // get_config(genre)["words_per_chapter"]
        chapters_per_batch = get_config(genre)["chapters_per_batch"]
        batches = calculate_batches(total_chapters, chapters_per_batch, genre)
        
        # 一阶段固定消耗 + 二阶段按批次消耗
        phase1_cost = point_model.calculate_phase1_cost(total_chapters, 4)['total']
        phase2_cost = batches * point_model.get_config('phase2_chapter_batch', 1)
        estimated_points = phase1_cost + phase2_cost
        
        # 门槛检查：至少要有75点才能开始
        MIN_POINTS_THRESHOLD = 75
        if user_id:
            user_points = point_model.get_user_points(user_id)
            if user_points['balance'] < MIN_POINTS_THRESHOLD:
                return jsonify({
                    "success": False,
                    "error": f"创造点不足，需要至少{MIN_POINTS_THRESHOLD}点才能开始生成，当前余额{user_points['balance']}点",
                    "required": MIN_POINTS_THRESHOLD,
                    "balance": user_points['balance']
                }), 402
            logger.info(f"✅ [MarketDriven] 余额检查通过: {user_points['balance']}点 >= {MIN_POINTS_THRESHOLD}点门槛")
        
        logger.info(f"💰 [MarketDriven] 预估消耗点数: {estimated_points} (一阶段:{phase1_cost}, 二阶段:{phase2_cost})")
        
        # 创建任务
        task_id = task_manager.create_task(genre, user_choices)
        
        # 🔥 保存用户ID、用户名、预估点数和目标字数到任务中（后台线程无法访问session）
        task_manager.update_task(
            task_id,
            username=username,
            user_id=user_id,
            estimated_points=estimated_points,
            points_consumed=0,
            target_words=target_words
        )
        logger.info(f"[Task {task_id}] 创建任务，用户名: {username}, user_id: {user_id}")
        
        # 在后台执行完整生成流程
        def run_full_generation():
            api_client = None
            try:
                # 初始化API客户端
                try:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                    api_client.set_username(username)
                    
                    # 🔥 设置API调用扣费回调
                    if user_id:
                        def _on_api_call_deduct_points(purpose: str, attempt: int, endpoint_name: str = None, discount_rate: int = 100):
                            try:
                                actual_cost = discount_rate / 100.0
                                
                                # 先检查余额是否足够
                                user_points = point_model.get_user_points(user_id)
                                # 🔥 确保 balance 是数字类型
                                balance = user_points.get('balance', 0)
                                if isinstance(balance, str):
                                    try:
                                        balance = float(balance)
                                    except (ValueError, TypeError):
                                        balance = 0
                                elif not isinstance(balance, (int, float)):
                                    balance = 0
                                if balance < actual_cost:
                                    # 点数不足，暂停任务
                                    logger.warning(f"⏸️ [Task {task_id}] 点数不足，暂停生成。当前余额: {balance}, 需要: {actual_cost}")
                                    task_manager.update_task(
                                        task_id,
                                        status="paused_insufficient_points",
                                        current_stage="paused",
                                        message=f"创造点不足，生成已暂停。当前余额: {balance:.1f}点",
                                        error="创造点不足，请充值后继续",
                                        points_needed=actual_cost,
                                        current_balance=balance
                                    )
                                    # 抛出异常中断生成
                                    raise Exception(f"创造点不足: 当前余额 {balance:.1f} 点，需要 {actual_cost} 点")
                                
                                result = point_model.spend_points(
                                    user_id=user_id,
                                    amount=actual_cost,
                                    source='api_call',
                                    description=f'API调用: {purpose} (端点:{endpoint_name}, 折扣:{discount_rate}%)',
                                    related_id=task_id
                                )
                                if result['success']:
                                    task = task_manager.get_task(task_id)
                                    current_consumed = task.get('points_consumed', 0) if task else 0
                                    if isinstance(current_consumed, str):
                                        try:
                                            current_consumed = float(current_consumed)
                                        except (ValueError, TypeError):
                                            current_consumed = 0
                                    elif not isinstance(current_consumed, (int, float)):
                                        current_consumed = 0
                                    task_manager.update_task(
                                        task_id,
                                        points_consumed=current_consumed + actual_cost
                                    )
                                    logger.info(f"💰 [Task {task_id}] API调用扣费成功: {purpose} (消耗:{actual_cost}点, 总计:{current_consumed + actual_cost:.2f})")
                                else:
                                    logger.error(f"❌ [Task {task_id}] API调用扣费失败: {result.get('error')}")
                                    # 扣费失败也暂停
                                    task_manager.update_task(
                                        task_id,
                                        status="paused_insufficient_points",
                                        current_stage="paused",
                                        message=f"扣费失败: {result.get('error')}",
                                        error=result.get('error', '扣费失败')
                                    )
                                    raise Exception(f"扣费失败: {result.get('error')}")
                            except Exception as e:
                                if "创造点不足" in str(e) or "扣费失败" in str(e):
                                    raise  # 重新抛出以便上层捕获
                                logger.error(f"❌ [Task {task_id}] API调用扣费回调出错: {e}")
                        
                        api_client.set_api_call_callback(_on_api_call_deduct_points)
                except Exception as e:
                    logger.warning(f"APIClient初始化失败，将使用模拟模式: {e}")
                
                # 第1阶段：套路分析（传递user_choices以检查是否有前端缓存的分析结果）
                _run_trope_analysis(task_id, genre, api_client, user_choices)
                
                # 第2阶段：方案 + 一阶段产物生成（对话模式）
                if not options.get('skip_phase_one', False):
                    _run_plan_and_products_conversation(task_id, genre, user_choices, api_client)
                
                # 第3阶段：生成章节
                if options.get('generate_chapters', True):
                    _run_chapter_generation(task_id, genre, target_words, api_client)
                
                # 完成
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="generation_completed",
                    message="全部生成完成"
                )
                
            except Exception as e:
                logger.error(f"生成任务失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"生成失败: {str(e)}"
                )
        
        # 启动后台线程
        thread = threading.Thread(target=run_full_generation)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "市场导向生成任务已创建并开始运行",
            "estimated_time": "30-60分钟（取决于字数）",
            "estimated_points": estimated_points
        }), 202
        
    except Exception as e:
        logger.error(f"创建生成任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def _run_trope_analysis(task_id: str, genre: str, api_client=None, user_choices: Dict = None):
    """执行套路分析"""
    task_manager.update_task(
        task_id,
        status="analyzing",
        progress=5,
        current_stage="analyzing_tropes",
        message="正在分析题材套路..."
    )
    
    try:
        # 检查是否有前端传递的分析上下文
        if user_choices and user_choices.get('analysis_context'):
            logger.info(f"[Task {task_id}] 使用前端传递的分析上下文，跳过AI分析")
            tropes = user_choices.get('analysis_context')
            task_manager.update_task(task_id, progress=15)
        else:
            # 初始化分析器
            analyzer = TropeAnalyzer(api_client=api_client)
            
            # 执行分析
            task_manager.update_task(task_id, progress=10)
            tropes = analyzer.analyze_genre(genre)
        
        # 更新任务结果
        task_manager.update_task(
            task_id,
            progress=15,
            result={
                "genre": genre,
                "tropes": tropes
            },
            message="套路分析完成"
        )
        
        logger.info(f"[Task {task_id}] 套路分析完成")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 套路分析失败: {e}")
        raise


def _run_plan_generation(task_id: str, genre: str, user_choices: Dict, api_client=None):
    """
    准备方案生成参数
    注意：实际方案生成将在对话模式中与一阶段产物一起完成
    """
    task_manager.update_task(
        task_id,
        status="preparing_plan",
        progress=20,
        current_stage="preparing_plan",
        message="正在准备生成参数..."
    )
    
    try:
        # 获取套路分析结果
        task = task_manager.get_task(task_id)
        tropes = task.get("result", {}).get("tropes", {})
        
        # 检查前端是否传递了分析上下文
        analysis_context = user_choices.get('analysis_context')
        if not tropes and analysis_context:
            logger.info(f"[Task {task_id}] 使用前端传递的分析上下文")
            tropes = analysis_context
            task_manager.update_task(
                task_id,
                result={"tropes": tropes}
            )
        
        if not tropes:
            # 如果没有缓存的套路，重新分析
            analyzer = TropeAnalyzer(api_client=api_client)
            tropes = analyzer.analyze_genre(genre)
            task_manager.update_task(
                task_id,
                result={"tropes": tropes}
            )
        
        # 🔥 保存用户选择到任务，供后续对话模式使用
        task_manager.update_task(
            task_id,
            user_choices=user_choices,  # 保存用户选择
            progress=30,
            message="准备完成，即将进入对话生成模式..."
        )
        
        logger.info(f"[Task {task_id}] 方案生成参数准备完成，将在对话模式中生成")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 方案准备失败: {e}")
        raise


def _run_plan_and_products_conversation(task_id: str, genre: str, user_choices: Dict, api_client=None):
    """
    使用对话模式生成方案 + 一阶段产物
    在一个连续对话中完成所有生成，保持上下文连贯
    """
    task_manager.update_task(
        task_id,
        status="conversation_mode",
        progress=20,
        current_stage="conversation_mode",
        message="启动AI对话模式，准备生成..."
    )
    
    try:
        # 获取任务数据
        task = task_manager.get_task(task_id)
        tropes = task.get("result", {}).get("tropes", {})
        
        # 🔥 从任务中获取用户名（后台线程无法访问Flask session）
        username = task.get('username') if task else 'anonymous'
        if not username:
            username = 'anonymous'
        logger.info(f"[Task {task_id}] 使用用户名: {username}")
        
        # 🔥 根据字数重新计算正确的章节数（覆盖用户可能错误选择的章节数）
        from web.services.market_driven.config import get_config, get_target_words
        target_words = task.get('target_words') or get_target_words(genre)
        correct_chapters = target_words // get_config(genre)["words_per_chapter"]
        # 确保 correct_chapters 是整数
        if not isinstance(correct_chapters, int):
            correct_chapters = int(correct_chapters)
        
        # 更新用户选择（添加套路信息，并强制使用正确计算的章节数）
        user_chapters = user_choices.get('chapters', 0)
        # 确保 user_chapters 是整数
        if isinstance(user_chapters, str):
            try:
                user_chapters = int(user_chapters)
            except (ValueError, TypeError):
                user_chapters = 0
        elif not isinstance(user_chapters, int):
            user_chapters = int(user_chapters) if user_chapters else 0
        
        enriched_user_choices = {
            **user_choices,
            "chapters": correct_chapters,  # 🔥 强制使用正确计算的章节数
            "target_words": target_words,   # 🔥 添加目标字数
            "trope_analysis": tropes
        }
        if user_chapters != correct_chapters:
            logger.info(f"[Task {task_id}] 章节数已修正: {user_chapters} -> {correct_chapters} (基于{target_words}字)")
        else:
            logger.info(f"[Task {task_id}] 章节数检查: {correct_chapters} 章 (基于{target_words}字)")
        
        logger.info(f"[Task {task_id}] 🚀 启动对话模式生成")
        
        # 进度回调
        def progress_callback(step_name, progress):
            step_messages = {
                "generate_plan": "正在生成完整方案（对话模式）...",
                "generate_worldview": "正在生成世界观...",
                "generate_characters": "正在生成角色设计...",
                "generate_growth_plan": "正在生成成长路线...",
                "generate_emotion_curve": "正在生成情绪曲线..."
            }
            task_manager.update_task(
                task_id,
                progress=progress,
                current_stage=step_name,
                message=step_messages.get(step_name, f"正在执行: {step_name}...")
            )
        
        # 🔥 创建项目目录（提前创建，用于保存每步结果）
        novel_title = enriched_user_choices.get("title") or f"未命名_{task_id[:8]}"
        project_path = create_unified_project(novel_title, "market_driven", genre, username)
        logger.info(f"[Task {task_id}] 项目目录已创建: {project_path}")
        
        # 使用对话会话生成所有产物（每步自动保存）
        products = generate_with_conversation(
            api_client=api_client,
            genre=genre,
            user_choices=enriched_user_choices,
            tropes=tropes,
            progress_callback=progress_callback,
            project_path=str(project_path)
        )
        
        # 提取方案信息
        plan = products.get("plan", {})
        
        # 🔥 结果已在每步生成时自动保存到 project_path
        # 这里只需要更新任务结果
        current_result = task.get("result", {})
        current_result["plan"] = plan
        current_result["products"] = products
        current_result["save_path"] = str(project_path)
        
        task_manager.update_task(
            task_id,
            progress=50,
            result=current_result,
            message="对话模式生成完成"
        )
        
        logger.info(f"[Task {task_id}] ✅ 对话模式生成完成，保存到: {project_path}")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ 对话模式生成失败: {e}")
        import traceback
        logger.error(f"[Task {task_id}] 错误堆栈:\n{traceback.format_exc()}")
        logger.info(f"[Task {task_id}] 🔄 回退到传统模式...")
        
        # 回退到传统模式
        _run_plan_generation(task_id, genre, user_choices, api_client)
        _run_phase_one_products(task_id, genre, api_client)


def _run_phase_one_products(task_id: str, genre: str, api_client=None):
    """
    生成第一阶段产物
    使用对话模式，在一个会话中完成所有生成，保持上下文连贯
    """
    task_manager.update_task(
        task_id,
        status="generating_products",
        progress=35,
        current_stage="generating_products",
        message="正在创建AI对话会话..."
    )
    
    try:
        # 获取套路、方案和用户选择
        task = task_manager.get_task(task_id)
        tropes = task.get("result", {}).get("tropes", {})
        plan = task.get("result", {}).get("plan", {})
        user_choices = task.get("user_choices", {})
        
        # 🔥 从任务中获取用户名（后台线程无法访问Flask session）
        username = task.get('username') if task else 'anonymous'
        if not username:
            username = 'anonymous'
        logger.info(f"[Task {task_id}] 使用用户名: {username}")
        
        # 🔥 使用对话模式生成
        logger.info(f"[Task {task_id}] 启动对话模式生成...")
        
        def progress_callback(step_name, progress):
            """进度回调 - 与UI阶段对应"""
            # 后端步骤 -> 前端UI阶段 映射
            step_to_stage = {
                "generate_plan": "planning",        # 方案生成 -> planning
                "generate_worldview": "worldview",  # 世界观 -> worldview
                "generate_characters": "worldview", # 角色设计 -> worldview（同属世界观阶段）
                "generate_growth_plan": "worldview",# 成长路线 -> worldview
                "generate_emotion_curve": "chapters" # 情绪曲线 -> chapters（准备生成章节）
            }
            step_messages = {
                "generate_plan": "正在生成创作方案...",
                "generate_worldview": "正在生成世界观设定...",
                "generate_characters": "正在生成角色设计...",
                "generate_growth_plan": "正在生成成长路线...",
                "generate_emotion_curve": "正在设计情绪曲线..."
            }
            task_manager.update_task(
                task_id,
                progress=progress,
                current_stage=step_to_stage.get(step_name, "planning"),
                message=step_messages.get(step_name, f"正在执行: {step_name}...")
            )
        
        # 🔥 创建项目目录（提前创建，用于保存每步结果）
        novel_title = user_choices.get("title") or plan.get("recommended_title") or f"未命名_{task_id[:8]}"
        project_path = create_unified_project(novel_title, "market_driven", genre, username)
        logger.info(f"[Task {task_id}] 项目目录已创建: {project_path}")
        
        # 使用对话会话生成所有产物（每步自动保存）
        products = generate_with_conversation(
            api_client=api_client,
            genre=genre,
            user_choices=user_choices,
            tropes=tropes,
            progress_callback=progress_callback,
            project_path=str(project_path)
        )
        
        # 🔥 结果已在每步生成时自动保存到 project_path
        # 这里只需要更新任务结果
        current_result = task.get("result", {})
        current_result["products"] = products
        current_result["save_path"] = str(project_path)
        
        task_manager.update_task(
            task_id,
            progress=50,
            result=current_result,
            message="第一阶段产物生成完成（对话模式）"
        )
        
        logger.info(f"[Task {task_id}] 对话模式生成完成，保存到: {project_path}")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 对话模式生成失败: {e}")
        logger.info(f"[Task {task_id}] 回退到模板模式...")
        
        # 回退到原来的模板模式
        try:
            tropes = task.get("result", {}).get("tropes", {})
            plan = task.get("result", {}).get("plan", {})
            
            generator = MarketDrivenPhaseOneGenerator(api_client=api_client)
            products = generator.generate_all_products(genre, tropes, plan)
            
            # 优先使用用户填写的书名
            user_choices = task.get("user_choices", {})
            novel_title = user_choices.get("title") or plan.get("recommended_title") or f"未命名_{task_id[:8]}"
            save_path = save_phase_one_products(novel_title, products, task_id, genre, plan, user_choices, username)
            
            current_result = task.get("result", {})
            current_result["products"] = products
            current_result["save_path"] = str(save_path)
            
            task_manager.update_task(
                task_id,
                progress=50,
                result=current_result,
                message="第一阶段产物生成完成（模板模式）"
            )
            
            logger.info(f"[Task {task_id}] 模板模式生成完成")
            
        except Exception as e2:
            logger.error(f"[Task {task_id}] 模板模式也失败: {e2}")
            raise


def save_phase_one_products(novel_title: str, products: Dict, task_id: str, 
                            genre: str = "", plan: Dict = None, user_choices: Dict = None,
                            username: str = None) -> Path:
    """保存第一阶段产物到项目目录（使用统一的项目信息管理）"""
    
    # 🔥 获取用户名（优先使用传入的参数，否则从session获取）
    if not username:
        username = _get_current_username()
    logger.info(f"[SaveProducts] 创建项目使用用户名: {username}")
    
    # 使用统一的项目管理创建项目
    project_path = create_unified_project(
        novel_title=novel_title,
        generation_mode="market_driven",
        genre=genre,
        username=username
    )
    
    # 更新项目信息
    project_info = UnifiedProjectManager.load_project_info(project_path)
    
    # 设置基本信息
    project_info["novel_synopsis"] = plan.get("core_selling_points", [{}])[0].get("point", "") if plan else ""
    project_info["genre"] = genre
    
    # 🔥 兼容旧版上传代码：添加 selected_plan 字段（包含完整的 tags）
    # novel_publisher.py 期望从 selected_plan.tags 读取标签信息
    # tags 需要包含: target_audience, main_category, themes, roles, plots
    
    # 从 genre 提取基础类型（如 "国运文-直播类" -> "国运文"）
    base_genre = genre.split("-")[0] if "-" in genre else genre
    
    # 从 CATEGORY_MAPPING 获取分类信息
    from web.services.market_driven.project_manager import FanqieUploadAdapter
    category_mapping = FanqieUploadAdapter.CATEGORY_MAPPING.get(base_genre, {
        "main": "都市",
        "sub": "都市生活", 
        "tags": ["爽文", "系统"]
    })
    
    # 构建完整的 tags 信息（符合 novel_publisher.py 期望）
    tags_info = {
        "target_audience": "男频",  # 默认男频，可根据 genre 调整
        "main_category": category_mapping["main"],
        "sub_category": category_mapping["sub"],
        "themes": category_mapping["tags"][:3] if len(category_mapping["tags"]) >= 3 else category_mapping["tags"] + ["爽文", "系统"],
        "roles": ["主角", "反派", "队友"],  # 默认角色标签
        "plots": ["装逼", "打脸", "升级"]  # 默认情节标签
    }
    
    # 根据 genre 调整受众和标签
    if "奶爸" in genre or "萌宝" in genre:
        tags_info["target_audience"] = "女频"
        tags_info["roles"] = ["奶爸", "萌宝", "妈妈"]
        tags_info["plots"] = ["温馨", "搞笑", "日常"]
    elif "国运" in genre:
        tags_info["plots"] = ["国运", "直播", "震惊", "装逼"]
    elif "神豪" in genre:
        tags_info["plots"] = ["神豪", "花钱", "装逼", "打脸"]
    elif "末日" in genre or "求生" in genre:
        tags_info["plots"] = ["末日", "囤货", "求生", "爽文"]
    
    # 🔥 优先使用AI生成的专业上传数据（步骤1B生成）
    fanqie_data = products.get("fanqie_upload_data", {})
    
    if fanqie_data and fanqie_data.get("title"):
        # 使用AI生成的专业数据
        selected_plan = {
            "title": fanqie_data["title"],
            "synopsis": fanqie_data["synopsis"],
            "tags": fanqie_data["tags"],
            "suggestions": {
                "name": user_choices.get("protagonist_name", "主角") if user_choices else "主角",
                "genre": genre
            }
        }
        project_info["selected_plan"] = selected_plan
        project_info["novel_info"] = {
            "title": fanqie_data["title"],
            "synopsis": fanqie_data["synopsis"],
            "selected_plan": selected_plan,
            "category": fanqie_data.get("tags", {}).get("main_category", "")
        }
        logger.info(f"[SaveProducts] 使用AI生成的专业上传数据: {fanqie_data['title']}")
    else:
        # 备用方案：从 plan 提取 + 使用默认标签
        plan_title = plan.get("title", novel_title) if plan else novel_title
        
        # 生成简介
        if plan:
            synopsis_parts = []
            gf = plan.get("golden_finger", {})
            if gf.get("initial"):
                synopsis_parts.append(f"金手指：{gf['initial']}")
            protagonist = plan.get("protagonist", {})
            if protagonist.get("traits"):
                synopsis_parts.append(f"主角：{', '.join(protagonist['traits'][:3])}")
            synopsis = "；".join(synopsis_parts) if synopsis_parts else f"一本精彩的{genre}小说"
        else:
            synopsis = ""
        
        selected_plan = {
            "title": plan_title,
            "synopsis": synopsis,
            "tags": tags_info,
            "suggestions": {
                "name": user_choices.get("protagonist_name", "主角") if user_choices else "主角",
                "genre": genre
            }
        }
        project_info["selected_plan"] = selected_plan
        project_info["novel_info"] = {
            "title": plan_title,
            "synopsis": synopsis,
            "selected_plan": selected_plan,
            "category": tags_info.get("main_category", "")
        }
        logger.info(f"[SaveProducts] 使用备用方案: {plan_title}")
    
    # 🔥 统一格式：保存兼容的 "{novel_title}_项目信息.json" 和 project_config.json
    safe_title = novel_title.replace('《', '').replace('》', '').replace('/', '_').replace('\\', '_')
    legacy_info_path = project_path / f"{safe_title}_项目信息.json"
    legacy_data = {
        "novel_info": project_info["novel_info"],
        "market_analysis": project_info.get("market_analysis", {}),
        "character_design": project_info.get("character_design", {}),
        "core_worldview": project_info.get("core_worldview", {}),
        "progress": {
            "completed_chapters": 0,
            "total_chapters": len(project_info.get("chapters_index", [])),
            "stage": "未开始"
        }
    }
    try:
        with open(legacy_info_path, 'w', encoding='utf-8') as f:
            json.dump(legacy_data, f, ensure_ascii=False, indent=2)
        logger.info(f"[SaveProducts] 已保存兼容格式项目信息: {legacy_info_path}")
    except Exception as e:
        logger.warning(f"[SaveProducts] 保存兼容项目信息失败: {e}")
    
    config_path = project_path / "project_config.json"
    config_data = {
        "title": novel_title,
        "fanqie_upload_data": {
            "title": project_info["novel_info"]["title"],
            "synopsis": project_info["novel_info"]["synopsis"],
            "tags": project_info["selected_plan"]["tags"]
        },
        "project_name": novel_title,
        "username": project_info.get("created_by", "")
    }
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        logger.info(f"[SaveProducts] 已保存桌面系统配置: {config_path}")
    except Exception as e:
        logger.warning(f"[SaveProducts] 保存桌面配置失败: {e}")
    
    # 设置模式特定信息（包含用户选择）
    mode_info = {
        "task_id": task_id,
        "tropes_analysis": products.get("based_on_tropes", {}),
        "plan": plan
    }
    
    # 🔥 保存用户选择（包括剧情路线）
    if user_choices:
        mode_info["user_choices"] = {
            "title": user_choices.get("title"),
            "protagonist_name": user_choices.get("protagonist_name"),
            "protagonist_identity": user_choices.get("protagonist_identity"),
            "selected_plot": user_choices.get("selected_plot"),  # 用户选择的剧情路线
            "golden_finger_desc": user_choices.get("golden_finger_desc"),
            "main_plot": user_choices.get("main_plot"),
            "first_climax": user_choices.get("first_climax")
        }
    
    UnifiedProjectManager.set_mode_specific_info(
        project_info,
        "market_driven",
        mode_info
    )
    
    # 保存产物
    for product_name in products:
        if product_name in ["writing_style_guide", "market_analysis", "core_worldview",
                           "faction_system", "character_design", "global_growth_plan",
                           "stage_writing_plans", "emotional_blueprint", "expectation_mapping",
                           "plan",           # 完整方案（标题确认、开局设计、金手指细化、主角人设、前30章大纲）
                           "emotion_curve"]: # 详细情绪曲线（每章设计）
            file_path = ProjectDirectoryManager.get_product_path(project_path, product_name)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(products[product_name], f, ensure_ascii=False, indent=2)
    
    # 保存项目信息
    UnifiedProjectManager.save_project_info(project_path, project_info)
    
    return project_path


def _find_project_path(novel_title: str, username: str = None) -> Optional[Path]:
    """
    查找项目路径（支持用户子目录）
    
    Args:
        novel_title: 小说标题
        username: 用户名（如果提供，优先在该用户目录下查找）
    
    搜索顺序：
    1. 指定用户目录下: 小说项目/{username}/{novel_title}
    2. 当前session用户目录下: 小说项目/{session_user}/{novel_title}
    3. 根目录下: 小说项目/{novel_title}
    4. 所有用户目录下（遍历）
    
    Returns:
        项目路径，如果未找到则返回 None
    """
    base_dir = Path("小说项目")
    
    # 1. 如果提供了username，优先尝试该用户目录
    if username and username != 'anonymous':
        user_project_path = base_dir / username / novel_title
        if user_project_path.exists():
            return user_project_path
    
    # 2. 尝试当前session用户目录（如果在主线程中）
    try:
        from flask import session
        session_username = session.get('user') or session.get('username') or 'anonymous'
        if session_username != 'anonymous':
            user_project_path = base_dir / session_username / novel_title
            if user_project_path.exists():
                return user_project_path
    except:
        pass
    
    # 3. 尝试根目录（兼容旧版）
    root_project_path = base_dir / novel_title
    if root_project_path.exists():
        return root_project_path
    
    # 4. 遍历所有用户目录
    if base_dir.exists():
        for user_dir in base_dir.iterdir():
            if user_dir.is_dir() and not user_dir.name.startswith('.'):
                project_path = user_dir / novel_title
                if project_path.exists():
                    return project_path
    
    return None


def _get_current_username() -> str:
    """获取当前用户名"""
    try:
        from flask import session
        return session.get('user') or session.get('username') or 'anonymous'
    except:
        return 'anonymous'


def _run_chapter_generation(task_id: str, genre: str, target_words: int, api_client=None):
    """生成章节（使用分层规划架构）"""
    # 使用新的配置
    from web.services.market_driven.config import get_config, calculate_batches
    config = get_config(genre)
    
    total_chapters = target_words // config["words_per_chapter"]
    chapters_per_batch = config["chapters_per_batch"]
    batches = calculate_batches(total_chapters, chapters_per_batch, genre)
    
    task_manager.update_task(
        task_id,
        status="generating_chapters",
        progress=55,
        current_stage="generating_chapters",
        message=f"开始生成章节，目标{total_chapters}章约{target_words}字，分{batches}批..."
    )
    
    try:
        # 获取任务数据
        task = task_manager.get_task(task_id)
        user_choices = task.get("user_choices", {})
        novel_title = user_choices.get("title") or task.get("result", {}).get("plan", {}).get("recommended_title") or f"未命名_{task_id[:8]}"
        tropes = task.get("result", {}).get("tropes", {})
        plan = task.get("result", {}).get("plan", {})
        products = task.get("result", {}).get("products", {})
        
        # 🔥 获取用户名
        username = task.get('username') or 'anonymous'
        logger.info(f"[ChapterGen] 使用用户名: {username}")
        
        # 🔥 初始化分层规划器
        from web.services.market_driven.hierarchical_planner import HierarchicalPlanner
        
        # 获取项目路径
        save_path = task.get("result", {}).get("save_path")
        if save_path:
            project_path = Path(save_path)
            logger.info(f"[ChapterGen] 从任务结果获取项目路径: {project_path}")
        else:
            project_path = _find_project_path(novel_title, username)
            logger.info(f"[ChapterGen] 通过查找获取项目路径: {project_path}")
        
        # 🔥 如果项目路径不存在，创建它
        if not project_path:
            logger.warning(f"[ChapterGen] 项目路径不存在，尝试创建...")
            from web.services.market_driven.project_manager import create_unified_project
            project_path = create_unified_project(
                novel_title=novel_title,
                generation_mode="market_driven",
                genre=genre,
                username=username
            )
            logger.info(f"[ChapterGen] 创建新项目路径: {project_path}")
        
        # 🔥 创建规划器并初始化战略框架
        # 传递一阶段产物（情绪曲线和爆款分析），确保二阶段战术规划符合爆款设计
        emotion_curve = products.get("emotion_curve", [])
        bestseller_analysis = products.get("bestseller_analysis", {}) or task.get("result", {}).get("bestseller_analysis", {})
        
        planner = HierarchicalPlanner(
            genre=genre,
            novel_title=novel_title,
            protagonist_name=user_choices.get('protagonist_name', '主角'),
            api_client=api_client,
            project_path=project_path,
            total_chapters=total_chapters,
            target_words=target_words,
            emotion_curve=emotion_curve,           # 传入一阶段情绪曲线
            bestseller_analysis=bestseller_analysis # 传入爆款分析数据
        )
        
        # 🔥 修复：构造已有的一阶段产物，避免重复调用 WorldBuilder
        # 对话模式已经生成了世界观和阶段目标，直接传入使用
        existing_world_setting = {
            "genre": genre,
            "novel_title": novel_title,
            "protagonist_name": user_choices.get('protagonist_name', '主角'),
            "total_chapters": total_chapters,
            "target_words": target_words,
            "world_setting": products.get("core_worldview", {}),
            "characters": products.get("character_design", {}),
            "stage_goals": products.get("stage_goals", []),
            # 其他一阶段产物也包含进来
            "emotion_curve": products.get("emotion_curve", {}),
            "plan": products.get("plan", {}),
        }
        
        # 如果有阶段目标，直接使用；否则才调用 WorldBuilder
        if existing_world_setting["stage_goals"]:
            logger.info(f"[ChapterGen] 检测到一阶段产物已有 {len(existing_world_setting['stage_goals'])} 个阶段目标，跳过 WorldBuilder 调用")
        else:
            logger.info(f"[ChapterGen] 一阶段产物无阶段目标，将调用 WorldBuilder 生成")
            existing_world_setting = None  # 让 initialize() 调用 WorldBuilder
        
        planner.initialize(existing_world_setting=existing_world_setting)
        
        logger.info(f"[ChapterGen] 分层规划器初始化完成，战略框架已创建，项目路径: {project_path}")
        
        # 准备novel_data
        novel_data = {
            "title": novel_title,
            "username": username,
            "_username": username,
            "core_worldview": products.get("core_worldview", {}),
            "character_design": products.get("character_design", {}),
            "faction_system": products.get("faction_system", {}),
            "plan": products.get("plan", {}),
            "emotion_curve": products.get("emotion_curve", {}),
            "user_choices": user_choices
        }
        
        # 创建批次生成器
        logger.info(f"[ChapterGen] 创建BatchChapterGenerator，project_path: {project_path}")
        batch_gen = BatchChapterGenerator(
            api_client=api_client,
            project_path=str(project_path) if project_path else None
        )
        
        all_results = []
        
        # 🔥 跨批次状态：保存前一章的摘要/钩子，确保批次间衔接
        prev_chapter_summary = ""
        last_chapter_hook = ""
        
        for batch_num in range(1, batches + 1):
            # 🔥 使用分层规划获取当前批次的战术规划
            tactical_plan, strategic_context = planner.get_next_batch_plan(chapters_per_batch)
            
            start = (batch_num - 1) * chapters_per_batch + 1
            end = min(batch_num * chapters_per_batch, total_chapters)
            
            # 🔥 如果是第2批及以后，将前一章的摘要/钩子注入到第一章的规划中
            if batch_num > 1 and (prev_chapter_summary or last_chapter_hook):
                chapters_plan = tactical_plan.get('chapters', [])
                if chapters_plan and len(chapters_plan) > 0:
                    first_chapter_plan = chapters_plan[0]
                    if prev_chapter_summary:
                        first_chapter_plan['prev_chapter_summary'] = prev_chapter_summary
                    if last_chapter_hook:
                        first_chapter_plan['hook_from_previous_batch'] = last_chapter_hook
                    logger.info(f"[Task {task_id}] 第{batch_num}批第1章已注入前一批次钩子: {last_chapter_hook[:100]}...")
            
            # 获取当前阶段信息
            current_stage = strategic_context.get("current_stage", {})
            next_milestone = strategic_context.get("next_milestone", {})
            
            progress_msg = f"正在生成第{batch_num}/{batches}批（第{start}-{end}章）"
            if current_stage:
                progress_msg += f" - {current_stage.get('title', '')}"
            if next_milestone:
                progress_msg += f"，距离下一个里程碑（第{next_milestone.get('chapter')}章）还有{next_milestone.get('chapter', 0) - end}章"
            
            task_manager.update_task(
                task_id,
                progress=int(55 + (batch_num / batches) * 35),
                message=progress_msg
            )
            
            logger.info(f"[Task {task_id}] 第{batch_num}批战术规划: {tactical_plan['batch_info']}")
            
            # 🔥 将战术规划合并到novel_data中
            novel_data_with_plan = {
                **novel_data,
                "tactical_plan": tactical_plan,  # 当前批次的详细规划
                "strategic_context": strategic_context  # 战略上下文
            }
            
            # 生成本批
            result = batch_gen.generate_batch(
                novel_title=novel_title,
                start_chapter=start,
                end_chapter=end,
                blueprint=tactical_plan,  # 使用战术规划替代旧blueprint
                tropes=tropes,
                novel_data=novel_data_with_plan
            )
            
            # 🔥 更新规划器进度
            planner.update_progress(result.get("generated", []))
            
            # 🔥 提取本批次最后一章的摘要和钩子，用于下一批次衔接
            generated_chapters = result.get('generated', [])
            if generated_chapters:
                last_chapter = generated_chapters[-1]
                # 获取最后300字作为摘要
                content = last_chapter.get('content', '')
                if content:
                    prev_chapter_summary = content[-300:] if len(content) > 300 else content
                    # 提取最后一段作为钩子
                    paragraphs = content.strip().split('\n')
                    last_chapter_hook = paragraphs[-1] if paragraphs else ""
                    logger.info(f"[Task {task_id}] 第{batch_num}批最后一章（第{last_chapter.get('chapter')}章）钩子已提取: {last_chapter_hook[:100]}...")
            
            all_results.append(result)
            
            logger.info(f"[Task {task_id}] 第{batch_num}批完成: {len(result['generated'])}章")
        
        # 汇总结果
        total_generated = sum(len(r["generated"]) for r in all_results)
        total_words = sum(r["total_words"] for r in all_results)
        total_failed = sum(len(r["failed"]) for r in all_results)
        # 🔥 确保 avg_quality 是数字
        def _to_float(val, default=0.0):
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default
            return default
        avg_quality = sum(_to_float(r.get("avg_quality", 0)) for r in all_results) / len(all_results) if all_results else 0
        
        # 更新任务结果
        current_result = task.get("result", {})
        current_result["chapter_generation"] = {
            "total_chapters": total_generated,
            "total_words": total_words,
            "failed_chapters": total_failed,
            "avg_quality": avg_quality
        }
        
        task_manager.update_task(
            task_id,
            progress=95,
            result=current_result,
            message=f"章节生成完成: {total_generated}章, {total_words}字, 平均质量{avg_quality:.1f}"
        )
        
        logger.info(f"[Task {task_id}] 章节生成完成: {total_generated}章, {total_words}字")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 章节生成失败: {e}")
        raise


@market_driven_api.route('/prepare-upload/<novel_title>', methods=['GET'])
def prepare_upload(novel_title: str):
    """
    准备番茄上传数据
    
    响应：
    {
        "upload_data": {...},  # 番茄上传所需的完整数据
        "project_info": {...}  # 项目信息
    }
    """
    try:
        if UnifiedProjectManager is None:
            return jsonify({"error": "服务暂不可用"}), 503
        
        # 🔥 加载项目（支持用户子目录）
        base_path = _find_project_path(novel_title)
        if not base_path:
            return jsonify({"error": "项目不存在"}), 404
        
        project_info = UnifiedProjectManager.load_project_info(base_path)
        
        if not project_info:
            return jsonify({"error": "项目信息损坏"}), 404
        
        # 准备上传数据
        upload_data = UnifiedProjectManager.get_upload_data(project_info)
        
        # 加载章节内容
        chapters_content = []
        for ch_entry in project_info.get("chapters_index", []):
            chapter_path = base_path / ch_entry.get("file", "")
            if chapter_path.exists():
                try:
                    with open(chapter_path, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                        chapters_content.append({
                            "chapter_number": chapter_data.get("chapter_number"),
                            "title": chapter_data.get("title"),
                            "content": chapter_data.get("content", "")
                        })
                except Exception as e:
                    logger.warning(f"加载章节失败: {chapter_path}, {e}")
        
        # 使用适配器准备完整上传数据
        full_upload_data = FanqieUploadAdapter.prepare_upload_payload(
            project_info, 
            chapters_content
        )
        
        return jsonify({
            "upload_data": full_upload_data,
            "project_info": {
                "novel_title": project_info["novel_title"],
                "total_chapters": project_info["generation_metadata"]["total_chapters"],
                "total_words": project_info["generation_metadata"]["total_words"],
                "generation_mode": project_info["generation_mode"]
            }
        }), 200
        
    except Exception as e:
        logger.error(f"准备上传数据失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/admin/genres/status', methods=['GET'])
def get_genre_scheduler_status():
    """
    获取题材自动更新调度器状态（管理员接口）
    
    响应：
    {
        "scheduler_active": true,
        "is_running": false,
        "total_genres": 20,
        "base_genres": 20,
        "ai_genres": 0,
        "last_update": "2026-03-21T10:00:00",
        "days_since_update": 3,
        "next_scheduled_update": "2026-03-28T02:00:00"
    }
    """
    try:
        # 始终返回GenreManager的基本状态
        from web.services.market_driven.genre_manager import get_genre_manager
        genre_manager = get_genre_manager()
        status = genre_manager.get_update_status()
        
        # 尝试获取调度器状态
        try:
            from web.services.market_driven.genre_scheduler import get_genre_scheduler
            scheduler = get_genre_scheduler()
            if scheduler:
                scheduler_status = scheduler.get_status()
                return jsonify(scheduler_status), 200
        except:
            pass
        
        # 调度器未初始化，返回基本状态
        return jsonify({
            "scheduler_active": False,
            "scheduler_note": "调度器将在服务器启动时初始化",
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/admin/genres/trigger-update', methods=['POST'])
def trigger_genre_update():
    """
    手动触发题材更新（管理员接口）
    
    响应：
    {
        "success": true,
        "message": "题材更新完成",
        "status": "completed"
    }
    """
    try:
        from web.services.market_driven.genre_scheduler import get_genre_scheduler
        
        scheduler = get_genre_scheduler()
        if scheduler is None:
            return jsonify({
                "success": False,
                "error": "调度器未初始化"
            }), 503
        
        # 在后台线程执行更新，避免阻塞请求
        import threading
        
        result_container = {}
        
        def do_update():
            result_container['result'] = scheduler.trigger_manual_update()
        
        thread = threading.Thread(target=do_update)
        thread.start()
        thread.join(timeout=60)  # 最多等待60秒
        
        if thread.is_alive():
            return jsonify({
                "success": True,
                "message": "更新任务已启动，将在后台执行",
                "status": "started"
            }), 202
        
        result = result_container.get('result', {
            "success": False,
            "message": "更新未返回结果"
        })
        
        status_code = 200 if result.get('success') else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"手动触发更新失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/admin/genres/logs', methods=['GET'])
def get_genre_update_logs():
    """
    获取题材更新历史日志（管理员接口）
    
    Query参数:
        - month: 月份 (格式: YYYYMM, 默认当前月)
        - limit: 返回条数 (默认50)
    
    响应：
    {
        "logs": [
            {
                "timestamp": "2026-03-21T10:00:00",
                "old_count": 20,
                "new_count": 23,
                "added": 3,
                "new_genres": ["类型A", "类型B", "类型C"]
            }
        ]
    }
    """
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        month = request.args.get('month', datetime.now().strftime('%Y%m'))
        limit = request.args.get('limit', 50, type=int)
        
        log_file = Path(f"logs/genre_updates/update_{month}.jsonl")
        
        logs = []
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except:
                            pass
        
        # 按时间倒序，限制条数
        logs = list(reversed(logs))[:limit]
        
        return jsonify({
            "logs": logs,
            "total": len(logs),
            "month": month
        }), 200
        
    except Exception as e:
        logger.error(f"获取更新日志失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ==================== AI 市场化评估 API ====================

@market_driven_api.route('/evaluate', methods=['POST'])
def evaluate_creative():
    """
    AI市场化评估 - 在生成最终方案前评估创意
    
    请求体：
    {
        "genre": "国运文-直播类",
        "dialog_history": [
            {"role": "ai", "content": "想在哪个角度做出不同？"},
            {"role": "user", "content": "主角性格 + 金手指"},
            {"role": "ai", "content": "主角性格类型？"},
            {"role": "user", "content": "话痨吐槽型"},
            {"role": "ai", "content": "金手指设定？"},
            {"role": "user", "content": "记忆消失代价"}
        ],
        "creative_draft": {
            "title": "存在感归零后，我成了幕后黑手",
            "protagonist": "话痨吐槽型，表面被动实则暗中布局",
            "golden_finger": "扮演历史人物，但每次使用会随机遗忘一段记忆",
            "unique_points": "直播变单口相声 + 越强大越被遗忘 + 妹妹是唯一记得他的人",
            "emotion_pacing": "快节奏，每3章一个小高潮，吐槽与爽点比例3:7"
        }
    }
    
    响应：
    {
        "success": true,
        "evaluation": {
            "overall_score": 78,
            "grade": "B+",
            "verdict": "建议继续，但有优化空间",
            "predicted_metrics": {
                "completion_rate": {"min": 12, "max": 18, "unit": "%"},
                "retention": {
                    "d3": {"value": 25, "unit": "%"},
                    "d7": {"value": 15, "unit": "%"},
                    "d30": {"value": 8, "unit": "%"}
                },
                "debut_pass_rate": {"value": 65, "unit": "%"}
            },
            "algorithm_potential": {
                "new_book_traffic": "中等偏上",
                "debut_pass_rate": 65,
                "recommendation_potential": ["书架推荐", "分类强推"]
            },
            "risk_analysis": {
                "level": "中等风险",
                "main_risks": [
                    "话痨人设可能在30章后审美疲劳",
                    "记忆消失代价过于压抑"
                ],
                "mitigation": "每5章安排1章轻松日常，妹妹线快速展开建立情感锚点"
            },
            "similar_cases": [
                {
                    "title": "《我在国运直播讲相声》",
                    "completion_rate": 18,
                    "note": "类似人设，30章后掉留存严重"
                },
                {
                    "title": "《副作用太大我只好无敌了》",
                    "completion_rate": 15,
                    "note": "轻喜剧风格成功对冲压抑感"
                }
            ],
            "optimization_suggestions": [
                {
                    "priority": "高",
                    "suggestion": "开局第1章增加妹妹提醒直播桥段，提前铺垫情感线",
                    "expected_impact": "3日留存+5%",
                    "target_chapters": "第1-3章"
                },
                {
                    "priority": "中",
                    "suggestion": "第5-10章设计震惊+吐槽组合拳，建立人设记忆点",
                    "expected_impact": "黄金三章完读率+10%",
                    "target_chapters": "第5-10章"
                }
            ],
            "detailed_reasoning": "基于用户选择的...",
            "recommendation": "proceed_with_caution"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        dialog_history = data.get('dialog_history', [])
        creative_draft = data.get('creative_draft', {})
        
        if not genre:
            return jsonify({"error": "缺少genre参数"}), 400
        
        if not creative_draft:
            return jsonify({"error": "缺少creative_draft参数"}), 400
        
        # 初始化API客户端
        from src.core.APIClient import APIClient
        from config.config import CONFIG
        api_client = APIClient(CONFIG)
        
        # 导入评估器
        from web.services.market_driven.ai_market_evaluator import AIMarketEvaluator
        evaluator = AIMarketEvaluator(api_client)
        
        # 执行评估
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                evaluator.evaluate(
                    genre=genre,
                    dialog_history=dialog_history,
                    final_creative=creative_draft
                )
            )
        finally:
            loop.close()
        
        # 转换为字典
        evaluation_dict = evaluator.to_dict(result)
        
        return jsonify({
            "success": True,
            "evaluation": evaluation_dict
        }), 200
        
    except Exception as e:
        logger.error(f"AI评估失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "AI评估服务暂时不可用，请稍后重试"
        }), 500


@market_driven_api.route('/evaluation-report/<task_id>', methods=['GET'])
def get_evaluation_report(task_id: str):
    """
    获取已保存的评估报告
    
    用于在生成过程中查看评估结果
    """
    try:
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        evaluation = task.get('evaluation')
        if not evaluation:
            return jsonify({
                "error": "评估报告不存在",
                "message": "该任务尚未完成评估或评估已过期"
            }), 404
        
        return jsonify({
            "success": True,
            "evaluation": evaluation
        }), 200
        
    except Exception as e:
        logger.error(f"获取评估报告失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ==================== 对话打磨 API ====================

@market_driven_api.route('/dialog/start', methods=['POST'])
def start_dialog_polish():
    """
    开始对话打磨流程
    
    请求体：
    {
        "genre": "国运文-直播类",
        "tropes": { ... },  // 套路分析结果
        "username": "作者名"  // 可选
    }
    
    响应：
    {
        "success": true,
        "session_id": "DPM-20260405143028",
        "round": 1,
        "round_type": "init",
        "ai_message": "🎯 【国运文-直播类】套路框架分析...",
        "options": [ ... ],
        "allow_custom": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        tropes = data.get('tropes', {})
        
        if not genre:
            return jsonify({"error": "缺少genre参数"}), 400
        
        # 导入对话打磨管理器
        from web.services.market_driven.dialog_polish_manager import create_dialog_session
        
        # 创建会话
        manager = create_dialog_session(None, genre, tropes)
        
        # 开始第一轮
        result = manager.start_dialog()
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"开始对话打磨失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/dialog/continue', methods=['POST'])
def continue_dialog_polish():
    """
    继续对话打磨流程
    
    请求体：
    {
        "session_id": "DPM-20260405143028",
        "choice": "protagonist",
        "custom_text": "我想写个话痨主角"  // 可选
    }
    
    响应：
    {
        "success": true,
        "session_id": "DPM-20260405143028",
        "round": 2,
        "round_type": "protagonist",
        "ai_message": "🎭 第二步：主角性格设定...",
        "options": [ ... ],
        "allow_custom": true,
        "is_final": false
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        session_id = data.get('session_id')
        choice = data.get('choice')
        custom_text = data.get('custom_text')
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        if not choice:
            return jsonify({"error": "缺少choice参数"}), 400
        
        # 获取会话
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在或已过期"}), 404
        
        # 处理用户输入
        result = manager.process_user_input(choice, custom_text)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"继续对话打磨失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/dialog/back', methods=['POST'])
def go_back_dialog():
    """
    返回到指定轮次
    
    请求体：
    {
        "session_id": "DPM-20260405143028",
        "target_round": 2
    }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        target_round = data.get('target_round')
        
        if not session_id or target_round is None:
            return jsonify({"error": "缺少参数"}), 400
        
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在"}), 404
        
        result = manager.go_back(target_round)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"返回对话轮次失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/dialog/draft/<session_id>', methods=['GET'])
def get_dialog_draft(session_id: str):
    """
    获取对话打磨产生的创意草案
    
    用于在对话结束后调用AI评估
    """
    try:
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在"}), 404
        
        draft = manager.get_creative_draft()
        
        return jsonify({
            "success": True,
            "creative_draft": draft.to_dict(),
            "dialog_history": draft.dialog_history,
            "summary": manager.get_dialog_summary()
        }), 200
        
    except Exception as e:
        logger.error(f"获取创意草案失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 应用启动时的初始化
app = None  # 将在注册时由 web_server_refactored.py 设置
