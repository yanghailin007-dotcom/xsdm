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
    VeOTaskResponse,
    VeOQueryResponse
)
from src.utils.logger import get_logger
from src.utils.image_compressor import validate_and_compress_images, MAX_IMAGE_SIZE_MB
import sys
sys.path.insert(0, str(BASE_DIR))
from config.aiwx_video_config import (
    get_api_key,
    get_request_headers,
    validate_config,
    AIWX_VIDEO_CREATE_URL,
    AIWX_VIDEO_QUERY_URL,
    POLLING_CONFIG,
    REQUEST_CONFIG,
    DEFAULT_AIWX_VIDEO_CONFIG
)

logger = get_logger(__name__)


class VeOVideoGenerationTask:
    """VeO 视频生成任务"""
    
    def __init__(self, request: VeOVideoRequest, config: VeOGenerationConfig, native_request: Optional[VeOCreateVideoRequest] = None):
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
        self._current_progress: int = 0  # 🔥 新增：当前进度
        self._current_stage: str = ""  # 🔥 新增：当前阶段
        
        # 转换为原生格式（如果提供了原生请求则使用，否则转换）
        self.native_request = native_request or VeOCreateVideoRequest.from_openai_format(request)
    
    def update_progress(self, progress: int, stage: str = ""):
        """更新进度"""
        with self._lock:
            self._current_progress = progress
            self._current_stage = stage
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
            error=self.error,
            progress=self._current_progress,  # 🔥 添加当前进度
            stage=self._current_stage  # 🔥 添加当前阶段
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
            # 清空现有任务列表
            self.tasks.clear()
            
            loaded_count = 0
            for task_file in self.storage_dir.glob("*.json"):
                try:
                    # 🔥 关键修复：使用文件名作为ID（去掉.json后缀）
                    # 文件名格式：veo_abc123def456.json
                    task_id = task_file.stem  # 自动去掉.json后缀
                    
                    # 验证ID格式（必须以veo_开头）
                    if not task_id.startswith("veo_"):
                        self.logger.warn(f"⚠️  跳过无效文件名: {task_file.name}")
                        continue
                    
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                    
                    # 🔥 修复：确保JSON内容中的ID与文件名一致
                    # 如果JSON中的ID与文件名不同，使用文件名（作为真实来源）
                    json_id = task_data.get("id")
                    if json_id and json_id != task_id:
                        self.logger.warn(f"⚠️  ID不匹配: 文件名={task_id}, JSON={json_id}，使用文件名")
                    
                    # 🔥 关键修复：从保存的JSON中读取prompt
                    saved_prompt = task_data.get("prompt", "")
                    model_name = task_data.get("model", "veo_3_1-fast")
                    
                    # 创建占位任务对象，但包含保存的prompt
                    placeholder_request = VeOVideoRequest(
                        model=model_name,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": saved_prompt}
                            ]
                        }]
                    )
                    placeholder_config = VeOGenerationConfig()
                          
                    # 创建任务并强制设置ID为文件名中的ID
                    task = VeOVideoGenerationTask(
                        placeholder_request,
                        placeholder_config
                    )
                    task.id = task_id  # 🔥 强制使用文件名中的ID
                    
                    # 🔥 新增：恢复进度和阶段信息
                    if task_data.get("progress") is not None:
                        task._current_progress = task_data["progress"]
                    if task_data.get("stage"):
                        task._current_stage = task_data["stage"]
                    
                    # 设置状态
                    status_str = task_data.get("status", "pending")
                    try:
                        task.status = VideoStatus(status_str)
                    except ValueError:
                        self.logger.warn(f"⚠️  无效状态: {status_str}，使用默认值")
                        task.status = VideoStatus.PENDING
                    
                    # 设置其他属性
                    task.created_at = task_data.get("created", int(time.time()))
                    if task_data.get("completed"):
                        task.completed_at = task_data["completed"]
                    
                    # 设置错误信息（如果有）
                    if task_data.get("error"):
                        task.error = task_data["error"]
                    
                    # 🔥 关键修复：恢复result数据（视频结果）
                    result_data = task_data.get("result")
                    if result_data and task.status == VideoStatus.COMPLETED:
                        try:
                            videos_data = result_data.get("videos", [])
                            videos = []
                            
                            for video_data in videos_data:
                                video = VeOVideoResult(
                                    id=video_data.get("id", ""),
                                    url=video_data.get("url", ""),
                                    duration_seconds=video_data.get("duration_seconds", 0.0),
                                    resolution=video_data.get("resolution", ""),
                                    size_bytes=video_data.get("size_bytes", 0),
                                    format=video_data.get("format", "mp4"),
                                    thumbnail_url=video_data.get("thumbnail_url", "")
                                )
                                videos.append(video)
                            
                            if videos:
                                task.result = VeOGenerationResult(
                                    videos=videos,
                                    finish_reason=result_data.get("finish_reason", "completed")
                                )
                                self.logger.info(f"✅ 恢复任务 {task_id} 的视频结果: {len(videos)} 个视频")
                        except Exception as e:
                            self.logger.warn(f"⚠️ 恢复任务 {task_id} 的结果失败: {e}")
                    
                    self.tasks[task_id] = task
                    loaded_count += 1
                    
                    self.logger.debug(f"✅ 加载任务: {task_id} (状态: {task.status})")
                
                except Exception as e:
                    self.logger.warn(f"加载任务文件失败 {task_file}: {e}")
            
            self.logger.info(f"✅ 从磁盘加载了 {loaded_count} 个任务")
        
        except Exception as e:
            self.logger.error(f"❌ 加载任务失败: {e}")
    
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
                # 🔥 修复：区分URL模式和base64模式
                # 如果是URL模式，不需要压缩
                # 如果是base64模式，需要压缩
                if task.native_request.images:
                    # 检查是否所有图片都是URL
                    all_urls = all(self._is_url(img) for img in task.native_request.images if img)
                    
                    if all_urls:
                        # URL模式：直接使用，不需要压缩
                        self.logger.info(f"🔗 URL模式：使用 {len(task.native_request.images)} 个图片URL")
                        compressed_images = task.native_request.images
                    else:
                        # base64模式：需要压缩
                        self.logger.info(f"🖼️  Base64模式：开始压缩 {len(task.native_request.images)} 张图片...")
                        compressed_images, compression_stats = validate_and_compress_images(
                            task.native_request.images,
                            max_size_mb=MAX_IMAGE_SIZE_MB
                        )
                    
                    # 更新请求对象中的图片
                    task.native_request.images = compressed_images
                
                payload = task.native_request.to_dict()
                self.logger.info(f"📤 发送请求到: {AIWX_VIDEO_CREATE_URL}")
                self.logger.info(f"📝 提示词长度: {len(task.native_request.prompt)} 字符")
                self.logger.info(f"🎬 模型: {task.native_request.model}")
                self.logger.info(f"📐 方向: {task.native_request.orientation}")
                self.logger.info(f"📐 尺寸: {task.native_request.size}")
                self.logger.info(f"⏱️  时长: {task.native_request.duration}秒")
                self.logger.info(f"💧 水印: {task.native_request.watermark}")
                self.logger.info(f"🔒 私有: {task.native_request.private}")
                
                if compressed_images:
                    self.logger.info(f"🖼️  图片数量: {len(compressed_images)}")
                
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
        使用标准查询接口轮询任务状态
        
        使用 /v1/video/query?id={task_id} 端点查询任务状态
        
        🔥 重要：只要任务状态是 in_progress/processing，就会持续轮询
        不会因为达到固定次数就停止，除非：
        1. 任务完成（completed）
        2. 任务失败（failed）
        3. 达到总超时时间（30分钟）
        """
        self.logger.info(f"🔄 开始轮询任务状态: {task_id}")
        
        poll_interval = POLLING_CONFIG['poll_interval']
        last_progress = 0
        attempt = 0
        
        # 🔥 使用无限循环，只要任务还在处理中就继续
        while True:
            attempt += 1
            try:
                # 更新进度（基于实际进度，而不是模拟）
                # 使用尝试次数的倒数来模拟进度增长（作为备用）
                simulated_progress = min(40 + int(50 * min(attempt / 100, 1)), 95)
                task.update_progress(simulated_progress, f"正在生成视频... (第 {attempt} 次查询)")
                
                # 构建查询URL - 使用新的标准查询接口
                query_url = f"{AIWX_VIDEO_QUERY_URL}?id={task_id}"
                self.logger.info(f"📡 查询任务状态: {query_url}")
                
                # 获取请求头
                headers = get_request_headers()
                
                # 查询任务状态
                response = requests.get(query_url, headers=headers, timeout=REQUEST_CONFIG['timeout'])
                
                if response.status_code == 200:
                    self.logger.info(f"✅ 查询成功")
                    
                    # 解析响应
                    result_data = response.json()
                    self.logger.info(f"📊 响应数据: {json.dumps(result_data, ensure_ascii=False)[:500]}")
                    
                    # 使用标准响应模型解析
                    query_response = VeOQueryResponse.from_dict(result_data)
                    
                    # 🔥 关键修复：使用API返回的真实进度
                    api_progress = query_response.progress or 0
                    if api_progress > last_progress:
                        # 更新为真实进度：40%基础 + (API进度 * 60%)
                        real_progress = 40 + int(api_progress * 0.6)
                        task.update_progress(real_progress, f"生成进度: {api_progress}%")
                        last_progress = api_progress
                        self.logger.info(f"📈 真实进度: {api_progress}%")
                    
                    # 检查状态
                    if query_response.is_completed():
                        # 任务完成
                        video_url = query_response.video_url
                        
                        if video_url:
                            self.logger.info(f"🎬 视频URL: {video_url}")
                            
                            # 提取视频分辨率
                            width = query_response.width or (1280 if task.native_request and task.native_request.orientation == "landscape" else 720)
                            height = query_response.height or (720 if task.native_request and task.native_request.orientation == "landscape" else 1280)
                            resolution = f"{width}x{height}"
                            
                            # 创建真实结果
                            video = VeOVideoResult(
                                id=f"video_{uuid.uuid4().hex[:8]}",
                                url=video_url,
                                duration_seconds=float(10),
                                resolution=resolution,
                                size_bytes=1024000,
                                format="mp4",
                                thumbnail_url=query_response.thumbnail_url or ""
                            )
                            
                            result = VeOGenerationResult(
                                videos=[video],
                                finish_reason="completed"
                            )
                            
                            task.complete(result)
                            self.logger.info(f"✅ 任务完成: {task.id}")
                            return
                        else:
                            self.logger.warn(f"⚠️ 未找到视频URL")
                    
                    elif query_response.is_failed():
                        # 任务失败
                        error_msg = "视频生成失败"
                        if query_response.detail:
                            error_detail = query_response.detail.get('failure_reason')
                            if error_detail:
                                error_msg = error_detail
                        task.fail(error_msg)
                        return
                    
                    elif query_response.is_processing():
                        self.logger.info(f"⏳ 任务仍在处理中 (状态: {query_response.status}, 进度: {api_progress}%)，继续轮询...")
                    
                    else:
                        self.logger.info(f"📊 当前状态: {query_response.status}, 进度: {api_progress}%")
                
                else:
                    self.logger.warn(f"⚠️ 请求失败: HTTP {response.status_code}")
                    # 继续轮询
                    time.sleep(poll_interval)
            
            except Exception as e:
                self.logger.error(f"轮询任务状态失败: {e}")
                # 继续重试，不中断
                time.sleep(poll_interval)
            
            # 🔥 检查是否应该继续轮询
            # 只有在任务完成、失败或达到总超时时间时才停止
            total_time = attempt * poll_interval
            max_total_time = 30 * 60  # 最多30分钟
            
            if task.status != VideoStatus.PENDING:
                # 任务已完成（成功或失败）
                self.logger.info(f"✅ 轮询结束: {task_id}，最终状态: {task.status}")
                break
            
            if total_time >= max_total_time:
                # 达到总超时时间
                self.logger.warn(f"⚠️  任务轮询超时: {task_id} (已轮询 {total_time/60:.1f} 分钟)")
                self.logger.warn(f"💡 提示：任务可能仍在后台生成，请稍后使用任务ID查询状态")
                task.error = f"轮询超时（已{total_time/60:.1f}分钟），任务可能仍在处理中"
                break
    
    
    def _is_url(self, img_str: str) -> bool:
        """判断图片字符串是否为URL"""
        if not img_str or not isinstance(img_str, str):
            return False
        return img_str.startswith(('http://', 'https://'))
    
    
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
        native_request: Optional[VeOCreateVideoRequest] = None,
        progress_callback: Optional[Callable] = None
    ) -> VeOGenerationResponse:
        """
        创建视频生成任务（OpenAI 格式）
        
        Args:
            request: OpenAI 格式的视频生成请求
            native_request: VeO 原生格式请求（保留完整配置参数）
            progress_callback: 进度回调函数
        
        Returns:
            生成响应
        """
        # 创建配置
        config = self._parse_config_from_request(request)
        
        # 创建任务（传递原生请求以保留配置参数）
        task = VeOVideoGenerationTask(request, config, native_request)
        
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
        # 从messages中提取duration（如果有）
        duration = 10  # VeO只支持10秒
        orientation = "portrait"
        aspect_ratio = "9:16"
        
        # 尝试从消息中提取配置信息
        if request.messages:
            content = request.messages[0].get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "").lower()
                    # 简单的文本解析（可以根据需要扩展）
                    if "landscape" in text or "16:9" in text:
                        orientation = "landscape"
                        aspect_ratio = "16:9"
        
        return VeOGenerationConfig(
            model=request.model,
            orientation=orientation,
            size="large",
            duration=duration,
            aspect_ratio=aspect_ratio,
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
        self.logger.info(f"🗑️ 请求删除任务: {generation_id}")
        
        # 🔥 修复：先删除文件（即使内存中没有也能删除）
        task_file = self.storage_dir / f"{generation_id}.json"
        file_deleted = False
        
        if task_file.exists():
            try:
                task_file.unlink()
                file_deleted = True
                self.logger.info(f"✅ 已删除任务文件: {task_file}")
            except Exception as e:
                self.logger.error(f"❌ 删除任务文件失败: {e}")
        
        # 🔥 修复：从内存中移除（如果存在）
        with self._tasks_lock:
            task = self.tasks.pop(generation_id, None)
        
        # 🔥 修复：只要文件删除成功或任务存在于内存，就认为删除成功
        if file_deleted or task:
            self.logger.info(f"✅ 任务删除成功: {generation_id}")
            return True
        
        self.logger.warn(f"⚠️ 任务不存在: {generation_id}")
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