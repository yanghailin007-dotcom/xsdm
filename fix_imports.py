#!/usr/bin/env python3
"""
修复导入路径 - 处理所有关键的导入路径更新
"""

import re
from pathlib import Path

def fix_web_server():
    """修复web_server.py的导入问题"""
    file_path = Path("web/web_server.py")
    content = file_path.read_text(encoding='utf-8')
    original = content

    # 修复导入路径
    replacements = [
        # 核心模块
        (r'from logger import', 'from src.utils.logger import'),
        (r'from NovelGenerator import', 'from src.core.NovelGenerator import'),
        (r'from config import', 'from config.config import'),
        (r'from Contexts import', 'from src.core.Contexts import'),

        # Flask路径配置
        (r"template_folder='templates'", "template_folder='web/templates'"),
        (r"static_folder='static'", "static_folder='web/static'"),
        (r'template_folder="templates"', 'template_folder="web/templates"'),
        (r'static_folder="static"', 'static_folder="web/static"'),
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print("✅ web_server.py imports fixed")
        return True
    return False

def fix_scripts():
    """修复脚本文件的导入"""
    scripts = [
        "scripts/main.py",
        "scripts/automain.py",
    ]

    total_fixes = 0

    for script in scripts:
        file_path = Path(script)
        if not file_path.exists():
            print(f"⚠️  File not found: {script}")
            continue

        content = file_path.read_text(encoding='utf-8')
        original = content

        # 修复导入
        replacements = [
            # NovelGenerator
            (r'from NovelGenerator import', 'from src.core.NovelGenerator import'),
            (r'import NovelGenerator', 'from src.core import NovelGenerator'),

            # Config
            (r'from config import', 'from config.config import'),
            (r'import config', 'import config.config as config'),
        ]

        for old, new in replacements:
            content = re.sub(old, new, content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ {script} imports fixed")
            total_fixes += 1
        else:
            print(f"ℹ️  {script} no changes needed")

    return total_fixes > 0

def fix_config():
    """修复config.py中的导入"""
    file_path = Path("config/config.py")
    if not file_path.exists():
        print("❌ config.py not found")
        return False

    content = file_path.read_text(encoding='utf-8')
    original = content

    # 修复logger导入
    content = re.sub(r'from logger import', 'from src.utils.logger import', content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print("✅ config.py imports fixed")
        return True
    print("ℹ️  config.py no changes needed")
    return False

def main():
    """主函数"""
    print("🔧 修复导入路径...")

    fixes_made = False

    if fix_config():
        fixes_made = True

    if fix_web_server():
        fixes_made = True

    if fix_scripts():
        fixes_made = True

    if fixes_made:
        print("\n✅ 导入路径修复完成！")
    else:
        print("\nℹ️  没有需要修复的内容")

if __name__ == "__main__":
    main()