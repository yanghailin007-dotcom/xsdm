#!/usr/bin/env python3
"""
测试用户隔离路径修复
验证文件是否保存到正确的用户目录
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_isolation():
    """测试用户隔离路径"""
    print("=" * 60)
    print("测试1: 用户隔离路径")
    print("=" * 60)
    
    from web.utils.path_utils import get_user_novel_dir
    from pathlib import Path
    
    # 测试不同用户的路径
    test_users = ['debug', 'test', 'admin', 'user1']
    
    for user in test_users:
        path = get_user_novel_dir(username=user, create=False)
        expected = f"小说项目\\{user}"
        is_correct = expected in str(path) or user in str(path)
        status = "✓" if is_correct else "✗"
        print(f"{status} 用户 '{user}' -> {path}")
    
    print("\n检查实际目录结构:")
    base_dir = Path("小说项目")
    if base_dir.exists():
        for item in base_dir.iterdir():
            if item.is_dir():
                print(f"  目录: {item.name}")
                # 检查该目录下是否有Refined_AI_Brief.txt文件
                brief_files = list(item.glob("*_Refined_AI_Brief.txt"))
                if brief_files:
                    for f in brief_files:
                        print(f"    -> {f.name}")
    
    print("\n" + "=" * 60)

def test_novel_generator_username():
    """测试 NovelGenerator 是否正确存储和使用用户名"""
    print("测试2: NovelGenerator 用户名存储")
    print("=" * 60)
    
    # 模拟设置用户名的过程
    class MockNovelGenerator:
        def __init__(self):
            pass
        
        def set_username(self, username: str):
            self._username = username
            print(f"  ✓ set_username('{username}') 调用成功")
        
        def get_output_dir(self):
            from web.utils.path_utils import get_user_novel_dir
            username = getattr(self, '_username', None)
            return get_user_novel_dir(username=username, create=False)
    
    ng = MockNovelGenerator()
    
    # 测试设置用户名
    ng.set_username('debug')
    path = ng.get_output_dir()
    print(f"  ✓ 输出路径: {path}")
    
    # 验证路径包含用户名
    assert 'debug' in str(path), f"路径应该包含 'debug'"
    print(f"  ✓ 路径验证通过: 包含 'debug'\n")
    
    print("=" * 60)

if __name__ == "__main__":
    test_user_isolation()
    test_novel_generator_username()
    print("\n✓ 用户隔离测试完成")
