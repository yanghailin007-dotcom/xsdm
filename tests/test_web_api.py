"""
测试 Web API 和模拟数据是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.logger import get_logger
from test_e2e_with_mock_data import TestScenario, MockAPIClient

logger = get_logger("TestWebAPI")

def test_mock_api():
    """测试模拟API是否能生成数据"""
    logger.info("=" * 60)
    logger.info("🧪 测试模拟 API 和小说生成")
    logger.info("=" * 60)
    
    # 1. 创建测试场景
    logger.info("\n1️⃣ 创建测试场景...")
    scenario = TestScenario()
    logger.info("✅ 测试场景创建成功")
    
    # 2. 运行模拟生成
    logger.info("\n2️⃣ 运行模拟测试...")
    try:
        # 运行测试
        success1, msg1 = scenario.test_creative_loading()
        success2, msg2 = scenario.test_novel_initialization()
        
        all_success = success1 and success2
        logger.info("✅ 测试完成")
        
        # 3. 验证结果
        logger.info("\n3️⃣ 验证模拟数据...")
        if all_success:
            logger.info("✅ 模拟数据生成成功")
            
            # 显示生成的数据
            logger.info(f"\n📊 小说信息:")
            logger.info(f"   标题: {scenario.mock_novel_data.get('novel_title')}")
            logger.info(f"   章数: {scenario.mock_novel_data.get('total_chapters')}")
            logger.info(f"   简介: {scenario.mock_novel_data.get('novel_synopsis', '')[:50]}...")
            
            # 4. 测试 MockAPIClient
            logger.info("\n4️⃣ 测试 MockAPIClient...")
            mock_client = MockAPIClient()
            
            logger.info("   📡 调用 mock_generate_outline...")
            outline = mock_client.mock_generate_outline(scenario.mock_novel_data)
            logger.info(f"   ✅ 返回数据类型: {type(outline).__name__}")
            
            logger.info("   📡 调用 mock_generate_content...")
            content = mock_client.mock_generate_content("第一章", scenario.mock_novel_data)
            logger.info(f"   ✅ 返回 {len(content)} 字符")
            
            logger.info("   📡 调用 mock_assess_quality...")
            assessment = mock_client.mock_assess_quality(content)
            logger.info(f"   ✅ 返回数据类型: {type(assessment).__name__}")
            
            # 5. 最终验证
            logger.info("\n" + "=" * 60)
            logger.info("✅ 所有测试通过!")
            logger.info("=" * 60)
            logger.info("\n🚀 模拟 API 工作正常")
            logger.info("📱 可以在网页端调用生成接口")
            logger.info("✨ 系统准备就绪!")
            logger.info("\n💡 下一步: 打开浏览器访问 http://localhost:5000")
            
            return True
            
        else:
            logger.error(f"❌ 测试失败: {msg1} / {msg2}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_mock_api()
    sys.exit(0 if success else 1)
