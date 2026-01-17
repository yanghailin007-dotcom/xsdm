"""
剧照图片素材库系统测试脚本

测试整个剧照图片素材库的功能
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def test_still_image_library():
    """测试剧照图片素材库"""
    
    print("=" * 60)
    print("🧪 剧照图片素材库系统测试")
    print("=" * 60)
    
    # 测试1: 导入模块
    print("\n📦 测试1: 导入模块")
    try:
        from src.models.still_image_models import StillImage, StillImageType, StillImageStatus
        from src.managers.StillImageManager import get_still_image_manager
        print("✅ 模块导入成功")
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    
    # 测试2: 初始化管理器
    print("\n🔧 测试2: 初始化管理器")
    try:
        manager = get_still_image_manager()
        print(f"✅ 管理器初始化成功")
        print(f"📁 存储目录: {manager.storage_dir}")
        print(f"📋 元数据目录: {manager.metadata_dir}")
        print(f"📊 已加载图片数: {len(manager.images)}")
    except Exception as e:
        print(f"❌ 管理器初始化失败: {e}")
        return False
    
    # 测试3: 创建测试图片
    print("\n🎨 测试3: 创建测试图片")
    try:
        test_image = manager.add_image(
            image_type=StillImageType.CUSTOM,
            prompt="测试剧照提示词",
            local_path="test_image.png",
            image_url="/generated_images/test_image.png",
            novel_title="测试小说",
            character_name=None,
            event_name=None,
            aspect_ratio="9:16",
            image_size="4K",
            used_reference_images=0,
            file_size=1024000,
            metadata={"test": True}
        )
        print(f"✅ 测试图片创建成功: {test_image.image_id}")
        print(f"   - 类型: {test_image.image_type.value}")
        print(f"   - 提示词: {test_image.prompt}")
        print(f"   - 本地路径: {test_image.local_path}")
        print(f"   - URL: {test_image.image_url}")
    except Exception as e:
        print(f"❌ 创建测试图片失败: {e}")
        return False
    
    # 测试4: 查询图片
    print("\n🔍 测试4: 查询图片")
    try:
        retrieved_image = manager.get_image(test_image.image_id)
        if retrieved_image:
            print(f"✅ 图片查询成功: {retrieved_image.image_id}")
            print(f"   - 状态: {retrieved_image.status.value}")
            print(f"   - 创建时间: {retrieved_image.created_at}")
        else:
            print(f"❌ 未找到图片: {test_image.image_id}")
            return False
    except Exception as e:
        print(f"❌ 查询图片失败: {e}")
        return False
    
    # 测试5: 列出图片
    print("\n📋 测试5: 列出图片")
    try:
        images = manager.list_images(limit=10)
        print(f"✅ 图片列表获取成功: {len(images)} 张")
        for img in images[:3]:  # 只显示前3张
            print(f"   - {img.image_id}: {img.image_type.value} - {img.prompt[:30]}...")
    except Exception as e:
        print(f"❌ 列出图片失败: {e}")
        return False
    
    # 测试6: 获取统计信息
    print("\n📊 测试6: 获取统计信息")
    try:
        stats = manager.get_statistics()
        print(f"✅ 统计信息获取成功:")
        print(f"   - 总数量: {stats['total_count']}")
        print(f"   - 类型分布: {stats['type_counts']}")
        print(f"   - 状态分布: {stats['status_counts']}")
        print(f"   - 总大小: {stats['total_size_mb']} MB")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
        return False
    
    # 测试7: 导出元数据
    print("\n📤 测试7: 导出元数据")
    try:
        export_file = "test_still_images_export.json"
        success = manager.export_metadata(export_file)
        if success:
            print(f"✅ 元数据导出成功: {export_file}")
            # 验证文件存在
            if os.path.exists(export_file):
                with open(export_file, 'r', encoding='utf-8') as f:
                    export_data = json.load(f)
                print(f"   - 导出图片数: {export_data.get('total_count', 0)}")
                # 清理测试文件
                os.remove(export_file)
                print(f"   - 测试文件已清理")
        else:
            print(f"❌ 元数据导出失败")
            return False
    except Exception as e:
        print(f"❌ 导出元数据失败: {e}")
        return False
    
    # 测试8: 删除图片
    print("\n🗑️  测试8: 删除图片")
    try:
        success = manager.delete_image(test_image.image_id)
        if success:
            print(f"✅ 图片删除成功: {test_image.image_id}")
            # 验证图片已删除
            deleted_image = manager.get_image(test_image.image_id)
            if not deleted_image:
                print(f"   - 确认图片已从内存中删除")
        else:
            print(f"❌ 图片删除失败")
            return False
    except Exception as e:
        print(f"❌ 删除图片失败: {e}")
        return False
    
    # 测试9: API接口测试
    print("\n🌐 测试9: API接口测试")
    try:
        # 导入API模块
        from web.api.still_image_api import still_image_api
        print("✅ API模块导入成功")
        print("   - 可用端点:")
        for rule in still_image_api.url_map.iter_rules():
            if 'still-images' in rule.rule:
                print(f"     • {rule.methods} {rule.rule}")
    except Exception as e:
        print(f"❌ API接口测试失败: {e}")
        return False
    
    # 测试10: 数据序列化/反序列化
    print("\n🔄 测试10: 数据序列化/反序列化")
    try:
        # 创建测试图片
        test_image2 = StillImage(
            image_id="test_serialization",
            image_type=StillImageType.CHARACTER,
            prompt="序列化测试",
            status=StillImageStatus.COMPLETED,
            novel_title="测试小说",
            character_name="测试角色"
        )
        
        # 序列化
        data = test_image2.to_dict()
        print(f"✅ 序列化成功: {len(data)} 个字段")
        
        # 反序列化
        restored_image = StillImage.from_dict(data)
        print(f"✅ 反序列化成功: {restored_image.image_id}")
        print(f"   - 类型: {restored_image.image_type.value}")
        print(f"   - 提示词: {restored_image.prompt}")
        print(f"   - 角色: {restored_image.character_name}")
        
        # 验证数据一致性
        assert restored_image.image_id == test_image2.image_id
        assert restored_image.image_type == test_image2.image_type
        assert restored_image.prompt == test_image2.prompt
        assert restored_image.character_name == test_image2.character_name
        print(f"✅ 数据一致性验证通过")
    except Exception as e:
        print(f"❌ 序列化/反序列化失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！剧照图片素材库系统工作正常")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = test_still_image_library()
    sys.exit(0 if success else 1)
