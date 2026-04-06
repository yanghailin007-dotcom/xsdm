"""
测试 StagePlanManager 重构后的功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def test_imports():
    """测试所有模块是否能正确导入"""
    print("=" * 60)
    print("测试 1: 导入所有重构模块")
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
        print("✅ 所有 stage_plan 模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_component_initialization():
    """测试组件初始化"""
    print("\n" + "=" * 60)
    print("测试 2: 组件初始化")
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
        print("✅ EventDecomposer 初始化成功")
        
        plan_validator = PlanValidator()
        print("✅ PlanValidator 初始化成功")
        
        plan_persistence = StagePlanPersistence(
            Path("./小说项目"),
            lambda: {"novel_title": "test"}
        )
        print("✅ StagePlanPersistence 初始化成功")
        
        event_optimizer = EventOptimizer(api_client)
        print("✅ EventOptimizer 初始化成功")
        
        major_event_generator = MajorEventGenerator(api_client)
        print("✅ MajorEventGenerator 初始化成功")
        
        scene_assembler = SceneAssembler(api_client)
        print("✅ SceneAssembler 初始化成功")
        
        return True
    except Exception as e:
        print(f"❌ 组件初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refactored_manager():
    """测试重构后的 StagePlanManager"""
    print("\n" + "=" * 60)
    print("测试 3: 重构后的 StagePlanManager")
    print("=" * 60)
    
    try:
        # 使用重构版本
        from src.managers.StagePlanManager_refactored import StagePlanManager
        print("✅ StagePlanManager_refactored 导入成功")
        
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
        print("✅ StagePlanManager 初始化成功")
        
        # 检查组件是否正确初始化
        assert hasattr(manager, 'event_decomposer'), "缺少 event_decomposer"
        assert hasattr(manager, 'plan_validator'), "缺少 plan_validator"
        assert hasattr(manager, 'plan_persistence'), "缺少 plan_persistence"
        assert hasattr(manager, 'event_optimizer'), "缺少 event_optimizer"
        assert hasattr(manager, 'major_event_generator'), "缺少 major_event_generator"
        assert hasattr(manager, 'scene_assembler'), "缺少 scene_assembler"
        print("✅ 所有组件正确初始化")
        
        # 测试计算阶段边界
        boundaries = manager.calculate_stage_boundaries(100)
        assert 'opening_end' in boundaries
        assert 'development_start' in boundaries
        assert 'climax_start' in boundaries
        assert 'ending_start' in boundaries
        print(f"✅ 阶段边界计算成功: {boundaries}")
        
        # 测试静态方法
        result = StagePlanManager.is_chapter_in_range(5, "1-10")
        assert result == True, "章节范围检查失败"
        print("✅ 静态方法 is_chapter_in_range 测试成功")
        
        return True
    except Exception as e:
        print(f"❌ StagePlanManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 60)
    print("测试 4: 向后兼容性")
    print("=" * 60)
    
    try:
        # 测试原始类仍然可用
        from src.managers.StagePlanManager import StagePlanManager as OldStagePlanManager
        print("✅ 原始 StagePlanManager 仍然可用")
        
        # 测试新版本
        from src.managers.StagePlanManager_refactored import StagePlanManager as NewStagePlanManager
        print("✅ 新版本 StagePlanManager_refactored 可用")
        
        return True
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n[测试] 开始测试 StagePlanManager 重构...")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("导入测试", test_imports()))
    results.append(("组件初始化", test_component_initialization()))
    results.append(("重构管理器", test_refactored_manager()))
    results.append(("向后兼容性", test_backward_compatibility()))
    
    # 打印结果
    print("\n" + "=" * 60)
    print("[结果] 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[通过]" if result else "[失败]"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n[成功] 所有测试通过！重构成功完成。")
        return 0
    else:
        print(f"\n[警告] 有 {failed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())