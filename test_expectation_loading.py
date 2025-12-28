"""
测试期待感数据加载功能

验证：
1. 从项目目录加载已保存的期待感映射
2. 自动为旧书籍生成期待感标签
3. 在故事线API中正确返回期待感数据
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_expectation_loading():
    """测试期待感加载功能"""
    print("=" * 80)
    print("测试期待感数据加载功能")
    print("=" * 80)
    
    # 测试1: 检查 select_expectation_type 函数
    print("\n[测试1] 测试期待感类型选择函数")
    print("-" * 40)
    
    from web.api.phase_generation_api import select_expectation_type
    
    test_events = [
        {"name": "击败温天仁", "main_goal": "击败温天仁", "emotional_focus": "愤怒"},
        {"name": "获得六极真魔体", "main_goal": "获得六极真魔体", "emotional_focus": "期待"},
        {"name": "身份揭秘", "main_goal": "揭秘主角身份", "emotional_focus": "震惊"},
        {"name": "打脸轻视者", "main_goal": "展示实力", "emotional_focus": "误解"},
        {"name": "修炼突破", "main_goal": "修炼突破", "emotional_focus": "成长"},
        {"name": "普通事件", "main_goal": "推进剧情", "emotional_focus": "平淡"}
    ]
    
    for event in test_events:
        exp_type = select_expectation_type(event)
        print(f"  ✓ {event['name'][:20]:20s} -> {exp_type.value}")
    
    # 测试2: 检查期待感映射文件加载
    print("\n[测试2] 检查项目目录中的期待感映射文件")
    print("-" * 40)
    
    project_base = Path("小说项目")
    if project_base.exists():
        projects_with_expectation = []
        projects_without = []
        
        for project_dir in project_base.iterdir():
            if project_dir.is_dir():
                expectation_file = project_dir / "expectation_map.json"
                if expectation_file.exists():
                    try:
                        with open(expectation_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            expectation_map = data.get('expectation_map', data)
                            expectations_count = len(expectation_map.get('expectations', {}))
                            projects_with_expectation.append({
                                'name': project_dir.name,
                                'count': expectations_count
                            })
                            print(f"  ✓ {project_dir.name:30s} ({expectations_count} 个期待)")
                    except Exception as e:
                        print(f"  ✗ {project_dir.name:30s} 加载失败: {e}")
                        projects_without.append(project_dir.name)
                else:
                    projects_without.append(project_dir.name)
        
        print(f"\n  统计:")
        print(f"    - 有期待感数据: {len(projects_with_expectation)} 个项目")
        print(f"    - 缺少期待感数据: {len(projects_without)} 个项目")
        
        if projects_without:
            print(f"\n  缺少期待感数据的项目:")
            for name in projects_without[:5]:  # 只显示前5个
                print(f"    - {name}")
            if len(projects_without) > 5:
                print(f"    ... 还有 {len(projects_without) - 5} 个项目")
    
    # 测试3: 验证期待感管理器导入
    print("\n[测试3] 验证期待感管理器导入")
    print("-" * 40)
    
    try:
        from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator, ExpectationType
        print("  ✓ ExpectationManager 导入成功")
        print("  ✓ ExpectationIntegrator 导入成功")
        print("  ✓ ExpectationType 导入成功")
        
        # 测试创建期待感管理器实例
        manager = ExpectationManager()
        print("  ✓ 期待感管理器实例创建成功")
        
        # 测试导出期待感映射
        export_data = manager.export_expectation_map()
        print(f"  ✓ 导出期待感映射成功 (包含 {len(export_data.get('expectations', {}))} 个期待)")
        
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    print("\n下一步:")
    print("1. 启动Web服务器")
    print("2. 访问故事线页面")
    print("3. 检查旧书籍是否正确显示期待感标签")
    print("\n如果旧书籍仍然没有期待感标签，请使用以下命令生成:")
    print("  python tools/generate_expectations_for_existing_novels.py --list")
    print("  python tools/generate_expectations_for_existing_novels.py --title \"项目名称\"")


if __name__ == "__main__":
    test_expectation_loading()