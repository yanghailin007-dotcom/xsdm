"""
视频生成任务数据模型

包含：
- VideoProject: 视频项目
- VideoTask: 视频生成任务
- Shot: 单个镜头
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json


class ProjectStatus(str, Enum):
    """项目状态"""
    CREATED = "created"
    GENERATING = "generating"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShotStatus(str, Enum):
    """镜头状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Shot:
    """单个镜头"""
    shot_index: int
    shot_type: str
    camera_movement: str
    duration_seconds: float
    description: str
    generation_prompt: str
    audio_prompt: Optional[str] = None
    status: ShotStatus = ShotStatus.PENDING
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "shot_index": self.shot_index,
            "shot_type": self.shot_type,
            "camera_movement": self.camera_movement,
            "duration_seconds": self.duration_seconds,
            "description": self.description,
            "generation_prompt": self.generation_prompt,
            "audio_prompt": self.audio_prompt,
            "status": self.status.value,
            "video_path": self.video_path,
            "thumbnail_path": self.thumbnail_path,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Shot':
        """从字典创建"""
        return cls(
            shot_index=data["shot_index"],
            shot_type=data["shot_type"],
            camera_movement=data["camera_movement"],
            duration_seconds=data["duration_seconds"],
            description=data["description"],
            generation_prompt=data["generation_prompt"],
            audio_prompt=data.get("audio_prompt"),
            status=ShotStatus(data.get("status", "pending")),
            video_path=data.get("video_path"),
            thumbnail_path=data.get("thumbnail_path"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            retry_count=data.get("retry_count", 0),
            error_message=data.get("error_message")
        )


@dataclass
class VideoTask:
    """视频生成任务"""
    task_id: str
    project_id: str
    shots: List[Shot]
    status: TaskStatus = TaskStatus.PENDING
    total_shots: int = 0
    completed_shots: int = 0
    failed_shots: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.total_shots == 0:
            self.total_shots = len(self.shots)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "shots": [shot.to_dict() for shot in self.shots],
            "status": self.status.value,
            "total_shots": self.total_shots,
            "completed_shots": self.completed_shots,
            "failed_shots": self.failed_shots,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VideoTask':
        """从字典创建"""
        return cls(
            task_id=data["task_id"],
            project_id=data["project_id"],
            shots=[Shot.from_dict(s) for s in data.get("shots", [])],
            status=TaskStatus(data.get("status", "pending")),
            total_shots=data.get("total_shots", 0),
            completed_shots=data.get("completed_shots", 0),
            failed_shots=data.get("failed_shots", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            config=data.get("config", {})
        )
    
    def get_progress(self) -> float:
        """获取任务进度（0-1）"""
        if self.total_shots == 0:
            return 0.0
        return self.completed_shots / self.total_shots
    
    def get_pending_shots(self) -> List[Shot]:
        """获取待处理的镜头"""
        return [s for s in self.shots if s.status == ShotStatus.PENDING]
    
    def get_failed_shots(self) -> List[Shot]:
        """获取失败的镜头"""
        return [s for s in self.shots if s.status == ShotStatus.FAILED]


@dataclass
class VideoProject:
    """视频项目"""
    project_id: str
    user_id: str
    project_name: str
    video_type: str
    status: ProjectStatus = ProjectStatus.CREATED
    total_shots: int = 0
    storyboard: Optional[Dict] = None
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    current_task_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "video_type": self.video_type,
            "status": self.status.value,
            "total_shots": self.total_shots,
            "storyboard": self.storyboard,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_task_id": self.current_task_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VideoProject':
        """从字典创建"""
        return cls(
            project_id=data["project_id"],
            user_id=data["user_id"],
            project_name=data["project_name"],
            video_type=data["video_type"],
            status=ProjectStatus(data.get("status", "created")),
            total_shots=data.get("total_shots", 0),
            storyboard=data.get("storyboard"),
            config=data.get("config", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            current_task_id=data.get("current_task_id")
        )