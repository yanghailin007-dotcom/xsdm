#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断势力系统文件检测问题
"""

import os
import sys
import json
from pathlib import Path
import re

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def diagnose_faction_system(title):
    """诊断势力系统文件检测问题"""
    
    print(f"\n{'='*80}")
    print(f"诊断项目: {title}")
    print(f"{'='*80}\n")
    
    # 清理标题
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    
    # 可能的路径
    possible_paths = [
        f"小说项目/{title}/materials/worldview",
        f"小说项目/{safe_title}/materials/worldview",
        f"小说项目/{title}/worldview",
        f"小说项目/{safe_title}/worldview",
    ]
    
    print("[搜索] 检查可能的势力系统文件路径:\n")
    
    found_files = []
    for base_path in possible_paths:
        if os.path.exists(base_path):
            print(f"[OK] 目录存在: {base_path}")
            
            # 查找势力系统文件
            faction_pattern = os.path.join(base_path, "*势力系统*")
            matching_files = []
            
            # 尝试多种模式
            patterns = [
                os.path.join(base_path, "*_势力系统.json"),
                os.path.join(base_path, "*_势力系统.js"),
                os.path.join(base_path, "*势力系统.json"),
                os.path.join(base_path, "*势力系统.js"),
            ]
            
            for pattern in patterns:
                if os.path.exists(pattern):
                    matching_files.append(pattern)
                    print(f"  [FILE] 找到文件: {pattern}")
            
            # 列出目录中所有文件
            all_files = os.listdir(base_path)
            print(f"  [DIR] 目录中的所有文件 ({len(all_files)} 个):")
            for f in sorted(all_files):
                if "势力" in f or "faction" in f.lower():
                    print(f"     [FOUND] {f}")
                    if f not in [os.path.basename(ff) for ff in matching_files]:
                        full_path = os.path.join(base_path, f)
                        matching_files.append(full_path)
            
            found_files.extend(matching_files)
        else:
            print(f"[X] 目录不存在: {base_path}")
    
    print(f"\n{'='*80}")
    print(f"诊断结果:")
    print(f"{'='*80}\n")
    
    if found_files:
        print(f"[SUCCESS] 找到 {len(found_files)} 个势力系统相关文件:\n")
        for i, file_path in enumerate(found_files, 1):
            print(f"{i}. {file_path}")
            
            # 检查文件扩展名
            ext = os.path.splitext(file_path)[1]
            print(f"   扩展名: {ext}")
            
            # 检查文件是否可读
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"   ✅ 文件可读，包含 {len(data)} 个顶级键")
                    
                    # 显示前几个键
                    keys = list(data.keys())[:5]
                    print(f"   键: {keys}")
            except Exception as e:
                print(f"   [ERROR] 文件读取失败: {e}")
            
            print()
    else:
        print("[FAIL] 未找到任何势力系统文件")
        print("\n[TIPS] 可能的原因:")
        print("1. 文件尚未生成")
        print("2. 文件保存在其他位置")
        print("3. 文件名使用了不同的命名模式")
    
    # 检查 ProductLoader 使用的路径
    print(f"\n{'='*80}")
    print("ProductLoader 路径检查:")
    print(f"{'='*80}\n")
    
    # 模拟 ProductLoader 的路径
    project_dir = Path("小说项目") / title
    if not project_dir.exists():
        project_dir = Path("小说项目") / safe_title
    
    print(f"项目目录: {project_dir}")
    print(f"存在: {project_dir.exists()}\n")
    
    worldview_dir = project_dir / "worldview"
    print(f"worldview_dir (尝试1): {worldview_dir}")
    print(f"存在: {worldview_dir.exists()}\n")
    
    if not worldview_dir.exists():
        worldview_dir = project_dir / "materials" / "worldview"
        print(f"worldview_dir (尝试2): {worldview_dir}")
        print(f"存在: {worldview_dir.exists()}\n")
    
    if worldview_dir.exists():
        print(f"使用 worldview_dir: {worldview_dir}")
        faction_files = list(worldview_dir.glob("*_势力系统.json"))
        print(f"glob 模式: *_势力系统.json")
        print(f"找到 {len(faction_files)} 个文件")
        for f in faction_files:
            print(f"  - {f.name}")

if __name__ == "__main__":
    # 测试项目
    test_title = "重生成剑：宿主祭天，法力无边"
    diagnose_faction_system(test_title)