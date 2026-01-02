"""
测试视频镜头生成修复

验证AI是否能正确生成25个镜头（5个单元×5个镜头）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web.api.video_generation_api import _generate_ai_shot_descriptions, _generate_fallback_shot_descriptions
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_ai_shot_generation():
    """测试AI镜头生成"""
    print("=" * 80)
    print("测试AI镜头生成功能")
    print("=" * 80)
    
    # 测试参数
    test_prompt = "赛博朋克风格的未来城市夜景，霓虹灯闪烁，无人机俯瞰视角"
    shot_count = 5
    video_type = "long_series"
    
    print(f"\n📝 测试提示词: {test_prompt}")
    print(f"🎯 需要生成镜头数: {shot_count}")
    print(f"📹 视频类型: {video_type}")
    
    # 调用AI生成
    print(f"\n🚀 开始调用AI生成镜头...")
    descriptions = _generate_ai_shot_descriptions(test_prompt, shot_count, video_type)
    
    print(f"\n✅ 生成完成!")
    print(f"📊 实际生成数量: {len(descriptions)}")
    
    # 显示所有镜头
    print(f"\n🎬 镜头详情:")
    for idx, desc in enumerate(descriptions, 1):
        print(f"\n镜头 {idx}:")
        print(f"  描述: {desc}")
        print(f"  长度: {len(desc)} 字符")
    
    # 验证
    print(f"\n" + "=" * 80)
    print("验证结果:")
    print("=" * 80)
    
    if len(descriptions) == shot_count:
        print(f"✅ 数量正确: {len(descriptions)}/{shot_count}")
    else:
        print(f"❌ 数量错误: {len(descriptions)}/{shot_count}")
    
    # 检查描述质量
    min_length = 10
    all_valid = all(len(desc) >= min_length for desc in descriptions)
    if all_valid:
        print(f"✅ 所有描述长度 >= {min_length} 字符")
    else:
        print(f"❌ 存在描述长度 < {min_length} 字符")
    
    # 检查唯一性
    unique_descriptions = len(set(descriptions))
    if unique_descriptions == len(descriptions):
        print(f"✅ 所有描述都是唯一的")
    else:
        print(f"⚠️  存在重复描述: {unique_descriptions}/{len(descriptions)} 唯一")
    
    return len(descriptions) == shot_count and all_valid


def test_fallback_generation():
    """测试备用方案生成"""
    print(f"\n" + "=" * 80)
    print("测试备用方案生成")
    print("=" * 80)
    
    test_prompt = "测试提示词"
    shot_count = 5
    video_type = "long_series"
    
    descriptions = _generate_fallback_shot_descriptions(test_prompt, shot_count, video_type)
    
    print(f"\n📊 备用方案生成数量: {len(descriptions)}")
    
    for idx, desc in enumerate(descriptions, 1):
        print(f"\n镜头 {idx}:")
        print(f"  描述: {desc}")
    
    if len(descriptions) == shot_count:
        print(f"\n✅ 备用方案数量正确: {len(descriptions)}/{shot_count}")
    else:
        print(f"\n❌ 备用方案数量错误: {len(descriptions)}/{shot_count}")
    
    return len(descriptions) == shot_count


def test_multiple_units():
    """测试多单元生成（模拟5个单元）"""
    print(f"\n" + "=" * 80)
    print("测试多单元生成（5个单元，每个5个镜头）")
    print("=" * 80)
    
    total_units = 5
    shots_per_unit = 5
    test_prompt = "赛博朋克都市夜景"
    video_type = "long_series"
    
    print(f"\n📊 模拟 {total_units} 个单元，每个 {shots_per_unit} 个镜头")
    print(f"🎯 总镜头数: {total_units * shots_per_unit}")
    
    all_shots = []
    for unit_idx in range(total_units):
        print(f"\n🎬 生成第 {unit_idx + 1} 个单元的镜头...")
        descriptions = _generate_ai_shot_descriptions(
            test_prompt,
            shots_per_unit,
            video_type
        )
        
        print(f"  ✅ 单元 {unit_idx + 1} 生成 {len(descriptions)} 个镜头")
        all_shots.extend(descriptions)
    
    print(f"\n" + "=" * 80)
    print("多单元生成结果:")
    print("=" * 80)
    print(f"📊 总镜头数: {len(all_shots)}")
    print(f"🎯 目标数量: {total_units * shots_per_unit}")
    
    if len(all_shots) == total_units * shots_per_unit:
        print(f"✅ 多单元生成成功！")
        return True
    else:
        print(f"❌ 多单元生成失败：{len(all_shots)}/{total_units * shots_per_unit}")
        return False


if __name__ == "__main__":
    print("\n" + "🎬" * 40)
    print("视频镜头生成修复测试")
    print("🎬" * 40)
    
    # 运行测试
    test1_passed = test_ai_shot_generation()
    test2_passed = test_fallback_generation()
    test3_passed = test_multiple_units()
    
    # 总结
    print(f"\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"测试1 (AI生成): {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试2 (备用方案): {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"测试3 (多单元): {'✅ 通过' if test3_passed else '❌ 失败'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\n{'🎉 所有测试通过！' if all_passed else '⚠️  存在失败的测试'}")
    
    sys.exit(0 if all_passed else 1)