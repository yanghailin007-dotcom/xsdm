"""
测试故事线修复效果
1. 验证后端数据提取逻辑（special_events 和 chapter_range）
2. 验证期待感类型多样性
3. 验证章节范围标准化
"""

import json
import sys
from pathlib import Path
from collections import Counter

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_backend_data_extraction():
    """测试后端数据提取逻辑"""
    print("\n" + "="*60)
    print("测试1: 后端数据提取逻辑")
    print("="*60)
    
    # 导入必要的模块
    from web.api.phase_generation_api import ProductLoader
    from src.utils.logger import get_logger
    
    # 创建 logger 实例
    logger = get_logger(__name__)
    
    # 查找测试项目 - 优先使用有完整数据的项目
    project_dir = Path("小说项目")
    projects = [p for p in project_dir.iterdir() if p.is_dir()]
    
    if not projects:
        print("❌ 未找到任何项目")
        return False
    
    # 优先选择包含 plans 目录的项目
    test_project = None
    for project in projects:
        if (project / "plans").exists():
            test_project = project
            break
    
    # 如果没有找到，使用第一个项目
    if not test_project:
        test_project = projects[0]
    
    print(f"\n📁 测试项目: {test_project.name}")
    
    # 加载数据
    loader = ProductLoader(test_project.name, logger)
    products = loader.load_all_products()
    
    if not products['storyline']['complete']:
        print("❌ 故事线数据不完整")
        return False
    
    storyline = json.loads(products['storyline']['content'])
    major_events = storyline.get('major_events', [])
    
    print(f"\n✅ 成功加载 {len(major_events)} 个重大事件")
    
    # 检查中级事件
    total_medium_events = 0
    events_with_special_events = 0
    events_with_chapter_range = 0
    
    for event in major_events:
        if '_medium_events' in event:
            medium_events = event['_medium_events']
            total_medium_events += len(medium_events)
            
            for me in medium_events:
                # 检查是否有 special_events
                if 'special_events' in me and me['special_events']:
                    events_with_special_events += 1
                
                # 检查是否有 chapter_range
                if 'chapter_range' in me and me['chapter_range']:
                    events_with_chapter_range += 1
                
                # 检查是否有标准化的章节范围
                if '_chapter_range_normalized' in me:
                    print(f"  ✅ 标准化章节范围: {me['chapter_range']} -> {me['_chapter_range_normalized']}")
    
    print(f"\n📊 统计结果:")
    print(f"  - 中级事件总数: {total_medium_events}")
    print(f"  - 有特殊事件的中级事件: {events_with_special_events}")
    print(f"  - 有章节范围的中级事件: {events_with_chapter_range}")
    
    if total_medium_events > 0:
        print(f"\n✅ 后端数据提取测试通过！")
        return True
    else:
        print(f"\n⚠️ 警告: 未找到中级事件数据")
        return False

def test_expectation_type_diversity():
    """测试期待感类型多样性"""
    print("\n" + "="*60)
    print("测试2: 期待感类型多样性")
    print("="*60)
    
    from web.api.phase_generation_api import select_expectation_type
    from src.managers.ExpectationManager import ExpectationType
    
    # 创建测试事件
    test_events = [
        {"name": "击败魔尊", "main_goal": "击败魔尊", "emotional_intensity": "high"},
        {"name": "获得神器", "main_goal": "获得上古神器", "emotional_intensity": "medium"},
        {"name": "揭秘身世", "main_goal": "揭开身世之谜", "emotional_intensity": "low"},
        {"name": "打脸反派", "name": "打脸", "emotional_focus": "被误解", "emotional_intensity": "high"},
        {"name": "修炼功法", "main_goal": "修炼绝世功法", "emotional_intensity": "low"},
        {"name": "探索秘境", "main_goal": "探索神秘秘境", "emotional_intensity": "medium"},
    ]
    
    type_counts = Counter()
    
    print("\n📋 测试事件类型分配:")
    for event in test_events:
        exp_type = select_expectation_type(event)
        type_counts[exp_type] += 1
        
        type_name = {
            ExpectationType.SUPPRESSION_RELEASE: "压抑释放",
            ExpectationType.SHOWCASE: "展示橱窗",
            ExpectationType.MYSTERY_FORESHADOW: "伏笔揭秘",
            ExpectationType.EMOTIONAL_HOOK: "情绪钩子",
            ExpectationType.POWER_GAP: "实力差距",
            ExpectationType.NESTED_DOLL: "套娃期待"
        }.get(exp_type, exp_type)
        
        print(f"  - {event['name']}: {type_name}")
    
    print(f"\n📊 类型分布统计:")
    for exp_type, count in type_counts.items():
        type_name = {
            ExpectationType.SUPPRESSION_RELEASE: "压抑释放",
            ExpectationType.SHOWCASE: "展示橱窗",
            ExpectationType.MYSTERY_FORESHADOW: "伏笔揭秘",
            ExpectationType.EMOTIONAL_HOOK: "情绪钩子",
            ExpectationType.POWER_GAP: "实力差距",
            ExpectationType.NESTED_DOLL: "套娃期待"
        }.get(exp_type, exp_type)
        print(f"  - {type_name}: {count} 个")
    
    unique_types = len(type_counts)
    if unique_types >= 3:
        print(f"\n✅ 期待感类型多样性测试通过！({unique_types} 种不同类型)")
        return True
    else:
        print(f"\n⚠️ 警告: 期待感类型较少 ({unique_types} 种)")
        return False

def test_chapter_range_normalization():
    """测试章节范围标准化"""
    print("\n" + "="*60)
    print("测试3: 章节范围标准化")
    print("="*60)
    
    from web.api.phase_generation_api import normalize_chapter_range
    
    test_cases = [
        ("101-103", "101-103章"),
        ("101-103章", "101-103章"),
        ("第1章", "第1章"),
        ("第3-4章", "第3-4章"),
        ("110", "第110章"),
        ("", ""),
    ]
    
    all_passed = True
    
    print("\n📋 标准化测试:")
    for input_val, expected in test_cases:
        result = normalize_chapter_range(input_val)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{input_val}' -> '{result}' (期望: '{expected}')")
        if result != expected:
            all_passed = False
    
    if all_passed:
        print(f"\n✅ 章节范围标准化测试通过！")
        return True
    else:
        print(f"\n❌ 部分测试失败")
        return False

def main():
    """主函数"""
    import sys
    import io
    # 设置标准输出为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("🔍 故事线修复效果测试")
    print("="*60)
    
    results = []
    
    # 测试1: 后端数据提取
    try:
        result = test_backend_data_extraction()
        results.append(("后端数据提取", result))
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        results.append(("后端数据提取", False))
    
    # 测试2: 期待感类型多样性
    try:
        result = test_expectation_type_diversity()
        results.append(("期待感类型多样性", result))
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}")
        results.append(("期待感类型多样性", False))
    
    # 测试3: 章节范围标准化
    try:
        result = test_chapter_range_normalization()
        results.append(("章节范围标准化", result))
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}")
        results.append(("章节范围标准化", False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())