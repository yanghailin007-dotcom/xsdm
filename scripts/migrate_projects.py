#!/usr/bin/env python3
"""
小说项目迁移脚本
将旧数据迁移到公共目录，实现用户隔离前的数据整理
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.utils.path_utils import (
    NOVEL_PROJECTS_ROOT,
    PUBLIC_PROJECTS_DIR,
    _is_project_dir,
    get_public_projects_dir
)


def migrate_legacy_projects(dry_run: bool = False) -> dict:
    """
    迁移旧数据到公共目录
    
    Args:
        dry_run: 试运行模式，只输出不执行
    
    Returns:
        迁移统计信息
    """
    stats = {
        'moved': 0,
        'skipped': 0,
        'errors': [],
        'total': 0
    }
    
    if not NOVEL_PROJECTS_ROOT.exists():
        print("小说项目根目录不存在，无需迁移")
        return stats
    
    # 确保公共目录存在
    public_dir = get_public_projects_dir(create=True)
    
    # 需要跳过的目录
    skip_dirs = {'_public', '_backup', 'admin', 'test', 'yang', 'yang123', 'yang1234', 
                 'yang12345', 'yang123456', 'yang1234567', 'debug123', 'debug123456'}
    
    print(f"扫描目录: {NOVEL_PROJECTS_ROOT}")
    print(f"公共目录: {public_dir}")
    print(f"{'='*60}")
    
    for item in NOVEL_PROJECTS_ROOT.iterdir():
        if not item.is_dir():
            continue
            
        # 跳过特殊目录和已有用户目录
        if item.name.startswith('_') or item.name in skip_dirs:
            print(f"跳过: {item.name}")
            continue
        
        stats['total'] += 1
        
        try:
            # 检查是否是项目目录
            if not _is_project_dir(item):
                print(f"非项目目录，跳过: {item.name}")
                stats['skipped'] += 1
                continue
            
            target = public_dir / item.name
            
            if target.exists():
                print(f"已存在，跳过: {item.name}")
                stats['skipped'] += 1
            else:
                if dry_run:
                    print(f"[试运行] 将移动: {item.name} -> {target}")
                    stats['moved'] += 1
                else:
                    # 执行移动
                    shutil.move(str(item), str(target))
                    print(f"已移动: {item.name} -> {target}")
                    stats['moved'] += 1
                    
        except Exception as e:
            error_msg = f"{item.name}: {str(e)}"
            print(f"错误: {error_msg}")
            stats['errors'].append(error_msg)
    
    return stats


def create_user_dirs(usernames: list):
    """为指定用户创建项目目录"""
    from web.utils.path_utils import get_user_novel_dir
    
    print(f"\n创建用户目录...")
    for username in usernames:
        user_dir = get_user_novel_dir(username, create=True)
        print(f"  创建: {user_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='小说项目迁移工具')
    parser.add_argument('--dry-run', action='store_true', 
                        help='试运行模式，只输出不执行')
    parser.add_argument('--create-users', nargs='+',
                        help='创建指定用户的项目目录')
    
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print("小说项目迁移脚本")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("模式: 试运行 (不执行实际移动)")
    print(f"{'='*60}\n")
    
    # 执行迁移
    stats = migrate_legacy_projects(dry_run=args.dry_run)
    
    # 创建用户目录
    if args.create_users:
        create_user_dirs(args.create_users)
    
    # 输出统计
    print(f"\n{'='*60}")
    print("迁移统计:")
    print(f"  扫描总数: {stats['total']}")
    print(f"  成功移动: {stats['moved']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {len(stats['errors'])}")
    
    if stats['errors']:
        print(f"\n错误详情:")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print(f"{'='*60}")
    
    return 0 if len(stats['errors']) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
