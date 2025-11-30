"""完整的automain测试脚本 - 带清理功能"""
import sys
import os
from pathlib import Path
import shutil

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置mock环境
os.environ['USE_MOCK_API'] = 'true'

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import json
from config.config import CONFIG
from src.utils.logger import get_logger
from src.core.NovelGenerator import NovelGenerator

logger = get_logger("test_automain")

print("=" * 60)
print("开始完整的automain测试 (带清理)")
print("=" * 60)

try:
    # 0. 清理旧的测试文件
    print("\n[0/7] 清理旧的测试文件...")

    # 清理小说项目目录中的测试文件
    novel_dir = BASE_DIR / "小说项目"
    if novel_dir.exists():
        for item in novel_dir.iterdir():
            if "异界归来的天才医生" in item.name or "未定稿创意" in item.name:
                try:
                    if item.is_file():
                        item.unlink()
                        print(f"  删除文件: {item.name}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        print(f"  删除目录: {item.name}")
                except Exception as e:
                    print(f"  跳过: {item.name} ({e})")

    # 清理quality_data中的测试文件
    quality_dir = BASE_DIR / "quality_data"
    if quality_dir.exists():
        for item in quality_dir.iterdir():
            if "异界归来的天才医生" in item.name:
                try:
                    if item.is_file():
                        item.unlink()
                        print(f"  删除文件: {item.name}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        print(f"  删除目录: {item.name}")
                except Exception as e:
                    print(f"  跳过: {item.name} ({e})")

    print("✓ 清理完成")

    # 1. 初始化generator
    print("\n[1/7] 初始化NovelGenerator...")
    generator = NovelGenerator(CONFIG)
    print("✓ NovelGenerator初始化成功")

    # 2. 加载创意文件
    print("\n[2/7] 加载创意文件...")
    creative_file_path = str(BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt")

    with open(creative_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        creatives = data.get("creativeWorks", [])

    print(f"✓ 成功加载 {len(creatives)} 个创意")

    if not creatives:
        print("❌ 没有创意可供测试")
        sys.exit(1)

    # 3. 获取第一个创意
    print("\n[3/7] 获取第一个创意...")
    test_creative = creatives[0]
    core_setting = test_creative.get('coreSetting', '')[:80]
    print(f"✓ 创意: {core_setting}...")

    # 4. 测试full_auto_generation（限制章节数为3）
    print("\n[4/7] 开始测试生成流程 (3章测试)...")
    print("  (这可能需要一些时间...)")

    total_chapters = 3  # 只生成3章用于测试
    result = generator.full_auto_generation(test_creative, total_chapters)

    # 5. 检查结果
    print("\n[5/7] 检查生成结果...")
    if result:
        print("✓ 生成成功！")

        # 打印生成摘要
        if hasattr(generator, 'novel_data') and generator.novel_data:
            print(f"\n生成的小说信息:")
            print(f"  - 标题: {generator.novel_data.get('novel_title', '未知')}")
            print(f"  - 完成章节: {generator.novel_data.get('current_progress', {}).get('completed_chapters', 0)}")
            print(f"  - 总章节: {generator.novel_data.get('current_progress', {}).get('total_chapters', 0)}")
    else:
        print("❌ 生成失败")

    # 6. 打印摘要
    print("\n[6/7] 打印生成摘要...")
    generator.print_generation_summary()

    # 7. 再次清理测试文件
    print("\n[7/7] 清理测试文件...")

    # 清理小说项目目录中的测试文件
    if novel_dir.exists():
        for item in novel_dir.iterdir():
            if "异界归来的天才医生" in item.name or "未定稿创意" in item.name:
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception:
                    pass

    # 清理quality_data中的测试文件
    if quality_dir.exists():
        for item in quality_dir.iterdir():
            if "异界归来的天才医生" in item.name:
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception:
                    pass

    print("✓ 清理完成")

    print("\n" + "=" * 60)
    if result:
        print("✅ 测试完成！流程正常")
    else:
        print("⚠️ 测试完成但生成失败，请检查日志")
    print("=" * 60)

except KeyboardInterrupt:
    print("\n\n收到中断信号，测试停止")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ 测试过程中出错: {e}")
    import traceback
    print("\n完整错误堆栈:")
    print(traceback.format_exc())
    sys.exit(1)
