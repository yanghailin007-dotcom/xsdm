"""
Google AI Platform 视频生成管理器

支持 Gemini 2.5 Flash Lite 等模型
支持任务队列、状态管理、流式响应等功能
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
from config.videoconfig import (
    get_api_endpoint,
    validate_config,
    get_request_headers,
    DEFAULT_VIDEO_CONFIG,
    POLLING_CONFIG,
    REQUEST_CONFIG
)

logger = get_logger(__name__)


class VideoGenerationTask:
    """视频生成任务"""
    
    def __init__(self, request: VideoGenerationRequest):
        self.id = f"gen_{uuid.uuid4().hex[:12]}"
        self.request = request
        self.status = GenerationStatus.PROCESSING
        self.created_at = int(time.time())
        self.completed_at: Optional[int] = None
        self.result: Optional[GenerationResult] = None
        self.error: Optional[str] = None
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


class VideoGenerationManager:
    """视频生成管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化视频生成管理器
        
        Args:
            storage_dir: 任务存储目录
        """
        self.logger = logger
        self.storage_dir = Path(storage_dir or BASE_DIR / "video_generations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务存储
        self.tasks: Dict[str, VideoGenerationTask] = {}
        self._tasks_lock = threading.Lock()
        
        # 任务队列
        self.task_queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 验证配置
        is_valid, message = validate_config()
        if not is_valid:
            self.logger.warn(f"⚠️  配置验证失败: {message}")
            self.logger.warn("⚠️  视频生成功能可能无法正常工作")
        
        # 加载已保存的任务
        self._load_tasks()
        
        self.logger.info(f"✅ 视频生成管理器初始化完成")
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
                    # 实际使用时需要完整的反序列化
                    task_id = task_data.get("id")
                    if task_id and task_id not in self.tasks:
                        # 创建占位任务对象
                        from src.models.video_openai_models import (
                            VideoGenerationRequest,
                            GenerationConfig,
                            GenerationStatus
                        )
                        
                        # 创建一个默认的请求对象
                        placeholder_request = VideoGenerationRequest(
                            model="video-model-v1",
                            prompt="占位任务"
                        )
                        
                        self.tasks[task_id] = VideoGenerationTask(placeholder_request)
                        self.tasks[task_id].status = GenerationStatus.PROCESSING
                
                except Exception as e:
                    self.logger.warn(f"加载任务文件失败 {task_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"加载任务失败: {e}")
    
    def _save_task(self, task: VideoGenerationTask):
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
        self.logger.info("🔄 工作线程启动")
        
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
        
        self.logger.info("🛑 工作线程停止")
    
    def _process_task(self, task: VideoGenerationTask):
        """处理单个任务 - 使用 Google AI Platform API"""
        self.logger.info(f"🎬 开始处理任务: {task.id}")
        
        # 更新进度
        task.update_progress(10, "初始化")
        
        try:
            # 🔥 调用 Google AI Platform 视频生成API
            self.logger.info(f"📡 调用 Google AI Platform API...")
            
            # 更新进度
            task.update_progress(20, "准备生成参数")
            
            # 获取API端点
            model_name = task.request.model or "gemini-2.5-flash-lite"
            api_url = get_api_endpoint(model=model_name, stream=True)
            
            # 准备请求参数
            generation_config = task.request.generation_config
            if generation_config is None:
                # 使用默认配置
                from src.models.video_openai_models import GenerationConfig
                generation_config = GenerationConfig(
                    **DEFAULT_VIDEO_CONFIG
                )
            
            # 构建 Google AI Platform 格式的请求
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": task.request.prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": generation_config.temperature,
                    "topP": generation_config.top_p,
                    "topK": generation_config.top_k,
                    "maxOutputTokens": 8192,
                    "candidateCount": 1
                }
            }
            
            # 如果有种子，添加到配置中
            if generation_config.seed:
                payload["generationConfig"]["seed"] = generation_config.seed
            
            self.logger.info(f"📤 发送请求到: {api_url}")
            self.logger.info(f"📝 提示词长度: {len(task.request.prompt)} 字符")
            self.logger.info(f"🎬 模型: {model_name}")
            
            task.update_progress(30, "发送生成请求")
            
            # 获取请求头
            headers = get_request_headers()
            
            # 发送流式请求
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=REQUEST_CONFIG['timeout'],
                stream=True
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ 请求成功，开始接收流式响应")
                task.update_progress(40, "接收生成数据")
                
                # 处理流式响应
                result = self._process_streaming_response(response, task)
                
                if result:
                    task.complete(result)
                    self.logger.info(f"✅ 任务完成: {task.id}")
                else:
                    raise Exception("未能从流式响应中获取有效结果")
                    
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                raise Exception(f"API请求失败: {error_msg}")
        
        except Exception as e:
            self.logger.error(f"❌ 任务处理失败: {e}")
            self.logger.error(f"❌ 错误详情: {str(e)}")
            
            # 创建失败结果
            task.fail(str(e))
            raise
        
        finally:
            self._save_task(task)
    
    def _process_streaming_response(self, response, task: VideoGenerationTask) -> Optional[GenerationResult]:
        """
        处理流式响应
        
        Args:
            response: requests响应对象
            task: 视频生成任务
        
        Returns:
            生成结果或None
        """
        try:
            accumulated_content = []
            video_url = None
            chunk_count = 0
            
            # 读取流式响应
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8')
                
                # 跳过非数据行
                if not line.startswith('data: '):
                    continue
                
                # 解析JSON数据
                try:
                    json_str = line[6:]  # 移除 "data: " 前缀
                    data = json.loads(json_str)
                    
                    chunk_count += 1
                    
                    # 更新进度
                    if chunk_count % 5 == 0:
                        progress = min(40 + int(50 * chunk_count / 100), 90)
                        task.update_progress(progress, f"处理响应块 {chunk_count}")
                    
                    # 提取候选结果
                    candidates = data.get('candidates', [])
                    if candidates:
                        candidate = candidates[0]
                        content = candidate.get('content', {})
                        parts = content.get('parts', [])
                        
                        for part in parts:
                            if 'text' in part:
                                accumulated_content.append(part['text'])
                            elif 'executableCode' in part:
                                # 可能包含视频生成代码
                                code = part['executableCode']
                                self.logger.info(f"📝 收到可执行代码块")
                            elif 'fileData' in part:
                                # 可能包含生成的文件数据（视频）
                                file_data = part['fileData']
                                video_url = file_data.get('fileUri')
                                self.logger.info(f"🎬 收到视频文件URI: {video_url}")
                    
                    # 检查是否完成
                    finish_reason = candidates[0].get('finishReason') if candidates else None
                    if finish_reason == 'FINISH_REASON_STOP':
                        self.logger.info(f"✅ 生成完成")
                        break
                    
                except json.JSONDecodeError as e:
                    self.logger.warn(f"⚠️  无法解析JSON块: {e}")
                    continue
                except Exception as e:
                    self.logger.warn(f"⚠️  处理响应块时出错: {e}")
                    continue
            
            # 如果有视频URL，创建结果
            if video_url:
                # 创建视频结果
                duration = task.request.generation_config.duration_seconds if task.request.generation_config else DEFAULT_VIDEO_CONFIG['duration_seconds']
                resolution = task.request.generation_config.resolution if task.request.generation_config else DEFAULT_VIDEO_CONFIG['resolution']
                
                video = VideoResult(
                    id=f"video_{uuid.uuid4().hex[:8]}",
                    url=video_url,
                    duration_seconds=duration,
                    resolution=resolution,
                    fps=DEFAULT_VIDEO_CONFIG['fps'],
                    size_bytes=0,  # 未知
                    format="mp4",
                    thumbnail_url=""
                )
                
                return GenerationResult(
                    videos=[video],
                    finish_reason=FinishReason.FINISH_REASON_STOP
                )
            
            # 如果没有视频URL但有文本内容，记录警告
            if accumulated_content:
                self.logger.warn(f"⚠️  只收到文本响应，没有视频数据")
                self.logger.warn(f"📝 文本内容: {''.join(accumulated_content)[:200]}...")
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 处理流式响应失败: {e}")
            raise
    
    def _parse_api_result(self, api_data: dict, task: VideoGenerationTask) -> GenerationResult:
        """解析API返回的结果（用于非流式响应）"""
        # 从API响应中提取视频信息
        result_data = api_data.get("result", {})
        videos_data = result_data.get("videos", [])
        
        if not videos_data:
            # 检查Google AI格式的响应
            candidates = api_data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                
                for part in parts:
                    if 'fileData' in part:
                        file_data = part['fileData']
                        video_url = file_data.get('fileUri')
                        
                        if video_url:
                            duration = task.request.generation_config.duration_seconds if task.request.generation_config else DEFAULT_VIDEO_CONFIG['duration_seconds']
                            resolution = task.request.generation_config.resolution if task.request.generation_config else DEFAULT_VIDEO_CONFIG['resolution']
                            
                            video = VideoResult(
                                id=f"video_{uuid.uuid4().hex[:8]}",
                                url=video_url,
                                duration_seconds=duration,
                                resolution=resolution,
                                fps=DEFAULT_VIDEO_CONFIG['fps'],
                                size_bytes=0,
                                format="mp4",
                                thumbnail_url=""
                            )
                            
                            return GenerationResult(
                                videos=[video],
                                finish_reason=FinishReason.FINISH_REASON_STOP
                            )
            
            raise Exception("API返回结果中没有视频数据")
        
        # 转换为VideoResult对象
        videos = []
        for video_data in videos_data:
            video = VideoResult(
                id=video_data.get("id", f"video_{uuid.uuid4().hex[:8]}"),
                url=video_data.get("url", ""),
                duration_seconds=video_data.get("duration_seconds", 10.0),
                resolution=video_data.get("resolution", "1920x1080"),
                fps=video_data.get("fps", 24),
                size_bytes=video_data.get("size_bytes", 0),
                format=video_data.get("format", "mp4"),
                thumbnail_url=video_data.get("thumbnail_url", "")
            )
            videos.append(video)
        
        return GenerationResult(
            videos=videos,
            finish_reason=FinishReason.FINISH_REASON_STOP
        )
    
    def _create_mock_result(self, task: VideoGenerationTask) -> GenerationResult:
        """创建模拟结果（用于测试）"""
        # 实际实现时应该调用真实的视频生成API
        video = VideoResult(
            id=f"video_{uuid.uuid4().hex[:8]}",
            url=f"/static/generated_videos/{task.id}.mp4",
            duration_seconds=task.request.generation_config.duration_seconds if task.request.generation_config else 5.0,
            resolution=task.request.generation_config.resolution if task.request.generation_config else "1920x1080",
            fps=task.request.generation_config.fps if task.request.generation_config else 24,
            size_bytes=1024000,
            format="mp4",
            thumbnail_url=f"/static/generated_videos/{task.id}_thumb.jpg"
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
            self.logger.info("✅ 视频生成管理器已启动")
    
    def stop(self):
        """停止管理器"""
        if self._running:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5.0)
            self.logger.info("🛑 视频生成管理器已停止")
    
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
        task = VideoGenerationTask(request)
        
        if progress_callback:
            task.progress_callbacks.append(progress_callback)
        
        # 存储任务
        with self._tasks_lock:
            self.tasks[task.id] = task
        
        # 保存初始状态
        self._save_task(task)
        
        # 添加到队列
        self.task_queue.put(task.id)
        
        self.logger.info(f"📝 创建生成任务: {task.id}")
        
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
    
    def stream_generation(
        self,
        request: VideoGenerationRequest
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成视频（Server-Sent Events）
        
        Args:
            request: 生成请求
        
        Yields:
            事件字典
        """
        # 创建任务
        task = VideoGenerationTask(request)
        
        # 添加进度回调
        events_queue = Queue()
        
        def progress_callback(task_id: str, progress: int, stage: str):
            events_queue.put({
                "event": "progress_update",
                "data": {
                    "id": task_id,
                    "status": "processing",
                    "progress": progress,
                    "stage": stage
                }
            })
        
        task.progress_callbacks.append(progress_callback)
        
        # 存储任务
        with self._tasks_lock:
            self.tasks[task.id] = task
        
        # 发送开始事件
        yield {
            "event": "generation_started",
            "data": {
                "id": task.id,
                "status": "processing",
                "progress": 0
            }
        }
        
        # 添加到队列
        self.task_queue.put(task.id)
        
        # 等待完成并流式返回进度
        last_progress = 0
        while task.status == GenerationStatus.PROCESSING:
            try:
                event = events_queue.get(timeout=0.5)
                yield event
                last_progress = event["data"]["progress"]
            except Empty:
                # 检查任务状态
                if task.status != GenerationStatus.PROCESSING:
                    break
        
        # 发送最终事件
        if task.status == GenerationStatus.COMPLETED:
            yield {
                "event": "generation_complete",
                "data": task.to_response().to_dict()
            }
        elif task.status == GenerationStatus.FAILED:
            yield {
                "event": "generation_failed",
                "data": {
                    "id": task.id,
                    "error": task.error
                }
            }
        
        # 发送完成事件
        yield {
            "event": "done",
            "data": {}
        }


# 全局单例
_manager_instance: Optional[VideoGenerationManager] = None
_manager_lock = threading.Lock()


def get_video_generation_manager() -> VideoGenerationManager:
    """获取视频生成管理器单例"""
    global _manager_instance
    
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = VideoGenerationManager()
            _manager_instance.start()
    
    return _manager_instance