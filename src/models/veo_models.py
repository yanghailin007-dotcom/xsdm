"""
VeO 视频生成 API 数据模型
支持 AI-WX 的 VeO 3.1 模型
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class VideoStatus(str, Enum):
    """视频生成状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoOrientation(str, Enum):
    """视频方向"""
    PORTRAIT = "portrait"  # 竖屏
    LANDSCAPE = "landscape"  # 横屏


class VideoSize(str, Enum):
    """视频尺寸"""
    SMALL = "small"  # 一般720p
    LARGE = "large"  # 1080p+


class AspectRatio(str, Enum):
    """宽高比"""
    RATIO_16_9 = "16:9"  # 横屏
    RATIO_9_16 = "9:16"  # 竖屏


@dataclass
class VeOGenerationConfig:
    """VeO 生成配置"""
    model: str = "veo_3_1"
    orientation: str = "portrait"
    size: str = "small"
    duration: int = 10
    aspect_ratio: str = "9:16"
    enable_upsample: bool = False
    
    def __post_init__(self):
        """初始化后验证"""
        # 验证时长
        if self.duration not in [10]:
            raise ValueError(f"不支持的视频时长: {self.duration}, 仅支持 10 秒")
        
        # 验证方向和宽高比一致性
        if self.orientation == "portrait" and self.aspect_ratio != "9:16":
            raise ValueError(f"竖屏模式必须使用 9:16 宽高比, 当前: {self.aspect_ratio}")
        if self.orientation == "landscape" and self.aspect_ratio != "16:9":
            raise ValueError(f"横屏模式必须使用 16:9 宽高比, 当前: {self.aspect_ratio}")
        
        # 验证高清模式仅支持横屏
        if self.enable_upsample and self.orientation != "landscape":
            raise ValueError("enable_upsample (高清) 仅支持横屏模式")


@dataclass
class VeOImageInput:
    """图片输入"""
    url: str
    type: str = "image_url"  # image_url 或 reference
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            self.type: {
                "url": self.url
            }
        }


@dataclass
class VeOVideoRequest:
    """VeO 视频生成请求 (OpenAI 格式)"""
    model: str
    messages: List[Dict[str, Any]]
    stream: bool = True

    # 元数据字段（可选，用于传递项目信息等）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (OpenAI 格式)"""
        return {
            "model": self.model,
            "stream": self.stream,
            "messages": self.messages
        }


@dataclass
class VeOCreateVideoRequest:
    """VeO 创建视频请求 (原生格式)

    支持两种图片输入模式：
    1. URL 模式（推荐）：直接传递图片 URL，无需 base64 编码
    2. Base64 模式：传递 base64 编码的图片数据（会自动压缩）
    """
    images: List[str] = field(default_factory=list)  # 支持图片 URL 或 base64
    image_urls: List[str] = field(default_factory=list)  # 新增：专门的图片 URL 字段
    model: str = "veo_3_1-fast"
    orientation: str = "portrait"
    prompt: str = ""
    size: str = "large"
    duration: int = 10
    watermark: bool = False
    private: bool = True

    # 🔥 新增：元数据字段，用于按项目/分集组织视频
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_image_urls(self) -> bool:
        """检查是否有图片 URL（不包括 data URL）"""
        return bool(self.image_urls) or any(self._is_url(img) for img in self.images if img)
    
    def _is_url(self, img_str: str) -> bool:
        """判断是否为 HTTP/HTTPS URL（不包括 data URL）"""
        if not img_str or not isinstance(img_str, str):
            return False
        # 只识别 http:// 和 https://，不识别 data:
        return img_str.startswith(('http://', 'https://'))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 优先使用 image_urls（如果有）
        if self.image_urls:
            images_param = self.image_urls
        else:
            # 处理 images 列表
            # 🔥 修复：保留 data URL 格式，让 API 能够识别图片格式
            images_param = []
            for img in self.images:
                if not img or not isinstance(img, str):
                    continue
                
                # 如果是 HTTP/HTTPS URL，直接使用
                if self._is_url(img):
                    images_param.append(img)
                # 如果是 data URL，保留完整格式（包含格式信息）
                elif img.startswith('data:image/'):
                    # 🔥 保留完整的 data URL 格式，让 API 能够识别图片格式
                    # 格式: data:image/jpeg;base64,<base64_data>
                    images_param.append(img)
                # 否则认为是纯 base64，添加默认的 JPEG 格式前缀
                else:
                    # 🔥 为纯 base64 数据添加格式前缀
                    # 默认使用 JPEG 格式（因为压缩后通常是 JPEG）
                    images_param.append(f"data:image/jpeg;base64,{img}")
        
        return {
            "images": images_param,
            "model": self.model,
            "orientation": self.orientation,
            "prompt": self.prompt,
            "size": self.size,
            "duration": self.duration,
            "watermark": self.watermark,
            "private": self.private
        }
    
    @classmethod
    def from_openai_format(cls, request: VeOVideoRequest, native_request: Optional['VeOCreateVideoRequest'] = None) -> 'VeOCreateVideoRequest':
        """
        从 OpenAI 格式转换为原生格式
        
        Args:
            request: OpenAI 格式请求
            native_request: 原生请求对象（如果提供，将优先使用其配置）
            
        Returns:
            原生格式请求
        """
        # 如果提供了原生请求对象，直接使用其配置
        if native_request:
            return native_request
        
        # 解析模型名称
        model = request.model
        
        # 提取图片和文本
        images = []
        prompt = ""
        
        if request.messages:
            user_message = request.messages[0]
            content = user_message.get("content", [])
            
            for item in content:
                if item.get("type") == "text":
                    prompt = item.get("text", "")
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url:
                        images.append(url)
        
        # 使用原始模型名称（应该是 veo_3_1-fast）
        return cls(
            images=images,
            model=model,
            orientation="portrait",
            prompt=prompt,
            size="large",
            duration=10,  # VeO 只支持 10 秒
            watermark=False,
            private=True,
            metadata=getattr(request, 'metadata', {})  # 传递 metadata
        )


@dataclass
class VeOTaskResponse:
    """VeO 任务创建响应"""
    id: str
    status: str
    status_update_time: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VeOTaskResponse':
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            status=data.get("status", "pending"),
            status_update_time=data.get("status_update_time", 0)
        )


@dataclass
class VeOQueryResponse:
    """VeO 视频查询响应（标准格式）

    匹配 /v1/video/query 接口的响应格式
    """
    id: str
    status: str
    video_url: Optional[str]
    enhanced_prompt: str
    status_update_time: int
    detail: Optional[Dict[str, Any]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None
    progress: Optional[int] = None  # 🔥 新增：生成进度（0-100）
    model: Optional[str] = None  # 🔥 新增：使用的模型
    seconds: Optional[str] = None  # 🔥 新增：视频时长
    error: Optional[Dict[str, str]] = None  # 🔥 新增：错误信息

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VeOQueryResponse':
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            status=data.get("status", "pending"),
            video_url=data.get("video_url"),
            enhanced_prompt=data.get("enhanced_prompt", ""),
            status_update_time=data.get("status_update_time", 0),
            detail=data.get("detail"),
            width=data.get("width"),
            height=data.get("height"),
            thumbnail_url=data.get("thumbnail_url"),
            progress=data.get("progress"),  # 🔥 解析进度
            model=data.get("model"),  # 🔥 解析模型
            seconds=data.get("seconds"),  # 🔥 解析时长
            error=data.get("error")  # 🔥 解析错误信息
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "id": self.id,
            "status": self.status,
            "video_url": self.video_url,
            "enhanced_prompt": self.enhanced_prompt,
            "status_update_time": self.status_update_time
        }
        
        if self.detail is not None:
            result["detail"] = self.detail
        if self.width is not None:
            result["width"] = self.width
        if self.height is not None:
            result["height"] = self.height
        if self.thumbnail_url is not None:
            result["thumbnail_url"] = self.thumbnail_url
        
        return result
    
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return self.status == "completed" and self.video_url is not None
    
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.status == "failed"
    
    def is_processing(self) -> bool:
        """检查任务是否处理中"""
        return self.status in ["pending", "processing"]


@dataclass
class VeOVideoResult:
    """VeO 视频结果"""
    id: str
    url: str
    duration_seconds: float
    resolution: str
    size_bytes: int = 0
    format: str = "mp4"
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "url": self.url,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "size_bytes": self.size_bytes,
            "format": self.format,
            "thumbnail_url": self.thumbnail_url,
            "metadata": self.metadata
        }


@dataclass
class VeOGenerationResult:
    """VeO 生成结果"""
    videos: List[VeOVideoResult]
    finish_reason: str = "completed"
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "videos": [v.to_dict() for v in self.videos],
            "finish_reason": self.finish_reason,
            "error": self.error
        }


@dataclass
class VeOUsageMetadata:
    """VeO 使用元数据"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    video_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "video_seconds": self.video_seconds
        }


@dataclass
class VeOGenerationResponse:
    """VeO 生成响应"""
    id: str
    object: str = "video.generation"
    created: Optional[int] = None
    completed: Optional[int] = None
    model: str = ""
    status: VideoStatus = VideoStatus.PENDING
    prompt: str = ""
    generation_config: Optional[VeOGenerationConfig] = None
    result: Optional[VeOGenerationResult] = None
    usage: Optional[VeOUsageMetadata] = None
    error: Optional[str] = None
    estimated_completion_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress: Optional[int] = None  # 🔥 新增：生成进度（0-100）
    stage: Optional[str] = None  # 🔥 新增：当前阶段描述
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created is None:
            self.created = int(datetime.now().timestamp())
        if isinstance(self.status, str):
            self.status = VideoStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "status": self.status.value if isinstance(self.status, VideoStatus) else self.status,
            "prompt": self.prompt
        }
        
        if self.completed:
            result["completed"] = self.completed
        
        if self.generation_config:
            result["generation_config"] = {
                "model": self.generation_config.model,
                "orientation": self.generation_config.orientation,
                "size": self.generation_config.size,
                "duration": self.generation_config.duration,
                "aspect_ratio": self.generation_config.aspect_ratio,
                "enable_upsample": self.generation_config.enable_upsample
            }
        
        # 🔥 关键修复：始终包含result字段，即使为None
        # 这样前端可以正确判断是否有视频URL
        if self.result:
            result["result"] = self.result.to_dict()
        else:
            # 即使result为None，也要包含这个字段，让前端知道没有结果
            result["result"] = None
        
        if self.usage:
            result["usage"] = self.usage.to_dict()
        
        if self.error:
            result["error"] = self.error
        
        if self.estimated_completion_time:
            result["estimated_completion_time"] = self.estimated_completion_time
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        # 🔥 添加进度和阶段信息
        if self.progress is not None:
            result["progress"] = self.progress
        if self.stage is not None:
            result["stage"] = self.stage
        
        return result


@dataclass
class VeOErrorResponse:
    """VeO 错误响应"""
    error: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.error