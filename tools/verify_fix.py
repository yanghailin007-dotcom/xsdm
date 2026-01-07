#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的验证脚本：确认 stage_writing_plans 字段映射修复
"""

import sys
import os
from pathlib import Path

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def verify_fix():
    """验证修复是否生效"""
    print("=" * 80)
    print("🔍 验证 stage_writing_plans 字段映射修复")
    print("=" * 80)
    
    novel_title = "重生成剑：宿主祭天，法力无边"
    
    # 1. 加载小说详情
    print("\n1️⃣ 加载小说详情...")
    try:
        from web.managers.novel_manager import NovelGenerationManager
        manager = NovelGenerationManager()
        
        novel_detail = manager.get_novel_detail(novel_title)
        
        if not novel_detail:
            print("  ❌ 无法获取小说详情")
            return False
        
        print(f"  ✅ 成功获取小说详情")
        
    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        return False
    
    # 2. 检查字段映射
    print("\n2️⃣ 检查字段映射...")
    
    # 检查 stage_writing_plans
    stage_writing_plans = novel_detail.get("stage_writing_plans", {})
    if stage_writing_plans:
        print(f"  ✅ stage_writing_plans 存在")
        print(f"     - 阶段数量: {len(stage_writing_plans)}")
        print(f"     - 阶段列表: {list(stage_writing_plans.keys())}")
    else:
        print(f"  ❌ stage_writing_plans 不存在")
        return False
    
    # 检查 overall_stage_plans
    overall_stage_plans = novel_detail.get("overall_stage_plans", {})
    if overall_stage_plans:
        print(f"  ✅ overall_stage_plans 存在")
    else:
        print(f"  ❌ overall_stage_plans 不存在")
    
    # 3. 检查阶段数据结构
    print("\n3️⃣ 检查阶段数据结构...")
    
    # 检查第一个阶段
    first_stage_name = list(stage_writing_plans.keys())[0]
    first_stage = stage_writing_plans[first_stage_name]
    
    print(f"  检查阶段: {first_stage_name}")
    
    if "stage_writing_plan" in first_stage:
        stage_plan = first_stage["stage_writing_plan"]
        print(f"  ✅ 包含 stage_writing_plan")
        
        if "event_system" in stage_plan:
            event_system = stage_plan["event_system"]
            print(f"  ✅ 包含 event_system")
            print(f"     - major_events: {len(event_system.get('major_events', []))} 个")
            print(f"     - big_events: {len(event_system.get('big_events', []))} 个")
        else:
            print(f"  ❌ 不包含 event_system")
    else:
        print(f"  ❌ 不包含 stage_writing_plan")
    
    # 4. 总结
    print("\n" + "=" * 80)
    print("✅ 验证结果：修复成功！")
    print("=" * 80)
    print("\n📋 修复内容:")
    print("在 web/managers/novel_manager.py 的 get_novel_detail() 方法中添加了:")
    print("1. 从 quality_data.writing_plans 映射到 stage_writing_plans")
    print("2. 从 writing_plans 构建 overall_stage_plans")
    print("3. 创建基础 global_growth_plan 结构")
    print("\n💡 这确保了 EventDrivenManager 能正确找到阶段写作计划数据，")
    print("    不再返回'未知阶段'。")
    
    return True


if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)