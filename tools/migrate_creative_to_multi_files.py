#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将单个创意文件迁移到多文件结构的工具

用法：
    python tools/migrate_creative_to_multi_files.py
"""

import os
import json
import sys
from datetime import datetime

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 配置路径
CREATIVE_IDEAS_FILE = os.path.join(project_root, "data", "creative_ideas", "novel_ideas.txt")
CREATIVE_IDEAS_DIR = os.path.join(project_root, "data", "creative_ideas")
BACKUP_FILE = os.path.join(project_root, "data", "creative_ideas", f"novel_ideas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")


def migrate_to_multi_files():
    """将单个创意文件迁移到多文件结构"""
    
    print("=" * 60)
    print("创意文件迁移工具")
    print("=" * 60)
    
    # 1. 备份原文件
    print(f"\n📦 步骤1: 备份原文件...")
    if os.path.exists(CREATIVE_IDEAS_FILE):
        try:
            with open(CREATIVE_IDEAS_FILE, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            print(f"✅ 备份成功: {BACKUP_FILE}")
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False
    else:
        print(f"⚠️  原文件不存在: {CREATIVE_IDEAS_FILE}")
        return False
    
    # 2. 读取原文件内容
    print(f"\n📖 步骤2: 读取原文件...")
    try:
        data = json.loads(original_content)
        creative_works = data.get("creativeWorks", [])
        print(f"✅ 成功读取 {len(creative_works)} 个创意")
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return False
    
    # 3. 为每个创意创建独立文件
    print(f"\n📝 步骤3: 创建独立创意文件...")
    success_count = 0
    
    for i, work in enumerate(creative_works):
        # 生成文件名（使用小说标题或序号）
        novel_title = work.get("novelTitle", f"创意{i+1}")
        # 清理文件名中的非法字符
        safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = f"creative_idea_{i+1}"
        
        filename = f"{i+1:03d}_{safe_title}.json"
        filepath = os.path.join(CREATIVE_IDEAS_DIR, filename)
        
        try:
            # 保存为独立JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(work, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            print(f"  ✅ 创建文件: {filename}")
            
        except Exception as e:
            print(f"  ❌ 创建文件失败 {filename}: {e}")
    
    print(f"\n✅ 成功创建 {success_count}/{len(creative_works)} 个创意文件")
    
    # 4. 询问是否删除原文件
    print(f"\n" + "=" * 60)
    print("🎉 迁移完成!")
    print(f"\n📊 迁移统计:")
    print(f"  - 原文件: {CREATIVE_IDEAS_FILE}")
    print(f"  - 备份文件: {BACKUP_FILE}")
    print(f"  - 创意数量: {len(creative_works)}")
    print(f"  - 成功创建: {success_count} 个创意文件")
    print(f"\n💡 说明:")
    print(f"  - 无需索引文件，系统会自动扫描目录中的JSON文件")
    print(f"  - 建议保留原文件作为备份")
    print(f"  - 创意文件按文件名排序，ID=文件序号")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = migrate_to_multi_files()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)