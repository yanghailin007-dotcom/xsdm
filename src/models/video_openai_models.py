"""
OpenAI 标准视频生成 API 数据模型

符合 OpenAI API 规范的请求和响应模型
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class HarmCategory(str, Enum):
    """安全类别"""
    HARM_CATEGORY_UNSPECIFIED = "HARM_CATEGORY_UNSPECIFIED"
    HARM_CATEGORY_HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
    HARM_CATEGORY_DANGEROUS_CONTENT = "HARM_CATEGORY_DANGEROUS_CONTENT"
    HARM_CATEGORY_HARASSMENT = "HARM_CATEGORY_HARASSMENT"
    HARM_CATEGORY_SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"


class HarmBlockThreshold(str, Enum):
    """屏蔽阈值"""
    HARM_BLOCK_THRESHOLD_UNSPECIFIED = "HARM_BLOCK_THRESHOLD_UNSPECIFIED"
    BLOCK_LOW_AND_ABOVE = "BLOCK_LOW_AND_ABOVE"
    BLOCK_MEDIUM_AND_ABOVE = "BLOCK_MEDIUM_AND_ABOVE"
    BLOCK_ONLY_HIGH = "BLOCK_ONLY_HIGH"
    BLOCK_NONE = "BLOCK_NONE"
    OFF = "OFF"


class HarmBlockMethod(str, Enum):
    """屏蔽方法"""
    HARM_BLOCK_METHOD_UNSPECIFIED = "HARM_BLOCK_METHOD_UNSPECIFIED"
    SEVERITY = "SEVERITY"
    PROBABILITY = "PROBABILITY"


class FinishReason(str, Enum):
    """完成原因"""
    FINISH_REASON_UNSPECIFIED = "FINISH_REASON_UNSPECIFIED"
    FINISH_REASON_STOP = "FINISH_REASON_STOP"
    FINISH_REASON_MAX_TOKENS = "FINISH_REASON_MAX_TOKENS"
    FINISH_REASON_SAFETY = "FINISH_REASON_SAFETY"
    FINISH_REASON_RECITATION = "FINISH_REASON_RECITATION"
    FINISH_REASON_BLOCKLIST = "FINISH_REASON_BLOCKLIST"
    FINISH_REASON_PROHIBITED_CONTENT = "FINISH_REASON_PROHIBITED_CONTENT"
    FINISH_REASON_IMAGE_PROHIBITED_CONTENT = "FINISH_REASON_IMAGE_PROHIBITED_CONTENT"
    FINISH_REASON_NO_IMAGE = "FINISH_REASON_NO_IMAGE"
    FINISH_REASON_SPII = "FINISH_REASON_SPII"
    FINISH_REASON_MALFORMED_FUNCTION_CALL = "FINISH_REASON_MALFORMED_FUNCTION_CALL"
    FINISH_REASON_OTHER = "FINISH_REASON_OTHER"


class GenerationStatus(str, Enum):
    """生成状态"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VideoInput:
    """视频输入配置"""
    type: Literal["multimodal", "text_only"] = "multimodal"
    text: Optional[str] = None
    images: List[Dict[str, Any]] = field(default_factory=list)
    video: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None


@dataclass
class GenerationConfig:
    """生成配置"""
    duration_seconds: int = 5
    resolution: str = "1080p"
    aspect_ratio: str = "16:9"
    fps: int = 24
    style: str = "cinematic"
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40
    seed: Optional[int] = None
    num_videos: int = 1


@dataclass
class OutputConfig:
    """输出配置"""
    format: str = "mp4"
    codec: str = "h264"
    quality: str = "high"
    include_audio: bool = True


@dataclass
class SafetySetting:
    """安全设置"""
    category: HarmCategory
    threshold: HarmBlockThreshold
    method: HarmBlockMethod = HarmBlockMethod.PROBABILITY


@dataclass
class VideoMetadata:
    """元数据"""
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class VideoGenerationRequest:
    """视频生成请求"""
    model: str
    prompt: str
    input: Optional[VideoInput] = None
    generation_config: Optional[GenerationConfig] = None
    output_config: Optional[OutputConfig] = None
    safety_settings: List[SafetySetting] = field(default_factory=list)
    system_instruction: Optional[str] = None
    metadata: Optional[VideoMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "model": self.model,
            "prompt": self.prompt
        }
        
        if self.input:
            result["input"] = {
                "type": self.input.type,
                "text": self.input.text
            }
            if self.input.images:
                result["input"]["images"] = self.input.images
            if self.input.video:
                result["input"]["video"] = self.input.video
            if self.input.audio:
                result["input"]["audio"] = self.input.audio
        
        if self.generation_config:
            result["generation_config"] = {
                "duration_seconds": self.generation_config.duration_seconds,
                "resolution": self.generation_config.resolution,
                "aspect_ratio": self.generation_config.aspect_ratio,
                "fps": self.generation_config.fps,
                "style": self.generation_config.style,
                "temperature": self.generation_config.temperature,
                "top_p": self.generation_config.top_p,
                "top_k": self.generation_config.top_k,
                "seed": self.generation_config.seed,
                "num_videos": self.generation_config.num_videos
            }
        
        if self.output_config:
            result["output_config"] = {
                "format": self.output_config.format,
                "codec": self.output_config.codec,
                "quality": self.output_config.quality,
                "include_audio": self.output_config.include_audio
            }
        
        if self.safety_settings:
            result["safety_settings"] = [
                {
                    "category": s.category.value,
                    "threshold": s.threshold.value,
                    "method": s.method.value
                }
                for s in self.safety_settings
            ]
        
        if self.system_instruction:
            result["system_instruction"] = self.system_instruction
        
        if self.metadata:
            result["metadata"] = {
                "user_id": self.metadata.user_id,
                "project_id": self.metadata.project_id,
                "labels": self.metadata.labels
            }
        
        return result


@dataclass
class VideoResult:
    """视频结果"""
    id: str
    url: str
    duration_seconds: float
    resolution: str
    fps: int
    size_bytes: int
    format: str
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyRating:
    """安全评级"""
    category: HarmCategory
    probability: str
    blocked: bool


@dataclass
class GenerationResult:
    """生成结果"""
    videos: List[VideoResult]
    finish_reason: FinishReason
    safety_ratings: List[SafetyRating] = field(default_factory=list)


@dataclass
class UsageMetadata:
    """使用元数据"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    video_seconds: float = 0.0


@dataclass
class VideoGenerationResponse:
    """视频生成响应"""
    id: str
    object: str = "video.generation"
    created: Optional[int] = None
    completed: Optional[int] = None
    model: str = ""
    status: GenerationStatus = GenerationStatus.PROCESSING
    prompt: str = ""
    generation_config: Optional[GenerationConfig] = None
    result: Optional[GenerationResult] = None
    usage: Optional[UsageMetadata] = None
    error: Optional[str] = None
    estimated_completion_time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created is None:
            self.created = int(datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "status": self.status.value,
            "prompt": self.prompt
        }
        
        if self.completed:
            result["completed"] = self.completed
        
        if self.generation_config:
            result["generation_config"] = {
                "duration_seconds": self.generation_config.duration_seconds,
                "resolution": self.generation_config.resolution,
                "aspect_ratio": self.generation_config.aspect_ratio,
                "fps": self.generation_config.fps
            }
        
        if self.result:
            result["result"] = {
                "videos": [
                    {
                        "id": v.id,
                        "url": v.url,
                        "duration_seconds": v.duration_seconds,
                        "resolution": v.resolution,
                        "fps": v.fps,
                        "size_bytes": v.size_bytes,
                        "format": v.format,
                        "thumbnail_url": v.thumbnail_url,
                        "metadata": v.metadata
                    }
                    for v in self.result.videos
                ],
                "finish_reason": self.result.finish_reason.value
            }
            
            if self.result.safety_ratings:
                result["result"]["safety_ratings"] = [
                    {
                        "category": r.category.value,
                        "probability": r.probability,
                        "blocked": r.blocked
                    }
                    for r in self.result.safety_ratings
                ]
        
        if self.usage:
            result["usage"] = {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
                "video_seconds": self.usage.video_seconds
            }
        
        if self.error:
            result["error"] = self.error
        
        if self.estimated_completion_time:
            result["estimated_completion_time"] = self.estimated_completion_time
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


@dataclass
class ErrorResponse:
    """错误响应"""
    error: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.error