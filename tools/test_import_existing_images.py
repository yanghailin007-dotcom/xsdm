"""
测试素材库导入功能

验证 StillImageManager 能否正确扫描并导入 generated_images 目录中的图片
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.StillImageManager import get_still_image_manager

def test_import():
    print("=" * 60)
    print("测试素材库导入功能")
    print("=" * 60)
    
    # 获取管理器实例
    manager = get_still_image_manager()
    
    # 列出所有图片
    images = manager.list_images(limit=100)
    
    print(f"\n📊 素材库统计:")
    print(f"  总图片数: {len(images)}")
    
    if images:
        print(f"\n🖼️ 前5张图片:")
        for i, img in enumerate(images[:5], 1):
            print(f"  {i}. {img.image_id}")
            print(f"     提示词: {img.prompt[:50]}...")
            print(f"     本地路径: {img.local_path}")
            print(f"     访问URL: {img.image_url}")
            print(f"     文件大小: {img.file_size} bytes")
            print()
    else:
        print("\n⚠️ 素材库中没有图片")
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"📈 详细统计:")
    print(f"  总数: {stats['total_count']}")
    print(f"  总大小: {stats['total_size_mb']} MB")
    print(f"  类型分布: {stats['type_counts']}")
    print(f"  状态分布: {stats['status_counts']}")
    
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_import()
