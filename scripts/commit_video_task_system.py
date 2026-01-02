"""
提交视频任务管理系统代码
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """执行命令并显示输出"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    
    print(result.stdout)
    return True

def main():
    print("=" * 60)
    print("🚀 开始提交视频任务管理系统代码")
    print("=" * 60)
    print()
    
    # 1. 添加所有新文件
    print("📝 添加文件到Git...")
    files_to_add = [
        "src/models/video_task_models.py",
        "src/models/__init__.py",
        "src/schedulers/video_task_scheduler.py",
        "src/schedulers/__init__.py",
        "src/workers/video_worker.py",
        "src/workers/__init__.py",
        "src/websocket/video_progress_ws.py",
        "src/websocket/__init__.py",
        "web/api/video_task_api.py",
        "web/templates/video-task-manager.html",
        "web/static/css/video-task-manager.css",
        "web/static/js/video-task-manager.js",
        "scripts/init_video_task_system.py",
        "docs/VIDEO_TASK_MANAGER_GUIDE.md",
        "docs/VIDEO_TASK_MANAGER_IMPLEMENTATION_SUMMARY.md"
    ]
    
    for file in files_to_add:
        if Path(file).exists():
            run_command(["git", "add", file])
        else:
            print(f"⚠️ 文件不存在: {file}")
    
    print()
    
    # 2. 查看状态
    print("📋 查看Git状态...")
    run_command(["git", "status"])
    
    print()
    
    # 3. 创建提交
    print("💾 创建提交...")
    run_command([
        "git", "commit", "-m",
        "feat: 实现视频生成任务管理系统\n\n- 实现完整的数据模型（VideoProject, VideoTask, Shot）\n- 实现任务调度器（VideoTaskScheduler）\n- 实现Worker（VideoWorker）\n- 实现任务管理API接口\n- 创建Web任务管理页面\n- 实现WebSocket实时进度推送\n- 完整的使用文档"
    ])
    
    print()
    print("=" * 60)
    print("✅ 代码提交完成！")
    print("=" * 60)
    print()
    print("📌 下一步：")
    print("1. 查看提交状态: git log --oneline -5")
    print("2. 推送到远程仓库: git push")
    print()

if __name__ == "__main__":
    main()