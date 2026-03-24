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
    获取可选择的题材列表
    
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
        ]
    }
    """
    try:
        if TropeAnalyzer is None:
            return jsonify({"error": "服务暂不可用"}), 503
        
        genres = TropeAnalyzer.get_available_genres()
        
        # 格式化输出
        genre_list = []
        for genre_id, info in genres.items():
            genre_list.append({
                "id": genre_id,
                "name": genre_id,
                **info
            })
        
        return jsonify({
            "genres": genre_list,
            "total": len(genre_list)
        }), 200
        
    except Exception as e:
        logger.error(f"获取题材列表失败: {e}", exc_info=True)
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
        "target_words": 300000,
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
        target_words = data.get('target_words', 300000)
        options = data.get('options', {})
        
        if not genre:
            return jsonify({"error": "缺少必要参数: genre"}), 400
        
        # 创建任务
        task_id = task_manager.create_task(genre, user_choices)
        
        # 在后台执行完整生成流程
        def run_full_generation():
            api_client = None
            try:
                # 初始化API客户端
                try:
                    from src.core.APIClient import APIClient
                    from config.config import CONFIG
                    api_client = APIClient(CONFIG)
                except Exception as e:
                    logger.warning(f"APIClient初始化失败，将使用模拟模式: {e}")
                
                # 第1阶段：套路分析（传递user_choices以检查是否有前端缓存的分析结果）
                _run_trope_analysis(task_id, genre, api_client, user_choices)
                
                # 第2阶段：生成方案（如果不跳过）
                if not options.get('skip_phase_one', False):
                    _run_plan_generation(task_id, genre, user_choices, api_client)
                    _run_phase_one_products(task_id, genre, api_client)
                
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
            "estimated_time": "30-60分钟（取决于字数）"
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
    """生成方案"""
    task_manager.update_task(
        task_id,
        status="generating_plan",
        progress=20,
        current_stage="generating_plan",
        message="正在基于套路生成方案..."
    )
    
    try:
        # 获取套路分析结果
        task = task_manager.get_task(task_id)
        tropes = task.get("result", {}).get("tropes", {})
        
        # 检查前端是否传递了分析上下文（复用之前的分析结果）
        analysis_context = user_choices.get('analysis_context')
        if not tropes and analysis_context:
            logger.info(f"[Task {task_id}] 使用前端传递的分析上下文")
            tropes = analysis_context
            # 保存到任务结果中
            task_manager.update_task(
                task_id,
                result={"tropes": tropes}
            )
        
        if not tropes:
            # 如果没有缓存的套路，重新分析
            analyzer = TropeAnalyzer(api_client=api_client)
            tropes = analyzer.analyze_genre(genre)
        
        # 生成方案（传递完整上下文给AI）
        generator = MarketDrivenPlanGenerator(api_client=api_client)
        # 将分析上下文注入到用户选择中，供AI参考
        enriched_user_choices = {
            **user_choices,
            "trope_analysis": tropes  # 确保AI能访问分析结果
        }
        plan = generator.generate_plan(genre, tropes, enriched_user_choices)
        
        # 更新任务结果
        current_result = task.get("result", {})
        current_result["plan"] = plan
        
        task_manager.update_task(
            task_id,
            progress=30,
            result=current_result,
            message="方案生成完成"
        )
        
        logger.info(f"[Task {task_id}] 方案生成完成")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 方案生成失败: {e}")
        raise


def _run_phase_one_products(task_id: str, genre: str, api_client=None):
    """生成第一阶段产物"""
    task_manager.update_task(
        task_id,
        status="generating_products",
        progress=35,
        current_stage="generating_products",
        message="正在生成世界观、角色等设定..."
    )
    
    try:
        # 获取套路和方案
        task = task_manager.get_task(task_id)
        tropes = task.get("result", {}).get("tropes", {})
        plan = task.get("result", {}).get("plan", {})
        
        # 生成第一阶段产物
        generator = MarketDrivenPhaseOneGenerator(api_client=api_client)
        
        products = generator.generate_all_products(genre, tropes, plan)
        
        # 保存产物到项目目录
        novel_title = plan.get("recommended_title", f"未命名_{task_id[:8]}")
        save_path = save_phase_one_products(novel_title, products, task_id, genre, plan)
        
        # 更新任务结果
        current_result = task.get("result", {})
        current_result["products"] = products
        current_result["save_path"] = str(save_path)
        
        task_manager.update_task(
            task_id,
            progress=50,
            result=current_result,
            message="第一阶段产物生成完成"
        )
        
        logger.info(f"[Task {task_id}] 第一阶段产物生成完成，保存到: {save_path}")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] 第一阶段产物生成失败: {e}")
        raise


def save_phase_one_products(novel_title: str, products: Dict, task_id: str, 
                            genre: str = "", plan: Dict = None) -> Path:
    """保存第一阶段产物到项目目录（使用统一的项目信息管理）"""
    
    # 使用统一的项目管理创建项目
    project_path = create_unified_project(
        novel_title=novel_title,
        generation_mode="market_driven",
        genre=genre
    )
    
    # 更新项目信息
    project_info = UnifiedProjectManager.load_project_info(project_path)
    
    # 设置基本信息
    project_info["novel_synopsis"] = plan.get("core_selling_points", [{}])[0].get("point", "") if plan else ""
    project_info["genre"] = genre
    
    # 设置模式特定信息
    UnifiedProjectManager.set_mode_specific_info(
        project_info,
        "market_driven",
        {
            "task_id": task_id,
            "tropes_analysis": products.get("based_on_tropes", {}),
            "plan": plan
        }
    )
    
    # 保存产物
    for product_name in products:
        if product_name in ["writing_style_guide", "market_analysis", "core_worldview",
                           "faction_system", "character_design", "global_growth_plan",
                           "stage_writing_plans", "emotional_blueprint", "expectation_mapping"]:
            file_path = ProjectDirectoryManager.get_product_path(project_path, product_name)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(products[product_name], f, ensure_ascii=False, indent=2)
    
    # 保存项目信息
    UnifiedProjectManager.save_project_info(project_path, project_info)
    
    return project_path


def _run_chapter_generation(task_id: str, genre: str, target_words: int, api_client=None):
    """生成章节"""
    total_chapters = target_words // 2500
    
    task_manager.update_task(
        task_id,
        status="generating_chapters",
        progress=55,
        current_stage="generating_chapters",
        message=f"开始生成章节，目标{total_chapters}章约{target_words}字..."
    )
    
    try:
        # 获取任务数据
        task = task_manager.get_task(task_id)
        novel_title = task.get("result", {}).get("plan", {}).get("recommended_title", f"未命名_{task_id[:8]}")
        tropes = task.get("result", {}).get("tropes", {})
        plan = task.get("result", {}).get("plan", {})
        products = task.get("result", {}).get("products", {})
        
        # 生成BluePrint
        blueprint_gen = ChapterBluePrintGenerator()
        blueprint = blueprint_gen.generate_blueprint(target_words, tropes, plan)
        
        # 准备novel_data
        novel_data = {
            "core_worldview": products.get("core_worldview", {}),
            "character_design": products.get("character_design", {}),
            "faction_system": products.get("faction_system", {})
        }
        
        # 批量生成
        batch_gen = BatchChapterGenerator(api_client=api_client)
        batches = (total_chapters + 9) // 10  # 每批10章
        
        all_results = []
        
        for batch_num in range(1, batches + 1):
            start = (batch_num - 1) * 10 + 1
            end = min(batch_num * 10, total_chapters)
            
            task_manager.update_task(
                task_id,
                progress=int(55 + (batch_num / batches) * 35),
                message=f"正在生成第{batch_num}/{batches}批章节（第{start}-{end}章）..."
            )
            
            # 生成本批
            result = batch_gen.generate_batch(
                novel_title=novel_title,
                start_chapter=start,
                end_chapter=end,
                blueprint=blueprint,
                tropes=tropes,
                novel_data=novel_data
            )
            
            all_results.append(result)
            
            logger.info(f"[Task {task_id}] 第{batch_num}批完成: {len(result['generated'])}章")
        
        # 汇总结果
        total_generated = sum(len(r["generated"]) for r in all_results)
        total_words = sum(r["total_words"] for r in all_results)
        total_failed = sum(len(r["failed"]) for r in all_results)
        avg_quality = sum(r["avg_quality"] for r in all_results) / len(all_results) if all_results else 0
        
        # 更新任务结果
        current_result = task.get("result", {})
        current_result["chapter_generation"] = {
            "total_chapters": total_generated,
            "total_words": total_words,
            "failed_chapters": total_failed,
            "avg_quality": avg_quality,
            "blueprint": blueprint
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
        
        # 加载项目
        base_path = Path("小说项目") / novel_title
        project_info = UnifiedProjectManager.load_project_info(base_path)
        
        if not project_info:
            return jsonify({"error": "项目不存在"}), 404
        
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


# 应用启动时的初始化
app = None  # 将在注册时由 web_server_refactored.py 设置
