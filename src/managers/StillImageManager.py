"""
剧照图片素材库管理器

管理生成的剧照图片，提供本地存储和检索功能
"""

import os
import json
import uuid
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

from src.models.still_image_models import StillImage, StillImageType, StillImageStatus
from src.utils.logger import get_logger

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent.parent

# 本地图片存储目录
STILL_IMAGE_STORAGE_DIR = BASE_DIR / "generated_images"
STILL_IMAGE_METADATA_DIR = BASE_DIR / "still_image_metadata"

logger = get_logger(__name__)


class StillImageManager:
    """剧照图片素材库管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None, metadata_dir: Optional[str] = None):
        """
        初始化剧照图片素材库管理器
        
        Args:
            storage_dir: 图片存储目录
            metadata_dir: 元数据存储目录
        """
        self.logger = logger
        self.storage_dir = Path(storage_dir or STILL_IMAGE_STORAGE_DIR)
        self.metadata_dir = Path(metadata_dir or STILL_IMAGE_METADATA_DIR)
        
        # 确保目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 图片存储
        self.images: Dict[str, StillImage] = {}
        self._images_lock = threading.Lock()
        
        # 加载已保存的图片元数据
        self._load_images()
        
        self.logger.info(f"✅ 剧照图片素材库管理器初始化完成")
        self.logger.info(f"📁 存储目录: {self.storage_dir}")
        self.logger.info(f"📋 元数据目录: {self.metadata_dir}")
        self.logger.info(f"📊 已加载图片数: {len(self.images)}")
    
    def _load_images(self):
        """从磁盘加载图片元数据"""
        try:
            # 清空现有图片列表
            self.images.clear()
            
            loaded_count = 0
            for metadata_file in self.metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        image_data = json.load(f)
                    
                    # 从元数据创建图片对象
                    image = StillImage.from_dict(image_data)
                    self.images[image.image_id] = image
                    loaded_count += 1
                    
                    self.logger.debug(f"✅ 加载图片元数据: {image.image_id} (状态: {image.status})")
                
                except Exception as e:
                    self.logger.warning(f"加载图片元数据失败 {metadata_file}: {e}")
            
            self.logger.info(f"✅ 从磁盘加载了 {loaded_count} 个图片元数据")
            
            # 扫描 generated_images 目录，为没有元数据的图片创建元数据
            self._scan_and_create_metadata()
        
        except Exception as e:
            self.logger.error(f"❌ 加载图片元数据失败: {e}")
    
    def _scan_and_create_metadata(self):
        """扫描 generated_images 目录并为没有元数据的图片创建元数据"""
        try:
            if not self.storage_dir.exists():
                self.logger.warning(f"⚠️ 图片存储目录不存在: {self.storage_dir}")
                return
            
            # 获取所有图片文件
            image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
            image_files = [
                f for f in self.storage_dir.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            # 获取已有元数据的图片路径
            metadata_paths = {
                img.local_path for img in self.images.values() if img.local_path
            }
            
            created_count = 0
            for image_file in image_files:
                # 跳过已有元数据的图片
                if str(image_file) in metadata_paths:
                    continue
                
                try:
                    # 从文件名提取信息
                    filename = image_file.stem  # 不包含扩展名的文件名
                    
                    # 解析文件名（格式：用户名_时间戳_提示词.png 或 小说名_角色名_类型_时间戳.png）
                    prompt = filename
                    
                    # 尝试从文件名提取更详细的信息
                    if '_' in filename:
                        parts = filename.split('_')
                        if len(parts) >= 2:
                            # 最后部分通常是时间戳
                            try:
                                # 提取提示词部分（移除时间戳）
                                prompt_parts = parts[:-1] if len(parts) > 2 else parts
                                prompt = '_'.join(prompt_parts)
                            except:
                                prompt = filename
                    
                    # 获取文件大小
                    file_size = image_file.stat().st_size if image_file.exists() else 0
                    
                    # 生成图片 URL（使用 /generated_images/ 路径）
                    relative_path = image_file.relative_to(self.storage_dir)
                    image_url = f"/generated_images/{relative_path}"
                    
                    # 创建并添加图片
                    image = self.add_image(
                        image_type=StillImageType.CUSTOM,
                        prompt=prompt,
                        local_path=str(image_file),
                        image_url=image_url,
                        aspect_ratio="9:16",  # 默认值
                        image_size="4K",      # 默认值
                        file_size=file_size,
                        metadata={"auto_imported": True, "imported_at": datetime.now().isoformat()}
                    )
                    
                    created_count += 1
                    self.logger.info(f"✅ 自动导入图片: {image_file.name} -> {image.image_id}")
                
                except Exception as e:
                    self.logger.warning(f"导入图片失败 {image_file.name}: {e}")
            
            if created_count > 0:
                self.logger.info(f"✅ 自动导入了 {created_count} 个现有图片")
        
        except Exception as e:
            self.logger.error(f"❌ 扫描和创建元数据失败: {e}")
    
    def _save_image_metadata(self, image: StillImage):
        """保存图片元数据到磁盘"""
        try:
            metadata_file = self.metadata_dir / f"{image.image_id}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(image.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存图片元数据失败: {e}")
    
    def add_image(
        self,
        image_type: StillImageType,
        prompt: str,
        local_path: str,
        image_url: str,
        novel_title: Optional[str] = None,
        character_name: Optional[str] = None,
        event_name: Optional[str] = None,
        aspect_ratio: str = "9:16",
        image_size: str = "4K",
        used_reference_images: int = 0,
        file_size: int = 0,
        metadata: Optional[Dict] = None
    ) -> StillImage:
        """
        添加新图片到素材库
        
        Args:
            image_type: 图片类型
            prompt: 生成提示词
            local_path: 本地文件路径
            image_url: HTTP访问URL
            novel_title: 所属小说
            character_name: 角色名称
            event_name: 事件名称
            aspect_ratio: 图片比例
            image_size: 图片质量
            used_reference_images: 使用的参考图数量
            file_size: 文件大小
            metadata: 其他元数据
        
        Returns:
            StillImage对象
        """
        # 生成唯一ID
        image_id = f"still_{uuid.uuid4().hex[:12]}"
        
        # 创建图片对象
        image = StillImage(
            image_id=image_id,
            image_type=image_type,
            prompt=prompt,
            status=StillImageStatus.COMPLETED,
            novel_title=novel_title,
            character_name=character_name,
            event_name=event_name,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            used_reference_images=used_reference_images,
            local_path=local_path,
            image_url=image_url,
            file_size=file_size,
            metadata=metadata or {}
        )
        
        # 保存到内存
        with self._images_lock:
            self.images[image_id] = image
        
        # 保存元数据到磁盘
        self._save_image_metadata(image)
        
        self.logger.info(f"✅ 添加图片到素材库: {image_id}")
        return image
    
    def get_image(self, image_id: str) -> Optional[StillImage]:
        """
        获取指定图片
        
        Args:
            image_id: 图片ID
        
        Returns:
            StillImage对象，不存在则返回None
        """
        with self._images_lock:
            return self.images.get(image_id)
    
    def list_images(
        self,
        limit: int = 50,
        image_type: Optional[StillImageType] = None,
        novel_title: Optional[str] = None,
        status: Optional[StillImageStatus] = None,
        order: str = "desc"
    ) -> List[StillImage]:
        """
        列出图片
        
        Args:
            limit: 返回数量限制
            image_type: 图片类型过滤
            novel_title: 小说标题过滤
            status: 状态过滤
            order: 排序方式（desc/asc）
        
        Returns:
            图片列表
        """
        with self._images_lock:
            images = list(self.images.values())
        
        # 过滤
        if image_type:
            images = [img for img in images if img.image_type == image_type]
        
        if novel_title:
            images = [img for img in images if img.novel_title == novel_title]
        
        if status:
            images = [img for img in images if img.status == status]
        
        # 排序
        reverse = order == "desc"
        images = sorted(
            images,
            key=lambda img: img.created_at,
            reverse=reverse
        )
        
        # 限制数量
        images = images[:limit]
        
        return images
    
    def delete_image(self, image_id: str) -> bool:
        """
        删除图片（包括元数据和本地文件）
        
        Args:
            image_id: 图片ID
        
        Returns:
            是否成功
        """
        self.logger.info(f"🗑️ 请求删除图片: {image_id}")
        
        with self._images_lock:
            image = self.images.pop(image_id, None)
        
        if not image:
            self.logger.warning(f"⚠️ 图片不存在: {image_id}")
            return False
        
        # 删除元数据文件
        metadata_file = self.metadata_dir / f"{image_id}.json"
        if metadata_file.exists():
            try:
                metadata_file.unlink()
                self.logger.info(f"✅ 已删除元数据文件: {metadata_file}")
            except Exception as e:
                self.logger.error(f"❌ 删除元数据文件失败: {e}")
        
        # 删除本地图片文件（可选，这里只删除元数据）
        # 如果需要删除实际文件，可以取消下面的注释
        # if image.local_path:
        #     local_file = Path(image.local_path)
        #     if local_file.exists():
        #         try:
        #             local_file.unlink()
        #             self.logger.info(f"✅ 已删除本地文件: {local_file}")
        #         except Exception as e:
        #             self.logger.error(f"❌ 删除本地文件失败: {e}")
        
        self.logger.info(f"✅ 图片删除成功: {image_id}")
        return True
    
    def get_statistics(self) -> Dict:
        """
        获取素材库统计信息
        
        Returns:
            统计信息字典
        """
        with self._images_lock:
            images = list(self.images.values())
        
        total_count = len(images)
        
        # 按类型统计
        type_counts = {}
        for img in images:
            type_name = img.image_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # 按状态统计
        status_counts = {}
        for img in images:
            status_name = img.status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        # 按小说统计
        novel_counts = {}
        for img in images:
            if img.novel_title:
                novel_counts[img.novel_title] = novel_counts.get(img.novel_title, 0) + 1
        
        # 计算总文件大小
        total_size = sum(img.file_size for img in images if img.file_size > 0)
        
        return {
            "total_count": total_count,
            "type_counts": type_counts,
            "status_counts": status_counts,
            "novel_counts": novel_counts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def export_metadata(self, output_file: str) -> bool:
        """
        导出所有图片元数据到JSON文件
        
        Args:
            output_file: 输出文件路径
        
        Returns:
            是否成功
        """
        try:
            with self._images_lock:
                images_data = [img.to_dict() for img in self.images.values()]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_time": datetime.now().isoformat(),
                    "total_count": len(images_data),
                    "images": images_data
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 元数据导出成功: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"❌ 导出元数据失败: {e}")
            return False


# 全局单例
_manager_instance: Optional[StillImageManager] = None
_manager_lock = threading.Lock()


def get_still_image_manager() -> StillImageManager:
    """获取剧照图片素材库管理器单例"""
    global _manager_instance
    
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = StillImageManager()
    
    return _manager_instance
