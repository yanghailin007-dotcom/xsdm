"""逐步测试脚本"""
import sys
import os
from pathlib import Path

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置mock环境
os.environ['USE_MOCK_API'] = 'true'

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("步骤1: 开始测试...")

try:
    print("步骤2: 导入配置...")
    from config.config import CONFIG
    print(f"步骤2完成: 配置已加载")

    print("步骤3: 导入logger...")
    from src.utils.logger import get_logger
    print(f"步骤3完成: logger已导入")

    print("步骤4: 创建logger实例...")
    logger = get_logger("test")
    print(f"步骤4完成: logger实例已创建")

    print("步骤5: 测试logger.info...")
    logger.info("测试消息")
    print(f"步骤5完成: logger.info已调用")

    print("步骤6: 导入seed_utils...")
    from src.utils.seed_utils import ensure_seed_dict
    print(f"步骤6完成: seed_utils已导入")

    print("步骤7: 导入NovelGenerator...")
    from src.core.NovelGenerator import NovelGenerator
    print(f"步骤7完成: NovelGenerator已导入")

    print("步骤8: 创建NovelGenerator实例...")
    print("  (这一步可能需要一些时间...)")
    generator = NovelGenerator(CONFIG)
    print(f"步骤8完成: NovelGenerator实例已创建")

    print("\n所有步骤完成！")

except Exception as e:
    print(f"\n错误发生在上面显示的步骤")
    print(f"错误信息: {e}")
    import traceback
    print("\n完整错误堆栈:")
    print(traceback.format_exc())
    sys.exit(1)
