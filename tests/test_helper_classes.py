#!/usr/bin/env python3
"""
Test script to verify that the new helper classes are working correctly
"""

from ContentGenerator import ContentGenerator
from StagePlanManager import StagePlanManager
from src.utils.logger import get_logger

logger = get_logger("TestHelperClasses")

def test_content_generator_helpers():
    """Test ContentGenerator helper classes"""
    logger.info("Testing ContentGenerator helper classes...")
    
    try:
        # Create a mock generator
        class MockGenerator:
            pass
        
        cg = ContentGenerator(MockGenerator(), None, None, None, None)
        
        # Test that helper classes were instantiated
        assert hasattr(cg, '_prompt_builder'), "Missing _prompt_builder"
        assert hasattr(cg, '_consistency_gatherer'), "Missing _consistency_gatherer"
        
        logger.info("✅ ContentGenerator helper classes instantiated successfully")
        logger.info(f"   - _PromptBuilder: {type(cg._prompt_builder).__name__}")
        logger.info(f"   - _ConsistencyGatherer: {type(cg._consistency_gatherer).__name__}")
        
        # Test that helper classes have expected methods
        assert hasattr(cg._prompt_builder, 'build_character_prompt'), "Missing build_character_prompt"
        assert hasattr(cg._consistency_gatherer, 'gather_all'), "Missing gather_all"
        
        logger.info("✅ ContentGenerator helper classes have expected methods")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ContentGenerator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_plan_manager_helpers():
    """Test StagePlanManager helper classes"""
    logger.info("\nTesting StagePlanManager helper classes...")
    
    try:
        # Create a mock generator
        class MockGenerator:
            pass
        
        spm = StagePlanManager(MockGenerator())
        
        # Test that helper classes were instantiated
        assert hasattr(spm, '_event_decomposer'), "Missing _event_decomposer"
        assert hasattr(spm, '_plan_validator'), "Missing _plan_validator"
        
        logger.info("✅ StagePlanManager helper classes instantiated successfully")
        logger.info(f"   - _EventDecomposer: {type(spm._event_decomposer).__name__}")
        logger.info(f"   - _PlanValidator: {type(spm._plan_validator).__name__}")
        
        # Test that helper classes have expected methods
        assert hasattr(spm._event_decomposer, 'decompose'), "Missing decompose"
        assert hasattr(spm._plan_validator, 'validate'), "Missing validate"
        
        logger.info("✅ StagePlanManager helper classes have expected methods")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ StagePlanManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    logger.info("="*60)
    logger.info("Testing New Helper Classes Implementation")
    logger.info("="*60)
    
    results = []
    results.append(("ContentGenerator Helpers", test_content_generator_helpers()))
    results.append(("StagePlanManager Helpers", test_stage_plan_manager_helpers()))
    
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        logger.info("\n✅ All tests passed!")
    else:
        logger.error("\n❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
