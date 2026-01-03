#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查点诊断脚本
"""
import os
import sys
import json
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint, CheckpointRecoveryManager

# 设置工作目录
workspace_dir = Path.cwd()

print("=" * 80)
print("检查点诊断工具")
print("=" * 80)
print(f"工作目录: {workspace_dir}")
print()

# 1. 查找所有检查点文件
print("1. 扫描检查点文件...")
projects_dir = workspace_dir / "小说项目"
checkpoint_files = []

if projects_dir.exists():
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        checkpoint_file = project_dir / ".generation" / "checkpoint.json"
        if checkpoint_file.exists() and checkpoint_file.is_file():
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                checkpoint_files.append({
                    'path': checkpoint_file,
                    'project_dir': project_dir.name,
                    'novel_title': checkpoint_data.get('novel_title', 'Unknown')
                })
            except Exception as e:
                print(f"  [FAIL] 读取失败 {checkpoint_file}: {e}")

print(f"[OK] 找到 {len(checkpoint_files)} 个检查点文件")
for cf in checkpoint_files:
    print(f"  - 项目目录: {cf['project_dir']}")
    print(f"    小说标题: {cf['novel_title']}")
    print(f"    文件路径: {cf['path']}")
print()

# 2. 测试查找特定标题
test_title = "修仙：我是一柄魔剑，专治各种不服"
print(f"2. 测试查找标题: {test_title}")
print()

# 2.1 使用 GenerationCheckpoint 类
print("  2.1 使用 GenerationCheckpoint 类:")
checkpoint_mgr = GenerationCheckpoint(test_title, workspace_dir)
print(f"    检查点目录: {checkpoint_mgr.checkpoint_dir}")
print(f"    检查点文件: {checkpoint_mgr.checkpoint_file}")
print(f"    文件存在: {checkpoint_mgr.checkpoint_file.exists()}")
print(f"    可以恢复: {checkpoint_mgr.can_resume()}")

if checkpoint_mgr.can_resume():
    resume_info = checkpoint_mgr.get_resume_info()
    if resume_info:
        print(f"    [OK] 可以恢复:")
        print(f"      阶段: {resume_info.get('phase')}")
        print(f"      步骤: {resume_info.get('current_step')}")
    else:
        print(f"    [FAIL] get_resume_info 返回 None")
else:
    print(f"    [FAIL] 无法恢复")
print()

# 2.2 检查安全文件名
print("  2.2 文件名清理:")
safe_title = checkpoint_mgr._sanitize_filename(test_title)
print(f"    原始标题: {test_title}")
print(f"    清理后: {safe_title}")
print(f"    项目目录名: {safe_title}")
expected_path = workspace_dir / "小说项目" / safe_title / ".generation" / "checkpoint.json"
print(f"    期望路径: {expected_path}")
print(f"    文件存在: {expected_path.exists()}")
print()

# 2.3 遍历实际项目目录
print("  2.3 遍历实际项目目录:")
if projects_dir.exists():
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        checkpoint_file = project_dir / ".generation" / "checkpoint.json"
        if checkpoint_file.exists():
            print(f"    找到检查点: {project_dir.name}")
            
            # 读取检查点
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                stored_title = data.get('novel_title', '')
                print(f"      存储的标题: {stored_title}")
                
                # 测试反向查找
                mgr = GenerationCheckpoint(stored_title, workspace_dir)
                print(f"      生成的路径: {mgr.checkpoint_file}")
                print(f"      路径匹配: {mgr.checkpoint_file == checkpoint_file}")
            except Exception as e:
                print(f"      [FAIL] 读取失败: {e}")
print()

# 3. 使用 CheckpointRecoveryManager
print("3. 使用 CheckpointRecoveryManager:")
recovery_manager = CheckpointRecoveryManager(workspace_dir)
resumable_tasks = recovery_manager.find_resumable_tasks()
print(f"找到 {len(resumable_tasks)} 个可恢复任务:")
for task in resumable_tasks:
    print(f"  - {task.get('novel_title')}")
    print(f"    阶段: {task.get('phase')}, 步骤: {task.get('current_step')}")
print()

# 4. 测试 URL 解码
print("4. 测试 URL 解码:")
from urllib.parse import unquote
url_encoded_title = "修仙：我是一柄魔剑，专治各种不服"
print(f"  URL 标题: {url_encoded_title}")
decoded_title = unquote(url_encoded_title)
print(f"  解码后: {decoded_title}")
print(f"  匹配: {decoded_title == test_title}")
print()

print("=" * 80)
print("诊断完成")
print("=" * 80)