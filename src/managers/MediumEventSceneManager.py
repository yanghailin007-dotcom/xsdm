"""MediumEvent 场景管理器 - 处理跨章场景共享机制

解决同一个 medium_event 跨越多章时，各章独立生成场景导致重复的问题。

核心策略：
- 跨度=1章：单章生成
- 跨度=2-3章：一次性生成全部场景，然后分配到各章
- 跨度>3章：逐章生成，但继承同一 medium_event 内的场景
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.utils.logger import get_logger


class MediumEventSceneManager:
    """medium_event 场景管理器 - 处理跨章场景共享"""

    def __init__(self, project_path: Path = None):
        """初始化管理器

        Args:
            project_path: 项目路径，用于确定缓存目录
        """
        self.logger = get_logger("MediumEventSceneManager")
        self.project_path = project_path or Path.cwd()

        # 缓存目录：{project}/data/medium_event_scenes/
        self.cache_dir = self.project_path / "data" / "medium_event_scenes"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self.cache: Dict[str, Dict] = {}

        self.logger.info(f"MediumEventSceneManager 初始化完成，缓存目录: {self.cache_dir}")

    def get_event_id(self, medium_event: Dict, stage_name: str) -> str:
        """生成 medium_event 的唯一标识

        Args:
            medium_event: 中型事件数据
            stage_name: 阶段名称

        Returns:
            唯一标识符
        """
        event_name = medium_event.get('name', 'unknown')
        # 使用 hash 确保事件名中的特殊字符不会导致文件路径问题
        name_hash = hashlib.md5(f"{stage_name}_{event_name}".encode()).hexdigest()[:8]
        return f"{stage_name}_{event_name}_{name_hash}"

    def get_cache_file_path(self, event_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{event_id}.json"

    def is_event_completed(self, event_id: str) -> bool:
        """检查事件是否已完全生成

        Args:
            event_id: 事件ID

        Returns:
            是否已完成
        """
        if event_id in self.cache:
            return self.cache.get(event_id, {}).get('status') == 'completed'

        # 尝试从磁盘加载
        self._load_from_disk(event_id)
        return self.cache.get(event_id, {}).get('status') == 'completed'

    def get_cached_scenes(self, event_id: str, chapter_number: int) -> Optional[Dict]:
        """获取已缓存的场景数据（用于场景继承）

        Args:
            event_id: 事件ID
            chapter_number: 当前章节号

        Returns:
            包含之前章节场景信息的字典，格式：
            {
                "previous_chapters": [3],  # 已生成场景的章节号列表
                "all_previous_scenes": [...],  # 所有之前章节的场景
                "scenes_by_chapter": {"3": [...], "4": [...]},
                "event_summary": "事件摘要"
            }
        """
        if event_id not in self.cache:
            if not self._load_from_disk(event_id):
                return None

        event_data = self.cache[event_id]
        scenes_by_chapter = event_data.get('scenes', {})

        # 收集之前章节的场景
        all_previous_scenes = []
        previous_chapters = []
        for ch_str, scenes in scenes_by_chapter.items():
            ch_num = int(ch_str)
            if ch_num < chapter_number and scenes:
                previous_chapters.append(ch_num)
                all_previous_scenes.extend(scenes)

        if not all_previous_scenes:
            return None

        return {
            "previous_chapters": sorted(previous_chapters),
            "all_previous_scenes": all_previous_scenes,
            "scenes_by_chapter": scenes_by_chapter,
            "event_summary": event_data.get('global_scene_summary', ''),
            "event_name": event_data.get('event_name', ''),
            "chapter_range": event_data.get('chapter_range', ''),
        }

    def get_scenes_for_chapter(self, event_id: str, chapter_number: int) -> Optional[List[Dict]]:
        """获取指定章节的场景（用于一次性生成后返回特定章节）

        Args:
            event_id: 事件ID
            chapter_number: 章节号

        Returns:
            该章节的场景列表
        """
        if event_id not in self.cache:
            if not self._load_from_disk(event_id):
                return None

        return self.cache.get(event_id, {}).get('scenes', {}).get(str(chapter_number), [])

    def save_event_scenes(self, event_id: str, event_data: Dict):
        """保存 medium_event 的所有场景

        Args:
            event_id: 事件ID
            event_data: 事件数据，格式：
                {
                    "medium_event_id": str,
                    "event_name": str,
                    "chapter_range": str,
                    "total_chapters": int,
                    "status": "completed",
                    "scenes": {
                        "3": [scene1, scene2, ...],
                        "4": [scene3, scene4, ...]
                    },
                    "global_scene_summary": str
                }
        """
        # 更新内存缓存
        self.cache[event_id] = event_data

        # 保存到磁盘
        self._save_to_disk(event_id, event_data)

        self.logger.info(f"已保存 medium_event 场景缓存: {event_id}")

    def _load_from_disk(self, event_id: str) -> bool:
        """从磁盘加载事件数据

        Args:
            event_id: 事件ID

        Returns:
            是否加载成功
        """
        cache_file = self.get_cache_file_path(event_id)

        if not cache_file.exists():
            return False

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            self.cache[event_id] = event_data
            self.logger.debug(f"从磁盘加载事件缓存: {event_id}")
            return True
        except Exception as e:
            self.logger.error(f"加载事件缓存失败 {event_id}: {e}")
            return False

    def _save_to_disk(self, event_id: str, event_data: Dict):
        """保存事件数据到磁盘

        Args:
            event_id: 事件ID
            event_data: 事件数据
        """
        cache_file = self.get_cache_file_path(event_id)

        try:
            # 添加时间戳
            event_data['saved_at'] = datetime.now().isoformat()

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(event_data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"事件缓存已保存到磁盘: {cache_file}")
        except Exception as e:
            self.logger.error(f"保存事件缓存失败 {event_id}: {e}")

    def clear_cache(self, event_id: str = None):
        """清除缓存

        Args:
            event_id: 指定事件ID，如果为None则清除所有缓存
        """
        if event_id:
            # 清除特定事件
            self.cache.pop(event_id, None)
            cache_file = self.get_cache_file_path(event_id)
            if cache_file.exists():
                cache_file.unlink()
                self.logger.info(f"已清除事件缓存: {event_id}")
        else:
            # 清除所有缓存
            self.cache.clear()
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.logger.info("已清除所有事件缓存")

    def get_all_cached_events(self) -> List[str]:
        """获取所有已缓存的事件ID

        Returns:
            事件ID列表
        """
        # 从内存获取
        cached_ids = list(self.cache.keys())

        # 从磁盘获取
        for cache_file in self.cache_dir.glob("*.json"):
            event_id = cache_file.stem
            if event_id not in cached_ids:
                cached_ids.append(event_id)

        return cached_ids


def parse_chapter_range(chapter_range: str) -> Tuple[int, int]:
    """解析章节范围字符串，返回 (start, end) 元组

    Args:
        chapter_range: 章节范围字符串，如 "1-1", "3-5", "10"

    Returns:
        (起始章节, 结束章节)
    """
    if not chapter_range:
        return 1, 1

    # 提取所有数字
    import re
    numbers = re.findall(r'\d+', chapter_range)

    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        return int(numbers[0]), int(numbers[0])

    return 1, 1
