#!/usr/bin/env python3
"""
详细计时：测量每个阶段的耗时
"""
import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 60)
print("Profiling: Detailed timing for each stage")
print("=" * 60)

total_start = time.time()

# Stage 1: Import web_config
print("\n[Stage 1] Importing web_config...")
start = time.time()
from web.web_config import logger, BASE_DIR, CREATIVE_IDEAS_FILE
stage1 = time.time() - start
print(f"   Time: {stage1:.3f}s")

# Stage 2: Import path_utils
print("\n[Stage 2] Importing path_utils...")
start = time.time()
from web.utils.path_utils import (
    get_user_novel_dir,
    get_public_projects_dir,
    find_novel_project,
    list_user_projects,
    is_admin,
    get_current_username,
    NOVEL_PROJECTS_ROOT
)
stage2 = time.time() - start
print(f"   Time: {stage2:.3f}s")

# Stage 3: Import config
print("\n[Stage 3] Importing config...")
start = time.time()
import importlib.util
config_path = BASE_DIR / "config" / "config.py"
spec = importlib.util.spec_from_file_location("config_module", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
CONFIG = config_module.CONFIG
stage3 = time.time() - start
print(f"   Time: {stage3:.3f}s")

# Stage 4: Import NovelGenerator
print("\n[Stage 4] Importing NovelGenerator...")
start = time.time()
from src.core.NovelGenerator import NovelGenerator
stage4 = time.time() - start
print(f"   Time: {stage4:.3f}s")

# Stage 5: Create NovelGenerator instance
print("\n[Stage 5] Creating NovelGenerator instance...")
start = time.time()
novel_gen = NovelGenerator(CONFIG)
stage5 = time.time() - start
print(f"   Time: {stage5:.3f}s")

# Stage 6: Import NovelGenerationManager
print("\n[Stage 6] Importing NovelGenerationManager...")
start = time.time()
from web.managers.novel_manager import NovelGenerationManager, get_novel_generator
stage6 = time.time() - start
print(f"   Time: {stage6:.3f}s")

# Stage 7: Create NovelGenerationManager instance
print("\n[Stage 7] Creating NovelGenerationManager instance...")
start = time.time()
manager = NovelGenerationManager()
stage7 = time.time() - start
print(f"   Time: {stage7:.3f}s")

# Stage 8: Get NovelGenerator via singleton
print("\n[Stage 8] Getting NovelGenerator via singleton...")
start = time.time()
novel_gen2 = get_novel_generator(CONFIG)
stage8 = time.time() - start
print(f"   Time: {stage8:.3f}s")

total = time.time() - total_start

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Stage 1 (web_config):     {stage1:.3f}s")
print(f"Stage 2 (path_utils):     {stage2:.3f}s")
print(f"Stage 3 (config):         {stage3:.3f}s")
print(f"Stage 4 (Import NG):      {stage4:.3f}s")
print(f"Stage 5 (Create NG):      {stage5:.3f}s")
print(f"Stage 6 (Import NGM):     {stage6:.3f}s")
print(f"Stage 7 (Create NGM):     {stage7:.3f}s")
print(f"Stage 8 (Singleton):      {stage8:.3f}s")
print("-" * 60)
print(f"TOTAL:                    {total:.3f}s")
print("=" * 60)
