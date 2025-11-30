#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试MockAPIClient返回的数据格式"""

import sys
import json
import os

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.MockAPIClient import MockAPIClient

# Test major event skeleton
print("=" * 60)
print("Testing stage_major_event_skeleton return")
print("=" * 60)

client = MockAPIClient(config={})
result = client.generate_content_with_retry(
    content_type="stage_major_event_skeleton",
    user_prompt="test",
    purpose="test"
)

print("Return data type:", type(result))

# Check if it has major_event_skeletons
if isinstance(result, dict) and "major_event_skeletons" in result:
    print("[OK] Contains major_event_skeletons")
    if isinstance(result["major_event_skeletons"], list):
        print(f"[OK] major_event_skeletons is a list with {len(result['major_event_skeletons'])} items")
    else:
        print("[ERROR] major_event_skeletons is not a list")
else:
    print("[ERROR] Does not contain major_event_skeletons")

# Test decomposition
print("\n" + "=" * 60)
print("Testing major_event_decomposition return")
print("=" * 60)

result2 = client.generate_content_with_retry(
    content_type="major_event_decomposition",
    user_prompt="test",
    purpose="test"
)

print("Return data type:", type(result2))
print("Key fields check:")
print(f"  - Has 'composition': {'composition' in result2}")
print(f"  - Has 'special_emotional_events': {'special_emotional_events' in result2}")
print(f"  - Has 'emotional_arc_summary': {'emotional_arc_summary' in result2}")

if "composition" in result2:
    print(f"  - composition type: {type(result2['composition'])}")
    if isinstance(result2['composition'], dict):
        print(f"    - Contains phases: {list(result2['composition'].keys())}")

print("\n[OK] Test complete")

