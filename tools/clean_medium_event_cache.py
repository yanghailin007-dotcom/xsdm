"""
清理中型事件场景缓存

用法：
    python tools/clean_medium_event_cache.py              # 查看缓存状态
    python tools/clean_medium_event_cache.py --clean      # 清理已整合的缓存
    python tools/clean_medium_event_cache.py --all        # 清理所有缓存
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.MediumEventSceneManager import MediumEventSceneManager
from config.config import CONFIG


def main():
    parser = argparse.ArgumentParser(description="清理中型事件场景缓存")
    parser.add_argument("--clean", action="store_true", help="清理已整合的缓存")
    parser.add_argument("--all", action="store_true", help="清理所有缓存")
    args = parser.parse_args()

    # 初始化管理器
    manager = MediumEventSceneManager()

    # 显示缓存状态
    stats = manager.get_cache_stats()
    print("=" * 60)
    print("中型事件场景缓存状态")
    print("=" * 60)
    print(f"缓存目录: {stats['cache_dir']}")
    print(f"总事件数: {stats['total_events']}")
    print(f"  - 已整合到写作计划: {stats['integrated_events']}")
    print(f"  - 尚未整合: {stats['pending_events']}")
    print(f"占用空间: {stats['total_size_mb']} MB")

    if args.all:
        print("\n[清理所有缓存]")
        manager.clear_cache()
        print("✅ 所有缓存已清理")
    elif args.clean:
        print("\n[清理已整合的缓存]")
        count = manager.clear_all_integrated_events()
        print(f"✅ 已清理 {count} 个已整合的事件缓存")
    else:
        print("\n提示: 使用 --clean 清理已整合的缓存，使用 --all 清理所有缓存")


if __name__ == "__main__":
    main()
