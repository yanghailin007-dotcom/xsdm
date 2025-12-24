# -*- coding: utf-8 -*-
"""
写作计划路径迁移脚本
将写作计划从 planning/writing_plans/ 目录迁移到 planning/ 目录
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def migrate_writing_plan():
    """迁移写作计划文件"""
    # 项目基础目录
    base_dir = Path("小说项目")
    
    # 查找所有项目
    projects = [d for d in base_dir.iterdir() if d.is_dir()]
    
    print(f"找到 {len(projects)} 个项目")
    
    for project_dir in projects:
        novel_title = project_dir.name
        print(f"\n处理项目: {novel_title}")
        
        # 旧路径
        old_planning_dir = project_dir / "planning" / "writing_plans"
        # 新路径
        new_planning_dir = project_dir / "planning"
        
        # 检查旧路径是否存在
        if not old_planning_dir.exists():
            print(f"  [!] 旧路径不存在: {old_planning_dir}")
            continue
        
        # 查找写作计划文件
        old_files = list(old_planning_dir.glob("*_写作计划.json"))
        
        if not old_files:
            print(f"  [!] 未找到写作计划文件")
            continue
        
        print(f"  找到 {len(old_files)} 个写作计划文件")
        
        for old_file in old_files:
            new_file = new_planning_dir / old_file.name
            
            print(f"  迁移: {old_file.name}")
            print(f"    从: {old_file}")
            print(f"    到: {new_file}")
            
            # 检查目标文件是否已存在
            if new_file.exists():
                print(f"    [!] 目标文件已存在，跳过")
                continue
            
            # 移动文件
            try:
                shutil.move(str(old_file), str(new_file))
                print(f"    [OK] 迁移成功")
            except Exception as e:
                print(f"    [ERROR] 迁移失败: {e}")
        
        # 尝试删除旧的 writing_plans 目录（如果为空）
        try:
            if old_planning_dir.exists() and not list(old_planning_dir.iterdir()):
                old_planning_dir.rmdir()
                print(f"  [OK] 已删除空的旧目录: {old_planning_dir}")
        except Exception as e:
            print(f"  [!] 无法删除旧目录: {e}")
    
    print("\n迁移完成！")

if __name__ == "__main__":
    migrate_writing_plan()