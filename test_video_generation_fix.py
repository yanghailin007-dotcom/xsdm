"""
测试视频生成系统修复
验证事件提取和角色设计功能
"""

import sys
sys.path.insert(0, '.')

from web.managers.novel_manager import NovelGenerationManager
from src.managers.EventExtractor import get_event_extractor
from src.utils.logger import get_logger

def test_event_extraction():
    """测试事件提取功能"""
    print("=" * 80)
    print("测试1: 事件提取功能")
    print("=" * 80)
    
    logger = get_logger("TestVideoGeneration")
    manager = NovelGenerationManager()
    
    # 获取项目列表
    projects = manager.get_novel_projects()
    if not projects:
        print("❌ 没有找到任何项目")
        return False
    
    # 选择第一个项目
    project = projects[0]
    title = project['title']
    print(f"\n📚 测试项目: {title}")
    
    # 获取项目详情
    novel_detail = manager.get_novel_detail(title)
    if not novel_detail:
        print(f"❌ 无法获取项目详情")
        return False
    
    # 使用通用事件提取器
    event_extractor = get_event_extractor(logger)
    
    # 测试1: 提取重大事件
    print("\n🔍 测试1.1: 提取重大事件...")
    major_events = event_extractor.extract_all_major_events(novel_detail)
    print(f"✅ 提取到 {len(major_events)} 个重大事件")
    
    if major_events:
        print(f"\n前3个事件示例:")
        for i, event in enumerate(major_events[:3], 1):
            print(f"  {i}. {event.get('name', '未命名')} (章节: {event.get('chapter_range', 'N/A')})")
    else:
        print("⚠️ 警告: 未提取到任何事件")
        return False
    
    # 测试2: 统计中级事件
    print("\n🔍 测试1.2: 统计中级事件...")
    medium_count = event_extractor.count_medium_events(novel_detail)
    print(f"✅ 总共 {medium_count} 个中级事件")
    
    # 测试3: 提取角色设计
    print("\n🔍 测试1.3: 提取角色设计...")
    characters = event_extractor.extract_character_designs(novel_detail)
    print(f"✅ 提取到 {len(characters)} 个角色设计")
    
    if characters:
        print(f"\n前3个角色示例:")
        for i, char in enumerate(characters[:3], 1):
            print(f"  {i}. {char.get('name', '未命名')} ({char.get('role', '未知角色')})")
        
        # 测试4: 生成角色提示词
        print("\n🔍 测试1.4: 生成角色剧照提示词...")
        character_prompts = event_extractor.generate_character_prompts(characters)
        print(f"✅ 生成了 {len(character_prompts)} 个角色提示词")
        
        if character_prompts:
            print(f"\n第一个角色提示词预览:")
            prompt = character_prompts[0].get('generation_prompt', '')
            print(f"  长度: {len(prompt)} 字符")
            print(f"  预览: {prompt[:200]}...")
    else:
        print("⚠️ 警告: 未提取到任何角色")
    
    print("\n" + "=" * 80)
    print("✅ 测试1完成: 事件提取功能正常")
    print("=" * 80)
    
    return True


def test_video_adapter():
    """测试视频适配器"""
    print("\n" + "=" * 80)
    print("测试2: 视频适配器")
    print("=" * 80)
    
    logger = get_logger("TestVideoAdapter")
    manager = NovelGenerationManager()
    
    # 获取项目列表
    projects = manager.get_novel_projects()
    if not projects:
        print("❌ 没有找到任何项目")
        return False
    
    # 选择第一个项目
    project = projects[0]
    title = project['title']
    print(f"\n📚 测试项目: {title}")
    
    # 获取项目详情
    novel_detail = manager.get_novel_detail(title)
    if not novel_detail:
        print(f"❌ 无法获取项目详情")
        return False
    
    # 测试视频适配器
    print("\n🔍 测试2.1: 长剧集模式转换...")
    from src.managers.VideoAdapterManager import VideoAdapterManager
    
    class MockGenerator:
        def __init__(self, novel_data):
            self.novel_data = novel_data
            self.api_client = None
    
    mock_generator = MockGenerator(novel_detail)
    adapter = VideoAdapterManager(mock_generator)
    
    try:
        result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type="long_series"
        )
        
        print(f"✅ 转换成功")
        print(f"   视频类型: {result.get('video_type_name', 'N/A')}")
        print(f"   单元数量: {len(result.get('units', []))}")
        print(f"   角色数量: {result.get('character_design', {}).get('total_characters', 0)}")
        
        # 检查是否有单元
        units = result.get('units', [])
        if units:
            print(f"\n第一个单元信息:")
            first_unit = units[0]
            print(f"  单元类型: {first_unit.get('unit_type', 'N/A')}")
            print(f"  单元编号: {first_unit.get('unit_number', 'N/A')}")
            print(f"  预估时长: {first_unit.get('estimated_duration_minutes', 0)} 分钟")
            
            storyboard = first_unit.get('storyboard', {})
            scenes = storyboard.get('scenes', [])
            print(f"  场景数量: {len(scenes)}")
        else:
            print("⚠️ 警告: 未生成任何单元")
            return False
        
        # 检查角色设计信息
        character_design = result.get('character_design', {})
        generation_order = character_design.get('generation_order', [])
        print(f"\n角色生成顺序:")
        for i, item in enumerate(generation_order[:5], 1):
            char = item.get('character', {})
            score = item.get('priority_score', 0)
            order = item.get('generation_order', 0)
            print(f"  {i}. {char.get('name', '未命名')} (优先级: {score}, 顺序: {order})")
        
        print("\n" + "=" * 80)
        print("✅ 测试2完成: 视频适配器正常")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ 视频适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 开始测试视频生成系统修复...\n")
    
    # 测试1: 事件提取
    test1_passed = test_event_extraction()
    
    # 测试2: 视频适配器
    test2_passed = test_video_adapter() if test1_passed else False
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"测试1 (事件提取): {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试2 (视频适配器): {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！视频生成系统修复成功！")
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
    
    print("=" * 80)