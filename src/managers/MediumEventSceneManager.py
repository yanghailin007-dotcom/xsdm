"""MediumEvent 场景管理器 - 处理跨章场景共享机制

解决同一个 medium_event 跨越多章时，各章独立生成场景导致重复的问题。

核心策略：
- 跨度=1章：单章生成
- 跨度=2-3章：一次性生成全部场景，然后分配到各章
- 跨度>3章：逐章生成，但继承同一 medium_event 内的场景

重要：缓存目录按项目隔离，避免不同项目的场景文件相互干扰。
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.utils.logger import get_logger


class MediumEventSceneManager:
    """medium_event 场景管理器 - 处理跨章场景共享"""

    def __init__(self, project_path: Path = None, novel_title: str = None):
        """初始化管理器

        Args:
            project_path: 项目路径，用于确定缓存目录
            novel_title: 小说标题，用于创建项目专属的缓存目录
        """
        self.logger = get_logger("MediumEventSceneManager")

        # 确定项目路径
        self.project_path = project_path or Path.cwd()

        # 🔥 按项目隔离缓存目录，避免不同项目混用
        self.cache_dir = self._get_isolated_cache_dir(self.project_path, novel_title)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self.cache: Dict[str, Dict] = {}

        self.logger.info(f"MediumEventSceneManager 初始化完成，缓存目录: {self.cache_dir}")

    def _get_isolated_cache_dir(self, project_path: Path, novel_title: str = None) -> Path:
        """
        获取项目隔离的缓存目录

        策略：
        1. 如果提供了 novel_title，在小说项目目录下创建缓存
        2. 否则，在 project_path/data/medium_event_scenes 下创建
        3. 确保 path 不包含多个项目（防止缓存共享）

        Args:
            project_path: 项目路径
            novel_title: 小说标题（可选）

        Returns:
            缓存目录路径
        """
        import re

        # 检查 project_path 是否指向根目录（包含多个项目）
        novel_projects_dir = project_path / "小说项目"
        if novel_projects_dir.exists():
            # project_path 是根目录，需要进一步定位
            # 使用 novel_title 查找具体项目
            if novel_title:
                for project_dir in novel_projects_dir.iterdir():
                    if project_dir.is_dir() and novel_title in project_dir.name:
                        return project_dir / "data" / "medium_event_scenes"
            # 无法确定具体项目，使用 novel_title 创建子目录
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title or "unknown")
            return project_path / "data" / "medium_event_scenes" / safe_title

        # 检查 project_path 本身是否就是小说项目目录
        # 父目录应该是 "小说项目"
        if "小说项目" in str(project_path.parent):
            # 直接在项目目录下创建缓存
            return project_path / "data" / "medium_event_scenes"

        # 如果 project_path 是小说项目下的子目录
        # 向上查找直到找到小说项目目录
        current = project_path
        for _ in range(3):  # 最多向上查找3层
            parent = current.parent
            if "小说项目" in str(parent):
                return current / "data" / "medium_event_scenes"
            current = parent

        # 默认：在传入路径下创建缓存
        if novel_title:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            return project_path / "data" / "medium_event_scenes" / safe_title
        else:
            return project_path / "data" / "medium_event_scenes"

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

    def mark_event_integrated(self, event_id: str) -> bool:
        """标记事件已整合到写作计划

        当场景被整合到 chapter_scene_events 后调用此方法，
        添加元数据标记，便于后续清理。

        Args:
            event_id: 事件ID

        Returns:
            是否成功标记
        """
        if event_id not in self.cache:
            if not self._load_from_disk(event_id):
                self.logger.warning(f"事件 {event_id} 不在缓存中，无法标记")
                return False

        # 更新元数据
        self.cache[event_id]['integrated_to_plan'] = True
        self.cache[event_id]['integrated_at'] = datetime.now().isoformat()

        # 持久化到磁盘
        self._save_to_disk(event_id, self.cache[event_id])

        self.logger.info(f"已标记事件已整合: {event_id}")
        return True

    def clear_event_after_integration(self, event_id: str) -> bool:
        """清理已整合到写作计划的事件缓存

        当场景已经保存到 chapter_scene_events 后，
        可以安全删除缓存文件以节省空间。

        Args:
            event_id: 事件ID

        Returns:
            是否成功清理
        """
        if event_id not in self.cache:
            self._load_from_disk(event_id)

        # 检查是否已整合
        if not self.cache.get(event_id, {}).get('integrated_to_plan', False):
            self.logger.warning(f"事件 {event_id} 尚未整合，跳过清理")
            return False

        # 清除内存缓存
        self.cache.pop(event_id, None)

        # 删除磁盘文件
        cache_file = self.get_cache_file_path(event_id)
        if cache_file.exists():
            cache_file.unlink()
            self.logger.info(f"已清理已整合的事件缓存: {event_id}")
            return True

        return False

    def clear_all_integrated_events(self) -> int:
        """清理所有已整合到写作计划的事件缓存

        Returns:
            清理的事件数量
        """
        # 获取所有缓存文件
        cached_files = list(self.cache_dir.glob("*.json"))
        cleared_count = 0

        for cache_file in cached_files:
            event_id = cache_file.stem

            # 加载检查
            if self._load_from_disk(event_id):
                if self.cache[event_id].get('integrated_to_plan', False):
                    if self.clear_event_after_integration(event_id):
                        cleared_count += 1

        self.logger.info(f"批量清理完成: 清理了 {cleared_count} 个已整合的事件缓存")
        return cleared_count

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息

        Returns:
            包含缓存统计的字典
        """
        cached_files = list(self.cache_dir.glob("*.json"))

        total_size = sum(f.stat().st_size for f in cached_files)
        integrated_count = 0
        pending_count = 0

        for cache_file in cached_files:
            event_id = cache_file.stem
            if self._load_from_disk(event_id):
                if self.cache[event_id].get('integrated_to_plan', False):
                    integrated_count += 1
                else:
                    pending_count += 1

        return {
            "total_events": len(cached_files),
            "integrated_events": integrated_count,
            "pending_events": pending_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }

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
