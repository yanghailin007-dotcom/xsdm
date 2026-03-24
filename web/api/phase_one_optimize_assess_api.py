# -*- coding: utf-8 -*-
"""
Phase One Optimize Then Assess API
第一阶段优化+质量评估组合API

提供端点:
- POST /api/phase-one/optimize-then-assess - 启动优化+评估任务
- GET /api/phase-one/optimize-then-assess/<task_id> - 获取任务状态
- POST /api/phase-one/optimize-then-assess/<task_id>/cancel - 取消任务
"""

import logging
import threading
from flask import Blueprint, request, jsonify
from pathlib import Path
import json

# 设置日志
logger = logging.getLogger(__name__)

# 创建蓝图
phase_one_optimize_assess_api = Blueprint('phase_one_optimize_assess_api', __name__, 
                                          url_prefix='/api/phase-one')

# 导入服务
try:
    from web.services.phase_one_optimize_then_assess import (
        PhaseOneOptimizeThenAssess, 
        optimize_assess_task_manager
    )
    from web.utils.path_utils import get_user_novel_dir
    logger.info("✅ PhaseOneOptimizeThenAssess 导入成功")
except ImportError as e:
    logger.error(f"❌ PhaseOneOptimizeThenAssess 导入失败: {e}")
    PhaseOneOptimizeThenAssess = None
    optimize_assess_task_manager = None


@phase_one_optimize_assess_api.route('/optimize-then-assess', methods=['POST'])
def start_optimize_then_assess():
    """
    启动优化+评估组合任务
    
    这是第一阶段最后一步的完整流程:
    1. 加载第一阶段所有产品
    2. 执行三轮智能优化
    3. 保存优化结果
    4. 执行质量评估
    
    请求体:
    {
        "title": "小说标题",
        "platform": "fanqie"  // 可选,默认fanqie
    }
    
    响应:
    {
        "task_id": "uuid",
        "status": "pending",
        "message": "优化+评估任务已创建"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        title = data.get('title')
        platform = data.get('platform', 'fanqie')
        
        if not title:
            return jsonify({"error": "缺少必要参数: title"}), 400
        
        # 检查服务是否可用
        if PhaseOneOptimizeThenAssess is None:
            return jsonify({"error": "优化+评估服务暂时不可用"}), 503
        
        # 获取用户目录
        from flask import session
        username = session.get('username', 'anonymous')
        user_novel_dir = get_user_novel_dir(username=username, create=False)
        
        # 创建任务
        task_id = optimize_assess_task_manager.create_task(title, platform)
        
        # 在后台线程中运行
        def run_optimize_then_assess():
            try:
                # 初始化服务
                from src.core.APIClient import APIClient
                from config.config import CONFIG
                api_client = APIClient(CONFIG)
                
                service = PhaseOneOptimizeThenAssess(
                    api_client=api_client,
                    user_novel_dir=user_novel_dir
                )
                
                # 设置进度回调
                def progress_callback(step: str, progress: int, message: str):
                    # 映射步骤到状态
                    phase_map = {
                        "loading": "loading_products",
                        "optimization": "optimizing",
                        "assessment": "assessing"
                    }
                    current_phase = phase_map.get(step, step)
                    
                    optimize_assess_task_manager.update_task(
                        task_id,
                        status="running",
                        progress=progress,
                        current_phase=current_phase,
                        message=message
                    )
                
                service.set_progress_callback(progress_callback)
                
                # 更新状态为运行中
                optimize_assess_task_manager.update_task(
                    task_id,
                    status="running",
                    progress=0,
                    current_phase="loading_products",
                    message="正在初始化..."
                )
                
                # 执行优化+评估
                result = service.optimize_then_assess(title, platform)
                
                # 更新完成状态
                optimize_assess_task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_phase="completed",
                    message=result.get("message", "完成"),
                    result=result
                )
                
                logger.info(f"✅ 优化+评估任务 {task_id} 完成")
                
            except Exception as e:
                logger.error(f"❌ 优化+评估任务 {task_id} 失败: {e}", exc_info=True)
                optimize_assess_task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"任务失败: {str(e)}"
                )
        
        # 启动后台线程
        thread = threading.Thread(target=run_optimize_then_assess)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "优化+评估任务已创建并开始运行"
        }), 202
        
    except Exception as e:
        logger.error(f"❌ 创建优化+评估任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_optimize_assess_api.route('/optimize-then-assess/<task_id>', methods=['GET'])
def get_optimize_assess_status(task_id: str):
    """
    获取优化+评估任务状态
    
    响应:
    {
        "task_id": "uuid",
        "novel_title": "小说标题",
        "status": "running",
        "progress": 45,
        "current_phase": "optimizing",
        "message": "正在执行平台风格适配...",
        "optimization": {...},  // 完成后包含
        "assessment": {...}     // 完成后包含
    }
    """
    try:
        if optimize_assess_task_manager is None:
            return jsonify({"error": "服务暂时不可用"}), 503
        
        task = optimize_assess_task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        # 构建响应
        response = {
            "task_id": task["id"],
            "novel_title": task["novel_title"],
            "platform": task["platform"],
            "status": task["status"],
            "progress": task["progress"],
            "current_phase": task["current_phase"],
            "message": task["message"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"]
        }
        
        # 如果完成，包含结果
        if task["status"] == "completed" and task["result"]:
            result = task["result"]
            response["has_optimization"] = result.get("has_optimization", False)
            response["has_assessment"] = result.get("has_assessment", False)
            response["combined_score"] = result.get("combined_score")
            
            # 简化返回，避免数据过大
            if result.get("optimization"):
                response["optimization_summary"] = {
                    "overall_score": result["optimization"].get("overall_score"),
                    "rounds": {
                        k: {"score": v.get("score")} 
                        for k, v in result["optimization"].get("rounds", {}).items()
                    }
                }
            
            if result.get("assessment"):
                response["assessment_summary"] = {
                    "overall_score": result["assessment"].get("overall_score"),
                    "readiness": result["assessment"].get("readiness")
                }
        
        # 如果失败，包含错误信息
        if task["status"] == "failed" and task["error"]:
            response["error"] = task["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_optimize_assess_api.route('/optimize-then-assess/<task_id>/result', methods=['GET'])
def get_optimize_assess_result(task_id: str):
    """
    获取优化+评估完整结果
    
    返回完整的优化结果和质量评估报告
    """
    try:
        if optimize_assess_task_manager is None:
            return jsonify({"error": "服务暂时不可用"}), 503
        
        task = optimize_assess_task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        if task["status"] != "completed":
            return jsonify({
                "error": "任务尚未完成",
                "status": task["status"],
                "progress": task["progress"]
            }), 400
        
        return jsonify({
            "task_id": task_id,
            "result": task.get("result", {})
        }), 200
        
    except Exception as e:
        logger.error(f"❌ 获取任务结果失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_optimize_assess_api.route('/optimize-then-assess/<task_id>/cancel', methods=['POST'])
def cancel_optimize_assess(task_id: str):
    """
    取消优化+评估任务
    
    注意: 只能取消待运行或运行中的任务
    """
    try:
        if optimize_assess_task_manager is None:
            return jsonify({"error": "服务暂时不可用"}), 503
        
        task = optimize_assess_task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        if task["status"] not in ["pending", "running"]:
            return jsonify({
                "error": f"无法取消状态为 '{task['status']}' 的任务"
            }), 400
        
        optimize_assess_task_manager.update_task(
            task_id,
            status="cancelled",
            message="任务已取消"
        )
        
        return jsonify({
            "success": True,
            "message": "任务已取消"
        }), 200
        
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 应用启动时的初始化
app = None  # 将在注册时由 web_server_refactored.py 设置
