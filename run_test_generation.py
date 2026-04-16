# -*- coding: utf-8 -*-
"""
后台测试生成脚本
使用修复后的子主题 prompt 重新生成一本神豪文-投资流小说
"""

import sys
import json
import threading
import time

sys.path.insert(0, r'c:\work\xsdm')

# 初始化日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 导入依赖
from src.core.APIClient import APIClient
from config.config import CONFIG
from web.api.market_driven_api import task_manager, _run_plan_and_products_conversation, _run_chapter_generation
from web.services.market_driven.project_manager import create_unified_project

# 配置
GENRE = "god-tier-spending"
USER_CHOICES = {
    "title": "开局爆仓，我能看到投资回报率（新版）",
    "protagonist_name": "陆诚",
    "golden_finger_desc": "能看到任意投资品的精确未来收益率",
    "main_plot": "从87元余额开始，依靠投资回报率之眼逆袭金融圈，建立诚盛资本",
    "sub_theme": "investment_guru",
    "target_words": 500000,
    "chapters": 200
}
USERNAME = "yanghailin"
USER_ID = 3


def main():
    logger.info("=" * 60)
    logger.info("🚀 启动后台测试生成 | 子主题: investment_guru")
    logger.info("=" * 60)
    
    # 初始化 API 客户端
    api_client = APIClient(CONFIG)
    api_client.set_username(USERNAME)
    
    # 创建任务
    task_id = task_manager.create_task(GENRE, USER_CHOICES)
    task_manager.update_task(
        task_id,
        username=USERNAME,
        user_id=USER_ID,
        current_stage='initializing',
        message='启动测试生成任务...',
        target_words=USER_CHOICES["target_words"]
    )
    logger.info(f"[TestGen] 任务已创建: {task_id}")
    
    # 先创建项目目录并写入 sub_theme
    try:
        project_path = create_unified_project(
            USER_CHOICES["title"],
            "market_driven",
            GENRE,
            USERNAME,
            writing_style=None
        )
        # 写入 sub_theme 到 project_info.json
        info_path = project_path / "project_info.json"
        if info_path.exists():
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            info["sub_theme"] = "investment_guru"
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            logger.info(f"[TestGen] 已写入 sub_theme 到项目: {project_path}")
    except Exception as e:
        logger.warning(f"[TestGen] 预创建项目失败（可能已存在）: {e}")
    
    # 后台生成
    def run_generation():
        try:
            # 第1阶段：对话模式生成产物
            _run_plan_and_products_conversation(
                task_id=task_id,
                genre=GENRE,
                user_choices=USER_CHOICES,
                api_client=api_client
            )
            
            # 检查是否被 block
            task = task_manager.get_task(task_id)
            if task and task.get('status') == 'alignment_failed':
                logger.error(f"[TestGen] 核心设定审核未通过，任务终止")
                return
            
            # 第2阶段：生成章节
            _run_chapter_generation(
                task_id=task_id,
                genre=GENRE,
                target_words=USER_CHOICES["target_words"],
                api_client=api_client
            )
            
            # 完成
            task_manager.update_task(
                task_id,
                status="completed",
                progress=100,
                current_stage="generation_completed",
                message="测试生成全部完成"
            )
            logger.info(f"[TestGen] ✅ 任务完成: {task_id}")
            
        except Exception as e:
            logger.error(f"[TestGen] 生成失败: {e}", exc_info=True)
            task_manager.update_task(
                task_id,
                status="failed",
                error=str(e),
                message=f"生成失败: {str(e)}"
            )
    
    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()
    
    logger.info(f"[TestGen] 后台线程已启动，任务ID: {task_id}")
    logger.info("[TestGen] 您可以使用任务ID查看进度")
    
    # 保持主线程运行
    while thread.is_alive():
        time.sleep(10)
        task = task_manager.get_task(task_id)
        if task:
            logger.info(f"[TestGen] 进度: {task.get('progress', 0)}% | 阶段: {task.get('current_stage', 'unknown')} | 状态: {task.get('status', 'unknown')}")


if __name__ == "__main__":
    main()
