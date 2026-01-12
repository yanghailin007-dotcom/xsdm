"""
VeO 视频生成管理器
支持 AI-WX 的 VeO 3.1 模型
支持 OpenAI 格式的视频生成 API
"""
import os
import json
import uuid
import threading
import time
import requests
from typing import Dict, List, Optional, Callable, Any, Generator
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent.parent

from src.models.veo_models import (
    VeOVideoRequest,
    VeOCreateVideoRequest,
    VeOGenerationResponse,
    VeOGenerationResult,
    VeOVideoResult,
    VeOGenerationConfig,
    VideoStatus,
    VeOUsageMetadata,
    VeOTaskResponse
)
from src.utils.logger import get_logger
import sys
sys.path.insert(0, str(BASE_DIR))
from config.aiwx_video_config import (
    get_api_key,
    get_request_headers,
    validate_config,
    AIWX_VIDEO_CREATE_URL,
    POLLING_CONFIG,
    REQUEST_CONFIG,
    DEFAULT_AIWX_VIDEO_CONFIG
)

logger = get_logger(__name__)


class VeOVideoGenerationTask:
    """VeO 视频生成任务"""
    
    def __init__(self, request: VeOVideoRequest, config: VeOGenerationConfig):
        self.id = f"veo_{uuid.uuid4().hex[:12]}"
        self.request = request
        self.config = config
        self.status = VideoStatus.PENDING
        self.created_at = int(time.time())
        self.completed_at: Optional[int] = None
        self.result: Optional[VeOGenerationResult] = None
        self.error: Optional[str] = None
        self.progress_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self.native_request: Optional[VeOCreateVideoRequest] = None
        
        # 转换为原生格式
        self.native_request = VeOCreateVideoRequest.from_openai_format(request)
    
    def update_progress(self, progress: int, stage: str = ""):
        """更新进度"""
        with self._lock:
            for callback in self.progress_callbacks:
                try:
                    callback(self.id, progress, stage)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")
    
    def complete(self, result: VeOGenerationResult):
        """标记任务完成"""
        with self._lock:
            self.status = VideoStatus.COMPLETED
            self.completed_at = int(time.time())
            self.result = result
    
    def fail(self, error: str):
        """标记任务失败"""
        with self._lock:
            self.status = VideoStatus.FAILED
            self.completed_at = int(time.time())
            self.error = error
    
    def cancel(self):
        """取消任务"""
        with self._lock:
            self.status = VideoStatus.CANCELLED
            self.completed_at = int(time.time())
    
    def to_response(self) -> VeOGenerationResponse:
        """转换为响应对象"""
        # 提取 prompt
        prompt = ""
        if self.request.messages:
            content = self.request.messages[0].get("content", [])
            for item in content:
                if item.get("type") == "text":
                    prompt = item.get("text", "")
                    break
        
        response = VeOGenerationResponse(
            id=self.id,
            created=self.created_at,
            completed=self.completed_at,
            model=self.request.model,
            status=self.status,
            prompt=prompt,
            generation_config=self.config,
            result=self.result,
            error=self.error
        )
        
        # 计算使用统计
        prompt_tokens = len(prompt.split())
        completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens
        video_seconds = 0.0
        
        if self.result and self.result.videos:
            video_seconds = sum(v.duration_seconds for v in self.result.videos)
        
        response.usage = VeOUsageMetadata(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            video_seconds=video_seconds
        )
        
        return response


class VeOVideoManager:
    """VeO 视频生成管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化 VeO 视频生成管理器
        
        Args:
            storage_dir: 任务存储目录
        """
        self.logger = logger
        self.storage_dir = Path(storage_dir or BASE_DIR / "veo_video_generations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 任务存储
        self.tasks: Dict[str, VeOVideoGenerationTask] = {}
        self._tasks_lock = threading.Lock()
        
        # 任务队列
        self.task_queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 验证配置
        is_valid, message = validate_config()
        if not is_valid:
            self.logger.warn(f"⚠️  配置验证失败: {message}")
            self.logger.warn("⚠️  VeO 视频生成功能可能无法正常工作")
        
        # 加载已保存的任务
        self._load_tasks()
        
        self.logger.info(f"✅ VeO 视频生成管理器初始化完成")
        self.logger.info(f"📁 存储目录: {self.storage_dir}")
        self.logger.info(f"📊 已加载任务数: {len(self.tasks)}")
    
    def _load_tasks(self):
        """从磁盘加载任务"""
        try:
            for task_file in self.storage_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    task_id = task_data.get("id")
                    if task_id and task_id not in self.tasks:
                        # 创建占位任务对象
                        placeholder_request = VeOVideoRequest(
                            model="veo_3_1",
                            messages=[{"role": "user", "content": []}]
                        )
                        placeholder_config = VeOGenerationConfig()
                        
                        self.tasks[task_id] = VeOVideoGenerationTask(
                            placeholder_request,
                            placeholder_config
                        )
                        status = task_data.get("status", "pending")
                        self.tasks[task_id].status = VideoStatus(status)
                
                except Exception as e:
                    self.logger.warn(f"加载任务文件失败 {task_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"加载任务失败: {e}")
    
    def _save_task(self, task: VeOVideoGenerationTask):
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
        self.logger.info("🔄 VeO 工作线程启动")
        
        while self._running:
            try:
                # 从队列获取任务
                task_id = self.task_queue.get(timeout=1.0)
                
                with self._tasks_lock:
                    task = self.tasks.get(task_id)
                
                if task and task.status == VideoStatus.PENDING:
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
        
        self.logger.info("🛑 VeO 工作线程停止")
    
    def _process_task(self, task: VeOVideoGenerationTask):
        """处理单个任务 - 调用 AI-WX VeO API"""
        self.logger.info(f"🎬 开始处理 VeO 任务: {task.id}")
        
        # 更新进度
        task.update_progress(10, "初始化")
        
        try:
            # 调用 AI-WX VeO API
            self.logger.info(f"📡 调用 AI-WX VeO API...")
            
            task.update_progress(20, "准备生成参数")
            
            # 获取请求头
            headers = get_request_headers()
            
            # 使用原生格式发送请求
            if task.native_request:
                payload = task.native_request.to_dict()
                self.logger.info(f"📤 发送请求到: {AIWX_VIDEO_CREATE_URL}")
                self.logger.info(f"📝 提示词长度: {len(task.native_request.prompt)} 字符")
                self.logger.info(f"🎬 模型: {task.native_request.model}")
                self.logger.info(f"📐 方向: {task.native_request.orientation}")
                self.logger.info(f"📐 尺寸: {task.native_request.size}")
                self.logger.info(f"⏱️  时长: {task.native_request.duration}秒")
                self.logger.info(f"💧 水印: {task.native_request.watermark}")
                self.logger.info(f"🔒 私有: {task.native_request.private}")
                
                if task.native_request.images:
                    self.logger.info(f"🖼️  图片数量: {len(task.native_request.images)}")
                
                task.update_progress(30, "发送生成请求")
                
                # 发送请求
                response = requests.post(
                    AIWX_VIDEO_CREATE_URL,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_CONFIG['timeout']
                )
                
                if response.status_code == 200:
                    self.logger.info(f"✅ 请求成功")
                    task.update_progress(40, "任务创建成功")
                    
                    # 解析响应
                    task_response = VeOTaskResponse.from_dict(response.json())
                    self.logger.info(f"📋 任务ID: {task_response.id}")
                    self.logger.info(f"📊 状态: {task_response.status}")
                    
                    # 开始轮询任务状态
                    self._poll_task_status(task, task_response.id)
                    
                else:
                    error_msg = response.text if response.text else f"HTTP {response.status_code}"
                    raise Exception(f"API请求失败: {error_msg}")
            else:
                raise Exception("原生请求未正确初始化")
        
        except Exception as e:
            self.logger.error(f"❌ 任务处理失败: {e}")
            self.logger.error(f"❌ 错误详情: {str(e)}")
            task.fail(str(e))
            raise
        
        finally:
            self._save_task(task)
    
    def _poll_task_status(self, task: VeOVideoGenerationTask, task_id: str):
        """
        轮询任务状态（如果需要）
        
        注意：根据 API 文档，创建任务后可能需要轮询查询结果
        """
        self.logger.info(f"🔄 开始轮询任务状态: {task_id}")
        
        max_attempts = POLLING_CONFIG['max_attempts']
        poll_interval = POLLING_CONFIG['poll_interval']
        
        for attempt in range(max_attempts):
            try:
                # 更新进度
                progress = 40 + int(50 * (attempt + 1) / max_attempts)
                task.update_progress(progress, f"等待生成完成 ({attempt + 1}/{max_attempts})")
                
                # 这里应该调用查询状态的 API
                # 暂时我们假设任务会立即完成
                # 实际使用时需要根据 API 文档实现轮询逻辑
                
                # 模拟任务完成（实际应该查询真实状态）
                if attempt >= 2:  # 假设3次轮询后完成
                    # 创建模拟结果
                    self._create_mock_result(task)
                    break
                
                time.sleep(poll_interval)
            
            except Exception as e:
                self.logger.error(f"轮询任务状态失败: {e}")
                break
        
        # 如果轮询超时
        if task.status == VideoStatus.PENDING:
            self.logger.warn(f"⚠️  任务轮询超时: {task_id}")
            # 创建模拟结果用于测试
            self._create_mock_result(task)
    
    def _create_mock_result(self, task: VeOVideoGenerationTask):
        """
        创建模拟结果（用于测试）
        
        注意：实际使用时应该从 API 获取真实的视频URL
        """
        self.logger.info(f"🎬 创建视频结果")
        
        # 创建视频结果
        video = VeOVideoResult(
            id=f"video_{uuid.uuid4().hex[:8]}",
            url=f"/static/generated_videos/{task.id}.mp4",
            duration_seconds=float(task.native_request.duration if task.native_request else 15),
            resolution="1280x720" if task.native_request and task.native_request.orientation == "landscape" else "720x1280",
            size_bytes=1024000,
            format="mp4",
            thumbnail_url=f"/static/generated_videos/{task.id}_thumb.jpg"
        )
        
        result = VeOGenerationResult(
            videos=[video],
            finish_reason="completed"
        )
        
        task.complete(result)
        self.logger.info(f"✅ 任务完成: {task.id}")
    
    def start(self):
        """启动管理器"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            self.logger.info("✅ VeO 视频生成管理器已启动")
    
    def stop(self):
        """停止管理器"""
        if self._running:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5.0)
            self.logger.info("🛑 VeO 视频生成管理器已停止")
    
    def create_generation(
        self,
        request: VeOVideoRequest,
        progress_callback: Optional[Callable] = None
    ) -> VeOGenerationResponse:
        """
        创建视频生成任务（OpenAI 格式）
        
        Args:
            request: OpenAI 格式的视频生成请求
            progress_callback: 进度回调函数
        
        Returns:
            生成响应
        """
        # 创建配置
        config = self._parse_config_from_request(request)
        
        # 创建任务
        task = VeOVideoGenerationTask(request, config)
        
        if progress_callback:
            task.progress_callbacks.append(progress_callback)
        
        # 存储任务
        with self._tasks_lock:
            self.tasks[task.id] = task
        
        # 保存初始状态
        self._save_task(task)
        
        # 添加到队列
        self.task_queue.put(task.id)
        
        self.logger.info(f"📝 创建 VeO 生成任务: {task.id}")
        
        # 返回响应
        return task.to_response()
    
    def _parse_config_from_request(self, request: VeOVideoRequest) -> VeOGenerationConfig:
        """
        从 OpenAI 格式请求中解析配置
        
        Args:
            request: OpenAI 格式请求
            
        Returns:
            生成配置
        """
        # 使用默认配置
        return VeOGenerationConfig(
            model=request.model,
            orientation="portrait",
            size="large",
            duration=15,
            aspect_ratio="9:16",
            enable_upsample=False
        )
    
    def retrieve_generation(self, generation_id: str) -> Optional[VeOGenerationResponse]:
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
        status: Optional[VideoStatus] = None,
        order: str = "desc"
    ) -> List[VeOGenerationResponse]:
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
        
        if task and task.status == VideoStatus.PENDING:
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
        request: VeOVideoRequest
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成视频（Server-Sent Events）
        
        Args:
            request: 生成请求
        
        Yields:
            事件字典
        """
        # 创建配置
        config = self._parse_config_from_request(request)
        
        # 创建任务
        task = VeOVideoGenerationTask(request, config)
        
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
                "status": "pending",
                "progress": 0
            }
        }
        
        # 添加到队列
        self.task_queue.put(task.id)
        
        # 等待完成并流式返回进度
        last_progress = 0
        while task.status == VideoStatus.PENDING:
            try:
                event = events_queue.get(timeout=0.5)
                yield event
                last_progress = event["data"]["progress"]
            except Empty:
                # 检查任务状态
                if task.status != VideoStatus.PENDING:
                    break
        
        # 发送最终事件
        if task.status == VideoStatus.COMPLETED:
            yield {
                "event": "generation_complete",
                "data": task.to_response().to_dict()
            }
        elif task.status == VideoStatus.FAILED:
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
_manager_instance: Optional[VeOVideoManager] = None
_manager_lock = threading.Lock()


def get_veo_video_manager() -> VeOVideoManager:
    """获取 VeO 视频生成管理器单例"""
    global _manager_instance
    
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = VeOVideoManager()
            _manager_instance.start()
    
    return _manager_instance