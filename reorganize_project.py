"""
项目目录重组脚本
根据功能重新组织项目结构，使其更加清晰
"""

import os
import shutil
from pathlib import Path

# 定义新的目录结构
NEW_STRUCTURE = {
    # 核心代码
    "src": {
        "core": [
            "NovelGenerator.py",
            "APIClient.py",
            "ContentGenerator.py",
            "QualityAssessor.py",
            "ProjectManager.py",
            "Contexts.py",
            "EventBus.py",
        ],
        "managers": [
            "EventDrivenManager.py",
            "EventManager.py",
            "EmotionalBlueprintManager.py",
            "EmotionalPlanManager.py",
            "ForeshadowingManager.py",
            "GlobalGrowthPlanner.py",
            "RomancePatternManager.py",
            "StagePlanManager.py",
            "WorldStateManager.py",
            "WritingGuidanceManager.py",
            "ElementTimingPlanner.py",
            "StagePlanUtils.py",
        ],
        "prompts": [
            "Prompts.py",
            "BasePrompts.py",
            "AnalysisPrompts.py",
            "OptimizationPrompts.py",
            "PlanningPrompts.py",
            "WorldviewPrompts.py",
            "WritingPrompts.py",
        ],
        "utils": [
            "logger.py",
            "utils.py",
            "DouBaoImageGenerator.py",
        ],
    },
    # Web 相关
    "web": {
        "": [
            "web_server.py",
        ],
        "templates": "templates",  # 目录
        "static": "static",  # 目录
    },
    # 配置文件
    "config": [
        "config.py",
        "doubaoconfig.py",
    ],
    # 入口脚本
    "scripts": [
        "main.py",
        "automain.py",
        "start_web_server.py",
    ],
    # 测试文件
    "tests": {
        "": [
            "test_e2e_with_mock_data.py",
            "test_helper_classes.py",
            "test_integration.py",
            "test_quick.py",
            "test_web_api.py",
            "test_web_api_request.py",
            "run_all_tests.py",
        ],
        "existing": "tests",  # 保留现有 tests 目录
    },
    # 文档
    "docs": {
        "guides": [
            "WEB_GENERATION_GUIDE.md",
            "WEB_ENHANCEMENT_SUMMARY.md",
            "WEB_COMPLETE_GUIDE.md",
            "WEB_QUICK_REFERENCE.md",
            "WEB_SYSTEM_README.md",
            "WEB_SERVICE_TROUBLESHOOTING.md",
            "SETUP_GUIDE.md",
            "QUICK_START.md",
            "E2E_TEST_GUIDE.md",
        ],
        "reports": [
            "PROJECT_COMPLETION_REPORT.md",
            "WEB_SYSTEM_COMPLETION.md",
            "FINAL_ARCHITECTURE_REPORT.md",
            "FINAL_ARCHITECTURE_REPORT.txt",
            "CLEANUP_COMPLETION_SUMMARY.md",
            "CLEANUP_FINAL_SUMMARY.txt",
            "FINAL_CLEANUP_REPORT.md",
            "AUTOMAIN_BUG_FIX_REPORT.md",
            "AUTOMAIN_COMPLETE_FIX_SUMMARY.txt",
            "AUTOMAIN_FINAL_REPORT.md",
            "AUTOMAIN_QUICK_REFERENCE.md",
            "RUNTIME_FIXES_SUMMARY.md",
            "FILE_MANIFEST.md",
            "EXECUTION_STEPS.md",
        ],
        "tests": [
            "TEST_COMPLETION_SUMMARY.md",
            "TEST_FLOW_DIAGRAM.md",
            "TEST_README.md",
            "TEST_SUITE_SUMMARY.md",
            "TEST_SYSTEM_INVENTORY.md",
        ],
        "features": [
            "FEATURE_CHAPTER_NAVIGATION.md",
            "LAYOUT_OPTIMIZATION.md",
            "NAVIGATION_QUICK_START.md",
        ],
    },
    # 工具脚本
    "tools": [
        "analyze_architecture.py",
        "batch_delete_deprecated.py",
        "cleanup_deprecated_methods.py",
        "cleanup_logs_and_dead_code.py",
        "delete_deprecated_methods.py",
        "generate_cleanup_report.py",
        "generate_final_architecture_report.py",
        "remove_unused_imports.py",
        "workspace_sweep.py",
        "web_api_demo.py",
    ],
    # 数据目录
    "data": {
        "projects": "小说项目",  # 重命名为 projects
        "creative_ideas": [
            "novel_ideas.txt",
            "novel_ideas copy.txt",
        ],
        "quality_data": "quality_data",  # 目录
        "generated_images": "generated_images",  # 目录
        "debug_responses": "debug_responses",  # 目录
    },
    # 其他资源
    "resources": {
        "models": "models",  # 目录
        "prompts": "optimized_prompts",  # 目录
        "driver_notes": "Driver_Notes",  # 目录
    },
}

# 根目录保留的文件
ROOT_FILES = [
    "requirements.txt",
    "README.md",
    ".gitignore",
    "doubao_generator.log",
]


def create_directory_structure(base_path: Path):
    """创建新的目录结构"""
    print("📁 创建新目录结构...")

    directories = [
        "src/core",
        "src/managers",
        "src/prompts",
        "src/utils",
        "web",
        "config",
        "scripts",
        "tests",
        "docs/guides",
        "docs/reports",
        "docs/tests",
        "docs/features",
        "tools",
        "data/projects",
        "data/creative_ideas",
        "resources",
    ]

    for dir_path in directories:
        (base_path / dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {dir_path}")


def move_files(base_path: Path, structure: dict, parent_key: str = ""):
    """递归移动文件到新位置"""
    for key, value in structure.items():
        current_path = parent_key + ("/" + key if key else "")

        if isinstance(value, dict):
            # 递归处理子目录
            move_files(base_path, value, current_path)
        elif isinstance(value, list):
            # 移动文件列表
            for file_name in value:
                src = base_path / file_name
                dest = base_path / current_path / file_name

                if src.exists() and src != dest:
                    print(f"  📦 移动: {file_name} -> {current_path}/")
                    try:
                        shutil.move(str(src), str(dest))
                    except Exception as e:
                        print(f"    ⚠️  移动失败: {e}")
        elif isinstance(value, str):
            # 移动目录
            src = base_path / value
            dest = base_path / current_path / key if key else base_path / current_path / value

            if src.exists() and src != dest:
                print(f"  📁 移动目录: {value} -> {dest}")
                try:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(src), str(dest))
                except Exception as e:
                    print(f"    ⚠️  移动失败: {e}")


def create_init_files(base_path: Path):
    """创建 __init__.py 文件使其成为包"""
    print("\n📝 创建 __init__.py 文件...")

    init_dirs = [
        "src",
        "src/core",
        "src/managers",
        "src/prompts",
        "src/utils",
    ]

    for dir_path in init_dirs:
        init_file = base_path / dir_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Auto-generated __init__.py\n")
            print(f"  ✅ {dir_path}/__init__.py")


def update_imports_reference():
    """生成导入路径更新参考"""
    print("\n📋 生成导入路径更新参考...")

    import_updates = {
        # 原路径 -> 新路径
        "from NovelGenerator import": "from src.core.NovelGenerator import",
        "from APIClient import": "from src.core.APIClient import",
        "from ContentGenerator import": "from src.core.ContentGenerator import",
        "from QualityAssessor import": "from src.core.QualityAssessor import",
        "from ProjectManager import": "from src.core.ProjectManager import",
        "from Contexts import": "from src.core.Contexts import",
        "from EventBus import": "from src.core.EventBus import",

        "import EventDrivenManager": "from src.managers import EventDrivenManager",
        "import EventManager": "from src.managers import EventManager",
        "import ForeshadowingManager": "from src.managers import ForeshadowingManager",
        "import GlobalGrowthPlanner": "from src.managers import GlobalGrowthPlanner",
        "import StagePlanManager": "from src.managers import StagePlanManager",
        "import ElementTimingPlanner": "from src.managers import ElementTimingPlanner",

        "from Prompts import": "from src.prompts.Prompts import",
        "from logger import": "from src.utils.logger import",
        "from config import": "from config.config import",
    }

    return import_updates


def generate_migration_guide(base_path: Path):
    """生成迁移指南"""
    guide_content = """# 📋 项目重组迁移指南

## 新的目录结构

```
work6.03/
├── src/                      # 核心源代码
│   ├── core/                 # 核心模块
│   │   ├── NovelGenerator.py
│   │   ├── APIClient.py
│   │   ├── ContentGenerator.py
│   │   ├── QualityAssessor.py
│   │   ├── ProjectManager.py
│   │   ├── Contexts.py
│   │   └── EventBus.py
│   ├── managers/             # 管理器模块
│   │   ├── EventDrivenManager.py
│   │   ├── EventManager.py
│   │   ├── EmotionalBlueprintManager.py
│   │   ├── ForeshadowingManager.py
│   │   ├── GlobalGrowthPlanner.py
│   │   └── ...
│   ├── prompts/              # 提示词模块
│   │   ├── Prompts.py
│   │   ├── BasePrompts.py
│   │   ├── AnalysisPrompts.py
│   │   └── ...
│   └── utils/                # 工具模块
│       ├── logger.py
│       └── utils.py
├── web/                      # Web 服务
│   ├── web_server.py
│   ├── templates/
│   └── static/
├── config/                   # 配置文件
│   ├── config.py
│   └── doubaoconfig.py
├── scripts/                  # 入口脚本
│   ├── main.py
│   ├── automain.py
│   └── start_web_server.py
├── tests/                    # 测试文件
│   ├── test_*.py
│   └── run_all_tests.py
├── docs/                     # 文档
│   ├── guides/              # 使用指南
│   ├── reports/             # 项目报告
│   ├── tests/               # 测试文档
│   └── features/            # 功能文档
├── tools/                    # 工具脚本
│   └── *.py
├── data/                     # 数据存储
│   ├── projects/            # 小说项目 (原 小说项目)
│   ├── creative_ideas/      # 创意想法
│   ├── quality_data/        # 质量数据
│   ├── generated_images/    # 生成的图片
│   └── debug_responses/     # 调试响应
├── resources/                # 资源文件
│   ├── models/
│   ├── prompts/
│   └── driver_notes/
└── requirements.txt          # 依赖

```

## 导入路径变更

### 核心模块

```python
# 旧
from NovelGenerator import NovelGenerator
from APIClient import APIClient

# 新
from src.core.NovelGenerator import NovelGenerator
from src.core.APIClient import APIClient
```

### 管理器模块

```python
# 旧
import EventManager
import GlobalGrowthPlanner

# 新
from src.managers import EventManager
from src.managers import GlobalGrowthPlanner
```

### 提示词模块

```python
# 旧
from src.prompts.Prompts import Prompts

# 新
from src.prompts.Prompts import Prompts
```

### 配置和工具

```python
# 旧
from config import CONFIG
from src.utils.logger import get_logger

# 新
from config.config import CONFIG
from src.utils.logger import get_logger
```

## 路径配置更新

### config.py 中的路径

```python
# 旧
"project_dir": "小说项目"

# 新
"project_dir": "data/projects"
```

### ProjectManager 中的路径

```python
# 旧
self.project_dir = "小说项目"

# 新
self.project_dir = "data/projects"
```

### Web 服务器中的路径

```python
# 旧
template_folder='templates'
static_folder='static'

# 新
template_folder='web/templates'
static_folder='web/static'
```

## 迁移步骤

1. **备份现有代码**
   ```bash
   # 建议先 git commit 或备份
   ```

2. **运行重组脚本**
   ```bash
   python reorganize_project.py
   ```

3. **更新导入路径**
   - 手动或使用工具更新所有 import 语句

4. **测试验证**
   ```bash
   python -m pytest tests/
   python scripts/main.py
   python web/web_server.py
   ```

## 优势

✅ **清晰的模块划分** - 按功能分类
✅ **易于导航** - 快速找到需要的文件
✅ **便于维护** - 职责明确
✅ **扩展友好** - 添加新功能更简单
✅ **专业标准** - 符合 Python 项目规范

## 注意事项

⚠️ 更新所有导入路径
⚠️ 检查相对路径引用
⚠️ 更新配置文件中的路径
⚠️ 测试所有功能确保正常
"""

    guide_file = base_path / "MIGRATION_GUIDE.md"
    guide_file.write_text(guide_content, encoding='utf-8')
    print(f"  ✅ 生成迁移指南: MIGRATION_GUIDE.md")


def main():
    """主函数"""
    print("=" * 60)
    print("🔧 项目目录重组工具")
    print("=" * 60)

    base_path = Path(__file__).parent
    print(f"\n📂 当前目录: {base_path}")

    # 询问确认
    print("\n⚠️  此操作将重组整个项目目录结构")
    confirm = input("是否继续？(yes/no): ").lower().strip()

    if confirm != 'yes':
        print("❌ 操作已取消")
        return

    # 创建目录结构
    create_directory_structure(base_path)

    # 移动文件
    print("\n📦 移动文件到新位置...")
    move_files(base_path, NEW_STRUCTURE)

    # 创建 __init__.py
    create_init_files(base_path)

    # 生成迁移指南
    generate_migration_guide(base_path)

    print("\n" + "=" * 60)
    print("✅ 目录重组完成！")
    print("=" * 60)
    print("\n📋 下一步:")
    print("  1. 查看 MIGRATION_GUIDE.md 了解详细变更")
    print("  2. 运行 update_imports.py 自动更新导入路径")
    print("  3. 测试所有功能确保正常运行")


if __name__ == "__main__":
    main()
