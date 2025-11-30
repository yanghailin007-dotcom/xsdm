"""
快速测试脚本 (Quick Test)
- 简化版端到端测试
- 只测试核心功能
- 执行时间 < 2 秒
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger
from Contexts import GenerationContext
from datetime import datetime
import json

def quick_test():
    """快速测试"""
    logger = get_logger("QuickTest")
    
    logger.info("\n" + "="*70)
    logger.info("快速功能测试 (Quick Functional Test)")
    logger.info("="*70)
    
    test_results = []
    
    # 测试 1: 导入验证
    logger.info("\n[测试 1] 模块导入验证")
    try:
        from APIClient import APIClient
        from ContentGenerator import ContentGenerator
        from NovelGenerator import NovelGenerator
        logger.info("✅ 所有关键模块导入成功")
        test_results.append(True)
    except Exception as e:
        logger.info(f"❌ 导入失败: {e}")
        test_results.append(False)
    
    # 测试 2: Logger 功能验证
    logger.info("\n[测试 2] Logger 功能验证")
    try:
        test_logger = get_logger("TestModule")
        test_logger.info("这是一条测试日志")
        logger.info("✅ Logger 功能正常")
        test_results.append(True)
    except Exception as e:
        logger.info(f"❌ Logger 失败: {e}")
        test_results.append(False)
    
    # 测试 3: Contexts 验证
    logger.info("\n[测试 3] GenerationContext 验证")
    try:
        mock_novel_data = {
            "novel_title": "测试小说",
            "novel_synopsis": "这是一个测试",
            "current_progress": {}
        }
        
        context = GenerationContext(
            chapter_number=1,
            total_chapters=50,
            novel_data=mock_novel_data,
            stage_plan={},
            event_context={},
            foreshadowing_context={},
            growth_context={},
            expectation_context={}
        )
        
        is_valid, msg = context.validate()
        if is_valid:
            logger.info(f"✅ GenerationContext 验证通过: {context}")
            test_results.append(True)
        else:
            logger.info(f"❌ GenerationContext 验证失败: {msg}")
            test_results.append(False)
    except Exception as e:
        logger.info(f"❌ GenerationContext 错误: {e}")
        test_results.append(False)
    
    # 测试 4: 数据结构验证
    logger.info("\n[测试 4] 创意数据结构验证")
    try:
        creative_data = {
            "coreSetting": "测试设定",
            "coreSellingPoints": "测试卖点",
            "completeStoryline": {
                "opening": {"stageName": "开篇"},
                "development": {"stageName": "发展"},
                "conflict": {"stageName": "冲突"},
                "ending": {"stageName": "结尾"}
            }
        }
        
        assert creative_data["coreSetting"]
        assert creative_data["completeStoryline"]["opening"]["stageName"]
        logger.info("✅ 创意数据结构验证通过")
        test_results.append(True)
    except Exception as e:
        logger.info(f"❌ 创意数据结构验证失败: {e}")
        test_results.append(False)
    
    # 测试 5: JSON 序列化
    logger.info("\n[测试 5] JSON 序列化验证")
    try:
        test_data = {
            "标题": "测试",
            "内容": "这是中文测试",
            "时间": datetime.now().isoformat()
        }
        
        json_str = json.dumps(test_data, ensure_ascii=False, indent=2)
        loaded_data = json.loads(json_str)
        
        assert loaded_data["标题"] == "测试"
        logger.info("✅ JSON 序列化正常")
        test_results.append(True)
    except Exception as e:
        logger.info(f"❌ JSON 序列化失败: {e}")
        test_results.append(False)
    
    # 测试 6: 文件操作
    logger.info("\n[测试 6] 文件操作验证")
    try:
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            test_data = {"测试": "数据"}
            
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False)
            
            assert test_file.exists()
            
            with open(test_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            assert loaded["测试"] == "数据"
            logger.info("✅ 文件操作正常")
            test_results.append(True)
    except Exception as e:
        logger.info(f"❌ 文件操作失败: {e}")
        test_results.append(False)
    
    # 测试 7: 系统配置
    logger.info("\n[测试 7] 系统配置验证")
    try:
        from config import CONFIG
        
        assert CONFIG
        assert "api_keys" in CONFIG
        logger.info("✅ 系统配置加载成功")
        logger.info(f"   可用提供商: {list(CONFIG['api_keys'].keys())}")
        test_results.append(True)
    except Exception as e:
        logger.info(f"❌ 系统配置失败: {e}")
        test_results.append(False)
    
    # 总结
    logger.info("\n" + "="*70)
    passed = sum(test_results)
    total = len(test_results)
    percentage = 100 * passed / total
    
    logger.info(f"测试结果: {passed}/{total} 通过 ({percentage:.1f}%)")
    
    if passed == total:
        logger.info("🎯 所有测试通过！系统准备就绪。")
    else:
        logger.info(f"⚠️ 有 {total - passed} 个测试失败，请检查上面的错误信息。")
    
    logger.info("="*70 + "\n")
    
    return passed == total

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
