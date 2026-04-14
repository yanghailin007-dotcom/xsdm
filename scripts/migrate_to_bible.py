# -*- coding: utf-8 -*-
"""
Migration Script: 批量为现有项目生成核心设定圣经

用法：
    python scripts/migrate_to_bible.py [--review] [--novel-dir 小说项目]

说明：
    - 扫描指定目录下所有小说项目
    - 为每个项目生成 layer_1_4_core_settings.md
    - 如果加了 --review，会调用 BibleReviewer 进行 AI 审稿（需要 API key）
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from web.services.market_driven.bible_generator import CoreSettingBibleGenerator


def find_projects(base_dir: Path):
    """递归查找所有包含 project_info.json 的小说项目目录"""
    projects = []
    for user_dir in base_dir.iterdir():
        if not user_dir.is_dir():
            continue
        for novel_dir in user_dir.iterdir():
            if not novel_dir.is_dir():
                continue
            if (novel_dir / "project_info.json").exists():
                projects.append(novel_dir)
    return projects


def main():
    parser = argparse.ArgumentParser(description="批量迁移现有项目到核心设定圣经")
    parser.add_argument(
        "--novel-dir",
        type=str,
        default=str(BASE_DIR / "小说项目"),
        help="小说项目根目录",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="是否同时运行 AI 审稿（需要 APIClient 配置）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的 layer_1_4_core_settings.md",
    )
    args = parser.parse_args()

    base_dir = Path(args.novel_dir)
    if not base_dir.exists():
        print(f"❌ 目录不存在: {base_dir}")
        sys.exit(1)

    projects = find_projects(base_dir)
    print(f"🔍 找到 {len(projects)} 个项目")

    api_client = None
    if args.review:
        try:
            from src.core.APIClient import APIClient
            from config.config import CONFIG

            api_client = APIClient(CONFIG)
            print("✅ APIClient 初始化成功，将运行 AI 审稿")
        except Exception as e:
            print(f"⚠️ APIClient 初始化失败: {e}，跳过 AI 审稿")

    success_count = 0
    skip_count = 0
    error_count = 0
    block_count = 0

    for project_path in projects:
        print(f"\n📚 处理项目: {project_path.name}")
        bible_path = project_path / "layer_1_4_core_settings.md"

        try:
            # 生成圣经
            gen = CoreSettingBibleGenerator(str(project_path))
            generated_path = gen.generate(force=args.force)
            print(f"  ✅ 已生成: {generated_path.name}")

            # 可选：AI 审稿
            if api_client:
                from web.services.market_driven.bible_reviewer import (
                    BibleReviewer,
                    BibleReviewBlockedError,
                )

                reviewer = BibleReviewer(
                    api_client=api_client,
                    project_path=str(project_path),
                )
                try:
                    report = reviewer.review()
                    print(
                        f"  ✅ 审稿通过 | 预估完读率: {report.get('estimated_read_rate', 'N/A')}"
                    )
                except BibleReviewBlockedError as e:
                    print(f"  🚫 审稿被 BLOCK: {e}")
                    block_count += 1

            success_count += 1
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            error_count += 1

    print("\n" + "=" * 50)
    print(f"📊 迁移结果: 成功 {success_count} | 失败 {error_count} | BLOCK {block_count}")
    print(f"📁 小说项目根目录: {base_dir}")


if __name__ == "__main__":
    main()
