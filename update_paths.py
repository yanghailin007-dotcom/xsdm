#!/usr/bin/env python3
"""
批量更新项目路径配置
将硬编码的路径更新为新的目录结构
"""

import re
from pathlib import Path

def update_project_manager():
    """更新 ProjectManager.py 中的路径"""
    file_path = Path("src/core/ProjectManager.py")

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # 路径替换映射
    replacements = {
        r'"小说项目"': '"data/projects"',
        r"'小说项目'": "'data/projects'",
        r'f"小说项目/': 'f"data/projects/',
        r"f'小说项目/": "f'data/projects/",
    }

    for old, new in replacements.items():
        content = re.sub(old, new, content)

    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print("✅ ProjectManager.py 路径已更新")
        return True
    else:
        print("ℹ️  ProjectManager.py 无需更新")
        return False

def update_config():
    """更新 config.py 中的导入"""
    file_path = Path("config/config.py")

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # 更新 logger 导入
    content = re.sub(r'from logger import', 'from src.utils.logger import', content)

    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print("✅ config.py 导入已更新")
        return True
    else:
        print("ℹ️  config.py 无需更新")
        return False

def update_main_scripts():
    """更新主脚本中的导入"""
    scripts = [
        "scripts/main.py",
        "scripts/automain.py",
        "web/web_server.py",
    ]

    updates_made = False

    for script_path in scripts:
        path = Path(script_path)

        if not path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            continue

        content = path.read_text(encoding='utf-8')
        original_content = content

        # 导入映射
        import_mappings = [
            (r'from NovelGenerator import', 'from src.core.NovelGenerator import'),
            (r'import NovelGenerator', 'from src.core import NovelGenerator'),
            (r'from config import', 'from config.config import'),
            (r'from logger import', 'from src.utils.logger import'),
            (r'import Contexts', 'from src.core import Contexts'),
            (r'from EventDrivenManager import', 'from src.managers import EventDrivenManager'),
            (r'import EventDrivenManager', 'from src.managers import EventDrivenManager'),
            (r'from EventManager import', 'from src.managers import EventManager'),
            (r'import EventManager', 'from src.managers import EventManager'),
            (r'from EmotionalBlueprintManager import', 'from src.managers import EmotionalBlueprintManager'),
            (r'from ForeshadowingManager import', 'from src.managers import ForeshadowingManager'),
            (r'import ForeshadowingManager', 'from src.managers import ForeshadowingManager'),
            (r'from GlobalGrowthPlanner import', 'from src.managers import GlobalGrowthPlanner'),
            (r'import GlobalGrowthPlanner', 'from src.managers import GlobalGrowthPlanner'),
            (r'from RomancePatternManager import', 'from src.managers import RomancePatternManager'),
            (r'import RomancePatternManager', 'from src.managers import RomancePatternManager'),
            (r'from StagePlanManager import', 'from src.managers import StagePlanManager'),
            (r'import StagePlanManager', 'from src.managers import StagePlanManager'),
            (r'from WorldStateManager import', 'from src.managers import WorldStateManager'),
            (r'import WorldStateManager', 'from src.managers import WorldStateManager'),
            (r'from WritingGuidanceManager import', 'from src.managers import WritingGuidanceManager'),
            (r'import WritingGuidanceManager', 'from src.managers import WritingGuidanceManager'),
            (r'from ElementTimingPlanner import', 'from src.managers import ElementTimingPlanner'),
            (r'import ElementTimingPlanner', 'from src.managers import ElementTimingPlanner'),
            (r'from Prompts import', 'from src.prompts.Prompts import'),
            (r'from BasePrompts import', 'from src.prompts.BasePrompts import'),
            (r'from AnalysisPrompts import', 'from src.prompts.AnalysisPrompts import'),
            (r'from OptimizationPrompts import', 'from src.prompts.OptimizationPrompts import'),
            (r'from PlanningPrompts import', 'from src.prompts.PlanningPrompts import'),
            (r'from WorldviewPrompts import', 'from src.prompts.WorldviewPrompts import'),
            (r'from WritingPrompts import', 'from src.prompts.WritingPrompts import'),
            (r'from ContentGenerator import', 'from src.core.ContentGenerator import'),
            (r'import ContentGenerator', 'from src.core import ContentGenerator'),
            (r'from QualityAssessor import', 'from src.core.QualityAssessor import'),
            (r'import QualityAssessor', 'from src.core import QualityAssessor'),
            (r'from ProjectManager import', 'from src.core.ProjectManager import'),
            (r'import ProjectManager', 'from src.core import ProjectManager'),
            (r'from Contexts import', 'from src.core.Contexts import'),
            (r'from EventBus import', 'from src.core.EventBus import'),
            (r'import EventBus', 'from src.core import EventBus'),
        ]

        changes = 0
        for old, new in import_mappings:
            old_content = content
            content = re.sub(old, new, content, flags=re.MULTILINE)
            if content != old_content:
                changes += 1

        if content != original_content:
            path.write_text(content, encoding='utf-8')
            print(f"✅ {script_path} 已更新 ({changes} 处修改)")
            updates_made = True
        else:
            print(f"ℹ️  {script_path} 无需更新")

    return updates_made

def update_web_server_paths():
    """更新 web_server.py 中的模板和静态文件路径"""
    file_path = Path("web/web_server.py")

    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False

    content = file_path.read_text(encoding='utf-8')
    original_content = content

    # 更新 Flask 配置中的路径
    replacements = [
        (r"template_folder='templates'", "template_folder='web/templates'"),
        (r"static_folder='static'", "static_folder='web/static'"),
        (r'template_folder="templates"', 'template_folder="web/templates"'),
        (r'static_folder="static"', 'static_folder="web/static"'),
    ]

    changes = 0
    for old, new in replacements:
        content = re.sub(old, new, content)

    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print("✅ web_server.py 路径配置已更新")
        return True
    else:
        print("ℹ️  web_server.py 路径配置无需更新")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔄 批量更新路径配置")
    print("=" * 60)

    updates_made = False

    # 更新各种文件
    print("\n📝 更新配置文件...")
    if update_config():
        updates_made = True

    print("\n📁 更新 ProjectManager...")
    if update_project_manager():
        updates_made = True

    print("\n🌐 更新 Web 服务器路径...")
    if update_web_server_paths():
        updates_made = True

    print("\n🔄 更新主脚本导入...")
    if update_main_scripts():
        updates_made = True

    print("\n" + "=" * 60)
    if updates_made:
        print("✅ 路径配置更新完成！")
        print("\n📋 下一步:")
        print("  1. 测试核心功能")
        print("  2. 测试 Web 服务")
        print("  3. 运行测试套件")
    else:
        print("ℹ️  没有需要更新的内容")
    print("=" * 60)

if __name__ == "__main__":
    main()