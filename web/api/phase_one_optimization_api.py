# -*- coding: utf-8 -*-
"""
Phase One Optimization API
第一阶段产品优化API

提供端点:
- POST /api/phase-one/optimize - 启动优化任务
- GET /api/phase-one/optimize/<task_id> - 获取任务状态
- GET /api/phase-one/tasks - 列出任务
"""

import logging
import threading
from flask import Blueprint, request, jsonify
from pathlib import Path
import sys
import json

# 设置日志
logger = logging.getLogger(__name__)

# 创建蓝图
phase_one_api = Blueprint('phase_one_api', __name__, url_prefix='/api/phase-one')

# 导入优化器
try:
    from web.services.phase_one_optimizer import PhaseOneOptimizer, task_manager, OptimizationTaskManager
    logger.info("✅ PhaseOneOptimizer 导入成功")
except ImportError as e:
    logger.error(f"❌ PhaseOneOptimizer 导入失败: {e}")
    PhaseOneOptimizer = None
    task_manager = None


def get_project_path(title: str) -> Path:
    """获取项目路径"""
    base_path = Path("小说项目")
    # 清理标题中的非法字符
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    return base_path / safe_title


def load_phase_one_products(title: str) -> dict:
    """
    加载第一阶段产品数据
    
    Args:
        title: 小说标题
        
    Returns:
        产品数据字典
    """
    project_path = get_project_path(title)
    
    products = {}
    product_files = {
        'worldview': '世界观设定.json',
        'characters': '核心角色.json',
        'factions': '势力设定.json',
        'growth': '升级路线.json',
        'writing': '写作风格.json',
        'storyline': '故事线.json',
        'market_analysis': '市场分析.json'
    }
    
    for key, filename in product_files.items():
        file_path = project_path / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    products[key] = json.load(f)
                logger.debug(f"✅ 已加载 {filename}")
            except Exception as e:
                logger.warning(f"⚠️ 加载 {filename} 失败: {e}")
                products[key] = None
        else:
            logger.debug(f"⚠️ 文件不存在: {file_path}")
            products[key] = None
    
    return products


@phase_one_api.route('/optimize', methods=['POST'])
def start_phase_one_optimization():
    """
    启动第一阶段产品优化任务
    
    请求体:
    {
        "title": "小说标题",
        "platform": "fanqie"  // 可选,默认fanqie
    }
    
    响应:
    {
        "task_id": "uuid",
        "status": "pending",
        "message": "优化任务已创建"
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
        
        # 检查优化器是否可用
        if PhaseOneOptimizer is None:
            return jsonify({"error": "优化服务暂时不可用"}), 503
        
        # 加载产品数据
        products = load_phase_one_products(title)
        
        # 检查是否有有效的产品数据
        valid_products = {k: v for k, v in products.items() if v is not None}
        if not valid_products:
            return jsonify({
                "error": "未找到有效的产品数据",
                "message": f"项目 '{title}' 似乎没有生成第一阶段产品"
            }), 404
        
        logger.info(f"加载了 {len(valid_products)} 个产品: {list(valid_products.keys())}")
        
        # 创建任务
        task_id = task_manager.create_task(title, platform)
        
        # 在后台线程中运行优化
        def run_optimization():
            try:
                task_manager.update_task(
                    task_id,
                    status="running",
                    progress=5,
                    current_round="platform_adaptation",
                    message="正在初始化优化器..."
                )
                
                # 创建优化器实例
                optimizer = PhaseOneOptimizer()
                
                # 更新进度回调
                def progress_callback(round_name: str, progress: int, message: str):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        current_round=round_name,
                        message=message
                    )
                
                # 执行优化
                task_manager.update_task(
                    task_id,
                    progress=10,
                    message="开始第一轮:平台风格适配..."
                )
                
                result = optimizer.optimize(valid_products, platform)
                
                # 更新任务完成状态
                task_manager.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    current_round="completed",
                    message="优化完成",
                    result=result
                )
                
                logger.info(f"✅ 优化任务 {task_id} 完成")
                
            except Exception as e:
                logger.error(f"❌ 优化任务 {task_id} 失败: {e}", exc_info=True)
                task_manager.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    message=f"优化失败: {str(e)}"
                )
        
        # 启动后台线程
        thread = threading.Thread(target=run_optimization)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "status": "pending",
            "message": "优化任务已创建并开始运行"
        }), 202
        
    except Exception as e:
        logger.error(f"❌ 创建优化任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_api.route('/optimize/<task_id>', methods=['GET'])
def get_optimization_status(task_id: str):
    """
    获取优化任务状态
    
    响应:
    {
        "task_id": "uuid",
        "status": "running",
        "progress": 45,
        "current_round": "data_matching",
        "message": "正在进行数据匹配分析...",
        "rounds": {
            "platform_adaptation": { "score": 78, ... }
        }
    }
    """
    try:
        if task_manager is None:
            return jsonify({"error": "优化服务暂时不可用"}), 503
        
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        
        # 构建响应
        response = {
            "task_id": task["id"],
            "title": task["title"],
            "platform": task["platform"],
            "status": task["status"],
            "progress": task["progress"],
            "current_round": task["current_round"],
            "message": task["message"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"]
        }
        
        # 如果任务完成,包含结果
        if task["status"] == "completed" and task["result"]:
            response["rounds"] = task["result"].get("rounds", {})
            response["overall_score"] = task["result"].get("overall_score", 0)
            response["summary"] = task["result"].get("summary", "")
            response["priority_actions"] = task["result"].get("priority_actions", {})
        
        # 如果任务失败,包含错误信息
        if task["status"] == "failed" and task["error"]:
            response["error"] = task["error"]
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_api.route('/tasks', methods=['GET'])
def list_optimization_tasks():
    """
    列出优化任务
    
    查询参数:
    - title: 按小说标题筛选(可选)
    
    响应:
    {
        "tasks": [
            {
                "task_id": "uuid",
                "title": "小说标题",
                "status": "completed",
                "progress": 100,
                "created_at": "..."
            }
        ]
    }
    """
    try:
        if task_manager is None:
            return jsonify({"error": "优化服务暂时不可用"}), 503
        
        title = request.args.get('title')
        tasks = task_manager.list_tasks(title)
        
        # 简化响应
        simplified_tasks = []
        for task in tasks:
            simplified_tasks.append({
                "task_id": task["id"],
                "title": task["title"],
                "platform": task["platform"],
                "status": task["status"],
                "progress": task["progress"],
                "current_round": task["current_round"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"]
            })
        
        return jsonify({
            "tasks": simplified_tasks,
            "total": len(simplified_tasks)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ 列出任务失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@phase_one_api.route('/platforms', methods=['GET'])
def list_platforms():
    """
    获取支持的平台列表
    
    响应:
    {
        "platforms": [
            {
                "id": "fanqie",
                "name": "番茄小说",
                "description": "..."
            }
        ]
    }
    """
    try:
        platforms = [
            {
                "id": "fanqie",
                "name": "番茄小说",
                "description": "免费阅读平台,读者偏好快节奏爽文",
                "icon": "🍅"
            },
            {
                "id": "qidian",
                "name": "起点中文网",
                "description": "付费阅读平台,读者注重作品质量",
                "icon": "📖"
            },
            {
                "id": "general",
                "name": "通用优化",
                "description": "适用于多数平台的通用优化方案",
                "icon": "🌐"
            }
        ]
        
        return jsonify({"platforms": platforms}), 200
        
    except Exception as e:
        logger.error(f"❌ 获取平台列表失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 应用启动时的初始化
app = None  # 将在注册时由 web_server_refactored.py 设置
