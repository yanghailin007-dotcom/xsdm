#!/usr/bin/env python3
"""
清理 debug_responses 目录中的过期日志文件
保留最近 N 天的日志（默认3天）
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_debug_logs(debug_dir: str = None, keep_days: int = 3, dry_run: bool = False):
    """
    清理 debug_responses 目录中的旧日志文件
    
    Args:
        debug_dir: 日志目录路径，默认使用项目根目录下的 debug_responses
        keep_days: 保留最近几天的日志，默认3天
        dry_run: 如果为True，只显示要删除的文件而不实际删除
    
    Returns:
        dict: 清理统计信息
    """
    # 默认路径
    if debug_dir is None:
        # 获取项目根目录（脚本所在目录的上两级）
        script_dir = Path(__file__).parent.absolute()
        project_root = script_dir.parent
        debug_dir = project_root / "debug_responses"
    else:
        debug_dir = Path(debug_dir)
    
    if not debug_dir.exists():
        print(f"[CLEANUP] 日志目录不存在: {debug_dir}")
        return {"deleted": 0, "skipped": 0, "errors": 0, "freed_bytes": 0}
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cutoff_timestamp = cutoff_date.timestamp()
    
    stats = {
        "deleted": 0,
        "skipped": 0,
        "errors": 0,
        "freed_bytes": 0,
        "total_files": 0
    }
    
    print(f"[CLEANUP] 开始清理日志目录: {debug_dir}")
    print(f"[CLEANUP] 保留最近 {keep_days} 天的日志（删除 {cutoff_date.strftime('%Y-%m-%d %H:%M')} 之前的文件）")
    if dry_run:
        print("[CLEANUP] 【试运行模式】不会实际删除文件\n")
    else:
        print("")
    
    # 遍历目录中的所有文件
    for file_path in debug_dir.iterdir():
        if not file_path.is_file():
            continue
        
        stats["total_files"] += 1
        
        try:
            # 获取文件最后修改时间
            file_mtime = file_path.stat().st_mtime
            file_size = file_path.stat().st_size
            
            if file_mtime < cutoff_timestamp:
                # 文件过期，需要删除
                file_date = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M')
                
                if dry_run:
                    print(f"[DRY-RUN] 将删除: {file_path.name} ({file_date}, {file_size/1024:.1f} KB)")
                else:
                    try:
                        file_path.unlink()
                        print(f"[DELETED] {file_path.name} ({file_date}, {file_size/1024:.1f} KB)")
                        stats["deleted"] += 1
                        stats["freed_bytes"] += file_size
                    except Exception as e:
                        print(f"[ERROR] 删除失败 {file_path.name}: {e}")
                        stats["errors"] += 1
            else:
                stats["skipped"] += 1
                
        except Exception as e:
            print(f"[ERROR] 处理文件失败 {file_path.name}: {e}")
            stats["errors"] += 1
    
    # 输出统计信息
    print(f"\n[CLEANUP] 清理完成!")
    print(f"  - 总文件数: {stats['total_files']}")
    print(f"  - 已删除: {stats['deleted']}")
    print(f"  - 保留: {stats['skipped']}")
    print(f"  - 错误: {stats['errors']}")
    print(f"  - 释放空间: {stats['freed_bytes']/1024/1024:.2f} MB")
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='清理 debug_responses 日志文件')
    parser.add_argument('--dir', help='日志目录路径（默认: 项目根目录/debug_responses）')
    parser.add_argument('--keep-days', type=int, default=3, help='保留最近几天的日志（默认: 3）')
    parser.add_argument('--dry-run', action='store_true', help='试运行，不实际删除文件')
    
    args = parser.parse_args()
    
    try:
        result = cleanup_debug_logs(
            debug_dir=args.dir,
            keep_days=args.keep_days,
            dry_run=args.dry_run
        )
        
        # 如果有错误，返回非零退出码
        if result["errors"] > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] 清理过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
