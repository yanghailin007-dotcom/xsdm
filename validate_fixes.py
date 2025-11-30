#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate that all fixes are in place"""

import sys
sys.path.insert(0, '.')

from src.utils.seed_utils import ensure_seed_dict

print("Testing ensure_seed_dict function:")
print("-" * 50)

# Test 1: JSON string
test_str = '{"key": "value"}'
result1 = ensure_seed_dict(test_str)
test1_pass = isinstance(result1, dict)
print(f"Test 1 (JSON string): {'✅ PASS' if test1_pass else '❌ FAIL'} - {type(result1).__name__}")

# Test 2: Dict input
test_dict = {'key': 'value'}
result2 = ensure_seed_dict(test_dict)
test2_pass = isinstance(result2, dict)
print(f"Test 2 (dict input): {'✅ PASS' if test2_pass else '❌ FAIL'} - {type(result2).__name__}")

# Test 3: Plain string
test_str2 = 'just a string'
result3 = ensure_seed_dict(test_str2)
test3_pass = isinstance(result3, dict) and 'coreSetting' in result3
print(f"Test 3 (plain string): {'✅ PASS' if test3_pass else '❌ FAIL'} - {type(result3).__name__}")

# Test 4: Check if ProjectManager imports the function
try:
    from src.core.ProjectManager import ProjectManager
    print("Test 4 (ProjectManager import): ✅ PASS")
    test4_pass = True
except Exception as e:
    print(f"Test 4 (ProjectManager import): ❌ FAIL - {e}")
    test4_pass = False

# Test 5: Check web_server imports
try:
    from web.web_server import app
    print("Test 5 (web_server import): ✅ PASS")
    test5_pass = True
except Exception as e:
    print(f"Test 5 (web_server import): ❌ FAIL - {e}")
    test5_pass = False

print("-" * 50)
if all([test1_pass, test2_pass, test3_pass, test4_pass, test5_pass]):
    print("✅ All validation tests PASSED!")
else:
    print("❌ Some tests FAILED - check output above")
    sys.exit(1)
