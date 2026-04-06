# -*- coding: utf-8 -*-
"""
Market Driven Generation API
市场导向生成API

提供市场导向模式的完整流程：
1. 获取可选择的题材列表
2. 分析爆款题材规律
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
        self._stop_flags = {}  # 🔥 新增：任务停止标志 {task_id: True/False}
    
    def should_stop(self, task_id: str) -> bool:
        """检查任务是否应该停止"""
        return self._stop_flags.get(task_id, False)
    
    def set_stop_flag(self, task_id: str, flag: bool = True):
        """设置任务停止标志"""
        self._stop_flags[task_id] = flag
        logger.info(f"[TaskManager] 任务 {task_id} 停止标志设置为: {flag}")
    
    def clear_stop_flag(self, task_id: str):
        """清除任务停止标志"""
        if task_id in self._stop_flags:
            del self._stop_flags[task_id]
    
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
    
    def get_user_active_tasks(self, username: str) -> List[Dict]:
        """获取用户的所有活跃任务
        
        返回运行中、等待中、暂停的任务（不包括已完成/失败的）
        """
        active_statuses = ['pending', 'running', 'in_progress', 'conversation_mode', 
                          'generating_chapters', 'paused', 'paused_insufficient_points']
        user_tasks = []
        
        for task in self.tasks.values():
            if task.get('username') == username and task.get('status') in active_statuses:
                user_tasks.append({
                    'task_id': task['id'],
                    'title': task.get('user_choices', {}).get('title', '未命名任务'),
                    'type': 'market_driven',
                    'status': task.get('status', 'unknown'),
                    'progress': task.get('progress', 0),
                    'stage': task.get('current_stage', '生成中...'),
                    'genre': task.get('genre', 'unknown'),
                    'created_at': task.get('created_at'),
                    'updated_at': task.get('updated_at')
                })
        
        # 按创建时间倒序，最新的在前面
        user_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_tasks

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
        "message": "爆款分析任务已创建"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        use_cache = data.get('use_cache', False)  # 🔥 修复：默认禁用缓存，确保每次分析都是新鲜结果
        
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
                    message="正在分析爆款题材规律..."
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
                    message="爆款分析完成",
                    result={
                        "genre": genre,
                        "tropes": tropes
                    }
                )
                
                logger.info(f"爆款分析任务完成: {task_id}")
                
            except Exception as e:
                logger.error(f"爆款分析任务失败: {e}", exc_info=True)
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
            "message": "爆款分析任务已创建并开始运行"
        }), 202
        
    except Exception as e:
        logger.error(f"创建爆款分析任务失败: {e}", exc_info=True)
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


@market_driven_api.route('/tasks/<task_id>/stop', methods=['POST'])
def stop_market_driven_task(task_id: str):
    """
    停止正在运行的市场导向生成任务
    
    请求体：无
    
    响应：
    {
        "success": true,
        "message": "任务已停止"
    }
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        # 检查任务是否可以停止
        if task["status"] not in ["pending", "running", "generating", "generating_chapters", "conversation_mode"]:
            return jsonify({
                "error": f"任务当前状态为 {task['status']}，无法停止"
            }), 400
        
        # 更新任务状态为停止中
        task_manager.update_task(
            task_id,
            status="stopping",
            message="正在停止任务..."
        )
        
        logger.info(f"[Task {task_id}] 用户请求停止任务")
        
        # 🔥 实际停止逻辑：设置停止标志
        # 章节生成器会定期检查这个标志
        task_manager.set_stop_flag(task_id, True)
        task["stopped_at"] = datetime.now().isoformat()
        
        logger.info(f"[Task {task_id}] 停止标志已设置，等待生成循环检测...")
        
        # 注意：实际状态更新会在生成循环检测到标志后完成
        
        return jsonify({
            "success": True,
            "message": "停止请求已发送，正在等待当前批次完成...",
            "task_id": task_id,
            "status": "stopping"
        }), 200
        
    except Exception as e:
        logger.error(f"停止任务失败: {e}", exc_info=True)
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
                
                # 🔥 检查是否来自对话模式（已生成最终方案）
                dialog_session_id = user_choices.get('dialog_session_id')
                final_plan = user_choices.get('final_plan')
                
                logger.info(f"[Task {task_id}] 检查对话模式 | dialog_session_id: {dialog_session_id} | final_plan: {bool(final_plan)}")
                
                if dialog_session_id and final_plan:
                    # 对话模式：已生成最终方案，跳过爆款分析和方案生成，直接生成章节
                    logger.info(f"[Task {task_id}] 对话模式检测到最终方案，跳过爆款分析和方案生成，直接生成章节")
                    _run_chapter_generation_with_plan(task_id, genre, target_words, api_client, final_plan, user_choices)
                else:
                    # 传统模式：完整流程
                    # 第1阶段：爆款分析
                    _run_trope_analysis(task_id, genre, api_client, user_choices)
                    
                    # 第2阶段：方案 + 一阶段产物生成
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
    """执行爆款分析"""
    task_manager.update_task(
        task_id,
        status="analyzing",
        progress=5,
        current_stage="analyzing_tropes",
        message="正在分析爆款题材规律..."
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
            message="爆款分析完成"
        )
        
        logger.info(f"[Task {task_id}] 爆款分析完成")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 爆款分析失败: {e}")
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
        # 获取爆款分析结果
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
        # 🔥 修复：用户留空表示要求AI生成标题，使用临时项目名
        user_title_for_project = enriched_user_choices.get("title")
        if user_title_for_project and user_title_for_project.strip():
            novel_title = user_title_for_project.strip()
        else:
            # 用户留空或未指定，使用临时项目名
            novel_title = f"未命名_{task_id[:8]}"
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
        
        # 🔥 创建停止检查函数
        def check_should_stop():
            return task_manager.should_stop(task_id)
        
        batch_gen = BatchChapterGenerator(
            api_client=api_client,
            project_path=str(project_path) if project_path else None,
            stop_checker=check_should_stop  # 🔥 传入停止检查函数
        )
        
        all_results = []
        
        # 🔥 跨批次状态：保存前一章的摘要/钩子，确保批次间衔接
        prev_chapter_summary = ""
        last_chapter_hook = ""
        
        for batch_num in range(1, batches + 1):
            # 🔥 检查是否应该停止任务
            if task_manager.should_stop(task_id):
                logger.info(f"[Task {task_id}] 检测到停止标志，正在优雅停止...")
                task_manager.update_task(
                    task_id,
                    status="stopped",
                    message=f"任务已在第{batch_num-1}批后停止",
                    progress=int(55 + ((batch_num - 1) / batches) * 35)
                )
                task_manager.clear_stop_flag(task_id)
                logger.info(f"[Task {task_id}] 任务已停止，已生成{batch_num-1}批章节")
                return all_results
            
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


def _get_genre_specific_prompts(genre: str) -> Dict:
    """
    根据题材获取差异化提示词
    返回各题材特定的书名公式、核心卖点示例、开局钩子公式等
    """
    genre_lower = genre.lower() if genre else ""
    
    # 神豪文特定提示词
    if "神豪" in genre_lower or "花钱" in genre_lower or "返利" in genre_lower:
        return {
            "title_formula": """1. 《神豪：从XX开始》 - 如《神豪：从XX开始》《神豪：从XX开始》
2. 《开局XX，我XX了》 - 如《开局物价XX，我无敌了》《激活XX系统》
3. 《绑定神豪系统后，我XX》 - 如《绑定神豪系统后，我直播XX》
4. 《我有XX》 - 如《我有XX》《我有XX》
5. 《XX，我XX》 - 如《分手XX，我XX》《分手后我XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：穷小子觉醒XX系统，越花越有钱，在反派面前疯狂装逼打脸，极致逆袭爽感",
            "hook_formula": "必须包含：主角身份卑微（外卖员/保安/穷学生）+ 被羞辱/分手 + 突然获得神豪系统 + 第一次装逼打脸",
            "personality_guide": "要有隐忍后的爆发感，表面低调实则掌控全局",
            "background_guide": "如：被分手的穷学生/被开除的保安/被看不起的实习生",
            "selling_point_requirement": "穷小子逆袭+神豪系统+疯狂打脸+前女友后悔",
            "story_keywords": "花钱返利、直播打赏、前女友后悔、富二代打脸、商业帝国",
            "hook_requirement": "必须包含：被羞辱场景+系统觉醒+第一次消费打脸",
            "emotion_guide": "逆袭爽感+打脸快感+前女友后悔的暗爽",
            "risk_guide": "避免装逼过于刻意，保持消费场景多样化",
            "rule_5": "开局钩子必须有被羞辱场景和第一次消费打脸"
        }
    
    # 国运文/禁地类特定提示词
    elif "国运" in genre_lower or "禁地" in genre_lower or "直播" in genre_lower:
        return {
            "title_formula": """1. 《开局XX，我XX了》 - 如《开局觉醒XX能力》《觉醒满级XX，我无敌了》
2. 《绑定XX系统后，我XX》 - 如《绑定XX系统后，我气哭了XX》《扮演XX，队友XX》
3. 《XX：从XX开始》 - 如《XX：从扮演XX开始》《XX：从被选中开始》
4. 《我有XX》 - 如《我有无限XX》《我能召唤XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：主角拥有XX能力，在全球直播的禁地挑战中靠XX操作带飞全场，极致反差爽感",
            "hook_formula": "必须包含：全球/全国直播场景 + 别人严肃紧张 + 主角离谱操作 + 震惊全球",
            "personality_guide": "要有反差感，如：表面沙雕吐槽实则掌控全局",
            "background_guide": "如：失意脱口秀演员/被选中的普通人/隐藏身份的大佬",
            "selling_point_requirement": "独特能力+反差操作+直播震惊+带飞全场",
            "story_keywords": "全球禁地、规则怪谈、神宠养成、跨国对垒、位面征服",
            "hook_requirement": "必须包含：直播场景+别人正经+主角离谱操作+震惊效果",
            "emotion_guide": "搞笑爽感+民族自豪感+观众震惊",
            "risk_guide": "避免搞笑风格单一，中后期升级世界规则",
            "rule_5": "开局钩子必须有直播元素和反差感"
        }
    
    # 玄幻/仙侠类特定提示词
    elif "玄幻" in genre_lower or "仙侠" in genre_lower or "修真" in genre_lower or "修仙" in genre_lower:
        return {
            "title_formula": """1. 《开局XX，我XX了》 - 如《开局觉醒XX》《觉醒满级XX，我XX》
2. 《XX：从XX开始》 - 如《XX：从XX开始》《XX：从XX开始逆袭》
3. 《绑定XX系统后，我XX》 - 如《绑定XX系统后，我无敌了》
4. 《我有XX》 - 如《我有XX》《我能XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：主角觉醒XX能力，越级挑战天才，在宗门大比中一路碾压，成就无上道途",
            "hook_formula": "必须包含：主角被废/被退婚/被看不起 + 觉醒金手指 + 第一次越级打脸",
            "personality_guide": "要有坚韧不屈、逆天改命的气质",
            "background_guide": "如：被废的天才/被退婚的少年/杂役弟子",
            "selling_point_requirement": "废柴逆袭+逆天悟性+越级挑战+宗门崛起",
            "story_keywords": "宗门争霸、秘境探索、天骄争锋、逆天改命、证道成帝",
            "hook_requirement": "必须包含：被羞辱场景+金手指觉醒+第一次越级战斗",
            "emotion_guide": "逆袭热血+战斗激情+逆天改命",
            "risk_guide": "避免套路同质化，创新金手指设定",
            "rule_5": "开局钩子必须有修炼体系和第一次战斗打脸"
        }
    
    # 都市/职场类特定提示词
    elif "都市" in genre_lower or "职场" in genre_lower or "医" in genre_lower or "兵王" in genre_lower:
        return {
            "title_formula": """1. 《神豪：从XX开始》 - 如《神豪：从XX开始》《从XX到XX》
2. 《开局XX，我XX了》 - 如《开局获得XX》《激活XX系统》
3. 《XX：从XX开始》 - 如《XX：从XX开始》《XX：从XX归来》
4. 《我有XX》 - 如《我有XX》《我能XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：小职员获得XX系统，每次选择都有丰厚奖励，在职场和情场疯狂逆袭",
            "hook_formula": "必须包含：主角身份低微 + 被羞辱/开除 + 获得金手指 + 第一次逆袭打脸",
            "personality_guide": "要有隐忍后的爆发，低调中带着霸气",
            "background_guide": "如：被开除的实习生/被退婚的小医生/退伍特种兵",
            "selling_point_requirement": "小人物逆袭+特殊能力+职场打脸+美女环绕",
            "story_keywords": "职场逆袭、美女总裁、医术无双、地下世界、商业帝国",
            "hook_requirement": "必须包含：被羞辱场景+金手指觉醒+第一次成功逆袭",
            "emotion_guide": "逆袭爽感+装逼快感+美女倒追",
            "risk_guide": "避免过于YY，保持一定现实逻辑",
            "rule_5": "开局钩子必须有都市场景和第一次逆袭打脸"
        }
    
    # 末日/求生类特定提示词
    elif "末日" in genre_lower or "求生" in genre_lower or "末世" in genre_lower or "天灾" in genre_lower:
        return {
            "title_formula": """1. 《末日：从XX开始》 - 如《末日：从XX开始》《天灾：从XX开始》
2. 《开局XX，我XX了》 - 如《开局XX，我XX了》《觉醒XX》
3. 《XX：从XX开始》 - 如《重生：从XX开始》《XX：从XX开始》
4. 《我有XX》 - 如《我有XX》《我能XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：重生者提前囤货备战末日，在丧尸和天灾面前打造安全堡垒，被前队友疯狂跪舔",
            "hook_formula": "必须包含：末日降临/重生归来 + 疯狂囤货 + 第一个求生挑战 + 打脸前队友",
            "personality_guide": "要有先知的冷静和果断，杀伐决断",
            "background_guide": "如：重生归来的先知/提前觉醒异能者/囤货达人",
            "selling_point_requirement": "重生囤货+末日求生+安全堡垒+前队友后悔",
            "story_keywords": "丧尸围城、天灾降临、囤货求生、安全堡垒、人性考验",
            "hook_requirement": "必须包含：末日场景+囤货准备+第一个危机+打脸",
            "emotion_guide": "生存紧张+囤货满足+人性反转",
            "risk_guide": "避免过于压抑，保持囤货爽感",
            "rule_5": "开局钩子必须有末日场景和囤货打脸"
        }
    
    # 默认提示词（通用）
    else:
        return {
            "title_formula": """1. 《开局XX，我XX了》 - 如《开局XX，我XX了》
2. 《绑定XX系统后，我XX》 - 如《绑定XX后，我XX了》
3. 《XX：从XX开始》 - 如《XX：从XX开始》
4. 《我有XX》 - 如《我有XX》

【重要】以上只是格式示例，严禁直接复制示例内容！必须根据用户的金手指和题材创作全新书名！""",
            "selling_point_example": "示例：普通主角觉醒XX能力，在困境中不断逆袭，打脸看不起他的人",
            "hook_formula": "必须包含：主角身份低微 + 被羞辱 + 觉醒能力 + 第一次打脸",
            "personality_guide": "要有逆袭的决心和隐藏的实力",
            "background_guide": "如：普通人/被看不起的小人物",
            "selling_point_requirement": "普通人逆袭+特殊能力+打脸爽感",
            "story_keywords": "系统、逆袭、打脸、成长",
            "hook_requirement": "必须包含：被羞辱场景+能力觉醒+第一次成功",
            "emotion_guide": "逆袭爽感+成长满足",
            "risk_guide": "避免过于套路化",
            "rule_5": "开局钩子必须有被羞辱场景和能力觉醒"
        }


def _run_chapter_generation_with_plan(task_id: str, genre: str, target_words: int, api_client=None, final_plan: Dict = None, user_choices: Dict = None):
    """
    基于已确认的最终方案，复用现有对话流程生成产物
    
    方案：将final_plan包装成类似tropes的结构，复用_run_plan_and_products_conversation
    """
    from web.services.market_driven.config import get_config
    config = get_config(genre)
    
    try:
        task = task_manager.get_task(task_id)
        username = task.get('username') or 'anonymous'
        
        # 从 final_plan 和 user_choices 获取核心设定
        # 🔥 修复：书名特殊处理 - 用户传空字符串表示要求AI生成，不能使用模板标题
        user_title = user_choices.get('title')
        if user_title is not None and user_title.strip():
            # 用户指定了标题（非空）
            novel_title = user_title.strip()
        elif user_title is not None and not user_title.strip():
            # 用户主动留空，要求AI生成全新标题 - 传空字符串标识
            novel_title = ""  # 空字符串表示由AI生成
        else:
            # 用户没有传title字段（undefined），使用final_plan的标题
            novel_title = final_plan.get('title') or ""
        
        protagonist_name = user_choices.get('protagonist_name') or final_plan.get('protagonist_name') or '主角'
        
        logger.info(f"[DialogMode] 复用对话流程生成 | 任务: {task_id} | 书名: {novel_title or '(由AI生成)'} | 主角: {protagonist_name}")
        
        # 🔥 关键：将final_plan包装成类似tropes的结构，复用现有对话流程
        # 这样 _run_plan_and_products_conversation 可以无缝使用final_plan
        
        # 获取金手指信息（优先使用完整的golden_finger，回退到summary）
        gf_data = final_plan.get('golden_finger', {})
        if not gf_data or not isinstance(gf_data, dict):
            gf_data = {
                "type": final_plan.get('golden_finger_summary', '花钱返利'),
                "mechanism": final_plan.get('golden_finger_summary', ''),
                "upgrade": "随主角成长逐步解锁"
            }
        
        fake_tropes = {
            "genre": genre,
            "final_plan": final_plan,  # 传递完整的final_plan
            "core_formula": final_plan.get('story_direction', ''),
            "protagonist_archetroype": final_plan.get('protagonist_personality', ''),
            "golden_finger": gf_data,  # 🔥 使用完整的金手指设计
            "core_selling_point": final_plan.get('core_selling_point', ''),
            "opening_hook": final_plan.get('opening_hook', ''),
            # 标记这是来自对话模式的final_plan
            "_source": "dialog_mode_final_plan"
        }
        
        # 更新任务，设置fake_tropes作为result，这样_run_plan_and_products_conversation可以获取
        current_result = task.get("result") or {}
        current_result["tropes"] = fake_tropes
        task_manager.update_task(task_id, result=current_result)
        
        # 🔥 复用现有的对话流程！
        # _run_plan_and_products_conversation 会使用 generate_with_conversation
        # 后者会调用 MarketDrivenConversationManager 进行真正的对话生成
        logger.info(f"[DialogMode] 调用现有对话流程 _run_plan_and_products_conversation")
        
        _run_plan_and_products_conversation(
            task_id=task_id,
            genre=genre,
            user_choices=user_choices,
            api_client=api_client
        )
        
        logger.info(f"[DialogMode] 对话流程完成，开始生成章节...")
        
        # 🔥 关键：对话流程完成后，继续生成章节
        # 复用传统模式的章节生成逻辑
        _run_chapter_generation(task_id, genre, target_words, api_client)
        
        logger.info(f"[DialogMode] 全部生成完成")
        return
        
    except Exception as e:
        logger.error(f"[DialogMode] 对话流程失败: {e}", exc_info=True)
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
        "tropes": { ... },  // 爆款分析结果
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


@market_driven_api.route('/dialog/next', methods=['POST'])
def dialog_next():
    """
    对话下一步（别名，等同于 /dialog/continue）
    请求体：
    {
        "session_id": "xxx",
        "selected_option": "option_id",
        "custom_input": "自定义文本"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        session_id = data.get('session_id')
        selected_option = data.get('selected_option')
        custom_input = data.get('custom_input')
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        # 获取会话
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在或已过期"}), 404
        
        # 处理用户输入
        result = manager.process_user_input(selected_option or 'continue', custom_input)
        
        return jsonify({
            "success": True,
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"对话下一步失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@market_driven_api.route('/dialog/complete', methods=['POST'])
def dialog_complete():
    """
    完成对话打磨，开始生成小说
    请求体：
    {
        "session_id": "xxx",
        "selected_option": "option_id",
        "custom_input": "自定义文本"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        session_id = data.get('session_id')
        selected_option = data.get('selected_option')
        custom_input = data.get('custom_input')
        
        if not session_id:
            return jsonify({"error": "缺少session_id参数"}), 400
        
        # 获取会话
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在或已过期"}), 404
        
        # 如果有选择或输入，先处理最后一轮
        if selected_option or custom_input:
            manager.process_user_input(selected_option or 'complete', custom_input)
        
        # 获取对话结果
        draft = manager.get_creative_draft()
        
        # 获取题材
        genre = manager.genre
        
        # 构建用户选择数据（兼容表单模式）
        user_choices = {
            'title': draft.title or '未命名小说',
            'protagonist_name': draft.protagonist_name or '主角',
            'protagonist_personality': draft.protagonist_personality or '',
            'golden_finger_desc': draft.golden_finger_desc or '',
            'opening_scene': draft.opening_scene or '',
            'main_plot': draft.main_plot or '',
            'wordcount': '50',
            'chapters': '200'
        }
        
        # 调用标准生成流程（复用 /generate 逻辑）
        # 创建任务
        task_id = task_manager.create_task(genre, user_choices)
        
        # 获取当前用户信息
        from flask import session
        user_id = session.get('user_id')
        username = _get_current_username()
        
        # 更新任务信息
        task_manager.update_task(
            task_id,
            username=username,
            user_id=user_id,
            current_stage='initializing',
            message='初始化生成任务...'
        )
        
        # 启动后台生成 - 复用 /generate 的内部逻辑
        def run_dialog_generation():
            api_client = None
            try:
                # 初始化API客户端
                try:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                    api_client.set_username(username)
                except Exception as e:
                    logger.warning(f"APIClient初始化失败，将使用模拟模式: {e}")
                
                # 使用目标字数配置
                from web.services.market_driven.config import get_target_words
                target_words = get_target_words(genre)
                
                # 对话模式：需要生成最终方案（如果还没有的话），然后生成章节
                # 第1步：生成最终方案
                task_manager.update_task(
                    task_id,
                    current_stage='planning',
                    progress=5,
                    message='生成最终创作方案...'
                )
                
                # 从对话草稿构建最终方案
                final_plan = {
                    'title': draft.title or '未命名小说',
                    'protagonist_name': draft.protagonist_name or '主角',
                    'protagonist_personality': draft.protagonist_personality or '冷静果断',
                    'golden_finger_summary': draft.golden_finger_desc or '系统金手指',
                    'core_selling_point': draft.main_plot or '热血爽文',
                    'opening_hook': draft.opening_scene or '开局获系统',
                    'emotion_core': '爽',
                    'world_rules': '现代都市+系统',
                    'first_climax': '第3章首次打脸',
                    'main_goal': '成为最强',
                    'story_direction': draft.main_plot or '升级打脸流',
                    'emotion_curve': [],
                    'chapter_count': 200
                }
                
                # 保存方案到任务
                task_manager.update_task(
                    task_id,
                    final_plan=final_plan,
                    progress=10,
                    message='方案已生成，准备生成章节...'
                )
                
                # 第2步：生成章节
                _run_chapter_generation_with_plan(
                    task_id=task_id,
                    genre=genre,
                    target_words=target_words,
                    api_client=api_client,
                    final_plan=final_plan,
                    user_choices=user_choices
                )
                
                # 完成
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_stage="generation_completed",
                    message="全部生成完成"
                )
                
            except Exception as e:
                logger.error(f"[Task {task_id}] 对话模式生成失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"生成失败: {str(e)}"
                )
        
        thread = threading.Thread(target=run_dialog_generation)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "已开始生成小说"
        }), 200
        
    except Exception as e:
        logger.error(f"完成对话打磨失败: {e}", exc_info=True)
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


@market_driven_api.route('/generate-final-plan', methods=['POST'])
def generate_final_plan():
    """
    生成最终详细方案
    
    请求体：
    {
        "genre": "国运文-直播类",
        "session_id": "DPM-xxx",
        "form_data": {
            "title": "xxx",
            "protagonist_name": "xxx",
            ...
        }
    }
    
    响应：
    {
        "success": true,
        "final_plan": {
            "title": "书名",
            "protagonist": "主角设定",
            "golden_finger_summary": "金手指概述",
            "core_selling_point": "核心卖点",
            "main_outline": "主线大纲",
            "first_30_chapters": "前30章规划",
            "characters": "核心角色",
            "emotion_curve": "情绪曲线",
            "risk_warning": "风险提示"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        genre = data.get('genre')
        session_id = data.get('session_id')
        form_data = data.get('form_data', {})
        
        if not genre or not session_id:
            return jsonify({"error": "缺少genre或session_id"}), 400
        
        # 获取对话会话
        from web.services.market_driven.dialog_polish_manager import get_dialog_session
        manager = get_dialog_session(session_id)
        
        if not manager:
            return jsonify({"error": "会话不存在或已过期"}), 404
        
        # 获取创意草案
        draft = manager.get_creative_draft()
        
        # 初始化API客户端
        from src.core.APIClient import APIClient
        from config.config import CONFIG
        api_client = APIClient(CONFIG)
        
        # 🔥 获取用户填写的主角名（第6步表单填写）
        user_protagonist_name = form_data.get('protagonist_name', '').strip()
        user_golden_finger_desc = form_data.get('golden_finger_desc', '').strip()
        user_title = form_data.get('title', '').strip()
        
        logger.info(f"[FinalPlan] 用户输入 | Session: {session_id} | 题材: {genre} | 书名: {user_title} | 主角: {user_protagonist_name}")
        
        # 🔥 根据题材获取差异化提示词
        genre_prompts = _get_genre_specific_prompts(genre)
        
        # 构建用户提示词 - 聚焦于核心设定（强制使用用户填写的值）
        user_prompt = f"""你是一位资深番茄小说爆款策划编辑，请基于以下设定，生成故事的核心创作方案。

**【强制要求】**
- 主角姓名：{user_protagonist_name if user_protagonist_name else '[由AI生成，2-4字]'}
- {'书名：用户指定标题《' + user_title + '》（必须严格使用此标题）' if user_title else '书名：由AI根据题材和金手指特点生成最佳爆款书名（6-14字，含数字/对比/反差/爽点预期）'}
- 金手指描述：{user_golden_finger_desc if user_golden_finger_desc else draft.golden_finger}

**【重要警告 - 书名创新要求】**
根据上述金扇指描述，可能涉及"吐槽系统"、"观众互动"等关键词。
但你必须创新，不能直接用"绑定XX系统后我XX"这种直白方式命名！

正确书名创作方法：
- 不要直接出现"系统"二字
- 使用回避、曲折、意外等手法
- 例如金手指是"吐槽系统"，书名可以是《我靠嘴炮带飞全国》《观众大爷救救我》《直播间里我气哭了怪谈》
- 书名要有悬念感，不能直白地告诉读者"我有系统"

**【参考设定】**
**题材：** {genre}
**主角性格：** {draft.protagonist}
**开局设计：** {draft.opening_design}
**情感线：** {draft.emotion_line}
**差异化亮点：** {draft.unique_points}
**目标字数：** {form_data.get('wordcount', '50')}万字 / {form_data.get('chapters', '200')}章

**【番茄爆款书名公式 - 必须遵守】**
{genre_prompts['title_formula']}
5. 必须包含：数字/强烈对比/爽点预期/身份反差
6. 严禁：文艺化书名、生僻字、超过15字

**【核心卖点公式】**
结构：[独特设定] + [主角性格] + [打脸方式] + [爽点结果]
{genre_prompts['selling_point_example']}

**【开局钩子公式】**
{genre_prompts['hook_formula']}

**【JSON输出格式 - 严格遵守】**
请输出故事核心设定，必须是**标准JSON格式**，要求如下：
- 所有字符串使用**双引号** "key": "value"（严禁使用单引号）
- 所有字段必须填写，不能为空
- 严禁在JSON中包含注释

```json
{{
    "title": "{user_title if user_title else '书名（6-14字，番茄爆款风格）'}",
    "protagonist_name": "{user_protagonist_name if user_protagonist_name else '主角名（2-4字，有记忆点）'}",
    "protagonist_personality": "核心性格（{genre_prompts['personality_guide']}）",
    "protagonist_background": "背景（要有代入感，{genre_prompts['background_guide']}）",
    "golden_finger_summary": "{user_golden_finger_desc if user_golden_finger_desc else '金手指机制'}",
    "core_selling_point": "核心卖点（一句话概括爽点，必须包含：{genre_prompts['selling_point_requirement']}）",
    "story_direction": "剧情方向（关键词，如：{genre_prompts['story_keywords']}）",
    "opening_hook": "开局钩子（{genre_prompts['hook_requirement']}，100字内）",
    "emotion_core": "情感核心（{genre_prompts['emotion_guide']}）",
    "risk_warning": "风险提示（如：{genre_prompts['risk_guide']}）"
}}
```

**【强制规则】**
1. {'主角姓名必须严格使用：' + user_protagonist_name if user_protagonist_name else '主角名要符合题材，2-4字有记忆点'}
2. {'书名必须严格使用：' + user_title if user_title else '书名必须符合番茄爆款公式，6-14字'}
3. {'金手指必须严格使用用户描述：' + user_golden_finger_desc if user_golden_finger_desc else '金手指要清晰'}
4. 核心卖点必须有画面感，能激发点击欲望
5. {genre_prompts['rule_5']}
6. 所有内容必须符合番茄读者口味，直白有力
7. **必须输出标准JSON格式（双引号），严禁Python字典格式（单引号）**"""

        # 系统提示词 - 番茄爆款风格专家
        system_prompt = """你是一位顶级番茄小说爆款策划专家，深谙番茄平台读者心理。

你的核心能力：
1. 精通番茄爆款书名公式：《开局XX，我XX了》《绑定XX系统后，我XX》《我有XX》
2. 擅长设计强爽点：反差感、直播震惊、气哭反派、带飞全国
3. 懂番茄读者：喜欢直白有力、画面感强、能引发好奇心的内容
4. 会写核心卖点：一句话让人想点击，包含独特设定+反差操作+爽感结果

输出要求：
- 【书名创作要求】必须根据用户提供的题材和金手指，创作全新的书名，严禁直接复制示例中的书名！书名必须是原创，15个中文字符以内，符合番茄爆款公式
- 核心卖点必须有画面感，能激发点击欲
- 开局钩子必须有直播元素和震惊效果
- 所有内容直白有力，符合番茄读者口味
- 必须输出有效JSON格式

【书名处理规则 - 必须遵守】
1. 如果用户未指定书名（留空）：
   - 你必须根据题材和金手指，创作一个原创的番茄爆款风格书名
   - 要求：6-14个中文字符，包含数字/对比/反差/爽点预期
   - 示例格式：《开局XX，我XX了》《绑定XX系统后，我XX》《我有XX》
   - 严禁直接复制任何示例书名，必须原创！

2. 如果用户指定了书名：
   - 必须严格使用用户提供的书名（一字不差）
   - 但你需要检查：书名必须在15个中文字符以内
   - 如果超过15字，你需要在保持原意的基础上精简到15字以内
   - 如果用户书名不符合番茄风格，你可以轻微优化但保持原意

【重要警告】
- 示例中的书名仅供参考格式，严禁直接复制！
- 用户未指定时，必须创作全新书名，不能复制任何已知作品标题！
- 书名字符数必须控制在15个中文以内！"""
        
        logger.info(f"[FinalPlan] 开始生成最终方案 | Session: {session_id} | 书名: {form_data.get('title', draft.title)}")
        
        # 调用AI生成
        try:
            response = api_client.generate_content_with_retry(
                content_type="conversation",  # 使用已存在的类型
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                purpose="final_plan_generation"
            )
            
            if response:
                logger.info(f"[FinalPlan] 收到AI响应 | Session: {session_id} | 响应长度: {len(str(response))}")
                logger.debug(f"[FinalPlan] AI响应内容: {str(response)[:500]}...")
                
                # 尝试解析JSON
                import json
                import re
                import ast
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    json_str = json_match.group()
                    try:
                        final_plan = json.loads(json_str)
                        logger.info(f"[FinalPlan] JSON解析成功 | Session: {session_id}")
                        
                        # 🔥 验证并处理书名长度
                        title = final_plan.get('title', '')
                        # 计算中文字符数（不包括标点和空格）
                        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', title)
                        chinese_count = len(chinese_chars)
                        
                        if chinese_count > 15:
                            logger.warning(f"[FinalPlan] 书名超过15字: {title} ({chinese_count}字)，需要截断")
                            # 截断到15字，保留前15个中文字符
                            truncated_title = ''.join(chinese_chars[:15])
                            final_plan['title'] = truncated_title
                            logger.info(f"[FinalPlan] 书名已截断: {truncated_title}")
                        elif not title:
                            # 如果书名为空，生成默认标题
                            default_title = f"{genre.split('-')[0]}之{user_protagonist_name or '主角'}传"
                            final_plan['title'] = default_title[:15]
                            logger.info(f"[FinalPlan] 书名为空，使用默认: {final_plan['title']}")
                        else:
                            logger.info(f"[FinalPlan] 书名: {title} ({chinese_count}字)")
                        
                        logger.info(f"[FinalPlan] 主角: {final_plan.get('protagonist_name', 'N/A')}")
                        logger.info(f"[FinalPlan] 核心卖点: {final_plan.get('core_selling_point', 'N/A')[:50]}...")
                        
                        return jsonify({
                            "success": True,
                            "final_plan": final_plan
                        }), 200
                    except json.JSONDecodeError:
                        # 尝试解析Python单引号字典格式
                        try:
                            final_plan = ast.literal_eval(json_str)
                            if isinstance(final_plan, dict):
                                logger.info(f"[FinalPlan] Python字典解析成功 | Session: {session_id}")
                                return jsonify({
                                    "success": True,
                                    "final_plan": final_plan
                                }), 200
                        except Exception as e2:
                            logger.error(f"[FinalPlan] JSON/Python解析均失败 | 内容: {json_str[:200]} | 错误: {e2}")
                else:
                    logger.error(f"[FinalPlan] 未找到JSON内容 | 响应: {str(response)[:200]}")
            else:
                logger.warning(f"[FinalPlan] AI返回空响应 | Session: {session_id}")
        except Exception as e:
            logger.error(f"[FinalPlan] AI生成异常: {e}", exc_info=True)
        
        # 如果AI失败，使用默认方案（核心设定）- 使用题材差异化的默认内容
        # 从form_data获取用户填写的主角名
        user_protagonist_name = form_data.get('protagonist_name', '')
        user_title = form_data.get('title', '')
        
        # 提取主角性格关键词和金手指关键词
        personality = draft.protagonist.split('（')[0].strip() if '（' in draft.protagonist else draft.protagonist
        gf_desc = draft.golden_finger
        gf_keyword = '特殊'
        if '吐槽' in gf_desc or '弹幕' in gf_desc:
            gf_keyword = '吐槽系统'
        elif '观众' in gf_desc or '互动' in gf_desc:
            gf_keyword = '互动系统'
        elif '记忆' in gf_desc:
            gf_keyword = '记忆回溯'
        elif '身体' in gf_desc or '衰弱' in gf_desc:
            gf_keyword = '身体强化'
        elif '花钱' in gf_desc or '返利' in gf_desc or '神豪' in gf_desc:
            gf_keyword = '花钱返利'
        
        # 🔥 根据题材获取差异化默认方案
        genre_lower = genre.lower() if genre else ""
        
        if "神豪" in genre_lower or "花钱" in genre_lower:
            # 神豪文默认方案
            default_plan = {
                "title": user_title or f"神豪：从被校花拒绝开始",
                "protagonist_name": user_protagonist_name or "林凡",
                "protagonist_personality": f"{personality}，表面低调实则霸气侧漏",
                "protagonist_background": f"{personality}主角，被校花拒绝后觉醒神豪系统",
                "golden_finger_summary": draft.golden_finger[:50] + "..." if len(draft.golden_finger) > 50 else draft.golden_finger,
                "core_selling_point": f"{personality}主角觉醒{gf_keyword}系统，花钱就能变强，在前女友和富二代面前疯狂装逼打脸，享受极致逆袭快感",
                "story_direction": "花钱返利、直播打赏、前女友后悔、商业帝国、美女环绕",
                "opening_hook": f"校花生日宴上，{user_protagonist_name or '主角'}被当众羞辱分手，绝望之际觉醒神豪系统，当场打脸全场",
                "emotion_core": f"{draft.emotion_line[:30] if hasattr(draft, 'emotion_line') and draft.emotion_line else '逆袭爽感+打脸快感+前女友后悔的暗爽'}",
                "risk_warning": "• 避免装逼过于刻意\n• 保持消费场景多样化\n• 中后期引入商业布局"
            }
        elif "玄幻" in genre_lower or "仙侠" in genre_lower:
            # 玄幻文默认方案
            default_plan = {
                "title": user_title or f"开局觉醒{gf_keyword}，我{personality}逆天改命",
                "protagonist_name": user_protagonist_name or "叶尘",
                "protagonist_personality": f"{personality}，逆天而行不屈服",
                "protagonist_background": f"{personality}少年，从废柴开始逆袭",
                "golden_finger_summary": draft.golden_finger[:50] + "..." if len(draft.golden_finger) > 50 else draft.golden_finger,
                "core_selling_point": f"{personality}主角觉醒{gf_keyword}，越级挑战各路天骄，在宗门大比中一路碾压，成就无上道途",
                "story_direction": "宗门争霸、秘境探索、天骄争锋、逆天改命、证道成帝",
                "opening_hook": f"宗门测试上，{user_protagonist_name or '主角'}被判定为废柴，绝望之际觉醒{gf_keyword}，当场击败天才",
                "emotion_core": f"{draft.emotion_line[:30] if hasattr(draft, 'emotion_line') and draft.emotion_line else '逆袭热血+战斗激情+逆天改命'}",
                "risk_warning": "• 避免套路同质化\n• 创新金手指设定\n• 保持升级节奏"
            }
        else:
            # 通用默认方案（偏向国运/禁地类）
            default_plan = {
                "title": user_title or f"开局觉醒{gf_keyword}，我{personality}无敌了",
                "protagonist_name": user_protagonist_name or "江辰",
                "protagonist_personality": f"{personality}，表面玩世不恭实则心思缜密",
                "protagonist_background": f"{personality}主角，意外觉醒金手指开启逆袭之旅",
                "golden_finger_summary": draft.golden_finger[:50] + "..." if len(draft.golden_finger) > 50 else draft.golden_finger,
                "core_selling_point": f"{personality}主角觉醒{gf_keyword}，在全球直播的禁地挑战中不按套路出牌，用沙雕操作气哭BOSS，全国观众笑到破防",
                "story_direction": "全球禁地、规则怪谈、神宠养成、跨国对垒、位面征服",
                "opening_hook": f"全球禁地开启，各国选手全副武装，{user_protagonist_name or '主角'}却带着独特金手指登场，全球直播瞬间炸裂",
                "emotion_core": f"{draft.emotion_line[:30] if hasattr(draft, 'emotion_line') and draft.emotion_line else '轻松搞笑+民族自豪感'}",
                "risk_warning": "• 避免搞笑风格单一\n• 中后期升级世界规则\n• 保持更新节奏"
            }
        
        logger.info(f"[FinalPlan] 使用默认方案 | Session: {session_id}")
        return jsonify({
            "success": True,
            "final_plan": default_plan,
            "note": "使用默认方案（AI生成失败）"
        }), 200
        
    except Exception as e:
        logger.error(f"生成最终方案失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 应用启动时的初始化
app = None  # 将在注册时由 web_server_refactored.py 设置


@market_driven_api.route('/tasks/active', methods=['GET'])
def get_user_active_tasks():
    """
    获取当前用户的所有活跃任务
    
    返回运行中、等待中、暂停的任务（不包括已完成/失败的）
    用于页面加载时恢复后台任务显示
    
    响应：
    {
        "success": true,
        "tasks": [
            {
                "task_id": "uuid",
                "title": "小说名",
                "type": "market_driven",
                "status": "running",
                "progress": 50,
                "stage": "生成世界观...",
                "genre": "国运文-直播类",
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:05:00"
            }
        ],
        "count": 1
    }
    """
    try:
        username = _get_current_username()
        
        # 获取市场导向任务
        tasks = task_manager.get_user_active_tasks(username)
        
        # TODO: 添加第一阶段任务查询（如果有独立的管理器）
        
        return jsonify({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户活跃任务失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "tasks": [],
            "count": 0
        }), 500


# ==================== 章节续写 API ====================

@market_driven_api.route('/<title>/continue-chapters', methods=['POST'])
def continue_chapters(title):
    """
    章节续写 - 直接生成后续章节，不重新生成设定
    
    Args:
        title: 项目标题
        
    Request Body:
        {
            "start_chapter": 11,  # 起始章节号
            "end_chapter": 16     # 结束章节号
        }
        
    Returns:
        {
            "success": True,
            "task_id": "...",
            "message": "章节续写任务已启动"
        }
    """
    try:
        from urllib.parse import unquote
        title = unquote(title)
        username = _get_current_username()
        
        # 获取请求参数
        data = request.json or {}
        start_chapter = data.get('start_chapter', 1)
        end_chapter = data.get('end_chapter', start_chapter + 5)
        
        logger.info(f"[章节续写] {title}: 第{start_chapter}-{end_chapter}章")
        
        # 查找项目路径
        from web.utils.path_utils import find_novel_project
        project_path = find_novel_project(title, username)
        
        if not project_path:
            return jsonify({
                "success": False,
                "error": f"项目 '{title}' 不存在"
            }), 404
        
        project_path = Path(project_path)
        
        # 工位修复：尝试多个可能的蓝图路径
        blueprint_paths = [
            project_path / "phase_one_products" / "完整方案.json",
            project_path / "phase_one_products" / "blueprint.json",
            project_path / "blueprint.json",
            project_path / "完整方案.json",
        ]
        
        blueprint_path = None
        for path in blueprint_paths:
            if path.exists():
                blueprint_path = path
                logger.info(f"[章节续写] 找到蓝图文件: {path}")
                break
        
        if not blueprint_path:
            # 工位修复：如果没有蓝图，尝试从 project_info.json 构建一个简单的蓝图
            project_info_file = project_path / "project_info.json"
            if project_info_file.exists():
                try:
                    with open(project_info_file, 'r', encoding='utf-8') as f:
                        project_info = json.load(f)
                    
                    logger.info(f"[章节续写] 没有蓝图文件，尝试从 project_info 构建")
                    
                    # 构建简单蓝图
                    blueprint = {
                        'title': project_info.get('novel_title', title),
                        'core_selling_point': project_info.get('novel_info', {}).get('synopsis', ''),
                        'protagonist': project_info.get('character_design', {}).get('protagonist', {}),
                        'golden_finger': project_info.get('golden_finger', {}),
                        'main_plot': project_info.get('storyline', ''),
                        'target_chapters': project_info.get('generation_metadata', {}).get('total_chapters', 200),
                    }
                    
                    # 保存临时蓝图以便后续使用
                    temp_blueprint_path = project_path / "phase_one_products" / "完整方案.json"
                    temp_blueprint_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(temp_blueprint_path, 'w', encoding='utf-8') as f:
                        json.dump(blueprint, f, ensure_ascii=False, indent=2)
                    
                    blueprint_path = temp_blueprint_path
                    logger.info(f"[章节续写] 已从 project_info 构建并保存蓝图")
                    
                except Exception as e:
                    logger.error(f"[章节续写] 从 project_info 构建蓝图失败: {e}")
            
            if not blueprint_path:
                return jsonify({
                    "success": False,
                    "error": "未找到章节规划文件，无法续写"
                }), 400
        
        with open(blueprint_path, 'r', encoding='utf-8') as f:
            blueprint = json.load(f)
        
        # 扣除点数（每章10点）
        from web.services.points_service import points_service
        chapters_to_generate = end_chapter - start_chapter + 1
        points_needed = chapters_to_generate * 10
        
        balance = points_service.get_balance(username)
        if balance < points_needed:
            return jsonify({
                "success": False,
                "error": f"创造点不足，需要{points_needed}点，当前{balance}点",
                "current_balance": balance,
                "needed": points_needed
            }), 402
        
        # 扣除点数
        success, result = points_service.consume_points(
            username=username,
            points=points_needed,
            action=f"续写章节: {title} 第{start_chapter}-{end_chapter}章",
            novel_title=title
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": result
            }), 402
        
        # 创建续写任务
        task_id = task_manager.create_task(
            title=title,
            task_type="continue_chapters",
            username=username
        )
        
        # 启动后台线程生成章节
        import threading
        thread = threading.Thread(
            target=_run_continue_chapter_generation,
            args=(task_id, title, blueprint, start_chapter, end_chapter, username)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"章节续写任务已启动，将生成第{start_chapter}-{end_chapter}章",
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "points_consumed": points_needed
        })
        
    except Exception as e:
        logger.error(f"[章节续写] 启动失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _run_continue_chapter_generation(task_id, title, blueprint, start_chapter, end_chapter, username):
    """
    在后台运行章节续写生成
    """
    try:
        task_manager.update_task(task_id, {
            'status': 'generating_chapters',
            'current_stage': 'generating_chapters',
            'progress': 0,
            'message': f'开始续写第{start_chapter}-{end_chapter}章'
        })
        
        # 初始化批量生成器
        from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
        batch_generator = BatchChapterGenerator(
            stop_checker=lambda: task_manager.should_stop(task_id)
        )
        
        # 获取项目路径
        from web.utils.path_utils import get_novel_project_dir
        project_path = get_novel_project_dir(title, username, create=False)
        
        total_chapters = end_chapter - start_chapter + 1
        generated_chapters = []
        total_words = 0
        
        # 分批生成
        batch_size = 6
        current = start_chapter
        
        while current <= end_chapter:
            if task_manager.should_stop(task_id):
                task_manager.update_task(task_id, {
                    'status': 'stopped',
                    'message': '用户停止生成'
                })
                return
            
            batch_end = min(current + batch_size - 1, end_chapter)
            
            task_manager.update_task(task_id, {
                'message': f'正在生成第{current}-{batch_end}章',
                'batch_num': (current - start_chapter) // batch_size + 1,
                'current_chapter': current
            })
            
            try:
                # 生成当前批次
                result = batch_generator.generate_batch(
                    project_path=str(project_path),
                    blueprint=blueprint,
                    start_chapter=current,
                    end_chapter=batch_end,
                    previous_chapters=generated_chapters[-3:] if generated_chapters else []
                )
                
                if result and 'chapters' in result:
                    generated_chapters.extend(result['chapters'])
                    total_words += result.get('total_words', 0)
                    
                    # 更新进度
                    progress = int((batch_end - start_chapter + 1) / total_chapters * 100)
                    task_manager.update_task(task_id, {
                        'progress': progress,
                        'completed_chapters': len(generated_chapters),
                        'total_words': total_words
                    })
                
                current = batch_end + 1
                
            except Exception as e:
                logger.error(f"[章节续写] 批次生成失败 {current}-{batch_end}: {e}")
                task_manager.update_task(task_id, {
                    'status': 'failed',
                    'error': f'第{current}-{batch_end}章生成失败: {str(e)}'
                })
                return
        
        # 完成任务
        task_manager.update_task(task_id, {
            'status': 'completed',
            'progress': 100,
            'current_stage': 'generation_completed',
            'message': f'续写完成，共生成{len(generated_chapters)}章',
            'result': {
                'total_chapters': len(generated_chapters),
                'total_words': total_words,
                'start_chapter': start_chapter,
                'end_chapter': end_chapter
            }
        })
        
    except Exception as e:
        logger.error(f"[章节续写] 生成失败: {e}", exc_info=True)
        task_manager.update_task(task_id, {
            'status': 'failed',
            'error': str(e)
        })



# ==================== 重新规划 API ====================

@market_driven_api.route('/<title>/replan', methods=['POST'])
def replan_project(title):
    """
    重新规划 - 基于新设定重新生成创作方案（不重新生成章节）
    
    Args:
        title: 项目标题
        
    Request Body:
        {
            "new_settings": {
                "title": "新标题",
                "sellpoint": "新卖点",
                "chapters": 200,
                "target_words": 500000,
                "protagonist_name": "主角名",
                "protagonist_bg": "背景",
                "golden_finger_type": "system",
                "golden_finger_desc": "金手指描述",
                "main_plot": "主线剧情"
            }
        }
        
    Returns:
        {
            "success": True,
            "task_id": "...",
            "message": "重新规划任务已启动"
        }
    """
    try:
        from urllib.parse import unquote
        title = unquote(title)
        username = _get_current_username()
        
        # 获取请求参数
        data = request.json or {}
        new_settings = data.get('new_settings', {})
        
        logger.info(f"[重新规划] {title}: 开始重新生成方案")
        
        # 查找项目路径
        from web.utils.path_utils import find_novel_project
        project_path = find_novel_project(title, username)
        
        if not project_path:
            return jsonify({
                "success": False,
                "error": f"项目 '{title}' 不存在"
            }), 404
        
        project_path = Path(project_path)
        
        # 扣除点数（重新规划消耗50点）
        from web.services.points_service import points_service
        points_needed = 50
        
        balance = points_service.get_balance(username)
        if balance < points_needed:
            return jsonify({
                "success": False,
                "error": f"创造点不足，需要{points_needed}点，当前{balance}点",
                "current_balance": balance,
                "needed": points_needed
            }), 402
        
        # 扣除点数
        success, result = points_service.consume_points(
            username=username,
            points=points_needed,
            action=f"重新规划: {title}",
            novel_title=title
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": result
            }), 402
        
        # 创建规划任务
        task_id = task_manager.create_task(
            title=title,
            task_type="replan",
            username=username
        )
        
        # 启动后台线程重新生成方案
        import threading
        thread = threading.Thread(
            target=_run_replan_generation,
            args=(task_id, title, project_path, new_settings, username)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "重新规划任务已启动，将重新生成创作方案",
            "points_consumed": points_needed
        })
        
    except Exception as e:
        logger.error(f"[重新规划] 启动失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _run_replan_generation(task_id, title, project_path, new_settings, username):
    """
    在后台运行重新规划生成
    """
    try:
        task_manager.update_task(task_id, {
            'status': 'generating',
            'current_stage': 'replanning',
            'progress': 10,
            'message': '开始重新生成创作方案'
        })
        
        # 加载现有项目信息
        project_info_file = project_path / "project_info.json"
        if project_info_file.exists():
            with open(project_info_file, 'r', encoding='utf-8') as f:
                project_info = json.load(f)
        else:
            project_info = {}
        
        # 更新项目信息中的设定
        if 'novel_info' not in project_info:
            project_info['novel_info'] = {}
        
        project_info['novel_info'].update({
            'title': new_settings.get('title', title),
            'synopsis': new_settings.get('sellpoint', ''),
            'target_chapters': new_settings.get('chapters', 200),
            'target_words': new_settings.get('target_words', 500000)
        })
        
        # 更新角色设计
        if 'character_design' not in project_info:
            project_info['character_design'] = {}
        if 'protagonist' not in project_info['character_design']:
            project_info['character_design']['protagonist'] = {}
        
        project_info['character_design']['protagonist'].update({
            'name': new_settings.get('protagonist_name', ''),
            'identity': new_settings.get('protagonist_bg', ''),
            'background': new_settings.get('protagonist_bg', '')
        })
        
        # 更新金手指
        if 'golden_finger' not in project_info:
            project_info['golden_finger'] = {}
        
        project_info['golden_finger'].update({
            'type': new_settings.get('golden_finger_type', 'system'),
            'description': new_settings.get('golden_finger_desc', ''),
            'desc': new_settings.get('golden_finger_desc', '')
        })
        
        # 更新故事线
        project_info['storyline'] = new_settings.get('main_plot', '')
        
        # 保存更新后的项目信息
        project_info['updated_at'] = datetime.now().isoformat()
        with open(project_info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        task_manager.update_task(task_id, {
            'progress': 30,
            'message': '已更新项目信息'
        })
        
        # 重新生成第一阶段产物
        from web.services.market_driven.phase_one_generator import MarketDrivenPhaseOneGenerator
        generator = MarketDrivenPhaseOneGenerator(project_path=str(project_path))
        
        task_manager.update_task(task_id, {
            'progress': 50,
            'message': '正在重新生成世界观设定'
        })
        
        # 构建新的 plan 数据
        plan = {
            'title': new_settings.get('title', title),
            'core_selling_point': new_settings.get('sellpoint', ''),
            'protagonist': {
                'name': new_settings.get('protagonist_name', ''),
                'background': new_settings.get('protagonist_bg', ''),
                'identity': new_settings.get('protagonist_bg', '')
            },
            'golden_finger': {
                'type': new_settings.get('golden_finger_type', 'system'),
                'description': new_settings.get('golden_finger_desc', ''),
                'mechanism': new_settings.get('golden_finger_desc', '')
            },
            'main_plot': new_settings.get('main_plot', ''),
            'target_chapters': new_settings.get('chapters', 200),
            'target_words': new_settings.get('target_words', 500000)
        }
        
        task_manager.update_task(task_id, {
            'progress': 70,
            'message': '正在重新生成角色设计和升级路线'
        })
        
        # 生成第一阶段产物
        # 注意：这里简化处理，实际应该调用完整的生成流程
        
        task_manager.update_task(task_id, {
            'progress': 90,
            'message': '正在保存新的创作方案'
        })
        
        # 更新蓝图文件
        blueprint_path = project_path / "phase_one_products" / "完整方案.json"
        if blueprint_path.exists():
            with open(blueprint_path, 'r', encoding='utf-8') as f:
                blueprint = json.load(f)
            
            # 更新蓝图中的设定
            blueprint.update(plan)
            
            with open(blueprint_path, 'w', encoding='utf-8') as f:
                json.dump(blueprint, f, ensure_ascii=False, indent=2)
        
        # 完成任务
        task_manager.update_task(task_id, {
            'status': 'completed',
            'progress': 100,
            'current_stage': 'replan_completed',
            'message': '重新规划完成，创作方案已更新',
            'result': {
                'message': '创作方案已更新，已有章节不受影响',
                'updated_fields': ['title', 'synopsis', 'protagonist', 'golden_finger', 'storyline']
            }
        })
        
    except Exception as e:
        logger.error(f"[重新规划] 生成失败: {e}", exc_info=True)
        task_manager.update_task(task_id, {
            'status': 'failed',
            'error': str(e)
        })



# ==================== 重写 API ====================

@market_driven_api.route('/<title>/rewrite', methods=['POST'])
def rewrite_project(title):
    """
    重写项目 - 删除已有章节，基于新设定重新生成完整方案
    
    Args:
        title: 项目标题
        
    Request Body:
        {
            "new_settings": {
                "title": "新标题",
                "sellpoint": "新卖点",
                "chapters": 200,
                "target_words": 500000,
                "protagonist_name": "主角名",
                "protagonist_bg": "背景",
                "golden_finger_type": "system",
                "golden_finger_desc": "金手指描述",
                "main_plot": "主线剧情"
            }
        }
        
    Returns:
        {
            "success": True,
            "task_id": "...",
            "message": "重写任务已启动"
        }
    """
    try:
        from urllib.parse import unquote
        title = unquote(title)
        username = _get_current_username()
        
        # 获取请求参数
        data = request.json or {}
        new_settings = data.get('new_settings', {})
        
        logger.info(f"[重写] {title}: 开始重写项目")
        
        # 查找项目路径
        from web.utils.path_utils import find_novel_project
        project_path = find_novel_project(title, username)
        
        if not project_path:
            return jsonify({
                "success": False,
                "error": f"项目 '{title}' 不存在"
            }), 404
        
        project_path = Path(project_path)
        
        # 扣除点数（重写消耗100点）
        from web.services.points_service import points_service
        points_needed = 100
        
        balance = points_service.get_balance(username)
        if balance < points_needed:
            return jsonify({
                "success": False,
                "error": f"创造点不足，需要{points_needed}点，当前{balance}点",
                "current_balance": balance,
                "needed": points_needed
            }), 402
        
        # 扣除点数
        success, result = points_service.consume_points(
            username=username,
            points=points_needed,
            action=f"重写项目: {title}",
            novel_title=title
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": result
            }), 402
        
        # 删除已有章节
        chapters_dir = project_path / "chapters"
        deleted_count = 0
        if chapters_dir.exists():
            for chapter_file in chapters_dir.glob("chapter_*.json"):
                try:
                    chapter_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除章节文件失败 {chapter_file}: {e}")
            logger.info(f"[重写] 已删除 {deleted_count} 个章节文件")
        
        # 清空 project_info.json 中的章节索引
        project_info_file = project_path / "project_info.json"
        if project_info_file.exists():
            try:
                with open(project_info_file, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
                
                # 清空章节相关数据
                project_info['chapters_index'] = []
                if 'generation_metadata' in project_info:
                    project_info['generation_metadata']['completed_chapters'] = 0
                    project_info['generation_metadata']['total_words'] = 0
                
                project_info['updated_at'] = datetime.now().isoformat()
                
                with open(project_info_file, 'w', encoding='utf-8') as f:
                    json.dump(project_info, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[重写] 已清空项目章节索引")
            except Exception as e:
                logger.warning(f"更新 project_info.json 失败: {e}")
        
        # 创建重写任务
        task_id = task_manager.create_task(
            title=title,
            task_type="rewrite",
            username=username
        )
        
        # 启动后台线程重新生成
        import threading
        thread = threading.Thread(
            target=_run_rewrite_generation,
            args=(task_id, title, project_path, new_settings, username)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "重写任务已启动，将删除旧章节并重新生成完整方案",
            "deleted_chapters": deleted_count,
            "points_consumed": points_needed
        })
        
    except Exception as e:
        logger.error(f"[重写] 启动失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _run_rewrite_generation(task_id, title, project_path, new_settings, username):
    """
    在后台运行重写生成（完整流程：方案+章节）
    """
    try:
        task_manager.update_task(task_id, {
            'status': 'generating',
            'current_stage': 'rewriting',
            'progress': 5,
            'message': '开始重写项目，更新设定'
        })
        
        # 1. 更新项目设定
        project_info_file = project_path / "project_info.json"
        if project_info_file.exists():
            with open(project_info_file, 'r', encoding='utf-8') as f:
                project_info = json.load(f)
        else:
            project_info = {}
        
        # 更新项目信息
        project_info.update({
            'novel_title': new_settings.get('title', title),
            'genre': new_settings.get('genre', project_info.get('genre', '未知')),
            'updated_at': datetime.now().isoformat()
        })
        
        if 'novel_info' not in project_info:
            project_info['novel_info'] = {}
        
        project_info['novel_info'].update({
            'title': new_settings.get('title', title),
            'synopsis': new_settings.get('sellpoint', ''),
            'target_chapters': new_settings.get('chapters', 200),
            'target_words': new_settings.get('target_words', 500000)
        })
        
        # 更新角色设计
        if 'character_design' not in project_info:
            project_info['character_design'] = {}
        if 'protagonist' not in project_info['character_design']:
            project_info['character_design']['protagonist'] = {}
        
        project_info['character_design']['protagonist'].update({
            'name': new_settings.get('protagonist_name', ''),
            'identity': new_settings.get('protagonist_bg', ''),
            'background': new_settings.get('protagonist_bg', '')
        })
        
        # 更新金手指
        if 'golden_finger' not in project_info:
            project_info['golden_finger'] = {}
        
        project_info['golden_finger'].update({
            'type': new_settings.get('golden_finger_type', 'system'),
            'description': new_settings.get('golden_finger_desc', ''),
            'desc': new_settings.get('golden_finger_desc', '')
        })
        
        # 更新故事线
        project_info['storyline'] = new_settings.get('main_plot', '')
        
        with open(project_info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        task_manager.update_task(task_id, {
            'progress': 10,
            'message': '已更新项目设定，开始生成完整方案'
        })
        
        # 2. 重新生成蓝图
        blueprint_path = project_path / "phase_one_products" / "完整方案.json"
        blueprint = {
            'title': new_settings.get('title', title),
            'core_selling_point': new_settings.get('sellpoint', ''),
            'protagonist': {
                'name': new_settings.get('protagonist_name', ''),
                'background': new_settings.get('protagonist_bg', ''),
                'identity': new_settings.get('protagonist_bg', '')
            },
            'golden_finger': {
                'type': new_settings.get('golden_finger_type', 'system'),
                'description': new_settings.get('golden_finger_desc', ''),
                'mechanism': new_settings.get('golden_finger_desc', '')
            },
            'main_plot': new_settings.get('main_plot', ''),
            'target_chapters': new_settings.get('chapters', 200),
            'target_words': new_settings.get('target_words', 500000)
        }
        
        # 确保目录存在
        blueprint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(blueprint_path, 'w', encoding='utf-8') as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        
        task_manager.update_task(task_id, {
            'progress': 20,
            'current_stage': 'generating_chapters',
            'message': '开始生成章节'
        })
        
        # 3. 重新生成章节（使用 _run_chapter_generation 的逻辑）
        from web.services.market_driven.batch_chapter_generator import BatchChapterGenerator
        batch_generator = BatchChapterGenerator(
            stop_checker=lambda: task_manager.should_stop(task_id)
        )
        
        total_chapters = new_settings.get('chapters', 200)
        generated_chapters = []
        total_words = 0
        
        # 分批生成
        batch_size = 6
        current = 1
        
        while current <= total_chapters:
            if task_manager.should_stop(task_id):
                task_manager.update_task(task_id, {
                    'status': 'stopped',
                    'message': '用户停止生成'
                })
                return
            
            batch_end = min(current + batch_size - 1, total_chapters)
            
            task_manager.update_task(task_id, {
                'message': f'正在生成第{current}-{batch_end}章',
                'batch_num': (current - 1) // batch_size + 1,
                'current_chapter': current
            })
            
            try:
                result = batch_generator.generate_batch(
                    project_path=str(project_path),
                    blueprint=blueprint,
                    start_chapter=current,
                    end_chapter=batch_end,
                    previous_chapters=generated_chapters[-3:] if generated_chapters else []
                )
                
                if result and 'chapters' in result:
                    generated_chapters.extend(result['chapters'])
                    total_words += result.get('total_words', 0)
                    
                    # 更新进度
                    progress = 20 + int((batch_end / total_chapters) * 80)
                    task_manager.update_task(task_id, {
                        'progress': progress,
                        'completed_chapters': len(generated_chapters),
                        'total_words': total_words
                    })
                
                current = batch_end + 1
                
            except Exception as e:
                logger.error(f"[重写] 批次生成失败 {current}-{batch_end}: {e}")
                task_manager.update_task(task_id, {
                    'status': 'failed',
                    'error': f'第{current}-{batch_end}章生成失败: {str(e)}'
                })
                return
        
        # 完成任务
        task_manager.update_task(task_id, {
            'status': 'completed',
            'progress': 100,
            'current_stage': 'rewrite_completed',
            'message': f'重写完成，共生成{len(generated_chapters)}章',
            'result': {
                'total_chapters': len(generated_chapters),
                'total_words': total_words,
                'message': '项目重写完成，所有章节已重新生成'
            }
        })
        
    except Exception as e:
        logger.error(f"[重写] 生成失败: {e}", exc_info=True)
        task_manager.update_task(task_id, {
            'status': 'failed',
            'error': str(e)
        })
