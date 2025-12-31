"""
视频生成适配器测试

测试三种视频模式的转换功能：
1. 短片/动画电影（5-30分钟）
2. 长篇剧集（20-40分钟/集）
3. 短视频系列（1-3分钟）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.VideoAdapterManager import VideoAdapterManager


class MockGenerator:
    """模拟生成器，用于测试"""
    def __init__(self):
        self.novel_data = {
            "novel_title": "测试小说：剑道独尊",
            "novel_synopsis": "一个少年剑客的传奇故事",
            "category": "玄幻",
            "current_progress": {
                "total_chapters": 200
            },
            "stage_writing_plans": {
                "opening_stage": {
                    "stage_writing_plan": {
                        "chapter_range": "1-30",
                        "event_system": {
                            "major_events": [
                                {
                                    "name": "主角觉醒剑心",
                                    "chapter_range": "1-5",
                                    "main_goal": "主角在危机中觉醒剑道天赋",
                                    "emotional_focus": "high",
                                    "role_in_stage_arc": "开局高潮",
                                    "composition": {
                                        "起": [
                                            {
                                                "name": "危机降临",
                                                "chapter_range": "1-2",
                                                "main_goal": "主角遭遇强敌追杀"
                                            }
                                        ],
                                        "承": [
                                            {
                                                "name": "绝境突破",
                                                "chapter_range": "3-4",
                                                "main_goal": "主角在生死关头觉醒"
                                            }
                                        ]
                                    },
                                    "special_emotional_events": [
                                        {
                                            "name": "剑心觉醒",
                                            "description": "主角感受到前所未有的力量",
                                            "chapter_range": "3-3"
                                        }
                                    ]
                                },
                                {
                                    "name": "初入宗门",
                                    "chapter_range": "6-15",
                                    "main_goal": "主角被剑宗收为弟子",
                                    "emotional_focus": "medium",
                                    "role_in_stage_arc": "发展",
                                    "composition": {
                                        "起": [
                                            {
                                                "name": "宗门试炼",
                                                "chapter_range": "6-10",
                                                "main_goal": "通过入门测试"
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        self.api_client = None


def test_short_film_conversion():
    """测试短片模式转换"""
    print("\n" + "="*60)
    print("🎬 测试 1: 短片/动画电影模式")
    print("="*60)
    
    mock_gen = MockGenerator()
    adapter = VideoAdapterManager(mock_gen)
    
    result = adapter.convert_to_video(
        novel_data=mock_gen.novel_data,
        video_type="short_film"
    )
    
    print(f"✅ 转换成功")
    print(f"   视频类型: {result['video_type_name']}")
    print(f"   单元数量: {len(result['units'])}")
    print(f"   总时长: {result['series_info']['total_duration_minutes']}分钟")
    
    # 检查结果结构
    assert 'video_type' in result
    assert 'units' in result
    assert len(result['units']) == 1  # 短片只有1个单元
    assert 'storyboard' in result['units'][0]
    
    print(f"\n📊 分镜详情:")
    storyboard = result['units'][0]['storyboard']
    print(f"   场景数: {storyboard['total_scenes']}")
    
    for scene in storyboard['scenes'][:2]:  # 只显示前2个场景
        print(f"\n   场景 {scene['scene_number']}: {scene['scene_title']}")
        print(f"   镜头数: {len(scene['shot_sequence'])}")
        for shot in scene['shot_sequence'][:2]:  # 只显示前2个镜头
            print(f"     - {shot['shot_type']} ({shot['duration_seconds']}秒): {shot['description']}")
    
    print("\n✅ 短片模式测试通过")
    return result


def test_long_series_conversion():
    """测试长剧集模式转换"""
    print("\n" + "="*60)
    print("📺 测试 2: 长篇剧集模式")
    print("="*60)
    
    mock_gen = MockGenerator()
    adapter = VideoAdapterManager(mock_gen)
    
    result = adapter.convert_to_video(
        novel_data=mock_gen.novel_data,
        video_type="long_series",
        total_units=10  # 指定10集
    )
    
    print(f"✅ 转换成功")
    print(f"   视频类型: {result['video_type_name']}")
    print(f"   集数: {len(result['units'])}")
    
    # 检查每集的结构
    for ep in result['units'][:2]:  # 只显示前2集
        print(f"\n📺 第{ep['unit_number']}集:")
        print(f"   章节范围: {ep.get('chapter_range', 'N/A')}")
        print(f"   重大事件数: {len(ep.get('major_events', []))}")
        storyboard = ep.get('storyboard', {})
        print(f"   场景数: {storyboard.get('total_scenes', 0)}")
    
    print("\n✅ 长剧集模式测试通过")
    return result


def test_short_video_conversion():
    """测试短视频模式转换"""
    print("\n" + "="*60)
    print("📱 测试 3: 短视频模式")
    print("="*60)
    
    mock_gen = MockGenerator()
    adapter = VideoAdapterManager(mock_gen)
    
    result = adapter.convert_to_video(
        novel_data=mock_gen.novel_data,
        video_type="short_video"
    )
    
    print(f"✅ 转换成功")
    print(f"   视频类型: {result['video_type_name']}")
    print(f"   短视频数量: {len(result['units'])}")
    
    # 短视频每个重大事件一个视频
    total_events = sum(
        len(stage.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []))
        for stage in mock_gen.novel_data['stage_writing_plans'].values()
    )
    print(f"   原始事件数: {total_events}")
    print(f"   生成视频数: {len(result['units'])}")
    
    # 检查短视频的特殊镜头特性
    if result['units']:
        first_video = result['units'][0]
        storyboard = first_video.get('storyboard', {})
        if storyboard.get('scenes'):
            first_scene = storyboard['scenes'][0]
            shots = first_scene.get('shot_sequence', [])
            print(f"\n📱 第1个短视频镜头特点:")
            for shot in shots[:3]:
                print(f"   - {shot['shot_type']}: {shot.get('tiktok_note', shot.get('description', ''))}")
    
    print("\n✅ 短视频模式测试通过")
    return result


def test_pacing_guidelines():
    """测试节奏指导"""
    print("\n" + "="*60)
    print("📊 测试 4: 节奏指导对比")
    print("="*60)
    
    mock_gen = MockGenerator()
    adapter = VideoAdapterManager(mock_gen)
    
    # 测试三种类型的节奏
    for video_type in ['short_film', 'long_series', 'short_video']:
        result = adapter.convert_to_video(
            novel_data=mock_gen.novel_data,
            video_type=video_type
        )
        
        pacing = result.get('pacing_guidelines', {})
        print(f"\n{result['video_type_name']} 节奏指导:")
        print(f"   整体节奏: {pacing.get('overall_pace', 'N/A')}")
        print(f"   平均镜头时长: {pacing.get('average_shot_duration', 'N/A')}")
        print(f"   剪辑风格: {pacing.get('editing_style', 'N/A')}")
    
    print("\n✅ 节奏指导测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 视频生成适配器 - 完整测试套件")
    print("="*60)
    
    try:
        # 测试1: 短片模式
        short_film_result = test_short_film_conversion()
        
        # 测试2: 长剧集模式
        long_series_result = test_long_series_conversion()
        
        # 测试3: 短视频模式
        short_video_result = test_short_video_conversion()
        
        # 测试4: 节奏指导
        test_pacing_guidelines()
        
        # 总结
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        print("\n📊 测试结果总结:")
        print(f"   ✓ 短片模式: {len(short_film_result['units'])} 个单元")
        print(f"   ✓ 长剧集模式: {len(long_series_result['units'])} 集")
        print(f"   ✓ 短视频模式: {len(short_video_result['units'])} 个视频")
        print(f"   ✓ 节奏指导: 三种模式对比完成")
        print("\n🎉 视频生成适配器测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)