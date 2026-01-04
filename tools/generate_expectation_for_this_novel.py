"""
为指定小说生成期待感映射
"""
import sys
import json
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.ExpectationManager import ExpectationManager, ExpectationType
from src.managers.StagePlanUtils import parse_chapter_range

def select_expectation_type(event):
    """根据事件特征智能选择期待感类型"""
    main_goal = event.get('main_goal', '').lower()
    emotional_focus = event.get('emotional_focus', '').lower()
    name = event.get('name', '').lower()
    description = event.get('description', '').lower()
    role_in_stage_arc = event.get('role_in_stage_arc', '').lower()
    
    all_text = f'{main_goal} {emotional_focus} {name} {description} {role_in_stage_arc}'
    
    scores = {
        ExpectationType.SUPPRESSION_RELEASE: 0,
        ExpectationType.SHOWCASE: 0,
        ExpectationType.MYSTERY_FORESHADOW: 0,
        ExpectationType.EMOTIONAL_HOOK: 0,
        ExpectationType.POWER_GAP: 0,
        ExpectationType.NESTED_DOLL: 0
    }
    
    # 压抑释放
    suppression_keywords = ['击败', '战胜', '复仇', '反击', '雪耻', '逆袭', '反杀', '报仇',
                           '报复', '反击战', '翻盘', '逆转', '反攻', '压制', '杀敌', '屠杀']
    for kw in suppression_keywords:
        if kw in all_text:
            scores[ExpectationType.SUPPRESSION_RELEASE] += 3
    
    # 展示橱窗
    showcase_keywords = ['获得', '得到', '炼成', '夺取', '收获', '宝物', '神器',
                         '功法', '秘籍', '法宝', '装备', '宝藏', '发现', '解锁', '吞噬']
    for kw in showcase_keywords:
        if kw in all_text:
            scores[ExpectationType.SHOWCASE] += 3
    
    # 伏笔揭秘
    mystery_keywords = ['揭秘', '真相', '发现', '秘密', '身世', '阴谋', '计谋', '背后',
                        '来历', '身份', '真实', '隐藏', '揭开', '曝光']
    for kw in mystery_keywords:
        if kw in all_text:
            scores[ExpectationType.MYSTERY_FORESHADOW] += 3
    
    # 情绪钩子
    emotion_keywords = ['误解', '轻视', '震惊', '打脸', '羞辱', '嘲讽', '看不起',
                        '不屑', '挑衅', '羞耻', '愤怒', '爆发', '羞辱']
    for kw in emotion_keywords:
        if kw in all_text:
            scores[ExpectationType.EMOTIONAL_HOOK] += 3
    
    # 实力差距
    power_keywords = ['展示', '学习', '修炼', '提升', '突破', '成长', '进阶', '升级',
                      '功法', '实力', '境界', '进化']
    for kw in power_keywords:
        if kw in all_text:
            scores[ExpectationType.POWER_GAP] += 2
    
    # 套娃期待
    nested_keywords = ['挑战', '任务', '试炼', '考验', '闯关', '冒险', '探索',
                       '旅程', '征程', '历练']
    for kw in nested_keywords:
        if kw in all_text:
            scores[ExpectationType.NESTED_DOLL] += 2
    
    # 选择得分最高的类型
    final_type = max(scores.items(), key=lambda x: x[1])[0]
    return final_type

def generate_expectation_for_novel(novel_title: str):
    """
    为指定小说生成期待感映射
    """
    print(f"🎯 开始为《{novel_title}》生成期待感映射...")
    
    # 查找项目目录
    project_dir = Path("小说项目") / novel_title
    
    if not project_dir.exists():
        import re
        safe_title = re.sub(r'[\\/*?"<>|]', "_", novel_title)
        project_dir = Path("小说项目") / safe_title
    
    if not project_dir.exists():
        print(f"❌ 未找到项目目录: {project_dir}")
        return False
    
    print(f"✅ 找到项目目录: {project_dir}")
    
    # 尝试多个可能的写作计划位置
    possible_plan_files = [
        project_dir / "planning" / f"{novel_title}_写作计划.json",
        project_dir / "plans" / f"{novel_title}_写作计划.json",
        project_dir / "stage_writing_plans" / "writing_plan.json",
    ]
    
    writing_plan_file = None
    for file_path in possible_plan_files:
        if file_path.exists():
            writing_plan_file = file_path
            break
    
    if not writing_plan_file:
        # 尝试查找任何包含写作计划的文件
        for json_file in project_dir.rglob("*.json"):
            if "writing_plan" in json_file.name or "写作计划" in json_file.name:
                writing_plan_file = json_file
                break
    
    if not writing_plan_file:
        print(f"❌ 未找到写作计划文件")
        return False
    
    print(f"✅ 找到写作计划: {writing_plan_file}")
    
    # 读取写作计划
    try:
        with open(writing_plan_file, 'r', encoding='utf-8') as f:
            writing_plan = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False
    
    # 初始化期待感管理器
    expectation_manager = ExpectationManager()
    total_tagged = 0
    
    # 提取所有阶段的重大事件
    stages = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
    
    for stage_name in stages:
        if stage_name not in writing_plan:
            continue
        
        stage_data = writing_plan[stage_name].get('stage_writing_plan', writing_plan[stage_name])
        major_events = stage_data.get('event_system', {}).get('major_events', [])
        
        if not major_events:
            continue
        
        print(f"\n📋 处理阶段: {stage_name}")
        print(f"   找到 {len(major_events)} 个重大事件")
        
        for event in major_events:
            event_name = event.get('name', '未命名事件')
            chapter_range = event.get('chapter_range', '1-10')
            main_goal = event.get('main_goal', '')
            
            # 解析章节范围
            try:
                start_ch, end_ch = parse_chapter_range(chapter_range)
                target_ch = max(start_ch + 3, end_ch)
            except:
                target_ch = end_ch if chapter_range else 10
                start_ch = 1
            
            # 智能选择期待类型
            exp_type = select_expectation_type(event)
            
            # 种植期待
            exp_id = expectation_manager.tag_event_with_expectation(
                event_id=event_name,
                expectation_type=exp_type,
                planting_chapter=start_ch,
                description=f"{event_name}: {main_goal[:80]}...",
                target_chapter=target_ch
            )
            
            total_tagged += 1
            print(f"   ✓ 为事件添加期待: {event_name} -> {exp_type.value}")
    
    # 导出期待感映射
    expectation_map = expectation_manager.export_expectation_map()
    
    # 保存到项目目录
    expectation_map_file = project_dir / "expectation_map.json"
    with open(expectation_map_file, 'w', encoding='utf-8') as f:
        json.dump({
            'novel_title': novel_title,
            'expectation_map': expectation_map,
            'total_tagged': total_tagged,
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'generation_method': 'ai_enhanced_rules'
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ 期待感映射生成完成！")
    print(f"  总计: {total_tagged} 个事件")
    print(f"  保存路径: {expectation_map_file}")
    print(f"{'='*60}")
    
    return True

if __name__ == "__main__":
    novel_title = "重生成剑：宿主祭天，法力无边"
    
    print("="*60)
    print("为现有项目生成期待感映射")
    print("="*60)
    print(f"小说标题: {novel_title}")
    print("="*60)
    
    success = generate_expectation_for_novel(novel_title)
    
    if success:
        print("\n✅ 期待感映射生成成功！")
        print("\n下一步：")
        print("1. 刷新故事线页面，应该能看到期待感标签了")
        print("2. 新生成的项目会自动包含期待感映射")
    else:
        print("\n❌ 期待感映射生成失败")