"""测试阶段名称提取逻辑"""
import re

STAGE_ORDER = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
STAGE_ORDER_MAP = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

def extract_stage_name(filename):
    """从文件名提取阶段名称"""
    # 文件名格式: 吞噬万界：从一把生锈铁剑开始_climax_stage_writing_plan.json
    match = re.search(r'_([^_]+_stage)_writing_plan$', filename)
    if match:
        return match.group(1)
    else:
        # 备用方案：尝试从 stem 中提取
        stem = filename.replace('_writing_plan.json', '')
        parts = stem.split('_')
        stage_name = None
        for i, part in enumerate(parts):
            if 'stage' in part and i > 0:
                stage_parts = []
                for j in range(1, i + 1):
                    stage_parts.append(parts[j])
                stage_name = '_'.join(stage_parts)
                break
        return stage_name

# 测试文件名
test_files = [
    "吞噬万界：从一把生锈铁剑开始_climax_stage_writing_plan.json",
    "吞噬万界：从一把生锈铁剑开始_development_stage_writing_plan.json",
    "吞噬万界：从一把生锈铁剑开始_ending_stage_writing_plan.json",
    "吞噬万界：从一把生锈铁剑开始_opening_stage_writing_plan.json",
]

print("=" * 80)
print("测试阶段名称提取")
print("=" * 80)

file_stage_pairs = []
for filename in test_files:
    stage_name = extract_stage_name(filename)
    if stage_name and stage_name in STAGE_ORDER_MAP:
        file_stage_pairs.append((stage_name, filename))
        print(f"\n[OK] {filename}")
        print(f"  Extracted stage: {stage_name}")
    else:
        print(f"\n[FAIL] {filename}")
        print(f"  Extracted stage: {stage_name}")

print(f"\n{'=' * 80}")
print(f"Before sorting:")
for stage, file in file_stage_pairs:
    print(f"  {stage}: {file}")

# 按照标准阶段顺序排序
sorted_pairs = sorted(file_stage_pairs, key=lambda x: STAGE_ORDER_MAP.get(x[0], 999))

print(f"\nAfter sorting:")
for stage, file in sorted_pairs:
    print(f"  {stage}: {file}")

print(f"\n{'=' * 80}")
print(f"Final order: {[p[0] for p in sorted_pairs]}")
print(f"Expected order: {STAGE_ORDER}")
print(f"{'=' * 80}")

if [p[0] for p in sorted_pairs] == STAGE_ORDER:
    print("\n[SUCCESS] Sorting is correct!")
else:
    print("\n[ERROR] Sorting is wrong!")