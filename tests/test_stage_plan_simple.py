"""
测试 StagePlanManager 重构后的功能 - 简化版
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def test_imports():
    """测试所有模块是否能正确导入"""
    print("=" * 60)
    print("Test 1: Import all refactored modules")
    print("=" * 60)
    
    try:
        from src.managers.stage_plan import (
            EventDecomposer,
            PlanValidator,
            StagePlanPersistence,
            EventOptimizer,
            MajorEventGenerator,
            SceneAssembler
        )
        print("[OK] All stage_plan modules imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_component_initialization():
    """测试组件初始化"""
    print("\n" + "=" * 60)
    print("Test 2: Component initialization")
    print("=" * 60)
    
    try:
        from src.managers.stage_plan import (
            EventDecomposer,
            PlanValidator,
            StagePlanPersistence,
            EventOptimizer,
            MajorEventGenerator,
            SceneAssembler
        )
        
        # 模拟 API 客户端
        class MockAPIClient:
            def generate_content_with_retry(self, *args, **kwargs):
                return {}
        
        api_client = MockAPIClient()
        
        # 测试各个组件初始化
        event_decomposer = EventDecomposer(api_client)
        print("[OK] EventDecomposer initialized")
        
        plan_validator = PlanValidator()
        print("[OK] PlanValidator initialized")
        
        plan_persistence = StagePlanPersistence(
            Path("./novel_projects"),
            lambda: {"novel_title": "test"}
        )
        print("[OK] StagePlanPersistence initialized")
        
        event_optimizer = EventOptimizer(api_client)
        print("[OK] EventOptimizer initialized")
        
        major_event_generator = MajorEventGenerator(api_client)
        print("[OK] MajorEventGenerator initialized")
        
        scene_assembler = SceneAssembler(api_client)
        print("[OK] SceneAssembler initialized")
        
        return True
    except Exception as e:
        print(f"[FAIL] Component initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refactored_manager():
    """测试重构后的 StagePlanManager"""
    print("\n" + "=" * 60)
    print("Test 3: Refactored StagePlanManager")
    print("=" * 60)
    
    try:
        # 使用重构版本
        from src.managers.StagePlanManager_refactored import StagePlanManager
        print("[OK] StagePlanManager_refactored imported")
        
        # 模拟生成器
        class MockGenerator:
            def __init__(self):
                self.novel_data = {
                    "novel_title": "test_novel",
                    "novel_synopsis": "test synopsis",
                    "overall_stage_plans": {},
                    "emotional_blueprint": {},
                    "global_growth_plan": {}
                }
                self.api_client = self.MockAPIClient()
                self.emotional_plan_manager = self.MockEmotionalManager()
            
            class MockAPIClient:
                def generate_content_with_retry(self, *args, **kwargs):
                    return {}
            
            class MockEmotionalManager:
                def generate_stage_emotional_plan(self, *args, **kwargs):
                    return {"main_emotional_arc": "test arc"}
        
        # 初始化管理器
        manager = StagePlanManager(MockGenerator())
        print("[OK] StagePlanManager initialized")
        
        # 检查组件是否正确初始化
        assert hasattr(manager, 'event_decomposer'), "Missing event_decomposer"
        assert hasattr(manager, 'plan_validator'), "Missing plan_validator"
        assert hasattr(manager, 'plan_persistence'), "Missing plan_persistence"
        assert hasattr(manager, 'event_optimizer'), "Missing event_optimizer"
        assert hasattr(manager, 'major_event_generator'), "Missing major_event_generator"
        assert hasattr(manager, 'scene_assembler'), "Missing scene_assembler"
        print("[OK] All components initialized correctly")
        
        # 测试计算阶段边界
        boundaries = manager.calculate_stage_boundaries(100)
        assert 'opening_end' in boundaries
        assert 'development_start' in boundaries
        assert 'climax_start' in boundaries
        assert 'ending_start' in boundaries
        print(f"[OK] Stage boundaries calculated: {boundaries}")
        
        # 测试静态方法
        result = StagePlanManager.is_chapter_in_range(5, "1-10")
        assert result == True, "Chapter range check failed"
        print("[OK] Static method is_chapter_in_range works")
        
        return True
    except Exception as e:
        print(f"[FAIL] StagePlanManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 60)
    print("Test 4: Backward compatibility")
    print("=" * 60)
    
    try:
        # 测试原始类仍然可用
        from src.managers.StagePlanManager import StagePlanManager as OldStagePlanManager
        print("[OK] Original StagePlanManager still available")
        
        # 测试新版本
        from src.managers.StagePlanManager_refactored import StagePlanManager as NewStagePlanManager
        print("[OK] New StagePlanManager_refactored available")
        
        return True
    except Exception as e:
        print(f"[FAIL] Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n[TEST] Starting StagePlanManager refactoring tests...")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("Import Test", test_imports()))
    results.append(("Component Init", test_component_initialization()))
    results.append(("Refactored Manager", test_refactored_manager()))
    results.append(("Backward Compat", test_backward_compatibility()))
    
    # 打印结果
    print("\n" + "=" * 60)
    print("[RESULTS] Test Summary")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed! Refactoring completed successfully.")
        return 0
    else:
        print(f"\n[WARNING] {failed} test(s) failed, please check.")
        return 1


if __name__ == "__main__":
    sys.exit(main())