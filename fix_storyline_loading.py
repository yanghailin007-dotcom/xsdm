"""
修复故事线加载顺序 - 直接按照指定顺序从plans目录加载文件
顺序: opening_stage -> development_stage -> climax_stage -> ending_stage
"""
import json
from pathlib import Path

# 标准阶段顺序
STAGE_ORDER = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']

def load_storyline_in_correct_order(project_dir):
    """按照正确的阶段顺序加载故事线"""
    plans_dir = Path(project_dir) / "plans"
    
    if not plans_dir.exists():
        print(f"  [ERROR] plans directory does not exist: {plans_dir}")
        return None
    
    print(f"\n[*] Processing project: {Path(project_dir).name}")
    print(f"  plans directory: {plans_dir}")
    
    # 按照标准顺序收集文件
    stage_files = {}
    
    # 遍历所有写作计划文件
    for stage_file in plans_dir.glob("*_writing_plan.json"):
        print(f"  Found file: {stage_file.name}")
        
        # 从文件名提取阶段名称
        # 文件名格式: 吞噬万界：从一把生锈铁剑开始_<stage>_writing_plan.json
        parts = stage_file.stem.split('_')
        
        # 查找阶段名称（包含'_stage'的部分）
        stage_name = None
        for i, part in enumerate(parts):
            if 'stage' in part and i > 0:
                # 可能是 xxx_stage 格式
                # 重建阶段名称（可能包含多个下划线）
                stage_parts = []
                for j in range(1, i + 1):
                    stage_parts.append(parts[j])
                stage_name = '_'.join(stage_parts)
                break
        
        if not stage_name:
            # 尝试另一种方式：直接在文件名中查找
            import re
            match = re.search(r'_([^_]+_stage)_writing_plan$', stage_file.name)
            if match:
                stage_name = match.group(1)
        
        print(f"    Extracted stage name: {stage_name}")
        
        if stage_name and stage_name in STAGE_ORDER:
            stage_files[stage_name] = stage_file
            print(f"    [OK] Matched standard stage: {stage_name}")
        else:
            print(f"    [!] Non-standard stage or cannot parse")
    
    print(f"\n  Found standard stage files:")
    for stage in STAGE_ORDER:
        if stage in stage_files:
            print(f"    [OK] {stage}: {stage_files[stage].name}")
        else:
            print(f"    [X] {stage}: Not found")
    
    # 按照标准顺序加载阶段数据
    all_major_events = []
    stage_info = []
    
    print(f"\n  Loading stage data in order:")
    for stage_name in STAGE_ORDER:
        if stage_name not in stage_files:
            continue
        
        stage_file = stage_files[stage_name]
        print(f"\n  Loading {stage_name}:")
        print(f"    File: {stage_file.name}")
        
        try:
            with open(stage_file, 'r', encoding='utf-8') as f:
                stage_data = json.load(f)
            
            stage_plan = stage_data.get('stage_writing_plan', {})
            major_events = stage_plan.get('event_system', {}).get('major_events', [])
            chapter_range = stage_plan.get('chapter_range', '')
            
            print(f"    Chapter range: {chapter_range}")
            print(f"    Major events: {len(major_events)}")
            
            if major_events:
                # 为每个事件添加阶段信息
                for event in major_events:
                    event['_stage'] = stage_name
                    event['_chapter_range'] = chapter_range
                
                all_major_events.extend(major_events)
                
                stage_info.append({
                    'stage_name': stage_name,
                    'chapter_range': chapter_range,
                    'major_event_count': len(major_events)
                })
                
                print(f"    [OK] Added {len(major_events)} events")
        
        except Exception as e:
            print(f"    [ERROR] Loading failed: {e}")
            import traceback
            traceback.print_exc()
    
    if not all_major_events:
        print(f"\n  [ERROR] No major events found")
        return None
    
    # 构建故事线数据
    storyline_data = {
        'stage_info': stage_info,
        'total_major_events': len(all_major_events),
        'major_events': all_major_events,
        'stage_name': '全书',
        'chapter_range': '1-200'
    }
    
    print(f"\n[SUCCESS] Storyline generated:")
    print(f"  Stages: {len(stage_info)}")
    print(f"  Total events: {len(all_major_events)}")
    print(f"  Stage order:")
    for info in stage_info:
        print(f"    {info['stage_name']}: {info['chapter_range']} ({info['major_event_count']} events)")
    
    return storyline_data

def save_storyline(project_dir, storyline_data):
    """保存故事线到文件"""
    project_path = Path(project_dir)
    planning_dir = project_path / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    title = project_path.name
    storyline_file = planning_dir / f"{title}_故事线.json"
    
    # 保存故事线
    with open(storyline_file, 'w', encoding='utf-8') as f:
        json.dump(storyline_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVE] Storyline saved: {storyline_file}")
    return storyline_file

# 主程序
if __name__ == "__main__":
    print("=" * 80)
    print("Fix Storyline Loading Order")
    print("=" * 80)
    print(f"Standard stage order: {' -> '.join(STAGE_ORDER)}")
    print("=" * 80)
    
    # 处理指定项目
    project_title = "吞噬万界：从一把生锈铁剑开始"
    projects_dir = Path("小说项目")
    project_dir = projects_dir / project_title
    
    if not project_dir.exists():
        print(f"\n[ERROR] Project directory does not exist: {project_dir}")
        exit(1)
    
    # 加载故事线
    storyline = load_storyline_in_correct_order(project_dir)
    
    if storyline:
        # 保存故事线
        save_storyline(project_dir, storyline)
        
        print(f"\n{'=' * 80}")
        print(f"[SUCCESS] Fix completed!")
        print(f"{'=' * 80}")
        
        # 输出事件顺序验证
        print(f"\nVerifying event order:")
        current_stage = None
        for event in storyline['major_events'][:10]:  # 只显示前10个
            stage = event.get('_stage', 'unknown')
            if stage != current_stage:
                print(f"\n  {stage}:")
                current_stage = stage
            print(f"    - {event.get('name', 'unnamed')} (章节: {event.get('_chapter_range', 'N/A')})")
    else:
        print(f"\n{'=' * 80}")
        print(f"[ERROR] Fix failed!")
        print(f"{'=' * 80}")