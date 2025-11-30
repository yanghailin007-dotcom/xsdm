#!/usr/bin/env python3
"""最简单的automain测试 - 直接跑"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

# 启用测试模式
os.environ['USE_MOCK_API'] = 'true'

from src.utils.logger import get_logger
logger = get_logger("simple_test")

logger.info("="*60)
logger.info("🚀 开始automain测试（测试模式）")
logger.info("="*60)

try:
    logger.info("\n1️⃣  导入automain...")
    from automain import SimpleCreativeManager, start_new_project
    from config.config import CONFIG
    from src.core.NovelGenerator import NovelGenerator
    
    logger.info("2️⃣  创建生成器...")
    generator = NovelGenerator(CONFIG)
    
    logger.info("3️⃣  加载创意...")
    creative_file_path = str(BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt")
    creative_manager = SimpleCreativeManager(creative_file_path)
    
    if not creative_manager.creative_data:
        logger.info("❌ 没有创意数据")
        sys.exit(1)
    
    logger.info(f"✅ 加载了 {len(creative_manager.creative_data)} 个创意")
    
    logger.info("\n4️⃣  获取第一个创意...")
    creative = creative_manager.get_current_creative()
    logger.info(f"✅ 创意: {str(creative)[:100]}...")
    
    logger.info("\n5️⃣  开始生成小说（测试模式）...")
    success = start_new_project(generator, creative, logger)
    
    if success:
        logger.info("\n✅ 生成成功！")
    else:
        logger.info("\n❌ 生成失败")
        
except Exception as e:
    logger.info(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

logger.info("\n" + "="*60)
logger.info("测试完成")
logger.info("="*60)
