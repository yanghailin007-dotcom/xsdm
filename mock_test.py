#!/usr/bin/env python3
"""
Simple Mock Test - 简单模拟测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_basic_modules():
    """Test basic modules"""
    print("Testing basic modules...")
    try:
        from src.utils.logger import get_logger
        logger = get_logger("TestLogger")
        logger.info("Logger working")
        print("  Logger: OK")
        return True
    except Exception as e:
        print(f"  Logger: FAILED - {e}")
        return False

def test_config():
    """Test configuration"""
    print("\nTesting config...")
    try:
        from config.config import CONFIG
        print(f"  Config: OK ({len(CONFIG)} keys)")
        return True
    except Exception as e:
        print(f"  Config: FAILED - {e}")
        return False

def test_mock():
    """Test mock environment"""
    print("\nTesting mock environment...")
    try:
        from mock_env_en import get_mock_client
        client = get_mock_client()
        response = client.call_api([{"role": "user", "content": "test"}])
        print(f"  Mock API: OK (response: {len(response)} chars)")
        return True
    except Exception as e:
        print(f"  Mock API: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directories():
    """Test required directories"""
    print("\nTesting directories...")
    try:
        dirs = [
            "data/projects",
            "data/creative_ideas",
            "web/templates",
            "web/static"
        ]

        missing = []
        for dir_path in dirs:
            if not Path(dir_path).exists():
                missing.append(dir_path)

        if missing:
            print(f"  Directories: FAILED - Missing: {missing}")
            return False
        else:
            print(f"  Directories: OK ({len(dirs)} dirs)")
            return True
    except Exception as e:
        print(f"  Directories: FAILED - {e}")
        return False

def test_mock_workflow():
    """Test complete mock workflow"""
    print("\nTesting mock workflow...")
    try:
        from mock_env_en import get_mock_client
        client = get_mock_client()

        # Test creative refinement
        response = client.call_api([{"role": "user", "content": "Refine creative idea"}])
        print("    Creative refinement: OK")

        # Test chapter outline
        response = client.call_api([{"role": "user", "content": "Generate chapter 1 outline"}])
        print("    Chapter outline: OK")

        # Test chapter content
        response = client.call_api([{"role": "user", "content": "Generate chapter 1 content"}])
        print("    Chapter content: OK")

        # Test quality assessment
        response = client.call_api([{"role": "user", "content": "Assess this content"}])
        print("    Quality assessment: OK")

        print("  Mock workflow: OK")
        return True
    except Exception as e:
        print(f"  Mock workflow: FAILED - {e}")
        return False

def test_web_server():
    """Test web server"""
    print("\nTesting web server...")
    try:
        # Import mock environment
        from mock_env_en import get_mock_client

        # Test web server module import
        import web.web_server as ws
        print("  Web server: OK")
        return True
    except Exception as e:
        print(f"  Web server: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("Simple Mock Test System")
    print("=" * 60)
    print("(Testing with simulated API responses)")
    print()

    tests = [
        test_basic_modules,
        test_config,
        test_mock,
        test_directories,
        test_mock_workflow,
        test_web_server
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("  Status: PASSED")
            else:
                print("  Status: FAILED")
        except Exception as e:
            print(f"  Status: ERROR - {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\nSUCCESS: System is ready!")
        print("\nNext steps:")
        print("  1. python mock_test_full.py - Complete mock test")
        print("  2. python web/web_server.py - Start web server")
        print("  3. Visit: http://localhost:5000")
    else:
        print(f"\nFAILED: {total-passed} tests failed. Check errors above.")

    print("\nMock Environment Benefits:")
    print("  - Fast testing (no real API calls)")
    print("  - No internet required")
    print("  - Predefined responses")
    print("  - Simulated novel generation")
    print("  - Quality assessment simulation")

    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)