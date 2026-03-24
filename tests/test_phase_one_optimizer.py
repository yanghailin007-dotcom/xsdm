# -*- coding: utf-8 -*-
"""
Phase One Optimizer 测试
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.services.phase_one_optimizer import PhaseOneOptimizer, task_manager


def test_optimizer():
    """测试优化器"""
    print("=" * 60)
    print("Phase One Optimizer 测试")
    print("=" * 60)
    
    # 创建测试数据
    test_products = {
        "worldview": {
            "世界观概述": "这是一个修仙与科技并存的世界",
            "修炼体系": ["炼气", "筑基", "金丹", "元婴", "化神"],
            "核心法则": "灵气复苏,科技与修仙融合"
        },
        "characters": {
            "主角": {
                "姓名": "林凡",
                "性格": "谨慎、机智",
                "金手指": "系统辅助修炼"
            },
            "主要配角": [
                {"姓名": "苏晴", "关系": "师妹"},
                {"姓名": "老者", "关系": "师父"}
            ]
        },
        "factions": {
            "正道联盟": "维护修仙界秩序",
            "魔教": "追求力量的极端组织"
        },
        "growth": {
            "升级路线": "从炼气期开始,逐步突破",
            "关键节点": ["获得系统", "突破筑基", "宗门大比"]
        },
        "writing": {
            "文风": "轻松幽默,节奏明快",
            "视角": "第三人称"
        },
        "storyline": {
            "主线": "林凡获得系统,踏上修仙之路",
            "关键事件": ["入门测试", "宗门任务", "秘境探险"]
        },
        "market_analysis": {
            "目标读者": "18-30岁男性",
            "竞品分析": "类似《凡人修仙传》"
        }
    }
    
    # 创建优化器
    optimizer = PhaseOneOptimizer()
    
    # 测试不同平台
    platforms = ["fanqie", "qidian", "general"]
    
    for platform in platforms:
        print(f"\n{'='*40}")
        print(f"测试平台: {platform}")
        print(f"{'='*40}")
        
        try:
            result = optimizer.optimize(test_products, platform)
            
            print(f"\n✅ 优化完成!")
            print(f"\n总体评分: {result['overall_score']}/100")
            print(f"目标平台: {result['platform_name']}")
            print(f"\n各轮评分:")
            for round_name, round_data in result['rounds'].items():
                print(f"  - {round_name}: {round_data['score']}分")
                if 'summary' in round_data:
                    print(f"    {round_data['summary'][:60]}...")
            
            print(f"\n优先改进项:")
            if result.get('priority_actions'):
                for priority, actions in result['priority_actions'].items():
                    if actions:
                        print(f"  [{priority.upper()}]")
                        for action in actions[:3]:  # 只显示前3个
                            print(f"    - {action[:50]}...")
            
        except Exception as e:
            print(f"\n❌ 优化失败: {e}")
            import traceback
            traceback.print_exc()


def test_task_manager():
    """测试任务管理器"""
    print("\n" + "=" * 60)
    print("Task Manager 测试")
    print("=" * 60)
    
    # 创建任务
    task_id = task_manager.create_task("测试小说", "fanqie")
    print(f"\n✅ 创建任务: {task_id}")
    
    # 获取任务
    task = task_manager.get_task(task_id)
    print(f"✅ 获取任务: {task['title']} - {task['status']}")
    
    # 更新任务
    task_manager.update_task(task_id, status="running", progress=50)
    task = task_manager.get_task(task_id)
    print(f"✅ 更新任务: {task['status']} - {task['progress']}%")
    
    # 列出任务
    tasks = task_manager.list_tasks()
    print(f"✅ 列出任务: 共 {len(tasks)} 个任务")


def test_api_client():
    """测试API客户端(模拟)"""
    print("\n" + "=" * 60)
    print("API 客户端测试 (模拟)")
    print("=" * 60)
    
    # 这里可以添加实际的API测试
    print("\nℹ️ API测试需要在Flask应用上下文中运行")
    print("   请使用: flask test 或 pytest tests/test_phase_one_optimizer.py")


if __name__ == "__main__":
    test_optimizer()
    test_task_manager()
    test_api_client()
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)
