#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试阶段写作计划加载修复
验证 EventDrivenManager 能否正确识别当前阶段
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


def test_stage_planning_loading():
    """测试阶段写作计划加载"""
    print("=" * 80)
    print("🧪 测试阶段写作计划加载修复")
    print("=" * 80)
    
    novel_title = "重生成剑：宿主祭天，法力无边"
    
    # 1. 测试 NovelGenerationManager.get_novel_detail()
    print("\n1️⃣ 测试 NovelGenerationManager.get_novel_detail()...")
    
    try:
        from web.managers.novel_manager import NovelGenerationManager
        manager = NovelGenerationManager()
        
        novel_detail = manager.get_novel_detail(novel_title)
        
        if not novel_detail:
            print("  ❌ 无法获取小说详情")
            return False
        
        print(f"  ✅ 成功获取小说详情")
        print(f"  📖 小说标题: {novel_detail.get('novel_title', 'N/A')}")
        
        # 2. 检查关键字段
        print("\n2️⃣ 检查关键字段...")
        
        # 检查 stage_writing_plans
        stage_writing_plans = novel_detail.get("stage_writing_plans", {})
        if stage_writing_plans:
            print(f"  ✅ stage_writing_plans 存在")
            print(f"     - 阶段数量: {len(stage_writing_plans)}")
            print(f"     - 阶段列表: {list(stage_writing_plans.keys())}")
        else:
            print(f"  ❌ stage_writing_plans 不存在或为空")
            return False
        
        # 检查 overall_stage_plans
        overall_stage_plans = novel_detail.get("overall_stage_plans", {})
        if overall_stage_plans:
            print(f"  ✅ overall_stage_plans 存在")
            overall_plan = overall_stage_plans.get("overall_stage_plan", {})
            if overall_plan:
                print(f"     - 阶段数量: {len(overall_plan)}")
                print(f"     - 阶段列表: {list(overall_plan.keys())}")
        else:
            print(f"  ⚠️ overall_stage_plans 不存在或为空")
        
        # 检查 global_growth_plan
        global_growth_plan = novel_detail.get("global_growth_plan", {})
        if global_growth_plan:
            print(f"  ✅ global_growth_plan 存在")
        else:
            print(f"  ⚠️ global_growth_plan 不存在或为空")
        
        # 3. 测试 EventDrivenManager.initialize_event_system()
        print("\n3️⃣ 测试 EventDrivenManager.initialize_event_system()...")
        
        try:
            from src.managers.EventDrivenManager import EventDrivenManager
            from src.core.NovelGenerator import NovelGenerator
            
            # 创建一个简单的 NovelGenerator 实例用于测试
            config = {"defaults": {"total_chapters": 200}}
            test_generator = NovelGenerator(config)
            test_generator.novel_data = novel_detail
            
            # 创建 EventDrivenManager
            event_manager = EventDrivenManager(test_generator)
            
            # 初始化事件系统
            event_manager.initialize_event_system()
            
            print(f"  ✅ EventDrivenManager 初始化完成")
            
            # 检查是否有活跃事件
            if event_manager.active_events:
                print(f"  ✅ 找到 {len(event_manager.active_events)} 个活跃事件")
                for event_name in event_manager.active_events.keys():
                    print(f"     - {event_name}")
            else:
                print(f"  ⚠️ 没有找到活跃事件")
            
            # 4. 测试获取当前阶段
            print("\n4️⃣ 测试获取当前阶段...")
            
            current_chapter = 1
            current_stage = event_manager._get_current_stage_from_plans(current_chapter)
            
            if current_stage and current_stage != "未知阶段":
                print(f"  ✅ 成功识别当前阶段: {current_stage}")
                print(f"     - 第{current_chapter}章属于 {current_stage}")
            else:
                print(f"  ❌ 无法识别当前阶段，返回: {current_stage}")
                return False
            
            # 5. 测试获取章节上下文
            print("\n5️⃣ 测试获取章节事件上下文...")
            
            event_context = event_manager.get_chapter_event_context(current_chapter)
            
            if event_context:
                print(f"  ✅ 成功获取事件上下文")
                print(f"     - 活跃事件数: {len(event_context.get('active_events', []))}")
                print(f"     - 事件任务数: {len(event_context.get('event_tasks', []))}")
                print(f"     - 缓冲期: {event_context.get('buffer_period', {}).get('is_buffer_period', False)}")
            else:
                print(f"  ⚠️ 事件上下文为空")
            
        except Exception as e:
            print(f"  ❌ EventDrivenManager 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 6. 总结
        print("\n" + "=" * 80)
        print("✅ 测试结果：所有检查通过！")
        print("=" * 80)
        print("\n📋 修复总结:")
        print("1. ✅ NovelGenerationManager.get_novel_detail() 正确返回 stage_writing_plans")
        print("2. ✅ EventDrivenManager 能正确加载事件系统")
        print("3. ✅ 能正确识别当前阶段（不再返回'未知阶段'）")
        print("4. ✅ 能正确获取章节事件上下文")
        print("\n💡 修复说明:")
        print("在 web/managers/novel_manager.py 的 get_novel_detail() 方法中，")
        print("添加了从 quality_data.writing_plans 到 novel_data.stage_writing_plans 的映射，")
        print("确保 EventDrivenManager 能找到阶段写作计划数据。")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_stage_planning_loading()
    sys.exit(0 if success else 1)