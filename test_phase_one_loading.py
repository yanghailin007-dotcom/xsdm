#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试第一阶段结果加载
"""

import json
import os
import sys

def test_phase_one_loading():
    """测试加载第一阶段结果"""
    
    novel_title = "凡人：满级体修，绑定韩立刷爆了"
    # 注意：实际的文件名保留了冒号和逗号
    # 但是文件系统不支持某些字符，所以需要检查实际文件名
    
    # 测试路径 - 使用原始标题
    test_paths = [
        f"小说项目/{novel_title}_第一阶段设定/{novel_title}_第一阶段设定.json",
        f"小说项目/{novel_title}_第一阶段设定/{novel_title}_第一阶段索引.json",
        f"小说项目/{novel_title}/{novel_title}_第一阶段设定/{novel_title}_第一阶段索引.json",
    ]
    
    print("=" * 60)
    print("Test Phase One Loading")
    print("=" * 60)
    
    # 1. 测试索引文件查找
    print("\n1. Test Index File Search:")
    for path in test_paths:
        exists = os.path.exists(path)
        print(f"   {path}: {'OK - Exists' if exists else 'FAIL - Not Exists'}")
        if exists:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"      - Has products_mapping: {'OK' in data}")
                print(f"      - Has novel_title: {'OK' in data}")
                if 'products_mapping' in data:
                    pm = data['products_mapping']
                    print(f"      - products_mapping has {len(pm)} products")
                    for key, value in pm.items():
                        print(f"        * {key}: {os.path.exists(value)}")
            except Exception as e:
                print(f"      FAIL to read: {e}")
    
    # 2. 测试实际产物文件加载
    print("\n2. Test Product Files Loading:")
    index_file = f"小说项目/{novel_title}_第一阶段设定/{novel_title}_第一阶段索引.json"
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        products_mapping = index_data.get('products_mapping', {})
        
        # 测试写作计划文件
        writing_plan_path = products_mapping.get('stage_writing_plans')
        if writing_plan_path and os.path.exists(writing_plan_path):
            print(f"   OK - Writing plan exists: {writing_plan_path}")
            with open(writing_plan_path, 'r', encoding='utf-8') as f:
                writing_plan = json.load(f)
            print(f"      - Contains stages: {list(writing_plan.keys())}")
            
            # 检查每个阶段的数据
            for stage_name in writing_plan.keys():
                stage_data = writing_plan[stage_name]
                print(f"      - {stage_name}: {type(stage_data).__name__}")
                if isinstance(stage_data, dict):
                    print(f"        Has keys: {list(stage_data.keys())[:5]}")
        else:
            print(f"   FAIL - Writing plan not exists: {writing_plan_path}")
    
    # 3. 测试API加载逻辑
    print("\n3. Simulate API Loading Logic:")
    possible_paths = [
        f"小说项目/{novel_title}_第一阶段设定/{novel_title}_第一阶段设定.json",
        f"小说项目/{novel_title}_第一阶段设定/{novel_title}_第一阶段索引.json",
        f"小说项目/{novel_title}/{novel_title}_第一阶段设定/{novel_title}_第一阶段设定.json",
        f"小说项目/{novel_title}/{novel_title}_第一阶段设定/{novel_title}_第一阶段索引.json",
        f"小说项目/{novel_title}/project_info",
        f"小说项目/{novel_title}/{novel_title}_项目信息.json",
        f"小说项目/{novel_title}_项目信息.json"
    ]
    
    phase_one_result = None
    actual_file = None
    
    for path in possible_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                # 是目录，查找JSON文件
                files = [f for f in os.listdir(path) if f.endswith('.json')]
                for file in files:
                    file_path = f"{path}/{file}"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 检查是否包含核心数据
                        has_core_data = any(key in data for key in [
                            'core_worldview', 'character_design', 'global_growth_plan',
                            'overall_stage_plans', 'stage_writing_plans', 'market_analysis',
                            'products_mapping', 'novel_title', 'creative_seed'
                        ])
                        
                        if has_core_data:
                            phase_one_result = data
                            actual_file = file_path
                            print(f"   OK - Loaded from directory: {file_path}")
                            break
                    except:
                        continue
                
                if phase_one_result:
                    break
            else:
                # 是文件，直接读取
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        phase_one_result = json.load(f)
                    actual_file = path
                    print(f"   OK - Loaded from file: {path}")
                    break
                except Exception as e:
                    print(f"   WARNING - Failed to read: {path}, {e}")
    
    if phase_one_result:
        print(f"\n   SUCCESS - Loaded phase one result")
        print(f"   Actual file: {actual_file}")
        print(f"   Has keys: {list(phase_one_result.keys())[:10]}")
        
        # 如果是索引文件，检查products_mapping
        if 'products_mapping' in phase_one_result:
            pm = phase_one_result['products_mapping']
            print(f"   Products mapping: {len(pm)} products")
            if 'stage_writing_plans' in pm:
                print(f"   OK - Writing plan path: {pm['stage_writing_plans']}")
                writing_plan_exists = os.path.exists(pm['stage_writing_plans'])
                print(f"   Writing plan file exists: {'OK' if writing_plan_exists else 'FAIL'}")
    else:
        print(f"\n   FAIL - Cannot load phase one result")
        return False
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_phase_one_loading()
    sys.exit(0 if success else 1)