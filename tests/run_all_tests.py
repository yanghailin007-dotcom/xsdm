"""
一键测试运行器 (One-Click Test Runner)
运行所有测试套件并生成总结报告
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from src.utils.logger import get_logger

def run_test(test_file, test_name):
    """运行单个测试文件"""
    logger = get_logger("TestRunner")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"运行: {test_name} ({test_file})")
    logger.info(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=str(Path(__file__).parent),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # 输出测试结果
        output = result.stdout + result.stderr
        print(output)
        
        # 检查测试是否通过
        success = result.returncode == 0
        return success, None
        
    except subprocess.TimeoutExpired:
        logger.info(f"❌ 测试超时")
        return False, "测试执行超时"
    except Exception as e:
        logger.info(f"❌ 测试执行失败: {e}")
        return False, str(e)


def main():
    """主函数"""
    logger = get_logger("TestRunner")
    
    logger.info("\n")
    logger.info("*"*70)
    logger.info("完整测试套件运行器 (Complete Test Suite Runner)")
    logger.info("*"*70)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("test_quick.py", "快速测试 (Quick Test)"),
        ("test_e2e_with_mock_data.py", "端到端测试 (E2E Test)"),
        ("test_integration.py", "集成测试 (Integration Test)"),
    ]
    
    results = []
    start_time = datetime.now()
    
    for test_file, test_name in tests:
        success, error = run_test(test_file, test_name)
        results.append((test_name, success, error))
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 生成总结报告
    logger.info("\n")
    logger.info("*"*70)
    logger.info("测试总结 (Test Summary)")
    logger.info("*"*70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        error_msg = f" - {error}" if error else ""
        logger.info(f"{status} | {test_name}{error_msg}")
    
    logger.info("="*70)
    logger.info(f"总体结果: {passed}/{total} 测试通过 ({100*passed/total:.1f}%)")
    logger.info(f"总耗时: {duration:.1f} 秒")
    logger.info("="*70)
    
    if passed == total:
        logger.info("\n✅ 所有测试都通过了！系统状态良好。")
    else:
        logger.info(f"\n⚠️ 有 {total - passed} 个测试失败，请查看上面的详细信息。")
    
    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("*"*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
