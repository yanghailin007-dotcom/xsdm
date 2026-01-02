"""
视频任务调度器 - 管理视频生成任务的队列和分配

功能：
- 管理任务队列
- 分配镜头给Worker
- 控制并发数量
- 处理任务状态变化
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import json
from pathlib import Path

from src.utils.logger import get_logger
from src.models.video_task_models import VideoTask, Shot, TaskStatus, ShotStatus


class VideoTaskScheduler:
    """视频任务调度器"""
    
    def __init__(self, max_concurrent: int = 3, storage_path: str = "视频项目"):
        """
        初始化调度器
        
        Args:
            max_concurrent: 最大并发数
            storage_path: 存储路径
        """
        self.logger = get_logger("VideoTaskScheduler")
        self.max_concurrent = max_concurrent
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # 任务队列
        self.tasks: Dict[str, VideoTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # Worker池
        self.workers: List['VideoWorker'] = []
        self.active_workers: int = 0
        
        # 任务状态回调
        self.on_task_completed: Optional[Callable] = None
        self.on_task_failed: Optional[Callable] = None
        self.on_shot_completed: Optional[Callable] = None
        self.on_shot_failed: Optional[Callable] = None
        
        # 进度跟踪
        self._progress_callbacks: List[Callable] = []
        
        self.logger.info(f"✅ 任务调度器初始化完成 (最大并发: {max_concurrent})")
    
    async def submit_task(self, shots: List[Dict], project_id: str, config: Dict = None) -> str:
        """
        提交任务
        
        Args:
            shots: 镜头列表
            project_id: 项目ID
            config: 任务配置
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建镜头对象
        shot_objects = []
        for idx, shot_data in enumerate(shots):
            shot = Shot(
                shot_index=idx,
                shot_type=shot_data.get("shot_type", "中景"),
                camera_movement=shot_data.get("camera_movement", "固定"),
                duration_seconds=shot_data.get("duration_seconds", 10.0),
                description=shot_data.get("description", ""),
                generation_prompt=shot_data.get("generation_prompt", ""),
                audio_prompt=shot_data.get("audio_cue") or shot_data.get("audio_prompt")
            )
            shot_objects.append(shot)
        
        # 创建任务
        task = VideoTask(
            task_id=task_id,
            project_id=project_id,
            shots=shot_objects,
            config=config or {}
        )
        
        self.tasks[task_id] = task
        
        # 保存任务信息
        await self._save_task(task)
        
        # 添加到队列
        await self.task_queue.put(task_id)
        
        self.logger.info(f"📋 任务已提交: {task_id} ({len(shots)} 个镜头)")
        
        # 通知进度回调
        await self._notify_progress(task_id, "task_created", {
            "total_shots": len(shots),
            "status": "pending"
        })
        
        return task_id
    
    async def assign_shot(self, worker: 'VideoWorker') -> Optional[Shot]:
        """
        分配镜头给Worker
        
        Args:
            worker: Worker实例
        
        Returns:
            待处理的镜头，如果没有则返回None
        """
        # 检查并发限制
        if self.active_workers >= self.max_concurrent:
            self.logger.debug(f"达到最大并发数限制 ({self.max_concurrent})")
            return None
        
        # 从队列获取任务
        try:
            task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
        
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # 获取待处理的镜头
        pending_shots = task.get_pending_shots()
        if not pending_shots:
            # 没有待处理的镜头，检查任务是否完成
            if task.completed_shots + task.failed_shots >= task.total_shots:
                await self._complete_task(task_id)
            return None
        
        # 分配第一个待处理的镜头
        shot = pending_shots[0]
        shot.status = ShotStatus.GENERATING
        shot.started_at = datetime.now()
        
        self.active_workers += 1
        
        self.logger.info(f"🎬 分配镜头 #{shot.shot_index} 给 Worker-{worker.worker_id}")
        
        await self._notify_progress(task_id, "shot_started", {
            "shot_index": shot.shot_index,
            "worker_id": worker.worker_id
        })
        
        return shot
    
    async def on_shot_completed(self, task_id: str, shot_index: int, result: Dict):
        """
        镜头完成回调
        
        Args:
            task_id: 任务ID
            shot_index: 镜头索引
            result: 生成结果
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error(f"❌ 任务不存在: {task_id}")
            return
        
        shot = task.shots[shot_index]
        shot.status = ShotStatus.COMPLETED
        shot.completed_at = datetime.now()
        shot.video_path = result.get("video_path")
        shot.thumbnail_path = result.get("thumbnail_path")
        
        task.completed_shots += 1
        self.active_workers -= 1
        
        self.logger.info(f"✅ 镜头 #{shot_index} 完成 ({task.completed_shots}/{task.total_shots})")
        
        # 保存任务状态
        await self._save_task(task)
        
        # 通知回调
        if self.on_shot_completed:
            await self.on_shot_completed(task_id, shot_index, result)
        
        await self._notify_progress(task_id, "shot_completed", {
            "shot_index": shot_index,
            "video_path": shot.video_path,
            "thumbnail_path": shot.thumbnail_path,
            "progress": task.get_progress()
        })
        
        # 检查任务是否完成
        if task.completed_shots + task.failed_shots >= task.total_shots:
            await self._complete_task(task_id)
    
    async def on_shot_failed(self, task_id: str, shot_index: int, error: Exception):
        """
        镜头失败回调
        
        Args:
            task_id: 任务ID
            shot_index: 镜头索引
            error: 错误信息
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error(f"❌ 任务不存在: {task_id}")
            return
        
        shot = task.shots[shot_index]
        shot.retry_count += 1
        shot.error_message = str(error)
        
        task.failed_shots += 1
        self.active_workers -= 1
        
        self.logger.error(f"❌ 镜头 #{shot_index} 失败: {error}")
        
        # 通知回调
        if self.on_shot_failed:
            await self.on_shot_failed(task_id, shot_index, error)
        
        await self._notify_progress(task_id, "shot_failed", {
            "shot_index": shot_index,
            "error": str(error),
            "retry_count": shot.retry_count
        })
        
        # 保存任务状态
        await self._save_task(task)
        
        # 检查任务是否完成
        if task.completed_shots + task.failed_shots >= task.total_shots:
            await self._complete_task(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.COMPLETED:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        # 标记所有待处理的镜头为已跳过
        for shot in task.shots:
            if shot.status == ShotStatus.PENDING:
                shot.status = ShotStatus.SKIPPED
        
        await self._save_task(task)
        
        self.logger.info(f"🚫 任务已取消: {task_id}")
        
        await self._notify_progress(task_id, "task_cancelled", {
            "cancelled_at": task.completed_at.isoformat()
        })
        
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功暂停
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        task.status = TaskStatus.PAUSED
        
        await self._save_task(task)
        
        self.logger.info(f"⏸️  任务已暂停: {task_id}")
        
        await self._notify_progress(task_id, "task_paused", {})
        
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功恢复
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        task.status = TaskStatus.RUNNING
        
        # 将任务重新加入队列
        await self.task_queue.put(task_id)
        
        await self._save_task(task)
        
        self.logger.info(f"▶️  任务已恢复: {task_id}")
        
        await self._notify_progress(task_id, "task_resumed", {})
        
        return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "project_id": task.project_id,
            "status": task.status.value,
            "total_shots": task.total_shots,
            "completed_shots": task.completed_shots,
            "failed_shots": task.failed_shots,
            "progress": task.get_progress(),
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    
    def register_progress_callback(self, callback: Callable):
        """
        注册进度回调
        
        Args:
            callback: 回调函数，签名为 (task_id: str, event: str, data: Dict)
        """
        self._progress_callbacks.append(callback)
    
    async def _notify_progress(self, task_id: str, event: str, data: Dict):
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, event, data)
                else:
                    callback(task_id, event, data)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    async def _complete_task(self, task_id: str):
        """完成任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        
        await self._save_task(task)
        
        self.logger.info(f"✅ 任务完成: {task_id} ({task.completed_shots}/{task.total_shots} 镜头成功)")
        
        if self.on_task_completed:
            await self.on_task_completed(task_id)
        
        await self._notify_progress(task_id, "task_completed", {
            "completed_shots": task.completed_shots,
            "failed_shots": task.failed_shots,
            "progress": 1.0
        })
    
    async def _save_task(self, task: VideoTask):
        """保存任务状态"""
        task_dir = self.storage_path / task.project_id
        task_dir.mkdir(exist_ok=True)
        
        task_file = task_dir / f"task_{task.task_id}.json"
        
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
    
    async def load_task(self, task_id: str) -> Optional[VideoTask]:
        """加载任务"""
        for project_dir in self.storage_path.iterdir():
            if project_dir.is_dir():
                task_file = project_dir / f"task_{task_id}.json"
                if task_file.exists():
                    with open(task_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return VideoTask.from_dict(data)
        return None
    
    async def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        tasks = []
        for task in self.tasks.values():
            tasks.append(await self.get_task_status(task.task_id))
        return tasks