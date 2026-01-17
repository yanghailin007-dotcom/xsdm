"""
剧照图片数据模型

包含：
- StillImage: 剧照图片
- StillImageStatus: 图片状态
- StillImageType: 图片类型（角色/场景/自定义）
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json


class StillImageStatus(str, Enum):
    """图片状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StillImageType(str, Enum):
    """图片类型"""
    CHARACTER = "character"  # 角色剧照
    SCENE = "scene"  # 场景剧照
    CUSTOM = "custom"  # 自定义剧照


@dataclass
class StillImage:
    """剧照图片"""
    image_id: str
    image_type: StillImageType
    prompt: str
    status: StillImageStatus = StillImageStatus.PENDING
    
    # 关联信息
    novel_title: Optional[str] = None  # 所属小说
    character_name: Optional[str] = None  # 角色名称（CHARACTER类型）
    event_name: Optional[str] = None  # 事件名称（SCENE类型）
    
    # 生成参数
    aspect_ratio: str = "9:16"  # 默认竖屏
    image_size: str = "4K"
    used_reference_images: int = 0  # 使用的参考图数量
    
    # 生成结果
    local_path: Optional[str] = None  # 本地文件路径
    image_url: Optional[str] = None  # HTTP访问URL
    thumbnail_url: Optional[str] = None  # 缩略图URL
    file_size: int = 0  # 文件大小（字节）
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # 其他
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "image_id": self.image_id,
            "image_type": self.image_type.value,
            "prompt": self.prompt,
            "status": self.status.value,
            "novel_title": self.novel_title,
            "character_name": self.character_name,
            "event_name": self.event_name,
            "aspect_ratio": self.aspect_ratio,
            "image_size": self.image_size,
            "used_reference_images": self.used_reference_images,
            "local_path": self.local_path,
            "image_url": self.image_url,
            "thumbnail_url": self.thumbnail_url,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StillImage':
        """从字典创建"""
        return cls(
            image_id=data["image_id"],
            image_type=StillImageType(data["image_type"]),
            prompt=data["prompt"],
            status=StillImageStatus(data.get("status", "pending")),
            novel_title=data.get("novel_title"),
            character_name=data.get("character_name"),
            event_name=data.get("event_name"),
            aspect_ratio=data.get("aspect_ratio", "9:16"),
            image_size=data.get("image_size", "4K"),
            used_reference_images=data.get("used_reference_images", 0),
            local_path=data.get("local_path"),
            image_url=data.get("image_url"),
            thumbnail_url=data.get("thumbnail_url"),
            file_size=data.get("file_size", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )
    
    def complete(self, local_path: str, image_url: str, file_size: int = 0):
        """标记为完成"""
        self.status = StillImageStatus.COMPLETED
        self.local_path = local_path
        self.image_url = image_url
        self.file_size = file_size
        self.completed_at = datetime.now()
    
    def fail(self, error_message: str):
        """标记为失败"""
        self.status = StillImageStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
    
    def cancel(self):
        """取消"""
        self.status = StillImageStatus.CANCELLED
        self.completed_at = datetime.now()
