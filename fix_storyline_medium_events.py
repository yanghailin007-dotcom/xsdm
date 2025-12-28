"""
诊断和修复故事线中级事件问题

问题1: 中级事件里面没有特殊事件
问题2: 中级事件的章节范围没有标注出来
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def analyze_stage_plan_file(file_path):
    """分析阶段计划文件结构"""
    print(f"\n{'='*60}")
    print(f"分析文件: {file_path}")
    print('='*60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        stage_plan = data.get('stage_writing_plan', {})
        event_system = stage_plan.get('event_system', {})
        major_events = event_system.get('major_events', [])
        
        print(f"\n✅ 找到 {len(major_events)} 个重大事件")
        
        if major_events:
            # 分析第一个重大事件
            first_event = major_events[0]
            print(f"\n📋 第一个重大事件结构:")
            print(f"   - name: {first_event.get('name', 'N/A')}")
            print(f"   - chapter_range: {first_event.get('chapter_range', 'N/A')}")
            print(f"   - 有 composition: {'composition' in first_event}")
            print(f"   - 有 special_events: {'special_events' in first_event}")
            
            # 分析 composition
            if 'composition' in first_event:
                composition = first_event['composition']
                print(f"\n   Composition 结构: {list(composition.keys())}")
                
                for phase, events in composition.items():
                    if isinstance(events, list) and events:
                        print(f"\n   [{phase}] 阶段 ({len(events)} 个中级事件):")
                        for i, me in enumerate(events[:2]):  # 只显示前2个
                            print(f"      {i+1}. {me.get('name', 'N/A')}")
                            print(f"         - chapter_range: {me.get('chapter_range', 'N/A')}")
                            print(f"         - 有 special_events: {'special_events' in me}")
                            if 'special_events' in me:
                                print(f"         - special_events 数量: {len(me.get('special_events', []))}")
            
            # 检查是否有 _medium_events
            if '_medium_events' in first_event:
                print(f"\n   _medium_events: {len(first_event['_medium_events'])} 个")
        
        return True
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import sys
    import io
    # 设置标准输出为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("故事线中级事件问题诊断工具")
    print("="*60)
    
    # 查找测试项目
    project_dir = Path("小说项目")
    if not project_dir.exists():
        print("❌ 未找到 '小说项目' 目录")
        return
    
    # 查找第一个包含 plans 目录的项目
    projects = [p for p in project_dir.iterdir() if p.is_dir()]
    
    if not projects:
        print("❌ 未找到任何项目")
        return
    
    for project in projects[:2]:  # 检查前2个项目
        plans_dir = project / "plans"
        if plans_dir.exists():
            stage_files = list(plans_dir.glob("*_stage_writing_plan.json"))
            if stage_files:
                print(f"\n📁 项目: {project.name}")
                for stage_file in stage_files:
                    analyze_stage_plan_file(stage_file)
    
    print(f"\n{'='*60}")
    print("诊断完成！")
    print("="*60)
    
    print("\n📋 问题描述:")
    print("1. 中级事件（medium events）中缺少 special_events 数据")
    print("2. 中级事件中缺少 chapter_range 信息")
    
    print("\n🔧 修复方案:")
    print("1. 后端: 从 composition 中提取中级事件时，保留 special_events 和 chapter_range")
    print("2. 前端: 在中级事件卡片中显示 special_events")
    print("3. 前端: 在中级事件卡片中显示 chapter_range（已有，但可能数据缺失）")

if __name__ == '__main__':
    main()