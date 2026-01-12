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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (OpenAI 格式)"""
        return {
            "model": self.model,
            "stream": self.stream,
            "messages": self.messages
        }


@dataclass
class VeOCreateVideoRequest:
    """VeO 创建视频请求 (原生格式)"""
    images: List[str] = field(default_factory=list)
    model: str = "sora-2"
    orientation: str = "portrait"
    prompt: str = ""
    size: str = "large"
    duration: int = 15
    aspect_ratio: str = "16:9"
    enable_upsample: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "images": self.images,
            "model": self.model,
            "orientation": self.orientation,
            "prompt": self.prompt,
            "size": self.size,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "enable_upsample": self.enable_upsample
        }
    
    @classmethod
    def from_openai_format(cls, request: VeOVideoRequest) -> 'VeOCreateVideoRequest':
        """
        从 OpenAI 格式转换为原生格式
        
        Args:
            request: OpenAI 格式请求
            
        Returns:
            原生格式请求
        """
        # 解析模型名称
        model = request.model
        parts = model.split('-')
        
        # 默认配置
        orientation = "portrait"
        size = "small"
        enable_upsample = False
        
        # 解析模型参数
        for part in parts[1:]:
            if part == "portrait":
                orientation = "portrait"
            elif part == "landscape":
                orientation = "landscape"
            elif part == "fast":
                size = "small"  # 快速模式使用小尺寸
            elif part == "fl":
                pass  # 首尾帧模式
        
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
        
        # 确定宽高比
        aspect_ratio = "9:16" if orientation == "portrait" else "16:9"
        
        return cls(
            images=images,
            model="sora-2",
            orientation=orientation,
            prompt=prompt,
            size=size,
            duration=10,
            aspect_ratio=aspect_ratio,
            enable_upsample=enable_upsample
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
        
        if self.result:
            result["result"] = self.result.to_dict()
        
        if self.usage:
            result["usage"] = self.usage.to_dict()
        
        if self.error:
            result["error"] = self.error
        
        if self.estimated_completion_time:
            result["estimated_completion_time"] = self.estimated_completion_time
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


@dataclass
class VeOErrorResponse:
    """VeO 错误响应"""
    error: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.error