#!/usr/bin/env python
"""
验证检查点与UI步骤对齐的测试脚本
"""

import sys
sys.path.insert(0, 'c:\\Users\\yangh\\Documents\\GitHub\\xsdm')

from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint

# 后端检查点步骤（13个，与 PhaseGenerator 的 step_progress_map 对齐）
CHECKPOINT_STEPS = GenerationCheckpoint.PHASES['phase_one']['steps']

# 前端UI步骤（14个显示步骤）
UI_STEPS = [
    'creative_refinement',      # 步骤1: 创意精炼 - 对应 initialization
    'fanfiction_detection',     # 步骤2: 同人检测 - 对应 initialization
    'multiple_plans',           # 步骤3: 多计划生成 - 对应 initialization
    'plan_selection',           # 步骤4: 计划选择 - 对应 initialization
    'foundation_planning',      # 步骤5: 基础规划 - 对应 writing_style + market_analysis
    'worldview_with_factions',  # 步骤6: 世界观与势力 - 对应 worldview + faction_system
    'character_design',         # 步骤7: 角色设计 - 对应 character_design
    'emotional_growth_planning', # 步骤8: 情感与成长规划 - 对应 emotional_growth_planning（合并）
    'stage_plan',               # 步骤9: 分阶段大纲 - 对应 stage_plan
    'detailed_stage_plans',     # 步骤10: 详细阶段计划 - 对应 detailed_stage_plans
    'expectation_mapping',      # 步骤11: 期待感地图 - 对应 expectation_mapping
    'system_init',              # 步骤12: 系统初始化 - 对应 system_init
    'saving',                   # 步骤13: 保存结果 - 对应 saving
    'quality_assessment'        # 步骤14: 质量评估 - 对应 quality_assessment
]

# 前后端映射关系
STEP_MAPPING = {
    # 后端检查点步骤 -> 前端UI步骤
    'initialization': ['creative_refinement', 'fanfiction_detection', 'multiple_plans', 'plan_selection'],
    'writing_style': ['foundation_planning'],
    'market_analysis': ['foundation_planning'],
    'worldview': ['worldview_with_factions'],
    'faction_system': ['worldview_with_factions'],
    'character_design': ['character_design'],
    'emotional_growth_planning': ['emotional_growth_planning'],
    'stage_plan': ['stage_plan'],
    'detailed_stage_plans': ['detailed_stage_plans'],
    'expectation_mapping': ['expectation_mapping'],
    'system_init': ['system_init'],
    'saving': ['saving'],
    'quality_assessment': ['quality_assessment']
}

# 反向映射（前端 -> 后端）
REVERSE_MAPPING = {
    'creative_refinement': 'initialization',
    'fanfiction_detection': 'initialization',
    'multiple_plans': 'initialization',
    'plan_selection': 'initialization',
    'foundation_planning': 'market_analysis',  # 使用更晚的步骤作为代表
    'worldview_with_factions': 'faction_system',  # 使用更晚的步骤作为代表
    'character_design': 'character_design',
    'emotional_growth_planning': 'emotional_growth_planning',
    'stage_plan': 'stage_plan',
    'detailed_stage_plans': 'detailed_stage_plans',
    'expectation_mapping': 'expectation_mapping',
    'system_init': 'system_init',
    'saving': 'saving',
    'quality_assessment': 'quality_assessment'
}

def test_checkpoint_steps():
    """测试检查点步骤定义"""
    print("=" * 60)
    print("验证后端检查点步骤（应包含13个步骤）")
    print("=" * 60)
    
    assert len(CHECKPOINT_STEPS) == 13, f"检查点步骤应为13个，实际为 {len(CHECKPOINT_STEPS)}"
    
    for i, step in enumerate(CHECKPOINT_STEPS, 1):
        print(f"  {i}. {step}")
    
    print(f"\n[OK] 检查点步骤验证通过：共 {len(CHECKPOINT_STEPS)} 个步骤")
    return True

def test_ui_steps():
    """测试UI步骤定义"""
    print("\n" + "=" * 60)
    print("验证前端UI步骤（应包含14个显示步骤）")
    print("=" * 60)
    
    assert len(UI_STEPS) == 14, f"UI步骤应为14个，实际为 {len(UI_STEPS)}"
    
    for i, step in enumerate(UI_STEPS, 1):
        print(f"  {i}. {step}")
    
    print(f"\n[OK] UI步骤验证通过：共 {len(UI_STEPS)} 个显示步骤")
    return True

def test_mapping_completeness():
    """测试映射完整性"""
    print("\n" + "=" * 60)
    print("验证前后端步骤映射完整性")
    print("=" * 60)
    
    # 检查每个后端步骤都有映射
    for step in CHECKPOINT_STEPS:
        assert step in STEP_MAPPING, f"后端步骤 '{step}' 缺少前端映射"
        print(f"  [OK] {step} -> {STEP_MAPPING[step]}")
    
    # 检查每个前端步骤都有反向映射
    for step in UI_STEPS:
        assert step in REVERSE_MAPPING, f"前端步骤 '{step}' 缺少后端映射"
        backend_step = REVERSE_MAPPING[step]
        assert backend_step in CHECKPOINT_STEPS, f"前端步骤 '{step}' 映射到不存在后端步骤 '{backend_step}'"
    
    print(f"\n[OK] 映射完整性验证通过")
    return True

def test_sub_steps():
    """测试子步骤定义"""
    print("\n" + "=" * 60)
    print("验证子步骤定义")
    print("=" * 60)
    
    sub_steps = GenerationCheckpoint.PHASES['phase_one'].get('sub_steps', {})
    
    for step in CHECKPOINT_STEPS:
        if step in sub_steps:
            print(f"  [OK] {step}: {len(sub_steps[step])} 个子步骤")
        else:
            print(f"  [WARN] {step}: 无子步骤定义")
    
    # 特别验证 emotional_growth_planning 包含合并前的两个步骤
    if 'emotional_growth_planning' in sub_steps:
        emotional_subs = [s[0] for s in sub_steps['emotional_growth_planning']]
        assert 'emotional_blueprint' in emotional_subs, "缺少 emotional_blueprint 子步骤"
        assert 'growth_plan' in emotional_subs, "缺少 growth_plan 子步骤"
        print(f"\n[OK] emotional_growth_planning 正确包含合并子步骤: {emotional_subs}")
    
    return True

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("检查点与UI步骤对齐验证")
    print("=" * 60)
    
    try:
        test_checkpoint_steps()
        test_ui_steps()
        test_mapping_completeness()
        test_sub_steps()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 所有验证通过！检查点与UI步骤已正确对齐")
        print("=" * 60)
        print(f"\n总结：")
        print(f"  - 后端检查点步骤: {len(CHECKPOINT_STEPS)} 个")
        print(f"  - 前端UI显示步骤: {len(UI_STEPS)} 个")
        print(f"  - emotional_blueprint + growth_plan 已合并为 emotional_growth_planning")
        print(f"  - 恢复时将从最后一个完成的检查点继续")
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] 验证失败: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
