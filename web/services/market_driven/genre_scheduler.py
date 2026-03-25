# -*- coding: utf-8 -*-
"""
Genre Auto-Update Scheduler
题材自动更新调度器

每周一自动调用AI分析市场趋势，生成新类型
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GenreUpdateScheduler:
    """
    题材自动更新调度器
    
    功能：
    1. 每周一凌晨2点自动执行AI分析
    2. 支持手动触发更新
    3. 防止重复执行
    """
    
    def __init__(self):
        self._scheduler = None
        self._job_id = "genre_auto_update"
        self._is_running = False
        self._lock = threading.Lock()
        
    def init_scheduler(self, app):
        """
        初始化调度器
        
        Args:
            app: Flask应用实例
        """
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            self._scheduler = BackgroundScheduler()
            
            # 添加每周一凌晨2点执行的任务
            self._scheduler.add_job(
                func=self._scheduled_update,
                trigger=CronTrigger(day_of_week='mon', hour=2, minute=0),
                id=self._job_id,
                name='Genre Auto Update',
                replace_existing=True,
                misfire_grace_time=3600  # 1小时的容错时间
            )
            
            self._scheduler.start()
            logger.info("[GenreScheduler] 调度器已启动，每周一凌晨2点自动更新题材")
            
        except ImportError:
            logger.warning("[GenreScheduler] APScheduler未安装，使用备用定时机制")
            self._init_fallback_scheduler()
        except Exception as e:
            logger.error(f"[GenreScheduler] 初始化调度器失败: {e}")
    
    def _init_fallback_scheduler(self):
        """备用定时机制（使用简单线程）"""
        def run_scheduler():
            while True:
                try:
                    now = datetime.now()
                    # 计算到下周一凌晨2点的时间
                    days_until_monday = (7 - now.weekday()) % 7
                    if days_until_monday == 0 and now.hour >= 2:
                        days_until_monday = 7
                    
                    next_run = now + timedelta(days=days_until_monday)
                    next_run = next_run.replace(hour=2, minute=0, second=0, microsecond=0)
                    
                    wait_seconds = (next_run - now).total_seconds()
                    
                    logger.info(f"[GenreScheduler] 下次更新时间: {next_run}, 等待 {wait_seconds/3600:.1f} 小时")
                    
                    # 等待到执行时间
                    threading.Event().wait(timeout=wait_seconds)
                    
                    # 执行更新
                    self._scheduled_update()
                    
                    # 等待1小时避免重复执行
                    threading.Event().wait(timeout=3600)
                    
                except Exception as e:
                    logger.error(f"[GenreScheduler] 备用调度器错误: {e}")
                    threading.Event().wait(timeout=3600)
        
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        logger.info("[GenreScheduler] 备用调度器已启动")
    
    def _scheduled_update(self):
        """定时执行的更新任务"""
        with self._lock:
            if self._is_running:
                logger.info("[GenreScheduler] 更新任务已在运行，跳过")
                return
            self._is_running = True
        
        try:
            logger.info("[GenreScheduler] 开始执行定时题材更新...")
            
            # 执行更新
            result = self._do_update()
            
            if result:
                logger.info("[GenreScheduler] 题材更新完成")
            else:
                logger.warning("[GenreScheduler] 题材更新未生成新类型")
                
        except Exception as e:
            logger.error(f"[GenreScheduler] 定时更新失败: {e}", exc_info=True)
        finally:
            self._is_running = False
    
    def _do_update(self) -> bool:
        """
        执行实际的更新操作
        
        Returns:
            是否成功生成新类型
        """
        try:
            # 初始化API客户端
            from src.core.APIClient import APIClient
            from config.config import CONFIG
            
            api_client = APIClient(CONFIG)
            
            # 获取GenreManager
            from web.services.market_driven.genre_manager import get_genre_manager
            genre_manager = get_genre_manager(api_client=api_client)
            
            # 记录更新前的数量
            old_genres = genre_manager.get_genres()
            old_count = len(old_genres)
            
            logger.info(f"[GenreScheduler] 当前有 {old_count} 个类型，开始AI分析...")
            
            # 执行AI生成
            new_genres = genre_manager._fetch_ai_genres()
            
            if new_genres:
                # 合并新旧类型
                merged = {**old_genres, **new_genres}
                genre_manager._save_cache(merged)
                genre_manager._genres_cache = merged
                genre_manager._update_last_update_time()
                
                logger.info(f"[GenreScheduler] AI生成了 {len(new_genres)} 个新类型，总数: {len(merged)}")
                
                # 记录更新日志
                self._log_update(old_count, len(merged), list(new_genres.keys()))
                
                return True
            else:
                # 即使没有新类型，也更新时间戳避免重复请求
                genre_manager._update_last_update_time()
                logger.info("[GenreScheduler] AI未生成新类型，仅更新时间戳")
                return False
                
        except Exception as e:
            logger.error(f"[GenreScheduler] 更新操作失败: {e}")
            return False
    
    def _log_update(self, old_count: int, new_count: int, new_genres: list):
        """记录更新日志"""
        try:
            from pathlib import Path
            import json
            
            log_dir = Path("logs/genre_updates")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "old_count": old_count,
                "new_count": new_count,
                "added": new_count - old_count,
                "new_genres": new_genres
            }
            
            log_file = log_dir / f"update_{datetime.now().strftime('%Y%m')}.jsonl"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"[GenreScheduler] 记录更新日志失败: {e}")
    
    def trigger_manual_update(self) -> dict:
        """
        手动触发更新
        
        Returns:
            更新结果信息
        """
        logger.info("[GenreScheduler] 收到手动更新请求")
        
        with self._lock:
            if self._is_running:
                return {
                    "success": False,
                    "message": "更新任务已在运行中",
                    "status": "running"
                }
            self._is_running = True
        
        try:
            result = self._do_update()
            
            if result:
                return {
                    "success": True,
                    "message": "题材更新完成",
                    "status": "completed"
                }
            else:
                return {
                    "success": True,
                    "message": "本次更新未生成新类型",
                    "status": "completed_no_changes"
                }
                
        except Exception as e:
            logger.error(f"[GenreScheduler] 手动更新失败: {e}")
            return {
                "success": False,
                "message": f"更新失败: {str(e)}",
                "status": "error"
            }
        finally:
            self._is_running = False
    
    def get_status(self) -> dict:
        """
        获取调度器状态
        
        Returns:
            状态信息
        """
        from web.services.market_driven.genre_manager import get_genre_manager
        
        genre_manager = get_genre_manager()
        update_status = genre_manager.get_update_status()
        
        # 计算下次更新时间
        next_update = None
        if update_status.get("last_update"):
            try:
                last_update = datetime.fromisoformat(update_status["last_update"])
                # 下周一凌晨2点
                days_until_monday = (7 - last_update.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_update = (last_update + timedelta(days=days_until_monday)).replace(
                    hour=2, minute=0, second=0, microsecond=0
                )
                next_update = next_update.isoformat()
            except:
                pass
        
        return {
            "scheduler_active": self._scheduler is not None and self._scheduler.running,
            "is_running": self._is_running,
            "total_genres": update_status.get("total_genres", 0),
            "base_genres": update_status.get("base_genres", 0),
            "ai_genres": update_status.get("ai_genres", 0),
            "last_update": update_status.get("last_update"),
            "days_since_update": update_status.get("days_since_update"),
            "next_scheduled_update": next_update
        }
    
    def shutdown(self):
        """关闭调度器"""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("[GenreScheduler] 调度器已关闭")


# 全局调度器实例
_scheduler_instance: Optional[GenreUpdateScheduler] = None


def init_genre_scheduler(app):
    """
    初始化全局调度器
    
    Args:
        app: Flask应用实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = GenreUpdateScheduler()
        _scheduler_instance.init_scheduler(app)
    return _scheduler_instance


def get_genre_scheduler() -> Optional[GenreUpdateScheduler]:
    """获取全局调度器实例"""
    return _scheduler_instance
