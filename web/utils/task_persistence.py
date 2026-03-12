"""
任务持久化工具 - 保存和加载生成任务状态
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.utils.logger import Logger

logger = Logger.get_logger(__name__)


class TaskPersistence:
    """任务持久化管理器"""
    
    # 默认存储目录
    DEFAULT_TASKS_DIR = Path("data/generation_tasks")
    
    # 保留最近多少天的任务
    RETENTION_DAYS = 30
    
    @classmethod
    def get_tasks_dir(cls) -> Path:
        """获取任务存储目录"""
        tasks_dir = cls.DEFAULT_TASKS_DIR
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return tasks_dir
    
    @classmethod
    def save_task(cls, task_data: Dict[str, Any]) -> bool:
        """
        保存单个任务到文件
        
        Args:
            task_data: 任务数据字典，必须包含 task_id
            
        Returns:
            bool: 是否保存成功
        """
        try:
            task_id = task_data.get('task_id')
            if not task_id:
                logger.error("❌ 保存任务失败: 缺少 task_id")
                return False
            
            tasks_dir = cls.get_tasks_dir()
            task_file = tasks_dir / f"{task_id}.json"
            
            # 添加保存时间戳
            task_data['_saved_at'] = datetime.now().isoformat()
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ 任务已保存: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存任务失败: {e}")
            return False
    
    @classmethod
    def load_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载单个任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务数据字典，如果不存在返回 None
        """
        try:
            tasks_dir = cls.get_tasks_dir()
            task_file = tasks_dir / f"{task_id}.json"
            
            if not task_file.exists():
                return None
            
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            return task_data
            
        except Exception as e:
            logger.error(f"❌ 加载任务 {task_id} 失败: {e}")
            return None
    
    @classmethod
    def load_all_tasks(cls, include_completed: bool = True, 
                       include_failed: bool = True) -> List[Dict[str, Any]]:
        """
        加载所有任务
        
        Args:
            include_completed: 是否包含已完成的任务
            include_failed: 是否包含失败的任务
            
        Returns:
            任务数据列表
        """
        tasks = []
        
        try:
            tasks_dir = cls.get_tasks_dir()
            if not tasks_dir.exists():
                return tasks
            
            for task_file in tasks_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    status = task_data.get('status', '').lower()
                    
                    # 根据状态过滤
                    if status in ['completed', 'success'] and not include_completed:
                        continue
                    if status in ['failed', 'error', 'cancelled'] and not include_failed:
                        continue
                    
                    tasks.append(task_data)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 加载任务文件 {task_file.name} 失败: {e}")
                    continue
            
            # 按更新时间倒序排序
            tasks.sort(key=lambda x: x.get('updated_at', x.get('created_at', '')), reverse=True)
            
            logger.info(f"✅ 已加载 {len(tasks)} 个历史任务")
            return tasks
            
        except Exception as e:
            logger.error(f"❌ 加载所有任务失败: {e}")
            return tasks
    
    @classmethod
    def load_active_tasks(cls) -> List[Dict[str, Any]]:
        """
        加载所有进行中的任务（用于服务器重启后恢复）
        
        Returns:
            进行中的任务列表
        """
        tasks = []
        
        try:
            tasks_dir = cls.get_tasks_dir()
            if not tasks_dir.exists():
                return tasks
            
            for task_file in tasks_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    status = task_data.get('status', '').lower()
                    
                    # 只加载进行中的任务
                    if status not in ['completed', 'success', 'failed', 'error', 'cancelled']:
                        tasks.append(task_data)
                        logger.info(f"📋 恢复进行中的任务: {task_data.get('task_id')}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 加载任务文件 {task_file.name} 失败: {e}")
                    continue
            
            logger.info(f"✅ 已恢复 {len(tasks)} 个进行中的任务")
            return tasks
            
        except Exception as e:
            logger.error(f"❌ 加载进行中的任务失败: {e}")
            return tasks
    
    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """
        删除任务文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            tasks_dir = cls.get_tasks_dir()
            task_file = tasks_dir / f"{task_id}.json"
            
            if task_file.exists():
                task_file.unlink()
                logger.info(f"✅ 任务文件已删除: {task_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 删除任务文件 {task_id} 失败: {e}")
            return False
    
    @classmethod
    def cleanup_old_tasks(cls, days: int = None) -> int:
        """
        清理过期的任务文件
        
        Args:
            days: 保留天数，默认使用 RETENTION_DAYS
            
        Returns:
            int: 清理的文件数量
        """
        if days is None:
            days = cls.RETENTION_DAYS
        
        cleaned_count = 0
        
        try:
            tasks_dir = cls.get_tasks_dir()
            if not tasks_dir.exists():
                return cleaned_count
            
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            for task_file in tasks_dir.glob("*.json"):
                try:
                    # 检查文件修改时间
                    file_mtime = task_file.stat().st_mtime
                    if file_mtime < cutoff_date:
                        task_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"🗑️ 已清理过期任务文件: {task_file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ 清理任务文件 {task_file.name} 失败: {e}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"🧹 已清理 {cleaned_count} 个过期任务文件")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ 清理过期任务失败: {e}")
            return cleaned_count
    
    @classmethod
    def get_task_stats(cls) -> Dict[str, int]:
        """
        获取任务统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total': 0,
            'active': 0,
            'completed': 0,
            'failed': 0
        }
        
        try:
            tasks_dir = cls.get_tasks_dir()
            if not tasks_dir.exists():
                return stats
            
            for task_file in tasks_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    status = task_data.get('status', '').lower()
                    stats['total'] += 1
                    
                    if status in ['completed', 'success']:
                        stats['completed'] += 1
                    elif status in ['failed', 'error', 'cancelled']:
                        stats['failed'] += 1
                    else:
                        stats['active'] += 1
                        
                except Exception:
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取任务统计失败: {e}")
            return stats
