#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试角色名称验证功能
"""

import sys
import io
from pathlib import Path

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.WorldStateManager import WorldStateManager

def test_character_name_validation():
    """测试角色名称验证"""
    
    # 创建WorldStateManager实例
    manager = WorldStateManager()
    
    # 测试用例：包含英文翻译的角色名称
    test_cases = [
        # (名称, 预期结果, 说明)
        ("魔渊", True, "3个汉字 + 9个字符翻译"),
        ("姜清雪", True, "4个汉字 + 15个字符翻译"),
        ("赵无极", True, "3个汉字 + 12个字符翻译"),
        ("林凡", True, "2个汉字 + 10个字符翻译"),
        ("李青元 (Li Qingyuan)", True, "3个汉字 + 15个字符翻译"),
        ("慕沛灵", True, "3个汉字 + 14个字符翻译"),
        ("张三", False, "2个汉字 - 有效但可能在黑名单中"),
        ("李", True, "1个汉字 - 常见姓氏"),
        ("A", False, "单个英文字母"),
        ("", False, "空字符串"),
        ("魔", True, "单个汉字"),
        ("This is a very long Chinese name with translation that exceeds twenty characters (ThisIsTooLong)", False, "超过20个字符"),
    ]
    
    print("=" * 80)
    print("角色名称验证测试")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for name, expected, description in test_cases:
        result = manager._is_valid_character_name(name)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} 测试: {name}")
        print(f"   说明: {description}")
        print(f"   预期: {'通过' if expected else '拒绝'}")
        print(f"   实际: {'通过' if result else '拒绝'}")
        
        if result != expected:
            print(f"   ⚠️ 测试失败!")
    
    print("\n" + "=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    # 测试新角色准入验证
    print("\n" + "=" * 80)
    print("新角色准入验证测试")
    print("=" * 80)
    
    test_characters = [
        {
            "name": "魔渊",
            "role_type": "重要配角",
            "importance": "major"
        },
        {
            "name": "姜清雪",
            "role_type": "主角",
            "importance": "major"
        },
        {
            "name": "赵无极",
            "role_type": "重要配角",
            "importance": "major"
        }
    ]
    
    for char_data in test_characters:
        name = char_data["name"]
        result = manager._should_accept_new_character(
            name,
            char_data,
            {},
            current_chapter=0
        )
        
        status = "✅" if result else "❌"
        print(f"\n{status} 角色: {name}")
        print(f"   类型: {char_data['role_type']}")
        print(f"   重要性: {char_data['importance']}")
        print(f"   结果: {'接受' if result else '拒绝'}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_character_name_validation()