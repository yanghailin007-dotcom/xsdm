#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动为现有项目创建项目信息JSON文件
解决第一阶段生成完成后没有产生项目信息JSON文件的问题
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

def create_safe_filename(title):
    """创建安全的文件名"""
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    safe_title = re.sub(r'[:]', "_", safe_title)  # 确保冒号被处理
    safe_title = safe_title.strip()
    return safe_title

def create_project_info_for_existing_project(novel_title):
    """为现有项目创建项目信息JSON文件"""
    
    print(f"开始为项目《{novel_title}》创建项目信息文件...")
    
    safe_title = create_safe_filename(novel_title)
    print(f"安全标题: {safe_title}")
    
    # 检查项目目录是否存在
    project_dir = Path(f"小说项目/{safe_title}")
    if not project_dir.exists():
        print(f"项目目录不存在: {project_dir}")
        return False
    
    # 构建基础项目信息
    project_info = {
        "novel_title": novel_title,
        "safe_title": safe_title,
        "category": "东方仙侠",  # 默认分类
        "total_chapters": 200,  # 默认章节数
        "creative_seed": {
            "coreSetting": "凡人修仙世界，落云宗种田生活",
            "coreSellingPoints": "种田流、凡人修仙传同人、慢节奏生活",
            "completeStoryline": {}
        },
        "selected_plan": {
            "title": novel_title,
            "synopsis": "一个凡人在落云宗的种田修仙生活",
            "tags": {"main_category": "东方仙侠"}
        },
        "is_phase_one_completed": True,
        "phase_one_completed_at": datetime.now().isoformat(),
        "next_phase": "second_phase_content_generation",
        "created_at": datetime.now().isoformat(),
        "status": "phase_one_completed",
        "project_directory": str(project_dir)
    }
    
    # 尝试从现有目录加载一些信息
    try:
        # 检查是否有规划目录
        planning_dir = project_dir / "planning"
        if planning_dir.exists():
            print(f"找到规划目录: {planning_dir}")
            project_info["has_planning"] = True
        
        # 检查是否有世界观目录
        worldview_dir = project_dir / "worldview"
        if worldview_dir.exists():
            print(f"找到世界观目录: {worldview_dir}")
            project_info["has_worldview"] = True
        
        # 检查是否有章节目录
        chapters_dir = project_dir / "chapters"
        if chapters_dir.exists():
            chapter_files = list(chapters_dir.glob("*.txt")) + list(chapters_dir.glob("*.json"))
            project_info["generated_chapters_count"] = len(chapter_files)
            print(f"找到 {len(chapter_files)} 个章节文件")
            
    except Exception as e:
        print(f"加载现有项目信息时出错: {e}")
    
    # 创建第一阶段设定目录
    phase_one_dir = Path(f"小说项目/{safe_title}_第一阶段设定")
    phase_one_dir.mkdir(exist_ok=True)
    print(f"创建第一阶段目录: {phase_one_dir}")
    
    # 保存第一阶段结果文件
    phase_one_file = phase_one_dir / f"{safe_title}_第一阶段设定.json"
    try:
        with open(phase_one_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        if phase_one_file.exists():
            file_size = phase_one_file.stat().st_size
            print(f"第一阶段结果文件已保存: {phase_one_file} (大小: {file_size} 字节)")
        else:
            print(f"第一阶段结果文件保存失败: {phase_one_file}")
            return False
            
    except Exception as e:
        print(f"保存第一阶段结果文件失败: {e}")
        return False
    
    # 保存主项目信息文件
    main_project_file = Path(f"小说项目/{safe_title}_项目信息.json")
    project_info_for_main = {
        **project_info,
        "phase_one_file": str(phase_one_file),
        "project_info_file": str(main_project_file)
    }
    
    try:
        with open(main_project_file, 'w', encoding='utf-8') as f:
            json.dump(project_info_for_main, f, ensure_ascii=False, indent=2)
        
        if main_project_file.exists():
            file_size = main_project_file.stat().st_size
            print(f"主项目信息文件已保存: {main_project_file} (大小: {file_size} 字节)")
        else:
            print(f"主项目信息文件保存失败: {main_project_file}")
            return False
            
    except Exception as e:
        print(f"保存主项目信息文件失败: {e}")
        return False
    
    print(f"项目《{novel_title}》的信息文件创建完成！")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("手动创建项目信息JSON文件工具")
    print("=" * 60)
    
    # 自动检测现有的项目
    novel_projects_dir = Path("小说项目")
    if not novel_projects_dir.exists():
        print(f"小说项目目录不存在: {novel_projects_dir}")
        return
    
    # 查找现有的项目目录
    existing_projects = []
    for item in novel_projects_dir.iterdir():
        if item.is_dir() and not item.name.endswith("_第一阶段设定"):
            existing_projects.append(item.name)
    
    if not existing_projects:
        print("没有找到现有的项目目录")
        return
    
    print(f"找到 {len(existing_projects)} 个现有项目:")
    for i, project_name in enumerate(existing_projects, 1):
        print(f"  {i}. {project_name}")
    
    # 为每个现有项目创建信息文件
    success_count = 0
    for project_name in existing_projects:
        print(f"\n" + "-" * 40)
        if create_project_info_for_existing_project(project_name):
            success_count += 1
    
    print(f"\n" + "=" * 60)
    print(f"完成！成功为 {success_count}/{len(existing_projects)} 个项目创建了信息文件")
    print("=" * 60)

if __name__ == "__main__":
    main()