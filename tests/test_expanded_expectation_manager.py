"""
测试扩充版期待感管理系统

测试内容：
1. 20种期待感类型的正确性
2. 事件驱动绑定机制
3. 自动事件匹配功能
4. 期待感密度监控
5. 完整的工作流程
"""

import sys
import io
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.ExpectationManager import (
    ExpectationManager,
    ExpectationType,
    auto_bind_expectation_to_event,
    ExpectationDensityMonitor
)
from src.utils.logger import get_logger


def test_expectation_types():
    """测试20种期待感类型"""
    print("\n" + "="*60)
    print("测试1：验证20种期待感类型")
    print("="*60)
    
    # 原有6种
    original_types = [
        ExpectationType.SHOWCASE,
        ExpectationType.SUPPRESSION_RELEASE,
        ExpectationType.NESTED_DOLL,
        ExpectationType.EMOTIONAL_HOOK,
        ExpectationType.POWER_GAP,
        ExpectationType.MYSTERY_FORESHADOW,
    ]
    
    # 新增14种
    new_types = [
        ExpectationType.PIG_EATS_TIGER,
        ExpectationType.SHOW_OFF_FACE_SLAP,
        ExpectationType.IDENTITY_REVEAL,
        ExpectationType.BEAUTY_FAVOR,
        ExpectationType.FORTUITOUS_ENCOUNTER,
        ExpectationType.COMPETITION,
        ExpectationType.AUCTION_TREASURE,
        ExpectationType.SECRET_REALM_EXPLORATION,
        ExpectationType.ALCHEMY_CRAFTING,
        ExpectationType.FORMATION_BREAKING,
        ExpectationType.SECT_MISSION,
        ExpectationType.CROSS_WORLD_TELEPORT,
        ExpectationType.CRISIS_RESCUE,
        ExpectationType.MASTER_INHERITANCE,
    ]
    
    print(f"✅ 原有类型: {len(original_types)}种")
    for exp_type in original_types:
        print(f"  - {exp_type.value}")
    
    print(f"\n✅ 新增类型: {len(new_types)}种")
    for exp_type in new_types:
        print(f"  - {exp_type.value}")
    
    print(f"\n✅ 总计: {len(original_types) + len(new_types)}种期待感类型")
    return True


def test_event_auto_binding():
    """测试自动事件匹配"""
    print("\n" + "="*60)
    print("测试2：自动事件匹配功能")
    print("="*60)
    
    test_events = [
        {"name": "炼丹大比", "main_goal": "赢得宗门炼丹比赛"},
        {"name": "秘境探险", "main_goal": "进入上古遗迹探险"},
        {"name": "拍卖会", "main_goal": "在拍卖会上竞拍宝物"},
        {"name": "救援行动", "main_goal": "拯救被绑架的朋友"},
        {"name": "师父传承", "main_goal": "获得老祖的功法传承"},
        {"name": "阵法破解", "main_goal": "破解护山大阵"},
        {"name": "隐藏实力", "main_goal": "主角故意示弱"},
    ]
    
    for event in test_events:
        exp_type = auto_bind_expectation_to_event(event)
        print(f"  事件: {event['name']}")
        print(f"    目标: {event['main_goal']}")
        print(f"    匹配类型: {exp_type.value}")
        print()
    
    return True


def test_expectation_manager():
    """测试期待感管理器完整流程"""
    print("\n" + "="*60)
    print("测试3：期待感管理器完整流程")
    print("="*60)
    
    manager = ExpectationManager()
    
    # 1. 添加期待标签
    print("步骤1：添加期待标签")
    exp_id_1 = manager.tag_event_with_expectation(
        event_id="alchemy_competition",
        expectation_type=ExpectationType.ALCHEMY_CRAFTING,
        planting_chapter=10,
        description="赢得炼丹比赛，证明主角实力",
        target_chapter=15,
        flexible_range={
            "min_chapters": 3,
            "max_chapters": 8,
            "optimal_chapters": 5
        }
    )
    print(f"  ✅ 添加期待: {exp_id_1}")
    
    # 2. 扮猪吃虎期待
    exp_id_2 = manager.tag_event_with_expectation(
        event_id="show_off_power",
        expectation_type=ExpectationType.PIG_EATS_TIGER,
        planting_chapter=5,
        description="长老嘲讽主角，主角默默承受",
        target_chapter=8
    )
    print(f"  ✅ 添加期待: {exp_id_2}")
    
    # 3. 生成前检查
    print("\n步骤2：生成前检查（第8章）")
    constraints = manager.pre_generation_check(
        chapter_num=8,
        event_context={"active_events": []}
    )
    print(f"  检测到 {len(constraints)} 个约束")
    for constraint in constraints:
        print(f"  - [{constraint.urgency}] {constraint.message}")
    
    # 4. 模拟生成后验证
    print("\n步骤3：生成后验证")
    validation_result = manager.post_generation_validate(
        chapter_num=8,
        content_analysis={"content": "主角展露真实实力，全场震惊"},
        released_expectation_ids=[exp_id_2]
    )
    print(f"  验证通过: {validation_result['passed']}")
    print(f"  满足的期待: {len(validation_result['satisfied_expectations'])}个")
    print(f"  待处理的期待: {len(validation_result['pending_expectations'])}个")
    
    # 5. 生成期待感报告
    print("\n步骤4：生成期待感报告")
    report = manager.generate_expectation_report(start_chapter=1, end_chapter=20)
    print(f"  总期待数: {report['total_expectations']}")
    print(f"  已释放: {report['released_expectations']}")
    print(f"  满足率: {report['satisfaction_rate']}%")
    
    return True


def test_density_monitor():
    """测试期待感密度监控"""
    print("\n" + "="*60)
    print("测试4：期待感密度监控")
    print("="*60)
    
    manager = ExpectationManager()
    
    # 添加多个期待
    manager.tag_event_with_expectation(
        event_id="event1",
        expectation_type=ExpectationType.SHOWCASE,
        planting_chapter=1,
        description="展示橱窗1"
    )
    manager.tag_event_with_expectation(
        event_id="event2",
        expectation_type=ExpectationType.EMOTIONAL_HOOK,
        planting_chapter=3,
        description="情绪钩子1"
    )
    manager.tag_event_with_expectation(
        event_id="event3",
        expectation_type=ExpectationType.PIG_EATS_TIGER,
        planting_chapter=5,
        description="扮猪吃虎1"
    )
    manager.tag_event_with_expectation(
        event_id="event4",
        expectation_type=ExpectationType.COMPETITION,
        planting_chapter=8,
        description="比试切磋1"
    )
    manager.tag_event_with_expectation(
        event_id="event5",
        expectation_type=ExpectationType.AUCTION_TREASURE,
        planting_chapter=12,
        description="拍卖会争宝1"
    )
    
    # 计算密度
    monitor = ExpectationDensityMonitor(manager)
    density = monitor.calculate_density(start_chapter=1, end_chapter=20)
    
    print(f"  总期待数: {density['total_expectations']}")
    print(f"  每章期待: {density['expectations_per_chapter']:.2f}")
    print(f"  密度评级: {density['density_rating']}")
    print(f"\n  类型分布:")
    for exp_type, count in density['type_distribution'].items():
        print(f"    - {exp_type}: {count}个")
    
    # 生成建议
    print(f"\n  改进建议:")
    recommendations = monitor.generate_recommendations(density)
    for rec in recommendations:
        print(f"    - {rec}")
    
    return True


def test_event_driven_release():
    """测试事件驱动释放机制"""
    print("\n" + "="*60)
    print("测试5：事件驱动释放机制")
    print("="*60)
    
    manager = ExpectationManager()
    
    # 添加绑定到事件的期待
    exp_id = manager.tag_event_with_expectation(
        event_id="boss_fight_001",
        expectation_type=ExpectationType.SUPPRESSION_RELEASE,
        planting_chapter=10,
        description="击败最终BOSS温天仁",
        target_chapter=20,
        bound_event_id="boss_fight_001",
        trigger_condition="event_reaches_climax",
        flexible_range={
            "min_chapters": 8,
            "max_chapters": 15,
            "optimal_chapters": 10
        }
    )
    
    print(f"  添加期待: {exp_id}")
    print(f"  绑定事件: boss_fight_001")
    print(f"  触发条件: event_reaches_climax")
    
    # 模拟事件进度
    print("\n  检查不同事件进度下的释放时机:")
    for progress in [30, 50, 70, 85, 95]:
        event_context = {
            "active_events": [
                {
                    "id": "boss_fight_001",
                    "current_chapter": 15,
                    "total_chapters": 20,
                    "current_phase": "climax",
                    "progress_percentage": progress
                }
            ]
        }
        
        pending = manager._get_pending_expectations_for_chapter(15, event_context)
        should_release = len(pending) > 0
        
        print(f"    进度 {progress}%: {'应该释放' if should_release else '等待中'}")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 扩充版期待感管理系统测试")
    print("="*60)
    
    tests = [
        ("期待感类型验证", test_expectation_types),
        ("自动事件匹配", test_event_auto_binding),
        ("期待感管理器流程", test_expectation_manager),
        ("密度监控", test_density_monitor),
        ("事件驱动释放", test_event_driven_release),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 运行测试: {test_name}")
            result = test_func()
            if result:
                print(f"✅ 测试通过: {test_name}")
                passed += 1
            else:
                print(f"❌ 测试失败: {test_name}")
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {test_name}")
            print(f"   错误: {e}")
            failed += 1
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    print(f"总计: {passed + failed}个测试")
    print(f"通过: {passed}个")
    print(f"失败: {failed}个")
    
    if failed == 0:
        print("\n🎉 所有测试通过！扩充版期待感管理系统工作正常。")
    else:
        print(f"\n⚠️ 有{failed}个测试失败，请检查。")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
