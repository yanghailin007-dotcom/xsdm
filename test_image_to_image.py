"""
测试Nano Banana图生图功能
根据官方demo改进的版本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator

def test_text_to_image():
    """测试文生图功能"""
    print("\n" + "="*60)
    print("🎨 测试1: 文生图 (Text to Image)")
    print("="*60)
    
    generator = NanoBananaImageGenerator()
    
    if not generator.is_available():
        print("❌ Nano Banana服务不可用")
        return False
    
    result = generator.generate_image(
        prompt="一位仙风道骨的剑仙，白发如雪，身穿白色仙袍，手持发光的长剑，背景是云雾缭绕的仙山，唯美仙侠风格，高清",
        aspect_ratio="16:9",
        image_size="2K",
        save_path="test_output_text_to_image.png"
    )
    
    if result["success"]:
        print(f"✅ 文生图成功!")
        print(f"   保存路径: {result['local_path']}")
        print(f"   文件大小: {result['file_size']} 字节")
        return True
    else:
        print(f"❌ 文生图失败: {result['error']}")
        return False

def test_image_to_image():
    """测试图生图功能（使用参考图）"""
    print("\n" + "="*60)
    print("🎨 测试2: 图生图 (Image to Image)")
    print("="*60)
    
    generator = NanoBananaImageGenerator()
    
    # 检查参考图是否存在
    reference_image = "test_output_text_to_image.png"
    if not os.path.exists(reference_image):
        print(f"❌ 参考图不存在: {reference_image}")
        print("   请先运行文生图测试生成参考图")
        return False
    
    print(f"📷 使用参考图: {reference_image}")
    
    result = generator.generate_image(
        prompt="将这张图片转换成水墨画风格，保持主要构图，添加传统中国水墨画的艺术效果，黑白为主，淡雅自然",
        aspect_ratio="16:9",
        image_size="2K",
        save_path="test_output_image_to_image.png",
        reference_image=reference_image  # 🔥 使用参考图
    )
    
    if result["success"]:
        print(f"✅ 图生图成功!")
        print(f"   保存路径: {result['local_path']}")
        print(f"   文件大小: {result['file_size']} 字节")
        return True
    else:
        print(f"❌ 图生图失败: {result['error']}")
        if 'details' in result:
            print(f"   详细信息: {result['details']}")
        return False

def test_portrait_with_reference():
    """测试人物剧照+参考图生成"""
    print("\n" + "="*60)
    print("🎨 测试3: 人物剧照+参考图")
    print("="*60)
    
    generator = NanoBananaImageGenerator()
    
    # 检查参考图是否存在
    reference_image = "test_output_text_to_image.png"
    if not os.path.exists(reference_image):
        print(f"❌ 参考图不存在: {reference_image}")
        return False
    
    print(f"📷 使用参考图: {reference_image}")
    
    result = generator.generate_image(
        prompt="参考这张图片的风格和构图，生成一位温柔美丽的少女，长发飘逸，身穿轻盈的连衣裙，站在花海中，柔和光线，唯美风格",
        aspect_ratio="9:16",  # 竖屏比例适合人物
        image_size="2K",
        save_path="test_output_portrait_ref.png",
        reference_image=reference_image
    )
    
    if result["success"]:
        print(f"✅ 人物剧照+参考图成功!")
        print(f"   保存路径: {result['local_path']}")
        print(f"   文件大小: {result['file_size']} 字节")
        return True
    else:
        print(f"❌ 人物剧照+参考图失败: {result['error']}")
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 Nano Banana图生图测试套件")
    print("="*60)
    
    results = []
    
    # 测试1: 文生图
    results.append(("文生图", test_text_to_image()))
    
    # 测试2: 图生图（需要先成功完成测试1）
    if results[0][1]:
        results.append(("图生图", test_image_to_image()))
    
    # 测试3: 人物剧照+参考图
    if results[0][1]:
        results.append(("人物剧照+参考图", test_portrait_with_reference()))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    print(f"\n总计: {success_count}/{total_count} 测试通过")
    
    if success_count == total_count:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ 有 {total_count - success_count} 个测试失败")
    
    print("\n💡 提示:")
    print("  - 生成的图片保存在: generated_images/ 目录")
    print("  - 测试图片保存在: 项目根目录")
    print("  - 详细日志查看: logs/nanobanana_detailed.log")

if __name__ == "__main__":
    main()