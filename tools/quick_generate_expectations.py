"""
快速为现有小说生成期待感标签的脚本
"""

import sys
import json
from pathlib import Path
from typing import Dict

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator, ExpectationType

def main():
    # 使用实际的项目目录名
    project_dir = Path("小说项目/凡人：绑定韩立，躺赢成圣_韩立圣")
    
    print(f"项目目录: {project_dir}")
    print(f"存在: {project_dir.exists()}")
    
    if not project_dir.exists():
        print("项目目录不存在，请检查项目名称")
        return
    
    # 查找plans目录
    plans_dir = project_dir / "plans"
    if not plans_dir.exists():
        print(f"Plans目录不存在: {plans_dir}")
        return
    
    print(f"Plans目录: {plans_dir}")
    
    # 查找所有写作计划文件
    plan_files = list(plans_dir.glob("*_writing_plan.json"))
    print(f"\n找到 {len(plan_files)} 个写作计划文件:")
    for pf in plan_files:
        print(f"  - {pf.name}")
    
    if not plan_files:
        print("未找到写作计划文件")
        return
    
    # 初始化期待管理器
    manager = ExpectationManager()
    integrator = ExpectationIntegrator(manager)
    
    total_tagged = 0
    
    # 处理每个阶段的计划
    for plan_file in plan_files:
        print(f"\n{'='*60}")
        print(f"处理: {plan_file.name}")
        print(f"{'='*60}")
        
        try:
            # 加载计划数据
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
            
            # 提取阶段写作计划
            stage_writing_plan = plan_data.get('stage_writing_plan', {})
            event_system = stage_writing_plan.get('event_system', {})
            major_events = event_system.get('major_events', [])
            
            print(f"  - 阶段名称: {plan_file.stem}")
            print(f"  - 重大事件数量: {len(major_events)}")
            
            # 为每个重大事件生成期待感标签
            for i, event in enumerate(major_events):
                event_name = event.get('name', f'事件{i+1}')
                chapter_range = event.get('chapter_range', '')
                main_goal = event.get('main_goal', '')
                
                print(f"    事件: {event_name}")
                print(f"      章节: {chapter_range}")
                print(f"      目标: {main_goal[:50]}...")
                
                # 根据事件特征智能选择期待类型
                expectation_type = select_expectation_type(event)
                
                # 计算种植和目标章节
                from src.managers.StagePlanUtils import parse_chapter_range
                try:
                    start_ch, end_ch = parse_chapter_range(chapter_range)
                    target_ch = max(start_ch + 3, end_ch)  # 目标章节至少3章后
                    
                    # 种植期待
                    exp_id = manager.tag_event_with_expectation(
                        event_id=event_name,
                        expectation_type=expectation_type,
                        planting_chapter=start_ch,
                        description=f"{event_name}: {main_goal[:50]}...",
                        target_chapter=target_ch
                    )
                    
                    print(f"      -> 添加期待: {expectation_type.value}")
                    total_tagged += 1
                    
                except Exception as e:
                    print(f"      ✗ 处理事件失败: {e}")
            
        except Exception as e:
            print(f"  ✗ 处理文件失败: {e}")
    
    print(f"\n{'='*60}")
    print(f"总计为 {total_tagged} 个事件添加了期待感标签")
    print(f"{'='*60}")
    
    # 生成期待感报告
    report = manager.generate_expectation_report()
    print(f"\n期待感统计:")
    print(f"  总期待数: {report['total_expectations']}")
    print(f"  已释放: {report['released_expectations']}")
    print(f"  待处理: {report['pending_expectations']}")
    print(f"  满足率: {report['satisfaction_rate']}%")
    
    # 保存期待感映射
    expectation_map = manager.export_expectation_map()
    expectation_file = project_dir / "expectation_map.json"
    
    try:
        with open(expectation_file, 'w', encoding='utf-8') as f:
            json.dump({
                'title': '凡人：绑定韩立，躺赢成圣',
                'generated_at': '2025-12-28',
                'expectation_map': expectation_map
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 期待感标签已保存到: {expectation_file}")
        print(f"\n下一步:")
        print(f"1. 刷新故事线页面")
        print(f"2. 你将看到每个事件卡片上显示期待感标签（🎯图标）")
        print(f"3. 点击事件可以查看详细的期待感信息")
        
    except Exception as e:
        print(f"✗ 保存期待感映射失败: {e}")


def select_expectation_type(event: Dict) -> "ExpectationType":
    """根据事件特征智能选择期待类型"""
    main_goal = event.get('main_goal', '').lower()
    emotional_focus = event.get('emotional_focus', '').lower()
    role = event.get('role_in_stage_arc', '').lower()
    
    # 决策树
    if '击败' in main_goal or '战胜' in main_goal or '复仇' in main_goal:
        return ExpectationType.SUPPRESSION_RELEASE
    
    if '获得' in main_goal or '得到' in main_goal or '炼成' in main_goal:
        return ExpectationType.SHOWCASE
    
    if '误解' in emotional_focus or '轻视' in emotional_focus:
        return ExpectationType.EMOTIONAL_HOOK
    
    if '展示' in main_goal or '学习' in main_goal:
        return ExpectationType.POWER_GAP
    
    if '揭秘' in main_goal or '真相' in main_goal:
        return ExpectationType.MYSTERY_FORESHADOW
    
    # 默认使用套娃式期待
    return ExpectationType.NESTED_DOLL


if __name__ == "__main__":
    main()