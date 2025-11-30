#!/usr/bin/env python3
"""测试所有导入"""

import sys
from pathlib import Path

BASE_DIR = Path.cwd()
sys.path.insert(0, str(BASE_DIR))

print("=" * 60)
print("🧪 测试导入链")
print("=" * 60)
print()

tests = [
    ("logger", "from src.utils.logger import get_logger"),
    ("OptimizationPrompts", "from src.prompts.OptimizationPrompts import OptimizationPrompts"),
    ("Prompts", "from src.prompts.Prompts import Prompts"),
    ("APIClient", "from src.core.APIClient import APIClient"),
    ("Contexts", "from src.core.Contexts import GenerationContext"),
    ("NovelGenerator", "from src.core.NovelGenerator import NovelGenerator"),
    ("web_server", "import web.web_server"),
]

failed = []

for name, import_stmt in tests:
    try:
        print(f"📌 Testing {name:25} ... ", end="", flush=True)
        exec(import_stmt)
        print("✅ OK")
    except Exception as e:
        print(f"❌ FAILED")
        print(f"   Error: {e}")
        failed.append((name, str(e)))

print()
print("=" * 60)

if failed:
    print(f"❌ {len(failed)} test(s) failed:")
    for name, error in failed:
        print(f"  - {name}: {error[:80]}")
    sys.exit(1)
else:
    print("✨ All imports successful!")
    print()
    print("Now you can start the web service:")
    print("  python run_web.py")
    print("=" * 60)
    sys.exit(0)
