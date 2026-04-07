"""
Session 集成测试
================

验证 FoundationPlanningSession 和 CharacterNarrativeSession 可以正确导入和使用
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """测试所有 Session 可以正确导入"""
    print("测试 Session 导入...")
    
    try:
        from src.core.session_mode.sessions.foundation_planning_session import (
            FoundationPlanningSession
        )
        print("  FoundationPlanningSession: OK")
    except Exception as e:
        print(f"  FoundationPlanningSession: FAIL - {e}")
        return False
    
    try:
        from src.core.session_mode.sessions.character_narrative_session import (
            CharacterNarrativeSession
        )
        print("  CharacterNarrativeSession: OK")
    except Exception as e:
        print(f"  CharacterNarrativeSession: FAIL - {e}")
        return False
    
    return True


def test_validators():
    """测试验证器可以正常工作"""
    print("\n测试验证器...")
    
    from src.core.session_mode.validators import (
        FoundationPlanningValidator,
        CharacterNarrativeValidator
    )
    
    # 测试 FoundationPlanningValidator
    foundation_data = {
        "writing_style_guide": {"core_style": "test", "language_characteristics": [], "key_principles": []},
        "market_analysis": {"target_platform": "test", "genre_positioning": "test", "core_selling_points": []},
        "core_worldview": {"world_overview": "test", "power_system": "test"},
        "faction_system": {"factions": [], "main_conflict": "test"}
    }
    
    validator1 = FoundationPlanningValidator()
    result1 = validator1.validate(foundation_data)
    print(f"  FoundationPlanningValidator: {'OK' if result1.is_valid else 'FAIL'}")
    
    # 测试 CharacterNarrativeValidator
    character_data = {
        "character_design": {"protagonist": {"basic_info": {"name": "test"}, "goals": {}, "abilities": {}}},
        "emotional_blueprint": {"emotional_arcs": []},
        "global_growth_plan": {"protagonist_growth": [], "milestone_events": []}
    }
    
    validator2 = CharacterNarrativeValidator()
    result2 = validator2.validate(character_data)
    print(f"  CharacterNarrativeValidator: {'OK' if result2.is_valid else 'FAIL'}")
    
    return result1.is_valid and result2.is_valid


def main():
    print("="*60)
    print("Session 集成测试")
    print("="*60)
    
    results = []
    results.append(("导入测试", test_imports()))
    results.append(("验证器测试", test_validators()))
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("所有测试通过")
        print("FoundationPlanningSession 和 CharacterNarrativeSession")
        print("可以正常工作")
    else:
        print("部分测试失败")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
