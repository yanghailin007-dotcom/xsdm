"""
AI-WX 视频生成管理器
使用 https://jyapi.ai-wx.cn API

支持 Sora-2 等模型
支持任务队列、状态管理、轮询查询等功能
"""
import os
import json
import uuid
import threading
import time
from typing import Dict, List, Optional, Callable, Any, Generator
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
import logging
import requests

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent.parent

from src.models.video_openai_models import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    GenerationStatus,
    GenerationResult,
    VideoResult,
    FinishReason,
    UsageMetadata
)
from src.utils.logger import get_logger
import sys
sys.path.insert(0, str(BASE_DIR))
from config.aiwx_video_config import (
    AIWX_VIDEO_CREATE_URL,
    AIWX_BASE_URL,
    AIWX_API_KEY,
    DEFAULT_AIWX_VIDEO_CONFIG,
    POLLING_CONFIG,
    REQUEST_CONFIG,
    get_request_headers,
    validate_config,
    get_video_url
)

logger = get_logger(__name__)


class AiWxVideoTask:
    """AI-WX 视频生成任务"""
    
    def __init__(self, request: VideoGenerationRequest):
        self.id = f"aiwx_{uuid.uuid4().hex[:12]}"
        self.request = request
        self.status = GenerationStatus.PROCESSING
        self.created_at = int(time.time())
        self.completed_at: Optional[int] = None
        self.result: Optional[GenerationResult] = None
        self.error: Optional[str] = None
        self.api_task_id: Optional[str] = None  # API返回的任务ID
        self.progress_callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
    def update_progress(self, progress: int, stage: str = ""):
        """更新进度"""
        with self._lock:
            for callback in self.progress_callbacks:
                try:
                    callback(self.id, progress, stage)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")
    
    def complete(self, result: GenerationResult):
        """标记任务完成"""
        with self._lock:
            self.status = GenerationStatus.COMPLETED
            self.completed_at = int(time.time())
            self.result = result
    
    def fail(self, error: str):
        """标记任务失败"""
        with self._lock:
            self.status = GenerationStatus.FAILED
            self.completed_at = int(time.time())
            self.error = error
    
    def cancel(self):
        """取消任务"""
        with self._lock:
            self.status = GenerationStatus.CANCELLED
            self.completed_at = int(time.time())
    
    def to_response(self) -> VideoGenerationResponse:
        """转换为响应对象"""
        # 构建metadata字典
        metadata_dict = None
        if self.request.metadata:
            metadata_dict = {
                "user_id": self.request.metadata.user_id,
                "project_id": self.request.metadata.project_id,
                "labels": self.request.metadata.labels
            }
        
        response = VideoGenerationResponse(
            id=self.id,
            created=self.created_at,
            completed=self.completed_at,
            model=self.request.model,
            status=self.status,
            prompt=self.request.prompt,
            generation_config=self.request.generation_config,
            result=self.result,
            error=self.error,
            metadata=metadata_dict
        )
        
        # 计算使用统计
        prompt_tokens = len(self.request.prompt.split())
        completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens
        video_seconds = 0.0
        
        if self.result and self.result.videos:
            video_seconds = sum(v.duration_seconds for v in self.result.videos)
        
        response.usage = UsageMetadata(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            video_seconds=video_seconds
        )
        
        return response


class AiWxVideoManager:
    """AI-WX 视频生成管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化 AI-WX 视频生成管理器
        
        Args:
            storage_dir: 任务存储目录
        """
        self.logger = logger
        self.storage_dir = Path(storage_dir or BASE_DIR / "aiwx_video_generations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务存储
        self.tasks: Dict[str, AiWxVideoTask] = {}
        self._tasks_lock = threading.Lock()
        
        # 任务队列
        self.task_queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 验证配置
        is_valid, message = validate_config()
        if not is_valid:
            self.logger.warn(f"⚠️  配置验证失败: {message}")
            self.logger.warn("⚠️  AI-WX 视频生成功能可能无法正常工作")
        
        # 加载已保存的任务
        self._load_tasks()
        
        self.logger.info(f"✅ AI-WX 视频生成管理器初始化完成")
        self.logger.info(f"📁 存储目录: {self.storage_dir}")
        self.logger.info(f"📊 已加载任务数: {len(self.tasks)}")
    
    def _load_tasks(self):
        """从磁盘加载任务"""
        try:
            for task_file in self.storage_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    # 这里简化处理，只加载任务ID和状态
                    task_id = task_data.get("id")
                    if task_id and task_id not in self.tasks:
                        # 创建占位任务对象
                        placeholder_request = VideoGenerationRequest(
                            model=DEFAULT_AIWX_VIDEO_CONFIG['model'],
                            prompt="占位任务"
                        )
                        
                        self.tasks[task_id] = AiWxVideoTask(placeholder_request)
                        self.tasks[task_id].status = GenerationStatus.PROCESSING
                
                except Exception as e:
                    self.logger.warn(f"加载任务文件失败 {task_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"加载任务失败: {e}")
    
    def _save_task(self, task: AiWxVideoTask):
        """保存任务到磁盘"""
        try:
            task_file = self.storage_dir / f"{task.id}.json"
            response = task.to_response()
            
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(response.to_dict(), f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            self.logger.error(f"保存任务失败: {e}")
    
    def _worker_loop(self):
        """工作线程循环"""
        self.logger.info("🔄 AI-WX 工作线程启动")
        
        while self._running:
            try:
                # 从队列获取任务
                task_id = self.task_queue.get(timeout=1.0)
                
                with self._tasks_lock:
                    task = self.tasks.get(task_id)
                
                if task and task.status == GenerationStatus.PROCESSING:
                    try:
                        self._process_task(task)
                    except Exception as e:
                        self.logger.error(f"处理任务失败 {task_id}: {e}")
                        task.fail(str(e))
                        self._save_task(task)
            
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"工作线程错误: {e}")
        
        self.logger.info("🛑 AI-WX 工作线程停止")
    
    def _process_task(self, task: AiWxVideoTask):
        """处理单个任务 - 使用 AI-WX 官方 API 格式"""
        self.logger.info(f"🎬 开始处理 AI-WX 任务: {task.id}")
        
        # 更新进度
        task.update_progress(10, "初始化")
        
        try:
            # 🔥 调用 AI-WX 视频生成API（官方格式）
            self.logger.info(f"📡 调用 AI-WX API: {AIWX_VIDEO_CREATE_URL}")
            
            # 更新进度
            task.update_progress(20, "准备生成参数")
            
            # 准备请求参数
            generation_config = task.request.generation_config
            
            # 确定方向（根据分辨率）
            orientation = DEFAULT_AIWX_VIDEO_CONFIG['orientation']  # 默认竖屏
            size = DEFAULT_AIWX_VIDEO_CONFIG['size']  # 默认 large
            duration = DEFAULT_AIWX_VIDEO_CONFIG['duration']
            
            if generation_config:
                if generation_config.resolution:
                    if "1920x1080" in generation_config.resolution or "1280x720" in generation_config.resolution:
                        orientation = "landscape"  # 横屏
                    elif "1080x1920" in generation_config.resolution or "720x1280" in generation_config.resolution:
                        orientation = "portrait"  # 竖屏
                
                if generation_config.duration_seconds:
                    duration = generation_config.duration_seconds
            
            # 构建官方 API 格式的请求
            payload = {
                "images": [],  # 可以添加图片URL
                "model": DEFAULT_AIWX_VIDEO_CONFIG['model'],
                "orientation": orientation,
                "prompt": task.request.prompt,
                "size": size,
                "duration": duration,
                "watermark": DEFAULT_AIWX_VIDEO_CONFIG['watermark'],
                "private": DEFAULT_AIWX_VIDEO_CONFIG['private']
            }
            
            self.logger.info(f"📤 发送请求到: {AIWX_VIDEO_CREATE_URL}")
            self.logger.info(f"📝 提示词长度: {len(task.request.prompt)} 字符")
            self.logger.info(f"🎬 模型: {payload['model']}")
            self.logger.info(f"📐 方向: {payload['orientation']}")
            self.logger.info(f"📏 尺寸: {payload['size']}")
            self.logger.info(f"⏱️  时长: {payload['duration']}秒")
            
            task.update_progress(30, "发送生成请求")
            
            # 获取请求头（官方格式：直接使用 API Key，不需要 Bearer）
            headers = {
                "Content-Type": "application/json",
                "Authorization": AIWX_API_KEY,
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Accept": "*/*",
                "Host": "jyapi.ai-wx.cn",
                "Connection": "keep-alive"
            }
            
            # 发送请求
            response = requests.post(
                AIWX_VIDEO_CREATE_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_CONFIG['timeout']
            )
            
            if response.status_code == 200:
                response_data = response.json()
                self.logger.info(f"✅ 请求成功")
                self.logger.info(f"📊 响应数据: {response_data}")
                
                # 解析响应
                if 'id' in response_data:
                    task.api_task_id = response_data['id']
                    self.logger.info(f"📋 API任务ID: {task.api_task_id}")
                    
                    # 检查状态
                    status = response_data.get('status', 'queued')
                    self.logger.info(f"📊 任务状态: {status}")
                    
                    if status == 'completed' or status == 'succeeded':
                        # 任务已完成，直接返回结果
                        result = self._parse_api_result(response_data, task)
                        task.complete(result)
                        self.logger.info(f"✅ AI-WX 任务完成: {task.id}")
                    elif status == 'failed' or status == 'error':
                        error_msg = response_data.get('error', '未知错误')
                        raise Exception(f"AI-WX 任务失败: {error_msg}")
                    else:
                        # 任务排队中或处理中，需要轮询
                        task.update_progress(40, "等待视频生成")
                        result = self._poll_task_status(task)
                        
                        if result:
                            task.complete(result)
                            self.logger.info(f"✅ AI-WX 任务完成: {task.id}")
                        else:
                            raise Exception("轮询超时，未能获取视频结果")
                else:
                    raise Exception(f"API返回格式异常: {response_data}")
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                raise Exception(f"AI-WX API请求失败: {error_msg}")
        
        except Exception as e:
            self.logger.error(f"❌ AI-WX 任务处理失败: {e}")
            self.logger.error(f"❌ 错误详情: {str(e)}")
            
            # 创建失败结果
            task.fail(str(e))
            raise
        
        finally:
            self._save_task(task)
    
    def _poll_task_status(self, task: AiWxVideoTask) -> Optional[GenerationResult]:
        """
        轮询任务状态 - 查询视频生成状态
        
        Args:
            task: 视频生成任务
        
        Returns:
            生成结果或None
        """
        if not task.api_task_id:
            self.logger.error("没有API任务ID，无法轮询")
            return None
        
        max_attempts = POLLING_CONFIG['max_attempts']
        poll_interval = POLLING_CONFIG['poll_interval']
        
        self.logger.info(f"🔄 开始轮询任务状态，最大尝试次数: {max_attempts}")
        
        for attempt in range(max_attempts):
            try:
                # 计算进度
                progress = min(40 + int(50 * (attempt + 1) / max_attempts), 90)
                task.update_progress(progress, f"轮询任务状态 ({attempt + 1}/{max_attempts})")
                
                # 查询任务状态 - 使用相同的端点，但传递任务ID
                status_url = f"{AIWX_BASE_URL}/v1/videos/{task.api_task_id}"
                headers = get_request_headers()
                
                response = requests.get(
                    status_url,
                    headers=headers,
                    timeout=REQUEST_CONFIG['timeout']
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.logger.info(f"📊 轮询响应: {response_data}")
                    
                    # 检查状态
                    status = response_data.get('status', 'queued')
                    self.logger.info(f"📊 任务状态: {status}")
                    
                    if status == 'completed' or status == 'succeeded':
                        # 任务完成
                        result = self._parse_api_result(response_data, task)
                        return result
                    
                    elif status == 'failed' or status == 'error':
                        # 任务失败
                        error_msg = response_data.get('error', '未知错误')
                        raise Exception(f"AI-WX 任务失败: {error_msg}")
                    
                    elif status in ['queued', 'processing', 'pending', 'in_progress']:
                        # 继续等待
                        self.logger.info(f"⏳ 任务处理中... ({status}) ({attempt + 1}/{max_attempts})")
                        time.sleep(poll_interval)
                    
                    else:
                        self.logger.warn(f"⚠️  未知状态: {status}")
                        time.sleep(poll_interval)
                else:
                    self.logger.warn(f"⚠️  查询状态失败: HTTP {response.status_code}")
                    time.sleep(poll_interval)
            
            except Exception as e:
                self.logger.error(f"❌ 轮询失败 (尝试 {attempt + 1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(poll_interval)
        
        self.logger.error(f"❌ 轮询超时，已达到最大尝试次数: {max_attempts}")
        return None
    
    def _parse_api_result(self, api_data: dict, task: AiWxVideoTask) -> GenerationResult:
        """
        解析API返回的结果
        
        Args:
            api_data: API返回的数据
            task: 视频生成任务
        
        Returns:
            GenerationResult对象
        """
        # AI-WX API 返回格式示例:
        # {
        #   'id': 'video_d5b740b4-ddc9-440e-983f-9f2859ee2d5e',
        #   'object': 'video',
        #   'model': 'veo_3_1-fast',
        #   'status': 'completed',
        #   'video_url': 'https://midjourney-plus.oss-us-west-1.aliyuncs.com/...',
        #   'size': '720x1280',
        #   'seconds': '10',
        #   'progress': 100
        # }
        
        self.logger.info(f"🔍 解析API返回数据: {api_data}")
        
        # 优先尝试 video_url 字段（AI-WX API实际返回的字段名）
        video_url = api_data.get('video_url', '')
        
        # 如果没有video_url，尝试其他可能的字段名
        if not video_url:
            video_url = api_data.get('url', '')
            if not video_url:
                self.logger.error(f"❌ API返回数据中没有视频URL: {api_data}")
                raise Exception("API返回结果中没有视频URL")
        
        self.logger.info(f"✅ 成功提取视频URL: {video_url}")
        
        # 获取视频参数
        duration = int(api_data.get('duration', 15))
        resolution = api_data.get('size', '720x1280')
        
        # 创建视频结果
        video = VideoResult(
            id=api_data.get('id', f"video_{uuid.uuid4().hex[:8]}"),
            url=video_url,
            duration_seconds=duration,
            resolution=resolution,
            fps=24,  # 默认24fps
            size_bytes=0,  # 未知
            format="mp4",
            thumbnail_url=""  # API可能不提供缩略图
        )
        
        return GenerationResult(
            videos=[video],
            finish_reason=FinishReason.FINISH_REASON_STOP
        )
    
    def start(self):
        """启动管理器"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            self.logger.info("✅ AI-WX 视频生成管理器已启动")
    
    def stop(self):
        """停止管理器"""
        if self._running:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5.0)
            self.logger.info("🛑 AI-WX 视频生成管理器已停止")
    
    def create_generation(
        self,
        request: VideoGenerationRequest,
        progress_callback: Optional[Callable] = None
    ) -> VideoGenerationResponse:
        """
        创建视频生成任务
        
        Args:
            request: 生成请求
            progress_callback: 进度回调函数
        
        Returns:
            生成响应
        """
        # 创建任务
        task = AiWxVideoTask(request)
        
        if progress_callback:
            task.progress_callbacks.append(progress_callback)
        
        # 存储任务
        with self._tasks_lock:
            self.tasks[task.id] = task
        
        # 保存初始状态
        self._save_task(task)
        
        # 添加到队列
        self.task_queue.put(task.id)
        
        self.logger.info(f"📝 创建 AI-WX 生成任务: {task.id}")
        
        # 返回响应
        return task.to_response()
    
    def retrieve_generation(self, generation_id: str) -> Optional[VideoGenerationResponse]:
        """
        查询生成状态
        
        Args:
            generation_id: 生成任务ID
        
        Returns:
            生成响应
        """
        with self._tasks_lock:
            task = self.tasks.get(generation_id)
        
        if task:
            return task.to_response()
        
        return None
    
    def list_generations(
        self,
        limit: int = 20,
        status: Optional[GenerationStatus] = None,
        order: str = "desc"
    ) -> List[VideoGenerationResponse]:
        """
        列出生成任务
        
        Args:
            limit: 返回数量限制
            status: 状态过滤
            order: 排序方式
        
        Returns:
            生成响应列表
        """
        with self._tasks_lock:
            tasks = list(self.tasks.values())
        
        # 过滤
        if status:
            tasks = [t for t in tasks if t and t.status == status]
        
        # 排序
        reverse = order == "desc"
        tasks = sorted(
            [t for t in tasks if t],
            key=lambda t: t.created_at,
            reverse=reverse
        )
        
        # 限制数量
        tasks = tasks[:limit]
        
        return [task.to_response() for task in tasks]
    
    def cancel_generation(self, generation_id: str) -> bool:
        """
        取消生成任务
        
        Args:
            generation_id: 生成任务ID
        
        Returns:
            是否成功
        """
        with self._tasks_lock:
            task = self.tasks.get(generation_id)
        
        if task and task.status == GenerationStatus.PROCESSING:
            task.cancel()
            self._save_task(task)
            self.logger.info(f"🚫 取消任务: {generation_id}")
            return True
        
        return False
    
    def delete_generation(self, generation_id: str) -> bool:
        """
        删除生成任务
        
        Args:
            generation_id: 生成任务ID
        
        Returns:
            是否成功
        """
        with self._tasks_lock:
            task = self.tasks.pop(generation_id, None)
        
        if task:
            # 删除文件
            task_file = self.storage_dir / f"{generation_id}.json"
            if task_file.exists():
                task_file.unlink()
            
            self.logger.info(f"🗑️ 删除任务: {generation_id}")
            return True
        
        return False


# 全局单例
_manager_instance: Optional[AiWxVideoManager] = None
_manager_lock = threading.Lock()


def get_aiwx_video_manager() -> AiWxVideoManager:
    """获取 AI-WX 视频生成管理器单例"""
    global _manager_instance
    
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = AiWxVideoManager()
            _manager_instance.start()
    
    return _manager_instance