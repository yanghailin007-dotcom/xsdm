"""修复已保存的故事线文件中的阶段顺序"""
import json
from pathlib import Path

# 阶段顺序
STAGE_ORDER = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
STAGE_ORDER_MAP = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

def fix_writing_plan(file_path):
    """修复写作计划文件中的阶段顺序"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'stage_names' in data and 'stages' in data:
            original = data['stage_names'].copy()
            data['stage_names'] = sorted(data['stage_names'], key=lambda x: STAGE_ORDER_MAP.get(x, 999))
            
            if original != data['stage_names']:
                print(f"  修复: {file_path.name}")
                print(f"    原始顺序: {original}")
                print(f"    修复顺序: {data['stage_names']}")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
    except Exception as e:
        print(f"  错误: {file_path.name} - {e}")
    return False

def fix_storyline(file_path):
    """修复故事线文件中的阶段顺序"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'stage_info' in data:
            # 按照章节范围排序 stage_info
            original = [item['stage_name'] for item in data['stage_info']]
            sorted_info = sorted(data['stage_info'], key=lambda x: STAGE_ORDER_MAP.get(x['stage_name'], 999))
            
            if original != [item['stage_name'] for item in sorted_info]:
                print(f"  修复: {file_path.name}")
                print(f"    原始顺序: {original}")
                print(f"    修复顺序: {[item['stage_name'] for item in sorted_info]}")
                
                data['stage_info'] = sorted_info
                
                # 同时修复 major_events 的顺序
                if 'major_events' in data:
                    # 重新组织事件顺序
                    stage_to_events = {}
                    for event in data['major_events']:
                        stage = event.get('_stage', '')
                        if stage not in stage_to_events:
                            stage_to_events[stage] = []
                        stage_to_events[stage].append(event)
                    
                    # 按阶段顺序重新排列事件
                    sorted_events = []
                    for stage in STAGE_ORDER:
                        if stage in stage_to_events:
                            sorted_events.extend(stage_to_events[stage])
                    
                    data['major_events'] = sorted_events
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
    except Exception as e:
        print(f"  错误: {file_path.name} - {e}")
    return False

# 主程序
print("=" * 60)
print("修复故事线阶段顺序")
print("=" * 60)

# 修复所有项目的 plans 目录
projects_dir = Path("小说项目")
fixed_count = 0

for project_dir in projects_dir.iterdir():
    if not project_dir.is_dir():
        continue
    
    print(f"\n检查项目: {project_dir.name}")
    
    # 修复 plans 目录中的写作计划
    plans_dir = project_dir / "plans"
    if plans_dir.exists():
        for plan_file in plans_dir.glob("*_writing_plan.json"):
            # 修复单个写作计划文件
            try:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否需要合并（如果文件包含单个阶段数据）
                # 这里我们只需要确保文件名是正确的
                # 实际的顺序问题在于合并后的 writing_plan.json
            except:
                pass
    
    # 修复合并的写作计划
    writing_plan = plans_dir / ".." / "planning" / f"{project_dir.name}_写作计划.json"
    if writing_plan.exists():
        if fix_writing_plan(writing_plan):
            fixed_count += 1
    
    # 修复故事线文件
    storyline_file = plans_dir / ".." / "planning" / f"{project_dir.name}_故事线.json"
    if storyline_file.exists():
        if fix_storyline(storyline_file):
            fixed_count += 1

print(f"\n{'=' * 60}")
print(f"修复完成！共修复 {fixed_count} 个文件")
print(f"{'=' * 60}")