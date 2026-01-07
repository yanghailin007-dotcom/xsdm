#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查写作计划加载情况的工具
用于诊断EventDrivenManager报告"未知阶段"的问题
"""

import sys
import os
import json
from pathlib import Path

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def check_project_structure(novel_title: str):
    """检查项目结构和写作计划文件"""
    print("=" * 80)
    print(f"📋 检查项目: {novel_title}")
    print("=" * 80)
    
    # 1. 检查项目目录
    from src.config.path_config import path_config
    paths = path_config.get_project_paths(novel_title)
    
    print("\n📁 项目路径配置:")
    for key, path in paths.items():
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"  {exists} {key}: {path}")
    
    # 2. 检查写作计划文件
    print("\n📝 写作计划文件检查:")
    
    # 检查多个可能的路径
    possible_paths = [
        Path(paths["writing_plans_dir"]) / f"{path_config.get_safe_title(novel_title)}_写作计划.json",
        Path("小说项目") / novel_title / "planning" / f"{novel_title}_写作计划.json",
        Path("小说项目") / path_config.get_safe_title(novel_title) / "planning" / f"{path_config.get_safe_title(novel_title)}_写作计划.json",
        Path("D:/work6.05/小说项目") / novel_title / "planning" / f"{novel_title}_写作计划.json",
    ]
    
    found_path = None
    for path in possible_paths:
        if path.exists():
            print(f"  ✅ 找到写作计划: {path}")
            found_path = path
            break
        else:
            print(f"  ❌ 未找到: {path}")
    
    if not found_path:
        print("\n⚠️ 未找到写作计划文件！")
        return None
    
    # 3. 读取并分析写作计划内容
    print(f"\n📖 读取写作计划: {found_path}")
    try:
        with open(found_path, 'r', encoding='utf-8') as f:
            writing_plan = json.load(f)
        
        print(f"  ✅ 成功读取文件")
        print(f"  📊 文件大小: {os.path.getsize(found_path) / 1024:.2f} KB")
        
        # 分析结构
        print("\n🔍 写作计划结构分析:")
        print(f"  - 顶层键数量: {len(writing_plan)}")
        print(f"  - 顶层键列表: {list(writing_plan.keys())}")
        
        # 检查是否包含阶段写作计划
        if "stage_writing_plans" in writing_plan:
            stage_plans = writing_plan["stage_writing_plans"]
            print(f"  ✅ 包含 stage_writing_plans: {len(stage_plans)} 个阶段")
            for stage_name in stage_plans.keys():
                print(f"     - {stage_name}")
        else:
            # 检查是否是直接包含阶段数据的格式
            print(f"  ⚠️ 不包含 stage_writing_plans 键")
            
            # 检查是否包含标准阶段键
            standard_stages = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
            found_stages = [k for k in writing_plan.keys() if k in standard_stages]
            if found_stages:
                print(f"  ✅ 包含标准阶段键: {found_stages}")
        
        # 检查第一个阶段的结构
        first_key = list(writing_plan.keys())[0]
        first_stage = writing_plan[first_key]
        
        if isinstance(first_stage, dict):
            print(f"\n📋 第一个阶段 ({first_key}) 的结构:")
            print(f"  - 键数量: {len(first_stage)}")
            print(f"  - 键列表: {list(first_stage.keys())}")
            
            if "stage_writing_plan" in first_stage:
                stage_plan = first_stage["stage_writing_plan"]
                print(f"  ✅ 包含 stage_writing_plan")
                print(f"  - stage_writing_plan 的键: {list(stage_plan.keys())}")
                
                if "event_system" in stage_plan:
                    event_system = stage_plan["event_system"]
                    print(f"  ✅ 包含 event_system")
                    print(f"    - major_events 数量: {len(event_system.get('major_events', []))}")
                    print(f"    - big_events 数量: {len(event_system.get('big_events', []))}")
                    
                if "chapter_range" in stage_plan:
                    print(f"  📖 章节范围: {stage_plan['chapter_range']}")
        
        return {
            "path": str(found_path),
            "data": writing_plan,
            "structure": list(writing_plan.keys())
        }
        
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def simulate_project_loading(novel_title: str):
    """模拟ProjectManager加载项目的过程"""
    print("\n" + "=" * 80)
    print("🔄 模拟项目加载过程")
    print("=" * 80)
    
    from src.core.ProjectManager import ProjectManager
    from src.managers.growth_plan_manager import growth_plan_manager
    
    pm = ProjectManager()
    
    print("\n1️⃣ 尝试从独立文件加载写作计划...")
    stage_plans = growth_plan_manager.load_stage_writing_plans(novel_title)
    
    if stage_plans:
        print(f"  ✅ 成功加载写作计划")
        print(f"  📊 阶段数量: {len(stage_plans)}")
        print(f"  📋 阶段列表: {list(stage_plans.keys())}")
        return stage_plans
    else:
        print(f"  ❌ 无法从独立文件加载")
        return None


def simulate_eventdriven_initialization(novel_title: str):
    """模拟EventDrivenManager初始化过程"""
    print("\n" + "=" * 80)
    print("🎯 模拟EventDrivenManager初始化")
    print("=" * 80)
    
    # 模拟novel_data结构
    from src.core.ProjectManager import ProjectManager
    from src.managers.growth_plan_manager import growth_plan_manager
    
    pm = ProjectManager()
    
    # 加载项目数据
    print("\n1️⃣ 加载项目数据...")
    novel_data = pm.load_project(novel_title)
    
    if not novel_data:
        print("  ❌ 无法加载项目数据")
        return
    
    print(f"  ✅ 项目数据加载成功")
    print(f"  📖 小说标题: {novel_data.get('novel_title', 'N/A')}")
    
    # 检查stage_writing_plans
    print("\n2️⃣ 检查 stage_writing_plans...")
    stage_plans = novel_data.get("stage_writing_plans", {})
    
    if stage_plans:
        print(f"  ✅ 包含 stage_writing_plans")
        print(f"  📊 阶段数量: {len(stage_plans)}")
        print(f"  📋 阶段列表: {list(stage_plans.keys())}")
        
        # 检查第一个阶段的结构
        first_stage_key = list(stage_plans.keys())[0]
        first_stage = stage_plans[first_stage_key]
        
        print(f"\n3️⃣ 检查第一个阶段 ({first_stage_key}) 的结构...")
        if "stage_writing_plan" in first_stage:
            stage_plan = first_stage["stage_writing_plan"]
            print(f"  ✅ 包含 stage_writing_plan")
            
            if "event_system" in stage_plan:
                event_system = stage_plan["event_system"]
                print(f"  ✅ 包含 event_system")
                print(f"    - major_events: {len(event_system.get('major_events', []))} 个")
                print(f"    - big_events: {len(event_system.get('big_events', []))} 个")
            else:
                print(f"  ⚠️ 不包含 event_system")
        else:
            print(f"  ⚠️ 不包含 stage_writing_plan")
    else:
        print(f"  ❌ 不包含 stage_writing_plans")
        print(f"  💡 这可能是导致'未知阶段'的原因！")
    
    # 模拟_get_current_stage_from_plans方法
    print("\n4️⃣ 模拟获取当前阶段...")
    chapter_number = 1  # 假设是第1章
    
    # 从 overall_stage_plans 中查找
    overall_plan = novel_data.get("overall_stage_plans", {}).get("overall_stage_plan", {})
    if overall_plan:
        print(f"  ✅ 包含 overall_stage_plan")
        for stage_name, stage_info in overall_plan.items():
            chapter_range = stage_info.get("chapter_range", "")
            print(f"     - {stage_name}: {chapter_range}")
    
    # 从 stage_writing_plans 中推断
    if stage_plans:
        print(f"  📋 从 stage_writing_plans 推断:")
        for stage_name, stage_data in stage_plans.items():
            chapter_range = ""
            if "stage_writing_plan" in stage_data:
                chapter_range = stage_data["stage_writing_plan"].get("chapter_range", "")
            else:
                chapter_range = stage_data.get("chapter_range", "")
            
            if chapter_range:
                print(f"     - {stage_name}: {chapter_range}")
                
                # 检查章节是否在范围内
                import re
                numbers = re.findall(r'\d+', chapter_range)
                if len(numbers) >= 2:
                    start_chapter = int(numbers[0])
                    end_chapter = int(numbers[1])
                    if start_chapter <= chapter_number <= end_chapter:
                        print(f"       ✅ 第{chapter_number}章属于此阶段！")
                        return stage_name
            else:
                print(f"     - {stage_name}: (无章节范围)")
    
    print(f"  ⚠️ 无法确定第{chapter_number}章所属阶段")
    return "未知阶段"


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🔍 写作计划加载诊断工具")
    print("=" * 80)
    
    # 默认检查用户提到的小说
    default_novel = "重生成剑：宿主祭天，法力无边"
    
    import argparse
    parser = argparse.ArgumentParser(description='检查写作计划加载情况')
    parser.add_argument('--novel', type=str, default=default_novel, 
                       help='小说标题 (默认: 重生成剑：宿主祭天，法力无边)')
    
    args = parser.parse_args()
    
    novel_title = args.novel
    
    # 1. 检查项目结构
    plan_info = check_project_structure(novel_title)
    
    if not plan_info:
        print("\n❌ 无法找到或读取写作计划文件")
        print("\n💡 可能的解决方案:")
        print("1. 确认写作计划文件路径是否正确")
        print("2. 检查文件是否存在于指定位置")
        print("3. 确认文件格式是否为有效的JSON")
        return
    
    # 2. 模拟项目加载
    stage_plans = simulate_project_loading(novel_title)
    
    # 3. 模拟EventDrivenManager初始化
    current_stage = simulate_eventdriven_initialization(novel_title)
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 诊断总结")
    print("=" * 80)
    
    if plan_info:
        print(f"✅ 写作计划文件存在: {plan_info['path']}")
        print(f"📋 文件结构: {plan_info['structure']}")
    
    if stage_plans:
        print(f"✅ 能够从独立文件加载写作计划: {len(stage_plans)} 个阶段")
    else:
        print(f"❌ 无法从独立文件加载写作计划")
    
    if current_stage and current_stage != "未知阶段":
        print(f"✅ 能够正确确定当前阶段: {current_stage}")
    else:
        print(f"❌ 无法确定当前阶段，返回: {current_stage}")
    
    print("\n💡 如果显示'未知阶段'，可能的原因:")
    print("1. 写作计划文件中没有章节范围信息 (chapter_range)")
    print("2. stage_writing_plans 结构与预期不符")
    print("3. EventDrivenManager 的 _get_current_stage_from_plans 方法逻辑有误")
    print("4. overall_stage_plans 和 stage_writing_plans 都缺少必要的阶段信息")


if __name__ == "__main__":
    main()