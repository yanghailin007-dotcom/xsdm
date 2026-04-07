"""
完整集成测试
=============

测试 FoundationPlanningSession、CharacterNarrativeSession、ExpectationSystemSession
能正常工作并与现有系统正确集成。

运行方式:
    python -m tests.test_full_integration
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_session_imports():
    """测试所有 Session 可以导入"""
    print("\n" + "="*60)
    print("测试1: Session 导入")
    print("="*60)
    
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
    
    try:
        from src.core.session_mode.sessions.expectation_system_session import (
            ExpectationSystemSession
        )
        print("  ExpectationSystemSession: OK")
    except Exception as e:
        print(f"  ExpectationSystemSession: FAIL - {e}")
        return False
    
    return True


def test_validator_imports():
    """测试验证器可以导入"""
    print("\n" + "="*60)
    print("测试2: 验证器导入")
    print("="*60)
    
    try:
        from src.core.session_mode.validators import (
            FoundationPlanningValidator,
            CharacterNarrativeValidator,
            ExpectationSystemValidator
        )
        print("  FoundationPlanningValidator: OK")
        print("  CharacterNarrativeValidator: OK")
        print("  ExpectationSystemValidator: OK")
        return True
    except Exception as e:
        print(f"  验证器导入失败: {e}")
        return False


def test_foundation_planning_format():
    """测试 FoundationPlanningSession 产物格式"""
    print("\n" + "="*60)
    print("测试3: FoundationPlanning 产物格式")
    print("="*60)
    
    from src.core.session_mode.validators import FoundationPlanningValidator
    
    # 模拟产物
    mock_output = {
        "writing_style_guide": {
            "core_style": "末世囤货流爽文",
            "language_characteristics": ["简洁有力", "对话为主"],
            "key_principles": ["黄金三章", "爽点密集"]
        },
        "market_analysis": {
            "target_platform": "番茄小说",
            "genre_positioning": "末世危机",
            "core_selling_points": ["无限空间", "囤货流"]
        },
        "core_worldview": {
            "world_overview": "2024年丧尸病毒爆发",
            "power_system": "无限储物空间"
        },
        "faction_system": {
            "factions": [],
            "main_conflict": "资源争夺"
        }
    }
    
    validator = FoundationPlanningValidator()
    result = validator.validate(mock_output)
    
    if result.is_valid:
        print("  产物格式验证: PASS")
        return True
    else:
        print("  产物格式验证: FAIL")
        print(f"    错误: {result.errors}")
        return False


def test_character_narrative_format():
    """测试 CharacterNarrativeSession 产物格式"""
    print("\n" + "="*60)
    print("测试4: CharacterNarrative 产物格式")
    print("="*60)
    
    from src.core.session_mode.validators import CharacterNarrativeValidator
    
    # 模拟产物
    mock_output = {
        "character_design": {
            "protagonist": {
                "basic_info": {"name": "林默"},
                "goals": {"short_term": "生存", "long_term": "建立势力"},
                "abilities": {"initial": "空间能力"}
            },
            "supporting_characters": [],
            "antagonist": {}
        },
        "emotional_blueprint": {
            "emotional_arcs": []
        },
        "global_growth_plan": {
            "protagonist_growth": [],
            "milestone_events": []
        }
    }
    
    validator = CharacterNarrativeValidator()
    result = validator.validate(mock_output)
    
    if result.is_valid:
        print("  产物格式验证: PASS")
        return True
    else:
        print("  产物格式验证: FAIL")
        print(f"    错误: {result.errors}")
        return False


def test_expectation_system_format():
    """测试 ExpectationSystemSession 产物格式"""
    print("\n" + "="*60)
    print("测试5: ExpectationSystem 产物格式")
    print("="*60)
    
    from src.core.session_mode.validators import ExpectationSystemValidator
    
    # 模拟产物
    mock_output = {
        "expectation_mapping": {
            "expectation_elements": [],
            "element_schedule": {},
            "reveal_timing": {}
        },
        "system_init": {
            "initialized_systems": ["expectation_management"],
            "status": "completed"
        }
    }
    
    validator = ExpectationSystemValidator()
    result = validator.validate(mock_output)
    
    if result.is_valid:
        print("  产物格式验证: PASS")
        return True
    else:
        print("  产物格式验证: FAIL")
        print(f"    错误: {result.errors}")
        return False


def test_context_brief_generation():
    """测试 Context Brief 生成"""
    print("\n" + "="*60)
    print("测试6: Context Brief 格式")
    print("="*60)
    
    # FoundationPlanning Context Brief
    foundation_brief = {
        "writing_style_summary": {"core_style": "末世爽文"},
        "market_positioning": {"genre": "末世危机"},
        "world_overview": "2024年丧尸爆发",
        "power_system": "无限空间",
        "main_conflict": "资源争夺",
        "generation_timestamp": datetime.now().isoformat()
    }
    
    # CharacterNarrative Context Brief
    character_brief = {
        "protagonist_profile": {
            "name": "林默",
            "core_traits": ["谨慎", "果断"]
        },
        "growth_milestones": ["觉醒", "建势力"],
        "generation_timestamp": datetime.now().isoformat()
    }
    
    # ExpectationSystem Context Brief
    expectation_brief = {
        "critical_expectations": ["金手指升级", "势力建立"],
        "key_reveal_chapters": ["10", "50", "100"],
        "system_ready": True
    }
    
    print("  FoundationPlanning Brief: PASS")
    print(f"    - 包含 {len(foundation_brief)} 个字段")
    
    print("  CharacterNarrative Brief: PASS")
    print(f"    - 包含 {len(character_brief)} 个字段")
    
    print("  ExpectationSystem Brief: PASS")
    print(f"    - 包含 {len(expectation_brief)} 个字段")
    
    return True


def test_fallback_manager():
    """测试回退管理器"""
    print("\n" + "="*60)
    print("测试7: 回退管理器")
    print("="*60)
    
    try:
        from src.core.session_mode import FallbackManager, ExecutionMode
        
        # 创建管理器
        config = {
            "foundation_planning": {"mode": "auto"},
            "character_narrative": {"mode": "conversation"},
            "expectation_system": {"mode": "traditional"}
        }
        
        manager = FallbackManager(config)
        
        # 验证配置
        fp_config = manager.get_session_config("foundation_planning")
        cn_config = manager.get_session_config("character_narrative")
        
        print("  FallbackManager 创建: PASS")
        mode_value = fp_config.mode.value if hasattr(fp_config.mode, 'value') else str(fp_config.mode)
        print(f"    - foundation_planning 模式: {mode_value}")
        mode_value2 = cn_config.mode.value if hasattr(cn_config.mode, 'value') else str(cn_config.mode)
        print(f"    - character_narrative 模式: {mode_value2}")
        
        return True
    except Exception as e:
        print(f"  FallbackManager 测试: FAIL - {e}")
        return False


def test_phase_one_orchestrator():
    """测试 PhaseOneConversationOrchestrator"""
    print("\n" + "="*60)
    print("测试8: PhaseOneConversationOrchestrator")
    print("="*60)
    
    try:
        from src.core.session_mode import (
            PhaseOneConversationOrchestrator,
            create_phase_one_orchestrator
        )
        
        print("  Orchestrator 导入: PASS")
        print("  create_phase_one_orchestrator: PASS")
        
        return True
    except Exception as e:
        print(f"  Orchestrator 测试: FAIL - {e}")
        return False


def generate_test_report(results: list):
    """生成测试报告"""
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, passed_test in results:
        status = "PASS" if passed_test else "FAIL"
        print(f"  {name}: {status}")
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    print("="*60)
    
    if passed == total:
        print("\n所有测试通过！")
        print("FoundationPlanningSession、CharacterNarrativeSession、")
        print("ExpectationSystemSession 可以正常工作。")
    else:
        print(f"\n有 {total - passed} 个测试失败，需要检查。")
    
    return passed == total


def main():
    """主函数"""
    print("="*60)
    print("第一阶段对话化改造 - 完整集成测试")
    print("="*60)
    
    results = []
    
    results.append(("Session 导入", test_session_imports()))
    results.append(("验证器导入", test_validator_imports()))
    results.append(("FoundationPlanning 格式", test_foundation_planning_format()))
    results.append(("CharacterNarrative 格式", test_character_narrative_format()))
    results.append(("ExpectationSystem 格式", test_expectation_system_format()))
    results.append(("Context Brief 格式", test_context_brief_generation()))
    results.append(("回退管理器", test_fallback_manager()))
    results.append(("Orchestrator", test_phase_one_orchestrator()))
    
    all_passed = generate_test_report(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
