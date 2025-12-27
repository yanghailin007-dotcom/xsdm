#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试第一阶段结果加载修复
"""

import json
import os
import sys
import re

def test_api_logic():
    """测试API中的第一阶段结果加载逻辑"""
    
    novel_title = "凡人：满级体修，绑定韩立刷爆了"
    
    print("=" * 60)
    print("Test Phase One Loading Fix")
    print("=" * 60)
    
    # 1. 测试路径处理
    print("\n1. Test Path Processing:")
    safe_title = re.sub(r'[\\/*?"<>|]', "_", novel_title)
    original_title = novel_title
    
    print(f"   Original title: {novel_title}")
    print(f"   Safe title: {safe_title}")
    
    # 测试路径列表
    possible_paths = [
        f"小说项目/{original_title}_第一阶段设定/{original_title}_第一阶段设定.json",
        f"小说项目/{original_title}_第一阶段设定/{original_title}_第一阶段索引.json",
        f"小说项目/{safe_title}_第一阶段设定/{safe_title}_第一阶段设定.json",
        f"小说项目/{safe_title}_第一阶段设定/{safe_title}_第一阶段索引.json",
        f"小说项目/{original_title}/project_info",
        f"小说项目/{safe_title}/project_info"
    ]
    
    phase_one_result = None
    actual_file = None
    
    for path in possible_paths:
        print(f"\n   Testing: {path}")
        print(f"   Exists: {os.path.exists(path)}")
        
        if os.path.exists(path):
            if os.path.isdir(path):
                print(f"   Type: Directory")
                files = [f for f in os.listdir(path) if f.endswith('.json')]
                print(f"   Files: {files}")
                
                for file in files:
                    file_path = f"{path}/{file}"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 检查是否是索引文件
                        if 'products_mapping' in data:
                            print(f"   ✅ Found index file: {file_path}")
                            print(f"   Products: {list(data.get('products_mapping', {}).keys())}")
                            phase_one_result = data
                            actual_file = file_path
                            break
                    except Exception as e:
                        print(f"   ⚠️ 读取失败: {e}")
                
                if phase_one_result:
                    break
            else:
                print(f"   Type: File")
                try:
                    with open(path, '+ encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"   ✅ Loaded file: {path}")
                    phase_one_result = data
                    actual_file = path
                    break
                except Exception as e:
                    print(f"   ❌ 读取失败: {e}")
    
    if phase_one_result:
        print(f"\n   ✅ SUCCESS: Loaded phase one result")
        print(f"   Actual file: {actual_file}")
        
        # 检查是否是索引文件
        if 'products_mapping' in phase_one_result:
            pm = phase_one_result['products_mapping']
            print(f"\n2. Test Products Mapping:")
            print(f"   Total products: {len(pm)}")
            
            # 测试产物文件是否存在
            for category, file_path in pm.items():
                exists = os.path.exists(file_path)
                print(f"   {category}: {'✅' if exists else '❌'} - {file_path}")
                
                if category == 'writing':
                    print(f"\n3. Test Writing Plan Content:")
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            wp_data = json.load(f)
                        print(f"   Writing plan keys: {list(wp_data.keys())}")
                        
                        # 检查是否有阶段数据
                        for stage in ['opening_stage', 'development_stage', '<arg_value>climax_stage', 'ending_stage']:
                            if stage in wp_data:
                                stage_data = wp_data[stage]
                                if isinstance(stage_data, dict):
                                    print(f"   {stage}: {list(stage_data.keys())[:5]}")
                                    if 'stage_writing_plan' in stage_data:
                                        print(f"      Has stage_writing_plan: ✅")
                                    else:
                                        print(f"      Has stage_writing_plan: ❌")
    else:
        print("\n   ❌ FAIL: Cannot load phase one result")
        return False
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_api_logic()
    sys.exit(0 if success else 1)