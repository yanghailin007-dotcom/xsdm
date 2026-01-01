"""
测试视频生成修复 - 验证写作计划加载是否正确
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from web.managers.novel_manager import NovelGenerationManager
from src.utils.logger import get_logger

logger = get_logger("test_video_generation_fix")

def test_writing_plans_loading():
    """测试写作计划是否正确加载"""
    
    print("=" * 60)
    print("🧪 测试写作计划加载")
    print("=" * 60)
    
    # 初始化管理器
    manager = NovelGenerationManager()
    
    # 测试小说标题
    title = "吞噬万界：从一把生锈铁剑开始"
    
    # 获取小说详情
    novel_detail = manager.get_novel_detail(title)
    
    if not novel_detail:
        print(f"❌ 无法找到小说: {title}")
        return False
    
    print(f"\n✅ 成功加载小说: {title}")
    
    # 检查 quality_data
    quality_data = novel_detail.get("quality_data", {})
    print(f"\n📊 quality_data 存在: {bool(quality_data)}")
    
    # 检查 writing_plans
    writing_plans = quality_data.get("writing_plans", {})
    print(f"📝 writing_plans 键: {list(writing_plans.keys())}")
    
    # 验证键是否正确
    expected_stages = ["opening_stage", "development_stage", "climax_stage", "ending_stage"]
    actual_stages = list(writing_plans.keys())
    
    print(f"\n🔍 验证阶段名称:")
    print(f"   期望的阶段: {expected_stages}")
    print(f"   实际的阶段: {actual_stages}")
    
    # 检查是否包含 "unknown"
    if "unknown" in actual_stages:
        print(f"\n❌ 发现错误: writing_plans 包含 'unknown' 键")
        print(f"   这意味着阶段名提取失败")
        return False
    
    # 检查是否包含所有期望的阶段
    missing_stages = [stage for stage in expected_stages if stage not in actual_stages]
    if missing_stages:
        print(f"\n⚠️ 警告: 缺少以下阶段: {missing_stages}")
    else:
        print(f"\n✅ 所有期望的阶段都存在")
    
    # 检查每个阶段的数据结构
    print(f"\n📋 检查各阶段数据结构:")
    for stage_name in actual_stages:
        plan_data = writing_plans.get(stage_name, {})
        if isinstance(plan_data, dict):
            stage_writing_plan = plan_data.get("stage_writing_plan", {})
            if isinstance(stage_writing_plan, dict):
                events = stage_writing_plan.get("event_system", {}).get("major_events", [])
                print(f"   ✅ {stage_name}: 包含 {len(events)} 个重大事件")
            else:
                print(f"   ❌ {stage_name}: stage_writing_plan 不是字典")
        else:
            print(f"   ❌ {stage_name}: plan_data 不是字典")
    
    # 测试 EventExtractor
    print(f"\n🔧 测试 EventExtractor:")
    try:
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        
        all_events = event_extractor.extract_all_major_events(novel_detail)
        print(f"   ✅ EventExtractor 成功提取到 {len(all_events)} 个重大事件")
        
        if len(all_events) > 0:
            print(f"   ✅ 修复成功！事件提取正常工作")
            return True
        else:
            print(f"   ❌ 提取到 0 个事件，可能还有问题")
            return False
            
    except Exception as e:
        print(f"   ❌ EventExtractor 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_writing_plans_loading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过 - 写作计划加载修复成功")
    else:
        print("❌ 测试失败 - 需要进一步检查")
    print("=" * 60)