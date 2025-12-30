"""
测试重构后的NovelGenerator模块
验证PhaseGenerator和ResumeManager是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试 1: 模块导入")
    print("=" * 60)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        print("✅ NovelGenerator 导入成功")
    except Exception as e:
        print(f"❌ NovelGenerator 导入失败: {e}")
        return False
    
    try:
        from src.core.PhaseGenerator import PhaseGenerator
        print("✅ PhaseGenerator 导入成功")
    except Exception as e:
        print(f"❌ PhaseGenerator 导入失败: {e}")
        return False
    
    try:
        from src.core.ResumeManager import ResumeManager
        print("✅ ResumeManager 导入成功")
    except Exception as e:
        print(f"❌ ResumeManager 导入失败: {e}")
        return False
    
    print("\n✅ 所有模块导入成功\n")
    return True


def test_initialization():
    """测试NovelGenerator初始化"""
    print("=" * 60)
    print("测试 2: NovelGenerator 初始化")
    print("=" * 60)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        
        # 创建一个简单的配置
        config = {
            "api": {
                "provider": "mock",
                "model": "mock-model"
            },
            "defaults": {
                "total_chapters": 10
            }
        }
        
        # 初始化NovelGenerator
        generator = NovelGenerator(config)
        print("✅ NovelGenerator 初始化成功")
        
        # 检查是否包含phase_generator和resume_manager
        if hasattr(generator, 'phase_generator'):
            print("✅ phase_generator 属性存在")
        else:
            print("❌ phase_generator 属性不存在")
            return False
        
        if hasattr(generator, 'resume_manager'):
            print("✅ resume_manager 属性存在")
        else:
            print("❌ resume_manager 属性不存在")
            return False
        
        # 检查类型
        from src.core.PhaseGenerator import PhaseGenerator
        from src.core.ResumeManager import ResumeManager
        
        if isinstance(generator.phase_generator, PhaseGenerator):
            print("✅ phase_generator 是 PhaseGenerator 实例")
        else:
            print("❌ phase_generator 类型不正确")
            return False
        
        if isinstance(generator.resume_manager, ResumeManager):
            print("✅ resume_manager 是 ResumeManager 实例")
        else:
            print("❌ resume_manager 类型不正确")
            return False
        
        print("\n✅ NovelGenerator 初始化测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ 初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase_generator_methods():
    """测试PhaseGenerator的方法"""
    print("=" * 60)
    print("测试 3: PhaseGenerator 方法")
    print("=" * 60)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        from src.core.PhaseGenerator import PhaseGenerator
        
        config = {
            "api": {"provider": "mock", "model": "mock-model"},
            "defaults": {"total_chapters": 10}
        }
        
        generator = NovelGenerator(config)
        phase_gen = generator.phase_generator
        
        # 检查关键方法是否存在
        methods_to_check = [
            'generate_phase_one_preparations',
            'generate_phase_two',
            '_generate_foundation_planning',
            '_generate_worldview_and_characters',
            '_generate_overall_planning',
            '_prepare_content_generation',
            '_generate_all_chapters',
            '_generate_chapters_batch',
            '_prepare_generation_context',
            '_finalize_generation'
        ]
        
        for method_name in methods_to_check:
            if hasattr(phase_gen, method_name):
                print(f"✅ PhaseGenerator.{method_name} 存在")
            else:
                print(f"❌ PhaseGenerator.{method_name} 不存在")
                return False
        
        print("\n✅ PhaseGenerator 方法检查通过\n")
        return True
        
    except Exception as e:
        print(f"❌ PhaseGenerator 方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resume_manager_methods():
    """测试ResumeManager的方法"""
    print("=" * 60)
    print("测试 4: ResumeManager 方法")
    print("=" * 60)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        from src.core.ResumeManager import ResumeManager
        
        config = {
            "api": {"provider": "mock", "model": "mock-model"},
            "defaults": {"total_chapters": 10}
        }
        
        generator = NovelGenerator(config)
        resume_mgr = generator.resume_manager
        
        # 检查关键方法是否存在
        methods_to_check = [
            'check_for_resume_checkpoint',
            'create_initial_checkpoint',
            'resume_phase_one_from_checkpoint',
            '_execute_phase_one_step',
            '_step_worldview_generation',
            '_step_character_generation',
            '_step_stage_plan',
            '_step_quality_assessment',
            '_step_finalization'
        ]
        
        for method_name in methods_to_check:
            if hasattr(resume_mgr, method_name):
                print(f"✅ ResumeManager.{method_name} 存在")
            else:
                print(f"❌ ResumeManager.{method_name} 不存在")
                return False
        
        print("\n✅ ResumeManager 方法检查通过\n")
        return True
        
    except Exception as e:
        print(f"❌ ResumeManager 方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delegation():
    """测试委托调用"""
    print("=" * 60)
    print("测试 5: 委托调用")
    print("=" * 60)
    
    try:
        from src.core.NovelGenerator import NovelGenerator
        
        config = {
            "api": {"provider": "mock", "model": "mock-model"},
            "defaults": {"total_chapters": 10}
        }
        
        generator = NovelGenerator(config)
        
        # 检查委托方法是否存在
        delegation_methods = [
            '_check_for_resume_checkpoint',
            '_resume_phase_one_from_checkpoint'
        ]
        
        for method_name in delegation_methods:
            if hasattr(generator, method_name):
                print(f"✅ NovelGenerator.{method_name} 存在（委托方法）")
            else:
                print(f"❌ NovelGenerator.{method_name} 不存在")
                return False
        
        print("\n✅ 委托调用检查通过\n")
        return True
        
    except Exception as e:
        print(f"❌ 委托调用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试重构后的 NovelGenerator 模块")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    # 运行测试
    all_passed &= test_imports()
    all_passed &= test_initialization()
    all_passed &= test_phase_generator_methods()
    all_passed &= test_resume_manager_methods()
    all_passed &= test_delegation()
    
    # 总结
    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        print("重构成功，NovelGenerator 已成功拆分为:")
        print("  - NovelGenerator (主控制器)")
        print("  - PhaseGenerator (阶段生成器)")
        print("  - ResumeManager (恢复模式管理器)")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)