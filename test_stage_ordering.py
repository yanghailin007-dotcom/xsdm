"""测试阶段排序逻辑"""

# 模拟的 STAGE_ORDER
STAGE_ORDER = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
STAGE_ORDER_MAP = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

def get_sorted_stages(stage_names):
    """按照标准阶段顺序排序阶段名称"""
    # 分离标准阶段和非标准阶段
    standard_stages = [s for s in stage_names if s in STAGE_ORDER_MAP]
    non_standard_stages = [s for s in stage_names if s not in STAGE_ORDER_MAP]
    
    # 标准阶段按预定顺序排序，非标准阶段保持原顺序
    sorted_standard = sorted(standard_stages, key=lambda x: STAGE_ORDER_MAP[x])
    
    return sorted_standard + non_standard_stages

# 测试数据
test_cases = [
    ['climax_stage', 'development_stage', 'ending_stage', 'opening_stage'],
    ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage'],
    ['development_stage', 'opening_stage', 'climax_stage'],
]

print("=" * 60)
print("测试阶段排序逻辑")
print("=" * 60)

for i, test_case in enumerate(test_cases, 1):
    result = get_sorted_stages(test_case)
    print(f"\n测试用例 {i}:")
    print(f"  输入: {test_case}")
    print(f"  输出: {result}")
    print(f"  ✓ 正确" if result == STAGE_ORDER[:len(result)] else "  ✗ 错误")

print("\n" + "=" * 60)
print("测试文件排序逻辑（模拟文件系统返回的字母顺序）")
print("=" * 60)

# 模拟文件系统返回的顺序（字母排序）
file_stage_pairs = [
    ('climax_stage', 'file_climax.json'),
    ('development_stage', 'file_development.json'),
    ('ending_stage', 'file_ending.json'),
    ('opening_stage', 'file_opening.json'),
]

print(f"\n原始文件顺序（字母排序）:")
for stage, file in file_stage_pairs:
    print(f"  {file} -> {stage}")

# 使用 STAGE_ORDER_MAP 排序
sorted_pairs = sorted(file_stage_pairs, key=lambda x: STAGE_ORDER_MAP.get(x[0], 999))

print(f"\n排序后的文件顺序:")
for stage, file in sorted_pairs:
    print(f"  {file} -> {stage}")

expected_order = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
actual_order = [stage for stage, _ in sorted_pairs]
print(f"\n✓ 排序正确" if actual_order == expected_order else "✗ 排序错误")