"""测试文件名清理逻辑"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint

# 测试原始书名
test_title = "我魔剑逼疯女帝屠苍生"
print(f"原始书名: {test_title}")

# 创建检查点管理器来测试
checkpoint = GenerationCheckpoint(test_title, Path.cwd())
print(f"安全标题: {checkpoint.safe_title}")
print(f"检查点目录: {checkpoint.checkpoint_dir}")
print(f"检查点文件: {checkpoint.checkpoint_file}")

# 检查目录是否存在
print(f"\n目录是否存在: {checkpoint.checkpoint_dir.exists()}")
print(f"文件是否存在: {checkpoint.checkpoint_file.exists()}")

# 列出实际的项目目录
projects_dir = Path("小说项目")
if projects_dir.exists():
    print(f"\n实际的项目目录列表:")
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            print(f"  - {project_dir.name}")