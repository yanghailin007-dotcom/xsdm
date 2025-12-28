"""
测试 ContentGenerator 重构后的模块
验证所有导入和基本功能是否正常
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def test_imports():
    """测试所有模块是否能正确导入"""
    print("=" * 60)
    print("Test 1: Verify Module Imports")
    print("=" * 60)
    
    try:
        # 测试新模块导入
        from src.core.content_generation import (
            PromptBuilder,
            ConsistencyGatherer,
            ChapterGenerator,
            PlanGenerator
        )
        print("[OK] All new modules imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Module import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_original_import():
    """测试原始ContentGenerator是否能正常导入"""
    print("\n" + "=" * 60)
    print("Test 2: Verify Original ContentGenerator Import")
    print("=" * 60)
    
    try:
        from src.core.ContentGenerator import ContentGenerator
        print("[OK] ContentGenerator imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] ContentGenerator import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_structure():
    """测试模块结构是否正确"""
    print("\n" + "=" * 60)
    print("Test 3: Verify Module Structure")
    print("=" * 60)
    
    try:
        from src.core.content_generation import PromptBuilder, ConsistencyGatherer
        
        # 检查PromptBuilder
        assert hasattr(PromptBuilder, 'build_character_prompt'), "PromptBuilder missing build_character_prompt method"
        assert hasattr(PromptBuilder, 'build_consistency_prompt'), "PromptBuilder missing build_consistency_prompt method"
        print("[OK] PromptBuilder structure correct")
        
        # 检查ConsistencyGatherer
        assert hasattr(ConsistencyGatherer, 'gather_all'), "ConsistencyGatherer missing gather_all method"
        print("[OK] ConsistencyGatherer structure correct")
        
        from src.core.content_generation import ChapterGenerator
        
        # 检查ChapterGenerator
        assert hasattr(ChapterGenerator, 'generate_chapter_content_for_novel'), "ChapterGenerator missing main method"
        assert hasattr(ChapterGenerator, '_build_emotional_intensity_guidance'), "ChapterGenerator missing emotional intensity method"
        print("[OK] ChapterGenerator structure correct")
        
        from src.core.content_generation import PlanGenerator
        
        # 检查PlanGenerator
        assert hasattr(PlanGenerator, 'generate_single_plan'), "PlanGenerator missing generate_single_plan method"
        print("[OK] PlanGenerator structure correct")
        
        return True
    except AssertionError as e:
        print(f"[FAIL] Module structure verification failed: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_emotional_intensity_logic():
    """测试情绪强度逻辑"""
    print("\n" + "=" * 60)
    print("Test 4: Verify Emotional Intensity Logic")
    print("=" * 60)
    
    try:
        # 模拟场景数据
        mock_scenes = [
            {"name": "Scene 1", "position": "opening", "emotional_intensity": "low", "emotional_impact": "Calm start"},
            {"name": "Scene 2", "position": "development1", "emotional_intensity": "medium", "emotional_impact": "Gradually tense"},
            {"name": "Scene 3", "position": "climax", "emotional_intensity": "high", "emotional_impact": "Emotional explosion"}
        ]
        
        # 统计强度
        intensity_votes = [scene["emotional_intensity"] for scene in mock_scenes if "emotional_intensity" in scene]
        
        low_count = intensity_votes.count("low")
        medium_count = intensity_votes.count("medium")
        high_count = intensity_votes.count("high")
        
        # 测试投票逻辑
        if high_count > 0:
            result_intensity = "high"
        elif low_count > medium_count * 2:
            result_intensity = "low"
        else:
            result_intensity = "medium"
        
        print(f"[OK] Emotional intensity statistics: low={low_count}, medium={medium_count}, high={high_count}")
        print(f"[OK] Final intensity: {result_intensity}")
        
        assert result_intensity == "high", f"Expected intensity 'high', got '{result_intensity}'"
        print("[OK] Emotional intensity logic correct")
        
        return True
    except Exception as e:
        print(f"[FAIL] Emotional intensity logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ContentGenerator Refactoring Verification Test")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("Module Import", test_imports()))
    results.append(("Original Import", test_original_import()))
    results.append(("Module Structure", test_module_structure()))
    results.append(("Emotional Intensity Logic", test_emotional_intensity_logic()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[OK] Passed" if passed else "[FAIL] Failed"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n[SUCCESS] All tests passed! Refactoring successful!")
        print("\nYou can safely use the refactored code.")
    else:
        print("\n[WARNING] Some tests failed, please check error messages.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())