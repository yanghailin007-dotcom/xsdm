"""测试automain的调试脚本"""
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

print("=" * 60)
print("开始调试测试...")
print("=" * 60)

try:
    # 1. 测试导入配置
    print("\n[1/6] 测试导入配置...")
    from config.config import CONFIG
    print(f"✓ 配置加载成功")
    print(f"  - API keys available: {any(CONFIG['api_keys'].values())}")
    print(f"  - Default chapters: {CONFIG['defaults']['total_chapters']}")

    # 2. 测试导入logger
    print("\n[2/6] 测试导入logger...")
    from src.utils.logger import get_logger
    logger = get_logger("test")
    logger.info("测试日志输出")
    print("✓ Logger工作正常")

    # 3. 测试导入seed_utils
    print("\n[3/6] 测试导入seed_utils...")
    from src.utils.seed_utils import ensure_seed_dict
    test_seed = {"coreSetting": "测试核心设定"}
    result = ensure_seed_dict(test_seed)
    print(f"✓ seed_utils工作正常: {result}")

    # 4. 测试导入NovelGenerator
    print("\n[4/6] 测试导入NovelGenerator...")
    from src.core.NovelGenerator import NovelGenerator
    print("✓ NovelGenerator导入成功")

    # 5. 测试创建generator实例
    print("\n[5/6] 测试创建NovelGenerator实例...")
    generator = NovelGenerator(CONFIG)
    print("✓ NovelGenerator实例创建成功")
    print(f"  - API Client类型: {type(generator.api_client).__name__}")

    # 6. 测试创意文件加载
    print("\n[6/6] 测试创意文件加载...")
    creative_file_path = str(BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt")
    print(f"  - 创意文件路径: {creative_file_path}")
    print(f"  - 文件是否存在: {os.path.exists(creative_file_path)}")

    if os.path.exists(creative_file_path):
        import json
        with open(creative_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            creatives = data.get("creativeWorks", [])
            print(f"✓ 创意文件加载成功")
            print(f"  - 创意数量: {len(creatives)}")
            if creatives:
                print(f"  - 第一个创意: {creatives[0].get('coreSetting', '')[:50]}...")

    print("\n" + "=" * 60)
    print("✅ 所有基础组件测试通过！")
    print("=" * 60)

    # 现在尝试运行一次简单的生成测试
    print("\n开始简单生成测试...")
    print("-" * 60)

    # 获取第一个创意
    if creatives:
        test_creative = creatives[0]
        print(f"使用创意: {test_creative.get('coreSetting', '')[:50]}...")

        # 尝试调用full_auto_generation
        print("调用full_auto_generation...")
        result = generator.full_auto_generation(test_creative, 3)

        if result:
            print("✅ 生成测试成功！")
        else:
            print("❌ 生成测试失败")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    print("\n完整错误堆栈:")
    print(traceback.format_exc())
    sys.exit(1)
