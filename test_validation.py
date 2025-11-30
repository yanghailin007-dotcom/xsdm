#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test if the stage plan generation validation passes"""

import sys
import json
import os

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.MockAPIClient import MockAPIClient

client = MockAPIClient(config={})

# Simulate the validation logic used in StagePlanManager._generate_detailed_stage_plan_for_opening_or_development
print("Simulating validation logic from StagePlanManager...")
print()

for attempt in range(3):
    print(f"Attempt {attempt + 1}:")
    try:
        result = client.generate_content_with_retry(
            content_type="stage_major_event_skeleton",
            user_prompt="test prompt",
            purpose="test"
        )
        
        print(f"  - Result type: {type(result)}")
        print(f"  - Is dict: {isinstance(result, dict)}")
        if isinstance(result, dict):
            print(f"  - Has 'major_event_skeletons' key: {'major_event_skeletons' in result}")
            if 'major_event_skeletons' in result:
                print(f"  - Is list: {isinstance(result['major_event_skeletons'], list)}")
                print(f"  - List length: {len(result['major_event_skeletons'])}")
        
        # The actual check from StagePlanManager
        if result and isinstance(result, dict) \
            and "major_event_skeletons" in result \
            and isinstance(result["major_event_skeletons"], list):
            print(f"  - VALIDATION PASSED - breaking out of loop")
            break
        else:
            print(f"  - VALIDATION FAILED - will retry")
    except Exception as e:
        print(f"  - ERROR: {e}")

print("\nTest complete")
