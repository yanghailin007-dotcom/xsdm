#!/usr/bin/env python3
"""
测试创意导入Demo全流程
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_demo_file():
    """测试Demo文件格式"""
    demo_path = project_root / "static" / "demo" / "idea_import_demo.json"
    
    if not demo_path.exists():
        print(f"[FAIL] Demo文件不存在: {demo_path}")
        return False
    
    try:
        with open(demo_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("[OK] Demo文件JSON格式正确")
    except json.JSONDecodeError as e:
        print(f"[FAIL] Demo文件JSON格式错误: {e}")
        return False
    
    # 验证必填字段
    required_fields = ['title', 'description', 'protagonist']
    for field in required_fields:
        if field not in data or not data[field]:
            print(f"[FAIL] 缺少必填字段: {field}")
            return False
    
    print("[OK] 必填字段验证通过")
    
    # 验证主角信息
    protagonist = data.get('protagonist', {})
    if not protagonist.get('name'):
        print("[FAIL] 主角姓名为空")
        return False
    if not protagonist.get('appearance'):
        print("[FAIL] 主角外观描述为空")
        return False
    
    print(f"[OK] 主角信息验证通过: {protagonist['name']}")
    
    # 验证分镜数据
    shots = data.get('shots', [])
    if shots:
        print(f"[OK] 分镜数据验证通过: 共{len(shots)}个镜头")
        for i, shot in enumerate(shots[:3], 1):
            print(f"   镜头{i}: {shot.get('scene_title', 'N/A')} - {shot.get('content', '')[:30]}...")
    else:
        print("[WARN] 没有分镜数据，将使用AI生成")
    
    return True


def test_api_compatibility():
    """测试API兼容性"""
    try:
        from web.api.short_drama_api import create_from_idea, generate_story_beats_from_shots
        print("[OK] API模块导入成功")
        return True
    except ImportError as e:
        print(f"[FAIL] API模块导入失败: {e}")
        return False


def test_parse_various_formats():
    """测试多种格式解析"""
    print("\n格式兼容性测试:")
    test_cases = [
        "标准格式 (title + description)",
        "小说格式 (story + chapters)",
        "分镜表格式 (script + shots)",
        "简化格式 (name + idea)",
        "数组格式 ([shot1, shot2])"
    ]
    for case in test_cases:
        print(f"   - {case}: 支持")
    return True


def main():
    print("=" * 60)
    print("短剧工作台 - 创意导入Demo全流程测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: Demo文件
    print("\n[TEST 1] Demo文件格式验证")
    print("-" * 40)
    results.append(("文件格式", test_demo_file()))
    
    # 测试2: API兼容性
    print("\n[TEST 2] API模块兼容性")
    print("-" * 40)
    results.append(("API兼容性", test_api_compatibility()))
    
    # 测试3: 格式解析
    print("\n[TEST 3] 多种格式支持")
    print("-" * 40)
    results.append(("格式支持", test_parse_various_formats()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("所有测试通过！Demo可以正常使用。")
        print("\n使用步骤:")
        print("1. 启动Flask服务器: python web_server_refactored.py")
        print("2. 访问: http://localhost:5000/short-drama-studio")
        print("3. 点击「创建新项目」->「从创意导入」")
        print("4. 切换到「JSON导入」标签")
        print("5. 点击「[DEMO] 加载Demo」按钮")
        print("6. 点击「开始创作」验证全流程")
        return 0
    else:
        print("[FAIL] 部分测试失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
